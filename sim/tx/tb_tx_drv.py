#!/usr/bin/env python3
"""
Block testbench for the dipole TX driver (sim/tx/tx_drv.py), ported from ook-asic-radio sim/tx/tb_tx_drv.py.

  ideal 433.92 MHz square on ls (0-3.3 V, --edge ps) -> tx_drv (splitter + both arms, en_p = en_n = 1)
  -> pad_model_gf180 per arm (rroute, n_off) -> dipole: 73 ohm + 100 pF between the two board pins.
  VDD (the driver's own supply, VDPWR) comes from an ideal 3.3 V source through Rsup + Lsup (assumed 1 ohm + 1 nH:
  the TT power grid and bond wire are not modelled), so the on-chip decap's ripple suppression is visible.

Measures over NPER periods after TSET: P into the dipole (total and the fundamental, from a Fourier fit), out_p
20-80 % rise/fall (of the actual swing), out_p / out_n duty at mid-swing, the antiphase error (out_p rise vs out_n
fall, at mid-swing) and the splitter skew (a vs b at VDD/2), ls -> out_p delay, I(VDD) avg / rms / peak, the VDD
ripple (peak-peak on chip), the harmonics H2-H7 of the dipole voltage vr in dBc (h2_dbc ... h7_dbc, ngspice
fourier over the last period, 1000-point grid), the pin current rms (the dipole current, sqrt(P / 73 ohm)), the
efficiency P_dip / (VDD x I_avg), and for EM sizing the rms / |avg| / peak currents in arm p's stage 4 and 5 drains and
sources. --off: both enables low (outputs must sit low, no DC through the dipole).

    python3 sim/tx/tb_tx_drv.py [corners...] [--set K=V ...] [--rroute 40] [--noff 3] [--off] [--jobs 8]
    python3 sim/tx/tb_tx_drv.py tt --sweep wn5=10,20,40,60,80        # one run per value
Outputs: build/tx/<tag>.cir/.log, build/tx/results.jsonl (one line per run).
Runs under nice -n 10, one thread per ngspice (the machine is shared).
"""
import argparse
import itertools
import json
import math
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import tx_drv  # noqa: E402

OUT = REPO / 'build' / 'tx'
PDK = os.environ.get('PDK_ROOT', '/foss/pdks') + '/gf180mcuD/libs.tech/ngspice'
CORNERS = {'tt': 'typical', 'ss': 'ss', 'ff': 'ff', 'sf': 'sf', 'fs': 'fs'}
F = 433.92e6
T = 1 / F
TSET, NPER = 40e-9, 8           # the dipole's series C starts near 0 V (.ic) and settles in the rest
RDIP, CDIP = 73.0, 100e-12


def probe(netlist):
    """0 V ammeters on stage 4 / 5 drains and sources inside tx_arm (named vd5p, vs5p, ...)."""
    out, inarm = [], False
    for ln in netlist.splitlines():
        t = ln.split()
        if t and t[0] == '.subckt':
            inarm = t[1] == 'tx_arm'
        if inarm and t and t[0] in ('XM5p', 'XM5n', 'XM4p', 'XM4n'):
            st, k = t[0][2], t[0][3]
            d, s = t[1], t[3]
            t[1], t[3] = f'd{st}{k}', f's{st}{k}'
            out += [' '.join(t), f'Vd{st}{k} d{st}{k} {d} 0', f'Vs{st}{k} {s} s{st}{k} 0']
            continue
        out.append(ln)
    return '\n'.join(out) + '\n'


