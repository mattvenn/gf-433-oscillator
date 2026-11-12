#!/usr/bin/env python3
"""
Phase A tables (markdown) from the bench outputs in build/rx/ -> sim/rx/results/<block>/*.json and summary.md.

    python3 sim/rx/rx_summary.py
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rxc  # noqa: E402

B = rxc.BUILD
R = rxc.RES


def jl(p):
    return json.loads(Path(p).read_text())


def lo_table():
    d = jl(B / 'lo_ring' / 'rows.json')
    rows = d['rows']
    by = {(r['corner'], r['code'], r['case']): r for r in rows}
    out = ['| corner | code | f, no RX (MHz) | f, Q tap on a2 (MHz) | shift | I/Q phase a2 / a3 (deg) | duty lo_i / lob_i / lo_q | '
           'rx_en 1 -> 0, Q tap gated (kHz) | rx_en 1 -> 0, Q tap kept on (kHz) | LO path current on / off (mA) |',
           '|' + '---|' * 10]
    for c in ('tt', 'ss', 'ff', 'sf', 'fs'):
        for code in sorted({r['code'] for r in rows if r['corner'] == c}):
            b, a2, a3 = by[(c, code, 'base')], by[(c, code, 'a2')], by[(c, code, 'a3')]
            off, k = by[(c, code, 'a2off')], by[(c, code, 'a2koff')]
            bad = any(x['bad'] for x in (b, a2, a3, off, k))
            out.append(f"| {c} | {code} | {b['f'] / 1e6:.2f} | {a2['f'] / 1e6:.2f} | {(a2['f'] / b['f'] - 1) * 100:+.2f} % | "
                       f"{a2['iq_phase']:+.1f} / {a3['iq_phase']:+.1f} | {a2['duty_lo_i'] * 100:.1f} / "
                       f"{a2['duty_lob_i'] * 100:.1f} / {a2['duty_lo_q'] * 100:.1f} % | {(off['f'] - a2['f']) / 1e3:+.0f} | "
                       f"{(k['f'] - a2['f']) / 1e3:+.2f} | {a2['i_rx'] * 1e3:.2f} / {k['i_rx'] * 1e3:.2f} |"
                       + (' op failed' if bad else ''))
    (R / 'lo').mkdir(parents=True, exist_ok=True)
    shutil.copy(B / 'lo_ring' / 'rows.json', R / 'lo' / 'ring.json')
    return '\n'.join(out)


def lna_table():
    rows = jl(B / 'lna_final' / 'rows.json')['rows']
    out = ['| corner | n_off | Rroute (Ω) | I (mA) | gain, EMF to one arm (dB) | NF (dB) | gain at 3 fLO (dB) | VDD to output, CM (dB) |',
           '|' + '---|' * 8]
    for r in sorted(rows, key=lambda r: (['tt', 'ss', 'ff', 'sf', 'fs'].index(r['corner']), r['n_off'], r['rroute'])):
        out.append(f"| {r['corner']} | {r['n_off']} | {r['rroute']:.0f} | {r['idd'] * 1e3:.2f} | {r['av_db']:.1f} | "
                   f"{r['nf']:.2f} | {r['av3_db']:.1f} | {r['psrr_cm_db']:.1f} |")
    shutil.copy(B / 'lna_final' / 'rows.json', R / 'lna' / 'final.json')
    return '\n'.join(out)


def mix_table():
    out = ['| corner | LO | gain, EMF to baseband I / Q (dB) | of which the LNA (dB) | baseband I/Q phase (deg) | '
           'LO at the baseband, diff (dBV) | 2 fLO at the baseband, CM (dBV) |', '|' + '---|' * 7]
    for tag, lo in (('mix_a3', 'ideal'), ('mix_a3b', 'buffers')):
        p = B / tag / 'rows.json'
        if not p.exists():
            continue
        rows = jl(p)['rows']
        for r in rows:
            if r['case'] != 'iq':
                continue
            out.append(f"| {r['corner']} | {lo} | {r['gain_i_db']:.1f} / {r['gain_q_db']:.1f} | {r['lna_db']:.1f} | "
                       f"{r['iq_phase']:.1f} | {r['lo_bb_i_dbv']:.0f} | {r['lo_bb_i_cm_dbv']:.0f} |")
        shutil.copy(p, R / 'mix' / f'{lo}.json')
    return '\n'.join(out)


def bb_table():
    rows = jl(B / 'bb_final' / 'rows.json')['rows']
    hy = {r['corner']: r for r in jl(B / 'hyst_final' / 'rows.json')['rows']}
    out = ['| corner | rx_bb gain (dB) | + limiter stage (dB) | -3 dB low / high (kHz) | input noise 10 kHz / 100 kHz (nV/√Hz) | '
           'current per arm (µA) | comparator hysteresis (mV) |', '|' + '---|' * 7]
    for r in sorted(rows, key=lambda r: ['tt', 'ss', 'ff', 'sf', 'fs'].index(r['corner'])):
        h = hy[r['corner']]
        out.append(f"| {r['corner']} | {r['gbb100k_db']:.1f} | {r['g100k_db']:.1f} | {r['flo'] / 1e3:.1f} / {r['fhi'] / 1e3:.0f} | "
                   f"{r['in_10k'] * 1e9:.0f} / {r['in_100k'] * 1e9:.1f} | {r['idd'] * 1e6:.0f} | ±{(h['vup2'] - h['vdn2']) / 2 * 1e3:.1f} |")
    for t, sub in (('bb_final', 'bb'), ('hyst_final', 'lim'), ('bb_offs', 'bb')):
        shutil.copy(B / t / 'rows.json', R / sub / f'{t}.json')
    return '\n'.join(out)


def main():
    parts = ['## LO taps (A1)', lo_table(), '## LNA (A2)', lna_table(), '## Mixers (A3)', mix_table(),
             '## Baseband + limiter (A4)', bb_table()]
    if (R / 'budget.md').exists():
        parts += ['## Noise budget', (R / 'budget.md').read_text()]
    (R / 'summary.md').write_text('\n\n'.join(parts) + '\n')
    print('\n\n'.join(parts))


if __name__ == '__main__':
    main()
