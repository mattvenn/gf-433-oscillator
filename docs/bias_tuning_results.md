# Bias reference and tuning results (handoff_bias_and_tuning.md)

- **Date:** 2026-11-07 / 08
- **Image:** IIC-OSIC-TOOLS 2026.09
- **Simulator:** ngspice-47, PDK gf180mcuD
- **CPU budget:** 20 CPUs on a 30-CPU host
- **Raw results:** `sim/results/2026-11-08/` (see its README)

> **Wiring capacitance.** Jobs 1 and 2 use the schematic estimate **cw = 2 fF per ring node**, so their absolute
> frequencies are high. The ring-core extraction (docs/ring_layout.md) gives about 10 fF per node. Job 3 was
> therefore run with `--set cw=10e-15`. **The extracted wiring R costs a further 10–12 % of frequency on top of the
> 10 fF numbers here**: with R and C, f is about 41 % below the schematic (code 31 at vctrl 1.65 V is 402 MHz at tt).
> The phase-noise and FM results of Jobs 1 and 2 are relative quantities and carry over approximately, but their f0
> values do not.

## Summary

1. **Job 1:** plain scaling of the reference (s = 1…14) does not meet the brief.
   - At s ≥ 4, no lnw nulls the tempco: it stays at +1200 to +1440 ppm/°C.
   - At s = 2, the FM is 43 kHz.
   - The best qualifying design scales the reference differently. MN1/MN2 become 14 × 14 series-parallel arrays of
     the 2/1 µm unit, so W/L is unchanged and the ring-foot tracking is kept. The PMOS mirror becomes 56/14 µm, the
     master leg is ×4 (mr = 4), and lnw = 3.665 µm.
   - It gives **rms FM 13.3 kHz (1–10 kHz)**, tempco +1 ppm/°C and start-up OK.
   - Area: 8683 µm² in total, of which 4624 is the 20 pF capacitor.
   - Ring power is 3.2 mW, against 1.9 mW without mr = 4.
2. **Job 2** (`cgmq`, code 5, cw = 2 fF):
   - rms FM over 1–10 kHz is 9–15 kHz at tt/ss/sf, and 16–30 kHz at ff/fs (worst at ff, 0 °C).
   - The term that sets it is everywhere the ring's own foot-device flicker noise (`dev_foot`), not the bias.
3. **Job 3** (cw = 10 fF):
   - **The 310–620 MHz coverage target is not met at any of the 45 PVT points.**
   - The bottom of the band is reached everywhere: fmin is 159–213 MHz.
   - The top is not: fmax is 442–549 MHz, so 71–178 MHz is missing, and more once R is included.
   - The code span (fmax/fmin ≥ 2.4) is wider than the ×2 needed. The range sits too low, so this is not a lack of
     coarse bits.
   - Fine ≥ 1.3 × the largest step holds at 18 of 45 points.
   - There are no non-monotonic steps.
4. **Ring start-up at code 0** (cw = 10 fF): **105 of 105 runs oscillate in the fundamental mode.** That is
   5 corners × 0/27/70 °C, each from the alternating start and 6 random initial states.

## Job 1: reference sizing for bias FM

**Method.**
- `sim/pn/ref_sweep.py --s S` scales W and L of MN1, MN2, MP1 and MP2 by s.
- It then searches lnw (lnp = 100 µm, rideal = 0) for zero tempco at tt:
  - the tempco is the least-squares slope of f over 0/27/70 °C at code 10, vctrl 1.65 V, divided by f(27 °C);
  - the search steps down from 4.5 µm in 0.5 µm steps, then up to 12 µm, and finishes with regula falsi to
    < 3 ppm/°C;
  - if no zero exists, it matches Iref = 49 µA instead.
- It runs `vco_bias.py pvt`: 5 corners × 0/27/70 °C × VDD 3.15/3.3/3.45 V, at code 10, vctrl 1.65 V.
- It checks start-up with `vco_bias.py startup`: VDD ramp 0 → 3.3 V in 10 µs at ss/ff × 0/70 °C; vbn and vbnf
  must be within 1 % of the DC operating point at 200 µs.
