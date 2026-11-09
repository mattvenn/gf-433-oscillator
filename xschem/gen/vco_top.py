"""
vco_top: the VCO top level as laid out in layout/vco_top.gds (the LVS source of layout/gen/check_top.sh):
ring_core_v3 (ring + DAC + vg decap) driven by cgm_ref (reference + 1 MOhm / 20 pF filter: vbnf -> the DAC gate),
lsdiv (level shifter + TSPC /4 + clock buffer) on a0, on its own supply VDD_LS, and the VDD_LS decap DCLS
(nfet_03v3 gate cap, gate VDD_LS, S/D/B VSS, sized as drawn by layout/gen/vco_top.py).

Ports: VDD (ring + reference), VDD_LS (level shifter / divider), VSS, vctrl, bit0-4, bitb0-4, ck (a0 / 4),
a0 (the ring tap), vbn (unfiltered reference bias, monitor), vg (DAC node, monitor), ls (lsdiv's level-shifter
output: the TX driver's tap).

    python3 xschem/gen/vco_top.py
"""
import importlib.util
import os
import sys

from common import P, REPO, Sch, Inst, gmos, finish, title, port, supply

# the drawn VDD_LS decap (fingers, W, L) comes from the layout generator, so the sheet is the layout's LVS source
sys.path.append(os.path.join(REPO, 'layout', 'gen'))
_spec = importlib.util.spec_from_file_location('lay_vco_top', os.path.join(REPO, 'layout', 'gen', 'vco_top.py'))
_lay = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lay)
DCLS = _lay.DCLS

BITS = P['bits']
PINS = (['VDD', 'VDD_LS', 'VSS', 'vctrl'] + [f'bit{b}' for b in range(BITS)] + [f'bitb{b}' for b in range(BITS)]
        + ['ck', 'a0', 'vbn', 'vg', 'ls'])
STAIR = [x for b in reversed(range(BITS)) for x in (f'bit{b}', f'bitb{b}')]


def vsupply(sch, pt, net):
    """A VDD-style supply symbol labelled net (VDD_LS uses the VDD arrow)."""
    sch.items.append(Inst('symbols/vdd.sym', pt[0], pt[1], 0, 0, {'name': sch._name('l'), 'lab': net}))


def build():
    s = Sch()
    xl, xr = -100, 1400
    core = s.place('ring_core_v3.sym', 600, 0, name='xcore')
    ref = s.place('cgm_ref.sym', 200, 420, name='xref')
    ls = s.place('lsdiv.sym', 960, -200, name='xls')
    # coarse code and vctrl straight into the core
    for net in STAIR + ['vctrl']:
        p = core.pin(net)
        s.wire((xl, p[1]), p)
        port(s, (xl, p[1]), net, 'in')
    # vbnf: the filtered bias into the DAC gate (the core's vbn pin); vbn (unfiltered) out as a monitor
    f, v = ref.pin('vbnf'), ref.pin('vbn')
    x2 = 380
    s.route(f, (x2, f[1]), (x2, core.pin('vbn')[1]), core.pin('vbn'))
    yb = 560
    s.route(v, (340, v[1]), (340, yb), (xr, yb))
    port(s, (xr, yb), 'vbn', 'out')
    s.text(392, 300, 'vbnf', 0.3)
    # a0: ring tap -> level shifter, tapped out as a port
    a0, la0 = core.pin('a0'), ls.pin('a0')
    ta = (800, a0[1])
    s.bus(a0, la0, [ta])
    s.route(ta, (800, -520), (xr, -520), vfirst=True)
    port(s, (xr, -520), 'a0', 'out')
    # ck out
    ck = ls.pin('ck')
    s.wire(ck, (xr, ck[1]))
    port(s, (xr, ck[1]), 'ck', 'out')
    # ls: the level-shifter output, a port for the TX driver's tap
    lp = ls.pin('ls')
    s.wire(lp, (xr, lp[1]))
    port(s, (xr, lp[1]), 'ls', 'out')
    # vg monitor
    g = core.pin('vg')
    s.wire(g, (xr, g[1]))
    port(s, (xr, g[1]), 'vg', 'io_r')
    # VDD_LS: lsdiv supply and its decap (gate VDD_LS, S/D/B VSS)
    lv = ls.pin('VDD')
    yr = -340
    dc = gmos(s, 'n', 1260, -300, W=DCLS['w'], L=DCLS['l'], m=DCLS['nf'], name='DCLS', ad=False)
    dc.props['val'] = f'"{DCLS["w"]:g}/{DCLS["l"]:g} ×{DCLS["nf"]}"'
    gx = dc.pin('G')[0] - 40
    s.route(lv, (lv[0], yr), vfirst=True)
    s.route((lv[0], yr), (gx, yr), (gx, dc.pin('G')[1]), dc.pin('G'))
    vsupply(s, (lv[0], yr), 'VDD_LS')
    xt = dc.pin('D')[0] + 20
    s.wire(dc.pin('D'), (xt, dc.pin('D')[1])); s.wire(dc.pin('B'), (xt, dc.pin('B')[1]))
    s.bus((xt, dc.pin('D')[1]), (xt, dc.pin('S')[1]), [(xt, dc.pin('B')[1])])
    s.wire(dc.pin('S'), (xt, dc.pin('S')[1]))
    supply(s, (xt, dc.pin('S')[1]), 'VSS')
    s.text(1300, -360, f'VDD_LS decap ~{DCLS["c_pf"]:.0f} pF', 0.35)
    # block supplies
    for blk in (core, ref):
        supply(s, blk.pin('VDD'), 'VDD')
        supply(s, blk.pin('VSS'), 'VSS')
    supply(s, ls.pin('VSS'), 'VSS')
    # supply ports
    for i, net in enumerate(('VDD', 'VDD_LS', 'VSS')):
        y = 660 + 60 * i
        s.wire((xl, y), (xl + 60, y)); port(s, (xl, y), net, 'io')
        (supply if net == 'VSS' else vsupply)(s, (xl + 60, y), net)
    title(s, xl, -800, ['vco_top: 433.92 MHz current-fed ring VCO, GF180MCU (top level)',
                        'cgm_ref -> vbnf -> ring_core_v3 -> a0 -> lsdiv -> ck = f / 4; lsdiv on its own supply VDD_LS',
                        'the LVS source of layout/vco_top.gds (layout/gen/check_top.sh)'])
    finish(s, 'vco_top', PINS, left=STAIR + ['vctrl'], right=['a0', 'ck', 'ls', 'vbn', 'vg'],
           top=['VDD', 'VDD_LS'], bottom=['VSS'], width=220, label='vco_top')


if __name__ == '__main__':
    build()
