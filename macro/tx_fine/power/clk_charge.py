#!/usr/bin/env python3
"""Charge drawn from VDD per clk cycle by the hardened tx_fine, split by clock gate (docs/tx_fine_tune.md,
"Digital supply coupling").

    python3 macro/tx_fine/power/clk_charge.py runs/r10 runs/r12      (paths relative to macro/tx_fine)

OpenSTA (clk_charge.tcl) gives each instance's power with clk at 25 MHz, every data net static and ck stopped,
so the power is only what the clk edges cost: the clock buffers' internal and switching power and the flops' clock
pin power. STA propagates clk through the clock gates as if they were always on, so this script traces the clock
tree in the netlist from the clk port: cells reached without passing a gate are 'free' (they see every edge), the
rest belong to the gate (icgtp) above them. Per-cycle charge = sum of P / f / VDD over the parts that run.
"""
import re, subprocess, sys, os
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
F, VDD = 25e6, 3.3


def netlist(path):
    txt = Path(path).read_text()
    insts = {}
    for m in re.finditer(r"^\s*(gf180mcu_\w+)\s+(\\?\S+)\s*\((.*?)\);", txt, re.M | re.S):
        pins = dict(re.findall(r"\.(\w+)\((\\?[^\s()]+(?:\s*\[\d+\])?)\s*\)", m.group(3)))
        insts[m.group(2).lstrip("\\")] = (m.group(1).split("__")[1], pins)
    return insts


def trace(insts):
    by_net = defaultdict(list)
    for n, (c, pins) in insts.items():
        for p, net in pins.items():
            by_net[net].append((n, p))
    dom = {}
    todo = [("clk", "free")]
    while todo:
        net, d = todo.pop()
        for n, p in by_net[net]:
            c, pins = insts[n]
            if n in dom:
                continue
            if c.startswith("icgtp") and p == "CLK":
                dom[n] = d                                   # the gate's own CLK pin sees the parent's edges
                todo.append((pins["Q"], n.split(".")[0]))
            elif re.match(r"(clk)?(buf|inv)", c) and p == "I":
                dom[n] = d
                todo.append((pins.get("Z") or pins.get("ZN"), d))
            elif p in ("CLK", "CLKN", "E", "EN"):
                dom[n] = d
    return dom


def power(run):
    out = HERE.parents[2] / "build/tx_fine/power" / f"inst_{Path(run).name}.rpt"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["sta", "-no_init", "-exit", str(HERE / "clk_charge.tcl")], check=True, capture_output=True,
                   env=dict(os.environ, RUN=str(run), OUT=str(out), PDK_ROOT=os.environ.get("PDK_ROOT", "/foss/pdks")))
    p = {}
    for ln in out.read_text().splitlines():
        t = ln.split()
        if len(t) == 5:
            try:
                p[t[4].lstrip("\\")] = float(t[3])
            except ValueError:
                pass
    return p


def main():
    for run in sys.argv[1:]:
        run = (HERE.parent / run).resolve()
        insts = netlist(run / "final/nl/tx_fine.nl.v")
        dom = trace(insts)
        p = power(run)
        tot = defaultdict(float); cnt = defaultdict(int)
        for n, d in dom.items():
            tot[d] += p.get(n, 0.0)
            if re.match(r"dff|sdff", insts[n][0]):
                cnt[d] += 1
        other = sum(v for n, v in p.items() if n not in dom)
        q = lambda w: w / F / VDD * 1e12
        print(f"{run.name}: total {sum(p.values())*1e3:.3f} mW at 25 MHz, data static ({other*1e6:.1f} uW off the clock tree)")
        for d in sorted(tot, key=lambda k: (k != "free", k)):
            print(f"  {d:6s}: {cnt[d]:4d} flops  {tot[d]*1e3:.3f} mW  {q(tot[d]):6.2f} pC per clk cycle")
        on = {"static": ["free"], "sd running": ["free", "g_sd"]}
        for k, ds in on.items():
            print(f"  -> {k:10s}: {q(sum(tot[d] for d in ds) + other):6.2f} pC per cycle")


if __name__ == "__main__":
    main()
