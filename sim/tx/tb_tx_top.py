#!/usr/bin/env python3
"""
The TX driver on its real source: the extracted vco_top (layout/pex/vco_top_<c|rcx>.spice, as sim/top/top_pex.py) with
lsdiv's ls node brought out as a port, driving the schematic tx_drv (sim/tx/tx_drv.py block()) -> pad_model_gf180 per
arm -> dipole 73 ohm + 100 pF. Code 9, vctrl 1.65 V (top_pex.py's operating point, so its results are the no-driver
reference).

Cases (supplies: ring VDD, VDD_LS, the driver's VDD_TX):
  off    : en_p = en_n = 0. Only the tap inverter loads ls (the splitter still toggles): f(a0) and LS duty shift.
  own    : drivers on. VDD_TX from its own 3.3 V source through Rsup + Lsup (1 ohm + 1 nH, assumed); ring VDD and
           VDD_LS ideal (the driver on its own VDPWR stripe and decap, star at the grid).
  shared : drivers on. Ring VDD, VDD_LS and VDD_TX all behind ONE Rsup + Lsup (worst case: a common supply path).
Measured over the last 40 % of tstop: f(a0) (mid-swing) and its period jitter, f / 4 ratio, LS duty, P into the
dipole (total, and the fundamental by a DFT at f(a0) over whole periods), out_p / out_n duty and the fundamental
phase error, I(VDD_TX) avg / rms, ripple (peak-peak) on the ring VDD and VDD_TX.

    python3 sim/tx/tb_tx_top.py run [--jobs 8] [--only NAME,...] [--tstop 1.2e-6]
    python3 sim/tx/tb_tx_top.py summary         # -> sim/tx/results/top.md + top.json
Outputs: build/tx_top/<name>/ (deck, log, raw). Runs under nice -n 10, one thread per ngspice.
"""
import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'sim/top'))
sys.path.insert(0, str(REPO / 'sim/lsdiv'))
sys.path.insert(0, str(REPO / 'tools'))
import tx_drv  # noqa: E402
import top_pex as TP  # noqa: E402  (read-only: PEX, VBN0, the no-driver references)
import lsdiv as LD  # noqa: E402  (read-only: freq, duty, STD)
from rawread import read_raw  # noqa: E402

OUT = REPO / 'build' / 'tx_top'
RES = HERE / 'results'
PDK = '/foss/pdks/gf180mcuD/libs.tech/ngspice'
CODE, VCTRL = 9, 1.65
RDIP, CDIP = 73.0, 100e-12
SAVE = ('v(a0) v(ck) v(vg) v(vbn) v(xtop.vbnf) v(ls) v(vdd) v(vls) v(vtx) i(vdd_s) i(vls_s) i(vtx_s) '
        'v(out_p) v(out_n) v(pin_p) v(pin_n) v(dmid) v(xdrv.a) v(xdrv.b)')


def topx(pex):
    """The extracted vco_top; ls is its last port (lsdiv's level-shifter output, since 2026-11-09)."""
    src = TP.PEX[pex].read_text()
    hdr = '.subckt vco_top VDD VDD_LS VSS vctrl bit0 bit1 bit2 bit3 bit4 bitb0 bitb1 bitb2 bitb3 bitb4 ck a0 vbn vg ls'
    assert src.count(hdr + '\n') == 1, 'vco_top header changed'
    return TP.PEX[pex]


def deck(pex, corner, case, temp=27, vdd=3.3, tstop=1.2e-6, rsup=1.0, lsup=1e-9):
    v0 = TP.VBN0[corner]
    en = 0 if case == 'off' else vdd
    if case == 'shared':
        sup = (f'vsrc vsrc 0 {vdd}\nRsup vsrc vs1 {rsup}\nLsup vs1 vgrid {lsup}\n'
               'vdd_s vdd vgrid 0\nvls_s vls vgrid 0\nvtx_s vtx vgrid 0\n')     # same current sign as a 3.3 V source
    else:
        sup = (f'vdd_s vdd 0 {vdd}\nvls_s vls 0 {vdd}\n'
               f'vtx_s vtxs 0 {vdd}\nRsup vtxs vt1 {rsup}\nLsup vt1 vtx {lsup}\n')
    bits = ''.join(f'vbit{i} bit{i} 0 {vdd if (CODE >> i) & 1 else 0}\nvbitb{i} bitb{i} 0 {0 if (CODE >> i) & 1 else vdd}\n'
                   for i in range(5))
    return f"""* tb_tx_top {pex} {corner} {case} {temp} C VDD {vdd}: code {CODE} vctrl {VCTRL}
.include {PDK}/design.ngspice
.lib {PDK}/sm141064.ngspice {corner}
.lib {PDK}/sm141064.ngspice res_typical
.lib {PDK}/sm141064.ngspice diode_typical
.include {LD.STD}
.include {REPO}/sim/pad/tt_asw_5v0.spice
.include {REPO}/sim/pad/pad_model_gf180.spice
.include {topx(pex)}
{tx_drv.block()}
{sup}vff vff 0 {vdd}
vctrl vctrl 0 {VCTRL}
{bits}Xtop vdd vls 0 vctrl {' '.join(f'bit{i}' for i in range(5))} {' '.join(f'bitb{i}' for i in range(5))} ck a0 vbn vg ls vco_top
Cwire ck 0 20f
XFF 0 ck ffq vff vff 0 0 gf180mcu_fd_sc_mcu7t5v0__dffq_1
Ven en 0 {en}
xdrv vtx 0 ls en en out_p out_n tx_drv
xpp 0 pin_p out_p pad_model_gf180 rroute=40 n_off=3 vsup={vdd}
xpn 0 pin_n out_n pad_model_gf180 rroute=40 n_off=3 vsup={vdd}
Rdip pin_p dmid {RDIP}
Cdip dmid pin_n {CDIP}
.ic v(a0)=0 v(vbn)={v0} v(xtop.vbnf)={v0} v(dmid)=0
.control
set num_threads=1
option temp={temp}
save {SAVE}
tran 5p {tstop} {0.6 * tstop} 5p
set filetype=binary
write out.raw {SAVE}
quit
.endc
.end
"""


