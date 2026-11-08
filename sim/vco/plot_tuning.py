#!/usr/bin/env python3
"""How the current-fed VCO is tuned: coarse code + fine vctrl -> f (tt 27 C, VDD 3.3 V, schematic, cw = 3 fF).

  A: f vs coarse code, band = vctrl 0 -> 3.3 V (from sim/results/2026-11-08/cfed/map.csv)
  B: f vs vctrl for the codes around 433.92 MHz (dense sweep, build/vco/topo_fine_tt/sweep.json)
  C: the tuning recipe: coarse search, then fine servo, then FSK as +-deviation on vctrl
Note: the map (100-200 ns window) reads about 1.3 % high against a fully settled ring (docs/cfed_startup_results.md),
and the extracted layout is 0.86-0.88 x lower again; the shape and the way the controls combine are what this shows.
Writes docs/img/tuning_*.png.
"""
import csv, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs/img"
INK, MUTED, GRID = "#2b2b2b", "#6b6b66", "#e4e3de"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7a5cd6", "#d64545"]
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "legend.frameon": False, "figure.dpi": 130})
F0 = 433.92

rows = [r for r in csv.DictReader(open(REPO / "sim/results/2026-11-08/cfed/map.csv"))
        if r["corner"] == "typical" and float(r["temp"]) == 27 and float(r["vdd"]) == 3.3]
mp = {}
for r in rows:
    mp[(int(r["code"]), round(float(r["vctrl"]), 2))] = float(r["f"]) / 1e6
codes = sorted({k[0] for k in mp})
lo = np.array([mp[(c, 0.0)] for c in codes]); mid = np.array([mp[(c, 1.65)] for c in codes])
hi = np.array([mp[(c, 3.3)] for c in codes])

fine = json.load(open(REPO / "build/vco/topo_fine_tt/sweep.json"))["rows"]
fine = [r for r in fine if r["f"]]
fcodes = sorted({r["code"] for r in fine})

fig, (a, b) = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw=dict(width_ratios=[1.15, 1]))
# A: coarse staircase with the fine band
for c, l, m, h in zip(codes, lo, mid, hi):
    a.plot([c - 0.4, c + 0.4], [l, l], color=C[0], lw=1)
    a.plot([c - 0.4, c + 0.4], [h, h], color=C[0], lw=1)
    a.fill_between([c - 0.4, c + 0.4], [l, l], [h, h], color=C[0], alpha=0.18, lw=0)
    a.plot([c - 0.4, c + 0.4], [m, m], color=INK, lw=1.6)
a.axhline(F0, color=C[6], lw=1.2); a.text(0, F0 + 12, "433.92 MHz", color=C[6], fontsize=9)
a.set_xlabel("coarse code (5 bits: base 6 + code units of DAC current)")
a.set_ylabel("f (MHz)")
a.set_title("A. Coarse code sets the band; fine vctrl moves within it\n"
            "black = vctrl 1.65 V, shaded = vctrl 0 → 3.3 V", loc="left", fontsize=10)
a.set_xlim(-1, 32)
ins = a.inset_axes([0.55, 0.06, 0.42, 0.42])
for c in range(6, 13):
    i = codes.index(c)
    ins.fill_between([c - 0.4, c + 0.4], [lo[i]] * 2, [hi[i]] * 2, color=C[0], alpha=0.25, lw=0)
    ins.plot([c - 0.4, c + 0.4], [mid[i]] * 2, color=INK, lw=1.4)
ins.axhline(F0, color=C[6], lw=1)
ins.set_xticks(range(6, 13)); ins.tick_params(labelsize=7); ins.set_title("codes 6–12: bands overlap (no gaps)", fontsize=8)

# B: fine tuning curves
for j, c in enumerate(fcodes):
    rr = sorted((r["vctrl"], r["f"] / 1e6) for r in fine if r["code"] == c)
    x, y = zip(*rr)
    b.plot(x, y, color=C[j % len(C)], lw=2, label=f"code {c}")
    b.text(x[-1] + 0.04, y[-1], f"{c}", color=C[j % len(C)], fontsize=9, va="center")
b.axhline(F0, color=C[6], lw=1.2)
# show slope at 1.65 for the code nearest 433.92 at mid
best = min(fcodes, key=lambda c: min(abs(f / 1e6 - F0) for r in fine if r["code"] == c for f in [r["f"]]))
rr = sorted((r["vctrl"], r["f"] / 1e6) for r in fine if r["code"] == best)
x, y = map(np.array, zip(*rr))
k = np.gradient(y, x)
i0 = int(np.argmin(abs(y - F0)))
b.plot(x[i0], y[i0], "o", color=INK, ms=6)
b.annotate(f"code {best}: 433.92 MHz at vctrl ≈ {x[i0]:.2f} V\nslope there ≈ {k[i0]:.0f} MHz/V (Kvco)",
           xy=(x[i0], y[i0]), xytext=(0.15, F0 + 45), fontsize=9, arrowprops=dict(arrowstyle="->", color=MUTED))
