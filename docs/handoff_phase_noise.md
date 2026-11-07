# Handoff: phase-noise sweep of the candidate VCOs (sim pod)

**Goal: run the ISF phase-noise sweep (`sim/pn/run_all.sh`) for the 3 VCO variants × 5 process corners,
check the results are physical, and commit them to `docs/pn_results.md` and `sim/pn/results/2026-11-07/`.**

## Read first
- This file (it is your whole brief).
- `sim/pn/isf.py` docstring: the method (impulse sensitivity function, Hajimiri & Lee 1998) and what
  each stage does. Don't read the rest of the repo unless something breaks.
- `docs/vco_study.md` §3 only if you need to know what the variants are.

## Host and tools
- You are in the IIC-OSIC-TOOLS pod (28 CPUs, 64 GB, no Docker). `tools/osic-mac` detects this and
  calls `tools/osic-inimage`, which runs commands directly with `PDK=gf180mcuD`. Don't edit them.
- The pod image is `iic-osic-tools:2026.09`. The design work used `2026.05`. Step 2 checks that they
  agree.
- `/foss/designs` is an emptyDir: clone the repo there, and push before the pod goes away.
- Don't run more ngspice processes than CPUs: `PAR × JOBS ≤ 28`.

## Steps
1. `cd /foss/designs && git clone git@github.com:mattvenn/gf-433-oscillator.git && cd gf-433-oscillator`
   (or `git pull` if it is already there). Set the git identity if needed: Matt Venn.
2. **Tool-version check** (about 1 min):
   ```
   tools/osic-mac ngspice -v | head -2
   tools/osic-mac bash -c 'ls $PDK_ROOT/gf180mcuD/libs.tech/ngspice'
   python3 sim/vco/ring_basic.py --quick
   ```
   Expect `typical_n5_t27_v330` ≈ **1949.9 MHz** and `typical_n9_t27_v330` ≈ **1082.3 MHz** (2.46 mW).
   Pass: within 0.5 %. If not, record both numbers and the ngspice version in the results doc, and carry
   on. The comparison is still valid within one tool version.
3. **Smoke test** (about 10 min): `python3 sim/pn/isf.py se --m 8 --jobs 8 --out build/pn_smoke`
   - Stage A line: f0 should be about 430–440 MHz (it is set up for 433.92 at tt), P about 0.9 mW,
     K_vdd about −1300 MHz/V, K_vctrl large and positive (about +800 MHz/V).
   - The ISF in `build/pn_smoke/se_typical_t27/isf.csv` (`g_rad_per_C`) should be small near the rails
     and peak near the node's edges, with both signs present.
   - L(1 MHz) in the range −80 … −120 dBc/Hz.
   - If a stage fails, read the `.log` next to its `.cir`. Common causes: an ngspice syntax difference in
     `alter @iinj[pulse] [...]`, a `meas` failing because an edge falls outside the window, or
     `wrdata` naming. Fix `sim/pn/isf.py` minimally, rerun the smoke test, and describe the fix in the
     commit message.
4. **Full sweep** (estimate 2–4 h; record the actual time from timestamps):
   ```
   nohup env M=60 PAR=7 JOBS=4 sim/pn/run_all.sh > build/pn_run.log 2>&1 &
   ```
   Progress: `grep -c done build/pn_run.log` (15 cases in total); one case's log is `build/pn/<v>_<c>.out`.
   Don't edit scripts while it runs.
5. **Check** (step 6 lists what to report):
   - all 15 `build/pn/*/result.json` exist; for any missing case, quote the tail of its `.out`;
   - ISF sanity: per case, `isf.csv` is smooth (no single-phase spikes over 10× its neighbours);
   - FOM at 1 MHz in the range −145 … −170 dBc/Hz for ring oscillators. Flag anything outside it;
   - `diff` should have |ISF dc| / sqrt(ISF rms²) smaller than `se`. Report the ratio per variant at tt.
6. **Write `docs/pn_results.md`**:
   - the date, image tag and ngspice version;
   - the step-2 numbers;
   - the table from `python3 sim/pn/summary.py build/pn`;
   - the ISF dc/rms ratios;
   - the actual run time;
   - any fixes made;
   - 3–5 plain sentences: which variant has the lowest phase noise at 10 kHz, 100 kHz and 1 MHz at tt, and
     what dominates (device head/foot, bias, vdd). Note that the vdd term uses an assumed 100 nV/√Hz supply,
     and the se/diff bias term an assumed 100 kΩ vctrl resistor.
7. **Commit**:
   - `docs/pn_results.md`;
   - a copy of every `build/pn/*/result.json` and `isf.csv` into `sim/pn/results/2026-11-07/<case>/` (small text files);
   - `build/pn/summary.md` as `sim/pn/results/2026-11-07/summary.md`;
   - any fix to `sim/pn/isf.py`.

   Stage and commit in one command, with no `git add -A`. Then `git pull --rebase` and `git push`.

## Don't
- Don't change `sim/vco/*.py` or the datasheet, and don't redesign circuits. Measure and report only.
- Don't commit `build/` or raw logs.
- Don't commit `sim.yaml` (it holds the VNC password).

## Done
When pushed, add a line at the top of this file: `> Done (date): results in docs/pn_results.md`.