- It then runs `sim/pn/bias_fm.py`:
  - a dense `.noise` (50 points/decade) of vbnf with rf = 1 MΩ and cf = 20 pF;
  - a `.noise` of vbp with vbnf held at its DC value, so this is vbp's own noise;
  - K_vbn and K_vbp measured with a stage-A run of the new sizing;
  - the stored cgm device and vdd terms (`cgm_typical_t27/result.json`), interpolated as power laws;
  - S_f = 2·f²·10^(L/10), integrated over 1–10 kHz and 1–100 kHz.
- The `nsn`, `p` and `mr` rows were added because the plain s sweep didn't qualify. They are explained in the
  conclusions.
- All of Job 1 is at tt 27 °C, code 10, cw = 2 fF.

| case | extra --set | lnw µm | tempco ppm/°C | Iref µA | PVT f MHz (spread) | start-up | P mW | K_vbn MHz/V | FM 1–10k kHz | [vbnf / vbp / foot] | FM 1–100k kHz | L 10k / 100k / 1M dBc/Hz | area FETs / total µm² |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| s1 | – | 3.071 | +1 (null) | 49.0 | 477–611 (25 %) | OK | 1.79 | -1093 | 110.4 | 109.4 / 9.7 / 10.5 | 118.6 | -28.8 / -70.0 / -95.3 | 24 / 5172 |
| s2 | – | 0.771 | +1 (null) | 91.0 | 607–847 (33 %) | OK | 2.67 | -761 | 42.6 | 40.3 / 8.9 / 10.5 | 48.1 | -36.5 / -71.1 / -95.4 | 78 / 5222 |
| s4 | – | 2.595 | +1226 | 48.9 | 407–596 (38 %) | OK | 1.69 | -1143 | 29.0 | 25.3 / 9.2 / 10.5 | 34.9 | -39.1 / -71.1 / -95.3 | 294 / 5441 |
| s7 | – | 2.591 | +1365 | 48.9 | 402–599 (39 %) | OK | 1.69 | -1148 | 20.1 | 14.3 / 9.1 / 10.5 | 26.8 | -41.3 / -71.2 / -95.3 | 888 / 6035 |
| s10 | – | 2.600 | +1411 | 48.9 | 401–600 (40 %) | OK | 1.69 | -1148 | 17.4 | 10.2 / 9.1 / 10.5 | 24.6 | -41.9 / -71.2 / -95.3 | 1806 / 6953 |
| s14 | – | 2.576 | +1439 | 48.9 | 398–599 (40 %) | OK | 1.68 | -1148 | 16.1 | 7.7 / 9.2 / 10.5 | 23.5 | -42.3 / -71.2 / -95.3 | 3534 / 8681 |
| s1_nsn4 | nsn=4 | 3.500 | +0 (null) | 45.6 | 473–623 (27 %) | OK | 1.78 | -1081 | 48.4 | 46.1 / 9.9 / 10.5 | 53.6 | -36.0 / -70.9 / -95.3 | 174 / 5323 |
| s1_nsn8 | nsn=8 | 3.758 | +1 (null) | 43.8 | 467–619 (28 %) | OK | 1.76 | -1094 | 44.3 | 41.9 / 9.7 / 10.5 | 49.5 | -36.7 / -70.9 / -95.3 | 654 / 5804 |
| s1_nsn14 | nsn=14 | 3.819 | +1 (null) | 43.7 | 470–623 (28 %) | OK | 1.76 | -1085 | 43.2 | 40.7 / 9.8 / 10.5 | 48.3 | -36.9 / -70.9 / -95.3 | 1974 / 7124 |
| s1_nsn8p | nsn=8 wpm=32 lpm=8 | 3.149 | +1 (null) | 50.1 | 512–665 (26 %) | OK | 1.93 | -1029 | 18.7 | 11.5 / 10.2 / 10.5 | 26.0 | -41.5 / -70.9 / -95.2 | 1158 / 6306 |
| s1_nsn10p | nsn=10 wpm=40 lpm=10 | 3.182 | +2 (null) | 49.9 | 513–666 (26 %) | OK | 1.93 | -1024 | 17.6 | 9.3 / 10.4 / 10.5 | 25.1 | -41.7 / -70.9 / -95.2 | 1806 / 6954 |
| s1_nsn14p | nsn=14 wpm=56 lpm=14 | 3.206 | +2 (null) | 49.9 | 515–669 (26 %) | OK | 1.93 | -1025 | 16.5 | 7.2 / 10.3 / 10.5 | 24.2 | -42.0 / -70.9 / -95.2 | 3534 / 8683 |
| s1_nsn20p | nsn=20 wpm=80 lpm=20 | 3.202 | +2 (null) | 50.2 | 519–672 (26 %) | OK | 1.95 | -1018 | 15.9 | 5.8 / 10.2 / 10.5 | 23.7 | -42.2 / -70.9 / -95.2 | 7206 / 12355 |
| **s1_nsn14p_mr4** | nsn=14 wpm=56 lpm=14 mr=4 | 3.665 | +1 (null) | 44.7 | 433–617 (35 %) | OK | 3.20 | -968 | **13.3** | 6.7 / 4.0 / 10.5 | 19.8 | -43.8 / -72.3 / -95.7 | 3534 / 8683 |

