"""
lsdiv: the a0 level shifter + TSPC /4 prescaler + clock buffer (docs/lsdiv_design.md), four sheets:

  ls_ac    : Cc (2 fF metal-finger cap) AC-couples a0 into INV1 -> INV2 -> INV3 (= ls, full rail). The output
             is low-passed by R1 / C1 (lf) and fed back to INV1's input lg through the long pfet LRB: three
             inversions, so negative DC feedback holds mean(ls) at INV1's trip point (duty ~50 %).
  tspc_t1  : TSPC toggle flip-flop (D = qb), clk = ls, q = q1 (ls / 2)
  tspc_t2  : the same, smaller, clk = q1, q = q2 (ls / 4)
  lsdiv    : the three in a row, then the clock buffer B1 (q2 -> ck)

Source of truth: sim/lsdiv/lsdiv.py block() (the simulated circuit with the drawn passives: R1 ppolyf_u_1k,
C1 nfet_03v3 gate cap). Every device is looked up there by name, so W, L, m and the nets are the simulated ones.

    python3 xschem/gen/lsdiv.py
"""
import os
import sys

from common import REPO, Sch, ginv, place as _place, finish, title, bulk, port, supply, parse

import importlib.util  # noqa: E402
sys.path.insert(0, os.path.join(REPO, 'tools'))
_spec = importlib.util.spec_from_file_location('sim_lsdiv', os.path.join(REPO, 'sim', 'lsdiv', 'lsdiv.py'))
LS = importlib.util.module_from_spec(_spec)       # sim/lsdiv/lsdiv.py (same module name as this file)
_spec.loader.exec_module(LS)

BLOCK = LS.block()
DEV = parse('\n'.join(ln for ln in BLOCK.splitlines() if ln and not ln.startswith('.')))
PINS = ['VDD', 'VSS', 'a0', 'ck', 'ls']


def place(s, name, x, y, **kw):
    kw.setdefault('dev', DEV[name])
    return _place(s, name, x, y, **kw)


def vmirror(s, name, x, y, **kw):
    return place(s, name, x, y, rot=2, flip=1, **kw)


def wl(d):
    return f"{d['w']:g}/{d['l']:g}"


def check(inst, **nets):
    assert inst.nets == nets, (inst.props.get('name'), inst.nets, nets)


def supplies(s, xl, y):
    """VDD and VSS ports, tied to the sheet's supply symbols by name."""
    for i, net in enumerate(('VDD', 'VSS')):
        yy = y + 60 * i
        s.wire((xl, yy), (xl + 60, yy))
        port(s, (xl, yy), net, 'io')
        supply(s, (xl + 60, yy), net)


def rails(s, ytop, ybot, tops, bots):
    """VDD rail at ytop over the PMOS sources (tops), VSS rail at ybot under the NMOS sources (bots)."""
    for y, pts, net in ((ytop, tops, 'VDD'), (ybot, bots, 'VSS')):
        for p in pts:
            s.wire(p, (p[0], y))
        xs = sorted(p[0] for p in pts)
        s.bus((xs[0], y), (xs[-1], y), [(x, y) for x in xs])
        supply(s, (xs[0], y), net)


def inverter(s, name, x, inp, out):
    """INV from the block netlist (<name>p over <name>n), bulks to the supplies; returns (gate, drain, Ps, Ns)."""
    dp, dn = DEV[f'{name}p'], DEV[f'{name}n']
    assert dp['nets'] == [out, inp, 'VDD', 'VDD'] and dn['nets'] == [out, inp, 'VSS', 'VSS'], name
    p, n, g, d = ginv(s, x, 0, dict(W=dp['w'], L=dp['l'], m=dp['m'], name=f'{name}p'),
                      dict(W=dn['w'], L=dn['l'], m=dn['m'], name=f'{name}n'))
    p.props['val'] = f'"{wl(dp)}"'
    n.props['val'] = f'"{wl(dn)}"'
    bulk(s, p, to='VDD')
    bulk(s, n, to='VSS')
    return g, d, p.pin('S'), n.pin('S')


