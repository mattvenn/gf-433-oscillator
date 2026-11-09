#!/usr/bin/env python3
"""Check the xschem pad model (xschem/pad_model_gf180.sch, tt_asw_5v0.sch, lv2hv.sch) is the simulated one
(sim/pad/pad_model_gf180.spice + tt_asw_5v0.spice). Laptop, repo root: python3 sim/pad/check_xsch.py

  1. netlist the three sheets headless (xschem/gen/netlist.sh) into build/xsch/
  2. run tb_rdson (tt) and tb_pad (tt, 1.65 V, Rroute 40, n_off 3) on both; every .meas must agree within 1e-4
  3. mutation: one TG nmos finger 31 -> 30 um in a copy of the xschem netlist; tb_rdson must then disagree
Writes build/pad/check_xsch.txt.
"""
import re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OSIC = str(REPO / "tools" / "osic-mac")
X = REPO / "build" / "xsch"
LOG = []


def log(s):
    print(s); LOG.append(s)


def sh(cmd):
    r = subprocess.run([OSIC, "bash", "-c", f"cd {REPO} && {cmd}"], capture_output=True, text=True)
    return r.stdout + r.stderr


def meas(out):
    return {m.group(1): float(m.group(2)) for m in re.finditer(r"^(\w+)\s*=\s*([-+\d.eE]+)", out, re.M)}


def run(tb, *args, models=None):
    a = " ".join(args) + (f" MODELS={models}" if models else "")
    return meas(sh(f"python3 sim/pad/run.py {tb} tt {a}"))


def compare(tag, a, b, tol=1e-4):
    bad = [k for k in a if k not in b or abs(a[k] - b[k]) > tol * max(1e-12, abs(a[k]))]
    log(f"{tag}: {len(a)} measures, {'PASS' if a and not bad else 'FAIL'}"
        + "".join(f"\n    {k}: spice {a[k]:.6g} xschem {b.get(k, float('nan')):.6g}" for k in bad))
    return bool(a) and not bad


def main():
    log(sh("xschem/gen/netlist.sh xschem build/xsch lv2hv tt_asw_5v0 pad_model_gf180").strip())
    # the top .subckt gets its parameters from the symbol only when instantiated: add the symbol's defaults
    sym = (REPO / "xschem" / "pad_model_gf180.sym").read_text()
    params = re.search(r'template="name=x1 ([^"]*)"', sym).group(1)
    net = (X / "pad_model_gf180.spice").read_text()
    net = re.sub(r"^\.subckt pad_model_gf180 (.*)$", lambda m: f".subckt pad_model_gf180 {m.group(1)} {params}",
                 net, count=1, flags=re.M)
    model = X / "pad_model_gf180_sim.spice"
    model.write_text(net.replace("\n.end\n", "\n"))
    ok = True
    for tb, args in (("tb_rdson", ()), ("tb_pad", ("VCM=1.65", "RROUTE=40", "NOFF=3"))):
        ok &= compare(f"{tb} spice vs xschem", run(tb, *args), run(tb, *args, models=model))
    mut = X / "pad_model_gf180_mut.spice"
    txt, n = re.subn(r"(XM2 bus \S+ mod VGND nfet_05v0 L=0.6u W=)31u", r"\g<1>30u", model.read_text())
    assert n == 1, "mutation not applied"
    mut.write_text(txt)
    caught = not compare("mutation XM2 W 31 -> 30 um (must FAIL)", run("tb_rdson"), run("tb_rdson", models=mut))
    log(f"mutation {'caught' if caught else 'NOT CAUGHT (BAD)'}")
    log("CHECK " + ("OK" if ok and caught else "FAIL"))
    (REPO / "build" / "pad" / "check_xsch.txt").write_text("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
