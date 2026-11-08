# a0 level shifter and ÷4 prescaler (schematic)

Code: `sim/lsdiv/` (`lsdiv.py`, `run_all.sh`, `summary.py`). Tables: `sim/lsdiv/results/summary.md`.
Ring: the extracted v3 core (`ring_core_v3_w30chk_rc.spice`) with the full reference, lnw 5.023, ka 16,
wfu = wff = 0.30 and the 1 MΩ / 20 pF filter. Start: DC operating point with the ring nodes held, then 1.2 µs;
everything is measured over 0.72–1.2 µs.

## Chosen: AC-coupled inverter with a duty-correcting bias
```
a0 ─┤├ Cc 2 fF ─┬─ lg ─INV1─ lo1 ─INV2─ lo2 ─INV3─┬─ ls (0–3.3 V) ─► TSPC ÷2 ─ q1 ─► TSPC ÷2 ─ q2 ─INV─ ck ─► DFF CLK + 20 fF
                │    0.22/0.5     0.6/1.5   1.2/3 │
                └─ MR: pfet 0.22/2, gate VSS ─ lf ─┴─ R1 500 kΩ;  C1 1 pF lf → VSS
```
Sizes are Wn/Wp in µm, L 0.28 µm. TSPC: 9 FETs plus a Q inverter. Stage 1 is 1.0/2.0 and stage 2 is 0.6/1.2,
with a 0.6/1.5 Q inverter in each. The buffer is 1.0/2.5.

- **Why it works.** INV1–3 invert three times, so feeding the low-passed output back to lg is negative DC
  feedback. The mean of ls settles at INV1's trip point, so the duty stays near 50 % at every code. The loop also
  absorbs the chain's own skew at 700 MHz and up.
- **Why it tracks vg.** Cc AC-couples a0, so vg drops out entirely.
- **Why it is stable.** MR × C(lg) is a few ns, against 0.5 µs for R1·C1. A first version with MR at L = 20 µm put
  the two poles too close; it limit-cycled and dropped pulses.

**Runner-up (a):** the same chain biased by a replica inverter. Duty is 58.7–60.8 % at code 31 (tt, ss), which fails
the 50 ± 10 % limit, and LS power is up to 0.85 mW.

**(b) Replica ring stage (VDD/vg) into a PMOS-input cross-coupled latch: rejected.** It never flips at code 0, where
VDD − vg ≈ 1.2 V. It costs 3.5–7 % of f, and it draws current from vg, which `ring_layout_v3.md` rules out.

## Results
All 25 points pass. Main: 5 corners at 27 °C, VDD 3.3 V, codes 0 / 433.92 / 31, vctrl 1.65 V. Robustness: ss and
ff at 0 and 70 °C. VDD 3.15 V: ff 70 °C code 0 (smallest a0 swing) and ss 0 °C code 31.
- **f shift:** −1.00 to −1.20 % (about 1.1 fF equivalent).
- **LS:** full rail, duty 47.1–53.5 %, edges 71–127 ps.
- **÷4:** ratio exactly 4.0000, duty 48.7–49.8 %.
- **Power:** LS 0.12–0.38 mW, ÷4 + buffer 0.06–0.29 mW. The ring is about 0.45 mW.

Δf is measured in the same window with and without the block. The absolute f reads about 0.7 % high against
fully settled (`cfed_startup_results.md`). **With the RC-extracted core, the map's 433.92 codes give 367–378 MHz**
(sch 434), so the real 433.92 code is a few codes higher; that is a ring finding, not an LS one.

