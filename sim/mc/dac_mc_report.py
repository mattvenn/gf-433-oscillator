#!/usr/bin/env python3
"""Metrics of sim/mc/dac_mc.py dc runs: python3 sim/mc/dac_mc_report.py typical ss ff -> build/mc2/report.txt (+ .json)

Per sample, at vctrl 1.65: step(c) = I(c+1) - I(c), DNL(c) = step(c) / nominal step(c) - 1 (nominal = the
mismatch-off run of the same corner); non-monotonic if any step < 0.
Fine coverage: fine(c) = I(c, 3.3) - I(c, 0); ratio(c) = fine(c) / step(c); the sample's worst = min over c 0..30.
"""
import json, statistics as st, sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "build" / "mc2"
CARRY = (7, 15, 23)   # step c -> c+1


def metrics(i, nom_steps):
    I = [x[1] for x in i]
    steps = [I[c + 1] - I[c] for c in range(31)]
    dnl = [s / n - 1 for s, n in zip(steps, nom_steps)]
    fines = [x[2] - x[0] for x in i if x[0] is not None]
    fmin = min(fines)   # vg held: fine dI is code-independent; the min over the measured codes (conservative)
    ratio = [(i[c][2] - i[c][0] if i[c][0] is not None else fmin) / steps[c] if steps[c] > 0 else 0.0 for c in range(31)]
    cw = min(range(31), key=lambda c: ratio[c])
    return dict(dnl=dnl, nonmono=min(steps) < 0, rmin=ratio[cw], rcode=cw, fspread=(max(fines) - fmin) / fmin)


def main():
    lines, js = [], {}
    for corner in sys.argv[1:] or ["typical"]:
        nom = json.loads((OUT / f"nom_{corner}.json").read_text())["samples"]["0"]["i"]
        nsteps = [nom[c + 1][1] - nom[c][1] for c in range(31)]
        nfine = nom[0][2] - nom[0][0]
        lines.append(f"(fine dI spread over the measured codes, worst sample: "
                     f"{max(metrics(v['i'], nsteps)['fspread'] for v in json.loads((OUT / f'dc_{corner}.json').read_text())['samples'].values()):.2e})")
        d = json.loads((OUT / f"dc_{corner}.json").read_text())["samples"]
        keys = {json.dumps(v["i"]) for v in d.values()}
        m = {s: metrics(v["i"], nsteps) for s, v in d.items()}
        N = len(m)
        lines.append(f"## {corner}: N = {N} ({len(keys)} distinct), vg {json.loads((OUT / f'dc_{corner}.json').read_text())['vg']} V, "
                     f"nominal step {nsteps[15] * 1e6:.3f} uA, nominal fine {nfine * 1e6:.2f} uA, "
                     f"nominal fine/step {min(nfine / s for s in nsteps):.2f}")
        for c in CARRY:
            x = [v["dnl"][c] for v in m.values()]
            lines.append(f"DNL {c}->{c + 1}: mean {st.mean(x):+.4f} sd {st.stdev(x):.4f} min {min(x):+.4f} max {max(x):+.4f}")
        allw = [max(v["dnl"], key=abs) for v in m.values()]
        lines.append(f"worst |DNL| any code per sample: mean {st.mean(abs(x) for x in allw):.4f} worst {max(allw, key=abs):+.4f}")
        lines.append(f"non-monotonic: {sum(v['nonmono'] for v in m.values())}/{N}")
        r = sorted(m.items(), key=lambda kv: kv[1]["rmin"])
        lines.append(f"fine/step: fraction < 1.3: {sum(v['rmin'] < 1.3 for v in m.values())}/{N}; worst {r[0][1]['rmin']:.3f}; "
                     f"mean of per-sample min {st.mean(v['rmin'] for v in m.values()):.3f} sd {st.stdev(v['rmin'] for v in m.values()):.3f}")
        lines.append("worst 3 (seed: min fine/step at code c->c+1): " +
                     ", ".join(f"{s}: {v['rmin']:.3f} at {v['rcode']}->{v['rcode'] + 1}" for s, v in r[:3]))
        js[corner] = dict(worst3=[(int(s), v["rcode"], v["rmin"]) for s, v in r[:3]], N=N)
    txt = "\n".join(lines) + "\n"
    (OUT / "report.txt").write_text(txt)
    (OUT / "report.json").write_text(json.dumps(js))
    print(txt)


if __name__ == "__main__":
    main()
