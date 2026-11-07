# xschem + ngspice (sky130) learnings

Tools: IIC-OSIC-TOOLS `hpretl/iic-osic-tools:2026.05` (ngspice 46/47, xschem 3.4.x), sky130A, run
headless in Docker. Pin the image tag: `:latest` can resolve to an old cached image, and
ngspice-44.2 (`2025.07`) raises a bogus `Pclm ... is not positive` fatal error.

## Setup and speed
- **`.spiceinit` is read only from ngspice's current directory.** Keep one tracked copy and have the
  wrapper copy it into `build/` on every run:
  ```
  set skywaterpdk
  set ng_nomodcheck
  set num_threads=8
  option noinit
  ```
- `option klu` breaks `.noise`. Put it only in big transient-only decks.
- Never `set ngbehavior=hsa`. It changes the scale factor and binned HV FETs (the TT pad model)
  fail with "could not find a valid modelname".
- Loading the model library is a fixed cost (15–25 s, ~2 min elsewhere). Sweep inside one process:
  `foreach w 10 20 40 / alterparam w_dp = $w / reset / ... / destroy all / end`. `alterparam` needs
  `reset`, and `destroy all` stops plots piling up.
- **Thread budget:** each ngspice starts `num_threads` OpenMP threads. 6 × 8 threads on 8 cores gave a
  load average of 48 and nothing finished. Keep the total threads ≤ the *cgroup quota*
  (`/sys/fs/cgroup/cpu.max`), not `nproc`: over-subscribing a pod cut throughput ~10×. On the Mac
  (Docker 10 CPU / 8 GB) up to 6 jobs ran fine.
- `.save` only what you measure in long transients (it applies to `op` too). "Memory required ... is
  more than available" refers to *free* RAM, not the page cache.
- Floating nodes (no DC path; gates and caps don't count) made op re-solve at every sweep point
  (123 s vs 25 s).
- Avoid extreme resistor ratios: 1e-12/1e12 Ω hung for 50+ min, while 1/1e9 Ω ran in seconds. ngspice
  silently swaps 0 Ω for 1e-12.
- Time a short probe and extrapolate, but the probe must cover the hardest regime. A probe taken before the
  circuit started switching hard underestimated the runtime 5–10×.
- Keep the machine awake (`systemd-inhibit`, `caffeinate -i`, `scripts/longrun`). `write` happens
  only at the end of a batch run, so split very long runs into pieces.
- **A failed `op` silently becomes a "transient op"**: unsettled slow nodes, charging currents in the
  supply, no error. Grep for `Transient op started` / `singular matrix`. In extracted netlists the
  usual cause is nets with only parasitic C (unconnected stubs): tie them down through 1 GΩ.
- "timestep too small" at the very end: check how many points were written before you throw the run
  away.

## Watching and killing runs
- Progress: `tr '\r' '\n' < run.log | grep Reference | tail -1`. No line yet means it's still loading
  models.
- `pkill -f pattern` can kill the shell running it, so kill by PID. A Docker container outlives
  its killed wrapper (`docker ps`, `docker kill`).
- **Don't edit a shell script while it's running.** Bash resumes at the old byte offset in the new
  file, and here that re-launched a whole Docker job.
- Parallel runs that write a fixed netlist name race each other. Use per-run names, staggered starts,
  or a lock (`sched.py` has both).
- ngspice 47 exits 1 after a d_cosim run even when it completed. Judge by the raw file and the log.

## xschem
- Headless netlist: `xschem -n -s -q -o build tb.sch`. **Grep the netlist for `IS MISSING`**, since
  the exit code doesn't say. For LVS add `--tcl "set top_subckt 1; set lvs_netlist 1"`; without
  `lvs_netlist 1` the `.subckt` line is commented out.
- Property values can't contain `{}`. Use `'expr'`. A `"` inside a code block truncates it (the sign is
  "Missing .endc").
- Subckt params: symbol `format="@name @pinlist @symname w=@w"`, `template="name=x1 w=20"`; use `'w'`
  inside. Default mismatch params such as `mm` to 0 so top-level netlists don't depend on testbench
  globals.
- No dots in top-level net names (they clash with `x1.node`). Instance `M1` becomes `XM1`.
- Corners: keep schematics at tt and rewrite the `.lib ... tt` line in the generated netlist.
  **Passive corners (hh/ll/…) are separate lib sections**: MOS corners keep R/C typical.
- Std cells in a schematic: the hd spice include goes in a tcleval code block, and supplies are
  instance properties.
- Generate schematics from Python (`scripts/xsch.py`): place symbols, put `lab_pin`s exactly on the pin
  coordinates, netlist to check. Repeatable, diffable, sweepable.