def deck(corner, sizes, rroute, noff, off, edge, rsup, lsup, temp=27, vdd=3.3, pex=None):
    hp = T / 2
    en = 0 if off else vdd
    if pex:     # the extracted layout (layout/pex/tx_drv_<c|rcx>.spice): no EM probes, the a / b nodes keep their names
        sub = f'.include {REPO}/layout/pex/tx_drv_{pex}.spice\n'
        assert not sizes, '--set has no effect on the extracted layout'
    else:
        sub = probe(tx_drv.block(sizes))
    probes = [] if pex else [f'v.xdut.xap.v{a}{st}{k}' for st in '45' for k in 'pn' for a in 'ds']
    em = ''
    for st in ('' if pex else '45'):
        for k in 'pn':
            for a in 'ds':
                v = f'{a}{st}{k}'
                em += (f'let j{v} = i(v.xdut.xap.v{v})\nlet a{v} = abs(j{v})\n'
                       f'meas tran rms_{v} rms j{v} from=$&t0 to=$&t1\n'
                       f'meas tran avg_{v} avg a{v} from=$&t0 to=$&t1\n'
                       f'meas tran pk_{v} max a{v} from=$&t0 to=$&t1\n')
    return f"""* tb_tx_drv {corner} rroute={rroute} n_off={noff} {'OFF' if off else 'on'}
.include {PDK}/design.ngspice
.lib {PDK}/sm141064.ngspice {CORNERS[corner]}
.lib {PDK}/sm141064.ngspice diode_typical
.include {REPO}/sim/pad/tt_asw_5v0.spice
.include {REPO}/sim/pad/pad_model_gf180.spice
.temp {temp}
{sub}
Vsup vsup 0 {vdd}
Rsup vsup vs1 {rsup}
Lsup vs1 VDD {lsup}
Vls ls 0 pulse(0 {vdd} 0 {edge:.4e} {edge:.4e} {hp - edge:.4e} {T:.4e})
Ven en 0 {en}
xdut VDD 0 ls en en out_p out_n tx_drv
xpp 0 pin_p out_p pad_model_gf180 rroute={rroute} n_off={noff} vsup={vdd}
xpn 0 pin_n out_n pad_model_gf180 rroute={rroute} n_off={noff} vsup={vdd}
Rdip pin_p dmid {RDIP}
Cdip dmid pin_n {CDIP}
* start the dipole C near its steady state (about 0 V): at the DC op out_p is high and out_n low (vc 3.2 V, tau ~45 ns)
.ic v(dmid)=0
.options method=gear
.control
set num_threads=1
save v(ls) v(out_p) v(out_n) v(pin_p) v(pin_n) v(dmid) v(VDD) i(Vsup) v(xdut.a) v(xdut.b) {' '.join(f'i({p})' for p in probes)}
tran 2p {TSET + NPER * T:.4e} 0
let t0 = {TSET:.4e}
let t1 = {TSET + NPER * T:.4e}
let vr = v(pin_p) - v(dmid)
let vc = v(dmid) - v(pin_n)
let tm = {TSET + NPER / 2 * T:.4e}
meas tran vc_a avg vc from=$&t0 to=$&tm
meas tran vc_b avg vc from=$&tm to=$&t1
let pr = vr * vr / {RDIP}
meas tran p_dip avg pr from=$&t0 to=$&t1
let isup = -i(Vsup)
let iabs = abs(isup)
meas tran i_avg avg isup from=$&t0 to=$&t1
meas tran i_rms rms isup from=$&t0 to=$&t1
meas tran i_pk max iabs from=$&t0 to=$&t1
meas tran vdd_max max v(VDD) from=$&t0 to=$&t1
meas tran vdd_min min v(VDD) from=$&t0 to=$&t1
meas tran vhi max v(out_p) from=$&t0 to=$&t1
meas tran vlo min v(out_p) from=$&t0 to=$&t1
meas tran vnhi max v(out_n) from=$&t0 to=$&t1
meas tran vnlo min v(out_n) from=$&t0 to=$&t1
meas tran vpin_hi max v(pin_p) from=$&t0 to=$&t1
meas tran vpin_lo min v(pin_p) from=$&t0 to=$&t1
let v20 = vlo + 0.2 * (vhi - vlo)
let v80 = vlo + 0.8 * (vhi - vlo)
let vm = (vhi + vlo) / 2
let vnm = (vnhi + vnlo) / 2
let vh = {vdd / 2}
meas tran tpr WHEN v(out_p)=$&vm TD=$&t0 RISE=1
meas tran tpf WHEN v(out_p)=$&vm TD=$&tpr FALL=1
meas tran tpr2 WHEN v(out_p)=$&vm TD=$&t0 RISE=2
* rise / fall timed from just after a mid-swing crossing of the opposite edge, so a full edge follows
meas tran tr TRIG v(out_p) VAL=$&v20 TD=$&tpf RISE=1 TARG v(out_p) VAL=$&v80 TD=$&tpf RISE=1
meas tran tf TRIG v(out_p) VAL=$&v80 TD=$&tpr FALL=1 TARG v(out_p) VAL=$&v20 TD=$&tpr FALL=1
meas tran tnf WHEN v(out_n)=$&vnm TD=$&t0 FALL=1
meas tran tnr WHEN v(out_n)=$&vnm TD=$&tnf RISE=1
meas tran tnf2 WHEN v(out_n)=$&vnm TD=$&t0 FALL=2
meas tran tar WHEN v(xdut.a)=$&vh TD=$&t0 RISE=1
meas tran tbf WHEN v(xdut.b)=$&vh TD=$&t0 FALL=1
meas tran taf WHEN v(xdut.a)=$&vh TD=$&t0 FALL=1
meas tran tbr WHEN v(xdut.b)=$&vh TD=$&t0 RISE=1
meas tran tdl TRIG v(ls) VAL=$&vh TD=$&t0 FALL=1 TARG v(out_p) VAL=$&vm TD=$&t0 RISE=1
{em}let op = v(out_p)
let on = v(out_n)
linearize vr op on
set fourgridsize=1000
fourier {F} vr op on
echo RESULTS_END
.endc
.end
"""


