#!/usr/bin/env python3
"""Plots for the ISF phase-noise sweep (sim/pn/results/<date>/).

  python3 sim/pn/plot_results.py [results_dir] [out_dir]

Fig 1  ISF vs phase for se / diff / cgm at tt, with the node voltage, head/foot split shaded.
Fig 2  L(df) contributions per variant at tt (head, foot, bias, vdd, total).
Fig 3  Frequency noise (Hz/rtHz) and integrated rms FM vs bandwidth, against FSK deviation.
Fig 4  L(1 MHz) per corner, total vs device-only.

The result.json files hold each term at 10k/100k/1M/10M only, so curves are log-log
interpolated between those decades.
"""
import csv, json, math, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
RES = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "sim/pn/results/2026-11-07"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / "build/pn_plots"
OUT.mkdir(parents=True, exist_ok=True)

VAR = {"se": ("single-ended (se)", "#2a78d6"), "diff": ("differential (diff)", "#eb6834"),
       "cgm": ("const-gm biased (cgm)", "#1baf7a")}
TERM = {"dev_head": ("head (PMOS) devices", "#2a78d6"), "dev_foot": ("foot (NMOS) devices", "#eb6834"),
        "bias": ("bias line", "#1baf7a"), "vdd": ("VDD (100 nV/√Hz assumed)", "#eda100")}
CORNERS = ["ss", "sf", "typical", "fs", "ff"]
FREQS = [1e4, 1e5, 1e6, 1e7]
INK, MUTED, GRID = "#2b2b2b", "#6b6b66", "#e4e3de"

plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2,
                     "legend.frameon": False, "figure.dpi": 130})


def load(v, c="typical"):
    d = RES / f"{v}_{c}_t27"
    r = json.loads((d / "result.json").read_text())
    rows = list(csv.DictReader(open(d / "isf.csv")))
    return r, rows


def curve(r, key, f):
    """log-log interpolation of an L term (dBc/Hz) between the stored decades."""
    xs = np.log10(FREQS)
    ys = np.array([r["L"][f"{x:g}"][key] for x in FREQS], dtype=float)
    return np.interp(np.log10(f), xs, ys)


def dev_only(r, f):
    p = sum(10 ** (curve(r, k, f) / 10) for k in ("dev_head", "dev_foot"))
    return 10 * np.log10(p)


# ---- Fig 1: ISF ----
fig, axs = plt.subplots(3, 1, figsize=(7.5, 7.5), sharex=True)
for ax, v in zip(axs, VAR):
    r, rows = load(v)
    phi = np.array([float(x["phi"]) for x in rows])
    g = np.array([float(x["g_rad_per_C"]) for x in rows])
    vm, vt = np.array([float(x["v_m3ps"]) for x in rows]), np.array([float(x["v_at_td"]) for x in rows])
    head = vt >= vm
    # Gamma (dimensionless) = g * q_max, q_max = C*Vswing; show g normalised to its peak instead
    gn = g / np.max(np.abs(g))
    for i in range(len(phi)):
        if head[i]:
            ax.axvspan(phi[i] - np.pi / len(phi), phi[i] + np.pi / len(phi), color="#cde2fb", lw=0)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.plot(phi, gn, color=INK, marker="o", ms=3, label="ISF (normalised)")
    ax2 = ax.twinx(); ax2.grid(False)
    ax2.plot(phi, vt, color="#9a9a93", lw=1.2, ls="--")
    ax2.set_ylim(-0.5, 3.8); ax2.set_yticks([0, 3.3]); ax2.tick_params(colors="#9a9a93")
    ax2.spines["right"].set_visible(True); ax2.spines["top"].set_visible(False)
    rms, dc = math.sqrt(np.mean(g ** 2)), np.mean(g)
    ax.set_title(f"{VAR[v][0]}:  dc/rms = {dc / rms:+.2f}", loc="left", fontsize=10, color=INK)
    ax.set_ylim(-1.15, 1.15)
    ax.set_ylabel("Γ / |Γ|max")
axs[-1].set_xlabel("injection phase (rad)")
axs[-1].set_xticks([0, np.pi / 2, np.pi, 1.5 * np.pi, 2 * np.pi], ["0", "π/2", "π", "3π/2", "2π"])
fig.suptitle("Fig. 1. Impulse sensitivity function at node a2, tt 27 °C\n"
             "dashed: node voltage (right axis); shaded: node rising, so the head (PMOS) conducts",
             x=0.02, ha="left", fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "fig1_isf.png"); plt.close(fig)

