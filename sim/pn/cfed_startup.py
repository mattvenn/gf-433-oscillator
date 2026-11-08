#!/usr/bin/env python3
"""Power-on start-up of the current-fed ring (docs/handoff_cfed_startup_mc.md). Driver: sim/pn/cfed_startup_run.sh.

Full circuit (reference + RC filter + DAC + 3 pF vg decap + ring), every node at 0 V at t = 0 (tran ... uic, no .ic),
VDD ramped 0 -> 3.3 V (PWL) in --tramp; bitb (code 0) / bit (code 31) lines ramp with VDD; vctrl a fixed 1.65 V.
Each run writes a binary raw file of time, vdd, vbn, vbnf, vg, a0, a2 only; Python analyses it and keeps a
decimated .npz (50 ns bins) for plots, then deletes the raw.

  calib    tt 27 C, code 0, 10 us ramp, --tstop (250 us) at max steps --tmaxs (5p,10p,20p): picks the largest step
           whose final f is within 0.1 % of the finest one, and the run length = settle + 20 us -> <out>/calib.json
  run      the 36 cases of the config (corners/temps from the handoff block, read by the driver) with calib.json's
           step and length -> <out>/runs/<case>.json, <out>/results.json
  summary  table + plots of the worst case -> <out>/summary.md, <out>/*.png

Per run (analysis of the raw):
  vbn: final = mean of the last 2 us; DC value = .op at VDD 3.3 (same corner/T/code); t_vbn = last time vbn is more
       than 1 % away from the DC value. vbnf the same (1 %).
  vg:  50 ns running mean (removes the ring ripple); t_vg = last time it is more than 2 % away from its final value;
       ripple = p-p of that mean over the last 20 us; overshoot = max(vg - vdd) over the run.
  ring: a0 / a2 rising crossings of the instantaneous mid-level (vdd + vg_mean)/2.
       t_osc = first a0 rise after which no gap between rises exceeds 100 ns (ring running continuously);
       t_f1  = time after which the 100-period mean f stays within 1 % of the final f;
       f = rises / time over the last 2 us; vs the DC-start f in map.csv (same corner/T/code, vctrl 1.65, VDD 3.3);
       mode = mean phase (a0 rise -> next a2 rise) / period over the last 2 us (fundamental: 0.2 +- 0.07);
       swing = min / max of a0 over the last 2 us; stuck = no rises in the last 2 us.
"""
import argparse, csv, json, math, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/vco"))
sys.path.insert(0, str(REPO / "sim/pn"))
import vco_bias as vb, topo_cmp as tcm, cfed_noise as cn  # noqa: E402

SETS = ["lnw=5.023", "ka=16", "wfu=0.30", "wff=0.30", "rf=1e6", "cf=20e-12"]   # + cfed_noise WINNER + CFED
MAP = REPO / "sim/results/2026-11-08/cfed/map.csv"
VEC = ["vdd", "vbn", "vbnf", "vg", "a0", "a2"]
BAD = ("singular", "timestep too small", "transient op started")


def params():
    return cn.params(SETS)


def sources(p, code, tramp, ramp=True):
    v = f"PWL(0 0 {tramp} 3.3)" if ramp else "3.3"
    s = f"vdd vdd 0 {v}\nvctrl vctrl 0 1.65\n"
    for b in range(p["bits"]):
        on = (code >> b) & 1
        s += f"vbit{b} bit{b} 0 {v if on else 0}\nvbitb{b} bitb{b} 0 {0 if on else v}\n"
    return s


def tran_deck(p, corner, temp, code, tramp, tstop, tmax, raw):
    body, _ = vb.netlist(p)
    return f"""* cfed power-on {corner} {temp} code {code} ramp {tramp}
{tcm.HDR.format(corner=corner)}{sources(p, code, tramp)}{body}.control
option temp={temp}
set filetype=binary
save {' '.join(f'v({x})' for x in VEC)}
tran 1n {tstop} 0 {tmax} uic
write {raw} {' '.join(f'v({x})' for x in VEC)}
echo "TRANDONE"
quit
.endc
.end
"""


