"""
rx_mix: the receiver's passive double-balanced mixer (sim/rx/rx_mix.py block()), one per arm.

  four transmission gates in a row: S1 rfp->bbp (lo), S4 rfp->bbn (lob), S3 rfn->bbp (lob), S2 rfn->bbn (lo);
  each gate's NMOS on its phase, its PMOS on the other phase; Cbp / Cbn (nfet gate caps) hold the baseband.

    python3 xschem/gen/rx_mix.py
"""
from rx_common import DEV, Sch, place, check, bulk, port, supply, finish, title, supplies, wl, mos_c, vmirror_place

C = 'rx_mix'
PINS = ['VDD', 'VSS', 'rfp', 'rfn', 'bbp', 'bbn', 'lo', 'lob']


def tgate(s, nm, x, y0, rf, bb, on, off, yrf, ybb, ylo, ylob):
    n = vmirror_place(s, C, f'{nm}n', x - 80, y0)
    p = place(s, C, f'{nm}p', x + 80, y0, flip=1)
    check(n, D=bb, G=on, S=rf, B='VSS'); check(p, D=bb, G=off, S=rf, B='VDD')
    bulk(s, n, to='VSS'); bulk(s, p, to='VDD')
    for pin, yb in (('S', y0 - 60), ('D', y0 + 60)):
        s.route(n.pin(pin), (n.pin(pin)[0], yb), (x, yb))
        s.route(p.pin(pin), (p.pin(pin)[0], yb), (x, yb))
    s.wire((x, y0 - 60), (x, yrf))
    s.wire((x, y0 + 60), (x, ybb))
    yn = ylo if on == 'lo' else ylob
    yp = ylo if off == 'lo' else ylob
    s.route(n.pin('G'), (x - 140, y0), (x - 140, yn))
    s.route(p.pin('G'), (x + 140, y0), (x + 140, yp))
    s.text(x - 40, y0 + 90, nm, 0.35)
    return [(x, yrf)], [(x, ybb)], (x - 140, yn), (x + 140, yp)


def build():
    s = Sch()
    xl, xr = -400, 1900
    yrfp, yrfn, ylo, ylob, ybbp, ybbn = -300, -380, -520, -460, 300, 380
    taps = {k: [] for k in ('rfp', 'rfn', 'bbp', 'bbn', 'lo', 'lob')}
    for i, (nm, rf, bb, on, off) in enumerate((('S1', 'rfp', 'bbp', 'lo', 'lob'), ('S4', 'rfp', 'bbn', 'lob', 'lo'),
                                              ('S3', 'rfn', 'bbp', 'lob', 'lo'), ('S2', 'rfn', 'bbn', 'lo', 'lob'))):
        x = 200 + i * 400
        yrf = yrfp if rf == 'rfp' else yrfn
        ybb = ybbp if bb == 'bbp' else ybbn
        trf, tbb, gn, gp = tgate(s, nm, x, 0, rf, bb, on, off, yrf, ybb, ylo, ylob)
        taps[rf] += trf
        taps[bb] += tbb
        taps[on].append(gn)
        taps[off].append(gp)
    for net, y in (('rfp', yrfp), ('rfn', yrfn), ('lo', ylo), ('lob', ylob)):
        s.bus((xl, y), (max(t[0] for t in taps[net]), y), taps[net])
        port(s, (xl, y), net, 'in')
    # baseband lines to the right, the caps on them
    xc = 1700
    for net, y, cn in (('bbp', ybbp, 'Cbp'), ('bbn', ybbn, 'Cbn')):
        c = place(s, C, cn, xc + (0 if net == 'bbp' else 160), y + 150)
        check(c, D='VSS', G=net, S='VSS', B='VSS')
        g = c.pin('G')
        s.route((g[0] - 40, g[1]), (g[0] - 40, y))
        s.wire(g, (g[0] - 40, g[1]))
        s.bus((min(t[0] for t in taps[net]), y), (xr, y), taps[net] + [(g[0] - 40, y)])
        port(s, (xr, y), net, 'out')
        xt = c.pin('D')[0] + 20
        s.wire(c.pin('D'), (xt, c.pin('D')[1])); s.wire(c.pin('B'), (xt, c.pin('B')[1]))
        s.bus((xt, c.pin('D')[1]), (xt, c.pin('S')[1]), [(xt, c.pin('B')[1])])
        s.wire(c.pin('S'), (xt, c.pin('S')[1]))
        supply(s, (xt, c.pin('S')[1]), 'VSS')
        s.text(xt + 20, c.pin('S')[1] - 10, f'{cn} ~{mos_c(DEV[C][cn]) * 1e15:.0f} fF', 0.3)
    supplies(s, xl, 700)
    dn, dp = DEV[C]['S1n'], DEV[C]['S1p']
    title(s, xl, -800, ['rx_mix: passive double-balanced mixer (one per arm)',
                        f'four transmission gates (N {wl(dn)}, P {wl(dp)} um): lo connects rfp-bbp and rfn-bbn, lob '
                        'crosses them; the RF nodes sit at the LNA output DC (~2.5 V), so each switch is a full TG',
                        'no DC through the switches (the baseband is high-Z), so no flicker noise; source: '
                        'sim/rx/rx_mix.py block()'])
    finish(s, C, PINS, left=['rfp', 'rfn', 'lo', 'lob'], right=['bbp', 'bbn'], top=['VDD'], bottom=['VSS'],
           width=160, label='mix')


if __name__ == '__main__':
    build()
