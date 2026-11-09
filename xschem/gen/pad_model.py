"""
pad_model_gf180, tt_asw_5v0 and lv2hv: one Tiny Tapeout GF180 analog pin, as the simulated netlists
sim/pad/pad_model_gf180.spice and sim/pad/tt_asw_5v0.spice (docs/pad_model.md).

  lv2hv          : two 3.3 V inverters (in -> in_n -> in_p), a cross-coupled 5 V latch on VAPWR, two output
                   inverters (out_p = ctrl, out_n = !ctrl at VAPWR levels). tnt's lv2hv.sch.
  tt_asw_5v0     : the transmission gate bus <-> mod (nfet_05v0 31/0.6 x7, pfet_05v0 37/0.5 x16: tnt's nf = 7 / 16
                   devices as unit fingers) and M3, which ties mod to VGND when the switch is off. Parameter mult:
                   that many switches in parallel on the bus (the level shifter is not multiplied).
  pad_model_gf180: board pin, package, asig_5p0 pad (ESD diodes + metal C), routing, this project's switch (on),
                   n_off other projects' switches (off), the project-side route. Supplies are internal sources.

    python3 xschem/gen/pad_model.py
"""
from common import Sch, Inst, finish, title, bulk, port

SW = dict(nl=dict(W=31, L=0.6, m=7, ad='3.189p', pd='35.63u'),               # per finger, as tt_asw_5v0.spice
          pl=dict(W=37, L=0.5, m=16, ad='3.330p', as_='3.746p', pd='37.18u', ps='41.83u'))


def mos(s, kind, v, x, y, W, L, m=1, flip=0, ad=None, as_=None, pd=None, ps=None, name=None, mexpr=None, nf=1):
    """GF180 nfet/pfet_<v> (symbols/<kind>fet_<v>.sym), ad/as/pd/ps as given, else the tnt schematic formula
    for nf = 1 (W x 0.18 um diffusion)."""
    model = f'{kind}fet_{v}'
    a = ad or f'{W * 0.18:.4g}p'
    p = pd or f'{2 * (W + 0.18):.4g}u'
    props = {'L': f'{L}u', 'W': f'{W}u', 'nf': str(nf), 'm': mexpr or str(m), 'ad': a, 'as': as_ or a,
             'pd': p, 'ps': ps or p, 'nrd': '0', 'nrs': '0', 'sa': '0', 'sb': '0', 'sd': '0',
             'model': model, 'spiceprefix': 'X'}
    return s.place(f'symbols/{model}.sym', x, y, flip=flip, name=name or s._name('M'), **props)


def sup(s, pt, net):
    """Supply symbol on a wire end / pin: VGND a ground, anything else (VDPWR, VAPWR, VDDIO) a VDD arrow."""
    sym = 'symbols/gnd.sym' if net == 'VGND' else 'symbols/vdd.sym'
    s.items.append(Inst(sym, pt[0], pt[1], 0, 0, {'name': s._name('l'), 'lab': net}))


def tied(s, m, net):
    """Bulk tied to the source, a supply symbol on the source."""
    bulk(s, m, to='S')
    sup(s, m.pin('S'), net)


def supply_ports(s, x, y, nets):
    """Supply ports in a column at (x, y): port, short wire, supply symbol."""
    for i, n in enumerate(nets):
        a, b = (x, y + 60 * i), (x + 60, y + 60 * i)
        s.wire(a, b)
        port(s, a, n, 'io')
        sup(s, b, n)


def inverter(s, x, vp, vdd, W, pkw=None):
    """Inverter at x: PMOS (vp, on vdd) over NMOS, gates joined at x-20 (input tap (x-20, 0)),
    drains at x+20 (output tap (x+20, 0)). W = (Wp, Lp, Wn, Ln); pkw: extra PMOS properties."""
    wp, lp, wn, ln = W
    p = mos(s, 'p', vp, x, -100, wp, lp, **(pkw or {}))
    n = mos(s, 'n', vp, x, 100, wn, ln)
    s.bus(p.pin('G'), n.pin('G'), [(x - 20, 0)])
    s.bus(p.pin('D'), n.pin('D'), [(x + 20, 0)])
    tied(s, p, vdd)
    tied(s, n, 'VGND')
    return p, n


