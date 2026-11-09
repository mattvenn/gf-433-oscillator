#!/usr/bin/env python3
"""GF silicon factor: explanatory figures for docs/gf_silicon_factor.md (Fig. 2-5).

Usage (repo root): python3 -I sim/silicon_factor/plots.py
Reads sim/silicon_factor/results.csv; writes docs/img/gf_sf_*.png. Fig. 1 is docs/img/gf_silicon_factor.png.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[2]
IMG = REPO / "docs" / "img"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"   # categorical slots 1-3, fixed order
INK, MUTED, GRID, CORNER = "#2b2b2a", "#6b6a64", "#e4e3de", "#b9b8b0"
SI1 = {"inv1x5": 319.6, "t3": 220.51, "t5": 196.22, "t9": 160.66, "t33": 77.69, "t65": 49.87, "t161": 23.72}
SI2 = {"inv1x5": 311.6, "t3": 216.0}
TAPS = [3, 5, 9, 33, 65, 161]

plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "legend.frameon": False,
                     "figure.dpi": 150, "savefig.bbox": "tight"})

R = {}
for r in csv.DictReader(open(REPO / "sim/silicon_factor/results.csv")):
    R[(r["cfg"], r["corner"], r["mode"])] = float(r["f_Hz"]) / 1e6
f = lambda g, c="typical": R[(g, c, "c")]


def fig2():
    """Factor per ring, with where each process corner would put it."""
    cfgs = ["t3", "t5", "t9", "t33", "t65", "t161", "inv1x5"]
    labels = ["3", "5", "9", "33", "65", "161", "5× inv_1"]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    x = np.arange(len(cfgs))
    lo = [f(g, "ss") / f(g) for g in cfgs]; hi = [f(g, "ff") / f(g) for g in cfgs]
    ax.vlines(x, lo, hi, color=CORNER, lw=6, alpha=0.5, label="sim ss … ff (relative to typical)", zorder=1)
    for c, m in (("sf", "_"), ("fs", "_")):
        ax.scatter(x, [f(g, c) / f(g) for g in cfgs], marker=m, s=160, color=MUTED, lw=1.5, zorder=2)
    for xi, g in zip(x, cfgs):
        ax.text(xi + 0.18, f(g, "sf") / f(g), "sf", va="center", fontsize=7, color=MUTED)
        ax.text(xi + 0.18, f(g, "fs") / f(g), "fs", va="center", fontsize=7, color=MUTED)
    ax.axhline(1.0, color=INK, lw=1, zorder=1)
    ax.axhline(0.866, color=MUTED, lw=1, ls="--", zorder=1)
    ax.text(len(cfgs) - 0.5, 0.866, " sky130 ×0.866", va="center", fontsize=8, color=MUTED)
    ax.scatter(x, [SI1[g] / f(g) for g in cfgs], s=64, color=BLUE, edgecolor="white", lw=2, zorder=3,
               label="silicon chip 1 / sim typical")
    x2 = [x[cfgs.index(g)] for g in SI2]
    ax.scatter(x2, [SI2[g] / f(g) for g in SI2], s=64, color=ORANGE, edgecolor="white", lw=2, marker="D", zorder=3,
               label="silicon chip 2 / sim typical")
    for xi, g in zip(x, cfgs):
        ax.annotate(f"{SI1[g] / f(g):.3f}", (xi, SI1[g] / f(g)), xytext=(0, 9) if g != "inv1x5" else (-10, 0),
                    textcoords="offset points", ha="center" if g != "inv1x5" else "right",
                    va="bottom" if g != "inv1x5" else "center", fontsize=8, color=INK)
    ax.axvspan(5.5, 6.5, color=GRID, alpha=0.5, zorder=0)
    ax.set_xticks(x, labels); ax.set_xlim(-0.6, len(cfgs) - 0.3)
    ax.set_xlabel("inv_2 tap (stages)                                              fixed ring")
    ax.set_ylabel("f / f_sim,typical"); ax.set_ylim(0.65, 1.4)
    ax.legend(loc="upper left", fontsize=8, ncol=3)
    fig.savefig(IMG / "gf_sf_factor.png"); plt.close(fig)


def fig3():
    """Period vs stages, straight-line fit, and the residuals (same curvature in silicon and sim)."""
    N = np.array(TAPS)
    Ts = 1e3 / np.array([SI1[f"t{n}"] for n in TAPS]); Tt = 1e3 / np.array([f(f"t{n}") for n in TAPS])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 3.4), gridspec_kw={"width_ratios": [1.3, 1]})
    nn = np.linspace(0, 170, 50)
    for T, col, lab, mk in ((Tt, ORANGE, "sim typical", "s"), (Ts, BLUE, "silicon chip 1", "o")):
        a, b = np.polyfit(N, T, 1)
        a1.plot(nn, a * nn + b, color=col, lw=1.5, alpha=0.7)
        a1.scatter(N, T, color=col, s=40, marker=mk, edgecolor="white", lw=1.5, zorder=3,
                   label=f"{lab}: a = {a:.4f} ns/stage, b = {b:.3f} ns")
        a2.plot(N, T - (a * N + b), color=col, lw=1.5, marker=mk, ms=6, mec="white", label=lab)
    a1.set_xlabel("stages N"); a1.set_ylabel("period T (ns)"); a1.set_xlim(0, 170); a1.set_ylim(0, 45)
    a1.set_title("T = a·N + b", fontsize=10, color=INK, loc="left")
    a1.legend(fontsize=8, loc="upper left")
    a2.axhline(0, color=INK, lw=0.8); a2.set_xscale("log"); a2.set_xticks(TAPS, [str(n) for n in TAPS])
    a2.set_xlabel("stages N"); a2.set_ylabel("T − fit (ns)")
    a2.set_title("residual: same shape in silicon and sim", fontsize=10, color=INK, loc="left")
    a2.legend(fontsize=8, loc="upper left")
    fig.tight_layout(); fig.savefig(IMG / "gf_sf_fit.png"); plt.close(fig)


def fig4():
    """Extracted capacitance by class, magic 8.3.642 vs 8.3.684 (values from docs/gf_silicon_factor.md)."""
    cls = ["signal to signal", "to VPWR", "to VGND / substrate", "total"]
    v642 = [3.32, 3.24, 6.15, 12.72]; v684 = [1.99, 2.60, 4.75, 9.33]
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    y = np.arange(len(cls)); h = 0.36
    ax.barh(y - h / 2 - 0.01, v642, h, color=BLUE, label="magic 8.3.642 (used)")
    ax.barh(y + h / 2 + 0.01, v684, h, color=ORANGE, label="magic 8.3.684 (image default)")
    for yi, a, b in zip(y, v642, v684):
        ax.text(a + 0.15, yi - h / 2, f"{a:.2f} pF", va="center", fontsize=8, color=INK)
        ax.text(b + 0.15, yi + h / 2, f"{b:.2f} pF  ({(b / a - 1) * 100:+.0f} %)", va="center", fontsize=8, color=INK)
    ax.set_yticks(y, cls); ax.invert_yaxis(); ax.set_xlim(0, 15.5); ax.set_xlabel("extracted capacitance (pF)")
    ax.grid(axis="y", visible=False); ax.legend(fontsize=8, loc="upper right")
    fig.savefig(IMG / "gf_sf_magic.png"); plt.close(fig)


def fig5():
    """Our VCO's extracted range under each factor, against 433.92 MHz."""
    lo, hi = 193, 851   # extracted v3 RC range over the corners at vctrl 1.65 V (docs/remap_results.md)
    rows = [("as simulated (×1.0)", 1.0, INK), ("inv_2 taps (×0.993)", 0.993, BLUE),
            ("5× inv_1 (×0.935)", 0.935, BLUE), ("old margin, slow (×0.7)", 0.7, CORNER),
            ("old margin, fast (×1.4)", 1.4, CORNER)]
    fig, ax = plt.subplots(figsize=(6.8, 2.8))
    for i, (lab, k, col) in enumerate(rows):
        ax.plot([lo * k, hi * k], [i, i], color=col, lw=8, solid_capstyle="butt")
        ax.text(hi * k + 12, i, f"{lo * k:.0f}–{hi * k:.0f} MHz", va="center", fontsize=8, color=INK)
    ax.axvline(433.92, color=ORANGE, lw=1.5)
    ax.text(433.92, -0.75, "433.92 MHz", ha="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows]); ax.invert_yaxis()
    ax.set_xlim(0, 1400); ax.set_ylim(len(rows) - 0.4, -1.1); ax.set_xlabel("ring frequency (MHz)")
    ax.grid(axis="y", visible=False)
    fig.savefig(IMG / "gf_sf_vco_range.png"); plt.close(fig)


if __name__ == "__main__":
    for fn in (fig2, fig3, fig4, fig5):
        fn()
    print("wrote", sorted(p.name for p in IMG.glob("gf_sf_*.png")))
