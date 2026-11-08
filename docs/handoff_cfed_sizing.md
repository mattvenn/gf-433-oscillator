> Running: sims done 12:46, write-up in progress

# Handoff: current-fed ring final sizing, PVT tuning map and PVT noise (sim pod)

**Goal: size the DAC width of the current-fed ring so that, with the temperature compensation re-nulled, it covers
the tuning range at every PVT point. Then measure its full tuning map and its rms FM over PVT. Commit the results to
`docs/cfed_sizing_results.md` and `sim/results/<date>/cfed/`.**

A laptop agent is drawing the v3 layout of the same circuit at the same time. **You own `sim/` and `docs/cfed_*`;
don't touch `layout/` or `mag/`.** Work in your own clone, `/foss/designs/gf433-sims`.

## Read first
- This file.
- `docs/cfed_results.md`: the circuit, the noise method, and why the range broke.
- The docstring of `sim/pn/cfed_noise.py`, which has all the modes you need.
- `.claude/skills/mixed-signal-asic/SKILL.md` and `references/verification.md`.

## Fixed settings
- The winner reference: `sim/results/2026-11-08/winner_sets.txt`.
- Plus `topo=cfed kc=0.75 k=6 cvg=3e-12 cw=3e-15 ka=16 rf=1e6 cf=20e-12`.
- cw = 3 fF is the current estimate. The v3 layout will give a new number later, so record cw with every result.

## Job 1: DAC width against tempco against range
For DAC width scale w ∈ {1.0, 1.1, 1.2, 1.3, 1.4} (`wfu = wff = 0.25·w`):
1. **Find the null jointly.** At tt, find the n-well length `lnw` (lnp = 100) and the code nearest 433.92 MHz
   (vctrl 1.65 V) together, so that the tempco at that code is nulled. `cfed_noise.py tc` has the search;
   `docs/cfed_results.md` explains why it has to be joint.
2. **Range:** at 5 corners × 0/70 °C, code 0 at vctrl 0 must be ≤ 310 MHz and code 31 at vctrl 3.3 V must be
   ≥ 700 MHz.
3. **Step vs fine:** fine ≥ 1.3 × the coarse step at ss 70 °C, tt 27 °C and ff 0 °C.
4. **Tempco at each corner's own 433.92 code.** The tempco depends on the code, so report it per corner.

**Pick** the smallest w that passes the range, with |tempco| ≤ 50 ppm/°C at tt. Report every w.

## Job 2: full tuning map of the winner
Codes 0–31 × vctrl {0, 1.65, 3.3} × 5 corners × {0, 27, 70} °C × VDD {3.15, 3.3, 3.45}.
Report, per point:
- the range, the 433.92 codes, the worst step against the fine range, and monotonicity;
- **plus** the vg and swing range (the level shifter needs it).

## Job 3: noise over PVT
At each of 5 corners × {0, 27, 70} °C, at that point's 433.92 code:
- run `cfed_noise.py ki` and `dacn`;
- report rms FM over 1–10 kHz and 1–100 kHz, split into ref/vbn and DAC;
- also run `isf` at tt 27 °C only (m = 40, or finer if time allows).

Worst case against 15 kHz (1–10 kHz).

## Running unattended (from docs/handoff_autonomy.md; this run tests those rules)
1. **One driver script,** `sim/pn/cfed_sizing_run.sh`, chains Job 1, then Job 2 and Job 3 on the winner, then the
   summary tables. Job 2 and Job 3 read the winning w and lnw from Job 1's output file, not from you.
2. **Launch it with the Bash tool's `run_in_background: true`.** Don't use bare `nohup`. If you need nohup, also
   start a Monitor on `build/cfed_sizing/DONE` or `FAILED`.
3. **Status files.** Each step writes `build/cfed_sizing/status.txt` (step, start time, done or failed). Each step
   checks its own outputs before the next starts: expected row counts, no "Transient op started", no "singular".
   On failure, write `FAILED` with the log tail and stop. Diagnose and retry at most twice.
4. **Heartbeat fallback.** After launching, schedule a wakeup (ScheduleWakeup) at about 1.5× your time estimate,
   at least 20 minutes.
5. **Progress Matt can see.** At each step change, commit and push the line at the top of this file:
   `> Running: step N/4 since HH:MM, ETA HH:MM`. Send a PushNotification on finish or failure, if that tool is
   available.
6. **Finish in one go.** When the driver ends, go straight on to the write-up, commit and push without waiting to
   be asked. Record the time from the last sim ending to the push.
7. **Stay within 20 CPUs** (`--jobs`, or `.claude/skills/mixed-signal-asic/scripts/sched.py`).

## Results doc and commit
`docs/cfed_sizing_results.md`:
- the image tag and ngspice version;
- per job: a method paragraph, a table, and 2–4 sentences of conclusion;
- run times from timestamps;
- script fixes;
- **a short "autonomy test" section:** did each rule work? (tracked launch, the step chain, status pushes,
  the wake-up on finish, the time to push).

Copy small result files into `sim/results/<date>/cfed/`. Stage and commit in one command, never `git add -A`,
and never commit `build/` or `sim.yaml`. Then `git pull --rebase` and `git push`.

## Don't
- Don't change the inverter sizes, k, kc or cvg. Don't change any non-cfed defaults in `vco_bias.py`.
- Don't edit `layout/`, `mag/` or the datasheet.

## Done
When pushed, replace the Running line at the top with `> Done (date): see docs/cfed_sizing_results.md`.
