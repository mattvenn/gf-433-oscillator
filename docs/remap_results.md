# 433.92 MHz codes on the extracted core, with the extracted level shifter on a0

**Problem.** The tuning map (`sim/results/2026-11-08/cfed/map.csv`) is schematic, and it reads about 1.3 % high because
it measures f at 100–200 ns, before vg settles. Bring-up and the procedure in `docs/tuning.md` need the codes of the
real layout. A first re-map (earlier the same day) used an RC netlist that double-counted the coupling C
(`docs/rc_extraction_fix.md`); its core ran about 13 % slow and its codes came out 3–4 too high. This page replaces it.

**Method.** `sim/lsdiv/remap.py`, driven by `sim/lsdiv/run_remap.sh` (`docs/handoff_remap.md`):
- the full constant-gm reference with the 1 MΩ / 20 pF filter (schematic: ppolyf_u_1k RF, ideal CF for step 1,
  nfet-cap CF for step 2; the two differ by 0.015 % in f);
- the RC-extracted core with the double count removed (`layout/pex/ring_core_v3_w30chk_rcx.spice`);
- the extracted level shifter + ÷4 on a0 (`layout/pex/lsdiv_c.spice`, R1 ppolyf_u_1k), with the 20 fF ck load and
  the standard-cell flip-flop.

DC operating point with the ring held, then 1.2 µs; f is measured over 0.72–1.2 µs, after vg has settled. 27 °C,
VDD 3.3 V, the 5 process corners. Step 1: codes 0–31 at vctrl 1.65 V. Step 2: the 4 codes around 433.92 at vctrl
0, 1.0, 2.3 and 3.3 V. 240 points, 34 minutes on sim0 (16 parallel), no warnings; ÷4 exact and level-shifter duty
45–55 % at every point. Data: `sim/lsdiv/results/remap.csv`, table `sim/lsdiv/results/remap.md`.

## Result
| corner | f at code 0 / 31, vctrl 1.65 V (MHz) | codes that reach 433.92 (vctrl for 433.92, f range vctrl 0–3.3 V) | **recommended code** | vctrl there | Kvco there (MHz/V) | schematic map code |
|---|---|---|---|---|---|---|
| tt | 214 / 779 | 8 (2.61 V, 383–465), 9 (2.12 V, 404–483), 10 (1.44 V, 424–501) | **9** | 2.12 V | 34 | 9 |
| ss | 193 / 718 | 10 (2.80 V, 392–451), 11 (2.25 V, 410–467), 12 (1.43 V, 428–483) | **11** | 2.25 V | 25 | 11 |
| ff | 241 / 851 | 6 (2.44 V, 371–485), 7 (2.00 V, 395–505), 8 (1.45 V, 418–525) | **7** | 2.00 V | 47 | 7 |
| sf | 208 / 790 | 8 (2.68 V, 386–460), 9 (2.16 V, 407–479), 10 (1.33 V, 428–498) | **9** | 2.16 V | 31 | 9 |
| fs | 214 / 762 | 9 (2.27 V, 394–480), 10 (1.75 V, 413–498), 11 (0.48 V, 433–515) | **10** | 1.75 V | 36 | 9 |

- **The codes are the schematic map's codes** at tt, ss, ff and sf, and one higher at fs. The layout (about −1 to
  −2 % in f) and the level shifter's load (about −1.6 %) are absorbed by the fine range: 433.92 sits at vctrl
  2.0–2.25 V instead of near 1.65 V.
- **Recommended code:** the one whose vctrl for 433.92 is nearest the middle of the steep part of the fine curve,
  1.7–2.3 V. Below about 1 V the fine leg is off and Kvco drops to a few MHz/V (fs code 11: 3 MHz/V at 0.48 V).
- **Overlap:** every corner has three codes that reach 433.92, so there is no gap.
- **FSK step:** with Kvco 25–47 MHz/V at the recommended points, ±50 kHz needs ±1.1–2.0 mV of vctrl
  (`docs/tuning.md` assumed about ±1.8 mV).
- **Range at vctrl 1.65 V:** 193–851 MHz over the corners (code 0 at vctrl 0 and code 31 at 3.3 V not run here).
- **Level-shifter block power:** 0.35–1.36 mW over all points (it scales with f).

## Limits
- 27 °C and VDD 3.3 V only; no mismatch. The reference is schematic (its layout is in progress).
- The GF silicon/sim factor isn't known yet (bench, 2026-11-09); the bring-up binary search over all 32 codes finds
  the real code whatever it is.
