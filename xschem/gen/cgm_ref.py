"""
cgm_ref: the constant-gm (beta-multiplier) reference and the vbn RC filter, as
sim/vco/vco_bias.py netlist() with the chosen sizing (common.WINNER):

  MN1 (diode, vbn) and MN2 (K = kb x MN1, source on R): each nsn units in series, unit w1/l1 x m
      (MN1 m = nsn, MN2 m = nsn x kb). Drawn as the real stacks, unit on unit, gates on one wire.
  R = nwell (rw x lnw) in series with nplus_u (rw x lnp), MN2 source to VSS.
  PMOS mirror MP1/MP2 (wpm/lpm), MP2 the diode.
  Start-up: MS1 (weak, long PMOS, always on) pulls x high while vbn is low, MS3 then feeds
      n2 -> vbn; once vbn is up MS2 pulls x low and MS3 turns off.
  Filter: RF ppolyf_u_1k rf ohm (the run is 1 kOhm/sq), CF cf to VSS -> vbnf (CF an nfet gate cap, as vco_bias cfm=mos; formerly ideal:
      a MOS cap in layout).
vco_bias's Rvbn (1 ohm, naming n1 as vbn) is a plain net here: n1 = vbn.

Textbook layout: VDD rail on top, PMOS mirror (gates joined), the two NMOS stacks under them (gates
joined), R under MN2, VSS rail at the bottom; the start-up sits between the two branches, where it
reaches n2 (the PMOS gate wire) and vbn (the NMOS gate wire) without crossing anything.

    python3 xschem/gen/cgm_ref.py
"""
from common import DEV, P, Sch, place, vmirror, finish, title, bulk, port, supply, wl

PINS = ['VDD', 'VSS', 'vbn', 'vbnf']
NS = int(P['nsn'])


def stack(s, nm, x, y0, flip, top, bot):
    """The nsn-unit series stack of vco_bias device nm, unit k at y0 + 60 k, pin on pin.
    Returns (units, gate x, bulk x)."""
    units = [DEV[nm]] + [DEV[f'{nm}s{i}'] for i in range(1, NS)]
    chain = [top] + [f'{nm.lower()}s{i}' for i in range(1, NS)] + [bot]
    insts = []
    for k, u in enumerate(units):
        assert u['nets'] == [chain[k], 'vbn', chain[k + 1], 'VSS']
        assert (u['w'], u['l'], u['m']) == (units[0]['w'], units[0]['l'], units[0]['m'])
        insts.append(place(s, nm if k == 0 else f'{nm}s{k}', x, y0 + 60 * k, flip=flip, hide=True, dev=u))
    gx, bx = insts[0].pin('G')[0], insts[0].pin('B')[0] + 20 * (1 if not flip else -1)
    s.bus((gx, y0), (gx, y0 + 60 * (NS - 1)), [i.pin('G') for i in insts])
    for i in insts:
        s.wire(i.pin('B'), (bx, i.pin('B')[1]))
    return insts, gx, bx


