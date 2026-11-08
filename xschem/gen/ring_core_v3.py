"""
ring_core_v3: the cfed ring core as laid out in layout/ring_core_v3.gds (the LVS source):
cfed_ring + cfed_dac + the vg MOS decap (nfet_03v3, gate vg, S/D/B VSS, sized for ~cvg by the
same rule as layout/gen/ring_core_v3.py, docs/ring_layout_v3.md).

Ports and order as layout/gen/export_core_v3.py. The DAC gate net is the port vbn: in vco_cfed it
is driven by the filtered vbnf. Drawn with wires: DAC on the left, vg across to the ring with the
decap hanging off it, ring outputs to the right edge.

    python3 xschem/gen/ring_core_v3.py
"""
from common import P, Sch, gmos, finish, title, decap_size, port, supply

BITS = P['bits']
PINS = (['VDD', 'VSS', 'vbn', 'vctrl'] + [f'bit{b}' for b in range(BITS)] + [f'bitb{b}' for b in range(BITS)]
        + ['vg'] + [f'a{i}' for i in range(P['n'])])
STAIR = [x for b in reversed(range(BITS)) for x in (f'bit{b}', f'bitb{b}')]


def build():
    s = Sch()
    xl, xr = -300, 800
    dac = s.place('cfed_dac.sym', 0, 0, name='xdac')
    ring = s.place('cfed_ring.sym', 500, -140, name='xring')
    assert dac.pin('vg')[1] == ring.pin('vg')[1]
    # inputs straight into the DAC
    for net in STAIR + ['vctrl', 'vbnf']:
        p = dac.pin(net)
        s.wire((xl, p[1]), p)
        port(s, (xl, p[1]), 'vbn' if net == 'vbnf' else net, 'in')
    # vg: DAC -> ring, the decap on it, and out to the vg port under the ring
    m, L, W = decap_size()
    dc = gmos(s, 'n', 200, -120, W=W, L=L, m=m, name='DC', ad=False)
    dc.props['val'] = f'"{W:g}/{L:g} ×{m}"'
    yv = dac.pin('vg')[1]
    tg, tp = (dc.pin('G')[0], yv), (370, yv)
    s.bus(dac.pin('vg'), ring.pin('vg'), [tg, tp])
    s.wire(tg, dc.pin('G'))
    xt = dc.pin('D')[0] + 20
    s.wire(dc.pin('D'), (xt, dc.pin('D')[1])); s.wire(dc.pin('B'), (xt, dc.pin('B')[1]))
    s.bus((xt, dc.pin('D')[1]), (xt, dc.pin('S')[1]), [(xt, dc.pin('B')[1])])
    s.wire(dc.pin('S'), (xt, dc.pin('S')[1]))
    supply(s, (xt, dc.pin('S')[1]), 'VSS')
    s.text(150, -40, f'vg decap ~{P["cvg"] * 1e12:g} pF', 0.35)
    s.route(tp, (370, 60), (xr, 60), vfirst=True)
    port(s, (xr, 60), 'vg', 'io_r')
    # ring outputs
    for i in range(P['n']):
        p = ring.pin(f'a{i}')
        s.wire(p, (xr, p[1]))
        port(s, (xr, p[1]), f'a{i}', 'out')
    for blk in (dac, ring):
        supply(s, blk.pin('VDD'), 'VDD')
        supply(s, blk.pin('VSS'), 'VSS')
    s.wire((xl, 360), (xl + 60, 360)); port(s, (xl, 360), 'VDD', 'io'); supply(s, (xl + 60, 360), 'VDD')
    s.wire((xl, 420), (xl + 60, 420)); port(s, (xl, 420), 'VSS', 'io'); supply(s, (xl + 60, 420), 'VSS')
    title(s, xl, -520, ['ring_core_v3: cfed ring + DAC + vg decap',
                        'the LVS source of layout/ring_core_v3.gds',
                        'vbn here is the DAC gate bias; vco_cfed drives it from the filtered vbnf'])
    finish(s, 'ring_core_v3', PINS, left=STAIR + ['vctrl', 'vbn'], right=[f'a{i}' for i in range(P['n'])] + ['vg'],
           top=['VDD'], bottom=['VSS'], width=200, label='ring_core_v3')


if __name__ == '__main__':
    build()
