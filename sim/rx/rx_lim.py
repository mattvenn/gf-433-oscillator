#!/usr/bin/env python3
"""
Receiver limiter + comparator (option B), one instance per arm (I, Q).

  inp/inn (rx_bb's outputs, DC ~2 V) -> AC coupling (gates at vb through pseudo-resistors)
  -> stage L: a wideband differential gain stage (rx_bb.dstage), which also limits on large signals
  -> AC coupling -> comparator with internal hysteresis:
       NMOS pair M1/M2 (tail mirror) into PMOS diode loads M3/M4 with cross-coupled PMOS M5/M6 (positive feedback,
       k = (W/L)5 / (W/L)3 < 1 sets the hysteresis), a self-biased output stage (M7..M10) and two inverters
  -> q (full swing 0 / VDD) to uo[4] / uo[5]
The comparator's input offset sees only the AC coupling (it adds to one threshold and subtracts from the other);
the hysteresis is set against the noise at the comparator input (phase A4).

    python3 sim/rx/rx_lim.py                  # print the netlist
    python3 sim/rx/rx_lim.py hyst [--corners ...]   # hysteresis: slow triangle at the comparator input
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rxc  # noqa: E402
import rx_bb  # noqa: E402
import rx_bias  # noqa: E402

S = dict(
    sl_w=4.0, sl_nf=2, sl_l=0.5, sl_mt=1.0, sl_rl=10e3,     # stage L
    cc=0.5e-12,
    vb1=150e3, vb2=100e3, cvb=1e-12,
    c_w=2.0, c_nf=2, c_l=0.5, c_mt=1.0,                    # comparator input pair, tail (x 25 uA)
    c_wl=1.0, c_ll=0.5,                                     # M3/M4 diode loads W, L
    c_k=1.7,                                                # M5/M6 = k x M3 (k > 1: hysteresis)
    c_wo=2.0,                                               # output stage PMOS M7/M8 W (L c_ll); NMOS M9/M10 W/2
    wn_buf=(0.5, 2.0), kp=2.5,                              # output inverters N widths
)


def comparator(s, ip, im, q):
    k = s['c_k']
    return (rxc.nfet('C1', 'ca', ip, 'ct', s['c_w'], s['c_l'], s['c_nf'])
            + rxc.nfet('C2', 'cb', im, 'ct', s['c_w'], s['c_l'], s['c_nf'])
            + rx_bb.tail('Ct', 'ct', s['c_mt'])
            + rxc.pfet('C3', 'ca', 'ca', 'VDD', s['c_wl'], s['c_ll'])
            + rxc.pfet('C4', 'cb', 'cb', 'VDD', s['c_wl'], s['c_ll'])
            + rxc.pfet('C5', 'ca', 'cb', 'VDD', round(k * s['c_wl'], 3), s['c_ll'])
            + rxc.pfet('C6', 'cb', 'ca', 'VDD', round(k * s['c_wl'], 3), s['c_ll'])
            + rxc.pfet('C7', 'cx', 'cb', 'VDD', s['c_wo'], s['c_ll'])
            + rxc.pfet('C8', 'co', 'ca', 'VDD', s['c_wo'], s['c_ll'])
            + rxc.nfet('C9', 'cx', 'cx', 'VSS', s['c_wo'] / 2, s['c_ll'])
            + rxc.nfet('C10', 'co', 'cx', 'VSS', s['c_wo'] / 2, s['c_ll'])
            + rxc.inv('B1', 'co', 'cq', s['wn_buf'][0], s['kp'] * s['wn_buf'][0])
            + rxc.inv('B2', 'cq', q, s['wn_buf'][1], s['kp'] * s['wn_buf'][1]))


def block(s=None):
    s = dict(S, **(s or {}))
    return ('.subckt rx_lim VDD VSS inp inn q nb enb\n'
            + rx_bb.vbias(s)
            + rx_bb.couple('L', 'inp', 'inn', 'glp', 'gln', s['cc'], 'vb')
            + rx_bb.dstage('L', 'glp', 'gln', 'lp', 'ln', s['sl_w'], s['sl_nf'], s['sl_l'], s['sl_mt'], s['sl_rl'])
            + rx_bb.couple('C', 'lp', 'ln', 'gcp', 'gcn', s['cc'], 'vb')
            + comparator(s, 'gcp', 'gcn', 'q')
            + '.ends\n')


def hyst_deck(corner, s=None, amp=0.05, f=20e3, vos=0.0):
    """Comparator alone: a slow triangle (+-amp, f) differential on gcp/gcn around vb (DC set by ideal sources)."""
    s = dict(S, **(s or {}))
    sub = ('.subckt cmp VDD VSS gcp gcn q nb\n' + comparator(s, 'gcp', 'gcn', 'q') + '.ends\n')
    T = 1 / f
    return f"""* comparator hysteresis {corner}
{rxc.hdr(corner)}{rx_bias.block()}{sub}
VDD VDD 0 {rxc.VDD}
VSS VSS 0 0
Ven en 0 {rxc.VDD}
Xb VDD VSS en enb nb rx_bias
vcm cm 0 1.0
vd d 0 pwl(0 0 {T / 4} {amp} {3 * T / 4} {-amp} {5 * T / 4} {amp} {7 * T / 4} {-amp} {2 * T} 0)
Bp gcp 0 V=v(cm)+v(d)/2+{vos / 2}
Bn gcn 0 V=v(cm)-v(d)/2-{vos / 2}
Xc VDD VSS gcp gcn q nb cmp
.control
option temp=27
tran {T / 4000} {2 * T}
let dd = v(gcp)-v(gcn)
meas tran vup find dd when v(q)={rxc.VDD / 2} rise=1
meas tran vdn find dd when v(q)={rxc.VDD / 2} fall=1
meas tran vup2 find dd when v(q)={rxc.VDD / 2} rise=2
meas tran vdn2 find dd when v(q)={rxc.VDD / 2} fall=2
let idd = -mean(i(VDD))
echo "IDD $&idd"
.endc
.end
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', nargs='?', default='print')
    ap.add_argument('--corners', default='typical')
    ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--tag', default='hyst')
    a = ap.parse_args()
    s = dict(S)
    for kv in a.set:
        k, v = kv.split('=')
        s[k] = float(v)
    if a.mode == 'print':
        print(block(s), end='')
        return
    t0 = time.time()

    def one(c):
        d, log, bad = rxc.run(rxc.CN[c], hyst_deck(c, s), sub=a.tag)
        m = rxc.meas(log)
        r = dict(corner=rxc.CN[c], vup=m.get('vup'), vdn=m.get('vdn'), vup2=m.get('vup2'), vdn2=m.get('vdn2'), bad=bad)
        if r['vup'] is not None and r['vdn'] is not None:
            r['hyst'] = (r['vup'] - r['vdn']) / 2
            r['offset'] = (r['vup'] + r['vdn']) / 2
        print(json.dumps(r), flush=True)
        return r
    rows = rxc.pmap(one, [{'tt': 'typical'}.get(c, c) for c in a.corners.split(',')], 8)
    (rxc.BUILD / a.tag / 'rows.json').write_text(json.dumps(dict(S=s, rows=rows), indent=1))
    print(f'{time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
