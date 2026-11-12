"""
rx_lo: the receiver LO path (sim/rx/rx_lo.py block()), three sheets:

  rx_lobuf : x = NAND2(in, en); the TX driver's splitter topology on x (T, A1 / A2 to a, B1 + an always-on
             transmission gate to b, weak cross-coupled keeper XA / XB); two arms NAND2(., en) + 3 inverters:
             lo = in & en, lob = !in & en (both low when en = 0)
  rx_lsq   : the Q tap: a copy of lsdiv's level shifter (ls_ac) with the same load as lsdiv's ls node (a dummy
             tspc_t1 and a dummy TX tap inverter TT), on vq behind the header Hq (gate qenb); Dq holds lsq low when off;
             Cq decouples vq
  rx_lo    : rx_lsq on aq + an rx_lobuf for I (on ls) and for Q (on lsq)

    python3 xschem/gen/rx_lo.py
"""
from rx_common import DEV, Sch, place, check, bulk, port, supply, finish, title, supplies, wl, stub, net, \
    mos_dev, capdev, inverter, nand2


def build_lobuf():
    c = 'rx_lobuf'
    s = Sch()
    xl, xr = -1100, 3100
    # input gate x = NAND2(in, en)
    pa, pb, po = nand2(s, c, ('G0a', 'G0b', 'G0c', 'G0d'), -400, 0, 'in', 'en', 'x', 'g0s')
    s.wire((xl, pa[1]), pa); port(s, (xl, pa[1]), 'in', 'in')
    # splitter (the tx_split drawing): T at x = 0 on the a row (y 0), B1 on the b row (y 900)
    ya, yb, ybl = 0, 900, 1100
    g, d, _, _ = inverter(s, c, 'T', 0, ya, 'x', 't')
    s.route(po, (-200, po[1]), (-200, ya), g)
    s.text(-260, po[1] - 24, 'x', 0.3)
    ga1, da1, _, _ = inverter(s, c, 'A1', 300, ya, 't', 'ta')
    ga2, da2, _, _ = inverter(s, c, 'A2', 600, ya, 'ta', 'a')
    gb1, db1, _, _ = inverter(s, c, 'B1', 300, yb, 't', 'tb')
    s.bus(d, ga1, [(100, ya)])
    s.route((100, ya), (100, yb), gb1)
    s.wire(da1, ga2)
    xt, yt = 600, yb + 80
    tp = place(s, c, 'TGp', xt - 60, yt, hide=True)
    tn = place(s, c, 'TGn', xt + 60, yt, rot=2, hide=True)
    check(tp, D='b', G='VSS', S='tb', B='VDD'); check(tn, D='b', G='VDD', S='tb', B='VSS')
    s.wire(tp.pin('B'), (xt - 20, yt)); supply(s, (xt - 20, yt), 'VDD')
    s.wire(tn.pin('B'), (xt + 20, yt)); supply(s, (xt + 20, yt), 'VSS')
    s.wire(tp.pin('G'), (xt - 120, yt)); supply(s, (xt - 120, yt), 'VSS')
    s.wire(tn.pin('G'), (xt + 120, yt)); supply(s, (xt + 120, yt), 'VDD')
    top, bot = yt - 50, yt + 50
    s.route(tp.pin('S'), (xt - 40, top), (xt, top)); s.route(tn.pin('S'), (xt + 40, top), (xt, top))
    s.route(db1, (xt, yb), (xt, top))
    s.route(tp.pin('D'), (xt - 40, bot), (xt, bot)); s.route(tn.pin('D'), (xt + 40, bot), (xt, bot))
    s.route((xt, bot), (xt, ybl))
    xk, xa_, xb_ = 1100, 950, 1250
    gxb, dxb, _, _ = inverter(s, c, 'XB', xk, 300, 'a', 'b')
    gxa, dxa, _, _ = inverter(s, c, 'XA', xk, 600, 'b', 'a', flip=True)
    xe = 1400                                    # the end of the a / b lines, into the arms
    s.bus(da2, (xe, ya), [(xa_, ya)])
    s.bus((xa_, ya), (xa_, 600), [(xa_, 300)])
    s.wire((xa_, 300), gxb); s.wire(dxa, (xa_, 600))
    s.bus((xt, ybl), (xe, ybl), [(xb_, ybl)])
    s.bus((xb_, 300), (xb_, ybl), [(xb_, 600)])
    s.wire(dxb, (xb_, 300)); s.wire(gxa, (xb_, 600))
    s.text(xt - 230, yt - 30, 'TGp', 0.3); s.text(xt - 230, yt + 6, wl(DEV[c]['TGp']), 0.3)
    s.text(xt + 140, yt - 30, 'TGn', 0.3); s.text(xt + 140, yt + 6, wl(DEV[c]['TGn']), 0.3)
    for t, x, y in (('t', 120, ya - 24), ('ta', 420, ya - 24), ('tb', 420, yb - 24), ('a', 780, ya - 24),
                    ('b', 780, ybl - 24)):
        s.text(x, y, t, 0.3)
    # arms: NAND2(a | b, en) + 3 inverters -> lo | lob
    for arm, yy, src, out in (('P', ya, 'a', 'lo'), ('N', ybl, 'b', 'lob')):
        xa0 = 1900
        aa, ab, ao = nand2(s, c, (f'{arm}Ga', f'{arm}Gb', f'{arm}Gc', f'{arm}Gd'), xa0, yy, src, 'en',
                           f'{arm}y0', f'{arm}gs')
        s.wire((xe, yy), aa)
        prev = ao
        for j in range(1, 4):
            x = 2050 + j * 250
            gi, di, _, _ = inverter(s, c, f'{arm}{j}', x, ao[1], f'{arm}y{j - 1}', out if j == 3 else f'{arm}y{j}',
                                    h=100)
            s.wire(prev, gi)
            prev = di
        s.wire(prev, (xr, prev[1])); port(s, (xr, prev[1]), out, 'out')
    # en: the input NAND and both arms, from a line along the top
    yen = -520
    s.route(pb, (-760, pb[1]), (-760, yen))
    for arm, yy in (('P', ya), ('N', ybl)):
        pass
    p_en = (1600, ya + 100)
    n_en = (1600, ybl + 100)
    s.bus((-760, yen), (1550, yen), [])
    s.bus((1550, yen), (1550, n_en[1]), [(1550, p_en[1])])
    s.wire((1550, p_en[1]), p_en); s.wire((1550, n_en[1]), n_en)
    s.route((-760, yen), (xl, yen)) if False else None
    s.wires = [w for w in s.wires if not (w[0] == (-760, yen) and w[1] == (1550, yen))]
    s.bus((xl, yen), (1550, yen), [(-760, yen)])
    port(s, (xl, yen), 'en', 'in')
    supplies(s, xl, 1500)
    d = DEV[c]
    title(s, xl, -900, ['rx_lobuf: LO buffer with enable (one per arm)',
                        'x = NAND2(in, en) -> the TX splitter on x (a = in, b = !in, edges pulled together by the keeper) '
                        '-> two arms NAND2(., en) + 3 inverters: lo = in & en, lob = !in & en',
                        f"arm inverters N {' / '.join(wl(d[f'P{j}n']) for j in (1, 2, 3))} um; en = 0: x high, "
                        'every mixer switch off, nothing after the first NAND toggles; source: sim/rx/rx_lo.py lobuf()'])
    finish(s, c, ['VDD', 'VSS', 'in', 'en', 'lo', 'lob'], left=['in', 'en'], right=['lo', 'lob'], top=['VDD'],
           bottom=['VSS'], width=160, label='lobuf')


