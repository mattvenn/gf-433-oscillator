# Schematics

[![Made with Claude](https://img.shields.io/badge/Made%20with-Claude-D97757?logo=anthropic&logoColor=white)](https://claude.com/claude-code)

The VCO as real xschem schematics, generated from Python in `xschem/gen/` (one generator per block, `python3 xschem/gen/all.py` rebuilds them all). Every size and multiplicity is read from `sim/vco/vco_bias.py`'s `netlist()` at the chosen design, so the schematics can't drift from what I simulated:

- the winner reference (`sim/results/2026-11-08/winner_sets.txt`) with lnw = 5.023 µm;
- plus `topo=cfed kc=0.75 k=6 cvg=3e-12 ka=16 wfu=0.30 wff=0.30 rf=1e6 cf=20e-12`.

Click a link to open it in the online viewer. Previews (SVG and PNG, rendered headless by `xschem/gen/render.sh`) are in `docs/img/xschem/`.

- [vco_cfed](https://xschem-viewer.com/?file=https://github.com/mattvenn/gf-433-oscillator/blob/main/xschem/vco_cfed.sch): the whole VCO - the constant-gm reference drives the ring core through the 1 MΩ / 20 pF filter (vbnf).
- [cgm_ref](https://xschem-viewer.com/?file=https://github.com/mattvenn/gf-433-oscillator/blob/main/xschem/cgm_ref.sch): the constant-gm (beta-multiplier) reference - MN1/MN2 as 14 × 14 series-parallel arrays (each drawn as one vector instance), the 56/14 µm PMOS mirror, the n-well + n+ resistor, the 3-transistor start-up and the RC filter to vbnf.
- [ring_core_v3](https://xschem-viewer.com/?file=https://github.com/mattvenn/gf-433-oscillator/blob/main/xschem/ring_core_v3.sch): the ring, the DAC and the vg decap (nfet_03v3, 6 × 30.71/4 µm, as drawn in the layout). This is the cell in `layout/ring_core_v3.gds`, so it can be its LVS source.
- [cfed_ring](https://xschem-viewer.com/?file=https://github.com/mattvenn/gf-433-oscillator/blob/main/xschem/cfed_ring.sch): the 5 inverters (P 5/0.28 µm, N 2/0.28 µm). Every NMOS source sits on the shared node vg.
- [cfed_dac](https://xschem-viewer.com/?file=https://github.com/mattvenn/gf-433-oscillator/blob/main/xschem/cfed_dac.sch): the current DAC from vg to VSS - the base leg (× 6 units), the binary coarse legs (× 1 to × 16), the fine leg on vctrl, and the 5 coarse gate switches.
- [lsdiv](https://xschem-viewer.com/?file=https://github.com/mattvenn/gf-433-oscillator/blob/main/xschem/lsdiv.sch): the a0 level shifter, the TSPC ÷4 and the clock buffer B1 (ck = f(a0) / 4, full rail). Source: `sim/lsdiv/lsdiv.py block()`; design in `docs/lsdiv_design.md`.
  - [ls_ac](https://xschem-viewer.com/?file=https://github.com/mattvenn/gf-433-oscillator/blob/main/xschem/ls_ac.sch): Cc (2 fF metal-finger cap, drawn as an ideal C) into INV1-3; R1 / C1 low-pass the output back to INV1's input through LRB (negative DC feedback, duty about 50 %).
  - [tspc_t1](https://xschem-viewer.com/?file=https://github.com/mattvenn/gf-433-oscillator/blob/main/xschem/tspc_t1.sch) and [tspc_t2](https://xschem-viewer.com/?file=https://github.com/mattvenn/gf-433-oscillator/blob/main/xschem/tspc_t2.sch): TSPC toggle flip-flops (÷2 each), 1/2 µm and 0.6/1.2 µm.

## Notes
- **GF180 symbols:** the viewer only knows the xschem, sky130 and IHP libraries. So I copied the 5 PDK symbols I use into `xschem/symbols/` (from open_pdks 7b70722e). The schematics reference them as `symbols/nfet_03v3.sym`, the same name xschem finds in the PDK, and the viewer finds them next to the `.sch`.
- **Ideal parts:** the 20 pF filter cap is ideal (`devices/capa.sym`), the same as in `vco_bias`. On silicon it will be a MOS cap, which isn't laid out yet.
- **What isn't drawn:** vco_bias's 1 Ω `Rvbn`, which only gives n1 the name vbn, is just the net vbn here. The wiring caps `Cw*` are left out too.
- **The bit buses:** they are separate pins (bit0…bit4, bitb0…bitb4), so the names match the layout's pins.

## Checks (`python3 xschem/gen/check.py`, results in `build/xsch/check.txt`)
Every `.sch` is netlisted headless with xschem (`xschem/gen/netlist.sh`) and compared with netgen, using the gf180mcuD setup:
- **ring_core_v3 against the layout's LVS source:** it matches uniquely with no property errors. I checked it at wfu 0.30 against `layout/gen/export_core_v3.py` and against the committed `layout/ref/ring_core_v3.spice`.
- **The layout against ring_core_v3:** this netlist is the LVS source of `layout/ring_core_v3.gds` (`layout/gen/check_v3.sh`). It matches uniquely with no property errors, and two deliberately broken copies (one DAC leg's m, one switch gate) both fail.
- **vco_cfed against `vco_bias.netlist()`:** it matches uniquely with no property errors (70 devices). netgen treats the PDK resistors as black boxes and doesn't compare their sizes, so a device-by-device size diff covers every W/L/m, resistor W/L and C value. It finds no differences.
- **lsdiv against `lsdiv.py block()`:** it matches uniquely (34 devices), and the device-by-device size diff finds no differences. A copy with R1 10 % longer fails the size diff, as it should (netgen alone would miss it).
- **Mutation test:** in a copy of cfed_dac.sch I changed the bit-3 leg from m = 8 to m = 7. All 3 comparisons fail on it, as they should.
- **Simulation:** I simulated vco_cfed from the xschem netlist at tt, 27 °C, code 9 and vctrl 1.65 V, with the same deck as vco_bias. It runs at 503.98 MHz, against 504.16 MHz for vco_bias (-0.036 %). Both draw 0.451 mW and both have vbn = 1.232 V. vco_bias here has its wiring caps off, so like for like.
- **Measurement threshold:** I measured the frequency at mid-swing, not at VDD/2. The cfed ring swings from vg (about 1.8 V) up to VDD, so a0 never crosses 1.65 V. That makes `vco_bias.deck()`'s VDD/2 measurement fail for cfed, and `topo_cmp.py` uses mid-swing too.

## Superseded
These hand-drawn SVGs in `docs/schematic/` came before the xschem schematics. I've kept them, but the xschem files are the reference now:
- `ring_stage.svg`, `ring_loop.svg`, `ring_bias.svg` (with `ring_svg.py`)
- `dac_cfed.svg` (with `dac_svg.py`)
