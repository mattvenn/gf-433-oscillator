#!/usr/bin/env python3
"""Two-page datasheet comparing the two 433.92 MHz tunable ring-oscillator candidates (GF180, schematic sims).

Reads the ngspice logs written by sim/vco/vco_cand.py and sim/vco/ring_basic.py, draws the figures
(SVG, into docs/datasheet/), builds docs/datasheet/datasheet.html and prints it to
docs/vco_options_datasheet.pdf with headless Chrome. Run from anywhere:

  python3 docs/datasheet/make_datasheet.py

Data it needs (regenerate with build/vco/run_dense.sh, one ngspice job at a time):
  build/vco/se_n5/sweep_dense_typical.log    se --n 5 sweep --vctrls 1.0:3.3:0.1 --codes 0,3,7,11,15 --tag dense_
  build/vco/diff_n4/sweep_dense_typical.log  same for diff --n 4
  build/vco/{se_n5,diff_n4}/pvt_<corner>.log pvt --code 7 --vctrl 1.5
  build/vco/ring_basic_full.txt              plain ring (sim/vco/ring_basic.py)
Sizing flags for both options: --set wn=2 --set wp=5 --set whead=6 --set wpb=1 --set wmb=0.25
  --set wfu=0.25 --set k=8 --set ls=1 --set wx=0.5
Branding (colours, Avenir Next, logo, header art) is copied from ook-asic-radio/docs/explainer.
"""
import math, re, subprocess, sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch, Circle

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BV = REPO / "build/vco"
PDF = REPO / "docs/vco_options_datasheet.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
F0 = 433.92e6
CORNERS = ["typical", "ss", "ff", "sf", "fs"]
CNAME = {"typical": "tt", "ss": "ss", "ff": "ff", "sf": "sf", "fs": "fs"}
OPT = {"A": dict(dir="se_n5", n=5, name="Option A: single-ended, N=5"),
       "B": dict(dir="diff_n4", n=4, name="Option B: pseudo-differential, N=4")}

# --- brand (ook-asic-radio/docs/explainer/template.html :root) --------------------------------
Z2A_CYAN, Z2A_PURPLE, Z2A_MAGENTA = "#5cc8da", "#7a3bbf", "#d9409f"
BG, PANEL, PANEL2, LINE, TEXT, MUTED, FAINT = "#0c0818", "#150f26", "#1e1636", "#382c5a", "#f1edf8", "#b4a9cf", "#81749e"
# print (light paper) versions: dark violet-grey ink, brand accents. Categorical slots validated with the
# dataviz validator on white (all checks pass): plain ring cyan (darkened brand cyan), A purple, B magenta.
INK, INK2, INK3, RULE, GRID = "#1e1636", "#4a3f66", "#7a6f96", "#d8d1e6", "#ece8f3"
COL = {"plain": "#1f9bb3", "A": Z2A_PURPLE, "B": Z2A_MAGENTA}

plt.rcParams.update({
    "font.family": ["Avenir Next", "Avenir", "DejaVu Sans"], "font.size": 7.5, "svg.fonttype": "none",
    "axes.edgecolor": INK3, "axes.labelcolor": INK2, "axes.linewidth": 0.6, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "xtick.color": INK3, "ytick.color": INK3,
    "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 7,
    "axes.titlesize": 8, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "lines.linewidth": 1.4, "figure.dpi": 100, "axes.axisbelow": True,
})
MM = 1 / 25.4


# --- data ---------------------------------------------------------------------------------------
RES = re.compile(r"^RES (\S+) (\S+) (\S+) (\S+) (\S+) (\S*) (\S+)$", re.M)


def read_res(path):
    """RES lines -> list of dict(code, vc, t, vdd, f [Hz, nan if no 10 periods in 100-200 ns], p [W])."""
    rows = []
    for m in RES.finditer(path.read_text()):
        f = float(m.group(6)) if m.group(6) else float("nan")
        rows.append(dict(code=int(m.group(2)), vc=float(m.group(3)), t=float(m.group(4)),
                         vdd=float(m.group(5)), f=f, p=float(m.group(7))))
    if not rows:
        sys.exit(f"no RES lines in {path}")
    return rows


def sweep(opt):
    dense = BV / OPT[opt]["dir"] / "sweep_dense_typical.log"
    rows = read_res(dense) if dense.exists() else []
    if not any(r["code"] == 15 and abs(r["vc"] - 3.3) < 1e-6 for r in rows):   # dense run missing/incomplete
        rows = read_res(BV / OPT[opt]["dir"] / "sweep_typical.log")              # original 6-point sweep
        COARSE.add(opt)
    out = {}
    for r in rows:
        if math.isfinite(r["f"]):          # below ~110 MHz the 10-period window doesn't fit: nan, dropped
            out.setdefault(r["code"], []).append((r["vc"], r["f"], r["p"]))
    return {c: np.array(sorted(v)) for c, v in sorted(out.items())}


def pvt(opt):
    d = {}
    for c in CORNERS:
        for r in read_res(BV / OPT[opt]["dir"] / f"pvt_{c}.log"):
            d[(c, r["t"], r["vdd"])] = (r["f"], r["p"])
    return d


def plain_ring(n=15):
    d = {}
    for line in (BV / "ring_basic_full.txt").read_text().splitlines()[1:]:
        m = re.match(r"(\w+)_n(\d+)_t(\d+)_v(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", line)
        if m and int(m.group(2)) == n:
            d[(m.group(1), float(m.group(5)), float(m.group(6)))] = (float(m.group(7)) * 1e6, float(m.group(8)) * 1e-3)
    return d


