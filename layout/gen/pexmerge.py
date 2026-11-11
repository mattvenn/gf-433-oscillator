#!/usr/bin/env python3
"""Merge parallel devices of a C-only extraction into one instance with m (exact), for fast transients.

    python3 layout/gen/pexmerge.py <c.spice> <out.spice>

In a C-only extraction (pex_*.sh c) every net is one node, so devices with the same model, W, L and the same
D / G / S / B nodes are exactly in parallel. Each group becomes one instance with m = the group size; the
junction areas and perimeters (ad / as / pd / ps, linear in the junction C) are summed over the group and divided
by m, because ngspice multiplies them by m. Source and drain are not swapped when grouping (a reversed copy stays a
separate instance). Capacitors and the rest of the file pass through. Used for the medium DAC (1390 unit
fingers -> layout/pex/mdac_cm.spice), whose unmerged transients are about 100x slower.
"""
import re
import sys
from collections import OrderedDict

UNIT = {"": 1, "a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3}


def num(v):
    m = re.fullmatch(r"([-\d.eE+]+)([afpnum]?)", v)
    return float(m.group(1)) * UNIT[m.group(2)]


def main(src, dst):
    lines = open(src).read().splitlines()
    groups = OrderedDict()
    out, first = [], None
    for ln in lines:
        t = ln.split()
        if t and t[0].upper().startswith("X") and len(t) > 6 and "=" in ln:
            d, g, s, b, model = t[1:6]
            p = dict(kv.split("=") for kv in t[6:])
            key = (d, g, s, b, model, p["w"], p["l"])
            grp = groups.setdefault(key, dict(n=0, ad=0.0, as_=0.0, pd=0.0, ps=0.0))
            grp["n"] += int(float(p.get("m", "1")))
            for k, kk in (("ad", "ad"), ("as", "as_"), ("pd", "pd"), ("ps", "ps")):
                grp[kk] += num(p.get(k, "0")) * int(float(p.get("m", "1")))
            if first is None:
                first = len(out)
                out.append(None)
            continue
        out.append(ln)
    dev = []
    for i, ((d, g, s, b, model, w, l), q) in enumerate(groups.items()):
        n = q["n"]
        dev.append(f"XM{i} {d} {g} {s} {b} {model} w={w} l={l} m={n} ad={q['ad']/n:.6g} as={q['as_']/n:.6g} "
                   f"pd={q['pd']/n:.6g} ps={q['ps']/n:.6g}")
    out[first:first + 1] = dev
    out.insert(1, f"* {sum(q['n'] for q in groups.values())} devices merged into {len(groups)} instances "
                  f"(layout/gen/pexmerge.py, from {src.split('/')[-1]})")
    open(dst, "w").write("\n".join(out) + "\n")
    print(f"{dst}: {sum(q['n'] for q in groups.values())} devices -> {len(groups)} instances")


if __name__ == "__main__":
    main(*sys.argv[1:3])
