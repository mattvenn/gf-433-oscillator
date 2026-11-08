#!/usr/bin/env python3
"""Per-ring-node C table from a C-only extraction (layout/pex/*_c.spice): total, to VSS, to VDD, to other ring
nodes, to f nets, other (mostly the stage's own h node).   python3 layout/gen/ctable.py layout/pex/ring_core_v2_c.spice"""
import re, sys, collections
ring = [f"a{i}" for i in range(5)]
tab = {a: collections.Counter() for a in ring}
for ln in open(sys.argv[1]):
    t = ln.split()
    if not t or not t[0].upper().startswith("C") or len(t) < 4:
        continue
    m = re.fullmatch(r"([-+.\deE]+)([fpa]?)", t[3])
    v = float(m.group(1)) * {"f": 1, "p": 1e3, "a": 1e-3, "": 1e15}[m.group(2)]
    for x, y in ((t[1], t[2]), (t[2], t[1])):
        if x in tab:
            tab[x][y] += v
print("| node | total | to VSS | to VDD | to other ring nodes | to f | other |\n|---|---|---|---|---|---|---|")
for a in ring:
    c = tab[a]
    tot = sum(c.values())
    rn = ", ".join(f"{k} {c[k]:.2f}" for k in ring if k in c and c[k] >= 0.005)
    f = sum(v for k, v in c.items() if re.fullmatch(r"f\d", k))
    oth = tot - c["VSS"] - c["VDD"] - sum(c[k] for k in ring) - f
    print(f"| {a} | {tot:.2f} | {c['VSS']:.2f} | {c['VDD']:.2f} | {rn} | {f:.2f} | {oth:.2f} |")