def sens(d):
    """supply %/10 mV and tempco ppm/C from a {(corner,T,VDD):(f,p)} dict at tt."""
    f = lambda t, v: d[("typical", t, v)][0]
    ref = f(27, 3.3)
    s = (f(27, 3.45) - f(27, 3.15)) / ref / 30 * 100          # 300 mV span -> per 10 mV, in %
    tc = (f(70, 3.3) - f(0, 3.3)) / ref / 70 * 1e6
    vals = [v[0] / ref for v in d.values()]
    return s, tc, min(vals), max(vals)


def bias_a():
    """Constant-gm-biased option A (sim/vco/vco_bias.py, build/vco/bias_a): sweep RES lines + pvt table."""
    d = BV / "bias_a"
    sw = {}
    for m in re.finditer(r"^RES \S+ (\d+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+)$", (d / "sweep_typical.log").read_text(), re.M):
        c, vc, t, vdd, f, p = int(m.group(1)), *map(float, m.group(2, 3, 4, 5, 6))
        sw.setdefault(c, []).append((vc, f, p))
    sw = {c: np.array(sorted(v)) for c, v in sw.items()}
    pv = {}
    for line in (d / "pvt.txt").read_text().splitlines():
        x = line.split()
        if len(x) == 9 and x[0].startswith("pvt_"):
            pv[(x[0][4:], float(x[3]), float(x[4]))] = (float(x[5]) * 1e6, float(x[6]) * 1e-3)
    return sw, pv


def kvco(arr):
    vc, f = arr[:, 0], arr[:, 1]
    return vc, np.gradient(f, vc) / 1e6       # MHz/V


def interp_vc(arr, ftarget):
    vc, f = arr[:, 0], arr[:, 1]
    if not (f.min() <= ftarget <= f.max()):
        return float("nan")
    return float(np.interp(ftarget, f, vc))


def devices(opt):
    """Device list (W, L um) from vco_cand's netlist with the datasheet sizing."""
    sys.path.insert(0, str(REPO / "sim/vco"))
    import vco_cand as vc
    p = dict(vc.P)
    p.update(wn=2.0, wp=5.0, whead=6.0, wpb=1.0, wmb=0.25, wfu=0.25, k=8, ls=1.0, wx=0.5)
    body, _, _ = vc.netlist("se" if opt == "A" else "diff", OPT[opt]["n"], p)
    return [(float(w), float(l)) for w, l in re.findall(r" w=([\d.]+)u l=([\d.]+)u", body)]


def area_est(devs):
    """Rough: each device (W+0.8)x(L+1.6) um (S/D 0.5 um each side + spacing), x3 for wells, taps, wiring."""
    return 3 * sum((w + 0.8) * (l + 1.6) for w, l in devs)


# --- figures ------------------------------------------------------------------------------------
CODES = [0, 3, 7, 11, 15]
COARSE = set()   # options that fell back to the 6-point vctrl sweep


def ramp(hexcol, n):
    """Light->dark steps of one hue for coarse codes (sequential: magnitude, not identity)."""
    c = np.array(matplotlib.colors.to_rgb(hexcol))
    ks = np.linspace(0.45, 1.0, n)
    out = []
    for k in ks:
        mix = 1 - k
        out.append(c * k + np.array([1, 1, 1]) * mix * 0.9 + c * 0.0)
    out[-1] = c * 0.78                       # darkest step a little deeper than the brand colour
    return [matplotlib.colors.to_hex(np.clip(x, 0, 1)) for x in out]


def f0_line(ax, xr, label=True):
    ax.axhline(F0 / 1e6, color=INK, lw=0.9, ls=(0, (4, 3)), zorder=1)
    if label:
        ax.text(xr, F0 / 1e6 + 12, "433.92 MHz", color=INK, fontsize=6.8, ha="right", va="bottom")


def fig_fv(SW, path):
    fig, axs = plt.subplots(1, 2, figsize=(186 * MM, 54 * MM), sharey=True)
    for ax, opt in zip(axs, "AB"):
        cols = ramp(COL[opt], len(CODES))
        for c, col in zip(CODES, cols):
            a = SW[opt].get(c)
            if a is None:
                continue
            ax.plot(a[:, 0], a[:, 1] / 1e6, color=col, lw=1.4, solid_capstyle="round")
            ax.text(a[-1, 0] + 0.04, a[-1, 1] / 1e6, f"{c}", color=INK2, fontsize=6.5, va="center")
        f0_line(ax, 3.48)
        ax.plot([1.5], [SW[opt][7][np.argmin(abs(SW[opt][7][:, 0] - 1.5)), 1] / 1e6], "o", ms=4.5,
                mfc="white", mec=INK, mew=1.0, zorder=5)
        ax.set_title(OPT[opt]["name"])
        ax.set_xlabel("vctrl (V)")
        ax.set_xlim(0.95, 3.5)
        ax.text(3.36, 1135, "code", color=INK3, fontsize=6.3, ha="left", va="top")
    axs[0].set_ylabel("frequency (MHz), tt 27 °C 3.3 V")
    axs[0].set_ylim(0, 1150)
    axs[0].text(1.02, 1040, "○ code 7, vctrl 1.5 V", color=INK2, fontsize=6.5)
    fig.tight_layout(pad=0.3, w_pad=1.5)
    fig.savefig(path)
    plt.close(fig)


