#!/usr/bin/env python3
"""
Check the generated schematics are the simulated circuit (run from the repo root, laptop):

  1. netlist every xschem/*.sch headless (xschem/gen/netlist.sh)
  2. netgen ring_core_v3 vs layout/gen/export_core_v3.py at the chosen wfu (the LVS source of the v3 layout)
     and vs the committed layout/ref/ring_core_v3.spice (both wfu 0.30; the layout-side LVS is layout/gen/check_v3.sh)
  3. netgen vco_cfed vs sim/vco/vco_bias.py netlist() at the chosen design (Cw* dropped, Rvbn merged,
     Cvg -> the v3 MOS decap, as the schematic)
  3b. netgen + device sizes: lsdiv vs sim/lsdiv/lsdiv.py block() (the simulated level shifter + /4, drawn passives);
      mutation: R1's length +10 % in a copy of the netlist -> the device diff must fail (netgen black-boxes the
      PDK resistors, so only the size diff sees it)
  3c. netgen + device sizes: tx_drv (tx_split, tx_arm) vs sim/tx/tx_drv.py block() (the simulated TX driver);
      mutations: the output stage M5n's width -10 % (netgen and the device diff must fail); TGn's gate on VSS
      instead of VDD (a wiring error: netgen must fail)
  3d. netgen: mdac vs layout/gen/mdac.py lvs_source() and (dummies removed) vs sim/tune/mdac_sim.py mdac_netlist();
      mutation: the SD cell's m 1 -> 2 must fail both
  4. mutation: one DAC leg's m changed in a copy of cfed_dac.sch -> both comparisons must fail
  5. simulate vco_cfed from the xschem netlist at tt 27 C, code 9, vctrl 1.65 V, against vco_bias's own
     deck at the same point (same deck, only the circuit swapped); |df| < 0.5 %

    python3 xschem/gen/check.py [--no-sim]
Outputs: build/xsch/ (netlists, *.report, sim decks and logs, check.txt)
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
from common import P, REPO, vco_bias, decap_size  # noqa: E402

OSIC = str(Path(REPO) / 'tools' / 'osic-mac')
OUT = Path(REPO) / 'build' / 'xsch'
SETUP = '$PDK_ROOT/$PDK/libs.tech/netgen/${PDK}_setup.tcl'
LOG = []


def log(s):
    print(s)
    LOG.append(s)


def sh(cmd):
    r = subprocess.run([OSIC, 'bash', '-c', f'cd {REPO} && {cmd}'], capture_output=True, text=True)
    return r.stdout + r.stderr


def netgen(a, cell_a, b, cell_b, tag):
    rel = OUT.relative_to(REPO)
    sh(f'cd {rel} && netgen -batch lvs "{a} {cell_a}" "{b} {cell_b}" {SETUP} {tag}.report > {tag}.log 2>&1')
    rep = (OUT / f'{tag}.report').read_text()
    ok = ('Final result: Circuits match uniquely' in rep and not re.search(r'property errors', rep, re.I)
          and 'do not match' not in rep)
    final = [ln for ln in rep.splitlines() if re.search(r'Final result|property errors|do not match|Netlists', ln)]
    return ok, '; '.join(dict.fromkeys(final[-3:]))


def gen(outdir, sets=''):
    env = dict(os.environ, XSCH_OUT=str(outdir), XSCH_SET=sets)
    outdir.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(HERE / 'all.py')], env=env, check=True, capture_output=True)


def vco_ref(p, path):
    """vco_bias.netlist(p) as a .subckt with the schematic's ports and nets (Cw* dropped, Rvbn merged,
    Cvg -> the v3 MOS decap)."""
    import vco_cfed
    body, _ = vco_bias.netlist(p)
    m, L, W = decap_size(p)
    lines = []
    for ln in body.splitlines():
        t = ln.split()
        if not t or t[0].startswith('Cw') or t[0] == 'Rvbn':
            continue
        t = [common.RENAME.get(x, x) for x in t]
        if t[0] == 'Cvg':
            t = f'XDC VDD vg VDD VDD pfet_03v3 w={W}u l={L}u m={m}'.split()   # PMOS gate cap to VDD
        lines.append(' '.join(t))
    path.write_text(f'* vco_bias.netlist() at the chosen design, as a subckt (xschem/gen/check.py)\n'
                    f'.subckt vco_ref {" ".join(vco_cfed.PINS)}\n' + '\n'.join(lines) + '\n.ends\n')


SUBCKTS = ('cfed_ring', 'cfed_dac', 'ring_core_v3', 'cgm_ref', 'vco_cfed', 'lsdiv', 'ls_ac', 'tspc_t1', 'tspc_t2',
           'tx_drv', 'tx_split', 'tx_arm', 'mdac')


def devices(path):
    """Multiset of device sizes in a netlist: (model, w, l, m) / (model, r_width, r_length) / ('c', value),
    ignoring nets and names. Every subckt in the xschem netlist is used once, so the union of their
    device lines is the flat circuit. Catches what netgen can't: the PDK resistors are black boxes to it."""
    from collections import Counter
    out = Counter()
    text = re.sub(r'\n\+', ' ', Path(path).read_text())     # join SPICE continuation lines (xschem wraps long ones)
    subs = set(SUBCKTS) | set(re.findall(r'(?im)^\.subckt\s+(\S+)', text))
    for ln in text.splitlines():
        t = ln.split()
        if not t or t[0][0] not in 'XxCc' or t[0].startswith('**'):
            continue
        kv = {k.lower(): v for k, v in (x.split('=', 1) for x in t if '=' in x)}
        pos = [x for x in t[1:] if '=' not in x]
        num = lambda v: round(common._num(v.lower().replace('e-6', 'u')) if not re.fullmatch(r'[-+\d.]+e-?\d+', v)
                              else float(v), 18)
        if t[0][0] in 'Cc':
            out[('c', float(pos[2]))] += 1
        elif pos[-1] in subs:
            continue
        elif 'fet' in pos[-1]:
            out[(pos[-1], num(kv['w']), num(kv['l']), int(kv.get('m', 1)))] += 1
        else:
            out[(pos[-1], round(float(kv['r_width']), 12), round(float(kv['r_length']), 12))] += 1
    return out