Notes on the table:
- **Columns:**
  - **FM components** combine in quadrature with dev_head (1.8 kHz) and vdd (1.5 kHz), which are not shown.
  - **PVT spread** is (fmax − fmin)/f_typ over the 45 points.
  - **Area** counts FET W·L·m (× nsn² for the arrays), the bias resistor, rf, and 4624 µm² for the 68 × 68 µm
    cf.
- **s2:** lnw lands at 0.77 µm, which doubles Iref to 91 µA and P to 2.7 mW.
- **Diagnostics in the raw files:** `s14_ponly` and `s14_nonly` are tempco diagnostics.

**Conclusions.**
- **Plain s-scaling fails.** It does reduce the vbnf term (109 → 7.7 kHz), but from s = 4 no lnw nulls the tempco.
  - Scaling L of the reference NMOS (MN1/MN2) away from the 1 µm of the ring feet breaks the tracking that the
    constant-gm reference relies on.
  - `s14_nonly` (NMOS only) shows the loss; `s14_ponly` (PMOS only) keeps the null but doesn't reduce noise.
  - The only s with FM near the limit is s14, at 16.1 kHz, with +1439 ppm/°C. So **none of s ∈ {1…14} qualifies**.
- **The winner is `s1_nsn14p_mr4`: rms FM 13.3 kHz, tempco +1 ppm/°C, start-up OK.**
  - Settings: `--set nsn=14 --set wpm=56 --set lpm=14 --set mr=4 --set lnw=3.665 --set lnp=100 --set rideal=0`.
  - The arrays scale area by nsn² with the same W/L and the same 1 µm unit L, so tracking is kept.
  - The remaining floor is the ring's own foot flicker (10.5 kHz) and the master-leg vbp (about 10 kHz). mr = 4
    halves the vbp term, at a cost of +1.3 mW.
  - With nsn = 20 (no mr), FM is 15.9 kHz, just over the limit, and the FET area doubles.
  - The 13.3 kHz is only 1.7 kHz below the 15 kHz limit and is a tt-only number. Job 2 shows ff and fs at 0 °C
    going well above it.
- **Lower K_vbn.** Yes, a lower K_vbn looks like the better route for the rest of the gap.
  - Once vbnf is filtered to 6–7 kHz, the bias FM is close to K_vbn × the reference noise. The device term
    (10.5 kHz at tt) can't be reduced from the reference side.
  - Taking more of the ring current from fixed legs cuts K_vbn, and with it both bias terms, roughly in proportion,
    at no area cost.
  - It would also reduce the corner spread of K_vbn seen in Job 2 (−590 to −980 MHz/V).

## Job 2: phase noise of the winner over PVT (`cgmq`)

**Method.**
- `isf.py` gains a variant `cgmq`: cgmf plus the winning sizing, with nsn = 14, wpm = 56, lpm = 14, mr = 4,
  lnw = 3.665, lnp = 100, rideal = 0, rf = 1 MΩ, cf = 20 pF.
- Operating point: code 5, vctrl 1.65 V, which is 436 MHz at tt from the 2 fF map.
- It was run with `OUT=build/pnq VARIANTS=cgmq TEMPS="0 27 70" PAR=3 JOBS=4 sim/pn/run_all.sh`, at m = 60 for
  5 corners × 3 temperatures.
