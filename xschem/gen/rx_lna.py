"""
rx_lna: the receiver LNA (sim/rx/rx_lna.py block()), two sheets:

  rx_lna2 : the second stage, one per arm: NMOS pair, poly loads, tail mirrored from nb
  rx_lna  : stage 1 (the OOK receiver's amp_dp, ported): NMOS pair M1 / M2, poly loads RLp / RLn, tail Mt; the
            pins self-biased at vcm through Rgp / Rgn; vcm from the gated divider Rv1 / Rv2 (Mvs, gate enb) and its
            decap Cvcm; the two second stages x2i / x2q drive the I and Q mixers

    python3 xschem/gen/rx_lna.py
"""
from rx_common import DEV, Sch, place, check, bulk, port, supply, finish, title, supplies, dpair, wl, mos_c

PINS2 = ['VDD', 'VSS', 'ip', 'im', 'op', 'om', 'nb']
PINS = ['VDD', 'VSS', 'inp', 'inn', 'oip', 'oin', 'oqp', 'oqn', 'nb', 'enb']


def build_lna2():
    c = 'rx_lna2'
    s = Sch()
    xl, xr = -500, 500
    p = dpair(s, c, 0, 0, 'M1', 'M2', 'Mt', 'RLp', 'RLn', 'ip', 'im', 'op', 'om', 'tail')
    s.wire((xl, 0), p['ip']); port(s, (xl, 0), 'ip', 'in')
    s.route((xl, 330), (220, 330), (220, 0), p['im']); port(s, (xl, 330), 'im', 'in')
    s.route((xl, 200), p['nb']); port(s, (xl, 200), 'nb', 'in')
    s.route(p['om'], (-100, -100), (-300, -100), (-300, -420), (xr, -420)); port(s, (xr, -420), 'om', 'out')
    s.route(p['op'], (100, -100), (300, -100), (300, -360), (xr, -360)); port(s, (xr, -360), 'op', 'out')
    supplies(s, xl, 520)
    d = DEV[c]
    title(s, xl, -760, ['rx_lna2: LNA second stage (one per arm)',
                        f"NMOS pair {wl(d['M1'])} um, poly loads, tail {wl(d['Mt'])} from nb; gates DC-coupled to "
                        'stage 1 (~2.15 V); op = !ip side', 'source: sim/rx/rx_lna.py stage2()'])
    finish(s, c, PINS2, left=['ip', 'im', 'nb'], right=['op', 'om'], top=['VDD'], bottom=['VSS'], width=160,
           label='lna2')