def cases():
    c = {}
    for corner in ('typical', 'ss', 'ff'):
        for case in ('off', 'own', 'shared'):
            c[f'c_{corner}_{case}'] = dict(pex='c', corner=corner, case=case)
    c['rcx_typical_own'] = dict(pex='rcx', corner='typical', case='own')
    for temp in (0, 70):
        c[f'c_typical_own_T{temp}'] = dict(pex='c', corner='typical', case='own', temp=temp)
    for vdd in (3.15, 3.45):
        c[f'c_typical_own_V{vdd}'] = dict(pex='c', corner='typical', case='own', vdd=vdd)
    return c


def run1(name, kw, tstop):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / '.spiceinit').write_text('set ng_nomodcheck\nset num_threads=1\noption noinit\n')
    (d / 'deck.cir').write_text(deck(tstop=tstop, **kw))
    (d / 'out.raw').unlink(missing_ok=True)
    t = time.time()
    subprocess.run(['bash', '-c', f'cd {d} && nice -n 10 ngspice -b deck.cir > deck.log 2>&1'], check=False)
    (d / 'runtime.txt').write_text(f'{time.time() - t:.0f}\n')
    (d / 'case.json').write_text(json.dumps(kw))
    return name, time.time() - t


def periods(t, y, th):
    """Rising mid-swing crossing times (linear interpolation)."""
    s = np.where((y[:-1] < th) & (y[1:] >= th))[0]
    return s, t[s] + (th - y[s]) / (y[s + 1] - y[s]) * (t[s + 1] - t[s])


def fund(t, y, f, t0, t1):
    """Amplitude of the f component of y over [t0, t1] (whole periods), by a DFT on a uniform grid."""
    n = int((t1 - t0) * f)
    t1 = t0 + n / f
    tu = np.linspace(t0, t1, n * 400, endpoint=False)
    yu = np.interp(tu, t, y)
    c = 2 * np.mean(yu * np.exp(-2j * np.pi * f * tu))
    return abs(c), np.angle(c, deg=True)


def analyse(name):
    d = OUT / name
    log = (d / 'deck.log').read_text(errors='replace') if (d / 'deck.log').exists() else ''
    flags = [w for w in ('singular', 'timestep too small', 'Transient op started', 'error') if w.lower() in log.lower()]
    kw = json.loads((d / 'case.json').read_text()) if (d / 'case.json').exists() else {}
    try:
        pl = read_raw(d / 'out.raw')[0]['vars']
    except Exception as e:  # noqa: BLE001
        return dict(name=name, error=str(e), flags=flags, **kw)
    t = pl['time']
    vdd = kw.get('vdd', 3.3)
    a0 = pl['v(a0)']
    th = (a0.min() + a0.max()) / 2
    _, tc = periods(t, a0, th)
    per = np.diff(tc)
    fa = 1 / per.mean()
    fc, _ = LD.freq(t, pl['v(ck)'], vdd / 2)
    r = dict(name=name, **kw, flags=flags, f_a0=fa, jit_rms_ps=float(per.std() * 1e12),
             per_pp_ps=float((per.max() - per.min()) * 1e12), div_ratio=fa / fc,
             ls_duty=LD.duty(t, pl['v(ls)'], vdd / 2),
             vdd_ripple_mv=float(np.ptp(pl['v(vdd)']) * 1e3), vtx_ripple_mv=float(np.ptp(pl['v(vtx)']) * 1e3),
             i_tx_avg_ma=float(-TP.mean(t, pl['i(vtx_s)']) * 1e3),
             i_tx_rms_ma=float(np.sqrt(TP.mean(t, pl['i(vtx_s)'] ** 2)) * 1e3),
             p_vdd_mw=float(-TP.mean(t, pl['i(vdd_s)']) * vdd * 1e3), p_vls_mw=float(-TP.mean(t, pl['i(vls_s)']) * vdd * 1e3),
             runtime_s=float((d / 'runtime.txt').read_text()) if (d / 'runtime.txt').exists() else None)
    vr = pl['v(pin_p)'] - pl['v(dmid)']
    r['p_dip_dbm'] = float(10 * np.log10(max(TP.mean(t, vr ** 2) / RDIP, 1e-18) / 1e-3))
    t0 = tc[0]
    a1, _ = fund(t, vr, fa, t0, t[-1])
    r['p1_dbm'] = float(10 * np.log10(max(a1 ** 2 / (2 * RDIP), 1e-18) / 1e-3))
    if kw.get('case') != 'off':
        op, on = pl['v(out_p)'], pl['v(out_n)']
        _, ph_p = fund(t, op, fa, t0, t[-1])
        _, ph_n = fund(t, on, fa, t0, t[-1])
        r['ph_err_deg'] = float((ph_p - ph_n) % 360 - 180)
        r['duty_p'] = LD.duty(t, op, (op.min() + op.max()) / 2)
        r['duty_n'] = LD.duty(t, on, (on.min() + on.max()) / 2)
        r['out_lo'], r['out_hi'] = float(op.min()), float(op.max())
    else:
        r['out_max'] = float(max(pl['v(out_p)'].max(), pl['v(out_n)'].max()))
    return r


