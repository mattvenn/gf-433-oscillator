#!/usr/bin/env python3
"""
The dipole TX driver circuit (source of truth for the schematic, the block benches and the layout's LVS source).

  lsdiv ls (0-3.3 V) -> TAP -> phase splitter -> a ---> arm p: NAND2(a, en_p) -> 5 inverters (taper) -> out_p
                                               -> b ---> arm n: NAND2(b, en_n) -> 5 inverters (taper) -> out_n

  tx_split : the tap inverter T on ls (t = !ls), then two paths to antiphase outputs:
             a = A2(A1(t))         two inverters          (a = !ls)
             b = TG(B1(t))         one inverter + an always-on transmission gate, matched to A2's delay (b = ls)
             plus a weak cross-coupled inverter pair (XA: b -> a, XB: a -> b) that pulls the two edges together.
  tx_arm   : out = in & en. NAND2 (in on the NMOS next to the output, the fast input) then 5 inverters: 6 inversions.
             en = 0: the NAND output is high, so out is held low (both arms off = no DC across the dipole).
  tx_drv   : tx_split + two tx_arm + the supply decap DC (nfet_03v3 gate cap, gate VDD, S/D/B VSS).

shape=1 (a study, docs/tx_harmonics.md; shape=0 gives the as-built netlist, byte for byte): the arm's stage 4 is
split into two predrivers from y3, so the final stage turns each device on slowly and off fast (break-before-make):
  gp (final PMOS gate): full-size PMOS pull-up (P off fast); pull-down = NMOS switch (y3) over an NMOS current
       source on vsn, current knp * islew * trim (P on slowly).
  gn (final NMOS gate): full-size NMOS pull-down (N off fast); pull-up = PMOS switch (y3) under a PMOS current
       source on vsp, current islew * trim (N on slowly).
  tx_slew_bias: an ideal reference current into an NMOS diode (vsn), mirrored into a PMOS diode (vsp); the legs are
       kmir x the diodes. The real reference current would come from the constant-gm reference (vbn), not modelled.
  cmil: an optional Miller cap from out to each final gate (ideal C in the study): the turn-on edge then slews at
       about I / cmil, linear, instead of following the final device's square-law knee.
  Device widths follow the current at fixed densities jn / jp (uA/um), so a larger islew is a wider leg at the
  same bias (as a trim's parallel legs would be).

All devices are 3.3 V nfet_03v3 / pfet_03v3. VDD is the driver's own supply (VDPWR, its own Metal4 stripe and
decap branch). Sizes are in S (um); block(S) gives the netlists as .subckt (tx_split, tx_arm, tx_drv), the same
hierarchy as the xschem sheets (xschem/gen/tx_drv.py), which xschem/gen/check.py compares against.

    python3 sim/tx/tx_drv.py          # print the netlist
"""
import math
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'sim' / 'vco'))
import vco_bias as vb  # noqa: E402

L = 0.28            # all gates
S = dict(
    kp=2.5,                                # P/N width ratio of every inverter
    wt=0.42,                               # tap inverter N (on lsdiv's ls node: keep it small)
    wa1=0.5, wa2=1.0, wb1=1.5,             # splitter inverters N (wb1 tuned: fundamental phase error +0.05 deg, tt)
    wtgn=1.0, wtgp=2.5,                    # transmission gate N / P
    wx=0.42,                               # cross-coupled keeper inverters N
    wnand_n=1.0, wnand_p=1.25,             # arm NAND2: series NMOS (each), parallel PMOS (each)
    wn5=40.0, taper=4.0, wmin=0.42,        # arm inverters: final N wn5, N_i = wn5 / taper^(5-i), at least wmin
    dcw=10.0, dcl=10.0, dcm=24,            # supply decap: m x W/L nfet_03v3 gate cap (24 x 100 um2 ~ 9.8 pF)
    shape=0,                               # 1: slew-controlled final stage (study, docs/tx_harmonics.md); 0: as built
    islew=0.25e-3,                         # shape=1: starved current that turns the final NMOS on (gn rising), A
    knp=2.5,                               # shape=1: the final PMOS's turn-on current (gp falling) / islew
    kmir=10.0,                             # shape=1: starved leg / bias diode current ratio
    trim=1.0,                              # shape=1: trim multiplier on both starved legs (parallel legs)
    jn=20.0, jp=8.0,                       # shape=1: starved current density NMOS / PMOS (uA/um), L = lcs
    lcs=0.5,                               # shape=1: starved current-source length (um)
    kswn=0.2, kswp=0.2,                    # shape=1: series switch width / its current source's width
    cmil=0.0,                              # shape=1: Miller cap out -> gp and out -> gn (F, ideal; 0 = none)
)


