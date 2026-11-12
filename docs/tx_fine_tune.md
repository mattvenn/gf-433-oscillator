# On-chip fine tuning and FSK for the 433.92 MHz TX

[![Made with Claude](https://img.shields.io/badge/Made%20with-Claude-D97757?logo=anthropic&logoColor=white)](https://claude.com/claude-code)

This page describes the fine-tuning path that replaces the board-driven `vctrl`: a 10-bit medium current
digital-to-analogue converter (DAC) on the ring's `vg` node, a first-order sigma-delta (ΣΔ) modulator that dithers
one extra DAC cell for sub-LSB resolution, frequency-shift keying (FSK) as a digital offset on the DAC word, and a
small digital macro with a Serial Peripheral Interface (SPI) register and a ÷16 / ÷64 / ÷1024 divider. With it the
chip needs nothing on the board except the dipole. The brief is `docs/handoff_tx_fine_tune.md`; the decisions
behind it (2026-11-10) are in `STATUS.md`.

All numbers are at 27 °C and VDD 3.3 V unless a corner is named (corner policy, `docs/handoff_autonomy.md`).

## Summary

| Item | Target | Result | Source |
|---|---|---|---|
| ΣΔ order, clock | simplest that meets the spurs | first order, 8 fractional bits, clocked by the TT `clk` (10-50 MHz) | `sim/tune/sd_model.py` |
| ΣΔ worst spur, 10 kHz-30 MHz, all 255 fractions | ≤ −40 dBc | −54.0 dBc at 25 MHz, −46.0 dBc at 10 MHz (LSB 50 kHz) | Fig. 1 |
| ΣΔ-added FM, 1-100 kHz | ≤ 2 kHz rms | 0.28 kHz rms worst (fraction 1/256, 10 MHz or 25 MHz clock) | Fig. 1 |
| Resolution with ΣΔ | ≤ 1 kHz | LSB / 256 = 115-150 Hz | |
| Medium DAC range | ≥ 1.3 × the largest coarse step | 1.58-1.59 × at tt / ss / ff / sf / fs | Table II |
| Medium DAC LSB | ≤ 50 kHz | 29.4 kHz (ss) … 38.5 kHz (ff) | Table II |
| Monotonic (Monte Carlo, N = 200) | DNL > −1 LSB in ≥ 99 % | 200 / 200 at tt, ss and ff (worst −0.76 LSB, ff) | Table III |
| rms FM, 1-10 kHz, reference path | ≤ 15 kHz (whole VCO) | 8.20 → 8.62 kHz at mid-scale, 9.08 kHz at full scale (tt) | Table IV |
| Extracted DAC on the extracted vco_top | LSB ≤ 50 kHz, range ≥ 1.3 steps | LSB 27.4 (ss) / 31.1 (tt) / 35.6 (ff) kHz, range 28.0-36.5 MHz; −0.2 % against the schematic DAC | Table VII |
| ΣΔ spurs, transistor level | ≤ −40 dBc | −58.2 dBc (fraction 77, model −60.1), −65.8 dBc (fraction ½), extracted DAC | Fig. 3 |
| FSK, ±3 LSB | ±100 kHz | 201-204 kHz step; settles to 2 % within 260 ns | Fig. 3 |
| Digital supply coupling | ≤ −40 dBc | −84.1 … −84.6 dBc at 25 MHz on the extracted layout (tt / ss / ff) with clock gating and the `vg` decap to VDD; −45.5 dBc with the decap to VSS | Fig. 3, Table X |
| Macro timing | 10-50 MHz clk, ~108 MHz ck | 50 MHz at tt 3.3 V (+1.6 ns); about 40 MHz at ss 125 °C 3.0 V | `macro/tx_fine` |
| Supply headroom | works at VDD 3.15 V | LSB and range unchanged (≤ 0.3 %) at 3.15, 3.0 and 2.8 V, tt and ss | Table V |
| Tile checks | LVS, DRC, antenna, CI | LVS match (7/7 mutations caught), magic DRC 0, antenna 0, KLayout only DCF.1a (fill); TT precheck passes in CI | |
| Tuning from cold, RP2350 model | about 1 kHz | 0.3-0.6 kHz at tt / ss / ff; FSK spread 199 kHz | Fig. 4 |

## The ΣΔ modulator

**Problem.** The ring's coarse step is about 21 MHz and the medium DAC's LSB is 30-40 kHz, but both ends of a
link should be tunable to about 1 kHz. A static DAC that fine would need about 15 bits. Dithering the last bit with
a ΣΔ modulator gets the resolution from time instead: the DAC toggles between two words, and the VCO's phase
integrates the toggling into the average frequency.

**Model.** The frequency error is LSB × (y[n] − x), with y[n] the modulator output and x the fractional input, held
for one clock. The phase is its integral. Every modulator in the model (first order, MASH 1-1) is periodic in
256 or 65536 clocks for 8-bit accumulators, so a rectangular window of that length gives exact spectral lines with
no leakage. One sideband of a small phase modulation is |φ_k| below the carrier, with φ_k the phase line (half the
sinusoid's peak), and the hold adds a sinc(f / f_clk) factor. The ring's own response (the `vg` node's
RC) is left out, so the numbers are an upper bound.

**Why first order is enough.** A first-order accumulator's residue is always under one LSB × one clock, so the
phase error stays below 2π × LSB / f_clk: 2π × 50 kHz / 25 MHz = 0.0126 rad. A signal bounded like that has no
sinusoidal component above (2 / π) × 0.0126 = 0.008 rad peak, about −48 dBc in one sideband, whatever the
fraction. The sweep finds −54.0 dBc (fraction 1/256, a 97.7 kHz sawtooth). Fraction ½ is −60 dBc at 12.5 MHz.
The handoff's quick laptop model gave −50 dBc there; the 10 dB difference is the single-sideband convention (6 dB)
and the hold's sinc at f_clk / 2 (3.9 dB).

![ΣΔ sweep](img/tx_fine_sd_sweep.png)

*Fig. 1. Worst spur from 10 kHz to 30 MHz (left) and the ΣΔ-added FM from 1 to 100 kHz (right) for every 8-bit
fraction, LSB 50 kHz, 25 MHz clock. First order: −54.0 dBc and 0.28 kHz rms at worst.*

MASH 1-1 lowers the worst spur only to −51.9 dBc (its multi-level output toggles two LSBs) and needs a 4-level
DAC input, so it gains nothing here. With 12 fractional bits, the extra fractions near 0, 1/5, 1/4, 1/3, ½ and
2/3 are no worse (−54.0 dBc, 0.20 kHz rms), but they add spurs down to 6 kHz. Eight bits already give LSB / 256
≈ 150 Hz.

*Table I. First-order ΣΔ, worst over all 255 fractions (`sd_model.py grid`).*

| LSB | clk 10 MHz | 12.5 MHz | 25 MHz | 50 MHz |
|---|---|---|---|---|
| 25 kHz | −52.0 dBc, 0.28 kHz | −54.0, 0.28 | −60.0, 0.14 | −66.0, 0.00 |
| 35 kHz | −49.1, 0.39 | −51.1, 0.39 | −57.1, 0.19 | −63.1, 0.00 |
| 50 kHz | −46.0, 0.55 | −48.0, 0.55 | −54.0, 0.28 | −60.0, 0.00 |
| 70 kHz | −43.1, 0.77 | −45.0, 0.77 | −51.1, 0.39 | −57.1, 0.00 |

(rms FM 1-100 kHz; at 50 MHz the lowest line, f_clk / 256 = 195 kHz, is above the band.) The design's LSB is
29-39 kHz, so a TT clock anywhere from 10 to 50 MHz meets −40 dBc with at least 6 dB to spare.

**The ΣΔ drives its own cell.** The ΣΔ output adds a separate 1-LSB cell; it doesn't carry into the 10-bit word.
So only one small cell toggles at the clock rate, and the 31 segments and 5 binary bits move only on a register
write or an FSK edge. The cell's mismatch to the LSB (0.93-1.07 in Monte Carlo) only scales the fractional
resolution by a few per cent, which the servo calibrates out by counting.

## The medium DAC

**Where it goes.** The ring is current-fed: plain inverters between VDD and a shared node `vg`, and the coarse DAC
sinks the ring current from `vg` to VSS. One coarse unit (nfet 1.2 / 5.33 µm on `vbnf`) carries Iu = 4.20 µA at tt
(3.96 ff … 4.46 µA ss) and is one coarse step, 19.1-25.4 MHz at the codes that reach 433.92 MHz. An ideal sink of
1.0 Iu on `vg` moves f by 18.8 (ss) … 24.4 MHz (ff), so the medium DAC is simply another sink on `vg`, sized in
units of Iu. Range ≥ 1.3 × the largest step (ff, 25.4 MHz) needs at least 1.36 Iu; the design uses 1.6 Iu for margin
on the gain chain.

**Circuit** (`sim/tune/mdac_sim.py`, `mdac_netlist()`).
1) Bias: two coarse units on `vbnf` sink 2 Iu from a diode of 128 PMOS units, so each PMOS unit carries
   I_L = Iu / 64 = 66 nA. The LSB tracks the coarse step over process and temperature, because both come from the
   constant-gm reference.
2) Array: PMOS units (W / L 1 / 4 µm, gate `pb`) in 31 unary segments of 32 units (word[9:5], thermometer-coded),
   binary groups of 16 / 8 / 4 / 2 / 1 units (word[4:0]), one ΣΔ cell (1 unit) and 32 always-on units. Each group's
   drain is steered by a PMOS pair, either to the output diode or to a matched dump diode, so a cell's current never
   stops and the bias line sees no load step when bits change.
3) Output mirror: the array current flows into a diode of 30 coarse units (`mo`), and 3 coarse units with gate
   `mo` sink from `vg`. I_out = (word + sd + 32) × I_L × 3 / 30, and full scale is 1023 / 64 × 3 / 30 = 1.60 Iu.
   The 32 always-on units keep the diode biased at word 0 (+0.05 Iu, a fixed offset).
