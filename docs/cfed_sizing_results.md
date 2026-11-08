# Current-fed ring: DAC sizing, PVT tuning map and PVT noise (sim pod, 2026-11-08)

Brief: `docs/handoff_cfed_sizing.md`.

**Result: w = 1.2 (`wfu = wff = 0.30 µm`) with lnw = 5.023 µm (lnp = 100).**
- **tt 27 °C:** code 9 at 434.1 MHz, with a tempco of +1.6 ppm/°C.
- **Range:** the worst corner covers 228.3–749.9 MHz over 5 corners × 0/27/70 °C × VDD 3.15/3.3/3.45. The target is
  ≤ 310 / ≥ 700 MHz.
- **Tuning:** monotonic everywhere; the worst fine/step is 2.08 against the 1.3 needed.
- **Noise:** the worst rms FM over 1–10 kHz is 8.26 kHz (sf 0 °C), against the 15 kHz limit.

## Setup
- **Tools:** iic-osic-tools image 2026.09 (sim-0 pod, run in the image directly), ngspice-47 (KLU), gf180mcuD.
  Every ngspice process runs single-threaded, with at most 20 at a time.
- **Circuit:** `sim/vco/vco_bias.py` with `topo=cfed`.
  - The winner reference is `sim/results/2026-11-08/winner_sets.txt`.
  - The settings on top are `kc=0.75 k=6 cvg=3e-12 cw=3e-15 ka=16 rf=1e6 cf=20e-12`.
  - **cw = 3 fF throughout.** This is the current estimate; rerun Job 2 when the v3 layout gives its number.
  - Inverter sizes, k, kc and cvg are unchanged. No non-cfed default in `vco_bias.py` was touched.
- **Scripts:**
  - `sim/pn/cfed_sizing_run.sh` is the driver.
  - `sim/pn/cfed_sizing.py` holds the steps (null, check, pick, map, noise, summary).
  - `sim/pn/cfed_noise.py` provides ki, dacn and isf.
  - Frequency is taken from the a0 mid-swing crossings over 100–200 ns (`topo_cmp.deck`).
- **Outputs:**
  - Raw results are in `build/cfed_sizing/` and `build/cfed/sz_*`.
  - The small files are in `sim/results/2026-11-08/cfed/`:
    - `summary.md`, with every table in full;
    - `null.json`, `check.json`, `winner.json`;
    - `map.csv` (4320 points), `map_summary.json`;
    - `noise.json`, `isf_tt27.json`;
    - `status.txt`.
- **Corner policy:** these runs follow the corners in the brief. `docs/handoff_autonomy.md` gained a new corner
  policy (room temperature only) while the run was in progress, so the 0 / 70 °C and VDD columns below are more than
  that policy asks for. They are kept as one full-PVT snapshot of this circuit revision.

## Job 1: DAC width vs tempco vs range

**Method.** For each w in {1.0, 1.1, 1.2, 1.3, 1.4} I set wfu = wff = 0.25·w, then found lnw and the nearest-433.92
code together.
- **Evaluation:** each one is codes 0–31 at vctrl 1.65 V and VDD 3.3 V, at 0/27/70 °C, tt. The nearest code is the
  one closest to 433.92 MHz at 27 °C. The tempco is the least-squares slope over 0/27/70 °C divided by f(27 °C).
- **Search:**
  1. Start from a grid of lnw = 3, 4.5, 6, 7.5, 9 µm.
  2. Then iterate: a secant root at a fixed code, accepted only if that code is still the nearest at the root;
     otherwise bisect, because the null falls on a code switch.
  3. 3 to 4 iterations brought every w to within 2 ppm/°C at tt (7–8 evaluations each).
- **Checks at each null:** a full grid of 5 corners × 0/27/70 °C × codes 0–31 × vctrl 0/1.65/3.3 at 3.3 V. It gives:
  - the range: code 0 at vctrl 0 and code 31 at vctrl 3.3, at 0 and 70 °C;
  - the coarse step against the fine range at ss 70, tt 27 and ff 0 °C;
  - the tempco at each corner's own 433.92 code (its nearest code at 27 °C).

