#!/usr/bin/env python3
"""
Upper bound for a slew-controlled TX driver: ideal linear trapezoids (rise = fall = frac x T, antiphase, 0-3.3 V)
through a series source resistance rs into the same pad path (pad_model_gf180, rroute 40, n_off 3) and dipole
(73 ohm + 100 pF) as sim/tx/tb_tx_drv.py. Harmonics of the dipole voltage vr and of the on-chip out_p.

    python3 sim/tx/ideal_trap.py [--outdir build/tx_harm/ideal] [--jobs 8]
Writes <outdir>/ideal.jsonl (one line per corner x rs x frac).
"""
import argparse
import json
import math
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
import tb_tx_drv as tb  # noqa: E402

FRACS = [0.10, 0.15, 0.20, 0.25, 0.28, 0.30, 0.31, 0.32, 0.33, 0.333, 0.34, 0.35, 0.36, 0.37, 0.38, 0.40, 0.42,
         0.45]


def deck(corner, rs, frac):
    T = tb.T
    tr = frac * T
    pw = T / 2 - tr
    return f"""* ideal trapezoid {corner} rs={rs} tr={frac}T
.include {tb.PDK}/design.ngspice
.lib {tb.PDK}/sm141064.ngspice {tb.CORNERS[corner]}
.lib {tb.PDK}/sm141064.ngspice diode_typical
.include {REPO}/sim/pad/tt_asw_5v0.spice
.include {REPO}/sim/pad/pad_model_gf180.spice
.temp 27
Vp sp 0 pulse(0 3.3 0 {tr:.5e} {tr:.5e} {pw:.5e} {T:.5e})
Vn sn 0 pulse(3.3 0 0 {tr:.5e} {tr:.5e} {pw:.5e} {T:.5e})
Rp sp out_p {rs}
Rn sn out_n {rs}
xpp 0 pin_p out_p pad_model_gf180 rroute=40 n_off=3 vsup=3.3
xpn 0 pin_n out_n pad_model_gf180 rroute=40 n_off=3 vsup=3.3
Rdip pin_p dmid {tb.RDIP}
Cdip dmid pin_n {tb.CDIP}
.ic v(dmid)=0
.options method=gear
.control
set num_threads=1
tran 2p {tb.TSET + tb.NPER * T:.4e} 0
let vr = v(pin_p) - v(dmid)
let op = v(out_p)
linearize vr op
set fourgridsize=1000
fourier {tb.F} vr op
.endc
.end
"""


def harm(log, name):
    m = re.search(r'Fourier analysis for ' + name + r':(.*?)(?:Fourier analysis for|\Z)', log, re.S)
    hv = {int(n): float(v) for n, v in re.findall(r'^\s*(\d+)\s+[\d.eE+-]+\s+' + tb.NUM, m.group(1), re.M)}
    return hv


def run(job, out):
    corner, rs, frac = job
    tag = f'{corner}_rs{rs:g}_f{frac:g}'
    cir = out / f'{tag}.cir'
    cir.write_text(deck(corner, rs, frac))
    p = subprocess.run(['nice', '-n', '10', 'ngspice', '-b', cir.name], cwd=out, capture_output=True, text=True)
    log = p.stdout + p.stderr
    (out / f'{tag}.log').write_text(log)
    rec = dict(tag=tag, corner=corner, rs=rs, frac=frac, ok=False)
    try:
        v, o = harm(log, 'vr'), harm(log, 'op')
        rec.update(ok=not any(s in log for s in ('singular', 'Transient op started')),
                   p1_dbm=10 * math.log10(v[1] ** 2 / (2 * tb.RDIP) / 1e-3),
                   **{f'h{n}_dbc': 20 * math.log10(abs(v[n]) / v[1]) for n in range(2, 8)},
                   **{f'op_h{n}_dbc': 20 * math.log10(abs(o[n]) / o[1]) for n in (3, 5, 7)})
    except (AttributeError, KeyError, ValueError):
        pass
    return rec


def main(outdir=REPO / 'build' / 'tx_harm' / 'ideal', jobs=8, corners=('tt', 'ss', 'ff'), rss=(10, 30)):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    (out / '.spiceinit').write_text('set ng_nomodcheck\nset num_threads=1\noption noinit\n')
    todo = [(c, rs, f) for c in corners for rs in rss for f in FRACS]
    with ThreadPoolExecutor(jobs) as ex:
        recs = list(ex.map(lambda j: run(j, out), todo))
    with open(out / 'ideal.jsonl', 'w') as fh:
        for r in recs:
            fh.write(json.dumps(r) + '\n')
    return recs


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--outdir', default=str(REPO / 'build' / 'tx_harm' / 'ideal'))
    ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    for r in main(a.outdir, a.jobs):
        print(r['tag'], ' '.join(f'{k} {v:.1f}' for k, v in r.items() if k.startswith(('h', 'p1', 'op_'))))
