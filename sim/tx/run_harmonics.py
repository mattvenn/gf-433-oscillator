#!/usr/bin/env python3
"""
Driver for docs/handoff_tx_harmonics.md (option 1: slew-controlled final stage), runs V, I, A-D in one chain.

  V  validate: shape=0 netlist == main's; today's circuit at tt, rroute 40, n_off 3 gives H3 ~ -14.1, H5 ~ -23.3 dBc
  I  bound: ideal linear trapezoids through the same pad path (sim/tx/ideal_trap.py), tt / ss / ff, rs 10 / 30 ohm
  A  baseline: today's circuit, 5 corners x rroute 15 / 40 / 60 x n_off 0 / 3
  B  tt sweep, shape=1: islew (12 log steps 50 uA - 2 mA, x1.4) x knp, without (cmil 0) and with a Miller cap
  C  the tt-best (cmil, knp) at 5 corners x the islew grid: H3 / H5 against islew per corner, each corner's best
  D  robustness at the tt-best islew and at each corner's best trim code (islew x 0.7 / 1 / 1.4 / 2): 5 corners x
     rroute 15 / 40 / 60 x n_off 0 / 3; tt at 20 / 35 C; VDD 3.15 V at the worst corner; --off at tt.

Selection score (B, C, trim): max(H3, H5) in dBc, among runs with fund >= +3 dBm and duty 48-52 % (relaxed to
45-55 %, then to any duty, if nothing qualifies). Results: build/tx_harm/<step>/results.jsonl, the selections in
build/tx_harm/sel.json, status in build/tx_harm/status.txt, DONE / FAILED at the end. Then sim/tx/harm_report.py.

    python3 sim/tx/run_harmonics.py [--jobs 26] [--from B]
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ideal_trap  # noqa: E402
import tb_tx_drv as tb  # noqa: E402
import tx_drv  # noqa: E402

REPO = HERE.parents[1]
B = REPO / 'build' / 'tx_harm'
CORNERS = ['tt', 'ss', 'ff', 'sf', 'fs']
ISLEW = [round(50e-6 * 1.4 ** k, 9) for k in range(12)]       # 50 uA ... 2.0 mA
TRIM = [0.7, 1.0, 1.4, 2.0]
STEPS = ['V', 'I', 'A', 'B', 'C', 'D']
JOBS = 8


def status(msg):
    B.mkdir(parents=True, exist_ok=True)
    line = f'{time.strftime("%Y-%m-%d %H:%M:%S")} {msg}'
    with open(B / 'status.txt', 'a') as fh:
        fh.write(line + '\n')
    print(line, flush=True)


def kw(rroute=40, noff=3, off=False, temp=27, vdd=3.3):
    return dict(rroute=float(rroute), noff=float(noff), off=off, edge=100e-12, rsup=1.0, lsup=1e-9, pex=None,
                temp=temp, vdd=vdd)


def runall(step, jobs):
    """jobs: (corner, sizes, kw). Runs into build/tx_harm/<step>/, returns the records; checks every one."""
    tb.OUT = B / step
    tb.OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(JOBS) as ex:
        recs = list(ex.map(tb.run, jobs))
    bad = [r for r in recs if not r['res'] or any('singular' in w or 'Transient op' in w for w in r['warn'])]
    if len(recs) != len(jobs) or len(bad) > 0.05 * len(jobs):
        raise RuntimeError(f'step {step}: {len(bad)} of {len(jobs)} runs failed, e.g. '
                           + '; '.join(f"{r['tag']} {r['warn']}" for r in bad[:5]))
    return recs


def score(r):
    x = r['res']
    return max(x['h3_dbc'], x['h5_dbc'])


def pick(recs):
    """Best record by score, with the fundamental and duty limits relaxed in turn."""
    ok = [r for r in recs if r['res'] and 'h3_dbc' in r['res'] and 'duty_p' in r['res']]
    for lo, hi in ((48, 52), (45, 55), (0, 100)):
        c = [r for r in ok if r['res'].get('p1_dbm', -99) >= 3 and lo <= r['res']['duty_p'] <= hi
             and lo <= r['res']['duty_n'] <= hi]
        if c:
            return min(c, key=score), (lo, hi)
    return min(ok, key=score), None


def step_V():
    old = subprocess.run(['git', 'show', 'main:sim/tx/tx_drv.py'], cwd=REPO, capture_output=True, text=True,
                         check=True).stdout
    p = B / 'tx_drv_main.py'
    p.write_text(old)
    a = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, cwd=HERE).stdout
    if a != tx_drv.block():
        raise RuntimeError('shape=0 netlist differs from main')
    r = runall('V', [('tt', {}, kw())])[0]['res']
    if abs(r['h3_dbc'] + 14.1) > 0.6 or abs(r['h5_dbc'] + 23.3) > 0.6:
        raise RuntimeError(f"baseline H3 {r['h3_dbc']:.2f} H5 {r['h5_dbc']:.2f} dBc, expected -14.1 / -23.3")
    status(f"V ok: shape=0 netlist identical to main; tt H3 {r['h3_dbc']:.2f} H5 {r['h5_dbc']:.2f} dBc, "
           f"vcap drift {r['vcap_drift_mv']:.1f} mV")


def step_I():
    recs = ideal_trap.main(B / 'I', JOBS)
    if sum(r['ok'] for r in recs) < len(recs):
        raise RuntimeError('ideal trapezoid runs failed: ' + ', '.join(r['tag'] for r in recs if not r['ok']))


def step_A():
    runall('A', [(c, {}, kw(rr, no)) for c in CORNERS for rr in (15, 40, 60) for no in (0, 3)])


def step_B(sel):
    jobs = [('tt', dict(shape=1, islew=i, knp=k, cmil=0.0), kw()) for i in ISLEW for k in (1.5, 2, 2.5, 3, 4)]
    jobs += [('tt', dict(shape=1, islew=i, knp=k, cmil=c), kw()) for c in (50e-15, 100e-15) for i in ISLEW
             for k in (1, 1.4, 2)]
    recs = runall('B', jobs)
    best, lim = pick(recs)
    sel['B'] = dict(sizes=best['sizes'], res=best['res'], duty_window=lim)
    status(f"B best: {best['tag']} H3 {best['res']['h3_dbc']:.1f} H5 {best['res']['h5_dbc']:.1f} dBc, "
           f"fund {best['res']['p1_dbm']:+.2f} dBm, duty window {lim}")


def step_C(sel):
    s0 = sel['B']['sizes']
    recs = runall('C', [(c, dict(s0, islew=i), kw()) for c in CORNERS for i in ISLEW])
    sel['C'] = {}
    for c in CORNERS:
        best, lim = pick([r for r in recs if r['corner'] == c])
        sel['C'][c] = dict(islew=best['sizes']['islew'], res=best['res'], duty_window=lim)
        status(f"C {c}: best islew {best['sizes']['islew'] * 1e6:.0f} uA H3 {best['res']['h3_dbc']:.1f} "
               f"H5 {best['res']['h5_dbc']:.1f} dBc fund {best['res']['p1_dbm']:+.2f} dBm")


def step_D(sel):
    s0 = sel['B']['sizes']
    # trim codes at rroute 40, n_off 3: pick each corner's code
    recs = runall('D', [(c, dict(s0, trim=t), kw()) for c in CORNERS for t in TRIM])
    sel['trim'] = {}
    for c in CORNERS:
        best, lim = pick([r for r in recs if r['corner'] == c])
        sel['trim'][c] = dict(trim=best['sizes']['trim'], res=best['res'], duty_window=lim)
    status('D trim codes: ' + ', '.join(f"{c} x{v['trim']:g}" for c, v in sel['trim'].items()))
    jobs = []
    for c in CORNERS:
        for t in sorted({1.0, sel['trim'][c]['trim']}):
            jobs += [(c, dict(s0, trim=t), kw(rr, no)) for rr in (15, 40, 60) for no in (0, 3)]
    jobs += [('tt', dict(s0, trim=1.0), kw(temp=t)) for t in (20, 35)]
    worst = max(CORNERS, key=lambda c: score(dict(res=sel['trim'][c]['res'])))
    sel['worst'] = worst
    jobs += [(worst, dict(s0, trim=sel['trim'][worst]['trim']), kw(vdd=3.15))]
    jobs += [('tt', dict(s0, trim=1.0), kw(off=True))]
    recs = runall('D', jobs)
    off = [r for r in recs if r['off']][0]['res']
    if max(abs(off['out_hi']), abs(off['out_lo'])) > 0.05:
        raise RuntimeError(f"--off: out_p {off['out_lo']:.3f}..{off['out_hi']:.3f} V, not held low")
    status(f"D done: worst corner {worst}; off out_p {off['out_lo']:.3f}..{off['out_hi']:.3f} V, "
           f"I avg {off['i_avg_ma']:.3f} mA")


def main():
    global JOBS
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument('--from', dest='start', default='V', choices=STEPS)
    a = ap.parse_args()
    JOBS = a.jobs
    for f in ('DONE', 'FAILED'):
        (B / f).unlink(missing_ok=True)
    selp = B / 'sel.json'
    sel = json.loads(selp.read_text()) if a.start != 'V' and selp.exists() else {}
    t0 = time.time()
    cur = None
    try:
        for i, st in enumerate(STEPS[STEPS.index(a.start):], STEPS.index(a.start) + 1):
            cur = st
            status(f'Running: step {st} ({i}/{len(STEPS)})')
            f = globals()[f'step_{st}']
            f(sel) if st in 'BCD' else f()
            selp.write_text(json.dumps(sel, indent=1))
            status(f'step {st} done')
        (B / 'DONE').write_text(f'done in {time.time() - t0:.0f} s\n')
        status('DONE')
    except Exception:
        tail = traceback.format_exc()
        (B / 'FAILED').write_text(f'step {cur}\n{tail}')
        status(f'FAILED in step {cur}: {tail.splitlines()[-1]}')
        sys.exit(1)


if __name__ == '__main__':
    main()
