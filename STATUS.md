# Where we are (2026-11-09, late evening)

This is the "pick up from here" note: a summary, the next steps, and where everything lives. The detail and evidence
for each result are in the docs it links.
Repo: github.com/mattvenn/gf-433-oscillator (`main`). Plans: `~/.claude/plans/in-a-recent-radio-majestic-lovelace.md` (VCO),
`~/.claude/plans/i-want-you-to-frolicking-sparkle.md` (TX driver).
Flow and rules: the project skill `.claude/skills/mixed-signal-asic/`.

## Goal
A tunable 433.92 MHz oscillator on GF180MCU (Tiny Tapeout, ttgf26c), with no inductors and no external components.
It is to become an **FM radio toolkit**:
- **On chip:** the VCO, dividers, the antenna driver, the LNA, the mixer and the IF chain.
- **On the RP2350:** all the digital: tuning, demodulation and framing.
- **Receiver:** single LO, low IF (about 200–300 kHz), demodulated by RP2350 PIO. I/Q is deferred to a later tapeout.
- **Range:** room-temperature operation only.

## Start here
**The oscillator topology is chosen: a current-fed ring with a 5-bit current DAC.**
- It passes every check so far, in schematic and on the extracted v3 layout.
- **GF silicon factor: about 1.0 at typical** (`docs/gf_silicon_factor.md`, 2026-11-09). On the ttgf0p2 ring #614
  the six inv_2 taps give silicon/sim 0.993–1.001 and sit between the sf and tt corners. The 5× inv_1 ring gives
  0.935, but it is the least certain bench point and disagrees with the taps: re-measure it. Even at 0.935, the
  extracted range (193–851 MHz) still covers 433.92 MHz.

| | Result | Doc |
|---|---|---|
| Topology | Five inverters between VDD and a shared node vg (3 pF decap); one binary-weighted current DAC (base 6 + 5 bits, unit 1.2/5.33 µm) plus a fine leg on vctrl; const-gm reference with a 1 MΩ / 20 pF RC filter | `docs/cfed_results.md`, `docs/schematics.md` |
| Range, full PVT (schematic) | 228–750 MHz (target ≤ 310 / ≥ 700); 433.92 at codes 7–11 | `docs/cfed_sizing_results.md` |
| Range, extracted v3 RC (corrected) | 193–851 MHz at vctrl 1.65 V with the level shifter (old 194–677 had the RC double count) | `docs/remap_results.md`, `docs/rc_extraction_fix.md` |
| 433.92 codes, extracted core + level shifter | tt 9, ss 11, ff 7, sf 9, fs 10 at vctrl 1.75–2.25 V (3 codes reach it at every corner) | `docs/remap_results.md` |
| Monotonic / no gaps | yes at all PVT; fine/step ≥ 2.1 (needs 1.3) | `docs/cfed_sizing_results.md` |
| DAC mismatch (MC, N = 900) | 0 % non-monotonic, worst DNL ±0.13, fine/step ≥ 3.1 | `docs/cfed_v3_check.md` |
| rms FM, 1–10 kHz | 7.3–8.3 kHz over PVT (limit 15); the reference path dominates | `docs/cfed_sizing_results.md` |
| Supply sensitivity | −0.008 %/10 mV (the starved ring was −0.25) | `docs/cfed_results.md` |
| Power at 433.92 MHz | 0.39–0.52 mW | `docs/cfed_sizing_results.md` |
| Power-on start-up | 36 of 36 runs reach the fundamental mode; worst 138 µs to within 1 %, set by the RC filter | `docs/cfed_startup_results.md` |
| Core layout (v3) | 69 × 52 µm, DRC / LVS / antenna clean; ring nodes 3.0–3.4 fF | `docs/ring_layout_v3.md` |
| Tuning procedure | binary-search the code, servo vctrl, FSK at about ±1.8 mV for ±50 kHz | `docs/tuning.md` |

## How we got here (short)
1. **First architecture study:** starved ring candidates (`docs/vco_study.md`). Phase noise came from the ISF method
   (`docs/pn_results.md`), cross-checked against VACASK transient noise.
