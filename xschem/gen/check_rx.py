#!/usr/bin/env python3
"""
Receiver sheets vs the simulated receiver (sim/rx/rx_top.py block()): run from the repo root.

  for each cell: netlist the sheet headless, then
    - netgen (the sheet vs the sim subckt, with the sim's own subcells as the reference hierarchy),
    - a device-by-device size diff (netgen black-boxes the PDK resistors).
  mutations (each must fail): rx_lna's M1 W -10 % (netgen and sizes); rx_mix's S1n gate lo -> lob (netgen);
  rx_bb's coupling resistor Mr L +20 % (sizes); rx_top's xlo qenb VSS -> enb (netgen).

    python3 xschem/gen/check_rx.py [cells...]
Called by xschem/gen/check.py (step 3e). Outputs: build/xsch/rx_* (netlists, reports).
"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check as CK  # noqa: E402  (netgen, devices, diff, sh, OUT, REPO)

REPO = Path(CK.REPO)
OUT = CK.OUT
CELLS = ['rx_bias', 'rx_lna2', 'rx_lna', 'rx_mix', 'rx_lobuf', 'rx_lsq', 'rx_lo', 'rx_bb', 'rx_lim', 'rx_top']
# xschem subcells that come from existing sheets (the reference has their devices flat inside rx_lsq)
SHARED = ('ls_ac', 'tspc_t1')


def ref_netlist():
    txt = subprocess.run([sys.executable, str(REPO / 'sim' / 'rx' / 'rx_top.py')], capture_output=True, text=True,
                         check=True).stdout
    (OUT / 'ref_rx.spice').write_text(txt)
    return txt


def cell_only(text, cell):
    """The reference netlist for one cell: its .subckt and every subckt it instantiates (all of them, simplest)."""
    return text


SUBS = ('rx_bias', 'rx_lna2', 'rx_lna', 'rx_mix', 'rx_lobuf', 'rx_lsq', 'rx_lo', 'rx_bb', 'rx_lim', 'rx_top',
        'ls_ac', 'tspc_t1')


def devices(path, cell):
    """Device sizes of `cell` flattened through its subcells (xschem netlists list each subckt once; the counts
    are multiplied by how often a subcell is instantiated)."""
    from collections import Counter
    text = re.sub(r'\n\+', ' ', Path(path).read_text())
    cells, cur = {}, None
    for ln in text.splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0].lower() == '.subckt':
            cur = t[1]
            cells[cur] = []
        elif t[0].lower() == '.ends':
            cur = None
        elif cur and t[0][0] in 'Xx':
            cells[cur].append(t)

    def flat(c, mult, acc):
        for t in cells.get(c, []):
            kv = {k.lower(): v for k, v in (x.split('=', 1) for x in t if '=' in x)}
            pos = [x for x in t[1:] if '=' not in x]
            if pos[-1] in cells:
                flat(pos[-1], mult, acc)
            elif 'fet' in pos[-1]:
                num = lambda v: round(float(re.sub(r'u$', 'e-6', v.lower())) if not v.lower().endswith('u') else float(v[:-1]) * 1e-6, 15)
                acc[(pos[-1], num(kv['w']), num(kv['l']), int(kv.get('m', 1)))] += mult
            else:
                acc[(pos[-1], round(float(kv['r_width']), 12), round(float(kv['r_length']), 12))] += mult
        return acc
    return flat(cell, 1, Counter())


def diff(a, b, cell):
    da, db = devices(a, cell), devices(b, cell)
    return da == db, [f'{k}: {da.get(k, 0)} vs {db.get(k, 0)}' for k in sorted(set(da) | set(db), key=str)
                      if da.get(k, 0) != db.get(k, 0)], sum(da.values())


def netlist(cells, src='xschem', out=None):
    out = out or OUT
    rel = Path(out).relative_to(REPO)
    return CK.sh(f'xschem/gen/netlist.sh {src} {rel} {" ".join(cells)}')


def main(cells=None):
    cells = cells or CELLS
    OUT.mkdir(parents=True, exist_ok=True)
    ref_netlist()
    print(netlist(cells).strip())
    ok = True
    for c in cells:
        n_ok, rep = CK.netgen(f'{c}.spice', c, 'ref_rx.spice', c, f'lvs_{c}')
        d_ok, dd, n = diff(OUT / f'{c}.spice', OUT / 'ref_rx.spice', c)
        CK.log(f'{c} vs sim/rx: netgen {"PASS" if n_ok else "FAIL"} [{rep}]; device sizes {"PASS" if d_ok else "FAIL"} '
               f'({n} devices){" " + "; ".join(dd[:6]) if dd else ""}')
        ok &= n_ok and d_ok
    if cells == CELLS:
        # mutations
        t = (OUT / 'rx_lna.spice').read_text()
        m, k = re.subn(r'(?m)^(XM1 .*?W=)([\d.]+)u', lambda x: f'{x.group(1)}{float(x.group(2)) * 0.9:g}u', t, count=1)
        (OUT / 'mut_rx_lna.spice').write_text(m)
        a, ra = CK.netgen('mut_rx_lna.spice', 'rx_lna', 'ref_rx.spice', 'rx_lna', 'lvs_mut_rx_lna')
        b, rb, _ = diff(OUT / 'mut_rx_lna.spice', OUT / 'ref_rx.spice', 'rx_lna')
        CK.log(f'mutation rx_lna M1 W -10 %: netgen {"FAIL (expected)" if not a else "PASS (BAD)"}; sizes '
               f'{"FAIL (expected)" if not b else "PASS (BAD)"}')
        ok &= k == 1 and not a and not b
        t = (OUT / 'rx_mix.spice').read_text()
        m, k = re.subn(r'(?m)^(XS1n \S+ )lo ', r'\1lob ', t, count=1)
        (OUT / 'mut_rx_mix.spice').write_text(m)
        a, ra = CK.netgen('mut_rx_mix.spice', 'rx_mix', 'ref_rx.spice', 'rx_mix', 'lvs_mut_rx_mix')
        CK.log(f'mutation rx_mix S1n gate lo -> lob: netgen {"FAIL (expected)" if not a else "PASS (BAD)"}')
        ok &= k == 1 and not a
        t = (OUT / 'rx_bb.spice').read_text()
        m, k = re.subn(r'(?m)^(XRp2ar .*?L=)([\d.]+)u', lambda x: f'{x.group(1)}{float(x.group(2)) * 1.2:g}u', t, count=1)
        (OUT / 'mut_rx_bb.spice').write_text(m)
        b, rb, _ = diff(OUT / 'mut_rx_bb.spice', OUT / 'ref_rx.spice', 'rx_bb')
        CK.log(f'mutation rx_bb Rp2ar L +20 %: sizes {"FAIL (expected)" if not b else "PASS (BAD)"}')
        ok &= k == 1 and not b
        t = (OUT / 'rx_top.spice').read_text()
        m, k = re.subn(r'(?m)^(xlo VDD VSS \S+ \S+ \S+ )VSS ', r'\1enb ', t, count=1)
        (OUT / 'mut_rx_top.spice').write_text(m)
        a, ra = CK.netgen('mut_rx_top.spice', 'rx_top', 'ref_rx.spice', 'rx_top', 'lvs_mut_rx_top')
        CK.log(f'mutation rx_top qenb VSS -> enb: netgen {"FAIL (expected)" if not a else "PASS (BAD)"}')
        ok &= k == 1 and not a
    CK.log('CHECK_RX ' + ('OK' if ok else 'FAIL'))
    return ok


if __name__ == '__main__':
    main(sys.argv[1:] or None)
