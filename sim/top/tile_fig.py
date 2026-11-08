#!/usr/bin/env python3
"""Floorplan figure: vco_top in the Tiny Tapeout GF180 analog tile -> docs/img/vco_top_tile.png

    python3 sim/top/tile_fig.py

Tile facts (tt-support-tools main, tech/gf180mcuD, fetched 2026-11-08): tile_sizes.yaml 1x2 = 346.64 x 325.36 um,
2x2 = 711.20 x 325.36 um; def/analog/tt_analog_2x2.def: ua[0..7] Metal4 pads 6 x 2 um on the bottom edge
(x = 327.32 ... 21.56 um), the digital pins (ui_in, uo_out, uio_*, clk, ena, rst_n) Metal4 1.2 x 2 um on the top
edge; def/analog/magic_init_project.tcl: the power stripes are drawn by the designer (Metal4, vertical, y 5 ...
320.36 um, width >= 0.8 um; template default VDPWR at x 1 um and VGND at x 4 um, 2 um wide).
Macro geometry from build/top/meta.json (layout/gen/vco_top.py).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[2]
META = json.loads((REPO / "build/top/meta.json").read_text())
W2, W1, H = 711.20, 346.64, 325.36
UA_X = [654640, 567280, 479920, 392560, 305200, 217840, 130480, 43120]     # 2x2 DEF, units 2000/um
DIG_X = [662480, 677040, 647920] + [633360 - 14560 * i for i in range(8)] + [516880 - 14560 * i for i in range(8)] \
    + [400400 - 14560 * i for i in range(8)] + [283920 - 14560 * i for i in range(8)] + [167440 - 14560 * i for i in range(8)]
OX, OY = 20.0, 14.0           # proposed macro offset: lower-left of the macro bbox in the tile


def main():
    bb = META["bbox"]
    dx, dy = OX - bb[0], OY - bb[1]                    # macro coords -> tile coords
    fig, ax = plt.subplots(figsize=(14, 7.2))
    ax.add_patch(Rectangle((0, 0), W2, H, fill=False, lw=1.6, ec="#222"))
    ax.add_patch(Rectangle((0, 0), W1, H, fill=False, lw=1.2, ec="#b03030", ls="--"))
    ax.text(W1 - 3, 140, "1x2 tile edge\n(346.64 µm)", color="#b03030", ha="right", va="top", fontsize=9)
    ax.text(W2 - 3, H - 8, "2x2 tile 711.20 × 325.36 µm", color="#222", ha="right", va="top", fontsize=9)
    for x in UA_X:
        x /= 2000
        ax.add_patch(Rectangle((x - 3, 0), 6, 2, color="#2a7ab0"))
    for i, x in enumerate(UA_X):
        ax.text(x / 2000, 4, f"ua[{i}]", ha="center", va="bottom", fontsize=7, color="#2a7ab0")
    for x in DIG_X:
        ax.add_patch(Rectangle((x / 2000 - 0.3, H - 2), 0.6, 2, color="#666"))
    ax.text(W2 / 2 + 80, H - 12, "digital pins (ui_in, uo_out, uio_*, clk, ena, rst_n): Metal4, top edge", ha="center",
            fontsize=8, color="#555")
    # Metal4 power stripes: the template default + proposed ones over the macro
    stripes = [(1, "VDPWR", "#c0392b", "default"), (4, "VGND", "#2c3e50", "default")]
    xs_vdd = META["place"]["cgm_ref"][0] / 1000 + 200 + dx          # over the macro's VDD M3 strap (top edge)
    vls = [p for p in META["pins"]["VDD_LS"]][0][0] + dx
    stripes += [(xs_vdd, "VDPWR", "#c0392b", "proposed"), (xs_vdd + 6, "VGND", "#2c3e50", "proposed"),
                (vls, "VDPWR / VAPWR\n(VDD_LS branch)", "#d35400", "proposed")]
    for x, n, col, kind in stripes:
        ax.add_patch(Rectangle((x - 1, 5), 2, H - 10, color=col, alpha=0.85 if kind == "default" else 0.45))
        ax.text(x + (2.5 if n != "VDPWR" or kind == "default" and x > 2 else -14), 200 if kind == "proposed" else 120,
                f"{n} Metal4 ({kind})", fontsize=7, color=col, rotation=90, va="bottom")
    # macro + blocks
    cols = dict(decap_ls="#f3d9a4", lsdiv="#b8e0c8", ring_core="#f5b7b1", cgm_ref="#c9d7f0")
    labels = dict(decap_ls="VDD_LS decap\n10 pF", lsdiv="lsdiv\n(LS + ÷4)", ring_core="ring_core_v3",
                  cgm_ref="cgm_ref (bias + 1 MΩ / 20 pF)")
    for n, (px, py) in META["place"].items():
        b = list(META["blocks"][n])
        if n == "decap_ls":                              # the finger area only (its VSS rail runs on under lsdiv)
            b[2] = META["decap"]["xr"] / 1000
        x0, y0 = px / 1000 + b[0] + dx, py / 1000 + b[1] + dy
        ax.add_patch(Rectangle((x0, y0), b[2] - b[0], b[3] - b[1], fc=cols[n], ec="#333", lw=0.8))
        ax.text(x0 + (b[2] - b[0]) / 2, y0 + (b[3] - b[1]) / 2, labels[n], ha="center", va="center", fontsize=8)
    ax.add_patch(Rectangle((bb[0] + dx, bb[1] + dy), bb[2] - bb[0], bb[3] - bb[1], fill=False, ec="#000", lw=1.4))
    ax.text(bb[0] + dx, bb[3] + dy + 3, f"vco_top {bb[2] - bb[0]:.1f} × {bb[3] - bb[1]:.1f} µm (no Metal4/5 inside)",
            fontsize=9, va="bottom")
    for n, pts in META["pins"].items():
        x, y = pts[0]
        ax.plot(x + dx, y + dy, "k.", ms=3)
    sides = [("bit0-4, bitb0-4, ck, VDD_LS, VDD: M3, top edge", (META["pins"]["bit0"][0][0] + dx, bb[3] + dy + 12)),
             ("vctrl, vbn: M2, right edge", (bb[2] + dx + 3, 30)), ("vg: M3, bottom edge", (29 + dx + 3, bb[1] + dy + 2))]
    for s, (x, y) in sides:
        ax.text(x, y, s, fontsize=8, color="#333")
    ax.set_xlim(-10, W2 + 10); ax.set_ylim(-12, H + 10); ax.set_aspect("equal")
    ax.set_xlabel("x (µm)"); ax.set_ylabel("y (µm)")
    ax.set_title("vco_top in the TT GF180 analog 2x2 tile (analog pins ua[] on the bottom edge)", fontsize=11)
    fig.tight_layout()
    out = REPO / "docs/img/vco_top_tile.png"
    fig.savefig(out, dpi=130)
    print("wrote", out)


if __name__ == "__main__":
    main()