def build():
    s = Sch()
    xl, xr = -220, 1000
    yvdd, yss, yn0 = -80, 1340, 300
    XL, XR = 0, 480                     # left branch (n2: MP2, MN2, R) flipped; right branch (vbn: MP1, MN1)
    # ---- PMOS mirror
    mp2 = place(s, 'MP2', XL, 0, flip=1)
    mp1 = place(s, 'MP1', XR, 0)
    assert mp2.nets == dict(D='n2', G='n2', S='VDD', B='VDD') and mp1.nets == dict(D='vbn', G='n2', S='VDD', B='VDD')
    vtaps = []
    for m in (mp2, mp1):
        s.wire(m.pin('S'), (m.pin('S')[0], yvdd)); vtaps.append((m.pin('S')[0], yvdd))
        vtaps.append(bulk(s, m, y=yvdd))
    # ---- NMOS stacks, MN2 under MP2, MN1 under MP1
    mn2, g2x, b2x = stack(s, 'MN2', XL, yn0, 1, 'n2', 'nr')
    mn1, g1x, b1x = stack(s, 'MN1', XR, yn0, 0, 'vbn', 'VSS')
    # ---- start-up, between the branches
    ms1 = place(s, 'MS1', 140, 110)
    ms2 = place(s, 'MS2', 140, 210)
    ms3 = place(s, 'MS3', 300, 270)
    assert ms1.nets == dict(D='x', G='VSS', S='VDD', B='VDD') and ms2.nets == dict(D='x', G='vbn', S='VSS', B='VSS')
    assert ms3.nets == dict(D='n2', G='x', S='vbn', B='VSS')
    # n2: MP2 diode, the PMOS gate wire (tapped by MS3's drain), MP2 drain down to MN2
    n2d = (mp2.pin('D')[0], 50)
    s.route(mp2.pin('G'), (mp2.pin('G')[0], 50), n2d, vfirst=True)
    s.bus(mp2.pin('D'), mn2[0].pin('D'), [n2d])
    ms3d = (ms3.pin('D')[0], 0)
    s.bus(mp2.pin('G'), mp1.pin('G'), [ms3d])
    s.wire(ms3.pin('D'), ms3d)
    # vbn: MN1 diode, the NMOS gate wire (tapped by MS3's source and MS2's gate), MP1 drain to MN1
    vbd = (mp1.pin('D')[0], 250)
    s.route(mn1[0].pin('G'), (mn1[0].pin('G')[0], 250), vbd, vfirst=True)
    s.bus(mp1.pin('D'), mn1[0].pin('D'), [vbd])
    s.bus(mn2[0].pin('G'), mn1[0].pin('G'), [ms3.pin('S'), (100, yn0)])
    s.route(ms2.pin('G'), (100, ms2.pin('G')[1]), (100, yn0))
    # x: MS1 / MS2 drains -> MS3 gate
    xj = (ms1.pin('D')[0], 160)
    s.bus(ms1.pin('D'), ms2.pin('D'), [xj])
    s.route(xj, (ms3.pin('G')[0], 160), ms3.pin('G'), vfirst=False)
    s.wire(ms1.pin('G'), (100, ms1.pin('G')[1])); supply(s, (100, ms1.pin('G')[1]), 'VSS')
    bulk(s, ms1, to='S'); supply(s, ms1.pin('S'), 'VDD')
    bulk(s, ms2, to='S'); supply(s, ms2.pin('S'), 'VSS')
    bulk(s, ms3, to='VSS')
    # ---- R in MN2's source: nwell then nplus_u
    # resistors drawn mirrored top-to-bottom (vmirror): M, vco_bias's first terminal, on top
    rbw = vmirror(s, 'RBW', XL - 20, 1170, val=f"nwell {DEV['RBW']['w']:g}/{DEV['RBW']['l']:.3g}")
    rbn = vmirror(s, 'RBN', XL - 20, 1260, val=f"nplus_u {DEV['RBN']['w']:g}/{DEV['RBN']['l']:g}")
    assert rbw.nets == dict(M='nr', P='nrm', B='VSS') and rbn.nets == dict(M='nrm', P='VSS', B='VSS')
    s.wire(mn2[-1].pin('S'), rbw.pin('M'))
    s.wire(rbw.pin('P'), rbn.pin('M'))
    s.wire(rbn.pin('P'), (rbn.pin('P')[0], yss))
    # bulk wires down to the VSS rail (the resistor wells tap the left one)
    s.bus((b2x, yn0), (b2x, yss), [(b2x, yn0 + 60 * k) for k in range(NS)] + [rbw.pin('B'), rbn.pin('B')])
    s.bus((b1x, yn0), (b1x, yss), [(b1x, yn0 + 60 * k) for k in range(NS)])
    s.wire(mn1[-1].pin('S'), (mn1[-1].pin('S')[0], yss))
    s.bus((xl, yss), (b1x, yss), [(b2x, yss), (rbn.pin('P')[0], yss), (mn1[-1].pin('S')[0], yss)])
    port(s, (xl, yss), 'VSS', 'io')
    s.bus((xl, yvdd), (max(x for x, _ in vtaps), yvdd), vtaps)
    port(s, (xl, yvdd), 'VDD', 'io')
    # ---- RC filter vbn -> vbnf, and the outputs
    xf = 780
    rf = vmirror(s, 'RF', xf, 340, val=f"{P['rf'] / 1e6:g} MΩ (ppolyf {DEV['RF']['w']:g}/{DEV['RF']['l']:.3g})")
    assert rf.nets == dict(M='vbn', P='vbnf', B='VSS')
    cfd = DEV['CF']
    assert cfd['nets'] == ['VSS', 'vbnf', 'VSS', 'VSS'], cfd
    cf = place(s, 'CF', xf + 20, 500, val=f"{P['cf'] * 1e12:g} pF: {wl(cfd)}")
    s.bus(vbd, (xr, 250), [(xf, 250)])
    s.wire((xf, 250), rf.pin('M'))
    port(s, (xr, 250), 'vbn', 'out')
    s.bus(rf.pin('P'), cf.pin('G'), [(xf, 420)])
    s.wire((xf, 420), (xr, 420))
    port(s, (xr, 420), 'vbnf', 'out')
    s.wire(rf.pin('B'), (xf - 40, 340)); supply(s, (xf - 40, 340), 'VSS')
    xt = cf.pin('D')[0] + 20                     # S/D/B tied to VSS, as the vg decap
    s.wire(cf.pin('D'), (xt, cf.pin('D')[1])); s.wire(cf.pin('B'), (xt, cf.pin('B')[1]))
    s.bus((xt, cf.pin('D')[1]), (xt, cf.pin('S')[1]), [(xt, cf.pin('B')[1])])
    s.wire(cf.pin('S'), (xt, cf.pin('S')[1]))
    supply(s, (xt, cf.pin('S')[1]), 'VSS')
    # ---- notes
    s.text(30, 420, f'MN2: {NS} in series,', 0.35)
    s.text(30, 450, f"each {DEV['MN2']['w']:g}/{DEV['MN2']['l']:g} ×{DEV['MN2']['m']}", 0.35)
    s.text(270, 420, f'MN1: {NS} in series,', 0.35)
    s.text(270, 450, f"each {DEV['MN1']['w']:g}/{DEV['MN1']['l']:g} ×{DEV['MN1']['m']}", 0.35)
    s.text(200, 20, 'start-up', 0.35)
    s.text(xf - 40, 180, 'RC filter', 0.35)
    title(s, xl, -340, ['cgm_ref: constant-gm (beta-multiplier) reference + vbn RC filter',
                        f"K = {P['kb']}: MN2 is {P['kb']}x MN1; R = nwell + nplus_u in MN2's source",
                        'start-up: MS1 holds x high until vbn rises, MS3 then kicks n2 into vbn'])
    finish(s, 'cgm_ref', PINS, right=['vbnf', 'vbn'], top=['VDD'], bottom=['VSS'], width=160, label='cgm_ref')


if __name__ == '__main__':
    build()
