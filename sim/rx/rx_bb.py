#!/usr/bin/env python3
"""
Receiver baseband (option B), one instance per arm (I, Q): three differential gain stages.

  bbp/bbn (the mixer's baseband nodes, DC = the LNA output, ~2.1 V)
   -> stage 1 (low noise): NMOS pair, gates DC-coupled to the mixer (the mixer is high-Z and passes the LNA's DC;
      the mixer offset sees only stage 1's gain), poly loads, wideband
   -> AC coupling (Cc nfet gate caps, gates of the next pair biased at vb2 through pseudo-resistors)
   -> stage 2: gain + a load cap: pole p1
   -> AC coupling -> stage 3: gain + a load cap: pole p2   -> outp/outn (to rx_lim)
  p1 = p2 ~ 233 kHz: a 2nd-order low-pass with -3 dB at 150 kHz (two real poles, Q 0.5; a Butterworth needs an
  active biquad). Every AC coupling is a high-pass far below 10 kHz (pseudo-resistors are >> 1 GOhm).
  Tails: mirrors of rx_bias's nb (unit 25 uA); fractional units are narrower devices of the same L.
  vb2 (the stage-2/3 gate bias) is a gated poly divider with a decap.

Stage helper dstage() is shared with rx_lim.

    python3 sim/rx/rx_bb.py                     # print the netlist
    python3 sim/rx/rx_bb.py bench [--corners ...]  # phase A4 (.ac / .noise / offset transient)
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rxc  # noqa: E402
import rx_bias  # noqa: E402

S = dict(
    # stage 1: low noise, gate DC = the mixer / LNA output DC
    s1_w=20.0, s1_nf=16, s1_l=1.0, s1_mt=8.0, s1_rl=10e3,
    # stages 2, 3: low current, high-R loads, load cap -> the two LPF poles
    s2_w=4.0, s2_nf=2, s2_l=1.0, s2_mt=0.15, s2_rl=200e3, s2_cl=4.0e-12,
    s3_w=4.0, s3_nf=2, s3_l=1.0, s3_mt=0.4, s3_rl=200e3, s3_cl=4.0e-12,
    cc=1.0e-12,                  # AC coupling caps (nfet gate caps)
    vb1=150e3, vb2=100e3,        # vb divider (top, bottom), ppolyf_u_1k: vb ~ 1.0 V
    cvb=1e-12,
)


def tail(name, d, mt):
    """mt x the rx_bias unit (IU 25 uA): integer part as m units, a fractional part as one narrower device."""
    n, fr = int(mt), mt - int(mt)
    out = rx_bias.mirror(name, d, 'nb', n) if n else ''
    if fr > 1e-6:
        out += rxc.nfet(f'{name}f', d, 'nb', 'VSS', rx_bias.UW * fr, rx_bias.UL)
    return out


def pseudo_r(name, a, b, vgr='vgr'):
    """Gate-bias element a (the high-Z gate) - b (vb), two parts in parallel:
    - Mr: a subthreshold pfet (W/L RW/RL, n-well on vb) with its gate at vgr from the replica in vbias(): at mV
      across it is a defined ~60 MOhm (I_sat = IREP x (W/L)r / (W/L)rep, g = I_sat / Ut), so each coupling is a
      high-pass of a few kHz that tracks process through the replica;
    - a MOS-bipolar pseudo-resistor (Harrison and Charles): two diode-connected pfets in series (gate = drain = the
      mid node), each n-well on its outer terminal: >> 1 GOhm for small signals, but it conducts exponentially for
      steps of more than ~0.3 V (power-up, overload), which Mr alone would only slew at its nA."""
    m = 'm' + name
    return (rxc.fet(f'{name}r', a, vgr, b, b, 'pfet_03v3', RR[0], RR[1])
            + rxc.fet(f'{name}a', m, m, a, a, 'pfet_03v3', 0.42, 1.0)
            + rxc.fet(f'{name}b', m, m, b, b, 'pfet_03v3', 0.42, 1.0))


RR = (0.42, 12.0)         # Mr W, L (um)
REP = (4.0, 1.0)          # replica pfet diode W, L: (W/L)r / (W/L)rep = 1 / 114
SINK = (0.42, 50.0)       # replica current: nfet on nb, W/L 1/119 of the 25 uA unit's W/L 4 -> ~0.1-0.2 uA


def dstage(tag, ip, im, op, om, w, nf, l, mt, rl, cl=0.0, rlw=1.0):
    """Differential pair with poly loads: op = !ip side. Loads ppolyf_u_1k (rl > 20k) or ppolyf_u."""
    model = 'ppolyf_u_1k' if rl > 20e3 else 'ppolyf_u'
    out = (rxc.nfet(f'M{tag}a', om, ip, f't{tag}', w, l, nf) + rxc.nfet(f'M{tag}b', op, im, f't{tag}', w, l, nf)
           + tail(f'Mt{tag}', f't{tag}', mt)
           + rxc.res(f'R{tag}a', om, 'VDD', rl, rlw, model) + rxc.res(f'R{tag}b', op, 'VDD', rl, rlw, model))
    if cl > 0:
        out += rxc.scap(f'C{tag}a', om, cl) + rxc.scap(f'C{tag}b', op, cl)
    return out


def couple(tag, ip, im, op, om, cc, vb):
    """AC coupling: pfet gate caps, gate on the next stage's input (high-Z, at vb ~1.3 V: only gate oxide on it) and
    S/D/n-well on the previous stage's output (~2 V, low-Z): inverted (Vsg ~0.8-1.5 V)."""
    w = cc / (rxc.COX * 10e-6) * 1e6
    return (rxc.fet(f'Cc{tag}a', ip, op, ip, ip, 'pfet_03v3', w, 10.0)
            + rxc.fet(f'Cc{tag}b', im, om, im, im, 'pfet_03v3', w, 10.0)
            + pseudo_r(f'Rp{tag}a', op, vb) + pseudo_r(f'Rp{tag}b', om, vb))


