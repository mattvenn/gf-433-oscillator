"""
vco_cfed: the whole VCO, cgm_ref (constant-gm reference + vbn RC filter) driving the
ring_core_v3 (cfed ring + current DAC + vg decap) with the filtered vbnf.
Equivalent to sim/vco/vco_bias.py netlist() at the chosen design, less the wiring caps Cw*
and with the ideal Cvg replaced by the v3 layout's MOS decap.

    python3 xschem/gen/vco_cfed.py
"""
from common import P, Sch, ports, finish, title

BITS = P['bits']
PINS = (['VDD', 'VSS', 'vctrl'] + [f'bit{b}' for b in range(BITS)] + [f'bitb{b}' for b in range(BITS)]
        + [f'a{i}' for i in range(P['n'])] + ['vg', 'vbn', 'vbnf'])


def build():
    s = Sch()
    ref = s.place('cgm_ref.sym', 0, 0, name='xref')
    s.connect(ref, VDD='VDD', VSS='VSS', vbn='vbn', vbnf='vbnf')
    core = s.place('ring_core_v3.sym', 500, 0, name='xcore')
    s.connect(core, VDD='VDD', VSS='VSS', vbn='vbnf', vctrl='vctrl', vg='vg',
              **{f'bit{b}': f'bit{b}' for b in range(BITS)}, **{f'bitb{b}': f'bitb{b}' for b in range(BITS)},
              **{f'a{i}': f'a{i}' for i in range(P['n'])})
    s.text(-120, 80, 'vbnf: the filtered bias drives the DAC gates', 0.3)
    ports(s, -450, -250, PINS)
    title(s, -450, -560, ['vco_cfed: current-fed ring VCO, GF180MCU',
                          'cgm_ref -> vbnf -> ring_core_v3 (ring + DAC + vg decap)',
                          'code = bit[4:0] (coarse), vctrl (fine); out a0..a4',
                          'source of truth: sim/vco/vco_bias.py netlist(), chosen design (xschem/gen/common.py)'])
    finish(s, 'vco_cfed', PINS, left=PINS[:3 + 2 * BITS], right=PINS[3 + 2 * BITS:], width=200)


if __name__ == '__main__':
    build()
