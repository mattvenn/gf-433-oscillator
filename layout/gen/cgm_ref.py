#!/usr/bin/env python3
"""Layout of the constant-gm bias reference + vbn RC filter ("cgm_ref", gf180mcuD, 3.3 V devices).

    python3 layout/gen/cgm_ref.py [--out build/layout_cgm_ref] [--gds layout/cgm_ref.gds] [--set K=V ...]

Circuit: xschem/cgm_ref.sch (= sim/vco/vco_bias.py netlist(), the reference elements):
  MN1  14 series stages x 14 parallel 2/1 um nfet units, diode (gate = top drain = vbn), bottom to VSS
  MN2  14 series stages x 56 parallel units, gate vbn, top net1, bottom net3
  MP1 / MP2  pfet 56/14 (drawn as 4 fingers 14/14 each), gates net1; MP2 diode (net1), MP1 drain vbn
  XRBW n-well resistor 2 x 5.025 um (net3 -> net4), XRBN n+ resistor 2 x 100 um (net4 -> VSS)
  MS1 pfet 0.5/10 (gate VSS, net2), MS2 nfet 2/0.28 (net2, gate vbn), MS3 nfet 1/0.28 (net1 <- gate net2 -> vbn)
  XRF  ppolyf_u_1k 1 x 970.23 um vbn -> vbnf (serpentine, 9 horizontal strips), XCF nfet 10 x 49.14/10 gate cap on vbnf

Floorplan (x left to right, y bottom to top; same y origin as layout/ring_core_v3.gds, the cell abuts its right edge):
  VSS rail (M1+M2, p+ tap) along the whole bottom, y -2.4..0 (= the core's VSS rail).
  column A (left, filter): CF (10 vertical fingers, S/D columns into the VSS rail, gate strap = vbnf on top), RF
           serpentine above it. vbnf pin: M2 at the left edge, y = 42.665 um (the core's vbn/DAC-gate pin).
  column B (array): resistor row (RBW | RBN) on the VSS rail; above it the MN array: 14 rows = 14 series stages
           (row 0 at the top), every row holds stage k of MN1 *and* MN2 in five groups B14 A7 B28 A7 B14
           (A = MN1, B = MN2 fingers; mirror-symmetric, so both centroids sit on the array centre line); continuous
           vertical gate poly through all rows (every gate is vbn), a poly dummy at each array edge. Between rows k-1
           and k an M1 bar per group joins the S/D regions of node k of both rows (series-parallel without wires);
           the A (MN1) and B (MN2) bars of one gap are joined by two M2 tracks (A above the bar, B below).
           Above: the MN gate strap (vbn), the MP gate strap (net1), the MP row (8 fingers P1 P1 P2 P2 P2 P2 P1 P1,
           common centroid), the VDD rail (n+ well tap) on top.
  column C (right): start-up MS3 / MS2 under the straps, MS1 (vertical, L along y) in the MP n-well, a VSS M1
           strap with a p+ tap down to the rail; pins vbn (M2) and vctrl (M2) on the right edge.
  vctrl: an M2 feed-through at y = 12.935 um from the left edge to the right edge (the core's vctrl pin), routed
         between the array's M2 tracks (no device on it).
No Metal4/5 (M3 only for the net2 start-up link).
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ring_core import Cell, CO, ENC_CO, CO_POLY, ENDCAP, fet_row  # noqa: E402

REPO = HERE.parents[1]
VBNF_Y = 42665       # core vbn (DAC gate) pin, right edge of ring_core_v3
VCTRL_Y = 12935      # core vctrl pin

S = dict(nst=14, mn1=14, mn2=56, wu=2.0, lu=1.0,              # MN arrays: stages, units per stage, unit W/L
         wp=14.0, lp=14.0, npf=4,                              # MP: finger W/L, fingers per device
         rw=2.0, lnw=5.023, lnp=100.0,                         # RBW / RBN
         rfw=1.0, rfl=970.229, rfn=9,                          # RF: width, length, strips
         cfw=49.14, cfl=10.0, cfn=10)                          # CF fingers
GROUPS = [("B", 14), ("A", 7), ("B", 28), ("A", 7), ("B", 14)]   # one MN row (A = MN1, B = MN2)
GAPROW = 900         # diffusion gap between MN rows (M1 bar 380 + 2 x 230 + pad overhang)
TOFF = 700           # M2 track offset from its bar (A above, B below)
DGAP = 600
TGAP = 1200         # MN group break holding a p+ tap strip (DF.14_LV: every n-diffusion within 20 um of a tap)
RPITCH = 1700        # RF strip pitch (1.0 strip + 0.7 space, as lsdiv R1)


def snap(v):
    return int(round(v / 5.0)) * 5


def um(v):
    return snap(v * 1000)


def ex(c, layer, x0, y0, x1, y1):
    c.r(layer, x0, y0, x1, y1)


# ---- MN array ---------------------------------------------------------------------------------------------
def mn_group_x(x0, n, L):
    """Region centres and gate x ranges of one group of n fingers starting at diffusion edge x0."""
    endw = CO_POLY + CO + ENC_CO           # 450
    rx, gx = [x0 + endw - (CO_POLY + CO // 2)], []
    x = x0 + endw
    for i in range(n):
        gx.append((x, x + L))
        x += L
        if i < n - 1:
            rx.append(x + 280)
            x += 560
    rx.append(x + CO_POLY + CO // 2)
    return rx, gx, x + endw


def build(sets=()):
    for kv in sets:
        k, v = kv.split("=")
        S[k] = type(S[k])(float(v))
    c = Cell("cgm_ref")
    nst = int(S["nst"])
    assert sum(n for g, n in GROUPS if g == "A") == S["mn1"] and sum(n for g, n in GROUPS if g == "B") == S["mn2"]
    W, L = um(S["wu"]), um(S["lu"])
    pitch = W + GAPROW
    Y = dict(vss_b=-2400, vss_t=0)

    # ---------------- column A: CF + RF ----------------
    cfx0 = 1000
    cf_b = 600
    cfW, cfL, cfn = um(S["cfw"]), um(S["cfl"]), int(S["cfn"])
    cf = fet_row(c, cfx0, cf_b, cfW, [(cfL, "vbnf")] * cfn, "n")
    cf_t = cf_b + cfW
    Y["cfs_b"] = cf_t + 255                  # vbnf gate strap (M1), poly contacts along its bottom
    Y["cfs_t"] = Y["cfs_b"] + 800
    pcy = Y["cfs_b"] + 190
    for (ga, gb) in cf["gx"]:
        c.r("poly", ga, cf_t, gb, pcy + 185)
        gcx = (ga + gb) // 2
        for o in range(-3600, 3601, 1200):
            c.r("pc", gcx + o - 115, pcy - 115, gcx + o + 115, pcy + 115)
    for cx in cf["rx"]:                      # S/D columns down into the VSS rail
        c.r("m1", cx - 190, Y["vss_t"] - 300, cx + 190, cf["cb"])
    cf_x1 = cf["x1"]
    c.r("m1", 600, Y["cfs_b"], cf_x1, Y["cfs_t"])

    # RF serpentine: 9 horizontal strips, strip 0 (bottom) starts at the vbnf terminal (left), strip 8 (top) ends
    # at the vbn terminal (right). magic's length = sum of strip rects + (n-1) x pitch (bars), as lsdiv R1.
    nrs = int(S["rfn"])
    assert nrs % 2 == 1
    rtot = um(S["rfl"])
    D = 2440                                 # terminal strips run D past the inner strips (SB.2: ends face nothing)
    Ls = (rtot - (nrs - 1) * RPITCH - 2 * D) // nrs // 10 * 10
    D0 = (rtot - (nrs - 1) * RPITCH - nrs * Ls) // 2 // 5 * 5
    D8 = rtot - (nrs - 1) * RPITCH - nrs * Ls - D0
    assert min(D0, D8) >= 2400, (D0, D8)
    xa = 600 + 610 + D0
    xb = xa + Ls
    ry0 = Y["cfs_t"] + 1000
    for i in range(nrs):
        ys = ry0 + i * RPITCH
        x0 = xa - D0 if i == 0 else xa
        x1 = xb + D8 if i == nrs - 1 else xb
        c.r("hires", x0, ys, x1, ys + 1000)
        if i < nrs - 1:
            if i % 2 == 0:
                c.r("hires", xb, ys, xb + 1000, ys + RPITCH + 1000)
            else:
                c.r("hires", xa - 1000, ys, xa, ys + RPITCH + 1000)
    # terminals
    ys0, ys8 = ry0, ry0 + (nrs - 1) * RPITCH
    xe0, xe8 = xa - D0, xb + D8
    c.r("poly", xe0 - 610, ys0, xe0, ys0 + 1000)
    c.r("pc", xe0 - 545, ys0 + 65, xe0 - 315, ys0 + 935)
    c.r("m1", xe0 - 610, ys0, xe0 - 250, ys0 + 1000)
    c.r("m1", xe0 - 610, Y["cfs_t"] - 300, xe0 - 250, ys0 + 500)        # vbnf terminal down to the CF strap
    c.r("poly", xe8, ys8, xe8 + 610, ys8 + 1000)
    c.r("pc", xe8 + 315, ys8 + 65, xe8 + 545, ys8 + 935)
    c.r("m1", xe8 + 250, ys8, xe8 + 610, ys8 + 1000)
    rf_vbn = (xe8 + 430, ys8 + 500)
    colA_x1 = max(cf_x1, xe8 + 610)
    Y["rf_top"] = ys8 + 1000
    # vbnf pin: M2 at the left edge (y = VBNF_Y), up the left side (over the CF's first VSS S/D column) to the strap
    c.r("m2", 0, VBNF_Y - 190, 1380, VBNF_Y + 190)
    c.r("m2", 1000, VBNF_Y - 190, 1380, Y["cfs_b"] + 400)
    c.via1(1190, Y["cfs_b"] + 400)
    c.label("vbnf", "m2", 100, VBNF_Y, port=True)

    # ---------------- column B: MN array ----------------
    xt = colA_x1 + 1300                      # left VSS strap + p+ tap (also a shield between filter and array)
    gx0 = xt + 190 + 1200                    # left dummy poly
    # groups along x
    x = gx0 + 1000 + 110
    grp = []
    for g, n in GROUPS:
        rx, gxs, x1 = mn_group_x(x, n, L)
        grp.append(dict(dev=g, n=n, x0=x, x1=x1, rx=rx, gx=gxs))
        x = x1 + TGAP
    arr_x1 = grp[-1]["x1"]
    dum = [(gx0, gx0 + 1000), (arr_x1 + 110, arr_x1 + 1110)]
    mn_x1 = arr_x1 + 1110
    # y: bar g at ybar(g), g = 0 (top) .. nst (bottom); row k between bar k and bar k+1. The vctrl track must sit
    # in a row middle (clear of every bar, via and track): row centre = bar(k+1) + GAPROW/2 + W/2.
    jrow = 2                                 # vctrl in the middle of row nst-1-jrow (third row from the bottom)
    ybar_bot = VCTRL_Y - (GAPROW // 2 + W // 2) - jrow * pitch
    ybar = [ybar_bot + (nst - g) * pitch for g in range(nst + 1)]
    rows = [(ybar[k + 1] + GAPROW // 2, ybar[k + 1] + GAPROW // 2 + W) for k in range(nst)]   # (ybot, ytop)
    for k, (yb, yt) in enumerate(rows):
        for gr in grp:
            c.r("ndiff", gr["x0"], yb, gr["x1"], yb + W)
            for cx in gr["rx"]:
                c.r("ndc", cx - CO // 2, yb + ENC_CO, cx + CO // 2, yt - ENC_CO)
                c.r("m1", cx - 190, yb - 5, cx + 190, yt + 5)
    Y["mn_bot"], Y["mn_top"] = rows[-1][0], rows[0][1]
    # gate strap (vbn) above bar 0; poly gates + dummies from below the bottom row to the strap
    Y["gs_b"] = ybar[0] + 190 + 230
    Y["gs_t"] = Y["gs_b"] + 380
    pb = rows[-1][0] - ENDCAP
    allg = [g for gr in grp for g in gr["gx"]] + dum
    for (a, b) in allg:
        c.r("poly", a, pb, b, Y["gs_t"] - 5)
    c.r("poly", gx0, Y["gs_b"] + 5, mn_x1, Y["gs_t"] - 5)
    for (a, b) in allg:
        gc = (a + b) // 2
        c.r("pc", gc - 115, Y["gs_b"] + 75, gc + 115, Y["gs_b"] + 305)
    # node connections in each gap: regions with (r + g) % 2 == 0 of the rows above / below; M1 bar per group
    segs = {}                                # (g, dev) -> list of (group index, [cx of connected regions])
    for g in range(nst + 1):
        yb_ = ybar[g]
        for gi, gr in enumerate(grp):
            cxs = [cx for r, cx in enumerate(gr["rx"]) if (r + g) % 2 == 0]
            ylo = rows[g][1] - 100 if g < nst else yb_ - 190          # top of row g (below)
            yhi = rows[g - 1][0] + 100 if g > 0 else yb_ + 190        # bottom of row g-1 (above)
            for cx in cxs:
                c.r("m1", cx - 190, ylo, cx + 190, yhi)
            c.r("m1", cxs[0] - 190, yb_ - 190, cxs[-1] + 190, yb_ + 190)
            segs.setdefault((g, gr["dev"]), []).append((gi, cxs))

    def mid(cxs):
        return cxs[len(cxs) // 2]
    # joins: gaps 1..nst-1 two M2 tracks; gap 0: A (vbn) M1 bridges to the gate strap, B (net1) M2 up to the MP gate
    # strap; gap nst: A (VSS) M1 straps down to the VSS rail, B (net3) M2 track to RBW
    tracks = {}
    for g in range(nst + 1):
        for dev, off in (("A", TOFF), ("B", -TOFF)):
            if (g == 0 and dev == "A") or (g == nst and dev == "A"):
                continue
            if g == 0:
                continue                      # B at the top: done with the MP below
            xs = [mid(cxs) for _, cxs in segs[(g, dev)]]
            ty = ybar[g] + off
            for xv in xs:
                c.via1(xv, ybar[g])
                c.r("m2", xv - 190, min(ty, ybar[g]) - 190, xv + 190, max(ty, ybar[g]) + 190)
            c.r("m2", min(xs) - 190, ty - 190, max(xs) + 190, ty + 190)
            tracks[(g, dev)] = (ty, min(xs), max(xs))
    for _, cxs in segs[(0, "A")]:            # MN1 top drain = vbn = gate strap
        c.r("m1", cxs[0] - 190, ybar[0], cxs[-1] + 190, Y["gs_b"] + 100)
    c.r("m1", xt - 190, Y["gs_b"], mn_x1, Y["gs_t"])

    # ---------------- resistor row (under the array) ----------------
    rcy = 2500                               # resistor centre line
    rw = um(S["rw"])
    ry_b, ry_t = rcy - rw // 2, rcy + rw // 2
    # RBW: n-well terminal 0.8 | rnw lnw | n-well terminal 0.8 (as the PDK's gf180mcu::nwell_draw)
    lnw = um(S["lnw"])
    bx0 = xt + 190 + 2000
    c.r("nwell", bx0, ry_b, bx0 + 800, ry_t)
    c.r("rnw", bx0 + 800, ry_b, bx0 + 800 + lnw, ry_t)
    c.r("nwell", bx0 + 800 + lnw, ry_b, bx0 + 1600 + lnw, ry_t)
    bterm = []
    for xc_ in (bx0 + 420, bx0 + 1180 + lnw):        # n+ tap 0.2..0.56 um from the rnw end, as the PDK cell
        c.r("nsd", xc_ - 180, ry_b + 240, xc_ + 180, ry_t - 240)
        c.r("nsc", xc_ - 115, ry_b + 310, xc_ + 115, ry_t - 310)
        c.r("m1", xc_ - 190, ry_b + 235, xc_ + 190, ry_t - 235)
        bterm.append(xc_)
    rbw_x1 = bx0 + 1600 + lnw
    # RBN: n+ terminal 0.63 | rnd lnp | n+ terminal 0.63
    lnp = um(S["lnp"])
    nx0 = rbw_x1 + 2500
    c.r("ndiff", nx0, ry_b, nx0 + 630, ry_t)
    c.r("rnd", nx0 + 630, ry_b, nx0 + 630 + lnp, ry_t)
    c.r("ndiff", nx0 + 630 + lnp, ry_b, nx0 + 1260 + lnp, ry_t)
    nterm = []
    for xc_ in (nx0 + 180, nx0 + 1080 + lnp):     # contact 0.45 um from the rnd end (PDK cell)
        c.r("ndc", xc_ - 115, ry_b + 65, xc_ + 115, ry_t - 65)
        c.r("m1", xc_ - 190, ry_b, xc_ + 190, ry_t)
        nterm.append(xc_)
    rbn_x1 = nx0 + 1260 + lnp
    assert rbn_x1 + 600 <= mn_x1 + 2500, (rbn_x1, mn_x1)
    c.r("m1", bterm[1] - 190, rcy - 190, nterm[0] + 190, rcy + 190)          # net4
    c.r("m1", nterm[1] - 190, Y["vss_t"] - 300, nterm[1] + 190, ry_b + 100)  # RBN -> VSS
    # MN1 bottom (VSS): M1 straps from the A bars down over the RBN body into the rail
    for _, cxs in segs[(nst, "A")]:
        x_ = mid(cxs)
        c.r("m1", x_ - 300, Y["vss_t"] - 300, x_ + 300, ybar[nst])
        assert nx0 + 1500 < x_ < nx0 + lnp - 500
    # MN2 bottom (net3): its M2 track extended left to RBW's left terminal
    ty3, xa3, xb3 = tracks[(nst, "B")]
    c.r("m2", bterm[0] - 190, ty3 - 190, xa3, ty3 + 190)
    c.r("m2", bterm[0] - 190, rcy - 190, bterm[0] + 190, ty3)
    c.via1(bterm[0], rcy)

    # p+ tap strips + VSS M1 straps in the group breaks, from the VSS rail up to bar 0 (latch-up, substrate noise)
    for g0, g1 in zip(grp, grp[1:]):
        xm = snap((g0["x1"] + g1["x0"]) / 2)
        c.r("psd", xm - 190, rows[-1][0], xm + 190, rows[0][1])
        c.r("psc", xm - 115, rows[-1][0] + 75, xm + 115, rows[0][1] - 75)
        c.r("m1", xm - 190, Y["vss_t"] - 300, xm + 190, ybar[0])

    # ---------------- left VSS strap + p+ tap ----------------
    c.r("psd", xt - 190, 600, xt + 190, Y["gs_b"] - 1200)
    c.r("psc", xt - 115, 675, xt + 115, Y["gs_b"] - 1275)
    c.r("m1", xt - 190, Y["vss_t"] - 300, xt + 190, Y["gs_b"] - 1200)

    # ---------------- MP row ----------------
    Y["ps_b"] = Y["gs_t"] + 315               # MP gate strap (net1)
    Y["ps_t"] = Y["ps_b"] + 380
    Y["p_bot"] = Y["ps_t"] + 500
    wp, lp, npf = um(S["wp"]), um(S["lp"]), int(S["npf"])
    pat = ["P1", "P1", "P2", "P2", "P2", "P2", "P1", "P1"]
    assert pat.count("P1") == npf and pat.count("P2") == npf
    mpw = 2 * (CO_POLY + CO + ENC_CO) + 8 * lp + 7 * 560
    mpx0 = snap((gx0 + mn_x1) / 2 - mpw / 2)
    mp = fet_row(c, mpx0, Y["p_bot"], wp, [(lp, "net1")] * 8, "p")
    Y["p_top"] = Y["p_bot"] + wp
    for (a, b) in mp["gx"]:
        c.r("poly", a, Y["ps_b"] + 5, b, Y["p_bot"])
        gc = (a + b) // 2
        for o in range(-6000, 6001, 1500):
            c.r("pc", gc + o - 115, Y["ps_b"] + 75, gc + o + 115, Y["ps_b"] + 305)
    c.r("poly", mp["gx"][0][0], Y["ps_b"] + 5, mp["gx"][-1][1], Y["ps_t"] - 5)
    mp_x1 = mp["x1"]
    # regions: 0,2,4,6,8 VDD; 1,7 P1 drain (vbn); 3,5 P2 drain (net1)
    rnet = {0: "VDD", 1: "vbn", 2: "VDD", 3: "net1", 4: "VDD", 5: "net1", 6: "VDD", 7: "vbn", 8: "VDD"}
    Y["vdd_b"] = Y["p_top"] + 600
    Y["vdd_t"] = Y["vdd_b"] + 2400
    vbn_x = []
    for i, cx in enumerate(mp["rx"]):
        n = rnet[i]
        if n == "VDD":
            c.r("m1", cx - 190, mp["ct"], cx + 190, Y["vdd_b"] + 300)
        elif n == "net1":
            c.r("m1", cx - 190, Y["ps_b"], cx + 190, mp["cb"])
        else:                                 # vbn: via1 at the region bottom, M2 down to the MN gate strap
            yv = Y["p_bot"] + 600
            c.via1(cx, yv)
            c.r("m2", cx - 190, Y["gs_b"] + 190 - 190, cx + 190, yv)
            c.via1(cx, Y["gs_b"] + 190)
            vbn_x.append(cx)
    # MN2 top (net1, gap 0 B bars): via1 + M2 up to the MP gate strap, away from the vbn drops
    net1_x = []
    for _, cxs in segs[(0, "B")]:
        cands = sorted(cxs, key=lambda v: abs(v - mid(cxs)))
        xv = next(v for v in cands if all(abs(v - u) > 1200 for u in vbn_x))
        c.via1(xv, ybar[0])
        c.r("m2", xv - 190, ybar[0], xv + 190, Y["ps_b"] + 190)
        c.via1(xv, Y["ps_b"] + 190)
        net1_x.append(xv)

    # ---------------- column C: start-up ----------------
    xc = max(mn_x1, mp_x1) + 1500
    c.r("m1", min(gx0, mpx0), Y["ps_b"], xc + 600, Y["ps_t"])                   # net1 strap
    c.r("m1", xt - 190, Y["gs_b"], xc + 1600, Y["gs_t"])                 # vbn strap (to column C)
    # MS3: nfet 1/0.28, regions [net1 | gate net2 | vbn], under the straps
    y3 = Y["gs_b"] - 900 - 1000
    ms3 = fet_row(c, xc, y3, 1000, [(280, "net2")], "n", pc="bot")
    r3n1, r3vbn = ms3["rx"]
    c.r("m1", r3vbn - 190, ms3["ct"], r3vbn + 190, Y["gs_b"] + 100)          # vbn up into the strap
    c.via1(r3n1, y3 + 500)
    c.r("m2", r3n1 - 190, y3 + 500, r3n1 + 190, Y["ps_b"] + 190)
    c.via1(r3n1, Y["ps_b"] + 190)
    g3x, g3y = ms3["pcs"][0]
    # MS2: nfet 2/0.28, regions [net2 (wide, contact under the MS3 gate) | gate vbn | VSS]
    y2t = y3 - 870
    y2 = y2t - 2000
    x2 = g3x - 590
    c.r("ndiff", x2, y2, x2 + 1180 + 280 + 450, y2t)
    for cx in (g3x, x2 + 1180 + 280 + 265):
        c.r("ndc", cx - 115, y2 + 70, cx + 115, y2t - 70)
        c.r("m1", cx - 190, y2 - 5, cx + 190, y2t + 5)
    g2a = x2 + 1180
    c.r("poly", g2a, y2 - ENDCAP, g2a + 280, y2t + 260)
    g2x = g2a + 140
    c.r("poly", g2x - 185, y2t + 260, g2x + 185, y2t + 630)
    c.r("pc", g2x - 115, y2t + 330, g2x + 115, y2t + 560)
    c.r("m1", g2x - 190, y2t + 255, g2x + 190, y2t + 635)
    r2vss = x2 + 1180 + 280 + 265
    c.r("m1", g3x - 190, y2t, g3x + 190, g3y)                                    # net2: MS2 drain -> MS3 gate
    c.via1(g2x, y2t + 445)                                                       # MS2 gate -> vbn strap (M2)
    c.r("m2", g2x - 190, y2t + 445, g2x + 190, Y["gs_b"] + 190)
    c.via1(g2x, Y["gs_b"] + 190)
    # MS1: pfet 0.5/10, vertical (L along y) in the MP n-well: drain (net2) at the bottom, source (VDD) on top
    m1x = g3x
    y1 = Y["p_bot"] + 300
    lms1 = 10000
    c.r("pdiff", m1x - 250, y1, m1x + 250, y1 + 450 + lms1 + 450)
    for yc in (y1 + 185, y1 + 450 + lms1 + 265):
        c.r("pdc", m1x - 115, yc - 115, m1x + 115, yc + 115)
        c.r("m1", m1x - 190, yc - 190, m1x + 190, yc + 190)
    c.r("poly", m1x - 250 - ENDCAP, y1 + 450, m1x + 250 + ENDCAP, y1 + 450 + lms1)
    pgx = m1x + 250 + 170 + 300
    c.r("poly", m1x, y1 + 450 + 3000, pgx + 300, y1 + 450 + 3600)
    c.r("pc", pgx - 115 + 100, y1 + 450 + 3185, pgx + 115 + 100, y1 + 450 + 3415)
    xs_r = xc + 3400                          # VSS strap (M1, p+ tap) on the right
    c.r("m1", pgx - 90, y1 + 450 + 3110, xs_r + 190, y1 + 450 + 3490)
    c.r("m1", m1x - 190, y1 + 450 + lms1 + 265, m1x + 190, Y["vdd_b"] + 300)    # source -> VDD
    # net2: MS1 drain -> M3 -> MS3 gate (via stacks)
    c.via12(m1x, y1 + 185)
    c.via12(g3x, g3y)
    c.r("m3", g3x - 190, g3y, g3x + 190, y1 + 185)
    # VSS strap + MS2 source
    c.r("m1", xs_r - 190, Y["vss_t"] - 300, xs_r + 190, y1 + 450 + 3490)
    c.r("m1", r2vss - 190, y2 + 300, xs_r, y2 + 680)
    c.r("psd", xs_r - 190, 600, xs_r + 190, y2 - 1000)
    c.r("psc", xs_r - 115, 675, xs_r + 115, y2 - 1075)
    W_bb = xs_r + 190 + 600
    # vbn pin (right edge, M2 from the MS2-gate vbn drop)
    yvp = Y["gs_b"] - 500
    c.r("m2", g2x - 190, yvp - 190, W_bb, yvp + 190)
    c.label("vbn", "m2", W_bb - 100, yvp, port=True)
    # vctrl feed-through
    c.r("m2", 0, VCTRL_Y - 190, W_bb, VCTRL_Y + 190)
    c.label("vctrl", "m2", W_bb - 100, VCTRL_Y, port=True)
    # VSS M1 shield under vctrl across the CF (joins the CF's VSS S/D columns): keeps vctrl off the vbnf gate poly
    c.r("m1", cf["rx"][0] - 190, VCTRL_Y - 2000, cf["rx"][-1] + 190, VCTRL_Y + 2000)

    # RF vbn terminal -> M2 down to the vbn strap (extended left to it)
    c.via1(*rf_vbn)
    vx = rf_vbn[0]
    c.r("m2", vx - 190, Y["gs_b"] + 190, vx + 190, rf_vbn[1])
    c.via1(vx, Y["gs_b"] + 190)
    c.r("m1", vx - 190, Y["gs_b"], xt, Y["gs_t"])

    # ---------------- n-well (MP + MS1), taps, rails ----------------
    Y["nw_b"] = Y["p_bot"] - 450
    Y["tap_t"] = Y["vdd_b"] + 1010
    Y["nw_t"] = Y["tap_t"] + 380 + 150
    nw_x0, nw_x1 = mpx0 - 450, max(mp_x1, m1x + 250) + 450
    c.r("nwell", nw_x0, Y["nw_b"], nw_x1, Y["nw_t"])
    c.r("nsd", nw_x0 + 150, Y["tap_t"], nw_x1 - 150, Y["tap_t"] + 380)
    c.r("nsc", nw_x0 + 225, Y["tap_t"] + 75, nw_x1 - 225, Y["tap_t"] + 305)

    def rail(x0, x1, yb, yt, name, tap):
        c.r("m1", x0, yb, x1, yt)
        c.r("m2", x0, yb, x1, yt)
        x = x0 + 400
        while x + 400 < x1:
            c.r("v1", x - 130, yb + 300, x + 130, yt - 300)
            x += 2000
        if tap:
            c.r("psd", x0 + 300, yb + 1010, x1 - 300, yb + 1390)
            c.r("psc", x0 + 375, yb + 1085, x1 - 375, yb + 1315)
        c.label(name, "m2", x0 + 1000, (yb + yt) // 2, port=True)
    rail(0, W_bb, Y["vss_b"], Y["vss_t"], "VSS", True)
    rail(nw_x0, W_bb, Y["vdd_b"], Y["vdd_t"], "VDD", False)
    for n, xx, yy in (("net1", mp["rx"][3], Y["ps_b"] + 190), ("net3", bterm[0], rcy),
                      ("net4", bterm[1], rcy), ("net2", g3x, g3y)):
        c.label(n, "m1", xx, yy)
    top = max(Y["vdd_t"], Y["rf_top"]) + 300
    bbox = (0, Y["vss_b"] - 300, W_bb, top)
    meta = dict(Y=Y, bbox=bbox, ybar=ybar, rows=rows, groups=[(g["dev"], g["n"], g["x0"], g["x1"]) for g in grp],
                dummies=dum, mp=dict(x0=mpx0, x1=mp_x1, pat=pat), rf=dict(xa=xa, xb=xb, Ls=Ls, D0=D0, D8=D8, n=nrs,
                y0=ry0), cf=dict(x0=cfx0, x1=cf_x1), rbw=dict(x0=bx0, lnw=lnw), rbn=dict(x0=nx0, lnp=lnp),
                rnw=[bx0 + 800, ry_b, bx0 + 800 + lnw, ry_t], colC=xc, tracks={f"{k[0]}{k[1]}": v for k, v in tracks.items()}, vbn_pin_y=yvp, S=S)
    return [c], meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--out", default=str(REPO / "build" / "layout_cgm_ref"))
    ap.add_argument("--gds", default=str(REPO / "layout" / "cgm_ref.gds"))
    ap.add_argument("--no-magic", action="store_true")
    a = ap.parse_args()
    cells, meta = build(a.set)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.mag"):
        old.unlink()
    tcl = "drc off\nsnap internal\n" + "".join(c.tcl() for c in cells)
    tcl += f"load cgm_ref\nselect top cell\nexpand\ngds write {Path(a.gds).resolve()}\nquit -noprompt\n"
    (out / "cgm_ref.tcl").write_text(tcl)
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
    bb = meta["bbox"]
    print(f"bbox {(bb[2]-bb[0])/1000:.2f} x {(bb[3]-bb[1])/1000:.2f} um = {(bb[2]-bb[0])*(bb[3]-bb[1])/1e6:.0f} um2,"
          f" x {bb[0]/1000}..{bb[2]/1000}, y {bb[1]/1000}..{bb[3]/1000}; vbnf pin y {VBNF_Y/1000}, vctrl y {VCTRL_Y/1000},"
          f" vbn pin y {meta['vbn_pin_y']/1000}")
    if not a.no_magic:
        rc = f"{os.environ.get('PDK_ROOT', '/foss/pdks')}/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc"
        r = subprocess.run(["magic", "-rcfile", rc, "-noconsole", "-dnull", "cgm_ref.tcl"], cwd=out,
                           capture_output=True, text=True)
        (out / "magic_gen.log").write_text(r.stdout + r.stderr)
        print("magic log:", out / "magic_gen.log")
        add_res_mk(a.gds, meta["rnw"])


def add_res_mk(gds, box):
    """magic's gf180mcuD GDS output marks every resistor with RES_MK (110/5) except the n-well resistor (rnw is not
    in its 'allres'), so the GDS would hold RBW as plain n-well. Add RES_MK over the rnw body (the PDK KLayout LVS
    derives the n-well resistor as NWELL & RES_MK; check_ref.sh / pex_ref.sh repaint rnw from it after gds read)."""
    import klayout.db as db
    ly = db.Layout()
    ly.read(gds)
    top = ly.cell("cgm_ref")
    li = ly.layer(110, 5)
    top.shapes(li).insert(db.Box(*[int(round(v / 1000 / ly.dbu)) for v in box]))
    ly.write(gds)
    print("added RES_MK (110/5) over the n-well resistor", [v / 1000 for v in box])


if __name__ == "__main__":
    main()
