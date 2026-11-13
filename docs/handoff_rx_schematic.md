> Running: phase C (chain runs, 6 jobs in parallel) since 02:52, ETA 05:42
# Handoff: the receiver (option B, zero-IF 1-bit I/Q), schematics and first-pass sims (sim server)

**Goal: design the receiver as xschem schematics, with each block sized and the whole chain simulated once, at
schematic level. Write it up in `docs/rx_design.md`. Stop before layout: Matt reviews the schematics and numbers
first.** First pass means tt plus the bounding process corners at 27 °C and 3.3 V. No temperature, VDD sweeps or
Monte Carlo yet.

Read `STATUS.md` first, then this file. **Work in `/foss/designs/gf433-sims` on branch `rx-option-b`**:
`git fetch origin && git checkout rx-option-b && git pull --rebase`. Commit and push everything (progress lines,
results, docs) to `rx-option-b`, never to `main`. Matt merges it after the review. You
own `sim/rx/`, `xschem/gen/rx_*.py`, `xschem/rx_*.sch`, `docs/rx_design.md` and `docs/img/rx/`. The only change
allowed in existing blocks is exposing the ring tap (below). Commit and push at the end of every phase, so nothing
is lost if the session dies.

## Why option B (decided 2026-11-12, Matt)
The behavioural model is `sim/rx/rx_model.py`, and its figures come from `sim/rx/rx_plots.py` (in `sim/rx/results/`).
It compared:
- **A:** low IF at 250 kHz with one real mixer;
- **B:** zero IF, I/Q mixers, a limiter per arm, and the RP2350 PIO decoding the two bits as a quadrature
  (rotary-encoder) counter.

B won on every count:
- **Sensitivity** (BER 1e-3, NF 10 dB): **B −107.9 vs A −104.3 dBm at 10 kbit/s**, and −114.6 vs −110.1 at
  1 kbit/s. There is no image noise, and the signed count cancels comparator glitches.
- **Selectivity:** at A's image (−500 kHz), B tolerates a CW 16.6 dB above the signal, A only −1.1 dB. B is about
  10 dB better out to ±2 MHz at the same filter order.
- **The ring's LO noise costs nothing** (within 0.2 dB). Neither do **72° taps instead of 90°**: with 1-bit
  limiters only the direction of rotation matters, so the 5-stage ring's 72° node spacing works with no 90°
  generator.
- **A DC offset** of 100× the signal at the mixer output costs nothing behind a 10 kHz high-pass.
- **Tuning error:** B loses under 1 dB out to ±50 kHz.

Two requirements came out of the model:
- **The comparators need hysteresis**, about ±0.25–0.5 × the noise rms at their input. Without it, the error count
  grows with the PIO sample rate, because the comparator chatters on noise.
- **The pin is expensive.** The dipole is 36.5 Ω per side. Each side then sees the TT switch plus routing (26–97 Ω)
  and 7.7 pF to ground. That forms a low-pass at about 240 MHz, below the carrier. For NF 10 dB the LNA needs about
  20–40 mS of gm per side (`rx_fig1_nf.png`).

## The architecture
```
ua[4] ─┐                          ┌─ I mixer (LO_I, LO_I_b) ─ BB amp + LPF ±150 kHz, AC-coupled ─ limiter ─ comparator ─► uo[4]
       ├─ LNA (differential) ─────┤
ua[5] ─┘                          └─ Q mixer (LO_Q, LO_Q_b) ─ BB amp + LPF ±150 kHz, AC-coupled ─ limiter ─ comparator ─► uo[5]
LO_I: lsdiv's `ls` (from a0) ─ buffer + rx_en gate      LO_Q: a second ls_ac on a2 (or a3) ─ identical buffer + gate
```
- **LO = 433.92 MHz**, the same code as the TX (half duplex: TX off while receiving). The FSK tones come out at
  ±100 kHz in baseband.
- **Ring taps on the verified core (Matt).**
  - I comes from the existing `ls`, so a0 gains no new load.
  - Q comes from a second `ls_ac` instance (the existing 2 fF metal-finger Cc level shifter) on a2 or a3, whichever
    is easier to reach in the vco_top layout later. a2 lags a0 by 72°, a3 leads it by 72°. The PIO learns the sign
    from the preamble, so either works.
  - The ring_core_v3 subckt already has a0–a4 as ports. Expose the chosen node at the vco_top level.
  - Leave the ring, DAC, reference and lsdiv circuits unchanged.
