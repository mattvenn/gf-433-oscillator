#!/usr/bin/env python3
"""Monte Carlo (mismatch only) of the cfed DAC current, chosen sizing (wfu = wff = 0.30, lnw 5.023, rf 1M / cf 20p).

    python3 sim/mc/dac_mc.py dc   --corner typical --n 500 --seed0 1000 [--jobs 8]
    python3 sim/mc/dac_mc.py tran --corner typical --seeds 0,1012,1044,1301 --codes 15,16 [--jobs 8]   (seed 0: mismatch off)
    python3 sim/mc/dac_mc.py nom  --corner typical            # mismatch off, same deck (nominal)

Mismatch: the gf180mcuD models draw mis_vth / mis_k (agauss) per nfet_03v3/pfet_03v3 subckt instance; they are
active when .param sw_stat_mismatch=1 (global variation stays off: sw_stat_global=0, the corner lib sets process).
Proven per instance and per seed by sim/mc/mm_proof.sh. One sample per ngspice process, .options seed=<seed>.
The models size sigma by one instance's W*L and ignore m, so every m>1 device is expanded into m instances
(the layout draws separate unit devices anyway).

Reference: the const-gm reference + RC filter are replaced by an ideal source on vbnf at the corner's nominal DC
value (VBN, from a mismatch-off run of the full netlist): with the full reference every op needed gmin stepping
(about 0.5 s per op), too slow for the time box. The reference's own mismatch is a common scale on every coarse
leg (no DNL); its effect on fine/step is not included.
Netlist = vco_bias.netlist() (reference + filter + switches + DAC + ring), unchanged order so a seed gives the same
DAC draws in both modes. The DAC drains sit on vgd with a 0 V ammeter Vam vg->vgd.
  dc  : ring nodes a0..a4 held at 0 V by sources, Cvg replaced by a source Vvg holding vg at the corner's operating value (tt 1.894, ss 1.680, ff 2.093 V);
        op at codes 0-31 x vctrl {0, 1.65, 3.3}: I_DAC = i(Vam). Output build/mc/dc_<corner>.json.
  tran: the ring as in the schematic (Cvg 3 pF, cw 3 fF), f at mid-swing over 100-200 ns, codes x vctrl {0,1.65,3.3}.
"""
import argparse, json, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim" / "vco"))
import vco_bias as vb  # noqa: E402
import topo_cmp as tcm  # noqa: E402

SETS = dict(topo="cfed", kc=0.75, k=6, cvg=3e-12, cw=3e-15, ka=16.0, rf=1e6, cf=20e-12, lnw=5.023, wfu=0.30, wff=0.30)
VBN = {"typical": 1.23197, "ss": 1.38407, "ff": 1.08278}   # nominal DC vbn (= vbnf) of the reference, 27 C
REF = re.compile(r"^(XMN\d|XMP\d|XMS\d|RB|XRB|Rvbn|XRF|CF\b|vir\b)", re.I)
VG = {"typical": 1.894, "ss": 1.680, "ff": 2.093}   # vg at the 433.92 code, 27 C (map.csv)
VCS = (0.0, 1.65, 3.3)
FINE_CODES = (0, 7, 8, 15, 16, 23, 24, 31)   # dc: vctrl 0 / 3.3 here too (with vg held, fine dI is code-independent)
OUT = REPO / "build" / "mc2"   # build/mc: an earlier, slower variant (full reference)


def params():
    return {**vb.P, **tcm.WINNER, **SETS}


def expand_m(body):
    out = []
    for ln in body.splitlines():
        m = re.search(r"\bm=(\d+)\s*$", ln)
        if ln.startswith("X") and m and int(m.group(1)) > 1:
            t = ln.split()
            for i in range(int(m.group(1))):
                out.append(" ".join([f"{t[0]}_u{i}"] + t[1:-1] + ["m=1"]))
        else:
            out.append(ln)
    return "\n".join(out) + "\n"


def body(p, mode, corner):
    b, ics = vb.netlist(p)
    lines = []
    for ln in b.splitlines():
        t = ln.split()
        if REF.match(t[0]):   # reference + filter -> ideal source at its nominal DC value (see the docstring)
            continue
        if t[0].startswith(("XFC", "XFFC")):   # DAC devices: drain vg -> vgd
            assert t[1] == "vg"
            t[1] = "vgd"
            ln = " ".join(t)
        if t[0] == "Cvg" and mode == "dc":
            ln = f"Vvg vg 0 {VG[corner]}"
        lines.append(ln)
    lines.append(f"Vvbn vbnf 0 {VBN[corner]}")
    lines.append("Vam vg vgd 0")
    if mode == "dc":   # ring nodes held at 0 V: N devices off, the op converges at once (devices kept: same draws)
        lines += [f"Va{i} a{i} 0 0" for i in range(p["n"])]
    return expand_m("\n".join(lines)), ics