| w | wfu=wff µm | lnw µm | tt code | f(27 °C) MHz | tempco tt ppm/°C | worst fmin MHz | worst fmax MHz | range | min fine/step ss70 / tt27 / ff0 | tempco at each corner's own code (code: ppm/°C) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1.0 | 0.250 | 5.497 | 14 | 437.1 | −0.6 | 183.8 | 631.8 | **fail** | 2.67 / 4.10 / 5.90 | tt 14: −1, ss 16: +30, ff 11: −28, sf 14: +68, fs 14: −13 |
| 1.1 | 0.275 | 5.296 | 11 | 429.0 | −1.0 | 204.2 | 688.2 | **fail** | 2.48 / 3.87 / 5.61 | tt 11: −1, ss 14: +14, ff 9: −46, sf 11: +71, fs 12: −35 |
| **1.2** | 0.300 | 5.023 | 9 | 434.1 | +1.6 | 227.2 | 750.9 | pass | 2.25 / 3.58 / 5.25 | tt 9: +2, ss 11: +27, ff 7: −50, sf 9: +74, fs 9: −24 |
| 1.3 | 0.325 | 4.627 | 7 | 443.2 | +0.2 | 259.0 | 831.6 | pass | 1.92 / 3.17 / 4.73 | tt 7: 0, ss 8: +53, ff 5: −56, sf 7: +78, fs 7: −26 |
| 1.4 | 0.350 | 4.462 | 5 | 429.3 | −1.8 | 283.3 | 891.4 | pass | 1.74 / 2.95 / 4.46 | tt 5: −2, ss 7: +31, ff 4: −80, sf 5: +82, fs 5: −33 |

Range per corner, as fmin at code 0 vctrl 0 / fmax at code 31 vctrl 3.3, in MHz:

| w | tt 0 | tt 70 | ss 0 | ss 70 | ff 0 | ff 70 | sf 0 | sf 70 | fs 0 | fs 70 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1.0 | 160/718 | 168/**693** | 147/**651** | 156/**632** | 175/799 | 184/766 | 156/720 | 164/**698** | 159/708 | 168/**682** |
| 1.1 | 179/783 | 187/754 | 165/710 | 174/**688** | 195/869 | 204/831 | 175/787 | 184/760 | 177/771 | 186/741 |
| 1.2 | 200/854 | 208/821 | 185/776 | 193/751 | 218/946 | 227/903 | 197/860 | 206/830 | 197/840 | 206/806 |

**Conclusion.**
- **The pick is w = 1.2, lnw = 5.023 µm.** It is the smallest w that meets the range at all 10 corner × 0/70 °C points,
  and its tt tempco is +1.6 ppm/°C, well inside 50.
- **The top of the range sets the width.** ss 70 °C sets fmax, and the bottom has plenty of margin: 228 MHz worst
  against 310. Each 0.1 step in w adds about 60 MHz at the top and moves the null to roughly 2 codes lower.
- **Step vs fine** is comfortable at every w; the worst is ss 70 °C at code 30.
- **The tempco is nulled only at tt.** At each corner's own code it spreads from −50 (ff) to +74 ppm/°C (sf). sf is
  the outlier at every w: the PMOS-strong corner gives a positive tempco at the same code. The brief's limit is at tt
  only, and under the new room-temperature policy this spread matters only as drift around 27 °C.

## Job 2: full tuning map of the winner
**Method.** For w = 1.2 and lnw = 5.023:
- **Grid:** codes 0–31 × vctrl 0/1.65/3.3 × 5 corners × 0/27/70 °C × VDD 3.15/3.3/3.45, 4320 points. The 3.3 V points
  are the ones from Job 1's check of this w.
- **Per PVT point:**
  - fmin and fmax;
  - the nearest-433.92 code at vctrl 1.65;
  - every code whose fine range (vctrl 0–3.3) covers 433.92;
  - the worst fine/step;
  - monotonicity in code (at each vctrl) and in vctrl (at each code);
  - the vg range and the a0 swing (min/max over 100–200 ns), over all points and at the 433.92 code.

All 45 rows are in `sim/results/2026-11-08/cfed/summary.md`. Here are the extremes and the VDD 3.3 V points.

| corner T (VDD 3.3) | fmin | fmax | 433.92 code (f MHz) | codes covering 433.92 | worst fine/step | vg range V | a0 swing range V | vg, swing at the 433.92 code | P mW |
|---|---|---|---|---|---|---|---|---|---|
| tt 0 | 199.8 | 854.2 | 9 (430.1) | 6–9 | 4.23 | 1.50–2.12 | 1.41–3.43 | 1.91, 1.82–3.43 | 0.435 |
| tt 27 | 205.4 | 846.5 | 9 (434.1) | 6–9 | 3.58 | 1.46–2.12 | 1.38–3.42 | 1.89, 1.81–3.42 | 0.451 |
| tt 70 | 208.3 | 821.1 | 9 (430.7) | 7–9 | 2.92 | 1.43–2.13 | 1.36–3.42 | 1.89, 1.81–3.42 | 0.461 |
| ss 0 | 185.0 | 776.4 | 11 (430.0) | 8–11 | 3.33 | 1.29–1.98 | 1.19–3.44 | 1.70, 1.60–3.44 | 0.483 |
| ss 70 | 193.3 | 750.9 | 11 (431.4) | 9–11 | 2.25 | 1.21–1.99 | 1.12–3.43 | 1.66, 1.57–3.43 | 0.515 |
| ff 0 | 218.1 | 946.1 | 7 (430.9) | 3–8 | 5.25 | 1.69–2.26 | 1.62–3.41 | 2.10, 2.03–3.41 | 0.393 |
| ff 70 | 227.2 | 903.3 | 7 (429.9) | 4–8 | 3.70 | 1.64–2.28 | 1.58–3.40 | 2.09, 2.03–3.40 | 0.412 |
| sf 0 | 196.5 | 860.0 | 9 (428.6) | 6–9 | 3.74 | 1.47–2.07 | 1.39–3.43 | 1.87, 1.80–3.43 | 0.451 |
| sf 70 | 205.6 | 829.5 | 9 (431.5) | 7–9 | 2.58 | 1.40–2.08 | 1.33–3.42 | 1.85, 1.78–3.42 | 0.478 |
| fs 0 | 197.0 | 840.0 | 10 (443.2) | 6–10 | 4.74 | 1.50–2.14 | 1.41–3.42 | 1.89, 1.80–3.42 | 0.434 |
| fs 70 | 206.0 | 806.1 | 10 (442.6) | 7–10 | 3.29 | 1.45–2.15 | 1.37–3.41 | 1.88, 1.79–3.41 | 0.458 |

**Over all 45 PVT points:**
- **Range:** the worst fmin is 228.3 MHz (ff 70 °C 3.15 V) and the worst fmax is 749.9 MHz (ss 70 °C 3.15 V).
- **Tuning:** the worst fine/step is 2.08 (ss 70 °C 3.15 V, code 30). It is monotonic in code and vctrl at every
  point, with 0 non-oscillating points.
- **433.92 codes:** they run from 7 (ff) to 11 (ss), and 3–6 codes cover 433.92 at every point.
- **VDD:** f moves less than 0.5 % over 3.15–3.45 V. vg and the swing floor track VDD one-to-one, about +0.14 V per
  +0.15 V.

**Level-shifter numbers:**
- vg spans 1.07–2.42 V over all codes and PVT; at the 433.92 code it is 1.52–2.24 V.
- The a0 minimum at a PVT point is 0.99–1.76 V over all codes (1.43–2.18 V at the 433.92 code). The high level overshoots VDD by
  0.10–0.15 V.
- So the ring output swings from roughly vg to VDD, a 1.2–2.3 V swing. The level shifter has to switch with an input
  low level as high as 2.2 V (ff, 3.45 V).

**Conclusion.** The winner meets the range with a margin of +50 MHz at the top and −82 MHz at the bottom, over the
full PVT and VDD set. Tuning is monotonic everywhere, and fine/step stays at 2.1 or more. The level shifter is the
open interface item, because the low level sits high at about vg.

## Job 3: noise over PVT
**Method.**
- **Where:** at each corner × 0/27/70 °C, at that point's 433.92 code (from the Job 2 map, VDD 3.3, vctrl 1.65).
- **`cfed_noise.py ki`:** gives I_DAC, vg, f and K_I = df/dI (±1 % of I injected into vg).
- **`cfed_noise.py dacn`:** gives the DAC output-current noise S_I with vg held, from a dense `.noise` over 1 k–100 MHz.
  - "DAC" is the DAC devices alone, with their gates on noiseless sources.
  - "ref" is the total minus the DAC, so it covers the reference, vbn, the RC filter and the gate switches.
  - "vdd" is 160 nV/√Hz through K_vdd.
- **rms FM** is √∫K_I²·S_I df over 1–10 kHz and 1–100 kHz.
- **ISF:** run at tt 27 °C only, with m = 80 phases (finer than the 40 asked for, since there was time).

| corner T | code | f MHz | I_DAC µA | vg V | K_I MHz/µA | FM 1–10 kHz: total (ref / DAC / vdd), kHz | FM 1–100 kHz: total (ref / DAC / vdd), kHz | L(100k) dBc/Hz |
|---|---|---|---|---|---|---|---|---|
| tt 0 | 9 | 429.6 | 64.6 | 1.91 | 5.05 | 8.08 (6.76 / 4.42 / 0.09) | 10.52 (7.92 / 6.92 / 0.30) | −80.0 |
| tt 27 | 9 | 433.5 | 66.5 | 1.89 | 4.87 | 7.87 (6.66 / 4.19 / 0.10) | 10.27 (7.87 / 6.59 / 0.32) | −80.2 |
| tt 70 | 9 | 429.7 | 67.3 | 1.89 | 4.68 | 7.52 (6.46 / 3.85 / 0.11) | 9.89 (7.77 / 6.10 / 0.36) | −80.6 |
| ss 0 | 11 | 429.5 | 76.0 | 1.70 | 4.24 | 7.90 (6.74 / 4.13 / 0.08) | 10.14 (7.84 / 6.42 / 0.25) | −80.7 |
| ss 27 | 11 | 434.1 | 78.5 | 1.68 | 4.07 | 7.68 (6.61 / 3.91 / 0.08) | 9.89 (7.77 / 6.11 / 0.27) | −81.0 |
| ss 70 | 11 | 430.6 | 79.9 | 1.66 | 3.89 | 7.33 (6.40 / 3.58 / 0.09) | 9.50 (7.64 / 5.63 / 0.30) | −81.4 |
| ff 0 | 7 | 430.4 | 54.6 | 2.10 | 6.05 | 8.18 (6.71 / 4.68 / 0.11) | 10.81 (7.88 / 7.39 / 0.35) | −79.4 |
| ff 27 | 7 | 433.4 | 55.8 | 2.09 | 5.86 | 7.98 (6.62 / 4.46 / 0.11) | 10.58 (7.86 / 7.06 / 0.38) | −79.6 |
| ff 70 | 7 | 428.9 | 56.1 | 2.09 | 5.66 | 7.67 (6.48 / 4.11 / 0.13) | 10.22 (7.82 / 6.57 / 0.42) | −80.0 |
| sf 0 | 9 | 428.3 | 66.3 | 1.87 | 5.01 | **8.26** (6.92 / 4.51 / 0.13) | 10.73 (8.09 / 7.04 / 0.43) | −79.9 |
| sf 27 | 9 | 433.4 | 68.5 | 1.86 | 4.83 | 8.05 (6.81 / 4.29 / 0.14) | 10.48 (8.04 / 6.71 / 0.45) | −80.1 |
| sf 70 | 9 | 430.8 | 69.5 | 1.85 | 4.63 | 7.70 (6.61 / 3.94 / 0.14) | 10.08 (7.93 / 6.21 / 0.47) | −80.6 |
| fs 0 | 10 | 442.7 | 67.0 | 1.89 | 4.95 | 8.11 (6.86 / 4.33 / 0.03) | 10.54 (8.04 / 6.81 / 0.10) | −80.0 |
| fs 27 | 9 | 426.4 | 64.7 | 1.90 | 4.89 | 7.65 (6.48 / 4.07 / 0.04) | 10.02 (7.68 / 6.43 / 0.14) | −80.4 |
| fs 70 | 10 | 441.6 | 69.4 | 1.88 | 4.60 | 7.58 (6.57 / 3.77 / 0.06) | 9.94 (7.92 / 6.01 / 0.19) | −80.7 |

**ISF at tt 27 °C** (code 9, m = 80, f0 434.1 MHz):
- **Inverter noise, crossings at mid-swing (switching bias):** 0.23 kHz over 1–10 kHz and 0.57 kHz over 1–100 kHz,
  with L = −77.0 / −98.5 / −118.7 / −138.7 dBc/Hz at 10k / 100k / 1M / 10M.
  - This is the same method as `docs/cfed_results.md` (0.5 / 1.3 kHz at M = 20).
  - The finer phase grid gives about half that.
- **"Fully on" bias row:** 66.6 / 97.1 kHz. It is the script's deliberately pessimistic bound, with each device's
  1/f noise at full gate drive applied over the whole cycle. It is not the estimate.

**Conclusion.**
- **Worst case:** 8.26 kHz rms over 1–10 kHz (sf 0 °C), against the 15 kHz limit, which leaves 45 % margin. The spread
  over PVT is small: 7.3–8.3 kHz over 1–10 kHz and 9.5–10.8 kHz over 1–100 kHz.
- **Split:** the reference/vbn path dominates (6.4–6.9 kHz), ahead of the DAC devices (3.6–4.7 kHz). VDD and the
  inverters are negligible.
- **Against the w = 1.0 study** (8.9 / 11.7 kHz at tt in `cfed_results.md`), the wider DAC costs nothing. The DAC
  term even drops a little, because the 433.92 code is lower (9 instead of 14).

## Run times (from `build/cfed_sizing/status.txt` and the logs)

| step | start | end | time |
|---|---|---|---|
| 1. Job 1: null search (5 w, 4 iterations, 468 decks) | 11:35:21 | ≈ 11:53 | 18 min |
| 1. Job 1: check (300 decks, 7200 points) + pick | ≈ 11:53 | 12:27:29 | 34 min |
| 2. Job 2: map (VDD 3.15/3.45, 2880 new points) | 12:27:29 | 12:41:34 | 14 min |
| 3. Job 3: ki + dacn at 15 points, ISF m = 80 | 12:41:34 | 12:46:22 | 4.8 min |
| 4. summary | 12:46:22 | 12:46:24 | 2 s |
| **driver total** | 11:35:21 | 12:46:24 | **71 min** (estimate 101 min) |

Setup and pre-flight checks took 11:28 to 11:35. They were a real null search for w = 1.0, a synthetic dry run of
every analysis step, a real ki/dacn run at ss 70 °C, and the failure test.

## Script fixes
- **`cfed_noise.py`:**
  - `ki` and `dacn` take `--corner` and `--temp`. They were hard-wired to tt 27 °C; the defaults are unchanged.
  - Their single-deck runs now use one-thread ngspice (`jobs=2` path), so 5 points in parallel stay within the CPU
    budget.
  - The ki.json and dacn.json files record the corner, the temperature and the code.
- **New:** `cfed_sizing.py` (steps) and `cfed_sizing_run.sh` (driver).
- **Bugs during the run:** none. The pre-flight dry run caught one problem, a missing output directory, and it was in
  the test harness, not the script.

## Autonomy test (rules from `docs/handoff_autonomy.md`)

| rule | worked? | notes |
|---|---|---|
| One driver, tracked launch | yes | `cfed_sizing_run.sh` was started once with the Bash tool's `run_in_background`; no nohup or Monitor was needed. |
| Step chain, results read from files | yes | Jobs 2 and 3 read w and lnw from `job1/winner.json`, and Job 3 read its codes from `job2/map_summary.json`. There were no gaps between steps. |
| Status file and output checks | yes | Every step wrote `status.txt`. Each deck is checked for its row count and for "singular", "Transient op started" and "timestep too small"; none tripped. |
| Fail loudly | yes, by test | A deliberate failure run before the launch (`CFS_FAILTEST=1`: step 1 reads a missing check.json) wrote `FAILED` with the traceback, logged "step 1/4 FAILED", stopped with exit 1, and ran no further steps. |
| Heartbeat | partly | ScheduleWakeup works, but it caps a delay at 60 min, below the 1.5 × 100 min asked for. It was armed for 12:35, fired on time, and was re-armed for 13:21. |
| Status pushes | yes | The driver committed and pushed the Running line at every step change: 11:35, 12:27, 12:41, 12:46 and the sims-done line. All reached GitHub, interleaved with 4 laptop commits, using `pull --rebase --autostash`, with no push failures. |
| Wake on finish | yes | The driver exited at 12:46:24, and the task notification woke the session at 12:46:29, with no human ping. |
| Finish in one go | yes | The write-up, commit and push followed directly. The time from the last sim ending (12:46:22) to the results push is in the commit message of the Done line. |
| CPU budget | yes | At most 20 one-thread ngspice processes at a time, via `--jobs 20`, and 5 × 4 for Job 3. The null search averaged about 17 CPUs. |

**What to change:**
1. The heartbeat rule should say "60 min, re-armed", since 60 min is the ScheduleWakeup maximum.
2. The ETA in the Running line is the whole-run ETA. It came from step estimates that were 30 % pessimistic.
3. The corner policy changed mid-run. The driver can't pick that up; the next handoff's driver should take its corner
   lists from the handoff.