NUM = r'([-+]?\d[\d.]*(?:[eE][-+]?\d+)?)'


def parse(log, off, vdd=3.3):
    r = {k: float(v) for k, v in re.findall(r'^(\w+)\s+=\s+' + NUM, log, re.M)}
    h1 = re.findall(r'^\s*1\s+[\d.eE+-]+\s+' + NUM + r'\s+' + NUM, log, re.M)   # Fourier harmonic 1: mag, phase
    if len(h1) >= 3:                                                                   # vr, out_p, out_n
        r['v1'] = float(h1[0][0])
        r['ph_err'] = (float(h1[1][1]) - float(h1[2][1])) % 360 - 180             # out_p vs out_n, minus 180 deg
    out = {}
    m = re.search(r'Fourier analysis for vr:(.*?)(?:Fourier analysis for|\Z)', log, re.S)
    if m:
        hv = {int(n): float(v) for n, v in re.findall(r'^\s*(\d+)\s+[\d.eE+-]+\s+' + NUM, m.group(1), re.M)}
        if hv.get(1):
            for n in range(2, 8):
                if n in hv:
                    out[f'h{n}_dbc'] = 20 * math.log10(max(abs(hv[n]), 1e-12) / hv[1])
    if 'p_dip' not in r:
        return None
    out['p_dip_dbm'] = 10 * math.log10(max(r['p_dip'], 1e-15) / 1e-3)
    if 'v1' in r:
        out['p1_dbm'] = 10 * math.log10(r['v1'] ** 2 / (2 * RDIP) / 1e-3)
    out.update(i_avg_ma=r['i_avg'] * 1e3, i_rms_ma=r['i_rms'] * 1e3, i_pk_ma=r['i_pk'] * 1e3,
               vdd_ripple_mv=(r['vdd_max'] - r['vdd_min']) * 1e3, vdd_min=r['vdd_min'],
               vcap_drift_mv=(r['vc_b'] - r['vc_a']) * 1e3,
               i_pin_ma=math.sqrt(max(r['p_dip'], 0) / RDIP) * 1e3,
               eff_pct=r['p_dip'] / max(vdd * r['i_avg'], 1e-15) * 100,
               out_hi=r['vhi'], out_lo=r['vlo'], pin_hi=r['vpin_hi'], pin_lo=r['vpin_lo'])
    if not off and 'tpr2' in r:
        out.update(tr_ps=r['tr'] * 1e12, tf_ps=r['tf'] * 1e12,
                   duty_p=(r['tpf'] - r['tpr']) / (r['tpr2'] - r['tpr']) * 100,
                   duty_n=(r['tnr'] - r['tnf']) / (r['tnf2'] - r['tnf']) * 100,
                   skew_out_ps=(r['tpr'] - r['tnf']) * 1e12,
                   skew_ab_r_ps=(r['tar'] - r['tbf']) * 1e12, skew_ab_f_ps=(r['taf'] - r['tbr']) * 1e12,
                   delay_ps=r['tdl'] * 1e12, ph_err_deg=r.get('ph_err', float('nan')))
        for st in '45':
            for k in 'pn':
                for a in 'ds':
                    v = f'{a}{st}{k}'
                    if f'rms_{v}' in r:
                        out[f'em_{v}'] = [round(r[f'rms_{v}'] * 1e3, 3), round(r[f'avg_{v}'] * 1e3, 3),
                                          round(r[f'pk_{v}'] * 1e3, 2)]
    return out


def run(job):
    corner, sizes, kw = job
    tag = '_'.join([corner] + ([f'pex{kw["pex"]}'] if kw.get('pex') else []) + [f'{k}{v:g}' for k, v in sorted(sizes.items())]
                   + [f'r{kw["rroute"]:g}', f'n{kw["noff"]:g}', 'off' if kw['off'] else 'on']
                   + ([f't{kw["temp"]:g}'] if kw.get('temp', 27) != 27 else [])
                   + ([f'v{kw["vdd"]:g}'] if kw.get('vdd', 3.3) != 3.3 else []))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / '.spiceinit').write_text('set ng_nomodcheck\nset num_threads=1\noption noinit\n')
    cir = OUT / f'{tag}.cir'
    cir.write_text(deck(corner, sizes, **kw))
    p = subprocess.run(['nice', '-n', '10', 'ngspice', '-b', cir.name], cwd=OUT, capture_output=True, text=True)
    log = p.stdout + p.stderr
    (OUT / f'{tag}.log').write_text(log)
    bad = [s for s in ('singular', 'Transient op started', 'timestep too small') if s in log]
    res = parse(log, kw['off'], kw.get('vdd', 3.3))
    if res and abs(res['vcap_drift_mv']) > 20:
        bad.append(f"not settled: dipole C drifts {res['vcap_drift_mv']:.0f} mV over the window")
    rec = dict(tag=tag, corner=corner, sizes=sizes, **kw, ok=res is not None and not bad, warn=bad, res=res)
    with open(OUT / 'results.jsonl', 'a') as fh:
        fh.write(json.dumps(rec) + '\n')
    return rec


