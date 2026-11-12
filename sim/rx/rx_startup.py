#!/usr/bin/env python3
"""
Phase A1 start-up check: power-on of the ring with both taps (sim/pn/cfed_startup.py's deck, unchanged circuit),
plus lsdiv on a0 (schematic block, the /4 and the TX tap splitter as its load) and the RX Q tap rx_lsq on a2
(rx_en = 1, its header on) with lsdiv's Cpa / Cpg parasitic stand-ins on both. Every node at 0 V at t = 0, VDD
ramped 0 -> 3.3 V in 10 us (uic), tt 27 C, codes 0 and 31 (the two ends, as in docs/cfed_startup_results.md).

Pass: the ring runs in the fundamental mode at the end (a0 -> a2 phase 0.2 +- 0.07 of a period), f within 1 % of
the same deck without the RX tap (base) at the same time, and lsq toggles.

    python3 sim/rx/rx_startup.py [--tstop 40e-6]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'sim' / 'pn'))
sys.path.insert(0, str(REPO / 'sim' / 'lsdiv'))
sys.path.insert(0, str(REPO / 'sim' / 'tx'))
import rxc  # noqa: E402
import cfed_startup as cs  # noqa: E402  (read-only: params, sources, the ring)
import lsdiv as LD  # noqa: E402
import tx_drv  # noqa: E402
import rx_lo  # noqa: E402


def deck(code, case, tstop, tmax=20e-12, tramp=10e-6):
    p = cs.params()
    body, _ = cs.vb.netlist(p)
    blk = (LD.block() + 'Xls vdd 0 a0 ck ls lsdiv\n' + f'Cpa a0 0 {LD.S["cpa"]}\nCpg xls.lg 0 {LD.S["cpg"]}\n'
           + f'Cwire ck 0 {LD.S["cwire"]}\n' + tx_drv.split(tx_drv.S) + 'Xtxs vdd 0 ls txa txb tx_split\n')
    vec = 'v(vdd) v(vg) v(a0) v(a2) v(ls)'
    if case == 'rx':
        blk += (rx_lo.lsq() + 'Xq vdd 0 a2 0 lsq rx_lsq\n'
                + f'Cpaq a2 0 {LD.S["cpa"]}\nCpgq xq.lg 0 {LD.S["cpg"]}\n')
        vec += ' v(lsq)'
    return f"""* rx start-up tt 27 C code {code} {case}
{cs.tcm.HDR.format(corner='typical')}{cs.sources(p, code, tramp)}{body}{blk}.control
option temp=27
set filetype=binary
save {vec}
tran 1n {tstop} 0 {tmax} uic
write out.raw {vec}
quit
.endc
.end
"""


def analyse(d, tstop):
    pl = rxc.read_raw(d / 'out.raw')[0]['vars']
    t = pl['time']
    end = t > tstop - 2e-6
    vg = pl['v(vg)'][end].mean()
    thr = (3.3 + vg) / 2
    ra = rxc.xings(t[end], pl['v(a0)'][end], thr)
    r2 = rxc.xings(t[end], pl['v(a2)'][end], thr)
    per = np.median(np.diff(ra))
    ph = [((r2[r2 > x][0] - x) / per) % 1 for x in ra[:-2] if (r2 > x).any()]
    r = dict(f=1 / per, mode=float(np.median(ph)), vg=float(vg))
    # first time after which a0 keeps toggling (no gap > 100 ns between rises)
    rr = rxc.xings(t, pl['v(a0)'], 1.65)
    gaps = np.where(np.diff(rr) > 100e-9)[0]
    r['t_osc'] = float(rr[gaps[-1] + 1]) if len(gaps) else float(rr[0]) if len(rr) else None
    if 'v(lsq)' in pl:
        r['lsq_toggles'] = int(len(rxc.xings(t[end], pl['v(lsq)'][end], 1.65)))
    r['ls_toggles'] = int(len(rxc.xings(t[end], pl['v(ls)'][end], 1.65)))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tstop', type=float, default=40e-6)
    a = ap.parse_args()
    jobs = [(c, k) for c in (0, 31) for k in ('base', 'rx')]

    def one(j):
        c, k = j
        d, log, bad = rxc.run(f'c{c}_{k}', deck(c, k, a.tstop), sub='startup')
        try:
            r = analyse(d, a.tstop)
        except Exception as e:  # noqa: BLE001
            r = dict(error=str(e))
        r.update(code=c, case=k, bad=bad)
        print(json.dumps(r), flush=True)
        return r
    rows = rxc.pmap(one, jobs, 4)
    (rxc.BUILD / 'startup' / 'rows.json').write_text(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main()
