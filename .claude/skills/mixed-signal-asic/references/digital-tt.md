# Digital macro, cocotb, formal, Tiny Tapeout, CI

## Tiny Tapeout analog tile
- 3.3 V needs the `_3v3` template plus `uses_vapwr: true`. Use the analog DEF
  (`tt_analog_3x2_3v3.def`, 493 × 226 µm), not `tt_block_3x2_pg.def` (the digital one, no ua pins).
  Read the pin positions from the DEF into a `tile.json`.
- All pins are met4, 1 µm deep. The ua[] pins are on the bottom edge and the digital pins on the top
  (x 15–131). ua[6]/[7] weren't usable here. The pin positions drive the floorplan.
- Power pins: vertical met4 ≥ 1.2 µm wide, running from within 10 µm of the bottom edge to within
  10 µm of the top. Several per net are allowed (they mustn't overlap or abut). **No met5 anywhere**:
  it belongs to the TT PDN.
- The analog pad path (≈2 pF, 1 nH, 3 pF, 50 Ω mux, 250 fF) can't be changed from the chip. The
  "4 mA" analog-pin limit is EM/RMS, not hard. A 3.3 V output stage gave +4.2 dB over 1.8 V.
- Document the voltage limit of any pin with thin-oxide devices (0–1.8 V).
- Floating uio inputs must give the safe default mode. Require a magic pattern (e.g. `1010`) to enter
  debug or raw modes. Mode straps risk contention if the RP2350 drives them.
- Export: copy the GDS, then `lef write -pinonly -hide`, then patch `USE POWER/GROUND` onto the supply
  pins (magic leaves it off and precheck wants it). See `scripts/export_tt.sh`.
- Run a local precheck (no met5, power-pin width and extent, nothing touching) plus magic DRC "the TT
  way" before relying on the GitHub precheck. Re-export the GDS/LEF and re-precheck after every layout
  change. Confirm the precheck accepts known antenna violations inside the macro.
- Old TT template scripts were stale (2x2 DEF, another project's readnet lines), and the inherited LVS
  CI had never actually reached LVS. **Audit inherited CI.**

## Digital macro (LibreLane)
- Die-size sweep, same config:
  - 200×220 at 82 % utilisation: clean.
  - 190×220 at 86 %: failed detailed routing.
  - A flat 450×110: failed antenna repair at 85 % (the default 4-row margins cost ~22 µm, leaving no
    room for diodes) and GRT overflow at 76 %.
  - Keep utilisation ≲ 80 % and avoid very flat dies (TT has no met5 for the macro).
- The macro's max layer is met4, so tile straps can't cross it. Leave a strap lane between the macro
  and the analog blocks, and bring pins out on met3 (E/W).
- `pin_order.cfg` (io_place.py): N/S pins sit on met2 tracks (origin 0.23, step 0.46), E/W on met3
  tracks (0.34, 0.68). A 1 µm pitch is off-grid, so use 1.36 or 0.68. If pins + `$n` < slots the
  group is spread and centred; if equal, io_place asserts. Pad with a trailing `$n` to exactly
  slots − 1.
- Quick pin check (~30 s): `librelane ... --to Odb.CustomIOPlacement`, then read PINS from the DEF
  (1000 DBU/µm).
- For trials, `DRT_OPT_ITERS: 20` caps a non-converging route; remove it for the final run. Killing
  the client leaves the docker container running.
- Orient the macro (MY) so its pin edge faces the analog, order the pins to match the analog block
  pins, and keep clocks on the edge away from the sensitive analog.
- Shift-register flop-to-flop paths cost ~850 hold buffers. Clock gating with
  `sky130_fd_sc_hd__dlclkp_1` (silicon-proven on TT08) removed 508 enable muxes and ~20 % of cells.
  Keep a behavioural latch+AND under `ifdef SIM`.
- Yosys' pre-synthesis check flags function-local wires in always blocks as undriven (a false
  positive).
- Re-check signoff on the shipped GDS/DEF: a re-harden doesn't reproduce the layout bit for bit.
- RTL constants frozen in the macro (e.g. a reset code) cost a re-harden to change. Absorb such changes
  on the analog side, and check the settling in the mixed-signal sim.
- Drive R-2R DACs with strong, balanced buffers: output R in series with the 2R legs gives 1–2 LSB of
  DNL.

## cocotb / Icarus / Verilator
- `make` returns success even when tests fail. Check `results.xml` with `! grep -q '<failure'` (plain
  `failure` matches `failures="0"`), and know that it may hold only the last partial run.
- PATH traps: oss-cad-suite's python (no numpy) gets picked up. `make -C` breaks `$(PWD)` (use `bash -c
  'cd … && make'`). A `|` in `COCOTB_TEST_FILTER` matched nothing.
- GL: `-DFUNCTIONAL -DUNIT_DELAY=#1` with cell models from the image's PDK. GL tests use pins only. A
  PINMON mode on RTL confirms the pin monitors match the internal signals.
- Verilator locally for speed, Icarus as the CI/GL reference.
- Mixed signal via ngspice d_cosim: generate the port list from Verilator's `inputs.h`/`outputs.h`, one
  node per bit (the output order is declaration order). The image's ngspice lowercases vlnggen's shell
  lines and Verilator 5.048 rejects `-mdir`, so vlnggen needed a bash rebuild.
- Add a TT-wrapper cocotb test, with the wrapper generated from the schematic and the analog as a stub.

## Formal (SymbiYosys)
- Prove properties with every input free (straps, comparator, `rst_n` at any time), assuming only a
  reset in the first clock. This found behaviour the sims never exercised.
- Yosys has no hierarchical references: use `connect -set` in the .sby. Abstract big registers to free
  state when no property depends on their contents.
- **Mutation-test each property group** with a deliberate RTL bug.
- Useful properties: mutually exclusive modes, both arms of a differential output never on alone, non-overlapping clocks
  with a dead time, and pipeline timing assumptions.

## Pinout as one source of truth
`check_pinout.py` holds a PINOUT table and checks `info.yaml`, the top schematic nets, the macro LEF,
the GL netlist and `uio_oe` against it, and also emits the cocotb wrapper. It was mutation-tested
(swapped ua[0]/ua[1], a reversed bus, a wrong label) and runs first in CI.

## CI
- `gds.yaml`: TT custom_gds (gds + lef + a `src/project.v` stub) → precheck → viewer. Extra docs (e.g. an
  explainer HTML) can ride along in the `gds_render` artifact.
- `lvs.yaml`: the pinout check, then real tile LVS on the committed gds/ with pinned tools (magic,
  netgen, xschem, PDK hash via ciel), built from source and cached. Fail on property errors. Tile LVS
  source = xschem top + macro `.pnl.v` + hd spice.
- `docs.yaml`: the TT docs action pinned to the shuttle tag.
- One lvs action failed silently for a week (PDK hash missing from volare). Look at CI results, not
  just the badge.
