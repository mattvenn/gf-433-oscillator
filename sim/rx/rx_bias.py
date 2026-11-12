#!/usr/bin/env python3
"""
Receiver bias (option B): one resistor-referenced NMOS current reference shared by the LNA, baseband and limiters.

  en -> inverter -> enb (to every block's enable switches)
  VDD -> Msw (pfet, gate enb) -> Rref (ppolyf_u_1k) -> nb : MB, a diode-connected unit NMOS (m = 1)
  nb pulled to VSS by Moff (gate enb) when disabled, so every mirror is off.
  IU = (VDD - Vgs) / Rref ~ 25 uA; each block mirrors m x the unit (W UW / L UL).

A resistor reference is supply- and process-dependent (about +-20 %); first pass. The VCO's constant-gm reference
(vbn) could feed this later, but it is a quiet node the ring depends on, so it is not loaded here.

    python3 sim/rx/rx_bias.py      # print the netlist
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rxc  # noqa: E402

UW, UL = 2.0, 0.5          # unit mirror device (um)
S = dict(rref=94e3, mb=1)


def mirror(name, d, g, m, s='VSS'):
    """m units of the reference device: the current is m x IU."""
    return rxc.nfet(name, d, g, s, UW, UL, int(m))


def block(s=None):
    s = dict(S, **(s or {}))
    return ('.subckt rx_bias VDD VSS en enb nb\n'
            + rxc.inv('Ie', 'en', 'enb', 0.42, 1.0)
            + rxc.pfet('Msw', 'rt', 'enb', 'VDD', 2.0)
            + rxc.res('Rref', 'rt', 'nb', s['rref'])
            + mirror('MB', 'nb', 'nb', s['mb'])
            + rxc.nfet('Moff', 'nb', 'enb', 'VSS', 0.42)
            + rxc.scap('Cnb', 'nb', 1e-12)
            + '.ends\n')


if __name__ == '__main__':
    print(block(), end='')
