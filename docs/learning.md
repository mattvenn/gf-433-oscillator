# Learning notes: a tunable 433.92 MHz ring oscillator on GF180

Notes written while designing this block, so the reasoning can be reused when explaining it to others.
Each section gives the idea in plain words, then the number from our own simulation. Results are
schematic simulations unless marked otherwise. Scripts are in `sim/vco/`, and the full results are in
[vco_study.md](vco_study.md).

## 1. What sets a ring oscillator's frequency
A ring oscillator is an odd number N of inverters in a loop. An edge travels round the loop twice per
period, so f = 1 / (2 · N · t<sub>d</sub>), where t<sub>d</sub> is the delay of one stage. The delay is
roughly the time to charge the next stage's capacitance C through the switch-on current I over the voltage
swing V: t<sub>d</sub> ≈ C · V / I.

- GF180 3.3 V inverters (Wn/Wp = 2/5 µm) have t<sub>d</sub> of about 51 ps, so f · N ≈ 9.74 GHz. A plain
  ring needs about 22 stages for 433.92 MHz.
- Power is about 2.5 mW whatever N is: each stage switches C · V² once per period, and N · f is constant.
- Every term in t<sub>d</sub> ≈ C · V / I moves: the supply V, the current I (temperature, process) and C
  (process). That is why a free-running ring lands anywhere in ×0.73 … ×1.29 of nominal across
  process, voltage and temperature (PVT).

## 2. Why the drift matters for FM and FSK
Frequency-shift keying (FSK) sends data by switching the carrier between two frequencies, often only
±25–50 kHz apart. The plain ring moves about +1 MHz for 10 mV of supply and about −800 kHz per °C, so a
0.5 mV supply change or a 0.06 °C temperature change is as large as the whole deviation. The frequency
loop therefore has to keep running during transmit, and the oscillator itself should be made as
insensitive as possible.

## 3. Tuning knobs: change C or change I
- **Switched capacitors** (change C). Tried and rejected: a switched GF180 MOS capacitor still loads the node
  through its junctions when switched off, so the on/off ratio is poor (only ×0.86 of range from a 4-bit
  bank).
- **Current starving** (change I). Each inverter gets its current through a series PMOS "head" and NMOS
  "foot" transistor that act as current sources. Switching binary-weighted foot transistors on and off
  (the coarse code) gives ×2–3 of range cleanly, because an off transistor adds almost no load.

## 4. Kvco: why steep tuning is bad
Kvco is the change in frequency per volt on the analog control input (vctrl). Noise on vctrl becomes
frequency noise multiplied by Kvco. With vctrl driving the whole foot current, Kvco was about
500–800 MHz/V, so just 1 mV of noise would move the carrier by up to 0.8 MHz.

The usual fix is to split the jobs: a fixed, clean bias sets most of the current (with the digital
coarse code), and vctrl drives only a small "fine" transistor. Our version brought Kvco down to about
16 MHz/V (±3.8 % fine range), roughly 50× lower.

## 5. A constant-gm bias, and why its current rises with temperature
A constant-gm (β-multiplier) reference is a small self-biased loop: two NMOS transistors with a size
ratio K, one with a resistor R in its source, and a PMOS current mirror forcing equal currents. The loop
settles where the transistor's transconductance gm ≈ 2(1 − 1/√K) / R. Its current is
I ∝ 1 / (μ · R²), where μ is the carrier mobility.

μ falls as the chip warms (roughly as T<sup>−1.5</sup>), so the reference pushes more current to keep gm
constant. With an ideal resistor, the ring's frequency followed and drifted **+2950 ppm/°C**, the opposite
sign to the plain ring (−1840 ppm/°C) and larger.

## 6. Cancelling temperature with the resistor's own tempco
Since I ∝ 1 / R², a resistor whose value rises with temperature pulls the current back down. Sweeping an
ideal resistor's tempco found a null at about **+1900 ppm/°C**. The GF180 PDK resistors (model file
`sm141064.ngspice`) range from about −1700 ppm/°C (high-resistance poly) to +3300 ppm/°C (salicided
diffusion). Two of them fit:

- **n-well** (about +2300 ppm/°C, about 1.3 kΩ/square) but with a large second-order term, so alone it bent the curve
  down when hot (−740 ppm/°C end to end);
- **n+ diffusion** (about +1360 ppm/°C, 60 Ω/square) with a much smaller second-order term.

**In series** (2 × 4.5 µm n-well + 2 × 100 µm n+) the drift is about −20 ppm/°C end to end, with a
±0.8 % bow (487.4 / 495.0 / 488.4 MHz at 0 / 27 / 70 °C). That is about 100× better than the ideal
resistor. This is the same trick a bandgap reference uses: add two effects with opposite temperature
behaviour so the first-order terms cancel.

## 7. Why starving flips the supply sensitivity
- Plain ring: a higher VDD gives more drive current, so f rises (+0.23 % per 10 mV).
- Starved ring with a fixed current: the current no longer rises with VDD, but the swing V in
  t<sub>d</sub> ≈ C · V / I still does. So f ∝ 1 / VDD: −0.30 % per 10 mV at 3.3 V, which is what we see
  (−0.27 to −0.29 %/10 mV).

So the remaining supply sensitivity comes from the swing, not the bias. The ways to remove it are to
regulate the ring's own supply, or to make the current rise with VDD exactly enough to cancel. This is the
next decision.
