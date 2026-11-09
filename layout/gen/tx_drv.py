#!/usr/bin/env python3
"""Layout of the dipole TX driver tx_drv (gf180mcuD, 3.3 V devices): sim/tx/tx_drv.py block() = xschem/tx_drv.sch.

    python3 layout/gen/tx_drv.py [--out build/layout_tx_drv] [--gds layout/tx_drv.gds] [--no-magic]

Floorplan (x left to right, y bottom to top), one flat cell, one logic band over the decap:
  logic band (layout/gen/lsdiv.py's style; its strip() and channel router are reused): VSS rail (M1+M2+M3, p+ tap
    strip under it) | N row (top-aligned) | channel (M2 tracks; every terminal is an M1 stub + via1 onto its track) |
    P row (bottom-aligned, n-well) | VDD rail (M1+M2+M3, n+ tap strip under it).
    columns: M5n | M4n M3n M2n M1n NANDn (mirrored) | T A1 A2 B1 TG XB XA | NANDp M1p M2p M3p M4p | M5p
  M5 (5 fingers, N 8 / P 20 um), drawn as a textbook inverter: one poly gate per finger runs from the N row across
    the channel to the P row; a poly bar on the y4 track joins them, contacted at its inner end. Drains: 1 um M1 straps
    from the N row across the channel to the P row, joined by a 2 um M2 + M3 out bar (a reserved slot above the
    tracks) that runs to the out pin at the block edge (out_n left, out_p right). Sources: 1 um M1 straps to the
    rails. EM: sized for the measured stage-5 currents (sim/tx/results/block_sch.txt, worst ff / rroute 15: 7.3 mA
    |avg|, 10.3 mA rms per arm) at the GF180MCU 85 C line limit (2.09 mA/um, Metal1..Metal5) and 0.58 mA per via.
  TG gates: the N gate (VDD) and the P gate (VSS) go on their own tracks (tgh, tgl), then M3 to the VDD / VSS rail.
  decap band: DC, nfet gate caps (gate VDD, S/D/B VSS) in row pairs; the two rows of a pair share continuous poly
    gates and a VDD poly-contact strap between them, joined to the VDD rail by M3 verticals.
Pins: VDD, VSS (rails, M2), ls, en_p, en_n (M3, top edge), out_p (right edge), out_n (left edge) (M2 + M3).
No Metal4/5: the rails carry M3 (via2 arrays) for the VDPWR Metal4 stripe at the top level.
"""
import argparse
import importlib.util
import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from ring_core import Cell, CO, ENC_CO, ENDCAP, TPITCH  # noqa: E402
import lsdiv as LL  # noqa: E402  (layout/gen/lsdiv.py: strip(), assign_tracks(), the rules it uses)

_spec = importlib.util.spec_from_file_location('sim_tx_drv', REPO / 'sim' / 'tx' / 'tx_drv.py')
TX = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(TX)

snap, um = LL.snap, LL.um
DGAP = LL.DGAP
RAIL = 2400
OUT_H = 2000                                   # out bar height (M2 + M3)
RW5 = 1200                                     # M5 S/D region width (1 um M1 strap on it)


def S():
    return dict(TX.S)


# ---- the circuit as columns of diffusion strips (lsdiv format: (W um, [reg, gate, reg, ...], L um)) ---------
def inv(i, o, wn, s):
    nf = TX.nfing(wn, s)
    wp, wnn = wn * s['kp'] / nf, wn / nf
    sp, sn = ['VDD'], ['VSS']
    for k in range(nf):
        sp += [i, o if k % 2 == 0 else 'VDD']
        sn += [i, o if k % 2 == 0 else 'VSS']
    return [(wp, sp, TX.L)], [(wnn, sn, TX.L)]


def arm_cols(side, s):
    """Arm columns NAND, M1..M4 (M5 is custom), input side first. Nets: in = a / b, en = en_p / en_n,
    internal <side>y0 .. y4, <side>ns."""
    i, e = ('a', 'en_p') if side == 'p' else ('b', 'en_n')
    y = [f'{side}y{k}' for k in range(5)]
    cols = [(f'NAND{side}', [(s['wnand_p'], ['VDD', i, y[0], e, 'VDD'], TX.L)],
             [(s['wnand_n'], [y[0], i, f'{side}ns', e, 'VSS'], TX.L)])]
    ws = TX.arm_widths(s)
    for k in range(4):
        P, N = inv(y[k], y[k + 1], ws[k], s)
        cols.append((f'M{k + 1}{side}', P, N))
    return cols


