#!/usr/bin/env python3
"""
mdac: the medium DAC for on-chip fine tuning (docs/tx_fine_tune.md), drawn from the layout's LVS source
(layout/gen/mdac.py lvs_source(): sim/tune/mdac_sim.py mdac_netlist() plus the dummy fingers).

  bias      : MB (1 coarse unit, gate vbnf) pulls Iu out of MPB (64 PMOS units, diode on pb)
  one column per group (31 unary segments s1..s31 of 32 units, binary b4..b0, the SD cell sd, off):
              MU<g> (PMOS units W/L 1/4 x n, gate pb, source VDD) -> c<g> -> SW<g> to mo (gate n<g>, active low)
                                                                         -> SD<g> to md (gate mo)
              off has no switches: always on into mo
  output    : MD (30 coarse units, diode on mo), MO (3 units, gate mo, drain vg), MDD (dump diode on md)
  dummies   : MDUM, the unused fingers of the binary rows (D = S = B = VDD, gate pb)

    python3 xschem/gen/mdac.py
"""
import importlib.util
import os
import re

from common import REPO, Sch, gmos, finish, title, bulk, port, supply

_spec = importlib.util.spec_from_file_location('lay_mdac', os.path.join(REPO, 'layout', 'gen', 'mdac.py'))
LAY = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(LAY)


def devices():
    """Group the LVS source's finger devices by (nets, model, W, L) -> {key: m}."""
    path = os.path.join(REPO, 'build', 'xsch', 'mdac_src.spice')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pins = LAY.lvs_source(path)
    grp = {}
    for ln in open(path):
        t = ln.split()
        if not t or not t[0].startswith('X'):
            continue
        d, g, s, b, model = t[1:6]
        w = float(re.search(r'w=([\d.]+)u', ln).group(1))
        l = float(re.search(r'l=([\d.]+)u', ln).group(1))
        k = (d, g, s, b, model, w, l)
        grp[k] = grp.get(k, 0) + 1
    return pins, grp


PINS, GRP = devices()
GROUPS = [g for g in [f's{i}' for i in range(1, 32)] + [f'b{b}' for b in range(4, -1, -1)] + ['sd']]


def m_of(d, g, s, b, model, w, l):
    return GRP[(d, g, s, b, model, w, l)]


