#!/usr/bin/env python3
"""Structural (powered) Verilog netlist -> SPICE .subckt, for the LVS source of a hardened standard-cell macro.

    python3 lvs/verilog2spice.py <netlist.pnl.v> <cell library .spice> [--top tx_fine] > out.spice

Handles what LibreLane's powered netlist contains: one module, port / wire declarations (with ranges), standard
cell instances with named connections (.PIN(net)), escaped identifiers, bit selects, constants 1'b0 / 1'b1 (as
nets VSS / VDD would be wrong in general, so they are rejected) and plain "assign a = b;" (the nets are merged).
Every instance becomes "X<name> <nets in the cell's .SUBCKT port order> <cell>"; the used cells' .SUBCKTs are
appended from the library. Cells without devices (filltie, endcap, fill_*) are written too: netgen ignores empty
subcircuits.
"""
import argparse, re, sys
from pathlib import Path


def tokens_ports(decl):
    """'input [3:0] a, b' -> ['a[3]', 'a[2]', ..., 'b'] (bit-blasted, MSB first as declared)."""
    m = re.match(r"\s*(input|output|inout|wire)\s*(\[(\d+):(\d+)\])?\s*(.*)", decl, re.S)
    kind, rng, msb, lsb, names = m.groups()
    out = []
    for n in names.split(","):
        n = n.strip().lstrip("\\").strip()
        if not n:
            continue
        if rng:
            a, b = int(msb), int(lsb)
            step = -1 if a > b else 1
            out += [f"{n}[{i}]" for i in range(a, b + step, step)]
        else:
            out.append(n)
    return kind, out


def net_name(s):
    s = s.strip()
    if s.startswith("\\"):
        s = s[1:].strip()
    m = re.fullmatch(r"(\S+?)\s*\[(\d+)\]", s)
    if m:
        return f"{m.group(1)}[{m.group(2)}]"
    if re.fullmatch(r"\d+'[bh][01]", s):
        raise SystemExit(f"constant {s} in the netlist: not supported (expected tie cells)")
    return s


def parse(path, top):
    t = Path(path).read_text()
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"//[^\n]*", "", t)
    m = re.search(rf"module\s+{re.escape(top)}\s*\((.*?)\)\s*;(.*?)endmodule", t, re.S)
    assert m, f"module {top} not found"
    hdr, body = m.groups()
    order = [x.strip().lstrip("\\").strip() for x in hdr.split(",") if x.strip()]
    ports, insts, assigns = {}, [], []
    for stmt in re.split(r";", body):
        s = stmt.strip()
        if not s:
            continue
        if re.match(r"(input|output|inout)\b", s):
            kind, names = tokens_ports(s)
            for n in names:
                ports[n] = kind
        elif re.match(r"wire\b", s):
            continue
        elif s.startswith("assign"):
            a, b = s[len("assign"):].split("=")
            assigns.append((net_name(a), net_name(b)))
        else:
            mi = re.match(r"(\S+)\s+(\\\S+\s|\S+)\s*\((.*)\)\s*$", s, re.S)
            assert mi, s[:120]
            cell, name, conns = mi.groups()
            pins = {p: net_name(n) for p, n in re.findall(r"\.(\w+)\s*\(\s*([^()]*?)\s*\)", conns)}
            insts.append((cell, name.strip().lstrip("\\"), pins))
    # port order: header order, bit-blasted
    plist = []
    for n in order:
        plist += [p for p in ports if p == n or p.startswith(n + "[")]
    return plist, insts, assigns


def lib_cells(lib):
    t = Path(lib).read_text()
    t = re.sub(r"\n\+", " ", t)
    cells = {}
    for m in re.finditer(r"^\.SUBCKT\s+(\S+)\s+([^\n]*)\n(.*?)^\.ENDS", t, re.M | re.S | re.I):
        cells[m.group(1)] = (m.group(2).split(), m.group(0))
    return cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("netlist")
    ap.add_argument("lib")
    ap.add_argument("--top", default="tx_fine")
    a = ap.parse_args()
    plist, insts, assigns = parse(a.netlist, a.top)
    cells = lib_cells(a.lib)
    # merge assigned nets (union-find); ports win as the representative
    par = {}

    def find(x):
        while par.get(x, x) != x:
            x = par[x]
        return x
    for x, y in assigns:
        rx, ry = find(x), find(y)
        if rx != ry:
            if rx in plist:
                par[ry] = rx
            else:
                par[rx] = ry
    out = [f".subckt {a.top} " + " ".join(plist)]
    used = []
    for cell, name, pins in insts:
        assert cell in cells, f"cell {cell} not in the library"
        order = cells[cell][0]
        missing = [p for p in order if p not in pins]
        assert not missing, (name, cell, missing)
        nm = re.sub(r"[^\w]", "_", name)
        out.append(f"X{nm} " + " ".join(find(pins[p]) for p in order) + f" {cell}")
        if cell not in used:
            used.append(cell)
    out.append(f".ends {a.top}\n")
    for c in used:
        out.append(cells[c][1] + "\n")
    sys.stdout.write("\n".join(out))
    print(f"* {len(insts)} instances, {len(used)} cell types, {len(assigns)} assigns", file=sys.stderr)


if __name__ == "__main__":
    main()
