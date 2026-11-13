#!/usr/bin/env python3
"""
Figures for docs/rx_design.md from the phase A / C / D results (style as sim/rx/rx_plots.py).

    python3 sim/rx/rx_figs.py      # -> docs/img/rx/rx_bb_response.png, rx_nf.png (+ the model figures when present)
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import rx_plots as P  # noqa: E402  (palette and rcParams)
from scipy import signal  # noqa: E402

IMG = os.path.join(REPO, 'docs', 'img', 'rx')
BUILD = os.path.join(REPO, 'build', 'rx')
CORN = ('tt', 'ss', 'ff', 'sf', 'fs')


def fig_bb():
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for c in CORN:
        a = np.loadtxt(os.path.join(BUILD, 'bb_final', c, 'ac.txt'))
        f, g = a[:, 0], 20 * np.log10(a[:, 1])
        if c == 'tt':
            ft, gt = f, g
        else:
            ax.plot(f, g - g.max(), color='#c9c9c4', lw=1.0)
    ax.plot(ft, gt - gt.max(), color=P.CA, lw=1.8)
    d = json.load(open(os.path.join(HERE, 'results', 'meas_model.json')))['fit']
    import rx_model_meas as M
    h = 20 * np.log10(np.abs(M.h_meas(ft, d['fh'], d['fp'], d['fp2'])))
    ax.plot(ft, h - h.max(), color=P.CB, lw=1.2, ls='--')
    w, hd = signal.freqs_zpk(*signal.butter(2, 2 * np.pi * 150e3, 'low', analog=True, output='zpk'), worN=2 * np.pi * ft)
    w2, hh = signal.freqs_zpk(*signal.butter(1, 2 * np.pi * 10e3, 'high', analog=True, output='zpk'), worN=2 * np.pi * ft)
    ax.plot(ft, 20 * np.log10(np.abs(hd * hh)), color=P.C3, lw=1.2, ls=':')
    ax.set_xscale('log'); ax.set_xlim(300, 1e7); ax.set_ylim(-60, 5)
    ax.axhline(-3, color=P.GREY, lw=0.7)
    ax.text(1.3e6, -20, 'simulated, tt', color=P.INK, fontsize=8.5)
    ax.text(5e3, -48, 'ss, ff, sf, fs (grey)', color=P.INK2, fontsize=8)
    ax.text(4e5, -6, 'design: Butterworth 2nd order\n150 kHz + 10 kHz high-pass (dotted)', color=P.INK2, fontsize=8)
    ax.text(330, -1, f"fit (dashed): 4 high-pass at {d['fh'] / 1e3:.1f} kHz,\n2 low-pass at {d['fp'] / 1e3:.0f} kHz",
            color=P.INK2, fontsize=8)
    ax.set_xlabel('baseband frequency (Hz)'); ax.set_ylabel('gain, normalised (dB)')
    ax.set_title('Baseband + limiter stage response: -3 dB at 8.5 kHz and 143 kHz (tt)')
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, 'rx_bb_response.png'))


def fig_nf():
    b = json.load(open(os.path.join(HERE, 'results', 'budget.json')))
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    rr = (15, 40, 60)
    for noff, ls in ((3, '-'), (0, '--')):
        allc = np.array([[next(x['nf_total'] for x in b if x['corner'] == c and x['n_off'] == noff and x['rroute'] == r)
                          for r in rr] for c in CORN])
        ax.fill_between(rr, allc.min(0), allc.max(0), color='#e3e3de', lw=0)
        ax.plot(rr, allc[0], color=P.CA, ls=ls, marker='o', ms=4)
        ax.text(61.5, allc[0][-1], f'tt, n_off {noff}', color=P.INK, fontsize=8.5, va='center')
    ax.axhline(10, color=P.INK, lw=0.8)
    ax.text(15.5, 9.6, 'target 10 dB (rx_model sensitivity assumption)', fontsize=8, color=P.INK, va='top')
    ax.text(15.5, 5.0, 'grey: range over tt, ss, ff, sf, fs', fontsize=8, color=P.INK2)
    ax.set_xlim(13, 72); ax.set_ylim(4, 11)
    ax.set_xlabel('pad routing resistance Rroute (Ω)'); ax.set_ylabel('noise figure (dB)')
    ax.set_title('Noise figure, antenna to the comparator input: 7.27 dB at tt, n_off 3, 40 Ω')
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, 'rx_nf.png'))


def fig_sel():
    d = json.load(open(os.path.join(HERE, 'results', 'meas_model.json')))
    if 'sel' not in d:
        return
    s = d['sel']
    f = np.array(s['f']) / 1e3
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for name, col, ls in (('design', P.C3, ':'), ('measured tt', P.CA, '-')):
        rel = np.array(s[name]) - (d['sens_1e-3_10k'][name] + 3)
        ax.plot(f, rel, color=col, ls=ls, marker='o', ms=3)
    ax.text(1050, 13, 'measured receiver (tt)', color=P.INK, fontsize=8.5)
    ax.text(250, 36, 'design assumptions\n(Butterworth, NF 10 dB)', color=P.INK2, fontsize=8.5)
    ax.set_xlabel('CW interferer offset from 433.92 MHz (kHz)')
    ax.set_ylabel('largest CW / wanted (dB)')
    ax.set_title('Selectivity (model): 20.4 dB at +1 MHz, 35.0 dB at +2 MHz (measured, tt)')
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, 'rx_sel_meas.png'))


if __name__ == '__main__':
    fig_bb()
    fig_nf()
    fig_sel()
