#!/usr/bin/env python3
"""Range check of the extracted v3 core at the chosen sizing (docs/cfed_sizing_results.md): w = 1.2
(wfu = wff = 0.30), lnw = 5.023, rf = 1 Mohm, cf = 20 pF, cw 3 fF (schematic), ka 16.

    python3 layout/gen/pex_check_v3.py [--tag v3_w30chk] [--jobs 6]

Deck = sim/vco/topo_cmp.deck() of the full schematic (const-gm winner reference + RC filter); for the RC variant
the cfed core elements are replaced by one Xcore of layout/pex/ring_core_<tag>_rc.spice with its gate port on
vbnf. No uic: the tran starts from the DC operating point (ring nodes held at .ic), so vbnf starts at its DC value
(the filtered gates draw no DC current). f from the a0 mid-swing crossings over 100-200 ns.
Points per corner {typical, ss, ff} at 27 C, 3.3 V: code 0 vctrl 0, code 31 vctrl 3.3, the 433.92 code at 1.65.
Output: build/pex_check_v3/results.txt (+ results.json).
"""
import argparse, json, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "sim" / "vco"))
sys.path.insert(0, str(HERE))
import vco_bias as vb  # noqa: E402
import topo_cmp as tcm  # noqa: E402
import export_core_v3 as ex3  # noqa: E402

CORE = re.compile(r"^(X(P|N|FC|FFC|TN|TP|TD)\S*|Cvg|Cw\d+)\s", re.I)
CODE433 = {"typical": 9, "ss": 11, "ff": 7}
SETS = dict(topo="cfed", kc=0.75, k=6, cvg=3e-12, cw=3e-15, ka=16.0, rf=1e6, cf=20e-12, lnw=5.023, wfu=0.30, wff=0.30)


def params():
    return {**vb.P, **tcm.WINNER, **SETS}


EXTRA = {}   # --rc433: RC only, the code(s) nearest 433.92 MHz in the extracted core, at vctrl 0 / 1.65 / 3.3


def points(corner):
    if corner in EXTRA:
        return [(c, vc, 27, 3.3) for c in EXTRA[corner] for vc in (0.0, 1.65, 3.3)]
    return [(0, 0.0, 27, 3.3), (CODE433[corner], 1.65, 27, 3.3), (31, 3.3, 27, 3.3)]


def rc_deck(p, corner, tag):
    d = tcm.deck(p, corner, points(corner))
    g = vb.gnet(p)
    out, n = [], 0
    for ln in d.splitlines():
        if CORE.match(ln):
            n += 1
            continue
        if ln.startswith(".ic "):
            out.append(f"Xcore vdd 0 {g} vctrl " + " ".join(ex3.ports(p)[4:]) + " ring_core")
            out.append(f".include {REPO / 'layout' / 'pex' / f'ring_core_{tag}_rc.spice'}")
        out.append(ln)
    assert n == 38, n   # 5 P, 5 N, 5 Cw, Cvg, FC + 5 FC_b + FFC, 15 switches
    return "\n".join(out) + "\n"


def run1(out, name, text):
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    (d / ".spiceinit").write_text("set ng_nomodcheck\nset num_threads=1\noption noinit\n")
    (d / f"{name}.cir").write_text(text)
    t0 = time.time()
    subprocess.run(["ngspice", "-b", f"{name}.cir"], cwd=d, stdout=open(d / f"{name}.log", "w"), stderr=subprocess.STDOUT)
    return name, tcm.parse((d / f"{name}.log").read_text()), time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v3_w30chk")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--rc433", default="", help="e.g. typical:12,ss:14:15,ff:10 -> build/pex_check_v3/rc433.txt")
    a = ap.parse_args()
    p = params()
    if a.rc433:
        for it in a.rc433.split(","):
            c, *codes = it.split(":")
            EXTRA[c] = [int(x) for x in codes]
        out = REPO / "build" / "pex_check_v3"
        with ThreadPoolExecutor(a.jobs) as ex:
            res = list(ex.map(lambda c: (c, run1(out, f"rc433_{c}", rc_deck(p, c, a.tag))[1]), EXTRA))
        txt = "corner code vctrl f_rc_MHz\n" + "".join(f"{c} {r['code']} {r['vctrl']} {r['f'] / 1e6:.2f}\n"
                                                    for c, rows in res for r in rows)
        (out / "rc433.txt").write_text(txt)
        print(txt)
        return
    assert vb.gnet(p) == "vbnf"
    out = REPO / "build" / "pex_check_v3"
    jobs = [(f"{v}_{c}", tcm.deck(p, c, points(c)) if v == "sch" else rc_deck(p, c, a.tag))
            for c in CODE433 for v in ("sch", "rc")]
    t0 = time.time()
    with ThreadPoolExecutor(a.jobs) as ex:
        res = {n: (rows, dt) for n, rows, dt in ex.map(lambda j: run1(out, *j), jobs)}
    lines = [f"# pex_check_v3 tag={a.tag} {time.strftime('%Y-%m-%d %H:%M')} 27 C 3.3 V, total {time.time() - t0:.0f} s",
             f"{'corner':8s} {'code':>4s} {'vctrl':>5s} {'f sch':>8s} {'f rc':>8s} {'rc/sch':>6s} {'vg sch':>6s} {'vg rc':>6s}"]
    js = []
    for c in CODE433:
        for (code, vc, t, vdd), s, r in zip(points(c), res[f"sch_{c}"][0], res[f"rc_{c}"][0]):
            lines.append(f"{c:8s} {code:4d} {vc:5.2f} {s['f'] / 1e6:8.2f} {r['f'] / 1e6:8.2f} {r['f'] / s['f']:6.3f} "
                         f"{s['vg']:6.3f} {r['vg']:6.3f}")
            js.append(dict(corner=c, code=code, vctrl=vc, f_sch=s["f"], f_rc=r["f"], vg_sch=s["vg"], vg_rc=r["vg"]))
    lines.append("# run s: " + " ".join(f"{k} {v[1]:.0f}" for k, v in res.items()))
    txt = "\n".join(lines) + "\n"
    (out / "results.txt").write_text(txt)
    (out / "results.json").write_text(json.dumps(js, indent=1))
    print(txt)


if __name__ == "__main__":
    main()
