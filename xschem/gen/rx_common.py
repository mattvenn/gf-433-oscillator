"""
Shared helpers for the receiver (option B) sheets, xschem/gen/rx_*.py.

Source of truth: the receiver netlisters in sim/rx/ (sim/rx/rx_top.py block() prints every subckt). They are run
as a subprocess (python3 sim/rx/rx_top.py), so their module names (rx_lna, rx_bias, ...) never meet these
generators' names. Every device is looked up by its subckt and instance name, so W, L, m and the nets drawn are
the simulated ones.

Drawing primitives (textbook style, every connection a drawn wire, labels only for ports and supplies):
  inverter(), nand2(), dpair() (differential pair + resistor loads + tail), couple() (AC coupling + bias element),
  passive() (resistor / MOS cap between two points).
"""
import os
import subprocess
import sys

from common import REPO, Sch, Inst, gmos, gres, ginv, place as _place, finish, title, bulk, port, supply, parse  # noqa: F401

NET = subprocess.run([sys.executable, os.path.join(REPO, 'sim', 'rx', 'rx_top.py')], capture_output=True, text=True,
                     check=True).stdout


def subckts(text):
    """{cell: {device: dict}} (device lines X... with a PDK model), and {cell: [instance lines]}, per .subckt."""
    out, inst, cell, lines = {}, {}, None, []
    for ln in text.splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] == '.subckt':
            cell, lines = t[1], []
            inst[cell] = []
        elif t[0] == '.ends':
            out[cell] = parse('\n'.join(lines))
        elif t[0].startswith('X'):
            lines.append(ln)
        elif t[0].startswith('x'):
            inst[cell].append(t)
    return out, inst


DEV, INST = subckts(NET)


def wl(d):
    if 'fet' not in d['model']:
        return f"{d['w']:g}/{d['l']:g}"
    return f"{d['w']:.3g}/{d['l']:.3g}" + (f" ×{d['m']}" if d.get('m', 1) > 1 else '')


def check(inst, **nets):
    assert inst.nets == nets, (inst.props.get('name'), inst.nets, nets)


def place(s, cell, name, x, y, **kw):
    kw.setdefault('dev', DEV[cell][name])
    d = DEV[cell][name]
    if 'fet' not in d['model']:
        rsh = {'ppolyf_u': 350.0, 'ppolyf_u_1k': 1000.0}[d['model']]
        r = rsh * d['l'] / d['w']
        kw.setdefault('val', f"{d['w']:g}/{d['l']:g} ({r / 1e3:.3g}k)" if r >= 1e3 else f"{d['w']:g}/{d['l']:g} ({r:.0f})")
    else:
        kw.setdefault('val', wl(d))
    return _place(s, name, x, y, **kw)


def mos_c(d):
    """Gate capacitance estimate (F) of an nfet / pfet used as a capacitor."""
    return d['w'] * d['l'] * d['m'] * 4.07e-15


def supplies(s, xl, y):
    """VDD and VSS ports, tied to the sheet's supply symbols by name."""
    for i, net in enumerate(('VDD', 'VSS')):
        yy = y + 60 * i
        s.wire((xl, yy), (xl + 60, yy))
        port(s, (xl, yy), net, 'io')
        supply(s, (xl + 60, yy), net)


def inverter(s, cell, name, x, y, inp, out, h=75, vdd='VDD', vss='VSS', flip=False):
    """INV <name>p over <name>n (pointing right, or left with flip), bulks to the supplies, sources to supply
    symbols (or, when vdd / vss are other nets, bulk tied to source and the caller wires the source pins).
    Returns (gate, drain, p, n)."""
    dp, dn = DEV[cell][f'{name}p'], DEV[cell][f'{name}n']
    assert dp['nets'] == [out, inp, vdd, vdd] and dn['nets'] == [out, inp, vss, vss], (name, dp['nets'], dn['nets'])
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
    if vdd == 'VDD':
        bulk(s, p, to='VDD')
        supply(s, p.pin('S'), 'VDD')
    else:
        bulk(s, p, to='S')
    if vss == 'VSS':
        bulk(s, n, to='VSS')
        supply(s, n.pin('S'), 'VSS')
    else:
        bulk(s, n, to='S')
    return g, d, p, n


