#!/usr/bin/env python3
"""a0 -> level shifter -> TSPC /4 -> buffer -> std-cell DFF clock (+20 fF), on the cfed ring (extracted v3 core).

  python3 sim/lsdiv/lsdiv.py ring --runs main|robust|vdd|cand|one [--jobs 8] [--tstop 1.2e-6] [--ls a|b] [--set K=V]
  python3 sim/lsdiv/lsdiv.py ring --runs one --ls x [--r1 1k|3k]   # the extracted layout block (layout/pex/lsdiv_c.spice)
  python3 sim/lsdiv/lsdiv.py div  [--jobs 8]           # /4 alone: ideal clock (through the LS output inverter), f sweep
  python3 sim/lsdiv/lsdiv.py summary                   # tables from build/lsdiv/*.json -> sim/lsdiv/results/

Ring: vco_bias.netlist(topo=cfed, winner reference, lnw 5.023, ka 16, wfu=wff=0.30, rf 1 MOhm, cf 20 pF) with the
core elements replaced by the extracted layout/pex/ring_core_v3_w30chk_rcx.spice (gate-net port vbn -> vbnf).
Start: DC op with the ring nodes held at the alternating .ic (vbn/vbnf/vg at DC), then f etc. over the last 40 %.
Block supplies are separate sources (vls: level shifter, vdv: divider + buffer, vff: the DFF) for the power split.
Outputs: build/lsdiv/<run>/ (decks, logs, raw) and build/lsdiv/<runs>.json.
"""
import argparse, json, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/vco"))
sys.path.insert(0, str(REPO / "tools"))
import vco_bias as vb  # noqa: E402
from rawread import read_raw  # noqa: E402

OSIC = str(REPO / "tools/osic-mac")
OUT = REPO / "build/lsdiv"
PEX = REPO / "layout/pex/ring_core_v3_w30chk_rcx.spice"   # RC with the coupling double count removed (rcfix.py)
STD = "/foss/pdks/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/spice/gf180mcu_fd_sc_mcu7t5v0.spice"
WINNER = dict(rideal=0, lnp=100.0, lnw=5.023, nsn=14, wpm=56.0, lpm=14.0, mr=4.0)
CFED = dict(topo="cfed", kc=0.75, k=6, cvg=3e-12, cw=3e-15, ka=16.0, wfu=0.30, wff=0.30, rf=1e6, cf=20e-12)
CORE = re.compile(r"^(X(P|N|FC|FFC|TN|TP|TD)\S*|Cvg|Cw\d+)\s", re.I)
CODE433 = dict(typical=9, ss=11, ff=7, sf=9, fs=9)    # map.csv nearest-433.92 code at 27 C, vctrl 1.65
CN = dict(typical="tt", ss="ss", ff="ff", sf="sf", fs="fs")

# block sizes (um). LS (a): Cc -> inv1 (self-biased by a replica inverter through a long PMOS) -> inv2 -> inv3
S = dict(cc=2.0e-15, cpa=0.2e-15, cpg=0.4e-15,          # coupling C, its plate parasitics (a0 side, gate side)
         wn1=0.22, wp1=0.5, l1=0.28,                    # inv1 (and, in (a), its replica: same size)
         wr=0.22, lr=2.0,                               # bias pseudo-R: pfet, gate VSS, bulk VDD ((a) tuned: lr 20)
         r1=500e3, c1=1e-12,                            # (c): output low-pass for the bias (tau 0.5 us)
         real=0, r1w=1.0, r1l=159.125, c1w=16.0, c1l=16.0,  # real=1: R1 ppolyf_u_1k r1w x r1l (as drawn), C1 nfet cap W/L (um)
         wn2=0.6, wp2=1.5, wn3=1.2, wp3=3.0,            # inv2, inv3 (= LS output, drives the /2 clock)
         # LS (b): replica ring stage (VDD/vg) -> PMOS-input cross-coupled latch -> inverter
         wbn=0.42, wbp=1.0, wxp=1.5, wxn=0.5,
         # TSPC /2 stages and buffers
         t1n=1.0, t1p=2.0, t2n=0.6, t2p=1.2, qn=0.6, qp=1.5, bn=1.0, bp=2.5, cwire=20e-15)


