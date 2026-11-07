#!/usr/bin/env python3
"""Phase-1 candidate VCOs on GF180 (schematic, nfet/pfet_03v3).

Topologies (both: coarse = switched MOS-cap bank on every ring node, fine = analog vctrl
on the starving NMOS feet with a mirrored PMOS head bias):
  se    single-ended current-starved ring, N odd
  diff  pseudo-differential: two starved rings cross-coupled per node by weak inverter pairs,
        N even or odd (wrap crosses over), gives complementary outputs

Usage (repo root):
  python3 sim/vco/vco_cand.py se   --n 7 sweep      # f vs code x vctrl at tt 27C
  python3 sim/vco/vco_cand.py diff --n 4 sweep
  python3 sim/vco/vco_cand.py se --n 7 pvt --code 8 --vctrl 2.0   # corners/temps/vdd at one point
Writes build/vco/<topo>_n<N>/*.cir|log and prints a table.
"""
import argparse, os, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OSIC = os.environ.get("OSIC", str(REPO / "tools/osic-mac"))
SAB = 0.5
P = dict(L=0.28, wn=1.0, wp=2.5,          # core inverter
         wfoot=4.0, whead=10.0,            # starving devices per stage
         wmb=4.0, wpb=10.0,                # bias mirror: nfet (gate vctrl) -> pfet diode vbp
         wcu=1.0, lcu=0.5, bits=4,         # cap bank unit (nfet gate cap W x L), binary bits
         wsw=1.0,                          # cap switch nfet width (unit; scaled by weight)
         wx=0.5, cw=2e-15,
         coarse="i", wfu=0.5, k=8, ls=0.28)          # coarse="i": foot legs (k + code) x wfu, gates g_b; "c": cap bank                 # diff: cross-couple inverter nfet width; wiring C/node


def fet(name, d, g, s, b, typ, w, l):
    a = w * SAB; p = 2 * (w + SAB)
    return f"X{name} {d} {g} {s} {b} {typ} w={w}u l={l}u ad={a}p as={a}p pd={p}u ps={p}u\n"


def starved_inv(tag, a, y, p):
    L = p["L"]
    return (fet(f"MH{tag}", f"h{tag}", "vbp", "vdd", "vdd", "pfet_03v3", p["whead"], p["ls"])
            + fet(f"MP{tag}", y, a, f"h{tag}", "vdd", "pfet_03v3", p["wp"], L)
            + fet(f"MN{tag}", y, a, f"f{tag}", "0", "nfet_03v3", p["wn"], L)
            + foot(tag, p)
            + f"Cw{tag} {y} 0 {p['cw']}\n")


def foot(tag, p):
    L = p["ls"]
    if p["coarse"] != "i":
        return fet(f"MF{tag}", f"f{tag}", "vctrl", "0", "0", "nfet_03v3", p["wfoot"], L)
    s = fet(f"MF{tag}", f"f{tag}", "vctrl", "0", "0", "nfet_03v3", p["wfu"] * p["k"], L)
    for b in range(p["bits"]):
        s += fet(f"MF{tag}_{b}", f"f{tag}", f"g{b}", "0", "0", "nfet_03v3", p["wfu"] * 2 ** b, L)
    return s


def gate_switches(p):
    """g_b = bit_b ? vctrl : 0 (TG + pulldown), one per bit, shared by all stages."""
    L = p["L"]; s = ""
    for b in range(p["bits"]):
        s += (fet(f"MTN{b}", f"g{b}", f"bit{b}", "vctrl", "0", "nfet_03v3", 2, L)
              + fet(f"MTP{b}", f"g{b}", f"bitb{b}", "vctrl", "vdd", "pfet_03v3", 5, L)
              + fet(f"MPD{b}", f"g{b}", f"bitb{b}", "0", "0", "nfet_03v3", 1, L))
    return s


