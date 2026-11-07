# Phase-noise sweep of the candidate VCOs (ISF method)

- Date: 2026-11-07
- Image: `iic-osic-tools:2026.09`, ngspice-47, PDK gf180mcuD
- Method: `sim/pn/isf.py` (Hajimiri & Lee ISF), `M=60` phases, 3 variants x 5 corners at 27 C, run with
  `M=60 PAR=7 JOBS=4 sim/pn/run_all.sh`
- Raw per-case results: `sim/pn/results/2026-11-07/<case>/{result.json,isf.csv}`, table in `summary.md`

## Tool-version check (step 2)

| case | expected | 2026.09 / ngspice-47 |
|---|---|---|
| `typical_n5_t27_v330` | 1949.9 MHz | 1949.9 MHz, 2.46 mW |
| `typical_n9_t27_v330` | 1082.3 MHz, 2.46 mW | 1082.3 MHz, 2.46 mW |

Pass: identical to the 2026.05 design numbers.

## Results

| variant | corner | f0 MHz | P mW | L(10k) | L(100k) | L(1M) | L(10M) dBc/Hz | FOM@1M | Kvdd MHz/V | Kbias MHz/V | dominant @1M |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cgm | ff | 395.9 | 1.45 | -22.8 | -52.2 | -79.9 | -103.4 | -130.3 | -227.5 | -1600.3 | bias |
| cgm | fs | 464.0 | 1.37 | -23.5 | -52.9 | -80.7 | -104.2 | -132.6 | -189.7 | -1420.2 | bias |
| cgm | sf | 377.3 | 1.38 | -25.2 | -54.7 | -82.5 | -106.2 | -132.7 | -120.7 | -1066.7 | bias |
| cgm | ss | 405.3 | 1.30 | -26.4 | -55.8 | -83.7 | -107.5 | -134.8 | -75.3 | -906.2 | bias |
| cgm | typical | 416.5 | 1.38 | -24.2 | -53.6 | -81.4 | -105.1 | -132.4 | -158.2 | -1257.6 | bias |
| diff | ff | 597.1 | 2.73 | -47.5 | -72.7 | -93.9 | -114.1 | -145.1 | -71.6 | 645.3 | bias |
| diff | fs | 511.9 | 2.19 | -48.9 | -74.4 | -95.8 | -116.0 | -146.6 | -30.4 | 526.7 | bias |
| diff | sf | 403.8 | 1.98 | -48.4 | -72.5 | -93.3 | -113.4 | -142.5 | -96.3 | 687.3 | bias |
| diff | ss | 344.3 | 1.59 | -49.7 | -73.9 | -94.8 | -114.9 | -143.5 | -69.1 | 588.1 | bias |
| diff | typical | 461.6 | 2.10 | -48.5 | -73.2 | -94.2 | -114.4 | -144.3 | -71.9 | 626.3 | bias |
| se | ff | 578.8 | 1.20 | -45.2 | -70.0 | -91.2 | -111.3 | -145.6 | -93.1 | 891.2 | bias |
| se | fs | 487.9 | 0.94 | -46.1 | -71.0 | -92.2 | -112.3 | -146.2 | -64.5 | 801.7 | bias |
| se | sf | 379.7 | 0.86 | -46.5 | -71.5 | -92.6 | -112.8 | -144.9 | -57.1 | 757.1 | bias |
| se | ss | 306.1 | 0.66 | -47.6 | -72.5 | -93.6 | -113.8 | -145.2 | -40.6 | 680.1 | bias |
| se | typical | 431.1 | 0.90 | -46.3 | -71.1 | -92.3 | -112.4 | -145.4 | -63.2 | 791.4 | bias |

Kbias is df/dvctrl for se/diff and df/dvbn for cgm. The operating points are fixed (code and vctrl), so f0
moves with the corner; nothing was retuned to 433.92 MHz.

Device-only phase noise (head + foot terms, without the bias and vdd terms), from the same `result.json` files:

| variant | corner | L(10k) | L(100k) | L(1M) dBc/Hz | FOM@1M |
|---|---|---|---|---|---|
| se | typical | -47.4 | -76.4 | -102.9 | -156.0 |
| diff | typical | -49.7 | -78.9 | -106.0 | -156.1 |
| cgm | typical | -45.4 | -73.9 | -98.6 | -149.6 |

Over all corners the device-only FOM@1M is -154.9 to -156.9 for se, -155.1 to -156.7 for diff and
-147.5 to -151.9 for cgm.

## Checks (step 5)

- All 15 `result.json` exist. No case failed.
- ISF smoothness: no phase in any `isf.csv` is above 10x both neighbours (ignoring points below 5 % of the peak).
- FOM@1M range -145 ... -170: **out of range** for cgm (all corners, -130 to -135), diff sf/ss/typical
  (-142.5 to -144.3) and se sf (-144.9). Each one is dominated by the bias term at 1 MHz. For se/diff that term
  comes from the assumed 100 kOhm vctrl resistor. For cgm it is the simulated noise of the const-gm reference
  on vbn, times |K_vbn| of about 1.3 GHz/V. Device-only FOMs are all within range (see above).
- ISF |dc| / rms (all phases, the quantity that sets flicker upconversion):

  | variant | ff | fs | sf | ss | typical |
  |---|---|---|---|---|---|
  | se | 0.282 | 0.300 | 0.289 | 0.322 | **0.306** |
  | diff | 0.188 | 0.172 | 0.253 | 0.256 | **0.221** |
  | cgm | 0.088 | 0.140 | 0.079 | 0.029 | **0.029** |

  diff < se at every corner, as expected.
- K_vdd: se at tt measures -63 MHz/V (427.9 / 434.2 MHz at 3.35 / 3.25 V; the alter does take effect, since supply
  current changes by ±2.3 %). This matches the corrected expectation of about -50 MHz/V in the brief (commit d7dcda1;
  the first version said -1300). Because K_vdd is small, the vdd term is never dominant.

## Run time

Full sweep: 18:17:34 to 18:56:34 CET, **39.0 min** (estimate was 2-4 h). Smoke test (se tt, M=8, 8 jobs): 70 s.

## Fixes to `sim/pn/isf.py`

1. **Stage C failed under ngspice-47.** `.noise` needs an AC value on the input source (`doAnalyses: ac input
   not found`). Added `ac 1` to `vd` (head/foot decks) and `vdd` (vbn deck). This does not change the output noise.
2. **The ISF was quantized.** `meas ... WHEN` results and `echo $&x` keep only about 6-7 digits, so absolute
   edge times near 1.3e-7 s resolved to 1 ps (and 0.1 ps after a first attempt). The injected shifts are 1-15 ps.
   Edges are now measured as `TRIG AT=tw TARG ...` intervals from the window start `tw`, which gives about 1 fs.
3. **The head/foot split was biased.** The node direction was taken from v(td-1p) vs v(td+1p), across the
   injected pulse, which always pushes the node up. So every phase was classed as "rising" (head), and the foot got
   rms² = 0. Both samples are now taken before the pulse (td-3p and td), and the `isf.csv` columns are renamed
   `v_m3ps,v_at_td`.

## Summary

At tt, diff has the lowest total phase noise at all three offsets: -48.5 / -73.2 / -94.2 dBc/Hz at
10 k / 100 k / 1 MHz, against -46.3 / -71.1 / -92.3 for se and -24.2 / -53.6 / -81.4 for cgm. It also burns
2.3x the power of se, so per watt (FOM) se and diff are within about 1 dB.
At 10 kHz the se and diff totals are set mostly by flicker noise of the foot (NMOS) devices,
upconverted through the ISF dc term, with the bias term about 5 dB below. From 100 kHz upward the bias line
dominates. That term uses an assumed 100 kOhm vctrl resistor (thermal noise only) for se/diff, so it scales
with whatever the real loop filter is. Without it, the device-only L(1 MHz) would be -102.9 (se) and -106.0 dBc/Hz (diff).
cgm is dominated at every offset by the noise of its own const-gm vbn reference, about 15-20 dB above its device noise.
The vdd term uses an assumed 100 nV/√Hz white supply and is 10-35 dB below the total everywhere.
