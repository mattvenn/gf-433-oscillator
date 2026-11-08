"""
cfed_dac: the shared current DAC that sinks the ring current from vg to VSS
(vco_bias topo=cfed, foot "C"), plus the coarse gate switches.

  base leg FC     : k units, gate vbnf (always on)
  coarse legs FC_b: 2^b units, gate g_b = bit_b ? vbnf : VSS  (TN/TP pass gate + TD pull-down)
  fine leg FFC    : one long unit, gate vctrl
Unit W/L = wfu*kw / ls*kl with kc, ka as vco_bias.netlist().

    python3 xschem/gen/cfed_dac.py
"""
from common import DEV, P, Sch, place, ports, finish, title

BITS = P['bits']
PINS = (['vg', 'vbnf', 'vctrl'] + [f'bit{b}' for b in range(BITS)] + [f'bitb{b}' for b in range(BITS)]
        + ['VDD', 'VSS'])
REN = {'vbnf': 'vbnf'}


def build():
    s = Sch()
    # ---- the legs: drains on the vg rail, sources on the VSS rail
    legs = ['FC'] + [f'FC_{b}' for b in range(BITS)] + ['FFC']
    tags = {'FC': f"base, k = {P['k']}", 'FFC': 'fine (vctrl)'}
    tags.update({f'FC_{b}': f'bit {b}, x{2 ** b}' for b in range(BITS)})
    dx, y0 = 240, 0
    top, bot = [], []
    for i, nm in enumerate(legs):
        d = DEV[nm]
        assert d['nets'][0] == 'vg' and d['nets'][2] == 'VSS'
        x = i * dx
        m = place(s, nm, x, y0, skip='DS')
        top.append(m.pin('D')); bot.append(m.pin('S'))
        s.text(x - 20, y0 + 70, tags[nm], 0.3)
    s.rail(y0 - 80, -80, top[-1][0] + 60, top, net='vg')
    s.rail(y0 + 120, -80, bot[-1][0] + 60, bot, net='VSS')
    # ---- the coarse switches, one column per bit, above the legs over their own leg
    ys = -760
    for b in range(BITS):
        x = (b + 1) * dx
        place(s, f'TN{b}', x, ys)
        place(s, f'TP{b}', x, ys + 160)
        place(s, f'TD{b}', x, ys + 320)
        s.text(x - 60, ys - 90, f'g{b} = bit{b} ? vbnf : VSS', 0.3)
    s.text(-80, ys - 30, 'coarse gate switches', 0.35)
    for i, (t, dy) in enumerate((('TN: pass n', 0), ('TP: pass p', 160), ('TD: pull-down', 320))):
        s.text(-80, ys + dy + 10, t, 0.3)
    ports(s, -420, -300, PINS)
    W = DEV['FC']
    title(s, -420, -1120, ['cfed_dac: ring current DAC, vg -> VSS',
                          f"unit nfet_03v3 {W['w']:.3g}/{W['l']:.4g} um; fine leg {DEV['FFC']['w']:.3g}/{DEV['FFC']['l']:.4g} um",
                          f"kc={P['kc']} ka={P['ka']:g} wfu={P['wfu']} wff={P['wff']} (sim/vco/vco_bias.py, topo=cfed)",
                          'I(vg) = (k + code) units at vbnf + the fine leg at vctrl'])
    finish(s, 'cfed_dac', PINS, left=PINS[:3 + 2 * BITS], right=['VDD', 'VSS'], width=180)


if __name__ == '__main__':
    build()
