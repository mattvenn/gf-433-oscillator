# Results 2026-11-08 (docs/handoff_bias_and_tuning.md), interim

All of these use the schematic wiring estimate **cw = 2 fF per node**. The ring-core extraction
(docs/ring_layout.md) gives about 10 fF per node, and absolute frequencies are about 41 % lower with the extracted
R and C. Job 3 is being rerun with cw = 10 fF. The full write-up will go in docs/bias_tuning_results.md.

- `job1/<case>.json`: Job 1 reference sweep, from `sim/pn/ref_sweep.py` (lnw search for zero tempco, PVT spread,
  start-up, and rms FM / L from `sim/pn/bias_fm.py`). `s<k>` = W and L of MN1, MN2, MP1, MP2 scaled by k.
  `s1_nsn<k>` = MN1/MN2 as k x k series-parallel arrays of the 2/1 um unit, `p` = PMOS mirror x k, `mr4` = master leg x4.
  `s14_ponly` / `s14_nonly` are tempco diagnostics; their `bias_fm` vbp term predates the DC-start fix (see `vbn`), so
  quote only their tempco and vbnf noise.
- `map_cw2f/`: tuning map of the chosen sizing (`s1_nsn14p_mr4`, lnw = 3.665 um), every code x vctrl 0/1.65/3.3 V at
  5 corners x 0/27/70 C x VDD 3.15/3.3/3.45 V (`vco_bias.py map`, cw = 2 fF). `map_summary.json` has, per PVT point,
  the range, the codes for 433.92 MHz, the largest coarse step against the smallest fine range, non-monotonic steps,
  and 310-620 MHz coverage.