def diff(a, b):
    da, db = devices(a), devices(b)
    return da == db, [f'{k}: {da.get(k, 0)} vs {db.get(k, 0)}' for k in sorted(set(da) | set(db), key=str)
                      if da.get(k, 0) != db.get(k, 0)]


SIM_PT = (9, 1.65, 27, 3.3)


def sim_decks(p):
    """vco_bias.deck() at SIM_PT (from the DC op, uic=False: the 20 us filter can't settle from 0 in a
    uic run); for the schematic the same deck with the circuit swapped for the xschem netlist."""
    import vco_cfed
    ref = vco_bias.deck(dict(p, cw=0.0), 'typical', [SIM_PT], uic=False)
    # cfed swings vg..VDD (vg ~1.8 V): measure at the mid-swing, as sim/vco/topo_cmp.py, not at VDD/2
    vdd = SIM_PT[3]
    t12 = (f"meas tran t1 WHEN v(a0)={vdd / 2} RISE=1 TD=100n\n"
           f"meas tran t2 WHEN v(a0)={vdd / 2} RISE=11 TD=100n\n")
    assert t12 in ref
    ref = ref.replace(t12, "meas tran amin MIN v(a0) FROM=100n TO=200n\nmeas tran amax MAX v(a0) FROM=100n TO=200n\n"
                      "let vth = (amin + amax)/2\nmeas tran t1 WHEN v(a0)=$&vth RISE=1 TD=100n\n"
                      "meas tran t2 WHEN v(a0)=$&vth RISE=11 TD=100n\n")
    body, _ = vco_bias.netlist(dict(p, cw=0.0))
    old = body.replace('XMN1 n1 n1 ', 'XMN1 n1i n1 ', 1) + 'vir n1 n1i 0\n'
    assert old in ref
    pins = ' '.join(x if x not in ('VDD', 'VSS') else {'VDD': 'vdd', 'VSS': '0'}[x] for x in vco_cfed.PINS)
    net = (OUT / 'vco_cfed.spice').read_text()
    (OUT / 'vco_cfed_sim.spice').write_text(re.sub(r'(?m)^\.end\s*$', '', net))   # the netlist's own .end would end the deck
    sch = ref.replace(old, f'.include {OUT}/vco_cfed_sim.spice\nxdut {pins} vco_cfed\n')
    sch = sch.replace('meas tran ir AVG i(vir)', 'meas tran ir AVG i(vdd)')
    return ref, sch