def op_deck(p, corner, temp, code):
    body, _ = vb.netlist(p)
    return f"""* cfed op {corner} {temp} code {code}
{tcm.HDR.format(corner=corner)}{sources(p, code, 0, ramp=False)}{body}.control
option temp={temp}
op
echo "OPV $&v(vbn) $&v(vbnf) $&v(vg)"
quit
.endc
.end
"""


def ngspice(d, name, text):
    d.mkdir(parents=True, exist_ok=True)
    (d / ".spiceinit").write_text(re.sub(r"num_threads=\d+", "num_threads=1", (REPO / ".spiceinit").read_text()))
    (d / f"{name}.cir").write_text(text)
    t0 = time.time()
    subprocess.run([vb.OSIC, "bash", "-c", f"cd {d} && ngspice -b {name}.cir > {name}.log 2>&1"], check=False)
    return (d / f"{name}.log").read_text(), time.time() - t0


def read_raw(path):
    """ngspice binary raw (real): header lines up to 'Binary:', then npoints x nvars doubles."""
    b = path.read_bytes()
    i = b.index(b"Binary:\n") + len(b"Binary:\n")
    hdr = b[:i].decode(errors="replace")
    nv = int(re.search(r"No\. Variables:\s*(\d+)", hdr).group(1))
    npnt = int(re.search(r"No\. Points:\s*(\d+)", hdr).group(1))
    names = re.findall(r"^\s*\d+\s+(\S+)\s+\S+", hdr.split("Variables:\n")[-1], re.M)[:nv]
    a = np.frombuffer(b[i:i + 8 * nv * npnt], dtype="<f8").reshape(npnt, nv)
    out = {}
    for k, n in enumerate(names):
        m = re.fullmatch(r"v\((\w+)\)", n)
        out[m.group(1) if m else n] = a[:, k].copy()
    return out


def run_mean(t, y, w):
    """Mean of y over [t - w/2, t + w/2] on the samples t (trapezoid cumulative integral)."""
    c = np.concatenate(([0.0], np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(t))))
    lo, hi = np.clip(t - w / 2, t[0], t[-1]), np.clip(t + w / 2, t[0], t[-1])
    span = np.maximum(hi - lo, 1e-15)
    return (np.interp(hi, t, c) - np.interp(lo, t, c)) / span


def rises(t, y, thr):
    s = y - thr
    k = np.where((s[:-1] < 0) & (s[1:] >= 0))[0]
    return t[k] - s[k] * (t[k + 1] - t[k]) / (s[k + 1] - s[k])


def last_out(t, y, ref, tol):
    """Last time |y - ref| > tol*|ref| (0 if never)."""
    k = np.where(np.abs(y - ref) > tol * abs(ref))[0]
    return float(t[k[-1]]) if len(k) else 0.0


