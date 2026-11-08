# Handoff: power-on start-up of the current-fed ring (sim pod)

**Goal: show that the current-fed ring, with its reference, RC filter and 3 pF vg decap, comes up from VDD = 0 into a
clean fundamental-mode oscillation at the expected frequency, at code 0 and code 31. Commit the results to
`docs/cfed_startup_results.md` and `sim/results/<date>/startup/`.**

A laptop agent is working in `layout/gen/` and `sim/mc/` at the same time. **You own `sim/pn/` and this file.** Use
your own clone, `/foss/designs/gf433-sims` (`git pull --rebase` first).

## Read first
- This file.
- `docs/cfed_sizing_results.md` (the design and its settings).
- `docs/handoff_autonomy.md` (the rules and the corner policy).
- The `startup` and `ringstart` modes in `sim/vco/vco_bias.py`, which you can reuse.

## Design under test (schematic)
- The winner reference from `sim/results/2026-11-08/winner_sets.txt`, with `lnw=5.023`.
- Plus `topo=cfed kc=0.75 k=6 cvg=3e-12 cw=3e-15 ka=16 wfu=0.30 wff=0.30 rf=1e6 cf=20e-12`.
- The vg decap is the ideal 3 pF. The v3 layout's MOS decap is within 0.1 %.

## Config (corner lists; the driver reads these)
```
MAIN_CORNERS = typical ss ff sf fs ; MAIN_TEMPS = 27
ROBUST_CORNERS = ss ff ; ROBUST_TEMPS = 0 70     # start-up is a robustness check (corner policy)
CODES = 0 31 ; VCTRL = 1.65 ; VDD_RAMP = 0 -> 3.3 V in 10 us, and in 1 us
```
That is (5 + 4) × 2 codes × 2 ramps = 36 runs.

## Test
1. **Power-on.** Every node starts at 0 V: VDD, vbn, vbnf, vg, the ring nodes, and the reference. No `.ic` or `uic`
   tricks beyond all-zero. Ramp VDD, then run until vbnf and vg settle. The RC filter's τ is about 20 µs, so expect
   about 150 µs; measure it from one case first, and set the run length to settle + 20 µs.
2. **Per run, report:**
   - **Reference:** does it start? Give the time for vbn to reach 1 % of its DC value.
   - **vg:** its settling time to 2 % (no sustained oscillation of vg itself).
   - **Ring:**
     - the time the ring starts oscillating;
     - the final f against the DC-start value from `map.csv` (within 1 %);
     - the swing;
     - the **mode**: the phase from an a0 rise to the next a2 rise, as a fraction of the period, must be 0.2 ± 0.07.
       This is the classifier in `vco_bias.py ringstart`.
   - **Anything odd:** a stuck state (no oscillation by the end), a higher mode, or vg overshoot above VDD.
3. **First, to set run length and step size:** run tt 27 °C, code 0, 10 µs ramp, once. Choose the transient max step
   so that f is accurate to 0.1 % in the final 2 µs (compare two step sizes). Record the wall time, and estimate the
   rest before launching.

## Running unattended
Follow `docs/handoff_autonomy.md` in full:
- one driver started with `run_in_background`;
- `status.txt` with `DONE` / `FAILED`;
- output checks per step;
- a `Running: step N/M since…, ETA (this step)` line pushed at each step change;
- a ScheduleWakeup heartbeat of at most 60 min, re-armed;
- write up and push straight after;
- ≤ 20 CPUs.

**Add a short "autonomy" table to the results doc, the same as last time.**

## Results doc and commit
`docs/cfed_startup_results.md` gives:
- the method;
- a 36-row table;
- the worst start-up time;
- any failure, with waveforms (save PNGs of the worst case: VDD, vbn, vbnf, vg and a0 against time);
- run times;
- script fixes;
- the autonomy table.

Copy small files into `sim/results/<date>/startup/`. Stage and commit in one command, never `git add -A`, and never
commit `build/` or `sim.yaml`. Then `git pull --rebase` and `git push`.

## Don't
- Don't change design values.
- Don't edit `layout/`, `sim/mc/` or `sim/vco/` defaults. Adding modes is fine; keep default netlists byte-identical.

## Done
When pushed, replace the top line with `> Done (date): see docs/cfed_startup_results.md`.
