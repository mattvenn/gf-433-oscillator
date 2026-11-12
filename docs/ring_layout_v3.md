# Ring-core layout v3: current-fed ring (cfed)

`vco_bias.netlist()` with `topo=cfed kc=0.75 k=6 cvg=3e-12 ka=16`, without the reference or the vbn filter. Set the DAC width with `--set wfu=0.30`: the generator's default is still 0.25.
**The committed `layout/ring_core_v3.gds` is the wfu 0.30 layout** (the chosen design; the 0.25 one was committed until 2026-11-08).
Scripts are in `layout/gen/`: `ring_core_v3.py`, `export_core_v3.py`, `check_v3.sh`, `check_v2.sh`, `pex_v3.sh`, `pex_sim_v3.py` and `vg_res_v3.py`.

## Floorplan (`docs/img/ring_core_v3.png`)
- **Left:** the decap, with the vg strap (M1+M2) on it. The v2 cluster sits on the strap without heads, and each N source drops 0.3 µm into it.
  Since 2026-11-12 the decap is a PMOS gate cap to VDD in its own n-well (Decap, below).
- **Right:** the DAC. It has 7 × 6 slots, point-symmetric, with the fine leg and g0 in the middle row. The switches sit above it, in a shared n-well.
- **Area: 70.1 × 51.9 µm = 3636 µm²** (69.1 × 51.9 µm = 3584 µm² with the NMOS decap), against 5889 µm² for v2.

## Node C, C-only (fF)
| | a0 | a1 | a2 | a3 | a4 |
|---|---|---|---|---|---|
| v2 | 2.87 | 3.15 | 3.03 | 2.96 | 3.32 |
| v3 | 3.20 | 3.25 | 3.11 | 2.99 | 3.41 |

## f (MHz) at codes 0 / 6 / 15 / 31, tt 27 °C, vctrl 1.65 V
| wfu | sch cw 0 | sch cw 3 | C | RC |
|---|---|---|---|---|
| 0.25 | 276/456/675/984 | 237/392/582/850 | 232/385/572/837 | 205/341/507/742 |
| 0.30 | 319/523/768/1107 | 274/450/663/957 | 268/442/652/944 | 238/392/578/837 |

- **Effective cw:** 3.4 fF (C) and 6.2 fF (RC).
- **The code sweep is monotonic.**
- **Where the RC loss comes from:** ~~the inverters' gate-poly feeds (63 and 102 Ω), as in v2~~. **Corrected:** the RC
  netlist double-counted the coupling C (`docs/rc_extraction_fix.md`); with that removed the RC column is about 13 % higher,
  close to the C column. The "RC" effective cw of 6.2 fF is the double count.

## Decap
- **Device (since 2026-11-12):** pfet_03v3, 6 × 29.82/4.12 µm (737 µm²), with the gate on vg and S/D/B on VDD, in
  its own n-well. The return to VDD keeps the ring's own supply, VDD − vg, quiet at the digital macro's 25 MHz clock:
  the 25 MHz supply spur on the extracted layout goes from −44 … −48 to −84 … −85 dBc (tt / ss / ff) (`docs/tx_fine_tune.md`, "Supply coupling: the vg decap").
- **Before:** nfet_03v3, 6 × 30.71/4 µm, S/D/B on VSS, C(V) 2.95–3.00 pF over 1.1–3.0 V. The PMOS of the same area
  gives 2.9–3.15 pF at every corner's vg (`sim/tune/vg_decap.py cv`).
- **Drawing:** an n+ tap strip with a VDD strap (M1 + M2) runs under the fingers, just above the VSS rail; the S/D
  columns drop onto it. Two 1 µm M3 drops bring VDD down from the top rail over the inverter cluster (no Metal4). L
  went from 4 to 4.12 µm so that W (29.82 µm) leaves room for the tap strip without moving anything above the decap:
  the core's vbn pin still meets cgm_ref's vbnf at the same y. The n-well is 0.43 µm from the DAC's p+ rails, so the
  DAC side moved 1.0 µm right.
- **LVS:** it replaces Cvg.
- **Frequency:** the extracted vco_top runs 0.10-0.11 % lower than with the NMOS decap (420.53 against 420.99 MHz at
  tt word 512). An ideal 3 pF in place of either decap device gives the same f within 1 ppm, so it is the re-drawn
  wiring, not the device; the mechanism is an open item (`docs/tx_fine_tune.md`, Limits).

## vg resistance
- From each N source: 8.0–8.2 Ω to the decap and 12.6–13.0 Ω to the DAC (PMOS decap, `ring_core_v3_w30chk_rc.spice`,
  2026-11-12; 8.3–8.5 Ω to the NMOS decap).
- Between two sources: 6 Ω or less.

## Checks (`build/check/ring_core_v3*/summary.txt`)
- **Script:** `bash layout/gen/check_v3.sh [gds] [outdir]`. The LVS source is the xschem netlist of `xschem/ring_core_v3.sch`; `layout/ref/ring_core_v3.spice` is only a cross-check. Three broken copies of the schematic must fail LVS (a DAC leg's m, a switch gate, the decap's S/D on VSS). `XSCH_SET=wfu=0.25,wff=0.25` checks a GDS made at another width.
- **Results:** DRC 0 in magic and in KLayout (FEOL+BEOL), antenna 0, LVS "match uniquely" with no property errors. Magic's feedback log has 6 entries, which are not violations: they are the decap fingers (S = D = B = VDD, "device missing 1 terminal; connecting remainder to node VDD").
- **Widths covered:** wfu 0.25, 0.30 and 0.35.

## For the level shifter
- **Tap:** take a0 from its M2 edge tap.
- **Load:** each fF costs about 1 % of f.
- **No current from vg:** use the vg pin for sensing only.

Wall time: about 25 min.
