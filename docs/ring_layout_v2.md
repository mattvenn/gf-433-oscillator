# Ring-core layout v2: compact inverter cluster

Same netlist, sizes and pins as v1 (`docs/ring_layout.md`), LVS against `layout/ref/ring_core.spice`.

```
tools/osic-mac python3 layout/gen/ring_core_v2.py        # -> layout/ring_core_v2.gds
tools/osic-mac bash layout/gen/check_v2.sh layout/ring_core_v2.gds ring_core layout/ref/ring_core.spice build/check/ring_core_v2
tools/osic-mac bash layout/gen/pex_v2.sh c|rc|lvs        # -> layout/pex/ring_core_v2_{c,rc,lvs}.spice
tools/osic-mac python3 layout/gen/pex_sim_v2.py          # -> build/pex_sim_v2/results.txt
python3 layout/gen/ctable.py layout/pex/ring_core_v2_c.spice
```

## Floorplan
The five feet, the master and the switches stay in one row along the bottom, drawn by v1's code. The bias tracks are unchanged.
Above them, five M2 f tracks carry each foot's f up to a **cluster of the five inverters** at 2.6–3.0 µm pitch, in loop order 0,4,1,3,2.
Each column is N, then the gap, then P, then H stacked above P, joined by a straight h line.
The gap holds the input poly contacts, the n-well tap strip and three short M2 ring rows. Some columns are mirrored, so every hop is 3.7–4.8 µm. There's no padding and no shielding.
There are two small n-wells, one for P+H and one for MPB+TP, each with its own tap ring. A p+ ring goes round everything. Metal4 is free. `docs/img/ring_core_v2.png`.

**Area: 126.1 × 46.7 µm = 5889 µm²**, against 147.9 × 48.6 µm (7192 µm²), so 18 % smaller.

## Ring-node C (C-only, fF)
| node | total | to VSS | to VDD | to other ring nodes | to f | other (own h) | v1 total |
|---|---|---|---|---|---|---|---|
| a0 | 2.87 | 0.40 | 0.79 | a1 0.59, a4 0.16 | 0.28 | 0.65 | 10.23 |
| a1 | 3.15 | 0.45 | 0.54 | a0 0.59, a2 0.15, a3 0.02, a4 0.40 | 0.36 | 0.65 | 10.08 |
| a2 | 3.03 | 0.34 | 0.61 | a1 0.15, a3 0.37, a4 0.38 | 0.31 | 0.86 | 10.06 |
| a3 | 2.96 | 0.44 | 0.72 | a1 0.02, a2 0.37, a4 0.34 | 0.42 | 0.64 | 9.99 |
| a4 | 3.32 | 0.34 | 0.56 | a0 0.16, a1 0.40, a2 0.38, a3 0.34 | 0.35 | 0.79 | 10.07 |

The nodes are 3.07 fF ±7 %, about a third of v1.

## f (MHz), tt 27 °C, vctrl 1.65 V
| code | sch cw 0 | sch cw 2 fF | sch cw 10 fF | **v2 C** | **v2 RC** | v1 C | v1 RC |
|---|---|---|---|---|---|---|---|
| 0  | 309.7 | 241.7 | 147.8 | 758.1 (*) | 317.4 (*) | 177.2 | 152.0 |
| 10 | 531.2 | 416.7 | 248.4 | 597.8 (*) | 413.0 | 281.6 | 244.7 |
| 31 | 841.0 | 698.5 | 429.7 | 753.9 | 611.5 | 455.0 | 401.6 |

**Effective cw** (C-only, at code 31, where it's well behaved): **1.1 fF**.

(*) **New problem: low codes lose current control.** At code 0 the C-only ring runs at 758 MHz with a0 swinging only 0.27–2.18 V. That's faster than code 31.
The cause is the **f node**: 24–26 fF, mostly the foot's own M2 row straps (v1 already had 22.4 fF). Once the ring C is small, f acts as a charge reservoir, and the stage stops being starved.
Evidence (`build/modechk/`):
- With the f wiring C removed, the extraction gives 288 / 462 / 715 MHz.
- The schematic at cw 3 fF plus 25 fF on each f gives 461 MHz at code 0, against 222 MHz without it.
- Grounding the ring/f couplings changes nothing.
- The start-up state (DC operating point, `uic`, a code 31 → 0 step) changes nothing either.

## What limits further reduction
- The device-equivalent node C, from the schematic 1/f-vs-cw slope, is 7–10 fF, so wiring is now about 25 % of the total.
- About 1 fF of the 3 fF is the inverters' own side-by-side S/D contact strips (to h and f).
- About 0.6 fF is VDD under the gap.
- The M2 hops are about 1 fF.
- **The next step is the foot's f C, not the ring.**

## Checks (`build/check/ring_core_v2/summary.txt`)
- **magic DRC 0**.
- **KLayout DRC 0**: 494 rules, FEOL+BEOL. The 2026.05 image's deck ignores `decks=`, so `check_v2.sh` adds `feol/beol=true`.
- **antenna 0**.
- **LVS "Circuits match uniquely"**, with no property errors.
- Tools: magic 8.3.642 for everything, netgen 1.5.319, KLayout 0.30.8.

Wall time about 35 min, with 80 s per sim batch.

## Follow-up: foot-node (f) capacitance budget (schematic, 2026-11-08)
`vco_bias.py cfsweep` adds Cf from each stage's f node to ground (`cfn`). The sweep covers 0–25 fF × codes 0–31 ×
5 corners × 0/70 °C, with the winning reference, VDD 3.3 V and vctrl 1.65 V. Results are in
`build/vco/bias_cf_*/cfsweep.json`. A Cf passes if f rises with the code, the swing is at least 90 % of VDD, and the
fine range at code 0 is at least 50 % of its Cf = 0 value, at every corner and temperature.

| ring-node wiring cw | largest extra Cf that passes everywhere |
|---|---|
| 1.1 fF (this layout) | none: at ff 0 °C and Cf = 0, f falls from 629 to 529 MHz between codes 0 and 3, with a 64 % swing |
| 3 fF | about 0 at ff 0 °C (tt holds to about 10 fF) |
| 5 fF | about 10 fF (ff swing 88 %) |

The f node already carries an estimated 10–15 fF from the 48 foot fingers' drain junctions. When the ring node is
lighter than f, charge sharing into f sets the edge, not the bias current. This happens first at the fast-NMOS corners
when cold, while the supply current barely changes. The non-monotonic low codes at ff 0 °C in the 2 fF map
(`docs/bias_tuning_results.md`) are the same effect. The rule is roughly Cf ≤ ring-node C, which no layout of a
48-finger foot can meet with light ring nodes. Next: compare a switch-at-the-bottom stage and a current-fed ring in
schematic.