def fet(name, d, g, s, b, typ, w, l=0.28):
    return vb.fet(name, d, g, s, b, typ, w, l)


def inv(name, i, o, vdd, w_n, w_p, l=0.28):
    return fet(f"{name}p", o, i, vdd, vdd, "pfet_03v3", w_p, l) + fet(f"{name}n", o, i, "0", "0", "nfet_03v3", w_n, l)


def tspc(name, clk, q, vdd, wn, wp):
    """Positive-edge TSPC DFF with D = Qb (toggle), Q = inv(Qb)."""
    n = name
    return (fet(f"{n}p1", f"{n}n1", f"{n}qb", vdd, vdd, "pfet_03v3", wp)
            + fet(f"{n}p2", f"{n}x", clk, f"{n}n1", vdd, "pfet_03v3", wp)
            + fet(f"{n}n1", f"{n}x", f"{n}qb", "0", "0", "nfet_03v3", wn)
            + fet(f"{n}p3", f"{n}y", clk, vdd, vdd, "pfet_03v3", wp)
            + fet(f"{n}n2", f"{n}y", f"{n}x", f"{n}n2", "0", "nfet_03v3", wn)
            + fet(f"{n}n3", f"{n}n2", clk, "0", "0", "nfet_03v3", wn)
            + fet(f"{n}p4", f"{n}qb", f"{n}y", vdd, vdd, "pfet_03v3", wp)
            + fet(f"{n}n4", f"{n}qb", clk, f"{n}n3", "0", "nfet_03v3", wn)
            + fet(f"{n}n5", f"{n}n3", f"{n}y", "0", "0", "nfet_03v3", wn)
            + inv(f"{n}q", f"{n}qb", q, vdd, S["qn"], S["qp"]))


def ls_a(s, inp="a0", out="lsout", vdd="vls"):
    return (f"Cc {inp} lg {s['cc']}\nCpa {inp} 0 {s['cpa']}\nCpg lg 0 {s['cpg']}\n"
            + inv("LR", "lb", "lb", vdd, s["wn1"], s["wp1"], s["l1"])               # replica: lb = trip point
            + fet("LRB", "lg", "0", "lb", vdd, "pfet_03v3", s["wr"], s["lr"])     # pseudo-R lb -> lg
            + inv("L1", "lg", "lo1", vdd, s["wn1"], s["wp1"], s["l1"])
            + inv("L2", "lo1", "lo2", vdd, s["wn2"], s["wp2"])
            + inv("L3", "lo2", out, vdd, s["wn3"], s["wp3"]))


def ls_c(s, inp="a0", out="lsout", vdd="vls"):
    """(a) without the replica: inv1's gate bias is the low-passed LS output (R1, C1), through the long PMOS.
    3 inversions -> negative DC feedback: mean(out) -> inv1's bias, so the output duty -> Vtrip1 / VDD."""
    return (f"Cc {inp} lg {s['cc']}\nCpa {inp} 0 {s['cpa']}\nCpg lg 0 {s['cpg']}\n"
            + passives(s, out)
            + fet("LRB", "lg", "0", "lf", vdd, "pfet_03v3", s["wr"], s["lr"])
            + inv("L1", "lg", "lo1", vdd, s["wn1"], s["wp1"], s["l1"])
            + inv("L2", "lo1", "lo2", vdd, s["wn2"], s["wp2"])
            + inv("L3", "lo2", out, vdd, s["wn3"], s["wp3"]))


def passives(s, out):
    """R1 (out -> lf) and C1 (lf -> VSS): ideal (500 kOhm, 1 pF), or with s['real'] the drawn devices: R1 ppolyf_u_1k
    1 x 159.125 um as laid out (sized for 500 kOhm at 3 kOhm/sq; the run is 1 kOhm/sq, so ~164 kOhm, tau ~0.16 us,
    still ~70x the ring period: verified on the extracted block), C1 an nfet_03v3 gate cap (gate lf, S/D/B VSS,
    16 x 16 um ~ 1 pF; lf sits at INV1's trip point, ~1.5 V, well into inversion)."""
    if not s.get("real"):
        return f"R1 {out} lf {s['r1']}\nC1 lf 0 {s['c1']}\n"
    return (f"XR1 {out} lf 0 ppolyf_u_1k r_width={s['r1w']}e-6 r_length={s['r1l']}e-6\n"
            + fet("C1", "0", "lf", "0", "0", "nfet_03v3", s["c1w"], s["c1l"]))