def line(rec):
    r = rec['res']
    if not r:
        return f"{rec['tag']}: NO RESULT {rec['warn']} (build/tx/{rec['tag']}.log)"
    s = (f"{rec['tag']:<40} P_dip {r['p_dip_dbm']:+6.2f} dBm (fund {r.get('p1_dbm', float('nan')):+6.2f})  "
         f"I avg/rms/pk {r['i_avg_ma']:6.2f}/{r['i_rms_ma']:6.2f}/{r['i_pk_ma']:6.1f} mA  VDD ripple {r['vdd_ripple_mv']:5.0f} mV")
    if 'tr_ps' in r:
        s += (f"  tr/tf {r['tr_ps']:4.0f}/{r['tf_ps']:4.0f} ps  duty {r['duty_p']:4.1f}/{r['duty_n']:4.1f} %  "
              f"phase err {r['ph_err_deg']:+5.2f} deg  skew out {r['skew_out_ps']:+5.1f} ab {r['skew_ab_r_ps']:+5.1f}/{r['skew_ab_f_ps']:+5.1f} ps  "
              f"delay {r['delay_ps']:4.0f} ps  out {r['out_lo']:.2f}..{r['out_hi']:.2f} V")
    else:
        s += f"  out_p {r['out_lo']:.3f}..{r['out_hi']:.3f} V  pin_p {r['pin_lo']:.3f}..{r['pin_hi']:.3f} V"
    if 'h3_dbc' in r:
        s += '  H2-7 ' + '/'.join(f"{r.get(f'h{n}_dbc', float('nan')):.1f}" for n in range(2, 8)) + ' dBc'
        s += f"  Ipin {r['i_pin_ma']:.2f} mA rms  eff {r['eff_pct']:.1f} %"
    if rec['warn']:
        s += f'  WARN {rec["warn"]}'
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('corners', nargs='*', default=['tt'])
    ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--sweep', action='append', default=[], help='K=v1,v2,...')
    ap.add_argument('--rroute', default='40')
    ap.add_argument('--noff', default='3')
    ap.add_argument('--off', action='store_true')
    ap.add_argument('--edge', type=float, default=100e-12)
    ap.add_argument('--rsup', type=float, default=1.0)
    ap.add_argument('--lsup', type=float, default=1e-9)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--temp', type=float, default=27)
    ap.add_argument('--vdd', type=float, default=3.3)
    ap.add_argument('--outdir', help='results / decks directory (default build/tx)')
    ap.add_argument('--em', action='store_true', help='print the stage 4/5 EM currents')
    ap.add_argument('--pex', choices=['c', 'rcx'], help='the extracted layout instead of block()')
    a = ap.parse_args()
    global OUT
    if a.outdir:
        OUT = Path(a.outdir).resolve()
    base = {k: float(v) for k, v in (kv.split('=') for kv in a.set)}
    sweeps = [[(k, float(v)) for v in vs.split(',')] for k, vs in (s.split('=') for s in a.sweep)]
    jobs = []
    for c in a.corners:
        for combo in itertools.product(*sweeps) if sweeps else [()]:
            for rr in a.rroute.split(','):
                for no in a.noff.split(','):
                    jobs.append((c, dict(base, **dict(combo)),
                                 dict(rroute=float(rr), noff=float(no), off=a.off, edge=a.edge, rsup=a.rsup,
                                      lsup=a.lsup, pex=a.pex, temp=a.temp, vdd=a.vdd)))
    with ThreadPoolExecutor(a.jobs) as ex:
        for rec in ex.map(run, jobs):
            print(line(rec), flush=True)
            if a.em and rec['res']:
                print('   EM (rms, |avg|, pk mA): ' + '  '.join(f'{k[3:]} {v}' for k, v in rec['res'].items()
                                                              if k.startswith('em_')))


if __name__ == '__main__':
    main()
