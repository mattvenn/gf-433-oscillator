# Bring-up planning and design for test

## Design for test (decide at architecture time)
- Raw modes: key internal decisions (a comparator output, a block enable) straight out on, or in
  from, a uio pin, so the bench can bypass the digital.
- A debug transmission gate that puts an internal analog node on a ua pin, isolated when off, so an AWG
  can drive the downstream analog directly. Tap a low-Z node; nA of pad leakage on a high-Z node is mV
  of offset.
- Trim freeze/override registers, so offsets can be measured on silicon.
- A fallback for every risky option (e.g. single-ended use of a differential pair of pins).
- Give every output stage a defined off state (both arms low, no DC across the load).
- A ring oscillator (or any free-running block) on a pin is a cheap speed calibration point for the
  next chip.

## Plan
- Stage the order: power + digital alone → each analog function alone → everything together. Each
  stage uses only parts already checked; stop on a failure.
- Every test row has how, expected (with its sim or model source), and a result column. Keep raw
  captures in `bench/data/<date>/`. Flag anything > 3 dB off, or outside the expected band, as a
  finding.
- Pin-safety rules up front: DC blocks and attenuation between strong outputs and instruments, and
  limits on what may be driven into which pin (thin-oxide pins at 0–1.8 V).
- Strapped-reset handover (avoids contention): hold reset with the straps driven, stop the clock,
  release reset, pulse one clock to latch, switch the host pins to inputs, restart the clock.
- Write the firmware spec early: RP2350 PIO rates, edge-triggered counting of 1-clock pulses, and test
  patterns generated from the bit-exact model.
- Measure the real board supplies (3 TT boards were 1.80–1.81 / 3.30 V) and feed them back into the
  verification limits.

## Feeding silicon back into design
- The workflow was measure → model → schematic/RTL → ASIC. Real waveforms captured on a scope can be
  injected into the models and testbenches.
- Re-extract a previously measured block with today's flow to get a silicon/extracted factor
  (×0.843–0.866 for rings), then design to target ÷ factor.
- Fitting the corner of a measured part takes two circuits: an inverter trip point (N/P ratio) and a
  ring frequency (speed).