def mirror(cols):
    return [(nm, [(W, seq[::-1], L) for W, seq, L in P], [(W, seq[::-1], L) for W, seq, L in N])
            for nm, P, N in reversed(cols)]


def split_cols(s):
    cols = []
    for nm, i, o, w in (('T', 'ls', 't', s['wt']), ('A1', 't', 'ta', s['wa1']), ('A2', 'ta', 'a', s['wa2']),
                        ('B1', 't', 'tb', s['wb1'])):
        P, N = inv(i, o, w, s)
        cols.append((nm, P, N))
    cols.append(('TG', [(s['wtgp'], ['tb', 'tgl', 'b'], TX.L)], [(s['wtgn'], ['tb', 'tgh', 'b'], TX.L)]))
    for nm, i, o in (('XB', 'a', 'b'), ('XA', 'b', 'a')):
        P, N = inv(i, o, s['wx'], s)
        cols.append((nm, P, N))
    return cols


# ---- geometry helpers ------------------------------------------------------------------------------------------
def rail(c, yb, yt, x0, x1, tap=None, m3=True, skip=()):
    """M1 + M2 rail from x0 to x1 (via1 every 2 um); M3 on it with via2 every 2 um, except in the skip windows
    (x ranges where an M3 vertical crosses); a tap strip ('p' / 'n', x range) under it."""
    c.r('m1', x0, yb, x1, yt)
    c.r('m2', x0, yb, x1, yt)
    x = x0 + 400
    while x + 400 < x1:
        c.r('v1', x - 130, yb + 300, x + 130, yt - 300)
        x += 2000
    if m3:
        segs, a = [], x0
        for (s0, s1) in sorted(skip):
            if s0 > a:
                segs.append((a, s0))
            a = max(a, s1)
        if a < x1:
            segs.append((a, x1))
        for a, b in segs:
            if b - a < 1000:
                continue
            c.r('m3', a, yb, b, yt)
            x = a + 500
            while x + 500 <= b:
                c.r('v2', x - 140, yb + 300, x + 140, yt - 300)
                x += 2000
    if tap:
        kind, (a, b) = tap
        imp, cont = ('psd', 'psc') if kind == 'p' else ('nsd', 'nsc')
        c.r(imp, a, yb + 1010, b, yb + 1390)
        c.r(cont, a + 75, yb + 1085, b - 75, yb + 1315)


def m5_width(nf):
    return nf * (RW5 + um(TX.L)) + RW5


