"""
cfed_dac: the shared current DAC that sinks the ring current from vg to VSS
(vco_bias topo=cfed, foot "C"), plus the coarse gate switches.

  fine leg FFC    : one long unit, gate vctrl
  base leg FC     : k units, gate vbnf (always on)
  coarse legs FC_b: 2^b units, gate g_b = bit_b ? vbnf : VSS  (TN/TP pass gate + TD pull-down)
Unit W/L = wfu*kw / ls*kl with kc, ka as vco_bias.netlist().

Drawn one column per leg: each bit's switch cell sits over its leg and g_b runs straight down to
the leg's gate; vbnf is the wire across the top of the switch row, vg the top rail of the legs,
VSS the bottom rail. The bit inputs come in from the left as a staircase (no crossings between them).

    python3 xschem/gen/cfed_dac.py
"""
from common import DEV, P, Sch, place, vmirror, finish, title, bulk, port, supply

BITS = P['bits']
PINS = (['vg', 'vbnf', 'vctrl'] + [f'bit{b}' for b in range(BITS)] + [f'bitb{b}' for b in range(BITS)]
        + ['VDD', 'VSS'])


def build():
    s = Sch()
    yvg, yss, yv, yp, yg, yd = -80, 80, -420, -330, -270, -200
    xl = -300                                         # left edge: ports
    xs = [0, 260] + [260 + 320 * (b + 1) for b in range(BITS)]     # leg D/S columns: FFC, FC, FC_0..
    legs = ['FFC', 'FC'] + [f'FC_{b}' for b in range(BITS)]
    tops, bots = [], []
    for nm, xc in zip(legs, xs):
        d = DEV[nm]
        assert d['nets'][0] == 'vg' and d['nets'][2] == 'VSS' and d['nets'][3] == 'VSS'
        m = place(s, nm, xc - 20, 0)
        s.wire(m.pin('D'), (xc, yvg)); tops.append((xc, yvg))
        s.wire(m.pin('S'), (xc, yss)); bots.append((xc, yss))
        bots.append(bulk(s, m, y=yss))
    tag = {'FFC': 'fine (vctrl)', 'FC': f"base, k = {P['k']}"}
    tag.update({f'FC_{b}': f'bit {b}' for b in range(BITS)})
    for nm, xc in zip(legs, xs):
        s.text(xc - 50, yss + 20, tag[nm], 0.35)
    xr = xs[-1] + 200
    s.bus((xs[0], yvg), (xr, yvg), tops)
    port(s, (xr, yvg), 'vg', 'io_r')
    s.bus((xl, yss), (bots[-1][0], yss), bots)
    port(s, (xl, yss), 'VSS', 'io')
    # fine leg: vctrl straight in from the left
    s.wire((xl, 0), (xs[0] - 40, 0))
    port(s, (xl, 0), 'vctrl', 'in')
    # vbnf across the top of the switch row; the base leg taps it straight down
    vtaps = [(xs[1] - 40, yv)]
    s.wire((xs[1] - 40, yv), (xs[1] - 40, 0))
    # the switch cells, one over each coarse leg
    for b in range(BITS):
        xc = xs[2 + b]
        tp = place(s, f'TP{b}', xc - 220, yp)                # vbnf -> g_b, gate bitb_b
        tn = vmirror(s, f'TN{b}', xc - 60, yp)               # vbnf -> g_b, gate bit_b (source up)
        td = place(s, f'TD{b}', xc - 220, yd)                # g_b -> VSS, gate bitb_b
        assert tp.nets == dict(D=f'g{b}', G=f'bitb{b}', S='vbnf', B='VDD')
        assert tn.nets == dict(D=f'g{b}', G=f'bit{b}', S='vbnf', B='VSS')
        assert td.nets == dict(D=f'g{b}', G=f'bitb{b}', S='VSS', B='VSS')
        bulk(s, tp, to='VDD')
        bulk(s, tn, to='VSS')
        bulk(s, td, to='S')
        supply(s, td.pin('S'), 'VSS')
        for t in (tp, tn):
            s.wire(t.pin('S'), (t.pin('S')[0], yv)); vtaps.append((t.pin('S')[0], yv))
        # g_b: pass-gate output, pull-down drain, straight down to the leg gate
        s.wire(tp.pin('D'), (xc - 200, yg)); s.wire(td.pin('D'), (xc - 200, yg))
        s.wire((xc - 200, yg), (xc - 40, yg))
        s.wire(tn.pin('D'), (xc - 40, yg)); s.wire((xc - 40, yg), (xc - 40, 0))
        s.text(xc - 190, yg - 4, f'g{b}', 0.3)
        # inputs: staircase from the left edge, later bits higher
        hb, h = -480 - 80 * b, -520 - 80 * b
        s.route((xl, hb), (xc - 260, hb), (xc - 260, yp), tp.pin('G'))
        s.route((xc - 260, yp), (xc - 260, yd), td.pin('G'))
        s.route((xl, h), (xc - 100, h), (xc - 100, yp), tn.pin('G'))
        port(s, (xl, hb), f'bitb{b}', 'in')
        port(s, (xl, h), f'bit{b}', 'in')
    s.bus((xl, yv), (max(x for x, _ in vtaps), yv), vtaps)
    port(s, (xl, yv), 'vbnf', 'in')
    # VDD port: the switch PMOS bulks
    s.wire((xl, yss + 100), (xl + 60, yss + 100))
    port(s, (xl, yss + 100), 'VDD', 'io')
    supply(s, (xl + 60, yss + 100), 'VDD')
    W = DEV['FC']
    title(s, xl, -1000, ['cfed_dac: ring current DAC, vg -> VSS',
                         f"I(vg) = (k + code) units at vbnf + the fine leg at vctrl; unit nfet {W['w']:.3g}/{W['l']:.3g} um, "
                         f"fine leg {DEV['FFC']['w']:.3g}/{DEV['FFC']['l']:.3g} um",
                         'switch cell per bit: TN/TP pass vbnf to g_b when bit_b = 1, TD pulls g_b to VSS when bit_b = 0'])
    left = ([x for b in reversed(range(BITS)) for x in (f'bit{b}', f'bitb{b}')] + ['vctrl', 'vbnf'])
    finish(s, 'cfed_dac', PINS, left=left, right=['vg'], top=['VDD'], bottom=['VSS'], width=160, label='DAC')


if __name__ == '__main__':
    build()