b.set_xlabel("fine control vctrl (V)"); b.set_ylabel("f (MHz)")
b.set_xlim(0, 3.55)
b.set_title("B. Fine control: f vs vctrl for the codes around 433.92 MHz\n"
            "each curve overlaps its neighbours, so every frequency is reachable", loc="left", fontsize=10)
fig.suptitle("Tuning the current-fed VCO (tt 27 °C, VDD 3.3 V, schematic)", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(OUT / "tuning_controls.png"); plt.close(fig)

# C: the recipe in time (illustrative, using the curves above)
fig, ax = plt.subplots(3, 1, figsize=(11, 6.4), sharex=True, gridspec_kw=dict(height_ratios=[1, 1, 1.4]))
t = np.arange(0, 40)
# binary search on code with vctrl at mid, then fine servo, then FSK
seq = []
lo_c, hi_c = 0, 31
code_t, vc_t, f_t, phase = [], [], [], []
fn = lambda c, v: np.interp(v, *zip(*sorted((r["vctrl"], r["f"] / 1e6) for r in fine if r["code"] == c))) \
    if c in fcodes else mid[codes.index(c)] + (v - 1.65) * (hi[codes.index(c)] - lo[codes.index(c)]) / 3.3
v = 1.65
for step in range(5):                       # binary search, 5 bits
    c = (lo_c + hi_c) // 2
    f = fn(c, v)
    code_t.append(c); vc_t.append(v); f_t.append(f); phase.append("coarse search")
    if f < F0: lo_c = c + 1
    else: hi_c = c
c = min(range(32), key=lambda cc: abs(fn(cc, 1.65) - F0))
for step in range(12):                      # fine servo: integrate the error
    f = fn(c, v)
    code_t.append(c); vc_t.append(v); f_t.append(f); phase.append("fine servo")
    v = float(np.clip(v - (f - F0) / 60.0, 0, 3.3))
k0 = (fn(c, min(v + 0.05, 3.3)) - fn(c, max(v - 0.05, 0))) / 0.1
dv = 0.05 / k0                              # +-50 kHz deviation in V
bitsq = [1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1]
for bt in bitsq:
    vv = v + (dv if bt else -dv)
    code_t.append(c); vc_t.append(vv); f_t.append(fn(c, vv)); phase.append("FSK")
n = len(code_t); t = np.arange(n)
ax[0].step(t, code_t, where="post", color=C[0], lw=2); ax[0].set_ylabel("coarse\ncode")
ax[1].step(t, vc_t, where="post", color=C[1], lw=2); ax[1].set_ylabel("vctrl (V)")
ax[2].step(t, f_t, where="post", color=INK, lw=2); ax[2].axhline(F0, color=C[6], lw=1)
ax[2].set_ylabel("f (MHz)"); ax[2].set_xlabel("RP2350 update step (each: count the ÷64 output for ~1 ms, adjust)")
ins = ax[2].inset_axes([0.62, 0.45, 0.36, 0.5])
s0 = phase.index("FSK")
ins.step(t[s0:], (np.array(f_t[s0:]) - F0) * 1e3, where="post", color=INK, lw=1.4)
ins.axhline(50, color=MUTED, ls=":", lw=0.8); ins.axhline(-50, color=MUTED, ls=":", lw=0.8)
ins.set_title("FSK zoom: ±50 kHz around 433.92 MHz", fontsize=8); ins.tick_params(labelsize=7); ins.set_ylabel("kHz", fontsize=7)
for a_ in ax:
    for name, col in (("coarse search", "#cde2fb"), ("fine servo", "#fde3cf"), ("FSK", "#d3f0e3")):
        idx = [i for i, p in enumerate(phase) if p == name]
        a_.axvspan(idx[0], idx[-1] + 1, color=col, alpha=0.5, lw=0)
for name in ("coarse search", "fine servo", "FSK"):
    idx = [i for i, p in enumerate(phase) if p == name]
    ax[0].text((idx[0] + idx[-1] + 1) / 2, 31, name, ha="center", va="top", fontsize=9, color=MUTED)
ax[0].set_ylim(-1, 33)
fig.suptitle(f"How the RP2350 tunes it: binary-search the code, servo vctrl onto 433.92 MHz, "
             f"then key FSK on vctrl (±{dv*1e3:.1f} mV for ±50 kHz)", x=0.01, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "tuning_recipe.png"); plt.close(fig)
print("wrote", OUT / "tuning_controls.png", OUT / "tuning_recipe.png", f"Kvco at op ≈ {k0:.0f} MHz/V")
