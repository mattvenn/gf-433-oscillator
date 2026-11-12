#!/usr/bin/env python3
"""Export the current-fed (topo=cfed) ring core from sim/vco/vco_bias.py netlist() as a .subckt (LVS source and
PEX schematic reference for layout/ring_core_v3.gds).

    python3 layout/gen/export_core_v3.py [--set wfu=0.30 ...] [-o layout/ref/ring_core_v3.spice] [--keep-cw] [--ideal-cvg]

Parameters: ring_core_v3.params() (vco_bias.P + the winner reference + CFED, wff = wfu unless set).
Dropped: the const-gm reference (MN*/MP1/MP2/MS*/RB*/XRB*/Rvbn), the vbn filter (XRF/CF, off here), the wiring
caps Cw* (unless --keep-cw). The ideal decap Cvg is replaced by the drawn MOS decap
  XDC VDD vg VDD VDD pfet_03v3 w=<W>u l=<L>u m=<nf>     (gate on vg, S/D/B on VDD in its own n-well; ~cvg at
                                                      every corner's vg, build/tx_fine/vg_decap/cv; to VSS before 2026-11-12)
unless --ideal-cvg (keeps Cvg, for the schematic comparison). Nets: "0" -> VSS, vdd -> VDD.
"""
import argparse, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "sim" / "vco"))
sys.path.insert(0, str(HERE))
import vco_bias  # noqa: E402
import ring_core_v3 as gen  # noqa: E402

REF = re.compile(r"^(XMN\d|XMP\d|XMS\d|RB|XRB|Rvbn|XRF|CF\b)", re.I)


def ports(p):
    return (["VDD", "VSS", "vbn", "vctrl"] + [f"bit{b}" for b in range(p["bits"])]
            + [f"bitb{b}" for b in range(p["bits"])] + ["vg"] + [f"a{i}" for i in range(p["n"])])


def core(p, keep_cw=False, ideal_cvg=False):
    assert p["topo"] == "cfed"
    if vco_bias.gnet(p) != "vbn":
        raise SystemExit("vbn RC filter is on (rf, cf > 0): the core's gate net would be vbnf")
    body, _ = vco_bias.netlist(p)
    out, dropped = [], []
    for ln in body.splitlines():
        t = ln.split()
        if not t:
            continue
        if REF.match(t[0]) or (t[0].upper().startswith("CW") and not keep_cw):
            dropped.append(t[0])
            continue
        t = [{"0": "VSS", "vdd": "VDD"}.get(x, x) for x in t]
        if t[0] == "Cvg" and not ideal_cvg:
            nf, L, W = gen.decap_size(p)
            dropped.append("Cvg")
            out.append(f"XDC VDD vg VDD VDD pfet_03v3 w={W}u l={L}u m={nf}")
            continue
        out.append(" ".join(t))
    return out, dropped


def subckt(p, name="ring_core", keep_cw=False, ideal_cvg=False):
    lines, dropped = core(p, keep_cw, ideal_cvg)
    return (f"* cfed ring core exported from sim/vco/vco_bias.py netlist() by layout/gen/export_core_v3.py\n"
            f"* wfu={p['wfu']} wff={p['wff']} k={p['k']} kc={p['kc']} ka={p['ka']} cvg={p['cvg']}\n"
            f"* dropped: {' '.join(dropped)}\n"
            f".subckt {name} {' '.join(ports(p))}\n" + "\n".join(lines) + "\n.ends\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("-o", default=str(REPO / "layout" / "ref" / "ring_core_v3.spice"))
    ap.add_argument("--keep-cw", action="store_true")
    ap.add_argument("--ideal-cvg", action="store_true")
    ap.add_argument("--name", default="ring_core")
    a = ap.parse_args()
    p = gen.params(a.set)
    txt = subckt(p, a.name, a.keep_cw, a.ideal_cvg)
    Path(a.o).parent.mkdir(parents=True, exist_ok=True)
    Path(a.o).write_text(txt)
    print(f"{a.o}: {txt.count(chr(10)) - 4} elements")


if __name__ == "__main__":
    main()