def cap_bank(tag, node, p):
    s = ""
    if p["coarse"] == "i":
        return s
    for b in range(p["bits"]):
        m = 2 ** b
        s += fet(f"MC{tag}_{b}", f"s{tag}_{b}", node, f"s{tag}_{b}", "0", "nfet_03v3", p["wcu"] * m, p["lcu"])
        s += fet(f"MS{tag}_{b}", f"s{tag}_{b}", f"bit{b}", "0", "0", "nfet_03v3", p["wsw"] * m, p["L"])
    return s


def plain_inv(tag, a, y, w, L, hi="vdd", lo="0"):
    """Inverter; hi/lo = the starved head/foot nodes of the stage it sits in (so latch strength tracks current)."""
    return (fet(f"XP{tag}", y, a, hi, "vdd", "pfet_03v3", 2.5 * w, L)
            + fet(f"XN{tag}", y, a, lo, "0", "nfet_03v3", w, L))


def netlist(topo, n, p):
    s = fet("MPB", "vbp", "vbp", "vdd", "vdd", "pfet_03v3", p["wpb"], p["ls"])
    if p["coarse"] == "i":   # mirror master scaled like one stage's foot (ratio wmb/wfu)
        r = p["wmb"]
        s += fet("MB", "vbp", "vctrl", "0", "0", "nfet_03v3", r * p["k"], p["ls"]) + gate_switches(p)
        for b in range(p["bits"]):
            s += fet(f"MB_{b}", "vbp", f"g{b}", "0", "0", "nfet_03v3", r * 2 ** b, p["ls"])
    else:
        s += fet("MB", "vbp", "vctrl", "0", "0", "nfet_03v3", p["wmb"], p["L"])
    if topo == "se":
        nodes = [f"a{i}" for i in range(n)]
        for i in range(n):
            s += starved_inv(f"a{i}", nodes[i], nodes[(i + 1) % n], p)
            s += cap_bank(f"a{i}", nodes[i], p)
        ics = {nodes[i]: (0 if i % 2 == 0 else 3.3) for i in range(n)}
        out = ("a0", None)
    else:
        A = [f"a{i}" for i in range(n)]; B = [f"b{i}" for i in range(n)]
        for i in range(n):
            j = (i + 1) % n
            if j == 0:     # wrap with a crossover: a(n-1)->b0, b(n-1)->a0 (even N works)
                s += starved_inv(f"a{i}", A[i], B[0], p); s += starved_inv(f"b{i}", B[i], A[0], p)
            else:
                s += starved_inv(f"a{i}", A[i], A[j], p); s += starved_inv(f"b{i}", B[i], B[j], p)
            s += cap_bank(f"a{i}", A[i], p) + cap_bank(f"b{i}", B[i], p)
            # weak cross-coupled latch between a_i and b_i
            # each latch inverter drives a node, so it shares that node's driver head/foot
            s += (plain_inv(f"xa{i}", A[i], B[i], p["wx"], p["L"], f"hb{i-1 if i else n-1}" if i else f"ha{n-1}", f"fb{i-1}" if i else f"fa{n-1}")
                  + plain_inv(f"xb{i}", B[i], A[i], p["wx"], p["L"], f"ha{i-1}" if i else f"hb{n-1}", f"fa{i-1}" if i else f"fb{n-1}"))
        ics = {}
        for i in range(n):
            v = 0 if i % 2 == 0 else 3.3
            ics[A[i]] = v; ics[B[i]] = 3.3 - v
        out = ("a0", "b0")
    return s, ics, out


