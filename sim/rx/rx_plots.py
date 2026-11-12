#!/usr/bin/env python3
"""Figures for the option A vs option B receiver comparison (rx_model.py).

Sweeps are cached in results/sweeps.json; pass --force NAME to re-run one (or 'all').
"""
import json
import os
import sys
from multiprocessing import Pool

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

import rx_model as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'results')
CACHE = os.path.join(OUT, 'sweeps.json')
CA, CB, C3, GREY = '#2a78d6', '#eb6834', '#1baf7a', '#8a8a85'
INK, INK2 = '#1f1f1e', '#5c5c58'

plt.rcParams.update({
    'figure.dpi': 100, 'savefig.dpi': 200, 'font.size': 9, 'axes.titlesize': 9.5, 'axes.labelsize': 9,
    'axes.edgecolor': '#b8b8b2', 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2,
    'axes.grid': True, 'grid.color': '#e6e6e1', 'grid.linewidth': 0.6, 'axes.spines.top': False,
    'axes.spines.right': False, 'lines.linewidth': 1.6, 'legend.frameon': False, 'legend.fontsize': 8.5,
    'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
})


def load():
    return json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def save(d):
    json.dump(d, open(CACHE, 'w'), indent=1)


def pmap(f, args):
    with Pool(4) as p:
        return p.starmap(f, args)


# ---- sweep workers (module level for multiprocessing) ----------------------------------------------------------
def _ber(opt, pin, rate, nbits, kw):
    return m.ber(opt, pin, rate=rate, nbits=nbits, **kw)


def _maxint(opt, sig, f, kw):
    return m.max_interferer(opt, sig, f, **kw)


def _lvl(opt, kw):
    return m.level_for_ber(opt, **kw)


def sweep_ber():
    pins = list(np.arange(-117, -95.5, 1.0))
    cases = {'A 10k': ('A', 10e3, 20000, {}), 'B 10k': ('B', 10e3, 20000, {}),
             'A 1k': ('A', 1e3, 4000, {}), 'B 1k': ('B', 1e3, 4000, {}),
             'B 10k 90deg': ('B', 10e3, 20000, {'dphi': 0.0}),
             'A 10k noPN': ('A', 10e3, 20000, {'pn': False}), 'B 10k noPN': ('B', 10e3, 20000, {'pn': False})}
    out = {'pins': pins}
    for name, (opt, rate, nb, kw) in cases.items():
        out[name] = pmap(_ber, [(opt, p, rate, nb, kw) for p in pins])
        print(name, out[name])
    return out


def sweep_offset():
    dfs = list(np.arange(-150e3, 150.1e3, 25e3))
    out = {'df': dfs}
    for opt in 'AB':
        out[opt] = pmap(_lvl, [(opt, {'df': d}) for d in dfs])
        print(opt, out[opt])
    return out


def sweep_selectivity(ref):
    offs = list(np.arange(-2000e3, 2000.1e3, 125e3))
    out = {'f': offs, 'ref': ref}
    for opt in 'AB':
        for pn in (True, False):
            sig = ref[opt] + 3
            out[f'{opt} pn{int(pn)}'] = pmap(_maxint, [(opt, sig, f, {'pn': pn}) for f in offs])
            print(opt, pn, out[f'{opt} pn{int(pn)}'])
    return out


# ---- figures -----------------------------------------------------------------------------------------------------
def note(fig, text):
    fig.text(0.01, 0.005, text, fontsize=7.5, color=INK2, va='bottom')