def nand2(s, cell, names, x, y, a, b, out, mid):
    """NAND2 from the block: names = (Pa, Pb, Na, Nb): PMOS Pa (gate a), Pb (gate b) in parallel to VDD on top, NMOS
    Na (gate a, at the output) over Nb (gate b) to VSS. Returns (a pin point, b pin point, out point); the inputs
    leave to the left at the NMOS gate heights."""
    pa, pb, na, nb = names
    ia = place(s, cell, pa, x - 100, y - 150)
    ib = place(s, cell, pb, x + 100, y - 150)
    ja = place(s, cell, na, x, y)
    jb = place(s, cell, nb, x, y + 100)
    check(ia, D=out, G=a, S='VDD', B='VDD'); check(ib, D=out, G=b, S='VDD', B='VDD')
    check(ja, D=out, G=a, S=mid, B='VSS'); check(jb, D=mid, G=b, S='VSS', B='VSS')
    for m, k in ((ia, 'VDD'), (ib, 'VDD'), (ja, 'VSS'), (jb, 'VSS')):
        bulk(s, m, to=k)
    supply(s, ia.pin('S'), 'VDD'); supply(s, ib.pin('S'), 'VDD'); supply(s, jb.pin('S'), 'VSS')
    yo = y - 50
    s.wire(ia.pin('D'), (x - 80, yo)); s.wire(ib.pin('D'), (x + 120, yo))
    s.bus((x - 80, yo), (x + 120, yo), [(x + 20, yo)])
    s.wire((x + 20, yo), ja.pin('D'))
    s.wire(ja.pin('S'), jb.pin('D'))
    # a: NMOS Na gate, and up to Pa's gate; b: NMOS Nb gate, and up and over to Pb's gate
    ga, gb = ja.pin('G'), jb.pin('G')
    xa, xb = x - 160, x - 220
    s.bus((xa - 140, ga[1]), ga, [(xa, ga[1])])
    s.route((xa, ga[1]), (xa, ia.pin('G')[1]), ia.pin('G'))
    s.bus((xa - 140, gb[1]), gb, [(xb, gb[1])])
    s.route((xb, gb[1]), (xb, y - 250), (x + 40, y - 250), (x + 40, ib.pin('G')[1]), ib.pin('G'))
    return (xa - 140, ga[1]), (xa - 140, gb[1]), (x + 120, yo)


def dpair(s, cell, x, y, ma, mb, mt, ra, rb, ip, im, op, om, tail, gnb='nb', dy=200):
    """Differential pair: ma (gate ip, drain om) left at x - 120, mb (gate im, drain op) right at x + 120 (mirrored,
    gate on the right), tail device mt under the middle, resistor loads ra (om) / rb (op) up to a VDD rail.
    Returns dict of the points: ip, im (gate ends, outward), om, op (load / drain nodes, outward), nb (tail gate),
    vdd (rail y)."""
    a = place(s, cell, ma, x - 120, y)
    b = place(s, cell, mb, x + 120, y, flip=1)
    t = place(s, cell, mt, x, y + dy)
    r1 = place(s, cell, ra, x - 100, y - dy)
    r2 = place(s, cell, rb, x + 100, y - dy)
    check(a, D=om, G=ip, S=tail, B='VSS'); check(b, D=op, G=im, S=tail, B='VSS')
    check(t, D=tail, G=gnb, S='VSS', B='VSS')
    assert r1.nets['M'] == om and r1.nets['P'] == 'VDD' and r2.nets['M'] == op and r2.nets['P'] == 'VDD'
    bulk(s, a, to='VSS'); bulk(s, b, to='VSS'); bulk(s, t, to='VSS')
    supply(s, t.pin('S'), 'VSS')
    # sources to the tail drain
    ys = a.pin('S')[1]
    s.route(a.pin('S'), (a.pin('S')[0], ys + 40), (x + 20, ys + 40))
    s.route(b.pin('S'), (b.pin('S')[0], ys + 40), (x + 20, ys + 40))
    s.wire((x + 20, ys + 40), t.pin('D'))
    # loads: M (bottom) to the drains, P (top) to VDD; bulks of the poly resistors to VSS
    yl = (r1.pin('M')[1] + a.pin('D')[1]) // 2
    s.route(r1.pin('M'), (r1.pin('M')[0], yl), (a.pin('D')[0], yl), a.pin('D'))
    s.route(r2.pin('M'), (r2.pin('M')[0], yl), (b.pin('D')[0], yl), b.pin('D'))
    supply(s, r1.pin('P'), 'VDD'); supply(s, r2.pin('P'), 'VDD')
    for r in (r1, r2):
        s.wire(r.pin('B'), (r.pin('B')[0] - 20, r.pin('B')[1])); supply(s, (r.pin('B')[0] - 20, r.pin('B')[1]), 'VSS')
    return dict(ip=a.pin('G'), im=b.pin('G'), om=(a.pin('D')[0], yl), op=(b.pin('D')[0], yl), nb=t.pin('G'),
                ta=a, tb=b, tt=t, ra=r1, rb=r2, yl=yl)


