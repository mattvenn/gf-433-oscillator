# Where we are (end of 2026-11-08, evening)

This is the "pick up from here" note: a summary, the next steps, and where everything lives. The detail and evidence
for each result are in the docs it links.
Repo: github.com/mattvenn/gf-433-oscillator (`main`). Plan: `~/.claude/plans/in-a-recent-radio-majestic-lovelace.md`.
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
- The only Gate 1 input still open is **the GF silicon factor** (bench, 2026-11-09).

| | Result | Doc |
|---|---|---|
| Topology | Five inverters between VDD and a shared node vg (3 pF decap); one binary-weighted current DAC (base 6 + 5 bits, unit 1.2/5.33 µm) plus a fine leg on vctrl; const-gm reference with a 1 MΩ / 20 pF RC filter | `docs/cfed_results.md`, `docs/schematics.md` |
| Range, full PVT (schematic) | 228–750 MHz (target ≤ 310 / ≥ 700); 433.92 at codes 7–11 | `docs/cfed_sizing_results.md` |
| Range, extracted v3 RC | 194–677 MHz worst case (target ≤ 310 / ≥ 620); 433.92 at codes about 10–15 | `docs/cfed_v3_check.md` |
| 433.92 codes, extracted core + level shifter | tt 12, ss 14, ff 10, sf 12, fs 13 at vctrl 1.7–2.3 V | `docs/remap_results.md` |
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
1. **Monday 2026-11-09, bench** (`bench/lab_todo.md`):
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
   - **433.92 MHz codes re-mapped** (`docs/remap_results.md`): recommended tt 12, ss 14, ff 10, sf 12, fs 13 (vctrl
     1.7–2.3 V), 3–4 codes above the schematic map; every corner has two or more codes that reach 433.92.
   - **Hi-res poly is 1 kΩ/sq (confirmed, `docs/platform.md`); the design now uses ppolyf_u_1k.** `vco_bias.py`
     sizes RF for 1 MΩ at 1k (970 µm at 1 µm wide; `rfm=3k` reproduces older results). tt 27 °C code 9 noise is
     unchanged (7.87 kHz rms 1–10 kHz). lsdiv's R1 stays as drawn (about 164 kΩ); extracted corners unchanged.
3. **Digital macro** (LibreLane): ÷8…÷256 (overall ÷32 / ÷64 / ÷1024), the `uo_out` buffers and mux, and later the
   code latch / TX enable / FLL counter.
4. **Layout of the reference:** the 14 × 14 arrays, the n-well + n+ resistor, and the 20 pF filter cap (about 8.7k µm²).
5. **Receiver blocks:**
   - port the OOK LNA (linear, not limiting) and TX driver to GF180;
   - new: mixer, IF preamp, filter, limiter and comparator.

   Pin budget: the TT analog pins are < 500 Ω / < 5 pF on sky130. **The GF figures are unknown, so ask the TT team.**
6. **Later:** a PLL (on-chip PFD, charge pump and loop filter, reference from the RP2350), and I/Q for the receiver.
7. **Sign-off:** full PVT (5 corners × 0/27/70 °C × VDD ±4.5 %) plus MC on the extracted tile.
8. **Estimated tile:** 2x2.

## Done since the morning
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
  extracted layout runs at about 0.87× the schematic.
- **Kvco is not linear:** the fine leg is flat below about 1 V and square-law above it, so measure Kvco at the
  operating point before setting the FSK step.
- **xschem-viewer has no GF180 library:** the symbols are copied into `xschem/symbols/`. They render correctly
  (confirmed by Matt, 2026-11-08).
- **Leftover Docker containers** from killed subagent runs (for example a hung xschem render): check with `docker ps`.
- **Never commit `sim.yaml`:** it holds the VNC password.