def block(s=None):
    """The drawn block as a .subckt (LVS / schematic source): LS (c) with the real passives + TSPC /4 + buffer.
    Ports VDD VSS a0 ck ls (ls: the level-shifter output, the TX driver's tap). Not in it: the parasitic stand-ins Cpa/Cpg, the 20 fF ck wire and the std-cell DFF (loads).
    Cc stays an ideal C (it is a metal-finger cap, no device)."""
    s = dict(S if s is None else s, real=1)
    body = ls_c(s, out="ls") + divider(s, clk="ls")
    lines = []
    for ln in body.splitlines():
        t = ln.split()
        if t[0] in ("Cpa", "Cpg", "Cwire", "XFF"):
            continue
        t = [{"vls": "VDD", "vdv": "VDD", "0": "VSS"}.get(x, x) for x in t]
        lines.append(" ".join(t))
    return ".subckt lsdiv VDD VSS a0 ck ls\n" + "\n".join(lines) + "\n.ends\n"   # ls: the TX driver tap (port)


def ls_b(s, inp="a0", out="lsout", vdd="vls"):
    return (fet("LBp", "a0b", inp, vdd, vdd, "pfet_03v3", s["wbp"]) + fet("LBn", "a0b", inp, "vg", "0", "nfet_03v3", s["wbn"])
            + fet("LX1", "lx", inp, vdd, vdd, "pfet_03v3", s["wxp"]) + fet("LX2", "ly", "a0b", vdd, vdd, "pfet_03v3", s["wxp"])
            + fet("LX3", "lx", "ly", "0", "0", "nfet_03v3", s["wxn"]) + fet("LX4", "ly", "lx", "0", "0", "nfet_03v3", s["wxn"])
            + inv("L2", "ly", "lo2", vdd, s["wn2"], s["wp2"])
            + inv("L3", "lo2", out, vdd, s["wn3"], s["wp3"]))


def divider(s, clk="lsout", vdd="vdv"):
    return (tspc("D1", clk, "q1", vdd, s["t1n"], s["t1p"]) + tspc("D2", "q1", "q2", vdd, s["t2n"], s["t2p"])
            + inv("B1", "q2", "ck", vdd, s["bn"], s["bp"])
            + f"Cwire ck 0 {s['cwire']}\n"
            + "XFF 0 ck ffq vff vff 0 0 gf180mcu_fd_sc_mcu7t5v0__dffq_1\n")


LSX = REPO / "layout/pex/lsdiv_c.spice"    # extracted block (layout/gen/pex_lsdiv.sh c), --ls x
R1MODEL = {"m": "1k"}                      # --r1 1k|3k: model for the extracted hi-res poly R1 (the run is 1k)


def ls_x(s):
    """The extracted lsdiv block (Cc, Cpa/Cpg and the wiring C are in the extraction) + the same loads as divider():
    the 20 fF ck wire and the std-cell DFF. One supply (vls) feeds LS + /4 + buffer, so p_ls is the block total
    and p_div is 0. ls and q1 are brought out as extra ports (lsout, q1) for analyse()."""
    t, n = re.subn(r"(?m)^\.subckt lsdiv VDD VSS a0 ck( ls)?$", ".subckt lsdiv_x VDD VSS a0 ck ls q1", LSX.read_text())
    assert n == 1, "lsdiv extraction header"     # old extractions have no ls port, newer ones end in ls
    t = t.replace(" ppolyf_u_1k ", f" ppolyf_u_{R1MODEL['m']} ")
    return (t + "Xlsdiv vls 0 a0 ck lsout q1 lsdiv_x\n" + f"Cwire ck 0 {s['cwire']}\n"
            + "XFF 0 ck ffq vff vff 0 0 gf180mcu_fd_sc_mcu7t5v0__dffq_1\n")


