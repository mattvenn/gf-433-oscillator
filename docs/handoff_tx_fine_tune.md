> Running: phase D (tile DRC / antenna / precheck, xschem, extraction) since 21:23, ETA 23:23. Phases A, B done; tile LVS clean
# Handoff: on-chip fine tuning and FSK for the TX (option C), schematic to tile (sim server)

**Goal: replace the board-driven vctrl with on-chip fine tuning, so that the chip needs nothing on the board except
the dipole. Deliver a medium current DAC with sigma-delta (ΣΔ) dither below one LSB, a small digital macro (SPI
register, ΣΔ, FSK offset, divider), the RP2350-side tuning model, layout, and the tile integration with every check
passing. Write the work up in `docs/tx_fine_tune.md`.**

Read `STATUS.md` ("Decisions 2026-11-10" under Next steps) first. **Work in `/foss/designs/gf433-sims`**
(`git pull --rebase` first). **For this job you own the whole repo**: the laptop session stays out until you push
`Done`. Commit and push at the end of each phase, so nothing is lost if the session dies.

## Why (the decisions behind it, 2026-11-10)
- **No board components except the dipoles** (Matt). vctrl on ua[0] driven from the RP2350 through an RC is
  therefore out. At about 27 MHz/V, 1 kHz is 37 µV on vctrl, and a voltage DAC is referenced to VDD, which reaches
  the tile through TT's 1.3 Ω power switch. So the fine control is a **current DAC referenced to the constant-gm
  bias**, like the existing coarse DAC.
- **Option C was chosen over B** (7-bit DAC, 250 kHz steps, no ΣΔ) for range: with C, both ends of a link can be
  tuned to about 1 kHz, so the receiver can use a narrow (~300 kHz) filter. Expected range in the discussion: about
  90 m outdoors at 1 m height, 20–40 m indoors through walls.
- **Modulation:** 2-FSK at ±100 kHz, 1–10 kbit/s, Manchester or whitened data. The RP2350 counts a divided output,
  runs a slow servo between packets, and freezes it during a packet (a 10–20 ms preamble absorbs the
  +110…+210 kHz key-on pull, `docs/tx_driver.md`).
- **GF output pins** toggle cleanly to about 50 MHz (ttgf0p2 measurement, `docs/platform.md`). `ck` (f/4 ≈ 108 MHz)
  is too fast, and **4 × ck = 433.92 MHz**, so `ck` on a pin is an on-channel spur: gate it off by default.
- The RX will get its own dipole on two more `ua` pins later (ua[4], ua[5]): leave them free. Zero-IF vs low-IF is
  deferred. Don't design the RX here.

## The existing circuit (what you build on)
- VCO: current-fed 5-stage ring, 5-bit binary coarse DAC (base 6 + 5 bits, unit 1.2/5.33 µm) plus a fine NMOS leg
  on vctrl; constant-gm reference with a 1 MΩ / 20 pF filter on vbnf. Sources: `sim/vco/vco_bias.py`,
  `xschem/gen/cfed_dac.py`, `xschem/gen/vco_cfed.py`, `layout/gen/ring_core_v3.py`, `layout/gen/vco_top.py`.
  Docs: `docs/cfed_results.md`, `docs/cfed_sizing_results.md`, `docs/remap_results.md`, `docs/tuning.md`.
- Coarse step near 433.92 MHz: about 21 MHz per code (tt 27 °C: code 8 / 9 / 10 at vctrl 1.65 V = 413.4 / 434.1 /
  454.5 MHz, `sim/results/2026-11-08/cfed/map.csv`). The fine leg is off below about 1 V; Kvco ≈ 26–28 MHz/V at
  1.6 V.
- lsdiv (level shifter + TSPC ÷4, `ck`), `tx_drv` (`docs/tx_driver.md`), tile wrapper `layout/gen/tt_wrapper.py`,
  LVS source `lvs/make_source.py`, tile checks `layout/gen/check_tt.sh`.
- **`docs/tuning.md` is wrong:** it says vctrl has an on-chip RC filter. It doesn't. Fix this when you rewrite the
  procedure.

