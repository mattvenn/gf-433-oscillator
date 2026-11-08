#!/usr/bin/env python3
"""Re-map the 433.92 MHz codes on the extracted v3 core, with the level shifter + /4 as the a0 load.

The tuning map (sim/results/2026-11-08/cfed/map.csv) is schematic: on the RC-extracted core its 433.92 codes give
367-378 MHz (docs/lsdiv_design.md), and it reads ~1.3 % high anyway (100-200 ns window). This re-maps with the
lsdiv deck: full reference + 1 MOhm / 20 pF filter, extracted core (layout/pex/ring_core_v3_w30chk_rc.spice),
the drawn lsdiv block (real R1 / C1) on a0, DC op with the ring held, f over 0.72-1.2 us (settled; f_drift reported).

  python3 sim/lsdiv/remap.py codes   [--jobs 8]   # 5 corners x codes 0..31 at vctrl 1.65, 27 C, 3.3 V
  python3 sim/lsdiv/remap.py fine    [--jobs 8]   # per corner, the 4 codes around 433.92 x vctrl 0 / 1.0 / 2.3 / 3.3
  python3 sim/lsdiv/remap.py summary              # sim/lsdiv/results/remap.md + remap.csv

Corners (docs/handoff_autonomy.md policy): the 5 process corners at 27 C, VDD 3.3 V only (room temperature;
the cfed ring moves -0.008 %/10 mV, so VDD is left out). Outputs: build/remap/*.json, decks under build/lsdiv/.
"""
import argparse, csv, importlib.util, json, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sim_lsdiv", HERE / "lsdiv.py")
LS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LS)

REPO = HERE.parents[1]
OUT = REPO / "build/remap"
RES = HERE / "results"
CORNERS = ("typical", "ss", "ff", "sf", "fs")
F0 = 433.92e6
VFINE = (0.0, 1.0, 2.3, 3.3)
# 433.92 codes of the schematic map (lsdiv.CODE433) and of the RC check without the LS (docs/cfed_v3_check.md)
RC_V3 = dict(typical=12, ss=14, ff=10)


def deck(c, code, vctrl, tstop):
    p = dict(LS.vb.P, **LS.WINNER, **LS.CFED)
    s = dict(LS.S, real=1)
    d = LS.ring_deck(p, s, c, 27, code, 3.3, "c", tstop)
    old = "vctrl vctrl 0 1.65\n"
    assert old in d
    return d.replace(old, f"vctrl vctrl 0 {vctrl}\n")


def run(points, tag, jobs, tstop):
    jl = [(f"map{tag}_{LS.CN[c]}_c{code}_v{v:.2f}", deck(c, code, v, tstop), dict(corner=c, code=code, vctrl=v))
          for c, code, v in points]
    t0 = time.time()
    with ThreadPoolExecutor(jobs) as ex:
        dts = dict(ex.map(lambda j: LS.run1(j[0], j[1]), jl))
    rows = []
    for n, _, meta in jl:
        r = LS.analyse(n, 3.3, "c")
        r.update(meta, run_s=dts[n])
        rows.append(r)
        print(json.dumps({k: r.get(k) for k in ("corner", "code", "vctrl", "f_a0", "f_drift", "ls_duty", "div_ratio",
                                                 "warn")}), flush=True)
    bad = [r for r in rows if not r.get("f_a0") or r.get("warn")]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{tag}.json").write_text(json.dumps(dict(tstop=tstop, wall_s=time.time() - t0, rows=rows), indent=1))
    print(f"wrote build/remap/{tag}.json: {len(rows)} rows, {len(bad)} with no f or a warning, {time.time() - t0:.0f} s")
    return rows, bad


def around(rows, c):
    """The 4 codes around 433.92 at vctrl 1.65: two below, two at or above."""
    fc = sorted((r["code"], r["f_a0"]) for r in rows if r["corner"] == c and r["vctrl"] == 1.65 and r.get("f_a0"))
    above = [k for k, f in fc if f >= F0]
    hi = above[0] if above else fc[-1][0]
    return [k for k in range(hi - 2, hi + 2) if 0 <= k <= 31]


