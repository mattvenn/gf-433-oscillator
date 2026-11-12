"""
rx_bias: the receiver's constant-gm reference (sim/rx/rx_bias.py block()).

  MN1 (diode, the unit device) on nb, MN2 (K x MN1) with Rb in its source, PMOS 1:1 mirror MP1 / MP2 from vh,
  vh = VDD through the header Msw (gate enb); start-up MS1-MS3; Moff / Moff2 hold nb and x low when disabled;
  Cnb decouples nb; the inverter Ie makes enb from en.

    python3 xschem/gen/rx_bias.py
"""
from rx_common import DEV, Sch, place, check, bulk, port, supply, finish, title, supplies, wl, stub, net, \
    mos_dev, capdev, resdev, inverter

C = 'rx_bias'
PINS = ['VDD', 'VSS', 'en', 'enb', 'nb']


def build():
    s = Sch()
    xl, xr = -900, 1000
    yvh, yn2, ynb, ybot, yen = -330, -110, -40, 460, -600
    msw, _ = mos_dev(s, C, 'Msw', 0, -440)
    mp1, _ = mos_dev(s, C, 'MP1', -200, -200, flip=1)
    mp2, _ = mos_dev(s, C, 'MP2', 200, -200)
    mn1, _ = mos_dev(s, C, 'MN1', -200, 60, flip=1)
    mn2, _ = mos_dev(s, C, 'MN2', 200, 60)
    ms1, _ = mos_dev(s, C, 'MS1', 560, -200)
    ms2, _ = mos_dev(s, C, 'MS2', 560, 60)
    ms3, _ = mos_dev(s, C, 'MS3', 380, 330, flip=1)
    moff, _ = mos_dev(s, C, 'Moff', -480, 560)
    moff2, _ = mos_dev(s, C, 'Moff2', 760, 200, flip=1)
    check(msw, D='vh', G='enb', S='VDD', B='VDD')
    check(mp1, D='nb', G='n2', S='vh', B='VDD'); check(mp2, D='n2', G='n2', S='vh', B='VDD')
    check(mn1, D='nb', G='nb', S='VSS', B='VSS'); check(mn2, D='n2', G='nb', S='nr', B='VSS')
    check(ms1, D='x', G='VSS', S='vh', B='VDD'); check(ms2, D='x', G='nb', S='VSS', B='VSS')
    check(ms3, D='n2', G='x', S='nb', B='VSS')
    check(moff, D='nb', G='enb', S='VSS', B='VSS'); check(moff2, D='x', G='enb', S='VSS', B='VSS')
    for m in (msw,):
        supply(s, m.pin('S'), 'VDD')
    for m in (mn1, ms2, moff, moff2):
        supply(s, m.pin('S'), 'VSS')
    rt, rb, _ = resdev(s, C, 'Rb', 220, 200, 'nr')
    s.wire(mn2.pin('S'), rt)
    supply(s, rb, 'VSS')
    g1 = stub(s, ms1.pin('G'), -40); supply(s, g1, 'VSS')
    # vh rail
    for m in (mp1, mp2, ms1):
        s.wire(m.pin('S'), (m.pin('S')[0], yvh))
    s.wire(msw.pin('D'), (msw.pin('D')[0], yvh))
    xs = sorted({mp1.pin('S')[0], mp2.pin('S')[0], ms1.pin('S')[0], msw.pin('D')[0]})
    s.bus((xs[0], yvh), (xs[-1], yvh), [(x, yvh) for x in xs])
    s.text(-160, yvh - 30, 'vh', 0.3)
    # n2: MP1 / MP2 gates, MP2 drain = MN2 drain, MS3 drain
    s.bus(mp1.pin('G'), mp2.pin('G'), [(100, mp1.pin('G')[1])])
    s.wire((100, mp1.pin('G')[1]), (100, yn2))
    xd = mp2.pin('D')[0]
    s.bus(mp2.pin('D'), mn2.pin('D'), [(xd, yn2)])
    s.wire(ms3.pin('D'), (ms3.pin('D')[0], yn2))
    s.bus((100, yn2), (ms3.pin('D')[0], yn2), [(xd, yn2)])
    s.text(260, yn2 - 24, 'n2', 0.3)
    # nb: MP1 drain = MN1 drain (tap at ynb), MN1 / MN2 gates (tap at x = -120), the bottom nb line
    xn = mp1.pin('D')[0]
    s.bus(mp1.pin('D'), mn1.pin('D'), [(xn, ynb)])
    s.bus(mn1.pin('G'), mn2.pin('G'), [(-120, mn1.pin('G')[1])])
    s.bus((-120, ynb), (-120, ybot), [(-120, mn1.pin('G')[1])])
    s.wire((xn, ynb), (-120, ynb))
    s.text(-200, ynb - 24, 'nb', 0.3)
    s.route(ms2.pin('G'), (500, ms2.pin('G')[1]), (500, ybot))
    s.wire(ms3.pin('S'), (ms3.pin('S')[0], ybot))
    s.wire(moff.pin('D'), (moff.pin('D')[0], ybot))
    gc, _ = capdev(s, C, 'Cnb', -300, 560)
    s.route(gc, (gc[0] - 40, gc[1]), (gc[0] - 40, ybot))
    xs = sorted({-700, -120, 500, ms3.pin('S')[0], moff.pin('D')[0], gc[0] - 40})
    s.bus((xs[0], ybot), (xs[-1], ybot), [(x, ybot) for x in xs])
    s.wire((-700, ybot), (xl, ybot)); port(s, (xl, ybot), 'nb', 'out')
    # x: MS1 drain = MS2 drain, MS3 gate, Moff2 drain
    xx = ms1.pin('D')[0]
    s.bus(ms1.pin('D'), ms2.pin('D'), [(xx, -60)])
    s.bus((xx, -60), (moff2.pin('D')[0], -60), [(640, -60)])
    s.wire(moff2.pin('D'), (moff2.pin('D')[0], -60))
    s.route((640, -60), (640, ms3.pin('G')[1]), ms3.pin('G'))
    s.text(650, -90, 'x', 0.3)
    # en -> Ie -> enb: the header, Moff, Moff2, the port
    g, d, _, _ = inverter(s, C, 'Ie', -560, -440, 'en', 'enb')
    s.wire((xl, -440), g); port(s, (xl, -440), 'en', 'in')
    s.route(d, (-460, d[1]), (-460, yen))
    s.route(msw.pin('G'), (-60, msw.pin('G')[1]), (-60, yen))
    s.bus((-460, yen), (xr, yen), [(-60, yen), (900, yen)])
    port(s, (xr, yen), 'enb', 'out')
    s.bus((900, yen), (900, 700), [(900, moff2.pin('G')[1])])
    s.wire((900, moff2.pin('G')[1]), moff2.pin('G'))
    s.route((900, 700), (-560, 700), (-560, moff.pin('G')[1]), moff.pin('G'))
    supplies(s, xl, 820)
    d = DEV[C]
    title(s, xl, -940, ['rx_bias: constant-gm reference for the receiver',
                        f"MN1 {wl(d['MN1'])}, MN2 {wl(d['MN2'])} (K = 4), Rb {d['Rb']['w']:g}/{d['Rb']['l']:g} um "
                        'ppolyf_u (5.2 kOhm): gm of the unit = 1 / Rb (x const), unit current ~25 uA',
                        'every tail mirrors nb, so each stage gain gm x RL is a resistor ratio; '
                        'en = 0: header off, nb and x held low; source: sim/rx/rx_bias.py block()'])
    finish(s, C, PINS, left=['en'], right=['nb', 'enb'], top=['VDD'], bottom=['VSS'], width=160, label='bias')


if __name__ == '__main__':
    build()