## Target spec (first pass; change a number only with the reason written down)
| Item | Target |
|---|---|
| vctrl | tied to VSS inside the chip through ppolyf_u_1k (≥ 100 kΩ), so the fine leg is off by default and adds no supply sensitivity; ua[0] stays as a bench override |
| Medium DAC range | unipolar, ≥ 1.3 × the largest coarse step at the codes that reach 433.92 MHz, at tt/ss/ff/sf/fs 27 °C (the old fine/step rule) |
| Medium DAC LSB | ≤ 50 kHz at every corner (about 10 bits). Upper bits unary (thermometer-coded) for monotonic steps |
| Monotonic | DNL > −1 LSB at ≥ 99 % of Monte Carlo runs (N ≥ 200, unit instances; see the MC trap in CLAUDE.md) |
| Resolution with ΣΔ | ≤ 1 kHz (8 fractional bits or more) |
| ΣΔ spurs | ≤ −40 dBc at any offset from 10 kHz to 30 MHz, for **every** fractional input (sweep them). Sanity check: in a first-order ΣΔ the accumulator residue is under one LSB × one clock, so the phase error stays below 2π·LSB/f_clk (0.0126 rad for 50 kHz at 25 MHz). A quick laptop model gives a worst spur of −50 dBc (fraction ½, 12.5 MHz offset) over all 256 fractions, so first order probably meets this; higher orders are for the noise target, if at all |
| ΣΔ-added FM noise | ≤ 2 kHz rms over 1–100 kHz (the ring's own is 7–8 kHz rms over 1–10 kHz) |
| FSK | a deviation word added to or subtracted from the DAC word, selected by ui[7] (synchronised to `clk`); ±100 kHz ≈ ±2 LSB, calibrated by counting both states |
| Divider | ÷16 (27 MHz), ÷64 (6.8 MHz), ÷1024 (424 kHz) on `uo` pins; `ck` on uo[0] gated by a register bit that resets to off |
| ΣΔ and SPI clock | the TT project `clk` (RP2350, 10–50 MHz): one clock domain, and it runs before the VCO starts. The divider runs on `ck` |
| Digital supply coupling | the macro's switching current through the 1.3 Ω switch × the ring's df/dVDD (−0.008 %/10 mV): report the resulting FM and spurs, target ≤ −40 dBc |
| Existing specs kept | start-up, 433.92 MHz reachable at every corner, rms FM ≤ 15 kHz (1–10 kHz), TX power within 0.3 dB of today |

**Pins:** ui[0–4] coarse (unchanged), ui[5] / ui[6] TX enables (unchanged), **ui[7] FSK data**, **uio[0] SCLK,
uio[1] MOSI, uio[2] CS_n, uio[3] MISO** (readback, the only uio output), **uo[0] ck (gated), uo[1] ÷16, uo[2] ÷64,
uo[3] ÷1024**. `rst_n` resets the register: ΣΔ off, `ck` gate off, medium DAC word at mid-scale. You define the
register map; write it into `docs/tx_fine_tune.md` and `info.yaml`.

## Phases
Push the progress line (top of this file) at every phase change.

**A. Study, behavioural first (local CPU, about 2 h).**
1. A Python ΣΔ model (first order, second order, MASH 1-1 / 1-1-1, optional LSB dither). Model the frequency as
   LSB × (bitstream − fraction), integrate it to phase, take the spectrum, and sweep the fractional input (all
   256 values, plus fine steps near 0, ½ and the small rationals). Choose the simplest order, clock and LSB that meet the spur
   and noise targets. If none does with LSB ≥ 10 kHz, **stop and report** the options (smaller LSB, higher clock,
   dither).
2. Size the medium DAC on the schematic. Mirror ratio from the reference, unit leg, segmentation; sweep tt/ss/ff/sf/fs
   at 27 °C to find the bounding corners (corner policy), then iterate on those. MC for DNL.
3. Check that tying vctrl to VSS still reaches 433.92 MHz at every corner with the medium DAC, and that start-up and
   FM noise are unchanged (the ring's existing decks).
4. Write phase A into `docs/tx_fine_tune.md` (numbers chosen and why), push, and carry on.

**B. Digital (local CPU, about 2 h).** Verilog in `src/`: SPI register with readback, ΣΔ, FSK offset, ÷16/÷64/÷1024,
`ck` gating. cocotb tests: register write/readback, the ΣΔ mean equal to the fractional word, the FSK offset, the
divider ratios, reset values. The cocotb ΣΔ bitstream must match the phase A Python model bit for bit. Harden with
LibreLane for gf180mcuD (`/foss/tools/bin/librelane`; the OOK project's `openlane/radio_digital` in
github.com/mattvenn/ook-asic-radio is a sky130 example of a macro inside an analog TT tile). Check the ÷16 first
stage at 108 MHz at ss: use custom TSPC ÷2 stages ahead of the standard cells if the cells won't toggle reliably.
Gate-level simulation of the hardened netlist.

**C. Transistor-level checks (the long runs; one driver, `run_in_background`).**
| Job | Corners | Why |
|---|---|---|
| Medium DAC on the extracted `vco_top` (after phase D's DAC layout, or schematic DAC + extracted ring first): f vs word, LSB | tt, plus the 2–3 bounding corners from A | the real step size |
| A ΣΔ bitstream (PWL from the Python model) on the DAC LSB, 5–10 µs: instantaneous frequency vs the model | tt | validates the behavioural spur numbers |
| Charge injection when DAC legs switch | tt, ss | glitches on vg / vbnf |
| The macro's supply current (from LibreLane power, or a PWL) on the tile supply through the power-switch model (`sim/tx/tb_tx_top.py` case pg) | tt | FM from digital noise |
| FSK keying: the deviation word toggling, TX on | tt | step shape and settling |
| rms FM noise with the new DAC | tt + bounding | the reference-path noise spec |

**D. Layout and integration.** The DAC in the ring_core / vco_top style (magic Tcl, `strip()`, the channel router),
the vctrl pull-down resistor, the hardened macro placed in the tile, wrapper routes, `lvs/make_source.py`,
`info.yaml`, the xschem generators and `xschem/gen/check.py` (with mutations). Checks: magic DRC, KLayout DRC
(`feol=true beol=true`), antenna, LVS with mutation tests on every new block, then `check_tt.sh` with new
mutations (SPI pins swapped, a DAC bit swapped). Extract (magic 8.3.642, then `rcfix.py`, simulate `_rcx`). CI must
pass (TT precheck, LVS, docs).

**E. RP2350 model and docs.** `sim/tune/rp2350_model.py`: coarse search, medium plus fractional servo on a counted
÷16 (gated counting and reciprocal counting), freeze during a packet, FSK calibration by counting both states, using
the measured f(word) from C. Show the tuning sequence converging from a cold start at tt/ss/ff and through a 27 → 35 °C
drift. Then:
- `docs/tx_fine_tune.md` (Matt's technical style: problem → fix → evidence, Fig. N. captions with numbers, honest
  limits, Made with Claude badge);
- rewrite the procedure in `docs/tuning.md`;
- update `docs/schematics.md`, `docs/tx_driver.md` (pins), `docs/platform.md` if facts change;
- update the `STATUS.md` lines for this work.

## Stop and report instead of pushing on if
- no ΣΔ/LSB choice meets the spur and noise targets (phase A);
- the new DAC raises rms FM above 15 kHz, breaks start-up, or loses 433.92 MHz at any corner;
- the macro doesn't fit in the 2x2 tile beside the existing blocks;
- the macro's supply noise breaks the −40 dBc target and a fix needs a floorplan or supply change (Matt expects
  to re-floorplan for the RX anyway).

## Running unattended (`docs/handoff_autonomy.md`)
1. Long batches: **one driver per batch**, started with the Bash tool's `run_in_background: true`, never a bare
   `nohup`. It writes `build/tx_fine/status.txt` per step and ends with `DONE` or `FAILED` (plus the log tail).
2. Each step checks its outputs (row counts; no "singular" or "Transient op started" in the logs) before the next
   one starts. On a failure, diagnose and retry at most twice, then write up and stop.
3. Heartbeat: ScheduleWakeup at about 1.5× the step's ETA (20–60 min), re-armed until done.
4. At each phase or step change, commit and push the first line of this file: `> Running: phase B, step 2 since
   HH:MM, ETA HH:MM`. Send a PushNotification to Matt at the end or on a stop, if the tool is available.
5. Between phases, carry straight on. Don't wait to be asked.
6. Use the CPU budget through `.claude/skills/mixed-signal-asic/scripts/sched.py` or `xargs -P`; leave 2 cores free.

## Don't
- Don't commit `sim.yaml` or anything under `build/`. Stage named files, never `git add -A`.
- Don't change `tx_drv`'s circuit, or the coarse DAC beyond what the medium DAC needs.
- Don't use the ua[4] / ua[5] pins (reserved for the RX).

## Done
When everything is pushed, replace the first line with `> Done (date): results in docs/tx_fine_tune.md`.
