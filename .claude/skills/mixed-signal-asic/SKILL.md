---
name: mixed-signal-asic
description: Hard-won flow, rules and scripts for designing an open-source analog / mixed-signal ASIC on sky130 (Tiny Tapeout analog tiles in particular) with xschem, ngspice, KLayout-Python layout generators, magic/netgen DRC-LVS-PEX, LibreLane digital macros, cocotb and formal. Use when starting or working on any analog or mixed-signal chip project: planning, schematic and testbench writing, layout, floorplan, power grid, extraction, Monte Carlo/corner/supply verification, TT precheck/submission, bring-up, or coordinating several Claude sessions on one chip.
---

# Analog / mixed-signal ASIC on sky130 / Tiny Tapeout

Lessons from taking a full mixed-signal design from idea to TT submission in ~10 days: high-gain
amplifiers, a comparator with a trim DAC loop, bias generation, switched-cap circuits, output
drivers on 3.3 V, decaps, and a hardened digital macro, all on one TT 3x2 analog tile. Several
Claude sessions worked on it across a laptop, a cloud pod and a big Linux box. Every rule here cost
time at least once.

Read the reference that matches the work in hand. Don't load them all:

| Working on | Read |
|---|---|
| testbenches, ngspice, xschem, noise, MC | [references/ngspice-xschem.md](references/ngspice-xschem.md) |
| block layout, pcells, DRC, LVS, PEX, antenna, EM | [references/layout-sky130.md](references/layout-sky130.md) |
| floorplan, top-level router, power grid, IR/EM, decap | [references/floorplan-power.md](references/floorplan-power.md) |
| verification plan, corners, MC, system sims, run times | [references/verification.md](references/verification.md) |
| digital macro, cocotb, formal, TT tile rules, CI, pinout | [references/digital-tt.md](references/digital-tt.md) |
| several sessions or machines, handoffs, docs, estimates | [references/workflow.md](references/workflow.md) |
| bring-up plan, design for test, silicon vs sim | [references/bringup.md](references/bringup.md) |
| background: Harald Pretl's IIC-JKU courses (analog design and etiquette, complex-IC layout, RF ICs) | [references/further-reading.md](references/further-reading.md) |

Reusable scripts are in [scripts/](scripts/README.md). Copy them into the new repo and adapt the paths.

## The flow that worked

```
bench data from earlier silicon ─► system model (Python, e2e statistics)
        │                                   │ budgets per block (noise, gain, offset, BW)
        ▼                                   ▼
bit-exact digital model ─vectors─► RTL (cocotb) ─► harden ─► GL      schematic per block (generated)
                                                                       │
                     floorplan with real block sizes ◄── block layout (generator) ─► DRC/LVS/antenna/PEX
                                     │                                             └► tb_<block> sch vs pex
                     top-level route ─► tile DRC/LVS/precheck ─► tile PEX (lvs → c → rc)
                                     │
             mixed signal (Verilated RTL in ngspice) + system sims on the extracted tile
                                     │
                  supply / temp / corner / MC / power-up / overload / formal ─► findings table ─► tapeout
```

1. **Measure before modelling.** Bench data from a previous shuttle (oscillator frequencies, the
   real board supplies, pad behaviour) grounds the specs. Silicon ran at ×0.85 of the extracted-tt
   speed.
2. **Two models.** A bit-exact Python model of the digital (it exports vectors that RTL and GL
   must match sample for sample), and a behavioural end-to-end model with knobs (noise, gain,
   offset, trim step, bandwidth) that turns transistor results into system pass rates and sets each
   block's budget *before* it is designed.
3. **Everything is a generator.** Schematics (`xsch.py`), layouts (KLayout Python + PDK pcells),
   floorplan variants, the router, the tile and the pinout wrapper. Generators make sweeps, pin
   moves and rebuilds mechanical. Hand-drawn layout breaks the rework loop.
4. **Lay blocks out early**, so floorplanning uses real sizes. One long block set the shape of the
   whole tile.
5. **Floorplan the whole tile with every net as a flyline before moving any pins.** A flip
   (MYR90) often beats a re-route. Pins are "edge + order", not exact coordinates.
6. **Per block:** DRC 0 in *both* magic and KLayout, antenna 0, LVS match with *no property
   errors*, then PEX, and a `tb_<block>` run on the schematic and the extraction comparing what the
   block must do. One end-to-end run on the fully extracted tile at the end, not per block.
7. **Tile:** connectivity-only extraction first (cheap wiring check), then C, then RC.
8. **Verify broadly once the design is stable**, with a scripted job list and a CPU-budget
   scheduler (`sched.py`). A full rerun was ~270 jobs and ~410 thread-hours, ~14 h overnight on
   28 CPUs. Rerun all of it after any design change or tool-image upgrade, and diff every number.

## Rules that each cost real time

**Verification blind spots**
- Corners don't replace Monte Carlo for anything with an offset/trim loop. Nominal and PEX
  passed, and MC showed ~30 % of chips missing spec: the nominal point sat on the knee of the trim
  transfer. Put the operating point mid-range and check mean ± 4σ inside the trim range on *both*
  sides.
- Supply sweeps find level-shifter failures that corners don't (one rail −5 % with the other +10 %
  at ss/fs). Get the platform's real supply figures early: measured boards cleared failures that only
  happen at an assumed worst case.
