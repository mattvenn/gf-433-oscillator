#!/usr/bin/env python3
"""Collect <out>/*/result.json from sim/pn/isf.py into a markdown table (stdout and <out>/summary.md)."""
import json, sys
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else "build/pn")
rows = []
for f in sorted(out.glob("*/result.json")):
    r = json.loads(f.read_text())
    a, L, F = r["A"], r["L"], r["FOM"]
    rows.append(f"| {r['variant']} | {r['corner']} | {r['temp']:g} | {a['f0']/1e6:.1f} | {a['P']*1e3:.2f} | "
                f"{L['10000']['L']:.1f} | {L['100000']['L']:.1f} | {L['1e+06']['L']:.1f} | {L['1e+07']['L']:.1f} | "
                f"{F['1e+06']:.1f} | {a['K_vdd']/1e6:.1f} | {a['K_bias']/1e6:.1f} | "
                f"{max((k for k in L['1e+06'] if k != 'L' and L['1e+06'][k] is not None), key=lambda k: L['1e+06'][k])} |")
head = ("| variant | corner | T C | f0 MHz | P mW | L(10k) | L(100k) | L(1M) | L(10M) dBc/Hz | FOM@1M | Kvdd MHz/V | "
        "Kbias MHz/V | dominant @1M |\n|" + "---|" * 13 + "\n")
text = head + "\n".join(rows) + "\n"
print(text)
(out / "summary.md").write_text(text)