2. **Quiet constant-gm reference:** 14 × 14 arrays of the unit device, which keep the tempco null; the RC filter
   (`docs/bias_tuning_results.md`).
3. **The layout showed about 10 fF per ring node, not the 2 fF assumed** (`docs/ring_layout.md`). The compact v2 cut
   that to about 3 fF. Then **f-node charge sharing broke the starved stage at low codes** (`docs/ring_layout_v2.md`).
4. **Topology comparison:** only the current-fed ring passes (`docs/cfed_results.md`).
5. **Sizing, PVT map, PVT noise, v3 layout, MC and start-up** (the docs in the table above).

## Next steps
**Decisions 2026-11-10 (Matt):** no board components except the dipoles, so all fine tuning is on chip. TX plan is option C: a ~10-bit medium current DAC (~50 kHz LSB, ±25 MHz, from the constant-gm reference) with sigma-delta dither below one LSB, an SPI register from the RP2350, FSK as a digital offset (±100 kHz, 2-FSK), and a ÷16/÷64/÷1024 divider to `uo_out` (GF pins are fine to ~50 MHz, so `ck` at 108 MHz is not; gate it, since 4 × ck = 433.92 MHz). vctrl is tied inside the chip, with ua[0] kept as a debug override. The RP2350 counts and servos (freezing during packets). The RX gets its own dipole on a second pair of `ua` pins (6 of 6 used); zero-IF vs low-IF is deferred. Focus on the TX first.

1. **Bench 2026-11-09: done** (results at the top of `bench/lab_todo.md`). **`docs/handoff_gf_silicon_factor.md` is
   running on the sim server (started 2026-11-09 evening)**: `git pull` for its status / DONE / FAILED files, then compare
   with the bench (inv1x5 319.6 MHz and the tap sweep) and re-check that codes 7–11 still reach 433.92 MHz.
   The original list was:
   - measure the ttgf0p2 #200 ring, for the GF silicon/sim factor;
   - check the carrier's core regulator (R1 or R3 feed, VDD_CORE noise);
   - check the RP2350 13.56 / 27.12 MHz reference clock;
   - if time allows, measure a `ua` pin's R and C.
