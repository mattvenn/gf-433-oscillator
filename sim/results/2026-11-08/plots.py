#!/usr/bin/env python3
"""Plots of the 2026-11-08 overnight results (reference sweep, cw = 2 fF tuning map). Writes build/overnight_plots/."""
import csv, json, glob, os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / "build/overnight_plots"; OUT.mkdir(parents=True, exist_ok=True)
INK, MUTED, GRID = "#2b2b2b", "#6b6b66", "#e4e3de"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "legend.frameon": False, "figure.dpi": 130})

# ---- Fig 1: reference variants ----
order = ["s1", "s2", "s4", "s7", "s10", "s14", "s1_nsn4", "s1_nsn8", "s1_nsn14", "s1_nsn8p", "s1_nsn10p",
         "s1_nsn14p", "s1_nsn20p", "s1_nsn14p_mr4"]
nice = {"s1": "as drawn (1×)", "s2": "W,L ×2", "s4": "W,L ×4", "s7": "W,L ×7", "s10": "W,L ×10", "s14": "W,L ×14",
        "s1_nsn4": "N array 4×4", "s1_nsn8": "N array 8×8", "s1_nsn14": "N array 14×14", "s1_nsn8p": "N 8×8 + P ×8",
        "s1_nsn10p": "N 10×10 + P ×10", "s1_nsn14p": "N 14×14 + P ×14", "s1_nsn20p": "N 20×20 + P ×20",
        "s1_nsn14p_mr4": "N 14×14 + P ×14 + master ×4  ★"}
rows = []
for k in order:
    d = json.load(open(HERE / f"job1/{k}.json")); b = d["bias_fm"]; fm = b["fm"]["1000-10000"]
    rows.append((k, fm, d["tc_ppm"], b["area"]["total"], b["P"]))
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 5.6), gridspec_kw=dict(width_ratios=[2.2, 1]), sharey=True)
y = np.arange(len(rows))[::-1]
terms = [("total", INK), ("vbnf", C[2]), ("vbp", C[3]), ("dev_foot", C[1])]
h = 0.2
for j, (t, col) in enumerate(terms):
    a1.barh(y + (1.5 - j) * h, [r[1][t] / 1e3 for r in rows], h * 0.9, color=col,
            label={"total": "total", "vbnf": "reference (filtered vbn)", "vbp": "master leg (vbp)",
                   "dev_foot": "ring's own foot devices"}[t])
a1.axvline(15, color=MUTED, ls="--", lw=0.9); a1.text(15.3, y[0] + 0.45, "target 15 kHz", fontsize=8, color=MUTED)
a1.axvline(117, color=MUTED, ls=":", lw=0.9); a1.text(118, y[-1] - 0.45, "yesterday's filtered cgm: 117 kHz", fontsize=8, color=MUTED)
a1.set_yticks(y, [nice[r[0]] for r in rows]); a1.set_xscale("log"); a1.set_xlim(1, 300)
a1.set_xlabel("rms FM, 1–10 kHz (kHz), tt 27 °C, cw = 2 fF")
a1.legend(loc="lower right", fontsize=8)
a1.set_title("rms frequency wander by contributor", loc="left", fontsize=10)
tc = [abs(r[2]) for r in rows]
a2.barh(y, tc, 0.6, color=[C[4] if t > 150 else C[0] for t in tc])
a2.set_xscale("log"); a2.set_xlim(0.1, 5000); a2.axvline(150, color=MUTED, ls="--", lw=0.9)
a2.set_xlabel("|tempco| at tt after n-well retune (ppm/°C)")
for yy, r in zip(y, rows):
    a2.text(0.12, yy - 0.05, f"{r[3]/1e3:.1f}k µm², {r[4]*1e3:.1f} mW", fontsize=7.5, color=INK, va="center")
a2.set_title("temperature compensation (pink = lost)", loc="left", fontsize=10)
fig.suptitle("Fig. 1. Reference sizing sweep: scaling W and L kills the tempco; arrays of the original unit keep it",
             x=0.01, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "fig1_reference.png"); plt.close(fig)

# ---- Fig 2: tuning map ----
data = list(csv.DictReader(open(HERE / "map_cw2f/map.csv")))
fig, ax = plt.subplots(figsize=(10, 5.4))
corners = ["ss", "sf", "typical", "fs", "ff"]
for ci, c in enumerate(corners):
    for t in ("0.0", "27.0", "70.0"):
        for v in ("3.15", "3.3", "3.45"):
            s = sorted((int(r["code"]), float(r["f_hz"]) / 1e6) for r in data
                       if r["deck"].startswith(f"map_{c}_") and r["temp"] == t and r["vdd"] == v and r["vctrl"] == "1.65")
            if s:
                x, f = zip(*s)
                ax.plot(x, f, color=C[ci], lw=1, alpha=0.55, label=c if (t, v) == ("27.0", "3.3") else None)
                if (c, t, v) == ("typical", "27.0", "3.3"):
                    ax.plot(x, np.array(f) * 0.587, color=INK, lw=2, ls="--", label="tt × 0.587 (extracted RC, 10 fF)")
ax.axhspan(310, 620, color="#cde2fb", alpha=0.5, lw=0)
ax.text(31.3, 615, "target: 310–620 MHz must be reachable\n(433.92 MHz for silicon factor 0.7–1.4)", fontsize=8,
        color=MUTED, ha="right", va="top")
