#!/usr/bin/env python3
"""Silicon / simulation factor table from build/silicon_factor/results.csv (markdown to stdout).

factor = f_silicon / f_sim. Silicon: chip 1 (2026-11-09, bench/2026-11-09/), inv4x5 from chip 2 (unconfirmed).
Chip 2 values are listed too: it runs about 2 % slower than chip 1.
"""
import csv, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tb import F_MEAS, CFGS  # noqa: E402

F_CHIP2 = {"t3": 216.0, "inv1x5": 311.6, "inv4x5": 206.5}
rows = list(csv.DictReader(open(Path(__file__).resolve().parents[2] / "build/silicon_factor/results.csv")))
corners = [c for c in ("typical", "ss", "ff", "sf", "fs") if any(r["corner"] == c for r in rows)]
sim = {(r["cfg"], r["corner"], r["mode"]): r for r in rows}


def f(cfg, corner, mode="c"):
    r = sim.get((cfg, corner, mode))
    return float(r["f_Hz"]) / 1e6 if r and r["status"] == "ok" else None


print("# GF silicon factor: tt_um_algofoogle_vgaringosc, extracted layout vs ttgf0p2 silicon\n")
print("f_sim in MHz (C-extracted, 27 °C, 3.3 V). factor = f_silicon(chip 1) / f_sim.\n")
hdr = "| ring | stages | silicon chip 1 | chip 2 | " + " | ".join(f"sim {c}" for c in corners) + \
      " | factor vs typical | silicon inside sim corners? |"
print(hdr); print("|" + "---|" * (hdr.count("|") - 1))
for cfg in CFGS:
    fm = F_MEAS[cfg]; fs = [f(cfg, c) for c in corners]
    ft = f(cfg, "typical")
    ok = [x for x in fs if x]
    inside = ("yes" if min(ok) <= fm <= max(ok) else "no") if ok else "–"
    fac = f"{fm / ft:.3f}" if ft else "–"
    note = " (unconfirmed)" if cfg == "inv4x5" else ""
    print(f"| {cfg}{note} | {CFGS[cfg][2]} | {fm:.1f} | {F_CHIP2.get(cfg, '–')} | "
          + " | ".join(f"{x:.1f}" if x else "–" for x in fs) + f" | {fac} | {inside} |")
print("\n## rc check (typical)\n")
for cfg in CFGS:
    c, rc = f(cfg, "typical"), f(cfg, "typical", "rc")
    if rc:
        print(f"- {cfg}: c {c:.1f} MHz, rc {rc:.1f} MHz ({(rc / c - 1) * 100:+.1f} %); "
              "rc includes magic's port double count (docs/rc_extraction_fix.md), so treat as a lower bound on f")
bad = [r for r in rows if r["status"] != "ok"]
if bad:
    print("\n## Non-ok runs\n")
    for r in bad: print(f"- {r['cfg']} {r['corner']} {r['mode']}: {r['status']}")