- `bias_fm.py --variant cgmq --dev build/pnq/cgmq_<corner>_t<T>/result.json` then adds the dense vbnf/vbp
  `.noise` terms at each corner and temperature, using that case's own device/vdd terms and K values.
- The L columns are the totals including the bias terms. The dominant term is the largest contributor to rms FM
  over 1–10 kHz.
- cw = 2 fF.

| corner | T °C | f0 MHz | Iref µA | L 10k | L 100k | L 1M | L 10M dBc/Hz | FM 1–10k kHz | FM 1–100k kHz | dominant (1–10k) | 2nd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| typical | 0 | 430.0 | 42.2 | -43.0 | -71.5 | -95.3 | -116.0 | 14.6 | 21.8 | dev_foot 12.9 | vbnf 6.2 |
| typical | 27 | 436.1 | 44.6 | -43.7 | -72.3 | -96.1 | -116.8 | 13.4 | 20.0 | dev_foot 11.4 | vbnf 6.1 |
| typical | 70 | 433.8 | 46.7 | -44.6 | -73.3 | -96.9 | -117.6 | 12.0 | 17.8 | dev_foot 9.4 | vbnf 5.9 |
| ss | 0 | 408.1 | 45.0 | -46.3 | -75.2 | -99.1 | -119.8 | 10.1 | 14.8 | dev_foot 7.5 | vbnf 5.3 |
| ss | 27 | 413.5 | 47.6 | -46.7 | -75.7 | -99.6 | -120.4 | 9.6 | 14.1 | dev_foot 6.9 | vbnf 5.1 |
| ss | 70 | 411.3 | 49.9 | -47.1 | -76.2 | -100.2 | -121.0 | 9.1 | 13.4 | dev_foot 6.3 | vbnf 4.9 |
| ff | 0 | 445.9 | 39.7 | -36.5 | -65.2 | -90.6 | -112.0 | 30.4 | 45.8 | dev_foot 28.6 | vbp 8.8 |
| ff | 27 | 443.8 | 41.9 | -39.7 | -68.2 | -92.6 | -113.6 | 21.1 | 31.9 | dev_foot 19.8 | vbnf 6.3 |
| ff | 70 | 436.7 | 43.7 | -41.4 | -70.0 | -94.0 | -114.7 | 17.1 | 25.9 | dev_foot 15.5 | vbnf 6.7 |
| sf | 0 | 369.6 | 44.0 | -45.9 | -74.7 | -98.1 | -118.7 | 10.6 | 15.5 | dev_foot 7.2 | vbnf 5.9 |
| sf | 27 | 380.4 | 46.5 | -46.2 | -75.1 | -98.5 | -119.1 | 10.2 | 14.8 | dev_foot 6.4 | vbnf 5.9 |
| sf | 70 | 384.5 | 48.8 | -46.4 | -75.4 | -98.9 | -119.5 | 9.9 | 14.4 | dev_foot 5.9 | vbnf 5.7 |
| fs | 0 | 522.4 | 40.6 | -38.3 | -66.9 | -91.8 | -113.0 | 24.7 | 37.4 | dev_foot 23.4 | vbp 6.0 |
| fs | 27 | 514.5 | 42.9 | -39.9 | -68.5 | -93.3 | -114.3 | 20.4 | 30.9 | dev_foot 19.5 | vbnf 5.2 |
| fs | 70 | 497.4 | 44.8 | -41.9 | -70.5 | -94.7 | -115.6 | 16.2 | 24.6 | dev_foot 15.2 | vbnf 5.4 |

Ring-only stage-B table (`sim/pn/summary.py`): `sim/results/2026-11-08/job2/summary.md`. There, the dominant term at
1 MHz is dev_foot, except vdd at sf.

**Conclusions.**
- At tt, ss and sf, the winner's rms FM over 1–10 kHz is 9–15 kHz. At ff and fs it is 16–30 kHz.
- The worst case is ff at 0 °C: 30 kHz, with L(10k) = −36.5 dBc/Hz.
- The excess comes from the ring's own NMOS foot-device flicker noise. In the fast-NMOS corners it is 2–4 × the tt
  value, and it is largest at 0 °C.