def vmirror_place(s, cell, name, x, y, **kw):
    """A MOS mirrored top-to-bottom (rot 2 + flip): gate still on the left, source on top (an NMOS pass device)."""
    return place(s, cell, name, x, y, rot=2, flip=1, **kw)


def stub(s, pt, dx=0, dy=0):
    """A short straight wire from a pin; returns its far end."""
    e = (pt[0] + dx, pt[1] + dy)
    s.wire(pt, e)
    return e


def net(s, pts, y, extra=()):
    """Join points with vertical drops to one horizontal track at y (T junctions split). extra: points already on the
    track (ports, other wires' ends) to include in the span. Returns the sorted track points."""
    taps = []
    for p in pts:
        if p[1] != y:
            s.wire(p, (p[0], y))
        taps.append((p[0], y))
    taps += list(extra)
    xs = sorted({t[0] for t in taps})
    if len(xs) > 1:
        s.bus((xs[0], y), (xs[-1], y), taps)
    return sorted(set(taps))


def mos_dev(s, cell, name, x, y, flip=0, supplies_=True):
    """Place a MOS from the block with its bulk tied to the rail named in the netlist (VDD / VSS: a supply symbol;
    any other net: the caller wires the bulk stub, returned as the second value)."""
    m = place(s, cell, name, x, y, flip=flip)
    b = m.nets['B']
    if b in ('VDD', 'VSS'):
        from common import bulk as _bulk
        _bulk(s, m, to=b)
        return m, None
    from common import bulk as _bulk
    return m, _bulk(s, m)


def capdev(s, cell, name, x, y):
    """A MOS gate cap (S / D / B on one net, VSS or VDD: tied together to a supply symbol). Returns the gate pin."""
    c = place(s, cell, name, x, y)
    rail = c.nets['S']
    assert c.nets['D'] == rail and c.nets['B'] == rail, (name, c.nets)
    xt = c.pin('D')[0] + 20
    s.wire(c.pin('D'), (xt, c.pin('D')[1])); s.wire(c.pin('B'), (xt, c.pin('B')[1]))
    s.bus((xt, c.pin('D')[1]), (xt, c.pin('S')[1]), [(xt, c.pin('B')[1])])
    s.wire(c.pin('S'), (xt, c.pin('S')[1]))
    supply(s, (xt, c.pin('S')[1] if rail == 'VSS' else c.pin('D')[1]), rail)
    return c.pin('G'), c


def resdev(s, cell, name, x, y, top):
    """A poly resistor, vertical, with the terminal on net `top` at the top; bulk to its net's supply symbol (VSS).
    Returns (top pin, bottom pin, inst)."""
    d = DEV[cell][name]
    r = place(s, cell, name, x, y, rot=0 if d['nets'][1] == top else 2)
    assert r.nets['B'] in ('VSS',), r.nets
    b = r.pin('B')
    s.wire(b, (b[0] + (20 if r.rot == 2 else -20), b[1]))
    supply(s, (b[0] + (20 if r.rot == 2 else -20), b[1]), 'VSS')
    pt, pb = (r.pin('P'), r.pin('M')) if r.rot == 0 else (r.pin('M'), r.pin('P'))
    return pt, pb, r
