#!/usr/bin/env python3
"""Fig. 2 of docs/pad_model.md: the xschem pad model's switch Rdson against tnt's tb_rdson plot, and the same sweep
through the whole pin. Data: tb_rdson / tb_pad_rdc run on the xschem netlist (sim/pad/check_xsch.py makes it):
  tools/osic-mac python3 sim/pad/run.py tb_rdson tt MODELS=$PWD/build/xsch/pad_model_gf180_sim.spice
  tools/osic-mac python3 sim/pad/run.py tb_pad_rdc tt RROUTE=15 MODELS=...   (and RROUTE=60)
"""
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
B = REPO / "build" / "pad"
S = "MODELSpad_model_gf180_sim"
# read by eye off tnt's ngspice plot ((v(mod) - v(bus)) / 100u, schematic), 2026-11-09; about +-0.2 ohm
TNT = [(0, 11.3), (0.2, 12.3), (0.4, 13.5), (0.6, 15.0), (0.8, 17.0), (1.0, 19.6), (1.2, 23.3), (1.4, 28.8),
       (1.5, 30.9), (1.6, 31.5), (1.7, 32.0), (1.8, 33.2), (1.9, 35.0), (2.04, 36.9), (2.2, 32.4), (2.4, 26.3),
       (2.6, 22.4), (2.8, 19.5), (3.0, 17.4), (3.2, 15.7), (3.3, 14.9)]

sw = np.loadtxt(B / f"tb_rdson_tt_{S}.dat")
fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6))
a.set_facecolor("black")
a.plot(sw[:, 0], sw[:, 1], color="red", lw=1.6, label="xschem tt_asw_5v0 (this repo)")
tv, tr = zip(*TNT)
a.plot(tv, tr, "o", mfc="none", mec="white", ms=6, label="tnt's plot (read off the screenshot)")
a.set(xlim=(0, 3.4), ylim=(11, 37.5), xlabel="v-sweep (V)", ylabel="(v(mod) − v(bus)) / 100 µA  (Ω)",
      title="switch alone, tt 27 °C: 36.9 Ω at 2.03 V, 11.3 Ω at 0 V")
a.grid(color="white", ls=":", lw=.6, alpha=.6)
a.legend(fontsize=8, facecolor="#222", labelcolor="white", loc="upper left")
b.plot(sw[:, 0], sw[:, 1], color="k", lw=1.2, label="switch alone")
for r, col in ((15, "tab:blue"), (60, "tab:red")):
    d = np.loadtxt(B / f"tb_pad_rdc_tt_RROUTE{r}_{S}.dat")
    b.plot(d[:, 0], d[:, 1], color=col, lw=1.6, label=f"pin → mod, Rroute {r} Ω (peak {d[:, 1].max():.1f} Ω)")
b.set(xlim=(0, 3.4), ylim=(0, 105), xlabel="signal DC level (V)", ylabel="DC resistance (Ω)",
      title="xschem pad_model_gf180: + 1 Ω package + routing")
b.grid(alpha=.3); b.legend(fontsize=8, loc="upper left")
fig.tight_layout()
out = REPO / "docs" / "img" / "pad_model_vs_tnt.png"
fig.savefig(out, dpi=130); print(out)