- The bias terms (vbnf, vbp) are 5–9 kHz everywhere, so the reference is no longer the limit.
- Meeting 15 kHz across PVT needs a change to the ring (larger foot devices), which is outside this brief, or the
  lower-K route from Job 1.
- tt 27 °C reproduces Job 1 (13.4 vs 13.3 kHz).

## Job 3: tuning map of the winner, cw = 10 fF

**Method.**
- `vco_bias.py map $(winner sets) --set cw=10e-15 --jobs 8 --tag map_cgmq_cw10f` runs f for codes 0–31 ×
  vctrl 0/1.65/3.3 V.
- PVT: 5 corners × 0/27/70 °C × VDD 3.15/3.3/3.45 V, which is 4320 points.
- Filter off. Each sim starts from the DC operating point, without uic (see script fixes).
- Per PVT point:
  - range = code 0 at vctrl 0 to code 31 at vctrl 3.3 V;
  - "codes for 433.92" = the codes whose 0–3.3 V fine range contains 433.92 MHz;
  - largest coarse step = the largest f(c+1) − f(c) at vctrl 1.65 V;
  - fine = the smallest f(c, 3.3 V) − f(c, 0) over all codes;
  - non-monotonic = any f(c+1) ≤ f(c) at any vctrl.
- Coverage means fmin ≤ 310 MHz and fmax ≥ 620 MHz.
- None of these numbers include the wiring R, which lowers f by a further 10–12 %.

