#!/usr/bin/env python3
"""Schematic vs extracted ring core: f and power at tt, 27 C, vctrl 1.65 V, codes 0 / 10 / 31.

    python3 layout/gen/pex_sim.py [--codes 0,10,31] [--jobs 8] [--variants ref,sch,sch0,lvs,c,rc]

1. ref  : vco_bias.deck() as is (const-gm reference + schematic core, cw = 2 fF). Gives vbn for step 2.
2. The same deck() text with the reference replaced by an ideal source at that vbn, and the core lines replaced
   by one instance Xcore of .subckt ring_core:
     sch  : the schematic core (export_core.py, with the cw = 2 fF wiring caps)
     sch0 : the schematic core without cw (must equal 'lvs': checks the swap itself)
     lvs / c / rc : layout/pex/ring_core_<mode>.spice (layout/gen/pex.sh), swapped in for the schematic subckt
                    the way tools/pexswap.py does it (pexswap itself is fixed to layout/pex/<block>.spice with a
                    build/-relative include, so the include here is an absolute path to the chosen extraction).
Power: ref = whole deck (reference included); the others = the core only (the ideal vbn source carries no current).
Each run is its own ngspice process (num_threads=1), at most --jobs at a time. Outputs: build/pex_sim/.
"""
import argparse, os, re, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim" / "vco"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vco_bias  # noqa: E402
import export_core  # noqa: E402

OUT = REPO / "build" / "pex_sim"
CORE = re.compile(r"^X(H|P|N|F|FF|TN|TP|TD|MPB)\S*\s", re.I)   # core devices in vco_bias.netlist()


def params():
    p = dict(vco_bias.P)
    p.update(export_core.REAL_R)
    return p


def subckt_sch(p, keep_cw):
    lines, _ = export_core.core(p, keep_cw)
    return f".subckt ring_core {' '.join(export_core.ports(p))}\n" + "\n".join(lines) + "\n.ends\n"


def core_deck(p, code, vb, variant):
    """deck() for one point with the reference -> ideal vbn and the core -> Xcore ring_core."""
    d = vco_bias.deck(p, "typical", [(code, 1.65, 27, 3.3)])
    out = []
    for ln in d.splitlines():
        t = ln.split()
        if t and (export_core.REF.match(t[0]) or CORE.match(ln) or t[0].upper().startswith("CW")):
            continue
        if t and t[0] == "vir":
            out.append("vir n1 0 0")                       # reference gone: keep i(vir) defined (0 A)
            out.append(f"vvbn vbn 0 {vb:.6f}")
            out.append("Xcore vdd 0 vbn vctrl " + " ".join(export_core.ports(p)[4:]) + " ring_core")
            out.append("@SUBCKT@")
            continue
        out.append(ln)
    deck = "\n".join(out) + "\n"
    assert "@SUBCKT@" in deck
    deck = deck.replace("@SUBCKT@", subckt_sch(p, keep_cw=(variant == "sch")).rstrip())
    if variant in ("lvs", "c", "rc"):
        pex = REPO / "layout" / "pex" / f"ring_core_{variant}.spice"
        gds = REPO / "layout" / "ring_core.gds"
        if pex.stat().st_mtime < gds.stat().st_mtime:
            raise SystemExit(f"{pex} is older than {gds}: rerun layout/gen/pex.sh {variant}")
        pat = re.compile(r"^\.subckt\s+ring_core\s.*?^\.ends\b[^\n]*\n", re.S | re.M | re.I)
        deck, n = pat.subn("", deck)
        assert n == 1
        deck = re.sub(r"^\.end\s*$", f".include {pex}\n.end", deck, flags=re.M)
    return deck


def stab(text):
    """Add a mode/settling check: f over rises 1-6 vs 6-11 of the measured window."""
    m = re.search(r"^meas tran t2 WHEN v\(a0\)=(\S+) RISE=11 TD=(\S+)$", text, re.M)
    assert m, "deck() measurement lines changed"
    add = (f"meas tran t6 WHEN v(a0)={m.group(1)} RISE=6 TD={m.group(2)}\n"
           "let fa = 5/(t6-t1)\nlet fb = 5/(t2-t6)\necho \"CHK $&fa $&fb\"\n")
    return text.replace(m.group(0), m.group(0) + "\n" + add.rstrip("\n"))


