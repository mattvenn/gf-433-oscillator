#!/usr/bin/env python3
"""Summarise build/vco/topo_<name>/sweep.json (+ tc.json, settle json) for the topology comparison.
  python3 sim/vco/topo_summary.py base_cw3 base_v2 stack cfed3p ..."""
import json, math, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
T = 433.92e6


def summ(name):
    d = REPO / f"build/vco/topo_{name}"
    rows = json.load(open(d / "sweep.json"))["rows"]
    pts = {}
    for r in rows:
        pts.setdefault((r["corner"], r["temp"]), {})[(r["code"], r["vctrl"])] = r
    nonmono, fmins, fmaxs, fine0, fine31, swings = [], [], [], [], [], []
    for (c, t), d_ in pts.items():
        codes = sorted({k[0] for k in d_}); vcs = sorted({k[1] for k in d_})
        f = lambda co, v: d_[(co, v)]["f"]
        for v in vcs:
            fs = [f(co, v) for co in codes]
            bad = [codes[i + 1] for i in range(len(fs) - 1) if not fs[i + 1] > fs[i]]
            if bad: nonmono.append(f"{c}/{t:g}/{v}:{bad}")
        fmins.append((f(codes[0], vcs[0]), c, t)); fmaxs.append((f(codes[-1], vcs[-1]), c, t))
        fine0.append(f(codes[0], vcs[-1]) - f(codes[0], vcs[0])); fine31.append(f(codes[-1], vcs[-1]) - f(codes[-1], vcs[0]))
        swings += [(r["amin"], r["amax"], c, t, r["code"]) for r in d_.values()]
    nan = lambda x: x != x
    fmin_w = max(fmins, key=lambda x: -1 if nan(x[0]) else x[0])
    fmax_w = min(fmaxs, key=lambda x: -1 if nan(x[0]) else x[0])
    sw = min(swings, key=lambda x: x[1] - x[0])
    out = dict(name=name, mono=not nonmono, nonmono=nonmono[:6], n_nonmono=len(nonmono),
               fmin_worst=fmin_w, fmax_worst=fmax_w, covers=fmin_w[0] <= 310e6 and fmax_w[0] >= 700e6,
               swing_worst=sw, amin_all=min(s[0] for s in swings), amax_all=max(s[1] for s in swings),
               fine0_min=min(fine0), fine31_min=min(fine31), nan=sum(nan(r["f"]) for r in rows))
    # tt code nearest 433.92 (vctrl 1.65, mean of 0/70 C)
    tt = {}
    for r in rows:
        if r["corner"] == "typical" and r["vctrl"] == 1.65: tt.setdefault(r["code"], []).append(r["f"])
    out["code433"] = min(tt, key=lambda c: abs(sum(tt[c]) / len(tt[c]) - T) if not any(map(nan, tt[c])) else 1e12)
    if (d / "tc.json").exists():
        tc = {(r["temp"], r["vdd"]): r for r in json.load(open(d / "tc.json"))["rows"]}
        f27 = tc[(27.0, 3.3)]["f"]
        out["tc_code"] = tc[(27.0, 3.3)]["code"]
        out["f27"] = f27; out["p27_mw"] = tc[(27.0, 3.3)]["p_w"] * 1e3
        out["dfdvdd_pct_per10mV"] = (tc[(27.0, 3.35)]["f"] - tc[(27.0, 3.25)]["f"]) / f27 * 10
        out["tempco_ppm_per_C"] = (tc[(70.0, 3.3)]["f"] - tc[(0.0, 3.3)]["f"]) / f27 / 70 * 1e6
        out["f_0_27_70"] = [tc[(t, 3.3)]["f"] / 1e6 for t in (0.0, 27.0, 70.0)]
        out["swing27"] = (tc[(27.0, 3.3)]["amin"], tc[(27.0, 3.3)]["amax"]); out["vg27"] = tc[(27.0, 3.3)]["vg"]
    return out


for n in sys.argv[1:]:
    s = summ(n)
    print(json.dumps(s, default=lambda x: str(x)))
    print()
