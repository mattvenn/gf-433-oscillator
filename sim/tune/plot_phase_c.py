#!/usr/bin/env python3
"""Fig. 3 of docs/tx_fine_tune.md from the phase C runs (sim/tune/phase_c.py).

    python3 sim/tune/plot_phase_c.py [--dir build/tx_fine/pexdac]     -> docs/img/tx_fine_phase_c.png

(a) FSK step (c5), (b) mean f against the SD fraction (c2), both from --dir (default: the extracted-DAC runs);
(c) the phase spectrum with the macro's measured clock charge on the tile supply (c4q, schematic DAC): r10 (no clock
gating) against r12 (clock-gated).
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/tune")); sys.path.insert(0, str(REPO / "tools"))
import phase_c as pc  # noqa: E402
from rawread import read_raw  # noqa: E402


def phase_spectrum(raw):
    pl = read_raw(raw)[0]["vars"]
    t = np.real(pl["time"])
    tc = pc.crossings(t, np.real(pl["v(a0)"]), 0.25e-6)
    k = np.arange(len(tc)); a, b = np.polyfit(k, tc, 1)
    phi = -2 * math.pi * (tc - (a * k + b)) / a
    wn = np.hanning(len(phi))
    return np.fft.rfftfreq(len(phi), d=a), np.abs(np.fft.rfft((phi - phi.mean()) * wn)) / wn.sum()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(REPO / "build/tx_fine/pexdac"))
    a = ap.parse_args()
    d = Path(a.dir)
    r = json.loads((d / "phase_c.json").read_text())
    tag = "extracted DAC" if "pexdac" in str(d) else "schematic DAC"
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
    # (a) FSK step
    pl = read_raw(d / "c5/fsk/out.raw")[0]["vars"]; t = np.real(pl["time"])
    tc = pc.crossings(t, np.real(pl["v(a0)"]), 0.25e-6); tm, f = pc.freq_track(tc)
    w = 20e-9; e = np.arange(0.3e-6, 3.0e-6, w); fw = [f[(tm >= x) & (tm < x + w)].mean() for x in e]
    ax[0].plot((e + w / 2) * 1e6, (np.array(fw) - r["c5"]["f_lo"]) / 1e3, ".-", ms=3)
    ax[0].set(xlabel="time (µs)", ylabel="f − f(word 509) (kHz, 20 ns windows)",
              title=f"FSK 509 → 515 → 509, step {r['c5']['dev']/1e3:.1f} kHz ({tag})")
    ax[0].grid(alpha=.3)
    # (b) SD mean frequency against the fraction
    c2 = r["c2"]; lsb = c2["lsb"]
    xs = [0, 77 / 256, 128 / 256, 1]
    ys = [0, (c2["f77"]["f"] - c2["w512"]["f"]) / 1e3, (c2["f128"]["f"] - c2["w512"]["f"]) / 1e3, lsb / 1e3]
    xx = np.linspace(0, 1, 101)
    ax[1].plot(xx, xx * lsb / 1e3, "k--", lw=.8, label="linear (static LSB)")
    ax[1].plot(xs, ys, "o-", label="transistor level")
    ax[1].set(xlabel="fraction x", ylabel="f − f(word 512) (kHz)", title=f"ΣΔ cell, 25 MHz clock ({tag})")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
    # (c) supply coupling, measured clock charge: r10 against r12
    q = json.loads((REPO / "build/tx_fine/c4q.json").read_text())
    for k, lab, col in (("q_r10", "r10, no clock gating", "0.6"), ("q_r12", "r12, clock-gated", "C0")):
        fr, S = phase_spectrum(REPO / "build/tx_fine/c4" / k / "out.raw")
        sel = (fr > 0.5e6) & (fr < 60e6)
        s25 = q[k]["spur_25m"][1]
        ax[2].plot(fr[sel] / 1e6, 20 * np.log10(S[sel] + 1e-12), lw=.8, color=col,
                   label=f"{lab}: {q[k]['qclk']*1e12:.1f} pC/cycle, {s25:.1f} dBc")
    ax[2].axhline(-40, color="k", ls="--", lw=.8)
    ax[2].set(xlabel="offset (MHz)", ylabel="phase line (dBc, one sideband)",
              title="Macro clock charge on the tile supply (1.32 Ω)", ylim=(-110, -20))
    ax[2].legend(fontsize=8, loc="upper left"); ax[2].grid(alpha=.3)
    fig.tight_layout()
    out = REPO / "docs/img/tx_fine_phase_c.png"
    fig.savefig(out, dpi=130)
    print(out)


if __name__ == "__main__":
    main()
