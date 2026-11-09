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
    wa1=0.5, wa2=1.0, wb1=1.5,             # splitter inverters N (wb1 tuned: fundamental phase error -0.03 deg, tt)
    wtgn=1.0, wtgp=2.5,                    # transmission gate N / P
    wx=0.42,                               # cross-coupled keeper inverters N
    wnand_n=1.0, wnand_p=1.25,             # arm NAND2: series NMOS (each), parallel PMOS (each)
    wn5=40.0, taper=4.0, wmin=0.42,        # arm inverters: final N wn5, N_i = wn5 / taper^(5-i), at least wmin
    dcw=10.0, dcl=10.0, dcm=24,            # supply decap: m x W/L nfet_03v3 gate cap (24 x 100 um2 ~ 9.8 pF)
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


def arm(s=S):
    out = ('.subckt tx_arm VDD VSS in en out\n'
           + fet('NAp', 'y0', 'in', 'VDD', 'VDD', 'pfet_03v3', s['wnand_p'])
           + fet('NBp', 'y0', 'en', 'VDD', 'VDD', 'pfet_03v3', s['wnand_p'])
           + fet('NAn', 'y0', 'in', 'ns', 'VSS', 'nfet_03v3', s['wnand_n'])
           + fet('NBn', 'ns', 'en', 'VSS', 'VSS', 'nfet_03v3', s['wnand_n']))
    for i, wn in enumerate(arm_widths(s), 1):
        out += inv(f'M{i}', f'y{i - 1}', 'out' if i == 5 else f'y{i}', wn, s)
    return out + '.ends\n'


def top(s=S):
    return ('.subckt tx_drv VDD VSS ls en_p en_n out_p out_n\n'
            'xsp VDD VSS ls a b tx_split\n'
            'xap VDD VSS a en_p out_p tx_arm\n'
            'xan VDD VSS b en_n out_n tx_arm\n'
            + fet('DC', 'VSS', 'VDD', 'VSS', 'VSS', 'nfet_03v3', s['dcw'], s['dcl'], int(s['dcm']))
            + '.ends\n')


def block(s=None):
    """tx_split, tx_arm and tx_drv as .subckt text (ports of tx_drv: VDD VSS ls en_p en_n out_p out_n)."""
    s = dict(S, **(s or {}))
    return split(s) + arm(s) + top(s)


if __name__ == '__main__':
    print(block(), end='')