def build_ls():
    s = Sch()
    xl, ytop, ybot = -400, -170, 170
    # INV1..3 in a row; ls out to the right edge
    xs = (200, 500, 800)
    nets = ('lg', 'lo1', 'lo2', 'ls')
    g, d, tops, bots = [], [], [], []
    for i, x in enumerate(xs):
        gi, di, ps, ns = inverter(s, f'L{i + 1}', x, nets[i], nets[i + 1])
        g.append(gi); d.append(di); tops.append(ps); bots.append(ns)
    s.wire(d[0], g[1]); s.wire(d[1], g[2])
    rails(s, ytop, ybot, tops, bots)
    # a0 -> Cc -> lg -> INV1; LRB's drain joins lg from below
    cc = DEV['Cc']
    assert cc['nets'] == ['a0', 'lg'], cc
    c = s.place('devices/capa.sym', -200, 0, rot=3, name='Cc', value=cc['value'], m='1')
    s.wire((xl, 0), c.pin('p'))
    port(s, (xl, 0), 'a0', 'in')
    s.bus(c.pin('m'), g[0], [(60, 0)])
    lrb = vmirror(s, 'LRB', 40, 330)
    check(lrb, D='lg', G='VSS', S='lf', B='VDD')
    s.wire(lrb.pin('D'), (60, 0))
    bulk(s, lrb, to='VDD')
    s.wire(lrb.pin('G'), (-20, 330)); supply(s, (-20, 330), 'VSS')
    # ls: out to the port, tapped down through R1 to lf; C1 on lf; lf back to LRB's source
    s.bus(d[2], (1100, 0), [(900, 0)])
    port(s, (1100, 0), 'ls', 'out')
    r1 = place(s, 'R1', 900, 330, rot=2)
    check(r1, M='ls', P='lf', B='VSS')
    s.wire((900, 0), r1.pin('M'))
    s.wire(r1.pin('B'), (940, 330)); supply(s, (940, 330), 'VSS')
    c1 = place(s, 'C1', 460, 500)
    check(c1, D='VSS', G='lf', S='VSS', B='VSS')
    xt = c1.pin('D')[0] + 20
    s.wire(c1.pin('D'), (xt, c1.pin('D')[1])); s.wire(c1.pin('B'), (xt, c1.pin('B')[1]))
    s.bus((xt, c1.pin('D')[1]), (xt, c1.pin('S')[1]), [(xt, c1.pin('B')[1])])
    s.wire(c1.pin('S'), (xt, c1.pin('S')[1]))
    supply(s, (xt, c1.pin('S')[1]), 'VSS')
    s.wire(lrb.pin('S'), (60, 420))
    s.wire(r1.pin('P'), (900, 420))
    s.bus((60, 420), (900, 420), [(c1.pin('G')[0], 420)])
    s.wire((c1.pin('G')[0], 420), c1.pin('G'))
    s.text(-300, 90, 'Cc 2 fF: M2-M3 metal fingers at the a0 tap', 0.3)
    s.text(-300, 120, '(no PDK device; LVS drops it)', 0.3)
    s.text(100, 440, 'lf', 0.3)
    s.text(80, -26, 'lg', 0.3)
    s.text(520, 560, 'C1 ~1 pF gate cap', 0.3)
    s.text(960, 300, 'R1 ~164k', 0.3)
    supplies(s, xl, 640)
    title(s, xl, -560, ['ls_ac: AC-coupled level shifter with duty-correcting feedback',
                        'a0 swings vg..VDD; Cc removes vg, INV1-3 restore the full rail (ls)',
                        'R1/C1 low-pass ls (tau ~0.16 us) back to lg through LRB: 3 inversions = negative DC '
                        'feedback, so mean(ls) sits at INV1\'s trip point (duty ~50 %)'])
    finish(s, 'ls_ac', ['VDD', 'VSS', 'a0', 'ls'], left=['a0'], right=['ls'], top=['VDD'], bottom=['VSS'],
           width=160, label='LS')


