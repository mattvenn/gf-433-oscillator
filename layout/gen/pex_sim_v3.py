#!/usr/bin/env python3
"""Schematic vs extracted cfed ring core (layout/ring_core_v3.gds): f and core power at tt, 27 C, vctrl 1.65 V.

    python3 layout/gen/pex_sim_v3.py [--set wfu=0.30 --tag v3_w30] [--codes 0,6,15,31] [--variants ...] [--jobs 8]

Adapted from pex_sim_v2.py.
1. ref  : vco_bias.deck() for the cfed settings (const-gm winner reference + schematic core, cw 3 fF, ideal Cvg).
          Gives vbn for step 2.
2. The same deck() with the reference replaced by an ideal vbn source at that value, and the core replaced by
   one instance Xcore of .subckt ring_core (export_core_v3 port order: ... vg a0..a4):
     cw<N> : schematic core, ideal Cvg, wiring cap N fF on every ring node (cw0, cw3, cw6 bracket the layout)
     mosdc : schematic core, cw 0, the MOS decap instead of the ideal Cvg (checks the decap substitution)
     c / rc: layout/pex/ring_core_<tag>_<mode>.spice (layout/gen/pex_v3.sh), MOS decap included.
   Effective cw: the cw at which the schematic (linear interpolation of 1/f between cw0/cw3/cw6) gives the C-only f.
Starts from the DC operating point with the ring nodes held at the .ic (pex_sim_v2's default).
Outputs: build/pex_sim_<tag>/results.txt.
"""
import argparse, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "sim" / "vco"))
sys.path.insert(0, str(HERE))
import vco_bias  # noqa: E402
import export_core_v3 as ex3  # noqa: E402
import ring_core_v3 as gen  # noqa: E402

CORE = re.compile(r"^(X(P|N|FC|FFC|TN|TP|TD)\S*|Cvg|Cw\d+)\s", re.I)   # cfed core elements of vco_bias.netlist()


def core_deck(p, code, vb, variant, tag):
    d = vco_bias.deck(p, "typical", [(code, 1.65, 27, 3.3)], uic=False)
    out = []
    for ln in d.splitlines():
        t = ln.split()
        if t and (ex3.REF.match(t[0]) or CORE.match(ln)):
            continue
        if t and t[0] == "vir":
            out += ["vir n1 0 0", f"vvbn vbn 0 {vb:.6f}",
                    "Xcore vdd 0 vbn vctrl " + " ".join(ex3.ports(p)[4:]) + " ring_core", "@SUBCKT@"]
            continue
        out.append(ln)
    deck = "\n".join(out) + "\n"
    assert deck.count("@SUBCKT@") == 1
    if variant.startswith("cw"):
        sub = ex3.subckt(dict(p, cw=float(variant[2:]) * 1e-15), keep_cw=True, ideal_cvg=True)
    elif variant == "mosdc":
        sub = ex3.subckt(dict(p, cw=0.0), keep_cw=False, ideal_cvg=False)
    else:
        sub = ""
        pex = REPO / "layout" / "pex" / f"ring_core_{tag}_{variant}.spice"
        deck = re.sub(r"^\.end\s*$", f".include {pex}\n.end", deck, flags=re.M)
    deck = deck.replace("@SUBCKT@", sub.rstrip())
    return deck


def stab(text):
    """The cfed ring swings vg..VDD, so deck()'s VDD/2 crossings may never happen: measure at mid-swing
    (amin+amax)/2 as sim/pn/cfed_noise.py does, and add a settling check (f over rises 1-6 vs 6-11)."""
    m1 = re.search(r"^meas tran t1 WHEN v\(a0\)=(\S+) RISE=1 TD=(\S+)$", text, re.M)
    m2 = re.search(r"^meas tran t2 WHEN v\(a0\)=(\S+) RISE=11 TD=(\S+)$", text, re.M)
    assert m1 and m2, "deck() measurement lines changed"
    td = m1.group(2)
    pre = ("meas tran amin MIN v(a0) FROM=100n TO=200n\nmeas tran amax MAX v(a0) FROM=100n TO=200n\n"
           "let vth = (amin + amax)/2\n")
    text = text.replace(m1.group(0), pre + f"meas tran t1 WHEN v(a0)=$&vth RISE=1 TD={td}")
    add = (f"meas tran t2 WHEN v(a0)=$&vth RISE=11 TD={td}\nmeas tran t6 WHEN v(a0)=$&vth RISE=6 TD={td}\n"
           "meas tran vgav AVG v(vg) FROM=100n TO=200n\n"
           "let fa = 5/(t6-t1)\nlet fb = 5/(t2-t6)\necho \"CHK $&fa $&fb $&amin $&amax $&vgav\"")
    return text.replace(m2.group(0), add)


def run1(out, name, text):
    text = stab(text)
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    (d / ".spiceinit").write_text("set ng_nomodcheck\nset num_threads=1\noption noinit\n")
    (d / f"{name}.cir").write_text(text)
    t0 = time.time()
    subprocess.run(["ngspice", "-b", f"{name}.cir"], cwd=d, stdout=open(d / f"{name}.log", "w"),
                   stderr=subprocess.STDOUT)
    log = (d / f"{name}.log").read_text()
    rows = re.findall(r"^RES (\S+) (\S+) (\S+) (\S+) (\S+) (\S*) (\S+) (\S+) (\S+)$", log, re.M)
    chk = re.findall(r"^CHK (\S+) (\S+) (\S+) (\S+) (\S+)$", log, re.M)
    warn, extra = [], None
    if chk:
        fa, fb, amin, amax, vg = (float(x) for x in chk[0])
        extra = (amin, amax, vg)
        if abs(fa / fb - 1) > 0.01:
            warn.append(f"UNSETTLED f(rise1-6)={fa / 1e6:.1f} f(rise6-11)={fb / 1e6:.1f} MHz")
    warn += [w for w in ("singular", "timestep too small", "Error") if w.lower() in log.lower()]
    return name, rows, warn, time.time() - t0, extra, log.splitlines()[-3:]