- **Mixers:** recommended start is passive, double-balanced and voltage-mode: CMOS or NMOS switches driven by a
  low-impedance LNA output, into a high-Z baseband input with a capacitor that removes the LO.
  - Passive mixers carry no DC, so there is little flicker noise at the ±100 kHz baseband.
  - The LO has 50 % duty and I/Q overlap. Check that the two mixers don't load each other through the LNA output.
  - If passive doesn't meet the NF or gain target, compare a Gilbert cell and write down why.
- **LNA: port stage 1 of the OOK receiver (Matt, 2026-11-12).** Source: `github.com/mattvenn/ook-asic-radio`,
  `layout/ref/lna_chain.spice` and `xschem/lna_chain.sch`. Its `amp_dp` is:
  - an NMOS differential pair, W 80 / L 0.15 µm, nf 4;
  - 1 kΩ resistor loads;
  - a 20 × (6 / 0.5) mirrored tail;
  - the input AC-coupled through 2 pF, with the gates biased to `vcm` through 20 kΩ.

  The OOK chain reached NF 9.4–12 dB in schematic, on sky130 with its own pin model.
  - **Port only the LNA, not the chain.**
    - Take `amp_dp`, plus at most one `amp_dpc`-style second stage, and only if the mixer's noise needs it (target
      about 15–20 dB of RF gain in front of the mixers).
    - The OOK chain's six stages and ~76 dB of RF gain fed a log detector. In option B the gain goes in baseband.
    - That also avoids the OOK chain's oscillation from 0.5–1 fF of output-to-input coupling
      (ook `docs/verify_lna_lo.md`).
  - **Port changes:**
    - sky130 `nfet_01v8` L 0.15 → GF180 `nfet_03v3` L 0.28 (slower: expect less gain-bandwidth per mA);
    - MIM → MOS caps (no MIM on TT GF);
    - `res_high_po` → `ppolyf_u_1k`.
  - **Re-size for the GF pin, not the sky130 numbers.** Fig. 1 of the model (`sim/rx/results/rx_fig1_nf.png`)
    asks for about 20–40 mS of gm per side for NF 10 dB through the 7.7 pF / 26–97 Ω pin. The load is now the two
    passive mixers, not `amp_dpc`.
  - **Use the AC-coupled input, and choose where the pin sits.** The TT switch is about 15 Ω near 0.5 V or 3 V and
    peaks mid-rail (37 Ω tt, 72 Ω ss; `docs/pad_model.md`). The dipole is open at DC, so hold the pin side of the
    coupling cap near 0 V or VDD through a large resistor, and bias the gate side at the pair's `vcm`. Size the
    coupling cap ≫ the pair's gate C. Compare the NF against a self-biased mid-rail pin through the pad model, and
    keep the better one.
  - If the ported pair can't reach the NF target within the current budget, try a resistive-feedback CMOS inverter
    (gm from both devices for the same current) and write down the comparison.
- **Baseband, per arm:** gain stages with AC coupling *between* stages, so the mixer's DC offset can't saturate
  anything. Every coupling corner counts toward the total high-pass, which must stay ≤ 10 kHz.
  - The model's low-pass: Butterworth 2nd order at 150 kHz. Report what 3rd or 4th order would cost in area; it is a
    selectivity knob.
  - Big R: ppolyf_u_1k (1 kΩ/sq) or MOS pseudo-resistors. Big C: MOS caps (no MIM on TT GF).
- **Limiter and comparator:** enough total gain to turn the sensitivity-level signal into full swing (about
  120 dB from the antenna, including the LNA). Use offset cancellation (AC coupling or a low-pass DC feedback loop)
  so mV offsets don't saturate the chain. Hysteresis is set relative to the noise at the comparator input. Outputs
  go to uo[4] / uo[5] at full logic swing, on the same supply as the tx_fine outputs.
- **Enable:** an `rx_en` port. When off, the LNA, baseband and LO buffers draw ≤ 10 µA, and the tap level shifter's
  output is gated (its Cc stays on the ring, so the ring load doesn't change with rx_en). How rx_en is wired (SPI
  register bit in tx_fine, or uio[4]) is decided at the review. For now, make it a port.
