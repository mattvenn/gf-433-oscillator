# Handoff: ring-core layout generator, DRC/LVS/PEX (sim pod, overnight)

**Goal: a parametric layout generator for the VCO ring core, clean in DRC (magic and KLayout), LVS and antenna
checks, plus an extracted-versus-schematic frequency comparison. Commit it with a short report in
`docs/ring_layout.md`.**

A second agent may be running bias and tuning sims (`docs/handoff_bias_and_tuning.md`) in the same repo at the same
time. Commit only your own files, use `git pull --rebase` before pushing, and use at most **8 CPUs**.

## What to draw
The ring core of `sim/vco/vco_bias.py` (function `netlist()`, default `P`, real resistor settings
`rideal=0 lnw=4.5 lnp=100`), **without** the const-gm reference, its resistor or the filter. The reference is being
redesigned tonight. The core contains:
- **5 stages.** Each has:
  - a head PMOS (`whead` / `ls`);
  - an inverter (`wp`, `wn`, L = 0.28 µm);
  - a foot network: a base leg (k = 16 × unit `wfu` / `ls`), binary coarse legs m = 1, 2, 4, 8, 16 and a fine leg
    (`wff` / `lff`, gate vctrl).
- **The master leg:** a copy of one foot plus the PMOS diode `MPB`, which makes vbp for all heads.
- **The coarse gate switches** TN/TP/TD for 5 bits (`g_b = bit ? vbn : 0`).
- **Pins:** VDD, VSS, vbn (in), vctrl (in), bit[4:0] and bitb[4:0] (in, 3.3 V logic), and the ring nodes a0…a4.
  Bring a0 out as the output, and keep a1…a4 reachable for a later buffer and probing.

Units: µm. The 3.3 V devices are `nfet_03v3` and `pfet_03v3` in gf180mcuD.

## Rules for the layout
1. **It must be a generator** (`layout/gen/ring_core.py`, or Tcl under `layout/gen/`), driven by the same parameter
   names as `vco_bias.P`, so that a sizing change is just a rerun. No hand edits to the output.
2. **Every ring node must see the same capacitance.**
   - Make all 5 stages identical cells, placed with the same orientation.
   - Wire the loop so that no node gets a long return wire. For example, use a folded order 0, 4, 1, 3, 2 (or two
     rows), so that all stage-to-stage wires are about equal in length.
   - Report the extracted capacitance per node; the schematic assumed 2 fF of wiring.
3. **Guard rings:** an n-well tap ring around the PMOS group, and a p+ substrate tap ring around the whole core.
   Taps in every device row.
4. **Wiring:**
   - The bias nets (vbn, vbp, vctrl) run on their own metal, away from the ring nodes. Where they must cross a ring
     node, cross at right angles.
   - VDD and VSS are wide rails (≥ 2 µm Metal1/Metal2), with several vias at each tap.
   - Leave Metal4 free for the TT power stripes. Metal5 isn't available to the project.
5. **Choice of tool.** Use whichever of these the image supports better, and say why:
   - KLayout Python with the gf180mcuD pcells (look under `$PDK_ROOT/gf180mcuD/libs.tech/klayout/`);
   - magic Tcl with `magic::gencell` devices.

   The repo's `mag/` flow (magic rc file, DRC, LVS and extraction Tcl) is the reference for the magic side.

## Checks (all must pass, judged from the output files, not exit codes)
1. **magic DRC: 0 errors.** Also **KLayout DRC: 0 errors**, with the gf180mcuD deck from the PDK.
2. **Antenna: 0 violations.** Prove the check works with a deliberate violation on a copy.
3. **LVS:**
   - "Circuits match uniquely" and **no property errors** (W, L, m all correct).
   - The source netlist must be the schematic. Export the core as a `.subckt` from `vco_bias.py`'s own netlist
     (add an export function), not from the layout generator's parameters.
   - Mutation-test LVS once: swap two coarse-bit legs on a copy; LVS must fail.
4. **Extraction and simulation:**
   - Extract for simulation (C first, then RC), and swap the extracted core into the `vco_bias.py` deck in place of
     the schematic core. Use `tools/pexswap.py` or a small new option.
   - At tt and 27 °C, ideal vbn from the schematic reference, run codes 0 / 10 / 31 at vctrl 1.65. Compare f and
     power with the schematic (`cw = 2 fF`).
   - Report the shift. The schematic plus 2 fF is expected to be within about 10 %. Larger means the wiring C
     estimate was wrong, which is useful to know, not a failure.
5. **Area and image:** the bounding box in µm, plus a PNG from `tools/render_gds.py`.

## Report and commit
`docs/ring_layout.md` contains:
- the tool and version;
- the floorplan sketch (a stage cell, and how the loop is folded);
- area;
- check results with their log paths;
- capacitance per node;
- PEX vs schematic frequencies;
- run times;
- open issues.

Commit the generator, the export function, the small Tcl/Python check scripts, the GDS of the core (it is small),
and the report. Stage and commit in one command, never `git add -A`, and don't commit `build/` or `sim.yaml`.
Then `git pull --rebase` and `git push`.

## Don't
- Don't change any device size. If a size can't be drawn (a DRC minimum), report it and use the nearest legal value
  on a branch only.
- Don't place the core into the TT tile yet, and don't touch the reference circuit.
- Stop if the time spent on the generator passes about 4 h without a DRC-clean core, and write up where it got stuck.

## Done
When pushed, add a line at the top of this file: `> Done (date): see docs/ring_layout.md`.
