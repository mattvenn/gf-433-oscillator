#!/usr/bin/env python3
"""One-page bench report for tt_um_algofoogle_vgaringosc (ttgf0p2), measured 2026-11-09.

Reads raw/sweep_div8.csv (main /8 sweep) and raw scope screenshots; writes
  fig1_freq_vs_stages.png       (the plot)
  vgaringosc_ttgf0p2_report.pdf (one A4 page)
Needs matplotlib + Pillow.
"""
import csv
import collections
import os
import textwrap

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")

# ---------------------------------------------------------------- data
rings = collections.defaultdict(list)
clksel_of = {}
for r in csv.DictReader(open(os.path.join(RAW, "sweep_div8.csv"))):
    if r["ring"] == "inv4x5":
        continue  # invalid: uio[1] net held low (location not isolated), this was really inv_2 x33
    rings[r["ring"]].append(float(r["f_ring_Hz"]))
    clksel_of[r["ring"]] = (int(r["clksel2"]), int(r["clksel"]))

taps = sorted((int(k[5:]), k) for k in rings if k.startswith("inv2x"))
N = np.array([n for n, _ in taps])
f_med = np.array([np.median(rings[k]) for _, k in taps])
spread = np.array([(max(rings[k]) - min(rings[k])) / np.mean(rings[k]) * 100 for _, k in taps])
T_ns = 1e9 / f_med
slope, icpt = np.polyfit(N, T_ns, 1)
resid = T_ns - (slope * N + icpt)

f1 = rings["inv1x5"]
f1_med = np.median(f1)
f1_spread = (max(f1) - min(f1)) / np.mean(f1) * 100

# ---------------------------------------------------------------- Fig. 1
def make_plot(ax):
    ax.semilogx(N, f_med / 1e6, "o", color="#1f5fa8", ms=4.5, label="inv_2 tapped ring (measured)")
    nn = np.logspace(np.log10(2.5), np.log10(200), 200)
    ax.semilogx(nn, 1e3 / (slope * nn + icpt), "-", color="#888888", lw=1,
                label=f"fit T = {slope:.3f} ns·N + {icpt:.2f} ns")
    ax.semilogx([5], [f1_med / 1e6], "s", color="#c0392b", ms=6, mfc="none", mew=1.5,
                label="separate fixed 5× inv_1 ring (clksel2 = 1)")
    for n, f in zip(N, f_med):
        ax.annotate(f"{f/1e6:.0f}", (n, f / 1e6), textcoords="offset points", xytext=(4, 3), fontsize=6)
    ax.annotate(f"{f1_med/1e6:.0f} MHz: fixed 5× inv_1 ring", (5, f1_med / 1e6), textcoords="offset points",
                xytext=(6, -2), fontsize=6, color="#c0392b")
    ax.set_xlabel("ring length N (inverter stages)", fontsize=7.5)
    ax.set_ylabel("ring frequency (MHz)", fontsize=7.5)
    ax.set_xticks([3, 5, 9, 17, 33, 65, 161])
    ax.set_xticklabels(["3", "5", "9", "17", "33", "65", "161"])
    ax.set_ylim(0, 350)
    ax.tick_params(labelsize=6.5)
    ax.grid(True, which="both", lw=0.3, alpha=0.5)
    ax.legend(fontsize=6, loc="lower left", frameon=False)


fig_s, ax_s = plt.subplots(figsize=(5, 3.3), dpi=200)
make_plot(ax_s)
fig_s.tight_layout()
fig_s.savefig(os.path.join(HERE, "fig1_freq_vs_stages.png"))
plt.close(fig_s)

# ---------------------------------------------------------------- scope crops
def crop(name, wave_box, table_box):
    """Stack the waveform area and the measurement table of a 1280x800 capture."""
    im = Image.open(os.path.join(RAW, name)).convert("RGB")
    a = im.crop(wave_box)
    b = im.crop(table_box)
    out = Image.new("RGB", (max(a.width, b.width), a.height + b.height + 4), (0, 0, 0))
    out.paste(a, (0, 0))
    out.paste(b, (0, a.height + 4))
    return np.asarray(out)


WAVE, TABLE = (0, 60, 1270, 560), (0, 612, 812, 760)  # same crop for every capture -> equal heights
shots = [
    (crop("scope_cs15.png", WAVE, TABLE),
     "Fig. 2. Raw pin uio[4], clksel = 15 (161 stages), 20 ns/div. "
     "Scope mean 23.728 MHz, s.d. 13.8 kHz over 12.3 k cycles."),
    (crop("d8_inv2x3_noch2.png", WAVE, TABLE),
     "Fig. 3. ÷8 output uio[7], clksel = 2 (3 stages), 10.9 ns/div. "
     "Scope mean 27.66 MHz ×8 = 221.3 MHz over 11.4 k cycles."),
    (crop("fin_harm_0.png", WAVE, TABLE),
     "Fig. 4. ÷8 output, 161 stages entered from clksel = 2 without reset: "
     "9.05 MHz ×8 = 72.4 MHz, the 3rd-harmonic mode (3.06× the 23.7 MHz fundamental)."),
]

