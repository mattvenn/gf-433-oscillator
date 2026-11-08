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
  python3 sim/vco/vco_bias.py tc --code 10                 # tt only: 0/27/70 C, and 27 C at VDD +-150 mV
  python3 sim/vco/vco_bias.py map --jobs 20 [--set ...]    # f for every code x vctrl 0/1.65/3.3 at 5 corners x
                                                           # 0/27/70 C x VDD 3.15/3.3/3.45 -> map.csv, map_summary.json
  python3 sim/vco/vco_bias.py startup --corners ss,ff --temps 0,70   # reference + master only, VDD ramp 0->3.3 V in 10 us, to 200 us
  python3 sim/vco/vco_bias.py ringstart --code 0 --jobs 20 [--seeds 6]   # ring mode from random initial states,
                                                           # 5 corners x 0/27/70 C: fundamental mode (a0->a1 phase) and
                                                           # f late within 5 % of the alternating start
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
         cw=2e-15, rideal=1,                     # wiring C; rideal=1: ideal R with tc1=tcr, else nwell + n+ diff
         rw=2.0, lnw=12.0, lnp=0.0,              # real R: width, nwell length, n+ diff length (um)
         rf=0.0, cf=0.0, rfw=1.0,                # vbn RC filter: ppolyf_u_3k rf ohm (width rfw um), ideal cf (F); 0 = off
         nsn=1,                                  # MN1/MN2 as nsn in series x nsn in parallel units of w1/l1 (1 = one device)
         cfn=0.0)                                # extra C (F) on each ring stage's foot node f{i} (layout f wiring); 0 = none
CORNERS = ("typical", "ss", "ff", "sf", "fs")


def fet(name, d, g, s, b, typ, w, l, m=1):
    a = w * SAB; p = 2 * (w + SAB)
    return f"X{name} {d} {g} {s} {b} {typ} w={w}u l={l}u ad={a}p as={a}p pd={p}u ps={p}u m={m}\n"


RSH_3K, DW_3K, RT_3K = 3000.0, 0.02256, 33.16   # ppolyf_u_3k sheet (ohm/sq), width loss per side (um), end R (ohm.um)


def rf_length(p):
    """ppolyf_u_3k length (um) giving rf ohm at width rfw (tt, 25 C: body + two end resistors)."""
    w = p["rfw"] - 2 * DW_3K
    return (p["rf"] - 2 * RT_3K / w) * w / RSH_3K


def gnet(p):
    """Net that drives the load gates: vbn, or the filtered vbnf when the RC filter is on."""
    return "vbnf" if p.get("rf", 0) > 0 and p.get("cf", 0) > 0 else "vbn"


def foot(tag, p, out, g="vbn"):
    """Foot network from `out` to ground: base + coarse legs + fine leg (base gate on `g`)."""
    s = fet(f"F{tag}", out, g, "0", "0", "nfet_03v3", p["wfu"], p["ls"], p["k"])
    for b in range(p["bits"]):
        s += fet(f"F{tag}_{b}", out, f"g{b}", "0", "0", "nfet_03v3", p["wfu"], p["ls"], 2 ** b)
    s += fet(f"FF{tag}", out, "vctrl", "0", "0", "nfet_03v3", p["wff"], p["lff"])
    return s