def build_lsq():
    c = 'rx_lsq'
    s = Sch()
    xl, xr = -700, 1500
    hq, _ = mos_dev(s, c, 'Hq', 0, -300)
    check(hq, D='vq', G='qenb', S='VDD', B='VDD')
    supply(s, hq.pin('S'), 'VDD')
    yq = -200
    gq, _ = capdev(s, c, 'Cq', -260, -60)
    ls = s.place('ls_ac.sym', 300, 100, name='xls')
    d1 = s.place('tspc_t1.sym', 800, 100, name='xd1')
    # TT: the dummy TX tap inverter, on vq
    g, d, tp, tn = inverter(s, c, 'TT', 800, 420, 'lsq', 'tt', vdd='vq', vss='VSS')
    s.text(d[0] + 20, d[1] - 24, 'tt (open)', 0.3)
    # vq: header drain, Cq, ls_ac / tspc_t1 VDD pins, TT's PMOS source
    s.route(gq, (gq[0] - 40, gq[1]), (gq[0] - 40, yq))
    s.wire(hq.pin('D'), (hq.pin('D')[0], yq))
    tps = tp.pin('S')
    s.route(tps, (tps[0], tps[1] - 20), (1100, tps[1] - 20), (1100, yq))
    s.route(ls.pin('VDD'), (ls.pin('VDD')[0], yq))
    s.route(d1.pin('VDD'), (d1.pin('VDD')[0], yq))
    xs = sorted({gq[0] - 40, hq.pin('D')[0], ls.pin('VDD')[0], d1.pin('VDD')[0], 1100})
    s.bus((xs[0], yq), (xs[-1], yq), [(x, yq) for x in xs])
    s.text(40, yq - 24, 'vq', 0.3)
    supply(s, ls.pin('VSS'), 'VSS'); supply(s, d1.pin('VSS'), 'VSS')
    # aq -> ls_ac's a0; ls_ac's ls = lsq -> tspc_t1 clk, TT, Dq, the port
    s.wire((xl, ls.pin('a0')[1]), ls.pin('a0')); port(s, (xl, ls.pin('a0')[1]), 'aq', 'in')
    xo = 620
    s.route(ls.pin('ls'), (xo, ls.pin('ls')[1]))
    s.route(d1.pin('clk'), (xo + 40, d1.pin('clk')[1]))
    s.text(d1.pin('q')[0] + 20, d1.pin('q')[1] - 24, 'q1 (open)', 0.3)
    dq, _ = mos_dev(s, c, 'Dq', 1200, 640)
    check(dq, D='lsq', G='qenb', S='VSS', B='VSS')
    supply(s, dq.pin('S'), 'VSS')
    ylsq = 260
    s.route((xo, ls.pin('ls')[1]), (xo, ylsq))
    s.route((xo + 40, d1.pin('clk')[1]), (xo + 40, ylsq))
    s.route(g, (g[0] - 40, g[1]), (g[0] - 40, ylsq))
    s.route(dq.pin('D'), (dq.pin('D')[0], ylsq))
    xs = sorted({xo, xo + 40, g[0] - 40, dq.pin('D')[0], xr})
    s.bus((xs[0], ylsq), (xs[-1], ylsq), [(x, ylsq) for x in xs])
    port(s, (xr, ylsq), 'lsq', 'out')
    # qenb: header gate, Dq gate
    yg = 760
    s.route(hq.pin('G'), (-40, hq.pin('G')[1]), (-40, -400), (xl, -400)); port(s, (xl, -400), 'qenb', 'in')
    s.route(dq.pin('G'), (1140, dq.pin('G')[1]), (1140, yg), (-560, yg), (-560, -400))
    s.wires = [w for w in s.wires if not ((w[0] == (-40, -400) and w[1] == (xl, -400)) or (w[1] == (-40, -400) and w[0] == (xl, -400)))]
    s.bus((xl, -400), (-40, -400), [(-560, -400)])
    supplies(s, xl, 880)
    title(s, xl, -760, ["rx_lsq: the Q tap level shifter (a copy of lsdiv's, with the same load)",
                        "ls_ac (the 2 fF metal-finger Cc level shifter) drives a dummy tspc_t1 and a dummy TX tap inverter "
                        "TT, as lsdiv's ls does: its delay (about 120 deg at 434 MHz) then matches the I tap's",
                        "header Hq (qenb low = on) feeds vq; Dq holds lsq low when off; the layout must copy lsdiv's LS "
                        "cell; source: sim/rx/rx_lo.py lsq()"])
    finish(s, c, ['VDD', 'VSS', 'aq', 'qenb', 'lsq'], left=['aq', 'qenb'], right=['lsq'], top=['VDD'], bottom=['VSS'],
           width=160, label='lsq')


