#!/usr/bin/env python3
"""
Receiver noise budget (phase A / C): antenna -> comparator input, from the block results.

ngspice can't run .noise through a switching mixer (no periodic noise), so the chain NF is assembled here:
  1. pin + LNA: F_rf from rx_lna.py's .noise (dipole 73 ohm diff, pad model on both pins, at 433.92 MHz,
     F = total output noise / the part from the dipole's 73 ohm), at the arm's output, per corner / n_off / routing.
  2. mixer: a passive switching mixer into a high-Z baseband (no DC through the switches, so no flicker). Its
     conversion gain Gc = BB / LNA-output amplitude comes from rx_mix.py's transient (real LO buffers). It folds
     the LNA output noise from both sidebands of fLO onto the baseband (2 x S x Gc^2 per arm), as it does the
     signal from one; the I/Q pair recovers the 3 dB, as in rx_model (complex noise). The odd LO harmonics fold in
     the LNA noise near 3 fLO and 5 fLO with weights 1/9, 1/25: bounded with the LNA's gain at 3 fLO (Av3 - Av
     ~ -17 dB) to < 0.05 dB, left out. The switches' own thermal noise: bounded as a resistor-switch network,
     2 x Ron (two switches in series, Ron <= 200 ohm for the transmission gates at the 2.5 V baseband DC).
  3. baseband + limiter stage: rx_bb.py's .noise, input-referred (the bench's 500 ohm source removed), averaged
     over the signal band 10-150 kHz.
  F_total = F_rf x (1 + (N_bb + N_sw) / N_fe), N_fe = 2 x onoise_rf^2 x Gc^2 (per arm, at the baseband).
  Noise rms at the comparator = sqrt(integral (N_fe + N_bb + N_sw) |G_bb+L(f)|^2 df), and the hysteresis ratio
  = hysteresis / that rms (target 0.25-0.5, rx_model's HYST).

    python3 sim/rx/rx_budget.py      # -> sim/rx/results/budget.json, budget.md
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rxc  # noqa: E402

KT = 1.380649e-23 * 300.15
RON = 200.0
BAND = (10e3, 150e3)


def load(p):
    return json.loads(Path(p).read_text())


def main(lna_tag='lna_final', mix_tag='mix_a3b', bb_tag='bb_final', hyst_tag='hyst_final', out=None):
    lna = load(rxc.BUILD / lna_tag / 'rows.json')['rows']
    mix = {r['corner']: r for r in load(rxc.BUILD / mix_tag / 'rows.json')['rows'] if r['case'] == 'iq'}
    hy = {r['corner']: (r['vup2'] - r['vdn2']) / 2 for r in load(rxc.BUILD / hyst_tag / 'rows.json')['rows']}
    rows = []
    for r in lna:
        c = r['corner']
        cc = {'tt': 'tt'}.get(c, c)
        if cc not in mix:
            continue
        m = mix[cc]
        gc = 10 ** ((m['gain_i_db'] - m['lna_db']) / 20)           # BB / LNA-out amplitude
        s_rf = r['onoise'] ** 2                                      # V^2/Hz at the arm's LNA output
        n_fe = 2 * s_rf * gc ** 2
        d = rxc.BUILD / bb_tag / cc
        nz = np.loadtxt(d / 'noise.txt')
        f, inn = nz[:, 0], nz[:, 3]
        n_bb_f = np.maximum(inn ** 2 - 4 * KT * 500.0, 0)
        band = (f >= BAND[0]) & (f <= BAND[1])
        n_bb = float(np.trapezoid(n_bb_f[band], f[band]) / (BAND[1] - BAND[0]))
        n_sw = 4 * KT * 2 * RON
        f_rf = 10 ** (r['nf'] / 10)
        f_tot = f_rf * (1 + (n_bb + n_sw) / n_fe)
        ac = np.loadtxt(d / 'ac.txt')                                # f, |G through stage L|, ., |G bb| ...
        fa, g = ac[:, 0], ac[:, 1]
        nf_interp = np.interp(fa, f, n_bb_f, left=n_bb_f[0], right=n_bb_f[-1])
        rms = float(np.sqrt(np.trapezoid((n_fe + n_sw + nf_interp) * g ** 2, fa)))
        rows.append(dict(corner=c, n_off=r['n_off'], rroute=r['rroute'], nf_rf=r['nf'],
                         nf_total=float(10 * np.log10(f_tot)), bb_add_db=float(10 * np.log10(f_tot / f_rf)),
                         gc_db=float(20 * np.log10(gc)), n_fe_nv=float(np.sqrt(n_fe) * 1e9),
                         n_bb_nv=float(np.sqrt(n_bb) * 1e9), noise_cmp_mv=rms * 1e3,
                         hyst_mv=hy.get(cc, float('nan')) * 1e3, hyst_ratio=hy.get(cc, float('nan')) / rms))
    rows.sort(key=lambda x: (x['corner'], x['n_off'], x['rroute']))
    res = rxc.RES / 'budget.json' if out is None else Path(out)
    res.write_text(json.dumps(rows, indent=1))
    md = ['| corner | n_off | Rroute (Ω) | NF pin+LNA (dB) | NF to the comparator (dB) | BB adds (dB) | '
          'noise at the comparator (mV rms) | hysteresis (mV) | hyst / noise |', '|' + '---|' * 9]
    for x in rows:
        md.append(f"| {x['corner']} | {x['n_off']} | {x['rroute']:.0f} | {x['nf_rf']:.2f} | {x['nf_total']:.2f} | "
                  f"{x['bb_add_db']:.2f} | {x['noise_cmp_mv']:.0f} | {x['hyst_mv']:.1f} | {x['hyst_ratio']:.2f} |")
    res.with_suffix('.md').write_text('\n'.join(md) + '\n')
    print('\n'.join(md))
    return rows


if __name__ == '__main__':
    main(*sys.argv[1:])