# ---------------------------------------------------------------- page
W, H = 8.27, 11.69
fig = plt.figure(figsize=(W, H))
L, R = 0.06, 0.94


def text(x, y, s, **kw):
    kw.setdefault("fontsize", 8)
    kw.setdefault("va", "top")
    fig.text(x, y, s, **kw)


def para(x, y, s, width, lh=0.0125, **kw):
    lines = textwrap.wrap(s, width)
    for i, ln in enumerate(lines):
        text(x, y - i * lh, ln, **kw)
    return y - len(lines) * lh


text(L, 0.975, "Ring osc on VGA (tt_um_algofoogle_vgaringosc): silicon measurements",
     fontsize=13, weight="bold")
text(L, 0.953, "Tiny Tapeout (TT) GF180MCU shuttle ttgf0p2, mux address 614  ·  "
     "Measured by Matt Venn, 2026-11-09", fontsize=8.5, color="#333333")
TT_URL = "https://tinytapeout.com/chips/ttgf0p2/tt_um_algofoogle_vgaringosc"
text(L, 0.939, "Project page: " + TT_URL, fontsize=8, color="#1a5fb4", url=TT_URL)
y = para(L, 0.922,
         "Chip 1 (ROM commit ff701baa) unless noted. Setup: TT demo board TTDBv3 (RP2350 microcontroller, TT SDK 3.1.1), ttgf0p2 carrier v0.1, "
         "VDD_CORE = 3.300 V (demo-board 3V3 through 0 Ω links; carrier regulator U1 not fitted), project clock "
         "25.25 MHz from the RP2350, room temperature (not controlled). Keysight HD304MSO oscilloscope, 10:1 probe, "
         "3.2 GSa/s. Ring frequency = 8 × median of 30 single-period readings of the ÷8 output uio[7]; each "
         "configuration run 3 times with a project reset between. Check: clksel = 0 gives 25.2524 MHz (0.01 % from the "
         "RP2350 clock), and ÷8 × 8 agrees with direct raw-pin readings within 0.25 %.", 132, fontsize=7.5)

# summary line
y = para(L, y - 0.006,
         f"Result: the rings run from {f_med[-1]/1e6:.1f} MHz (161 stages) to {f_med[0]/1e6:.1f} MHz (3 stages); "
         f"the fixed 5× inv_1 ring runs at about {f1_med/1e6:.0f} MHz. Period fits T = {slope:.3f} ns × N + "
         f"{icpt:.2f} ns: about {slope/2*1000:.0f} ps per inv_2 stage (T = 2·N·t_pd) plus about {icpt:.1f} ns fixed "
         f"loop overhead (tap multiplexer and clock buffer). Your docs expected about 15 to 350 MHz.",
         112, fontsize=8, weight="bold")

# table
top = y - 0.012
tab_ax = fig.add_axes([L, top - 0.33, 0.36, 0.33])
tab_ax.axis("off")
rows = []
for (n, k), f, s, r in zip(taps, f_med, spread, resid):
    cs2, cs = clksel_of[k]
    rows.append([str(cs), f"{n}", f"{f/1e6:.2f}", f"{s:.2f}", f"{r:+.2f}"])