def build_lo():
    c = 'rx_lo'
    s = Sch()
    xl, xr = -500, 1300
    lq = s.place('rx_lsq.sym', 200, 400, name='xlq')
    bi = s.place('rx_lobuf.sym', 700, -100, name='xbi')
    bq = s.place('rx_lobuf.sym', 700, 400, name='xbq')
    s.route((xl, bi.pin('in')[1]), bi.pin('in')); port(s, (xl, bi.pin('in')[1]), 'ls', 'in')
    s.wire((xl, lq.pin('aq')[1]), lq.pin('aq')); port(s, (xl, lq.pin('aq')[1]), 'aq', 'in')
    s.wire((xl, lq.pin('qenb')[1]), lq.pin('qenb')); port(s, (xl, lq.pin('qenb')[1]), 'qenb', 'in')
    s.route(lq.pin('lsq'), (500, lq.pin('lsq')[1]), (500, bq.pin('in')[1]), bq.pin('in'))
    ye = bi.pin('en')[1]
    s.wire((xl, -300), (560, -300))
    s.bus((560, -300), (560, bq.pin('en')[1]), [(560, ye)])
    s.wire((560, ye), bi.pin('en')); s.wire((560, bq.pin('en')[1]), bq.pin('en'))
    port(s, (xl, -300), 'en', 'in')
    for blk, a, b in ((bi, 'lo_i', 'lob_i'), (bq, 'lo_q', 'lob_q')):
        s.wire(blk.pin('lo'), (xr, blk.pin('lo')[1])); port(s, (xr, blk.pin('lo')[1]), a, 'out')
        s.wire(blk.pin('lob'), (xr, blk.pin('lob')[1])); port(s, (xr, blk.pin('lob')[1]), b, 'out')
    for blk in (lq, bi, bq):
        supply(s, blk.pin('VDD'), 'VDD'); supply(s, blk.pin('VSS'), 'VSS')
    supplies(s, xl, 760)
    title(s, xl, -560, ['rx_lo: I and Q LOs for the mixers',
                        "I: lsdiv's ls (from a0, shared with the TX) -> rx_lobuf; Q: rx_lsq on aq (ring a2: +72 deg) "
                        "-> rx_lobuf", 'qenb: low keeps the Q tap copy on (rx_top ties it to VSS); source: sim/rx/rx_lo.py block()'])
    finish(s, c, ['VDD', 'VSS', 'ls', 'aq', 'en', 'qenb', 'lo_i', 'lob_i', 'lo_q', 'lob_q'],
           left=['ls', 'aq', 'en', 'qenb'], right=['lo_i', 'lob_i', 'lo_q', 'lob_q'], top=['VDD'], bottom=['VSS'],
           width=200, label='rx_lo')


def build():
    build_lobuf()
    build_lsq()
    build_lo()


if __name__ == '__main__':
    build()