def fig_nf():
    """Front-end noise figure: dipole -> pin (switch + routing R, pad C) -> LNA input noise Rn."""
    w = 2 * np.pi * m.FC
    rs = 73.0                         # dipole, differential
    rn = np.logspace(np.log10(10), np.log10(1000), 200)   # LNA input noise resistance, differential
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for rp, c, lab in ((26, CA, 'best: 11 Ω switch + 15 Ω routing'), (50, CB, 'mid: 50 Ω'),
                       (97, C3, 'worst tt: 37 Ω switch + 60 Ω routing')):
        R, C = 2 * rp, 7.7e-12 / 2
        f = 1 + R / rs + rn * (1 + (w * (rs + R) * C) ** 2) / rs
        ax.plot(rn, 10 * np.log10(f), color=c, label=f'R per side {rp} Ω ({lab})')
    R = 100
    f0 = 1 + R / rs + rn / rs
    ax.plot(rn, 10 * np.log10(f0), color=CB, ls=':', lw=1.2, label='mid, if the pin had no capacitance')
    for g in (10e-3, 20e-3, 40e-3):
        r = 2 / g
        ax.axvline(r, color=GREY, lw=0.8, ls='--')
        ax.text(r * 1.04, 1.2, f'gm {g*1e3:.0f} mS\nper side', fontsize=7.5, color=INK2)
    ax.axhline(10, color=INK, lw=0.8)
    ax.text(11, 10.3, 'NF used in the BER sims: 10 dB', fontsize=8, color=INK)
    ax.set_xscale('log')
    ax.set_xlim(10, 1000)
    ax.set_ylim(0, 22)
    ax.set_xlabel('LNA input noise resistance Rn, differential (Ω)   [Rn = 2γ/gm, γ = 1]')
    ax.set_ylabel('noise figure (dB)')
    ax.set_title('Fig. 1. Front-end NF: the pin R sets a 3–7 dB floor; the pin C multiplies the LNA noise 3–8×')
    ax.legend(loc='upper left')
    note(fig, 'Dipole 73 Ω; per side: series R (tt_asw_5v0 + routing), 7.7 pF to ground (docs/pad_model.md).\n'
              'LNA as a high-Z input with voltage noise 4kT·Rn. Mixer and IF noise not included (~+1 dB).')
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(os.path.join(OUT, 'rx_fig1_nf.png'))


def psd(x, fs, onesided):
    f, p = signal.welch(x, fs, nperseg=8192, return_onesided=onesided, scaling='density')
    if not onesided:
        f, p = np.fft.fftshift(f), np.fft.fftshift(p)
    return f, 10 * np.log10(p / 1e-3)


def fig_spectra():
    fs, rate = 8e6, 10e3
    rng = np.random.default_rng(3)
    bits = rng.integers(0, 2, 400)
    x, sps = m.rx_input(bits, rate, fs, -95, 10.0, rng, intf=[(-500e3, -95)])
    fig, axs = plt.subplots(3, 1, figsize=(6.4, 7.4))
    # (a) at the antenna
    f, p = psd(x, fs, False)
    ax = axs[0]
    ax.axvspan(-150, 150, color=CB, alpha=0.10, lw=0)
    ax.axvspan(-650, -350, color=CA, alpha=0.12, lw=0)
    ax.plot(f / 1e3, p, color=INK, lw=0.8)
    ax.axvline(-250, color=CA, lw=1.4)
    ax.axvline(0, color=CB, lw=1.4)
    ax.text(-245, -110, 'LO A\n433.67', color=CA, fontsize=8)
    ax.text(5, -110, 'LO B\n433.92', color=CB, fontsize=8)
    ax.text(-640, -110, "A's image band", color=CA, fontsize=8)
    ax.text(-140, -135, 'wanted 2-FSK', color=INK, fontsize=8)
    ax.text(-470, -132, 'CW −95 dBm', fontsize=8, color=INK)
    ax.set_title('(a) At the antenna: 2-FSK ±100 kHz at −95 dBm, a CW at −500 kHz, NF 10 dB noise')
    ax.set_xlim(-1000, 1000)
    ax.set_ylim(-170, -95)
    ax.set_xlabel('offset from 433.92 MHz (kHz)')
    ax.set_ylabel('dBm/Hz')
    # (b) A after the mixer
    t = np.arange(len(x)) / fs
    ya = np.real(x * np.exp(2j * np.pi * 250e3 * t))
    f, p = psd(ya, fs, True)
    ax = axs[1]
    ax.axvspan(100, 400, color=CA, alpha=0.12, lw=0)
    ax.plot(f / 1e3, p, color=CA, lw=0.8)
    ax.text(105, -100, 'IF band-pass 100–400 kHz', color=CA, fontsize=8)
    ax.annotate('image CW lands at 250 kHz,\nbetween the two tones', xy=(262, -141), xytext=(470, -125),
                fontsize=8, color=INK, arrowprops=dict(arrowstyle='-', color=INK2, lw=0.8))
    ax.text(120, -128, '150 kHz = "0"', fontsize=8, color=INK)
    ax.text(330, -128, '350 = "1"', fontsize=8, color=INK)
    ax.set_title('(b) Option A after the real mixer: the image folds onto the IF (noise too: +3 dB)')
    ax.set_xlim(0, 1000)
    ax.set_ylim(-170, -95)
    ax.set_xlabel('IF frequency (kHz)')
    ax.set_ylabel('dBm/Hz')
    # (c) B after the I/Q mixers
    i = x.real
    q = (x * np.exp(-1j * np.deg2rad(18))).imag
    f, p = psd(i + 1j * q, fs, False)
    ax = axs[2]
    ax.axvspan(-150, 150, color=CB, alpha=0.12, lw=0)
    ax.plot(f / 1e3, p, color=CB, lw=0.8)
    ax.text(-145, -100, 'I/Q low-pass ±150 kHz', color=CB, fontsize=8)
    ax.annotate('the CW stays at −500 kHz,\noutside the low-pass', xy=(-490, -141), xytext=(-980, -122),
                fontsize=8, color=INK, arrowprops=dict(arrowstyle='-', color=INK2, lw=0.8))
    ax.annotate('72° taps: a −16 dB mirror\nof the CW at +500 kHz', xy=(510, -155), xytext=(560, -128),
                fontsize=8, color=INK, arrowprops=dict(arrowstyle='-', color=INK2, lw=0.8))
    ax.set_title('(c) Option B after the I/Q mixers (I + jQ): ±100 kHz tones; the image does not exist')
    ax.set_xlim(-1000, 1000)
    ax.set_ylim(-170, -95)
    ax.set_xlabel('baseband frequency (kHz)')
    ax.set_ylabel('dBm/Hz')
    fig.suptitle('Fig. 2. How A and B see the band', x=0.01, ha='left', fontweight='bold', fontsize=10.5)
    note(fig, 'Welch PSD, 1 kHz bins; LO noise of the ring included. Noise floor −164 dBm/Hz = kT0 + NF 10 dB.')
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    fig.savefig(os.path.join(OUT, 'rx_fig2_spectra.png'))