def build_lna():
    c = 'rx_lna'
    s = Sch()
    xl, xr = -900, 1500
    p = dpair(s, c, 0, 0, 'M1', 'M2', 'Mt', 'RLp', 'RLn', 'inp', 'inn', 'outp', 'outn', 'tail')
    yv = 480                                       # the vcm line
    # inp: port -> gate, tap down through Rgp to vcm
    s.bus((xl, 0), p['ip'], [(-300, 0)])
    port(s, (xl, 0), 'inp', 'in')
    rg = place(s, c, 'Rgp', -300, 150, rot=2)
    check(rg, M='inp', P='vcm', B='VSS')
    s.wire((-300, 0), rg.pin('M'))
    s.wire(rg.pin('P'), (-300, yv))
    s.wire(rg.pin('B'), (rg.pin('B')[0] + 20, rg.pin('B')[1])); supply(s, (rg.pin('B')[0] + 20, rg.pin('B')[1]), 'VSS')
    # inn: port at the bottom left, under the vcm line, up the right of the pair to its gate, tap Rgn
    rn = place(s, c, 'Rgn', 300, 150, rot=2)
    check(rn, M='inn', P='vcm', B='VSS')
    s.route((xl, 620), (240, 620), (240, 0), p['im'])
    port(s, (xl, 620), 'inn', 'in')
    s.route((240, 60), (300, 60), rn.pin('M'))
    s.wire(rn.pin('P'), (300, yv))
    s.wire(rn.pin('B'), (rn.pin('B')[0] + 20, rn.pin('B')[1])); supply(s, (rn.pin('B')[0] + 20, rn.pin('B')[1]), 'VSS')
    # the inn wire passes (240, 60): split it there
    s.wires = [w for w in s.wires if not (w[0] == (240, 620) and w[1] == (240, 0)) and not (w[0] == (240, 0) and w[1] == (240, 620))]
    s.bus((240, 620), (240, 0), [(240, 60)])
    # vcm: Mvs (gate enb) -> vt -> Rv1 -> vcm -> Rv2 -> VSS, decap Cvcm; at the left
    xv = -600
    ms = place(s, c, 'Mvs', xv - 20, 120)
    check(ms, D='vt', G='enb', S='VDD', B='VDD')
    bulk(s, ms, to='VDD'); supply(s, ms.pin('S'), 'VDD')
    s.route((xl, 120), ms.pin('G')); port(s, (xl, 120), 'enb', 'in')
    r1 = place(s, c, 'Rv1', xv, 300, rot=2)        # M = vt on top
    check(r1, M='vt', P='vcm', B='VSS')
    s.wire(ms.pin('D'), r1.pin('M'))
    r2 = place(s, c, 'Rv2', xv, 660, rot=2)        # M = vcm on top, P = VSS below
    check(r2, M='vcm', P='VSS', B='VSS')
    supply(s, r2.pin('P'), 'VSS')
    for r in (r1, r2):
        s.wire(r.pin('B'), (r.pin('B')[0] + 20, r.pin('B')[1])); supply(s, (r.pin('B')[0] + 20, r.pin('B')[1]), 'VSS')
    s.route(r1.pin('P'), (xv, yv))
    s.wire((xv, yv), r2.pin('M'))
    cv = place(s, c, 'Cvcm', xv - 160, yv + 120)
    check(cv, D='VSS', G='vcm', S='VSS', B='VSS')
    s.route(cv.pin('G'), (xv - 220, yv + 120), (xv - 220, yv))
    xt = cv.pin('D')[0] + 20
    s.wire(cv.pin('D'), (xt, cv.pin('D')[1])); s.wire(cv.pin('B'), (xt, cv.pin('B')[1]))
    s.bus((xt, cv.pin('D')[1]), (xt, cv.pin('S')[1]), [(xt, cv.pin('B')[1])])
    s.wire(cv.pin('S'), (xt, cv.pin('S')[1])); supply(s, (xt, cv.pin('S')[1]), 'VSS')
    s.bus((xv - 220, yv), (300, yv), [(xv, yv), (-300, yv)])
    s.text(xv - 200, yv - 30, 'vcm', 0.3)
    # tail gate: nb from a port, under the pair
    s.route((xl, 280), (-120, 280), (-120, 200), p['nb'])
    port(s, (xl, 280), 'nb', 'in')
    # the two second stages, to the right; outp / outn from the loads
    x2i = s.place('rx_lna2.sym', 900, -150, name='x2i')
    x2q = s.place('rx_lna2.sym', 900, 350, name='x2q')
    xo1, xo2 = 600, 660
    s.route(p['om'], (-100, -100), (-260, -100), (-260, -420), (xo2, -420))
    s.route(p['op'], (100, -100), (360, -100), (360, -360), (xo1, -360))
    # outp -> both ip, outn -> both im
    s.bus((xo1, -360), (xo1, x2q.pin('ip')[1]), [(xo1, x2i.pin('ip')[1])])
    s.wire((xo1, x2i.pin('ip')[1]), x2i.pin('ip')); s.wire((xo1, x2q.pin('ip')[1]), x2q.pin('ip'))
    s.bus((xo2, -420), (xo2, x2q.pin('im')[1]), [(xo2, x2i.pin('im')[1])])
    s.wire((xo2, x2i.pin('im')[1]), x2i.pin('im')); s.wire((xo2, x2q.pin('im')[1]), x2q.pin('im'))
    s.text(380, -390, 'outp', 0.3); s.text(380, -450, 'outn', 0.3)
    for blk, a, b in ((x2i, 'oip', 'oin'), (x2q, 'oqp', 'oqn')):
        s.wire(blk.pin('op'), (xr, blk.pin('op')[1])); port(s, (xr, blk.pin('op')[1]), a, 'out')
        s.wire(blk.pin('om'), (xr, blk.pin('om')[1])); port(s, (xr, blk.pin('om')[1]), b, 'out')
        s.wire(blk.pin('nb'), (720, blk.pin('nb')[1]))
        supply(s, blk.pin('VDD'), 'VDD'); supply(s, blk.pin('VSS'), 'VSS')
    s.bus((720, x2i.pin('nb')[1]), (720, 820), [(720, x2q.pin('nb')[1])])
    s.route((720, 820), (-120, 820), (-120, 280))
    supplies(s, xl, 900)
    d = DEV[c]
    title(s, xl, -900, ['rx_lna: two-stage LNA, one stage-2 per mixer',
                        f"stage 1: NMOS pair {wl(d['M1'])} um (the OOK amp_dp, ported), loads {d['RLp']['l']:g} um "
                        f"ppolyf_u, tail {wl(d['Mt'])}; the pins sit at vcm (~1.37 V) through Rgp / Rgn",
                        'stage 2 (x2i, x2q) gives each mixer its own driver: no I/Q cross-loading; '
                        'source: sim/rx/rx_lna.py block()'])
    finish(s, c, PINS, left=['inp', 'inn', 'nb', 'enb'], right=['oip', 'oin', 'oqp', 'oqn'], top=['VDD'],
           bottom=['VSS'], width=200, label='lna')


def build():
    build_lna2()
    build_lna()


if __name__ == '__main__':
    build()
