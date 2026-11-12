#!/usr/bin/env python3
"""
Receiver top level (option B): every block as one .subckt rx_top, the source of truth for xschem/rx_top.sch.

  rx_top VDD VSS inp inn ls aq en q_i q_q
    inp / inn : the two RX ua pins (through the TT pad path) -> rx_lna (two stages, I and Q outputs)
    ls        : lsdiv's level-shifter output (the I LO, shared with the TX)
    aq        : the ring node for the Q tap (a2 in the vco_top, see rx_lo.S['tap'])
    en        : rx_en (1 = receive); enb is made in rx_bias
    q_i, q_q  : comparator outputs, full swing, to uo[4] / uo[5]
  rx_bias -> nb (all tails), enb; rx_lo -> lo_i / lob_i / lo_q / lob_q; rx_mix x2; rx_bb x2; rx_lim x2;
  DC: the RX supply decap (nfet gate cap, gate VDD), next to the LO buffers that switch at 434 MHz.

    python3 sim/rx/rx_top.py          # print the full netlist (every subckt)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rxc  # noqa: E402
import rx_bias  # noqa: E402
import rx_lna  # noqa: E402
import rx_lo  # noqa: E402
import rx_mix  # noqa: E402
import rx_bb  # noqa: E402
import rx_lim  # noqa: E402

S = dict(dcw=10.0, dcl=10.0, dcm=12)          # supply decap: 12 x 100 um2 nfet gate cap ~ 4.9 pF

PINS = ['VDD', 'VSS', 'inp', 'inn', 'ls', 'aq', 'en', 'q_i', 'q_q']


def top(s=None):
    s = dict(S, **(s or {}))
    return ('.subckt rx_top ' + ' '.join(PINS) + '\n'
            'xb VDD VSS en enb nb rx_bias\n'
            'xlna VDD VSS inp inn ri_p ri_n rq_p rq_n nb enb rx_lna\n'
            'xlo VDD VSS ls aq en VSS lo_i lob_i lo_q lob_q rx_lo\n'   # qenb = VSS: the Q tap copy always on
            'xmi VDD VSS ri_p ri_n bi_p bi_n lo_i lob_i rx_mix\n'
            'xmq VDD VSS rq_p rq_n bq_p bq_n lo_q lob_q rx_mix\n'
            'xbbi VDD VSS bi_p bi_n oi_p oi_n nb enb rx_bb\n'
            'xbbq VDD VSS bq_p bq_n oq_p oq_n nb enb rx_bb\n'
            'xli VDD VSS oi_p oi_n q_i nb enb rx_lim\n'
            'xlq VDD VSS oq_p oq_n q_q nb enb rx_lim\n'
            + rxc.fet('DC', 'VSS', 'VDD', 'VSS', 'VSS', 'nfet_03v3', s['dcw'], s['dcl'], s['dcm'])
            + '.ends\n')


def block(s=None):
    """Every subckt the receiver needs (lsdiv's ls_ac / tspc_t1 are inside rx_lsq, flat)."""
    return (rx_bias.block() + rx_lna.block() + rx_lo.block() + rx_mix.block() + rx_bb.block() + rx_lim.block()
            + top(s))


if __name__ == '__main__':
    print(block(), end='')