| corner | T °C | VDD V | f range MHz | codes for 433.92 | max coarse step MHz (code) | min fine range MHz | fine/step | ≥1.3? | non-monotonic | 310–620 |
|---|---|---|---|---|---|---|---|---|---|---|
| typical | 0 | 3.15 | 189.4–511.4 | 21–23 | 12.2 (0) | 16.8 | 1.37 | yes | – | NO |
| typical | 0 | 3.30 | 178.7–505.7 | 22–24 | 11.9 (0) | 18.6 | 1.56 | yes | – | NO |
| typical | 0 | 3.45 | 168.3–497.5 | 24–25 | 11.5 (0) | 20.1 | 1.75 | yes | – | NO |
| typical | 27 | 3.15 | 197.5–512.7 | 21–22 | 12.5 (0) | 12.9 | 1.03 | no | – | NO |
| typical | 27 | 3.30 | 187.0–509.2 | 22–23 | 12.3 (0) | 14.8 | 1.20 | no | – | NO |
| typical | 27 | 3.45 | 176.6–502.9 | 23–24 | 12.0 (0) | 16.3 | 1.36 | yes | – | NO |
| typical | 70 | 3.15 | 202.7–501.0 | 22 | 12.6 (0) | 8.8 | 0.70 | no | – | NO |
| typical | 70 | 3.30 | 192.7–500.7 | 22–23 | 12.4 (0) | 10.5 | 0.84 | no | – | NO |
| typical | 70 | 3.45 | 182.7–497.2 | 23–24 | 12.2 (0) | 12.0 | 0.98 | no | – | NO |
| ss | 0 | 3.15 | 192.9–462.7 | 27 | 11.3 (0) | 10.0 | 0.89 | no | – | NO |
| ss | 0 | 3.30 | 184.8–464.8 | 27–28 | 11.3 (0) | 11.9 | 1.05 | no | – | NO |
| ss | 0 | 3.45 | 176.1–463.6 | 27–28 | 11.2 (0) | 13.5 | 1.21 | no | – | NO |
| ss | 27 | 3.15 | 200.0–459.2 | 27 | 11.4 (0) | 7.2 | 0.63 | no | – | NO |
| ss | 27 | 3.30 | 192.3–463.8 | 26–27 | 11.4 (0) | 8.8 | 0.77 | no | – | NO |
| ss | 27 | 3.45 | 184.1–464.8 | 27 | 11.4 (0) | 10.4 | 0.91 | no | – | NO |
| ss | 70 | 3.15 | 203.8–442.1 | 29–30 | 11.3 (0) | 4.5 | 0.40 | no | – | NO |
| ss | 70 | 3.30 | 196.9–450.1 | 28 | 11.4 (0) | 5.7 | 0.50 | no | – | NO |
| ss | 70 | 3.45 | 189.3–454.0 | 28 | 11.4 (0) | 7.0 | 0.61 | no | – | NO |
| ff | 0 | 3.15 | 179.3–543.7 | 20–22 | 12.3 (1) | 24.8 | 2.01 | yes | – | NO |
| ff | 0 | 3.30 | 168.4–530.1 | 21–23 | 11.8 (3) | 26.3 | 2.23 | yes | – | NO |
| ff | 0 | 3.45 | 158.6–514.6 | 23–25 | 11.3 (7) | 27.3 | 2.41 | yes | – | NO |
| ff | 27 | 3.15 | 187.0–549.5 | 19–20 | 12.9 (0) | 20.3 | 1.58 | yes | – | NO |
| ff | 27 | 3.30 | 175.6–537.8 | 20–22 | 12.3 (3) | 21.9 | 1.78 | yes | – | NO |
| ff | 27 | 3.45 | 165.2–524.1 | 22–23 | 11.8 (7) | 23.1 | 1.96 | yes | – | NO |
| ff | 70 | 3.15 | 192.3–543.2 | 19–20 | 13.1 (0) | 15.1 | 1.15 | no | – | NO |
| ff | 70 | 3.30 | 180.9–534.2 | 20–21 | 12.6 (0) | 16.8 | 1.33 | yes | – | NO |
| ff | 70 | 3.45 | 170.3–523.1 | 22–23 | 12.1 (3) | 18.1 | 1.49 | yes | – | NO |
| sf | 0 | 3.15 | 178.9–484.5 | 25–26 | 11.4 (0) | 16.2 | 1.43 | yes | – | NO |
| sf | 0 | 3.30 | 169.9–478.0 | 26–27 | 11.0 (0) | 17.7 | 1.60 | yes | – | NO |
| sf | 0 | 3.45 | 161.2–469.4 | 27–28 | 10.7 (0) | 18.8 | 1.77 | yes | – | NO |
| sf | 27 | 3.15 | 186.9–487.7 | 24–25 | 11.7 (0) | 12.6 | 1.08 | no | – | NO |
| sf | 27 | 3.30 | 178.0–483.1 | 25–26 | 11.4 (0) | 14.1 | 1.24 | no | – | NO |
| sf | 27 | 3.45 | 169.2–476.3 | 26–27 | 11.1 (0) | 15.4 | 1.38 | yes | – | NO |
| sf | 70 | 3.15 | 192.3–478.5 | 24–25 | 11.8 (0) | 8.6 | 0.73 | no | – | NO |
| sf | 70 | 3.30 | 183.8–477.0 | 25–26 | 11.6 (0) | 10.1 | 0.87 | no | – | NO |
| sf | 70 | 3.45 | 175.2–472.8 | 26–27 | 11.3 (0) | 11.3 | 1.00 | no | – | NO |
| fs | 0 | 3.15 | 200.4–536.2 | 19–20 | 13.2 (0) | 16.7 | 1.26 | no | – | NO |
| fs | 0 | 3.30 | 187.8–532.3 | 20–21 | 12.9 (0) | 18.8 | 1.46 | yes | – | NO |
| fs | 0 | 3.45 | 175.3–525.1 | 21–22 | 12.5 (0) | 20.7 | 1.66 | yes | – | NO |
| fs | 27 | 3.15 | 208.4–535.2 | 18–19 | 13.4 (0) | 12.8 | 0.95 | no | – | NO |
| fs | 27 | 3.30 | 196.1–533.7 | 19–20 | 13.3 (0) | 14.9 | 1.12 | no | – | NO |
| fs | 27 | 3.45 | 183.8–528.6 | 20–21 | 12.9 (0) | 16.7 | 1.30 | no (1.296) | – | NO |
| fs | 70 | 3.15 | 213.0–520.5 | 19–20 | 13.4 (0) | 8.7 | 0.65 | no | – | NO |
| fs | 70 | 3.30 | 201.5–522.2 | 20 | 13.3 (0) | 10.5 | 0.79 | no | – | NO |
| fs | 70 | 3.45 | 189.8–520.1 | 21 | 13.1 (0) | 12.2 | 0.93 | no | – | NO |

