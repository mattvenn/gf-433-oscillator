#!/usr/bin/env python3
"""
Receiver bias (option B): one constant-gm (beta-multiplier) reference shared by the LNA, baseband and limiters.

  en -> inverter -> enb (to every block's enable switches)
  MN1 (diode, the unit device, W UW / L UL) on nb; MN2 (K x MN1) with Rb in its source; PMOS 1:1 mirror MP1 / MP2
  from VDD through a header Msw (gate enb); a start-up (MS1-MS3, as the VCO's reference).
  gm(MN1) = (2 / Rb) (1 - 1 / sqrt(K)) in strong inversion (ln K / Rb in weak): every stage that mirrors nb at the
  unit's current density has gm proportional to 1 / Rb, so a stage gain gm x RL is a resistor ratio and holds over
  process (the resistor-referenced first version spread the baseband gain by 8 dB from ss to ff).
  nb is pulled to VSS by Moff (gate enb) when disabled, so every mirror is off. IU ~ 25 uA at tt.
The VCO's own constant-gm reference (vbn) is not loaded: it is a quiet node the ring depends on.

    python3 sim/rx/rx_bias.py      # print the netlist
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rxc  # noqa: E402

UW, UL = 2.0, 0.5          # unit mirror device (um)
S = dict(rb=5.2e3, k=4, mb=1)


def mirror(name, d, g, m, s='VSS'):
    """m units of the reference device: the current is m x IU."""
    return rxc.nfet(name, d, g, s, UW, UL, int(m))


def block(s=None):
    s = dict(S, **(s or {}))
    return ('.subckt rx_bias VDD VSS en enb nb\n'
            + rxc.inv('Ie', 'en', 'enb', 0.42, 1.0)
            + rxc.pfet('Msw', 'vh', 'enb', 'VDD', 4.0)
            + mirror('MN1', 'nb', 'nb', s['mb'])
            + mirror('MN2', 'n2', 'nb', s['k'] * s['mb'], s='nr')
            + rxc.res('Rb', 'nr', 'VSS', s['rb'], 2.0, 'ppolyf_u')
            + rxc.pfet('MP1', 'nb', 'n2', 'vh', 4.0, 1.0, 2)
            + rxc.pfet('MP2', 'n2', 'n2', 'vh', 4.0, 1.0, 2)
            + rxc.pfet('MS1', 'x', 'VSS', 'vh', 0.42, 10.0)
            + rxc.nfet('MS2', 'x', 'nb', 'VSS', 2.0)
            + rxc.nfet('MS3', 'n2', 'x', 'nb', 1.0)
            + rxc.nfet('Moff', 'nb', 'enb', 'VSS', 0.42)
            + rxc.nfet('Moff2', 'x', 'enb', 'VSS', 0.42)
            + rxc.scap('Cnb', 'nb', 1e-12)
            + '.ends\n')


if __name__ == '__main__':
    print(block(), end='')
