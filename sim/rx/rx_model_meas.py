#!/usr/bin/env python3
"""
Phase D: the behavioural model (rx_model.py) with the measured receiver in place of the design assumptions.

  filter : the measured baseband + limiter-stage response (sim/rx/rx_bb.py bench, tt, build/rx/bb_final/tt/ac.txt)
           fitted as 4 first-order high-passes (the four AC couplings) and 2 first-order low-passes (stages 2, 3)
  NF     : from sim/rx/results/budget.json (antenna to the comparator)
  I/Q    : the measured baseband I/Q phase (Table III) -> dphi = 90 - phase
  HYST   : the measured hysteresis / noise ratio (budget.json)
Re-runs sensitivity (BER 1e-3, 10 kbit/s) and selectivity (Fig. 5) for B: design assumptions vs measured.

    python3 sim/rx/rx_model_meas.py fit | ber | sel | figs
Outputs: sim/rx/results/meas_model.json, docs/img/rx/rx_meas_*.png
"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
from scipy import signal, optimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rx_model as m  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, 'results', 'meas_model.json')
FIT = {}


def h_meas(f, fh, fp, fp2=1e9, nh=4, nl=2):
    s = 1j * f
    return (s / (s + fh)) ** nh * (1 / (1 + s / fp)) ** nl / (1 + s / fp2)


def fit(path=os.path.join(REPO, 'build', 'rx', 'bb_final', 'tt', 'ac.txt')):
    a = np.loadtxt(path)
    f, g = a[:, 0], a[:, 1]
    m_ = (f > 300) & (f < 3e6)
    f, g = f[m_], g[m_]
    def err(p):
        fh, fp, fp2, k = p
        return np.log(np.abs(h_meas(f, fh, fp, fp2)) * k) - np.log(g)
    r = optimize.least_squares(err, [4e3, 220e3, 2e6, g.max()], x_scale=[1e3, 1e5, 1e6, g.max()],
                               bounds=([100, 1e4, 3e5, 0], [5e4, 1e6, 1e8, np.inf]))
    fh, fp, fp2, k = r.x
    e = err(r.x) * 20 / np.log(10)
    band = (f > 1e3) & (f < 1e6)
    return dict(fh=float(fh), fp=float(fp), fp2=float(fp2), gain_db=float(20 * np.log10(k)),
                max_err_db=float(np.max(np.abs(e))), max_err_1k_1M_db=float(np.max(np.abs(e[band]))),
                rms_err_db=float(np.sqrt(np.mean(e ** 2))))


def sos_meas(fs, fh, fp, fp2=None):
    out = [] if fp2 is None or fp2 >= 0.45 * fs else [signal.butter(1, fp2, 'low', fs=fs, output='sos')]
    for _ in range(4):
        out.append(signal.butter(1, fh, 'high', fs=fs, output='sos'))
    for _ in range(2):
        out.append(signal.butter(1, fp, 'low', fs=fs, output='sos'))
    return np.vstack(out)


_chain_b, _noise_rms = m.chain_b, m.noise_rms


def chain_b(x, fs, bw, order, hpf, dphi, dc, meas=None):
    if meas is None:
        return _chain_b(x, fs, bw, order, hpf, dphi, dc)
    i = x.real + dc
    q = (x * np.exp(-1j * np.deg2rad(dphi))).imag + dc
    sos = sos_meas(fs, *meas)
    return signal.sosfilt(sos, i), signal.sosfilt(sos, q)


def noise_rms(opt, fs, p, nf_db):
    if opt != 'B' or p.get('meas') is None:
        return _noise_rms(opt, fs, {k: v for k, v in p.items() if k != 'meas'}, nf_db)
    imp = np.zeros(int(fs * 2e-3)); imp[0] = 1
    g = np.sum(signal.sosfilt(sos_meas(fs, *p['meas']), imp) ** 2)
    return np.sqrt(m.KT0 * 10 ** (nf_db / 10) * fs / 2 * g)


m.chain_b, m.noise_rms = chain_b, noise_rms


def cases():
    fitd = json.load(open(OUT))['fit']
    bud = json.load(open(os.path.join(HERE, 'results', 'budget.json')))
    tt = [r for r in bud if r['corner'] == 'tt' and r['n_off'] == 3 and r['rroute'] == 40][0]
    worst = max(bud, key=lambda r: r['nf_total'])
    mix = json.load(open(os.path.join(HERE, 'results', 'mix', 'buffers.json')))['rows']
    ph = [r['iq_phase'] for r in mix if r['case'] == 'iq' and r['corner'] == 'tt'][0]
    meas = dict(meas=(fitd['fh'], fitd['fp'], fitd['fp2']), dphi=90 - ph)
    return {
        'design': dict(nf_db=10.0, hyst=None, over={}),
        'measured tt': dict(nf_db=tt['nf_total'], hyst=tt['hyst_ratio'], over=meas),
        'measured worst': dict(nf_db=worst['nf_total'], hyst=min(r['hyst_ratio'] for r in bud), over=meas),
    }, tt, worst, ph


def _lvl(kw):
    return m.level_for_ber('B', target=1e-3, nbits=20000, lo=-118, hi=-95, tol=0.25, **kw)


def _maxint(sig, f, kw):
    return m.max_interferer('B', sig, f, target=1e-2, nbits=2000, **kw)


def run_ber():
    cs, *_ = cases()
    args = [dict(nf_db=c['nf_db'], hyst=c['hyst'], **c['over']) for c in cs.values()]
    with Pool(6) as p:
        lv = p.map(_lvl, args)
    return dict(zip(cs.keys(), lv))


def run_sel(sens):
    cs, *_ = cases()
    offs = list(np.arange(-2000e3, 2000.1e3, 250e3))
    out = {'f': offs}
    for name in ('design', 'measured tt'):
        c = cs[name]
        kw = dict(nf_db=c['nf_db'], hyst=c['hyst'], **c['over'])
        with Pool(6) as p:
            out[name] = p.starmap(_maxint, [(sens[name] + 3, f, kw) for f in offs])
        print(name, out[name], flush=True)
    return out


if __name__ == '__main__':
    d = json.load(open(OUT)) if os.path.exists(OUT) else {}
    mode = sys.argv[1]
    if mode == 'fit':
        d['fit'] = fit()
        print(d['fit'])
    elif mode == 'ber':
        d['sens_1e-3_10k'] = run_ber()
        print(d['sens_1e-3_10k'])
    elif mode == 'sel':
        d['sel'] = run_sel(d['sens_1e-3_10k'])
    json.dump(d, open(OUT, 'w'), indent=1)
