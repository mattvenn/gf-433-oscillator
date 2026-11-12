# Handoff: return the vg decap to VDD (PMOS gate cap), model to tile (local session)

**Goal: move the ring's 3 pF `vg` decap from VSS to VDD by redrawing it as a PMOS gate cap (gate `vg`, S/D/B on
VDD, in an n-well), and carry the change through the simulation model, the schematic, the layout, the top level, the
tile and the docs, with every check passing. Then confirm the 25 MHz supply spur on the re-extracted layout.**

Read `STATUS.md` item 3 (the "To look at later: the 25 MHz supply spur" bullet) first. **Work in
`/foss/designs/gf433-sims`** (`git pull --rebase` first). Every step is a short local run (minutes); no sim server.
Commit and push after each phase (model, layout, tile, docs) so nothing is lost. Stage named files and commit in one
command; never `git add -A`; never commit `sim.yaml`; don't commit `build/` or `.spiceinit`.

## Why (2026-11-12)
- The 25 MHz spur from the `tx_fine` macro's clock (r12, 4.48 pC per cycle on the 1.32 Ω tile supply) was
  −45.5 dBc (tt): it passed the −40 target, but ff was only 3.4 dB inside.
- `sim/tune/spur_paths.py` found that all of it comes in through the ring inverters' own VDD:
  - ripple on the ring alone: −45.3 dBc;
  - ripple on either DAC, or on nothing: about −80 dBc.
- **The mechanism:**
  - the ring runs between VDD and `vg`, so its supply is VDD − `vg`;
  - the 3 pF decap ties `vg` to VSS, so at 25 MHz `vg` holds still (2 mV p-p) while VDD moves 15 mV;
  - the ring therefore sees about 17 mV across it;
  - at DC, `vg` follows VDD, which is why the static supply sensitivity (8.3 kHz/mV) looked harmless.
- **The fix:** the same capacitor, returned to VDD, so `vg` rides with VDD and VDD − `vg` stays quiet.

**Results so far** (`sim/tune/vg_decap.py`, `build/tx_fine/vg_decap/`):

| Check | Today (decap to VSS) | Decap to VDD |
|---|---|---|
| PMOS cap C at each corner's vg (737 µm², 6 × 30.71 / 4 µm) | NMOS 2.9–3.1 pF | 2.9–3.15 pF |
| 25 MHz spur, schematic, tt / ss / ff | −45.2 / −47.0 / −43.4 dBc | −79.8 / −80.3 / −80.8 dBc |
| 25 MHz spur, extracted vco_top (decap swapped in the netlist), tt / ss / ff | −46.1 / −47.8 / −44.2 dBc | −88.4 / −89.6 / −89.7 dBc |
| Supply FM, tt, at DC / 1 / 10 / 25 / 60 MHz (kHz per mV) | 8.3 / 95 / 687 / 919 / 972 | 8.3 / 6.7 / 8.5 / 15 / 31 |
| Start-up, 5 corners × code 0 / 31 (+ tt 1 µs ramp) | all start | all start, 0.5–1 µs later, same f |
| TX driver on (behind the power switch), ring jitter | 0.20–0.29 ps rms | 0.10–0.13 ps rms |
| TX driver on: ring frequency shift | +0.03…+0.05 % | unchanged (the DC drop through 1.32 Ω) |

- **Size:** keep 3 pF.
  - 2–4 pF is within 4 dB of the best; 6 pF is worse (−74 dBc).
  - **Any C left from `vg` to VSS undoes it:** 2 pF to VDD + 1 pF to VSS gives −54.9 dBc.
  - So don't keep the old NMOS decap alongside, and don't add C from `vg` to VSS.
- **Device:** the PMOS form, not an NMOS with its gate on VDD. That NMOS gives only 2.4–2.8 pF to VDD and leaves
  0.5–1 pF of junction C on VSS.
- **No MIM on TT GF** (`docs/platform.md`: no Metal5).

## Phase 1: simulation model (so every bench uses the new connection)
1. `sim/vco/vco_bias.py` `netlist()`: the cfed branch writes `Cvg vg 0 {cvg}`.
   - Add a parameter `cvg_to` (default `"vdd"`), giving `Cvg vg vdd {cvg}`; `cvg_to="vss"` reproduces the old circuit.
   - Keep the ideal C here: the device-level check is the layout's LVS and the extracted runs.
2. Fix the users that string-match the old line:
   - `sim/tune/mdac_sim.py:394` (`noise_deck` comments out `Cvg vg 0`);
   - `sim/tune/vg_decap.py` (`CVG_OLD`; its "today" cases must ask for `cvg_to="vss"` explicitly);
   - `sim/tune/spur_paths.py`;
   - `xschem/gen/check.py` (~line 71–81, maps `Cvg` to the MOS decap: map it to the PMOS form);
   - `layout/gen/export_core_v3.py`, `layout/gen/pex_check_v3.py`, `layout/gen/pex_sim_v3.py` (`grep -n "Cvg\|cvg"`);
   - `sim/lsdiv/lsdiv.py` and `sim/mc/dac_mc.py` match by name only (check, probably fine).
3. Re-run `python3 sim/tune/phase_c.py c4q` (the supply spur with the r12 charge), then `sim/tune/plot_phase_c.py`.
   Fig. 3c of `docs/tx_fine_tune.md` gets regenerated; keep r10/r12 today as the reference trace if useful.

