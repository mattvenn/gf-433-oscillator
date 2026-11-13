#!/usr/bin/env python3
"""
Phase C chain benches: the whole receiver (sim/rx/rx_top.py blocks) behind the pad model, at schematic level.

  fsk    : 2-FSK (+-100 kHz, continuous phase) at 50 kbit/s, NBITS bits, ideal LO squares (72 deg, 50 ps edges) into
           the mixers (rx_lo left out), at a given antenna level; q_i / q_q -> quadrant steps per bit, compared with
           rx_model.steps_b on the same bits (noiseless).
  noise  : the same with the antenna noise of the model's NF as a white trnoise source (all device noise lumped at
           the input: ngspice has no device noise in .tran), at the sensitivity level: comparator chatter.
  cw     : a CW tone (fLO + df) for the P1dB / blocker runs: LNA + mixers + the baseband's stage-1 load, measured at
           the mixer output (see blocker()).
The signal source is a behavioural voltage A sin(2 pi fLO t + phi(t)) with phi(t) a PWL node (exact for CPFSK).

    python3 sim/rx/rx_chain.py fsk --level -95 [--corner typical] [--tstop ...]
    python3 sim/rx/rx_chain.py p1db | blocker
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
import rx_top  # noqa: E402
import rx_mix  # noqa: E402
import rx_model  # noqa: E402

FLO = rx_mix.FLO
RATE, DEV, NPRE = 50e3, 100e3, 1
BITS = np.array([1, 1, 0, 1, 1, 0, 0])           # 1 preamble bit (settling) + 6 data bits


def phase_pwl(bits, rate=RATE, dev=DEV, t0=0.0):
    """CPFSK phase (rad) as PWL points: slope +-2 pi dev per bit."""
    pts = [(0.0, 0.0)]
    ph = 0.0
    T = 1 / rate
    for k, b in enumerate(bits):
        ph += 2 * np.pi * (dev if b else -dev) * T
        pts.append((t0 + (k + 1) * T, ph))
    return ' '.join(f'{t:.9e} {p:.9f}' for t, p in pts)


def front(level_dbm, bits, noise_nf=None, noff=3, tone=None, blocker=None):  # noqa: C901
    """Dipole source (EMF) + pads. tone: (df, dBm) CW instead of FSK; blocker: (df, dBm) added CW."""
    if tone is not None:
        sig = f'{rx_mix.dbm_emf(tone[1])}*sin(2*pi*{FLO + tone[0]}*time)'
        ph = ''
    else:
        sig = f'{rx_mix.dbm_emf(level_dbm)}*sin(2*pi*{FLO}*time+v(ph))'
        ph = f'vph ph 0 pwl({phase_pwl(bits)})\n'
    if blocker is not None:
        sig += f'+{rx_mix.dbm_emf(blocker[1])}*sin(2*pi*{FLO + blocker[0]}*time)'
    nz = ''
    if noise_nf is not None:
        # antenna-referred noise of the whole receiver: 4kT x 73 ohm x F (V^2/Hz EMF), white to 2 GHz
        kt = 1.380649e-23 * 300.15
        vn = np.sqrt(4 * kt * 73 * 10 ** (noise_nf / 10) * 2e9)   # rms over a 2 GHz bandwidth (sampling 0.25 ns)
        nz = f'vnz dn dn2 dc 0 trnoise({vn:.4e} 0.25n 0 0)\n'
    dn = 'dn2' if noise_nf is not None else 'dn'
    return (f'{ph}Bsig dp {dn} V={sig}\n{nz}Rsp dp pinp 36.5\nRsn dn pinn 36.5\nRdc dn 0 1e9\n'
            f'Xpp 0 pinp inp pad_model_gf180 rroute=40 n_off={noff}\nXpn 0 pinn inn pad_model_gf180 rroute=40 n_off={noff}\n')


def chain_body(lo='ideal', dphi=72.0):
    vdd = rxc.VDD
    los = (rx_mix.lo_src('loi', 'lo_i', vdd, 0) + rx_mix.lo_src('lobi', 'lob_i', vdd, 180)
           + rx_mix.lo_src('loq', 'lo_q', vdd, dphi) + rx_mix.lo_src('lobq', 'lob_q', vdd, 180 + dphi))
    return (los + 'xb VDD VSS en enb nb rx_bias\n'
            'xlna VDD VSS inp inn ri_p ri_n rq_p rq_n nb enb rx_lna\n'
            'xmi VDD VSS ri_p ri_n bi_p bi_n lo_i lob_i rx_mix\nxmq VDD VSS rq_p rq_n bq_p bq_n lo_q lob_q rx_mix\n'
            'xbbi VDD VSS bi_p bi_n oi_p oi_n nb enb rx_bb\nxbbq VDD VSS bq_p bq_n oq_p oq_n nb enb rx_bb\n'
            'xli VDD VSS oi_p oi_n q_i nb enb rx_lim\nxlq VDD VSS oq_p oq_n q_q nb enb rx_lim\n')


def fsk_deck(corner, level, tstop, noise_nf=None, maxstep=20e-12, bits=BITS):
    return f"""* rx chain fsk {corner} {level} dBm noise {noise_nf}
{rxc.hdr(corner, pad=True)}{rx_top.block()}
VDD VDD 0 {rxc.VDD}
VSS VSS 0 0
Ven en 0 {rxc.VDD}
{front(level, bits, noise_nf)}{chain_body()}.control
option temp=27
save v(q_i) v(q_q) v(oi_p) v(oi_n) v(oq_p) v(oq_n) v(xli.lp) v(xli.ln) v(xlq.lp) v(xlq.ln) v(xli.gcp) v(xli.gcn) v(xlq.gcp) v(xlq.gcn) i(VDD)
tran {maxstep} {tstop} 0 {maxstep}
set filetype=binary
write out.raw
quit
.endc
.end
"""


def fsk_analyse(d, bits=BITS, fs=8e6):
    pl = rxc.read_raw(d / 'out.raw')[0]['vars']
    t = pl['time']
    tu = np.arange(0, t[-1], 1 / fs)
    qi = np.interp(tu, t, pl['v(q_i)']) > rxc.VDD / 2
    qq = np.interp(tu, t, pl['v(q_q)']) > rxc.VDD / 2
    st = rx_model.steps_b(qi, qq)
    sps = int(round(fs / RATE))
    nb = len(bits) - NPRE
    # the model on the same bits, noiseless, at its own genie delay
    p = dict(rx_model.B_DEF)
    dl = rx_model.delay('B', fs, RATE, p, DEV)
    x, _ = rx_model.rx_input(bits, RATE, fs, -60, None, np.random.default_rng(1), dev=DEV, pn=False)
    ms = rx_model.run_chain('B', x, fs, p)
    best = None
    for off in range(0, sps, max(1, sps // 40)):
        if NPRE * sps + off + nb * sps > len(st):
            break
        c = rx_model.counts(st, sps, nb, NPRE * sps + off)
        agree = int(np.sum((c > 0) == (bits[NPRE:] > 0)))
        score = (max(agree, nb - agree), int(np.min(np.abs(c))))
        if best is None or score > best[0]:
            best = (score, off, c, agree)
    mc = rx_model.counts(ms, sps, nb, NPRE * sps + dl) if NPRE * sps + dl + nb * sps <= len(ms) else None
    _, off, c, agree = best
    sign = 1 if agree >= nb / 2 else -1        # the decoder learns the sign from the preamble
    errs = int(np.sum(((sign * c) > 0) != (bits[NPRE:] > 0)))
    T = t[-1] - t[0]
    m = t > NPRE / RATE
    # glitches: comparator pulses shorter than 1 us (a 100 kHz tone gives 5 us half periods)
    gl = 0
    for k in ('v(q_i)', 'v(q_q)'):
        e = np.sort(np.concatenate([rxc.xings(t[m], pl[k][m], rxc.VDD / 2), rxc.xings(t[m], pl[k][m], rxc.VDD / 2, False)]))
        gl += int(np.sum(np.diff(e) < 1e-6))
    return dict(glitches=gl, counts=[int(x) for x in c], model_counts=[int(x) for x in mc] if mc is not None else None,
                sign=sign, bit_errors=errs, delay_us=off / fs * 1e6,
                edges_i=int(len(rxc.xings(t[m], pl['v(q_i)'][m], rxc.VDD / 2))),
                edges_q=int(len(rxc.xings(t[m], pl['v(q_q)'][m], rxc.VDD / 2))),
                idd_ma=-float(np.trapezoid(pl['i(vdd)'], t)) / T * 1e3)


def cw_deck(corner, tone, blocker, tstop, maxstep=20e-12):
    return f"""* rx chain cw {corner} tone {tone} blocker {blocker}
{rxc.hdr(corner, pad=True)}{rx_top.block()}
VDD VDD 0 {rxc.VDD}
VSS VSS 0 0
Ven en 0 {rxc.VDD}
{front(None, None, tone=tone, blocker=blocker)}{chain_body()}.control
option temp=27
save v(bi_p) v(bi_n) v(oi_p) v(oi_n) v(q_i)
tran {maxstep} {tstop} 0 {maxstep}
set filetype=binary
write out.raw
quit
.endc
.end
"""


def cw_analyse(d, tone, blocker, tskip):
    import rx_mix as M
    pl = rxc.read_raw(d / 'out.raw')[0]['vars']
    t = pl['time']
    bi = pl['v(bi_p)'] - pl['v(bi_n)']
    oi = pl['v(oi_p)'] - pl['v(oi_n)']
    emf = M.dbm_emf(tone[1])
    r = dict(g_mix_db=float(rxc.db(M.dft(t, bi, abs(tone[0]), tskip) / emf)),
             wanted_bb_v=float(abs(M.dft(t, oi, abs(tone[0]), tskip))))
    if blocker is not None:
        r['blocker_bb_v'] = float(abs(M.dft(t, oi, abs(blocker[0]), tskip)))
        r['blocker_mix_v'] = float(abs(M.dft(t, bi, abs(blocker[0]), tskip)))
    return r


def real_lo_deck(tstop, df=100e3, level=-70, corner='typical', code=9, f_lo=None):
    """The ring (extracted core) + extracted lsdiv + the TX splitter as in rx_lo.py's A1 bench, driving the whole
    rx_top (its own rx_lo: I from lsdiv's ls, Q tap copy on a2) behind the pads; a CW tone at the ring's own f
    (f_lo, from A1) + df."""
    import rx_lo
    import lsdiv as LD
    import tx_drv
    p = dict(LD.vb.P, **LD.WINNER, **LD.CFED)
    body, ics = LD.ring(p, 'pex')
    vdd = rxc.VDD
    bits = ''.join(f'vbit{b} bit{b} 0 {vdd if (code >> b) & 1 else 0}\nvbitb{b} bitb{b} 0 {0 if (code >> b) & 1 else vdd}\n'
                   for b in range(5))
    a = rx_mix.dbm_emf(level)
    return f"""* rx chain, real LO (ring + taps) {corner} code {code}
{LD.hdr(corner)}.lib {rxc.PDK}/sm141064.ngspice diode_typical
.include {rxc.PAD}/tt_asw_5v0.spice
.include {rxc.PAD}/pad_model_gf180.spice
vdd vdd 0 {vdd}
vls vls 0 {vdd}
vdv vdv 0 {vdd}
vff vff 0 {vdd}
vctrl vctrl 0 1.65
VSS VSS 0 0
Ven en 0 {vdd}
{bits}{body}{LD.ls_x(LD.S)}{tx_drv.split(tx_drv.S)}Xtxs vls 0 lsout txa txb tx_split
Cpaq a2 0 {LD.S['cpa']}
{rx_top.block()}Bsig dp dn V={a}*sin(2*pi*{f_lo + df}*time)
Rsp dp pinp 36.5
Rsn dn pinn 36.5
Rdc dn 0 1e9
Xpp 0 pinp inp pad_model_gf180 rroute=40 n_off=3
Xpn 0 pinn inn pad_model_gf180 rroute=40 n_off=3
Xrx VDD VSS inp inn lsout a2 en q_i q_q rx_top
.ic {ics}
.control
option temp=27
save v(q_i) v(q_q) v(a0) v(xrx.lo_i) v(xrx.lo_q) v(xrx.oi_p) v(xrx.oi_n) v(xrx.oq_p) v(xrx.oq_n) v(dp) v(pinp)
tran 5p {tstop} 0 5p
set filetype=binary
write out.raw
quit
.endc
.end
"""


def real_lo_analyse(d, df, tskip=5e-6):
    import rx_mix as M
    pl = rxc.read_raw(d / 'out.raw')[0]['vars']
    t = pl['time']
    m = t > tskip
    a0 = pl['v(a0)']
    f = (len(rxc.xings(t[m], a0[m], (a0[m].min() + a0[m].max()) / 2)) - 1) / (t[-1] - tskip)
    oi = pl['v(xrx.oi_p)'] - pl['v(xrx.oi_n)']
    oq = pl['v(xrx.oq_p)'] - pl['v(xrx.oq_n)']
    ci, cq = M.dft(t, oi, df, tskip), M.dft(t, oq, df, tskip)
    ri = rxc.xings(t[m], pl['v(q_i)'][m], rxc.VDD / 2)
    rq = rxc.xings(t[m], pl['v(q_q)'][m], rxc.VDD / 2)
    ph = [((rq[rq > x][0] - x) * df * 360) % 360 for x in ri[:-1] if (rq > x).any()]
    fs = 8e6
    tu = np.arange(tskip, t[-1], 1 / fs)
    st = rx_model.steps_b(np.interp(tu, t, pl['v(q_i)']) > rxc.VDD / 2, np.interp(tu, t, pl['v(q_q)']) > rxc.VDD / 2)
    i_ant = (pl['v(dp)'] - pl['v(pinp)']) / 36.5
    return dict(f_ring=f, bb_iq_phase=float(np.angle(cq / ci, deg=True)), bb_i_v=float(abs(ci)), bb_q_v=float(abs(cq)),
                q_iq_phase=float(np.median(ph)) if ph else None, steps=int(st.sum()),
                steps_expected=float(df * (t[-1] - tskip) * 4),
                duty_lo_i=rxc.duty(t[m], pl['v(xrx.lo_i)'][m], rxc.VDD / 2),
                duty_lo_q=rxc.duty(t[m], pl['v(xrx.lo_q)'][m], rxc.VDD / 2),
                lo_ant_dbm=float(10 * np.log10(abs(M.dft(t, i_ant, f, tskip)) ** 2 * 73 / 2 / 1e-3 + 1e-30)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode')
    ap.add_argument('--level', type=float, default=-95)
    ap.add_argument('--corner', default='typical')
    ap.add_argument('--tstop', type=float, default=len(BITS) / RATE + 5e-6)
    ap.add_argument('--maxstep', type=float, default=20e-12)
    ap.add_argument('--nf', type=float, default=None)
    ap.add_argument('--tag', default='chain')
    ap.add_argument('--nbits', type=int, default=len(BITS))
    a = ap.parse_args()
    t0 = time.time()
    if a.mode in ('fsk', 'noise'):
        name = f'{a.mode}_{rxc.CN[a.corner]}_{a.level:g}' + (f'_nf{a.nf:g}' if a.nf is not None else '')
        bits = BITS[:a.nbits]
        d, log, bad = rxc.run(name, fsk_deck(a.corner, a.level, a.tstop, a.nf, a.maxstep, bits), sub=a.tag,
                              timeout=6 * 3600)
        try:
            r = fsk_analyse(d, bits)
        except Exception as e:  # noqa: BLE001
            r = dict(error=str(e), log=log.splitlines()[-5:])
        r.update(mode=a.mode, corner=rxc.CN[a.corner], level=a.level, nf=a.nf, bad=bad, wall_s=time.time() - t0)
        (d / 'result.json').write_text(json.dumps(r, indent=1))
        print(json.dumps(r))
    elif a.mode in ('p1db', 'blocker'):
        if a.mode == 'p1db':
            jobs = [((2e6, lv), None, 4e-6) for lv in (-60, -50, -45, -40, -35, -30, -25, -20)]
        else:
            jobs = [((150e3, -70), (df, lv), 16e-6) for df in (1e6, 2e6) for lv in (-70, -50, -40, -30, -20)]

        def one(j):
            tone, blk, ts = j
            nm = f'{a.mode}_{rxc.CN[a.corner]}_t{tone[1]:g}' + (f'_b{blk[0] / 1e6:g}M{blk[1]:g}' if blk else '')
            d, log, bad = rxc.run(nm, cw_deck(a.corner, tone, blk, ts, a.maxstep), sub=a.tag, timeout=6 * 3600)
            try:
                r = cw_analyse(d, tone, blk, ts - (2e-6 if a.mode == 'p1db' else 13.33e-6))
            except Exception as e:  # noqa: BLE001
                r = dict(error=str(e))
            r.update(tone=tone, blocker=blk, bad=bad)
            print(json.dumps(r), flush=True)
            return r
        rows = rxc.pmap(one, jobs, len(jobs))
        (rxc.BUILD / a.tag / f'{a.mode}.json').write_text(json.dumps(rows, indent=1))
    elif a.mode == 'reallo':
        d, log, bad = rxc.run(f'reallo_{rxc.CN[a.corner]}', real_lo_deck(a.tstop, level=a.level, corner=a.corner,
                                                                          f_lo=409.60e6), sub=a.tag, timeout=8 * 3600)
        try:
            r = real_lo_analyse(d, 100e3)
        except Exception as e:  # noqa: BLE001
            r = dict(error=str(e), log=log.splitlines()[-5:])
        r.update(mode='reallo', corner=rxc.CN[a.corner], level=a.level, bad=bad, wall_s=time.time() - t0)
        (d / 'result.json').write_text(json.dumps(r, indent=1))
        print(json.dumps(r))


if __name__ == '__main__':
    main()