def draw_m5(c, Y, y_in, xd0, nf, wn, wp, out, x_edge, side):
    """Custom output inverter, diffusion from xd0: nf shared poly gates N -> P across the channel, a poly bar on the y4
    track contacted at the inner end (side 'R': left of the diffusion, 'L': right of it), 1 um M1 drain straps N -> P
    joined by the out bar (M2 + M3, Y out_b..out_t, via1 / via2 arrays) to x_edge, 1 um M1 source straps.
    Regions are counted from the inner end: even = source, odd = drain."""
    L = um(TX.L)
    xd1 = xd0 + m5_width(nf)
    nb, nt = Y['n_top'] - wn, Y['n_top']
    pb, pt = Y['p_bot'], Y['p_bot'] + wp
    c.r('ndiff', xd0, nb, xd1, nt)
    c.r('pdiff', xd0, pb, xd1, pt)
    gx = [xd0 + RW5 + k * (RW5 + L) for k in range(nf)]
    for a in gx:
        c.r('poly', a, nb - ENDCAP, a + L, pt + ENDCAP)
    xp = (xd0 - 600) if side == 'R' else (xd1 + 600)
    c.r('poly', min(xp - 185, gx[0]), y_in - 185, max(xp + 185, gx[-1] + L), y_in + 185)
    c.r('pc', xp - 115, y_in - 115, xp + 115, y_in + 115)
    c.via1(xp, y_in)
    outs = []
    for k in range(nf + 1):
        cx = xd0 + RW5 // 2 + k * (RW5 + L)
        kin = k if side == 'R' else nf - k
        for (b, t, cont) in ((nb, nt, 'ndc'), (pb, pt, 'pdc')):
            c.r(cont, cx - CO // 2, b + ENC_CO, cx + CO // 2, t - ENC_CO)
        if kin % 2 == 1:
            c.r('m1', cx - 500, nb + ENC_CO - 75, cx + 500, pt - ENC_CO + 75)
            outs.append(cx)
        else:
            c.r('m1', cx - 500, Y['vss_t'] - 300, cx + 500, nt - ENC_CO + 75)
            c.r('m1', cx - 500, pb + ENC_CO - 75, cx + 500, Y['vdd_b'] + 300)
    yb, yt = Y['out_b'], Y['out_t']
    xa, xb = (min(outs) - 500, x_edge) if side == 'R' else (x_edge, max(outs) + 500)
    c.r('m2', xa, yb, xb, yt)
    c.r('m3', xa, yb, xb, yt)
    for cx in outs:                                               # 2 x 3 via1 per drain strap
        for vx in (cx - 270, cx + 270):                           # V1.2a: 0.26 um cut spacing
            for vy in range(yb + 400, yt - 300, 600):
                c.r('v1', vx - 130, vy - 130, vx + 130, vy + 130)
    for vx in range(xa + 400, xb - 300, 600):                     # via2 array along the bar
        for vy in range(yb + 400, yt - 300, 600):
            c.r('v2', vx - 140, vy - 140, vx + 140, vy + 140)
    lx = xb - 400 if side == 'R' else xa + 400
    c.label(out, 'm3', lx, snap((yb + yt) / 2), port=True)
    return xd1, xp


# ---- the band ---------------------------------------------------------------------------------------------------
def build():
    s = S()
    c = Cell('tx_drv')
    nf5 = TX.nfing(TX.arm_widths(s)[4], s)
    wn5 = um(TX.arm_widths(s)[4] / nf5)
    wp5 = um(TX.arm_widths(s)[4] * s['kp'] / nf5)
    cols = mirror(arm_cols('n', s)) + split_cols(s) + arm_cols('p', s)
    cnt = {}
    for _, P, N in cols:
        for W, seq, L in P + N:
            for net in seq:
                cnt[net] = cnt.get(net, 0) + 1
    gates = {net for _, P, N in cols for W, seq, L in P + N for net in seq[1::2]}
    chan = {n for n in cnt if n not in ('VDD', 'VSS') and (cnt[n] > 1 or n in gates)} | {'ny4', 'py4'}
    Y = dict(vss_b=-RAIL, vss_t=0)
    wnmax = max([um(W) for _, _, N in cols for W, _, _ in N] + [wn5])
    Y['n_top'] = 600 + wnmax
    # x: out_n bar from x 0, M5n diffusion, its poly contact, then the columns
    xd5n = 2500
    x_col0 = xd5n + m5_width(nf5) + 600 + 190 + 700

    def placement(offs):
        x = x_col0
        place = []
        for (name, P, N), off in zip(cols, offs):
            xp, xn = x + off, x
            cp, cn = [], []
            for W, seq, L in P:
                cp.append(xp)
                xp = LL.strip(Cell('tmp'), xp, 0, um(W), seq, um(L), 'p', chan)[0] + DGAP
            for W, seq, L in N:
                cn.append(xn)
                xn = LL.strip(Cell('tmp'), xn, 0, um(W), seq, um(L), 'n', chan)[0] + DGAP
            place.append((name, P, N, cp, cn))
            x = max(xp, xn) + 200
        return place, x

    def draw(cc, p_bot, place):
        terms = []
        for name, P, N, cp, cn in place:
            for (W, seq, L), x0 in zip(P, cp):
                _, t, g = LL.strip(cc, x0, p_bot, um(W), seq, um(L), 'p', chan)
                terms += [(net, xx, yy, k, 'P', g) for (net, xx, yy, k) in t]
            for (W, seq, L), x0 in zip(N, cn):
                _, t, g = LL.strip(cc, x0, Y['n_top'] - um(W), um(W), seq, um(L), 'n', chan)
                terms += [(net, xx, yy, k, 'N', g) for (net, xx, yy, k) in t]
        return terms

    # per column: P offset and strip order with no track-order cycle and the least track length (lsdiv.py)
    offs = []
    for i in range(len(cols)):
        name, P, N = cols[i]
        best = None
        for off in range(0, 2001, 200):
            for pp in itertools.permutations(P):
                for nn in itertools.permutations(N):
                    bak = cols[:]
                    cols[i] = (name, list(pp), list(nn))
                    pl, _ = placement(offs + [off] + [0] * (len(cols) - i - 1))
                    cols[:] = bak
                    t = draw(Cell('tmp'), 20000, pl[:i + 1])
                    try:
                        _, span = LL.assign_tracks([(n, xx, sd) for (n, xx, yy, k, sd, g) in t if n in chan], {})
                    except SystemExit:
                        continue
                    cost = sum(b - a for a, b in span.values()) + off // 2
                    if best is None or cost < best[0]:
                        best = (cost, off, list(pp), list(nn))
        if not best:
            raise SystemExit(f'no P offset / strip order for column {name}')
        offs.append(best[1])
        cols[i] = (name, best[2], best[3])
    place, xlogic = placement(offs)
    terms = draw(Cell('tmp'), 20000, place)
    npad = max(yy for (net, xx, yy, k, side, g) in terms if side == 'N')
    Y['t0'] = snap(npad + 230 + 190 + 5)
    x_pc5n = xd5n + m5_width(nf5) + 600
    x_pc5p = xlogic + 600
    xd5p = x_pc5p + 600
    xr = xd5p + m5_width(nf5) + 2500
    # pins: just left of their first terminal; TG ties left of the keeper
    colx = {name: (min(cp + cn), max(cp + cn)) for name, P, N, cp, cn in place}
    xpin = dict(ls=colx['T'][0] - 500, en_n=colx['NANDn'][0] - 500, en_p=colx['NANDp'][0] - 500)
    xtie = dict(tgh=colx['XB'][0] - 300, tgl=colx['XB'][0] - 300 - 900)
    ext = {'ny4': [x_pc5n], 'py4': [x_pc5p]}
    for k, v in list(xpin.items()) + list(xtie.items()):
        ext.setdefault(k, []).append(v)
    stubs = [(net, xx, side) for (net, xx, yy, k, side, g) in terms if net in chan]
    trk, span = LL.assign_tracks(stubs, ext)
    ntrk = max(trk.values()) + 1
    ty = {n: Y['t0'] + k * TPITCH for n, k in trk.items()}
    Y['out_b'] = Y['t0'] + (ntrk - 1) * TPITCH + 190 + 400
    Y['out_t'] = Y['out_b'] + OUT_H
    Y['p_bot'] = snap(Y['out_t'] + 230 + 635 + 80)
    wpmax = max([um(W) for _, P, _ in cols for W, _, _ in P] + [wp5])
    Y['p_top'] = Y['p_bot'] + wpmax
    Y['vdd_b'] = Y['p_top'] + 600
    Y['vdd_t'] = Y['vdd_b'] + RAIL
    terms = draw(c, Y['p_bot'], place)

    # stubs and tracks (lsdiv.py)
    vias = {}
    for (net, xx, yy, kind, side, g) in terms:
        if net in chan:
            t = ty[net]
            if side == 'N':
                c.r('m1', xx - 190, yy - 5, xx + 190, t + 190)
            else:
                c.r('m1', xx - 190, t - 190, xx + 190, yy + 5)
            near = [v for v in vias.get(net, []) if abs(v - xx) < 520]
            if near:
                c.r('m1', min(near[0], xx) - 190, t - 190, max(near[0], xx) + 190, t + 190)
            else:
                c.via1(xx, t)
                vias.setdefault(net, []).append(xx)
        elif net == 'VSS' and side == 'N':
            c.r('m1', xx - 190, Y['vss_t'] - 300, xx + 190, g['cb'])
        elif net == 'VDD' and side == 'P':
            c.r('m1', xx - 190, g['ct'], xx + 190, Y['vdd_b'] + 300)
        elif net in ('VDD', 'VSS') or kind == 'g':
            raise SystemExit(f'unhandled terminal {net} {side} {kind} at {xx}')
        # else: a stack midpoint on one diffusion (the NANDs' ns): no stub
    for net in trk:
        a, b = span[net]
        c.r('m2', a - 190, ty[net] - 190, b + 190, ty[net] + 190)
        if net not in xpin:                # internal net names for the extraction (a, b, t, ..., py4)
            c.label(net, 'm2', snap((a + b) / 2), ty[net])
    # M5n (left, out_n to x 0) and M5p (right, out_p to xr)
    draw_m5(c, Y, ty['ny4'], xd5n, nf5, wn5, wp5, 'out_n', 0, 'L')
    draw_m5(c, Y, ty['py4'], xd5p, nf5, wn5, wp5, 'out_p', xr, 'R')
    # M3 verticals: pins up to the top edge (through a window in the VDD rail's M3), TG ties to the rails
    ytop = Y['vdd_t']
    skip_vdd, skip_vss = [], []
    for net, xx in xpin.items():
        c.via2(xx, ty[net])
        c.r('m3', xx - 190, ty[net] - 190, xx + 190, ytop)
        c.label(net, 'm3', xx, ytop - 200, port=True)
        skip_vdd.append((xx - 190 - 400, xx + 190 + 400))
    for net, xx in xtie.items():
        yr = (Y['vdd_b'] + Y['vdd_t']) // 2 if net == 'tgh' else (Y['vss_b'] + Y['vss_t']) // 2
        c.via2(xx, ty[net])
        c.r('m3', xx - 190, min(ty[net], yr) - 190, xx + 190, max(ty[net], yr) + 190)
        c.via2(xx, yr)                     # onto the rail's M2; the rail's own M3 has a window here
        (skip_vdd if net == 'tgh' else skip_vss).append((xx - 190 - 400, xx + 190 + 400))
    # wells, taps, rails
    pxs = [x for (_, _, _, cp, _) in place for x in cp] + [xd5n]
    pmax = xd5p + m5_width(nf5)
    nw_x0, nw_x1 = min(pxs) - 600, pmax + 600
    Y['nw_b'] = Y['p_bot'] - 80 - 450
    Y['tap_t'] = Y['vdd_b'] + 1010
    Y['nw_t'] = Y['tap_t'] + 380 + 150
    c.r('nwell', nw_x0, Y['nw_b'], nw_x1, Y['nw_t'])
    # DF.13_LV (n-well tap within 20 um of every PMOS): a second n+ tap strip just above the tallest P strip of
    # the columns (between the M5s); the VDD source stubs that cross it tie it to VDD, plus an M1 strap to the rail
    # at each end
    wpcol = max(um(W) for _, P, _ in cols for W, _, _ in P)
    yt2 = Y['p_bot'] + wpcol + 800
    tx0, tx1 = x_col0 - 200, xlogic + 200
    c.r('nsd', tx0, yt2, tx1, yt2 + 380)
    c.r('nsc', tx0 + 75, yt2 + 75, tx1 - 75, yt2 + 305)
    c.r('m1', tx0, yt2, tx1, yt2 + 380)
    for xx in (tx0, tx1 - 600):
        c.r('m1', xx, yt2, xx + 600, Y['vdd_b'] + 300)
    Y['tap2'] = yt2
    # decap below: its VDD verticals (M3) cross the VSS rail through windows
    s_dc, dmeta, ybot = decap(c, s, xr, Y, xv=(x_col0 - 300, xlogic + 100))   # M3-free x: inside the M5s
    skip_vss += s_dc
    rail(c, Y['vss_b'], Y['vss_t'], 0, xr, tap=('p', (300, xr - 300)), skip=skip_vss)
    rail(c, Y['vdd_b'], Y['vdd_t'], 0, xr, tap=('n', (nw_x0 + 150, nw_x1 - 150)), skip=skip_vdd)
    c.label('VSS', 'm2', 1000, (Y['vss_b'] + Y['vss_t']) // 2, port=True)
    c.label('VDD', 'm2', 1000, (Y['vdd_b'] + Y['vdd_t']) // 2, port=True)
    meta = dict(Y=Y, bbox=(0, ybot, xr, ytop), tracks={n: [k, ty[n], span[n]] for n, k in trk.items()}, ntrk=ntrk,
                cols=colx, xpin=xpin, xtie=xtie, decap=dmeta, offs=offs, S=s)
    return c, meta


def decap(c, s, xr, Yb, xv):
    """Decap rows below the band's VSS rail (it is the top VSS strap). m gates W x L in rows of ng; rows in pairs
    sharing continuous poly gates and one VDD poly-contact strap (M1) between them; S/D straps to the VSS straps
    above / below the pair. The VDD straps reach the VDD rail through M3 verticals at xv (via1 + via2): x with no other M3 (the out bars
    run to the block edges, so not there).
    Returns (the VSS rail's M3 windows, meta, bottom y)."""
    W, L, m = um(s['dcw']), um(s['dcl']), int(s['dcm'])
    RWd, MID = 1200, 1400
    x0 = 2600
    ng = max(1, (xr - 2600 - x0 - RWd) // (L + RWd))
    npair = -(-m // (2 * ng))
    y = Yb['vss_b']                              # top of the current strap stack (built downwards)
    left = m
    vdd_y, straps = [], []
    for p in range(npair):
        n1 = min(ng, left)                       # upper row
        n0 = min(ng, left - n1)                  # lower row
        left -= n0 + n1
        yb1 = y - 600 - W
        ym = yb1 - MID // 2
        yb0 = yb1 - MID - W
        ylow = (yb0 if n0 else ym - 300) - 600   # top of the strap below the pair
        for yb, n, up in ((yb1, n1, True), (yb0, n0, False)):
            if not n:
                continue
            c.r('ndiff', x0, yb, x0 + n * (L + RWd) + RWd, yb + W)
            for k in range(n + 1):
                cx = x0 + RWd // 2 + k * (L + RWd)
                c.r('ndc', cx - CO // 2, yb + ENC_CO, cx + CO // 2, yb + W - ENC_CO)
                if up:
                    c.r('m1', cx - 300, yb + ENC_CO - 75, cx + 300, y + 300)
                else:
                    c.r('m1', cx - 300, ylow - 300, cx + 300, yb + W - ENC_CO + 75)
        for k in range(n1):
            a = x0 + RWd + k * (L + RWd)
            c.r('poly', a, (yb0 - ENDCAP) if k < n0 else (ym - 300), a + L, yb1 + W + ENDCAP)
        xg1 = x0 + RWd + (n1 - 1) * (L + RWd) + L
        c.r('poly', x0 + RWd, ym - 300, xg1, ym + 300)
        c.r('pc', x0 + RWd + 200, ym - 115, xg1 - 200, ym + 115)
        c.r('m1', xv[0] - 300, ym - 300, xv[1] + 300, ym + 300)
        for xx in xv:
            c.via1(xx, ym)
            c.via2(xx, ym)
        vdd_y.append(ym)
        y = ylow
        straps.append((y - RAIL, y))
        y -= RAIL
    for yb, yt in straps:
        rail(c, yb, yt, 0, xr, tap=('p', (300, xr - 300)), m3=False)
    ytop = (Yb['vdd_b'] + Yb['vdd_t']) // 2
    for xx in xv:
        c.r('m3', xx - 300, min(vdd_y) - 300, xx + 300, ytop + 300)
        c.via2(xx, ytop)
    win = [(xx - 300 - 400, xx + 300 + 400) for xx in xv]
    return win, dict(rows_pairs=npair, per_row=ng, vdd_y=vdd_y), y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(REPO / 'build' / 'layout_tx_drv'))
    ap.add_argument('--gds', default=str(REPO / 'layout' / 'tx_drv.gds'))
    ap.add_argument('--no-magic', action='store_true')
    a = ap.parse_args()
    c, meta = build()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob('*.mag'):
        old.unlink()
    tcl = 'drc off\nsnap internal\n' + c.tcl()
    tcl += f'load tx_drv\nselect top cell\nexpand\ngds write {Path(a.gds).resolve()}\nquit -noprompt\n'
    (out / 'tx_drv.tcl').write_text(tcl)
    (out / 'meta.json').write_text(json.dumps(meta, indent=1, default=str))
    bb = meta['bbox']
    print(f'bbox {(bb[2] - bb[0]) / 1000:.2f} x {(bb[3] - bb[1]) / 1000:.2f} um = '
          f'{(bb[2] - bb[0]) * (bb[3] - bb[1]) / 1e6:.0f} um2; {meta["ntrk"]} tracks; decap {meta["decap"]["rows_pairs"]}'
          f' row pairs x {meta["decap"]["per_row"]}')
    if not a.no_magic:
        rc = f"{os.environ.get('PDK_ROOT', '/foss/pdks')}/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc"
        r = subprocess.run(['magic', '-rcfile', rc, '-noconsole', '-dnull', 'tx_drv.tcl'], cwd=out,
                           capture_output=True, text=True)
        (out / 'magic_gen.log').write_text(r.stdout + r.stderr)
        print('magic log:', out / 'magic_gen.log')


if __name__ == '__main__':
    main()