def summary():
    codes = json.loads((OUT / "codes.json").read_text())["rows"]
    fine = json.loads((OUT / "fine.json").read_text())["rows"] if (OUT / "fine.json").exists() else []
    allr = codes + fine
    RES.mkdir(exist_ok=True)
    with open(RES / "remap.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["corner", "code", "vctrl", "f_a0_hz", "f_drift", "ls_duty", "div_ratio", "p_ls_w", "p_div_w"])
        for r in sorted(allr, key=lambda r: (CORNERS.index(r["corner"]), r["code"], r["vctrl"])):
            w.writerow([LS.CN[r["corner"]], r["code"], r["vctrl"], r.get("f_a0"), r.get("f_drift"), r.get("ls_duty"),
                        r.get("div_ratio"), r.get("p_ls"), r.get("p_div")])
    L = ["# 433.92 MHz codes on the extracted core, with the level shifter + /4 on a0",
         "", "From `sim/lsdiv/remap.py` (27 °C, VDD 3.3 V; data `sim/lsdiv/results/remap.csv`).", "",
         "| corner | f code 0 / 31 at 1.65 V (MHz) | 433.92 code at 1.65 V | f there (MHz) | sch map code | RC, no LS | "
         "codes covering 433.92 with vctrl 0–3.3 V (f range MHz) | worst ls duty % | ÷4 exact |",
         "|---|---|---|---|---|---|---|---|---|"]
    for c in CORNERS:
        rc = [r for r in codes if r["corner"] == c and r.get("f_a0")]
        f = {r["code"]: r["f_a0"] for r in rc}
        best = min(f, key=lambda k: abs(f[k] - F0)) if f else None
        cov = []
        for k in sorted({r["code"] for r in fine if r["corner"] == c}):
            fs = [r["f_a0"] for r in allr if r["corner"] == c and r["code"] == k and r.get("f_a0")]
            if fs and min(fs) <= F0 <= max(fs):
                cov.append(f"{k} ({min(fs) / 1e6:.0f}–{max(fs) / 1e6:.0f})")
        rr = [r for r in allr if r["corner"] == c and r.get("ls_duty") is not None]
        wd = max((abs(r["ls_duty"] - 0.5) for r in rr), default=float("nan"))
        ex = all(abs(r.get("div_ratio", 0) - 4) < 1e-3 for r in rr)
        L.append(f"| {LS.CN[c]} | {f.get(0, 0) / 1e6:.0f} / {f.get(31, 0) / 1e6:.0f} | {best} | "
                 f"{f.get(best, 0) / 1e6:.1f} | {LS.CODE433[c]} | {RC_V3.get(c, '–')} | {', '.join(cov) or '–'} | "
                 f"{50 + 100 * wd:.1f} | {'yes' if ex else 'NO'} |")
    (RES / "remap.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["codes", "fine", "summary"])
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--tstop", type=float, default=1.2e-6)
    ap.add_argument("--corners", default=",".join(CORNERS))
    ap.add_argument("--codes", default="0-31")
    a = ap.parse_args()
    cs = a.corners.split(",")
    if a.step == "codes":
        lo, hi = map(int, a.codes.split("-"))
        _, bad = run([(c, k, 1.65) for c in cs for k in range(lo, hi + 1)], "codes", a.jobs, a.tstop)
    elif a.step == "fine":
        rows = json.loads((OUT / "codes.json").read_text())["rows"]
        pts = [(c, k, v) for c in cs for k in around(rows, c) for v in VFINE]
        _, bad = run(pts, "fine", a.jobs, a.tstop)
    else:
        summary()
        return
    if bad:
        raise SystemExit(f"{len(bad)} points with no frequency or a warning: see build/remap/{a.step}.json")


if __name__ == "__main__":
    main()
