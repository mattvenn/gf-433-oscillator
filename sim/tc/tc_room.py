#!/usr/bin/env python3
"""Room-temperature tempco of the cfed VCO vs the n-well length lnw (the bias resistor's tempco knob).

    python3 sim/tc/tc_room.py [--lnws 3,3.5,...] [--code 9] [--corner typical] [--jobs 16] [--name tcr]

The sizing nulled the 0/27/70 C least-squares slope (+1.6 ppm/C at lnw 5.023), but f(T) is a parabola peaking
near 35 C, so the slope at 27 C is +100..+140 ppm/C. Here: f at 20/27/35 C (tt, code 9, vctrl 1.65, VDD 3.3;
the map deck of sim/vco/topo_cmp.py, f over 100-200 ns) for each lnw; slope = LSQ over 20/27/35 / f(27), and the
curvature. Design settings: WINNER + CFED + lnw/ka/wfu/wff/rf/cf as the chosen design (cfed_noise.params).
Writes build/cfed/<name>/tc_room.json.
"""
import argparse, json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/pn")); sys.path.insert(0, str(REPO / "sim/vco"))
import cfed_noise as cn, vco_bias as vb, topo_cmp as tcm  # noqa: E402

TS = (20.0, 27.0, 35.0)
ap = argparse.ArgumentParser()
ap.add_argument("--lnws", default="3,3.5,4,4.5,5.023,5.5,6,6.5,7,8")
ap.add_argument("--code", type=int, default=9)
ap.add_argument("--corner", default="typical")
ap.add_argument("--jobs", type=int, default=16)
ap.add_argument("--name", default="tcr")
a = ap.parse_args()
p = cn.params(["ka=16", "wfu=0.30", "wff=0.30", "rf=1e6", "cf=20e-12"])
out = REPO / "build/cfed" / a.name; out.mkdir(parents=True, exist_ok=True)
lnws = [float(x) for x in a.lnws.split(",")]
decks = [(f"tcr_{a.corner}_lnw{x:g}", tcm.deck(dict(p, lnw=x), a.corner, [(a.code, 1.65, t, 3.3) for t in TS]))
         for x in lnws]
vb.run(out, decks, a.jobs)
res = []
for (n, _), x in zip(decks, lnws):
    f = {r["temp"]: r["f"] for r in tcm.parse((out / f"{n}.log").read_text())}
    tm = sum(TS) / 3; fm = sum(f[t] for t in TS) / 3
    sl = sum((t - tm) * (f[t] - fm) for t in TS) / sum((t - tm) ** 2 for t in TS)
    curv = ((f[35.0] - f[27.0]) / 8 - (f[27.0] - f[20.0]) / 7) / 7.5      # d2f/dT2 (Hz/C^2)
    r = dict(lnw=x, f=f, tc_ppm=sl / f[27.0] * 1e6, curv_ppm=curv / f[27.0] * 1e6)
    res.append(r)
    print(f"lnw {x:6.3f}  f27 {f[27.0]/1e6:7.2f} MHz  slope {r['tc_ppm']:+7.1f} ppm/C  "
          f"curvature {r['curv_ppm']:+6.2f} ppm/C^2  ({f[20.0]/1e6:.2f} / {f[27.0]/1e6:.2f} / {f[35.0]/1e6:.2f})", flush=True)
(out / "tc_room.json").write_text(json.dumps(dict(corner=a.corner, code=a.code, temps=TS, rows=res), indent=1))
