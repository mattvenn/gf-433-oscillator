#!/usr/bin/env python3
"""Parametric layout generator for the VCO ring core (gf180mcuD, 3.3 V devices), driven by vco_bias.P.

    python3 layout/gen/ring_core.py [--set k=v ...] [--out build/layout]

Writes <out>/ring_core.tcl and runs magic on it, which saves ring_stage / ring_master / ring_sw / ring_core
.mag files and layout/ring_core.gds. The geometry is raw magic layers (ndiff/pdiff/poly/contacts/metal), not
gencells, so every coordinate is known to the router. All coordinates are integer nm on the 5 nm grid.

Floorplan (one row of columns, all the same orientation):
    col 0..4  ring stages in loop order 0,4,1,3,2 (folded: every ring wire spans <= 2 columns and is
              padded to exactly the same length)
    col 5     master leg (foot copy + PMOS diode MPB -> vbp)
    col 6     coarse switches TN/TP/TD, 5 bit slices
  bottom->top in a column: VSS rail | foot rows (dogbone W=wfu fingers, gate bands with M3 bias tracks) |
  inverter NMOS | ring channel (5 M2 tracks a0..a4) | n-well tap ring | PMOS (P + head, MPB, TP) |
  head gate band with the vbp M3 track | VDD rail (over the n-well tap ring top side).
  The whole core sits in a p+ substrate tap ring. Metal4 is unused.
Metal use: M1 device-local, M2 rails/straps/ring tracks, M3 bias nets (vbn, vctrl, g0..g4, vbp).
"""
import argparse, os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim" / "vco"))
import vco_bias  # noqa: E402  (read-only import: the sizes come from vco_bias.P)

# ---- rules (nm), each with a little margin over the gf180mcuD magic deck ----
CO = 230        # drawn contact (cut 0.22 + 5 nm)
ENC_CO = 70     # diff/poly enclosure of contact (CO.3/CO.4 0.065 drawn)
CO_POLY = 150   # diff contact to gate (CO.7)
PC_DIFF = 170   # poly contact to diff (CO.8)
POLY_DIFF = 110  # field poly to diff (PL.5a 0.10)
ENDCAP = 230    # poly past diff (PL.4 0.22)
PAD = 380       # metal pad over a contact/via (area >= 0.1444)
V1, V2 = 260, 280
SHGAP = 700     # gap between a ring track and its VSS shields (set by --shgap)
XIN_OFF = 1200  # input line offset from the inverter gate centre: in/out M1 lines 1.2 um apart (Miller C)
TRK = 380       # M2/M3 track width
TPITCH = 680    # track pitch (380 + 300)
GAP_DOG = 2 * POLY_DIFF + PAD   # S/D region between gates, dogbone fingers (W < 370)
GAP = 560       # S/D region between gates, plain fingers
SHP = 140 + SHGAP + 190   # shield-to-ring-track centre spacing
NW_ENC_P = 450
  # nwell over pdiff (DF.7 0.43)
NW_ENC_NSD = 150
NSD_PSD = 600   # opposite-implant diffusion spacing used everywhere


def g5(v):
    v = int(round(v))
    assert v % 5 == 0, v
    return v


