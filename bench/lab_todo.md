# Lab to-do

## Results, 2026-11-09 (data: `bench/2026-11-09/`, public: github.com/mattvenn/ttgf0p2-vgaringosc-measurements)
1. **Ring #614 (`tt_um_algofoogle_vgaringosc`) measured** on 2 chips. Chip 1: 23.7–220.5 MHz on the inv_2 taps,
   5× inv_1 ring 319.6 MHz; about 120 ps per inv_2 stage + 4.2 ns overhead. Chip 2 about 2 % slower.
   The silicon factor needs the matching simulation: `docs/handoff_gf_silicon_factor.md`.
2. **Carrier regulator: not fitted.** U1/U2 and R1 absent; R2, R3, R4 fitted, so VDD_CORE = demo-board +3V3
   (3.300 V). Noise about 0.34 mV rms in 20 MHz after removing the probe floor (about 61–76 nV/√Hz, below the
   100 nV/√Hz assumed).
3. **RP2350 reference: integer PLL works.** 12 MHz × 113 ÷5 ÷2 = 135.6 MHz, PWM ÷10 = 13.56 MHz / ÷5 = 27.12 MHz;
   8-cycle jitter ≤ 44 / 29 ps rms. The SDK default lands on 13.50 MHz, so set the PLL in firmware. All readings
   about +85 ppm high (crystal or scope timebase: check on the RTL-SDR). The RTL-SDR phase-noise check is still open.
4. **COB carriers:** 3 of 4 had inputs held low (shorted, bonds look intact); 2 did not boot. Start bring-up with
   the pin check (`bench/2026-11-09/` pin test: drive each pin, read the pad).

Bench measurements the design is waiting on. Record the board, chip and VDPWR with every result.

## 1. GF silicon factor: ttgf0p2 #200 ring (Monday 2026-11-09)
- Project #200 `tt_um_algofoogle_vgaringosc`. Record the `clksel` setting, the output pin, VDPWR and the frequency.
- Measure a few `clksel` values if time allows.
- Afterwards, the same configurations are simulated from the GDS-extracted netlist, which gives the silicon /
  simulation factor. sky130 was ×0.866. Until it is known, the tuning range has to cover ×0.7 … ×1.4.

## 2. Carrier-board core regulator (same session)
The GF CoB carrier schematic marks U1/U2 (AP2112K-3.3) as do-not-populate, but they are fitted on real boards.
- Which 0 Ω link feeds U1's input: R1 (+5 V, the normal case) or R3 (+3V3)? Fed from R3, the 3.3 V regulator
  has no headroom, so it barely filters supply noise.
- VDD_CORE with a multimeter.
- If possible: VDD_CORE noise on the scope (AC-coupled, 20 MHz bandwidth limit), with a ring running.

These readings replace the assumed 100 nV/√Hz supply noise in the phase-noise budget.

## 3. RP2350 as a PLL reference clock
A later on-chip phase-locked loop (PLL) would need a clean reference from the demo board: no external components
on the chip side. 433.92 MHz = 32 × 13.56 MHz = 16 × 27.12 MHz.
- Can the RP2350 make 13.56 or 27.12 MHz with **integer dividers only**? Fractional dividers add jitter, which the
  PLL multiplies by N² (+30 dB for N = 32). A candidate (check against the datasheet's PLL limits):
  12 MHz × 113 = 1356 MHz VCO, then postdiv 5 × 2 gives clk_sys = 135.6 MHz, then GPOUT ÷10 = 13.56 MHz or
  ÷5 = 27.12 MHz.
- Does the firmware still run correctly at clk_sys = 135.6 MHz (PIO counting, USB)?
- Measure the clock on a GPIO and at the TT chip's clock input:
  - frequency against the crystal;
  - period jitter on the scope (TIE or persistence);
  - phase noise of 27.12 MHz on the RTL-SDR (in range without direct sampling). Add 20·log₁₀(16) ≈ 24 dB to
    estimate what it would give at 433.92 MHz.
- Compare with a fractional-divider setting to see how much worse it is.