def fig_kvco(SW, BW, path):
    fig, ax = plt.subplots(figsize=(90 * MM, 58 * MM))
    for opt, ls in (("A", "-"), ("B", (0, (5, 2)))):
        for c, lw in ((0, 0.9), (7, 1.6), (15, 0.9)):
            a = SW[opt].get(c)
            if a is None:
                continue
            vc, k = kvco(a)
            ax.plot(vc, k, color=COL[opt], ls=ls, lw=lw, alpha=1 if c == 7 else 0.55,
                    label=f"{opt}, code 7" if c == 7 else None)
            if c != 7:
                i = int(np.argmax(k))
                ax.text(vc[i], k[i] + 15, f"{c}", color=INK3, fontsize=6, ha="center")
    vc, k = kvco(BW[15])
    ax.plot(vc, k, color=INK, lw=1.6, label="A + const-gm, code 15")
    ax.axvline(1.5, color=INK3, lw=0.7, ls=":")
    ax.set_xlabel("vctrl (V)")
    ax.set_ylabel("Kvco = df/dvctrl (MHz/V)")
    ax.set_xlim(1.0, 3.3)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", handlelength=2.6)
    ax.set_title("Kvco vs vctrl (codes 0 / 7 / 15)")
    fig.tight_layout(pad=0.3)
    fig.savefig(path)
    plt.close(fig)


def fig_power(SW, PR, path):
    fig, ax = plt.subplots(figsize=(90 * MM, 58 * MM))
    for opt, ls in (("A", "-"), ("B", (0, (5, 2)))):
        for c in CODES:
            a = SW[opt].get(c)
            if a is None:
                continue
            ax.plot(a[:, 1] / 1e6, a[:, 2] * 1e3, color=COL[opt], ls=ls, lw=1.0 if c != 7 else 1.6,
                    alpha=1 if c == 7 else 0.45, label=f"{opt} (code 7 bold)" if c == 7 else None)
    pp = PR[("typical", 27, 3.3)][1] * 1e3
    ax.axhline(pp, color=COL["plain"], lw=1.4, ls=(0, (1.5, 1.5)), label="plain ring (any N)")
    ax.axvline(F0 / 1e6, color=INK, lw=0.9, ls=(0, (4, 3)))
    ax.text(F0 / 1e6 + 10, 0.12, "433.92 MHz", color=INK, fontsize=6.5)
    ax.set_xlabel("frequency (MHz)")
    ax.set_ylabel("supply power (mW)")
    ax.set_ylim(0, max(3.4, pp + 0.5))
    ax.set_xlim(100, 1100)
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 0.4))
    ax.set_title("Power vs frequency, tt 27 °C 3.3 V")
    fig.tight_layout(pad=0.3)
    fig.savefig(path)
    plt.close(fig)


def fig_pvt(PV, PR, path):
    fig, ax = plt.subplots(figsize=(118 * MM, 58 * MM))
    temps = [0, 27, 70]
    series = (("plain", PR, -0.24, "Plain ring N=15"), ("A", PV["A"], 0.0, "A (code 7, 1.5 V)"),
              ("B", PV["B"], 0.24, "B (code 7, 1.5 V)"))
    xt, xl = [], []
    for ci, c in enumerate(CORNERS):
        for ti, t in enumerate(temps):
            x = ci * 3.6 + ti
            xt.append(x); xl.append(f"{t}")
            for key, d, off, lab in series:
                ref = d[("typical", 27, 3.3)][0]
                lo, mid, hi = (d[(c, t, v)][0] / ref for v in (3.15, 3.3, 3.45))
                ax.plot([x + off] * 2, [lo, hi], color=COL[key], lw=1.6, solid_capstyle="round")
                ax.plot([x + off], [mid], "o", ms=3.6, color=COL[key], mec="white", mew=0.6,
                        label=lab if (ci, ti) == (0, 0) else None)
        ax.text(ci * 3.6 + 1, -0.15, CNAME[c], ha="center", va="top", color=INK, fontsize=7.5, fontweight="bold",
                transform=matplotlib.transforms.blended_transform_factory(ax.transData, ax.transAxes))
    ax.axhline(1, color=INK3, lw=0.7)
    ax.set_xticks(xt, xl, fontsize=6.3)
    ax.set_xlabel("temperature (°C) / process corner;  bar = VDD 3.15 … 3.45 V, dot = 3.3 V", labelpad=14)
    ax.set_ylabel("f / f(tt, 27 °C, 3.3 V)")
    ax.set_ylim(0.6, 1.55)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="lower left", ncol=3, bbox_to_anchor=(0.0, 0.99), handlelength=1)
    fig.tight_layout(pad=0.3)
    fig.savefig(path)
    plt.close(fig)


def fig_sens(S, path):
    fig, axs = plt.subplots(1, 2, figsize=(66 * MM, 56 * MM))
    keys = ["plain", "A", "B"]
    labs = ["plain", "A", "B"]
    for ax, idx, title, fmt in ((axs[0], 0, "df/dVDD (%/10 mV)", "{:+.2f}"), (axs[1], 1, "tempco (ppm/°C)", "{:+.0f}")):
        v = [S[k][idx] for k in keys]
        ax.bar(range(3), v, color=[COL[k] for k in keys], width=0.62, edgecolor="white", linewidth=1)
        ax.axhline(0, color=INK3, lw=0.7)
        span = max(abs(min(v)), abs(max(v)), 1e-9)
        for i, x in enumerate(v):
            ax.text(i, x + (0.04 * span if x >= 0 else -0.04 * span), fmt.format(x).replace("-", "−"), ha="center",
                    va="bottom" if x >= 0 else "top", fontsize=6.3, color=INK)
        ax.set_xticks(range(3), labs)
        ax.set_title(title, fontsize=7.2)
        ax.grid(axis="x", visible=False)
        lo, hi = min(0, min(v)), max(0, max(v))
        ax.set_ylim(lo - 0.22 * span, hi + 0.22 * span)
    fig.tight_layout(pad=0.3, w_pad=1.0)
    fig.savefig(path)
    plt.close(fig)


