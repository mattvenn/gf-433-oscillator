#!/usr/bin/env python3
"""Fig. for docs/pad_model.md from build/pad/*.dat (run the sims first, see docs/pad_model.md)."""
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
B = REPO / "build" / "pad"
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2))
for c, col in zip(["tt", "ss", "ff", "sf", "fs"], ["k", "tab:blue", "tab:red", "tab:green", "tab:orange"]):
    d = np.loadtxt(B / f"tb_rdson_{c}.dat")
    a.plot(d[:, 0], d[:, 1], color=col, lw=2 if c == "tt" else 1.2, label=f"{c}  (peak {d[:, 1].max():.1f} Ω)")
a.set(xlabel="signal DC level (V)", ylabel="switch on-resistance (Ω)", title="tt_asw_5v0, 27 °C, VAPWR = VDPWR = 3.3 V")
a.grid(alpha=.3); a.legend(fontsize=8)
for f, lab, col in [("tb_pad_tt_VCM1.65_RROUTE15_NOFF3", "tt, Rroute 15 Ω", "k"),
                    ("tb_pad_tt_VCM1.65_RROUTE60_NOFF3", "tt, Rroute 60 Ω", "tab:gray"),
                    ("tb_pad_ss_VCM2.03_RROUTE60_NOFF3", "ss, 60 Ω, 2.03 V (worst)", "tab:blue")]:
    d = np.loadtxt(B / f"{f}.dat")
    b.semilogx(d[:, 0], d[:, 1], color=col, ls="-", label=f"in: 50 Ω gen → mod, {lab}")
    b.semilogx(d[:, 0], d[:, 3], color=col, ls="--", label=f"out: mod → 50 Ω load, {lab}")
b.axvline(433.92e6, color="tab:red", lw=.8); b.text(440e6, -14, "433.92 MHz", color="tab:red", fontsize=8)
b.axhline(-3, color="k", lw=.5, ls=":")
b.set(xlabel="frequency (Hz)", ylabel="gain relative to 1 MHz (dB)", ylim=(-20, 2),
      title="pin path, 3 off switches on the pin (ttgf0p3 worst), 1.65 V")
b.grid(alpha=.3, which="both"); b.legend(fontsize=7, loc="lower left")
fig.tight_layout()
out = REPO / "docs" / "img" / "pad_model.png"
fig.savefig(out, dpi=130); print(out)
