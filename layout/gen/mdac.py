#!/usr/bin/env python3
"""Layout of the medium DAC ("mdac", gf180mcuD, 3.3 V devices): sim/tune/mdac_sim.py mdac_netlist() plus dummies.

    python3 layout/gen/mdac.py [--out build/layout_mdac] [--gds layout/mdac.gds] [--spice build/layout_mdac/mdac_src.spice]

Circuit (sizes from sim/tune/mdac_sim.py M): PMOS unit 1/4 um, gate pb, source VDD. Groups: 31 unary segments s1..s31 of
32 units, binary b4..b0 (16/8/4/2/1), the sigma-delta cell sd (1), off (32, always on to mo), MPB (64, diode on pb).
Each switched group: SW (gate n<g>, c<g> -> mo) and SD (gate mo, c<g> -> md), PMOS 1/0.28. NMOS (coarse unit
1.2/5.335): MD 30 (diode on mo), MO 3 (gate mo, drain vg), MB 1 (gate vbnf, drain pb); MDD 2 x 3.4/1 (diode on md).

Floorplan (x left to right, y bottom to top; origin = lower-left corner of the cell):
  PMOS array: 40 rows of 32 fingers on one diffusion each (fingers 4.56 um apart), in 20 mirrored pairs that share
    a horizontal poly bar (the gate pb) between the two rows; an n+ tap rail (VDD, M1) between pairs. Row order
    (bottom to top) MPB off s30 s28 .. s2 b4 b2 b0 | sd b1 b3 s1 s3 .. s31 MPB: the segments sit symmetric about
    the binary rows, so a linear gradient cancels pairwise. A row with fewer than 32 active fingers fills up with
    dummies (both regions on VDD). Sources go to the tap rail by M1 stubs (lower row down, upper row up); drains
    via1 onto an M2 track along the row centre.
  Switch column (left of the array, same rows): per row a 2-finger PMOS [mo | SW | c | SD | md]. c meets the row's
    M2 drain track; mo and md go to M3 buses (x of the mo and md regions); SW's gate drops into the tap band to a
    poly contact on the row's control line (M2, from the left edge pin n<g>); SD's gate (mo) is contacted in the
    pair's bar band, shared by both rows of the pair. The off row's track goes straight to the mo bus.
  Right of the array: the bars' poly contacts and the MPB drain tracks on a pb M2 bus, the tap rails on a VDD M3 bus.
  Below the array (p-substrate): NMOS rows R1 (MD 16 | MB 1, own gate vbnf) and R2 (MD 14 | MO 3) sharing a poly
    bar (mo), p+ tap rails (VSS) above and below; MDD bottom left under the switch column.
Pins: n<g> (M2, left edge), vg (M2, right edge), vbnf (M3, right edge), VDD (M3 top strap), VSS (M3 bottom strap).
No Metal4/5.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ring_core import Cell, CO, ENC_CO, CO_POLY, ENDCAP, POLY_DIFF, NSD_PSD  # noqa: E402

REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "sim/tune"))
import mdac_sim as md  # noqa: E402

M = md.M
NF = 32                       # fingers per PMOS row
WU, LU = 1000, 4000           # PMOS unit (nm)
GAP = 560                     # S/D region between gates
END = CO_POLY + CO + ENC_CO   # 450: diffusion end beyond the outer gate
FP = LU + GAP                 # finger pitch
ROWLEN = 2 * END + NF * LU + (NF - 1) * GAP
TAPH = 380                    # n+ / p+ tap strip
DT = 600                      # p-diff to the n+ tap (and n-diff to p+ tap)
BAR_R = 1000                  # band between the two rows of a pair (poly bar 400 in the middle)
PAIR = TAPH + DT + WU + BAR_R + WU + DT
WN, LN = 1200, 5335           # NMOS coarse unit
WDD, LDD = 3400, 1000
LSW = 280


def snap(v):
    return int(round(v / 5.0)) * 5


# ---------------------------------------------------------------------------------------------------------
def row_plan():
    """40 rows bottom to top: (name, kind, active_drains, start) with kind seg/bin/off/mpb; start 'S' or 'D'."""
    lo = ["MPB0", "off"] + [f"s{i}" for i in range(30, 0, -2)] + ["b4", "b2", "b0"]
    hi = ["sd", "b1", "b3"] + [f"s{i}" for i in range(1, 32, 2)] + ["MPB1"]
    rows = lo + hi
    assert len(rows) == 40 and len(set(rows)) == 40
    out = []
    for r in rows:
        if r.startswith("MPB"):
            out.append((r, "mpb", 16, "S"))
        elif r == "off":
            out.append((r, "off", 16, "S"))
        elif r.startswith("s"):
            out.append((r, "seg", 16, "S"))
        elif r in ("b0", "sd"):
            out.append((r, "bin", 1, "D"))            # one finger: region 0 is its drain, the rest are dummies
        else:
            out.append((r, "bin", (1 << int(r[1])) // 2, "S"))
    return out


def region_nets(name, kind, nact, start):
    """Net per S/D region (33 regions) of a 32-finger row."""
    nets = []
    for i in range(NF + 1):
        is_d = (i % 2 == 1) if start == "S" else (i % 2 == 0)
        if not is_d:
            nets.append("VDD")
            continue
        k = i // 2 if start == "S" else i // 2      # k-th drain region from the left
        if kind == "mpb":
            nets.append("pb")
        elif k < nact:
            nets.append("mo" if kind == "off" else f"c{name}")
        else:
            nets.append("VDD")                        # dummy fingers
    return nets


def fingers(nets):
    """Per finger: (left region net, right region net)."""
    return [(nets[i], nets[i + 1]) for i in range(len(nets) - 1)]


# ---------------------------------------------------------------------------------------------------------
def diff_row(c, x0, yb, W, L, ngate, typ, gap=GAP, contacts=None):
    """Diffusion x0.. with ngate vertical gates of length L; contacted regions; returns region centres and gate x."""
    diff, cont = ("pdiff", "pdc") if typ == "p" else ("ndiff", "ndc")
    gaps = gap if isinstance(gap, list) else [gap] * (ngate - 1)
    rx, gx = [], []
    x = x0 + END
    rx.append(x - CO_POLY - CO // 2)
    for i in range(ngate):
        gx.append((x, x + L))
        x += L
        if i < ngate - 1:
            rx.append(x + gaps[i] // 2)
            x += gaps[i]
    rx.append(x + CO_POLY + CO // 2)
    x1 = x + END
    c.r(diff, x0, yb, x1, yb + W)
    cb, ct = yb + ENC_CO, yb + W - ENC_CO
    for i, cx in enumerate(rx):
        if contacts is None or contacts[i]:
            c.r(cont, cx - CO // 2, cb, cx + CO // 2, ct)
            c.r("m1", cx - 190, cb - 75, cx + 190, ct + 75)
    return dict(rx=rx, gx=gx, x0=x0, x1=x1, yb=yb, yt=yb + W, cb=cb, ct=ct)


def pc_pad(c, x, y):
    """Poly contact centred at (x, y): poly 370 x 370, contact 230, M1 380 x 380."""
    c.r("poly", x - 185, y - 185, x + 185, y + 185)
    c.r("pc", x - 115, y - 115, x + 115, y + 115)
    c.r("m1", x - 190, y - 190, x + 190, y + 190)


def via1(c, x, y):
    c.via1(x, y)


def via2(c, x, y):
    c.via2(x, y)


# ---------------------------------------------------------------------------------------------------------
def build(c):
    rows = row_plan()
    geo = dict(pins={}, rows=[])
    # ---- x plan ----
    # switch column: diffusion from XS: END | SW (280) | 560 | SD (280) | md region 1200 | END
    XS = 2000                                   # left margin for the control-line pins / MDD
    sw_gaps = [GAP]
    sw = diff_row(Cell("tmp"), XS, 0, WU, LSW, 2, "p", gap=sw_gaps)
    x_mo, x_c, x_md0 = sw["rx"]
    x_md = sw["gx"][1][1] + 600                 # the md region is widened to 1200 (contact at its centre)
    sw_x1 = x_md + 600 + 0
    gsw = (sw["gx"][0][0] + sw["gx"][0][1]) // 2
    gsd = (sw["gx"][1][0] + sw["gx"][1][1]) // 2
    X0 = snap(sw_x1 + 1500)                     # array diffusion left edge
    X1 = X0 + ROWLEN
    x_pbpc = X1 + 700                           # bar poly contacts (right of the array)
    x_pb = X1 + 1700                            # pb M2 bus
    x_vdd = x_pb + 1400                         # VDD M3 bus
    XR = x_vdd + 1200                           # right edge
    # ---- y plan ----
    YN = 0                                      # NMOS block from y = 0 (VSS strap) up
    ytn0 = 1000                                 # p+ tap N0 (bottom)
    yR2 = ytn0 + TAPH + 1200                    # R2 diffusion (band below for nothing; MO/MD)
    ybarN = yR2 + WN                            # bar band R2/R1
    yR1 = ybarN + BAR_R
    ytn1 = yR1 + WN + 1400                      # p+ tap N1 (band above R1 for MB's gate contact)
    ynw = ytn1 + TAPH + 1800                    # n-well bottom edge
    yt0 = ynw + 150 + 0                         # first n+ tap rail
    ytap = [yt0 + k * PAIR for k in range(21)]
    ytop = ytap[20] + TAPH
    YT = ytop + 150 + 2400                      # top edge (VDD strap above the n-well)
    # ---- n-well ----
    c.r("nwell", XS - 450 - 300, ynw, x_vdd + 600, ytop + 150 + 300)
    # ---- n+ tap rails (VDD) ----
    for k, yt in enumerate(ytap):
        c.r("nsd", X0 - 300, yt, x_vdd + 450, yt + TAPH)
        c.r("nsc", X0 - 300 + 75, yt + 75, x_vdd + 450 - 75, yt + TAPH - 75)
        c.r("m1", X0 - 305, yt - 5, x_vdd + 190, yt + TAPH + 5)
        via1(c, x_vdd, yt + 190)
        via2(c, x_vdd, yt + 190)
    c.r("m3", x_vdd - 190, ytap[0], x_vdd + 190, YT)          # VDD bus up to the top strap
    c.r("m3", XS - 750, YT - 2000, XR, YT)                    # VDD top strap
    geo["pins"]["VDD"] = ("m3", (XS - 750 + XR) // 2, YT - 1000)
    # ---- PMOS rows ----
    ctrl_y = {}
    for ri, (name, kind, nact, start) in enumerate(rows):
        k, upper = ri // 2, ri % 2
        yA = ytap[k] + TAPH + DT
        yb = yA if not upper else yA + WU + BAR_R
        nets = region_nets(name, kind, nact, start)
        g = diff_row(c, X0, yb, WU, LU, NF, "p")
        ybar = yA + WU + BAR_R // 2                           # bar centre of this pair
        # gate poly: from the outer endcap to the bar
        for (ga, gb) in g["gx"]:
            if not upper:
                c.r("poly", ga, yb - ENDCAP, gb, ybar + 200)
            else:
                c.r("poly", ga, ybar - 200, gb, yb + WU + ENDCAP)
        ymid = yb + WU // 2
        tap_y = ytap[k] if not upper else ytap[k + 1]
        dr = []
        for i, (cx, n) in enumerate(zip(g["rx"], nets)):
            if n == "VDD":                                    # M1 stub to the tap rail
                if not upper:
                    c.r("m1", cx - 190, tap_y + TAPH, cx + 190, g["cb"])
                else:
                    c.r("m1", cx - 190, g["ct"], cx + 190, tap_y)
            else:
                via1(c, cx, ymid)
                dr.append(cx)
        # drain track (M2, row centre)
        if kind == "mpb":
            c.r("m2", min(dr) - 190, ymid - 190, x_pb + 190, ymid + 190)
        elif kind == "off":
            c.r("m2", x_mo - 190, ymid - 190, max(dr) + 190, ymid + 190)
            via2(c, x_mo, ymid)
        else:
            c.r("m2", x_c - 190, ymid - 190, max(dr) + 190, ymid + 190)
        # switch pair (not for mpb / off)
        if kind in ("seg", "bin"):
            s = diff_row(c, XS, yb, WU, LSW, 2, "p", gap=sw_gaps, contacts=[1, 1, 0])
            # widen the md region to 1200 and contact it at x_md
            c.r("pdiff", s["x1"], yb, x_md + 600, yb + WU)
            c.r("pdc", x_md - CO // 2, s["cb"], x_md + CO // 2, s["ct"])
            # c: the drain track lands on it (via1 at row centre)
            via1(c, x_c, ymid)
            # mo region -> mo M3 bus
            via1(c, x_mo, ymid)
            via2(c, x_mo, ymid)
            # md region: M1 up/down into the bar band, via1 + via2 to the md M3 bus at the bar centre
            if not upper:
                c.r("m1", x_md - 190, s["cb"] - 75, x_md + 190, ybar + 190)
            else:
                c.r("m1", x_md - 190, ybar - 190, x_md + 190, s["ct"] + 75)
            # SW gate (n<g>) into the tap band, to its control line
            ga, gb = s["gx"][0]
            yc = (tap_y + 190 + 340) if not upper else (tap_y + 190 - 340)
            if not upper:
                c.r("poly", ga, yc - 185, gb, yb + WU + ENDCAP)
            else:
                c.r("poly", ga, yb - ENDCAP, gb, yc + 185)
            pc_pad(c, gsw, yc)
            via1(c, gsw, yc)
            c.r("m2", 0, yc - 190, gsw + 190, yc + 190)
            ctrl_y[name] = yc
            geo["pins"][f"n{name}"] = ("m2", 190, yc)
            # SD gate (mo) into the bar band
            ga, gb = s["gx"][1]
            if not upper:
                c.r("poly", ga, yb - ENDCAP, gb, ybar + 185)
            else:
                c.r("poly", ga, ybar - 185, gb, yb + WU + ENDCAP)
        geo["rows"].append(dict(name=name, kind=kind, yb=yb, nets=nets))
    # per pair: SD gate contact (mo) + md via stack in the bar band; the poly bar (pb) and its contact
    for k in range(20):
        yA = ytap[k] + TAPH + DT
        ybar = yA + WU + BAR_R // 2
        kinds = [rows[2 * k][1], rows[2 * k + 1][1]]
        c.r("poly", X0 + END, ybar - 200, x_pbpc + 185, ybar + 200)
        pc_pad(c, x_pbpc, ybar)
        c.r("m1", x_pbpc - 190, ybar - 190, x_pb + 190, ybar + 190)
        via1(c, x_pb, ybar)
        if any(kd in ("seg", "bin") for kd in kinds):
            pc_pad(c, gsd, ybar)
            via1(c, gsd, ybar)
            c.r("m2", x_mo - 190, ybar - 190, gsd + 190, ybar + 190)
            via2(c, x_mo, ybar)
            via1(c, x_md, ybar)
            via2(c, x_md, ybar)
    # buses
    ybus_top = ytap[20] - DT                          # just below the top tap
    ymbt = (ytn0 + TAPH + 1200) + WN + BAR_R + WN // 2      # R1 centre (MB's drain track)
    c.r("m2", x_pb - 190, ymbt - 190, x_pb + 190, ybus_top)    # pb bus (down to MB's track in R1)
    # ---- NMOS block ----
    c.r("psd", 300, ytn0, XR - 600, ytn0 + TAPH)
    c.r("psc", 300 + 75, ytn0 + 75, XR - 600 - 75, ytn0 + TAPH - 75)
    c.r("m1", 295, ytn0 - 5, XR - 595, ytn0 + TAPH + 5)
    c.r("psd", X0 - 300, ytn1, XR - 600, ytn1 + TAPH)
    c.r("psc", X0 - 300 + 75, ytn1 + 75, XR - 600 - 75, ytn1 + TAPH - 75)
    c.r("m1", X0 - 305, ytn1 - 5, XR - 595, ytn1 + TAPH + 5)
    # VSS strap (M3) along the bottom, via2/via1 onto the bottom tap rail
    c.r("m3", 0, YN, XR, YN + 2000)
    for x in range(1000, XR - 1000, 4000):
        via1(c, x, ytn0 + 190)
        via2(c, x, ytn0 + 190)
    # tap N1 to tap N0 (M1 columns at the block's left and right ends)
    c.r("m1", X0 - 305, ytn0, X0 + 75, ytn1 + TAPH)
    geo["pins"]["VSS"] = ("m3", (XS + XR) // 2, YN + 1000)
    # R2 (bottom row): MD 14 | MO 3, S-start; R1 (top row): MD 16 | MB 1 (separate diffusion, gate vbnf)
    r2_nets = ["VSS" if i % 2 == 0 else ("mo" if i < 15 else "vg") for i in range(18)]   # 17 fingers
    r1_nets = ["VSS" if i % 2 == 0 else "mo" for i in range(17)]                           # 16 fingers
    n2 = diff_row(c, X0, yR2, WN, LN, 17, "n")
    n1 = diff_row(c, X0, yR1, WN, LN, 16, "n")
    mb = diff_row(c, n2["x1"] + 1500, yR1, WN, LN, 1, "n")
    ybarn = ybarN + BAR_R // 2
    for (ga, gb) in n2["gx"]:
        c.r("poly", ga, yR2 - ENDCAP, gb, ybarn + 200)
    for (ga, gb) in n1["gx"]:
        c.r("poly", ga, ybarn - 200, gb, yR1 + WN + ENDCAP)
    c.r("poly", n2["gx"][0][0], ybarn - 200, n2["gx"][-1][1], ybarn + 200)
    pc_pad(c, X0 - 1100, ybarn)
    c.r("poly", X0 - 1100, ybarn - 200, n2["gx"][0][0], ybarn + 200)
    via1(c, X0 - 1100, ybarn)
    for g, nets, upper, tap_y in ((n2, r2_nets, False, ytn0), (n1, r1_nets, True, ytn1)):
        ymid = g["yb"] + WN // 2
        dr = {}
        for cx, n in zip(g["rx"], nets):
            if n == "VSS":
                if not upper:
                    c.r("m1", cx - 190, tap_y + TAPH, cx + 190, g["cb"])
                else:
                    c.r("m1", cx - 190, g["ct"], cx + 190, tap_y)
            else:
                via1(c, cx, ymid)
                dr.setdefault(n, []).append(cx)
        c.r("m2", x_mo - 190, ymid - 190, max(dr["mo"]) + 190, ymid + 190)    # mo track to the mo bus
        via2(c, x_mo, ymid)
        if "vg" in dr:
            c.r("m2", min(dr["vg"]) - 190, ymid - 190, XR, ymid + 190)
            geo["pins"]["vg"] = ("m2", XR - 190, ymid)
    # mo: the bar contact's M2 onto the R1 mo track (M2 from the bar contact up to R1's centre)
    c.r("m2", X0 - 1290, ybarn - 190, X0 - 910, yR1 + WN // 2 + 190)
    c.r("m2", X0 - 1290, yR1 + WN // 2 - 190, X0 + 200, yR1 + WN // 2 + 190)
    # MB: S (left) VSS, D (right) pb; gate up into the band above R1, contact, M1 -> via1/2 -> M3 vbnf to the right edge
    ymb = yR1 + WN // 2
    c.r("m1", mb["rx"][0] - 190, mb["ct"], mb["rx"][0] + 190, ytn1)
    via1(c, mb["rx"][1], ymb)
    c.r("m2", mb["rx"][1] - 190, ymb - 190, x_pb + 190, ymb + 190)
    ga, gb = mb["gx"][0]
    yvb = yR1 + WN + 700
    c.r("poly", ga, yR1 - ENDCAP, gb, yvb + 185)
    gm = snap((ga + gb) / 2)
    pc_pad(c, gm, yvb)
    via1(c, gm, yvb)
    via2(c, gm, yvb)
    c.r("m3", gm - 190, yvb - 190, XR, yvb + 190)
    geo["pins"]["vbnf"] = ("m3", XR - 190, yvb)
    # MDD (2 fingers 3.4/1) bottom left: S | D(md) | S, gates md, under the switch column
    xdd = XS - 1400
    yd = ytn0 + TAPH + DT
    dd = diff_row(c, xdd, yd, WDD, LDD, 2, "n")
    for cx in (dd["rx"][0], dd["rx"][2]):
        c.r("m1", cx - 190, ytn0 + TAPH, cx + 190, dd["cb"])
    ygd = yd + WDD + 700
    for (ga, gb) in dd["gx"]:
        c.r("poly", ga, yd - ENDCAP, gb, ygd + 185)
    c.r("poly", dd["gx"][0][0], ygd - 185, dd["gx"][1][1], ygd + 185)
    xg = dd["rx"][1]
    c.r("pc", xg - 115, ygd - 115, xg + 115, ygd + 115)
    c.r("m1", xg - 190, dd["ct"], xg + 190, ygd + 190)          # D (md) joined to the gate contact
    via1(c, xg, ygd)
    # md: M2 from MDD over to the md column (x_md), via2, M3 bus up to the top pair
    c.r("m2", xg - 190, ygd - 190, x_md + 190, ygd + 190)
    via2(c, x_md, ygd)
    c.r("m3", x_md - 190, ygd - 190, x_md + 190, ybus_top)
    # mo bus: M3 at x_mo from R2's mo track up to the top pair
    c.r("m3", x_mo - 190, yR2 + WN // 2 - 190, x_mo + 190, ybus_top)
    # labels
    for n, (ly, x, y) in geo["pins"].items():
        c.label(n, ly, x, y, port=True)
    geo.update(XR=XR, YT=YT, X0=X0, X1=X1, ctrl_y=ctrl_y, x_mo=x_mo, x_md=x_md, x_pb=x_pb)
    return geo


# ---------------------------------------------------------------------------------------------------------
def lvs_source(path):
    """SPICE subckt mdac matching the layout (dummies included): from the row plan, so every finger is a device."""
    rows = row_plan()
    pins = ["VDD", "VSS", "vg", "vbnf"] + [f"n{r[0]}" for r in rows if r[1] in ("seg", "bin")]
    L = [f".subckt mdac {' '.join(pins)}"]
    k = 0
    fet = lambda d, g, s, b, typ, w, l: f"X{k} {d} {g} {s} {b} {typ} w={w / 1000:.3f}u l={l / 1000:.3f}u"
    for name, kind, nact, start in rows:
        for (a, b) in fingers(region_nets(name, kind, nact, start)):
            d = b if a == "VDD" else a
            L.append(fet(d, "pb", "VDD", "VDD", "pfet_03v3", WU, LU)); k += 1
        if kind in ("seg", "bin"):
            L.append(fet("mo", f"n{name}", f"c{name}", "VDD", "pfet_03v3", WU, LSW)); k += 1
            L.append(fet("md", "mo", f"c{name}", "VDD", "pfet_03v3", WU, LSW)); k += 1
    for i in range(30):
        L.append(fet("mo", "mo", "VSS", "VSS", "nfet_03v3", WN, LN)); k += 1
    for i in range(3):
        L.append(fet("vg", "mo", "VSS", "VSS", "nfet_03v3", WN, LN)); k += 1
    L.append(fet("pb", "vbnf", "VSS", "VSS", "nfet_03v3", WN, LN)); k += 1
    for i in range(2):
        L.append(fet("md", "md", "VSS", "VSS", "nfet_03v3", WDD, LDD)); k += 1
    L.append(".ends mdac")
    Path(path).write_text("\n".join(L) + "\n")
    return pins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/layout_mdac")
    ap.add_argument("--gds", default="layout/mdac.gds")
    a = ap.parse_args()
    out = REPO / a.out
    out.mkdir(parents=True, exist_ok=True)
    c = Cell("mdac")
    geo = build(c)
    tcl = out / "mdac.tcl"
    gds = REPO / a.gds
    tcl.write_text("drc off\nsnap internal\n" + c.tcl() + f"gds write {gds}\nquit -noprompt\n")
    pins = lvs_source(out / "mdac_src.spice")
    rc = "/foss/pdks/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc"
    r = subprocess.run([str(REPO / "tools/osic-mac"), "bash", "-c",
                        f"cd {out} && magic -dnull -noconsole -rcfile {rc} mdac.tcl > magic.log 2>&1"], check=False)
    pj = json.dumps(dict(XR=geo["XR"], YT=geo["YT"], pins=geo["pins"], ctrl_y=geo["ctrl_y"]), indent=1)
    (out / "geo.json").write_text(pj)
    (REPO / "layout/mdac_pins.json").write_text(pj)      # read by layout/gen/tt_wrapper.py
    print(f"mdac {geo['XR'] / 1000:.2f} x {geo['YT'] / 1000:.2f} um, {len(pins)} pins -> {gds}")


if __name__ == "__main__":
    main()