def inv(ax, x, y, s=1.0, col=INK, lw=1.0, fill="white"):
    """Inverter triangle pointing right, input at (x,y), output at (x+0.9s, y)."""
    ax.add_patch(Polygon([[x, y - 0.4 * s], [x, y + 0.4 * s], [x + 0.75 * s, y]], closed=True,
                         fc=fill, ec=col, lw=lw, zorder=3))
    ax.plot([x + 0.8 * s], [y], "o", ms=2.6 * s ** 0.5, mfc="white", mec=col, mew=lw, zorder=4)


def fig_topo(path):
    fig, axs = plt.subplots(1, 3, figsize=(186 * MM, 34 * MM), gridspec_kw=dict(width_ratios=[1.0, 1.0, 1.1]))
    for ax in axs:
        ax.axis("off")
    # (a) one starved stage
    ax = axs[0]
    ax.set_xlim(-0.3, 8.6); ax.set_ylim(-0.4, 5.7)
    def box(x, y, w, h, t, c, fs=5.2):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=c + "22", ec=c, lw=0.9))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, color=INK, linespacing=1.15)
    ax.plot([2.75, 2.75], [4.6, 4.95], color=INK, lw=0.9); ax.text(2.9, 4.9, "VDD", fontsize=5.6, color=INK2, va="center")
    box(0.6, 3.75, 4.3, 0.85, "head PMOS 6/1 µm\ngate vbp (mirror)", COL["A"])
    box(0.6, 2.45, 4.3, 0.95, "inverter\nP 5/0.28  N 2/0.28 µm", INK3)
    box(0.0, 0.4, 2.6, 1.6, "main foot\n8 × 0.25/1 µm\ngate vctrl", COL["A"])
    box(2.9, 0.4, 2.6, 1.6, "binary legs\n1, 2, 4, 8 ×\n0.25/1 µm\ngates g0..g3", COL["A"])
    for (x0, y0, x1, y1) in ((2.75, 3.75, 2.75, 3.4), (2.75, 2.45, 2.75, 2.2), (1.3, 2.2, 4.2, 2.2),
                             (1.3, 2.2, 1.3, 2.0), (4.2, 2.2, 4.2, 2.0), (1.3, 0.4, 1.3, 0.0), (4.2, 0.4, 4.2, 0.0)):
        ax.plot([x0, x1], [y0, y1], color=INK, lw=0.9)
    ax.plot([0.6, 4.9], [0.0, 0.0], color=INK, lw=0.9); ax.text(5.0, 0.0, "GND", fontsize=5.6, color=INK2, va="center")
    ax.plot([4.9, 5.4], [2.92, 2.92], color=INK, lw=0.9); ax.text(5.5, 2.92, "out", fontsize=5.6, color=INK2, va="center")
    ax.text(5.75, 1.2, "g_b = bit_b ?\n  vctrl : 0\n(pass gate +\npull-down,\nshared by all\nstages)", fontsize=5.2, color=INK2, va="center")
    ax.text(-0.3, 5.7, "Starved stage (both options)", fontsize=7.2, fontweight="bold", color=INK, va="top")
    # (b) option A ring
    ax = axs[1]
    ax.set_xlim(-0.2, 8.6); ax.set_ylim(-0.6, 4.0)
    ax.text(-0.2, 3.95, "Option A: 5-stage single-ended ring", fontsize=7.2, fontweight="bold", color=INK, va="top")
    y = 1.8
    for i in range(5):
        x = 0.4 + i * 1.6
        inv(ax, x, y, 1.0, COL["A"], 1.0)
        ax.plot([x + 0.87, x + 1.6], [y, y], color=INK, lw=0.9)
    ax.plot([8.4, 8.4, 0.1, 0.1, 0.4], [y, 0.6, 0.6, y, y], color=INK, lw=0.9)
    ax.text(8.45, y + 0.15, "out", fontsize=6, color=INK2)
    ax.text(4.2, 0.0, "I(stage) ∝ (8 + code) · I(vctrl);  f ≈ I / (C·VDD)", fontsize=6.2, color=INK2, ha="center")
    ax.text(4.2, 2.9, "one output, rail-to-rail", fontsize=6.2, color=INK2, ha="center")
    # (c) option B ring
    ax = axs[2]
    ax.set_xlim(-0.3, 8.8); ax.set_ylim(-0.8, 4.6)
    ax.text(-0.3, 4.6, "Option B: 4-stage pseudo-differential", fontsize=7.2, fontweight="bold", color=INK, va="top")
    ya, yb = 2.75, 0.85
    for i in range(4):
        x = 0.4 + i * 1.9
        for yy in (ya, yb):
            inv(ax, x, yy, 1.0, COL["B"], 1.0)
            ax.plot([x + 0.87, x + 1.9], [yy, yy], color=INK, lw=0.9)
        # weak cross-coupled latch pair (wx = 0.5) between a_i and b_i at the stage output node
        xn = x + 1.35
        ax.plot([xn, xn], [yb, ya], color=INK3, lw=0.7)
        ax.plot([xn], [ya], "o", ms=2.2, color=INK); ax.plot([xn], [yb], "o", ms=2.2, color=INK)
        ax.add_patch(FancyBboxPatch((xn - 0.42, 1.52), 0.84, 0.56, boxstyle="round,pad=0.02,rounding_size=0.08",
                                    fc="white", ec=INK3, lw=0.7, zorder=5))
        ax.text(xn, 1.8, "latch", fontsize=4.8, color=INK2, ha="center", va="center", zorder=6)
    xe = 0.4 + 4 * 1.9   # wrap with crossover: a3 -> b0, b3 -> a0
    ax.plot([xe, xe + 0.25, xe + 0.25], [ya, ya, 3.45], color=INK, lw=0.9)
    ax.plot([xe + 0.25, 0.1, 0.1, 0.4], [3.45, 3.45, yb, yb], color=COL["B"], lw=0.8)
    ax.plot([xe, xe + 0.45, xe + 0.45], [yb, yb, 0.25], color=INK, lw=0.9)
    ax.plot([xe + 0.45, -0.1, -0.1, 0.4], [0.25, 0.25, ya, ya], color=COL["B"], lw=0.8, ls=(0, (3, 1.5)))
    ax.text(xe + 0.6, ya, "a", fontsize=6.2, color=INK2, va="center"); ax.text(xe + 0.6, yb, "b", fontsize=6.2, color=INK2, va="center")
    ax.text(4.2, -0.45, "wrap crosses a↔b;  latch = weak back-to-back inverters (wx 0.5 µm)", fontsize=5.9,
            color=INK2, ha="center")
    fig.tight_layout(pad=0.2, w_pad=0.6)
    fig.savefig(path)
    plt.close(fig)


