# Handoff: quiet const-gm reference, phase noise at PVT, tuning map (sim pod, overnight)

**Goal: find the smallest constant-gm reference whose flicker noise no longer dominates the ring's frequency noise,
keeping it temperature-compensated. Then measure phase noise and the full tuning map of the ring with that
reference, and commit the results to `docs/bias_tuning_results.md` and `sim/results/2026-11-08/`.**

A second agent may be doing the ring layout (`docs/handoff_ring_layout.md`) in the same repo at the same time.
Commit only your own files, use `git pull --rebase` before pushing, and use at most **20 CPUs** (`PAR × JOBS ≤ 20`).

## Decision so far (Gate 1, partial, 2026-11-07)
- **Topology: one single-ended, current-starved ring, N = 5.** This is the "cgm" structure in `sim/vco/vco_bias.py`:
  binary-weighted coarse foot legs, a small fine leg on vctrl, and a head that tracks the foot through the master leg.
  The differential variant is dropped: it has the same figure of merit for 2.3× the power.
- **The bias is not settled.** At tt the reference's flicker noise sets the rms frequency modulation (FM) at
  about 117 kHz in 1–10 kHz, even with a 1 MΩ / 20 pF RC filter. Without the bias noise, the ring's own devices give
  about 11 kHz. See `docs/pn_results.md`, "Follow-up 1".

## Read first
- This file.
- `docs/pn_results.md`: the method, results and the two follow-up sections.
- The docstrings of `sim/vco/vco_bias.py` and `sim/pn/isf.py`.

## Host and tools
- You are in the IIC-OSIC-TOOLS pod. `tools/osic-mac` runs tools directly there. Don't edit it.
- Clone over HTTPS: `git clone https://github.com/mattvenn/gf-433-oscillator.git` into `/foss/designs`.
  The `GITHUB_TOKEN` credential helper is set up by Matt. If a push fails on authentication, stop and say so;
  don't try other credentials.
- Start every new scripted run with a single short case, and check its log before launching the batch.

## Job 1: reference size sweep (about 1–2 h)
The reference's flicker noise density scales roughly as 1/√(W·L). So scaling the W and L of MN1, MN2 (×kb) and
MP1/MP2 by s (W/L constant) should cut it by about s, for the same current. About 10× less is needed.

1. Add a `--set`-style override to `isf.py` (for example `--set w1=20 --set l1=10`) so that a variant can take
   extra parameters. Variants without `--set` must give exactly the same results as now. Check with
   `isf.py cgm --m 8` against the stored `cgm_typical_t27/result.json` A-stage numbers.
2. Write `sim/pn/bias_fm.py`. Given a reference sizing, it should:
   - run the `.noise` of the filtered gate node (as `isf.bias_noise_deck`, rf = 1 MΩ, cf = 20 pF), and of vbp;
   - combine them with the stored cgm device and vdd terms (`sim/pn/results/2026-11-07/cgm_typical_t27/result.json`),
     K_vbn from a quick stage-A run of the new sizing, and K_vbp = +282 MHz/V (or measure it);
   - integrate the frequency noise S_f = 2·f²·10^(L/10) over 1–10 kHz and 1–100 kHz. Use the **dense** `.noise`
     spectrum for the bias terms, not the 4-decade interpolation (it fails for the filtered term);
   - report rms FM (kHz) and L at 10k / 100k / 1M.
3. Sweep s ∈ {1, 2, 4, 7, 10, 14}.
   - For each s, retune the n-well length `lnw` (with `lnp = 100`) to null the temperature coefficient at tt
     (`vco_bias.py tc`, 0 / 27 / 70 °C). Start from `lnw = 4.5`.
   - For each s, record:
     - rms FM 1–10k and 1–100k;
     - the tempco at tt, and the corner spread from `vco_bias.py pvt` (5 corners × 0/27/70 °C × VDD ±4.5 %);
     - the reference current;
     - the device area of the reference (Σ W·L × m), plus the resistor and the 20 pF capacitor (about 68 × 68 µm);
     - whether it starts up: a VDD ramp from 0 to 3.3 V in 10 µs, at ss and ff, 0 and 70 °C, must reach the
       normal vbn.
4. **Pick the winner:** the smallest s with rms FM (1–10 kHz) ≤ 15 kHz at tt, |tempco| ≤ 150 ppm/°C at tt, and
   start-up OK at every corner checked. If none qualifies, report the trend and pick the best. Note in the results
   whether a lower K_vbn (more of the current from fixed legs) looks like the better route.

## Job 2: phase noise of the winner over PVT (about 40 min)
Add a variant `cgmq` to `isf.py` (cgmf plus the winning sizing). Run `isf.py cgmq --m 60` for the 5 corners ×
0 / 27 / 70 °C (15 cases), in the same way as `run_all.sh` (which can take a variant list). Then tabulate:
- L at 10k / 100k / 1M / 10M;
- rms FM 1–10k and 1–100k, with the bias terms integrated as in Job 1;
- which term dominates.

## Job 3: tuning map of the winner (about 30 min)
Add a `map` mode to `vco_bias.py`: f for every code 0..31 × vctrl ∈ {0, 1.65, 3.3} V, at 5 corners × 0 / 27 / 70 °C
× VDD 3.15 / 3.3 / 3.45 V. The filter doesn't affect DC, so it can be off. Report per PVT point:
- the f range (code 0 at vctrl 0, to code 31 at vctrl 3.3);
- the code needed for 433.92 MHz;
- the largest coarse step against the fine range (the requirement is fine ≥ 1.3 × the largest step, so every
  frequency can be reached);
- any non-monotonic code steps.

**Coverage target:** with no GF silicon factor yet, the coarse range must reach 433.92 MHz for a silicon factor
anywhere in ×0.7 … ×1.4. That means simulated frequencies from 310 to 620 MHz must be inside the range at every
PVT point. State plainly whether that is met. If it is not, state how many coarse bits or how much range is missing,
but don't redesign.

## Results doc and commit
`docs/bias_tuning_results.md` contains:
- the date, image tag and ngspice version;
- per job: the method in one paragraph, the table, and 2–4 plain sentences of conclusion;
- the actual run times from timestamps;
- any fixes made to the scripts.

Copy small result files (json/csv/txt) into `sim/results/2026-11-08/`. Commit the scripts you added or changed.
Stage and commit in one command, never `git add -A`, and don't commit `build/` or `sim.yaml`. Then
`git pull --rebase` and `git push`.

## Don't
- Don't change the ring core sizes (wn, wp, whead, wfu, k, bits, ls, wff, lff). The layout agent is drawing them.
- Don't edit the datasheet.

## Done
When pushed, add a line at the top of this file: `> Done (date): results in docs/bias_tuning_results.md`.