def lv2hv():
    s = Sch()
    # 3.3 V inverters in -> in_n -> in_p
    inverter(s, 0, '03v3', 'VDPWR', (2.0, 0.28, 0.89, 0.28))
    inverter(s, 200, '03v3', 'VDPWR', (2.0, 0.28, 0.89, 0.28))
    s.wire((-100, 0), (-20, 0)); port(s, (-100, 0), 'in', 'in')
    s.bus((20, 0), (180, 0), [(100, 0)])                                  # in_n
    # 5 V latch: left branch n1 (M4 flipped, gate inward; M3 gate outward), right branch n2 (mirror image)
    m4 = mos(s, 'p', '05v0', 500, -100, 0.5, 0.5, flip=1)
    m3 = mos(s, 'n', '05v0', 460, 100, 0.5, 0.6)
    m6 = mos(s, 'p', '05v0', 700, -100, 0.5, 0.5)
    m5 = mos(s, 'n', '05v0', 740, 100, 0.5, 0.6, flip=1)
    for p in (m4, m6):
        tied(s, p, 'VAPWR')
    for n in (m3, m5):
        tied(s, n, 'VGND')
    s.bus(m4.pin('D'), m3.pin('D'), [(480, 20), (480, -40)])              # n1
    s.bus(m6.pin('D'), m5.pin('D'), [(720, -20), (720, 40)])              # n2
    s.route(m4.pin('G'), (580, -100), (580, -20), (720, -20))             # M4 gate <- n2
    s.route(m6.pin('G'), (620, -100), (620, 20), (480, 20))               # M6 gate <- n1 (the latch's X)
    s.route((220, 0), (400, 0), (400, 100), m3.pin('G'))                  # in_p -> M3
    s.route((100, 0), (100, 260), (780, 260), (780, 100), m5.pin('G'))    # in_n -> M5, under the latch
    # output inverters (5 V): out_p = !n1, out_n = !n2
    nf2 = dict(nf=2, ad='0.09p', as_='0.18p', pd='1.36u', ps='2.72u')          # tnt: 1.0/0.5 nf = 2
    inverter(s, 960, '05v0', 'VAPWR', (1.0, 0.5, 0.5, 0.6), nf2)
    inverter(s, 1160, '05v0', 'VAPWR', (1.0, 0.5, 0.5, 0.6), nf2)
    s.route((480, -40), (420, -40), (420, -300), (900, -300), (900, 0), (940, 0))       # n1 over the top
    s.route((720, 40), (800, 40), (800, 320), (1100, 320), (1100, 0), (1140, 0))        # n2 under
    s.route((980, 0), (1040, 0), (1040, -220), (1280, -220)); port(s, (1280, -220), 'out_p', 'out')
    s.wire((1180, 0), (1280, 0)); port(s, (1280, 0), 'out_n', 'out')
    supply_ports(s, -200, -320, ['VDPWR', 'VAPWR', 'VGND'])
    s.text(-20, 170, '3.3 V: in -> in_n -> in_p', 0.3)
    s.text(470, -380, '5 V latch (n1, n2)', 0.3)
    s.text(920, 170, 'outputs on VAPWR', 0.3)
    title(s, -200, -560, ['lv2hv: 3.3 V -> VAPWR level shifter (tnt, tt_asw_5v0)',
                          '3.3 V inverters 2/0.28 + 0.89/0.28; latch 0.5/0.5 + 0.5/0.6; outputs 1/0.5 nf 2 + 0.5/0.6',
                          'in = 1: out_p = VAPWR, out_n = 0'])
    finish_params(s, 'lv2hv', ['VGND', 'VDPWR', 'VAPWR', 'in', 'out_p', 'out_n'], {}, left=['in'],
                  right=['out_p', 'out_n'], top=['VDPWR', 'VAPWR'], bottom=['VGND'], width=160, tpitch=80)