def interp_cw(fc, fs):
    """cw (fF) where the schematic 1/f (piecewise linear in cw) equals 1/fc. fs: {cw: f}."""
    pts = sorted((cw, 1 / f) for cw, f in fs.items() if f == f and f > 0)
    y = 1 / fc
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if y1 != y0 and min(y0, y1) <= y <= max(y0, y1):
            return x0 + (y - y0) * (x1 - x0) / (y1 - y0)
    (x0, y0), (x1, y1) = (pts[0], pts[1]) if y < pts[0][1] else (pts[-2], pts[-1])
    return x0 + (y - y0) * (x1 - x0) / (y1 - y0)   # extrapolated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--tag", default="v3")
    ap.add_argument("--codes", default="0,6,15,31")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--variants", default="ref,cw0,cw3,cw6,mosdc,c,rc")
    a = ap.parse_args()
    p = gen.params(a.set)
    out = REPO / "build" / f"pex_sim_{a.tag}"
    out.mkdir(parents=True, exist_ok=True)
    for mode in ("c", "rc"):
        pex = REPO / "layout" / "pex" / f"ring_core_{a.tag}_{mode}.spice"
        if mode in a.variants and not pex.exists():
            raise SystemExit(f"missing {pex}: run layout/gen/pex_v3.sh {mode}")
    codes = [int(c) for c in a.codes.split(",")]
    var = a.variants.split(",")
    t_all = time.time()
    res = {}
    with ThreadPoolExecutor(a.jobs) as exr:
        ref = list(exr.map(lambda c: run1(out, f"ref_c{c}", vco_bias.deck(p, "typical", [(c, 1.65, 27, 3.3)], uic=False)),
                           codes))
    vb = {}
    for (name, rows, warn, dt, extra, tail), c in zip(ref, codes):
        r = rows[0] if rows else None
        vb[c] = float(r[7]) if r else float("nan")
        res[("ref", c)] = (r, warn, dt, extra, tail)
    jobs = [(v, c) for v in var if v != "ref" for c in codes]
    with ThreadPoolExecutor(a.jobs) as exr:
        outs = list(exr.map(lambda vc: run1(out, f"{vc[0]}_c{vc[1]}", core_deck(p, vc[1], vb[vc[1]], vc[0], a.tag)), jobs))
    for (name, rows, warn, dt, extra, tail), (v, c) in zip(outs, jobs):
        res[(v, c)] = (rows[0] if rows else None, warn, dt, extra, tail)
    fget = lambda v, c: (float(res[(v, c)][0][5]) if res.get((v, c)) and res[(v, c)][0] and res[(v, c)][0][5]
                         else float("nan"))
    lines = [f"# pex_sim_v3 tag={a.tag} wfu={p['wfu']} wff={p['wff']} {time.strftime('%Y-%m-%d %H:%M')}  tt 27C vdd 3.3 "
             f"vctrl 1.65, total {time.time() - t_all:.0f} s",
             f"{'variant':7s} {'code':>4s} {'f MHz':>8s} {'P mW':>7s} {'vbn V':>7s} {'vg V':>6s} {'a0 min':>6s} "
             f"{'a0 max':>6s} {'df vs cw3':>9s} {'run s':>6s}  warnings"]
    for v in var:
        for c in codes:
            r, warn, dt, extra, tail = res[(v, c)]
            f = fget(v, c)
            pw = float(r[6]) if r else float("nan")
            fs = fget("cw3", c)
            df = f"{100 * (f / fs - 1):+.1f}%" if v not in ("cw3",) else ""
            amin, amax, vgv = extra if extra else (float("nan"),) * 3
            lines.append(f"{v:7s} {c:4d} {f / 1e6:8.2f} {pw * 1e3:7.3f} {vb[c]:7.4f} {vgv:6.3f} {amin:6.3f} {amax:6.3f} "
                         f"{df:>9s} {dt:6.0f}  {','.join(warn)}{'' if r else ' NO RESULT: ' + ' | '.join(tail)}")
    if all(v in var for v in ("cw0", "cw3", "cw6")):
        lines.append("# effective cw (fF): schematic 1/f(cw) interpolated to the extracted f")
        for mode in ("c", "rc"):
            if mode in var:
                lines.append(f"#  {mode:3s} " + "  ".join(
                    f"code {c}: {interp_cw(fget(mode, c), {cw: fget(f'cw{cw}', c) for cw in (0, 3, 6)}):.2f}"
                    for c in codes))
    for mode in ("c", "rc"):
        if mode in var:
            fs = [fget(mode, c) for c in codes]
            lines.append(f"# {mode} monotonic in code: {all(b > a for a, b in zip(fs, fs[1:]))}")
    txt = "\n".join(lines) + "\n"
    (out / "results.txt").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