def header(corner, seed, mm=1):
    return f"""* dac_mc {corner} seed {seed} mismatch {mm}
.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical
.param sw_stat_mismatch={mm}
.options seed={seed}
vdd vdd 0 3.3
vctrl vctrl 0 1.65
""" + "".join(f"vbit{b} bit{b} 0 0\nvbitb{b} bitb{b} 0 3.3\n" for b in range(5))


def dc_deck(p, corner, seed, mm=1):
    b, _ = body(p, "dc", corner)
    ctl = "option temp=27\n"
    for code in range(32):
        ctl += tcm.bits(code, 3.3)
        for vc in (VCS if code in FINE_CODES else (1.65,)):
            ctl += f"alter vctrl {vc}\nop\necho \"ROW {code} {vc} $&vam#branch $&v(vbnf)\"\ndestroy all\n"
    return header(corner, seed, mm) + b + f".control\n{ctl}quit\n.endc\n.end\n"


def tran_deck(p, corner, seed, codes, mm=1):
    b, ics = body(p, "tran", corner)
    ctl = ""
    for code in codes:
        for vc in VCS:
            ctl += f"""option temp=27
alter vctrl {vc}
{tcm.bits(code, 3.3)}tran 5p 200n 0 5p
meas tran amin MIN v(a0) FROM=100n TO=200n
meas tran amax MAX v(a0) FROM=100n TO=200n
let vth = (amin + amax)/2
meas tran t1 WHEN v(a0)=$&vth RISE=1 TD=100n
meas tran t2 WHEN v(a0)=$&vth RISE=11 TD=100n
meas tran ia AVG i(vam) FROM=100n TO=200n
meas tran vga AVG v(vg) FROM=100n TO=200n
let f = 10/(t2-t1)
echo "TR {code} {vc} $&f $&ia $&vga"
destroy all
"""
    return header(corner, seed, mm) + b + f".ic {ics}\n.control\n{ctl}quit\n.endc\n.end\n"


def run1(d, name, text, pat):
    d.mkdir(parents=True, exist_ok=True)
    (d / ".spiceinit").write_text("set ng_nomodcheck\nset num_threads=1\noption noinit\n")
    (d / f"{name}.cir").write_text(text)
    r = subprocess.run(["ngspice", "-b", f"{name}.cir"], cwd=d, capture_output=True, text=True)
    (d / f"{name}.log").write_text(r.stdout + r.stderr)
    return [tuple(float(x) for x in m) for m in re.findall(pat, r.stdout, re.M)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("dc", "tran", "nom"))
    ap.add_argument("--corner", default="typical")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("--seeds", default="")
    ap.add_argument("--codes", default="15,16")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    p = params()
    t0 = time.time()
    rowpat = r"^ROW (\S+) (\S+) (\S+) (\S+)$"
    if a.mode in ("dc", "nom"):
        seeds = [0] if a.mode == "nom" else list(range(a.seed0, a.seed0 + a.n))
        mm = 0 if a.mode == "nom" else 1
        d = OUT / f"{a.mode}_{a.corner}"
        with ThreadPoolExecutor(a.jobs) as ex:
            rows = list(ex.map(lambda s: run1(d, f"s{s}", dc_deck(p, a.corner, s, mm), rowpat), seeds))
        res = {}
        for s, r in zip(seeds, rows):
            if len(r) != 32 + 2 * len(FINE_CODES):
                print(f"seed {s}: {len(r)} rows", flush=True)
                continue
            by = {(int(x[0]), x[1]): x[2] for x in r}
            res[s] = {"i": [[by.get((c, vc)) for vc in VCS] for c in range(32)], "vbnf": r[0][3]}
        (OUT / f"{a.mode}_{a.corner}.json").write_text(json.dumps(dict(corner=a.corner, vg=VG[a.corner], vcs=VCS,
                                                                       samples=res)))
        print(f"{a.mode} {a.corner}: {len(res)}/{len(seeds)} samples, {time.time() - t0:.0f} s")
    else:
        seeds = [int(s) for s in a.seeds.split(",")]
        codes = [int(c) for c in a.codes.split(",")]
        d = OUT / f"tran_{a.corner}"
        jobs = [(s, c) for s in seeds for c in codes]
        with ThreadPoolExecutor(a.jobs) as ex:
            rows = list(ex.map(lambda sc: run1(d, f"s{sc[0]}_c{sc[1]}", tran_deck(p, a.corner, sc[0], [sc[1]], 0 if sc[0] == 0 else 1),
                                               r"^TR (\S+) (\S+) (\S+) (\S+) (\S+)$"), jobs))
        res = [dict(seed=s, code=int(r[0]), vctrl=r[1], f=r[2], i=r[3], vg=r[4]) for (s, c), rr in zip(jobs, rows)
               for r in rr]
        (OUT / f"tran_{a.corner}.json").write_text(json.dumps(res, indent=1))
        for x in res:
            print(x)
        print(f"tran {a.corner}: {len(res)} rows, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