def fig_pio():
    fs, rate = 8e6, 10e3
    rng = np.random.default_rng(7)
    data = np.array([1, 0, 0, 1, 1, 0, 1, 0])
    bits = np.concatenate([rng.integers(0, 2, m.NPRE), data, rng.integers(0, 2, m.NPOST)])
    x, sps = m.rx_input(bits, rate, fs, -100, 10.0, rng)
    pa, pb = m.A_DEF, m.B_DEF
    ya = m.chain_a(x, fs, **pa)
    ib, qb = m.chain_b(x, fs, **pb)
    ha = m.HYST * m.noise_rms('A', fs, pa, 10.0)
    hb = m.HYST * m.noise_rms('B', fs, pb, 10.0)
    ca, ci, cq = m.schmitt(ya, ha), m.schmitt(ib, hb), m.schmitt(qb, hb)
    sa, sb = m.steps_a(ca), m.steps_b(ci, cq)
    da, db = m.delay('A', fs, rate, pa), m.delay('B', fs, rate, pb)
    t = np.arange(len(x)) / fs * 1e6
    fig, axs = plt.subplots(3, 1, figsize=(6.4, 7.0))
    # zoom: 30 us around the 1->0 boundary (data bits 0/1), delayed by the filter
    b0 = (m.NPRE + 1) * sps
    for ax, d, opt in ((axs[0], da, 'A'), (axs[1], db, 'B')):
        z = slice(b0 + d - int(15e-6 * fs), b0 + d + int(15e-6 * fs))
        tz = t[z] - t[b0 + d]
        if opt == 'A':
            ax.plot(tz, ya[z] / np.abs(ya[z]).max(), color=CA, lw=0.9, label='IF after the band-pass')
            ax.step(tz, ca[z] * 0.8 + 1.3, color=INK, lw=1.0, where='post', label='comparator (the PIO input)')
            ax.set_title('(a) Option A at −100 dBm: one bit, IF tone 350 kHz ("1") then 150 kHz ("0")')
        else:
            ax.plot(tz, ib[z] / np.abs(ib[z]).max(), color=CB, lw=0.9, label='I after the low-pass')
            ax.plot(tz, qb[z] / np.abs(qb[z]).max(), color=CB, lw=0.9, ls='--', label='Q (72° tap)')
            ax.step(tz, ci[z] * 0.8 + 1.3, color=INK, lw=1.0, where='post', label='I comparator')
            ax.step(tz, cq[z] * 0.8 + 2.4, color=INK2, lw=1.0, where='post', label='Q comparator')
            ax.set_title('(b) Option B: I/Q rotate one way at +100 kHz, then the other way at −100 kHz')
        ax.axvline(0, color=GREY, lw=0.8, ls='--')
        ax.set_yticks([])
        ax.set_ylim(-2.4, 3.4 if opt == 'B' else 2.3)
        ax.set_xlim(tz[0], tz[-1])
        ax.set_xlabel('time from the bit boundary (µs)')
        ax.legend(loc='lower left', ncol=4, fontsize=7.5)
        ax.grid(False)
    # running counts over the data bits, threshold rate removed
    ax = axs[2]
    n0 = m.NPRE * sps
    nwin = len(data) * sps
    tt = (np.arange(nwin)) / fs * 1e6
    acc_a = np.cumsum(sa[n0 + da:n0 + da + nwin]) - 2 * pa['fif'] * tt * 1e-6
    acc_b = np.cumsum(sb[n0 + db:n0 + db + nwin])
    ax.plot(tt, acc_a, color=CA, label='A: transitions − 2·f_IF·t')
    ax.plot(tt, acc_b, color=CB, label='B: signed quadrant steps')
    for k, b in enumerate(data):
        ax.axvline(k * 100, color=GREY, lw=0.6)
        ax.text(k * 100 + 50, 175, str(b), ha='center', color=INK, fontsize=9, fontweight='bold')
    ax.set_xlim(0, nwin / fs * 1e6)
    ax.set_ylim(-95, 190)
    ax.set_xlabel('time (µs), 10 kbit/s')
    ax.set_ylabel('PIO count')
    ax.set_title('(c) What the RP2350 decides on: the count per bit (slope up = "1"); A ±20, B ±40 per bit')
    ax.legend(loc='lower left', ncol=2)
    fig.suptitle('Fig. 3. What the PIO sees (bits 1 0 0 1 1 0 1 0, near sensitivity)', x=0.01, ha='left',
                 fontweight='bold', fontsize=10.5)
    note(fig, 'Comparators with ±0.5 × noise-rms hysteresis; traces shifted by each chain\'s filter delay.')
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    fig.savefig(os.path.join(OUT, 'rx_fig3_pio.png'))