def ring(p, core="pex"):
    body, ics = vb.netlist(p)
    if core == "pex":
        body = "".join(ln + "\n" for ln in body.splitlines() if not CORE.match(ln))
        body += ("Xcore vdd 0 vbnf vctrl " + " ".join(f"bit{b}" for b in range(5)) + " "
                 + " ".join(f"bitb{b}" for b in range(5)) + " vg a0 a1 a2 a3 a4 ring_core\n"
                 + f".include {PEX}\n")
    return body.replace("XMN1 n1 n1 ", "XMN1 n1i n1 ", 1) + "vir n1 n1i 0\n", ics


def hdr(corner):
    return (".include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice\n"
            f".lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}\n"
            ".lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical\n"
            f".include {STD}\n")


def ring_deck(p, s, corner, temp, code, vdd, block, tstop, core="pex"):
    body, ics = ring(p, core)
    bits = "".join(f"vbit{b} bit{b} 0 {vdd if (code >> b) & 1 else 0}\nvbitb{b} bitb{b} 0 {0 if (code >> b) & 1 else vdd}\n"
                   for b in range(5))
    blk = ("" if block == "none" else ls_x(s) if block == "x"
           else dict(a=ls_a, b=ls_b, c=ls_c)[block](s) + divider(s))
    t0 = 0.6 * tstop
    save = "v(a0) v(vg)" + ("" if block == "none" else " v(lsout) v(q1) v(ck) i(vls) i(vdv)")
    return f"""* lsdiv ring {corner} {temp} code {code} vdd {vdd} block {block}
{hdr(corner)}vdd vdd 0 {vdd}
vls vls 0 {vdd}
vdv vdv 0 {vdd}
vff vff 0 {vdd}
vctrl vctrl 0 1.65
{bits}{body}{blk}.ic {ics}
.control
option temp={temp}
save {save}
tran 5p {tstop} {t0} 5p
set filetype=binary
write out.raw {save}
quit
.endc
.end
"""


def div_deck(s, corner, temp, vdd, freqs):
    """Ideal 50 % clock (50 ps edges) -> LS output inverter -> /4 -> buffer -> DFF; one tran per f."""
    ctl = ""
    for f in freqs:
        per = 1 / f
        n = 48
        ctl += f"""alter @vclk[pulse] = [ 0 {vdd} 0 50p 50p {per / 2 - 50e-12:.4e} {per:.4e} ]
tran {per / 100:.3e} {n * per:.4e} 0 {per / 100:.3e}
meas tran r1 WHEN v(ck)={vdd / 2} RISE=4
meas tran r2 WHEN v(ck)={vdd / 2} RISE=10
meas tran fl WHEN v(ck)={vdd / 2} FALL=4 TD=r1
meas tran vmn MIN v(ck) FROM=r1 TO=r2
meas tran vmx MAX v(ck) FROM=r1 TO=r2
let fo = 6/(r2-r1)
let du = (fl-r1)/((r2-r1)/6)
echo "DV {f:.4e} $&fo $&du $&vmn $&vmx"
destroy all
"""
    return f"""* lsdiv div {corner} {temp} {vdd}
{hdr(corner)}vdd vls 0 {vdd}
vdv vdv 0 {vdd}
vff vff 0 {vdd}
vclk clkin 0 pulse(0 {vdd} 0 50p 50p 1n 2n)
{inv("L3", "clkin", "lsout", "vls", S["wn3"], S["wp3"])}{divider(S)}
.control
option temp={temp}
{ctl}quit
.endc
.end
"""


