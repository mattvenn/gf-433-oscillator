#!/usr/bin/env python3
"""Compact ring-core layout (v2): same circuit, pins and LVS source as ring_core.py, short ring-node wires.

    python3 layout/gen/ring_core_v2.py [--set k=v ...] [--out build/layout_v2] [--gds layout/ring_core_v2.gds]

The principle: ring nodes a0..a4 short, bias-side wiring (f0..f4, vbn, g0..g4, vctrl, vbp, VDD/VSS) as long as needed.

Floorplan (x left to right, y bottom to top):
  feet row     : 5 stage feet (ring_foot, the same 7-row finger blocks as v1) | master leg | coarse switches.
                 The M3 bias tracks (vbn, g4..g0, vctrl) run across all of them as in v1.
  f channel    : 5 M2 tracks f0..f4 just above the feet. Each foot's f spine (M1) rises to its track, the track
                 runs to the stage's inverter in the cluster, and an M1 drop reaches the NMOS source.
  inverter cluster (centred over the stage feet), 5 x ring_inv at 2.6 um pitch, loop order 0,4,1,3,2:
                 N (2/0.28) | gap: input poly contacts, n-well tap strip, 3 short M2 ring rows | P (5/0.28) |
                 head H (6/1, its own diffusion above P, h joined by a straight M1 line) | vbp M3 track | VDD rail.
                 Every a_i -> a_i+1 hop spans <= 2 inverter pitches (<= 5.6 um of M2). No padding, no shields.
  n-wells      : one around the cluster's P+H (tap ring), one around MPB + switch TP (tap ring).
  p+ substrate tap ring around everything. Metal4 unused.
Device drawing (fet_row, foot, master, switches) is imported unchanged from ring_core.py.
"""
import argparse, itertools, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ring_core as v1  # noqa: E402
from ring_core import (Cell, fet_row, draw_foot, master_cell, switch_cell, g5, vco_bias,  # noqa: E402
                       CO, CO_POLY, ENC_CO, NW_ENC_P, NW_ENC_NSD, NSD_PSD, TPITCH)

REPO = HERE.parents[1]
ORDER = [0, 4, 1, 3, 2]   # stage at cluster column 0..4 (folded loop)
MIRROR = [-1, 1, -1, -1, -1]   # per cluster column: +1 input riser right of the gate, -1 mirrored (left)
# gate-centre pitch between neighbouring columns by orientation pair: same 2.6 um; (+1,-1) the two input
# risers face each other 2.9 um; (-1,+1) the two heads face each other 3.0 um
IPITCH = {(1, 1): 2600, (-1, -1): 2600, (1, -1): 2900, (-1, 1): 3000}
XIN = 1100                # input riser offset from the gate centre (output riser is on the drain side)
RROW = 1000               # ring M2 row pitch in the N-P gap
HGAP = 800                # P top to H bottom (poly end caps + spacing)