def build_tspc(cell, pre, clk, q):
    """TSPC toggle FF: three stacks (x, y, qb) + the Q inverter. Device D/G/S nets checked against the block."""
    s = Sch()
    loc = {f'{pre}n1': 'n1', f'{pre}x': 'x', f'{pre}y': 'y', f'{pre}n2': 'n2', f'{pre}n3': 'n3', f'{pre}qb': 'qb',
           clk: 'clk', q: 'q', 'VDD': 'VDD', 'VSS': 'VSS'}
    xl, ytop, ybot = -300, -240, 240
    X = (0, 360, 720)
    # stacks, outer device first: (name, column, centre y)
    stacks = [('p1', 0, -150), ('p2', 0, -60), ('n1', 0, 60),
              ('p3', 1, -60), ('n2', 1, 60), ('n3', 1, 150),
              ('p4', 2, -60), ('n4', 2, 60), ('n5', 2, 150)]
    m = {}
    for nm, col, cy in stacks:
        d = DEV[pre + nm]
        inst = place(s, pre + nm, X[col] - 20, cy, dev=dict(d, nets=[loc[n] for n in d['nets']]), inst_name=nm,
                     val=wl(d))
        bulk(s, inst, to='VDD' if nm[0] == 'p' else 'VSS')
        m[nm] = inst
    check(m['p1'], D='n1', G='qb', S='VDD', B='VDD'); check(m['p2'], D='x', G='clk', S='n1', B='VDD')
    check(m['n1'], D='x', G='qb', S='VSS', B='VSS'); check(m['p3'], D='y', G='clk', S='VDD', B='VDD')
    check(m['n2'], D='y', G='x', S='n2', B='VSS'); check(m['n3'], D='n2', G='clk', S='VSS', B='VSS')
    check(m['p4'], D='qb', G='y', S='VDD', B='VDD'); check(m['n4'], D='qb', G='clk', S='n3', B='VSS')
    check(m['n5'], D='n3', G='y', S='VSS', B='VSS')
    # stack wiring: series joints and the output node of each stage at y = 0
    s.wire(m['p1'].pin('D'), m['p2'].pin('S'))
    s.wire(m['n2'].pin('S'), m['n3'].pin('D'))
    s.wire(m['n4'].pin('S'), m['n5'].pin('D'))
    for pt, nt, xc in ((m['p2'], m['n1'], X[0]), (m['p3'], m['n2'], X[1]), (m['p4'], m['n4'], X[2])):
        s.bus(pt.pin('D'), nt.pin('D'), [(xc, 0)])
    # Q inverter
    dp, dn = DEV[f'{pre}qp'], DEV[f'{pre}qn']
    assert dp['nets'] == [q, f'{pre}qb', 'VDD', 'VDD'] and dn['nets'] == [q, f'{pre}qb', 'VSS', 'VSS']
    xq = 1080
    ip, in_, gq, dq = ginv(s, xq, 0, dict(W=dp['w'], L=dp['l'], name='qp'), dict(W=dn['w'], L=dn['l'], name='qn'))
    ip.props['val'] = f'"{wl(dp)}"'; in_.props['val'] = f'"{wl(dn)}"'
    bulk(s, ip, to='VDD'); bulk(s, in_, to='VSS')
    rails(s, ytop, ybot, [m['p1'].pin('S'), m['p3'].pin('S'), m['p4'].pin('S'), ip.pin('S')],
          [m['n1'].pin('S'), m['n3'].pin('S'), m['n5'].pin('S'), in_.pin('S')])
    s.wire(dq, (1250, 0)); port(s, (1250, 0), 'q', 'out')
    # x -> n2 gate
    s.route((X[0], 0), (240, 0), (240, 60), m['n2'].pin('G'), vfirst=False)
    # y -> p4 and n5 gates
    s.wire((X[1], 0), (640, 0))
    s.bus((640, -60), (640, 150), [(640, 0)])
    s.wire((640, -60), m['p4'].pin('G')); s.wire((640, 150), m['n5'].pin('G'))
    # qb -> Q inverter, and back over the top to p1 / n1 gates
    s.bus((X[2], 0), gq, [(780, 0)])
    s.route((780, 0), (780, -330), (-120, -330), (-120, -150), vfirst=True)
    s.wire((-120, -150), (-120, 60))
    s.wire((-120, -150), m['p1'].pin('G')); s.wire((-120, 60), m['n1'].pin('G'))
    # clk along the bottom, up to p2, p3 / n3 and n4
    s.bus((xl, 330), (600, 330), [(-80, 330), (280, 330)])
    port(s, (xl, 330), 'clk', 'in')
    s.route((-80, 330), (-80, -60), m['p2'].pin('G'), vfirst=True)
    s.bus((280, 330), (280, -60), [(280, 150)])
    s.wire((280, -60), m['p3'].pin('G')); s.wire((280, 150), m['n3'].pin('G'))
    s.route((600, 330), (600, 60), m['n4'].pin('G'), vfirst=True)
    for t, xx in (('x', 20), ('y', 380), ('qb', 740)):
        s.text(xx, -24, t, 0.3)
    supplies(s, xl, 520)
    title(s, xl, -640, [f'{cell}: TSPC toggle flip-flop (q = clk / 2)',
                        'true single-phase clock DFF with D = qb: clk low precharges y and passes qb into x; '
                        'the clk rising edge evaluates y and writes qb',
                        f'nfet / pfet {wl(DEV[pre + "n1"])} / {wl(DEV[pre + "p1"])} um, Q inverter {wl(dn)} / {wl(dp)}'])
    finish(s, cell, ['VDD', 'VSS', 'clk', 'q'], left=['clk'], right=['q'], top=['VDD'], bottom=['VSS'],
           width=160, label='TSPC /2')