def build():
    s = Sch()
    yvdd, ypb, ymo, ymd = -180, -110, 280, 330
    pitch = 260
    cols = GROUPS + ['off']
    x0 = 0
    vdd_taps, pb_taps, mo_taps, md_taps = [], [], [], []
    for i, g in enumerate(cols):
        xc = x0 + pitch * i
        c = 'mo' if g == 'off' else f'c{g}'
        n = m_of(c, 'pb', 'VDD', 'VDD', 'pfet_03v3', 1.0, 4.0)
        mu = gmos(s, 'p', xc - 20, 0, W=1.0, L=4.0, m=n, name=f'MU{g}')
        s.wire(mu.pin('S'), (xc, yvdd)); vdd_taps.append((xc, yvdd))
        bulk(s, mu, to='S')
        s.route(mu.pin('G'), (xc - 70, 0), (xc - 70, ypb)); pb_taps.append((xc - 70, ypb))
        s.text(xc - 60, -70, g, 0.35)
        if g == 'off':
            s.wire(mu.pin('D'), (xc, ymo)); mo_taps.append((xc, ymo))
            continue
        # c node: down to the switch pair
        s.wire(mu.pin('D'), (xc, 100))
        sw = gmos(s, 'p', xc - 60, 160, W=1.0, L=0.28, name=f'SW{g}')           # S top: c, D bottom: mo
        sd = gmos(s, 'p', xc + 60, 160, W=1.0, L=0.28, name=f'SD{g}', flip=1)   # gate on the right: mo
        s.bus((xc - 40, 100), (xc + 40, 100), [(xc, 100)])
        s.wire((xc - 40, 100), sw.pin('S')); s.wire((xc + 40, 100), sd.pin('S'))
        s.wire(sw.pin('D'), (xc - 40, ymo)); mo_taps.append((xc - 40, ymo))
        s.wire(sd.pin('D'), (xc + 40, ymd)); md_taps.append((xc + 40, ymd))
        s.route(sd.pin('G'), (xc + 100, 160), (xc + 100, ymo)); mo_taps.append((xc + 100, ymo))
        for t in (sw, sd):
            bulk(s, t, to='VDD')
        s.wire(sw.pin('G'), (xc - 110, 160))
        port(s, (xc - 110, 160), f'n{g}', 'in')
        s.text(xc - 27, 222, '1 / 0.28', 0.25)    # SW and SD, each
    xr = x0 + pitch * (len(cols) - 1)
    # dummies and the bias diode, right of the columns
    xd = xr + pitch
    nd = m_of('VDD', 'pb', 'VDD', 'VDD', 'pfet_03v3', 1.0, 4.0)
    du = gmos(s, 'p', xd - 20, 0, W=1.0, L=4.0, m=nd, name='MDUM')
    s.wire(du.pin('S'), (xd, yvdd)); vdd_taps.append((xd, yvdd))
    bulk(s, du, to='S')
    s.route(du.pin('D'), (xd, 60), (xd + 40, 60), (xd + 40, yvdd)); vdd_taps.append((xd + 40, yvdd))
    s.route(du.pin('G'), (xd - 70, 0), (xd - 70, ypb)); pb_taps.append((xd - 70, ypb))
    s.text(xd - 60, -70, 'dummies', 0.35)
    xp = xd + pitch
    npb = m_of('pb', 'pb', 'VDD', 'VDD', 'pfet_03v3', 1.0, 4.0)
    mpb = gmos(s, 'p', xp - 20, 0, W=1.0, L=4.0, m=npb, name='MPB')
    s.wire(mpb.pin('S'), (xp, yvdd)); vdd_taps.append((xp, yvdd))
    bulk(s, mpb, to='S')
    s.route(mpb.pin('G'), (xp - 70, 0), (xp - 70, ypb)); pb_taps.append((xp - 70, ypb))
    s.route(mpb.pin('D'), (xp, 60), (xp + 60, 60), (xp + 60, ypb)); pb_taps.append((xp + 60, ypb))
    s.text(xp - 60, -70, 'bias diode', 0.35)
    # MB: Iu from pb (gate vbnf)
    xb = xp + pitch
    mb = gmos(s, 'n', xb - 20, 60, W=1.2, L=5.335, m=m_of('pb', 'vbnf', 'VSS', 'VSS', 'nfet_03v3', 1.2, 5.335), name='MB')
    s.wire(mb.pin('D'), (xb, ypb)); pb_taps.append((xb, ypb))
    bulk(s, mb, to='S')
    s.wire(mb.pin('S'), (xb, 140)); supply(s, (xb, 140), 'VSS')
    s.wire(mb.pin('G'), (xb - 80, 60)); port(s, (xb - 80, 60), 'vbnf', 'in')
    # rails
    s.bus((x0 - 600, yvdd), (max(t[0] for t in vdd_taps), yvdd), [t for t in vdd_taps if t[0] != max(u[0] for u in vdd_taps)])
    supply(s, (x0 - 600, yvdd), 'VDD')
    s.bus((x0 - 70, ypb), (xb, ypb), [t for t in pb_taps if t not in ((xb, ypb), (x0 - 70, ypb))])
    s.text(x0 - 90, ypb - 30, 'pb', 0.35)
    # output mirror and dump diode, left of the columns
    xm = x0 - 300
    md = gmos(s, 'n', xm - 20, 420, W=1.2, L=5.335, m=m_of('mo', 'mo', 'VSS', 'VSS', 'nfet_03v3', 1.2, 5.335), name='MD')
    s.bus(md.pin('D'), (xm, ymo), [(xm, 380)]); mo_taps.append((xm, ymo))
    s.route(md.pin('G'), (xm - 50, 420), (xm - 50, 380), (xm, 380))
    bulk(s, md, to='S')
    s.wire(md.pin('S'), (xm, 480)); supply(s, (xm, 480), 'VSS')
    xo = x0 - 500
    mo = gmos(s, 'n', xo - 20, 420, W=1.2, L=5.335, m=m_of('vg', 'mo', 'VSS', 'VSS', 'nfet_03v3', 1.2, 5.335), name='MO')
    s.route(mo.pin('G'), (xo - 50, 420), (xo - 50, 360), (xm - 50, 360), (xm - 50, 380))
    s.route(mo.pin('D'), (xo, 220), (x0 - 650, 220))
    port(s, (x0 - 650, 220), 'vg', 'io')
    bulk(s, mo, to='S')
    s.wire(mo.pin('S'), (xo, 480)); supply(s, (xo, 480), 'VSS')
    xq = x0 - 150
    mdd = gmos(s, 'n', xq - 20, 470, W=3.4, L=1.0, m=m_of('md', 'md', 'VSS', 'VSS', 'nfet_03v3', 3.4, 1.0), name='MDD')
    s.bus(mdd.pin('D'), (xq, ymd), [(xq, 420)]); md_taps.append((xq, ymd))
    s.route(mdd.pin('G'), (xq - 50, 470), (xq - 50, 420), (xq, 420))
    bulk(s, mdd, to='S')
    s.wire(mdd.pin('S'), (xq, 530)); supply(s, (xq, 530), 'VSS')
    xmo = max(t[0] for t in mo_taps)
    s.bus((xm, ymo), (xmo, ymo), [t for t in mo_taps if t not in ((xm, ymo), (xmo, ymo))])
    xmd = max(t[0] for t in md_taps)
    s.bus((xq, ymd), (xmd, ymd), [t for t in md_taps if t not in ((xq, ymd), (xmd, ymd))])
    s.text(xm + 15, ymo - 35, 'mo', 0.35)    # net names next to the diodes they belong to
    s.text(xq + 15, ymd - 35, 'md', 0.35)
    # supply ports
    for k, net in enumerate(('VDD', 'VSS')):
        y = 640 + 60 * k
        s.wire((x0 - 650, y), (x0 - 590, y)); port(s, (x0 - 650, y), net, 'io')
        supply(s, (x0 - 590, y), net)
    title(s, x0 - 650, -370, ['mdac: 10-bit medium DAC for fine tuning (5 unary + 5 binary + SD cell), PMOS current steering',
                              'I_out = (word + sd + 32) x Iu / 64 x 3 / 30 into vg; full scale 1.6 coarse units (docs/tx_fine_tune.md)',
                              'the LVS source of layout/mdac.gds (layout/gen/mdac.py); one control line per group, active low',
                              'sizes: m x W / L in um; the steering pair SW / SD is 1 / 0.28 each'])
    # sizes as plain text: the symbol's own 'm x W / L' label is on a layer the renders and xschem-viewer don't draw
    for it in s.items:
        if 'fet' not in it.sym:
            continue
        p = it.props
        if p.get('name', '').startswith(('SW', 'SD')):
            continue                            # one note per steering pair, below
        w, l, m = (float(str(p[k]).rstrip('u')) for k in ('W', 'L', 'm'))
        t = f'{m:g} x {w:g} / {l:g}' if m != 1 else f'{w:g} / {l:g}'
        sz = 0.25
        name = p.get('name', '')
        left = name.startswith('SW') or name in ('MD', 'MO', 'MDUM', 'MPB')   # off the wires / the SD note
        dx = 25 if it.flip else (-25 - len(t) * 27 * sz if left else 25)
        s.text(it.x + dx, it.y + 38, t, sz)
    ctl = [p for p in PINS if p.startswith('n')]
    finish(s, 'mdac', PINS, left=ctl, right=['vg', 'vbnf'], top=['VDD'], bottom=['VSS'], width=240, label='mdac')


if __name__ == '__main__':
    build()
