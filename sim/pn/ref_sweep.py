#!/usr/bin/env python3
"""Job 1 of docs/handoff_bias_and_tuning.md, one reference scale s per call:

  1. retune the n-well length lnw (lnp = 100) to null the tempco at tt (code 10, vctrl 1.65, VDD 3.3 V, filter off:
     it does not change DC). Tempco = least-squares slope of f over 0/27/70 C, divided by f(27 C), in ppm/C.
     Search: down from lnw = 4.5 um in 0.5 um steps, then up, to bracket the nearest zero, then regula falsi.
     With no zero in 0.5 .. 12 um: lnw for the same Iref as the s = 1 null (--iref), tempco reported as is.
  2. PVT spread at that lnw (vco_bias pvt points: 5 corners x 0/27/70 C x VDD 3.15/3.3/3.45 V).
  3. start-up (vco_bias startup, with the RC filter): ss and ff at 0 and 70 C.
  4. rms FM and L (sim/pn/bias_fm.py) at tt 27 C.

Usage (repo root): python3 sim/pn/ref_sweep.py --s 4 [--out build/refsweep] [--jobs 3]
Writes <out>/s<s>/ref_sweep.json (+ the per-step build dirs).
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/vco"))
sys.path.insert(0, str(REPO / "sim/pn"))
import vco_bias, bias_fm  # noqa: E402

CODE, VCTRL = 10, 1.65


EXTRA = []   # --set K=V overrides applied after the scaling


def params(s, lnw, filt):
    st = bias_fm.scaled(s, EXTRA + [f"lnw={lnw}"])
    if not filt:
        st.update(rf=0.0, cf=0.0)
    p = dict(vco_bias.P); p.update(st)
    return p


def tc(s, lnw, out, jobs):
    p = params(s, lnw, False)
    pts = [(CODE, VCTRL, t, 3.3) for t in (0, 27, 70)]
    rows = vco_bias.run(out / f"tc_lnw{lnw:.4f}", [("tc_typical", vco_bias.deck(p, "typical", pts, uic=False))], max(jobs, 2))
    f = {r[3]: r[5] for r in rows}
    ts = [0.0, 27.0, 70.0]
    tm = sum(ts) / 3; fm = sum(f[t] for t in ts) / 3
    slope = sum((t - tm) * (f[t] - fm) for t in ts) / sum((t - tm) ** 2 for t in ts)
    iref = {r[3]: r[8] for r in rows}
    return dict(lnw=lnw, f=f, tc_ppm=slope / f[27.0] * 1e6, iref27=iref[27.0])


def fm_step(a, res, out, lnw):
    """4. bias FM at tt (sim/pn/bias_fm.py); updates and writes ref_sweep.json."""
    bf = subprocess.run([sys.executable, str(REPO / "sim/pn/bias_fm.py"), "--s", f"{a.s:g}", "--tag", a.tag,
                         *sum((["--set", kv] for kv in EXTRA + [f"lnw={lnw}"]), []),
                         "--jobs", str(a.jobs), "--out", a.out + "/bfm"], capture_output=True, text=True, cwd=REPO)
    (out / "bias_fm.txt").write_text(bf.stdout + bf.stderr)
    m = re.search(r"wrote (\S+)/bias_fm.json", bf.stdout)
    res["bias_fm"] = json.loads(Path(m.group(1), "bias_fm.json").read_text()) if m else None
    print(bf.stdout, flush=True)
    (out / "ref_sweep.json").write_text(json.dumps(res, indent=1))
    print(f"wrote {out}/ref_sweep.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--s", type=float, required=True)
    ap.add_argument("--lnw0", type=float, default=4.5)
    ap.add_argument("--out", default="build/refsweep")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--iref", type=float, default=49.0e-6, help="target Iref (A) when tempco has no zero")
    ap.add_argument("--set", action="append", default=[], metavar="K=V", help="override after scaling (e.g. w1=2)")
    ap.add_argument("--tag", default="")
    ap.add_argument("--fm-only", action="store_true", help="redo step 4 only, from an existing ref_sweep.json")
    a = ap.parse_args()
    EXTRA[:] = a.set
    out = REPO / a.out / f"s{a.s:g}{a.tag}"
    if a.fm_only:
        res = json.loads((out / "ref_sweep.json").read_text())
        fm_step(a, res, out, res["lnw"])
        return
    res = dict(s=a.s, set=a.set, tc_iter=[])
    # 1. lnw for zero tempco. tempco(lnw) is not monotonic (s = 1: peak near lnw = 5 um, zeros near 3 and 7 um), and
    #    for s >= 4 it has no zero at all (the reference's long devices stop tracking the ring's L = 1 um feet).
    #    So: step down from lnw0 in 0.5 um steps (to 0.5 um), then up in 1 um steps (to 12 um), to bracket a sign
    #    change, then regula falsi. With no zero, set lnw for the same reference current as the s = 1 null (--iref),
    #    so that every s is compared at the same current, and report the tempco left there.
    def step(x):
        t = tc(a.s, round(x, 4), out, a.jobs); res["tc_iter"].append(t)
        print(f"s={a.s:g} lnw {t['lnw']:.4f} tempco {t['tc_ppm']:.1f} ppm/C  Iref {t['iref27']*1e6:.2f} uA", flush=True)
        return t
    first = step(a.lnw0)
    lo, hi = first, None
    for x in [a.lnw0 - 0.5 * i for i in range(1, 9)] + [None] + [a.lnw0 + 0.5 + i for i in range(8)]:
        if x is None:          # going up now: restart from lnw0
            lo = first; continue
        if x < 0.5 or x > 12:
            continue
        t = step(x)
        if t["tc_ppm"] != t["tc_ppm"]:
            continue
        if (t["tc_ppm"] > 0) != (lo["tc_ppm"] > 0):
            hi = t; break
        lo = t
    if hi:
        for _ in range(8):
            if min(abs(lo["tc_ppm"]), abs(hi["tc_ppm"])) < 3:
                break
            t = step(lo["lnw"] - lo["tc_ppm"] * (hi["lnw"] - lo["lnw"]) / (hi["tc_ppm"] - lo["tc_ppm"]))
            if (t["tc_ppm"] > 0) == (lo["tc_ppm"] > 0):
                lo = t
            else:
                hi = t
        best = min((lo, hi), key=lambda r: abs(r["tc_ppm"]))
        res["tc_null"] = True
    else:                      # no zero: same Iref as the s = 1 null (Iref falls monotonically with lnw)
        res["tc_null"] = False
        ok = [r for r in res["tc_iter"] if r["tc_ppm"] == r["tc_ppm"]]
        res["tc_min_scanned"] = min(ok, key=lambda r: abs(r["tc_ppm"]))
        pts = sorted(ok, key=lambda r: r["lnw"])
        for _ in range(6):
            up = [r for r in pts if r["iref27"] >= a.iref]
            dn = [r for r in pts if r["iref27"] < a.iref]
            r0, r1 = up[-1], dn[0]
            x = r0["lnw"] + (a.iref - r0["iref27"]) * (r1["lnw"] - r0["lnw"]) / (r1["iref27"] - r0["iref27"])
            t = step(x)
            pts = sorted(pts + [t], key=lambda r: r["lnw"])
            if abs(t["iref27"] / a.iref - 1) < 0.003:
                break
        best = t
    res["tc_iter"] = [r for r in res["tc_iter"] if r["tc_ppm"] == r["tc_ppm"]]   # drop nan (no oscillation)
    lnw = best["lnw"]
    res.update(lnw=lnw, tc_ppm=best["tc_ppm"], f_tc=best["f"], iref=best["iref27"])
    print(f"s={a.s:g}: lnw {lnw:.4f} um, tempco {best['tc_ppm']:.1f} ppm/C (null: {res['tc_null']}), "
          f"Iref {best['iref27']*1e6:.2f} uA", flush=True)
    # 2. PVT spread
    p = params(a.s, lnw, False)
    pts = [(CODE, VCTRL, t, d) for t in (0, 27, 70) for d in (3.15, 3.3, 3.45)]
    rows = vco_bias.run(out / "pvt", [(f"pvt_{c}", vco_bias.deck(p, c, pts, uic=False)) for c in vco_bias.CORNERS], max(a.jobs, 2))
    fs = [r[5] for r in rows]
    res["pvt"] = [dict(corner=r[0][4:], temp=r[3], vdd=r[4], f=r[5], iref=r[8]) for r in rows]
    res["pvt_fmin"], res["pvt_fmax"] = min(fs), max(fs)
    res["pvt_spread_pct"] = (max(fs) - min(fs)) / (max(fs) + min(fs)) * 200   # +-% about the midpoint
    print(f"s={a.s:g}: PVT f {min(fs)/1e6:.1f} .. {max(fs)/1e6:.1f} MHz (+-{res['pvt_spread_pct']/2:.1f} %), "
          f"{len(fs)} points", flush=True)
    # 3. start-up (RC filter on)
    cmd = [sys.executable, str(REPO / "sim/vco/vco_bias.py"), "startup", "--corners", "ss,ff", "--temps", "0,70",
           "--jobs", str(max(a.jobs, 2)), "--tag", f"su_s{a.s:g}{a.tag}"]
    for k, x in bias_fm.scaled(a.s, EXTRA + [f"lnw={lnw}"]).items():
        cmd += ["--set", f"{k}={x}"]
    su = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO).stdout
    (out / "startup.txt").write_text(su)
    res["startup_ok"] = "STARTUP OK" in su
    print(f"s={a.s:g}: start-up {'OK' if res['startup_ok'] else 'FAIL'}", flush=True)
    fm_step(a, res, out, lnw)
    print(f"wrote {out}/ref_sweep.json")


if __name__ == "__main__":
    main()