def run1(name, text):
    text = stab(text)
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / ".spiceinit").write_text("set ng_nomodcheck\nset num_threads=1\noption noinit\n")
    (d / f"{name}.cir").write_text(text)
    t0 = time.time()
    subprocess.run(["ngspice", "-b", f"{name}.cir"], cwd=d, stdout=open(d / f"{name}.log", "w"),
                   stderr=subprocess.STDOUT)
    log = (d / f"{name}.log").read_text()
    rows = re.findall(r"^RES (\S+) (\S+) (\S+) (\S+) (\S+) (\S*) (\S+) (\S+) (\S+)$", log, re.M)
    chk = re.findall(r"^CHK (\S+) (\S+)$", log, re.M)
    warn = []
    if chk:
        fa, fb = float(chk[0][0]), float(chk[0][1])
        if abs(fa / fb - 1) > 0.01:
            warn.append(f"UNSETTLED f(rise1-6)={fa / 1e6:.1f} f(rise6-11)={fb / 1e6:.1f} MHz")
    warn += [w for w in ("Transient op started", "singular", "timestep too small", "Error") if w.lower() in log.lower()]
    return name, rows, warn, time.time() - t0, log.splitlines()[-3:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", default="0,10,31")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--variants", default="ref,sch,sch0,lvs,c,rc")
    a = ap.parse_args()
    p = params()
    codes = [int(c) for c in a.codes.split(",")]
    var = a.variants.split(",")
    OUT.mkdir(parents=True, exist_ok=True)
    t_all = time.time()
    res = {}
    with ThreadPoolExecutor(a.jobs) as ex:
        ref = list(ex.map(lambda c: run1(f"ref_c{c}", vco_bias.deck(p, "typical", [(c, 1.65, 27, 3.3)])), codes))
    vb = {}
    for (name, rows, warn, dt, tail), c in zip(ref, codes):
        r = rows[0] if rows else None
        vb[c] = float(r[7]) if r else float("nan")
        res[("ref", c)] = (r, warn, dt, tail)
    jobs = [(v, c) for v in var if v != "ref" for c in codes]
    with ThreadPoolExecutor(a.jobs) as ex:
        outs = list(ex.map(lambda vc: run1(f"{vc[0]}_c{vc[1]}", core_deck(p, vc[1], vb[vc[1]], vc[0])), jobs))
    for (name, rows, warn, dt, tail), (v, c) in zip(outs, jobs):
        res[(v, c)] = (rows[0] if rows else None, warn, dt, tail)
    lines = [f"# pex_sim {time.strftime('%Y-%m-%d %H:%M')}  tt 27C vdd 3.3 vctrl 1.65, total {time.time() - t_all:.0f} s",
             f"{'variant':6s} {'code':>4s} {'f MHz':>9s} {'P mW':>7s} {'vbn V':>7s} {'df vs sch':>9s} {'dP vs sch':>9s} {'run s':>6s}  warnings"]
    for v in var:
        for c in codes:
            r, warn, dt, tail = res[(v, c)]
            f = float(r[5]) if r and r[5] else float("nan")
            pw = float(r[6]) if r else float("nan")
            s = res.get(("sch", c), (None,))[0]
            fs = float(s[5]) if s and s[5] else float("nan")
            ps = float(s[6]) if s else float("nan")
            df = f"{100 * (f / fs - 1):+.1f}%" if v not in ("sch", "ref") else ""
            dp = f"{100 * (pw / ps - 1):+.1f}%" if v not in ("sch", "ref") else ""
            lines.append(f"{v:6s} {c:4d} {f / 1e6:9.2f} {pw * 1e3:7.3f} {vb[c]:7.4f} {df:>9s} {dp:>9s} {dt:6.0f}  "
                         f"{','.join(warn)}{'' if r else ' NO RESULT: ' + ' | '.join(tail)}")
    txt = "\n".join(lines) + "\n"
    (OUT / "results.txt").write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
