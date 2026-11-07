# Further reading: Harald Pretl's IIC-JKU courses

Three open courses by Harald Pretl (Institute for Integrated Circuits, JKU Linz), hosted on GitHub.
The first two shaped many of the layout and robustness rules in this skill.
Read the relevant chapter before starting block layout or a new schematic set.

- **Analog Circuit Design**: <https://github.com/iic-jku/analog-circuit-design>
  - Start with the appendix, *The Circuit Designer's Etiquette*:
    <https://github.com/iic-jku/analog-circuit-design/blob/main/content/appendix/_app_circuit_designers_etiquette.qmd>
  - It covers naming, schematic style, robustness and mixed-signal rules.
- **Design of Complex ICs**: <https://github.com/iic-jku/design-complex-ic>
  - The layout chapter:
    <https://github.com/iic-jku/design-complex-ic/blob/main/content/layout/_sec_layout.qmd>
  - It covers floorplanning, matching, antenna, density and extraction levels.
- **Radio-Frequency Integrated Circuits** (JKU course 336.023): <https://github.com/iic-jku/radio-frequency-integrated-circuits>
  - Rendered book: <https://iic-jku.github.io/radio-frequency-integrated-circuits/rfic.html>
  - Chapters: fundamentals, LNA, mixer, oscillator, PLL, power amplifier, spurs, transceivers,
    simulation.
  - Read it before designing any high-frequency block (amplifiers, oscillators, drivers), and for
    spur and coupling planning on a mixed-signal tile.
- Tools: **IIC-OSIC-TOOLS**, the Docker image used for everything: <https://github.com/iic-jku/IIC-OSIC-TOOLS>.
  Its issues are worth searching when a tool misbehaves.

## Points from them that proved most useful in practice

**From the etiquette guide**
- Guard rings and substrate contacts go to a *quiet* potential. Tying them to a noisy supply injects
  noise. Separate noisy and clean supplies, and separate noisy and quiet circuits physically.
- Run VDD and VSS as pairs to keep loop inductance small (not one net on the left of the tile and the
  other on the right).
- Unit-sized devices with dummies in the schematic, so matching doesn't have to be forced in layout.
- Buffer incoming digital controls locally, with an inverter on the analog block's own supply.
- Decouple to the right potential, and check the on-chip decap × bond-wire L resonance.
- Name internal nets (net labels in the layout generators), so LVS reports and extracted netlists are
  readable.
- No floating nodes in the off state. Simulate power-down and power-up, not just "on".
- Use one schematic for both simulation and LVS, with current probes (0 V sources) added by the
  testbench, not drawn in.

**From the layout chapter**
- The common mistake is laying out lots of cells and then ending up with a mess at assembly. Plan the
  floorplan top-down first: target outline, pin sides and aspect per block.
- Hot spots: keep matched pairs away from high-power drivers, or on a symmetry line through them.
- Check antenna rules: long metal to a small gate.
- Group PMOS and NMOS into rows (the diffusion-to-nwell spacing is large). Share diffusion between
  series devices.
- Matching:
  - unit devices with the same W and L;
  - the same orientation and current direction, no snaking;
  - dummies tied to a defined potential, never floating;
  - common centroid for pairs;
  - symmetric wiring parasitics;
  - no low metal over sensitive devices;
  - matched PMOS kept away from nwell edges (the well-proximity effect).
- Per-finger gate resistance < 1/gm at high frequency. Contact both ends if needed.
- Extraction levels: full-chip RC is very slow, so use C-only for most nets and RC where it matters.
  KLayout-PEX (`kpex`) supports sky130A and can cross-check magic.
- Density/fill: find out whether the shuttle adds fill (TT does) rather than assuming either way.
