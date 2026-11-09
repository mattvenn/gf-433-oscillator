> Done (2026-11-09): results in docs/gf_silicon_factor.md
# Handoff: GF silicon factor from a measured ttgf0p2 ring (sim pod)

**Goal: simulate the ring configurations of `tt_um_algofoogle_vgaringosc` (ttgf0p2, mux address 614) from its
extracted layout, and compare them with today's silicon measurements. The ratio f_silicon / f_sim is the GF silicon
factor, the one Gate 1 input still open (`STATUS.md`). Commit `sim/silicon_factor/results.md` + `results.csv` and a
short write-up, `docs/gf_silicon_factor.md`.**

Why: our VCO's tuning range has to cover ×0.7 … ×1.4 until the GF silicon / simulation factor is known (sky130 was
×0.866). The bench measured a public GF design today (`bench/2026-11-09/`, and
github.com/mattvenn/ttgf0p2-vgaringosc-measurements). Its fixed 5× inv_1 ring is the closest match to our 5-stage
ring (no tap multiplexer in its loop). The tapped inv_2 chain (3…161 stages) gives the delay per stage separately
from the fixed overhead.

**You own `sim/silicon_factor/`, `build/silicon_factor/` and `docs/gf_silicon_factor.md`.** Work in your own clone,
`/foss/designs/gf433-sims` (`git pull --rebase` first: the scripts are new).

## Read first
- This file, and the docstrings of `sim/silicon_factor/{extract.sh,tb.py,run.sh,summary.py}`.
- `bench/2026-11-09/raw/notes_div8.txt` (how the silicon numbers were taken).

## The measurements (chip 1, 27 °C nominal: the lab was not temperature-controlled; VDD_CORE 3.300 V)
| cfg | path | stages | silicon f (MHz) |
|---|---|---|---|
| inv1x5 | clksel2 = 1, fixed 5× inv_1 | 5 | 319.6 (least certain: wide single-reading spread) |
| inv4x5 | clksel2 = 2, fixed 5× inv_4 | 5 | 206.5 (chip 2 only, unconfirmed: irregular ÷8 output) |
| t3, t5, t9, t33, t65, t161 | clksel = 2, 3, 5, 10, 13, 15 | 3 … 161 | 220.51, 196.22, 160.66, 77.69, 49.87, 23.72 |

Chip 2 ran about 2 % slower (t3 216.0, inv1x5 311.6 MHz). These values are in `tb.py` (`F_MEAS`) and `summary.py`.

## What runs (all in `sim/silicon_factor/run.sh`)
Config: `JOBS=8 CORNERS="typical ss ff sf fs"` (edit the corner list here, not in the script).

| step | what | corners | why |
|---|---|---|---|
| 1 | fetch the shuttle OASIS (pinned commit), convert to GDS, magic 8.3.642 C extraction of the whole 1×1 tile (4 s on the laptop, about 11.9k MOSFETs, 69k caps) | – | the layout that was fabricated |
| 2 | 8 ring configs | typical, 27 °C, 3.3 V | the factor itself (typical) |
| 3 | 8 ring configs | ss, ff, sf, fs | new circuit, so the full process set once (corner policy); does the silicon fall inside the corner spread? |
| 4 | RC extraction, then inv1x5 and t3 | typical | how much wire R moves the short rings; magic's rc mode double-counts C on ports (`docs/rc_extraction_fix.md`), so the C netlist stays the main result |
| 5 | `summary.py` → `results.md` | – | the table |

**Run time:** the full tile simulates at about **7–8 ns per minute** on the laptop (KLU solver, 4 threads). `tb.py`
sizes each run as 20 ns of start-up + 7 periods at 0.6× the silicon frequency: from about 8 min (inv1x5) to about
70 min (t161) per run, about 3 h of job time per corner. At `JOBS=8` (set `num_threads` in `.spiceinit` so that
JOBS × threads ≤ the pod's cores, leave 2 free), expect about **2–2.5 h** in total.
Temperature: 27 °C only (Matt: room temperature). VDD: 3.3 V only (the bench supply was 3.300 V).

Stimulus (in `tb.py`): ena = 1, clk held low, rst_n released at 10 ns, ui_in[3:0] = clksel, uio_in[1:0] = clksel2.
Measured: uio_out[4] (the selected clock through a buf_1) at VDD/2, periods after the first edge. Check `vmin`/`vmax`
in `results.csv`: it should be full-swing logic; a reduced swing means the deck is wrong.

## Running unattended (docs/handoff_autonomy.md)
1. **Launch** `JOBS=8 bash sim/silicon_factor/run.sh` with the Bash tool's `run_in_background: true`. No bare nohup.
2. The driver writes `build/silicon_factor/status.txt` per step and ends with `DONE` or `FAILED` (log tail). Each step
   checks its row count, flags non-`ok` rows, and greps the deck logs for "singular" / "Transient op started".
   On `FAILED`, diagnose, retry at most twice, then write up what you have and stop.
3. **Heartbeat:** ScheduleWakeup at about 60 minutes; re-arm until DONE.
4. **Progress line:** at each step change, commit and push the first line of this file:
   `> Running: step N/5 since HH:MM, ETA HH:MM`. PushNotification to Matt on finish or failure, if available.
5. **When DONE, carry straight on** to the write-up, commit and push, without waiting to be asked.

## Write-up (`docs/gf_silicon_factor.md`, Matt's technical style: plain, factual, problem → result → limits)
- The table from `results.md`. Headline: **the factor at typical for inv1x5** (closest to our ring) and for the
  inv_2 taps (their spread), and whether the silicon lies inside the ss … ff simulated range.
- Fit T = a·N + b to the simulated taps as on the bench (bench: a = 0.240 ns/stage, b = 4.19 ns); compare a (gate
  delay) and b (overhead) separately: which part carries the silicon/sim difference?
- What it means for our VCO: the tuning range needed, if the same factor applied (our extracted range at
  vctrl 1.65 V: 193–851 MHz; 433.92 MHz at codes 7–11 per corner, `docs/remap_results.md`).
- Limits, stated plainly:
  - one wafer, two chips;
  - the lab temperature was not controlled;
  - standard-cell rings, not our current-fed ring, so the factor transfers to our design only through the same
    devices (5 V nfet/pfet_05v0 at 3.3 V; our ring uses the same family);
  - C-only extraction;
  - the 5× inv_1 point is the least certain silicon value;
  - inv4x5 is unconfirmed.
- Update `STATUS.md` only for the "GF silicon factor" line; leave everything else to the laptop session.

## Don't
- Don't commit `sim.yaml` or anything under `build/`. Stage files by name, never `git add -A`.
- Don't change files outside the ones you own (above).

## Done
When pushed, replace the first line with: `> Done (date): results in docs/gf_silicon_factor.md`.