def interp_level(pins, bers, target):
    b = np.array(bers)
    for k in range(len(b) - 1):
        if b[k] > target >= b[k + 1] and b[k + 1] > 0:
            return np.interp(np.log10(target), [np.log10(b[k + 1]), np.log10(b[k])], [pins[k + 1], pins[k]])
        if b[k] > target and b[k + 1] == 0:
            return pins[k + 1]
    return np.nan


def fig_ber(d, off):
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.9), gridspec_kw=dict(width_ratios=[1.25, 1]))
    ax = axs[0]
    pins = d['pins']
    sty = {'A 10k': (CA, '-', 'A, 10 kbit/s'), 'B 10k': (CB, '-', 'B, 10 kbit/s'),
           'A 1k': (CA, '--', 'A, 1 kbit/s'), 'B 1k': (CB, '--', 'B, 1 kbit/s')}
    for k, (c, ls, lab) in sty.items():
        b = np.array(d[k], float)
        b[b == 0] = np.nan
        ax.semilogy(pins, b, color=c, ls=ls, marker='o', ms=3.5, label=lab)
    b = np.array(d['B 10k 90deg'], float)
    b[b == 0] = np.nan
    ax.semilogy(pins, b, color=GREY, ls=':', lw=1.2, label='B, 10 kbit/s, ideal 90° taps')
    ax.axhline(1e-3, color=INK, lw=0.7)
    ax.set_ylim(5e-5, 0.5)
    ax.set_xlim(pins[0], pins[-1])
    ax.set_xlabel('signal at the antenna (dBm)')
    ax.set_ylabel('bit-error rate')
    ax.set_title('(a) BER vs input level, NF 10 dB, ring LO noise')
    ax.legend(loc='upper right', fontsize=7.5)
    ax = axs[1]
    df = np.array(off['df']) / 1e3
    ax.plot(df, off['A'], color=CA, marker='o', ms=3.5, label='A')
    ax.plot(df, off['B'], color=CB, marker='o', ms=3.5, label='B')
    ax.set_xlabel('carrier offset, TX − RX LO (kHz)')
    ax.set_ylabel('level for BER 1e-2 (dBm)')
    ax.set_title('(b) Tolerance to tuning error, 10 kbit/s')
    ax.legend(loc='upper center')
    fig.suptitle('Fig. 4. Sensitivity at BER 1e-3: B −107.9 vs A −104.3 dBm at 10 kbit/s; B −114.6 vs A −110.1 at 1 kbit/s', x=0.01, ha='left',
                 fontweight='bold', fontsize=10.5)
    note(fig, '2-FSK ±100 kHz, NRZ whitened; A: IF 250 kHz, band-pass 100–400 kHz (4th order); '
              'B: ±150 kHz low-pass (2nd) + 10 kHz high-pass;\ngenie bit timing, threshold learned per packet. Points with no errors not drawn (20000 bits at 10 kbit/s, 4000 at 1 kbit/s).')
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(os.path.join(OUT, 'rx_fig4_ber.png'))