def analyse(raw, op, f_map, tstop):
    d = read_raw(raw)
    t = d.pop("time")
    T2 = tstop - 2e-6
    end = t >= T2
    r = {}
    for k, tol in (("vbn", 0.01), ("vbnf", 0.01)):
        r[f"{k}_final"] = float(d[k][end].mean())
        r[f"{k}_dc"] = op[k]
        r[f"t_{k}"] = last_out(t, d[k], op[k], tol)
    vgm = run_mean(t, d["vg"], 50e-9)
    r["vg_final"] = float(vgm[end].mean())
    r["vg_dc"] = op["vg"]
    r["t_vg"] = last_out(t, vgm, r["vg_final"], 0.02)
    last20 = t >= tstop - 20e-6
    r["vg_ripple_last20us"] = float(vgm[last20].max() - vgm[last20].min())
    r["vg_over_vdd_max"] = float(np.max(d["vg"] - d["vdd"]))
    thr = (d["vdd"] + vgm) / 2
    ra = rises(t, d["a0"], thr)
    rb = rises(t, d["a2"], thr)
    r["n_rises"] = int(len(ra))
    fin = ra[ra >= T2]
    r["stuck"] = len(fin) < 3
    if r["stuck"]:
        r.update(f=float("nan"), f_map=f_map, df_pct=float("nan"), mode=float("nan"), t_osc=float("nan"), t_f1=float("nan"),
                 swing=[float(d["a0"][end].min()), float(d["a0"][end].max())])
        return r, d, t, vgm
    f = (len(fin) - 1) / (fin[-1] - fin[0])
    r["f"], r["f_map"] = float(f), f_map
    r["df_pct"] = 100 * (f / f_map - 1) if f_map else float("nan")
    ph = []
    for x in fin[:-1]:
        j = np.searchsorted(rb, x)
        if j < len(rb):
            ph.append(((rb[j] - x) * f) % 1.0)
    r["mode"] = float(np.mean(ph)) if ph else float("nan")
    r["mode_ok"] = bool(abs(r["mode"] - 0.2) <= 0.07)
    r["swing"] = [float(d["a0"][end].min()), float(d["a0"][end].max())]
    gaps = np.diff(ra)
    big = np.where(gaps > 100e-9)[0]
    r["t_osc"] = float(ra[big[-1] + 1] if len(big) else ra[0])
    # 100-period mean f, last time it is outside 1 % / 0.1 % of the final f
    n = 100
    if len(ra) > n + 1:
        fm = n / (ra[n:] - ra[:-n])
        tm = ra[n:]
        for tag, tol in (("t_f1", 0.01), ("t_f01", 0.001)):
            k = np.where(np.abs(fm / f - 1) > tol)[0]
            r[tag] = float(tm[k[-1]]) if len(k) else float(tm[0])
    else:
        r["t_f1"] = r["t_f01"] = float("nan")
    # f in the 2 us window ending 10 us before the end (settling check)
    w = ra[(ra >= tstop - 12e-6) & (ra < tstop - 10e-6)]
    r["f_minus10us_pct"] = float(100 * ((len(w) - 1) / (w[-1] - w[0]) / f - 1)) if len(w) > 2 else float("nan")
    return r, d, t, vgm


def decimate(d, t, vgm, path, bin_=50e-9):
    """50 ns bins: mean of vdd / vbn / vbnf / vg (running mean), min / max of a0."""
    e = np.arange(0, t[-1] + bin_, bin_)
    idx = np.searchsorted(t, e)
    out = {"t": e[:-1]}
    for k in ("vdd", "vbn", "vbnf"):
        out[k] = np.interp(e[:-1], t, d[k])
    out["vg"] = np.interp(e[:-1], t, vgm)
    mn, mx = [], []
    for a, b in zip(idx[:-1], idx[1:]):
        seg = d["a0"][a:max(b, a + 1)]
        mn.append(seg.min()); mx.append(seg.max())
    out["a0_min"], out["a0_max"] = np.array(mn), np.array(mx)
    np.savez_compressed(path, **out)


def f_map_of(corner, temp, code):
    for row in csv.DictReader(open(MAP)):
        if (row["corner"] == corner and float(row["temp"]) == temp and float(row["vdd"]) == 3.3
                and int(row["code"]) == code and float(row["vctrl"]) == 1.65):
            return float(row["f"])
    return None


