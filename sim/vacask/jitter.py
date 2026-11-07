#!/usr/bin/env python3
"""Period jitter -> white-noise phase noise from VACASK transient-noise raw files.
  c = var(t_{n+k} - t_n - k*T)/k  (timing-error diffusion, s^2/s; k=1 gives sigma_T^2 / T)
  L(df) = f0^2 * c / df^2 = f0^3 * sigma_T^2 / df^2   (Demir 2000, white noise, df >> corner of the Lorentzian)
Also a direct estimate: S_phi from the PSD of the edge-time error x_n = t_n - n*T (Welch), L = S_phi/2.
Usage: python3 jitter.py <tn.raw> [...]"""
import sys, numpy as np
from rawfile import rawread
from scipy.signal import welch
for fn in sys.argv[1:]:
    p = rawread(fn).get(); t, v = p["time"], p["a0"]
    k = np.where((v[:-1] < 1.65) & (v[1:] >= 1.65))[0]
    tc = t[k] + (1.65 - v[k]) * (t[k + 1] - t[k]) / (v[k + 1] - v[k])
    tc = tc[tc > 100e-9]
    Tn = np.diff(tc); T = Tn.mean(); f0 = 1 / T; sT = Tn.std(ddof=1)
    cs = [np.var(tc[kk:] - tc[:-kk], ddof=1) / kk for kk in (1, 2, 4, 8)]
    x = tc - tc[0] - np.arange(len(tc)) * T
    x -= np.polyval(np.polyfit(np.arange(len(x)), x, 1), np.arange(len(x)))
    f, Sx = welch(x, fs=f0, nperseg=min(256, len(x)), detrend="linear")   # one-sided, s^2/Hz
    Lp = 10 * np.log10((2 * np.pi * f0) ** 2 * Sx / 2 + 1e-300)
    out = f"{fn}: N={len(Tn)} f0={f0/1e6:.2f} MHz sigma_T={sT*1e15:.1f} fs  c(k=1,2,4,8)=" + \
          ",".join(f"{c:.3e}" for c in cs)
    for df in (1e4, 1e5, 1e6, 1e7):
        out += f"\n   L_white({df:.0e}) = {10*np.log10(f0**3*sT**2/df**2):.1f} dBc/Hz"
        if f[1] <= df <= f[-1]:
            sel = (f > df / 1.5) & (f < df * 1.5)
            out += f"   PSD-direct: {10*np.log10(np.mean(10**(Lp[sel]/10))):.1f}"
    print(out)
