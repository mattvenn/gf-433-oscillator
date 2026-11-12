#!/usr/bin/env python3
"""
Receiver LO path (option B): the I and Q LO buffers and the Q tap level shifter.

  I: lsdiv's `ls` (from a0, always running: the TX shares it) -> rx_lobuf -> lo_i / lob_i
  Q: a second ls_ac on a2 or a3 (rx_lsq: the lsdiv level shifter, same sizes, behind a PMOS header gated by
     enb) -> rx_lobuf -> lo_q / lob_q

  rx_lobuf (in, en -> lo, lob):  x = NAND2(in, en)  ->  splitter (tx_split topology: an inverter on x, then two
     inverters to a, one inverter + an always-on transmission gate to b, weak cross-coupled inverters pulling the
     edges together)  ->  two arms NAND2(., en) + 3 tapered inverters:  lo = in & en,  lob = !in & en.
     en = 0: x = 1, both arms held low, so every mixer switch is off and nothing after the first NAND toggles.

The Q level shifter keeps its 2 fF Cc on the ring whatever en is (the ring load stays put); its header cuts the
supply of INV1 (biased at its trip point: a class-A current) and the rest when en = 0.

    python3 sim/rx/rx_lo.py            # print the netlist
    python3 sim/rx/rx_lo.py ring [--jobs 20] [--tstop 1.2e-6] [--only ...]   # phase A1 bench (below)
    python3 sim/rx/rx_lo.py summary
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'sim' / 'lsdiv'))
sys.path.insert(0, str(REPO / 'sim' / 'tx'))
import rxc  # noqa: E402
import lsdiv as LD  # noqa: E402  (read-only: ls_c, S, ring, ls_x, freq)
import tx_drv  # noqa: E402  (read-only: the TX splitter, a load on ls)
import rx_mix  # noqa: E402

S = dict(
    wnand_n=0.5, wnand_p=0.6,          # input NAND (on ls: keep it small)
    wt=0.42, wa1=0.5, wa2=1.0, wb1=1.5, wtgn=1.0, wtgp=2.5, wx=0.42,   # splitter, as tx_split (N widths)
    anand_n=1.0, anand_p=1.25,         # arm NAND2
    arm=(0.8, 2.0, 5.0),               # arm inverters N widths (P = kp x N)
    kp=2.5,
    whead=10.0, mhead=2, cq=1e-12,     # Q tap header PMOS (m x W) and its supply decap
    tap='a2',                          # Q tap node on the ring
)


def lobuf(s=None):
    s = dict(S, **(s or {}))
    k = s['kp']
    out = ('.subckt rx_lobuf VDD VSS in en lo lob\n'
           + rxc.pfet('G0a', 'x', 'in', 'VDD', s['wnand_p']) + rxc.pfet('G0b', 'x', 'en', 'VDD', s['wnand_p'])
           + rxc.nfet('G0c', 'x', 'in', 'g0s', s['wnand_n']) + rxc.nfet('G0d', 'g0s', 'en', 'VSS', s['wnand_n'])
           + rxc.inv('T', 'x', 't', s['wt'], k * s['wt'])
           + rxc.inv('A1', 't', 'ta', s['wa1'], k * s['wa1']) + rxc.inv('A2', 'ta', 'a', s['wa2'], k * s['wa2'])
           + rxc.inv('B1', 't', 'tb', s['wb1'], k * s['wb1'])
           + rxc.nfet('TGn', 'b', 'VDD', 'tb', s['wtgn']) + rxc.pfet('TGp', 'b', 'VSS', 'tb', s['wtgp'])
           + rxc.inv('XA', 'b', 'a', s['wx'], k * s['wx']) + rxc.inv('XB', 'a', 'b', s['wx'], k * s['wx']))
    for arm, i, o in (('P', 'a', 'lo'), ('N', 'b', 'lob')):
        out += (rxc.pfet(f'{arm}Ga', f'{arm}y0', i, 'VDD', s['anand_p'])
                + rxc.pfet(f'{arm}Gb', f'{arm}y0', 'en', 'VDD', s['anand_p'])
                + rxc.nfet(f'{arm}Gc', f'{arm}y0', i, f'{arm}gs', s['anand_n'])
                + rxc.nfet(f'{arm}Gd', f'{arm}gs', 'en', 'VSS', s['anand_n']))
        for j, wn in enumerate(s['arm'], 1):
            out += rxc.inv(f'{arm}{j}', f'{arm}y{j - 1}', o if j == len(s['arm']) else f'{arm}y{j}', wn, k * wn)
    return out + '.ends\n'


def lsq(s=None):
    """The Q tap: a copy of lsdiv's level shifter (ls_c with the drawn passives, same sizes) with the same load on
    its output as lsdiv's `ls` has: a dummy first TSPC stage (tspc_t1, its q1 unloaded) and a dummy TX tap inverter
    (tx_drv's T). The level shifter's delay is about 120 deg at 434 MHz and depends on that load, so only a matched
    copy keeps the I/Q phase at the ring's 72 deg. The whole copy sits behind a PMOS header (gate enb) with its own
    decap; lsq is pulled low when off. Cpa / Cpg (lsdiv's Cc plate parasitics) are left out; the benches add them."""
    s = dict(S, **(s or {}))
    t = (LD.ls_c(dict(LD.S, real=1), inp='aq', out='lsq', vdd='vq')
         + LD.tspc('D1', 'lsq', 'q1', 'vq', LD.S['t1n'], LD.S['t1p'])
         + rxc.inv('TT', 'lsq', 'tt', tx_drv.S['wt'], tx_drv.S['kp'] * tx_drv.S['wt'], vdd='vq'))
    lines = []
    for ln in t.splitlines():
        tk = ln.split()
        if tk[0] in ('Cpa', 'Cpg'):
            continue
        lines.append(' '.join({'0': 'VSS'}.get(x, x) for x in tk))
    return ('.subckt rx_lsq VDD VSS aq qenb lsq\n' + rxc.pfet('Hq', 'vq', 'qenb', 'VDD', s['whead'], m=s['mhead'])
            + rxc.scap('Cq', 'vq', s['cq'])
            + rxc.nfet('Dq', 'lsq', 'qenb', 'VSS', 0.42) + '\n'.join(lines) + '\n.ends\n')


def block(s=None):
    """rx_lo: the Q level shifter + the two LO buffers. Ports: VDD VSS ls aq en qenb lo_i lob_i lo_q lob_q.
    qenb gates the Q tap copy's supply (low = on). rx_top ties it to VSS (the copy always on, so rx_en doesn't move
    the ring; 0.15-0.26 mA with rx_en = 0); tying it to enb instead turns the copy off with rx_en (about 0 A, but the
    ring moves by 14-23 fine-DAC LSB): the review's choice (docs/rx_design.md)."""
    s = dict(S, **(s or {}))
    return (lobuf(s) + lsq(s)
            + '.subckt rx_lo VDD VSS ls aq en qenb lo_i lob_i lo_q lob_q\n'
            + 'xlq VDD VSS aq qenb lsq rx_lsq\n'
            + 'xbi VDD VSS ls en lo_i lob_i rx_lobuf\n'
            + 'xbq VDD VSS lsq en lo_q lob_q rx_lobuf\n'
            + '.ends\n')


# ---- phase A1 bench: ring (extracted core rcx + schematic reference) + extracted lsdiv (I) + TX splitter (load on
# ls, TX off) + rx_lo with the Q level shifter on a2 or a3 + both mixers (switch gates as the real load; their
# RF/BB nodes held at the LNA output DC) --------------------------------------------------------------------------
CODES = dict(typical=(8, 9, 10), ss=(10, 11, 12), ff=(6, 7, 8), sf=(8, 9, 10), fs=(9, 10, 11))
CASES = ('base', 'a2', 'a3', 'a2off')      # base: no RX at all (the TX-only reference); a2off: rx_en = 0


def ring_deck(corner, code, case, tstop=1.2e-6, vdd=3.3, vctrl=1.65, s=None, qmodel='x', opt=''):
    s = dict(S, **(s or {}))
    p = dict(LD.vb.P, **LD.WINNER, **LD.CFED)
    body, ics = LD.ring(p, 'pex')
    bits = ''.join(f'vbit{b} bit{b} 0 {vdd if (code >> b) & 1 else 0}\nvbitb{b} bitb{b} 0 {0 if (code >> b) & 1 else vdd}\n'
                   for b in range(5))
    rx = ''
    save = 'v(a0) v(a2) v(a3) v(lsout) v(vg)'
    if qmodel == 'x':
        iblk = LD.ls_x(LD.S)                     # the extracted lsdiv: Xlsdiv vls 0 a0 ck lsout q1 lsdiv_x
    else:
        iblk = (LD.block() + 'Xlsdiv vls 0 a0 ck lsout lsdiv\n' + f'Cwire ck 0 {LD.S["cwire"]}\n'
                + 'XFF 0 ck ffq vff vff 0 0 gf180mcu_fd_sc_mcu7t5v0__dffq_1\n'
                + f'Cpa a0 0 {LD.S["cpa"]}\nCpg xlsdiv.lg 0 {LD.S["cpg"]}\n')
    if case != 'base':
        en = 0 if case.endswith('off') else vdd
        tapn = case[:2]
        hq = '0' if 'k' in case else 'enb'      # 'k': the Q tap copy stays powered (header always on)
        if qmodel == 'x':
            # Q tap = a copy of the extracted lsdiv (LS + the /4 as the matched load) behind the header, + the dummy
            # TX tap inverter; its ck carries the same 20 fF + DFF load as the I copy
            q = (f'Xhq vq {hq} vrxq vrxq pfet_03v3 w={s["whead"]}u l=0.28u m={s["mhead"]}\nCq vq 0 {s["cq"]}\n'
                 f'vrxq vrxq 0 {vdd}\n'
                 f'Xlsq vq 0 {tapn} ckq lsq q1q lsdiv_x\nCwq ckq 0 {LD.S["cwire"]}\n'
                 'XFFq 0 ckq ffqq vq vq 0 0 gf180mcu_fd_sc_mcu7t5v0__dffq_1\n'
                 + rxc.inv('TTq', 'lsq', 'ttq', tx_drv.S['wt'], tx_drv.S['kp'] * tx_drv.S['wt'], vdd='vq', vss='0')
                 + f'XDq lsq {hq} 0 0 nfet_03v3 w=0.42u l=0.28u\n'
                 f'Xlo vrx 0 lsout lsq en enb lo_i lob_i lo_q lob_q rx_lo_x\n')
            sub = lobuf(s) + ('.subckt rx_lo_x VDD VSS ls lsq en enb lo_i lob_i lo_q lob_q\n'
                              'xbi VDD VSS ls en lo_i lob_i rx_lobuf\nxbq VDD VSS lsq en lo_q lob_q rx_lobuf\n.ends\n')
            lsqn = 'lsq'
        else:
            q = (f'Cpaq {tapn} 0 {LD.S["cpa"]}\nCpgq xlo.xlq.lg 0 {LD.S["cpg"]}\n'
                 f'Xlo vrx 0 lsout {tapn} en {hq} lo_i lob_i lo_q lob_q rx_lo\n')
            sub = block(s)
            lsqn = 'xlo.lsq'
        rx = (f'{sub}{rx_mix.block()}Ven en 0 {en}\nVenb enb 0 {vdd - en}\n{q}'
              f'vrx vrx 0 {vdd}\nVrf rfp 0 2.15\nVrfn rfn 0 2.15\n'
              'Xmi vrx 0 rfp rfn bip bin lo_i lob_i rx_mix\nXmq vrx 0 rfp rfn bqp bqn lo_q lob_q rx_mix\n'
              'Rbb1 bip 0 1e9\nRbb2 bin 0 1e9\nRbb3 bqp 0 1e9\nRbb4 bqn 0 1e9\n')
        save += f' v(lo_i) v(lob_i) v(lo_q) v(lob_q) v({lsqn}) i(vrx)' + (' i(vrxq)' if qmodel == 'x' else '')
    blk = iblk + f'{tx_drv.split(tx_drv.S)}Xtxs vls 0 lsout txa txb tx_split\n'
    t0 = 0.6 * tstop
    return f"""* rx_lo ring {corner} code {code} case {case}
{LD.hdr(corner)}.lib {rxc.PDK}/sm141064.ngspice diode_typical
vdd vdd 0 {vdd}
vls vls 0 {vdd}
vdv vdv 0 {vdd}
vff vff 0 {vdd}
vctrl vctrl 0 {vctrl}
{bits}{body}{blk}{rx}.ic {ics}
.control
option temp=27
{opt}save {save}
tran 5p {tstop} {t0} 5p
set filetype=binary
write out.raw {save}
quit
.endc
.end
"""


def analyse(d, case, vdd=3.3, qmodel='x'):
    pl = rxc.read_raw(d / 'out.raw')[0]['vars']
    t = pl['time']
    a0 = pl['v(a0)']
    mid = (a0.min() + a0.max()) / 2
    f, _ = LD.freq(t, a0, mid)
    r = dict(f=f, ls_duty=rxc.duty(t, pl['v(lsout)'], vdd / 2))
    if case == 'base':
        return r
    T = t[-1] - t[0]
    r['i_rx'] = -float(np.trapezoid(pl['i(vrx)'], t)) / T
    if 'i(vrxq)' in pl:
        r['i_q'] = -float(np.trapezoid(pl['i(vrxq)'], t)) / T
        r['i_rx'] += r['i_q']
    if case.endswith('off'):
        r['lo_max'] = float(max(pl[k].max() for k in ('v(lo_i)', 'v(lob_i)', 'v(lo_q)', 'v(lob_q)')))
        return r
    per = 1 / f
    ri = rxc.xings(t, pl['v(lo_i)'], vdd / 2)
    rq = rxc.xings(t, pl['v(lo_q)'], vdd / 2)
    ph = []
    for x in ri[1:-1]:
        nq = rq[rq > x]
        if len(nq):
            ph.append(((nq[0] - x) / per * 360) % 360)
    phq = float(np.median(ph))
    r.update(iq_phase=phq if phq <= 180 else phq - 360,       # + : Q lags I
             duty_lo_i=rxc.duty(t, pl['v(lo_i)'], vdd / 2), duty_lob_i=rxc.duty(t, pl['v(lob_i)'], vdd / 2),
             duty_lo_q=rxc.duty(t, pl['v(lo_q)'], vdd / 2), duty_lob_q=rxc.duty(t, pl['v(lob_q)'], vdd / 2),
             lsq_duty=rxc.duty(t, pl['v(lsq)' if qmodel == 'x' else 'v(xlo.lsq)'], vdd / 2))
    # overlap of lo and lob (both above VDD/2) as a fraction of the period, I arm
    both = (pl['v(lo_i)'] > vdd / 2) & (pl['v(lob_i)'] > vdd / 2)
    none = (pl['v(lo_i)'] < vdd / 2) & (pl['v(lob_i)'] < vdd / 2)
    dt = np.diff(t, append=t[-1])
    r.update(overlap_i=float(np.sum(dt[both]) / T), gap_i=float(np.sum(dt[none]) / T))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', nargs='?', default='print')
    ap.add_argument('--jobs', type=int, default=20)
    ap.add_argument('--tstop', type=float, default=1.2e-6)
    ap.add_argument('--corners', default='typical,ss,ff,sf,fs')
    ap.add_argument('--cases', default=','.join(CASES))
    ap.add_argument('--tag', default='lo_ring')
    ap.add_argument('--q', default='x')
    a = ap.parse_args()
    if a.mode == 'print':
        print(block(), end='')
        return
    if a.mode == 'retry':
        # re-run the rows whose log shows a failed operating point, with gmin stepping forced off and a source ramp
        f = rxc.BUILD / a.tag / 'rows.json'
        dat = json.loads(f.read_text())
        def redo(k):
            r = dat['rows'][k]
            c = {'tt': 'typical'}.get(r['corner'], r['corner'])
            name = f"{r['corner']}_c{r['code']}_{r['case']}"
            for opt in ('option rshunt=1e12\n', 'option rshunt=1e12 gminsteps=0\n', 'option srcsteps=50\n'):
                d, log, bad = rxc.run(name, ring_deck(c, r['code'], r['case'], dat['tstop'], qmodel=r.get('q', 'x'), opt=opt),
                                      sub=a.tag)
                if not bad:
                    break
            nr = analyse(d, r['case'], qmodel=r.get('q', 'x'))
            nr.update(corner=r['corner'], code=r['code'], case=r['case'], q=r.get('q', 'x'), bad=bad, retry=opt.strip())
            print(json.dumps({kk: (round(v, 6) if isinstance(v, float) else v) for kk, v in nr.items()}), flush=True)
            return k, nr
        for k, nr in rxc.pmap(redo, [k for k, r in enumerate(dat['rows']) if r.get('bad')], a.jobs):
            dat['rows'][k] = nr
        f.write_text(json.dumps(dat, indent=1))
        return
    if a.mode == 'ring':
        jobs = [(c, code, case) for c in a.corners.split(',') for code in CODES[c] for case in a.cases.split(',')]
        t0 = time.time()

        def one(j):
            c, code, case = j
            name = f'{rxc.CN[c]}_c{code}_{case}'
            d, log, bad = rxc.run(name, ring_deck(c, code, case, a.tstop, qmodel=a.q), sub=a.tag)
            try:
                r = analyse(d, case, qmodel=a.q)
            except Exception as e:  # noqa: BLE001
                r = dict(error=str(e), log=log.splitlines()[-5:])
            r.update(corner=rxc.CN[c], code=code, case=case, q=a.q, bad=bad)
            print(json.dumps({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
            return r
        rows = rxc.pmap(one, jobs, a.jobs)
        out = rxc.BUILD / a.tag / 'rows.json'
        out.write_text(json.dumps(dict(S=S, tstop=a.tstop, wall_s=time.time() - t0, rows=rows), indent=1))
        print('wrote', out, f'{time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