def one_case(out, p, corner, temp, code, tramp, tstop, tmax, keep_raw=False):
    name = f"{corner}_t{temp:g}_c{code}_r{tramp * 1e6:g}u_s{tmax}"
    d = out / "runs" / name
    raw = d / f"{name}.raw"
    raw.unlink(missing_ok=True)
    log_op, _ = ngspice(d, "op", op_deck(p, corner, temp, code))
    m = re.search(r"^OPV (\S+) (\S+) (\S+)$", log_op, re.M)
    log, dt = ngspice(d, name, tran_deck(p, corner, temp, code, tramp, tstop, tmax, raw.name))
    res = dict(name=name, corner=corner, temp=temp, code=code, tramp=tramp, tstop=tstop, tmax=tmax, wall_s=dt)
    issues = [b for b in BAD if b in log.lower() or b in log_op.lower()]
    if not m or "TRANDONE" not in log or not raw.exists() or issues:
        res["error"] = f"op {'ok' if m else 'MISSING'}, tran {'done' if 'TRANDONE' in log else 'NOT DONE'}, issues {issues}: " \
                       + " | ".join(log.splitlines()[-4:])
        (d / "result.json").write_text(json.dumps(res, indent=1))
        return res
    op = dict(zip(("vbn", "vbnf", "vg"), map(float, m.groups())))
    r, dd, t, vgm = analyse(raw, op, f_map_of(corner, temp, code), tstop)
    res.update(r, npoints=int(len(t)))
    decimate(dd, t, vgm, d / "wave.npz")
    if not keep_raw:
        raw.unlink()
    (d / "result.json").write_text(json.dumps(res, indent=1))
    return res


def do_calib(a):
    p = params()
    tm = a.tmaxs.split(",")
    with ThreadPoolExecutor(len(tm)) as ex:
        rs = list(ex.map(lambda x: one_case(a.out, p, "typical", 27.0, 0, 10e-6, a.tstop, x), tm))
    bad = [r for r in rs if "error" in r or r.get("stuck")]
    if bad:
        print("FAIL calib:", json.dumps(bad, indent=1)); sys.exit(1)
    ref = min(rs, key=lambda r: float(r["tmax"].rstrip("p")))
    ok = [r for r in rs if abs(r["f"] / ref["f"] - 1) <= 0.001]
    pick = max(ok, key=lambda r: float(r["tmax"].rstrip("p")))
    settle = max(pick["t_vbnf"], pick["t_vg"], pick["t_f01"], pick["t_vbn"])
    tstop = math.ceil((settle + 20e-6) / 10e-6) * 10e-6
    c = dict(tmax=pick["tmax"], tstop=tstop, settle=settle, runs=rs,
             f_by_tmax={r["tmax"]: r["f"] for r in rs}, wall_by_tmax={r["tmax"]: r["wall_s"] for r in rs})
    (a.out / "calib.json").write_text(json.dumps(c, indent=1))
    for r in rs:
        print(f"tmax {r['tmax']:>4s}: f {r['f']/1e6:.4f} MHz ({100*(r['f']/ref['f']-1):+.4f} % vs finest)  wall {r['wall_s']:.0f} s "
              f"points {r['npoints']}  t_vbn {r['t_vbn']*1e6:.1f} t_vbnf {r['t_vbnf']*1e6:.1f} t_vg {r['t_vg']*1e6:.1f} "
              f"t_f0.1% {r['t_f01']*1e6:.1f} us  mode {r['mode']:.3f}")
    # estimate the main run: wall per simulated us at the picked step, x the longest case (ss 0 C is the slowest)
    est = pick["wall_s"] * tstop / a.tstop
    print(f"PICK tmax {pick['tmax']}  settle {settle*1e6:.1f} us  tstop {tstop*1e6:.0f} us  "
          f"est per run {est/60:.1f} min, 36 runs on {a.jobs} CPUs ~ {math.ceil(36 / a.jobs) * est * 1.3 / 60:.0f} min")
    (a.out / "eta_min.txt").write_text(f"{math.ceil(math.ceil(36 / a.jobs) * est * 1.3 / 60)}\n")