# --- page ---------------------------------------------------------------------------------------
def fmt(x, nd=0):
    return f"{x:,.{nd}f}".replace("-", "−")


def build():
    SW = {o: sweep(o) for o in "AB"}
    PV = {o: pvt(o) for o in "AB"}
    PR = plain_ring(15)
    BW, BP = bias_a()
    S = {"plain": sens(PR), "A": sens(PV["A"]), "B": sens(PV["B"]), "C": sens(BP)}
    b15 = dict((round(v, 2), (f, p)) for v, f, p in BW[15])
    C = dict(f=b15[1.65][0], p=b15[1.65][1], k=(b15[2.3][0] - b15[1.65][0]) / 0.65 / 1e6,
             fmin=min(a[:, 1].min() for a in BW.values()), fmax=max(a[:, 1].max() for a in BW.values()),
             cr=BW[31][2, 1] / BW[0][2, 1], c0=BW[0][2, 1], c31=BW[31][2, 1],
             fine=(b15[3.3][0] - b15[0.0][0]) / 2 / b15[1.65][0] * 100, f15lo=b15[0.0][0], f15hi=b15[3.3][0])
    sC = S["C"]
    # plain ring stage count for 433.92 MHz: f*N at tt 27 3.3 V
    fN_plain = PR[("typical", 27, 3.3)][0] * 15
    N_plain = fN_plain / F0
    K = {}
    for o in "AB":
        a7 = SW[o][7]
        vc, k = kvco(a7)
        i15 = int(np.argmin(abs(vc - 1.5)))
        v434 = interp_vc(a7, F0)
        allf = np.concatenate([SW[o][c][:, 1] for c in SW[o]])
        f0c = dict((round(v, 2), f) for v, f, _ in SW[o][0])
        f15c = dict((round(v, 2), f) for v, f, _ in SW[o][15])
        devs = devices(o)
        K[o] = dict(f=a7[i15, 1], p=a7[i15, 2], k15=k[i15], v434=v434, k434=float(np.interp(v434, vc, k)),
                    p434=float(np.interp(v434, a7[:, 0], a7[:, 2])),
                    fmin=allf.min(), fmax=allf.max(), cr=f15c[1.5] / f0c[1.5], ndev=len(devs), area=area_est(devs),
                    fN=a7[i15, 1] * OPT[o]["n"])
    pdevs = [(2.0, 0.28), (5.0, 0.28)] * math.ceil(N_plain)
    plain_area = area_est(pdevs)

    fig_topo(HERE / "fig0_topology.svg")
    fig_fv(SW, HERE / "fig1_f_vs_vctrl.svg")
    fig_kvco(SW, BW, HERE / "fig2_kvco.svg")
    fig_pvt(PV, PR, HERE / "fig3_pvt.svg")
    fig_sens(S, HERE / "fig4_sensitivity.svg")
    fig_power(SW, PR, HERE / "fig5_power.svg")

    A, B = K["A"], K["B"]
    sA, sB, sP = S["A"], S["B"], S["plain"]
    mhz = lambda pct: pct / 100 * F0 / 1e6     # %/10 mV -> MHz/10 mV at 433.92
    mk = lambda x: fmt(mhz(x) * 1e3)
    rows = [
        ("Tuning span (all codes, vctrl)", f"{fmt(A['fmin']/1e6)}–{fmt(A['fmax']/1e6)} MHz",
         f"{fmt(B['fmin']/1e6)}–{fmt(B['fmax']/1e6)} MHz", f"{fmt(C['fmin']/1e6)}–{fmt(C['fmax']/1e6)} MHz", "none"),
        ("Coarse range, top / bottom code", f"×{A['cr']:.2f} (1.5 V)", f"×{B['cr']:.2f} (1.5 V)",
         f"×{C['cr']:.2f}, about 15 MHz steps", "—"),
        ("Fine tuning: Kvco at 433.92 MHz", f"{fmt(A['k434'])} MHz/V", f"{fmt(B['k434'])} MHz/V",
         f"about {C['k']:.0f} MHz/V, ±{C['fine']:.1f} %", "—"),
        ("df/dVDD, %/10 mV (kHz at 433.92 MHz)", f"{fmt(sA[0],2)} ({mk(sA[0])})",
         f"{fmt(sB[0],2)} ({mk(sB[0])})", f"{fmt(sC[0],2)} ({mk(sC[0])})", f"+{sP[0]:.2f} (+{mk(sP[0])})"),
        ("Tempco, 0–70 °C", f"{fmt(sA[1])} ppm/°C", f"{fmt(sB[1])} ppm/°C",
         f"+{fmt(sC[1])} ppm/°C", f"{fmt(sP[1])} ppm/°C"),
        ("PVT spread (process, VDD, temp.)", f"×{sA[2]:.2f} … ×{sA[3]:.2f}", f"×{sB[2]:.2f} … ×{sB[3]:.2f}",
         f"×{sC[2]:.2f} … ×{sC[3]:.2f}", f"×{sP[2]:.2f} … ×{sP[3]:.2f}"),
        ("Power at 433.92 MHz", f"{A['p434']*1e3:.2f} mW", f"{B['p434']*1e3:.2f} mW",
         f"{C['p']*1e3:.2f} mW at {fmt(C['f']/1e6)} MHz", f"{PR[('typical',27,3.3)][1]*1e3:.2f} mW"),
        ("Outputs", "1, single-ended", "2, complementary", "1, single-ended", "1, single-ended"),
    ]
    trows = "\n".join(
        f"<tr><th>{r[0]}</th><td>{r[1]}</td><td>{r[2]}</td><td class='c'>{r[3]}</td><td class='pl'>{r[4]}</td></tr>" for r in rows)
    logo = (HERE / "z2a_logo.svg").read_text()

    page_head = f"""<header><div class="brand">{logo}<span><small>Zero to ASIC Course</small><b>GF180 433.92 MHz VCO</b></span></div>
<div class="tag">Preliminary · pre-silicon, schematic simulation, not extracted</div></header>"""

    def foot(n):
        return f"""<footer><span class="nw">Zero to ASIC Course · zerotoasiccourse.com · Matt Venn</span>
<span>GF180 433.92 MHz VCO options · 2026-11-07 · Preliminary</span>
<a class="claude" href="https://claude.com/claude-code">Made with Claude</a><span class="nw">{n} / 2</span></footer>"""

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>GF180 VCO options</title>
<style>
@page {{ size: A4; margin: 0 }}
:root {{
  --bg:{BG}; --panel:{PANEL}; --panel2:{PANEL2}; --line:{LINE}; --text:{TEXT}; --muted:{MUTED}; --faint:{FAINT};
  --z2a-cyan:{Z2A_CYAN}; --z2a-purple:{Z2A_PURPLE}; --z2a-magenta:{Z2A_MAGENTA};
  --ink:{INK}; --ink2:{INK2}; --ink3:{INK3}; --rule:{RULE}; --tint:#f5f2fa;
  --sans:"Avenir Next", Avenir, "Nunito Sans", "Segoe UI", ui-sans-serif, system-ui, -apple-system, sans-serif;
  --mono:"IBM Plex Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}}
* {{ box-sizing:border-box }}
html, body {{ margin:0; padding:0; background:#fff; color:var(--ink); font-family:var(--sans); font-size:8.6pt; line-height:1.38;
  -webkit-print-color-adjust:exact; print-color-adjust:exact }}
.page {{ width:210mm; height:297mm; position:relative; overflow:hidden; page-break-after:always; break-after:page;
  display:flex; flex-direction:column }}
.page:last-child {{ page-break-after:auto; break-after:auto }}
header {{ display:flex; align-items:center; justify-content:space-between; gap:6mm; padding:3.2mm 12mm; color:var(--text);
  background:linear-gradient(90deg, rgba(12,8,24,.55) 0%, rgba(12,8,24,.8) 22%, rgba(12,8,24,.88) 100%),
  url(brand_header.jpg) center 40%/cover, var(--panel) }}
.brand {{ display:flex; align-items:center; gap:2.6mm; color:var(--text) }}
.brand svg {{ width:9.5mm; height:9.5mm; flex:none }}
.brand span {{ display:flex; flex-direction:column; line-height:1.15 }}
.brand small {{ font-size:6.6pt; font-weight:600; letter-spacing:.12em; text-transform:uppercase; color:var(--z2a-cyan) }}
.brand b {{ font-size:12pt; letter-spacing:-.01em }}
header .tag {{ font-size:7.4pt; color:var(--muted); text-align:right; max-width:110mm }}
main {{ flex:1; padding:4.5mm 12mm 3mm; display:flex; flex-direction:column; gap:2.6mm; min-height:0; justify-content:space-between }}
.box {{ font-size:9.2pt }}
footer {{ display:flex; justify-content:space-between; gap:4mm; padding:2.6mm 12mm 4mm; font-size:6.8pt; color:var(--ink3);
  border-top:0.4mm solid var(--rule); margin:0 12mm; padding-left:0; padding-right:0 }}
h1 {{ margin:0; font-size:17pt; line-height:1.15; letter-spacing:-.01em; font-weight:700 }}
h2 {{ margin:0 0 1.4mm; font-size:9.6pt; font-weight:700; color:var(--ink); padding-bottom:.8mm;
  border-bottom:0.5mm solid var(--z2a-purple); display:inline-block }}
.titleblock .meta {{ margin-top:1.2mm; color:var(--ink2); font-size:8.2pt; display:flex; gap:3mm; flex-wrap:wrap; align-items:center }}
footer .nw {{ white-space:nowrap }}
footer {{ align-items:center }}
footer a.claude {{ background:#D97757; color:#fff; text-decoration:none; font-weight:600; padding:.2mm 2mm; border-radius:1mm; white-space:nowrap }}
.pill {{ display:inline-block; padding:.3mm 2.2mm; border-radius:99px; font-size:7.2pt; font-weight:600 }}
.pill.pre {{ background:var(--z2a-magenta); color:#fff }}
.pill.sim {{ background:var(--tint); color:var(--ink); border:0.3mm solid var(--rule) }}
p {{ margin:0 0 1.4mm }}
ul {{ margin:0; padding-left:4mm }} li {{ margin:0 0 .7mm }}
.cols {{ display:grid; grid-template-columns:1fr 1fr; gap:6mm }}
.cols3 {{ display:grid; grid-template-columns:62fr 124fr; gap:6mm }}
table {{ width:100%; border-collapse:collapse; font-size:7.4pt; line-height:1.3; font-variant-numeric:tabular-nums }}
thead th {{ text-align:left; font-weight:700; padding:1.1mm 1.6mm; border-bottom:0.5mm solid var(--ink) }}
thead th.a {{ color:{COL['A']} }} thead th.b {{ color:{COL['B']} }} thead th.pl {{ color:{COL['plain']} }}
tbody th {{ text-align:left; font-weight:500; color:var(--ink2); padding:.45mm 1.4mm; width:24% }}
tbody td {{ padding:.45mm 1.4mm }}
td.c {{ color:{COL['A']}; font-weight:600 }}
tbody tr:nth-child(odd) {{ background:var(--tint) }}
td.pl {{ color:var(--ink2) }}
figure {{ margin:0 }}
figure img {{ display:block; width:100% }}
figcaption {{ font-size:7.0pt; color:var(--ink2); margin-top:.6mm }}
.key {{ display:inline-block; width:4mm; height:1.1mm; border-radius:1mm; vertical-align:middle; margin:0 1mm 0 0 }}
.note {{ font-size:7.1pt; color:var(--ink2) }}
.box {{ background:var(--tint); border-left:0.8mm solid var(--z2a-purple); padding:2mm 3mm; border-radius:0 1.5mm 1.5mm 0 }}
.box.b {{ border-left-color:var(--z2a-magenta) }}
.box h3 {{ margin:0 0 1mm; font-size:8.6pt }}
ol {{ margin:0; padding-left:4.5mm }} ol li {{ margin-bottom:.9mm }}
</style></head><body>

<div class="page">
{page_head}
<main>
<div class="titleblock">
<h1>Tunable 433.92 MHz ring oscillator: GF180 candidate options</h1>
<div class="meta"><span>Matt Venn / Zero to ASIC Course</span><span>2026-11-07</span><span class="pill pre">Preliminary</span>
<span class="pill sim">Pre-silicon · schematic simulation (ngspice, gf180mcuD nfet/pfet_03v3) · not extracted</span></div>
</div>

<div class="cols">
<div>
<h2>Description</h2>
<p><b style="color:{COL['A']}">Option A</b> uses about {B['p434']/A['p434']:.1f}× less power than <b style="color:{COL['B']}">Option B</b>
and rejects supply changes about {sB[0]/sA[0]:.1f}× better; B gives the complementary outputs the antenna drive needs.
As drawn, both tune far too steeply with vctrl; a constant-gm bias fixes this. A plain inverter ring is the untuned baseline.</p>
<p>Both are current-starved ring VCOs (voltage-controlled oscillators) for a Tiny Tapeout GF180MCU transmitter. Each inverter's
current is set by a PMOS head and an NMOS foot of binary legs switched between <b>vctrl</b> and 0: the 4-bit <b>code</b> tunes
coarsely, vctrl finely. A is a 5-stage single-ended (SE) ring; B is two 4-stage rings tied by weak cross-coupled inverters.</p>
</div>
<div>
<h2>Features</h2>
<ul>
<li>Coarse: 4-bit binary foot legs (k = 8 base), ×{A['cr']:.2f} (A) / ×{B['cr']:.2f} (B) at vctrl 1.5 V</li>
<li>Fine: vctrl on every leg; {fmt(A['fmin']/1e6)}–{fmt(A['fmax']/1e6)} MHz (A), {fmt(B['fmin']/1e6)}–{fmt(B['fmax']/1e6)} MHz (B)</li>
<li>Power at 433.92 MHz: A {A['p434']*1e3:.2f} mW, B {B['p434']*1e3:.2f} mW (plain ring {PR[('typical',27,3.3)][1]*1e3:.2f} mW)</li>
<li>A + constant-gm bias (a β-multiplier, whose current is set by an on-chip resistor, not vctrl): 5-bit coarse,
 ±{C['fine']:.1f} % fine; Kvco (frequency change per volt of vctrl) about {C['k']:.0f} MHz/V vs {fmt(A['k434'])} for A</li>
<li>3.3 V devices only, no inductors, small area</li>
</ul>
</div>
</div>

<figure><img src="fig0_topology.svg" alt="stage and ring topologies"></figure>

<div>
<h2>Key specifications</h2>
<table><thead><tr><th>tt, 27 °C, 3.3 V unless noted</th><th class="a">A · SE N=5</th>
<th class="b">B · diff N=4</th><th class="a">A + const-gm bias</th><th class="pl">Plain ring (baseline)</th></tr></thead>
<tbody>{trows}</tbody></table>

</div>

<figure><img src="fig1_f_vs_vctrl.svg" alt="frequency vs vctrl">
<figcaption><b>Fig. 1.</b> Frequency vs vctrl for codes 0, 3, 7, 11, 15 (light → dark), tt 27 °C 3.3 V; at code 7, A reaches
433.92 MHz at {A['v434']:.2f} V and B at {B['v434']:.2f} V. Points below about 110 MHz are outside the measurement window (10 periods in 100–200 ns) and are not plotted.{" " + ", ".join(sorted(COARSE)) + ": coarse sweep (codes 0/7/15, vctrl 0.9/1.2/1.5/2.0/2.5/3.3 V), so its curves and Kvco are coarse." if COARSE else ""}</figcaption></figure>
</main>
{foot(1)}
</div>

<div class="page">
{page_head}
<main>
<div class="cols">
<figure><img src="fig2_kvco.svg" alt="Kvco vs vctrl">
<figcaption><b>Fig. 2.</b> Kvco vs vctrl: about {fmt(A['k434'])} MHz/V for A at 433.92 MHz, about {C['k']:.0f} MHz/V with constant-gm bias (black). <span class="key" style="background:{COL['A']}"></span>A solid,
<span class="key" style="background:{COL['B']}"></span>B dashed; code 7 bold, codes 0 and 15 faint.</figcaption></figure>
<figure><img src="fig5_power.svg" alt="power vs frequency">
<figcaption><b>Fig. 3.</b> Supply power vs frequency for every code: A draws {A['p434']*1e3:.2f} mW at 433.92 MHz, B {B['p434']*1e3:.2f} mW.
The plain ring draws about {PR[('typical',27,3.3)][1]*1e3:.1f} mW whatever N is.</figcaption></figure>
</div>

<div class="cols3">
<figure><img src="fig4_sensitivity.svg" alt="supply and temperature sensitivity">
<figcaption><b>Fig. 4.</b> Supply sensitivity (±150 mV) and tempco (0–70 °C, fixed vctrl) at tt; A is lowest at {fmt(sA[0],2)} %/10 mV.</figcaption></figure>
<figure><img src="fig3_pvt.svg" alt="PVT spread">
<figcaption><b>Fig. 5.</b> PVT (process, voltage, temperature) spread, each normalised to its own tt 27 °C 3.3 V; A spans ×{sA[2]:.2f} to ×{sA[3]:.2f}. A and B at code 7, vctrl 1.5 V.</figcaption></figure>
</div>

<div>
<h2>Trade-offs</h2>
<div class="cols">
<div class="box"><h3 style="color:{COL['A']}">Option A: single-ended, N=5</h3><ul>
<li>Lower power: {A['p434']*1e3:.2f} mW at 433.92 MHz vs {B['p434']*1e3:.2f} mW for B
 ({A['p434']/F0*1e9*1e3:.2f} vs {B['p434']/F0*1e9*1e3:.2f} µW/MHz).</li>
<li>Better supply rejection (PSRR): {fmt(sA[0],2)} vs {fmt(sB[0],2)} %/10 mV, opposite in sign to the plain ring as the current is fixed and the swing is VDD.</li>
<li>Kvco at 433.92 MHz (code 7): {fmt(A['k434'])} MHz/V vs {fmt(B['k434'])} for B{" (lower)" if A['k434'] < B['k434'] else " (higher: A sits lower on its curve, at " + f"{A['v434']:.2f} V)"}.</li>
<li>One output only: the antiphase antenna drive needs an extra inverter, which adds skew.</li>
</ul></div>
<div class="box b"><h3 style="color:{COL['B']}">Option B: pseudo-differential, N=4</h3><ul>
<li>Complementary outputs a0 / b0 for the antiphase antenna drive, no extra splitter.</li>
<li>Possibly less flicker upconversion (low-frequency transistor noise turned into phase noise), as symmetric waveforms give a smaller
 ISF (impulse sensitivity function) average; <b>needs a phase-noise simulation</b>.</li>
<li>No tail current source, so supply rejection is about {abs(sB[0]/sA[0]):.1f}× worse than A.</li>
<li>About {B['p434']/A['p434']:.1f}× the power of A at 433.92 MHz and {B['ndev']/A['ndev']:.1f}× the devices{"; steeper Kvco" if B['k434'] > A['k434'] else ""}.</li>
</ul></div>
</div>
</div>

<p class="note">Sizes: core Wn/Wp 2/5 µm, L 0.28 µm; starving L 1 µm. Plain-ring figures from N=15. Tuning span: codes 0–15, vctrl 1.0–3.3 V
(A + const-gm: codes 0–31, vctrl 0–3.3 V; PVT and sensitivities at code 15, vctrl 1.65 V). Data: <code>sim/vco/</code>.
Regenerate: <code>python3 docs/datasheet/make_datasheet.py</code>.</p>
</main>
{foot(2)}
</div>
</body></html>
"""
    out = HERE / "datasheet.html"
    out.write_text(html)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    "--virtual-time-budget=4000", f"--print-to-pdf={PDF}", out.as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"wrote {PDF}")
    print("\nKey numbers")
    for r in rows:
        print("  " + " | ".join(r))


if __name__ == "__main__":
    build()
