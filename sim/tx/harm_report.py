#!/usr/bin/env python3
"""
Tables and figures for the TX harmonic study (sim/tx/run_harmonics.py output in build/tx_harm/).

    python3 sim/tx/harm_report.py
Writes sim/tx/results/harmonics.md and docs/img/tx_harm_{bars,islew,wave}.png (the wave figure re-runs two decks).
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harm_table as ht  # noqa: E402
import tb_tx_drv as tb  # noqa: E402

REPO = HERE.parents[1]
B = REPO / 'build' / 'tx_harm'
IMG = REPO / 'docs' / 'img'
CORNERS = ['tt', 'ss', 'ff', 'sf', 'fs']
COL = dict(tt='#2a78d6', ss='#eb6834', ff='#1baf7a', sf='#eda100', fs='#e87ba4')   # categorical slots 1-5
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'
LIMIT, GOAL = -36, -40
OPT2 = {n: abs(math.cos(math.radians(36 * n))) / math.cos(math.radians(36)) for n in range(1, 8)}  # rel. to fund


def style(ax):
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis='y', color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def jl(p):
    return [json.loads(x) for x in open(p)] if Path(p).exists() else []


def last(recs):
    d = {}
    for r in recs:
        d[r['tag']] = r
    return list(d.values())


def h(r, n):
    return r['res'].get(f'h{n}_dbc', float('nan'))


def ideal_rows(I):
    out = ['| corner | rs Ω | t_r / T | fund dBm | H2 | H3 | H4 | H5 | H6 | H7 | out_p H3 | out_p H5 |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in I:
        if r['ok']:
            out.append(f"| {r['corner']} | {r['rs']:g} | {r['frac']:g} | {r['p1_dbm']:+.2f} | "
                       + ' | '.join(f"{r[f'h{n}_dbc']:.1f}" for n in range(2, 8))
                       + f" | {r['op_h3_dbc']:.1f} | {r['op_h5_dbc']:.1f} |")
    return '\n'.join(out)


def opt2_rows(rows):
    """rows: (label, res). Option 2 on top: x cos(n 36 deg) / cos(36 deg) per harmonic, fund x cos(36 deg)."""
    out = ['| setting | fund dBm | H3 | H5 | H7 | + option 2: fund | H3 | H5 | H7 | max(H3, H5) |',
           '|---|---|---|---|---|---|---|---|---|---|']
    for lab, x in rows:
        o = {n: x[f'h{n}_dbc'] + 20 * math.log10(OPT2[n]) for n in (3, 5, 7)}
        out.append(f"| {lab} | {x['p1_dbm']:+.2f} | {x['h3_dbc']:.1f} | {x['h5_dbc']:.1f} | {x['h7_dbc']:.1f} | "
                   f"{x['p1_dbm'] + 20 * math.log10(math.cos(math.radians(36))):+.2f} | {o[3]:.1f} | {o[5]:.1f} | "
                   f"{o[7]:.1f} | {max(o[3], o[5]):.1f} |")
    return '\n'.join(out)


def fig_bars(base, shaped, ideal):
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    style(ax)
    ns = np.arange(2, 8)
    sets = [('today (square edges)', base, '#2a78d6'), ('shaped, best at tt', shaped, '#eb6834'),
            ('ideal trapezoid, t_r = T/3', ideal, '#1baf7a')]
    w = 0.26
    for i, (lab, x, c) in enumerate(sets):
        v = [x[f'h{n}_dbc'] if (n % 2 or x is not ideal) else -80 for n in ns]   # ideal bench: odd only
        bot = -80
        ax.bar(ns + (i - 1) * w, [vv - bot for vv in v], w * 0.92, bottom=bot, color=c, label=lab)
        for n, vv in zip(ns, v):
            if n in (3, 5):
                ax.text(n + (i - 1) * w, vv + 1, f'{vv:.0f}', ha='center', va='bottom', fontsize=8, color=INK)
    ax.axhline(LIMIT, color=INK, lw=1, ls='--')
    ax.text(1.55, LIMIT + 0.8, '−36 dBc pass line', ha='left', fontsize=8, color=INK2)
    ax.set_xticks(ns, [f'H{n}' for n in ns])
    ax.set_ylim(-80, 0)
    ax.set_ylabel('dBc at the dipole (73 Ω)', color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8, loc='upper right', ncol=1)
    fig.tight_layout()
    fig.savefig(IMG / 'tx_harm_bars.png', dpi=130)
    plt.close(fig)


def fig_islew(C):
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, n in zip(axs, (3, 5)):
        style(ax)
        for c in CORNERS:
            rs = sorted([r for r in C if r['corner'] == c and r['res'] and f'h{n}_dbc' in r['res']],
                        key=lambda r: r['sizes']['islew'])
            x = [r['sizes']['islew'] * 1e6 for r in rs]
            ax.plot(x, [h(r, n) for r in rs], color=COL[c], lw=2, marker='o', ms=4, label=c)
        ax.axhline(LIMIT, color=INK, lw=1, ls='--')
        ax.set_xscale('log')
        ax.set_xlabel('islew (µA, final NMOS turn-on current)', color=INK2, fontsize=9)
        ax.set_title(f'H{n} at the dipole', fontsize=10, color=INK, loc='left')
    axs[0].set_ylabel('dBc', color=INK2, fontsize=9)
    axs[0].text(axs[0].get_xlim()[0] * 1.1, LIMIT + 0.7, '−36 dBc', fontsize=8, color=INK2)
    h_, l_ = axs[0].get_legend_handles_labels()
    fig.legend(h_, l_, frameon=False, fontsize=8, loc='lower center', ncol=5, title='process corner',
               title_fontsize=8)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.savefig(IMG / 'tx_harm_islew.png', dpi=130)
    plt.close(fig)


def wave(sizes, tag):
    out = B / 'wave'
    out.mkdir(parents=True, exist_ok=True)
    (out / '.spiceinit').write_text('set ng_nomodcheck\nset num_threads=1\noption noinit\n')
    d = tb.deck('tt', sizes, 40.0, 3.0, False, 100e-12, 1.0, 1e-9)
    d = d.replace('linearize vr', f'wrdata {tag}.dat v(out_p) vr\nlinearize vr')
    (out / f'{tag}.cir').write_text(d)
    subprocess.run(['ngspice', '-b', f'{tag}.cir'], cwd=out, capture_output=True, text=True)
    return np.loadtxt(out / f'{tag}.dat')


def fig_wave(shaped_sizes):
    a, b = wave({}, 'today'), wave(shaped_sizes, 'shaped')
    fig, axs = plt.subplots(2, 1, figsize=(7.5, 4.6), sharex=True)
    t0 = tb.TSET + 5 * tb.T
    for ax, k, lab in ((axs[0], 1, 'out_p (on chip, V)'), (axs[1], 3, 'dipole voltage vr (V)')):
        style(ax)
        for d, c, n in ((a, '#2a78d6', 'today'), (b, '#eb6834', 'shaped')):
            m = (d[:, 0] >= t0) & (d[:, 0] <= t0 + 2 * tb.T)
            ax.plot((d[m, 0] - t0) * 1e9, d[m, k], color=c, lw=2, label=n)
        ax.set_ylabel(lab, color=INK2, fontsize=9)
    axs[0].legend(frameon=False, fontsize=8, loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2)
    axs[1].set_xlabel('time (ns), two periods at 433.92 MHz, tt, rroute 40 Ω, n_off 3', color=INK2, fontsize=9)
    fig.tight_layout()
    fig.savefig(IMG / 'tx_harm_wave.png', dpi=130)
    plt.close(fig)


def main():
    sel = json.loads((B / 'sel.json').read_text())
    A, Bs, C, D = (last(jl(B / s / 'results.jsonl')) for s in 'ABCD')
    I = jl(B / 'I' / 'ideal.jsonl')
    st = (B / 'status.txt').read_text()
    base = [r for r in A if r['corner'] == 'tt' and r['rroute'] == 40 and r['noff'] == 3][0]['res']
    best = sel['B']
    ideal = [r for r in I if r['corner'] == 'tt' and r['rs'] == 30 and r['frac'] == 0.333][0]
    s0 = best['sizes']
    md = ['# TX harmonics, option 1 (slew-controlled final stage): results',
          '', 'Generated by `sim/tx/harm_report.py` from `sim/tx/run_harmonics.py` (build/tx_harm). Write-up: '
          '`docs/tx_harmonics.md`. All dBc are at the dipole (vr across 73 Ω), ngspice `fourier` over the last '
          'period (1000-point grid), 2 ps step, 8 periods after 40 ns. VDPWR through 1 Ω + 1 nH (the TT grid and '
          'bond wire are not modelled). 27 °C, 3.3 V unless stated.', '',
          '## Driver log', '```', st.strip(), '```', '',
          f"**tt-best shaped setting (step B):** `{json.dumps(s0)}` (duty window used: {best['duty_window']}).", '',
          '## I. Bound: ideal linear trapezoids through the same pad path (rroute 40, n_off 3)', '',
          ideal_rows(I), '',
          '## A. Baseline: today\'s circuit', '', ht.table(A), '',
          '## B. tt sweep, shape=1 (best 25 by max(H3, H5), fund ≥ +3 dBm)', '',
          ht.table(sorted([r for r in Bs if r['res'] and r['res'].get('p1_dbm', -99) >= 3],
                          key=lambda r: max(h(r, 3), h(r, 5)))[:25]), '',
          '### B, all runs', '', ht.table(Bs), '',
          '## C. Corners: the tt-best (cmil, knp) against islew', '',
          '| corner | best islew µA | fund dBm | H3 | H5 | H7 | duty p/n % | duty window |', '|---|---|---|---|---|---|---|---|']
    for c in CORNERS:
        x = sel['C'][c]
        r = x['res']
        md.append(f"| {c} | {x['islew'] * 1e6:.0f} | {r['p1_dbm']:+.2f} | {r['h3_dbc']:.1f} | {r['h5_dbc']:.1f} | "
                  f"{r['h7_dbc']:.1f} | {r['duty_p']:.1f}/{r['duty_n']:.1f} | {x['duty_window']} |")
    md += ['', ht.table(sorted(C, key=lambda r: (CORNERS.index(r['corner']), r['sizes']['islew']))), '',
           '## D. Robustness at the tt-best islew (trim ×1) and each corner\'s trim code', '',
           'Trim codes (rroute 40, n_off 3): ' + ', '.join(f"{c} ×{v['trim']:g}" for c, v in sel['trim'].items())
           + f"; worst corner {sel['worst']}.", '', ht.table(D), '',
           '## Option 2 on top (estimate, not simulated)', '',
           'Two ring taps 72° apart summed: harmonic n scales by |cos(n·36°)|, so H3 and H7 by 0.309 (−10.2 dB), '
           'H5 by 1, and the fundamental by cos 36° = 0.809 (−1.8 dB); in dBc, H3 and H7 move by −8.4 dB and H5 by '
           '+1.8 dB.', '',
           opt2_rows([('today, tt r40 n3', base)]
                     + [(f"today, {r['corner']} r40 n3", r['res']) for r in A if r['rroute'] == 40 and r['noff'] == 3
                        and r['corner'] != 'tt']
                     + [(f"shaped, {c}, own islew", sel['C'][c]['res']) for c in CORNERS]
                     + [(f"shaped, {c}, trim ×{sel['trim'][c]['trim']:g}", sel['trim'][c]['res']) for c in CORNERS]),
           '']
    (HERE / 'results' / 'harmonics.md').write_text('\n'.join(md))
    IMG.mkdir(exist_ok=True)
    fig_bars(base, best['res'], ideal)
    fig_islew(C)
    fig_wave(s0)
    print('wrote sim/tx/results/harmonics.md, docs/img/tx_harm_{bars,islew,wave}.png')


if __name__ == '__main__':
    main()