| corner | T °C | VDD | code | f a0 no block MHz | f a0 with block MHz | Δf % | a0 swing V | LS out V | LS duty % | LS tr / tf ps | ÷4 f MHz | f a0 / f ÷4 | ÷4 duty % | P LS / ÷4+buf mW | warn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tt | 27 | 3.30 | 0 | 192.88 | 190.64 | -1.16 | 2.04–3.40 | -0.02–3.33 | 48.5 | 99 / 88 | 47.66 | 4.0000 | 49.7 | 0.161 / 0.072 | - |
| tt | 27 | 3.30 | 9 | 377.19 | 373.05 | -1.10 | 1.82–3.41 | -0.03–3.33 | 49.4 | 98 / 85 | 93.26 | 4.0000 | 49.4 | 0.210 / 0.142 | - |
| tt | 27 | 3.30 | 31 | 704.20 | 696.85 | -1.04 | 1.43–3.41 | -0.03–3.34 | 51.0 | 89 / 82 | 174.21 | 4.0000 | 48.9 | 0.296 / 0.265 | - |
| ss | 27 | 3.30 | 0 | 174.05 | 172.14 | -1.09 | 1.89–3.41 | -0.03–3.33 | 50.0 | 104 / 107 | 43.03 | 4.0000 | 49.7 | 0.117 / 0.066 | - |
| ss | 27 | 3.30 | 11 | 378.95 | 375.00 | -1.04 | 1.59–3.42 | -0.03–3.34 | 51.3 | 104 / 103 | 93.75 | 4.0000 | 49.3 | 0.170 / 0.142 | - |
| ss | 27 | 3.30 | 31 | 649.48 | 642.97 | -1.00 | 1.20–3.42 | -0.04–3.35 | 52.9 | 96 / 100 | 160.74 | 4.0000 | 48.8 | 0.241 / 0.244 | - |
| ff | 27 | 3.30 | 0 | 217.42 | 214.72 | -1.24 | 2.19–3.39 | -0.01–3.32 | 47.2 | 90 / 90 | 53.68 | 4.0000 | 49.7 | 0.229 / 0.083 | - |
| ff | 27 | 3.30 | 7 | 376.44 | 372.06 | -1.16 | 2.03–3.39 | -0.01–3.32 | 47.7 | 92 / 83 | 93.01 | 4.0000 | 49.5 | 0.271 / 0.143 | - |
| ff | 27 | 3.30 | 31 | 768.58 | 760.23 | -1.09 | 1.65–3.39 | -0.02–3.33 | 49.1 | 86 / 74 | 190.06 | 4.0000 | 49.0 | 0.377 / 0.291 | - |
| sf | 27 | 3.30 | 0 | 188.16 | 185.80 | -1.26 | 2.01–3.40 | -0.01–3.33 | 49.7 | 105 / 91 | 46.45 | 4.0000 | 49.8 | 0.165 / 0.071 | - |
| sf | 27 | 3.30 | 9 | 377.74 | 373.40 | -1.15 | 1.80–3.41 | -0.02–3.33 | 50.5 | 85 / 91 | 93.35 | 4.0000 | 49.5 | 0.216 / 0.143 | - |
| sf | 27 | 3.30 | 31 | 713.90 | 706.22 | -1.08 | 1.41–3.41 | -0.03–3.34 | 52.1 | 82 / 86 | 176.55 | 4.0000 | 49.1 | 0.305 / 0.269 | - |
| fs | 27 | 3.30 | 0 | 193.20 | 191.08 | -1.10 | 2.04–3.39 | -0.02–3.32 | 48.0 | 103 / 87 | 47.77 | 4.0000 | 49.6 | 0.158 / 0.073 | - |
| fs | 27 | 3.30 | 9 | 370.66 | 366.74 | -1.06 | 1.82–3.40 | -0.03–3.33 | 48.7 | 98 / 86 | 91.68 | 4.0000 | 49.3 | 0.204 / 0.140 | - |
| fs | 27 | 3.30 | 31 | 688.51 | 681.51 | -1.02 | 1.44–3.40 | -0.03–3.34 | 50.1 | 88 / 88 | 170.38 | 4.0000 | 48.7 | 0.286 / 0.259 | - |
| ss | 0 | 3.30 | 0 | 170.71 | 168.84 | -1.10 | 1.89–3.41 | -0.03–3.34 | 50.1 | 97 / 95 | 42.21 | 4.0000 | 49.7 | 0.116 / 0.063 | - |
| ss | 0 | 3.30 | 31 | 646.61 | 640.10 | -1.01 | 1.24–3.42 | -0.04–3.35 | 52.9 | 101 / 99 | 160.03 | 4.0000 | 48.9 | 0.239 / 0.240 | - |
| ss | 70 | 3.30 | 0 | 174.88 | 172.97 | -1.09 | 1.90–3.41 | -0.02–3.33 | 49.8 | 127 / 125 | 43.24 | 4.0000 | 49.6 | 0.118 / 0.066 | - |
| ss | 70 | 3.30 | 31 | 638.98 | 632.65 | -0.99 | 1.16–3.41 | -0.04–3.34 | 52.9 | 112 / 116 | 158.16 | 4.0000 | 48.7 | 0.241 / 0.243 | - |
| ff | 0 | 3.30 | 0 | 215.39 | 212.68 | -1.26 | 2.18–3.39 | -0.01–3.32 | 47.3 | 88 / 79 | 53.17 | 4.0000 | 49.7 | 0.227 / 0.081 | - |
| ff | 0 | 3.30 | 31 | 767.95 | 759.52 | -1.10 | 1.67–3.40 | -0.02–3.33 | 49.2 | 71 / 73 | 189.88 | 4.0000 | 49.0 | 0.376 / 0.288 | - |
| ff | 70 | 3.30 | 0 | 216.45 | 213.80 | -1.22 | 2.21–3.38 | -0.01–3.31 | 47.1 | 107 / 90 | 53.45 | 4.0000 | 49.7 | 0.233 / 0.084 | - |
| ff | 70 | 3.30 | 31 | 753.47 | 745.38 | -1.07 | 1.63–3.38 | -0.02–3.32 | 49.0 | 90 / 87 | 186.34 | 4.0000 | 48.9 | 0.378 / 0.290 | - |
| ff | 70 | 3.15 | 0 | 217.44 | 214.82 | -1.20 | 2.07–3.23 | -0.01–3.16 | 47.3 | 111 / 91 | 53.71 | 4.0000 | 49.7 | 0.196 / 0.076 | - |
| ss | 0 | 3.15 | 31 | 647.43 | 640.94 | -1.00 | 1.10–3.27 | -0.04–3.20 | 53.5 | 98 / 96 | 160.24 | 4.0000 | 48.8 | 0.208 / 0.219 | - |

