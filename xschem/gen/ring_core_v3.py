"""
ring_core_v3: the cfed ring core as laid out in layout/ring_core_v3.gds (the LVS source):
cfed_ring + cfed_dac + the vg MOS decap (nfet_03v3, gate vg, S/D/B VSS, sized for ~cvg by the
same rule as layout/gen/ring_core_v3.py, docs/ring_layout_v3.md).

Ports and order as layout/gen/export_core_v3.py. The DAC gate net is the port vbn: in vco_cfed it
is driven by the filtered vbnf.

    python3 xschem/gen/ring_core_v3.py
"""
from common import P, Sch, gmos, ports, finish, title, decap_size

BITS = P['bits']
PINS = (['VDD', 'VSS', 'vbn', 'vctrl'] + [f'bit{b}' for b in range(BITS)] + [f'bitb{b}' for b in range(BITS)]
        + ['vg'] + [f'a{i}' for i in range(P['n'])])


def build():
    s = Sch()
    ring = s.place('cfed_ring.sym', 700, -60, name='xring')
    s.connect(ring, VDD='VDD', vg='vg', VSS='VSS', **{f'a{i}': f'a{i}' for i in range(P['n'])})
    dac = s.place('cfed_dac.sym', 200, 0, name='xdac')
    s.connect(dac, vg='vg', vbnf='vbn', vctrl='vctrl', VDD='VDD', VSS='VSS',
              **{f'bit{b}': f'bit{b}' for b in range(BITS)}, **{f'bitb{b}': f'bitb{b}' for b in range(BITS)})
    m, L, W = decap_size()
    dc = gmos(s, 'n', 520, 260, W=W, L=L, m=m, name='DC', ad=False)
    s.connect(dc, D='VSS', G='vg', S='VSS', B='VSS')
    s.text(560, 330, f'vg decap ~{P["cvg"] * 1e12:g} pF: {m} x {W:g}/{L:g} um', 0.3)
    s.text(560, 355, 'as the v3 layout (gate on vg, S/D/B on VSS)', 0.3)
    ports(s, -250, -300, PINS)
    title(s, -250, -560, ['ring_core_v3: cfed ring + DAC + vg decap',
                          'the LVS source of layout/ring_core_v3.gds',
                          'vbn here = the DAC gate; vco_cfed drives it from the filtered vbnf'])
    finish(s, 'ring_core_v3', PINS, left=PINS[:4 + 2 * BITS], right=PINS[4 + 2 * BITS:], width=200)


if __name__ == '__main__':
    build()
