> Running: step V-D since 22:07, ETA 22:27 (all short runs, local)

# Handoff: TX harmonic reduction, option 1 (slew-controlled final stage), block sims (sim0)

**Goal: find out whether a slew-controlled final stage in the TX driver gets the 3rd and 5th harmonics at the dipole
to −36 dBc or lower at all five process corners, and what it costs in fundamental, current and duty. This is a
block-level simulation study on `sim/tx/tx_drv.py` + `sim/tx/tb_tx_drv.py`, not a layout task.**

**Work on the branch `tx-harmonics`** in your clone `/foss/designs/gf433-sims`:
`git fetch && git checkout tx-harmonics && git pull --rebase`. Commit and push to that branch only, never to `main`
(Matt merges it after review). Stage named files and commit in one command; never `git add -A`; never commit
`sim.yaml`, `build/` or `.spiceinit`.

## Read first
- This file, then `STATUS.md` item 5 (TX driver) and `docs/tx_driver.md` ("Harmonics" under the limits).
- The docstrings of `sim/tx/tx_drv.py` (the circuit) and `sim/tx/tb_tx_drv.py` (the bench).
- `.claude/skills/mixed-signal-asic/SKILL.md` (written for sky130; this is gf180mcuD, 3.3 V devices).

## Why (2026-11-12)
- The driver (NAND2 + 5 inverters tapered ×4, final N 40 / P 100 µm) drives the dipole with a near-square wave.
  At tt, 73 Ω sees **H3 −14.1 dBc, H5 −23.3 dBc**; the even harmonics cancel (−41 dBc). The pad path filters only
  ~2.6 dB, and a half-wave dipole is near resonance again at 3f.
- **Target:** ETSI EN 300 220 spurious emissions above 1 GHz are −30 dBm. At our ~+6 dBm fundamental, that is
  about **−36 dBc** for H3 (1.30 GHz) and H5 (2.17 GHz). Treat −36 dBc conducted at the dipole as the pass line and
  −40 dBc as the goal (margin for the antenna's gain at 3f, which is not modelled).
- **No board components** except the dipoles (Matt, 2026-11-10), so no board filter: the fix is on chip.
- **Option 1 (this handoff):** turn-on edges of about T/3 (0.77 ns). A trapezoid's harmonics scale as
  sinc(n·π·t_r/T), so t_r = T/3 nulls H3 and cuts H5 by roughly 15 dB, for about 1.7 dB of fundamental. The catch
  is that the edge rate moves with process, so the null moves with corner.
- **Option 2 (not this handoff):** two ring taps 72° apart summed in a split final stage: about −8 dB on H3 at
  every corner, but nothing on H5. Matt may combine the two later; note anything that bears on that.

## The circuit to build (in `sim/tx/tx_drv.py`, behind a switch)
Add a parameter `shape` to `S` (default `0`). **With `shape=0` the netlist must be byte-identical to today's**
(diff `python3 sim/tx/tx_drv.py` before and after), so the xschem check and the tile LVS on `main` are unaffected.
With `shape=1`, change only `tx_arm`'s last two stages:

1. **Split the final stage's gate drive (break-before-make).** Stage 4 becomes two predrivers from y3:
   - `gp` drives the final PMOS gate. Turning the PMOS **off** is `gp` rising: fast (full-size pull-up). Turning it
     **on** is `gp` falling: slow, through a current-starved pull-down (an NMOS switch in series with an NMOS current
     source on bias `vsn`).
   - `gn` drives the final NMOS gate. Turning the NMOS **off** is `gn` falling: fast (full-size pull-down). Turning
     it **on** is `gn` rising: slow, through a current-starved pull-up (a PMOS switch in series with a PMOS current
     source on bias `vsp`).
   - So only one output device conducts at a time (no crowbar), and the shaped edge is always the one turning on.
   - Keep the stage count so the arm still inverts the same number of times (`out = in & en`); check `--off` still
     holds both outputs low.
2. **Bias the starved legs from a reference current.** A `tx_slew_bias` subcircuit: an ideal current `islew` into an
   NMOS diode (gives `vsn`), mirrored into a PMOS diode (gives `vsp`), with mirror ratio `kmir` so the static diode
   current is small (e.g. 1:10). In the real design this current comes from the constant-gm reference (`vbn`), so
   use a mirror device size that would work from a few µA–tens of µA; the bias wiring to the reference is a later
   step. Expose `islew` (the edge current per starved leg) and `knp` (the N-side / P-side current ratio, to balance
   the two edges) as parameters.
3. **Starting point.** The final gates are roughly C ≈ 50 fF (N 40 µm) and 125 fF (P 100 µm) plus Miller. A ~0.8 ns
   ramp needs I ≈ C·ΔV/t ≈ 0.25 mA (N side) and 0.6 mA (P side). Sweep **islew 50 µA – 2 mA** (log steps), knp
   around the C ratio.
4. **Trim (design only, no macro change).** Model a 2-bit trim as parallel starved legs (×0.7 / ×1 / ×1.4 / ×2 of
   the base, or similar), held at constants in the bench. Decide from the corner spread whether it's needed.

Keep the existing splitter, NAND2, earlier stages, decap and final widths unless the study shows a reason; if the
final stage needs widening to win back fundamental, report it (and the pin current, see below).

## The bench (`sim/tx/tb_tx_drv.py`)
- The deck already runs `fourier` on `vr` (the voltage across the 73 Ω), `out_p`, `out_n`; `parse()` reads only
  harmonic 1. **Add H2–H7 of `vr` in dBc** to the record, plus the **pin current rms** (the dipole current,
  √(P / 73 Ω)), and an efficiency P_dip / (VDD × I_avg).
- **Validate first:** today's circuit at tt, `--rroute 40 --noff 3`, must give H3 ≈ −14.1 and H5 ≈ −23.3 dBc (as in
  `docs/tx_driver.md`). If not, stop and find out why before any sweep.