def tt_asw():
    s = Sch()
    x1 = s.place('lv2hv.sym', 300, 20, name='x1')
    s.wire((120, 0), x1.pin('in')); port(s, (120, 0), 'ctrl', 'in')
    for nm in ('VDPWR', 'VAPWR'):
        a = x1.pin(nm); b = (a[0], a[1] - 30); s.wire(a, b); sup(s, b, nm)
    a = x1.pin('VGND'); b = (a[0], a[1] + 30); s.wire(a, b); sup(s, b, 'VGND')
    # transmission gate, upright: N on the left (gate tgon_p from the left), P on the right (gate tgon_n)
    n = mos(s, 'n', '05v0', 500, 0, **{k: v for k, v in SW['nl'].items() if k != 'm'}, mexpr="'7*mult'", name='M2')
    p = mos(s, 'p', '05v0', 800, 0, **{k: v for k, v in SW['pl'].items() if k != 'm'}, mexpr="'16*mult'",
            flip=1, name='M1')
    b = bulk(s, n); sup(s, b, 'VGND')
    b = bulk(s, p); sup(s, b, 'VAPWR')
    s.route(n.pin('D'), (520, -80), (650, -80))
    s.route(p.pin('S'), (780, -80), (650, -80))
    s.wire((650, -80), (650, -160)); port(s, (650, -160), 'bus', 'io_r')
    s.route(n.pin('S'), (520, 80), (650, 80))
    s.route(p.pin('D'), (780, 80), (650, 80))
    m3 = mos(s, 'n', '05v0', 630, 180, 31, 0.6, mexpr='mult', ad='5.58p', pd='62.36u', name='M3')
    s.bus((650, 80), m3.pin('D'), [(650, 110)])
    s.wire((650, 110), (960, 110)); port(s, (960, 110), 'mod', 'io_r')
    tied(s, m3, 'VGND')
    s.wire(x1.pin('out_p'), n.pin('G'))                                    # tgon_p
    s.wire(x1.pin('out_n'), (440, 40))                                     # tgon_n: up and over to M1, down to M3
    s.bus((440, -240), (440, 180), [(440, 40)])
    s.wire((440, 180), m3.pin('G'))
    s.route((440, -240), (880, -240), (880, 0), p.pin('G'))
    supply_ports(s, -100, -240, ['VDPWR', 'VAPWR', 'VGND'])
    s.text(470, 270, 'M3 ties mod to VGND when off', 0.3)
    title(s, -100, -480, ['tt_asw_5v0: Tiny Tapeout GF180 analog switch (tnt)',
                          'M2 nfet_05v0 217/0.6 (7 x 31/0.6), M1 pfet_05v0 592/0.5 (16 x 37/0.5); ctrl = 1: bus <-> mod',
                          'mult: that many switches in parallel on bus (the level shifter not multiplied)'])
    finish_params(s, 'tt_asw_5v0', ['VGND', 'VDPWR', 'VAPWR', 'ctrl', 'mod', 'bus'], {'mult': 1},
                  left=['bus'], right=['mod'], top=['VDPWR', 'VAPWR', 'ctrl'], bottom=['VGND'], width=240, tpitch=80)


def finish_params(s, name, pins, params, tpitch=40, **kw):
    """finish(), then rewrite the symbol with instance parameters (xschem puts them on the .subckt line) and the
    top / bottom pin pitch tpitch."""
    import os
    from common import XDIR, write_symbol
    finish(s, name, pins, **kw)
    write_symbol(os.path.join(XDIR, f'{name}.sym'), params=params, order=list(pins), label=name,
                 dirs=getattr(s, 'dirs', None), tpitch=tpitch, **kw)