def netlist(p):
    s = ""
    # beta multiplier (constant gm)
    ns = p.get("nsn", 1)
    if ns <= 1:
        s += fet("MN1", "n1", "n1", "0", "0", "nfet_03v3", p["w1"], p["l1"])
        s += fet("MN2", "n2", "n1", "nr", "0", "nfet_03v3", p["w1"], p["l1"], p["kb"])
    else:   # series-parallel array: same W/L and current, nsn^2 x the area, every unit at the ring's channel length
        for nm, top, bot, m in (("MN1", "n1", "0", ns), ("MN2", "n2", "nr", ns * p["kb"])):
            nodes = [top] + [f"{nm.lower()}s{i}" for i in range(1, ns)] + [bot]
            for i in range(ns):
                s += fet(nm if i == 0 else f"{nm}s{i}", nodes[i], "n1", nodes[i + 1], "0", "nfet_03v3", p["w1"], p["l1"], m)
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
    g = gnet(p)
    # coarse gate switches: g_b = bit ? vbn : 0
    for b in range(p["bits"]):
        s += (fet(f"TN{b}", f"g{b}", f"bit{b}", g, "0", "nfet_03v3", 2, 0.28)
              + fet(f"TP{b}", f"g{b}", f"bitb{b}", g, "vdd", "pfet_03v3", 5, 0.28)
              + fet(f"TD{b}", f"g{b}", f"bitb{b}", "0", "0", "nfet_03v3", 1, 0.28))
    s += "Rvbn n1 vbn 1\n"   # vbn = n1 (named net; 1 ohm keeps MN1 as the reference diode)
    if g != "vbn":            # RC low-pass vbn -> vbnf: real hi-R poly, ideal C (a MOS cap on silicon)
        s += f"XRF vbn vbnf 0 ppolyf_u_3k r_width={p['rfw']}e-6 r_length={rf_length(p):.3f}e-6\n"
        s += f"CF vbnf 0 {p['cf']}\n"
    # master: copy of one stage's foot (x mr) into a PMOS diode -> vbp
    total = p["k"] + 2 ** p["bits"] - 1
    s += fet("MPB", "vbp", "vbp", "vdd", "vdd", "pfet_03v3", p["wpb"], p["ls"], max(1, round(p["mr"] * total / 4)))
    s += foot("M", dict(p, wfu=p["wfu"] * p["mr"], wff=p["wff"] * p["mr"]), "vbp", g)
    # ring
    n = p["n"]
    for i in range(n):
        a, y = f"a{i}", f"a{(i + 1) % n}"
        s += fet(f"H{i}", f"h{i}", "vbp", "vdd", "vdd", "pfet_03v3", p["whead"], p["ls"])
        s += fet(f"P{i}", y, a, f"h{i}", "vdd", "pfet_03v3", p["wp"], p["L"])
        s += fet(f"N{i}", y, a, f"f{i}", "0", "nfet_03v3", p["wn"], p["L"])
        s += foot(f"s{i}", p, f"f{i}", g)
        s += f"Cw{i} {y} 0 {p['cw']}\n"
        if p.get("cfn", 0) > 0:   # the master's foot drains on vbp (a diode node), so it gets none
            s += f"Cfn{i} f{i} 0 {p['cfn']}\n"
    ics = " ".join(f"v(a{i})={0 if i % 2 == 0 else 3.3}" for i in range(n))
    return s, ics


def deck(p, corner, points, uic=True, swing=False):
    """uic=False: start each tran from the DC operating point with the ring nodes held at their .ic (needed when
    the reference is too slow to start within the 100 ns before the measurement, e.g. large scaled references)."""
    body, ics = netlist(p)
    src = "".join(f"vbit{b} bit{b} 0 0\nvbitb{b} bitb{b} 0 3.3\n" for b in range(p["bits"]))
    ctl = []
    for (code, vc, t, vdd) in points:
        tag = f"c{code}_v{vc:.2f}_t{t}_d{vdd:.2f}"
        alts = "".join(f"alter vbit{b} {vdd if (code >> b) & 1 else 0}\nalter vbitb{b} {0 if (code >> b) & 1 else vdd}\n"
                       for b in range(p["bits"]))
        sw = "meas tran amin MIN v(a0) FROM=100n TO=200n\nmeas tran amax MAX v(a0) FROM=100n TO=200n\n" if swing else ""
        swe = f'echo "SW {tag} $&amin $&amax"\n' if swing else ""
        ctl.append(f"""option temp={t}
alter vdd {vdd}
alter vctrl {vc}
{alts}tran 5p 200n 0 5p{' uic' if uic else ''}
meas tran t1 WHEN v(a0)={vdd/2} RISE=1 TD=100n
meas tran t2 WHEN v(a0)={vdd/2} RISE=11 TD=100n
meas tran iavg AVG i(vdd) FROM=100n TO=200n
meas tran vb AVG v(vbn) FROM=100n TO=200n
meas tran ir AVG i(vir) FROM=100n TO=200n
{sw}let f = 10/(t2-t1)
let pw = -iavg*{vdd}
echo "RES {tag} {code} {vc} {t} {vdd} $&f $&pw $&vb $&ir"
{swe}destroy all
""")
    return f"""* vco_bias {corner}
.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical
vdd vdd 0 3.3
vctrl vctrl 0 1.65
{src}{body.replace('XMN1 n1 n1 ', 'XMN1 n1i n1 ', 1)}vir n1 n1i 0
.ic {ics}
.control
{''.join(ctl)}quit
.endc
.end
"""


