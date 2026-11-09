"""
tx_drv: the dipole TX driver (sim/tx/tx_drv.py, plan "dipole transmitter drivers"), three sheets:

  tx_split : the tap inverter T on lsdiv's ls node, then the phase splitter: a = A2(A1(t)), b = TG(B1(t)), and the
             weak cross-coupled keeper XA / XB between a and b that pulls the two edges together
  tx_arm   : one antenna arm, out = in & en: NAND2 then 5 inverters tapering up to the output stage
  tx_drv   : tx_split -> two tx_arm (a -> out_p, b -> out_n), each with its own enable, plus the supply decap DC

Source of truth: sim/tx/tx_drv.py block() (the simulated circuit). Every device is looked up there by its subckt and
name, so W, L, m and the nets are the simulated ones.

    python3 xschem/gen/tx_drv.py
"""
import importlib.util
import os

from common import REPO, Sch, gmos, ginv, place as _place, finish, title, bulk, port, supply, parse

_spec = importlib.util.spec_from_file_location('sim_tx_drv', os.path.join(REPO, 'sim', 'tx', 'tx_drv.py'))
TX = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(TX)

PINS = ['VDD', 'VSS', 'ls', 'en_p', 'en_n', 'out_p', 'out_n']


def subckts(text):
    """{cell: {device: dict}} from block(): device lines only (X... with a PDK model), per .subckt."""
    out, cell, lines = {}, None, []
    for ln in text.splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] == '.subckt':
            cell, lines = t[1], []
        elif t[0] == '.ends':
            out[cell] = parse('\n'.join(lines))
        elif t[0].startswith('X'):
            lines.append(ln)
    return out


DEV = subckts(TX.block())


def wl(d):
    return f"{d['w']:g}/{d['l']:g}" + (f" ×{d['m']}" if d.get('m', 1) > 1 else '')


def check(inst, **nets):
    assert inst.nets == nets, (inst.props.get('name'), inst.nets, nets)


def place(s, cell, name, x, y, **kw):
    kw.setdefault('dev', DEV[cell][name])
    kw.setdefault('val', wl(DEV[cell][name]))
    return _place(s, name, x, y, **kw)


def inverter(s, cell, name, x, y, inp, out, flip=False, h=75):
    """INV <name>p over <name>n from the block (pointing right, or left with flip), bulks and sources to supply
    symbols; returns (gate, drain)."""
    dp, dn = DEV[cell][f'{name}p'], DEV[cell][f'{name}n']
    assert dp['nets'] == [out, inp, 'VDD', 'VDD'] and dn['nets'] == [out, inp, 'VSS', 'VSS'], name
    if flip:
        p = gmos(s, 'p', x + 20, y - h, W=dp['w'], L=dp['l'], m=dp['m'], name=f'{name}p', flip=1)
        n = gmos(s, 'n', x + 20, y + h, W=dn['w'], L=dn['l'], m=dn['m'], name=f'{name}n', flip=1)
        g, d = (x + 40, y), (x, y)
        s.bus(p.pin('G'), n.pin('G'), [g])
        s.bus(p.pin('D'), n.pin('D'), [d])
    else:
        p, n, g, d = ginv(s, x, y, dict(W=dp['w'], L=dp['l'], m=dp['m'], name=f'{name}p'),
                          dict(W=dn['w'], L=dn['l'], m=dn['m'], name=f'{name}n'), h=h)
    p.props['val'] = f'"{wl(dp)}"'
    n.props['val'] = f'"{wl(dn)}"'
    bulk(s, p, to='VDD')
    bulk(s, n, to='VSS')
    supply(s, p.pin('S'), 'VDD')
    supply(s, n.pin('S'), 'VSS')
    return g, d


def supplies(s, xl, y):
    """VDD and VSS ports, tied to the sheet's supply symbols by name."""
    for i, net in enumerate(('VDD', 'VSS')):
        yy = y + 60 * i
        s.wire((xl, yy), (xl + 60, yy))
        port(s, (xl, yy), net, 'io')
        supply(s, (xl + 60, yy), net)


