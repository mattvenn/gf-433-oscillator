# RC extraction double-counted the coupling capacitance

**Problem.** Every RC-extracted result before 2026-11-08 evening put the v3 core at about 0.87× the schematic
frequency (`docs/cfed_v3_check.md`), and `docs/ring_layout_v3.md` put the loss down to the gate-poly resistance.
The C-only extraction of the same layout runs at about 0.98×. The level-shifter extraction (`docs/lsdiv_layout.md`)
showed the cause: in the RC netlist, a0's capacitance to VSS (2.61 fF) was exactly a0's *total* capacitance in the
C-only netlist, while the 1.99 fF of coupling to lg was also still there.

**What magic does.** In `rc` mode (`ext2sim` → `extresist` → `ext2spice extresist on`), every labelled net (the
ports) and every net that extresist splits into sub-nodes gets its whole lumped capacitance, coupling included, as a
capacitor to VSS, and ext2spice still writes the coupling capacitors to the other nets. So these nets carry their
coupling twice. Unlabelled internal nets are not affected (lsdiv lg, ls, q1 match the C-only netlist exactly).

| net (v3 core) | total C, C-only (fF) | total C, RC as extracted (fF) | of which to VSS: C-only / RC (fF) |
|---|---|---|---|
| a0 | 3.20 | 5.89 | 0.51 / 3.20 |
| a1 | 3.25 | 6.14 | 0.37 / 3.25 |
| vg | 53.6 | 75.1 | 32.1 / 53.6 |
| vbn | 56.1 | 99.7 | 12.5 / 56.1 |

The resistance itself can't explain an 11 % drop: about 100 Ω of gate poly with a few fF is under 1 ps, against a
2.3 ns period. Doubling the ring-node C (about 1 % of f per fF) does.

**Fix.** `layout/gen/rcfix.py`: for each port or split net N, scale its caps to VSS by (S − K) / S, where S is its C
to VSS and K its coupling to the other non-VSS nets. `pex_v3.sh rc` and `pex_lsdiv.sh rc` now run it and write
`<name>_rcx.spice`; with `--check` it compares every net's total C with the C-only netlist. On the core, all 19
corrected nets (its ports) match the C-only totals within 0.5 %; on lsdiv, a0, ck and VDD match exactly.
The sims now use `layout/pex/ring_core_v3_w30chk_rcx.spice` (`sim/lsdiv/lsdiv.py`, `remap.py`).

**Evidence.** The extracted core alone (full reference and filter, 27 °C, 3.3 V, vctrl 1.65 V), RC as extracted
against corrected:

| corner | code 0 (MHz) | code 9 (MHz) | code 31 (MHz) |
|---|---|---|---|
| tt | 192.9 → 218.1 (+13.1 %) | 377.2 → 425.7 (+12.9 %) | 704.2 → 793.2 (+12.6 %) |
| ss | 174.0 → 196.4 (+12.8 %) | 345.9 → 389.5 (+12.6 %) | 649.5 → 730.0 (+12.4 %) |
| ff | 217.4 → 246.4 (+13.3 %) | 415.9 → 470.4 (+13.1 %) | 768.6 → 867.5 (+12.9 %) |

At tt code 9 the corrected core gives 425.7 MHz against about 434 MHz for the schematic (`map.csv` window, which
reads about 1.3 % high): **the layout costs about 1–2 % of f, not 13 %.**

**What changes.**
- The "0.87×" factor (CLAUDE.md, STATUS, `docs/tuning.md`, `docs/cfed_v3_check.md`, `docs/remap_results.md`) is
  wrong; the RC rows of `docs/cfed_v3_check.md` and `docs/ring_layout_v3.md` carry the double count.
- The 433.92 codes from the first re-map (tt 12, ss 14, ff 10, sf 12, fs 13) used the inflated core; they are being
  re-run on the corrected core with the extracted level shifter (`docs/remap_results.md`).
- Relative results (DAC MC monotonicity and DNL, level-shifter Δf, duty, ÷4) are not affected in kind; the absolute
  frequencies are.

**Limits.** The mechanism is inferred from the netlists, not from magic's source; the check against the C-only
extraction is what the fix relies on. Not yet reported upstream.