def plan(p):
    um = lambda v: g5(v * 1000)
    tmp = Cell("tmp")
    f = draw_foot(tmp, p)
    Y = {"foot_top": f["top"]}
    Y["fch"] = [f["top"] + 490 + i * TPITCH for i in range(p["n"])]       # f channel M2 tracks
    Y["n_bot"] = Y["fch"][-1] + 190 + 400
    Y["n_top"] = Y["n_bot"] + um(p["wn"])
    Y["pcl"] = Y["n_top"] + 445
    Y["tap_b"] = Y["n_top"] + 730                                         # n-well tap strip bottom (in the gap)
    Y["nw_b"] = Y["tap_b"] - NW_ENC_NSD
    Y["p_bot"] = Y["tap_b"] + 1280
    Y["pch"] = Y["p_bot"] - 445
    Y["p_top"] = Y["p_bot"] + max(um(p["wp"]), um(p["wpb"]), 5000)
    Y["h_bot"] = Y["p_top"] + HGAP
    Y["vbp"] = Y["h_bot"] + um(p["whead"]) + 445
    Y["vdd_b"] = Y["vbp"] + 190 + 300
    Y["vdd_t"] = Y["vdd_b"] + 2400
    Y["tap_t"] = Y["vdd_b"] + 1010
    Y["nw_t"] = Y["tap_t"] + 380 + NW_ENC_NSD
    Y["vss_t"] = -300
    Y["vss_b"] = Y["vss_t"] - 2400
    mid = g5((Y["pcl"] + Y["pch"]) // 2 // 5 * 5)
    Y["rows"] = [mid, mid - RROW, mid + RROW]                              # ring M2 rows, preferred first
    return Y


def inv_cell(p, Y):
    """One inverter pair + its head. Origin: N/P diffusion left edge at x=0."""
    um = lambda v: g5(v * 1000)
    c = Cell("ring_inv")
    Ln, wn, wp, wh, Lh = um(p["L"]), um(p["wn"]), um(p["wp"]), um(p["whead"]), um(p["ls"])
    n = fet_row(c, 0, Y["n_bot"], wn, [(Ln, "in")], "n")
    gx0, gx1 = n["gx"][0]
    gc = (gx0 + gx1) // 2
    xin, xout, xs = gc + XIN, n["rx"][0], n["rx"][1]
    pb = Y["pcl"] - 185                                    # N input pc above N
    c.r("poly", gx0, n["ybot"] + wn, gx1, pb + 370)
    c.r("poly", gx0, pb, xin + 185, pb + 370)
    c.r("pc", xin - 115, pb + 70, xin + 115, pb + 300)
    pr = fet_row(c, 0, Y["p_bot"], wp, [(Ln, "in")], "p")
    assert pr["gx"][0] == n["gx"][0] and pr["rx"][1] == xs
    pt = Y["pch"] + 185                                    # P input pc below P
    c.r("poly", gx0, pt - 370, gx1, pr["ybot"])
    c.r("poly", gx0, pt - 370, xin + 185, pt)
    c.r("pc", xin - 115, pt - 300, xin + 115, pt - 70)
    c.r("m1", xin - 190, Y["pcl"] - 190, xin + 190, Y["pch"] + 190)      # input riser (extended at top level)
    c.r("m1", xout - 190, n["cb"] - 75, xout + 190, pr["ct"] + 75)        # output riser N drain -> P drain
    # head above P: regions [VDD | g | h], h region straight above P's source
    endw = CO_POLY + CO + ENC_CO
    hx0 = xs - (endw + Lh + CO_POLY + CO // 2)
    h = fet_row(c, hx0, Y["h_bot"], wh, [(Lh, "vbp")], "p", pc="top")
    assert h["rx"][1] == xs, (h["rx"], xs)
    c.r("m1", xs - 190, pr["ct"], xs + 190, h["cb"])                      # h: P source -> H drain
    c.r("m1", h["rx"][0] - 190, h["ct"], h["rx"][0] + 190, Y["vdd_b"] + 400)   # H source -> VDD rail
    hpc = h["pcs"][0]
    assert hpc[1] == Y["vbp"], (hpc, Y["vbp"])
    c.via12(hpc[0], hpc[1])
    # all x relative to the gate centre gc
    return c, dict(gc=gc, xin=xin - gc, xout=xout - gc, xs=xs - gc, hx=hpc[0] - gc, dl=hx0 - gc,
                   dr=max(pr["x1"], h["x1"]) - gc, mr=xin + 190 - gc)


def mirror_cell(c, name):
    """x -> -x copy of a flat cell (no instances, no labels)."""
    m = Cell(name)
    assert not c.insts and not c.labels
    for (l, x1, y1, x2, y2) in c.rects:
        m.r(l, -x2, y1, -x1, y2)
    return m


def tap_ring(top, xl, xr, Y, cross_m1, contacts_bottom=True):
    """n-well [xl, xr] x [nw_b, nw_t] with an nsd tap ring inside; M1 on the top/left/right sides,
    bottom-side contacts (with M1) only in pieces clear of the M1 lines in cross_m1."""
    e = NW_ENC_NSD
    top.r("nwell", xl, Y["nw_b"], xr, Y["nw_t"])
    tb, tt = Y["tap_b"], Y["tap_t"]
    top.r("nsd", xl + e, tb, xr - e, tb + 380)
    top.r("nsd", xl + e, tt, xr - e, tt + 380)
    top.r("nsd", xl + e, tb, xl + e + 380, tt + 380)
    top.r("nsd", xr - e - 380, tb, xr - e, tt + 380)
    top.r("nsc", xl + e + 75, tt + 75, xr - e - 75, tt + 305)
    for xa in (xl + e, xr - e - 380):
        top.r("nsc", xa + 75, tb + 75, xa + 305, tt + 305)
        top.r("m1", xa - 5, tb - 5, xa + 385, Y["vdd_t"])
    if not contacts_bottom:
        return
    xa = xl + e
    for xc in sorted(cross_m1) + [xr - e - 380]:
        xb = xc - 190 - 240 if xc != xr - e - 380 else xr - e
        if xb - xa >= 800:
            top.r("m1", xa, tb - 5, xb, tb + 385)
            top.r("nsc", xa + 75, tb + 75, xb - 75, tb + 305)
        xa = xc + 190 + 240


def build(p):
    Y = plan(p)
    foot = Cell("ring_foot")
    fi = draw_foot(foot, p)
    iv, ii = inv_cell(p, Y)
    ms, mi = master_cell(p, Y)
    tracks = fi["tracks"]
    sw, wi = switch_cell(p, Y, tracks)
    top = Cell("ring_core")
    fpitch = g5(fi["x1"] + 1000)
    colx = [i * fpitch for i in range(5)]
    for i, s in enumerate(ORDER):                          # foot column i feeds the inverter at cluster column i
        top.inst("ring_foot", colx[i], 0, f"foot{s}")
    mx = 5 * fpitch
    top.inst("ring_master", mx, 0, "master")
    swx = g5(mx + mi["x1"] + 1000)
    top.inst("ring_sw", swx, 0, "sw")
    xr_core = swx + wi["x1"]
    for net, y in tracks:                                  # bias M3 tracks, as v1
        xe = swx + wi["vbnx"] + 190 if net == "vbn" else (None if net == "vctrl" else swx + wi["gline"][net] + 190)
        top.r("m3", 0, y - 190, xe if xe else xr_core, y + 190)

    # ---- f routing: foot spine (M1) up to its f track (M2), across, M1 drop to the NMOS source ----
    fspine = [colx[i] + fi["fx"] for i in range(5)]
    frt = fi["geos"][-1]["rt"]
    best = None
    rel = [0]
    for i in range(4):
        rel.append(rel[-1] + IPITCH[(MIRROR[i], MIRROR[i + 1])])
    centre = (colx[0] + colx[4] + fi["x1"]) // 2 - rel[-1] // 2
    for dx in range(0, 20000, 100):                        # cluster x offset and f-track order: no M1 clashes
        for sgn in (1, -1):
            cx0 = g5(centre + sgn * dx)
            cx = [cx0 + r for r in rel]                    # gate centres
            ns = [x + ii["xs"] * m for x, m in zip(cx, MIRROR)]
            for perm in itertools.permutations(range(5)):
                ok = True
                for i in range(5):
                    for j in range(5):
                        if i != j and abs(fspine[i] - ns[j]) < 380 + 300 and Y["fch"][perm[j]] < Y["fch"][perm[i]] + 400:
                            ok = False
                if ok:
                    best = (cx, perm)
                    break
            if best:
                break
        if best:
            break
    cx, perm = best
    ns = [x + ii["xs"] * m for x, m in zip(cx, MIRROR)]
    for i in range(5):
        s = ORDER[i]
        y = Y["fch"][perm[i]]
        xa, xb = fspine[i], ns[i]
        top.r("m1", xa - 190, frt, xa + 190, y + 190)
        top.via1(xa, y)
        top.r("m2", min(xa, xb) - 190, y - 190, max(xa, xb) + 190, y + 190)
        top.via1(xb, y)
        top.r("m1", xb - 190, y - 190, xb + 190, Y["n_bot"] + 300)
        top.label(f"f{s}", "m2", (xa + xb) // 20 * 10, y)
    for i, s in enumerate(ORDER):
        if MIRROR[i] > 0:
            top.inst("ring_inv", cx[i] - ii["gc"], 0, f"inv{s}")
        else:
            top.inst("ring_inv_m", cx[i] + ii["gc"], 0, f"inv{s}")

    # ---- ring nodes: driver output riser -> load input riser, on the first free M2 row ----
    col = {s: i for i, s in enumerate(ORDER)}
    rows = {k: [] for k in range(len(Y["rows"]))}
    lens, spans = {}, {}
    ivals = []
    for j in range(p["n"]):
        cd, cl = col[(j - 1) % p["n"]], col[j]
        xo = cx[cd] + ii["xout"] * MIRROR[cd]
        xi = cx[cl] + ii["xin"] * MIRROR[cl]
        ivals.append((min(xo, xi), max(xo, xi), j, xo, xi))
    for a, b, j, xo, xi in sorted(ivals, key=lambda t: -(t[1] - t[0])):   # longest first -> middle row
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
        lo, hi = min(ty, Y["pcl"]), max(ty, Y["pch"])                     # input riser reaches the row
        top.r("m1", xi - 190, lo - 190, xi + 190, hi + 190)
        lens[j] = b - a
        spans[j] = (a, b, ty)
        top.label(f"a{j}", "m2", (a + b) // 20 * 10, ty, port=True)

    # ---- vbp: cluster heads -> master ----
    hxs = [x + ii["hx"] * m for x, m in zip(cx, MIRROR)]
    top.r("m3", min(hxs) - 190, Y["vbp"] - 190, mx + mi["vbpx"] + 190, Y["vbp"] + 190)

    # ---- rails, wells, guard rings ----
    xl, xr = -1500, xr_core + 1500
    for (yb, yt, nm) in ((Y["vss_b"], Y["vss_t"], "VSS"), (Y["vdd_b"], Y["vdd_t"], "VDD")):
        top.r("m1", xl, yb, xr, yt)
        top.r("m2", xl, yb, xr, yt)
        x = xl + 400
        while x + 400 < xr:
            top.r("v1", x - 130, yb + 300, x + 130, yt - 300)
            x += 2000
        top.label(nm, "m2", xl + 1000, (yb + yt) // 2, port=True)
    # cluster well: P + H only. nsd ring 0.6 from the pdiff, the bottom strip crosses the gap without contacts
    ext = lambda i: sorted((cx[i] + ii["dl"] * MIRROR[i], cx[i] + ii["dr"] * MIRROR[i]))
    mext = lambda i: cx[i] + ii["mr"] * MIRROR[i]
    cl = min(ext(0)[0] - NSD_PSD, mext(0) - 300) - 380 - NW_ENC_NSD
    cr = max(ext(4)[1] + NSD_PSD, mext(4) + 300) + 380 + NW_ENC_NSD
    tap_ring(top, g5(cl // 5 * 5), g5(-(-cr // 5) * 5), Y, [], contacts_bottom=False)
    # master + switch well (v1 style, bottom contacts in pieces between the M1 crossings)
    bl = mx - NSD_PSD - 380 - NW_ENC_NSD
    tap_ring(top, bl, xr - 300, Y, [mx + mi["foot"]["fx"]])
    assert cr + 600 <= bl, ("wells too close", cr, bl)
    # p+ substrate ring
    gl, gr = xl - 1500, xr + 1500
    gb, gt = Y["vss_b"] + 1010, Y["nw_t"] + 1200
    for (a, b, c2, d) in ((gl, gb, gr, gb + 380), (gl, gt, gr, gt + 380), (gl, gb, gl + 380, gt + 380),
                          (gr - 380, gb, gr, gt + 380)):
        top.r("psd", a, b, c2, d)
        top.r("m1", a - 5, b - 5, c2 + 5, d + 5)
    top.r("psc", gl + 75, gb + 75, gr - 75, gb + 305)
    top.r("psc", gl + 75, gt + 75, gr - 75, gt + 305)
    top.r("psc", gl + 75, gb + 75, gl + 305, gt + 305)
    top.r("psc", gr - 305, gb + 75, gr - 75, gt + 305)
    top.r("m1", gl - 5, Y["vss_b"], xl, Y["vss_t"])
    top.r("m1", xr, Y["vss_b"], gr + 5, Y["vss_t"])
    # pins (as v1): bit/bitb M3 at the bottom, vctrl/vbn M3 at the right edge
    pin_y = Y["vss_b"] - 1600
    for nm, lx in wi["end"].items():
        x = swx + lx
        top.r("m3", x - 190, pin_y, x + 190, 380)
        top.label(nm, "m3", x, pin_y + 300, port=True)
    for net, y in tracks:
        if net == "vctrl":
            top.r("m3", xr_core, y - 190, gr + 300, y + 190)
            top.label("vctrl", "m3", gr + 100, y, port=True)
            break
    top.r("m3", swx + wi["vbnx"], wi["vbny"] - 190, gr + 300, wi["vbny"] + 190)
    top.label("vbn", "m3", gr + 100, wi["vbny"], port=True)
    bbox = (gl, pin_y, gr + 300, gt + 380)
    meta = dict(Y=Y, cx=cx, lens=lens, spans=spans, bbox=bbox, fperm=perm, fpitch=fpitch)
    return [foot, iv, mirror_cell(iv, "ring_inv_m"), ms, sw, top], meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--out", default=str(REPO / "build" / "layout_v2"))
    ap.add_argument("--gds", default=str(REPO / "layout" / "ring_core_v2.gds"))
    ap.add_argument("--no-magic", action="store_true")
    a = ap.parse_args()
    p = dict(vco_bias.P)
    p.update(rideal=0, lnw=4.5, lnp=100.0)
    for kv in a.set:
        k, v = kv.split("=")
        p[k] = type(vco_bias.P[k])(float(v))
    p["_mutate"], p["_rows"] = None, 7
    cells, meta = build(p)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.mag"):
        old.unlink()
    tcl = "drc off\nsnap internal\n" + "".join(c.tcl() for c in cells)
    tcl += f"load ring_core\nselect top cell\nexpand\ngds write {Path(a.gds).resolve()}\nquit -noprompt\n"
    (out / "ring_core.tcl").write_text(tcl)
    bb = meta["bbox"]
    print(f"bbox {(bb[2]-bb[0])/1000:.2f} x {(bb[3]-bb[1])/1000:.2f} um = {(bb[2]-bb[0])*(bb[3]-bb[1])/1e6:.0f} um2")
    print("ring wire lengths (um, via to via):", {f"a{j}": l / 1000 for j, l in sorted(meta["lens"].items())})
    print("cluster x:", meta["cx"], "f track order:", meta["fperm"])
    if not a.no_magic:
        rc = f"{os.environ.get('PDK_ROOT', '/foss/pdks')}/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc"
        r = subprocess.run(["magic", "-rcfile", rc, "-noconsole", "-dnull", "ring_core.tcl"], cwd=out,
                           capture_output=True, text=True)
        (out / "magic_gen.log").write_text(r.stdout + r.stderr)
        print("magic log:", out / "magic_gen.log")


if __name__ == "__main__":
    main()
