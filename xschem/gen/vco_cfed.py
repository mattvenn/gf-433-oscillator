"""
vco_cfed: the whole VCO, cgm_ref (constant-gm reference + vbn RC filter) driving the
ring_core_v3 (cfed ring + current DAC + vg decap) with the filtered vbnf.
Equivalent to sim/vco/vco_bias.py netlist() at the chosen design, less the wiring caps Cw*
and with the ideal Cvg replaced by the v3 layout's MOS decap.

    python3 xschem/gen/vco_cfed.py
"""
from common import P, Sch, finish, title, port, supply

BITS = P['bits']
PINS = (['VDD', 'VSS', 'vctrl'] + [f'bit{b}' for b in range(BITS)] + [f'bitb{b}' for b in range(BITS)]
        + [f'a{i}' for i in range(P['n'])] + ['vg', 'vbn', 'vbnf'])
STAIR = [x for b in reversed(range(BITS)) for x in (f'bit{b}', f'bitb{b}')]


def build():
    s = Sch()
    xl, xr = -100, 900
    core = s.place('ring_core_v3.sym', 600, 0, name='xcore')
    ref = s.place('cgm_ref.sym', 200, 400, name='xref')
    for net in STAIR + ['vctrl']:
        p = core.pin(net)
        s.wire((xl, p[1]), p)
        port(s, (xl, p[1]), net, 'in')
    for net in [f'a{i}' for i in range(P['n'])] + ['vg']:
        p = core.pin(net)
        s.wire(p, (xr, p[1]))
        port(s, (xr, p[1]), net, 'out' if net != 'vg' else 'io_r')
    # vbnf: the filtered bias into the core's DAC gate, and out; vbn (unfiltered) out under the core
    f, v = ref.pin('vbnf'), ref.pin('vbn')
    x2, x1, yb2, yb1 = 380, 320, 540, 580
    s.wire(f, (x2, f[1]))
    s.route((x2, f[1]), (x2, core.pin('vbn')[1]), core.pin('vbn'), vfirst=True)
    s.route((x2, f[1]), (x2, yb2), (xr, yb2), vfirst=True)
    port(s, (xr, yb2), 'vbnf', 'out')
    s.route(v, (x1, v[1]), (x1, yb1), (xr, yb1))
    port(s, (xr, yb1), 'vbn', 'out')
    for blk in (core, ref):
        supply(s, blk.pin('VDD'), 'VDD')
        supply(s, blk.pin('VSS'), 'VSS')
    s.wire((xl, 640), (xl + 60, 640)); port(s, (xl, 640), 'VDD', 'io'); supply(s, (xl + 60, 640), 'VDD')
    s.wire((xl, 700), (xl + 60, 700)); port(s, (xl, 700), 'VSS', 'io'); supply(s, (xl + 60, 700), 'VSS')
    title(s, xl, -520, ['vco_cfed: current-fed ring VCO, GF180MCU',
                        'cgm_ref -> vbnf -> ring_core_v3; code = bit[4:0] (coarse) + vctrl (fine); out a0..a4',
                        'source of truth: sim/vco/vco_bias.py netlist(), chosen design (xschem/gen/common.py)'])
    finish(s, 'vco_cfed', PINS, left=STAIR + ['vctrl'], right=[f'a{i}' for i in range(P['n'])] + ['vg', 'vbnf', 'vbn'],
           top=['VDD'], bottom=['VSS'], width=200, label='vco_cfed')


if __name__ == '__main__':
    build()
