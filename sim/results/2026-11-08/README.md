# Results 2026-11-08 (docs/handoff_bias_and_tuning.md)

The full write-up is in docs/bias_tuning_results.md. Jobs 1 and 2 use cw = 2 fF per ring node. Job 3 and the
start-up check use cw = 10 fF, the extraction value from docs/ring_layout.md; the extracted R lowers f by a further
10–12 %.

- `winner_sets.txt`: the `--set` string of the chosen reference (`s1_nsn14p_mr4`).
- `job1/<case>.json`: Job 1 reference sweep, from `sim/pn/ref_sweep.py`.
  - Each file has the lnw search for zero tempco, the PVT spread, start-up, and rms FM / L from
    `sim/pn/bias_fm.py`.
  - Case names:
    - `s<k>`: W and L of MN1, MN2, MP1 and MP2 scaled by k;
    - `s1_nsn<k>`: MN1/MN2 as k × k series-parallel arrays of the 2/1 µm unit;
    - suffix `p`: PMOS mirror × k;
    - suffix `mr4`: master leg × 4.
  - `s14_ponly` and `s14_nonly` are tempco diagnostics. Their `bias_fm` vbp term predates the DC-start fix, so quote
    only their tempco and vbnf noise.
- `job2/isf/cgmq_<corner>_t<T>.json`: `isf.py cgmq --m 60` result.json. `job2/summary.md` has the ring-only table.
- `job2/bias_fm/cgmq_<corner>_t<T>.json`: `bias_fm.py --variant cgmq`, with total L and rms FM including the bias
  terms.
- `map_cw2f/` and `map_cw10f/`: `vco_bias.py map` for the winner at cw = 2 fF and 10 fF.
  - `map.csv` has every code × vctrl × PVT point.
  - `map_summary.json` has, per PVT point, the range, the codes for 433.92 MHz, the largest step against the
    smallest fine range, non-monotonic steps, and 310–620 MHz coverage.
- `ringstart_cw10f/ringstart.json`: code-0 start-up from the alternating start and 6 random states per corner and
  temperature, with the phase-based mode check.