## ÷4 alone
An ideal clock, through the LS output inverter, swept from 10 MHz to 4 GHz (`lsdiv.py div`, `sim/lsdiv/results/div.json`).
- **Upper limit:** ÷4 is exact up to 4 GHz at tt, ff, sf and fs, and up to 3.5 GHz at ss (27 and 70 °C). That is
  more than 4× the ring's maximum.
- **Lower limit:** at sf, ÷4 is wrong at 10 and 50 MHz input (spurious edges) and right from 150 MHz up. Every
  other corner works down to 10 MHz. TSPC stores the state dynamically, on node capacitance, so it fails when the
  clock is too slow; sf (slow nfet, fast pfet) leaks the stored node fastest. The ring's minimum is 169 MHz, so it
  never runs this slowly, but it sets a floor: **don't clock this ÷4 from anything slower than about 150 MHz.**

## Drawn passives (schematic, 2026-11-08)
The results above use an ideal R1 and C1. The drawn devices are R1 = hi-res poly, 1 × 159 µm, and
C1 = an nfet_03v3 gate cap, 16 × 16 µm (about 1 pF; gate on lf, which sits near 1.5 V, so well into inversion).
With them, at tt 27 °C code 9: f(a0) 373.04 MHz (373.05 before), LS duty 49.5 % (49.4), ÷4 exact,
LS power 0.236 mW (0.210). R1 was sized for 3 kΩ/sq (500 kΩ); the run is 1 kΩ/sq, so as drawn it is about
164 kΩ (τ about 0.16 µs, still about 70 ring periods): the schematic now uses `ppolyf_u_1k` at the drawn length,
and the extracted block behaves the same with it (`docs/lsdiv_layout.md`). Schematic: `xschem/lsdiv.sch` (`docs/schematics.md`), generated from `lsdiv.py block()`.

## For layout
- **a0 tap:** put Cc at the a0 M2 edge tap. Cc is a metal-finger cap (M2–M3 fringe) of about 2 fF; MIM is far too
  big. The block costs about 1.1 %, so the 2 fF budget leaves about 0.9 fF, roughly 9 µm of M2 at about
  0.1 fF/µm. Run any long route on the lg side, or better after INV1.
- **lg:** this is a MΩ node. Keep it short and away from ls and ck. Its own C only cuts the swing; 0.4 fF is
  modelled.
- **Passives:** Cc, R1 and C1 are ideal in the sim. R1 is hi-res poly, about 164 squares (164 kΩ at the run's 1 kΩ/sq) and C1 is a 1 pF
  nfet_03v3 cap (about 250 µm²).
- **Supply:** give LS + ÷4 its own VDD/VSS branch, not shared with the ring rails, plus about 10 pF of MOS decap at
  the block. The charge per edge is about 0.1 pC, so the ripple is about 10 mV.
- **Device count:** 31 FETs (LS 7, two TSPCs 11 each, buffer 2) plus Cc, R1 and C1. The DFF is
  `gf180mcu_fd_sc_mcu7t5v0__dffq_1`, with 5 V devices run at 3.3 V.


Wall time: about 65 min (15:05–16:10). Final sims: main 13.9 min, robustness 7.7 min, VDD 2.6 min at 8 parallel; tuning about 25 min; ÷4 sweep 35 s.