def vbias(s, name='vb'):
    """vb: a gated poly divider (+ decap). vgr: the gate of the coupling resistors Mr, from a replica pfet diode
    (source on vb) carrying a small current sunk by a long nfet mirrored from nb."""
    return (rxc.pfet(f'M{name}s', f'{name}t', 'enb', 'VDD', 1.0) + rxc.res(f'R{name}1', f'{name}t', name, s['vb1'])
            + rxc.res(f'R{name}2', name, 'VSS', s['vb2']) + rxc.scap(f'C{name}', name, s['cvb'])
            + rxc.fet(f'M{name}rep', 'vgr', 'vgr', name, name, 'pfet_03v3', REP[0], REP[1])
            + rxc.nfet(f'M{name}snk', 'vgr', 'nb', 'VSS', SINK[0], SINK[1]))


def block(s=None):
    s = dict(S, **(s or {}))
    return ('.subckt rx_bb VDD VSS inp inn outp outn nb enb\n'
            + vbias(s)
            + dstage('1', 'inp', 'inn', 'o1p', 'o1n', s['s1_w'], s['s1_nf'], s['s1_l'], s['s1_mt'], s['s1_rl'], rlw=2.0)
            + couple('2', 'o1p', 'o1n', 'g2p', 'g2n', s['cc'], 'vb')
            + dstage('2', 'g2p', 'g2n', 'o2p', 'o2n', s['s2_w'], s['s2_nf'], s['s2_l'], s['s2_mt'], s['s2_rl'], s['s2_cl'])
            + couple('3', 'o2p', 'o2n', 'g3p', 'g3n', s['cc'], 'vb')
            + dstage('3', 'g3p', 'g3n', 'outp', 'outn', s['s3_w'], s['s3_nf'], s['s3_l'], s['s3_mt'], s['s3_rl'],
                     s['s3_cl'])
            + '.ends\n')


