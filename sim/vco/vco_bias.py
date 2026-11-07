#!/usr/bin/env python3
"""Phase-1 step 1: single-ended current-starved ring biased from a constant-gm reference.

  beta-multiplier (MN1 diode, MN2 = K x MN1 with source R, PMOS mirror, 3-device start-up)
      -> vbn (gate of MN1)
  every stage's NMOS foot = k x unit (gate vbn) + binary coarse legs (gate g_b = bit ? vbn : 0)
                          + fine leg (gate vctrl, long L, small)
  a master copy of the foot legs (scaled by `mr`) feeds a PMOS diode -> vbp for every head.

Usage (repo root):
  python3 sim/vco/vco_bias.py sweep [--set k=v ...]      # f vs code x vctrl, tt 27C (+ vbn, Iref)
  python3 sim/vco/vco_bias.py pvt --code 15 --vctrl 1.65  # corners x 0/27/70C x VDD +-4.5%
Outputs: build/vco/bias_<tag>/
"""
import argparse, os, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OSIC = os.environ.get("OSIC", str(REPO / "tools/osic-mac"))
SAB = 0.5
P = dict(n=5, L=0.28, wn=2.0, wp=5.0,          # core
         ls=1.0, wfu=0.25, k=16, bits=5,         # foot unit, base weight, coarse bits
         whead=6.0, mr=1.0, wpb=1.0,             # head W, master scale, PMOS diode W (x total weight/24)
         wff=0.25, lff=4.0,                      # fine leg per stage (gate vctrl)
         w1=2.0, l1=1.0, kb=4, r=6e3, tcr=0.0,   # beta multiplier: MN1 W/L, K, R (ohm), R tc1 (1/K)
         wpm=4.0, lpm=1.0,                       # beta multiplier PMOS mirror
         cw=2e-15, rideal=1,
         rw=2.0, lnw=12.0, lnp=0.0)        # real R: width, nwell length, n+ diff length (um)                     # wiring C; rideal=1: ideal R with tc1=tcr, else ppolyf_u
CORNERS = ("typical", "ss", "ff", "sf", "fs")


def fet(name, d, g, s, b, typ, w, l, m=1):
    a = w * SAB; p = 2 * (w + SAB)
    return f"X{name} {d} {g} {s} {b} {typ} w={w}u l={l}u ad={a}p as={a}p pd={p}u ps={p}u m={m}\n"


def foot(tag, p, out):
    """Foot network from `out` to ground: base + coarse legs + fine leg."""
    s = fet(f"F{tag}", out, "vbn", "0", "0", "nfet_03v3", p["wfu"], p["ls"], p["k"])
    for b in range(p["bits"]):
        s += fet(f"F{tag}_{b}", out, f"g{b}", "0", "0", "nfet_03v3", p["wfu"], p["ls"], 2 ** b)
    s += fet(f"FF{tag}", out, "vctrl", "0", "0", "nfet_03v3", p["wff"], p["lff"])
    return s


def netlist(p):
    s = ""
    # beta multiplier (constant gm)
    s += fet("MN1", "n1", "n1", "0", "0", "nfet_03v3", p["w1"], p["l1"])
    s += fet("MN2", "n2", "n1", "nr", "0", "nfet_03v3", p["w1"], p["l1"], p["kb"])
    if p["rideal"]:
        s += f"RB nr 0 {p['r']} tc1={p['tcr']}\n"
    else:   # real PDK resistors in series: nwell (tc +2285 ppm) then n+ diffusion (tc +1360 ppm)
        mid = "0" if p["lnp"] <= 0 else "nrm"
        s += f"XRBW nr {mid} 0 nwell r_width={p['rw']}e-6 r_length={p['lnw']}e-6\n"
        if p["lnp"] > 0:
            s += f"XRBN {mid} 0 0 nplus_u r_width={p['rw']}e-6 r_length={p['lnp']}e-6\n"
    s += fet("MP1", "n1", "n2", "vdd", "vdd", "pfet_03v3", p["wpm"], p["lpm"])
    s += fet("MP2", "n2", "n2", "vdd", "vdd", "pfet_03v3", p["wpm"], p["lpm"])
    # start-up: x high while n1 is low -> MS3 pulls current from n2 into n1
    s += fet("MS1", "x", "0", "vdd", "vdd", "pfet_03v3", 0.5, 10.0)
    s += fet("MS2", "x", "n1", "0", "0", "nfet_03v3", 2.0, 0.28)
    s += fet("MS3", "n2", "x", "n1", "0", "nfet_03v3", 1.0, 0.28)
    # coarse gate switches: g_b = bit ? vbn : 0
    for b in range(p["bits"]):
        s += (fet(f"TN{b}", f"g{b}", f"bit{b}", "vbn", "0", "nfet_03v3", 2, 0.28)
              + fet(f"TP{b}", f"g{b}", f"bitb{b}", "vbn", "vdd", "pfet_03v3", 5, 0.28)
              + fet(f"TD{b}", f"g{b}", f"bitb{b}", "0", "0", "nfet_03v3", 1, 0.28))
    s += "Rvbn n1 vbn 1\n"   # vbn = n1 (named net; 1 ohm keeps MN1 as the reference diode)
    # master: copy of one stage's foot (x mr) into a PMOS diode -> vbp
    total = p["k"] + 2 ** p["bits"] - 1
    s += fet("MPB", "vbp", "vbp", "vdd", "vdd", "pfet_03v3", p["wpb"], p["ls"], max(1, round(p["mr"] * total / 4)))
    s += foot("M", dict(p, wfu=p["wfu"] * p["mr"], wff=p["wff"] * p["mr"]), "vbp")
    # ring
    n = p["n"]
    for i in range(n):
        a, y = f"a{i}", f"a{(i + 1) % n}"
        s += fet(f"H{i}", f"h{i}", "vbp", "vdd", "vdd", "pfet_03v3", p["whead"], p["ls"])
        s += fet(f"P{i}", y, a, f"h{i}", "vdd", "pfet_03v3", p["wp"], p["L"])
        s += fet(f"N{i}", y, a, f"f{i}", "0", "nfet_03v3", p["wn"], p["L"])
        s += foot(f"s{i}", p, f"f{i}")
        s += f"Cw{i} {y} 0 {p['cw']}\n"
    ics = " ".join(f"v(a{i})={0 if i % 2 == 0 else 3.3}" for i in range(n))
    return s, ics


