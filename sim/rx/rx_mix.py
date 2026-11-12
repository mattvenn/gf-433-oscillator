#!/usr/bin/env python3
"""
Receiver mixer (option B): passive, double-balanced, voltage-mode. One instance per arm (I, Q).

  rfp/rfn: the LNA outputs (DC ~2.1 V: the LNA's load drop), shared by the I and Q mixers
  S1 rfp->bbp (lo)   S2 rfn->bbn (lo)   S3 rfn->bbp (lob)   S4 rfp->bbn (lob)
  each switch a transmission gate (NMOS gate on its phase, PMOS gate on the other phase): the RF node sits at about
  2.1 V, where an NMOS alone has little overdrive.
  Cbb per side (nfet gate cap to VSS, the BB node is at the RF DC, well into inversion) removes the LO and, through
  the switches, makes the mixer an N-path filter at the LNA output: in band (fLO +- 150 kHz) it is high-Z, so the
  LNA's voltage gain holds; far away the caps shunt the LNA output.

No DC flows through the switches (the baseband is AC-coupled after Cbb), so there is no switch flicker noise.

    python3 sim/rx/rx_mix.py           # print the netlist
    python3 sim/rx/rx_mix.py bench ... # phase A3 (see bench())
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

S = dict(wn=8.0, wp=16.0, cbb=0.5e-12, cbbl=5.0)


def block(s=None):
    s = dict(S, **(s or {}))
    out = '.subckt rx_mix VDD VSS rfp rfn bbp bbn lo lob\n'
    for nm, a, b, on, off in (('S1', 'rfp', 'bbp', 'lo', 'lob'), ('S2', 'rfn', 'bbn', 'lo', 'lob'),
                              ('S3', 'rfn', 'bbp', 'lob', 'lo'), ('S4', 'rfp', 'bbn', 'lob', 'lo')):
        out += rxc.nfet(f'{nm}n', b, on, a, s['wn']) + rxc.pfet(f'{nm}p', b, off, a, s['wp'])
    out += rxc.scap('Cbp', 'bbp', s['cbb'], s['cbbl']) + rxc.scap('Cbn', 'bbn', s['cbb'], s['cbbl'])
    return out + '.ends\n'


# ---- phase A3 bench: dipole -> pads -> rx_lna -> I and Q mixers, ideal LO squares ------------------------------
FLO = 433.92e6


def dbm_emf(p_dbm, r=73.0):
    """EMF amplitude (V peak) of a source of available power p_dbm and resistance r."""
    return float(np.sqrt(2 * 4 * r * 1e-3 * 10 ** (p_dbm / 10)))


def lo_src(name, node, vdd, delay_deg, tr=50e-12, duty=0.5):
    T = 1 / FLO
    td = (delay_deg % 360) / 360 * T
    return f'V{name} {node} 0 pulse(0 {vdd} {td:.5e} {tr} {tr} {duty * T - tr:.5e} {T:.5e})\n'


def bench_deck(corner, case, s=None, fif=2e6, pin_dbm=-50, tstop=3e-6, dphi=72.0, noff=3, lo='ideal', extra='', lna=None):
    """case: iq (both mixers), i (I mixer only), dc (no RF: LO feedthrough / offset)."""
    import rx_lna
    import rx_bias
    s = dict(S, **(s or {}))
    amp = 0 if case == 'dc' else dbm_emf(pin_dbm)
    vdd = rxc.VDD
    if lo == 'ideal':
        los = (lo_src('loi', 'lo_i', vdd, 0) + lo_src('lobi', 'lob_i', vdd, 180)
               + lo_src('loq', 'lo_q', vdd, dphi) + lo_src('lobq', 'lob_q', vdd, 180 + dphi))
    else:       # 'buf': ideal level-shifter outputs (ls, lsq: 50 ps edges, dphi apart) -> the rx_lobuf buffers
        import rx_lo
        los = (rx_lo.lobuf() + lo_src('ls', 'ls', vdd, 0) + lo_src('lsq', 'lsq', vdd, dphi)
               + 'xbi VDD VSS ls en lo_i lob_i rx_lobuf\nxbq VDD VSS lsq en lo_q lob_q rx_lobuf\n')
    mixq = 'Xmq VDD VSS rqp rqn bqp bqn lo_q lob_q rx_mix\n' if case != 'i' else ''
    return f"""* rx_mix bench {corner} {case} fif {fif} pin {pin_dbm} dBm
{rxc.hdr(corner, pad=True)}{rx_bias.block()}{rx_lna.block(lna)}{block(s)}
VDD VDD 0 {vdd}
VSS VSS 0 0
Ven en 0 {vdd}
vsig dp dn dc 0 sin(0 {amp} {FLO + fif})
Rsp dp pinp 36.5
Rsn dn pinn 36.5
Rdc dn 0 1e9
Xpp 0 pinp inp pad_model_gf180 rroute=40 n_off={noff}
Xpn 0 pinn inn pad_model_gf180 rroute=40 n_off={noff}
Xb VDD VSS en enb nb rx_bias
Xl VDD VSS inp inn rfp rfn rqp rqn nb enb rx_lna
{los}Xmi VDD VSS rfp rfn bip bin lo_i lob_i rx_mix
{mixq}{extra}.control
option temp=27
save v(bip) v(bin) v(bqp) v(bqn) v(rfp) v(rfn) v(rqp) v(rqn) v(dp) v(pinp) v(pinn) v(inp) v(inn)
tran 10p {tstop} 0 10p
set filetype=binary
write out.raw
quit
.endc
.end
"""


def dft(t, v, f, t0):
    """Complex amplitude at f over [t0, t_end] trimmed to whole periods of f (uniform resampling)."""
    T = 1 / f
    n = int((t[-1] - t0) / T)
    t1 = t0 + n * T
    tu = np.linspace(t0, t1, max(2000, int(n * T / 2e-12)), endpoint=False)
    vu = np.interp(tu, t, v)
    return 2 * np.mean(vu * np.exp(-2j * np.pi * f * tu))


def analyse(d, case, fif, pin_dbm, tskip=1e-6):
    pl = rxc.read_raw(d / 'out.raw')[0]['vars']
    t = pl['time']
    bi = pl['v(bip)'] - pl['v(bin)']
    r = {}
    emf = dbm_emf(pin_dbm)
    if case != 'dc':
        ci = dft(t, bi, fif, tskip)
        r['gain_i_db'] = float(rxc.db(ci / emf))
        rf = pl['v(rfp)'] - pl['v(rfn)']
        r['lna_db'] = float(rxc.db(dft(t, rf, FLO + fif, tskip) / emf))
        if 'v(bqp)' in pl and np.ptp(pl['v(bqp)']) > 0:
            cq = dft(t, pl['v(bqp)'] - pl['v(bqn)'], fif, tskip)
            r['gain_q_db'] = float(rxc.db(cq / emf))
            r['iq_phase'] = float((np.angle(cq / ci, deg=True)))
    m = t > tskip
    r['bb_dc_i'] = float(np.mean(bi[m]))
    r['bb_cm'] = float(np.mean((pl['v(bip)'] + pl['v(bin)'])[m]) / 2)
    r['lo_bb_i_dbv'] = float(rxc.db(dft(t, bi, FLO, tskip)))          # LO at the baseband (diff)
    r['lo_bb_i_cm_dbv'] = float(rxc.db(dft(t, (pl['v(bip)'] + pl['v(bin)']) / 2, 2 * FLO, tskip)))
    i_ant = (pl['v(dp)'] - pl['v(pinp)']) / 36.5
    r['lo_ant_dbm'] = float(10 * np.log10(abs(dft(t, i_ant, FLO, tskip)) ** 2 * 73 / 2 / 1e-3 + 1e-30))
    r['lo_rf_dbv'] = float(rxc.db(dft(t, pl['v(rfp)'] - pl['v(rfn)'], FLO, tskip)))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', nargs='?', default='print')
    ap.add_argument('--corners', default='typical')
    ap.add_argument('--cases', default='iq,i,dc')
    ap.add_argument('--fif', type=float, default=2e6)
    ap.add_argument('--pin', type=float, default=-50)
    ap.add_argument('--tstop', type=float, default=3e-6)
    ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--tag', default='mix')
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--lo', default='ideal')
    a = ap.parse_args()
    s = dict(S)
    import rx_lna
    lna = dict(rx_lna.S)
    for kv in a.set:
        k, v = kv.split('=')
        if k.startswith('lna.'):
            lna[k[4:]] = float(v)
        else:
            s[k] = float(v)
    if a.mode == 'print':
        print(block(s), end='')
        return
    jobs = [(c, k) for c in a.corners.split(',') for k in a.cases.split(',')]
    t0 = time.time()

    def one(j):
        c, k = j
        d, log, bad = rxc.run(f'{rxc.CN[c]}_{k}_{a.lo}', bench_deck(c, k, s, a.fif, a.pin, a.tstop, lna=lna, lo=a.lo), sub=a.tag)
        try:
            r = analyse(d, k, a.fif, a.pin)
        except Exception as e:  # noqa: BLE001
            r = dict(error=str(e), log=log.splitlines()[-5:])
        r.update(corner=rxc.CN[c], case=k, bad=bad)
        print(json.dumps({kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in r.items()}), flush=True)
        return r
    rows = rxc.pmap(one, jobs, a.jobs)
    (rxc.BUILD / a.tag / 'rows.json').write_text(json.dumps(dict(S=s, fif=a.fif, pin=a.pin, rows=rows), indent=1))
    print(f'{time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