## sky130 device modelling traps
- `W` is the total width over `nf`. **Write folded devices as W-per-finger × `mult`**, the way magic
  extracts them. W-total + nf bins differently under `set skywaterpdk` (~8 % current), and extracted
  stages then show fake +0.5–1 dB "gain".
- Each finger W is its own model bin: 4.55 µm fingers carry ~12 % more current per µm than 2 µm ones.
  Don't mirror across different finger widths.
- Passive models carry no parasitic C (poly-to-sub, MIM bottom plate) until extraction. Orient MIM
  bottom plates on purpose.
- high_po resistors: each segment has its own head resistance (0p69: R = 526 Ω + 470.9 Ω/µm·L). One
  10 kΩ device drawn as 2 segments came out 5 % high. Model the segments in the schematic.
- BSIM is quasi-static, so MOS-decap channel R isn't modelled. Estimate it by hand.
- nfet_01v8 flicker noise is still significant at hundreds of MHz in the models; pfet shows almost
  none. A wider NMOS pair still beat PMOS on noise figure at high frequency.
- Calibrate schematic wiring-C estimates from the first extraction (3.2 fF/stage here, not the
  guessed 10).

## Control-language traps
- `print -i(v1) v(a)` merges into one expression. Use `let x = -i(v1)`.
- Vectors belong to a plot and vanish after the next analysis. `meas` results too, and `destroy all`
  deletes them. Copy values out first: `set o0 = "$&off0"`. `$&` takes a vector name only.
- `option temp = 60` *after* `reset`. `set temp` is ignored.
- `meas ... rise=N` counts from the first saved point.
- `write x_$v.raw` reads a variable called `v.raw`. Use `{$v}` in plain decks, or unroll the cases in a
  generated block (braces break xschem).
- `if $var = string` doesn't work.
- Join echo lines with `echo "$a" NOEOL` + `sed -z "s/ NOEOL\n/ /g"`.
- Switch AC sources inside one run: `alter @vin[acmag]=0`, `alter @vcm[acmag]=1`.
- `trnoise` with clocked sources gives "timestep too small" when edges land on the noise grid. Offset
  every edge by NT/2. Use `tanh(k*x)` rather than a hard ternary in B-sources.
- `.options interp` with `tran tstep ... tmax` saves only on the tstep grid: 400 µs gave a 2 MB raw
  file.
- Subckt sources in extracted decks are named `v.<inst>.<name>`. Element names are
  case-insensitive (VD vs Vd collide).
- Measure edges at 20–80 % of the *actual* swing, not of the rail.

## Noise recipes
- Decision noise = `onoise_total` / DC gain. `inoise_total` integrates over the whole sweep, blows up
  above the pole, and makes band-limiting look like it adds noise.
- After `noise ... dec ...` the current plot holds the totals and `setplot previous` is the spectrum.
  A single-point `lin 1 f f` makes no integrated plot.
- NF = 10·log10(onoise² / (|G|²·4kT·Rs)), with G from source EMF to output and T = 300.15 K.
- Per-device contributions: `noise v(out) vsrc lin 1 f f 1`, then `print all`. Don't sum a MOSFET's
  total with its sub-terms.
- Repeatable transient noise: generate it in numpy (per-sample σ = d/√(2T)) and feed it through an
  XSPICE `filesource` plus E sources. Cap `tmax` at the sample spacing.

## Monte Carlo
- `.lib sky130.lib.spice tt_mm` (also `ss_mm`, …) turns on per-device AGAUSS for Vt, R and MIM C,
  scaled 1/√(W·L·m). Each `reset` redraws.
- **Seeds:** without a seed every process repeats the same sequence ("200" samples were 8 × 25 copies).
  `set rndseed` and `option seed` in .control are ignored. `.options seed=N` works, but every reset
  re-seeds to N. So run one sample per process, each with its own seed, and check for duplicates.
- Attribute variance by zeroing one device type at a time:
  `.param sw_mm_vth0_sky130_fd_pr__pfet_01v8_lvt=0`. A_Vt (mV·µm): nfet 3.4, nfet_lvt 5.5, pfet 5.9,
  **pfet_lvt 10.9** (65 % of one comparator's offset came from a pfet_lvt mirror; 4× its area fixed
  it).
- Compute per-chip metrics at each chip's own operating point, not the nominal transfer applied to
  every sample.
- 200 comparator samples took about 40 s on 24 threads.

## Python side
- `scripts/rawread.py` reads ngspice raw files (binary or ascii, real or complex). Plot in the host
  venv, not in the container.
- NumPy 2: `np.trapz` is gone, use `np.trapezoid`.
