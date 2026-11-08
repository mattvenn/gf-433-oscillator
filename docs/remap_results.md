# 433.92 MHz codes on the extracted core, with the level shifter on a0

**Problem.** The tuning map (`sim/results/2026-11-08/cfed/map.csv`) is schematic, and it reads about 1.3 % high
because it measures f at 100–200 ns, before vg settles. On the RC-extracted v3 core its 433.92 MHz codes give only
367–378 MHz (`docs/lsdiv_design.md`), and the level shifter on a0 pulls f down by another 1.0–1.8 %. Bring-up and
the procedure in `docs/tuning.md` need the real codes.

**Method.** `sim/lsdiv/remap.py`, driven by `sim/lsdiv/run_remap.sh` (`docs/handoff_remap.md`): the full constant-gm
reference with the 1 MΩ / 20 pF filter, the RC-extracted core (`layout/pex/ring_core_v3_w30chk_rc.spice`), and the
schematic level shifter + ÷4 with the drawn R1 / C1 on a0. DC operating point with the ring held, then 1.2 µs; f is
measured over 0.72–1.2 µs, after vg has settled. 27 °C, VDD 3.3 V, the 5 process corners. Step 1: codes 0–31 at
vctrl 1.65 V. Step 2: the 4 codes around 433.92 at vctrl 0, 1.0, 2.3 and 3.3 V. 240 points, 35 minutes on sim0
(16 parallel), no warnings; ÷4 exact and level-shifter duty 47–53 % at every point.
Data: `sim/lsdiv/results/remap.csv`, table `sim/lsdiv/results/remap.md`.

## Result
| corner | f at code 0 / 31, vctrl 1.65 V (MHz) | codes that reach 433.92 (vctrl for 433.92) | **recommended code** | vctrl there | Kvco there (MHz/V) | old schematic code |
|---|---|---|---|---|---|---|
| tt | 191 / 697 | 11 (2.49 V), 12 (1.97 V), 13 (1.15 V) | **12** | 1.97 V | 28 | 9 |
| ss | 172 / 643 | 13 (2.82 V), 14 (2.26 V), 15 (1.42 V) | **14** | 2.26 V | 21 | 11 |
| ff | 215 / 760 | 9 (2.22 V), 10 (1.74 V), 11 (0.89 V) | **10** | 1.74 V | 39 | 7 |
| sf | 186 / 706 | 11 (2.51 V), 12 (1.92 V) | **12** | 1.92 V | 26 | 9 |
| fs | 191 / 682 | 12 (2.19 V), 13 (1.68 V) | **13** | 1.68 V | 31 | 9 |

- **The codes moved up by 3–4 at every corner** against the schematic map. Most of it is the extracted core
  (about 0.87× the schematic's f); the level shifter adds about one more code's worth at the low end.
  Against the RC check without the level shifter (`docs/cfed_v3_check.md`: tt 12, ss 14–15, ff 10) the codes are
  the same or one lower, because that check picked the code nearest 433.92 at vctrl 1.65 V.
- **Recommended code:** the one whose vctrl for 433.92 sits nearest the middle of the steep part of the fine curve,
  1.7–2.3 V. Below about 1 V the fine leg is off and Kvco drops to a few MHz/V (ff code 11: 3 MHz/V at 0.89 V), so a
  code that needs vctrl < 1.2 V leaves little room to tune down.
- **Overlap:** every corner has at least two codes that reach 433.92, so there is no gap. sf and fs only just miss a
  third code (sf code 13 starts at 434.7 MHz, fs code 14 at 435.2 MHz at vctrl 0).
- **FSK step:** with Kvco 21–39 MHz/V at the recommended points, ±50 kHz needs ±1.3–2.4 mV of vctrl
  (`docs/tuning.md` assumed about ±1.8 mV).
- **Range at vctrl 1.65 V:** 172–760 MHz over the corners. Code 0 at vctrl 0 and code 31 at vctrl 3.3 V weren't run;
  `docs/cfed_v3_check.md` has them for the core alone.

## Limits
- The a0 load is the schematic level shifter. The extracted layout (`docs/lsdiv_layout.md`) pulls f a further
  0.5–0.6 % down (tt code 9: 370.97 against 373.04 MHz), about a third of a code, so the vctrl values above would
  rise by about 0.1–0.2 V. The recommended codes don't change.
- 27 °C only, VDD 3.3 V only, no mismatch. The GF silicon/sim factor isn't known yet (bench, 2026-11-09); the
  bring-up binary search over all 32 codes finds the real code whatever it is.
