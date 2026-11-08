"""
cfed_dac: the shared current DAC that sinks the ring current from vg to VSS
(vco_bias topo=cfed, foot "C"), plus the coarse gate switches.

  fine leg FFC    : one long unit, gate vctrl
  base leg FC     : k units, gate vbnf (always on)
  coarse legs FC_b: 2^b units, gate g_b = bit[b] ? vbnf : VSS  (TN + TP transmission gate, TD pull-down)
Unit W/L = wfu*kw / ls*kl with kc, ka as vco_bias.netlist().

Drawn one column per leg: each bit's switch cell sits over its leg, its transmission gate drawn
the textbook way (NMOS over PMOS, lying on their sides, gates outside), and g_b runs down to the
leg's gate; vbnf is the wire across the top of the switch row, vg the top rail of the legs,
VSS the bottom rail. The bit inputs come in from the left as a staircase (no crossings between them).

    python3 xschem/gen/cfed_dac.py
"""
from common import DEV, P, Sch, place, finish, title, bulk, port, supply, wl

BITS = P['bits']
PINS = (['vg', 'vbnf', 'vctrl'] + [f'bit{b}' for b in range(BITS)] + [f'bitb{b}' for b in range(BITS)]
        + ['VDD', 'VSS'])


def build():
    s = Sch()
    yvg, yss, yv = -80, 80, -500                       # vg rail, VSS rail, vbnf rail
    yn, yp, yj, yd = -420, -300, -220, -170           # tgate NMOS / PMOS rows, g_b tap, TD centre
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
    # the switch cells, one over each coarse leg. Each is a textbook transmission gate lying on its
    # side (vbnf in on the left, g_b out on the right): TN on top with its gate (bit_b) above it, TP
    # underneath with its gate (bitb_b, the bubble) below it. Their bulk ties sit inside the gate.
    # TD hangs off g_b to VSS, gate bitb_b; g_b then runs right and down to the leg gate.
    for b in range(BITS):
        xc = xs[2 + b]
        xt, xb = xc - 180, xc - 240                          # tgate centre, bitb drop
        tn = place(s, f'TN{b}', xt, yn - 20, rot=1, hide=True)   # S left, D right, G up, B down
        tp = place(s, f'TP{b}', xt, yp + 20, rot=3, hide=True)   # S left, D right, G down, B up
        td = place(s, f'TD{b}', xt + 10, yd)                 # g_b -> VSS, gate bitb_b
        assert tp.nets == dict(D=f'g{b}', G=f'bitb{b}', S='vbnf', B='VDD')
        assert tn.nets == dict(D=f'g{b}', G=f'bit{b}', S='vbnf', B='VSS')
        assert td.nets == dict(D=f'g{b}', G=f'bitb{b}', S='VSS', B='VSS')
        assert tn.pin('S') == (xt - 30, yn) and tp.pin('S') == (xt - 30, yp)
        assert tn.pin('D') == (xt + 30, yn) and tp.pin('D') == (xt + 30, yp) and td.pin('D') == (xt + 30, yd - 30)
        # bulks: short stubs into the gate's middle, ground for TN, VDD for TP; TD bulk to its source
        s.wire(tn.pin('B'), (xt, yn + 20)); supply(s, (xt, yn + 20), 'VSS')
        s.wire(tp.pin('B'), (xt, yp - 20)); supply(s, (xt, yp - 20), 'VDD')
        bulk(s, td, to='S')
        supply(s, td.pin('S'), 'VSS')
        # vbnf down the left side, g_b down the right side to TD, tapped across to the leg gate
        s.wire((xt - 30, yv), tn.pin('S')); s.wire(tn.pin('S'), tp.pin('S')); vtaps.append((xt - 30, yv))
        s.wire(tn.pin('D'), tp.pin('D')); s.wire(tp.pin('D'), (xt + 30, yj)); s.wire((xt + 30, yj), td.pin('D'))
        s.route((xt + 30, yj), (xc - 40, yj), (xc - 40, 0))
        s.text(xc - 120, yj - 24, f'g{b}', 0.3)
        s.text(xt + 8, yn - 52, f"TN{b}  {wl(DEV[f'TN{b}'])}", 0.3)
        s.text(xt + 8, yp + 22, f"TP{b}  {wl(DEV[f'TP{b}'])}", 0.3)
        # inputs: staircase from the left edge, later bits higher. bit_b drops onto TN's gate;
        # bitb_b drops past the gate, in under TP's gate, and on to TD's gate.
        hb, h = -560 - 80 * b, -600 - 80 * b
        s.route((xl, h), (xt, h), tn.pin('G'))
        s.route((xl, hb), (xb, hb), (xb, yp + 60), (xt, yp + 60), tp.pin('G'))
        s.route((xb, yp + 60), (xb, yd), td.pin('G'))
        port(s, (xl, hb), f'bitb{b}', 'in')
        port(s, (xl, h), f'bit{b}', 'in')
    s.bus((xl, yv), (max(x for x, _ in vtaps), yv), vtaps)
    port(s, (xl, yv), 'vbnf', 'in')
    # VDD port: the switch PMOS bulks
    s.wire((xl, yss + 100), (xl + 60, yss + 100))
    port(s, (xl, yss + 100), 'VDD', 'io')
    supply(s, (xl + 60, yss + 100), 'VDD')
    W = DEV['FC']
    title(s, xl, -1100, ['cfed_dac: ring current DAC, vg -> VSS',
                         f"I(vg) = (k + code) units at vbnf + the fine leg at vctrl; unit nfet {W['w']:.3g}/{W['l']:.3g} um, "
                         f"fine leg {DEV['FFC']['w']:.3g}/{DEV['FFC']['l']:.3g} um",
                         'switch cell per bit b: the transmission gate TN + TP connects g_b to vbnf when bit[b] = 1; TD pulls g_b to VSS when bit[b] = 0'])
    left = ([x for b in reversed(range(BITS)) for x in (f'bit{b}', f'bitb{b}')] + ['vctrl', 'vbnf'])
    finish(s, 'cfed_dac', PINS, left=left, right=['vg'], top=['VDD'], bottom=['VSS'], width=160, label='DAC')


if __name__ == '__main__':
    build()