def pad():
    s = Sch()
    port(s, (0, 0), 'pin', 'io')
    cp = s.place('devices/capa.sym', 60, 30, name='Cpcb', value='2p')
    r1 = s.place('devices/res.sym', 150, 0, rot=1, name='R1', value='1')
    l1 = s.place('devices/ind.sym', 250, 0, rot=1, name='L1', value='1n')
    dp = s.place('symbols/diode_pd2nw_06v0.sym', 360, -30, rot=2, name='Dp', model='diode_pd2nw_06v0',
                 r_w='50e-6', r_l='3e-6', m='4')
    dn = s.place('symbols/diode_nd2ps_06v0.sym', 360, 30, rot=2, name='Dn', model='diode_nd2ps_06v0',
                 r_w='50e-6', r_l='3e-6', m='4')
    cpad = s.place('devices/capa.sym', 440, 30, name='Cpad', value='1.29p')
    cr1 = s.place('devices/capa.sym', 520, 30, name='Cr1', value="'croute/2'")
    rr = s.place('devices/res.sym', 600, 0, rot=1, name='Rr', value="'rroute'")
    cr2 = s.place('devices/capa.sym', 680, 30, name='Cr2', value="'croute/2'")
    xon = s.place('tt_asw_5v0.sym', 860, 0, name='Xon', mult='1')
    cm = s.place('devices/capa.sym', 1020, 30, name='Cmod', value='250f')
    xoff = s.place('tt_asw_5v0.sym', 860, 220, name='Xoff', mult="'max(n_off,1e-6)'")
    # the series path pin -> pad -> bus -> mod, split at each shunt
    s.bus((0, 0), r1.pin('M'), [cp.pin('p')])
    s.wire(r1.pin('P'), l1.pin('m'))
    s.bus(l1.pin('p'), rr.pin('M'), [(360, 0), cpad.pin('p'), cr1.pin('p')])
    s.bus(rr.pin('P'), xon.pin('bus'), [cr2.pin('p'), (720, 0)])
    s.bus(xon.pin('mod'), (1100, 0), [cm.pin('p')]); port(s, (1100, 0), 'mod', 'io_r')
    for c in (cp, cpad, cr1, cr2, cm):
        sup(s, c.pin('m'), 'VGND')
    sup(s, dn.pin('p'), 'VGND')
    sup(s, dp.pin('m'), 'VDDIO')
    s.route((720, 0), (720, 220), xoff.pin('bus'))
    # switch supplies and controls: Xon on (ctrl = VDPWR), Xoff off (ctrl = VGND)
    for x, c in ((xon, 'VDPWR'), (xoff, 'VGND')):
        for nm, net in (('VDPWR', 'VDPWR'), ('VAPWR', 'VAPWR'), ('ctrl', c)):
            a = x.pin(nm); b = (a[0], a[1] - 30); s.wire(a, b); sup(s, b, net)
        a = x.pin('VGND'); b = (a[0], a[1] + 30); s.wire(a, b); sup(s, b, 'VGND')
    # internal supplies, as the sky130 model
    for i, net in enumerate(('VDDIO', 'VAPWR', 'VDPWR')):
        v = s.place('devices/vsource.sym', 100 + 120 * i, 300, name=f'V{net}', value="'vsup'")
        sup(s, v.pin('p'), net); sup(s, v.pin('m'), 'VGND')
    s.wire((0, 420), (60, 420)); port(s, (0, 420), 'VGND', 'io'); sup(s, (60, 420), 'VGND')
    s.text(90, -60, 'board, bond wire', 0.3)
    s.text(320, -140, 'asig_5p0 pad', 0.3)
    s.text(560, -60, 'route 15-60 ohm', 0.3)
    s.text(800, -140, 'this project (on)', 0.3)
    s.text(980, 300, 'n_off other projects on this pin (off)', 0.3)
    s.text(60, 360, 'internal supplies (vsup)', 0.3)
    title(s, 0, -400, ['pad_model_gf180: one Tiny Tapeout GF180 analog pin, board pin to ua[] (docs/pad_model.md)',
                       'Cpcb / R1 / L1 / Cmod from tnt\'s sky130 pad_model; ESD diodes from the PDK asig_5p0 netlist;',
                       'Cpad 1.29 pF extracted from the asig_5p0 GDS; Croute assumed; n_off 0..3 on ttgf0p3 (default 3)'])
    finish_params(s, 'pad_model_gf180', ['VGND', 'pin', 'mod'],
                  {'rroute': 40, 'croute': '0.2p', 'vsup': 3.3, 'n_off': 3},
                  left=['pin'], right=['mod'], bottom=['VGND'], width=200)


def build():
    lv2hv()
    tt_asw()
    pad()


if __name__ == '__main__':
    build()
