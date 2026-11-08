# Current-fed ring (topo = cfed): noise, tempco and tuning (laptop, 2026-11-08)

- **Circuit:** `sim/vco/vco_bias.py` with `topo=cfed`. Five plain inverters (wn/wp 2/5, L 0.28) between VDD and a
  shared node vg, a 3 pF decap on vg, and one shared NMOS current DAC (base k = 6, 5 binary bits, fine leg on vctrl)
  from vg to GND, with gates on the const-gm reference's vbn.
- **Settings:** winner reference (`sim/results/2026-11-08/winner_sets.txt`) plus `topo=cfed kc=0.75 k=6
  cvg=3e-12 cw=3e-15`.
- **Script:** `sim/pn/cfed_noise.py` (modes tc / pvt / ki / dacn / isf / step / range).
- **Raw outputs:** `build/cfed/` (not committed).

## Topology choice (sim/vco/topo_cmp.py, schematic, 5 corners × 0/70 °C)
cfed is the only topology that tunes monotonically everywhere and covers the range:
- worst-case range 296–849 MHz;
- 0.53 mW near 433.92 MHz;
- df/dVDD −0.008 %/10 mV, against −0.25 for the starved ring.

The starved ring loses current control from f-node charge sharing (`docs/ring_layout_v2.md`). The "stack" variant
is about 5× too slow, because the foot's drains load the output.

## Noise at tt 27 °C, code 6
- **Operating point:** I_DAC = 66.7 µA, vg = 1.85 V, swing 1.81–3.42 V.
- **Sensitivities:** K_I = 4.81 MHz/µA, K_vdd = −3.7 MHz/V.
- **Method:** S_f = K_I²·S_I, with S_I a dense `.noise` of the DAC output current with vg held.

rms FM in kHz, 1–10 kHz / 1–100 kHz:

| case | ref/vbn | DAC devices | total |
|---|---|---|---|
| base | 8.5 / 22.4 | 18.2 / 26.6 | 20.1 / 34.8 |
| + vbn RC filter (1 MΩ / 20 pF) | 7.2 / 8.7 | 18.2 / 26.6 | 19.6 / 28.0 |
| DAC area × 4 (`ka=4`) | 9.0 / 23.8 | 9.2 / 13.8 | 12.9 / 27.5 |
| filter + DAC × 4 | 7.7 / 9.2 | 9.2 / 13.8 | 12.0 / 16.6 |
| **filter + DAC × 16** | 7.7 / 9.3 | 4.4 / 7.1 | **8.9 / 11.7** |

- **Other contributors:** the inverters (ISF with crossings at mid-swing, coarse M = 20, ±6 dB) add 0.5 / 1.3 kHz.
  vdd at 160 nV/√Hz adds 0.06 / 0.19 kHz.
- **For comparison**, the starved `cgmq` gives 13.4 / 20.0 kHz.
- **L at 10k / 100k / 1M / 10M dBc/Hz:**

  | case | 10k | 100k | 1M | 10M |
  |---|---|---|---|---|
  | base | −39.8 | −65.1 | −91.5 | −120.8 |
  | filter + DAC × 16 | −47.7 | −79.1 | −101.5 | −121.5 |
  | cgmq | −43.7 | −72.3 | −96.1 | −116.8 |

- **Cost of DAC × 16:** about 220 µm².

## Tempco and range
- **Tempco depends on the code**, about −14 ppm/°C per code. lnw = 7.25 µm nulls it at code 15: 435.2 MHz at tt,
  +7 ppm/°C, with a parabolic curve (431.1 / 435.2 / 431.9 MHz at 0 / 27 / 70 °C).
- **That retune lowers Iref by about 34 %.** The worst-case range becomes 164–586 MHz, which **fails** the
  310 / 700 MHz target.
- **Untested fix:** a wider DAC (`wfu = wff = 0.3`), then a re-null of lnw. The DAC width, lnw and the 433.92 code
  interact, so this is handed to the sim pod (`docs/handoff_cfed_sizing.md`).
- **Coarse step vs fine** (k = 6, all codes, ss 70 / tt 27 / ff 0 °C): fine/step is at least 3.0, so it passes.