- Check the time step is fine enough for H5–H7 (it is 2 ps; keep it) and that 8 periods after 40 ns settle the
  dipole C (`vcap_drift_mv` small).

## Runs (corners: all five process corners at 27 °C, 3.3 V; they are cheap, and the null moves with process)
- **A. Baseline:** today's circuit, 5 corners × rroute 15 / 40 / 60 × n_off 0 / 3. This is the reference table.
- **B. Sweep at tt:** `shape=1`, islew × knp (rroute 40, n_off 3). Find the H3 null, the H5 level there, and the
  knp that keeps duty 48–52 % and the even harmonics ≤ −36 dBc.
- **C. Corners:** the tt-best setting at ss / ff / sf / fs; then each corner's own best islew. The spread between
  the two answers is the case for (or against) a trim. Show H3 against islew per corner in one figure.
- **D. Robustness at the chosen setting (and trim codes):** 5 corners × rroute 15 / 40 / 60 × n_off 0 / 3; a tt
  20 / 35 °C spot check (null drift); VDD 3.15 V at the worst corner. `--off` at tt (outputs low, no DC).
- Expected size: a few hundred short transients (seconds each). Use `xargs -P` or `sched.py`, leave 2 cores free.

## Report for each setting
fundamental (dBm), H2–H7 (dBc), duty out_p / out_n, phase error, I(VDD) avg / rms / peak, VDD ripple, pin current
rms (**limit 10 mA rms per `ua` pin**, tnt; today 7.8–8.1 at tt / 40 Ω and 10.8–11.1 at ff / 15 Ω), efficiency.

## Pass / stop
- **Pass:** H3 and H5 ≤ −36 dBc at all 5 corners (with one trim code per corner, if a trim is used), fundamental
  ≥ +3 dBm at the worst corner (today +3.7…+9.3), duty 48–52 %, even harmonics ≤ −36 dBc, pin current no worse
  than today.
- **If it can't pass:** report the best achievable per corner and what's left (e.g. H3 −28 at ff), and estimate
  what adding option 2 (×0.31 on H3, ×1 on H5, using `cos(n·36°)` per harmonic) would give on top. Don't build
  option 2.
- **Stop and report** (don't push on) if the shaped edge makes the output fail to swing rail to rail, the duty
  can't be held 48–52 % with knp, or `--off` stops holding the outputs low.

## Deliverables (on `tx-harmonics`)
- `sim/tx/tx_drv.py` (`shape` switch), `sim/tx/tb_tx_drv.py` (harmonics, pin current), one driver script
  `sim/tx/run_harmonics.sh` (or `.py`) for runs A–D.
- `sim/tx/results/harmonics.md`: the tables from A–D.
- `docs/tx_harmonics.md` in Matt's technical style: problem → fix → evidence, every acronym expanded at first use,
  "Fig. N." captions that give the measured value, honest limits ("at the time of writing"), Made with Claude badge.
  Figures in `docs/img/`: (1) harmonic bars today vs shaped at tt; (2) H3 and H5 against islew, one line per
  corner; (3) the out_p / dipole waveforms, today vs shaped. Keep it short.
- `STATUS.md` item 5: replace the "To check: on-chip harmonic reduction" bullet's option-1 line with the result
  and a link.
- Not in scope: xschem sheets, layout, the macro's trim bits, the reference's bias wiring. List what they would
  need in the doc's "Next steps".

## Running unattended (`docs/handoff_autonomy.md`)
1. **One driver** for the batch, started with the Bash tool's `run_in_background: true`, never a bare `nohup`. It
   writes `build/tx_harm/status.txt` per step and ends with `build/tx_harm/DONE` or `FAILED` (plus the log tail).
2. Each step checks its outputs (row counts; no "singular" or "Transient op started" in the logs; the baseline
   reproduces −14.1 / −23.3 dBc) before the next one starts. On a failure, diagnose and retry at most twice, then
   write up and stop.
3. Heartbeat: ScheduleWakeup at about 1.5× the step's ETA (20–60 min), re-armed until done.
4. At each step change, commit and push the first line of this file to `tx-harmonics`:
   `> Running: step B since HH:MM, ETA HH:MM`. Send a PushNotification to Matt at the end or on a stop, if the tool
   is available.
5. Carry straight on between steps and on to the write-up. Don't wait to be asked.
6. **Time budget:** about 2 hours in all. If the sweeps run long, cut the D matrix (keep tt / ss / ff) rather than
   the write-up.

## Traps (from this project)
- `rm` is aliased to `rm -i`: use `command rm -f`. `gh` isn't installed: use curl against the GitHub API.
- Kill your own ngspice runs with `[x]`-bracketed `pkill -f` patterns (a plain one matches its own shell).
- Judge runs by output files and log tails, not exit codes.
- The block bench assumes VDPWR via 1 Ω + 1 nH (the TT grid and bond wires aren't modelled); keep that, and say so.

## Done
When everything is pushed to `tx-harmonics`, replace the first line with
`> Done (date): results in docs/tx_harmonics.md (branch tx-harmonics)`.