# ---- Fig 2: L(df) breakdown ----
f = np.logspace(4, 7, 200)
fig, axs = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
for ax, v in zip(axs, VAR):
    r, _ = load(v)
    for k, (lab, col) in TERM.items():
        ax.plot(f, curve(r, k, f), color=col, lw=1.6, label=lab)
    ax.plot(f, curve(r, "L", f), color=INK, lw=2.6, label="total")
    ax.set_xscale("log"); ax.set_xlim(1e4, 1e7); ax.set_ylim(-140, -20)
    ax.set_title(f"{VAR[v][0]}  f0 {r['A']['f0'] / 1e6:.0f} MHz, {r['A']['P'] * 1e3:.2f} mW",
                 loc="left", fontsize=10)
    ax.set_xlabel("offset from carrier Δf (Hz)")
    # -20 / -30 dB/dec guides
    ax.plot([1e5, 1e6], [-125, -145 + 0], color=MUTED, lw=0.8, ls=":")
    ax.text(3e5, -128, "−20 dB/dec", fontsize=7, color=MUTED)
axs[0].set_ylabel("L(Δf)  (dBc/Hz)")
axs[0].legend(loc="upper right", fontsize=8)
fig.suptitle("Fig. 2. Phase-noise contributions, tt 27 °C. Bias line for se/diff assumes a 100 kΩ vctrl source",
             x=0.01, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "fig2_L_breakdown.png"); plt.close(fig)

# ---- Fig 3: frequency noise + integrated FM ----
f = np.logspace(3, 7, 400)


def sf_from_L(Ldb, f):   # S_f = f^2 * S_phi = 2 f^2 10^(L/10)  (Hz^2/Hz)
    return 2 * f ** 2 * 10 ** (Ldb / 10)


def ext(r, key, f):      # extrapolate below 10 kHz with the 10k-100k slope
    xs = np.log10(FREQS); ys = np.array([r["L"][f"{x:g}"][key] for x in FREQS])
    s = (ys[1] - ys[0])
    return np.where(f < 1e4, ys[0] + s * (np.log10(f) - 4), np.interp(np.log10(f), xs, ys))


fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.4))
cases = []
for v in VAR:
    r, _ = load(v)
    allt = sum(10 ** (ext(r, k, f) / 10) for k in TERM)
    cases.append((VAR[v][0], VAR[v][1], "-", 2 * f ** 2 * allt))
    dev = sum(10 ** (ext(r, k, f) / 10) for k in ("dev_head", "dev_foot", "vdd"))
    cases.append((VAR[v][0] + ": devices + vdd only", VAR[v][1], ":", 2 * f ** 2 * dev))
print(f"{'case':45s} rms FM 1k-10k  1k-100k  1k-1M (kHz)")
for lab, col, ls, S in cases:
    a1.plot(f, np.sqrt(S), color=col, ls=ls, label=lab)
    cum = np.sqrt(np.concatenate([[0], np.cumsum(0.5 * (S[1:] + S[:-1]) * np.diff(f))]))
    a2.plot(f, cum / 1e3, color=col, ls=ls, label=lab)
    print(f"{lab:45s} {np.interp(1e4, f, cum)/1e3:8.1f} {np.interp(1e5, f, cum)/1e3:8.1f} {np.interp(1e6, f, cum)/1e3:8.1f}")
for ax in (a1, a2):
    ax.set_xscale("log"); ax.set_xlim(1e3, 1e7); ax.set_xlabel("offset frequency (Hz)")
a1.set_yscale("log"); a1.set_ylabel("frequency noise  (Hz/√Hz)")
a1.set_title("frequency noise density", loc="left", fontsize=10)
a2.set_yscale("log"); a2.set_ylabel("rms frequency error, 1 kHz → f  (kHz)")
a2.set_title("integrated rms FM (from 1 kHz up to the x value)", loc="left", fontsize=10)
for dv in (25, 50):
    a2.axhline(dv, color=MUTED, lw=0.8, ls="--")
    a2.text(1.1e3, dv * 1.08, f"±{dv} kHz FSK deviation", fontsize=7, color=MUTED)
a1.legend(fontsize=7, loc="upper right")
fig.suptitle("Fig. 3. Frequency noise, tt 27 °C (below 10 kHz extrapolated). Dotted: bias line removed",
             x=0.01, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "fig3_fm.png"); plt.close(fig)

# ---- Fig 4: corners ----
fig, ax = plt.subplots(figsize=(7.5, 4))
x = np.arange(len(CORNERS)); w = 0.26
for i, v in enumerate(VAR):
    tot = [load(v, c)[0]["L"]["1e+06"]["L"] for c in CORNERS]
    dv = [float(dev_only(load(v, c)[0], 1e6)) for c in CORNERS]
    ax.bar(x + (i - 1) * w, [t + 140 for t in tot], w - 0.03, bottom=-140, color=VAR[v][1], label=VAR[v][0])
    ax.scatter(x + (i - 1) * w, dv, color="white", edgecolor=INK, zorder=3, s=30,
               label="devices only" if i == 0 else None)
ax.set_xticks(x, CORNERS); ax.set_ylim(-112, -75); ax.set_ylabel("L(1 MHz)  (dBc/Hz)")
ax.legend(fontsize=8, ncol=2, loc="upper left")
ax.set_title("Fig. 4. Phase noise at 1 MHz offset per process corner (bars: total, dots: devices only)",
             loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(OUT / "fig4_corners.png"); plt.close(fig)
print("wrote", OUT)