WFP = 20.0          # widest P finger (um): an inverter wider than that is nf fingers, the same nf for its N and P,
                    # so each finger is one vertical poly gate shared by the N and P rows (the layout's columns).
                    # The models stop at W 100 um anyway.


def fet(name, d, g, s, b, typ, w, l=L, m=1):
    return vb.fet(name, d, g, s, b, typ, round(w, 4), l, int(m))


def nfing(wn, s):
    return max(1, math.ceil(wn * s['kp'] / WFP - 1e-9))


def inv(name, i, o, wn, s):
    nf = nfing(wn, s)
    return (fet(f'{name}p', o, i, 'VDD', 'VDD', 'pfet_03v3', wn * s['kp'] / nf, m=nf)
            + fet(f'{name}n', o, i, 'VSS', 'VSS', 'nfet_03v3', wn / nf, m=nf))


def arm_widths(s=S):
    """N widths of the 5 arm inverters, stage 1 (after the NAND) to stage 5 (the output)."""
    return [max(s['wmin'], s['wn5'] / s['taper'] ** (5 - i)) for i in range(1, 6)]


def split(s=S):
    return ('.subckt tx_split VDD VSS ls a b\n'
            + inv('T', 'ls', 't', s['wt'], s)
            + inv('A1', 't', 'ta', s['wa1'], s) + inv('A2', 'ta', 'a', s['wa2'], s)
            + inv('B1', 't', 'tb', s['wb1'], s)
            + fet('TGn', 'b', 'VDD', 'tb', 'VSS', 'nfet_03v3', s['wtgn'])
            + fet('TGp', 'b', 'VSS', 'tb', 'VDD', 'pfet_03v3', s['wtgp'])
            + inv('XA', 'b', 'a', s['wx'], s) + inv('XB', 'a', 'b', s['wx'], s)
            + '.ends\n')


def fetw(name, d, g, s_, b, typ, w, l=L):
    """One device of total width w, split into m equal fingers of at most WFP."""
    m = max(1, math.ceil(w / WFP - 1e-9))
    return fet(name, d, g, s_, b, typ, max(0.42, w / m), l, m)


def slew_currents(s):
    """(I that turns the final PMOS on, I that turns the final NMOS on), A."""
    return s['knp'] * s['islew'] * s['trim'], s['islew'] * s['trim']


def slew_bias(s):
    ipon, inon = slew_currents(s)
    wdn = max(0.42, ipon / s['trim'] / s['kmir'] / (s['jn'] * 1e-6))   # NMOS diode
    iref = wdn * s['jn'] * 1e-6
    i2 = inon / s['trim'] / s['kmir']                                     # into the PMOS diode
    wm2 = max(0.42, i2 / (s['jn'] * 1e-6))
    wdp = wm2 * s['jn'] / s['jp']
    return ('.subckt tx_slew_bias VDD VSS vsn vsp\n'
            f'Iref VDD vsn dc {iref:.6g}\n'
            + fetw('BDn', 'vsn', 'vsn', 'VSS', 'VSS', 'nfet_03v3', wdn, s['lcs'])
            + fetw('BMn', 'vsp', 'vsn', 'VSS', 'VSS', 'nfet_03v3', wm2, s['lcs'])
            + fetw('BDp', 'vsp', 'vsp', 'VDD', 'VDD', 'pfet_03v3', wdp, s['lcs'])
            + '.ends\n')


def arm(s=S):
    if s['shape']:
        return arm_shaped(s)
    out = ('.subckt tx_arm VDD VSS in en out\n'
           + fet('NAp', 'y0', 'in', 'VDD', 'VDD', 'pfet_03v3', s['wnand_p'])
           + fet('NBp', 'y0', 'en', 'VDD', 'VDD', 'pfet_03v3', s['wnand_p'])
           + fet('NAn', 'y0', 'in', 'ns', 'VSS', 'nfet_03v3', s['wnand_n'])
           + fet('NBn', 'ns', 'en', 'VSS', 'VSS', 'nfet_03v3', s['wnand_n']))
    for i, wn in enumerate(arm_widths(s), 1):
        out += inv(f'M{i}', f'y{i - 1}', 'out' if i == 5 else f'y{i}', wn, s)
    return out + '.ends\n'