rows.append(["10*", "5 (inv_1)", f"{f1_med/1e6:.1f}", f"{f1_spread:.1f}", "–"])
tbl = tab_ax.table(cellText=rows,
                   colLabels=["clksel", "stages N", "f (MHz)", "restart\nspread %", "fit resid.\n(ns)"],
                   loc="upper center", cellLoc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(7)
tbl.scale(1, 1.08)
for (rr, cc), cell in tbl.get_celld().items():
    cell.set_linewidth(0.3)
    if rr == 0:
        cell.set_height(cell.get_height() * 1.7)
        cell.set_facecolor("#e8eef6")
        cell.set_text_props(weight="bold")
    if rr == len(rows):
        cell.set_text_props(color="#c0392b")
fig.canvas.draw()
tb = tbl.get_window_extent(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted())
text(L, tb.y0 - 0.006,
     "Table 1. Median ring frequency per tap (3 restarts). *clksel2 = 1, clksel = 10.\n"
     "Spread = (max − min) / mean of the 3 restart medians.", fontsize=6.5, color="#333333")

# plot
pax = fig.add_axes([0.52, top - 0.285, 0.43, 0.27])
make_plot(pax)
para(0.48, top - 0.315,
     f"Fig. 1. Ring frequency vs. ring length. Measured {f_med[-1]/1e6:.1f} MHz at 161 stages to "
     f"{f_med[0]/1e6:.1f} MHz at 3 stages; fit residuals {resid.min():+.2f} to {resid.max():+.2f} ns "
     f"(ring segments differ). Red square: separate fixed 5× inv_1 ring (clksel2 = 1), {f1_med/1e6:.0f} MHz, not part of the tapped ring.",
     78, lh=0.011, fontsize=6.5, color="#333333")

# waveforms
wy = top - 0.37
wh = 0.105
ww = (R - L - 0.04) / 3
for i, (img, cap) in enumerate(shots):
    x = L + i * (ww + 0.02)
    a = fig.add_axes([x, wy - wh, ww, wh])
    a.imshow(img, interpolation="none")  # embed full-resolution capture in the PDF
    a.set_aspect("equal")
    a.axis("off")
    a.set_anchor("N")
    ih = ww * W * img.shape[0] / img.shape[1] / H  # drawn image height (figure fraction)
    para(x, wy - ih - 0.006, cap, 48, lh=0.0105, fontsize=6.3, color="#333333")

# notes
ny = wy - wh - 0.05
text(L, ny, "Notes / limits", fontsize=9, weight="bold")
notes = [
    "Multi-mode locking: switching to the 161-stage ring without a reset gave the 3rd-harmonic mode (about 72.5 MHz, "
    "3.06× the fundamental) in 3 of 8 tries, plus once earlier the same day. With a reset after each change: 12/12 "
    "fundamental (23.67 to 23.70 MHz). Advice for users: reset after changing clksel.",
    f"5× inv_1 ring ({f1_med/1e6:.0f} MHz) is the least certain point: single readings spread widely at this speed, "
    "and the 3-bit counter clocked at a 3.1 ns period may be marginal.",
    "Raw pin uio[4] works only up to about 50 MHz with a standard probe (it agrees with ÷8 × 8 within 0.25 % for "
    "clksel 13 to 15); the 5× inv_1 ring does not toggle it at all. Pad edges at 3.3 V: rise 1.82 ns, fall 1.19 ns "
    "(10 to 90 %).",
    "The ÷2/÷4/÷8 counter is held in reset during VGA horizontal blanking, so the ÷8 output has a gap each line; "
    "single-period readings near the trigger are not biased by it.",
    "Pin fault on chip 1: the uio[1] pad (clksel2[1]) is shorted to ground. The RP2350 cannot pull it high, the same "
    "RP2350 pin toggles with the carrier removed, and the bond wires look intact. So clksel2 = 2 and 3 were measured "
    "on chip 2 only. Tip for TT SDK users: after enabling the project, uio[0]/uio[1] stayed RP2350 inputs despite "
    "uio_oe_pico = 0b11; set them with Pin.OUT.",
    "Chip 2 (second carrier, ROM commit 7416232b): only ui_in[1], ui_in[7] and uio[0..3] reach the chip (the other "
    "inputs are held low), so only the 3-stage tap, the fixed rings and the clock paths could be selected. "
    "3 stages: 216.0 MHz (chip 1: 220.5 MHz, −2.0 %). 5× inv_1: 311.6 MHz (chip 1: 319.6 MHz, −2.5 %). "
    "clksel2 = 3 (!clk): 25.252 MHz, as expected. 5× inv_4: median 206.5 MHz over 3 restarts, but the ÷8 output is "
    "irregular (duty 23 to 92 %), so the counter may be miscounting; treat this value as unconfirmed.",
    "Not tested: VGA output (no VGA PMOD or monitor), altclk path with a clock (with ui_in[4] static there are no edges, "
    "as expected). Full tap sweep on chip 1 only; one supply voltage, room temperature only.",
]
y = ny - 0.016
for nt in notes:
    lines = textwrap.wrap(nt, 138)
    text(L, y, "•", fontsize=7.2)
    for j, ln in enumerate(lines):
        text(L + 0.015, y - j * 0.0118, ln, fontsize=7.2)
    y -= len(lines) * 0.0118 + 0.003

# footer
fig.add_artist(plt.Line2D([L, R], [0.03, 0.03], lw=0.4, color="#999999"))
text(L, 0.026, "Design source: github.com/algofoogle/ttgf0p2-vga-ring-osc (commit cdefb8e).",
     fontsize=6.3, color="#555555", url="https://github.com/algofoogle/ttgf0p2-vga-ring-osc")
text(L, 0.015, "Raw data and scope captures: https://github.com/mattvenn/ttgf0p2-vgaringosc-measurements",
     fontsize=6.3, color="#1a5fb4", url="https://github.com/mattvenn/ttgf0p2-vgaringosc-measurements")
text(R, 0.025, "Made with Claude", fontsize=6.5, color="#555555", ha="right",
     bbox=dict(boxstyle="round,pad=0.25", fc="#f3efe6", ec="#c96442", lw=0.6))

with PdfPages(os.path.join(HERE, "vgaringosc_ttgf0p2_report.pdf")) as pdf:
    pdf.savefig(fig)
print(f"fit: T = {slope:.4f} ns*N + {icpt:.3f} ns; resid {resid.min():+.2f}..{resid.max():+.2f} ns")