def build_split():
    c = 'tx_split'
    s = Sch()
    xl, xr = -300, 1400
    ya, yb, ybl = 0, 900, 1100               # A row, B row, the b line
    g, d = inverter(s, c, 'T', 0, ya, 'ls', 't')
    s.wire((xl, ya), g); port(s, (xl, ya), 'ls', 'in')
    ga1, da1 = inverter(s, c, 'A1', 300, ya, 't', 'ta')
    ga2, da2 = inverter(s, c, 'A2', 600, ya, 'ta', 'a')
    gb1, db1 = inverter(s, c, 'B1', 300, yb, 't', 'tb')
    # t: right into A1, and down the left to B1
    s.bus(d, ga1, [(100, ya)])
    s.route((100, ya), (100, yb), gb1)
    s.wire(da1, ga2)
    # the transmission gate, upright: tb in at the top bar, b out at the bottom bar; TP (gate VSS) on the left,
    # TN (gate VDD) on the right, bulk ties pointing inward
    xt, yt = 600, yb + 80
    tp = place(s, c, 'TGp', xt - 60, yt, hide=True)
    tn = place(s, c, 'TGn', xt + 60, yt, rot=2, hide=True)
    check(tp, D='b', G='VSS', S='tb', B='VDD')
    check(tn, D='b', G='VDD', S='tb', B='VSS')
    s.wire(tp.pin('B'), (xt - 20, yt)); supply(s, (xt - 20, yt), 'VDD')
    s.wire(tn.pin('B'), (xt + 20, yt)); supply(s, (xt + 20, yt), 'VSS')
    s.wire(tp.pin('G'), (xt - 120, yt)); supply(s, (xt - 120, yt), 'VSS')
    s.wire(tn.pin('G'), (xt + 120, yt)); supply(s, (xt + 120, yt), 'VDD')
    top, bot = yt - 50, yt + 50
    s.route(tp.pin('S'), (xt - 40, top), (xt, top)); s.route(tn.pin('S'), (xt + 40, top), (xt, top))
    s.route(db1, (xt, yb), (xt, top))
    s.route(tp.pin('D'), (xt - 40, bot), (xt, bot)); s.route(tn.pin('D'), (xt + 40, bot), (xt, bot))
    s.route((xt, bot), (xt, ybl))
    # keeper: XB (a -> b) pointing right, XA (b -> a) pointing left under it, between the a and b lines
    xk, xa_, xb_ = 1100, 950, 1250
    gxb, dxb = inverter(s, c, 'XB', xk, 300, 'a', 'b')
    gxa, dxa = inverter(s, c, 'XA', xk, 600, 'b', 'a', flip=True)
    s.bus(da2, (xr, ya), [(xa_, ya)]); port(s, (xr, ya), 'a', 'out')
    s.bus((xa_, ya), (xa_, 600), [(xa_, 300)])
    s.wire((xa_, 300), gxb); s.wire(dxa, (xa_, 600))
    s.bus((xt, ybl), (xr, ybl), [(xb_, ybl)]); port(s, (xr, ybl), 'b', 'out')
    s.bus((xb_, 300), (xb_, ybl), [(xb_, 600)])
    s.wire(dxb, (xb_, 300)); s.wire(gxa, (xb_, 600))
    for t, x, y in (('t', 120, ya - 24), ('ta', 420, ya - 24), ('tb', 420, yb - 24), ('a', 780, ya - 24),
                    ('b', 780, ybl - 24)):
        s.text(x, y, t, 0.3)
    s.text(xt - 230, yt - 30, 'TGp', 0.3); s.text(xt - 230, yt + 6, wl(DEV[c]['TGp']), 0.3)
    s.text(xt + 140, yt - 30, 'TGn', 0.3); s.text(xt + 140, yt + 6, wl(DEV[c]['TGn']), 0.3)
    s.text(xk + 60, 420, 'keeper (weak)', 0.3)
    supplies(s, xl, 1300)
    title(s, xl, -330, ['tx_split: tap on ls + phase splitter (a = !ls, b = ls)',
                        'T is the only load on lsdiv\'s ls node; path a has two inverters, path b one inverter and an '
                        'always-on transmission gate that stands in for the second inverter\'s delay',
                        'the weak cross-coupled pair XA / XB pulls the a and b edges together (target skew <= 10 ps)'])
    finish(s, c, ['VDD', 'VSS', 'ls', 'a', 'b'], left=['ls'], right=['a', 'b'], top=['VDD'], bottom=['VSS'],
           width=160, label='split')