def deck(topo, n, p, corner, points):
    body, ics, out = netlist(topo, n, p)
    ic = " ".join(f"v({k})={v}" for k, v in ics.items())
    bits = "".join(f"vbit{b} bit{b} 0 0\nvbitb{b} bitb{b} 0 3.3\n" for b in range(p["bits"]))
    ctl = []
    for (code, vc, t, vdd) in points:
        tag = f"c{code}_v{vc:.2f}_t{t}_d{vdd:.2f}"
        alts = "".join(f"alter vbit{b} {vdd if (code >> b) & 1 else 0}\nalter vbitb{b} {0 if (code >> b) & 1 else vdd}\n" for b in range(p["bits"]))
        ctl.append(f"""option temp={t}
alter vdd {vdd}
alter vctrl {vc}
{alts}tran 5p 200n 0 5p uic
meas tran t1 WHEN v({out[0]})={vdd/2} RISE=1 TD=100n
meas tran t2 WHEN v({out[0]})={vdd/2} RISE=11 TD=100n
meas tran iavg AVG i(vdd) FROM=100n TO=200n
let f = 10/(t2-t1)
let pw = -iavg*{vdd}
echo "RES {tag} {code} {vc} {t} {vdd} $&f $&pw"
destroy all
""")
    return f"""* {topo} N={n} {corner}
.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}
vdd vdd 0 3.3
vctrl vctrl 0 2
{bits}{body}
.ic {ic}
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
        if "Transient op started" in log or "singular" in log.lower():
            print(f"WARN {name}: op problem", file=sys.stderr)
        for m in re.finditer(r"^RES (\S+) (\S+) (\S+) (\S+) (\S+) (\S*) (\S+)$", log, re.M):
            f = float(m.group(6)) if m.group(6) else float("nan")
            rows.append((name, int(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)), f, float(m.group(7))))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topo", choices=["se", "diff"])
    ap.add_argument("mode", choices=["sweep", "pvt"])
    ap.add_argument("--n", type=int, default=7)
    ap.add_argument("--code", type=int, default=8)
    ap.add_argument("--vctrl", type=float, default=2.0)
    ap.add_argument("--set", action="append", default=[], help="override a size, e.g. --set wfoot=6")
    ap.add_argument("--vctrls", help="sweep: vctrl list 'a,b,c' or range 'start:stop:step' (default 0.9,1.2,1.5,2.0,2.5,3.3)")
    ap.add_argument("--codes", help="sweep: coarse code list 'a,b,c' (default 0, mid, max)")
    ap.add_argument("--tag", default="", help="deck name prefix, e.g. 'dense_' writes sweep_dense_typical.cir|log")
    a = ap.parse_args()
    p = dict(P)
    for kv in a.set:
        k, v = kv.split("="); p[k] = v if isinstance(P[k], str) else type(P[k])(float(v))
    outdir = REPO / f"build/vco/{a.topo}_n{a.n}"
    maxc = 2 ** p["bits"] - 1
    if a.mode == "sweep":
        vcs = [0.9, 1.2, 1.5, 2.0, 2.5, 3.3]
        if a.vctrls and ":" in a.vctrls:
            v0, v1, dv = map(float, a.vctrls.split(":"))
            vcs = [round(v0 + i * dv, 4) for i in range(int(round((v1 - v0) / dv)) + 1)]
        elif a.vctrls:
            vcs = [float(v) for v in a.vctrls.split(",")]
        codes = [int(c) for c in a.codes.split(",")] if a.codes else [0, maxc // 2, maxc]
        decks = [(f"sweep_{a.tag}typical", deck(a.topo, a.n, p, "typical", [(c, v, 27, 3.3) for c in codes for v in vcs]))]
    else:
        pts = lambda: [(a.code, a.vctrl, t, d) for t in (0, 27, 70) for d in (3.15, 3.3, 3.45)]
        decks = [(f"pvt_{a.tag}{c}", deck(a.topo, a.n, p, c, pts())) for c in ("typical", "ss", "ff", "sf", "fs")]
    rows = run(outdir, decks)
    print(f"{a.topo} N={a.n} {p}")
    print(f"{'deck':14s} {'code':>4s} {'vctrl':>5s} {'T':>3s} {'VDD':>5s} {'f MHz':>8s} {'P mW':>6s}")
    for r in rows:
        print(f"{r[0]:14s} {r[1]:4d} {r[2]:5.2f} {r[3]:3.0f} {r[4]:5.2f} {r[5]/1e6:8.1f} {r[6]*1e3:6.2f}")


if __name__ == "__main__":
    main()