# ---- phase A4 bench: rx_bb (+ rx_lim's preamp stage) .ac / .noise, the input at the mixer's DC ------------------
def bench_deck(corner, s=None, lim=True, vin_dc=2.51, rsrc=500.0):
    import rx_lim
    s = dict(S, **(s or {}))
    out = 'xlim.lp xlim.ln' if lim else 'outp outn'
    limx = (rx_lim.block() + 'Xlim VDD VSS outp outn q nb enb rx_lim\n') if lim else ''
    return f"""* rx_bb bench {corner}
{rxc.hdr(corner)}{rx_bias.block()}{block(s)}
VDD VDD 0 {rxc.VDD}
VSS VSS 0 0
Ven en 0 {rxc.VDD}
Xb VDD VSS en enb nb rx_bias
vcm cm 0 {vin_dc}
vin ip im dc 0 ac 1
Rs1 cm ip {rsrc / 2}
Rs2 im cm {rsrc / 2}
Cbp ip 0 2p
Cbn im 0 2p
Xbb VDD VSS ip im outp outn nb enb rx_bb
{limx}.control
option temp=27
op
let idd = -i(VDD)
echo "OP $&idd"
print v(xbb.o1p) v(xbb.o2p) v(outp) v(xbb.g2p) v(xbb.vb) v(xbb.t1) v(xbb.t2) v(xbb.vgr) @m.xbb.xmvbsnk.m0[id]
ac dec 40 10 100e6
let glo = vm({out.split()[0]},{out.split()[1]})
let g = vm({out.split()[0]},{out.split()[1]})
let gbb = vm(outp,outn)
meas ac gpk max g
meas ac gbbpk max gbb
let g3 = gpk/sqrt(2)
meas ac fhi when g=g3 fall=last
meas ac flo when g=g3 rise=1
meas ac g100k find g at=100e3
meas ac gbb100k find gbb at=100e3
meas ac g150k find g at=150e3
meas ac g1m find g at=1e6
wrdata ac.txt g gbb
noise v({out.split()[0]},{out.split()[1]}) vin dec 20 1e3 10e6
setplot noise1
wrdata noise.txt onoise_spectrum inoise_spectrum
let in100 = inoise_spectrum[60]
echo "INZ $&in100"
.endc
.end
"""


def offs_deck(corner, vos=10e-3, step=0, asig=100e-6, fsig=100e3, tstop=1e-3, vin_dc=2.51, s=None):
    """rx_bb + rx_lim, a 100 kHz tone (asig, diff peak) at the input with a DC offset vos: static (in the operating
    point) when step = 0, else stepped from 0 to vos at t = 50 us. Watches q (duty, edges) and the stage outputs."""
    import rx_lim
    s = dict(S, **(s or {}))
    vo = f'pwl(0 0 50u 0 50.01u {vos})' if step else f'dc {vos}'
    return f"""* rx_bb offset {corner} vos {vos} step {step}
{rxc.hdr(corner)}{rx_bias.block()}{block(s)}{rx_lim.block()}
VDD VDD 0 {rxc.VDD}
VSS VSS 0 0
Ven en 0 {rxc.VDD}
Xb VDD VSS en enb nb rx_bias
vcm cm 0 {vin_dc}
vos ov 0 {vo}
vsig sg 0 sin(0 {asig} {fsig})
Bp ip 0 V=v(cm)+(v(ov)+v(sg))/2
Bn im 0 V=v(cm)-(v(ov)+v(sg))/2
Xbb VDD VSS ip im outp outn nb enb rx_bb
Xlim VDD VSS outp outn q nb enb rx_lim
.control
option temp=27
save v(q) v(outp) v(outn) v(xbb.o1p) v(xbb.o1n) v(xbb.o2p) v(xbb.o2n) v(xlim.lp) v(xlim.ln)
tran 50n {tstop} 0 50n
set filetype=binary
write out.raw
quit
.endc
.end
"""


