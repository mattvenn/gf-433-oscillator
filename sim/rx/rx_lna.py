#!/usr/bin/env python3
"""
Receiver LNA (option B): a port of the OOK receiver's first stage amp_dp (github.com/mattvenn/ook-asic-radio,
layout/ref/lna_chain.spice) to GF180, re-sized for the GF pin.

  inp/inn (ua pins, via the pad model) -> Cin (nfet gate cap, AC coupling) -> gates at vcm (Rg each)
  NMOS differential pair M1/M2 (nf fingers of wf x L), poly-resistor loads RL to VDD -> outp/outn
  tail: m x unit NMOS mirrored from rx_bias's nb (unit current IU), so I_tail = mt x IU

Port changes against amp_dp: sky130 nfet_01v8 L 0.15 -> nfet_03v3 L 0.28; res_high_po -> ppolyf_u (350 ohm/sq);
MIM -> nfet gate caps. Input option (S['pin']):
  'ac'  : (a) the pin side of Cin is held at 0 V through Rpin (the TT switch is ~15 ohm near 0 V), gates at vcm
  'dc'  : (b) no Cin: the pin sits at vcm (self-biased mid-rail, the switch near its 37 ohm peak)
vcm: a resistor divider from VDD (gated by en through a PMOS), decoupled by a gate cap.

    python3 sim/rx/rx_lna.py               # print the netlist
    python3 sim/rx/rx_lna.py bench [--set K=V ...] [--corners tt,ss,...] [--noff 0,3] [--pin ac,dc]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rxc  # noqa: E402
import rx_bias  # noqa: E402

S = dict(
    pin='dc',
    wf=10.0, nf=24, l=0.28,          # input pair: nf fingers of wf um per side
    mt=120,                          # tail: mt x the rx_bias unit (IU = 25 uA) -> 3 mA
    rl=800.0, rlw=4.0,               # load: ppolyf_u, rl ohm at rlw um wide
    cin=4e-12,                       # AC coupling cap per side (nfet gate cap, 'ac' only)
    rg=20e3,                         # gate bias resistors from vcm (ppolyf_u_1k)
    rpin=50e3,                       # pin-side bias resistor to VSS ('ac' only)
    rv1=40e3, rv2=30e3,              # vcm divider (top, bottom): vcm ~ VDD x rv2/(rv1+rv2)
    cvcm=2e-12,                      # vcm decap
    split=2,                         # 2: a second stage per arm (I, Q), both driven from stage 1: each mixer has its
                                     #    own LNA output, so the I and Q mixers don't load each other
                                     # 1: (tried) cascode current split into I / Q loads: +2 dB NF (cascode noise)
                                     # 0: one output pair (both mixers on it: -4 dB, I/Q phase -7 deg)
    wc=10.0, nfc=6,                  # split=1 cascodes: nfc fingers of wc um (each of the 4)
    rc1=40e3, rc2=80e3,              # split=1 cascode gate divider (top, bottom): vc ~ 2.2 V
    w2=10.0, nf2=6, mt2=40, rl2=1600.0, rlw2=2.0,  # split=2: second-stage pair per arm (DC-coupled to stage 1)
)


def block(s=None):
    s = dict(S, **(s or {}))
    g = ('gp', 'gn') if s['pin'] == 'ac' else ('inp', 'inn')
    if s['split'] == 2:
        return stage2(s) + block(dict(s, split=0)).replace('.subckt rx_lna VDD VSS inp inn outp outn nb enb',
                                                           '.subckt rx_lna VDD VSS inp inn oip oin oqp oqn nb enb')\
            .replace('.ends\n', 'x2i VDD VSS outp outn oip oin nb rx_lna2\nx2q VDD VSS outp outn oqp oqn nb rx_lna2\n.ends\n')
    if s['split']:
        out = '.subckt rx_lna VDD VSS inp inn oip oin oqp oqn nb enb\n'
    else:
        out = '.subckt rx_lna VDD VSS inp inn outp outn nb enb\n'
    if s['pin'] == 'ac':
        out += rxc.ccap('Cinp', 'gp', 'inp', s['cin']) + rxc.ccap('Cinn', 'gn', 'inn', s['cin'])
        out += rxc.res('Rpinp', 'inp', 'VSS', s['rpin']) + rxc.res('Rpinn', 'inn', 'VSS', s['rpin'])
    out += rxc.res('Rgp', g[0], 'vcm', s['rg']) + rxc.res('Rgn', g[1], 'vcm', s['rg'])
    out += (rxc.pfet('Mvs', 'vt', 'enb', 'VDD', 2.0) + rxc.res('Rv1', 'vt', 'vcm', s['rv1'])
            + rxc.res('Rv2', 'vcm', 'VSS', s['rv2']) + rxc.scap('Cvcm', 'vcm', s['cvcm']))
    if not s['split']:
        out += (rxc.nfet('M1', 'outn', g[0], 'tail', s['wf'], s['l'], s['nf'])
                + rxc.nfet('M2', 'outp', g[1], 'tail', s['wf'], s['l'], s['nf'])
                + rx_bias.mirror('Mt', 'tail', 'nb', s['mt']))
        out += (rxc.res('RLp', 'outn', 'VDD', s['rl'], s['rlw'], 'ppolyf_u')
                + rxc.res('RLn', 'outp', 'VDD', s['rl'], s['rlw'], 'ppolyf_u'))
        return out + '.ends\n'
    out += (rxc.nfet('M1', 'd1', g[0], 'tail', s['wf'], s['l'], s['nf'])
            + rxc.nfet('M2', 'd2', g[1], 'tail', s['wf'], s['l'], s['nf'])
            + rx_bias.mirror('Mt', 'tail', 'nb', s['mt']))
    out += (rxc.res('Rc1', 'vt', 'vc', s['rc1']) + rxc.res('Rc2', 'vc', 'VSS', s['rc2'])
            + rxc.scap('Cvc', 'vc', s['cvcm']))
    for arm in ('i', 'q'):
        out += (rxc.nfet(f'K{arm}1', f'o{arm}n', 'vc', 'd1', s['wc'], s['l'], s['nfc'])
                + rxc.nfet(f'K{arm}2', f'o{arm}p', 'vc', 'd2', s['wc'], s['l'], s['nfc'])
                + rxc.res(f'RL{arm}p', f'o{arm}n', 'VDD', 2 * s['rl'], s['rlw'] / 2, 'ppolyf_u')
                + rxc.res(f'RL{arm}n', f'o{arm}p', 'VDD', 2 * s['rl'], s['rlw'] / 2, 'ppolyf_u'))
    return out + '.ends\n'


def stage2(s):
    """rx_lna2: the second stage, one per arm. NMOS pair, gates DC-coupled to stage 1's outputs (~2.15 V),
    ppolyf_u loads: op = !ip side."""
    return ('.subckt rx_lna2 VDD VSS ip im op om nb\n'
            + rxc.nfet('M1', 'om', 'ip', 'tail', s['w2'], s['l'], s['nf2'])
            + rxc.nfet('M2', 'op', 'im', 'tail', s['w2'], s['l'], s['nf2'])
            + rx_bias.mirror('Mt', 'tail', 'nb', s['mt2'])
            + rxc.res('RLp', 'om', 'VDD', s['rl2'], s['rlw2'], 'ppolyf_u')
            + rxc.res('RLn', 'op', 'VDD', s['rl2'], s['rlw2'], 'ppolyf_u')
            + '.ends\n')


def bench_deck(s, corner, noff=3, rroute=40, cload=150e-15, temp=27):
    """Dipole (73 ohm diff, EMF vsig) -> pad_model x2 -> rx_lna (+ rx_bias) -> cload per output side."""
    f0 = 433.92e6
    return f"""* rx_lna bench {corner} n_off {noff} rroute {rroute} pin {s['pin']}
{rxc.hdr(corner, pad=True)}{rx_bias.block()}{block(s)}
VDD VDD 0 {rxc.VDD}
VSS VSS 0 0
Ven en 0 {rxc.VDD}
vsig dp dn dc 0 ac 1
Rsp dp pinp 36.5
Rsn dn pinn 36.5
Rdc dn 0 1e9
Xpp 0 pinp inp pad_model_gf180 rroute={rroute} n_off={noff}
Xpn 0 pinn inn pad_model_gf180 rroute={rroute} n_off={noff}
Xb VDD VSS en enb nb rx_bias
Xl VDD VSS inp inn {'outp outn oqp oqn' if s['split'] else 'outp outn'} nb enb rx_lna
Clp outp 0 {cload}
Cln outn 0 {cload}
{'Cqp oqp 0 '+str(cload)+chr(10)+'Cqn oqn 0 '+str(cload) if s['split'] else ''}
.control
option temp={temp}
op
let idd = -i(VDD)
echo "OP $&idd $&v(outp) $&v(xl.tail) $&v(xl.vcm) $&v(inp)"
noise v(outp,outn) vsig lin 2 {f0} {f0 * 1.0001}
setplot noise1
let on = onoise_spectrum[0]
echo "NZ $&on"
ac lin 1 {f0} {f0}
let g = v(outp)-v(outn)
let gr = real(g)
let gi = imag(g)
echo "AC0 $&gr $&gi"
ac lin 1 {3 * f0} {3 * f0}
let g = v(outp)-v(outn)
let gr = real(g)
let gi = imag(g)
echo "AC3 $&gr $&gi"
ac dec 20 1e6 10e9
let g = vm(outp,outn)
meas ac gpk max g
let g3 = gpk/sqrt(2)
meas ac fhi when g=g3 fall=last
alter vsig ac=0
alter VDD ac=1
ac lin 1 25e6 25e6
let pr = real(v(outp))
let pi = imag(v(outp))
let nr = real(v(outn))
let ni = imag(v(outn))
echo "PS $&pr $&pi $&nr $&ni"
.endc
.end
"""


def analyse(log, temp=27):
    r = {}
    for line in log.splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == 'OP' and len(t) >= 6:
            r.update(idd=float(t[1]), vout=float(t[2]), vtail=float(t[3]), vcm=float(t[4]), vpin=float(t[5]))
            if len(t) > 6:
                r['vd1'] = float(t[6])
        elif t[0] == 'AC0':
            r['av'] = abs(complex(float(t[1]), float(t[2])))
        elif t[0] == 'AC3':
            r['av3'] = abs(complex(float(t[1]), float(t[2])))
        elif t[0] == 'NZ' and len(t) > 1:
            r['onoise'] = float(t[1])
        elif t[0] == 'PS' and len(t) > 4:
            vp, vn = complex(float(t[1]), float(t[2])), complex(float(t[3]), float(t[4]))
            r['psrr_cm_db'] = float(rxc.db((vp + vn) / 2))
            r['psrr_dm_db'] = float(rxc.db(vp - vn)) if abs(vp - vn) > 0 else -300.0
    m = rxc.meas(log)
    r['fhi'] = m.get('fhi', float('nan'))
    if 'av' in r and 'onoise' in r:
        kt = 1.380649e-23 * (273.15 + temp)
        ns = 4 * kt * 73.0 * r['av'] ** 2
        r['nf'] = float(10 * np.log10(r['onoise'] ** 2 / ns))
        r['av_db'] = float(rxc.db(r['av']))
        r['av3_db'] = float(rxc.db(r['av3'])) if 'av3' in r else None
    return r


def bench(s, corners, noffs, pins, rroutes=(40,), tagname='lna', jobs=12, cload=150e-15):
    pts = [(c, n, p, rr) for c in corners for n in noffs for p in pins for rr in rroutes]

    def one(pt):
        c, n, p, rr = pt
        ss = dict(s, pin=p)
        name = f'{rxc.CN[c]}_n{n}_{p}_r{rr}'
        d, log, bad = rxc.run(name, bench_deck(ss, c, n, rr, cload), sub=tagname)
        r = analyse(log)
        r.update(corner=rxc.CN[c], n_off=n, pin=p, rroute=rr, bad=bad)
        return r
    rows = rxc.pmap(one, pts, jobs)
    for r in rows:
        print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}))
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', nargs='?', default='print')
    ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--corners', default='typical')
    ap.add_argument('--noff', default='3')
    ap.add_argument('--pin', default=S['pin'])
    ap.add_argument('--rroute', default='40')
    ap.add_argument('--tag', default='lna')
    ap.add_argument('--cload', type=float, default=150e-15)
    a = ap.parse_args()
    s = dict(S)
    for kv in a.set:
        k, v = kv.split('=')
        s[k] = type(S[k])(v) if not isinstance(S[k], str) else v
    if a.mode == 'print':
        print(rx_bias.block() + block(s), end='')
    else:
        corners = [{'tt': 'typical'}.get(c, c) for c in a.corners.split(',')]
        rows = bench(s, corners, [int(x) for x in a.noff.split(',')], a.pin.split(','),
                     [float(x) for x in a.rroute.split(',')], a.tag, cload=a.cload)
        out = rxc.BUILD / a.tag / 'rows.json'
        out.write_text(json.dumps(dict(S=s, rows=rows), indent=1))