def run(outdir, decks, jobs=1):
    """Run the decks; jobs > 1: that many single-threaded ngspice processes in parallel, from outdir."""
    outdir.mkdir(parents=True, exist_ok=True)
    rel = outdir.relative_to(REPO)
    for name, text in decks:
        (outdir / f"{name}.cir").write_text(text)
    if jobs <= 1:
        script = " ; ".join(f"ngspice -b {rel}/{n}.cir > {rel}/{n}.log 2>&1" for n, _ in decks)
        subprocess.run([OSIC, "bash", "-c", f"cd {REPO} && {script}"], check=False)
    else:
        from concurrent.futures import ThreadPoolExecutor
        init = (REPO / ".spiceinit").read_text()
        (outdir / ".spiceinit").write_text(re.sub(r"num_threads=\d+", "num_threads=1", init))
        one = lambda n: subprocess.run([OSIC, "bash", "-c", f"cd {REPO}/{rel} && ngspice -b {n}.cir > {n}.log 2>&1"],
                                       check=False)
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            list(ex.map(one, [n for n, _ in decks]))
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


def startup_deck(p, corner, temp, tramp=10e-6, tstop=200e-6, op=False):
    """Reference + master only (no ring), all nodes from 0, VDD ramped 0 -> 3.3 V in tramp.
    op=True: the DC operating point at 3.3 V instead (the 'normal' vbn)."""
    body, _ = netlist(dict(p, n=0))
    src = "".join(f"vbit{b} bit{b} 0 0\nvbitb{b} bitb{b} 0 3.3\n" for b in range(p["bits"]))
    if op:
        vdd, ctl = "vdd vdd 0 3.3", f'op\nlet vo = v(vbn)\necho "OP {corner} {temp} $&vo"\n'
    else:
        vdd = f"vdd vdd 0 PWL(0 0 {tramp} 3.3)"
        ctl = f"""tran 10n {tstop} 0 10n uic
meas tran vbn_end FIND v(vbn) AT={tstop}
meas tran vbnf_end FIND v({gnet(p)}) AT={tstop}
meas tran vbn_r FIND v(vbn) AT={tramp * 2}
echo "SU {corner} {temp} $&vbn_end $&vbnf_end $&vbn_r"
"""
    return f"""* startup {corner} {temp}
.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical
{vdd}
vctrl vctrl 0 1.65
{src}{body}.control
option temp={temp}
{ctl}quit
.endc
.end
"""


def ringstart_deck(p, corner, temp, ics, code=0, vctrl=1.65, vdd=3.3):
    """Ring start-up from the given ring-node initial state: DC op with the ring nodes held at `ics` (the reference
    and all other nodes at DC), then released. f over rises 1-6 after 50 ns (early) and after 400 ns (late);
    mode: phase from an a0 rise to the next a2 rise (two stage delays, so rise/fall asymmetry cancels), as a
    fraction of the period: k/N mod 1 in mode k (0.2 for the fundamental of N = 5, 0.6 for mode 3);
    swing: min/max of a0 over 400-500 ns."""
    body, _ = netlist(p)
    src = "".join(f"vbit{b} bit{b} 0 {vdd if (code >> b) & 1 else 0}\nvbitb{b} bitb{b} 0 {0 if (code >> b) & 1 else vdd}\n"
                  for b in range(p["bits"]))
    ic = " ".join(f"v(a{i})={x:.4f}" for i, x in enumerate(ics))
    return f"""* ring start {corner} {temp}
.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical
vdd vdd 0 {vdd}
vctrl vctrl 0 {vctrl}
{src}{body}.ic {ic}
.control
option temp={temp}
tran 5p 500n 0 5p
meas tran e1 WHEN v(a0)={vdd/2} RISE=1 TD=50n
meas tran e6 WHEN v(a0)={vdd/2} RISE=6 TD=50n
meas tran l1 WHEN v(a0)={vdd/2} RISE=1 TD=400n
meas tran l6 WHEN v(a0)={vdd/2} RISE=6 TD=400n
meas tran tf1 WHEN v(a2)={vdd/2} RISE=1 TD=400n
meas tran tf2 WHEN v(a2)={vdd/2} RISE=2 TD=400n
meas tran vmin MIN v(a0) FROM=400n TO=500n
meas tran vmax MAX v(a0) FROM=400n TO=500n
let fe = 5/(e6-e1)
let fl = 5/(l6-l1)
echo "RS $&fe $&fl"
echo "RT $&l1 $&l6 $&tf1 $&tf2 $&vmin $&vmax"
quit
.endc
.end
"""