def cases(a):
    cs = []
    for corners, temps in ((a.main_corners, a.main_temps), (a.robust_corners, a.robust_temps)):
        for c in corners.split():
            for t in temps.split():
                for code in map(int, a.codes.split()):
                    for tr in a.ramps.split():
                        cs.append((c, float(t), code, float(tr)))
    return cs


def do_run(a):
    c = json.loads((a.out / "calib.json").read_text())
    p = params()
    cs = cases(a)
    print(f"{len(cs)} cases, tmax {c['tmax']}, tstop {c['tstop']*1e6:.0f} us", flush=True)
    # slowest first (cold ss / low current): longest wall times start early
    cs.sort(key=lambda x: (x[0] != "ss", x[1] != 0.0))
    def go(x):
        r = one_case(a.out, p, x[0], x[1], x[2], x[3], c["tstop"], c["tmax"])
        print(f"{r['name']}: " + (r["error"] if "error" in r else
              f"f {r['f']/1e6:.3f} MHz ({r['df_pct']:+.3f} % vs map) mode {r['mode']:.3f} t_osc {r['t_osc']*1e6:.1f} "
              f"t_f1% {r['t_f1']*1e6:.1f} t_vg {r['t_vg']*1e6:.1f} us  wall {r['wall_s']/60:.1f} min"), flush=True)
        return r
    with ThreadPoolExecutor(a.jobs) as ex:
        rs = list(ex.map(go, cs))
    (a.out / "results.json").write_text(json.dumps(dict(calib={k: v for k, v in c.items() if k != "runs"}, runs=rs), indent=1))
    err = [r for r in rs if "error" in r]
    if len(rs) != len(cs) or err:
        print(f"FAIL run: {len(err)} runs with errors:\n" + "\n".join(f"{r['name']}: {r['error']}" for r in err[:5]))
        sys.exit(1)


def judge(r):
    f = []
    if r.get("stuck"):
        return ["STUCK"]
    if not r["mode_ok"]:
        f.append(f"mode {r['mode']:.2f}")
    if not abs(r["df_pct"]) <= 1.0:
        f.append(f"f {r['df_pct']:+.2f} %")
    if r["vg_over_vdd_max"] > 0.05:            # reported for every run; flagged above 50 mV
        f.append(f"vg > VDD by {r['vg_over_vdd_max']*1e3:.0f} mV")
    if not abs(r["vbn_final"] / r["vbn_dc"] - 1) <= 0.01:
        f.append("vbn != DC")
    if r["t_vg"] > r["tstop"] - 20e-6 or r["t_f1"] > r["tstop"] - 20e-6:
        f.append("not settled 20 us before the end")
    return f


