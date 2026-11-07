#!/usr/bin/env python3
"""f0 and P from a VACASK tran raw file (same windows as isf.py stage A: rising a0 crossings after 100 ns)."""
import sys, numpy as np
from rawfile import rawread
p = rawread(sys.argv[1]).get()
t, v = p["time"], p["a0"]
tw = float(sys.argv[2]) if len(sys.argv) > 2 else 100e-9
k = np.where((v[:-1] < 1.65) & (v[1:] >= 1.65))[0]
tc = t[k] + (1.65 - v[k]) * (t[k + 1] - t[k]) / (v[k + 1] - v[k])
tc = tc[tc > tw]
f0 = (len(tc) - 1) / (tc[-1] - tc[0])
m = t > tw
i = np.trapezoid(p["vdd:flow(br)"][m], t[m]) / (t[m][-1] - t[m][0])
print(f"f0 = {f0/1e6:.2f} MHz  P = {-i*3.3*1e3:.4f} mW  vbp = {np.mean(p['vbp'][m]):.5f}  edges = {len(tc)}")
