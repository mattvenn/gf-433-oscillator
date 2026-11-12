#!/usr/bin/env python3
"""
Board low-pass filter between the TX pins and the dipole (the harmonic fix, Matt 2026-11-12).

A balanced 5th-order Butterworth low-pass, designed for the dipole's 73 ohm (differential), inserted into the block
bench (sim/tx/tb_tx_drv.py) between pin_p / pin_n and the dipole. Balanced form: each series L is split into two
L/2 (one per line), each differential shunt C becomes 2C from each line to ground, so the common mode is filtered
too. Topologies:
  pi : C - L - C - L - C  (shunt first; the pad's own C sits in parallel with the first C)
  t  : L - C - L - C - L  (series first)
The harmonics come from the bench's fourier of vr (the voltage across the 73 ohm).

    python3 sim/tx/board_lpf.py [corners] --topo pi,t --fc 500e6,600e6 [--rroute 40] [--noff 3]
"""
import argparse
import itertools
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tb_tx_drv as tb  # noqa: E402

G5 = [0.618, 1.618, 2.0, 1.618, 0.618]      # Butterworth n = 5
R0 = tb.RDIP


def values(topo, fc, r0=R0):
    """[(kind, value)] in the differential form: C in F (across the pair), L in H (total of both lines)."""
    w = 2 * math.pi * fc
    kinds = 'CLCLC' if topo == 'pi' else 'LCLCL'
    return [(k, g / (w * r0) if k == 'C' else g * r0 / w) for k, g in zip(kinds, G5)]



STD = [('C', 2 * 4.7e-12), ('L', 2 * 18e-9), ('C', 2 * 15e-12), ('L', 2 * 18e-9), ('C', 2 * 4.7e-12)]
# topo 'pistd': the pi filter from standard values, per line 4.7 pF / 18 nH / 15 pF / 18 nH / 4.7 pF
# (stored here in the differential form used by values(): C across the pair = half the per-line C, L = both lines)
STD = [(k, v / 4 if k == 'C' else v) for k, v in STD]


def filt(topo, fc):
    """Netlist from pin_p / pin_n to the dipole nodes fp / fn."""
    out, a, b = ['Vip pin_p qp 0', 'Vin pin_n qn 0'], 'qp', 'qn'
    for i, (k, v) in enumerate(STD if topo == 'pistd' else values(topo, fc)):
        if k == 'C':
            out += [f'Cf{i}p {a} 0 {2 * v:.4e}', f'Cf{i}n {b} 0 {2 * v:.4e}']
        else:
            na, nb = f'f{i}p', f'f{i}n'
            out += [f'Lf{i}p {a} {na} {v / 2:.4e}', f'Lf{i}n {b} {nb} {v / 2:.4e}']
            a, b = na, nb
    out += [f'Rfp {a} fp 0', f'Rfn {b} fn 0']
    return '\n'.join(out) + '\n'


_deck = tb.deck


def deck_with(topo, fc):
    def deck(*args, **kw):
        d = _deck(*args, **kw)
        if topo == 'none':
            return d
        d = d.replace(f'Rdip pin_p dmid {tb.RDIP}\nCdip dmid pin_n {tb.CDIP}',
                      filt(topo, fc) + f'Rdip fp dmid {tb.RDIP}\nCdip dmid fn {tb.CDIP}')
        return d.replace('let vr = v(pin_p) - v(dmid)', 'let vr = v(fp) - v(dmid)\n'
                         'meas tran ipin_rms rms i(Vip) from=$&t0 to=$&t1').replace(
            'save v(ls)', 'save v(fp) v(fn) i(Vip) v(ls)')
    return deck


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('corners', nargs='*', default=['tt'])
    ap.add_argument('--topo', default='pi,t')
    ap.add_argument('--fc', default='500e6')
    ap.add_argument('--rroute', default='40')
    ap.add_argument('--noff', default='3')
    ap.add_argument('--jobs', type=int, default=20)
    ap.add_argument('--wn5', default='40', help='final-stage N width(s), um')
    ap.add_argument('--tset', type=float, default=80e-9, help='settling time before the 8 measured periods')
    a = ap.parse_args()
    tb.OUT = tb.REPO / 'build' / 'tx_lpf'
    tb.TSET = a.tset
    jobs = []
    for topo, fc, c, rr, no, w in itertools.product(a.topo.split(','), a.fc.split(','), a.corners,
                                                    a.rroute.split(','), a.noff.split(','), a.wn5.split(',')):
        jobs.append((topo, float(fc), c, float(rr), float(no), float(w)))

    print('topo  fc  cn  rr n wn5 | fund dBm |   H2     H3     H4     H5     H6     H7 dBc | Idip  Ipad mA rms | Iavg mA |')
    with ThreadPoolExecutor(a.jobs) as ex:
        futs = []
        for j in jobs:
            futs.append(ex.submit(run_one, j, deck_with(j[0], j[1])))
        for f in futs:
            j, r = f.result()
            res = r['res'] or {}
            g = lambda k: res.get(k, float('nan'))
            print(f"{j[0]:>4} {j[1] / 1e6:4.0f} {j[2]:>2} {j[3]:3g} {j[4]:g} {j[5]:3g} | {g('p1_dbm'):+6.2f} | "
                  + ' '.join(f"{g(f'h{n}_dbc'):6.1f}" for n in range(2, 8))
                  + f" | {g('i_pin_ma'):5.2f} {g('ipad_ma'):5.2f} | {g('i_avg_ma'):5.2f} | {' '.join(r['warn'])}", flush=True)


def run_one(j, dk):
    topo, fc, c, rr, no, w = j
    kw = dict(rroute=rr, noff=no, off=False, edge=100e-12, rsup=1.0, lsup=1e-9)
    tag = f"{c}_{topo}_fc{fc / 1e6:g}_r{rr:g}_n{no:g}_w{w:g}"
    tb.OUT.mkdir(parents=True, exist_ok=True)
    (tb.OUT / '.spiceinit').write_text('set ng_nomodcheck\nset num_threads=1\noption noinit\n')
    cir = tb.OUT / f'{tag}.cir'
    cir.write_text(dk(c, {} if w == 40 else {'wn5': w}, **kw))
    import subprocess
    p = subprocess.run(['nice', '-n', '10', 'ngspice', '-b', cir.name], cwd=tb.OUT, capture_output=True, text=True)
    log = p.stdout + p.stderr
    (tb.OUT / f'{tag}.log').write_text(log)
    bad = [s for s in ('singular', 'Transient op started', 'timestep too small') if s in log]
    res = tb.parse(log, False)
    import re
    m = re.search(r'^ipin_rms\s+=\s+' + tb.NUM, log, re.M)
    if res is not None:
        res['ipad_ma'] = float(m.group(1)) * 1e3 if m else res['i_pin_ma']
    if res and abs(res['vcap_drift_mv']) > 20:
        bad.append(f"not settled: {res['vcap_drift_mv']:.0f} mV")
    return j, dict(res=res, warn=bad)


if __name__ == '__main__':
    main()
