"""cfed map-window check (docs/cfed_startup_results.md). Map method (DC op + ring .ic, VDD 3.3 fixed) run long: f at 100-200 ns (as map.csv) vs f over the last 2 us.
Usage: python3 sim/pn/cfed_mapref.py CORNER TEMP CODE TSTOP TMAX   e.g. typical 27 0 20e-6 20p
DC op + ring .ic at VDD 3.3 (the map.csv deck: sim/vco/topo_cmp.py deck), one tran; f over 100-200 ns (the map window) and
over the last 2 us. Writes build/cfed_startup/mapref/<name>.json; the raw is deleted."""
import sys, json
from pathlib import Path
REPO = Path("/foss/designs/gf433-sims")
sys.path.insert(0, str(REPO / "sim/pn")); sys.path.insert(0, str(REPO / "sim/vco"))
import cfed_startup as cs, vco_bias as vb, topo_cmp as tcm
corner, temp, code, tstop, tmax = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
p = cs.params(); body, ics = vb.netlist(p)
src = "".join(f"vbit{b} bit{b} 0 {3.3 if (code>>b)&1 else 0}\nvbitb{b} bitb{b} 0 {0 if (code>>b)&1 else 3.3}\n" for b in range(p["bits"]))
T2 = tstop - 2e-6
raw = REPO / f"build/cfed_startup/mapref/mr_{corner}_t{temp:g}_c{code}_{tmax}_{tstop*1e9:.0f}n.raw"
deck = f"""* mapref
{tcm.HDR.format(corner=corner)}vdd vdd 0 3.3
vctrl vctrl 0 1.65
{src}{body}.ic {ics}
.control
option temp={temp}
set filetype=binary
save v(a0) v(vg) v(vbnf)
tran 1n {tstop} 0 {tmax}
write {raw} v(a0) v(vg) v(vbnf)
quit
.endc
.end
"""
name = f"mr_{corner}_t{temp:g}_c{code}_{tmax}_{tstop*1e9:.0f}n"
d = REPO / "build/cfed_startup/mapref"
log, w = cs.ngspice(d, name, deck)
import numpy as np
dd = cs.read_raw(raw); t = dd["time"]
def fwin(lo, hi):
    m = (t >= lo) & (t <= hi); thr = (dd["a0"][m].min() + dd["a0"][m].max()) / 2
    r = cs.rises(t[m], dd["a0"][m], thr); return (len(r) - 1) / (r[-1] - r[0]), float(dd["vg"][m].mean())
f1, vg1 = fwin(100e-9, 200e-9); f2, vg2 = fwin(T2, tstop)
out = dict(name=name, f_100_200n=f1, vg_100_200n=vg1, f_last2us=f2, vg_last2us=vg2, vbnf_end=float(dd["vbnf"][-1]), wall_s=w)
print(json.dumps(out)); (d / f"{name}.json").write_text(json.dumps(out, indent=1)); raw.unlink()