def do_summary(a):
    R = json.loads((a.out / "results.json").read_text())
    rs, c = R["runs"], R["calib"]
    U = lambda x: f"{x * 1e6:.1f}"
    ln = ["# cfed power-on start-up summary (sim/pn/cfed_startup.py summary)", "",
          f"tmax {c['tmax']}, run length {c['tstop']*1e6:.0f} us", "",
          "| corner | T °C | code | ramp µs | vbn DC V | t_vbn 1 % µs | t_vbnf 1 % µs | t_vg 2 % µs | vg final V | t_osc µs | "
          "t_f 1 % µs | f MHz | vs map % | mode | swing V | max(vg−VDD) mV | verdict | wall min |", "|" + "---|" * 18]
    for r in rs:
        v = judge(r)
        ln.append(f"| {r['corner']} | {r['temp']:g} | {r['code']} | {r['tramp']*1e6:g} | {r['vbn_dc']:.4f} | {U(r['t_vbn'])} | "
                  f"{U(r['t_vbnf'])} | {U(r['t_vg'])} | {r['vg_final']:.3f} | {U(r['t_osc'])} | {U(r['t_f1'])} | "
                  f"{r['f']/1e6:.2f} | {r['df_pct']:+.3f} | {r['mode']:.3f} | {r['swing'][0]:.2f}–{r['swing'][1]:.2f} | "
                  f"{r['vg_over_vdd_max']*1e3:.0f} | {'ok' if not v else '**' + '; '.join(v) + '**'} | {r['wall_s']/60:.1f} |")
    fails = [r for r in rs if judge(r)]
    key = lambda r: max(r["t_f1"], r["t_vg"], r["t_vbnf"])
    worst = max(rs, key=lambda r: (r.get("stuck", False), key(r) if not math.isnan(key(r)) else 9e9))
    ln += ["", f"Runs: {len(rs)}, flagged: {len(fails)}.",
           f"Worst start-up (max of t_f 1 %, t_vg, t_vbnf): {worst['name']} at {U(key(worst))} µs.",
           f"Worst t_osc: {max(rs, key=lambda r: r['t_osc'])['name']} at {U(max(r['t_osc'] for r in rs))} µs; "
           f"worst |f − map|: {max(abs(r['df_pct']) for r in rs):.3f} %; mode {min(r['mode'] for r in rs):.3f}–"
           f"{max(r['mode'] for r in rs):.3f}; max f drift over the last 10 µs: "
           f"{max(abs(r['f_minus10us_pct']) for r in rs):.3f} %."]
    (a.out / "summary.md").write_text("\n".join(ln) + "\n")
    print("\n".join(ln))
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for tag, r in [("worst", worst)] + [(f"fail{i}", x) for i, x in enumerate(fails[:3])]:
        w = np.load(a.out / "runs" / r["name"] / "wave.npz")
        fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
        tu = w["t"] * 1e6
        for k in ("vdd", "vbn", "vbnf", "vg"):
            ax[0].plot(tu, w[k], label=k + (" (50 ns mean)" if k == "vg" else ""))
        ax[0].legend(); ax[0].set_ylabel("V"); ax[0].grid(alpha=.3)
        ax[0].set_title(f"cfed power-on: {r['name']}  (f {r['f']/1e6:.2f} MHz, mode {r['mode']:.3f})")
        ax[1].fill_between(tu, w["a0_min"], w["a0_max"], alpha=.5, label="a0 min/max per 50 ns")
        ax[1].plot(tu, w["vdd"], "k", lw=.8, label="vdd")
        for x, lab in ((r["t_osc"], "t_osc"), (r["t_f1"], "t_f 1 %")):
            ax[1].axvline(x * 1e6, ls="--", c="r" if lab == "t_osc" else "g", label=lab)
        ax[1].legend(); ax[1].set_ylabel("V"); ax[1].set_xlabel("t (µs)"); ax[1].grid(alpha=.3)
        fig.tight_layout(); fig.savefig(a.out / f"startup_{tag}.png", dpi=110); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["calib", "run", "summary", "one"])
    ap.add_argument("--out", default=str(REPO / "build/cfed_startup"))
    ap.add_argument("--jobs", type=int, default=20)
    ap.add_argument("--tstop", type=float, default=220e-6)
    ap.add_argument("--tmaxs", default="10p,20p")
    ap.add_argument("--main-corners", default="typical ss ff sf fs")
    ap.add_argument("--main-temps", default="27")
    ap.add_argument("--robust-corners", default="ss ff")
    ap.add_argument("--robust-temps", default="0 70")
    ap.add_argument("--codes", default="0 31")
    ap.add_argument("--ramps", default="10e-6 1e-6")
    ap.add_argument("--case", default="typical,27,0,10e-6,10p", help="one: corner,T,code,tramp,tmax (quick test)")
    a = ap.parse_args()
    a.out = Path(a.out).resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.mode == "one":
        c, t, code, tr, tm = a.case.split(",")
        r = one_case(a.out, params(), c, float(t), int(code), float(tr), a.tstop, tm, keep_raw=False)
        print(json.dumps(r, indent=1))
    else:
        dict(calib=do_calib, run=do_run, summary=do_summary)[a.mode](a)


if __name__ == "__main__":
    main()
