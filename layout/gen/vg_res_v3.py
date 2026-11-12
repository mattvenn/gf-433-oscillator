#!/usr/bin/env python3
"""vg resistance from an RC extraction (layout/pex/ring_core_v3_rc.spice): the effective R from each inverter's
NMOS source terminal to (a) the decap gates (all decap finger gate terminals shorted together), (b) the DAC
(all DAC drain terminals shorted), (c) the vg pin, by nodal analysis of the extracted R network of net vg.
    python3 layout/gen/vg_res_v3.py [layout/pex/ring_core_v3_rc.spice]"""
import re, sys
import numpy as np

f = sys.argv[1] if len(sys.argv) > 1 else "layout/pex/ring_core_v3_rc.spice"
lines, R = [], []
for ln in open(f):
    if ln.startswith("+") and lines:
        lines[-1] += " " + ln[1:].strip()
    else:
        lines.append(ln.strip())
inv, decap, dac = {}, [], []
for ln in lines:
    t = ln.split()
    if not t:
        continue
    if t[0].startswith("R") and t[1].split(".")[0] == "vg" and t[2].split(".")[0] == "vg":
        R.append((t[1], t[2], float(t[3])))
    if t[0].startswith("X") and ("nfet_03v3" in t or "pfet_03v3" in t):
        d, g, s = t[1], t[2], t[3]
        w = re.search(r"\bw=(\S+)u", ln).group(1)
        l = re.search(r"\bl=(\S+)u", ln).group(1)
        if "pfet_03v3" in t:                     # the decap: PMOS gate cap to VDD since 2026-11-12 (gate vg)
            if g.startswith("vg"):
                decap.append(g)
        elif w == "2" and g.startswith("a") and "vg" in (s.split(".")[0], d.split(".")[0]):
            inv[f"N{(int(g[1]))}"] = s if s.startswith("vg") else d   # N{i}: gate a{i}, source vg (magic may swap S/D)
        elif l == "4" and g.startswith("vg"):  # the NMOS decap to VSS (layouts before 2026-11-12)
            decap.append(g)
        elif float(l) > 5 and d.startswith("vg"):
            dac.append(d)
        elif float(l) > 5 and s.startswith("vg"):
            dac.append(s)
nodes = sorted({n for a, b, _ in R for n in (a, b)} | set(inv.values()) | set(decap) | set(dac) | {"vg"})
ix = {n: i for i, n in enumerate(nodes)}
G = np.zeros((len(nodes), len(nodes)))
for a, b, r in R:
    i, j = ix[a], ix[b]
    g = 1 / max(r, 1e-6)
    G[i, i] += g; G[j, j] += g; G[i, j] -= g; G[j, i] -= g


def reff(src, sinks):
    """R from node src to the set sinks (shorted, grounded)."""
    keep = [k for k in range(len(nodes)) if nodes[k] not in sinks]
    Gk = G[np.ix_(keep, keep)] + np.eye(len(keep)) * 1e-12
    I = np.zeros(len(keep)); I[keep.index(ix[src])] = 1.0
    return np.linalg.solve(Gk, I)[keep.index(ix[src])]


print(f"{f}: {len(R)} vg resistors, {len(decap)} decap gates, {len(dac)} DAC terminals")
print("| inverter | R to decap (ohm) | R to DAC (ohm) | R to vg pin (ohm) |\n|---|---|---|---|")
for k in sorted(inv):
    s = inv[k]
    print(f"| {k} | {reff(s, set(decap)):.1f} | {reff(s, set(dac)):.1f} | {reff(s, {'vg'}):.1f} |")
srcs = [inv[k] for k in sorted(inv)]
print("max R between two inverter sources:",
      f"{max(reff(a, {b}) for a in srcs for b in srcs if a != b):.2f} ohm")