def fig_sel(s):
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    f = np.array(s['f']) / 1e3
    for opt, c in (('A', CA), ('B', CB)):
        sig = s['ref'][opt] + 3
        ax.plot(f, np.array(s[f'{opt} pn1']) - sig, color=c, marker='o', ms=3, label=f'{opt}, ring LO noise')
        y0 = np.array(s[f'{opt} pn0']) - sig
        y0[y0 > 60] = np.nan
        ax.plot(f, y0, color=c, ls=':', lw=1.2, label=f'{opt}, ideal LO')
    ax.axvline(-500, color=CA, lw=0.7, ls='--')
    ax.text(-490, -8, "A's image", color=CA, fontsize=8)
    ax.axhline(0, color=INK, lw=0.6)
    ax.set_ylim(-10, 50)
    ax.annotate("CW on A's LO: DC at the IF,\nremoved by the band-pass", xy=(-250, 21), xytext=(-900, 40),
                fontsize=7.5, color=CA, arrowprops=dict(arrowstyle='-', color=CA, lw=0.7))
    ax.annotate("CW on B's LO: DC, removed by the\nhigh-pass (ideal LO: off scale)", xy=(0, 1), xytext=(150, 44),
                fontsize=7.5, color=CB, arrowprops=dict(arrowstyle='-', color=CB, lw=0.7))
    ax.set_xlabel('CW interferer offset from 433.92 MHz (kHz)')
    ax.set_ylabel('largest interferer, dB above the signal')
    ax.set_xlim(f[0], f[-1])
    ax.legend(loc='lower right', ncol=2, fontsize=7.5)
    ax.set_title(f'Fig. 5. Selectivity: at A\'s image (−500 kHz) B takes a CW +16.6 dB above the signal, A −1.1 dB\n'
                 f"signal 3 dB above its own BER-1e-2 level (A {s['ref']['A']+3:.1f}, B {s['ref']['B']+3:.1f} dBm); "
                 f"largest CW keeping BER ≤ 1e-2")
    note(fig, 'Both filters 2nd-order prototypes. The model has no compression. The gap between solid and dotted '
              'is reciprocal mixing with the ring\'s phase noise.')
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(OUT, 'rx_fig5_selectivity.png'))


if __name__ == '__main__':
    force = sys.argv[sys.argv.index('--force') + 1] if '--force' in sys.argv else ''
    os.makedirs(OUT, exist_ok=True)
    d = load()
    fig_nf()
    fig_spectra()
    fig_pio()
    if 'ber' not in d or force in ('ber', 'all'):
        d['ber'] = sweep_ber(); save(d)
    if 'offset' not in d or force in ('offset', 'all'):
        d['offset'] = sweep_offset(); save(d)
    fig_ber(d['ber'], d['offset'])
    if 'sel' not in d or force in ('sel', 'all'):
        ref = {o: m.level_for_ber(o) for o in 'AB'}
        print('ref levels BER 1e-2:', ref)
        d['sel'] = sweep_selectivity(ref); save(d)
    fig_sel(d['sel'])