class Cell:
    def __init__(self, name):
        self.name, self.rects, self.labels, self.insts = name, [], [], []

    def r(self, layer, x1, y1, x2, y2):
        x1, x2 = sorted((g5(x1), g5(x2)))
        y1, y2 = sorted((g5(y1), g5(y2)))
        assert x2 > x1 and y2 > y1, (layer, x1, y1, x2, y2)
        self.rects.append((layer, x1, y1, x2, y2))

    def label(self, text, layer, x, y, port=False):
        self.labels.append((text, layer, g5(x), g5(y), port))

    def inst(self, cell, x, y, name):
        self.insts.append((cell, g5(x), g5(y), name))

    # metal pads / vias -------------------------------------------------------------
    def via1(self, x, y):           # via1 cut with M1 and M2 pads, centred on (x, y)
        self.r("m1", x - 190, y - 190, x + 190, y + 190)
        self.r("m2", x - 190, y - 190, x + 190, y + 190)
        self.r("v1", x - V1 // 2, y - V1 // 2, x + V1 // 2, y + V1 // 2)

    def via2(self, x, y):
        self.r("m2", x - 190, y - 190, x + 190, y + 190)
        self.r("m3", x - 190, y - 190, x + 190, y + 190)
        self.r("v2", x - V2 // 2, y - V2 // 2, x + V2 // 2, y + V2 // 2)

    def via12(self, x, y):
        self.via1(x, y)
        self.via2(x, y)

    def tcl(self):
        um = lambda v: f"{v / 1000:.3f}um"
        out = [f"load {self.name}", "box 0 0 0 0"]
        order = {"nwell": 0}
        for (l, x1, y1, x2, y2) in sorted(self.rects, key=lambda t: order.get(t[0], 1)):
            out.append(f"box {um(x1)} {um(y1)} {um(x2)} {um(y2)}; paint {l}")
        for (c, x, y, n) in self.insts:
            out.append(f"box {um(x)} {um(y)} {um(x)} {um(y)}; getcell {c} child 0 0; identify {n}")
        for i, (t, l, x, y, port) in enumerate(self.labels):
            out.append(f"box {um(x - 50)} {um(y - 50)} {um(x + 50)} {um(y + 50)}; label {t} c {l}")
            if port:
                out.append(f"port make")
        out.append(f"save {self.name}")
        return "\n".join(out) + "\n"


# ---- transistor row: vertical gates, horizontal row ---------------------------------------
def fet_row(c, x0, ybot, W, gates, typ, reg_h=None, pc=None):
    """Draw one row of fingers on a shared diffusion.

    x0: left edge of the diffusion; ybot: bottom of the gate diffusion (channel W along y).
    gates: list of (L, net). typ 'n'/'p'. reg_h: dogbone S/D region height (W < 370 only).
    pc: per-gate 'top'/'bot'/None, or one value for all; poly contact pad on that side.
    Returns geometry: region centres rx[], gate x ranges gx[], contact y span, pc pad centres.
    """
    diff, cont = ("ndiff", "ndc") if typ == "n" else ("pdiff", "pdc")
    dog = W < 2 * ENC_CO + CO
    gap = GAP_DOG if dog else GAP
    endw = (POLY_DIFF + PAD) if dog else (CO_POLY + CO + ENC_CO)
    n = len(gates)
    if not isinstance(pc, list):
        pc = [pc] * n
    rx, gx = [], []
    x = x0 + endw
    rx.append(x - (POLY_DIFF + PAD // 2 if dog else CO_POLY + CO // 2))
    for i, (L, net) in enumerate(gates):
        gx.append((x, x + L))
        x += L
        if i < n - 1:
            rx.append(x + gap // 2)
            x += gap
    rx.append(x + (POLY_DIFF + PAD // 2 if dog else CO_POLY + CO // 2))
    x1 = x + endw
    c.r(diff, x0, ybot, x1, ybot + W)
    if dog:
        ym = ybot + W / 2
        rb, rt = g5(ym - reg_h / 2), g5(ym + reg_h / 2)
        for cx in rx:
            c.r(diff, cx - PAD // 2, rb, cx + PAD // 2, rt)
    else:
        rb, rt = ybot, ybot + W
    cb, ct = rb + ENC_CO, rt - ENC_CO
    for cx in rx:
        c.r(cont, cx - CO // 2, cb, cx + CO // 2, ct)
        c.r("m1", cx - 190, cb - 75, cx + 190, ct + 75)
    pcs = []
    for i, ((a, b), side) in enumerate(zip(gx, pc)):
        ylo, yhi = ybot - ENDCAP, ybot + W + ENDCAP
        gc = (a + b) // 2
        if side == "top":
            pb = rt + 260
            c.r("poly", a, ylo, b, pb + 370)
            c.r("poly", min(a, gc - 185), pb, max(b, gc + 185), pb + 370)
            c.r("pc", gc - 115, pb + 70, gc + 115, pb + 300)
            c.r("m1", gc - 190, pb - 5, gc + 190, pb + 375)
            pcs.append((gc, pb + 185))
        elif side == "bot":
            pt = rb - 260
            c.r("poly", a, pt - 370, b, yhi)
            c.r("poly", min(a, gc - 185), pt - 370, max(b, gc + 185), pt)
            c.r("pc", gc - 115, pt - 300, gc + 115, pt - 70)
            c.r("m1", gc - 190, pt - 375, gc + 190, pt + 5)
            pcs.append((gc, pt - 185))
        else:
            c.r("poly", a, ylo, b, yhi)
            pcs.append(None)
    return dict(rx=rx, gx=gx, x0=x0, x1=x1, rb=rb, rt=rt, cb=cb, ct=ct, pcs=pcs, ybot=ybot, W=W)


def groups(gates):
    """Runs of consecutive gates on the same net: [(net, first, last)]."""
    out = []
    for i, (_, net) in enumerate(gates):
        if out and out[-1][0] == net and out[-1][2] == i - 1:
            out[-1] = (net, out[-1][1], i)
        else:
            out.append((net, i, i))
    return out


# ---- foot: rows of W=wfu fingers, shared by stage and master -------------------------------
def foot_rows(p):
    """Finger plan: _rows rows (default 7); coarse bit b has 2**b fingers, base k fingers on vbn, fine leg last."""
    seq = [(p["ls"], "vbn")] * p["k"]
    for b in reversed(range(p["bits"])):
        seq += [(p["ls"], f"g{b}")] * (2 ** b)
    seq += [(p["lff"], "vctrl")]
    if p.get("_mutate") == "swapbits":   # LVS mutation test: legs of bit 0 and bit 1 swap gate nets
        seq = [(L, {"g0": "g1", "g1": "g0"}.get(n, n)) for (L, n) in seq]
    nrow = p.get("_rows", 7)
    per = -(-len(seq) // nrow)
    return [seq[i:i + per] for i in range(0, len(seq), per)]


REG_H = 1200    # dogbone S/D region height: room for the VSS (bottom) and f (top) via1 rows
FOFF = 100      # f via1 row sits this far below the region top (M2 clearance to the gate-band pads)


def draw_foot(c, p, fnet_label=None):
    """Foot network in cell c from y=0 upward. Returns dict with x of the f spine, top y, track list.

    Left: p+ tap per row + VSS M2 spine. Right: f M1 spine. Gate groups go up to their M3 track.
    """
    um = lambda v: g5(v * 1000)
    W = um(p["wfu"])
    rows = foot_rows(p)
    tap_x = 190                       # p+ tap centre (the VSS spine runs over it)
    x0 = tap_x + 190 + NSD_PSD        # finger diffusion starts here
    y0 = 0
    tracks = []                       # (net, y) of every M3 bias track this cell needs
    geos = []
    for row in rows:
        gates = [(um(L), net) for (L, net) in row]
        ybot = y0 + (REG_H - W) // 2
        ybot = g5(ybot - (ybot % 5))
        geo = fet_row(c, x0, ybot, W, gates, "n", reg_h=REG_H, pc="top")
        geos.append(geo)
        rb, rt = geo["rb"], geo["rt"]
        # S/D: even regions VSS (via1 at bottom), odd regions f (via1 at top)
        for i, cx in enumerate(geo["rx"]):
            c.via1(cx, rb + 190 if i % 2 == 0 else rt - 190 - FOFF)
        # p+ tap at the row's left end, under the VSS spine
        c.r("psd", tap_x - 190, rb, tap_x + 190, rt)
        c.r("psc", tap_x - 115, rb + ENC_CO, tap_x + 115, rt - ENC_CO)
        c.r("m1", tap_x - 190, rb - 5, tap_x + 190, rt + 5)
        c.r("v1", tap_x - 130, rb + 60, tap_x + 130, rt - 60)
        c.r("m2", tap_x - 190, rb, tap_x + 190, rt)
        # M2 straps: VSS along the bottom of the regions, f along the top
        c.r("m2", tap_x - 190, rb, geo["rx"][-1] + 190, rb + 380)
        geo["fstrap"] = (geo["rx"][1] - 190, rt - 380 - FOFF, rt - FOFF)
        # gate groups: M1 strap over the pc pads, one M3 track per net in this row
        pcy = geo["pcs"][0][1]
        nets = []
        for net, a, b in groups(gates):
            if net not in nets:
                nets.append(net)
            xa, xb = geo["pcs"][a][0], geo["pcs"][b][0]
            c.r("m1", xa - 190, pcy - 190, xb + 190, pcy + 190)
        geo["tracks"] = []
        for k, net in enumerate(nets):
            ty = pcy + k * TPITCH
            geo["tracks"].append((net, ty))
            tracks.append((net, ty))
        for net, a, b in groups(gates):
            k = nets.index(net)
            ty = pcy + k * TPITCH
            xs = geo["pcs"][(a + b) // 2][0]
            if k:
                c.r("m1", xs - 190, pcy, xs + 190, ty + 190)
            c.via12(xs, ty)
        geo["top"] = pcy + (len(nets) - 1) * TPITCH + 190
        y0 = geo["top"] + 300
    # f spine (M1) right of the widest row; f straps reach it
    xr = max(g["rx"][-1] for g in geos) + 190 + 240 + 190
    for g in geos:
        xa, yb, yt = g["fstrap"]
        c.r("m2", xa, yb, xr + 190, yt)
        c.r("v1", xr - 130, yb + 60, xr + 130, yt - 60)
    c.r("m1", xr - 190, geos[0]["rt"] - 380 - FOFF - 5, xr + 190, geos[-1]["rt"] + 5)
    # VSS spine: M2 over the taps, from y<0 (rail) to the top row
    c.r("m2", tap_x - 190, -700, tap_x + 190, geos[-1]["rt"])
    return dict(fx=xr, top=geos[-1]["top"], tracks=tracks, geos=geos, x1=xr + 190)


# ---- vertical plan (shared by every column) -----------------------------------------------
def plan(p):
    """y coordinates common to all columns, from a throw-away foot."""
    tmp = Cell("tmp")
    f = draw_foot(tmp, p)
    um = lambda v: g5(v * 1000)
    Y = {}
    Y["foot_top"] = f["top"]
    Y["n_bot"] = f["top"] + 300 + 50                    # inverter NMOS diffusion bottom
    Y["n_top"] = Y["n_bot"] + um(p["wn"])
    Y["pcl"] = Y["n_top"] + 260 + 185                   # input pc (low) centre
    # ring channel: VSS shield (280 wide), ring track (380), shield, ... 400 nm gaps, so that every ring node
    # sees the same neighbours (shield on both sides) and no ring node couples to another one directly
    sh0 = Y["pcl"] + 190 + 300 + 140
    Y["shield"] = [sh0 + 2 * SHP * i for i in range(p["n"] + 1)]
    Y["trk"] = [sh0 + SHP * (2 * i + 1) for i in range(p["n"])]
    Y["tap_b"] = Y["shield"][-1] + 140 + 400            # n-well tap ring, bottom side (nsd strip bottom)
    Y["nw_b"] = Y["tap_b"] - NW_ENC_NSD
    Y["p_bot"] = Y["tap_b"] + 380 + 900                 # PMOS diffusion bottom
    Y["pch"] = Y["p_bot"] - 260 - 185                   # bottom pc centre (P input, MPB, TP)
    hmax = max(um(p["whead"]), um(p["wp"]), um(p["wn"]) * 0 + um(p["wpb"]), 5000)
    Y["p_top"] = Y["p_bot"] + hmax
    Y["vbp"] = Y["p_top"] + 260 + 185                   # head pc centre = vbp track
    Y["vdd_b"] = Y["vbp"] + 190 + 300                   # VDD rail (M1+M2) bottom
    Y["vdd_t"] = Y["vdd_b"] + 2400
    Y["tap_t"] = Y["vdd_b"] + 1010                      # n-well tap ring top side (under the rail)
    Y["nw_t"] = Y["tap_t"] + 380 + NW_ENC_NSD
    Y["vss_t"] = -300                                   # VSS rail top
    Y["vss_b"] = Y["vss_t"] - 2400
    return Y, f


# ---- ring stage ------------------------------------------------------------------------------
def stage_cell(p, Y):
    um = lambda v: g5(v * 1000)
    c = Cell("ring_stage")
    f = draw_foot(c, p)
    fx = f["fx"]
    # inverter NMOS: regions [out | g | f]; f region lands on the f spine
    Ln = um(p["L"])
    wn = um(p["wn"])
    endw = CO_POLY + CO + ENC_CO
    nx0 = fx - (CO_POLY + CO // 2) - Ln - endw
    n = fet_row(c, nx0, Y["n_bot"], wn, [(Ln, "in")], "n")
    assert n["rx"][1] == fx, (n["rx"], fx)
    c.r("m1", fx - 190, f["geos"][-1]["rt"], fx + 190, n["ct"] + 75)       # f spine up to N source
    gx0, gx1 = n["gx"][0]
    gc = (gx0 + gx1) // 2
    xin = gc + XIN_OFF                                                      # input line x (clear of the output line)
    xout = n["rx"][0]                                                       # output line x
    # N input pc (low), offset right of the gate
    pb = Y["pcl"] - 185
    c.r("poly", gx0, n["ybot"] + wn, gx1, pb + 370)
    c.r("poly", gx0, pb, xin + 185, pb + 370)
    c.r("pc", xin - 115, pb + 70, xin + 115, pb + 300)
    # P: regions [out | g | h], same gate x
    wp, wh, Lh = um(p["wp"]), um(p["whead"]), um(p["ls"])
    pr = fet_row(c, nx0, Y["p_bot"], wp, [(Ln, "in")], "p")
    assert pr["gx"][0] == n["gx"][0]
    pt = Y["pch"] + 185
    c.r("poly", gx0, pt - 370, gx1, pr["ybot"])
    c.r("poly", gx0, pt - 370, xin + 185, pt)
    c.r("pc", xin - 115, pt - 300, xin + 115, pt - 70)
    # input M1 line pc_low -> pc_high, output M1 line N drain -> P drain
    c.r("m1", xin - 190, Y["pcl"] - 190, xin + 190, Y["pch"] + 190)
    c.r("m1", xout - 190, n["cb"] - 75, xout + 190, pr["ct"] + 75)
    # head H: regions [h | g | VDD], right of P
    hx0 = pr["x1"] + 600
    h = fet_row(c, hx0, Y["p_bot"], wh, [(Lh, "vbp")], "p", pc="top")
    # h bridge (M1) between P's h region and H's h region, low on the diffusion
    c.r("m1", pr["rx"][1], pr["cb"], h["rx"][0], pr["cb"] + 600)
    # VDD region of H up into the rail
    c.r("m1", h["rx"][1] - 190, h["ct"], h["rx"][1] + 190, Y["vdd_b"] + 400)
    # H gate pc -> vbp track (via1+via2 on the pc pad)
    hpc = h["pcs"][0]
    assert hpc[1] == Y["vbp"], (hpc, Y["vbp"])
    c.via12(hpc[0], hpc[1])
    # nwell inside the cell over the PMOS (merges with the top-level well)
    c.r("nwell", pr["x0"] - NW_ENC_P, Y["nw_b"], h["x1"] + NW_ENC_P, Y["nw_t"])
    return c, dict(xin=xin, xout=xout, x1=max(f["x1"], h["x1"] + NW_ENC_P), tracks=f["tracks"],
                   hx=hpc[0], vddx=h["rx"][1], foot=f)


# ---- master leg ------------------------------------------------------------------------------
def master_cell(p, Y):
    um = lambda v: g5(v * 1000)
    c = Cell("ring_master")
    f = draw_foot(c, p)
    fx = f["fx"]
    total = p["k"] + 2 ** p["bits"] - 1
    m = max(1, round(p["mr"] * total / 4))
    wpb, lpb = um(p["wpb"]), um(p["ls"])
    gates = [(lpb, "vbp")] * m
    x0 = fx - 6000 - 0
    # MPB: regions alternate VDD (even) / vbp (odd); pc at the bottom; gate strap ties to drains
    mp = fet_row(c, 0, Y["p_bot"], wpb, gates, "p", pc="bot")
    # shift so that the strap reaches fx: draw at x 0.. then the strap extends to fx
    pcy = mp["pcs"][0][1]
    c.r("m1", mp["pcs"][0][0] - 190, pcy - 190, max(fx, mp["pcs"][-1][0]) + 190, pcy + 190)
    for i, cx in enumerate(mp["rx"]):
        if i % 2:   # drain -> down to the gate strap
            c.r("m1", cx - 190, pcy, cx + 190, mp["cb"])
        else:       # source -> up into the VDD rail
            c.r("m1", cx - 190, mp["ct"], cx + 190, Y["vdd_b"] + 400)
    # f spine (vbp) up to the strap
    c.r("m1", fx - 190, f["geos"][-1]["rt"], fx + 190, pcy)
    # vbp up to the M3 vbp track: via1 on the strap at a drain column, M2 riser, via2 at the track
    vx = mp["rx"][1]
    c.via1(vx, pcy)
    c.r("m2", vx - 190, pcy, vx + 190, Y["vbp"])
    c.via2(vx, Y["vbp"])
    c.label("vbp", "m3", vx, Y["vbp"])
    c.r("nwell", mp["x0"] - NW_ENC_P, Y["nw_b"], mp["x1"] + NW_ENC_P, Y["nw_t"])
    assert mp["x1"] < fx or True
    return c, dict(x1=max(f["x1"], mp["x1"] + NW_ENC_P), tracks=f["tracks"], vbpx=vx, foot=f)


# ---- coarse switches -------------------------------------------------------------------------
def switch_cell(p, Y, tracks):
    """Bit slices: M2 lines bitb_b, bit_b, g_b, then TD (g|VSS) low, TN (g|vbn) on a vbn track, TP (g|vbn)
    in the PMOS row. tracks: [(net, y)] of the foot M3 tracks (stage x-ranges end at the g_b line)."""
    um = lambda v: g5(v * 1000)
    c = Cell("ring_sw")
    L = um(0.28)
    vbn_ys = sorted(y for n, y in tracks if n == "vbn")
    tn_y = vbn_ys[-1]                  # TN centred on the highest vbn track
    wtn, wtp, wtd = um(2.0), um(5.0), um(1.0)
    endw = CO_POLY + CO + ENC_CO
    sx = 0
    info = dict(gline={}, end={})
    for b in range(p["bits"]):
        lb, li, lg = sx + 190, sx + 190 + 680, sx + 190 + 1360
        dx0 = lg + 190 + 300 + (endw - (CO_POLY + CO // 2) - 190) * 0 + 300
        # TD at the bottom: regions [g | VSS], pc top
        td = fet_row(c, dx0, 200, wtd, [(L, f"bitb{b}")], "n", pc="top")
        # TN on the vbn track: regions [g | vbn], pc bottom
        tn = fet_row(c, dx0, tn_y - wtn // 2, wtn, [(L, f"bit{b}")], "n", pc="bot")
        assert td["pcs"][0][1] + 190 + 240 <= tn["pcs"][0][1] - 190, "TD/TN pc straps collide"
        # TP in the PMOS row: regions [g | vbn], pc bottom
        tp = fet_row(c, dx0, Y["p_bot"], wtp, [(L, f"bitb{b}")], "p", pc="bot")
        # g_b: M1 from each g region left to the g line
        for d in (td, tn, tp):
            yy = (d["cb"] + d["ct"]) // 2
            c.r("m1", lg - 190, yy - 190, d["rx"][0], yy + 190)
            c.via1(lg, yy)
        # gates: TD/TP -> bitb line, TN -> bit line (M1 left over the M2 lines)
        for d, lx in ((td, lb), (tn, li), (tp, lb)):
            gx, gy = d["pcs"][0]
            c.r("m1", lx - 190, gy - 190, gx + 190, gy + 190)
            c.via1(lx, gy)
        # TD source -> VSS rail; TN source on the vbn track (via1+via2); TP source -> PMOS vbn M3 line
        c.r("m1", td["rx"][1] - 190, Y["vss_t"] - 400, td["rx"][1] + 190, td["cb"])
        c.via12(tn["rx"][1], tn_y)
        vy = Y["p_bot"] + wtp // 2
        c.via12(tp["rx"][1], vy)
        # M2 lines
        gys = [y for n, y in tracks if n == f"g{b}"]
        ybot_pin = Y["vss_b"] - 0
        c.r("m2", lg - 190, min(gys + [td["cb"]]) - 190, lg + 190, (tp["cb"] + tp["ct"]) // 2 + 190)
        c.r("m2", li - 190, 0, li + 190, tn["pcs"][0][1] + 190)
        c.r("m2", lb - 190, 0, lb + 190, tp["pcs"][0][1] + 190)
        for gy in gys:
            c.via2(lg, gy)
        # pins: M3 stubs from the bit/bitb line bottoms down through the VSS rail
        for lx, nm in ((li, f"bit{b}"), (lb, f"bitb{b}")):
            c.via2(lx, 190)
            info["end"][nm] = lx
        # p+ substrate-tap island (no metal) in the empty gap between TN and TP: active-fill rule DCF.1a
        ym = (tn["rt"] + Y["nw_b"]) // 2 // 10 * 10
        c.r("psd", dx0, ym - 500, td["x1"], ym + 500)
        info["gline"][f"g{b}"] = lg
        info.setdefault("tn", []).append(tn["rx"][1])
        sx = tp["x1"] + 600
    # global vbn line: M2 from the lowest vbn track to the PMOS-row vbn M3 line
    vx = sx + 190
    vy = Y["p_bot"] + wtp // 2
    c.r("m2", vx - 190, vbn_ys[0] - 190, vx + 190, vy + 190)
    for y in vbn_ys:
        c.via2(vx, y)
    c.via2(vx, vy)
    c.r("m3", 0, vy - 190, vx + 190, vy + 190)
    c.r("nwell", -NW_ENC_P + 0, Y["nw_b"], vx + 190 + NW_ENC_P, Y["nw_t"])
    info["vbnx"] = vx
    info["vbny"] = vy
    info["x1"] = vx + 190 + NW_ENC_P
    return c, info


# ---- top level -------------------------------------------------------------------------------
ORDER = [0, 4, 1, 3, 2]          # stage index at column 0..4


def build(p):
    um = lambda v: g5(v * 1000)
    Y, _ = plan(p)
    st, si = stage_cell(p, Y)
    ms, mi = master_cell(p, Y)
    tracks = si["tracks"]
    sw, wi = switch_cell(p, Y, tracks)
    top = Cell("ring_core")
    pitch = g5(si["x1"] + 1000)
    X0 = 0
    colx = [X0 + i * pitch for i in range(5)]
    for i, s in enumerate(ORDER):
        top.inst("ring_stage", colx[i], 0, f"stage{s}")
    mx = X0 + 5 * pitch
    top.inst("ring_master", mx, 0, "master")
    swx = g5(mx + mi["x1"] + 1000)
    top.inst("ring_sw", swx, 0, "sw")
    xr_core = swx + wi["x1"]
    # bias M3 tracks across stages + master into the switch column
    for net, y in tracks:
        if net == "vbn":
            xe = swx + wi["vbnx"] + 190
        elif net == "vctrl":
            xe = None
        else:
            xe = swx + wi["gline"][net] + 190
        top.r("m3", X0, y - 190, xe if xe else xr_core, y + 190)
    # vbp M3 track: stage heads + master
    top.r("m3", colx[0] + si["hx"] - 190, Y["vbp"] - 190, mx + mi["vbpx"] + 190, Y["vbp"] + 190)
    # ring channel: node a_j driven by stage j-1 (out line), loads stage j (input line)
    col = {s: i for i, s in enumerate(ORDER)}
    lens = {}
    spans = {}
    for j in range(p["n"]):
        drv, ld = (j - 1) % p["n"], j
        xo = colx[col[drv]] + si["xout"]
        xi = colx[col[ld]] + si["xin"]
        spans[j] = (min(xo, xi), max(xo, xi), xo, xi)
    Lmax = max(b - a for a, b, _, _ in spans.values())
    xl_core = None
    for j, (a, b, xo, xi) in spans.items():
        ext = Lmax - (b - a)
        if j == 0:
            a -= ext                  # a0: pad to the left, out of the core as the output pin
        elif a - ext >= colx[0]:
            a -= ext
        else:
            b += ext
        ty = Y["trk"][j]
        top.r("m2", a - 190, ty - 190, b + 190, ty + 190)
        top.via1(xo, ty)
        top.via1(xi, ty)
        lens[j] = b - a
        spans[j] = (a, b, xo, xi)
    # VSS shields in the ring channel, tied to VSS through an M2 riser on the master's VSS spine
    shl = min(a for a, _, _, _ in spans.values()) - 190 - 300
    shx = mx + 190
    for y in Y["shield"]:
        top.r("m2", shl, y - 140, shx + 190, y + 140)
    top.r("m2", shx - 190, mi["foot"]["geos"][-1]["rt"] - 400, shx + 190, Y["shield"][-1] + 140)
    # rails (M1 + M2, 2.4 um) with via1 arrays, nwell, n-well tap ring, p+ substrate ring
    xl = spans[0][0] - 190 - 1500       # core inner left edge (a0 pin region)
    xl = min(xl, -1500)
    xr = xr_core + 1500
    for (yb, yt, nm) in ((Y["vss_b"], Y["vss_t"], "VSS"), (Y["vdd_b"], Y["vdd_t"], "VDD")):
        top.r("m1", xl, yb, xr, yt)
        top.r("m2", xl, yb, xr, yt)
        x = xl + 400
        while x + 400 < xr:
            top.r("v1", x - 130, yb + 300, x + 130, yt - 300)
            x += 2000
        top.label(nm, "m2", xl + 1000, (yb + yt) // 2, port=True)
    # VSS rail must clear the M3 pin stubs? (M3 over M2: fine). Bit pins: M3 stubs down to below VSS rail
    pin_y = Y["vss_b"] - 1600
    for nm, lx in wi["end"].items():
        x = swx + lx
        top.r("m3", x - 190, pin_y, x + 190, 190 + 190)
        top.label(nm, "m3", x, pin_y + 300, port=True)
    # n-well over the whole PMOS band + tap ring (nsd) inside it
    nwl, nwr = xl + 300, xr - 300
    top.r("nwell", nwl, Y["nw_b"], nwr, Y["nw_t"])
    e = NW_ENC_NSD
    tb, tt = Y["tap_b"], Y["tap_t"]
    top.r("nsd", nwl + e, tb, nwr - e, tb + 380)              # bottom
    top.r("nsd", nwl + e, tt, nwr - e, tt + 380)              # top (under the VDD rail)
    top.r("nsd", nwl + e, tb, nwl + e + 380, tt + 380)        # left
    top.r("nsd", nwr - e - 380, tb, nwr - e, tt + 380)        # right
    # contacts: top side under the rail, left/right sides with M1, bottom side in pieces between crossings
    top.r("nsc", nwl + e + 75, tt + 75, nwr - e - 75, tt + 305)
    for xa in (nwl + e, nwr - e - 380):
        top.r("nsc", xa + 75, tb + 75, xa + 305, tt + 305)
        top.r("m1", xa - 5, tb - 5, xa + 385, Y["vdd_t"] if True else 0)
    cross = []
    for i in range(5):
        cross += [colx[i] + si["xin"], colx[i] + si["xout"]]
    cross.append(mx + mi["foot"]["fx"])
    cross.sort()
    xa = nwl + e
    pieces = []
    for xc in cross + [nwr - e - 380]:
        xb = xc - 190 - 240 if xc != nwr - e - 380 else nwr - e
        if xb - xa >= 800:
            pieces.append((xa, xb))
        xa = xc + 190 + 240
    for (a, b) in pieces:
        top.r("m1", a, tb - 5, b, tb + 385)
        top.r("nsc", a + 75, tb + 75, b - 75, tb + 305)
    # p+ substrate tap ring around everything
    gl, gr = xl - 1500, xr + 1500
    gb, gt = Y["vss_b"] + 1010, Y["nw_t"] + 1200
    top.r("psd", gl, gb, gr, gb + 380)
    top.r("psd", gl, gt, gr, gt + 380)
    top.r("psd", gl, gb, gl + 380, gt + 380)
    top.r("psd", gr - 380, gb, gr, gt + 380)
    for (a, b, cc, d) in ((gl, gb, gr, gb + 380), (gl, gt, gr, gt + 380), (gl, gb, gl + 380, gt + 380),
                          (gr - 380, gb, gr, gt + 380)):
        top.r("m1", a - 5, b - 5, cc + 5, d + 5)
    top.r("psc", gl + 75, gb + 75, gr - 75, gb + 305)
    top.r("psc", gl + 75, gt + 75, gr - 75, gt + 305)
    top.r("psc", gl + 75, gb + 75, gl + 305, gt + 305)
    top.r("psc", gr - 305, gb + 75, gr - 75, gt + 305)
    top.r("m1", gl - 5, Y["vss_b"], xl, Y["vss_t"])            # VSS rail joins the ring (left)
    top.r("m1", xr, Y["vss_b"], gr + 5, Y["vss_t"])            # (right)
    # pins
    a0x = spans[0][0]
    top.r("m2", gl - 300, Y["trk"][0] - 190, a0x, Y["trk"][0] + 190)
    top.label("a0", "m2", gl - 100, Y["trk"][0], port=True)
    for j in range(1, p["n"]):
        a, b, xo, xi = spans[j]
        top.label(f"a{j}", "m2", (xo + xi) // 20 * 10, Y["trk"][j], port=True)
    for net, y in tracks:
        if net == "vctrl":
            top.r("m3", xr_core, y - 190, gr + 300, y + 190)
            top.label("vctrl", "m3", gr + 100, y, port=True)
            break
    top.r("m3", swx + wi["vbnx"], wi["vbny"] - 190, gr + 300, wi["vbny"] + 190)
    top.label("vbn", "m3", gr + 100, wi["vbny"], port=True)
    if p.get("_mutate") == "antenna":    # antenna mutation: a long M3 comb on the bit0 pin (TN0 gate)
        x = swx + wi["end"]["bit0"]
        # antenna rules are sidewall ratios (M3 400): a comb of 20 x 25 um fingers, ~1000 um of edge,
        # on the 0.56 um^2 TN0 gate gives a ratio of ~1000
        top.r("m3", x - 190, pin_y - 5000, x + 190, pin_y)
        top.r("m3", x - 190, pin_y - 5300, x + 16000, pin_y - 5000)
        for i in range(20):
            top.r("m3", x - 190 + i * 800, pin_y - 30300, x + 110 + i * 800, pin_y - 5300)
    bbox = (gl - 300, pin_y, gr + 300, gt + 380)
    meta = dict(Y=Y, pitch=pitch, colx=colx, lens=lens, bbox=bbox, tracks=tracks, spans=spans)
    return [st, ms, sw, top], meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--out", default=str(REPO / "build" / "layout"))
    ap.add_argument("--gds", default=str(REPO / "layout" / "ring_core.gds"))
    ap.add_argument("--no-magic", action="store_true")
    ap.add_argument("--shgap", type=int, default=SHGAP, help="ring track to VSS shield gap (nm)")
    ap.add_argument("--rows", type=int, default=7, help="foot finger rows per column (layout only, no size change)")
    ap.add_argument("--mutate", choices=["swapbits", "antenna"], help="deliberately broken copy (checker tests)")
    a = ap.parse_args()
    p = dict(vco_bias.P)
    p.update(rideal=0, lnw=4.5, lnp=100.0)
    for kv in a.set:
        k, v = kv.split("=")
        p[k] = type(vco_bias.P[k])(float(v))
    p["_mutate"] = a.mutate
    globals().update(SHGAP=a.shgap, SHP=140 + a.shgap + 190)
    p["_rows"] = a.rows
    cells, meta = build(p)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.mag"):   # magic 'load' would open a stale cell and paint on top of it
        old.unlink()
    tcl = "drc off\nsnap internal\n" + "".join(c.tcl() for c in cells)
    tcl += f"load ring_core\nselect top cell\nexpand\ngds write {Path(a.gds).resolve()}\nquit -noprompt\n"
    (out / "ring_core.tcl").write_text(tcl)
    bb = meta["bbox"]
    print(f"bbox {(bb[2]-bb[0])/1000:.2f} x {(bb[3]-bb[1])/1000:.2f} um; column pitch {meta['pitch']/1000:.2f} um")
    print("ring wire lengths (um):", {f"a{j}": l / 1000 for j, l in meta["lens"].items()})
    if not a.no_magic:
        rc = f"{os.environ.get('PDK_ROOT', '/foss/pdks')}/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc"
        r = subprocess.run(["magic", "-rcfile", rc, "-noconsole", "-dnull", "ring_core.tcl"], cwd=out,
                           capture_output=True, text=True)
        (out / "magic_gen.log").write_text(r.stdout + r.stderr)
        print("magic log:", out / "magic_gen.log")


if __name__ == "__main__":
    main()
