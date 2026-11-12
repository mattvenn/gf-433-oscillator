#!/usr/bin/env python3
"""Current-fed ring core layout (v3): vco_bias.netlist() with topo=cfed, without the const-gm reference and vbn filter.

    python3 layout/gen/ring_core_v3.py [--set wfu=0.30 ...] [--out build/layout_v3] [--gds layout/ring_core_v3.gds]

Circuit (sizes from vco_bias, settings CFED below; wff follows wfu unless set):
  5 plain inverters P 5/0.28 (source VDD), N 2/0.28 (source vg), ring a0..a4;
  vg: MOS decap (pfet_03v3, gate vg, S/D/B VDD, ~cvg; to VSS as an nfet before 2026-11-12) + one shared NMOS
      current DAC vg -> VSS:
      base k units (gate vbn), binary coarse legs 2^b units (gate g_b), fine leg (gate vctrl);
      unit W = wfu*kw, L = ls*kl (kc, ka as vco_bias.netlist); coarse switches TN/TP/TD per bit.

Floorplan (x left to right, y bottom to top):
  VSS rail (M1+M2) along the bottom, inside the p+ substrate ring.
  left : MOS decap, one row of dc_nf PMOS fingers (L dc_l) in its own n-well, gate contacts up into the vg strap
         (M1+M2) that runs straight above it; S/D columns down onto an n+ tap strip with a VDD strap (M1+M2) just
         above the VSS rail, fed from the top VDD rail by two M3 drops over the inverter cluster (VDD - vg is the
         ring's own supply: with the decap to VDD, vg rides with VDD at the macro's 25 MHz, docs/tx_fine_tune.md);  the inverter cluster (v2 cluster without heads) sits
         directly on the vg strap: every N source is a 0.3 um M1 drop into it.
  right: the DAC, 7 rows x 6 unit slots, point-symmetric (common centroid) for the base and binary legs, the fine
         leg and bit 0 in the middle row. Rows pair up around an M2 gate-track bundle (row A gate contacts on top,
         row B below); S/D alternate VSS / vg: vg on an M2 strap over each row, VSS M1 columns to p+-tapped M1 rails
         between the pairs. vg (M3) and VSS (M1) verticals on the DAC's left side.
         Above the DAC, in the cluster band: 5 switch slices (TD, TN in the N band, TP in the P band, shared n-well
         with the cluster), g_b dropped on M3 straight onto the DAC tracks.
  top  : vbn M2 line over the switch PMOS, VDD rail (M1+M2) over the n-well tap ring.
Pins: VDD, VSS (M2 rails), vbn, vctrl (M2, right edge), bit/bitb (M3, top edge), vg (M3, bottom edge),
      a0 (M2, left edge, short tap), a1..a4 labels on the ring rows. No Metal4.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ring_core as v1  # noqa: E402
from ring_core import Cell, fet_row, vco_bias, CO, CO_POLY, ENC_CO, NW_ENC_NSD, NW_ENC_P, NSD_PSD, TPITCH  # noqa: E402
from ring_core_v2 import ORDER, MIRROR, IPITCH, XIN, RROW, mirror_cell, tap_ring  # noqa: E402

REPO = HERE.parents[1]
# the 2026-11-08 winner reference + the cfed settings (docs/cfed_results.md); ka = 16: DAC area x16
WINNER = dict(rideal=0, lnp=100.0, lnw=3.665, nsn=14, wpm=56.0, lpm=14.0, mr=4.0)
CFED = dict(topo="cfed", kc=0.75, k=6, cvg=3e-12, cw=3e-15, ka=16.0, rf=0.0, cf=0.0)
COX = 4.07e-3            # nfet_03v3 gate C per area incl. overlap (F/m2), tt, Vg 1.1-3 V (build/v3/cv); the pfet_03v3
                         # decap to VDD gives the same C at the same size (2.9-3.15 pF, build/tx_fine/vg_decap/cv)
DECAP = dict(dc_nf=6, dc_l=4.12)   # L 4.12 (W 29.82, 737 um2 as the 4.0 x 30.71 before): the PMOS decap's n+ tap strip
                                   # fits under it with every y above the decap unchanged (vbn meets cgm_ref at a fixed y)
END = CO_POLY + CO + ENC_CO   # diffusion end beyond the outer gate (contacted)
DGAP = 560                    # S/D region between gates


def snap(v):
    return int(round(v / 5.0)) * 5


def um(v):
    return snap(v * 1000)


def params(sets=()):
    p = dict(vco_bias.P)
    p.update(WINNER)
    p.update(CFED)
    p.update(DECAP)
    wff_set = False
    for kv in sets:
        k, v = kv.split("=")
        p[k] = type(p[k])(float(v)) if not isinstance(p[k], str) else v
        wff_set |= k == "wff"
    if not wff_set:
        p["wff"] = p["wfu"]
    return p


def dac_sizes(p):
    """Unit and fine-leg W/L (um) exactly as vco_bias.netlist() topo=cfed."""
    kw, kl = max(p["kc"], 1.0), 1.0 / min(p["kc"], 1.0)
    kw, kl = kw * p["ka"] ** 0.5, kl * p["ka"] ** 0.5
    return dict(wu=p["wfu"] * kw, lu=p["ls"] * kl, wf=p["wff"] * kw, lf=p["lff"] * kl)


def decap_size(p):
    """(nf, L um, W um) of the vg MOS decap for ~cvg."""
    nf, L = int(p["dc_nf"]), p["dc_l"]
    W = round(p["cvg"] / (nf * L * 1e-6 * COX) * 1e6, 2)
    return nf, L, W


# DAC unit placement: rows 0..2 (6 slots) hold one unit of every point-symmetric pair, rows 4..6 the mirrors,
# row 3 the singletons (bit 0) and the fine leg.
HALF = [["g4", "g3", "g4", "vbn", "g4", "g2"],
        ["g3", "g4", "g1", "g4", "vbn", "g4"],
        ["g4", "vbn", "g2", "g3", "g4", "g3"]]
MID = ["g0", "vctrl"]


def dac_plan(p):
    assert p["k"] == 6 and p["bits"] == 5, "placement table is for k=6, 5 bits"
    rows = HALF + [MID] + [list(reversed(r)) for r in reversed(HALF)]
    cnt = {}
    for r in rows:
        for n in r:
            cnt[n] = cnt.get(n, 0) + 1
    want = dict(vbn=p["k"], vctrl=1, **{f"g{b}": 2 ** b for b in range(p["bits"])})
    assert cnt == want, (cnt, want)
    return rows


# ---------------------------------------------------------------------------------------------------------
def plan(p, dac_h):
    """y coordinates. dac_h: DAC height above the VSS rail top (from draw_dac in a dry run)."""
    nf, L, Wdc = decap_size(p)
    Y = dict(vss_b=-2400, vss_t=0)
    Y["dct_b"] = 310                       # decap n+ tap strip (VDD) above the VSS rail; strap M1+M2 dcs_b..dcs_t
    Y["dcs_b"], Y["dcs_t"] = 300, 900
    Y["dc_b"] = Y["dct_b"] + 380 + NSD_PSD
    assert Y["dc_b"] + um(Wdc) + 255 <= 31365, "the decap would move every y above it (vco_top, cgm_ref vbn)"
    Y["dcw_b"] = Y["dct_b"] - NW_ENC_NSD     # decap n-well bottom
    Y["dc_t"] = Y["dc_b"] + um(Wdc)
    Y["vg_b"] = max(Y["dc_t"] + 255, dac_h + 500)
    Y["dc_pc"] = Y["vg_b"] + 190
    Y["dcw_t"] = Y["dc_t"] + NW_ENC_P
    Y["vg_t"] = Y["vg_b"] + 1500
    Y["n_bot"] = Y["vg_t"] + 300
    Y["n_top"] = Y["n_bot"] + um(p["wn"])
    Y["pcl"] = Y["n_top"] + 445
    Y["tap_b"] = Y["n_top"] + 730
    Y["nw_b"] = Y["tap_b"] - NW_ENC_NSD
    Y["p_bot"] = Y["tap_b"] + 1280
    Y["pch"] = Y["p_bot"] - 445
    Y["p_top"] = Y["p_bot"] + max(um(p["wp"]), 5000)
    Y["vbnl"] = Y["p_top"] + 490
    Y["vdd_b"] = Y["vbnl"] + 490
    Y["vdd_t"] = Y["vdd_b"] + 2400
    Y["tap_t"] = Y["vdd_b"] + 1010
    Y["nw_t"] = Y["tap_t"] + 380 + NW_ENC_NSD
    mid = (Y["pcl"] + Y["pch"]) // 2 // 5 * 5
    Y["rows"] = [mid, mid - RROW, mid + RROW]
    Y["gstrap"] = Y["n_bot"] - 600
    return Y


def inv_cell(p, Y):
    """Plain inverter (v2 ring_inv without the head). Origin: diffusion left edge at x=0.
    N: [out | in | vg], P: [out | in | VDD]; input riser on the source side, output riser on the drain side."""
    c = Cell("ring_inv")
    Ln, wn, wp = um(p["L"]), um(p["wn"]), um(p["wp"])
    n = fet_row(c, 0, Y["n_bot"], wn, [(Ln, "in")], "n")
    gx0, gx1 = n["gx"][0]
    gc = (gx0 + gx1) // 2
    xin, xout, xs = gc + XIN, n["rx"][0], n["rx"][1]
    pb = Y["pcl"] - 185
    c.r("poly", gx0, n["ybot"] + wn, gx1, pb + 370)
    c.r("poly", gx0, pb, xin + 185, pb + 370)
    c.r("pc", xin - 115, pb + 70, xin + 115, pb + 300)
    pr = fet_row(c, 0, Y["p_bot"], wp, [(Ln, "in")], "p")
    assert pr["gx"][0] == n["gx"][0] and pr["rx"][1] == xs
    pt = Y["pch"] + 185
    c.r("poly", gx0, pt - 370, gx1, pr["ybot"])
    c.r("poly", gx0, pt - 370, xin + 185, pt)
    c.r("pc", xin - 115, pt - 300, xin + 115, pt - 70)
    c.r("m1", xin - 190, Y["pcl"] - 190, xin + 190, Y["pch"] + 190)       # input riser
    c.r("m1", xout - 190, n["cb"] - 75, xout + 190, pr["ct"] + 75)         # output riser N drain -> P drain
    c.r("m1", xs - 190, pr["ct"], xs + 190, Y["vdd_b"] + 400)              # P source -> VDD rail
    c.r("m1", xs - 190, Y["vg_t"] - 400, xs + 190, n["cb"])                # N source -> vg strap (0.3 um drop)
    return c, dict(gc=gc, xin=xin - gc, xout=xout - gc, xs=xs - gc, dl=-gc, dr=max(n["x1"], pr["x1"]) - gc,
                   mr=xin + 190 - gc)


# ---------------------------------------------------------------------------------------------------------
def draw_dac(top, p, x0, info):
    """DAC rows from y=300 up, rows left-aligned to a common centre at x0 + max_w/2.
    Returns geometry: tracks {net: [(y, xa, xb)]}, rails, vg strap ys, extents."""
    s = dac_sizes(p)
    W, Lu, Lf = um(s["wu"]), um(s["lu"]), um(s["lf"])
    assert um(s["wf"]) == W, "fine-leg W must equal the unit W (shared diffusion)"
    rows = dac_plan(p)
    gl = lambda n: Lf if n == "vctrl" else Lu
    width = lambda r: 2 * END + sum(gl(n) for n in r) + DGAP * (len(r) - 1)
    wmax = max(width(r) for r in rows)
    xc = x0 + wmax // 2
    # vertical stack: pairs (0,1) (2,3) (4,5), single 6
    groups = [(0, 1), (2, 3), (4, 5), (6,)]
    y = 300
    geo = dict(rows=[], tracks={}, rails=[], straps=[], x0=x0, x1=x0 + wmax)
    stubs = []          # (x, ylo, yhi) M1 stubs, for clash checks
    for gi, grp in enumerate(groups):
        nets = []
        for ri in grp:
            for n in rows[ri]:
                if n not in nets:
                    nets.append(n)
        ra = grp[0]
        yb_a = y
        t0 = yb_a + W + 445
        ty = {n: t0 + k * TPITCH for k, n in enumerate(nets)}
        tl = t0 + (len(nets) - 1) * TPITCH
        rowsy = [(ra, yb_a, "A")]
        if len(grp) == 2:
            rowsy.append((grp[1], tl + 445, "B"))
        xs_all = []
        for ri, yb, kind in rowsy:
            r = rows[ri]
            rx0 = snap(xc - width(r) / 2)
            g = fet_row(top, rx0, yb, W, [(gl(n), n) for n in r], "n")
            assert abs(g["x1"] - rx0 - width(r)) <= 5
            xs_all += [rx0, g["x1"]]
            pcy = t0 if kind == "A" else tl
            # gate poly to the contact row, contact offset along the gate so A and B stubs never share an x
            for (ga, gb), n in zip(g["gx"], r):
                gc = (ga + gb) // 2
                if kind == "A":
                    top.r("poly", ga, yb + W, gb, pcy + 185)
                else:
                    top.r("poly", ga, pcy - 185, gb, yb)
                lim = (gb - ga) // 2 - 185
                offs = [-1500, -2300, -700, 0, 700, 1500, 2300] if kind == "A" else [1500, 2300, 700, 0, -700, -1500, -2300]
                yk = ty[n]
                ylo, yhi = min(pcy, yk) - 190, max(pcy, yk) + 190
                for o in offs:
                    if abs(o) > lim:
                        continue
                    x = snap(gc + o)
                    if all(abs(x - sx) >= 380 + 300 or yhi + 230 <= sl or ylo - 230 >= sh for sx, sl, sh in stubs):
                        break
                else:
                    raise SystemExit(f"no stub position for row {ri} gate {n}")
                stubs.append((x, ylo, yhi))
                top.r("pc", x - 115, pcy - 115, x + 115, pcy + 115)
                top.r("m1", x - 190, ylo, x + 190, yhi)
                top.via1(x, yk)
            # S/D: even regions VSS, odd regions vg
            ymid = yb + W // 2
            for i, cx in enumerate(g["rx"]):
                if i % 2:
                    top.via1(cx, ymid)
                else:
                    if kind == "A":
                        top.r("m1", cx - 190, yb - 790 - 190 if (ri > 0) else -300, cx + 190, g["cb"])
                    else:
                        top.r("m1", cx - 190, g["ct"], cx + 190, yb + W + 790 + 190)
            geo["straps"].append((ymid, g["rx"][1], g["rx"][-2]))
            geo["rows"].append(dict(ri=ri, yb=yb, x0=rx0, x1=g["x1"], nets=r))
        xa, xb = min(xs_all), max(xs_all)
        for n, yk in ty.items():
            top.r("m2", xa, yk - 190, xb, yk + 190)
            geo["tracks"].setdefault(n, []).append((yk, xa, xb))
        ytop = rowsy[-1][1] + W if len(grp) == 2 else tl + 190
        rail = ytop + 790 if len(grp) == 2 else tl + 680
        geo["rails"].append(rail)
        y = rail + 790
    geo["top"] = geo["rails"][-1] + 190
    return geo


def build(p):
    nf, Ldc, Wdc = decap_size(p)
    # dry run of the DAC for its height
    tmp = Cell("tmp")
    gd = draw_dac(tmp, p, 0, {})
    Y = plan(p, gd["top"])
    iv, ii = inv_cell(p, Y)
    top = Cell("ring_core")

    # ---- decap: one row of nf PMOS fingers from x=0, in its own n-well with an n+ tap strip below ----
    dc = fet_row(top, 0, Y["dc_b"], um(Wdc), [(um(Ldc), "vg")] * nf, "p")
    for (ga, gb) in dc["gx"]:
        top.r("poly", ga, Y["dc_t"], gb, Y["dc_pc"] + 185)
        gc = (ga + gb) // 2
        for o in (-1200, 0, 1200):
            top.r("pc", gc + o - 115, Y["dc_pc"] - 115, gc + o + 115, Y["dc_pc"] + 115)
        top.r("m1", ga + 600 - 190 * 0, Y["dc_pc"] - 190, gb - 600, Y["dc_pc"] + 190)
    dcx1 = dc["x1"]
    wl_, wr_ = -NW_ENC_P, dcx1 + NW_ENC_P   # decap n-well
    top.r("nwell", wl_, Y["dcw_b"], wr_, Y["dcw_t"])
    top.r("nsd", wl_ + NW_ENC_NSD, Y["dct_b"], wr_ - NW_ENC_NSD, Y["dct_b"] + 380)
    top.r("nsc", wl_ + NW_ENC_NSD + 75, Y["dct_b"] + 75, wr_ - NW_ENC_NSD - 75, Y["dct_b"] + 305)
    for lay in ("m1", "m2"):                 # VDD strap over the tap
        top.r(lay, wl_ + NW_ENC_NSD - 5, Y["dcs_b"], wr_ - NW_ENC_NSD + 5, Y["dcs_t"])
    top.r("v1", wl_ + 400, Y["dcs_b"] + 170, wr_ - 400, Y["dcs_t"] - 170)
    for cx in dc["rx"]:                      # S/D (both) onto the VDD strap
        top.r("m1", cx - 190, Y["dcs_b"], cx + 190, dc["cb"])
    dcvdd = [1000, snap(dcx1 - 1000)]        # M3 VDD drops (1 um), top rail -> strap; drawn with the rails below

    # ---- DAC to the right ----
    vssv = wr_ + 430 + 190                   # VSS M1 vertical (left side of the DAC; its p+ rails 0.43 from the n-well)
    vgv = vssv + 700                        # vg M3 vertical
    dx0 = vssv + 190 + 900
    gd = draw_dac(top, p, dx0, {})
    for (ym, xa, xb) in gd["straps"]:       # vg M2 straps over each row -> vg M3 vertical
        top.r("m2", vgv - 190, ym - 190, xb + 190, ym + 190)
        top.via2(vgv, ym)
    for ry in gd["rails"]:                  # p+ tapped VSS M1 rails
        top.r("m1", vssv - 190, ry - 190, gd["x1"], ry + 190)
        top.r("psd", vssv - 190, ry - 190, gd["x1"], ry + 190)
        top.r("psc", vssv - 115, ry - 115, gd["x1"] - 75, ry + 115)
    top.r("m1", vssv - 190, Y["vss_t"] - 300, vssv + 190, gd["rails"][-1] + 190)

    # ---- vg strap over the decap, M2 extension to the DAC's vg vertical ----
    top.r("m1", 0, Y["vg_b"], dcx1, Y["vg_t"])
    top.r("m2", 0, Y["vg_b"], dcx1, Y["vg_t"])
    x = 400
    while x + 400 < dcx1:
        top.r("v1", x - 130, Y["vg_b"] + 300, x + 130, Y["vg_t"] - 300)
        x += 2000
    vgy = (Y["vg_b"] + Y["vg_t"]) // 2
    top.r("m2", dcx1 - 400, Y["vg_b"], vgv + 190, Y["vg_t"])
    top.via2(vgv, vgy)

    # ---- inverter cluster on the vg strap, left-aligned at x=0 ----
    rel = [0]
    for i in range(4):
        rel.append(rel[-1] + IPITCH[(MIRROR[i], MIRROR[i + 1])])
    ext0 = sorted((ii["dl"] * MIRROR[0], ii["dr"] * MIRROR[0]))
    left0 = min(ext0[0] - NSD_PSD, ii["mr"] * MIRROR[0] - 300) - 380 - NW_ENC_NSD   # well left, rel. to gc0
    cx0 = snap(-left0 + 0)
    cx = [cx0 + r for r in rel]
    for i, s in enumerate(ORDER):
        if MIRROR[i] > 0:
            top.inst("ring_inv", cx[i] - ii["gc"], 0, f"inv{s}")
        else:
            top.inst("ring_inv_m", cx[i] + ii["gc"], 0, f"inv{s}")
    assert max(cx[i] + max(ii["dl"] * MIRROR[i], ii["dr"] * MIRROR[i]) for i in range(5)) < dcx1

    # ---- ring nodes (v2 row assignment) ----
    col = {s: i for i, s in enumerate(ORDER)}
    rows = {k: [] for k in range(len(Y["rows"]))}
    lens, spans = {}, {}
    ivals = []
    for j in range(p["n"]):
        cd, cl = col[(j - 1) % p["n"]], col[j]
        xo = cx[cd] + ii["xout"] * MIRROR[cd]
        xi = cx[cl] + ii["xin"] * MIRROR[cl]
        ivals.append((min(xo, xi), max(xo, xi), j, xo, xi))
    for a, b, j, xo, xi in sorted(ivals, key=lambda t: -(t[1] - t[0])):
        for k in range(len(Y["rows"])):
            if all(b + 190 + 300 <= a2 - 190 or a - 190 - 300 >= b2 + 190 for a2, b2 in rows[k]):
                rows[k].append((a, b))
                break
        else:
            raise SystemExit("ring rows full")
        ty = Y["rows"][k]
        top.r("m2", a - 190, ty - 190, b + 190, ty + 190)
        top.via1(xo, ty)
        top.via1(xi, ty)
        lo, hi = min(ty, Y["pcl"]), max(ty, Y["pch"])
        top.r("m1", xi - 190, lo - 190, xi + 190, hi + 190)
        lens[j] = b - a
        spans[j] = (a, b, ty)
        if j:
            top.label(f"a{j}", "m2", (a + b) // 20 * 10, ty, port=True)

    # ---- coarse switches: 5 slices above the DAC ----
    L = um(0.28)
    gcs = [snap(dx0 + 2600 + b * 3700) for b in range(p["bits"])]
    assert gcs[0] - 1325 > dcx1 + 600 and gcs[0] - 770 - 190 > vgv + 190 + 300
    sw = dict(bit={}, bitb={}, g={})
    for b, gc in enumerate(gcs):
        xa = gc - 590
        tn = fet_row(top, xa, Y["n_bot"], um(2.0), [(L, f"bit{b}")], "n")
        tp = fet_row(top, xa, Y["p_bot"], um(5.0), [(L, f"bitb{b}")], "p")
        assert tn["rx"][0] == gc - 405 and tn["rx"][1] == gc + 405
        gtd = gc - 1540
        td = fet_row(top, gtd - 140 - END, Y["n_bot"], um(1.0), [(L, f"bitb{b}")], "n")
        assert td["rx"][1] == gc - 1135, td["rx"]
        # TN gate -> pc right of its vbn riser (bit)
        top.r("poly", gc - 140, Y["n_top"], gc + 140, Y["pcl"] + 185)
        top.r("poly", gc - 140, Y["pcl"] - 185, gc + 1100 + 185, Y["pcl"] + 185)
        top.r("pc", gc + 1100 - 115, Y["pcl"] - 115, gc + 1100 + 115, Y["pcl"] + 115)
        top.via12(gc + 1100, Y["pcl"])
        sw["bit"][b] = (gc + 1100, Y["pcl"])
        # TP gate -> pc above TD's gate (bitb); TD gate -> pc at pcl, same x; M1 joins them
        top.r("poly", gc - 140, Y["pch"] - 185, gc + 140, Y["p_bot"])
        top.r("poly", gtd - 185, Y["pch"] - 185, gc + 140, Y["pch"] + 185)
        top.r("pc", gtd - 115, Y["pch"] - 115, gtd + 115, Y["pch"] + 115)
        top.r("poly", gtd - 140, Y["n_bot"] + um(1.0), gtd + 140, Y["pcl"] + 185)
        top.r("poly", gtd - 185, Y["pcl"] - 185, gtd + 185, Y["pcl"] + 185)
        top.r("pc", gtd - 115, Y["pcl"] - 115, gtd + 115, Y["pcl"] + 115)
        top.r("m1", gtd - 190, Y["pcl"] - 190, gtd + 190, Y["pch"] + 190)
        top.via12(gtd, Y["pch"])
        sw["bitb"][b] = (gtd, Y["pch"])
        # g: TN g -> TP g riser; TN g + TD g strap below the N band -> M3 down to the DAC
        top.r("m1", gc - 405 - 190, tn["cb"] - 75, gc - 405 + 190, tp["ct"] + 75)
        top.r("m1", gc - 1135 - 190, Y["gstrap"] - 190, gc - 405 + 190, Y["gstrap"] + 190)
        top.r("m1", gc - 1135 - 190, Y["gstrap"], gc - 1135 + 190, td["cb"])
        top.r("m1", gc - 405 - 190, Y["gstrap"], gc - 405 + 190, tn["cb"])
        gx = gc - 770
        top.via12(gx, Y["gstrap"])
        sw["g"][b] = gx
        # vbn: TN source -> TP source riser, TP source -> vbn M2 line
        top.r("m1", gc + 405 - 190, tn["cb"] - 75, gc + 405 + 190, Y["vbnl"] + 190)
        top.via1(gc + 405, Y["vbnl"])
        # TD source -> DAC top VSS rail
        top.r("m1", gc - 1945 - 190, gd["rails"][-1] - 190, gc - 1945 + 190, td["cb"])
    vbnx = gcs[-1] + 2000
    top.r("m2", gcs[0] + 405 - 190, Y["vbnl"] - 190, vbnx + 190, Y["vbnl"] + 190)

    # ---- M3 drops onto the DAC tracks: g_b, vbn ----
    for b, gx in sw["g"].items():
        ys = [t[0] for t in gd["tracks"][f"g{b}"]]
        assert all(t[1] + 190 <= gx <= t[2] - 190 for t in gd["tracks"][f"g{b}"])
        top.r("m3", gx - 190, min(ys) - 190, gx + 190, Y["gstrap"] + 190)
        for yk in ys:
            top.via2(gx, yk)
    ys = [t[0] for t in gd["tracks"]["vbn"]]
    assert all(t[1] + 190 <= vbnx <= t[2] - 190 for t in gd["tracks"]["vbn"])
    top.r("m3", vbnx - 190, min(ys) - 190, vbnx + 190, Y["vbnl"] + 190)
    for yk in ys:
        top.via2(vbnx, yk)
    top.via2(vbnx, Y["vbnl"])

    # ---- n-well (cluster P + switch TP) with tap ring ----
    cl = snap(cx[0] + left0)
    wr = gcs[-1] + 2200
    tap_ring(top, cl, wr, Y, [], contacts_bottom=False)

    # ---- rails, p+ ring, pins ----
    core_r = max(gd["x1"], wr)
    gl, gr = cl - 1600, core_r + 1600
    xl, xr = gl + 380 + 300, gr - 380 - 300
    for (yb, yt, nm) in ((Y["vss_b"], Y["vss_t"], "VSS"), (Y["vdd_b"], Y["vdd_t"], "VDD")):
        top.r("m1", xl, yb, xr, yt)
        top.r("m2", xl, yb, xr, yt)
        x = xl + 400
        while x + 400 < xr:
            top.r("v1", x - 130, yb + 300, x + 130, yt - 300)
            x += 2000
        top.label(nm, "m2", xl + 1000, (yb + yt) // 2, port=True)
    for x in dcvdd:                          # decap VDD drops: M3 from the VDD rail down to the decap's tap strap
        top.r("m3", x - 500, Y["dcs_b"], x + 500, Y["vdd_t"])
        for (yb, yt) in ((Y["dcs_b"], Y["dcs_t"]), (Y["vdd_b"], Y["vdd_t"])):
            top.r("m2", x - 500, yb, x + 500, yt)
            top.r("v2", x - 330, yb + 150, x + 330, yt - 150)
    gb, gt = Y["vss_b"] + 1010, Y["nw_t"] + 1200
    for (a, b2, c2, d) in ((gl, gb, gr, gb + 380), (gl, gt, gr, gt + 380), (gl, gb, gl + 380, gt + 380),
                           (gr - 380, gb, gr, gt + 380)):
        top.r("psd", a, b2, c2, d)
        top.r("m1", a - 5, b2 - 5, c2 + 5, d + 5)
    top.r("psc", gl + 75, gb + 75, gr - 75, gb + 305)
    top.r("psc", gl + 75, gt + 75, gr - 75, gt + 305)
    top.r("psc", gl + 75, gb + 75, gl + 305, gt + 305)
    top.r("psc", gr - 305, gb + 75, gr - 75, gt + 305)
    top.r("m1", gl - 5, Y["vss_b"], xl, Y["vss_t"])
    top.r("m1", xr, Y["vss_b"], gr + 5, Y["vss_t"])
    pin_b = Y["vss_b"] - 1600
    pin_t = gt + 380 + 1600
    # a0: short M2 tap from its ring row to the left edge
    a, b2, ty = spans[0]
    top.r("m2", gl - 300, ty - 190, a, ty + 190)
    top.label("a0", "m2", gl - 100, ty, port=True)
    # vg: DAC vg vertical (M3) down to the bottom edge, and up to the strap
    top.r("m3", vgv - 190, pin_b, vgv + 190, vgy + 190)
    top.label("vg", "m3", vgv, pin_b + 300, port=True)
    # bit / bitb: M3 up to the top edge
    for nm in ("bit", "bitb"):
        for b, (x, y) in sw[nm].items():
            top.r("m3", x - 190, y - 190, x + 190, pin_t)
            top.label(f"{nm}{b}", "m3", x, pin_t - 300, port=True)
    # vbn: switch-band M2 line to the right edge; vctrl: its DAC track to the right edge
    top.r("m2", vbnx, Y["vbnl"] - 190, gr + 300, Y["vbnl"] + 190)
    top.label("vbn", "m2", gr + 100, Y["vbnl"], port=True)
    vy, vxa, vxb = gd["tracks"]["vctrl"][0]
    top.r("m2", vxb - 400, vy - 190, gr + 300, vy + 190)
    top.label("vctrl", "m2", gr + 100, vy, port=True)
    bbox = (gl - 300, pin_b, gr + 300, pin_t)
    meta = dict(Y=Y, cx=cx, lens=lens, spans=spans, bbox=bbox, decap=dict(nf=nf, L=Ldc, W=Wdc, x1=dcx1, vdd_m3=dcvdd),
                dac=dict(x0=gd["x0"], x1=gd["x1"], top=gd["top"], rows=gd["rows"]), switches=gcs,
                sizes=dac_sizes(p), vgv=vgv, wfu=p["wfu"])
    return [iv, mirror_cell(iv, "ring_inv_m"), top], meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--out", default=str(REPO / "build" / "layout_v3"))
    ap.add_argument("--gds", default=str(REPO / "layout" / "ring_core_v3.gds"))
    ap.add_argument("--no-magic", action="store_true")
    a = ap.parse_args()
    p = params(a.set)
    cells, meta = build(p)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.mag"):
        old.unlink()
    tcl = "drc off\nsnap internal\n" + "".join(c.tcl() for c in cells)
    tcl += f"load ring_core\nselect top cell\nexpand\ngds write {Path(a.gds).resolve()}\nquit -noprompt\n"
    (out / "ring_core.tcl").write_text(tcl)
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
    bb = meta["bbox"]
    print(f"bbox {(bb[2]-bb[0])/1000:.2f} x {(bb[3]-bb[1])/1000:.2f} um = {(bb[2]-bb[0])*(bb[3]-bb[1])/1e6:.0f} um2")
    print("ring wire lengths (um, via to via):", {f"a{j}": l / 1000 for j, l in sorted(meta["lens"].items())})
    print("decap", meta["decap"], "dac", {k: v for k, v in meta["dac"].items() if k != "rows"}, "sizes", meta["sizes"])
    if not a.no_magic:
        rc = f"{os.environ.get('PDK_ROOT', '/foss/pdks')}/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc"
        r = subprocess.run(["magic", "-rcfile", rc, "-noconsole", "-dnull", "ring_core.tcl"], cwd=out,
                           capture_output=True, text=True)
        (out / "magic_gen.log").write_text(r.stdout + r.stderr)
        print("magic log:", out / "magic_gen.log")


if __name__ == "__main__":
    main()