ax.axhline(433.92, color=INK, lw=0.8)
ax.set_xlabel("coarse code"); ax.set_ylabel("f (MHz), vctrl = 1.65 V")
ax.legend(fontsize=8, loc="upper left", ncol=2)
ax.set_title("Fig. 2. Tuning map, all 45 PVT points (5 corners × 0/27/70 °C × VDD ±4.5 %), schematic with cw = 2 fF",
             loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "fig2_map.png"); plt.close(fig)

# ---- Fig 3: coarse step vs fine range, tt 27 C 3.3 V ----
def fcv(c, t, v, vc):
    return dict(sorted((int(r["code"]), float(r["f_hz"]) / 1e6) for r in data
                       if r["deck"].startswith(f"map_{c}_") and r["temp"] == t and r["vdd"] == v and r["vctrl"] == vc))
fig, ax = plt.subplots(figsize=(10, 4.6))
for ci, (c, t, v) in enumerate([("typical", "27.0", "3.3"), ("ss", "70.0", "3.3"), ("ff", "0.0", "3.15")]):
    lo, mid, hi = fcv(c, t, v, "0.0"), fcv(c, t, v, "1.65"), fcv(c, t, v, "3.3")
    codes = sorted(mid)
    step = [100 * (mid[k + 1] - mid[k]) / mid[k] for k in codes[:-1]]
    fine = [100 * (hi[k] - lo[k]) / mid[k] for k in codes[:-1]]
    ax.plot(codes[:-1], step, color=C[ci], lw=2, label=f"{c} {t[:-2]} °C {v} V: coarse step")
    ax.plot(codes[:-1], fine, color=C[ci], lw=1.4, ls="--", label=f"{c}: fine range (vctrl 0 → 3.3 V)")
ax.set_xlabel("coarse code"); ax.set_ylabel("% of f")
ax.legend(fontsize=8, ncol=2, loc="upper right")
ax.set_title("Fig. 3. Gaps: every coarse step (solid) must be smaller than the fine range (dashed) ÷ 1.3",
             loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "fig3_step_fine.png"); plt.close(fig)

# ---- Fig 4: tuning map at cw = 10 fF (+ R) ----
d10 = list(csv.DictReader(open(HERE / "map_cw10f/map.csv")))
fig, ax = plt.subplots(figsize=(10, 5.4))
for ci, c in enumerate(corners):
    for t in ("0.0", "27.0", "70.0"):
        for v in ("3.15", "3.3", "3.45"):
            lo = sorted((int(r["code"]), float(r["f_hz"]) / 1e6) for r in d10
                        if r["deck"].startswith(f"map_{c}_") and r["temp"] == t and r["vdd"] == v and r["vctrl"] == "0.0")
            hi = sorted((int(r["code"]), float(r["f_hz"]) / 1e6) for r in d10
                        if r["deck"].startswith(f"map_{c}_") and r["temp"] == t and r["vdd"] == v and r["vctrl"] == "3.3")
            if lo:
                x, fl = zip(*lo); _, fh = zip(*hi)
                ax.fill_between(x, fl, fh, color=C[ci], alpha=0.12, lw=0)
                ax.plot(x, fh, color=C[ci], lw=0.8, alpha=0.6, label=c if (t, v) == ("27.0", "3.3") else None)
                if (c, t, v) == ("ss", "70.0", "3.15"):
                    ax.plot(x, np.array(fh) * 0.89, color=INK, lw=2, ls="--", label="ss 70 °C 3.15 V top, × 0.89 for wiring R")
ax.axhspan(310, 620, color="#cde2fb", alpha=0.5, lw=0)
ax.axhline(433.92, color=INK, lw=0.8); ax.text(0.3, 438, "433.92 MHz", fontsize=8)
ax.text(31.3, 615, "target band 310–620 MHz", fontsize=8, color=MUTED, ha="right", va="top")
ax.set_xlabel("coarse code"); ax.set_ylabel("f (MHz): band = vctrl 0 → 3.3 V")
ax.legend(fontsize=8, loc="upper left")
ax.set_title("Fig. 4. Tuning map at cw = 10 fF (no R): the range has dropped below the band; top reached nowhere",
             loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "fig4_map_10f.png"); plt.close(fig)

# ---- Fig 5: rms FM over PVT (Job 2) ----
fig, ax = plt.subplots(figsize=(10, 4.4))
labels, tots, foots, bias = [], [], [], []
for c in corners:
    for t in (0, 27, 70):
        b = json.load(open(HERE / f"job2/bias_fm/cgmq_{c}_t{t}.json"))["fm"]["1000-10000"]
        labels.append(f"{c}\n{t}°C"); tots.append(b["total"] / 1e3); foots.append(b["dev_foot"] / 1e3)
        bias.append(np.hypot(b["vbnf"], b["vbp"]) / 1e3)
x = np.arange(len(labels)); w = 0.27
ax.bar(x - w, tots, w * 0.9, color=INK, label="total")
ax.bar(x, foots, w * 0.9, color=C[1], label="ring foot devices (flicker)")
ax.bar(x + w, bias, w * 0.9, color=C[2], label="bias (vbnf + vbp)")
ax.axhline(15, color=MUTED, ls="--", lw=0.9); ax.text(len(x) - 0.5, 15.5, "15 kHz", fontsize=8, color=MUTED, ha="right")
ax.set_xticks(x, labels, fontsize=8); ax.set_ylabel("rms FM 1–10 kHz (kHz)"); ax.legend(fontsize=8, loc="upper right")
ax.set_title("Fig. 5. Quiet-reference VCO over PVT (cw = 2 fF): the ring's own foot flicker sets it, worst at ff/fs cold",
             loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "fig5_fm_pvt.png"); plt.close(fig)
print("wrote", OUT)