def build_arm():
    c = 'tx_arm'
    s = Sch()
    xl = -700
    yc = -50                                   # the y0 .. out chain
    # NAND2: PMOS in parallel on top, NMOS in series below; in on the NMOS next to the output (the fast input)
    nap = place(s, c, 'NAp', -420, -150)
    nbp = place(s, c, 'NBp', -220, -150)
    nan = place(s, c, 'NAn', -320, 0)
    nbn = place(s, c, 'NBn', -320, 100)
    check(nap, D='y0', G='in', S='VDD', B='VDD'); check(nbp, D='y0', G='en', S='VDD', B='VDD')
    check(nan, D='y0', G='in', S='ns', B='VSS'); check(nbn, D='ns', G='en', S='VSS', B='VSS')
    for m, k in ((nap, 'VDD'), (nbp, 'VDD'), (nan, 'VSS'), (nbn, 'VSS')):
        bulk(s, m, to=k)
    supply(s, nap.pin('S'), 'VDD'); supply(s, nbp.pin('S'), 'VDD'); supply(s, nbn.pin('S'), 'VSS')
    s.wire(nap.pin('D'), (-400, yc)); s.wire(nbp.pin('D'), (-200, yc))
    s.bus((-400, yc), (-200, yc), [(-300, yc)])
    s.wire((-300, yc), nan.pin('D'))
    s.wire(nan.pin('S'), nbn.pin('D'))
    s.bus((xl, 0), nan.pin('G'), [(-460, 0)])
    s.route((-460, 0), (-460, -150), nap.pin('G'))
    port(s, (xl, 0), 'in', 'in')
    s.bus((xl, 100), nbn.pin('G'), [(-560, 100)])
    s.route((-560, 100), (-560, -250), (-260, -250), (-260, -150), nbp.pin('G'))
    port(s, (xl, 100), 'en', 'in')
    prev = (-200, yc)
    ws = TX.arm_widths(TX.S)
    for i in range(1, 6):
        x = -100 + i * 250
        g, d = inverter(s, c, f'M{i}', x, yc, f'y{i - 1}', 'out' if i == 5 else f'y{i}', h=100)
        s.wire(prev, g)
        s.text(x - 60, yc + 170, f'M{i}', 0.3)
        if i < 5:
            s.text(x + 20, yc - 24, f'y{i}', 0.3)
        prev = d
    s.wire(prev, (prev[0] + 150, yc)); port(s, (prev[0] + 150, yc), 'out', 'out')
    s.text(-180, yc - 24, 'y0', 0.3); s.text(-290, 26, 'ns', 0.3)
    supplies(s, xl, 400)
    title(s, xl, -480, ['tx_arm: one antenna arm, out = in & en',
                        'NAND2 then 5 inverters (6 inversions); en = 0 holds out low, so with both arms off there is '
                        'no DC across the dipole',
                        'inverter N widths ' + ' / '.join(f'{w:g}' for w in ws) + f' um, P = {TX.S["kp"]:g} N, '
                        f'L {TX.L} um (taper x{TX.S["taper"]:g})'])
    finish(s, c, ['VDD', 'VSS', 'in', 'en', 'out'], left=['in', 'en'], right=['out'], top=['VDD'], bottom=['VSS'],
           width=160, label='arm')


def build_top():
    c = 'tx_drv'
    s = Sch()
    xl, xr = -400, 900
    sp = s.place('tx_split.sym', 0, 0, name='xsp')
    ap = s.place('tx_arm.sym', 500, -250, name='xap')
    an = s.place('tx_arm.sym', 500, 250, name='xan')
    s.wire((xl, sp.pin('ls')[1]), sp.pin('ls')); port(s, (xl, sp.pin('ls')[1]), 'ls', 'in')
    for blk, src, side in ((ap, sp.pin('a'), 'p'), (an, sp.pin('b'), 'n')):
        xm = 250 if side == 'p' else 300
        s.route(src, (xm, src[1]), (xm, blk.pin('in')[1]), blk.pin('in'))
        e = blk.pin('en')
        ye = e[1]
        s.route((xl, ye + (-200 if side == 'p' else 200)), (200, ye + (-200 if side == 'p' else 200)), (200, ye))
        s.wire((200, ye), e)
        port(s, (xl, ye + (-200 if side == 'p' else 200)), f'en_{side}', 'in')
        o = blk.pin('out')
        s.wire(o, (xr, o[1])); port(s, (xr, o[1]), f'out_{side}', 'out')
    for blk in (sp, ap, an):
        supply(s, blk.pin('VDD'), 'VDD')
        supply(s, blk.pin('VSS'), 'VSS')
    # supply decap: nfet gate cap, gate VDD, drain / source / bulk VSS
    dc = place(s, c, 'DC', -200, 600)
    check(dc, D='VSS', G='VDD', S='VSS', B='VSS')
    xt = dc.pin('D')[0] + 20
    s.wire(dc.pin('D'), (xt, dc.pin('D')[1])); s.wire(dc.pin('B'), (xt, dc.pin('B')[1]))
    s.bus((xt, dc.pin('D')[1]), (xt, dc.pin('S')[1]), [(xt, dc.pin('B')[1])])
    s.wire(dc.pin('S'), (xt, dc.pin('S')[1]))
    supply(s, (xt, dc.pin('S')[1]), 'VSS')
    s.wire(dc.pin('G'), (dc.pin('G')[0] - 40, dc.pin('G')[1])); supply(s, (dc.pin('G')[0] - 40, dc.pin('G')[1]), 'VDD')
    d = DEV[c]['DC']
    cdec = d['w'] * d['l'] * d['m'] * 4.07e-3
    s.text(-160, 660, f'DC supply decap ~{cdec:.1f} pF', 0.3)
    supplies(s, xl, 800)
    title(s, xl, -560, ['tx_drv: dipole TX driver (out_p, out_n in antiphase)',
                        'ls (lsdiv\'s level-shifter output, 0-3.3 V) -> splitter -> two arms; en_p / en_n gate each arm '
                        '(both low: both outputs low); one arm alone is the monopole fallback',
                        'VDD is the driver\'s own supply (VDPWR stripe and decap), separate from the ring\'s; '
                        'source: sim/tx/tx_drv.py block()'])
    finish(s, c, PINS, left=['ls', 'en_p', 'en_n'], right=['out_p', 'out_n'], top=['VDD'], bottom=['VSS'],
           width=160, label='tx_drv')


def build():
    build_split()
    build_arm()
    build_top()


if __name__ == '__main__':
    build()