def summary():
    rs = [analyse(d.name) for d in sorted(OUT.iterdir()) if d.is_dir()]
    RES.mkdir(exist_ok=True)
    (RES / 'top.json').write_text(json.dumps(rs, indent=1))
    cn = dict(typical='tt', ss='ss', ff='ff')
    ref = {k: TP.REFS['core_ls'][k] for k in ('typical', 'ss', 'ff')}
    ref_d = TP.REFS['core_ls_duty']
    L = ['# TX driver on the extracted vco_top: results', '',
         f'Generated by `python3 sim/tx/tb_tx_top.py summary` from `build/tx_top/`. Code {CODE}, vctrl {VCTRL} V, '
         'rroute 40 ohm, n_off 3, dipole 73 ohm + 100 pF, VDD_TX via 1 ohm + 1 nH (assumed). Reference without '
         'the driver: extracted core (rcx) + extracted LS (`sim/top/top_pex.py`, `sim/lsdiv/results/remap.csv`). '
         'Measured over the last 40 % of 1.2 us.', '',
         '| run | f(a0) (MHz) | vs no driver | jitter rms / p-p (ps) | f/f(ck) | LS duty (no driver) | P_dip / fund (dBm) '
         '| out duty p / n | phase err (deg) | I(VDD_TX) avg / rms (mA) | ripple VDD / VDD_TX (mV) | P(VDD) / P(VDD_LS) (mW) | flags |',
         '|' + '---|' * 13]
    for r in rs:
        if 'error' in r:
            L.append(f"| {r['name']} | error: {r['error']} |" + ' |' * 11 + f" {r['flags']} |")
            continue
        c = r.get('corner', 'typical')
        dv = (r['f_a0'] / ref[c] - 1) * 100 if c in ref else float('nan')
        od = (f"{r['duty_p'] * 100:.1f} / {r['duty_n'] * 100:.1f} %" if 'duty_p' in r else f"off (max {r['out_max']:.3f} V)")
        L.append(f"| {r['name']} | {r['f_a0'] / 1e6:.2f} | {dv:+.2f} % | {r['jit_rms_ps']:.2f} / {r['per_pp_ps']:.1f} | "
                 f"{r['div_ratio']:.4f} | {r['ls_duty'] * 100:.1f} % ({ref_d.get(c, float('nan')) * 100:.1f} %) | "
                 f"{r['p_dip_dbm']:+.2f} / {r['p1_dbm']:+.2f} | {od} | {r.get('ph_err_deg', float('nan')):+.2f} | "
                 f"{r['i_tx_avg_ma']:.2f} / {r['i_tx_rms_ma']:.2f} | {r['vdd_ripple_mv']:.1f} / {r['vtx_ripple_mv']:.0f} | "
                 f"{r['p_vdd_mw']:.3f} / {r['p_vls_mw']:.3f} | {', '.join(r['flags']) or 'none'} |")
    (RES / 'top.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('what', choices=['run', 'summary'])
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--only', default='')
    ap.add_argument('--tstop', type=float, default=1.2e-6)
    a = ap.parse_args()
    if a.what == 'summary':
        summary()
        return
    cs = cases()
    if a.only:
        cs = {k: v for k, v in cs.items() if k in a.only.split(',')}
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        for name, dt in ex.map(lambda kv: run1(kv[0], kv[1], a.tstop), cs.items()):
            print(f'{name}: {dt:.0f} s', flush=True)
            print(json.dumps(analyse(name)), flush=True)


if __name__ == '__main__':
    main()