**Conclusions.**
- **Coverage of 310–620 MHz is not met at any PVT point (0 of 45). The shortfall is at the top:**
  - fmax is 442–549 MHz, against 620 needed, so 71–178 MHz is missing;
  - the worst point is ss at 70 °C and 3.15 V, which needs ×1.40 more top frequency;
  - with the further 10–12 % from wiring R, that becomes about ×1.6.
- **This is not a shortage of coarse bits.** The bottom is reached with margin (fmin 159–213 MHz), and the code span
  fmax/fmin is 2.4–3.3 at every point, more than the ×2 that 310–620 needs. The range sits too low, and the
  5 bits would cover the target if it were moved up by about ×1.4–1.6.
- **433.92 MHz is reachable at every point**, at codes 18–30, near the top of the code range. At tt 27 °C and 3.3 V
  it is codes 22–23.
- **The fine range fails the requirement at many points.**
  - Fine ≥ 1.3 × the largest step holds at 18 of 45 points. ff 70 °C 3.3 V (1.33) is only just above the limit,
    and fs 27 °C 3.45 V (1.296) only just below it.
  - The fine range shrinks with temperature and at ss. The worst point is ss 70 °C 3.15 V, at 0.40.
  - Steps are 10.7–13.4 MHz, largest at the lowest codes.
  - No step is non-monotonic.

**For reference, the 2 fF map** (same method, `sim/results/2026-11-08/map_cw2f/`, run before the extraction
result was known):
- **Range:** fmin is 258–422 MHz and fmax 665–908 MHz.
- **Coverage:** met at 16 of 45 points. It fails at the bottom at every ff, fs, ss and tt point.
- **Fine range:** fine ≥ 1.3 × step at only 5 of 45 points, and steps are 17–22 MHz.
- **ff 0 °C, 3.45 V:** codes 0–1 are non-monotonic at vctrl 0 and 1.65 V. At ff 0 °C, the fine range is negative at
  3.3 V and 3.45 V, and so is fs 0 °C 3.45 V: f falls as vctrl rises from 1.65 to 3.3 V at low codes. The ring
  stays in its fundamental mode there.
- **cgmq operating point:** tt 27 °C 3.3 V needs code 4–5, which is why `cgmq` uses code 5. At 10 fF this becomes
  22–23.

## Ring start-up at code 0 (fundamental mode), cw = 10 fF

**Method.**
- `vco_bias.py ringstart --code 0 --seeds 6 --jobs 20 $(winner sets) --set cw=10e-15` runs the winner at code 0,
  vctrl 1.65 V, VDD 3.3 V, over 5 corners × 0/27/70 °C.
- Each corner and temperature starts from the deck's alternating state and from 6 random states, with each ring
  node uniform in 0–3.3 V. That is 105 transients.
- The reference starts from its DC operating point with the ring nodes held at the initial state; then everything
  is released for 500 ns.
- Mode test:
  - the phase from an a0 rise to the next a2 rise, as a fraction of the period, must be within 0.07 of 0.2 (the
    fundamental of a 5-stage ring; mode 3 gives 0.6);
  - f over rises 1–6 after 400 ns must be within 5 % of the alternating start;
  - f after 50 ns must be within 5 % of f after 400 ns.

**Result: 105 of 105 runs are in the fundamental mode.**
- Phase is 0.1999–0.2002, and every random-start f is within 0.07 % of the alternating start (ratio 0.9993–1.0000).
- f at 50 ns is within 0.2 % of f at 400 ns, so the ring settles quickly.
- a0 swings rail to rail, at least 3.13 V peak to peak.
- Code-0 f is 175–209 MHz (cw = 10 fF, no R).

A first run had every node at the same voltage in each random state, because of the seeding bug (script fixes). It
is kept in `build/` as an extra symmetric-start stress case, and its 105 runs were also all in the fundamental mode.
Spot checks with the fixed classifier also showed phase 0.200, the fundamental: cw = 0 (tt/ff/fs at 27 °C) and
cw = 2 fF at ff 0 °C 3.45 V. Results: `sim/results/2026-11-08/ringstart_cw10f/ringstart.json`.

## Run times (from timestamps in build/logs)

