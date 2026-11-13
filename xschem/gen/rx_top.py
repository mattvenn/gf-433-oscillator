"""
rx_top: the receiver (option B) top level (sim/rx/rx_top.py top()).

  inp / inn -> rx_lna (I and Q outputs) -> rx_mix x2 (LOs from rx_lo: I from ls, Q from the ring node aq through
  rx_lsq) -> rx_bb x2 -> rx_lim x2 -> q_i / q_q; rx_bias: nb and enb from en; DC: supply decap.

    python3 xschem/gen/rx_top.py
"""
from rx_common import DEV, Sch, place, check, port, supply, finish, title, supplies, capdev

C = 'rx_top'
PINS = ['VDD', 'VSS', 'inp', 'inn', 'ls', 'aq', 'en', 'q_i', 'q_q']


def lr(s, a, b, xm):
    """a (output pin) -> b (input pin) with one vertical at xm."""
    s.route(a, (xm, a[1]), (xm, b[1]), b)


def build():
    s = Sch()
    xl, xr = -900, 3500
    ynb, yen = 1100, 1160
    b = s.place('rx_bias.sym', -500, 800, name='xb')
    ln = s.place('rx_lna.sym', 0, 0, name='xlna')
    lo = s.place('rx_lo.sym', 0, -800, name='xlo')
    mi = s.place('rx_mix.sym', 1000, -300, name='xmi')
    mq = s.place('rx_mix.sym', 1000, 400, name='xmq')
    bi = s.place('rx_bb.sym', 1700, -300, name='xbbi')
    bq = s.place('rx_bb.sym', 1700, 400, name='xbbq')
    li = s.place('rx_lim.sym', 2500, -300, name='xli')
    lq = s.place('rx_lim.sym', 2500, 400, name='xlq')
    blocks = (b, ln, lo, mi, mq, bi, bq, li, lq)
    for blk in blocks:
        supply(s, blk.pin('VDD'), 'VDD'); supply(s, blk.pin('VSS'), 'VSS')
    for net in ('inp', 'inn'):
        s.wire((xl, ln.pin(net)[1]), ln.pin(net)); port(s, (xl, ln.pin(net)[1]), net, 'in')
    for net in ('ls', 'aq'):
        s.wire((xl, lo.pin(net)[1]), lo.pin(net)); port(s, (xl, lo.pin(net)[1]), net, 'in')
    q = lo.pin('qenb')
    s.wire(q, (q[0] - 40, q[1])); supply(s, (q[0] - 40, q[1]), 'VSS')
    s.text(q[0] - 300, q[1] + 10, 'qenb = VSS: Q tap copy always on', 0.25)
    # LNA -> mixers
    lr(s, ln.pin('oip'), mi.pin('rfp'), 500); lr(s, ln.pin('oin'), mi.pin('rfn'), 540)
    lr(s, ln.pin('oqp'), mq.pin('rfp'), 580); lr(s, ln.pin('oqn'), mq.pin('rfn'), 620)
    # LOs -> mixers
    for k, (src, dst) in enumerate((('lo_i', (mi, 'lo')), ('lob_i', (mi, 'lob')), ('lo_q', (mq, 'lo')),
                                    ('lob_q', (mq, 'lob')))):
        lr(s, lo.pin(src), dst[0].pin(dst[1]), 660 + 40 * k)
    # mixers -> bb -> lim
    for m, bb, lm in ((mi, bi, li), (mq, bq, lq)):
        lr(s, m.pin('bbp'), bb.pin('inp'), 1260); lr(s, m.pin('bbn'), bb.pin('inn'), 1300)
        lr(s, bb.pin('outp'), lm.pin('inp'), 2060); lr(s, bb.pin('outn'), lm.pin('inn'), 2100)
    s.wire(li.pin('q'), (xr, li.pin('q')[1])); port(s, (xr, li.pin('q')[1]), 'q_i', 'out')
    s.wire(lq.pin('q'), (xr, lq.pin('q')[1])); port(s, (xr, lq.pin('q')[1]), 'q_q', 'out')
    # en: the bias and the LO buffers
    e = b.pin('en')
    s.route((xl, e[1]), e); port(s, (xl, e[1]), 'en', 'in')
    s.route((xl + 100, e[1]), (xl + 100, lo.pin('en')[1]), lo.pin('en'))
    s.wires = [w for w in s.wires if w[:2] != ((xl, e[1]), e)]
    s.bus((xl, e[1]), e, [(xl + 100, e[1])])
    # nb / enb lines at the bottom, drops to every user
    nbx, enx = [], []
    for k, blk in enumerate((ln, bi, bq, li, lq)):
        for net, y, acc, dx in (('nb', ynb, nbx, 60), ('enb', yen, enx, 100)):
            p = blk.pin(net)
            x = p[0] - dx - (80 if blk in (bi, li) else 0)
            s.route(p, (x, p[1]), (x, y))
            acc.append((x, y))
    for net, y, acc in (('nb', ynb, nbx), ('enb', yen, enx)):
        p = b.pin(net)
        s.route(p, (p[0] + 60 + (40 if net == 'enb' else 0), p[1]), (p[0] + 60 + (40 if net == 'enb' else 0), y))
        acc.append((p[0] + 60 + (40 if net == 'enb' else 0), y))
        xs = sorted({a[0] for a in acc})
        s.bus((xs[0], y), (xs[-1], y), acc)
    g, _ = capdev(s, C, 'DC', 3000, 900)
    s.wire(g, (g[0] - 40, g[1])); supply(s, (g[0] - 40, g[1]), 'VDD')
    d = DEV[C]['DC']
    s.text(2900, 1000, f"DC supply decap ~{d['w'] * d['l'] * d['m'] * 4.07e-3:.1f} pF", 0.3)
    supplies(s, xl, 1350)
    title(s, xl, -1300, ['rx_top: 433.92 MHz zero-IF receiver (option B)',
                         'ua pins -> two-stage LNA -> I / Q passive mixers (LO: ls and the a2 tap, 72 deg apart) -> '
                         'baseband (LPF ~145 kHz, HPF ~9 kHz) -> limiter + comparator -> q_i / q_q (uo[4] / uo[5])',
                         'about 7 mA at tt; the RP2350 PIO decodes q_i / q_q as a quadrature counter; '
                         'source: sim/rx/rx_top.py'])
    finish(s, C, PINS, left=['inp', 'inn', 'ls', 'aq', 'en'], right=['q_i', 'q_q'], top=['VDD'], bottom=['VSS'],
           width=200, label='rx_top')


if __name__ == '__main__':
    build()
