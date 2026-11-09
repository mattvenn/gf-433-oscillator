# Platform facts (TT GF180, ttgf26c)

Each entry says where it comes from: **[repo]** a file in a repo, **[sim]** our simulation,
**[silicon]** a bench measurement, **[assumed]** not confirmed yet, **[open]** a question for Matt.

## Process and tile
| Item | Value | Source |
|---|---|---|
| PDK | gf180mcuD, 5 metal layers. Devices: nfet/pfet_03v3 (L ≥ 0.28 µm) and 06v0 | [repo] `.github/workflows/gds.yaml` |
| Tools | `hpretl/iic-osic-tools:2026.05`: magic 8.3.642, netgen 1.5.319, ngspice-46, KLayout 0.30.8 | [repo] `tools/osic-mac` |
| 1x2 tile | 346.64 × 325.36 µm (≈ 113k µm², about 3× a sky130 1x2) | [repo] tt-support-tools `tech/gf180mcuD/tile_sizes.yaml` |
| 2x2 tile | 711.20 × 325.36 µm | same |
| Power pins | Metal4 vertical stripes, VDPWR / VGND (+ VAPWR with the `_pgvaa` template) | [repo] `def/analog/magic_init_project.tcl` |
| Std-cell rows | `GF018hv5v_mcu_sc7` (7-track), 3.92 µm row pitch | [repo] `tt_analog_1x2.def` |
| Top metal | Metal5 (the 1.19 µm top metal) is not available to TT projects, so no inductors and **no MIM caps**. gf180mcuD's MIM is option B: M4 bottom plate, a thin top plate contacted only through Via4 to Metal5 (PDK analog layout specs, [section 3.43](https://gf180mcu-pdk.readthedocs.io/en/latest/analog/layout/inter_specs/inter_specs_3_43.html)). Large caps are MOS caps | Matt, 2026-11-08 |
| Hi-res poly | **1 kΩ/sq** (`ppolyf_u_1k`, mask L63 included). The `_2k` / `_3k` models in `sm141064.ngspice` are other process options on the same layers, not available. Matches magic (extracts only `ppolyf_u_1k`) and the KLayout LVS (`poly_res=1K`) | tnt [TT], wafer.space Discord, 2026-11-06 |
| MIM | 2.0 fF/µm², M4–M5 (option B); unusable for TT projects anyway (no Metal5) | same |

## Supplies and pins
| Item | Value | Source |
|---|---|---|
| VDPWR | always 3.3 V | tnt [TT], via Matt, 2026-11-09. **[open]** tolerance and ripple on the GF demo board, and the VDPWR grid impedance a project sees (it sets the TX driver's supply ripple, `sim/tx/results/block_sch.txt`) |
| Tile power switch | VDPWR reaches the tile through TT's power gate; 2x2: `tt_pg_3v3_hp_2`, pfet_03v3 W 3357.5 µm L 0.28 µm, Ron 1.32 Ω tt (1.18 ff … 1.48 ss), common to everything in the tile | [repo] [tt-multiplexer pg/gf180mcuD](https://github.com/TinyTapeout/tt-multiplexer/tree/main/pg/gf180mcuD) (Matt, 2026-11-09) + [sim] `sim/tx/tb_tx_top.py` case pg |
| VAPWR, VIO | independent of VDPWR, each 3.3–5 V, with VAPWR ≤ VIO (the pad ESD diodes); the analog switch `tt_asw_5v0` runs from VAPWR | tnt [TT], via Matt, 2026-11-09. The TX driver uses 3.3 V devices on VDPWR, so it doesn't depend on the VAPWR setting |
| ua pin path | switch 11–37 Ω tt (ss peak 72 Ω) + routing 15–60 Ω; about 7.7 pF on a project node with the pin open (3 other projects on the pin); 433.92 MHz out into 50 Ω: −0.5 to −0.9 dB vs DC. Model: `sim/pad/pad_model_gf180.spice`, `docs/pad_model.md` | [sim] + tnt (switch R matches his silicon; routing R). projects per chip pin: 1–4 on ttgf0p3 (TT index API), ttgf26c not known yet |
| Digital output max toggle | unknown for GF pads | **[open]**. The plan keeps ÷64 (6.8 MHz) and ÷1024 on `uo_out` |
| Project clock | from the RP2350; 10–50 MHz is typical | [assumed] |
| RP2350 PIO counting | counts edges up to ~sysclk/2 (75 MHz at 150 MHz); the crystal is ±30 ppm, ≈ 13 kHz at 433.92 MHz | [assumed] RP2350 datasheet; check on the bench |

## Prior GF180 silicon (ttgf0p2)
[Silicon-proven list](https://tinytapeout.com/chips/silicon-proven/#ttgf0p2). There is little analog on
it, but there are two standard-cell rings:
- **#207 [`tt_um_dlmiles_ringosc_5inv`](https://tinytapeout.com/chips/ttgf0p2/tt_um_dlmiles_ringosc_5inv)**:
  a 5-inverter ring with ÷2 … ÷32768 outputs. No measured frequency published ("square waves halving pin by pin").
- **#200 [`tt_um_algofoogle_vgaringosc`](https://tinytapeout.com/chips/ttgf0p2/tt_um_algofoogle_vgaringosc)**:
  gf180mcuD inv_1 / inv_2 / inv_4 chains, taps from 3 to 161 stages; the expected range was 15–350 MHz.
  One user report of "~78 MHz", with the setting not given.

**Action [open]:** measure #207 (÷N outputs) and #200 (a few `clksel` values) on a ttgf0p2 board, with
the board's VDPWR recorded. Then simulate the same std-cell rings, extracted from their GDS if
possible. That gives the GF **silicon / extracted-tt factor** (sky130 was ×0.866). Until we have it,
the tuning range must cover ×0.7–×1.4 of nominal.

## Simulated GF180 3.3 V ring basics
[sim] `sim/vco/ring_basic.py`: plain nfet/pfet_03v3 inverters, Wn/Wp = 2/5 µm, L = 0.28 µm, AD/AS from a
0.5 µm diffusion, plus 2 fF of wiring per node. Schematic only.

| | Value |
|---|---|
| tt 27 °C 3.3 V | 5 stages 1950 MHz, 9 stages 1082 MHz → **≈ 51 ps per stage** (f·N ≈ 9.75 GHz) |
| Power | ≈ 2.5 mW, independent of N (N·f is constant) |
| Plain ring at 433.92 MHz | ≈ 22–23 stages |
| Corners, temperature, df/dVDD | see `docs/vco_study.md` once the sweep finishes |
