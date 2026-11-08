# cfed v3 check: extracted range and DAC mismatch (2026-11-08)

## Task 1: v3 at w = 1.2, RC extraction
- **Layout:** the generator at `wfu=0.30` gives the same magic script as `build/layout_v3_w30` (only the output path differs).
  DRC 0 (magic and KLayout), antenna 0, LVS matches uniquely (`build/check/ring_core_v3_w30_chk/`). Re-extracted as `layout/pex/ring_core_v3_w30chk_rc.spice`.
- **Sim:** `layout/gen/pex_check_v3.py`. Full schematic reference (lnw 5.023, rf 1 MΩ, cf 20 pF), no uic, so vbnf starts at DC. 27 °C, 3.3 V. Schematic at cw 3 fF (matches `map.csv` within 0.1 %).

| corner | code 0, vctrl 0: sch / RC MHz | 433.92 code at 1.65: sch / RC | code 31, vctrl 3.3: sch / RC | RC/sch |
|---|---|---|---|---|
| tt | 205.4 / 177.5 | 9: 434.1 / 377.8 | 846.5 / 740.7 | 0.864–0.875 |
| ss | 190.5 / 164.8 | 11: 434.6 / 379.4 | 771.7 / 676.5 | 0.865–0.877 |
| ff | 224.1 / 194.1 | 7: 434.1 / 377.2 | 934.5 / 816.4 | 0.866–0.874 |

**Pass:**
- worst fmax is 676.5 MHz (ss), against ≥ 620;
- worst fmin is 194.1 MHz (ff), against ≤ 310;
- 433.92 is reachable at every corner, but the code moves up about 3. In RC, the codes at vctrl 0–3.3 are tt 12 (418–485, 430.1 at 1.65), ss 14 (419–466) and ss 15 (433.8–480), and ff 10 (417–509, 436.1 at 1.65).

## Task 2: DAC mismatch Monte Carlo (`sim/mc/`)
- **Switching it on:** `.param sw_stat_mismatch=1` after `design.ngspice`, global off, plus `.options seed=N` with one process per sample.
- **Per-instance proof** (`mm_proof.sh`): 4 identical units at one seed gave 1.584–1.602 µA. A second seed gave different values. With mismatch off, all four were 1.6018 µA.
- **m is ignored:** the models size σ by one instance's W·L, so every DAC `m` is expanded into unit instances.
- **Circuit:** vg held at 1.894 / 1.680 / 2.093 V (tt/ss/ff), with vbnf an ideal source at the reference's nominal DC value.
  - The full reference needed gmin stepping on every op, which was too slow.
  - Its mismatch only scales the coarse legs, so DNL is not affected.
- **Points:** codes 0–31 at 1.65 V, plus 0 and 3.3 V at codes 0, 7, 8, 15, 16, 23, 24 and 31.

| corner, N | DNL 7→8 mean / σ / worst | 15→16 | 23→24 | non-mono | fine < 1.3×step | worst fine/step |
|---|---|---|---|---|---|---|
| tt, 500 | 0.000 / 0.027 / +0.093 | +0.002 / 0.039 / +0.107 | 0.000 / 0.027 / +0.094 | 0 % | 0 % | 3.82 (nominal 4.22) |
| ss, 200 | −0.001 / 0.025 / −0.080 | +0.001 / 0.037 / +0.086 | −0.001 / 0.025 / −0.080 | 0 % | 0 % | 3.12 (3.40) |
| ff, 200 | +0.002 / 0.028 / +0.084 | +0.004 / 0.040 / +0.132 | +0.002 / 0.028 / +0.084 | 0 % | 0 % | 4.58 (5.19) |

All worst cases are at 15→16. All samples are distinct.

**Transients:** I ran the ring at codes 15/16 for tt, with the worst 3 seeds plus nominal. The same seed gives the same draws. f follows the current at 4.2 MHz/µA for both the step and the fine range.
- The worst seed's step is +10.8 % in f, against +10.9 % in I.
- Its f fine/step is 3.65 (nominal 4.03).
- Fine overlap is 51 MHz.

**Verdict:** mismatch is not a risk. The worst DNL is 13 %, every sample is monotonic, and fine/step stays ≥ 3.1.

Wall time: about 12 min (13:01–13:12).