def deck(p, corner, points):
    body, ics = netlist(p)
    src = "".join(f"vbit{b} bit{b} 0 0\nvbitb{b} bitb{b} 0 3.3\n" for b in range(p["bits"]))
    ctl = []
    for (code, vc, t, vdd) in points:
        tag = f"c{code}_v{vc:.2f}_t{t}_d{vdd:.2f}"
        alts = "".join(f"alter vbit{b} {vdd if (code >> b) & 1 else 0}\nalter vbitb{b} {0 if (code >> b) & 1 else vdd}\n"
                       for b in range(p["bits"]))
        ctl.append(f"""option temp={t}
alter vdd {vdd}
alter vctrl {vc}
{alts}tran 5p 200n 0 5p uic
meas tran t1 WHEN v(a0)={vdd/2} RISE=1 TD=100n
meas tran t2 WHEN v(a0)={vdd/2} RISE=11 TD=100n
meas tran iavg AVG i(vdd) FROM=100n TO=200n
meas tran vb AVG v(vbn) FROM=100n TO=200n
meas tran ir AVG i(vir) FROM=100n TO=200n
let f = 10/(t2-t1)
let pw = -iavg*{vdd}
echo "RES {tag} {code} {vc} {t} {vdd} $&f $&pw $&vb $&ir"
destroy all
""")
    return f"""* vco_bias {corner}
.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical
vdd vdd 0 3.3
vctrl vctrl 0 1.65
{src}{body.replace('XMN1 n1 n1 0 0', 'XMN1 n1i n1 0 0')}vir n1 n1i 0
.ic {ics}
.control
{''.join(ctl)}quit
.endc
.end
"""


def run(outdir, decks):
    outdir.mkdir(parents=True, exist_ok=True)
    rel = outdir.relative_to(REPO)
    for name, text in decks:
        (outdir / f"{name}.cir").write_text(text)
    script = " ; ".join(f"ngspice -b {rel}/{n}.cir > {rel}/{n}.log 2>&1" for n, _ in decks)
    subprocess.run([OSIC, "bash", "-c", f"cd {REPO} && {script}"], check=False)
    rows = []
    for name, _ in decks:
        log = (outdir / f"{name}.log").read_text()
        if "singular" in log.lower() or "error" in log.lower():
            print(f"WARN {name}: check log", file=sys.stderr)
        for m in re.finditer(r"^RES (\S+) (\S+) (\S+) (\S+) (\S+) (\S*) (\S+) (\S+) (\S+)$", log, re.M):
            f = float(m.group(6)) if m.group(6) else float("nan")
            rows.append((name, int(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)), f,
                         float(m.group(7)), float(m.group(8)), float(m.group(9))))
        if not rows:
            print("\n".join(log.splitlines()[-20:]), file=sys.stderr)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sweep", "pvt", "tc"])
    ap.add_argument("--code", type=int, default=15)
    ap.add_argument("--vctrl", type=float, default=1.65)
    ap.add_argument("--codes", default=None, help="comma list")
    ap.add_argument("--vcs", default="0,1.0,1.65,2.3,3.3", help="comma list")
    ap.add_argument("--tag", default="a")
    ap.add_argument("--set", action="append", default=[])
    a = ap.parse_args()
    p = dict(P)
    for kv in a.set:
        k, v = kv.split("="); p[k] = type(P[k])(float(v))
    outdir = REPO / f"build/vco/bias_{a.tag}"
    maxc = 2 ** p["bits"] - 1
    if a.mode == "sweep":
        codes = [int(c) for c in a.codes.split(",")] if a.codes else [0, maxc // 2, maxc]
        vcs = [float(v) for v in a.vcs.split(",")]
        decks = [("sweep_typical", deck(p, "typical", [(c, v, 27, 3.3) for c in codes for v in vcs]))]
    elif a.mode == "tc":   # tt only: 0/27/70 C at 3.3 V plus +-150 mV at 27 C
        pts = [(a.code, a.vctrl, t, 3.3) for t in (0, 27, 70)] + [(a.code, a.vctrl, 27, d) for d in (3.15, 3.45)]
        decks = [("tc_typical", deck(p, "typical", pts))]
    else:
        pts = [(a.code, a.vctrl, t, d) for t in (0, 27, 70) for d in (3.15, 3.3, 3.45)]
        decks = [(f"pvt_{c}", deck(p, c, pts)) for c in CORNERS]
    rows = run(outdir, decks)
    print(f"{p}")
    print(f"{'deck':12s} {'code':>4s} {'vctrl':>5s} {'T':>3s} {'VDD':>5s} {'f MHz':>8s} {'P mW':>6s} {'vbn':>6s} {'Iref uA':>8s}")
    for r in rows:
        print(f"{r[0]:12s} {r[1]:4d} {r[2]:5.2f} {r[3]:3.0f} {r[4]:5.2f} {r[5]/1e6:8.1f} {r[6]*1e3:6.2f} {r[7]:6.3f} {r[8]*1e6:8.2f}")


if __name__ == "__main__":
    main()