| step | start | end | wall |
|---|---|---|---|
| Job 1 plain s sweep (`ref_sweep.py` s = 1…14, 6 in parallel) | 2026-11-07 22:24:22 | 22:33:22 | 9 min |
| Job 1 nsn / nsn+p cases | 22:40:18 | 22:54:22 | 14 min |
| Job 1 bias_fm rerun after the DC-start fix (all cases, incl. nsn14p_mr4 and nsn20p in full) | 22:58:01 | 23:10:35 | 13 min |
| Job 3 map, cw = 2 fF (20 jobs) | 23:11:36 | 23:54:24 | 43 min |
| Job 3 map, cw = 10 fF (8 jobs) | 2026-11-08 00:01:34 | 01:20:59 | 79 min |
| Job 2 ISF, 15 cases (PAR 3 × JOBS 4) | 00:05:32 | 01:30:31 | 85 min |
| Job 2 bias_fm, 15 cases (5 × 2 jobs) | 07:55:56 | 08:05:51 | 10 min |
| Ring start-up, code 0, cw = 10 fF (20 jobs) | 08:55:51 | 08:57:47 | 2 min |

Gaps between steps were spent on diagnostics and script fixes, listed below. The wait from 01:30 to 07:55 was idle:
nothing woke me when the jobs finished.

## Script changes and fixes

- **`sim/pn/isf.py`**
  - `--set K=V` (repeatable) merges into the variant's parameters, and `--tag` suffixes the work directory.
    `result.json` records the sets. Without `--set`, results are unchanged: `cgm --m 8` matches the stored A-stage
    numbers.
  - New variant `cgmq`.
  - `bias_noise_deck` gains `node`, `out` and `edit` arguments (backward compatible).
  - `no_uic()`: variants with `ic_ref` start transients from the DC operating point, not from `uic`.
    - Large references (nsn arrays, long-L mirrors) don't settle within the 100 ns of a uic start.
    - Holding the reference nodes with `.ic` was not enough, because PDK subcircuit-internal nodes still start at 0
      V. vbn sagged to 0.69–0.96 V instead of 1.27 V.
- **`sim/vco/vco_bias.py`** (`P` and `netlist()` backward compatible; new keys default to the old circuit)
  - `nsn`: MN1/MN2 as nsn-series × nsn-parallel arrays.
  - `deck(uic=False)` option.
  - `run(jobs=N)` runs single-threaded ngspice processes in parallel.
  - New modes:
    - `map`, plus `map_summary`;
    - `startup`: VDD ramp, vbn/vbnf against the DC op;
    - `ringstart`: mode from random initial states.
  - **ringstart fix 1, the mode classifier:** it uses the phase from an a0 rise to the next a2 rise, which is k/N in
    mode k: 0.2 for the fundamental, 0.6 for mode 3.
    - The first version compared only against the alternating start, so it could not catch a higher mode there.
    - A version using the a0-rise to a1-fall phase was skewed by rise/fall asymmetry.
    - Mutation-tested with fake phases: 0.2 → 1, 0.6 → 3, 0.4 → 7, 0.8 → 9, junk → rejected.
  - **ringstart fix 2, random initial states:** the generator was re-seeded per node, so every "random" state had
    the same voltage on all five nodes. The run was redone with independent per-node values.
- **`sim/pn/bias_fm.py`** (new)
  - Dense vbnf/vbp `.noise`, measured K values and FM integration.
  - Fix: `scaled()` first overwrote the variant's own wpm/lpm instead of scaling them.
  - Fix: the vbp noise had used the sagged transient vbn as its hold voltage. All Job 1 FM numbers were rerun after
    the DC-start fix. The vbp term of `s14_ponly`/`s14_nonly` predates the fix, so quote only their tempco.
- **`sim/pn/ref_sweep.py`** (new)
  - lnw search: the tempco is not monotonic in lnw (at s = 1 it has zeros near 3.07 and about 7 µm), so a plain
    secant search diverged. It now brackets, then uses regula falsi, with an Iref-match fallback.
- **`sim/pn/run_all.sh`:** takes VARIANTS, CORNERS, TEMPS, OUT and JOBS from the environment.
- **`sim/pn/summary.py`:** adds a temperature column.
- **Log check:** none of the Job 2, Job 3 or start-up logs contain "Transient op started".
