"""
cgm_ref: the constant-gm (beta-multiplier) reference and the vbn RC filter, as
sim/vco/vco_bias.py netlist() with the chosen sizing (common.CHOSEN):

  MN1 (diode, vbn) and MN2 (K = kb x MN1, source on R): each a series-parallel array of
      nsn units in series x nsn (MN2: nsn x kb) in parallel, unit w1/l1. Drawn as one
      vector instance per array (MN1[1:nsn]): xschem netlists it as nsn devices, the
      i-th from node i to node i+1 of the series chain.
  R = nwell (rw x lnw) in series with nplus_u (rw x lnp), MN2 source to VSS.
  PMOS mirror MP1/MP2 (wpm/lpm), MP2 the diode.
  Start-up: MS1 (weak, long PMOS, always on) pulls x high while vbn is low, MS3 then feeds
      n2 -> vbn; once vbn is up MS2 pulls x low and MS3 turns off.
  Filter: XRF ppolyf_u_3k rf ohm, CF cf to VSS -> vbnf (CF ideal here, as in vco_bias:
      a MOS cap in layout).
vco_bias's Rvbn (1 ohm, naming n1 as vbn) is a plain net here: n1 = vbn.

    python3 xschem/gen/cgm_ref.py
"""
from common import DEV, P, Sch, place, ports, finish, title, gmos

PINS = ['VDD', 'VSS', 'vbn', 'vbnf']


def array(s, nm, x, y, top, bot):
    """nsn-unit series chain as one vector instance; check it against vco_bias's devices."""
    ns = int(P['nsn'])
    units = [DEV[nm]] + [DEV[f'{nm}s{i}'] for i in range(1, ns)]
    chain = [top] + [f'{nm.lower()}s{i}' for i in range(1, ns)] + [bot]
    for i, u in enumerate(units):
        assert u['nets'][0] == chain[i] and u['nets'][2] == chain[i + 1] and u['nets'][1] == 'vbn'
        assert (u['w'], u['l'], u['m']) == (units[0]['w'], units[0]['l'], units[0]['m'])
    u = units[0]
    inst = gmos(s, 'n', x, y, W=u['w'], L=u['l'], m=u['m'], name=f'{nm}[1:{ns}]')
    # vector pins: unit i's D is chain[i], its S chain[i+1] (xschem bus shorthand; the internal
    # nodes netlist as mn1s[1]..: names only, netgen matches them to vco_bias's mn1s1..)
    mid = f'{nm.lower()}s[1:{ns - 1}]'
    s.connect(inst, D=f'{top},{mid}', G='vbn', S=f'{mid},{bot}', B='VSS')
    s.text(x + 30, y + 40, f'{ns} in series x m={u["m"]}', 0.3)
    return inst


def build():
    s = Sch()
    array(s, 'MN1', 0, 0, 'vbn', 'VSS')
    array(s, 'MN2', 400, 0, 'n2', 'nr')
    place(s, 'MP1', 0, -300)
    place(s, 'MP2', 400, -300)
    place(s, 'RBW', 420, 220)
    place(s, 'RBN', 420, 380)
    s.text(470, 200, f"nwell {DEV['RBW']['w']:g} x {DEV['RBW']['l']:g} um", 0.3)
    s.text(470, 360, f"nplus_u {DEV['RBN']['w']:g} x {DEV['RBN']['l']:g} um", 0.3)
    # start-up
    place(s, 'MS1', 800, -300)
    place(s, 'MS2', 800, -60)
    place(s, 'MS3', 1050, -180)
    s.text(780, -440, 'start-up: x high while vbn is low -> MS3 feeds n2 into vbn', 0.3)
    # filter
    rf = place(s, 'RF', 1350, -100)
    cf = DEV['CF']
    c = s.place('devices/capa.sym', 1350, 100, name='CF', value=cf['value'], m='1')
    s.connect(c, p=cf['nets'][0], m=cf['nets'][1])
    s.text(1400, -120, f"ppolyf_u_3k {DEV['RF']['w']:g} x {DEV['RF']['l']:.4g} um = {P['rf'] / 1e6:g} MOhm", 0.3)
    s.text(1400, 90, f"{P['cf'] * 1e12:g} pF (ideal here; MOS cap on silicon)", 0.3)
    s.text(1300, -220, 'vbn RC filter -> vbnf', 0.35)
    ports(s, -400, -300, PINS)
    title(s, -400, -640, ['cgm_ref: constant-gm reference + vbn RC filter',
                          f"MN1/MN2 {P['nsn']:g}x{P['nsn']:g} arrays of {P['w1']:g}/{P['l1']:g} um, K = {P['kb']}; "
                          f"PMOS mirror {P['wpm']:g}/{P['lpm']:g} um",
                          f"R = nwell {P['rw']:g} x {P['lnw']:g} um + nplus_u {P['rw']:g} x {P['lnp']:g} um; "
                          f"filter {P['rf'] / 1e6:g} MOhm / {P['cf'] * 1e12:g} pF",
                          'sizes from sim/vco/vco_bias.py netlist() (winner set, lnw 5.023)'])
    finish(s, 'cgm_ref', PINS, left=['VDD', 'VSS'], right=['vbn', 'vbnf'], width=160)


if __name__ == '__main__':
    build()