def run_sim(name, text):
    (OUT / f'{name}.cir').write_text(text)
    rel = OUT.relative_to(REPO)     # from the repo root, so ngspice reads its .spiceinit (as vco_bias.run())
    log_ = sh(f'ngspice -b {rel}/{name}.cir > {rel}/{name}.log 2>&1; grep ^RES {rel}/{name}.log')
    m = re.search(r'^RES \S+ \S+ \S+ \S+ \S+ (\S+) (\S+) (\S+)', log_, re.M)
    return (float(m.group(1)), float(m.group(2)), float(m.group(3))) if m else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rel = OUT.relative_to(REPO)
    # 1. netlists of the committed schematics
    log(sh(f'xschem/gen/netlist.sh xschem {rel}').strip())
    # 2. ring_core_v3 vs the layout's LVS source
    subprocess.run([sys.executable, str(Path(REPO) / 'layout/gen/export_core_v3.py'), '--set', f'wfu={P["wfu"]}',
                    '--set', f'wff={P["wff"]}', '-o', str(OUT / 'ref_ring_core_v3.spice')], check=True, capture_output=True)
    ok1, r1 = netgen('ring_core_v3.spice', 'ring_core_v3', 'ref_ring_core_v3.spice', 'ring_core', 'lvs_core')
    log(f'ring_core_v3 (wfu {P["wfu"]}) vs export_core_v3.py: {"PASS" if ok1 else "FAIL"}  [{r1}]')
    shutil.copy(Path(REPO) / 'layout/ref/ring_core_v3.spice', OUT / 'layout_ref.spice')
    ok2, r2 = netgen('ring_core_v3.spice', 'ring_core_v3', 'layout_ref.spice', 'ring_core', 'lvs_core_ref')
    log(f'ring_core_v3 vs layout/ref/ring_core_v3.spice: {"PASS" if ok2 else "FAIL"}  [{r2}]')
    # 3. vco_cfed vs vco_bias.netlist()
    vco_ref(P, OUT / 'ref_vco_cfed.spice')
    ok3, r3 = netgen('vco_cfed.spice', 'vco_cfed', 'ref_vco_cfed.spice', 'vco_ref', 'lvs_vco')
    log(f'vco_cfed vs vco_bias.netlist(): {"PASS" if ok3 else "FAIL"}  [{r3}]')
    okd, dd = diff(OUT / 'vco_cfed.spice', OUT / 'ref_vco_cfed.spice')
    log(f'vco_cfed vs vco_bias.netlist(), device-by-device sizes (incl. R, C): {"PASS" if okd else "FAIL"} '
        f'({sum(devices(OUT / "vco_cfed.spice").values())} devices){" " + "; ".join(dd) if dd else ""}')
    ok3 &= okd
    # 3b. lsdiv vs the simulated block
    import importlib.util
    spec = importlib.util.spec_from_file_location('sim_lsdiv', Path(REPO) / 'sim' / 'lsdiv' / 'lsdiv.py')
    LS = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(LS)
    (OUT / 'ref_lsdiv.spice').write_text(LS.block())
    ok6, r6 = netgen('lsdiv.spice', 'lsdiv', 'ref_lsdiv.spice', 'lsdiv', 'lvs_lsdiv')
    ok7, d7 = diff(OUT / 'lsdiv.spice', OUT / 'ref_lsdiv.spice')
    log(f'lsdiv vs lsdiv.py block(): {"PASS" if ok6 else "FAIL"}  [{r6}]; device sizes '
        f'{"PASS" if ok7 else "FAIL"} ({sum(devices(OUT / "lsdiv.spice").values())} devices){" " + "; ".join(d7) if d7 else ""}')
    mtxt = re.sub(r'(XR1 .*r_length=)([\d.]+)(e-6)', lambda m: f'{m.group(1)}{float(m.group(2)) * 1.1:.3f}{m.group(3)}',
                  (OUT / 'lsdiv.spice').read_text())
    (OUT / 'mut_lsdiv.spice').write_text(mtxt)
    ok8, d8 = diff(OUT / 'mut_lsdiv.spice', OUT / 'ref_lsdiv.spice')
    log(f'mutation R1 length +10 %: device diff {"FAIL (expected)" if not ok8 else "PASS (BAD: not caught)"}  [{"; ".join(d8)}]')
    ok3 &= ok6 and ok7 and not ok8 and mtxt != (OUT / 'lsdiv.spice').read_text()
    # 3c. tx_drv vs the simulated TX driver
    spec = importlib.util.spec_from_file_location('sim_tx_drv', Path(REPO) / 'sim' / 'tx' / 'tx_drv.py')
    TX = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(TX)
    (OUT / 'ref_tx_drv.spice').write_text(TX.block())
    ok9, r9 = netgen('tx_drv.spice', 'tx_drv', 'ref_tx_drv.spice', 'tx_drv', 'lvs_tx_drv')
    ok10, d10 = diff(OUT / 'tx_drv.spice', OUT / 'ref_tx_drv.spice')
    log(f'tx_drv vs tx_drv.py block(): {"PASS" if ok9 else "FAIL"}  [{r9}]; device sizes '
        f'{"PASS" if ok10 else "FAIL"} ({sum(devices(OUT / "tx_drv.spice").values())} devices){" " + "; ".join(d10) if d10 else ""}')
    ttxt = (OUT / 'tx_drv.spice').read_text()
    mtxt, nm = re.subn(r'(?m)^(XM5n .*?W=)([\d.]+)u', lambda m: f'{m.group(1)}{float(m.group(2)) * 0.9:g}u', ttxt, count=1)
    (OUT / 'mut_tx_drv.spice').write_text(mtxt)
    ok11, r11 = netgen('mut_tx_drv.spice', 'tx_drv', 'ref_tx_drv.spice', 'tx_drv', 'lvs_mut_tx_drv')
    ok12, d12 = diff(OUT / 'mut_tx_drv.spice', OUT / 'ref_tx_drv.spice')
    log(f'mutation M5n W -10 %: netgen {"FAIL (expected)" if not ok11 else "PASS (BAD: not caught)"}  [{r11}]; '
        f'device diff {"FAIL (expected)" if not ok12 else "PASS (BAD: not caught)"}  [{"; ".join(d12)}]')
    gtxt, ng = re.subn(r'(?m)^(XTGn \S+ )VDD ', r'\1VSS ', ttxt, count=1)
    (OUT / 'mut2_tx_drv.spice').write_text(gtxt)
    ok13, r13 = netgen('mut2_tx_drv.spice', 'tx_drv', 'ref_tx_drv.spice', 'tx_drv', 'lvs_mut2_tx_drv')
    log(f'mutation TGn gate VDD -> VSS: netgen {"FAIL (expected)" if not ok13 else "PASS (BAD: not caught)"}  [{r13}]')
    ok3 &= ok9 and ok10 and nm == 1 and not ok11 and not ok12 and ng == 1 and not ok13
    # 3d. mdac (the medium DAC) vs the layout's LVS source (layout/gen/mdac.py lvs_source(), dummies included) and,
    #     with its dummies removed, vs the simulated circuit (sim/tune/mdac_sim.py mdac_netlist()); mutation: the SD
    #     cell's m 1 -> 2 (the 2026-11-10 layout bug drew it as 32 units) must fail both
    spec = importlib.util.spec_from_file_location('lay_mdac', Path(REPO) / 'layout' / 'gen' / 'mdac.py')
    LM = importlib.util.module_from_spec(spec); spec.loader.exec_module(LM)
    LM.lvs_source(OUT / 'ref_mdac_layout.spice')
    mtxt = (OUT / 'mdac.spice').read_text()
    hdr = re.search(r'^\.subckt mdac (.*?)\n(?!\+)', mtxt, re.M | re.S).group(1).replace('\n+', ' ')
    sys.path.insert(0, str(Path(REPO) / 'sim' / 'tune'))
    import mdac_sim as MS
    body = MS.mdac_netlist(MS.base_p(), MS.M, g='vbnf')
    body = re.sub(r'(?<=\s)0(?=\s)', 'VSS', body)
    body = re.sub(r'(?<=\s)vdd(?=\s)', 'VDD', body).replace(' vgo ', ' vg ')
    body = re.sub(r'^Roff coff mo 1\n', '', body, flags=re.M).replace(' coff ', ' mo ')
    (OUT / 'ref_mdac_sim.spice').write_text(f'.subckt mdac {hdr}\n{body}.ends\n')
    (OUT / 'mdac_nodum.spice').write_text(re.sub(r'^XMDUM .*\n', '', mtxt, flags=re.M))
    ok14, r14 = netgen('mdac.spice', 'mdac', 'ref_mdac_layout.spice', 'mdac', 'lvs_mdac_layout')
    ok15, r15 = netgen('mdac_nodum.spice', 'mdac', 'ref_mdac_sim.spice', 'mdac', 'lvs_mdac_sim')
    log(f'mdac vs layout/gen/mdac.py lvs_source(): {"PASS" if ok14 else "FAIL"}  [{r14}]')
    log(f'mdac (dummies removed) vs mdac_sim.mdac_netlist(): {"PASS" if ok15 else "FAIL"}  [{r15}]')
    mm, nmm = re.subn(r'^(XMUsd .* )m=1$', r'\1m=2', mtxt, flags=re.M)
    if not nmm:   # m=1 is not written: add it
        mm, nmm = re.subn(r'^(XMUsd .*)$', r'\1 m=2', mtxt, flags=re.M)
    (OUT / 'mut_mdac.spice').write_text(mm)
    (OUT / 'mut_mdac_nodum.spice').write_text(re.sub(r'^XMDUM .*\n', '', mm, flags=re.M))
    ok16, r16 = netgen('mut_mdac.spice', 'mdac', 'ref_mdac_layout.spice', 'mdac', 'lvs_mut_mdac_layout')
    ok17, r17 = netgen('mut_mdac_nodum.spice', 'mdac', 'ref_mdac_sim.spice', 'mdac', 'lvs_mut_mdac_sim')
    log(f'mutation MUsd m 1 -> 2: vs layout {"FAIL (expected)" if not ok16 else "PASS (BAD: not caught)"}  [{r16}]; '
        f'vs sim {"FAIL (expected)" if not ok17 else "PASS (BAD: not caught)"}  [{r17}]')
    ok3 &= ok14 and ok15 and nmm == 1 and not ok16 and not ok17
    # 4. mutation: FC_3 (bit 3, m = 8) -> m = 7 in a copy
    mut = OUT / 'mut'
    if mut.exists():
        shutil.rmtree(mut)
    shutil.copytree(Path(REPO) / 'xschem', mut, ignore=shutil.ignore_patterns('gen'))
    sch = (mut / 'cfed_dac.sch').read_text()
    new, n = re.subn(r'(name=FC_3\n(?:[^\n]*\n)*?m=)8\n', r'\g<1>7\n', sch, count=1)
    assert n == 1, 'mutation not applied'
    (mut / 'cfed_dac.sch').write_text(new)
    sh(f'xschem/gen/netlist.sh {mut.relative_to(REPO)} {mut.relative_to(REPO)}')
    ok4, r4 = netgen('mut/ring_core_v3.spice', 'ring_core_v3', 'ref_ring_core_v3.spice', 'ring_core', 'lvs_mut_core')
    ok5, r5 = netgen('mut/vco_cfed.spice', 'vco_cfed', 'ref_vco_cfed.spice', 'vco_ref', 'lvs_mut_vco')
    log(f'mutation FC_3 m 8 -> 7: ring_core_v3 {"FAIL (expected)" if not ok4 else "PASS (BAD: not caught)"}  [{r4}]')
    log(f'mutation FC_3 m 8 -> 7: vco_cfed {"FAIL (expected)" if not ok5 else "PASS (BAD: not caught)"}  [{r5}]')
    okm, dm = diff(mut / 'vco_cfed.spice', OUT / 'ref_vco_cfed.spice')
    log(f'mutation FC_3 m 8 -> 7: device diff {"FAIL (expected)" if not okm else "PASS (BAD: not caught)"}  [{"; ".join(dm)}]')
    allok = ok1 and ok2 and ok3 and not ok4 and not ok5 and not okm
    # 5. simulation cross-check
    if '--no-sim' not in sys.argv:
        ref, sch = sim_decks(P)
        rr, rs = run_sim('sim_ref', ref), run_sim('sim_sch', sch)
        if rr and rs:
            d = rs[0] / rr[0] - 1
            log(f'sim tt 27C code {SIM_PT[0]} vctrl {SIM_PT[1]}: vco_bias f {rr[0] / 1e6:.2f} MHz (P {rr[1] * 1e3:.3f} mW, '
                f'vbn {rr[2]:.4f} V), xschem f {rs[0] / 1e6:.2f} MHz (P {rs[1] * 1e3:.3f} mW, vbn {rs[2]:.4f} V): '
                f'df {d * 100:+.3f} % {"PASS" if abs(d) < 0.005 else "FAIL"}')
            allok &= abs(d) < 0.005
        else:
            log('sim: no result, see build/xsch/sim_*.log')
            allok = False
    log('CHECK ' + ('OK' if allok else 'FAIL'))
    (OUT / 'check.txt').write_text('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
