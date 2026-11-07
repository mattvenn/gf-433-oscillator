#!/usr/bin/env python3
"""Export the VCO ring core from the schematic netlist (sim/vco/vco_bias.py netlist()) as a .subckt.

    python3 layout/gen/export_core.py [--set k=v ...] [-o layout/ref/ring_core.spice] [--keep-cw]

This is the LVS source and the schematic reference for PEX: it comes from vco_bias.netlist() itself, not
from the layout generator's parameters. The const-gm reference (MN1/MN2/RB*/XRB*/MP1/MP2/MS*/Rvbn) and
the vbn filter (XRF/CF) are left out; the wiring caps Cw* are dropped for LVS (--keep-cw keeps them).
Nets: "0" -> VSS, vdd -> VDD.
"""
import argparse, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim" / "vco"))
import vco_bias  # noqa: E402

REF = re.compile(r"^(XMN\d|XMP\d|XMS\d|RB|XRB|Rvbn|XRF|CF)", re.I)
REAL_R = dict(rideal=0, lnw=4.5, lnp=100.0)   # the handoff's real-resistor settings


def ports(p):
    return (["VDD", "VSS", "vbn", "vctrl"] + [f"bit{b}" for b in range(p["bits"])]
            + [f"bitb{b}" for b in range(p["bits"])] + [f"a{i}" for i in range(p["n"])])


def core(p, keep_cw=False):
    body, _ = vco_bias.netlist(p)
    out, dropped = [], []
    for ln in body.splitlines():
        t = ln.split()
        if not t:
            continue
        if REF.match(t[0]) or (t[0].upper().startswith("CW") and not keep_cw):
            dropped.append(t[0])
            continue
        if vco_bias.gnet(p) != "vbn":
            raise SystemExit("vbn RC filter is on (rf, cf > 0): the core's gate net would be vbnf")
        t = [{"0": "VSS", "vdd": "VDD"}.get(x, x) for x in t]
        out.append(" ".join(t))
    return out, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("-o", default=str(REPO / "layout" / "ref" / "ring_core.spice"))
    ap.add_argument("--keep-cw", action="store_true")
    ap.add_argument("--name", default="ring_core")
    a = ap.parse_args()
    p = dict(vco_bias.P)
    p.update(REAL_R)
    for kv in a.set:
        k, v = kv.split("=")
        p[k] = type(vco_bias.P[k])(float(v))
    lines, dropped = core(p, a.keep_cw)
    Path(a.o).parent.mkdir(parents=True, exist_ok=True)
    txt = (f"* ring core exported from sim/vco/vco_bias.py netlist() by layout/gen/export_core.py\n"
           f"* dropped (reference/filter/wiring C): {' '.join(dropped)}\n"
           f".subckt {a.name} {' '.join(ports(p))}\n" + "\n".join(lines) + "\n.ends\n")
    Path(a.o).write_text(txt)
    print(f"{a.o}: {len(lines)} elements, dropped {len(dropped)}")


if __name__ == "__main__":
    main()
