# Block layout on sky130: generators, DRC, LVS, PEX

Layout was **Python generators run in KLayout batch mode** (`klayout -b -r layout/gen/<block>.py`)
using the PDK's sky130 KLayout pcells. magic and netgen were used only for DRC, LVS, antenna and
extraction.

## Per-block loop
`gen/<block>.py` → `check.sh <block>` (magic DRC, KLayout `sky130A_mr` DRC, magic antenna on a flat
copy, density, netgen LVS against the xschem netlist; ~10 s) → `pex.sh <block>` + `pexfix.py` →
`tb_<block>.py --pex` through `pexswap.py`. Done = DRC 0 in both tools, antenna 0, LVS match with no
property errors, and PEX close to the schematic on what the block must do.

## Shared generator library (worth rebuilding)
- `lay.py`: a `Fet` wrapper that reads S/D/gate/guard-ring terminals from the pcell geometry, `via()`
  for DRC-safe cut arrays, `stack()`, `pin()`, `label()`, `clear()`, `write_ref()`.
- `rows.py`: a PMOS row and an NMOS row, each with one shared guard ring, and a met3-track / met2-stub
  channel between them. Track width comes from the measured RMS current, and tracks are assigned with
  a constrained left-edge algorithm. It came out 19 % smaller than one column per stage.
- Changing shared code: regenerate every dependent block, XOR its GDS against the committed one (it
  must come out identical), and push the change on its own, early.
- Generators should take an **aspect ratio and a pin spec** (edge, order) as inputs. Then a floorplan
  rework is just a rerun.
- Reuse proven IP unchanged (the R-2R DAC came verbatim from an earlier TT project, with its schematic
  redrawn device for device).

