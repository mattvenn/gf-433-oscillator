# Phase 1: VCO architecture study (in progress)

All results are **schematic only** (nfet/pfet_03v3, 2 fF wiring per node estimated, AD/AS from a 0.5 µm
diffusion), with no extraction and no GF silicon factor yet (see [platform.md](platform.md)).
Scripts: `sim/vco/ring_basic.py` (plain ring) and `sim/vco/vco_cand.py` (candidates). Outputs go to `build/vco/`.

## 1. Plain inverter ring (baseline)
`python3 sim/vco/ring_basic.py`, Wn/Wp = 2/5 µm, N = 5–15, 5 corners × 0/27/70 °C × VDD 3.15/3.3/3.45.

| | Value |
|---|---|
| f·N, tt 27 °C | 9.74 GHz·stage (≈ 51 ps/stage). ss 8.02, ff 11.59, sf 9.61, fs 9.75 |
| N for 433.92 MHz | 22.4 |
| PVT spread | ×0.73 … ×1.29 of tt 27 °C 3.3 V |
| df/dVDD | +0.23 %/10 mV ≈ **+1.0 MHz/10 mV** at 434 |
| Temperature | −1840 ppm/°C ≈ **−800 kHz/°C** at 434 |
| Power | 2.5 mW (independent of N) |

**What it means for FSK (±50 kHz):** 0.5 mV of supply or 0.06 °C moves the carrier by the full
deviation. The FLL has to keep tracking during transmit (or a PLL comes later), and the ring supply
has to be quiet.

**Thermal-noise floor (Hajimiri estimate, not simulated):**
L(1 MHz) ≈ (8/3)·(kT/P)·(VDD/Vchar)·(f0/Δf)² ≈ **−110 dBc/Hz** at 2.5 mW. That is ~330 Hz rms of FM in a
10 kHz band, which is negligible next to the supply and temperature terms. The sky130 ring's measured
45 kHz rms wander must therefore come from supply noise and flicker, not thermal noise. The
design priorities follow from that: supply rejection, and symmetry (low ISF DC → less 1/f
upconversion).

## 2. Coarse tuning: switched MOS-cap bank (rejected)
Every node had binary nfet gate-caps switched to ground (`coarse=c`). It failed both ways:
- small units (0.5 × 0.56 µm): the whole 4-bit code range is only **×0.86**;
- large units (3 × 1 µm): with every switch off, the floating S/D still loads the node, and the
  ring slows from ~1 GHz to 317 MHz before any code is applied.

The off/on C ratio of switched GF180 3.3 V MOS caps is too poor. (MIM would be better, but it is
area-hungry and not checked yet.)

## 3. Coarse tuning: switched starving current (current choice)
`coarse=i`: every stage has a current-starved inverter. The NMOS feet are
`k·wfu` (gate `vctrl`) plus binary legs `2^b·wfu` whose gates `g_b` are switched to `vctrl` or 0
(one TG + pulldown per bit, shared by all stages). A mirror copies the same total into the PMOS
heads. So I ∝ (k + code)·I(vctrl), and the fine control moves every leg by the same fraction.

**Single-ended, N = 5** (core Wn/Wp 2/5 µm, starving L 1 µm, wfu 0.25, k = 8, 4 bits, head 6 µm):

| vctrl | code 0 | code 7 | code 15 | (MHz, tt 27 °C) |
|---|---|---|---|---|
| 1.2 V | 196 | 306 | 419 | |
| 1.5 V | 349 | 540 | 719 | coarse range ×2.06 |
| 2.0 V | 585 | 803 | 931 | |
| 2.5 V | 710 | 891 | 994 | |

At code 7, vctrl 1.5 V (540 MHz, 1.0 mW):
- df/dVDD **−0.11 %/10 mV** (≈ −0.5 MHz/10 mV at 434). Half the plain ring, with the opposite sign:
  current is fixed, swing = VDD, so f ∝ 1/VDD.
- Temperature **−2060 ppm/°C** with a fixed vctrl voltage.
- Corners at 27 °C: ss 401, ff 701 → ×0.74 … ×1.30.

**Differential (pseudo-differential), N = 4:** two starved rings with weak cross-coupled inverters per
node. The latch inverters share their stage's starved head and foot so that their strength
tracks the current. Same sizing, wx = 0.5.

| vctrl | code 0 | code 7 | code 15 | (MHz) |
|---|---|---|---|---|
| 1.5 V | 177 | 344 | 511 | |
| 2.0 V | 402 | 607 | 726 | |

At code 7, vctrl 1.5 V: 1.8 mW, **df/dVDD −0.29 %/10 mV**, −1900 ppm/°C. Compared with SE it uses
~1.6× the power per MHz, has a steeper Kvco and worse supply rejection, because a
pseudo-differential stage has no tail and so no common-mode rejection. Its advantages
(complementary outputs for the antiphase antenna drive, and possibly lower flicker upconversion)
only show up in the phase-noise comparison (still to do).

## Open problems and next steps
1. **Kvco on vctrl is far too high** (≈ 500–800 MHz/V around 1.5 V). Noise or ΣΔ ripple on vctrl
   becomes FM. Plan: the main legs get a fixed bias from an on-chip **constant-gm (β-multiplier)
   reference**, and vctrl drives only a small fine leg (≈ ±10 % range). Constant-gm current rises
   with temperature, so it should also cancel much of the −2000 ppm/°C. Its PSRR sets the supply
   term, so simulate it with the ring.
2. **Coarse resolution:** use 5 bits with k = 16 (steps ≤ 1/16 of the current), so a ±10 % fine range
   overlaps every coarse step with ≥ 1.3× margin.
3. **Supply-sensitivity cancellation:** the plain ring is +0.23 %/10 mV and fully starved is
   −0.11 %/10 mV. A partly starved design (or one that tracks swing) may null it. Try it.
4. **Phase noise:** ISF method (impulse injection) plus device noise PSDs, cross-checked with a
   numpy-noise transient. Compare SE vs diff at equal power, flicker included.
5. Divider first stage (TSPC vs std-cell DFF) at the fastest corner. RF buffer into the ua pad
   model once the GF pad R/C is known.
