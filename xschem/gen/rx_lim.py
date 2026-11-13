"""
rx_lim: the receiver limiter + comparator, one per arm (sim/rx/rx_lim.py block()).

  AC coupling L -> stage L (MLa / MLb, 10 kOhm) -> AC coupling C -> comparator: pair C1 / C2 (tail Ct) into PMOS
  diode loads C3 / C4 with the cross-coupled C5 / C6 (hysteresis), output stage C7-C10, inverters B1, B2 -> q

    python3 xschem/gen/rx_lim.py
"""
from rx_common import DEV, Sch, place, check, port, supply, finish, title, supplies, wl, couple_side, stage, \
    vbias_draw, mos_dev, inverter

C = 'rx_lim'
PINS = ['VDD', 'VSS', 'inp', 'inn', 'q', 'nb', 'enb']


def build():
    s = Sch()
    xl, xr = -1300, 4300
    yvb, yvgr, ynb = 330, 410, 520
    enb_g, vb0, vg0, nb0, _ = vbias_draw(s, C, -800)
    # coupling L from the ports
    ga, va, ra = couple_side(s, C, 'L', 'a', 0, (-40, -540), 'glp', 'inp')
    gb, vb_, rb = couple_side(s, C, 'L', 'b', 400, (360, -600), 'gln', 'inn', yout=-60)
    s.wire((xl, -540), (-40, -540)); port(s, (xl, -540), 'inp', 'in')
    s.wire((xl, -600), (360, -600)); port(s, (xl, -600), 'inn', 'in')
    # the ports' tracks pass over side a's cap column top: split nothing (they end at the column tops)
    x1 = 1200
    top, tom, tnb, gates = stage(s, C, x1, 'L', 'glp', 'gln', 'lp', 'ln', 'tL')
    s.route(ga, gates[0])
    s.route(gb, (gates[1][0] + 80, gb[1]), (gates[1][0] + 80, gates[1][1]), gates[1])
    gca, vca, rca = couple_side(s, C, 'C', 'a', x1 + 500, top, 'gcp', 'lp')
    s.route(tom, (x1 + 860, tom[1]))
    gcb, vcb, rcb = couple_side(s, C, 'C', 'b', x1 + 900, (x1 + 860, tom[1]), 'gcn', 'ln', yout=-60)
    # comparator
    xc = 2900
    c1, _ = mos_dev(s, C, 'C1', xc - 200, 0)
    c2, _ = mos_dev(s, C, 'C2', xc + 200, 0, flip=1)
    ct, _ = mos_dev(s, C, 'Ct', xc, 200)
    check(c1, D='ca', G='gcp', S='ct', B='VSS'); check(c2, D='cb', G='gcn', S='ct', B='VSS')
    check(ct, D='ct', G='nb', S='VSS', B='VSS')
    supply(s, ct.pin('S'), 'VSS')
    for m in (c1, c2):
        s.route(m.pin('S'), (m.pin('S')[0], 70), (xc + 20, 70))
    s.wire((xc + 20, 70), ct.pin('D'))
    s.route(ct.pin('G'), (xc - 60, 200), (xc - 60, ynb))
    s.route(gca, c1.pin('G'))
    s.route(gcb, (c2.pin('G')[0] + 80, gcb[1]), (c2.pin('G')[0] + 80, 0), c2.pin('G'))
    c3, _ = mos_dev(s, C, 'C3', xc - 260, -250)
    c5, _ = mos_dev(s, C, 'C5', xc - 120, -250, flip=1)
    c4, _ = mos_dev(s, C, 'C4', xc + 260, -250, flip=1)
    c6, _ = mos_dev(s, C, 'C6', xc + 120, -250)
    check(c3, D='ca', G='ca', S='VDD', B='VDD'); check(c5, D='ca', G='cb', S='VDD', B='VDD')
    check(c4, D='cb', G='cb', S='VDD', B='VDD'); check(c6, D='cb', G='ca', S='VDD', B='VDD')
    for m in (c3, c4, c5, c6):
        supply(s, m.pin('S'), 'VDD')
    xo = xc + 600
    c7, _ = mos_dev(s, C, 'C7', xo, -250)
    c8, _ = mos_dev(s, C, 'C8', xo + 300, -250)
    c9, _ = mos_dev(s, C, 'C9', xo, 100)
    c10, _ = mos_dev(s, C, 'C10', xo + 300, 100)
    check(c7, D='cx', G='cb', S='VDD', B='VDD'); check(c8, D='co', G='ca', S='VDD', B='VDD')
    check(c9, D='cx', G='cx', S='VSS', B='VSS'); check(c10, D='co', G='cx', S='VSS', B='VSS')
    for m in (c7, c8):
        supply(s, m.pin('S'), 'VDD')
    for m in (c9, c10):
        supply(s, m.pin('S'), 'VSS')
    yl = -150
    # ca: C3 drain + gate (diode), C5 drain, C1 drain, C6 gate, C8 gate
    s.wire(c3.pin('D'), (c3.pin('D')[0], yl)); s.wire(c5.pin('D'), (c5.pin('D')[0], yl))
    s.wire(c1.pin('D'), (c1.pin('D')[0], yl))
    s.wire(c3.pin('G'), (xc - 300, -250))
    s.bus((xc - 300, -380), (xc - 300, yl), [(xc - 300, -250)])
    s.route(c6.pin('G'), (xc + 60, -250), (xc + 60, -90), (xc - 200, -90), (xc - 200, yl))
    s.bus((xc - 300, yl), (xc - 140, yl), [(xc - 240, yl), (xc - 200, yl), (xc - 180, yl)])
    s.route((xc - 300, -380), (xo + 240, -380), (xo + 240, -250), c8.pin('G'))
    s.text(xc - 290, yl - 24, 'ca', 0.3)
    # cb: C4 drain + gate, C6 drain, C2 drain, C5 gate, C7 gate
    s.wire(c4.pin('D'), (c4.pin('D')[0], yl)); s.wire(c6.pin('D'), (c6.pin('D')[0], yl))
    s.wire(c2.pin('D'), (c2.pin('D')[0], yl))
    s.route(c4.pin('G'), (xc + 300, -250), (xc + 300, yl))
    s.route(c5.pin('G'), (xc - 60, -250), (xc - 60, -120), (xc + 200, -120), (xc + 200, yl))
    s.bus((xc + 140, yl), (xo - 80, yl), [(xc + 180, yl), (xc + 200, yl), (xc + 240, yl), (xc + 300, yl)])
    s.route((xo - 80, yl), (xo - 80, -250), c7.pin('G'))
    s.text(xc + 320, yl - 24, 'cb', 0.3)
    # cx: C7 drain = C9 drain, C9 gate, C10 gate
    s.bus(c7.pin('D'), c9.pin('D'), [(xo + 20, 0), (xo + 20, 30)])
    s.route(c9.pin('G'), (xo - 60, 100), (xo - 60, 0), (xo + 20, 0))
    s.route((xo + 20, 30), (xo + 200, 30), (xo + 200, 100), c10.pin('G'))
    s.text(xo + 30, -60, 'cx', 0.3)
    # co -> B1 -> cq -> B2 -> q
    s.bus(c8.pin('D'), c10.pin('D'), [(xo + 320, -75)])
    g1, d1, _, _ = inverter(s, C, 'B1', xo + 550, -75, 'co', 'cq')
    g2, d2, _, _ = inverter(s, C, 'B2', xo + 800, -75, 'cq', 'q')
    s.wire((xo + 320, -75), g1); s.wire(d1, g2); s.wire(d2, (xr, -75)); port(s, (xr, -75), 'q', 'out')
    s.text(xo + 330, -100, 'co', 0.3); s.text(xo + 600, -100, 'cq', 0.3)
    # vb / vgr / nb lines
    for pts, y in ((vb0 + va + vb_ + vca + vcb, yvb), (vg0 + ra + rb + rca + rcb, yvgr),
                   ([nb0, tnb, (xc - 60, ynb)], ynb)):
        xs = sorted({p[0] for p in pts})
        s.bus((xs[0], y), (xs[-1], y), sorted(set(pts)))
    s.wire((xl, ynb), (nb0[0], ynb)); port(s, (xl, ynb), 'nb', 'in')
    s.route(enb_g, (enb_g[0] - 40, enb_g[1]), (enb_g[0] - 40, -420), (xl, -420)); port(s, (xl, -420), 'enb', 'in')
    s.text(-700, yvb - 24, 'vb', 0.3); s.text(-700, yvgr - 24, 'vgr', 0.3); s.text(-700, ynb - 24, 'nb', 0.3)
    supplies(s, xl, 900)
    d = DEV[C]
    title(s, xl, -900, ['rx_lim: limiter stage + comparator with hysteresis (one per arm)',
                        f"stage L {wl(d['MLa'])} um, 25 uA, 10 kOhm (about 9 dB); comparator pair {wl(d['C1'])}, "
                        f"diode loads {wl(d['C3'])}, cross-coupled {wl(d['C5'])} (k = 1.7: hysteresis about +-35 mV)",
                        'both inputs AC-coupled (offsets only shift the thresholds); q full swing to uo[4] / uo[5]; '
                        'source: sim/rx/rx_lim.py block()'])
    finish(s, C, PINS, left=['inp', 'inn', 'nb', 'enb'], right=['q'], top=['VDD'], bottom=['VSS'], width=160,
           label='lim')


if __name__ == '__main__':
    build()