## Phase 2: schematic and layout of ring_core_v3
1. **Layout** (`layout/gen/ring_core_v3.py`):
   - Today the decap is one row of `nf = 6` NMOS fingers (W 30.71, L 4 µm, `decap_size()`, `COX` of nfet_03v3) at
     the bottom left: S/D columns go down into the VSS rail and gate contacts go up into the `vg` strap (M1 + M2)
     under the inverter cluster.
   - Redraw it as **pfet_03v3, same W / L / nf**, in its own n-well:
     - an n+ tap (VDD) around or beside it;
     - S/D on VDD;
     - gate contacts on the `vg` strap as now.
   - VDD has to reach it. Today VDD is the core's top rail over the n-well tap ring; the decap sits next to the
     bottom VSS rail.
     - Options: an M2/M3 VDD drop from the top rail, or move the decap up into the P band.
     - The core has no Metal4; keep it that way, since the tile's Metal4 stripes are separate.
   - Watch the n-well spacing to the NMOS DAC and the p+ VSS rail (let magic and KLayout DRC decide), and keep the
     `vg` strap's resistance low: from each N source, 8.4 Ω to the decap and 13 Ω to the DAC
     (`docs/ring_layout_v3.md`).
   - `decap_size()` sizes W from nfet COX; the PMOS gave the same C at the same size (cv study), so keep
     6 × 30.71 / 4 or re-derive from `build/tx_fine/vg_decap/cv/cv.json`.
2. **Schematic** (`xschem/gen/ring_core_v3.py`): `DC` becomes a PMOS with S/D/B on VDD (the sheet draws S/D/B to
   VSS today). Drawn textbook-style with wires. Regenerate and re-render the sheets; check them with
   `python3 xschem/gen/check.py`.
3. **Checks:**
   - `bash layout/gen/check_v3.sh`: DRC, KLayout DRC with `feol=true beol=true`, antenna, LVS against the xschem
     netlist, and two mutations that must FAIL.
     - Its antenna note expects 6 "feedback" entries for the decap fingers with S = D = VSS; update that note for
       S = D = VDD.
     - Add or keep a mutation that would catch the decap's S/D on the wrong net.

## Phase 3: top level, tile, extraction
1. `python3 layout/gen/vco_top.py` (abuts ring_core_v3, cgm_ref, lsdiv, decap_ls), then
   `bash layout/gen/check_top.sh`.
2. Re-extract: `bash layout/gen/pex_top.sh c`, then `rc`.
   - The rc step runs `layout/gen/rcfix.py` and writes `vco_top_rcx.spice`.
   - **Use magic 8.3.642** (the script pins it; 8.3.684 drops substrate C).
   - Always simulate the `_rcx`, never the raw `_rc` (it double-counts coupling C, `docs/rc_extraction_fix.md`).
3. Tile: `layout/gen/tt_wrapper.py`, `lvs/make_source.py`, then `bash layout/gen/check_tt.sh`. The tile LVS, DRC
   and antenna must stay clean. Regenerate `docs/img/tt_wrapper.png` and the vco_top render if the docs show them.
4. **Re-run on the real layout:**
   - the spur and TX checks: `python3 sim/tune/vg_decap.py pex`. Its PMOS swap expects six NMOS decap fingers in the
     netlist. With the new layout the decap is already PMOS, so change `pex()` to run the committed netlists as the
     "new" case and keep today's numbers from this handoff as the reference.
   - the frequency map check: `phase_c.py` c1 (`pex_deck`). f should move by under 0.1 %; the netlist swap gave
     +70 kHz.
5. Push and let CI run (gds/precheck, LVS, docs). All three must pass.

## Phase 4: docs
- `docs/tx_fine_tune.md`: a "Supply coupling: the vg decap" subsection in Matt's technical style (problem → fix →
  evidence). Include:
  - the path isolation;
  - the supply-FM-against-frequency table;
  - the size sweep;
  - the extracted spur;
  - the honest limits: ground ripple not modelled, the VDPWR before the power switch unknown.
  
  Update the summary row (supply spur) and Fig. 3c.
- `docs/ring_layout_v3.md` (Decap section), `docs/top_layout.md` (if dimensions moved), `docs/schematics.md`.
- `STATUS.md` item 3: replace the "to look at later" bullet with the result. Mark this handoff Done at its top line.

## Traps (from this project)
- **No MIM on TT GF.** Large caps are MOS caps.
- **magic 8.3.642** for extraction; **KLayout gf180 DRC needs `feol=true beol=true`**, or it silently runs zero rules.
- **Judge runs by output files and log tails** ("Transient op started", "singular"), not exit codes.
- **Mutation-test every checker** you touch.
- **Kill your own ngspice runs with care:** `pkill -f` matches its own shell. Use `[x]`-bracketed patterns or the
  `/proc/<pid>/cwd` of the run.
- `rm` is aliased to `rm -i` here: use `command rm -f`.
- `gh` isn't installed: use curl against the GitHub API for CI status.
- Frequency in this ring is measured at **mid-swing** (it swings `vg`…VDD and never crosses VDD/2).

## Not in scope
- Ground-bounce modelling (needs the TT ground path's R and L; ask tnt with the VDPWR question).
- The floorplan clean-up Matt suspects (routing and placement coupling into the analog). Note anything you see, but
  don't redesign the tile.
