#!/usr/bin/env python3
"""Print a markdown table of the TX harmonic runs from a tb_tx_drv results.jsonl (last record per tag).

    python3 sim/tx/harm_table.py build/tx_harm/A/results.jsonl [--filter SUBSTR] [--sort key]
"""
import argparse
import json

COLS = [('p1_dbm', 'fund dBm', '{:+.2f}')] + [(f'h{n}_dbc', f'H{n}', '{:.1f}') for n in range(2, 8)] + [
    ('duty_p', 'duty p %', '{:.1f}'), ('duty_n', 'duty n %', '{:.1f}'), ('ph_err_deg', 'ph err °', '{:+.2f}'),
    ('tr_ps', 'tr ps', '{:.0f}'), ('tf_ps', 'tf ps', '{:.0f}'),
    ('i_avg_ma', 'I avg mA', '{:.2f}'), ('i_rms_ma', 'I rms mA', '{:.2f}'), ('i_pk_ma', 'I pk mA', '{:.1f}'),
    ('vdd_ripple_mv', 'VDD ripple mV', '{:.0f}'), ('i_pin_ma', 'I pin mA rms', '{:.2f}'), ('eff_pct', 'eff %', '{:.1f}')]


def load(path):
    recs = {}
    for ln in open(path):
        r = json.loads(ln)
        recs[r['tag']] = r
    return list(recs.values())


def label(r):
    s = dict(r['sizes'])
    s.pop('shape', None)
    p = [r['corner']] + [f'{k}={v:g}' for k, v in sorted(s.items())] + [f"r{r['rroute']:g}", f"n{r['noff']:g}"]
    if r.get('temp', 27) != 27:
        p.append(f"{r['temp']:g}°C")
    if r.get('vdd', 3.3) != 3.3:
        p.append(f"{r['vdd']:g} V")
    if r.get('off'):
        p.append('OFF')
    return ' '.join(p)


def table(recs, cols=COLS):
    out = ['| run | ' + ' | '.join(c[1] for c in cols) + ' | warn |', '|' + '---|' * (len(cols) + 2)]
    for r in recs:
        res = r['res'] or {}
        cells = [(f.format(res[k]) if k in res else '') for k, _, f in cols]
        out.append(f'| {label(r)} | ' + ' | '.join(cells) + ' | ' + ('; '.join(r['warn']) or '') + ' |')
    return '\n'.join(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('jsonl')
    ap.add_argument('--filter', default='')
    a = ap.parse_args()
    print(table([r for r in load(a.jsonl) if a.filter in r['tag']]))