def map_summary(rows, maxc, target=433.92e6, lo=310e6, hi=620e6):
    """Per PVT point: range, code for target, largest coarse step vs smallest fine range, monotonicity."""
    pts = {}
    for r in rows:
        pts.setdefault((r[0], r[3], r[4]), {})[(r[1], r[2])] = r[5]
    out = []
    for (dk, t, vdd), d in sorted(pts.items()):
        vcs = sorted({k[1] for k in d})
        vmin, vmid, vmax = vcs[0], vcs[len(vcs) // 2], vcs[-1]
        f = lambda c, vc: d.get((c, vc), float("nan"))
        fmin, fmax = f(0, vmin), f(maxc, vmax)
        steps = [f(c + 1, vmid) - f(c, vmid) for c in range(maxc)]
        fine = [f(c, vmax) - f(c, vmin) for c in range(maxc + 1)]
        nonmono = [(c, vc) for vc in vcs for c in range(maxc) if not f(c + 1, vc) > f(c, vc)]
        # codes whose fine range (vctrl min..max) holds the target
        tc = [c for c in range(maxc + 1) if min(f(c, vmin), f(c, vmax)) <= target <= max(f(c, vmin), f(c, vmax))]
        big = max(steps)
        out.append(dict(corner=dk.replace("map_", "").rsplit("_t", 1)[0], temp=t, vdd=vdd, fmin=fmin, fmax=fmax,
                        codes_433=tc, step_max=big, step_max_code=steps.index(big), fine_min=min(fine),
                        fine_over_step=min(fine) / big, nonmono=nonmono,
                        covers=fmin <= lo and fmax >= hi))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sweep", "pvt", "tc", "map", "startup", "ringstart", "cfsweep"])
    ap.add_argument("--cfns", default="0,3,6,10,15,25", help="cfsweep: foot-node C per stage (fF), comma list")
    ap.add_argument("--seeds", type=int, default=6, help="ringstart: random initial states per corner x temp")
    ap.add_argument("--vdd", type=float, default=3.3, help="ringstart: supply")
    ap.add_argument("--code", type=int, default=15)
    ap.add_argument("--vctrl", type=float, default=1.65)
    ap.add_argument("--codes", default=None, help="comma list")
    ap.add_argument("--vcs", default="0,1.0,1.65,2.3,3.3", help="comma list")
    ap.add_argument("--tag", default="a")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--jobs", type=int, default=1, help="parallel ngspice processes (map, startup)")
    ap.add_argument("--corners", default=",".join(CORNERS), help="comma list (map, startup)")
    ap.add_argument("--temps", default="0,27,70", help="comma list (map, startup)")
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
    elif a.mode == "map":   # every code x vctrl {0, 1.65, 3.3} at each corner x temp x VDD; one deck per PVT point
        vcs = [float(v) for v in a.vcs.split(",")] if a.vcs != ap.get_default("vcs") else [0.0, 1.65, 3.3]
        temps = [float(t) for t in a.temps.split(",")]
        decks = [(f"map_{c}_t{t:g}_d{d:.2f}", deck(p, c, [(code, vc, t, d) for code in range(maxc + 1) for vc in vcs], uic=False))
                 for c in a.corners.split(",") for t in temps for d in (3.15, 3.3, 3.45)]
        rows = run(outdir, decks, a.jobs)
        import json
        summ = map_summary(rows, maxc)
        (outdir / "map.csv").write_text("deck,code,vctrl,temp,vdd,f_hz,p_w,vbn,iref\n" + "".join(",".join(map(str, r)) + "\n" for r in rows))
        (outdir / "map_summary.json").write_text(json.dumps(dict(p=p, rows=summ), indent=1))
        print(f"{p}")
        print(f"{'corner':8s} {'T':>3s} {'VDD':>5s} {'fmin':>6s} {'fmax':>6s} {'codes@433.92':>14s} {'stepmax':>7s} {'@c':>3s} "
              f"{'finemin':>7s} {'fine/step':>9s} {'310-620':>7s} nonmono  (MHz)")
        for r in summ:
            cs = f"{r['codes_433'][0]}-{r['codes_433'][-1]}" if r["codes_433"] else "none"
            print(f"{r['corner']:8s} {r['temp']:3.0f} {r['vdd']:5.2f} {r['fmin']/1e6:6.1f} {r['fmax']/1e6:6.1f} {cs:>14s} "
                  f"{r['step_max']/1e6:7.2f} {r['step_max_code']:3d} {r['fine_min']/1e6:7.2f} {r['fine_over_step']:9.2f} "
                  f"{'yes' if r['covers'] else 'NO':>7s} {r['nonmono'] or ''}")
        print(f"wrote {outdir}/map.csv, map_summary.json")
        return
    elif a.mode == "cfsweep":   # foot-node C sweep: codes x Cf x corner x temp at 3.3 V, + fine range at codes 0/maxc
        import json
        codes = [int(c) for c in a.codes.split(",")] if a.codes else [0, 1, 2, 3, 5, 8, 12, maxc]
        pts = lambda t: ([(c, 1.65, t, 3.3) for c in codes] + [(c, vc, t, 3.3) for c in (0, maxc) for vc in (0.0, 3.3)])
        cts = [(c, float(t)) for c in a.corners.split(",") for t in a.temps.split(",")]
        decks = [(f"cf{cf:g}_{c}_t{t:g}", deck(dict(p, cfn=cf * 1e-15), c, pts(t), uic=False, swing=True))
                 for cf in [float(x) for x in a.cfns.split(",")] for c, t in cts]
        run(outdir, decks, a.jobs)
        rows = []
        for n, _ in decks:
            log = (outdir / f"{n}.log").read_text()
            sw = {m.group(1): (float(m.group(2)), float(m.group(3)))
                  for m in re.finditer(r"^SW (\S+) (\S+) (\S+)$", log, re.M)}
            for m in re.finditer(r"^RES (\S+) (\S+) (\S+) (\S+) (\S+) (\S*) (\S+) (\S+) (\S+)$", log, re.M):
                cf, c, t = n.split("_", 2)
                rows.append(dict(cfn=float(cf[2:]), corner=c, temp=float(t[1:]), code=int(m.group(2)), vctrl=float(m.group(3)),
                                 f=float(m.group(6)) if m.group(6) else float("nan"), p_w=float(m.group(7)),
                                 i_a=float(m.group(7)) / 3.3, vmin=sw.get(m.group(1), (float("nan"),) * 2)[0],
                                 vmax=sw.get(m.group(1), (float("nan"),) * 2)[1]))
        (outdir / "cfsweep.json").write_text(json.dumps(dict(p=p, rows=rows), indent=1))
        print(f"wrote {outdir}/cfsweep.json ({len(rows)} points)")
        return
    elif a.mode == "ringstart":   # ring mode check at --code (pass 0) and --vctrl, from random initial states
        import json, random
        cts = [(c, float(t)) for c in a.corners.split(",") for t in a.temps.split(",")]
        decks, meta = [], {}
        _, ics0 = netlist(p)
        alt = [0 if i % 2 == 0 else 3.3 for i in range(p["n"])]     # the deck's own .ic (alternating)
        for c, t in cts:
            for k in range(a.seeds + 1):
                rng = random.Random(f"{c}{t}{k}")    # one generator per seed, so every node gets its own value
                ics = alt if k == 0 else [round(rng.uniform(0, 3.3), 4) for _ in range(p["n"])]
                n = f"rs_{c}_t{t:g}_{'alt' if k == 0 else f's{k}'}"
                decks.append((n, ringstart_deck(p, c, t, ics, a.code, a.vctrl, a.vdd)))
                meta[n] = dict(corner=c, temp=t, seed=k, ics=ics)
        run(outdir, decks, a.jobs)
        rows, bad = [], 0
        for n, _ in decks:
            m = re.search(r"^RS (\S*) (\S*)$", (outdir / f"{n}.log").read_text(), re.M)
            fe = float(m.group(1)) if m and m.group(1) else float("nan")
            fl = float(m.group(2)) if m and m.group(2) else float("nan")
            rt = re.search(r"^RT (\S+) (\S+) (\S+) (\S+) (\S+) (\S+)$", (outdir / f"{n}.log").read_text(), re.M)
            ph, vmin, vmax = float("nan"), float("nan"), float("nan")
            if rt:
                l1, l6, tf1, tf2, vmin, vmax = map(float, rt.groups())
                T = (l6 - l1) / 5
                tf = tf1 if tf1 > l1 else tf2
                ph = ((tf - l1) % T) / T
            rows.append(dict(name=n, **meta[n], f_early=fe, f_late=fl, phase=ph, vmin=vmin, vmax=vmax))
        print(f"{p}")
        print(f"{'corner':8s} {'T':>3s} {'f alt MHz':>9s} alt start: mode, phase, a0 swing | random seeds: f late / f alt, mode")
        for c, t in cts:
            rs = [r for r in rows if r["corner"] == c and r["temp"] == t]
            f0 = rs[0]["f_late"]
            for r in rs:
                r["ratio"] = r["f_late"] / f0
                # mode k (odd, < 2N, not a multiple of N) whose k/N mod 1 is nearest the measured phase; -1 if nothing within 0.07
                ks = [k for k in range(1, 2 * p["n"], 2) if k % p["n"]]
                d = {k: abs((r["phase"] - k / p["n"] + 0.5) % 1 - 0.5) for k in ks} if r["phase"] == r["phase"] else {}
                kb = min(d, key=d.get) if d else -1
                r["mode"] = kb if d and d[kb] < 0.07 else -1
                r["ok"] = (r["f_late"] == r["f_late"] and 0.95 < r["ratio"] < 1.05 and abs(r["f_early"] / r["f_late"] - 1) < 0.05
                           and r["mode"] == 1)
                bad += not r["ok"]
            print(f"{c:8s} {t:3.0f} {f0/1e6:9.1f} mode {rs[0]['mode']} ph {rs[0]['phase']:.3f} swing {rs[0]['vmin']:.2f}-{rs[0]['vmax']:.2f} | "
                  + " ".join(f"{r['ratio']:.3f}/m{r['mode']}{'' if r['ok'] else '!'}" for r in rs[1:])
                  + ("" if rs[0]["ok"] else "  (alt start not in the fundamental or not settled!)"))
        (outdir / "ringstart.json").write_text(json.dumps(dict(p=p, code=a.code, rows=rows), indent=1))
        print("RINGSTART", "OK" if not bad else f"FAIL ({bad} runs not in the fundamental mode or not settled)")
        return
    elif a.mode == "startup":   # reference start-up from a VDD ramp, filter as set
        cts = [(c, t) for c in a.corners.split(",") for t in a.temps.split(",")]
        decks = [(f"su_{c}_t{t}", startup_deck(p, c, t)) for c, t in cts]
        run(outdir, decks + [(f"op_{c}_t{t}", startup_deck(p, c, t, op=True)) for c, t in cts], a.jobs)
        print(f"{'corner':8s} {'T':>3s} {'vbn@20us':>9s} {'vbn@200u':>9s} {'vbnf@200u':>9s} {'vbn op':>7s} ok")
        allok = True
        for n, _ in decks:
            log = (outdir / f"{n}.log").read_text()
            su = re.search(r"^SU (\S+) (\S+) (\S+) (\S+) (\S+)$", log, re.M)
            op = re.search(r"^OP \S+ \S+ (\S+)$", (outdir / f"op{n[2:]}.log").read_text(), re.M)
            if not (su and op):
                print(f"{n}: no result, see log"); allok = False; continue
            ve, vf, vr, vo = float(su.group(3)), float(su.group(4)), float(su.group(5)), float(op.group(1))
            ok = abs(ve - vo) < 0.01 * vo and abs(vf - vo) < 0.01 * vo
            allok &= ok
            print(f"{su.group(1):8s} {su.group(2):>3s} {vr:9.4f} {ve:9.4f} {vf:9.4f} {vo:7.4f} {'OK' if ok else 'FAIL'}")
        print("STARTUP", "OK" if allok else "FAIL")
        return
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
