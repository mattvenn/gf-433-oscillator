> Done (2026-11-08, run on sim0 from the gf433-dev session; re-run on the corrected core at 18:00): results in docs/remap_results.md
# Handoff: re-map the 433.92 MHz codes on the extracted core, with the level shifter on a0 (sim pod)

**Goal: find each corner's 433.92 MHz code (and the codes whose vctrl range covers it) on the RC-extracted v3
core, loaded by the level shifter + ÷4. Commit the table to `sim/lsdiv/results/remap.md` and a short write-up to
`docs/remap_results.md`.**

Why: the schematic tuning map's 433.92 codes give only 367–378 MHz on the extracted core (`docs/lsdiv_design.md`),
the map reads about 1.3 % high (100–200 ns window), and the level shifter pulls f down another 1.0–1.2 %. Bring-up
and the `docs/tuning.md` procedure need the real codes.

A laptop agent is drawing the level-shifter layout at the same time. **You own `sim/lsdiv/results/remap*`,
`docs/remap_results.md` and `build/remap/`; don't touch `layout/`, `xschem/` or `sim/lsdiv/lsdiv.py`.** Work in your
own clone, `/foss/designs/gf433-sims` (`git pull --rebase` first: the scripts below are new).

## Read first
- This file.
- The docstrings of `sim/lsdiv/remap.py` and `sim/lsdiv/run_remap.sh`.
- `docs/lsdiv_design.md` (the block and its deck), `docs/cfed_v3_check.md` (the extracted-core range).

## What runs (all in `sim/lsdiv/run_remap.sh`)
| step | points | corners | why these |
|---|---|---|---|
| 1 codes | codes 0–31 at vctrl 1.65 V | tt, ss, ff, sf, fs at 27 °C, 3.3 V | the code → f curve per corner; room temperature only (Matt); VDD moves f by −0.008 %/10 mV, so it is left out |
| 2 fine | per corner, the 4 codes around 433.92 × vctrl 0 / 1.0 / 2.3 / 3.3 V | same | which codes cover 433.92 within the fine range (Kvco is flat below about 1 V and square-law above) |
| 3 summary | – | – | `sim/lsdiv/results/remap.md` + `remap.csv` |

Each point is the `lsdiv.py` deck: the full reference with the 1 MΩ / 20 pF filter, the extracted core
(`layout/pex/ring_core_v3_w30chk_rc.spice`), and the drawn lsdiv block (real R1 / C1, `S["real"] = 1`) on a0.
DC operating point with the ring held, 1.2 µs, f over 0.72–1.2 µs (settled; `f_drift` is in the output).
One point takes about 2 minutes; 240 points at `JOBS=16` is about 35 minutes (use the pod's cores, leave 2 free).

## Running unattended (docs/handoff_autonomy.md)
1. **Launch** `JOBS=16 bash sim/lsdiv/run_remap.sh` with the Bash tool's `run_in_background: true`. No bare nohup.
2. The driver writes `build/remap/status.txt` per step and ends with `build/remap/DONE` or `FAILED` (with the log
   tail). Each step checks its row count and greps the deck logs for "singular" / "Transient op started".
   On `FAILED`, diagnose, retry at most twice, then write up what you have and stop.
3. **Heartbeat:** ScheduleWakeup at about 50 minutes; re-arm if it fires before DONE.
4. **Progress line:** at each step change, commit and push the line at the top of this file:
   `> Running: step N/3 since HH:MM, ETA HH:MM`. PushNotification to Matt on finish or failure, if available.
5. **When DONE, carry straight on** to the write-up, commit and push, without waiting to be asked.

## Write-up (`docs/remap_results.md`, Matt's technical style: plain, factual, problem → result → limits)
- The table from `remap.md`, and per corner the recommended code (433.92 inside its vctrl range, as near
  vctrl 1.65 V as possible) and the vctrl that gives 433.92 there (interpolate from the fine points).
- The shift against the schematic map codes (tt 9, ss 11, ff 7, sf 9, fs 9) and against the RC check without the
  level shifter (tt 12, ss 14–15, ff 10).
- Range check at 27 °C: code 0 at vctrl 0 and code 31 at vctrl 3.3 per corner, if you have them (code 31 / 0 are
  only at 1.65 V in step 1; say so rather than extrapolate).
- Limits: the a0 load is the schematic block plus the modelled Cc; the extracted level-shifter layout comes later
  and may move f by a few tenths of a percent. 27 °C only.
- Update the "433.92 codes" row of `STATUS.md` only if it is clearly yours to change; otherwise put the new codes in
  the doc and leave STATUS to the laptop session.

## Don't
- Don't change `sim/lsdiv/lsdiv.py` (the layout agent may be editing it); if `remap.py` needs a fix, fix it there.
- Don't commit `sim.yaml` or anything under `build/`. Stage files by name, never `git add -A`.

## Done
When pushed, replace the Running line with: `> Done (date): results in docs/remap_results.md`.