def build_top():
    s = Sch()
    xl = -300
    ls = s.place('ls_ac.sym', 0, 0, name='xls')
    t1 = s.place('tspc_t1.sym', 300, 0, name='xd1')
    t2 = s.place('tspc_t2.sym', 600, 0, name='xd2')
    s.wire((xl, 0), ls.pin('a0')); port(s, (xl, 0), 'a0', 'in')
    # ls: on to the /2 clock, and up to the ls port (the TX driver's tap)
    tl = ((ls.pin('ls')[0] + t1.pin('clk')[0]) // 20 * 10, ls.pin('ls')[1])
    s.bus(ls.pin('ls'), t1.pin('clk'), [tl])
    s.route(tl, (tl[0], -200), (1100, -200), vfirst=True)
    port(s, (1100, -200), 'ls', 'out')
    s.wire(t1.pin('q'), t2.pin('clk'))
    g, d, ps, ns = inverter(s, 'B1', 900, 'q2', 'ck')
    s.wire(t2.pin('q'), g)
    supply(s, ps, 'VDD'); supply(s, ns, 'VSS')
    s.wire(d, (1100, 0)); port(s, (1100, 0), 'ck', 'out')
    for blk in (ls, t1, t2):
        supply(s, blk.pin('VDD'), 'VDD')
        supply(s, blk.pin('VSS'), 'VSS')
    for t, x in (('ls', 130), ('q1', 430), ('q2', 730)):
        s.text(x, -24, t, 0.3)
    supplies(s, xl, 260)
    title(s, xl, -400, ['lsdiv: a0 level shifter + TSPC /4 + clock buffer',
                        'ck = f(a0) / 4 at full rail, for the digital dividers; ls (the full-rail level-shifter output) '
                        'is a port for the TX driver tap; give it its own VDD/VSS branch '
                        'and ~10 pF decap (docs/lsdiv_design.md)',
                        'source: sim/lsdiv/lsdiv.py block()'])
    finish(s, 'lsdiv', PINS, left=['a0'], right=['ck', 'ls'], top=['VDD'], bottom=['VSS'], width=160, label='lsdiv')


def build():
    build_ls()
    build_tspc('tspc_t1', 'D1', 'ls', 'q1')
    build_tspc('tspc_t2', 'D2', 'q1', 'q2')
    build_top()


if __name__ == '__main__':
    build()