def run1(name, text):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / ".spiceinit").write_text("set ng_nomodcheck\nset num_threads=1\noption noinit\n")
    (d / "deck.cir").write_text(text)
    t = time.time()
    subprocess.run([OSIC, "bash", "-c", f"cd {d} && ngspice -b deck.cir > deck.log 2>&1"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return name, time.time() - t


def xings(t, v, th, rising=True):
    a, b = v[:-1] - th, v[1:] - th
    idx = np.where((a < 0) & (b >= 0))[0] if rising else np.where((a > 0) & (b <= 0))[0]
    return t[idx] + (th - v[idx]) * (t[idx + 1] - t[idx]) / (v[idx + 1] - v[idx])


def freq(t, v, th):
    r = xings(t, v, th)
    return (len(r) - 1) / (r[-1] - r[0]) if len(r) > 2 else float("nan"), r


def duty(t, v, th):
    r, f = xings(t, v, th), xings(t, v, th, False)
    d = []
    for i in range(len(r) - 1):
        nf = f[(f > r[i]) & (f < r[i + 1])]
        if len(nf):
            d.append((nf[0] - r[i]) / (r[i + 1] - r[i]))
    return float(np.mean(d)) if d else float("nan")


def edges(t, v, vdd):
    """mean 10-90 % rise and 90-10 % fall time."""
    lo, hi = 0.1 * vdd, 0.9 * vdd
    rl, rh = xings(t, v, lo), xings(t, v, hi)
    fh, fl = xings(t, v, hi, False), xings(t, v, lo, False)
    tr = [rh[rh > x][0] - x for x in rl if (rh > x).any()]
    tf = [fl[fl > x][0] - x for x in fh if (fl > x).any()]
    return float(np.median(tr)) if tr else float("nan"), float(np.median(tf)) if tf else float("nan")


def analyse(name, vdd, block):
    d = OUT / name
    log = (d / "deck.log").read_text(errors="replace")
    warn = [w for w in ("singular", "timestep too small", "Transient op started") if w.lower() in log.lower()]
    try:
        pl = read_raw(d / "out.raw")[0]["vars"]
    except Exception as e:  # noqa: BLE001
        return dict(name=name, error=str(e), log=log.splitlines()[-5:])
    t = pl["time"]
    a0 = pl["v(a0)"]
    amin, amax = float(a0.min()), float(a0.max())
    fa, _ = freq(t, a0, (amin + amax) / 2)
    h = (t[0] + t[-1]) / 2
    fa1, _ = freq(t[t < h], a0[t < h], (amin + amax) / 2)
    fa2, _ = freq(t[t >= h], a0[t >= h], (amin + amax) / 2)
    r = dict(name=name, f_a0=fa, f_drift=fa2 / fa1 - 1, a0_min=amin, a0_max=amax, vg=float(np.trapezoid(pl["v(vg)"], t) / (t[-1] - t[0])),
             warn=warn)
    if block != "none":
        ls = pl["v(lsout)"]
        ck = pl["v(ck)"]
        fl, _ = freq(t, ls, vdd / 2)
        fc, _ = freq(t, ck, vdd / 2)
        tr, tf = edges(t, ls, vdd)
        T = t[-1] - t[0]
        r.update(ls_min=float(ls.min()), ls_max=float(ls.max()), ls_duty=duty(t, ls, vdd / 2), ls_tr=tr, ls_tf=tf,
                 f_ls=fl, f_div=fc, div_ratio=fa / fc, div_duty=duty(t, ck, vdd / 2), ck_min=float(ck.min()), ck_max=float(ck.max()),
                 p_ls=-float(np.trapezoid(pl["i(vls)"], t)) / T * vdd, p_div=-float(np.trapezoid(pl["i(vdv)"], t)) / T * vdd)
        q1 = pl["v(q1)"]
        r["q1_duty"] = duty(t, q1, vdd / 2)
    return r


def ring_points(which):
    pts = []
    if which in ("main", "one"):
        for c in ("typical", "ss", "ff", "sf", "fs"):
            for code in sorted({0, CODE433[c], 31}):
                pts.append((c, 27, code, 3.3))
        if which == "one":
            pts = [("typical", 27, 9, 3.3)]
    elif which == "robust":
        pts = [(c, t, code, 3.3) for c in ("ss", "ff") for t in (0, 70) for code in (0, 31)]
    elif which == "vdd":
        pts = [(c, t, code, 3.15) for (c, t, code) in VDD_WORST]
    elif which == "cand":
        pts = [(c, 27, code, 3.3) for c in ("typical", "ff", "ss") for code in (0, 31)]
    return pts


VDD_WORST = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["ring", "div", "summary"])
    ap.add_argument("--runs", default="one")
    ap.add_argument("--ls", default="c")
    ap.add_argument("--blocks", default="none,blk")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--tstop", type=float, default=1.2e-6)
    ap.add_argument("--core", default="pex")
    ap.add_argument("--worst", default="ss,0,31", help="vdd run: corner,temp,code[;...]")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--tag", default="")
    ap.add_argument("--r1", default="1k", choices=["1k", "3k"], help="--ls x: R1 model (1k: the run; 3k: old results)")
    a = ap.parse_args()
    R1MODEL["m"] = a.r1
    for kv in a.set:
        k, v = kv.split("=")
        S[k] = float(v)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.mode == "ring":
        p = dict(vb.P, **WINNER, **CFED)
        if a.core != "pex":
            p["cw"] = 3.4e-15
        for w in a.worst.split(";"):
            c, t, code = w.split(",")
            VDD_WORST.append((c, int(t), int(code)))
        blocks = [("none" if b == "none" else a.ls) for b in a.blocks.split(",")]
        jobs = []
        for (c, t, code, vdd) in ring_points(a.runs):
            for blk in blocks:
                n = f"r{a.tag}_{CN[c]}_t{t}_c{code}_d{vdd:.2f}_{blk}"
                jobs.append((n, ring_deck(p, S, c, t, code, vdd, blk, a.tstop, a.core), dict(corner=CN[c], temp=t, code=code,
                                                                                            vdd=vdd, block=blk)))
        t0 = time.time()
        with ThreadPoolExecutor(a.jobs) as ex:
            dts = dict(ex.map(lambda j: run1(j[0], j[1]), jobs))
        res = []
        for n, _, meta in jobs:
            r = analyse(n, meta["vdd"], meta["block"])
            r.update(meta, run_s=dts[n])
            res.append(r)
            print(json.dumps({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}))
        out = OUT / f"ring_{a.runs}{a.tag}_{a.ls}.json"
        out.write_text(json.dumps(dict(S=S, tstop=a.tstop, core=a.core, wall_s=time.time() - t0, rows=res), indent=1))
        print(f"wrote {out} in {time.time() - t0:.0f} s")
    elif a.mode == "div":
        freqs = [10e6, 50e6, 150e6, 300e6, 500e6, 700e6, 870e6, 1.0e9, 1.2e9, 1.4e9, 1.6e9, 1.8e9, 2.0e9, 2.3e9,
                 2.6e9, 3.0e9, 3.5e9, 4.0e9]
        cts = [(c, 27) for c in ("typical", "ss", "ff", "sf", "fs")] + [(c, t) for c in ("ss", "ff") for t in (0, 70)]
        jobs = [(f"div{a.tag}_{CN[c]}_t{t}", div_deck(S, c, t, 3.3, freqs), (c, t)) for c, t in cts]
        t0 = time.time()
        with ThreadPoolExecutor(a.jobs) as ex:
            list(ex.map(lambda j: run1(j[0], j[1]), jobs))
        res = []
        for n, _, (c, t) in jobs:
            log = (OUT / n / "deck.log").read_text(errors="replace")
            rows = []
            for m in re.finditer(r"^DV (\S+) (\S*) (\S*) (\S*) (\S*)$", log, re.M):
                fi = float(m.group(1))
                g = lambda i: float(m.group(i)) if m.group(i) else float("nan")
                fo, du, vmn, vmx = g(2), g(3), g(4), g(5)
                ok = abs(fo * 4 / fi - 1) < 0.01 and vmn < 0.3 and vmx > 3.0
                rows.append(dict(fin=fi, fout=fo, duty=du, vmin=vmn, vmax=vmx, ok=ok))
            okf = [r["fin"] for r in rows if r["ok"]]
            # max: highest f with every f below it (from 150 MHz) ok
            fmax = None
            for r in rows:
                if r["fin"] >= 150e6:
                    if r["ok"]:
                        fmax = r["fin"]
                    else:
                        break
            fmin = min(okf) if okf else None
            res.append(dict(corner=CN[c], temp=t, fmax=fmax, fmin=fmin, rows=rows))
            print(f"{CN[c]} {t}: fmin {fmin} fmax {fmax} " + " ".join(f"{r['fin']/1e9:.3g}{'' if r['ok'] else '!'}" for r in rows))
        (OUT / f"div{a.tag}.json").write_text(json.dumps(dict(S=S, wall_s=time.time() - t0, rows=res), indent=1))
        print(f"wall {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