4) `vctrl` is pulled to VSS by 200 kΩ of `ppolyf_u_1k`, so the fine NMOS leg is off by default and adds no supply
   sensitivity; ua[0] can still override it on the bench.

**Why a current gain.** The output current per LSB is only 6.6 nA. A unit sized for that current directly would
sit in deep weak inversion, where the current mismatch is about 30 × σVt. With the 10:1 current gain of the output
mirror, the 66 nA units run in moderate inversion (gm / Id about 12 V⁻¹), and a 1 × 4 µm PMOS unit has a σ of
about 2.9 % (σVt 2.3 mV, σβ 1.0 %, from the PDK's mismatch model). The output mirror's own mismatch is a common gain
error: it changes the LSB in hertz, not the monotonicity.

**Why 5 unary + 5 binary.** The only step that can go negative is a major carry, where one 32-unit segment replaces
the 31 units of the binary groups. Its σ is about 2.9 % × √63 = 0.23 LSB, so a −1 LSB step is more than 4σ away.
Six binary bits would double the units in that difference and put it near 3σ, at about the 99 % limit.

*Table II. Medium DAC on the schematic ring, at each corner's 433.92 MHz code, `vctrl` pulled down
(`mdac_sim.py fword`).*

| Corner | Code | f(word 0) MHz | f(word 1023) MHz | Range MHz | Coarse step MHz | Range / step | LSB kHz |
|---|---|---|---|---|---|---|---|
| tt | 9 | 441.16 | 475.34 | 34.19 | 21.55 | 1.59 | 33.4 |
| ss | 11 | 446.94 | 477.04 | 30.10 | 19.09 | 1.58 | 29.4 |
| ff | 7 | 432.38 | 471.72 | 39.34 | 24.68 | 1.59 | 38.5 |
| sf | 9 | 443.67 | 478.88 | 35.21 | 22.18 | 1.59 | 34.4 |
| fs | 10 | 451.46 | 483.83 | 32.37 | 20.42 | 1.59 | 31.6 |

The range is over 1.3 coarse steps everywhere, so the coarse + medium settings overlap with no gaps, and
433.92 MHz stays reachable at every corner (the schematic map's 433.92 codes move down by about one with the
medium DAC at mid-scale). The swing at `vg` and the ring nodes is unchanged (tt 1.81-3.43 V).

*Table III. Monotonicity, Monte Carlo (mismatch only, every PMOS / NMOS unit its own instance, N = 200 per corner,
`mdac_sim.py mc`; DC output current for all 1024 words, `vg` held at the corner's operating point).*

| Corner | DNL > −1 LSB | Worst DNL | 1st percentile of the per-sample minimum | LSB (output) | ΣΔ cell / LSB |
|---|---|---|---|---|---|
| tt | 200 / 200 | −0.721 | −0.700 | 6.52-6.81 nA | 0.928-1.071 |
| ss | 200 / 200 | −0.682 | −0.662 | 6.90-7.19 nA | 0.932-1.068 |
| ff | 200 / 200 | −0.763 | −0.738 | 6.17-6.46 nA | 0.924-1.075 |

*Table IV. rms FM from the reference and DAC current noise (`mdac_sim.py noise`: `.noise` of the coarse DAC's and
the medium DAC's drain currents with `vg` held, times K_I = df/dI from the ideal sink; 1-10 kHz).*

| Corner | Coarse path only | + medium, word 0 | word 512 | word 1023 |
|---|---|---|---|---|
| tt (code 9) | 8.20 kHz | 8.22 | 8.62 | 9.08 |
| ss (code 11) | 8.03 | 8.05 | 8.40 | 8.80 |
| ff (code 7) | 8.36 | 8.38 | 8.84 | 9.40 |

The medium DAC adds its own noise (1.2 kHz rms alone at mid-scale) and correlated `vbnf` noise, about +5 % at mid-scale
and +11 % at full scale. Its noise rises with the word, so the servo should keep the coarse code that puts 433.92
MHz nearest mid-scale. The ring's own (ISF) noise is not in this table; the whole-VCO number is a phase C job.

**Start-up.** The DAC loads `vbnf` only through the gates of two coarse units (about 0.05 pF on the 20 pF filter),
and at most adds 1.65 Iu to `vg`. That is less than the fine leg at `vctrl` = 3.3 V on top of code 31, which the
2026-11-08 map already covers. Ring start-up at code 0 (the weakest case) is unchanged, since the DAC only adds current.

**Power.** The array runs at (1024 + 32) × 66 nA = 70 µA plus 8.4 µA of bias, about 0.26 mW from VDPWR, against
12.6 mA for the TX driver.

**Supply headroom.** The PMOS cells need VDD − V(`mo`) for their own saturation plus the switch, and the output
mirror needs `vg` above its saturation voltage, so a low supply could compress the top of the range. It does not.
The ring, reference and DAC were simulated together (`sim/tune/mdac_sim.py fword --vdd`, schematic) down to 2.8 V:
the LSB and range stay within 0.3 % of their 3.3 V values. As VDD drops, `vg` falls with the ring's swing (1.89 V at
3.3 V, 1.42 V at 2.8 V, tt), which still leaves the cells over 1 V of headroom. At 3.15 V the DAC alone (vg held)
has DNL within ±0.015 LSB at all five corners, and the ΣΔ cell is 1.000 LSB.

*Table V. Medium DAC against VDD, at the 433.92 MHz code (schematic ring + DAC).*

| VDD | tt LSB | tt range | ss LSB | ss range | tt `vg` |
|---|---|---|---|---|---|
| 3.30 V | 33.4 kHz | 34.13 MHz (1.58 steps) | 29.4 kHz | 30.05 MHz (1.57 steps) | 1.89 V |
| 3.15 V | 33.3 | 34.11 (1.58) | 29.4 | 30.03 (1.58) | 1.75 |
| 3.00 V | 33.4 | 34.19 (1.58) | 29.3 | 30.02 (1.58) | 1.61 |
| 2.80 V | 33.3 | 34.09 (1.58) | 29.3 | 30.01 (1.57) | 1.42 |

(ff, sf and fs at 3.15 V: LSB 38.4, 34.4 and 31.6 kHz, range 1.58-1.59 steps, as at 3.3 V.)

## The digital macro (`src/tx_fine.v`, `macro/tx_fine`)

**What it does.** The macro is one LibreLane-hardened block (170 × 260 µm, Metal1-4, gf180mcuD 7-track cells at
3.3 V) with two clock domains:
- `clk` (the TT project clock, 25 MHz recommended): the SPI register, the FSK offset, the ΣΔ and the 37 DAC control
  lines (31 thermometer segments, 5 binary bits, the ΣΔ cell), registered and active low (0 V turns a cell on).
  Four integrated clock gates keep `clk` off the flops that are not changing (see "Clock gating" below);
- `ck` (f / 4, about 108 MHz, from the VCO's divider): a ripple divider giving f / 16 (27.1 MHz), f / 64 (6.78 MHz)
  and f / 1024 (424 kHz) on uo[1..3], and `ck` itself on uo[0] through a glitch-free gate that is off after reset.
  4 × ck = 433.92 MHz, so a toggling `ck` pin would be an on-channel spur.

*Table VI. Register map. SPI mode 0, MSB first, 16-bit frames while CS_n is low: [15] 1 = read / 0 = write,
[14:12] address, [11:0] data. SCLK must stay below clk / 8.*

| Address | Name | Bits | Reset | Use |
|---|---|---|---|---|
| 0 | MED_INT | [9:0] | 512 | medium DAC word |
| 1 | MED_FRAC | [7:0] | 0 | ΣΔ fraction (LSB / 256) |
| 2 | FSK_DEV | [11:0] | 0 | FSK deviation, 4.8 fixed point in LSBs |
| 3 | CTRL | [0] SD_EN, [1] CK_EN, [2] FSK_EN, [3] FSK_INV | 0 | |
| 4 | EFF_INT | [9:0] | read only | the integer word the DAC sees (after FSK and saturation) |
| 7 | ID | [11:0] | 0x433 | read only |

The effective word is {MED_INT, MED_FRAC} ± FSK_DEV (+ when ui[7] = 1, unless FSK_INV), saturated to 0 … 1023.996. It is
registered, then decoded, so the adder and the decoder sit in separate clock cycles.

**Clock gating.** *Problem:* every `clk` edge draws a burst of charge from the tile supply, which the ring shares
behind TT's 1.32 Ω power switch, so the edges frequency-modulate the carrier at 25 MHz. Without gating, all 150
`clk` flops and their clock tree switch on every edge, whether their data changes or not: 21.1 pC per cycle, which
puts a −32.1 dBc line at 25 MHz (target −40 dBc). *Fix:* four of the library's integrated clock gates (`icgtp`), so
only the flops that can change see the clock:

| Gate | Flops | Clock runs |
|---|---|---|
| (none) | 10 input synchronisers (SCLK, MOSI, CS_n, fsk) | every edge |
| `g_spi` | 68: the SPI shifter and the registers | while CS_n is low, and two clks after |
| `g_eff` | 18: the effective word `eff_q` | after an FSK edge, and while the SPI runs |
| `g_dec` | 46: `EFF_INT` and the 36 array lines | when `eff_q`'s integer part differs from them |
| `g_sd` | 9: the ΣΔ accumulator and cell | while SD_EN and the fraction is not zero (and until they have cleared) |

The outputs are the same, cycle for cycle. `g_eff` is enabled by the causes of a change (an FSK edge or SPI
activity) rather than by comparing the new word with the old, which would put the FSK adder in front of the gate
and cost 11 ns of setup slack. Clock-tree synthesis also used `clkbuf_16` buffers by default: 11 of them on the 14
always-clocked sinks, costing more than the flops. The macro now uses `clkbuf_2` / `clkbuf_4` only.

*Evidence:* `macro/tx_fine/power/clk_charge.py` takes each cell's power from OpenSTA (25 MHz `clk`, data static) and
traces the clock tree through the netlist to split it by gate. Per `clk` cycle, r10 (no gating) draws 21.1 pC and
r12 draws 4.48 pC with the ΣΔ running (3.22 pC idle), 4.7× less. In the supply bench that moves the 25 MHz line
from −32.1 to −45.5 dBc (Fig. 3, right). All the charge is put on the rising edge there, which is the worst case for
the 25 MHz line.

**Evidence.**
- Six cocotb tests (`test/`, `make` and `make GL=1`): reset values, write and readback, the ΣΔ bitstream bit for
  bit against `sim/tune/sd_model.py`, the FSK offset and saturation, the divider ratios and `ck` gate, and the
  clock gating (no gated edges when idle, only `g_sd` with the ΣΔ running, one `g_eff` and one `g_dec` edge per
  FSK edge, the ΣΔ cell held off with a zero fraction). They pass on the RTL and on the hardened netlist (the
  edge counts are RTL only). Three RTL mutations (a wrong carry bit, a wrong divider tap, a shifted FSK_DEV write)
  and three of the gate enables (`g_dec` always on, `g_sd` without its clear term, `g_spi` without its tail) each
  fail a test.
- LibreLane (run r12): magic and KLayout DRC, LVS and antenna are clean. At tt 3.3 V the 50 MHz `clk` and the
  140 MHz `ck` constraint both close (+1.6 ns). At the 3.3 V libraries' slow corner (ss, 125 °C, 3.0 V) the `clk`
  domain closes at about 40 MHz (−5.3 ns at 50 MHz). That corner is far from the room-temperature operating point,
  so 25 MHz has a wide margin.

## Layout and tile integration

![Tile](img/tt_wrapper.png)

*Fig. 2. The 2x2 tile: the digital macro (left strip), the medium DAC above vco_top (x 335-492 µm, y 118-222 µm), the
vctrl pull-down left of vco_top, and the 37 control lines through a Metal3 jog channel between the two TX risers.*

- **Medium DAC** (`layout/gen/mdac.py`, 156.8 × 104.2 µm): 40 PMOS rows of 32 fingers (1 / 4 µm) in mirrored
  pairs. Each pair shares a poly gate bar (`pb`) and an n+ tap rail. The segments are placed symmetrically about
  the binary rows, so a linear gradient cancels pairwise. Unused fingers in the binary rows are dummies with both
  ends on VDD. A steering pair per row is on the left, with Metal3 `mo` / `md` buses. The output mirror (30 + 3
  coarse units) and the bias device are below. The generator asserts that each group's unit count equals the
  simulated circuit's.
- **vco_top** brings `vg` and `vbnf` up to its top edge on Metal3 risers. Its own checks still pass
  (`check_top.sh`).
- **Tile** (`layout/gen/tt_wrapper.py`): the macro's VDD / VSS strap pairs at x 56.5 and 136.5 µm are extended to
  become the tile's stripes there. The control lines' jog columns are ordered so that no two Metal2 runs overlap.
  Each line also gets a short Metal3 hop just before the DAC: the long Metal2 run is then not connected to the
  switch gate when Metal2 is etched (antenna).
- **Checks:** block DRC / LVS / antenna clean for mdac and vctrl_pd, with three mutations caught in mdac. The
  xschem schematic `xschem/mdac.sch` matches both the layout source and the simulated circuit (`check.py`, with an
  SD-cell mutation). Tile LVS matches with 7 of 7 mutations caught, including the SPI pins swapped and two DAC lines
  swapped. Tile magic DRC 0, antenna 0, KLayout only DCF.1a (dummy fill). The TT precheck passes in CI.
- **A bug the cross-check found:** the layout first drew the ΣΔ cell as a 32-unit segment (`"sd".startswith("s")`),
  and every LVS passed because the LVS source came from the same code. The schematic-against-simulation comparison
  caught it.

## Transistor-level checks (`sim/tune/phase_c.py`)

Every bench below uses the extracted medium DAC (`layout/gen/pex_mdac.sh`, magic 8.3.642). Table VII also puts it
on the extracted vco_top (RC, `rcfix.py`); the other benches use the schematic ring with the reference. The DAC is
the C-only extraction with its parallel unit fingers merged (`layout/gen/pexmerge.py`, 1390 devices into 158
instances with `m`, exact for a C-only netlist). The RC extraction splits VDD into about 1000 small-R nodes and the
transient stops on "timestep too small"; at the DAC's µA currents the wire resistance does not matter, while the
wiring C on `mo`, `pb` and the cell nodes does. Unmerged, the transients ran about 100× slower. In these transients
`vbnf` is held at its DC value.
The 1 MΩ / 20 pF filter node otherwise drifts by about 0.1 mV/µs, which is about 2 nA of integration error on a
20 ms node. That drift moves f by tens of kHz per µs, which hides LSB-sized effects.

*Table VII. Medium DAC on the extracted vco_top (27 °C): extracted DAC, with the schematic DAC in brackets.*

| Corner | Code | f(word 0) | f(word 512) | f(word 1023) | LSB (full scale / 1023) | LSB at 512 → 513 |
|---|---|---|---|---|---|---|
| tt | 9 | 404.89 MHz | 420.97 | 436.66 | 31.06 kHz (31.12) | 31.06 kHz (31.12) |
| ss | 11 | 411.41 | 425.56 | 439.40 | 27.37 (27.42) | 27.37 (27.43) |
| ff | 7 | 396.60 | 415.08 | 433.05 | 35.63 (35.70) | 35.59 (35.68) |

The extracted DAC changes the LSB by −0.2 %. On the schematic ring it is within 0.3 % of the schematic DAC at all
five corners (LSB 29.3-38.3 kHz, range 1.57-1.59 steps), and its static transfer at tt (`vg` held, every word)
matches to 0.03 % at full scale with DNL −0.013 … +0.012 LSB, against −0.014 … +0.012. The extracted LSB on the
extracted ring is 0.93× the schematic value, close to the ring's own extracted factor. At ff, code 7 tops out at
433.11 MHz, so 433.92 MHz is reached from code 8. The range (more than 1.3 steps) ensures one of the two codes
covers it.

Table VII is the layout with the `vg` decap to VSS. The re-drawn layout with the decap to VDD (below) runs
0.10-0.11 % lower at every word and corner: 420.53 MHz at tt word 512 (−460 kHz), LSB 31.09 / 27.41 / 35.64 kHz
(tt / ss / ff), and ff code 7 tops out at 432.65 MHz, so the codes are unchanged. The cause is an open item
(Limits).

![Phase C](img/tx_fine_phase_c.png)

*Fig. 3. Extracted DAC. Left: FSK by ±3 LSB (word 509 ↔ 515), a 204 kHz step that settles within 260 ns; this
pair crosses the major carry at 512, and each edge overshoots the new frequency by about 450 kHz for one 20 ns window. Middle: mean
frequency against the ΣΔ fraction, 8.4 kHz (fraction 77) and 14.0 kHz (fraction ½) above the static LSB line.
Right: the phase spectrum
with the macro's measured clock charge on the tile supply (schematic ring, from 0.25 µs). With the `vg` decap to VSS:
−31.8 dBc at 25 MHz without clock gating (r10), −45.2 dBc with it (r12). With the decap to VDD: −67.9 and −79.4 dBc.*

- **Extracted against schematic DAC.** With the first 1 µs left out of both, the ΣΔ spurs are −58.2 / −65.8 dBc
  extracted against −57.9 / −64.3 dBc schematic (fractions 77 and ½), and the ΣΔ excess is 8.4 / 14.0 kHz against
  8.2 / 13.7 kHz. The extracted runs start about 6 kHz low and settle with a time constant of about 0.4 µs (`mo`
  charging its wiring C, 0.05 mV), so anything measured in the first microsecond carries that offset; the
  transient step at the 511 → 512 carry (37.2 against 33.6 kHz) is one such case, and the DC sweep above is the
  better measure of that step.
- **ΣΔ.** The spurs match the model: −58.7 dBc at 7.59 MHz for fraction 77 (model −60.1 dBc) and −65.2 dBc for
  fraction ½ (schematic DAC, from 0.25 µs). The mean frequency is not linear in the fraction. Each turn-on of the ΣΔ cell injects charge from
  its drain node (about 0.9 V swing) into `mo`: about 1.1 Hz·ms per edge. The excess therefore follows the edge
  rate, which is largest at fraction ½. The curve stays monotonic and continuous across word boundaries, so the
  counting servo absorbs it. A dummy switch or slower edges on that one cell would remove it.
- **Charge injection.** At the major carry 511 → 512 (16 cells switch): `mo` peaks 30 mV (ss 35 mV), `vg` 1.5 mV,
  and `vbnf` 0.07 mV in the run without the hold. The step is +33.3 kHz, so it stays monotonic. With the ΣΔ toggling,
  `mo` ripples 2.8 mV p-p.
- **FSK.** The step is the expected 6 LSB (201.4 kHz). The 40 ns spike at a major carry is about 0.1 rad of phase
  per edge. The RP2350 can avoid it by keeping the FSK pair on one side of a multiple of 32.
- **Digital supply coupling.** The model is the ring's VDD through the 1.32 Ω power switch with 9.8 pF of decap,
  plus the macro's current: 0.6 mA DC, a 1 ns triangle on each `clk` rising edge carrying the measured clock charge
  per cycle, and a 0.4 ns pulse on each `ck` edge. More decap does not help at this source impedance: the
  volt-seconds per edge are set by charge × 1.32 Ω, so the fix is less charge per edge (clock gating, above).
  Without gating (r10, 21.1 pC) VDD moves 57.6 mV p-p and the 25 MHz line is −32.1 dBc. With gating (r12, 4.48 pC)
  it is 15.4 mV p-p and −45.5 dBc, 5.5 dB inside the target. (The first estimate, 12 pC scaled from LibreLane's
  power report, gave −37.0 dBc; the measured charge of the ungated macro was higher.) These numbers are with the
  ring's `vg` decap to VSS; with it to VDD the same charge gives −79.4 dBc (next section).
- **FM noise** with the DAC is Table IV (`.noise`, schematic): +5 % at mid-scale.

### Supply coupling: the vg decap

*Problem.* With clock gating the 25 MHz line was −45.5 dBc at tt, but only 3.4 dB inside the target at ff
(−43.4 dBc). More decap on VDD barely helps: below 1.3 Ω at 25 MHz needs about 5 nF, about 1 mm² of MOS cap, and
the TT GF180 process has no metal-insulator-metal (MIM) capacitor (`docs/platform.md`). `sim/tune/spur_paths.py`
puts the measured ripple on one path at a time (schematic, tt):

*Table VIII. The 25 MHz line with the r12 supply ripple on one path only.*

| Rippled path | 25 MHz line |
|---|---|
| ring inverters' VDD only | −45.3 dBc |
| either DAC's VDD only | about −80 dBc |
| nothing | about −80 dBc |

All of it comes in through the ring. The current-fed ring runs between VDD and `vg`, so its own supply is
VDD − `vg`. The 3 pF decap tied `vg` to VSS, so at 25 MHz `vg` held still (2 mV p-p) while VDD moved 15 mV, and the
whole ripple appeared across the inverters.

*Fix.* Return the decap to VDD, so that `vg` rides with VDD above the reference loop's bandwidth. With no MIM it is
a PMOS gate capacitor: gate on `vg`, source, drain and body on VDD, in its own n-well, 6 × 29.82 / 4.12 µm (737 µm²,
the same area as the NMOS it replaces). Its C(V) is 3.06 pF at `vg` = 1.4 V and 3.01 pF at 2.0 V (tt), within
2.9-3.15 pF at every corner's `vg`; the NMOS was 2.9-3.1 pF (`sim/tune/vg_decap.py cv`). The layout is in
[ring_layout_v3.md](ring_layout_v3.md), "Decap".

*Evidence.* The supply sensitivity against ripple frequency (`vg_decap.py psr`, schematic, tt, a sine on VDD,
frequency deviation per mV) shows the mechanism directly. At DC both are the same, because the reference sets
`vg`; above about 1 MHz the decap to VSS holds `vg` and the sensitivity rises more than 100-fold.

*Table IX. Supply frequency modulation (FM), size of the deviation in kHz per mV of VDD ripple, with the decap to VSS and to VDD.*

| Ripple frequency | DC | 1 MHz | 3 MHz | 10 MHz | 25 MHz | 60 MHz |
|---|---|---|---|---|---|---|
| decap to VSS | 8.3 | 95 | 273 | 687 | 919 | 972 |
| decap to VDD | 8.3 | 6.7 | 6.4 | 8.5 | 14.8 | 30.6 |

The 25 MHz line, with r12's measured clock charge on the 1.32 Ω tile supply:

*Table X. The 25 MHz line, decap to VSS against decap to VDD (tt / ss / ff).*

| Bench | Decap to VSS | Decap to VDD |
|---|---|---|
| schematic ring, ideal 3 pF / PMOS model | −45.2 / −47.0 / −43.4 dBc | −79.8 / −80.3 / −80.8 dBc |
| extracted vco_top, decap swapped in the netlist | −46.1 / −47.8 / −44.2 dBc | −88.4 / −89.6 / −89.7 dBc |
| extracted vco_top, re-drawn layout (`layout/pex/vco_top_rcx.spice`) | −46.1 / −47.8 / −44.2 dBc | **−84.6 / −84.3 / −84.1 dBc** |

The 50 MHz line on the re-drawn layout is −83.7 / −84.6 / −82.5 dBc (was −51.6 / −53.5 / −49.8). The re-drawn
layout is about 4-5 dB worse than the netlist swap, which is still about 44 dB inside the target; the difference
was not investigated.

- **Size** (ideal C to VDD, tt): 1 / 2 / 3 / 4 / 6 pF give −68.6 / −76.6 / −80.5 / −77.5 / −74.1 dBc. The best is
  near 3 pF, so the size is kept. Why more C is worse above 3 pF is not explained at the time of writing.
- **Any C left from `vg` to VSS undoes the fix:** 2 pF to VDD with 1 pF to VSS gives −54.9 dBc. The re-drawn layout
  has 14.3 fF of wiring C from `vg` to VSS (0.5 % of the decap) and 24 fF to VDD.
- **TX driver** (extracted vco_top, C only, the driver behind the power switch): ring jitter with the driver on is
  0.11 / 0.13 / 0.10 ps rms at tt / ss / ff (was 0.25 / 0.20 / 0.29). The on/off shift, +0.03 … +0.05 %, is the DC
  drop through 1.32 Ω and is unchanged; so is the output power (+6.31 / +4.80 / +7.31 dBm).
- **Start-up** (5 corners × codes 0 and 31, 10 µs ramp, plus tt with a 1 µs ramp, with the real `vbn` filter): every
  case starts in the fundamental mode, `vg` never goes above VDD, and the ring starts 0.5-1 µs later than before.
- **Checks:** ring_core_v3 DRC (magic and KLayout), antenna and LVS, with a new LVS mutation (decap S/D on VSS)
  caught; vco_top and the tile LVS, DRC and antenna clean; the schematic netlist check passes.

## RP2350 tuning model (`sim/tune/rp2350_model.py`)

![Tuning sequence](img/tx_fine_servo.png)

*Fig. 4. Left: the frequency error after the coarse search and the LSB measurement, 0.3-0.6 kHz after two or three
10 ms reciprocal counts at tt / ss / ff. Right: a 27 → 35 °C warm-up in 60 s with the servo every 0.1 s, within
2.3 kHz at each packet start.*

The procedure and the counting methods are in [tuning.md](tuning.md). The model uses the schematic f(word), white FM
noise of 8 kHz rms (1-10 kHz), +120 ppm/°C and a +10 ppm RP2350 crystal. The residual error is the FM noise over a
10 ms count. A 1 s servo interval is too slow for the fastest warm-up (8.3 kHz); 0.1 s keeps it to 2.3 kHz. The
nonlinearity of the ΣΔ cell (Fig. 3, middle) is not in the model. The servo corrects it, but the first step lands
up to 0.4 LSB off.

## Limits and open items (at the time of writing)

- **Digital supply coupling** uses the charge per cycle from OpenSTA's cell power models with the SPEF, put into
  one 1 ns pulse per cycle. It is not a transistor-level simulation of the macro. Only the macro's own charge
  through the 1.32 Ω power switch is modelled: the ripple on the chip's VDPWR before the switch (from other
  projects) is unknown, and VSS is ideal, so ground ripple is not modelled either. How a VSS ripple couples in with the decap on VDD has
  not been simulated; it needs the TT ground path's resistance and inductance.
- **The re-drawn layout runs 0.10-0.11 % low** (−410 … −470 kHz at every word and corner, extracted RC) against the
  layout with the NMOS decap. It is not the decap device: on the old layout, the PMOS or an ideal 3 pF to VSS or to
  VDD in place of the NMOS all give the same f within 1 ppm (+180 ppm against the NMOS), and on the new layout an
  ideal 3 pF gives the PMOS's f within 1 ppm. `vg` sits 0.76 mV lower in the new layout, which accounts for about
  half of the shift (f ≈ I / (C × swing)). The C-only extraction moves f by only −0.011 % (the TX bench), so the
  wiring resistance of the re-drawn core is the likely place to look. It does not matter in use: the RP2350 servo
  measures and tunes the absolute frequency, and the codes, the LSB and the 1.3-step range are unaffected, so the
  mechanism was not pursued (2026-11-12). Swapping the core's extraction (old against new) inside the same top
  would locate it.
- **The medium DAC's extraction is C only.** The RC netlist does not converge in transients (above). Its static
  transfer from the RC netlist was not checked separately.
- **Monte Carlo** used the schematic DAC (unit instances), not the layout. The extracted DAC adds only C, which
  does not change the mismatch.
- **Corners:** 27 °C, VDD 3.3 V, except the supply-headroom check (Table V).
- **The ΣΔ cell's charge injection** (1.1 Hz·ms per edge) and the FSK major-carry spike are measured and explained,
  but not designed out, by choice (2026-11-12): the first bends f against the fraction without reversing it, and
  the servo measures the result; the second is avoided in firmware by keeping both FSK words inside one block of 32.
- **Crystal error:** tuning is relative to each RP2350's crystal (±30 ppm, ±13 kHz), so two boards agree to the sum
  of their crystal errors unless the receiver corrects it.