- **Supply:** VDPWR 3.3 V, like the TX driver. Moving the analog to VAPWR is an open question for the review; report
  the LNA's PSRR so it can be decided.

## Target spec (first pass; change a number only with the reason written down)
| Item | Target |
|---|---|
| Noise figure, antenna (73 Ω differential) to the baseband output, with `sim/pad/pad_model_gf180.spice` on both pins | ≤ 10 dB at tt, n_off 3 (the model's assumption); report n_off 0–3 and ss/ff |
| Gain distribution | baseband and limiter noise add ≤ 1 dB to the NF |
| Baseband response | high-pass ≤ 10 kHz (all couplings together); low-pass 150 kHz −3 dB, ≥ 2nd order |
| I/Q LO phase difference | 72° ± 25° at every process corner (the model works from about 20° to 160°); LO duty 45–55 % at the mixer switches |
| Ring with the new tap | 433.92 MHz still reached at tt/ss/ff/sf/fs, 27 °C; report the new codes and the f shift (expect about −1.5 %) |
| Comparator | hysteresis 0.25–0.5 × the noise rms at its input; clean edges up to 400 kHz; no chatter in a noisy transient |
| Linearity | input 1 dB compression ≥ −45 dBm (Fig. 5 needs a CW up to about −64 dBm to pass linearly; the margin is for the TX dipole nearby) |
| Supply current | ≤ 10 mA at tt, 3.3 V, including the LO buffers (the TX takes 12.6 mA; half duplex) |
| rx_en = 0 | ≤ 10 µA; the ring frequency moves by less than one fine-DAC LSB (31 kHz) between rx_en 0 and 1 |
| Report only | LO leakage to the RX pins (dBm at the dipole); the gain at 1.3 GHz (a square LO also mixes in 3 × f); PSRR of the LNA at 25 MHz (the tx_fine clock) |

## Corner config (edit here, not in scripts)
- **Block sizing (phase A):** tt 27 °C, 3.3 V. Then ss / ff / sf / fs once, to find the bounding corners.
- **Chain runs (phase C):** tt plus the 2–3 bounding corners from A, 27 °C, 3.3 V.
- **Pad model:** n_off 3 (default) and 0 (likely); 1–2 only if they bracket worse.
- **Not in this pass:** 0 / 70 °C, VDD ± 4.5 %, Monte Carlo, extraction.

## Phases
Push the progress line (top of this file) at every phase change.

**A. Block sizing (short local sims).** One Python netlister per block in `sim/rx/` (as `sim/lsdiv/lsdiv.py
block()` and `sim/tx/tx_drv.py`), with the sizes defined there, a testbench per block, and results in
`sim/rx/results/<block>/`.
1. **LO taps:** the ring with the second `ls_ac` on a2 / a3 and both buffers, at 5 corners. Measure f, the I/Q phase
   at the mixer switches (mid-swing crossings; see the CLAUDE.md trap), duty, and the codes for 433.92 MHz. Also
   check start-up once at tt (the existing `sim/pn/cfed_startup.py` deck).
2. **LNA with the pad model:**
   - `.ac` gain and bandwidth, `.noise` for the NF at 433.92 MHz, and the gain at 1.3 GHz;
   - input options (a) and (b);
   - choose by NF per mA.
3. **Mixers:** transient with ideal 433.92 MHz LO squares and an RF tone 100 kHz above the carrier: conversion
   gain, LO feedthrough, and I/Q cross-loading. Then the same with the phase-A1 LO buffers.
   - **Mixer NF:** ngspice can't do periodic noise. Use VACASK transient noise (as in `docs/pn_results.md`), or bound
     the mixer's noise as a resistor-switch network. Write down which method you used.
4. **Baseband and limiter:** `.ac`/`.noise` per arm; a transient with offsets; the hysteresis set from the noise.
5. Write phase A into `docs/rx_design.md`: the chosen topology, the sizes and the reasons. Push, and carry on.

**B. Schematics.** One generator per block in `xschem/gen/rx_*.py`:
- blocks: `rx_lna`, `rx_lo` (tap level shifter + buffers + gates), `rx_mix`, `rx_bb`, `rx_lim`, and `rx_top`;
- sizes read from the phase-A netlisters, so they can't drift;
- drawn like textbook schematics with wires (labels only for ports and supplies);
- added to `xschem/gen/all.py` and `xschem/gen/check.py`, netlist-checked against the simulated netlists, with
  mutation tests on the checker;
- rendered previews in `docs/img/xschem/`, and the links added to `docs/schematics.md`.

**C. Chain runs (one driver, `run_in_background`).**
| Job | Corners | Why |
|---|---|---|
| rx_top, ideal LO sources: `.ac` / `.noise` antenna → each limiter input | tt + bounding, n_off 0 / 3 | the NF and gain the model needs |
| rx_top + ideal LO: transient FSK, ±100 kHz at 50 kbit/s, 6 bits, at −95 and −70 dBm; compare uo[4]/uo[5] counts with `rx_model.steps_b` | tt | functional proof of the decoding, short enough to run |
| Same with the real ring + taps as the LO (vco_top schematic at the 433.92 code) | tt, then one bounding corner if time allows | the real LO: phase, duty, leakage |
| Transient noise (VACASK) on rx_top with ideal LO, about 40 µs at the sensitivity level | tt | the comparator hysteresis and chatter with real noise |
| CW blocker at +1 and +2 MHz, raised until the wanted signal's count fails; also the 1 dB compression | tt | linearity vs the Fig. 5 needs |
| rx_en toggling with the ring running | tt | ring f shift and the off current |

**D. Back into the model and the write-up.**
- Put the measured NF, filter response (order and corners, or the fitted transfer function), I/Q phase and
  hysteresis into `sim/rx/rx_model.py`. Re-run sensitivity (Fig. 4) and selectivity (Fig. 5) with them. Target:
  ≤ −105 dBm at BER 1e-3, 10 kbit/s.
- Write `docs/rx_design.md` in Matt's technical style:
  - problem → fix → evidence;
  - every acronym expanded at first use;
  - "Fig. N." captions that give the measured value;
  - honest limits;
  - the Made with Claude badge.
- Open the doc with a short "why B" section reusing `sim/rx/results/rx_fig2/4/5` (copy them to `docs/img/rx/`).
- Update the receiver lines in `STATUS.md`.
- **List the open questions for the review:**
  - rx_en wiring;
  - VAPWR or VDPWR;
  - the filter order;
  - the area estimate for each block, as a first floorplan input.

## Stop and report instead of pushing on if
- the NF is above 13 dB at tt, n_off 3, for every LNA option within 10 mA;
- the I/Q phase falls outside 30–150° at any corner, or the new tap loses 433.92 MHz at any corner;
- the tap or rx_en disturbs the ring by more than 1 LSB, or breaks start-up;
- a block can't meet its target without an inductor or an off-chip part.

## Running unattended (`docs/handoff_autonomy.md`)
1. **One driver per batch.** Start it with the Bash tool's `run_in_background: true`, never a bare `nohup`. It writes
   `build/rx/status.txt` per step and ends with `DONE` or `FAILED` (plus the log tail).
2. **Each step checks its outputs** before the next one starts: row counts, and no "singular" or "Transient op
   started" in the logs. Judge by output files and log tails, not exit codes. On a failure, diagnose and retry at
   most twice, then write up and stop.
3. **Heartbeat:** ScheduleWakeup at about 1.5× the step's ETA (20–60 min), re-armed until done.
4. **Progress line:** at each phase or step change, commit and push the first line of this file:
   `> Running: phase C, step 2 since HH:MM, ETA HH:MM`. Send a PushNotification to Matt at the end or on a stop, if
   the tool is available.
5. **Between phases, carry straight on.** Don't wait to be asked.
6. **CPU budget:** use `.claude/skills/mixed-signal-asic/scripts/sched.py` or `xargs -P`, and leave 2 cores free.

## Don't
- Don't commit `sim.yaml` or anything under `build/`. Stage named files, never `git add -A`.
- Don't change the ring, DAC, reference, lsdiv, tx_drv or tx_fine circuits. Exposing a2 / a3 and adding the second
  `ls_ac` outside them is the only change.
- Don't start layout: Matt reviews first.
- Don't run temperature, VDD or Monte Carlo sweeps in this pass.

## Done
When everything is pushed, replace the first line with `> Done (date): results in docs/rx_design.md`.