def offs_analyse(d, tstop=1e-3):
    pl = rxc.read_raw(d / 'out.raw')[0]['vars']
    t = pl['time']
    q = pl['v(q)']
    r = {}
    # recovery: the first time after the step from which every 100 kHz period has one rising edge of q
    rr = rxc.xings(t, q, 1.65)
    after = rr[rr > 50e-6]
    gaps = np.where(np.diff(after) > 15e-6)[0]
    r['t_recover'] = float((after[gaps[-1] + 1] if len(gaps) else (after[0] if len(after) else np.nan)) - 50e-6)
    for nm, a, b in (('w1', 10e-6, 50e-6), ('w2', 55e-6, 100e-6), ('w3', 900e-6, tstop)):
        m = (t >= a) & (t <= b)
        r[f'duty_{nm}'] = rxc.duty(t[m], q[m], 1.65)
        r[f'edges_{nm}'] = int(len(rxc.xings(t[m], q[m], 1.65)))
        for k in ('o1', 'o2'):
            dv = pl[f'v(xbb.{k}p)'][m] - pl[f'v(xbb.{k}n)'][m]
            r[f'{k}_{nm}'] = [float(dv.min()), float(dv.max())]
    return r


def analyse(d, log):
    m = rxc.meas(log)
    r = {k: m.get(k) for k in ('gpk', 'gbbpk', 'fhi', 'flo', 'g100k', 'gbb100k', 'g150k', 'g1m')}
    mv = re.search(r'v\(xbb.vgr\) = (\S+)', log)
    r['vgr'] = float(mv.group(1)) if mv else None
    for line in log.splitlines():
        t = line.split()
        if t and t[0] == 'OP' and len(t) > 1:
            r['idd'] = float(t[1])
    try:
        nz = np.loadtxt(d / 'noise.txt')
        f, on, inn = nz[:, 0], nz[:, 1], nz[:, 3]
        r['in_100k'] = float(np.interp(100e3, f, inn))      # input-referred V/rtHz at 100 kHz
        r['in_10k'] = float(np.interp(10e3, f, inn))
        r['in_1m'] = float(np.interp(1e6, f, inn))
        # output rms noise over 1 kHz .. 10 MHz
        r['on_rms'] = float(np.sqrt(np.trapezoid(on ** 2, f)))
    except Exception as e:  # noqa: BLE001
        r['noise_err'] = str(e)
    for k in ('gpk', 'gbbpk', 'g100k', 'gbb100k', 'g150k', 'g1m'):
        if r.get(k):
            r[k + '_db'] = float(rxc.db(r[k]))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', nargs='?', default='print')
    ap.add_argument('--corners', default='typical')
    ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--tag', default='bb')
    a = ap.parse_args()
    s = dict(S)
    for kv in a.set:
        k, v = kv.split('=')
        s[k] = float(v)
    if a.mode == 'print':
        print(block(s), end='')
        return
    t0 = time.time()
    if a.mode == 'offs':
        jobs = [(c, v, st) for c in [{'tt': 'typical'}.get(c, c) for c in a.corners.split(',')]
                for v, st in ((0.0, 0), (10e-3, 0), (50e-3, 0), (10e-3, 1), (50e-3, 1))]

        def onef(j):
            c, v, st = j
            d, log, bad = rxc.run(f'{rxc.CN[c]}_v{v * 1e3:.0f}m_s{st}', offs_deck(c, v, st), sub=a.tag)
            try:
                r = offs_analyse(d)
            except Exception as e:  # noqa: BLE001
                r = dict(error=str(e))
            r.update(corner=rxc.CN[c], vos=v, step=st, bad=bad)
            print(json.dumps(r), flush=True)
            return r
        rows = rxc.pmap(onef, jobs, 10)
        (rxc.BUILD / a.tag / 'rows.json').write_text(json.dumps(dict(S=s, rows=rows), indent=1))
        print(f'{time.time() - t0:.0f} s')
        return

    def one(c):
        d, log, bad = rxc.run(rxc.CN[c], bench_deck(c, s), sub=a.tag)
        r = analyse(d, log)
        r.update(corner=rxc.CN[c], bad=bad)
        print(json.dumps({k: (float(f'{v:.4g}') if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
        return r
    rows = rxc.pmap(one, [{'tt': 'typical'}.get(c, c) for c in a.corners.split(',')], 8)
    (rxc.BUILD / a.tag / 'rows.json').write_text(json.dumps(dict(S=s, rows=rows), indent=1))
    print(f'{time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