2. **Level shifter + TSPC ÷4 prescaler: schematic and layout done** (`docs/lsdiv_design.md`, `docs/lsdiv_layout.md`,
   `xschem/lsdiv.sch`, `layout/lsdiv.gds`, 40.5 × 37 µm, DRC/LVS/antenna clean).
   - On the extracted core: ÷4 exact, duty 46–51 %, −1.5…−1.8 % f; Cc extracted 1.99 fF.
   - **Open:**
     - block power is about 1.7× the schematic (0.63 mW at tt code 9): routing C on the TSPC nodes;
     - the RC extraction double-counts Cc on a0 (sims use the C-only `lsdiv_c.spice`); check the core's RC ports for
       the same effect;
     - sf/fs, 0/70 °C, VDD ±4.5 %, MC on the extracted block; the ~10 pF supply decap (top level);
     - don't clock the ÷4 below about 150 MHz (sf fails below that; the ring never goes there).
   - **433.92 MHz codes re-mapped** on the corrected extracted core + extracted level shifter (`docs/remap_results.md`):
     tt 9, ss 11, ff 7, sf 9, fs 10 (the schematic map's codes, fs +1), vctrl 1.75–2.25 V; 3 codes reach 433.92
     at every corner.
   - **Hi-res poly is 1 kΩ/sq (confirmed, `docs/platform.md`); the design now uses ppolyf_u_1k.** `vco_bias.py`
     sizes RF for 1 MΩ at 1k (970 µm at 1 µm wide; `rfm=3k` reproduces older results). tt 27 °C code 9 noise is
     unchanged (7.87 kHz rms 1–10 kHz). lsdiv's R1 stays as drawn (about 164 kΩ); extracted corners unchanged.
3. **On-chip fine tuning and FSK (option C): done through the tile, 2026-11-11** (`docs/tx_fine_tune.md`,
   handoff `docs/handoff_tx_fine_tune.md`). 10-bit medium current DAC on vg (5 unary + 5 binary, PMOS steering,
   3/30 mirror) + first-order ΣΔ cell, SPI register / FSK offset / ÷16 ÷64 ÷1024 / gated ck in the digital macro
   `tx_fine` (LibreLane), vctrl pulled down on chip (200 kΩ), tile LVS / DRC / antenna clean, TT precheck passes.
   - Extracted ring + extracted DAC (C only, `pex_mdac.sh` + `pexmerge.py`): LSB 27.4 / 31.1 / 35.6 kHz (ss / tt / ff),
     −0.2 % vs the schematic DAC, range > 1.3 coarse steps; MC (N = 200 × 3 corners, schematic DAC) monotonic; ΣΔ
     spurs −58.2 dBc (model −60); FSK ±3 LSB = 204 kHz, settles within 0.26 µs; FM +5 %. VDD 2.8-3.3 V: LSB and
     range unchanged (no headroom issue).
   - **Clock gating (2026-11-11, macro r12):** 4 icgtp gates, small CTS buffers; clock charge 21.1 -> 4.48 pC per
     25 MHz cycle (OpenSTA, `macro/tx_fine/power/clk_charge.py`); supply spur −32.1 -> **−45.5 dBc** (target −40).
   - **To look at later: the 25 MHz supply spur** (-45.5 dBc, target -40). More decap barely helps (|Z| < 1.3 ohm
     at 25 MHz needs ~5 nF, ~2.5 mm² of MIM). **Coupling path found (2026-11-12, `sim/tune/spur_paths.py`,
     schematic, tt, supply path only):** all of it comes through the ring inverters' VDD: ripple on the ring alone
     -45.3 dBc, on the DACs or nothing about -80 dBc. vg's 3 pF decap goes to VSS, so vg holds still (2 mV p-p) while
     VDD moves 15 mV, and the ring sees ~17 mV across it. **Returning that decap to VDD gives -80.5 dBc** (VDD - vg
     ripple 2 mV; 6 pF to VDD: -74 dBc). To check before adopting: start-up, ss/ff, a PMOS gate cap's C(V) at
     VDD - vg = 1.2-1.6 V (or MIM), ground ripple (not modelled), then the layout (ring_core_v3 decap). Other options: the floorplan (Matt suspects routing / placement coupling, which the supply-only bench doesn't
     model); the analog on VAPWR (needs the `_pgvaa` template, VAPWR set to 3.3 V, ask tnt whether it is switched);
     an RC filter on the ring supply (~1 kohm + 20-100 pF: -10…-24 dB); trimming the 10 always-clocked flops.
   - **Kept as is (Matt, 2026-11-12):** the ΣΔ-cell charge injection (+0.4 LSB at fraction ½; monotonic, the servo
     corrects it) and the FSK overshoot at a major carry (firmware keeps the FSK pair inside one block of 32).
4. **Reference layout: done** (`docs/ref_layout.md`, `layout/cgm_ref.gds`, 238.8 × 69.4 µm, DRC/LVS/antenna clean).
   Extracted core + extracted reference: f within −0.03 % of the schematic reference at tt/ss/ff, vbnf start-up
   88–94 µs. **Top level `vco_top` done** (`docs/top_layout.md`, 406.7 × 70.8 µm, DRC/LVS/antenna clean, no Metal4/5): the extracted
   top matches the blocks within 0.07 % (tt 418.0 MHz at code 9 with the LS). As a straight row it needs a 2x2;
   folded (about 29k µm²) it would fit a 1x2. Open: a0 tap for the TX driver, full start-up to settling.
   - **Tempco at room temperature is +100…+140 ppm/°C (about 45–60 kHz/°C)**, schematic and layout alike. The sizing
     nulled the 0–70 °C least-squares slope (+1.6 ppm/°C), but f(T) is a parabola peaking near 35 °C. For
     room-temperature operation, re-tune the n-well length lnw to put the peak at 27 °C (only RBW's length changes).
5. **TX driver: done through the tile** (`docs/tx_driver.md`, 2026-11-09). lsdiv's `ls` -> tap -> phase splitter ->
   two arms (NAND2 enable + x4 taper, final N 40 / P 100 um, 3.3 V devices on VDPWR) -> ua[3] (out_p) / ua[2] (out_n)
   into a two-wire dipole; enables on ui_in[5] / ui_in[6].
   - Schematic: +3.7…+9.3 dBm fundamental into 73 ohm over 5 corners x routing 15–60 ohm x n_off 0–3 (+6.3 dBm tt),
     12.6 mA from VDPWR at tt, duty 48.8–52.1 %, phase error <= 0.5 deg, off state 0 V (`sim/tx/results/`).
   - Layout `layout/tx_drv.gds` 73 x 106 um: DRC / antenna / LVS clean; extracted -0.2…-0.3 dB vs schematic.
   - On the extracted vco_top: the tap does not disturb the ring. Behind TT's power switch (tt_pg_3v3_hp_2, Ron
     1.2–1.5 ohm, common to the whole tile) keying the driver on moves the ring +0.03…+0.05 % (+110…+210 kHz), ripple
     12–15 mV, no jitter change. LS duty passes through (out_p 54.0 % at ff). 3rd harmonic at the dipole -14 dBc.
   - **To check: on-chip harmonic reduction** (the 3rd is -14 dBc at the dipole; the ETSI spurious limit at 1.3 GHz
     is about -36 dBc at our power; the pad path filters only ~2.6 dB). Block sims on the driver bench:
     - slower, controlled edges (rise time ~T/3 = 0.77 ns nulls the 3rd; ~1.7 dB of fundamental; the null moves with
       corner);
     - two ring taps 72 deg apart summed in a split final stage (~8 dB off the 3rd, ~1 dB of fundamental; tracks
       process); together perhaps -30…-35 dBc.
   - In the 2x2 tile above lsdiv; wrapper LVS passes (5 mutations caught), KLayout DRC clean except fill rules.
   - CI on 6503f1c: TT precheck, LVS and docs workflows pass.
   - **ua pin limit is 10 mA rms** (tnt, 2026-11-11): each arm carries 7.8-8.1 mA rms at tt / 40 Ω, but
     10.8-11.1 mA at ff with 15 Ω of routing. Kept at 40 um (Matt, 2026-11-12: the small ff excess is acceptable).
   - **Open:** ask tnt about VDPWR before the power switch (bond wires, chip grid); re-floorplan with the receiver.
     The pin plan can't be known before tapeout (it depends on the other projects then), so the TX is checked
     over n_off 0-3 instead.
6. **Receiver blocks:**
   - port the OOK LNA (linear, not limiting) to GF180;
   - new: mixer, IF preamp, filter, limiter and comparator.

   **Pin budget: GF analog pin model done** (`docs/pad_model.md`, `sim/pad/pad_model_gf180.spice`,
   `xschem/pad_model_gf180.sch`, checked by `sim/pad/check_xsch.py`). tnt's `tt_asw_5v0` switch is 11–37 Ω tt
   (ss peak 72 Ω), plus 15–60 Ω of routing; a project node sees about 7.7 pF with the pin open; 433.92 MHz out into
   50 Ω loses −0.5…−0.9 dB vs DC (6–12 dB absolute, the R divider). VAPWR is 3.3–5 V, set independently of VDPWR
   (tnt, `docs/platform.md`; simulated at 3.3 V, the conservative case). The ttgf26c pin plan isn't known until
   tapeout (it depends on the other analog projects then, Matt 2026-11-11), so designs are checked over n_off 0–3
   (3 the default, 0–1 likely). 12 `ua` pins requested so far, 4 used now: vctrl, vbn, TX out_n, TX out_p.
   **Our project is not in `TinyTapeout/tinytapeout-gf-26c` yet: submit before 2026-12-07.**
7. **Later:** a PLL (on-chip PFD, charge pump and loop filter, reference from the RP2350), and I/Q for the receiver.
8. **Sign-off:** full PVT (5 corners × 0/27/70 °C × VDD ±4.5 %) plus MC on the extracted tile.
9. **Estimated tile:** 2x2.

## Done 2026-11-09 (TX driver)
- Plan steps 1–5: circuit + xschem sheets (`sim/tx/tx_drv.py`, `xschem/gen/tx_drv.py`), block and top-level benches
  (`sim/tx/tb_tx_drv.py`, `sim/tx/tb_tx_top.py`), layout + checks + extraction (`layout/gen/tx_drv.py`,
  `check_tx.sh`, `pex_tx.sh`), the `ls` port on lsdiv / vco_top, and the tile (`layout/gen/tt_wrapper.py`).
- `xschem/gen/check.py`'s size diff now joins SPICE continuation lines (a wrapped `m=3` was missed before).

## Done 2026-11-08
- The xschem schematics are redrawn as wired, textbook-style sheets (no net labels). Checks pass, and they render in
  xschem-viewer.
- The level shifter and ÷4 prescaler: schematic, layout, extracted sims (above), and the 433.92 code re-map.
- **The xschem netlist is now the LVS source of the v3 core** (`layout/gen/check_v3.sh`). It caught that the committed
  `layout/ring_core_v3.gds` was the wfu 0.25 layout, not the chosen 0.30. The GDS, `layout/ref/ring_core_v3.spice` and
  the floorplan PNG are now 0.30, the layout the extracted netlists (`*_w30chk_rc.spice`) were made from. All checks pass.

## How things run
- **Tools:** `tools/osic-mac <cmd>` runs IIC-OSIC-TOOLS (laptop image 2026.05; sim pod 2026.09). **It doesn't pass
  env vars into Docker:** use `tools/osic-mac env K=V cmd`.
- **Corners** (`docs/handoff_autonomy.md`, "Corner policy"):
  - iterate at 27 °C and VDD 3.3 V on the bounding process corners;
  - VDD and 0 / 70 °C only for robustness checks and sign-off.
- **Long runs (over about 5 min) go to the sim pod** via `docs/handoff_<topic>.md`.
  - The rules for unattended runs are in `docs/handoff_autonomy.md`; they were tested twice and work.
  - The pod session, "gf433 sims", can be messaged directly over Remote Control.
  - The laptop session watches the handoff's status line on GitHub.
- **Key scripts:**
  - `sim/vco/vco_bias.py` (the circuit; `topo=cfed`), `sim/vco/topo_cmp.py`;
  - `sim/pn/cfed_noise.py`, `sim/pn/cfed_sizing.py`, `sim/pn/cfed_startup.py`;
  - `sim/mc/dac_mc.py`;
  - `layout/gen/ring_core_v3.py` (pass `--set wfu=0.30`) + `check_v3.sh`/`pex_v3`/`pex_sim_v3`;
  - `xschem/gen/` + `check.py`.
- **Chosen design settings:** `sim/results/2026-11-08/winner_sets.txt`, plus `lnw=5.023 topo=cfed kc=0.75 k=6
  cvg=3e-12 ka=16 wfu=0.30 wff=0.30 rf=1e6 cf=20e-12`.
- **Viewers:**
  - GDS: `https://gds-viewer.tinytapeout.com/?url=<raw github URL>&pdk=gf180mcuD`;
  - schematics: the links in `docs/schematics.md` (xschem-viewer).

## Known issues and traps
- **Map reads high:** `map.csv` frequencies read about 1.3 % high (a 100–200 ns window, before vg settles). The
  extracted layout runs at about 0.98× the schematic.
- **magic RC extraction double-counted the coupling C** on ports and split nets, which made the core look 13 % slow
  (the old "0.87×"). Simulate the `_rcx.spice` files (`layout/gen/rcfix.py`, `docs/rc_extraction_fix.md`).
- **Kvco is not linear:** the fine leg is flat below about 1 V and square-law above it, so measure Kvco at the
  operating point before setting the FSK step.
- **xschem-viewer has no GF180 library:** the symbols are copied into `xschem/symbols/`. They render correctly
  (confirmed by Matt, 2026-11-08).
- **Leftover Docker containers** from killed subagent runs (for example a hung xschem render): check with `docker ps`.
- **Never commit `sim.yaml`:** it holds the VNC password.