def arm_shaped(s):
    ipon, inon = slew_currents(s)
    wn = arm_widths(s)
    wcn = ipon / (s['jn'] * 1e-6)            # gp pull-down current source (NMOS on vsn)
    wcp = inon / (s['jp'] * 1e-6)            # gn pull-up current source (PMOS on vsp)
    out = ('.subckt tx_arm VDD VSS in en out vsn vsp\n'
           + fet('NAp', 'y0', 'in', 'VDD', 'VDD', 'pfet_03v3', s['wnand_p'])
           + fet('NBp', 'y0', 'en', 'VDD', 'VDD', 'pfet_03v3', s['wnand_p'])
           + fet('NAn', 'y0', 'in', 'ns', 'VSS', 'nfet_03v3', s['wnand_n'])
           + fet('NBn', 'ns', 'en', 'VSS', 'VSS', 'nfet_03v3', s['wnand_n']))
    for i in (1, 2, 3):
        out += inv(f'M{i}', f'y{i - 1}', f'y{i}', wn[i - 1], s)
    out += (fetw('M4p', 'gp', 'y3', 'VDD', 'VDD', 'pfet_03v3', wn[3] * s['kp'])       # final P off: fast
            + fetw('M4ps', 'gp', 'y3', 'gpm', 'VSS', 'nfet_03v3', wcn * s['kswn'])  # final P on: starved
            + fetw('M4pc', 'gpm', 'vsn', 'VSS', 'VSS', 'nfet_03v3', wcn, s['lcs'])
            + fetw('M4n', 'gn', 'y3', 'VSS', 'VSS', 'nfet_03v3', wn[3])               # final N off: fast
            + fetw('M4ns', 'gn', 'y3', 'gnm', 'VDD', 'pfet_03v3', wcp * s['kswp'])  # final N on: starved
            + fetw('M4nc', 'gnm', 'vsp', 'VDD', 'VDD', 'pfet_03v3', wcp, s['lcs']))
    nf = nfing(wn[4], s)
    out += (fet('M5p', 'out', 'gp', 'VDD', 'VDD', 'pfet_03v3', wn[4] * s['kp'] / nf, m=nf)
            + fet('M5n', 'out', 'gn', 'VSS', 'VSS', 'nfet_03v3', wn[4] / nf, m=nf))
    if s['cmil']:
        out += f"CMp out gp {s['cmil']:.4g}\nCMn out gn {s['cmil']:.4g}\n"
    return out + '.ends\n'


def top(s=S):
    if s['shape']:
        return ('.subckt tx_drv VDD VSS ls en_p en_n out_p out_n\n'
                'xsp VDD VSS ls a b tx_split\n'
                'xbias VDD VSS vsn vsp tx_slew_bias\n'
                'xap VDD VSS a en_p out_p vsn vsp tx_arm\n'
                'xan VDD VSS b en_n out_n vsn vsp tx_arm\n'
                + fet('DC', 'VSS', 'VDD', 'VSS', 'VSS', 'nfet_03v3', s['dcw'], s['dcl'], int(s['dcm']))
                + '.ends\n')
    return ('.subckt tx_drv VDD VSS ls en_p en_n out_p out_n\n'
            'xsp VDD VSS ls a b tx_split\n'
            'xap VDD VSS a en_p out_p tx_arm\n'
            'xan VDD VSS b en_n out_n tx_arm\n'
            + fet('DC', 'VSS', 'VDD', 'VSS', 'VSS', 'nfet_03v3', s['dcw'], s['dcl'], int(s['dcm']))
            + '.ends\n')


def block(s=None):
    """tx_split, tx_arm and tx_drv as .subckt text (ports of tx_drv: VDD VSS ls en_p en_n out_p out_n)."""
    s = dict(S, **(s or {}))
    return split(s) + (slew_bias(s) if s['shape'] else '') + arm(s) + top(s)


if __name__ == '__main__':
    print(block(), end='')