## Environment
- The pcells need gdsfactory 8.x but the image ships 9.x. Install 8.5 into a private dir first on
  `sys.path` and delete the pip `klayout` so KLayout's own module wins (`scripts/kpcell_setup.sh`).
  A fresh worktree needs that dir copied in (it's gitignored), as well as gitignored inputs like the
  TT DEF.
- A pcell version bump can move edges by 0.01 µm, so regenerated GDS isn't bit-identical across
  images.

## Routing traps in generated layout
- Channel routing: a P stub going down and an N stub going up at the same x short in met2 unless every
  overlapping pair gets a vertical constraint.
- Strip groups: give each run of one net's strips (with no other net between) its own bar. One tail
  bar across `tail | d | tail` shorted three nets.
- Same-net stubs closer than spacing need explicit merging. A naive "clear cuts within 0.1 µm" removed
  both cuts and opened the net.
- `clear()` before drawing, or you delete your own new wire. Remove pin shapes too: magic reads a pin
  shape (datatype 16) as metal and KLayout doesn't.
- Net labels on the label purpose (e.g. 70/5) without a pin shape name the net for LVS/PEX without
  making it a port.
- A riser spanning rail to rail shorts a signal to both supplies. LVS shows "(no pin, node is out)".
- Look at every route. A dead-end pin stub passed DRC and LVS and was only found by eye.

## DRC gotchas (sky130)
- g5v0d10v5 pcell: `w` is per finger, and the S/D met1 strips are 0.23 µm (widen to 0.29 for via1).
- `bulk='guard ring'` draws tap + li only. Add mcon + met1 yourself.
- One nwell over the whole PMOS row, and one hvi over everything HV, so neighbours merge. magic treats
  each GDS cell on its own: a tap is HV only if nwell + hvi are in the same cell, so flatten the ring
  into the well cell (symptoms: nwell.4, LU.3, nwell.8). Write leaf GDS flattened so a clean block
  stays clean in the tile (hvi.5 showed up only standalone).
- Ringless nfets leave hvntm notches. Draw one hvntm rectangle over the whole NMOS row.
- Two overlapping via arrays fail via2.1a/2.2 in KLayout but not in magic. Let shapes abut.
- Metal wider than 3 µm needs 0.4 µm spacing (m3.3cd / m4.5ab), and a rail merged with a supply wire
  becomes "wide".
- MIM: unrelated met3 within ~1.3 µm of the bottom plate is an error (capm.11/2b), as is a via2 within
  0.1 µm (capm.8) or a via3 within 0.08 µm of the edge (capm.5). **KLayout's deck missed capm.8/5 and
  magic caught them. Run both decks.** capm is a keep-out that only the top-plate net may cross.
- Poly heads between facing gate pads need 0.75 µm (poly.2/npc.2).
- high_po 0p69 side by side: the rpm markers must merge (pitch ≤ 1.27) or sit ≥ 0.84 apart.
- Tiled ring cells with implants 0.2 µm apart fail psdm.1. Bridge psdm across them.
- The middle via pad in a met3/met4 stack must meet 0.24 µm² minimum area.
- Print magic DRC locations in µm (`cif scale out`).

## LVS
- Dummies are devices to netgen: put them in the schematic, with every terminal on the rail.
- Parameterised blocks: write a parameter-substituted reference (`layout/ref/<variant>.spice`), because
  netgen can't evaluate `W='0.42*kn'`. **But the tile LVS source must be the real schematic,
  elaborated, not the generator's copy.** Mutation-test it: W 20 → 24 must fail.
- Strip instance parameters from hierarchical references, or netgen compares them.
- Drop schematic wiring-estimate caps from the LVS reference.
- Std cells inside analog blocks: copy the PDK GDS in and read the hd spice library on the schematic
  side.
- **Fail on property errors.** netgen says "Circuits match uniquely" alongside "Property errors were
  found" (top) or "had property errors" (a subcell). `check.sh` handles this.

## Extraction
- Flatten, `extract do local`, `cthresh 0`, plus `extresist` for R. The coupling range is finite (0 aF
  at ~200 µm). The substrate is tied to VSS, so **substrate coupling is not modelled**: use guard
  rings and distance.
- `pexfix.py` reorders ports to the schematic `.subckt` order (instances connect by position) and ties
  the substrate to VSS. `pexswap.py` swaps the schematic subckt in a deck for the extraction.
- Tile: flatten first, or each block's VSUBS floats. Strip the digital macro and label its pin-wire ends
  with the wrapper's port names so the result drops into the analog testbench. Go in the order lvs →
  c → rc. If the "c" netlist moves DC points, diff its non-C elements against the lvs one.
- Full-tile RC is slow (18k C / 85k R took ~1 h per run). Consider C-only for most nets and RC only on
  the critical paths.
- **Pin the magic version** (8.3.684 dropped substrate C) and sanity-check one known node's C after any
  upgrade. Committed extractions go stale: re-extract before comparing.
- Extract a block in its real surroundings before trusting its parasitic loss.

## Antenna and density
- magic `antennacheck` finds nothing on a hierarchy (it misses gates inside pcells) or in the same
  session as the LVS extraction. Run it on a flattened copy in a fresh session with `antennacheck
  debug`, and prove the setup with a deliberate violation (a 0.5 × 0.42 µm g5 gate on 300 µm² of
  met1).
- A long top-level met3 run into the macro's input gates fails antenna. A met4 jumper near the macro
  fixes it.
- Density: the PDK wants ≥ 40 % clear per layer and TT adds fill. Flag > 50 % per layer. MIM blocks hit
  73–84 % met3 by nature; accept that only when there's no needless metal. Size rails to their current
  rather than filling space with plates.

## EM and current sizing (tech-LEF limits, Tj 90 °C; design with 2× margin)
| | DC limit |
|---|---|
| met1/met2 | 2.8 mA/µm |
| met3/met4 | 6.8 mA/µm |
| met5 | 10.17 mA/µm |
| mcon / via1 / via2,3 / via4 | 0.36 / 0.29 / 0.48 / 2.49 mA per cut |

- Sheet R: met1/2 ~0.125 Ω/□, met3/4 ~0.047 Ω/□. Put big currents on wide met3.
- Measure the currents with 0 V ammeters in the block bench (RMS for AC nets, average for supplies),
  then use cuts ≥ 2·I/limit. Have the generator print a via-count check.
- v1 mistakes: gate links on one via1 ran 5× over the limit, and 0.29 µm source strips were too
  narrow. They cost 0.46 dB and +26 % delay after extraction.

## Analog layout practice
- Matching: unit devices, the same orientation and current direction, dummies on a defined potential,
  common centroid (ABBA), no low metal over sensitive devices, and matched PMOS kept away from nwell
  edges.
- Buffer digital controls locally on the analog block's own supply. Every block has a defined off
  state, and its bench tests off and start-up.
- High-frequency gate fingers: per-finger gate R < 1/gm. Contact both ends if needed.
- Switched-cap symmetry: fixed track order with phi/phib mirrored, VDD/VSS shield tracks, nothing
  crossing the channel. That took the imbalance from 0.19 to 0.002 fF and the offset from 4 to
  0.15 mV. Check (phi − phib) C per node in the extraction.
- A trim pair running 90 µm alongside the outputs gave 6–7 fF of positive feedback. Placed beside the
  core it was 0 fF.
- Folding a long high-gain amplifier: compare fold variants by extracted per-stage gain. A 14 µm guard-ring moat
  (p-tap ring + n-well stripe) gave 0 aF output→input.
- Filters: put the input and output pins on different edges so coupling can't bypass the filter.
- Fold long std-cell rings into two rows (R180) to keep the feedback wire short.
- Cross-coupled level shifters have a sizing window: too-strong pull-ups latch (fs first) and too-weak
  pull-downs skew at ss/cold. Check every corner for "not switching".
- Keep matched devices far from hot drivers (~50 mW here), or on a symmetry line through them.