- Simulate interacting blocks *extracted together* at least once. A level shifter and its driver
  lost 1.5 dB only as a pair. Block benches need the real source impedance as well as the real load.
- Block and tile extraction gave a high-gain path 3.6 dB apart with the same magic settings. Quote
  the tile number and keep the worse one as a bound.
- Measure at the operating point that matters (near the spec limit, at the real trim code), not
  where it is easy.
- "Works" doesn't prove the wiring. A reversed trim bus still converged. Use structural checks
  (every DAC step exactly ±1 LSB) and **mutation-test every checker**: a deliberate swap must fail it.
  That applies to LVS, the pinout check, formal properties and antenna checks alike.
- LVS can pass while device sizes are wrong. netgen prints "Circuits match uniquely" *and*
  "Property errors were found". Fail on property errors. Also make sure the LVS source is the real
  schematic and not the generator's own parameter copy (that was a circular check).
- An impossible PEX result (a DC shift that capacitors can't cause) is usually a failed operating
  point: ngspice silently fell back to a "transient op". Grep for `Transient op started`, and tie
  floating pin stubs to ground through 1 GΩ.
- Debug the analysis script before the circuit. An apparent signal loss was a plotting-window bug.
- Don't quote results at the edge. An ngspice version bump alone flipped a marginal pass to a fail.
  Quote one step back, and use several noise seeds at the edge (≥ 4/5 pass).

**Tools** (details in the references)
- Pin the tools image tag and the magic version. magic 8.3.684 silently dropped node-to-substrate
  C, so every extraction looked better than it was (we pinned 8.3.642). Record the tool version
  with each extraction and re-extract the *old* GDS before calling a difference a regression.
- MC samples repeat across ngspice processes unless each has its own `.options seed`. Run one sample
  per process and check for duplicate rows.
- `trnoise` can't be made repeatable. Make noise in numpy and feed it in through an XSPICE
  filesource.
- magic `antennacheck` reports nothing unless it runs on a flattened copy in a fresh session with
  `debug`. Prove it with a deliberate violation.
- magic `extresist` / FastHenry are unusable for supply nets. Build your own conductance mesh (see
  floorplan-power.md).
- Exit codes lie (cocotb `make`, tool wrappers that end in `grep`, ngspice after d_cosim). Judge runs
  by the output files and the log tail.

**Physical**
- Sensitive blocks were 27–67 Ω from their supply because current wound through *other blocks'
  rails*. Wider straps didn't help. The fix was a dedicated ground trunk per sensitive block.
- Size every via by cut count against the EM limits with 2× margin. Vias are the weak point. Feed
  high-current blocks at several points along their rail.
- Decap behind 10–20 Ω of mesh does nothing. Put it at the load.
- A high-gain differential amplifier is limited by asymmetric output→input coupling (≤ 0.1 fF for
  80 dB), not supply L. Mirror the geometry, add a guard-ring moat, and keep floating debug wires
  away from it.
- Keep debug pins off high-impedance nodes (nA of pad leakage × MΩ = mV). Tap a low-Z node through a
  debug-only transmission gate.
- Put noisy, high-current loads on their own supply and ground, away from the sensitive analog.

**Working with Claude sessions**
- Run anything over a minute in the background and end the turn. Never poll in the foreground.
- Quote run times from the timestamps of the same jobs, with every chained step included.
- Check connectivity (LVS, magic "shorted" warnings) on any modified or what-if layout *before*
  queuing sims. A what-if once shorted two supplies and wasted an hour of runs.
- Several sessions on one repo: give each its own block, use worktrees for risky changes, stage and
  commit in one command, and never `git add -A` or `rebase --autostash` in a shared checkout.
- Design work and small sims on the laptop. Full verification on the big machine, started from a
  `docs/handoff_<topic>.md`.

## Effort to avoid
- **Tunable or calibrated-in-design blocks when measured silicon already gives the number.** A
  previous shuttle's measurement plus a silicon/extracted factor was enough.
- **Closed-loop sims through a fully extracted high-gain path.** They were far too slow; split the
  system instead (see verification.md).
- **On-chip passives that "should" help** (a matching inductor, interstage AC coupling) without first
  checking the loss in sim. Both were worse here.

Spend the effort on MC, supply sweeps and the power grid instead.

## Starting a new project: checklist
- [ ] Repo skeleton: `xschem/` (+`gen/`), `layout/gen/`, `layout/pex/`, `layout/ref/`, `sim/<block>/`,
      `model/`, `verilog/`, `docs/`, `tools/`, `build/` (gitignored). Tracked root `.spiceinit`.
- [ ] Copy [scripts/](scripts/README.md) into `tools/` and `layout/`, then set the image tag, PDK and
      paths.
- [ ] `docs/agent_start.md` (rules, what to read, done criteria), `STATUS.md` (short, "pick up from
      here"), `docs/history.md` (per-block detail), `docs/verification.md` (every check with its run
      command).
- [ ] Bench numbers from previous silicon, the platform's pad/supply model, and a system model with
      budgets.
- [ ] Pinout as one source of truth, checked in CI against info.yaml, the schematic, the LEF and GL.
- [ ] CI: TT gds + precheck, real tile LVS with pinned tools (fail on property errors), docs.
- [ ] A constraints file (net classes, aggressors, modes, keep-outs) written at schematic time for
      the floorplan and router (sketch in floorplan-power.md).
- [ ] Book the big machine for the final verification. It needs a day.
