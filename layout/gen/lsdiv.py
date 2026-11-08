#!/usr/bin/env python3
"""Layout of the a0 level shifter + TSPC /4 + clock buffer ("lsdiv", gf180mcuD, 3.3 V devices).

    python3 layout/gen/lsdiv.py [--set ccl=1.6 ...] [--out build/layout_lsdiv] [--gds layout/lsdiv.gds]

Circuit: sim/lsdiv/lsdiv.py block() (= xschem/lsdiv.sch): Cc a0 -> lg (metal fingers, no device), LRB pfet
0.22/2 lg <- lf (gate VSS), INV1 0.22/0.5, INV2 0.6/1.5, INV3 1.2/3.0 -> ls, R1 hires poly 1 x 159.125 um ls -> lf
(serpentine), C1 nfet 16 x 16 gate cap on lf; TSPC toggle flops D1 (clk ls, 1.0/2.0) and D2 (clk q1, 0.6/1.2),
each 9 FETs + a 0.6/1.5 Q inverter; buffer B1 1.0/2.5 q2 -> ck. All L 0.28 unless stated.

Floorplan (x left to right, y bottom to top; same y origin as layout/ring_core_v3.gds):
  logic band: VSS rail (M1+M2, p+ tap strip under it) | N row (top-aligned) | routing channel (M2 tracks, one net per
              track interval; every terminal is an M1 stub + via1 onto its track) | P row (bottom-aligned, n-well) |
              VDD rail (M1+M2, n+ well tap strip under it).
              columns: B1 | D2 | D1 | INV3 | INV2 | INV1 | LRB | Cc, with Cc at the right edge.
  passive band (above the VDD rail): R1 serpentine (ls terminal left, lf right) | C1, then a second VSS rail
              (p+ tap strip under it), joined to the bottom one by an M3 strap at the left edge.
  ls and lf reach the passive band on M3 (over the P row and the VDD rail).
Cc: interdigitated M2 and M3 fingers (0.3 / 0.3 um), the a0 and lg fingers alternate on each layer and swap between
    layers (each a0 finger has lg on its sides and above / below). a0 spine at the right edge, lg spine on its left,
    which is where the lg track ends.
Pins: VDD, VSS (M2 rails), a0 (M2, right edge, y = 4.715 um = the core's a0 tap), ck (M2, left edge). No Metal4/5.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ring_core import Cell, CO, CO_POLY, ENC_CO, POLY_DIFF, ENDCAP, TPITCH  # noqa: E402

REPO = HERE.parents[1]
A0_Y = 4715          # a0 pin centre in lsdiv coordinates. NB the core's a0 tap is at y = 36170 (ring_core_v3 rows[0]):
                     # place lsdiv at dy = +31455 (or mirrored) at the top level so the two meet

# sizes (um) = sim/lsdiv/lsdiv.py S
S = dict(wn1=0.22, wp1=0.5, wr=0.22, lr=2.0, wn2=0.6, wp2=1.5, wn3=1.2, wp3=3.0,
         t1n=1.0, t1p=2.0, t2n=0.6, t2p=1.2, qn=0.6, qp=1.5, bn=1.0, bp=2.5,
         r1w=1.0, r1l=159.125, c1w=16.0, c1l=16.0,
         ccn=9, ccl=1.15)       # Cc: fingers per layer, finger overlap length (um)
L0 = 280
STUB = 1000          # S/D region width for a region with a channel stub
INNER = 560          # S/D region between gates, no stub
DGAP = 600           # same-type diffusion gap
MSP = 610            # min centre distance of two different-net 380 M1 stubs (380 + 230)
WIDE = {"lo1": 2200}  # INV1 output region: its stubs ~1.2 um from the lg gate stubs (Miller C on lg)
RPITCH = 1700        # R1 strip pitch (1.0 strip + 0.7 space: SB.2 needs 0.42 between the grown SAB)


def snap(v):
    return int(round(v / 5.0)) * 5


def um(v):
    return snap(v * 1000)


# ---- devices ---------------------------------------------------------------------------------------------
def tspc(n, clk, q, wn, wp):
    """TSPC toggle flop (lsdiv.py tspc()) as diffusion strips: [region, (L, gate), region, ...]."""
    x, y, qb = f"{n}x", f"{n}y", f"{n}qb"
    P = [(wp_, seq) for wp_, seq in (
        (S["qp"], [q, qb, "VDD"]),                                           # Q inverter P
        (wp, ["VDD", y, qb]),                                                # p4
        (wp, [y, clk, "VDD", qb, f"{n}n1", clk, x]))]                        # p3 | p1 p2
    N = [(S["qn"], [q, qb, "VSS"]),                                          # Q inverter N
         (wn, ["VSS", y, f"{n}n3", clk, qb]),                                # n5 n4
         (wn, [y, x, f"{n}n2", clk, "VSS", qb, x])]                          # n2 n3 | n1
    return P, N


def inv(i, o, wn, wp, l=0.28):
    return [(wp, ["VDD", i, o], l)], [(wn, ["VSS", i, o], l)]


def columns():
    cols = []
    cols.append(("B1",) + inv("q2", "ck", S["bn"], S["bp"]))
    cols.append(("D2",) + tspc("D2", "q1", "q2", S["t2n"], S["t2p"]))
    cols.append(("D1",) + tspc("D1", "ls", "q1", S["t1n"], S["t1p"]))
    cols.append(("INV3",) + inv("lo2", "ls", S["wn3"], S["wp3"]))
    cols.append(("INV2",) + inv("lo1", "lo2", S["wn2"], S["wp2"]))
    # INV1 flipped (output on the left, away from the lg track / Cc): less lg-lo1 (Miller) coupling
    cols.append(("INV1", [(S["wp1"], ["lo1", "lg", "VDD"], 0.28)], [(S["wn1"], ["lo1", "lg", "VSS"], 0.28)]))
    cols.append(("LRB", [(S["wr"], ["lg", "VSS", "lf"], S["lr"])], []))
    out = []
    for name, P, N in cols:
        norm = lambda lst: [(d + (0.28,)) if len(d) == 2 else d for d in lst]
        out.append((name, norm(P), norm(N)))
    return out


# ---- one diffusion strip ----------------------------------------------------------------------------------
def strip(c, x0, ybot, W, seq, L, typ, chan):
    """Draw regions/gates of seq on one diffusion; pads on the channel side (N: top, P: bottom).
    Returns (x1, terminals) with terminals = [(net, x, y_edge_on_channel_side, kind)]."""
    diff, cont = ("ndiff", "ndc") if typ == "n" else ("pdiff", "pdc")
    dog = W < 2 * ENC_CO + CO
    regs, gates = seq[0::2], seq[1::2]
    n = len(gates)

    def rw(i):
        net = regs[i]
        end = i in (0, n)
        if net in chan:
            return WIDE.get(net, STUB)
        if dog:
            return POLY_DIFF + 380 + (0 if end else POLY_DIFF)
        return (CO_POLY + CO + ENC_CO) if end else INNER
    x = x0
    rx, gx = [], []
    for i in range(n + 1):
        w = rw(i)
        # contact centre: middle of a stub/inner region; ends without a stub sit CO_POLY + CO/2 from the gate
        if regs[i] in chan or (0 < i < n):
            cx = x + w // 2
        elif i == 0:
            cx = x + w - ((POLY_DIFF + 190) if dog else (CO_POLY + CO // 2))
        else:
            cx = x + ((POLY_DIFF + 190) if dog else (CO_POLY + CO // 2))
        rx.append(snap(cx))
        x += w
        if i < n:
            gx.append((x, x + L))
            x += L
    x1 = x
    c.r(diff, x0, ybot, x1, ybot + W)
    ym = ybot + W // 2
    if dog:
        rb, rt = ym - 190, ym + 190
        for cx in rx:
            c.r(diff, cx - 190, rb, cx + 190, rt)
    else:
        rb, rt = ybot, ybot + W
    cb, ct = rb + ENC_CO, rt - ENC_CO
    terms = []
    for cx, net in zip(rx, regs):
        c.r(cont, cx - CO // 2, cb, cx + CO // 2, ct)
        c.r("m1", cx - 190, cb - 75, cx + 190, ct + 75)
        terms.append((net, cx, (ct + 75) if typ == "n" else (cb - 75), "sd"))
    for (a, b), net in zip(gx, gates):
        gc = (a + b) // 2
        if typ == "n":
            pb = rt + 260
            c.r("poly", a, ybot - ENDCAP, b, pb + 370)
            c.r("poly", min(a, gc - 185), pb, max(b, gc + 185), pb + 370)
            c.r("pc", gc - 115, pb + 70, gc + 115, pb + 300)
            c.r("m1", gc - 190, pb - 5, gc + 190, pb + 375)
            terms.append((net, gc, pb + 375, "g"))
        else:
            pt = rb - 260
            c.r("poly", a, pt - 370, b, ybot + W + ENDCAP)
            c.r("poly", min(a, gc - 185), pt - 370, max(b, gc + 185), pt)
            c.r("pc", gc - 115, pt - 300, gc + 115, pt - 70)
            c.r("m1", gc - 190, pt - 375, gc + 190, pt + 5)
            terms.append((net, gc, pt - 375, "g"))
    return x1, terms, dict(rb=rb, rt=rt, cb=cb, ct=ct)


# ---- channel router: one M2 track per net interval, stub-order constraints ---------------------------------
def assign_tracks(stubs, extra):
    """stubs: [(net, x, side)] side 'N' (stub goes up to its track) / 'P' (down). extra: {net: [x]} track points.
    Different-net N and P stubs closer than MSP in x need track(N net) < track(P net). Returns {net: k}."""
    span = {}
    for net, x, _ in stubs:
        a, b = span.get(net, (x, x))
        span[net] = (min(a, x), max(b, x))
    for net, xs in extra.items():
        for x in xs:
            a, b = span.get(net, (x, x))
            span[net] = (min(a, x), max(b, x))
    nets = sorted(span, key=lambda n: span[n][0])
    pred = {n: set() for n in nets}
    for na, xa, sa in stubs:
        for nb, xb, sb in stubs:
            if na != nb and abs(xa - xb) < MSP:
                if sa == sb:
                    raise SystemExit(f"same-side stub clash {na}@{xa} {nb}@{xb}")
                if sa == "N":
                    pred[nb].add(na)
    order, done = [], set()
    while len(order) < len(nets):
        ready = [n for n in nets if n not in done and pred[n] <= done]
        if not ready:
            raise SystemExit(f"track order cycle among {[n for n in nets if n not in done]}")
        order.append(ready[0])
        done.add(ready[0])
    trk, used = {}, {}
    for n in order:
        k = max([trk[p] + 1 for p in pred[n]] + [0])
        a, b = span[n]
        while any(not (b + 190 + 300 <= a2 - 190 or a - 190 - 300 >= b2 + 190) for a2, b2 in used.get(k, [])):
            k += 1
        trk[n] = k
        used.setdefault(k, []).append((a, b))
    return trk, span


def build(sets=()):
    for kv in sets:
        k, v = kv.split("=")
        S[k] = type(S[k])(float(v))
    c = Cell("lsdiv")
    cols = columns()
    # channel nets: every net except rails and nets that live on one diffusion only (stack midpoints)
    cnt = {}
    for _, P, N in cols:
        for W, seq, L in P + N:
            for net in seq:
                cnt[net] = cnt.get(net, 0) + 1
    chan = {n for n in cnt if n not in ("VDD", "VSS") and not n.endswith(("n1", "n2", "n3"))}
    chan.discard("VSS")

    # ---- vertical plan (logic band) ----
    Y = dict(vss_b=-2400, vss_t=0)
    wnmax = max(um(W) for _, _, N in cols for W, _, _ in N)
    Y["n_top"] = 600 + wnmax
    # placement: columns left to right; the P strips of a column may be shifted right (offs) so that no N stub and
    # P stub of two nets sit at the same x in both orders (a track-order cycle). Greedy search, column by column.
    def placement(offs):
        x = 900
        place = []
        for (name, P, N), off in zip(cols, offs):
            xp, xn = x + off, x
            cp, cn = [], []
            for W, seq, L in P:
                cp.append(xp)
                xp = strip(Cell("tmp"), xp, 0, um(W), seq, um(L), "p", chan)[0] + DGAP
            for W, seq, L in N:
                cn.append(xn)
                xn = strip(Cell("tmp"), xn, 0, um(W), seq, um(L), "n", chan)[0] + DGAP
            place.append((name, P, N, cp, cn))
            x = max(xp, xn) + 200
        return place, x

    def draw(c, p_bot, place):
        terms = []
        for name, P, N, cp, cn in place:
            for (W, seq, L), x0 in zip(P, cp):
                w = um(W)
                _, t, g = strip(c, x0, p_bot, w, seq, um(L), "p", chan)
                terms += [(net, xx, yy, k, "P", g) for (net, xx, yy, k) in t]
            for (W, seq, L), x0 in zip(N, cn):
                w = um(W)
                _, t, g = strip(c, x0, Y["n_top"] - w, w, seq, um(L), "n", chan)
                terms += [(net, xx, yy, k, "N", g) for (net, xx, yy, k) in t]
        return terms

    # per column: the P offset and strip orders with no track-order cycle and the least total track length
    # (+ half the offset: width), so the dynamic TSPC nodes carry as little wire as possible
    import itertools
    offs = []
    for i in range(len(cols)):
        name, P, N = cols[i]
        best = None
        for off in range(0, 3001, 200):
            for pp in itertools.permutations(P):
                for nn in itertools.permutations(N):
                    cols_bak = cols[:]
                    cols[i] = (name, list(pp), list(nn))
                    pl, _ = placement(offs + [off] + [0] * (len(cols) - i - 1))
                    cols[:] = cols_bak
                    t = draw(Cell("tmp"), 20000, pl[:i + 1])
                    try:
                        _, span = assign_tracks([(n, xx, sd) for (n, xx, yy, k, sd, g) in t if n in chan], {})
                    except SystemExit:
                        continue
                    cost = sum(b2 - a2 for a2, b2 in span.values()) + off // 2
                    if best is None or cost < best[0]:
                        best = (cost, off, list(pp), list(nn))
        if not best:
            raise SystemExit(f"no P offset / strip order for column {name}")
        offs.append(best[1])
        cols[i] = (name, best[2], best[3])
    place, xlogic = placement(offs)
    terms = draw(Cell("tmp"), 20000, place)
    npad = max(yy for (net, xx, yy, k, side, g) in terms if side == "N")
    Y["t0"] = snap(npad + 230 + 190 + 5)

    # ---- Cc geometry (x), lf / ls drop points ----
    nf, ccl = int(S["ccn"]), um(S["ccl"])
    W_bb = None
    lrb = [t for t in terms if t[0] == "lf" and t[3] == "sd"][0]
    lf_x = lrb[1]
    xc0 = xlogic + 400                     # lg spine left edge
    xa0 = xc0 + 380 + 300 + ccl            # a0 spine left edge
    W_bb = xa0 + 380 + 300                 # bbox right (a0 M2 stub runs to it)
    lg_spine = xc0 + 190
    # passive band x: R1's lf terminal (strip 9) right above the lf drop (LRB), so its ls terminal (strip 0) lands
    # near D1 / INV3 (short ls track); C1 to the left of R1
    c1w, c1l = um(S["c1w"]), um(S["c1l"])
    rx0 = lf_x - 500 - 9 * RPITCH
    c1_x1 = rx0 - 1000                    # HRES.5: 0.7 um to diffusion
    c1_x0 = c1_x1 - (2 * (CO_POLY + CO + ENC_CO) + c1l)
    assert c1_x0 >= 1500, c1_x0
    ls_x = rx0 + 500
    stubs = [(net, xx, side) for (net, xx, yy, k, side, g) in terms if net in chan]
    extra = {"lg": [lg_spine], "ls": [ls_x], "lf": [lf_x], "ck": [300]}
    trk, span = assign_tracks(stubs, extra)
    ntrk = max(trk.values()) + 1
    ty = {n: Y["t0"] + k * TPITCH for n, k in trk.items()}
    Y["p_bot"] = snap(Y["t0"] + (ntrk - 1) * TPITCH + 190 + 230 + 635 + 80)
    wpmax = max(um(W) for _, P, _ in cols for W, _, _ in P)
    Y["p_top"] = Y["p_bot"] + wpmax
    Y["vdd_b"] = Y["p_top"] + 600
    Y["vdd_t"] = Y["vdd_b"] + 2400
    terms = draw(c, Y["p_bot"], place)

    # ---- stubs and tracks ----
    vias = {}
    for (net, xx, yy, kind, side, g) in terms:
        if net in chan:
            t = ty[net]
            if side == "N":
                c.r("m1", xx - 190, yy - 5, xx + 190, t + 190)
            else:
                c.r("m1", xx - 190, t - 190, xx + 190, yy + 5)
            near = [v for v in vias.get(net, []) if abs(v - xx) < 520]
            if near:        # same-net stubs (N and P) almost on top of each other: one via, M1 bridge
                c.r("m1", min(near[0], xx) - 190, t - 190, max(near[0], xx) + 190, t + 190)
            else:
                c.via1(xx, t)
                vias.setdefault(net, []).append(xx)
        elif net == "VSS" and side == "N":
            c.r("m1", xx - 190, Y["vss_t"] - 300, xx + 190, g["cb"])
        elif net == "VDD" and side == "P":
            c.r("m1", xx - 190, g["ct"], xx + 190, Y["vdd_b"] + 300)
        elif net == "VSS" and side == "P" and kind == "g":       # LRB gate: straight down to the VSS rail
            assert not any(abs(t[1] - xx) < MSP for t in terms if t[4] == "N"), "LRB gate drop blocked"
            c.r("m1", xx - 190, Y["vss_t"] - 300, xx + 190, yy + 5)
    for net, k in trk.items():
        a, b = span[net]
        c.r("m2", a - 190, ty[net] - 190, b + 190, ty[net] + 190)
    for net in ("lg", "lf", "ls", "lo1", "lo2", "q1", "q2"):     # internal net names (not ports) for the extraction
        c.label(net, "m2", (span[net][0] + span[net][1]) // 10 * 5, ty[net])
    # ck pin: its track to the left edge
    c.r("m2", 0, ty["ck"] - 190, 300, ty["ck"] + 190)
    c.label("ck", "m2", 150, ty["ck"], port=True)

    # ---- Cc ----
    h = (nf - 1) * 600 + 300
    cy0 = snap(A0_Y - h / 2)
    cy0 = cy0 - (cy0 % 5)
    assert cy0 <= ty["lg"] - 190 and ty["lg"] + 190 <= cy0 + h, ("lg track outside the Cc spine", ty["lg"], cy0, h)
    for lay in ("m2", "m3"):
        c.r(lay, xc0, cy0, xc0 + 380, cy0 + h)
        c.r(lay, xa0, cy0, xa0 + 380, cy0 + h)
        for i in range(nf):
            y = cy0 + i * 600
            is_a0 = (i % 2 == 0) == (lay == "m2")
            if is_a0:
                c.r(lay, xc0 + 380 + 300, y, xa0, y + 300)
            else:
                c.r(lay, xc0 + 380, y, xa0 - 300, y + 300)
    for xs in (xc0 + 190, xa0 + 190):
        y = cy0 + 190
        while y + 190 <= cy0 + h:
            c.r("v2", xs - 140, y - 140, xs + 140, y + 140)
            y += 1200
    c.r("m2", xa0, A0_Y - 190, W_bb, A0_Y + 190)
    c.label("a0", "m2", W_bb - 100, A0_Y, port=True)

    # ---- wells, taps, rails (logic band) ----
    pxs = [x for (_, _, _, cp, _) in place for x in cp]
    nw_x0 = min(pxs) - 600
    nw_x1 = max(t[1] for t in terms if t[4] == "P") + 1100
    Y["nw_b"] = Y["p_bot"] - 80 - 450
    Y["tap_t"] = Y["vdd_b"] + 1010
    Y["nw_t"] = Y["tap_t"] + 380 + 150
    c.r("nwell", nw_x0, Y["nw_b"], nw_x1, Y["nw_t"])
    c.r("nsd", nw_x0 + 150, Y["tap_t"], nw_x1 - 150, Y["tap_t"] + 380)
    c.r("nsc", nw_x0 + 225, Y["tap_t"] + 75, nw_x1 - 225, Y["tap_t"] + 305)
    xl, xr = 300, W_bb - 300

    def rail(yb, yt, name, tap, label=True):
        c.r("m1", xl, yb, xr, yt)
        c.r("m2", xl, yb, xr, yt)
        x = xl + 400
        while x + 400 < xr:
            c.r("v1", x - 130, yb + 300, x + 130, yt - 300)
            x += 2000
        if tap:
            c.r("psd", xl, yb + 1010, xr, yb + 1390)
            c.r("psc", xl + 75, yb + 1085, xr - 75, yb + 1315)
        if label:
            c.label(name, "m2", xl + 1000, (yb + yt) // 2, port=True)
    rail(Y["vss_b"], Y["vss_t"], "VSS", True)
    rail(Y["vdd_b"], Y["vdd_t"], "VDD", False)

    # ---- passive band ----
    Y["pb0"] = Y["vdd_t"] + 900
    # C1: one 16 x 16 gate, S/D columns up to the top VSS rail, gate pads along the bottom (lf strap)
    c1_b = Y["pb0"] + 630
    gx0 = c1_x0 + CO_POLY + CO + ENC_CO
    gx1 = gx0 + c1l
    c.r("ndiff", c1_x0, c1_b, c1_x1, c1_b + c1w)
    c.r("poly", gx0, Y["pb0"], gx1, c1_b + c1w + ENDCAP)
    c1_cols = []
    for cx in (c1_x0 + CO_POLY // 2 + 190 - 75 + 0, c1_x1 - (CO_POLY // 2 + 190 - 75)):
        cx = snap(cx)
        c.r("ndc", cx - 115, c1_b + 70, cx + 115, c1_b + c1w - 70)
        c1_cols.append(cx)
    x = gx0 + 300
    while x + 300 <= gx1:
        c.r("pc", x, Y["pb0"] + 70, x + 230, Y["pb0"] + 300)
        x += 700
    Y["vss2_b"] = max(c1_b + c1w + 600, Y["pb0"] + 610 + 100 + um(S["r1l"]) // 5)  # provisional, fixed below
    Y["vss2_t"] = Y["vss2_b"] + 2400
    # R1 serpentine: 10 strips, ls terminal (strip 0) and lf terminal (strip 9) at the bottom
    # strips 1..8 are Ls long; the terminal strips 0 and 9 run ~2.5 um past the bottom bars so that their ends (where
    # the SAB steps) face nothing (SB.2). magic counts length = sum of strip rects + 9 * pitch (bars).
    ls_len = um(S["r1l"])
    nstr = 10
    Ls = snap((ls_len - (nstr - 1) * RPITCH - 5000) / nstr) // 10 * 10
    term = ls_len - 8 * Ls - 9 * RPITCH
    L0, L9 = term // 2 // 5 * 5, term - term // 2 // 5 * 5
    assert min(L0, L9) - Ls >= 2400, (L0, Ls)
    yb = Y["pb0"] + 610 + (L0 - Ls) + 100 + 700    # + 0.7 um: the lf M2 line runs under the R1 terminals
    yt = yb + Ls
    for i in range(nstr):
        xs = rx0 + i * RPITCH
        if i == 0:
            ya = yt - L0
        elif i == nstr - 1:
            ya = yt - L9
        else:
            ya = yb
        c.r("hires", xs, ya, xs + 1000, yt)
        if i < nstr - 1:
            if i % 2 == 0:
                c.r("hires", xs, yt, xs + RPITCH + 1000, yt + 1000)
            else:
                c.r("hires", xs, yb - 1000, xs + RPITCH + 1000, yb)
        if i in (0, nstr - 1):
            c.r("poly", xs, ya - 610, xs + 1000, ya)
            c.r("pc", xs + 65, ya - 545, xs + 935, ya - 315)
            c.r("m1", xs, ya - 610, xs + 1000, ya - 250)
            if i == 0:
                r_ls = (xs + 500, ya - 430)
            else:
                r_lf = (xs + 500, ya - 430)
    Y["vss2_b"] = max(c1_b + c1w + 600, yt + 1000 + 700 - 1010 + 100)    # R1 top bar 0.7 um from the p+ tap
    Y["vss2_t"] = Y["vss2_b"] + 2400
    for cx in c1_cols:                                                      # C1 S/D columns up into the rail
        c.r("m1", cx - 190, c1_b, cx + 190, Y["vss2_b"] + 300)
    # lf: C1 gate pads (M1 strap) -> via1 -> M2 line under R1 -> lf_x; R1 lf terminal (via12) and the lf track (via2)
    # on one M3 vertical at lf_x
    sy = Y["pb0"] + 185
    c.r("m1", gx0, Y["pb0"], gx1, Y["pb0"] + 370)
    c.via1(gx1 - 300, sy)
    c.r("m2", gx1 - 490, sy - 190, lf_x + 190, sy + 190)
    assert r_lf[0] == lf_x and r_ls[1] - 190 >= sy + 190 + 300
    c.via2(lf_x, sy)
    c.via12(lf_x, r_lf[1])
    c.r("m3", lf_x - 190, ty["lf"] - 190, lf_x + 190, r_lf[1] + 190)
    c.via2(lf_x, ty["lf"])
    # ls: R1 ls terminal -> via12 + M3 down to the ls track
    c.via12(ls_x, r_ls[1])
    c.r("m3", ls_x - 190, ty["ls"] - 190, ls_x + 190, r_ls[1] + 190)
    c.via2(ls_x, ty["ls"])
    rail(Y["vss2_b"], Y["vss2_t"], "VSS", True, label=False)
    # VSS rails joined by an M3 strap at the left edge
    sx0, sx1 = xl, xl + 1000
    c.r("m3", sx0, Y["vss_b"], sx1, Y["vss2_t"])
    for yy in (Y["vss_b"] + 600, Y["vss_b"] + 1800, Y["vss2_b"] + 600, Y["vss2_b"] + 1800):
        for xx in (sx0 + 200, sx0 + 800):
            c.r("v2", xx - 140, yy - 140, xx + 140, yy + 140)
    bbox = (0, Y["vss_b"] - 300, W_bb, Y["vss2_t"] + 300)
    meta = dict(Y=Y, bbox=bbox, tracks={n: [k, ty[n], span[n]] for n, k in trk.items()}, ntrk=ntrk,
                cc=dict(nf=nf, ccl=ccl, xc0=xc0, xa0=xa0, cy0=cy0, h=h), r1=dict(x0=rx0, L0=L0, L9=L9, Ls=Ls),
                c1=dict(x0=c1_x0, x1=c1_x1), lf_x=lf_x, ls_x=ls_x, S=S)
    return [c], meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--out", default=str(REPO / "build" / "layout_lsdiv"))
    ap.add_argument("--gds", default=str(REPO / "layout" / "lsdiv.gds"))
    ap.add_argument("--no-magic", action="store_true")
    a = ap.parse_args()
    cells, meta = build(a.set)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.mag"):
        old.unlink()
    tcl = "drc off\nsnap internal\n" + "".join(c.tcl() for c in cells)
    tcl += f"load lsdiv\nselect top cell\nexpand\ngds write {Path(a.gds).resolve()}\nquit -noprompt\n"
    (out / "lsdiv.tcl").write_text(tcl)
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
    bb = meta["bbox"]
    print(f"bbox {(bb[2]-bb[0])/1000:.2f} x {(bb[3]-bb[1])/1000:.2f} um = {(bb[2]-bb[0])*(bb[3]-bb[1])/1e6:.0f} um2,"
          f" x {bb[0]/1000}..{bb[2]/1000}, y {bb[1]/1000}..{bb[3]/1000}; a0 at y {A0_Y/1000} um; {meta['ntrk']} tracks")
    if not a.no_magic:
        rc = f"{os.environ.get('PDK_ROOT', '/foss/pdks')}/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc"
        r = subprocess.run(["magic", "-rcfile", rc, "-noconsole", "-dnull", "lsdiv.tcl"], cwd=out,
                           capture_output=True, text=True)
        (out / "magic_gen.log").write_text(r.stdout + r.stderr)
        print("magic log:", out / "magic_gen.log")


if __name__ == "__main__":
    main()
