#!/usr/bin/env python3
"""Current-fed ring (topo=cfed) final sizing: DAC width vs tempco vs range, full PVT map, PVT noise.
Brief: docs/handoff_cfed_sizing.md. Driver: sim/pn/cfed_sizing_run.sh (runs the steps below in order).

  null     Job 1a: for each DAC width scale w (wfu = wff = 0.25 w), find the n-well length lnw (lnp = 100) and the
           code nearest 433.92 MHz (tt 27 C, vctrl 1.65, VDD 3.3) jointly so that the tempco at that code is nulled.
           Start grid lnw 3..9 um, then per w: secant root of tc(code, lnw) at fixed code inside the lnw interval
           where that code is the nearest one; bisection when the null falls on a code switch; extension if the grid
           does not bracket it. Each evaluation = 32 codes x 0/27/70 C at tt. -> <out>/job1/null.json
  check    Job 1b: each w at its null: 5 corners x 0/27/70 C x codes 0-31 x vctrl 0/1.65/3.3, VDD 3.3
           -> range, step vs fine (ss 70 / tt 27 / ff 0), tempco at each corner's own 433.92 code -> job1/check.json
  pick     smallest w with the range met at all 10 corner x 0/70 C points and |tempco| <= 50 ppm/C at tt
           -> job1/winner.json (Jobs 2 and 3 read w and lnw from here)
  map      Job 2: winner, codes 0-31 x vctrl 0/1.65/3.3 x 5 corners x 0/27/70 C x VDD 3.15/3.3/3.45 (VDD 3.3 reused
           from check) -> job2/map.csv, job2/map_summary.json
  noise    Job 3: at each corner x 0/27/70 C, at that point's 433.92 code (VDD 3.3, vctrl 1.65): cfed_noise.py ki and
           dacn; isf at tt 27 C (m = --m) -> job3/noise.json
  summary  tables -> <out>/summary.md
Every step checks its own outputs (row counts, no "singular", no "Transient op started") and exits 1 on failure.
Common: --out (default build/cfed_sizing), --jobs (CPU budget, one-thread ngspice each).
"""
import argparse, csv, json, math, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/vco"))
sys.path.insert(0, str(REPO / "sim/pn"))
import vco_bias as vb, topo_cmp as tcm, cfed_noise as cn  # noqa: E402

FIXED = ["ka=16", "rf=1e6", "cf=20e-12"]     # on top of cfed_noise WINNER + CFED (topo cfed, kc .75, k 6, cvg 3p, cw 3f)
WS = [1.0, 1.1, 1.2, 1.3, 1.4]
FT = 433.92e6
TEMPS = (0.0, 27.0, 70.0)
VCS = (0.0, 1.65, 3.3)
GRID = [3.0, 4.5, 6.0, 7.5, 9.0]
CHUNK = 8                                    # codes per deck
BAD = ("singular", "transient op started", "timestep too small")


def sets_for(w, lnw):
    return FIXED + [f"wfu={0.25 * w:.6g}", f"wff={0.25 * w:.6g}", f"lnw={lnw:.4f}"]


class Fail(Exception):
    pass


def run(decks, jobs):
    """decks: [(dir, name, text, n_expected_rows)]. One-thread ngspice each, `jobs` at a time. Returns {(dir, name): rows}."""
    init = re.sub(r"num_threads=\d+", "num_threads=1", (REPO / ".spiceinit").read_text())
    for d, n, t, _ in decks:
        d.mkdir(parents=True, exist_ok=True)
        (d / ".spiceinit").write_text(init)
        (d / f"{n}.cir").write_text(t)

    def one(x):
        d, n, _, _ = x
        subprocess.run([vb.OSIC, "bash", "-c", f"cd {d} && ngspice -b {n}.cir > {n}.log 2>&1"], check=False)
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        list(ex.map(one, decks))
    out, bad = {}, []
    for d, n, _, ne in decks:
        lp = d / f"{n}.log"
        log = lp.read_text() if lp.exists() else ""
        rows = tcm.parse(log)
        issues = [b for b in BAD if b in log.lower()]
        if len(rows) != ne or issues:
            bad.append(f"{lp}: {len(rows)}/{ne} rows {issues} | " + " | ".join(log.splitlines()[-4:]))
        out[(d, n)] = rows
    if bad:
        raise Fail(f"{len(bad)} bad decks, first: " + "\n".join(bad[:5]))
    return out


def tt_decks(d, w, lnw):
    p = cn.params(sets_for(w, lnw))
    dd = d / f"w{w:g}_lnw{lnw:.4f}"
    return [(dd, f"t{t:g}_{i}", tcm.deck(p, "typical", [(c, 1.65, t, 3.3) for c in range(i, min(i + CHUNK, 32))]),
             min(CHUNK, 32 - i)) for t in TEMPS for i in range(0, 32, CHUNK)]


def tc3(f0, f27, f70):
    return cn.tc_of([dict(temp=0.0, f=f0), dict(temp=27.0, f=f27), dict(temp=70.0, f=f70)])


def ev_summary(fs):
    """fs: {(code, temp): f} at tt -> nearest code at 27 C and its tempco."""
    c = min(range(32), key=lambda k: abs(fs[(k, 27.0)] - FT) if not math.isnan(fs[(k, 27.0)]) else 9e99)
    return dict(code=c, f27=fs[(c, 27.0)], tc=tc3(fs[(c, 0.0)], fs[(c, 27.0)], fs[(c, 70.0)]),
                tc_all=[tc3(fs[(k, 0.0)], fs[(k, 27.0)], fs[(k, 70.0)]) for k in range(32)],
                f27_all=[fs[(k, 27.0)] for k in range(32)])


def next_lnw(ev):
    """ev: {lnw: ev_summary}. Next lnw to evaluate, or None when done."""
    L = sorted(ev)
    best = min(L, key=lambda l: abs(ev[l]["tc"]))
    if abs(ev[best]["tc"]) <= 2.0:
        return None
    tcs = [ev[l]["tc"] for l in L]
    if all(t < 0 for t in tcs):                 # null at smaller lnw (higher I, lower code)
        return max(L[0] - 1.5, 0.5) if L[0] > 0.5 else None
    if all(t > 0 for t in tcs):
        return L[-1] + 2.0
    # bracket around the sign change of tc at the nearest code
    for l1, l2 in zip(L, L[1:]):
        if (ev[l1]["tc"] > 0) != (ev[l2]["tc"] > 0):
            break
    e1, e2 = ev[l1], ev[l2]
    # secant root of tc(c, lnw) at fixed c, valid if c is still the nearest code there
    for c in sorted({e1["code"], e2["code"]}):
        t1, t2 = e1["tc_all"][c], e2["tc_all"][c]
        if (t1 > 0) == (t2 > 0) or t1 == t2:
            continue
        l0 = l1 + (0 - t1) * (l2 - l1) / (t2 - t1)
        x = (l0 - l1) / (l2 - l1)
        f = [a + x * (b - a) for a, b in zip(e1["f27_all"], e2["f27_all"])]
        cn0 = min(range(32), key=lambda k: abs(f[k] - FT))
        if cn0 == c and all(abs(l0 - l) > 0.005 for l in L):
            return round(l0, 4)
    l0 = round((l1 + l2) / 2, 4)                 # null on a code switch: bisect to the switch
    return l0 if l2 - l1 > 0.01 else None


def do_null(a):
    d = a.out / "job1/null"
    ws = [float(x) for x in a.ws.split(",")]
    ev = {w: {} for w in ws}
    todo = {w: list(GRID) for w in ws}
    for it in range(a.iters + 1):
        batch = [(w, l) for w in ws for l in todo[w]]
        if not batch:
            break
        t0 = time.time()
        decks = [x for w, l in batch for x in tt_decks(d, w, l)]
        rows = run(decks, a.jobs)
        for w, l in batch:
            dd = d / f"w{w:g}_lnw{l:.4f}"
            fs = {(r["code"], r["temp"]): r["f"] for (dk, _), rs in rows.items() if dk == dd for r in rs}
            ev[w][l] = ev_summary(fs)
            print(f"it {it} w {w:g} lnw {l:.4f}: code {ev[w][l]['code']:2d} f27 {ev[w][l]['f27']/1e6:7.2f} MHz "
                  f"tc {ev[w][l]['tc']:+7.1f} ppm/C", flush=True)
        print(f"iteration {it}: {len(decks)} decks, {time.time() - t0:.0f} s", flush=True)
        todo = {w: ([n] if (n := next_lnw(ev[w])) is not None and it < a.iters else []) for w in ws}
    res = {}
    for w in ws:
        best = min(ev[w], key=lambda l: abs(ev[w][l]["tc"]))
        e = ev[w][best]
        res[f"{w:g}"] = dict(w=w, lnw=best, code=e["code"], f27=e["f27"], tc=e["tc"],
                             evals={f"{l:.4f}": dict(code=x["code"], f27=x["f27"], tc=x["tc"]) for l, x in sorted(ev[w].items())})
        print(f"NULL w {w:g}: lnw {best:.4f} code {e['code']} f27 {e['f27']/1e6:.2f} MHz tc {e['tc']:+.1f} ppm/C")
        if abs(e["tc"]) > 50:
            print(f"NOTE w {w:g}: no null within 50 ppm/C found")
    (a.out / "job1/null.json").write_text(json.dumps(res, indent=1))


def grid_decks(d, p, corner, temp, vdd):
    return [(d, f"{corner}_t{temp:g}_v{vdd:g}_{i}",
             tcm.deck(p, corner, [(c, vc, temp, vdd) for c in range(i, min(i + CHUNK, 32)) for vc in VCS]),
             3 * min(CHUNK, 32 - i)) for i in range(0, 32, CHUNK)]


def analyze_pvt(rs):
    """rs: rows of one corner x temp x vdd (32 codes x 3 vctrl)."""
    f = {(r["code"], r["vctrl"]): r["f"] for r in rs}
    F = lambda c, v: f.get((c, v), float("nan"))
    worst, wc = 9e9, None
    for c in range(31):
        step = F(c + 1, 1.65) - F(c, 1.65)
        fine = min(F(c, 3.3) - F(c, 0.0), F(c + 1, 3.3) - F(c + 1, 0.0))
        ratio = fine / step if step > 0 else float("nan")
        if not ratio >= worst:
            worst, wc = ratio, c
    mono_code = all(F(c + 1, v) > F(c, v) for c in range(31) for v in VCS)
    mono_vc = all(F(c, 0.0) < F(c, 1.65) < F(c, 3.3) for c in range(32))
    near = min(range(32), key=lambda c: abs(F(c, 1.65) - FT) if not math.isnan(F(c, 1.65)) else 9e99)
    cover = [c for c in range(32) if F(c, 0.0) <= FT <= F(c, 3.3)]
    vg = [r["vg"] for r in rs]
    return dict(fmin=F(0, 0.0), fmax=F(31, 3.3), near=near, f_near=F(near, 1.65), codes433=cover,
                worst_ratio=worst, worst_code=wc, mono_code=mono_code, mono_vctrl=mono_vc,
                vg_min=min(vg), vg_max=max(vg), amin_min=min(r["amin"] for r in rs),
                amax_max=max(r["amax"] for r in rs),
                vg_near=next(r["vg"] for r in rs if r["code"] == near and r["vctrl"] == 1.65),
                swing_near=[next((r["amin"], r["amax"]) for r in rs if r["code"] == near and r["vctrl"] == 1.65)],
                n_nan=sum(1 for r in rs if math.isnan(r["f"])), p_near=next(r["p_w"] for r in rs
                                                                           if r["code"] == near and r["vctrl"] == 1.65))


def by_pvt(rows):
    g = {}
    for r in rows:
        g.setdefault((r["corner"], r["temp"], r["vdd"]), []).append(r)
    return g


def do_check(a):
    null = json.loads((a.out / "job1/null.json").read_text())
    decks = []
    for k, n in null.items():
        p = cn.params(sets_for(n["w"], n["lnw"]))
        d = a.out / f"job1/check/w{k}"
        decks += [x for c in vb.CORNERS for t in TEMPS for x in grid_decks(d, p, c, t, 3.3)]
    rows = run(decks, a.jobs)
    res = {}
    for k, n in null.items():
        d = a.out / f"job1/check/w{k}"
        rr = [dict(corner=nm.split("_t")[0], **r) for (dk, nm), rs in rows.items() if dk == d for r in rs]
        (d / "rows.json").write_text(json.dumps(rr))
        g = {kk: analyze_pvt(v) for kk, v in by_pvt(rr).items()}
        rng = {f"{c} {t:g}": dict(fmin=g[(c, t, 3.3)]["fmin"], fmax=g[(c, t, 3.3)]["fmax"],
                                  ok=g[(c, t, 3.3)]["fmin"] <= 310e6 and g[(c, t, 3.3)]["fmax"] >= 700e6)
               for c in vb.CORNERS for t in (0.0, 70.0)}
        step = {f"{c} {t:g}": dict(worst_ratio=g[(c, t, 3.3)]["worst_ratio"], code=g[(c, t, 3.3)]["worst_code"],
                                   ok=g[(c, t, 3.3)]["worst_ratio"] >= 1.3)
                for c, t in (("ss", 70.0), ("typical", 27.0), ("ff", 0.0))}
        tcs = {}
        for c in vb.CORNERS:
            near = g[(c, 27.0, 3.3)]["near"]
            fx = {t: next(r["f"] for r in by_pvt(rr)[(c, t, 3.3)] if r["code"] == near and r["vctrl"] == 1.65) for t in TEMPS}
            tcs[c] = dict(code=near, f27=fx[27.0], tc=tc3(fx[0.0], fx[27.0], fx[70.0]))
        res[k] = dict(w=n["w"], lnw=n["lnw"], null=n, range=rng, range_ok=all(v["ok"] for v in rng.values()),
                      fmin_worst=max(v["fmin"] for v in rng.values()), fmax_worst=min(v["fmax"] for v in rng.values()),
                      step=step, step_ok=all(v["ok"] for v in step.values()), tc=tcs,
                      tc_tt_ok=abs(tcs["typical"]["tc"]) <= 50)
        r = res[k]
        print(f"w {k}: lnw {n['lnw']:.4f}  range {r['fmin_worst']/1e6:.1f}..{r['fmax_worst']/1e6:.1f} MHz "
              f"{'OK' if r['range_ok'] else 'FAIL'}  step {min(v['worst_ratio'] for v in step.values()):.2f} "
              f"{'OK' if r['step_ok'] else 'FAIL'}  tc " + " ".join(f"{c} c{v['code']} {v['tc']:+.0f}" for c, v in tcs.items()))
    (a.out / "job1/check.json").write_text(json.dumps(res, indent=1))


def do_pick(a):
    ch = json.loads((a.out / "job1/check.json").read_text())
    ok = [v for v in ch.values() if v["range_ok"] and v["tc_tt_ok"]]
    if ok:
        win = min(ok, key=lambda v: v["w"])
        why = "smallest w with the range met and |tempco| <= 50 ppm/C at tt"
    else:   # nothing passes: the one closest to the range (worst margin in %), flagged
        marg = lambda v: min(310e6 / v["fmin_worst"], v["fmax_worst"] / 700e6)
        win = max(ch.values(), key=marg)
        why = "NO w PASSES; best range margin taken for Jobs 2/3"
    w = dict(w=win["w"], lnw=win["lnw"], code_tt=win["null"]["code"], tc_tt=win["tc"]["typical"]["tc"],
             passed=bool(ok), why=why, sets=sets_for(win["w"], win["lnw"]))
    (a.out / "job1/winner.json").write_text(json.dumps(w, indent=1))
    print(json.dumps(w))


def do_map(a):
    win = json.loads((a.out / "job1/winner.json").read_text())
    p = cn.params(win["sets"])
    d = a.out / "job2/runs"
    decks = [x for c in vb.CORNERS for t in TEMPS for v in (3.15, 3.45) for x in grid_decks(d, p, c, t, v)]
    rows = run(decks, a.jobs)
    rr = [dict(corner=nm.split("_t")[0], **r) for (dk, nm), rs in rows.items() for r in rs]
    rr += json.loads((a.out / f"job1/check/w{win['w']:g}/rows.json").read_text())   # VDD 3.3 from Job 1
    if len(rr) != 5 * 3 * 3 * 96:
        raise Fail(f"map has {len(rr)} rows, expected {5 * 3 * 3 * 96}")
    rr.sort(key=lambda r: (vb.CORNERS.index(r["corner"]), r["temp"], r["vdd"], r["code"], r["vctrl"]))
    with open(a.out / "job2/map.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["corner", "temp", "vdd", "code", "vctrl", "f", "p_w", "amin", "amax", "vg"])
        wr.writeheader()
        for r in rr:
            wr.writerow({k: r[k] for k in wr.fieldnames})
    g = {f"{c} {t:g} {v:g}": analyze_pvt(x) for (c, t, v), x in by_pvt(rr).items()}
    (a.out / "job2/map_summary.json").write_text(json.dumps(dict(winner=win, pvt=g), indent=1))
    for k, s in g.items():
        print(f"{k:16s} {s['fmin']/1e6:6.1f}..{s['fmax']/1e6:6.1f} MHz near c{s['near']:2d} cover {s['codes433']} "
              f"ratio {s['worst_ratio']:.2f} mono {s['mono_code']}/{s['mono_vctrl']} vg {s['vg_min']:.2f}..{s['vg_max']:.2f} "
              f"a0 {s['amin_min']:.2f}..{s['amax_max']:.2f}")


def do_noise(a):
    win = json.loads((a.out / "job1/winner.json").read_text())
    ms = json.loads((a.out / "job2/map_summary.json").read_text())["pvt"]
    sets = sum((["--set", s] for s in win["sets"]), [])
    pts = [(c, t, ms[f"{c} {t:g} 3.3"]["near"]) for c in vb.CORNERS for t in TEMPS]
    logd = a.out / "job3"
    logd.mkdir(parents=True, exist_ok=True)

    def one(x):
        c, t, code = x
        name = f"sz_{c}_t{t:g}"
        kij = REPO / "build/cfed" / name / "ki.json"
        for f in (kij, kij.with_name("dacn.json")):
            f.unlink(missing_ok=True)
        with open(logd / f"{name}.log", "w") as lg:
            base = [sys.executable, str(REPO / "sim/pn/cfed_noise.py")]
            subprocess.run(base + ["ki", "--name", name, "--code", str(code), "--corner", c, "--temp", f"{t:g}",
                                   "--jobs", "4"] + sets, stdout=lg, stderr=subprocess.STDOUT, cwd=REPO)
            if kij.exists():
                subprocess.run(base + ["dacn", "--name", name, "--code", str(code), "--corner", c, "--temp", f"{t:g}",
                                       "--ki", str(kij), "--jobs", "2"] + sets, stdout=lg, stderr=subprocess.STDOUT, cwd=REPO)
        return x, name
    with ThreadPoolExecutor(max_workers=max(1, a.jobs // 4)) as ex:
        done = list(ex.map(one, pts))
    res, bad = {}, []
    for (c, t, code), name in done:
        dd = REPO / "build/cfed" / name
        for lg in dd.glob("*.log"):
            txt = lg.read_text().lower()
            if any(b in txt for b in BAD):
                bad.append(f"{lg}: {[b for b in BAD if b in txt]}")
        if not (dd / "dacn.json").exists():
            bad.append(f"{name}: no dacn.json | " + " | ".join((logd / f"{name}.log").read_text().splitlines()[-4:]))
            continue
        ki, dn = json.loads((dd / "ki.json").read_text()), json.loads((dd / "dacn.json").read_text())
        res[f"{c} {t:g}"] = dict(corner=c, temp=t, code=code, f0=ki["f0"], I=ki["I"], vg=ki["vg"], K_I=dn["K_I"],
                                 K_vdd=ki["K_vdd"], fm=dn["fm"], L=dn["L"])
    if bad:
        raise Fail("\n".join(bad[:6]))
    # ISF at tt 27 C
    code = ms["typical 27 3.3"]["near"]
    kij = REPO / "build/cfed/sz_typical_t27/ki.json"
    with open(logd / "isf.log", "w") as lg:
        subprocess.run([sys.executable, str(REPO / "sim/pn/cfed_noise.py"), "isf", "--name", "sz_typical_t27",
                        "--code", str(code), "--ki", str(kij), "--m", str(a.m), "--jobs", str(a.jobs)] + sets,
                       stdout=lg, stderr=subprocess.STDOUT, cwd=REPO)
    ij = REPO / "build/cfed/sz_typical_t27/isf.json"
    if not ij.exists() or ij.stat().st_mtime < kij.stat().st_mtime:
        raise Fail("isf.json missing | " + " | ".join((logd / "isf.log").read_text().splitlines()[-4:]))
    isfr = json.loads(ij.read_text())
    out = dict(winner=win, points=res, isf=dict(m=a.m, code=code, fm=isfr["fm"], L=isfr["L"], f0=isfr["A"]["f0"]))
    (a.out / "job3/noise.json").write_text(json.dumps(out, indent=1))
    for k, r in res.items():
        print(f"{k:12s} c{r['code']:2d} f {r['f0']/1e6:.1f} I {r['I']*1e6:.1f} uA  FM 1-10k {r['fm']['1000-10000']['total']/1e3:.2f} "
              f"(ref {r['fm']['1000-10000']['ref']/1e3:.2f} dac {r['fm']['1000-10000']['dac']/1e3:.2f})  1-100k "
              f"{r['fm']['1000-100000']['total']/1e3:.2f} kHz")
    print("isf", json.dumps(out["isf"]["fm"]))


def do_summary(a):
    M = lambda x: f"{x / 1e6:.1f}"
    ln = ["# cfed sizing summary (generated by sim/pn/cfed_sizing.py summary)", ""]
    nl = json.loads((a.out / "job1/null.json").read_text())
    ch = json.loads((a.out / "job1/check.json").read_text())
    win = json.loads((a.out / "job1/winner.json").read_text())
    ln += ["## Job 1", "", "| w | wfu=wff µm | lnw µm | tt code | f27 MHz | tc tt ppm/°C | worst fmin MHz | worst fmax MHz | "
           "range | min fine/step (ss70/tt27/ff0) | tc per corner (code: ppm/°C) |", "|" + "---|" * 11]
    for k, v in ch.items():
        n = nl[k]
        st = " / ".join(f"{s['worst_ratio']:.2f}" for s in v["step"].values())
        tcs = ", ".join(f"{c.replace('typical', 'tt')} {x['code']}: {x['tc']:+.0f}" for c, x in v["tc"].items())
        ln.append(f"| {k} | {0.25 * v['w']:.3f} | {v['lnw']:.3f} | {n['code']} | {M(n['f27'])} | {n['tc']:+.1f} | "
                  f"{M(v['fmin_worst'])} | {M(v['fmax_worst'])} | {'pass' if v['range_ok'] else 'FAIL'} | {st} | {tcs} |")
    ln += ["", f"Winner: w = {win['w']:g}, lnw = {win['lnw']:.4f} ({win['why']})", "",
           "Range per corner (fmin at code 0 vctrl 0 / fmax at code 31 vctrl 3.3, MHz):", "",
           "| w | " + " | ".join(ch[next(iter(ch))]["range"]) + " |", "|" + "---|" * 11]
    for k, v in ch.items():
        ln.append(f"| {k} | " + " | ".join(f"{M(r['fmin'])}/{M(r['fmax'])}{'' if r['ok'] else ' ✗'}" for r in v["range"].values()) + " |")
    ln.append("\nNull search evaluations (lnw: code, tc):\n")
    for k, n in nl.items():
        ln.append(f"- w {k}: " + "; ".join(f"{l}: c{e['code']} {e['tc']:+.1f}" for l, e in n["evals"].items()))
    mp = a.out / "job2/map_summary.json"
    if mp.exists():
        ms = json.loads(mp.read_text())["pvt"]
        ln += ["", "## Job 2 (winner)", "", "| corner T VDD | fmin | fmax | 433.92 code (vctrl 1.65) | codes covering 433.92 | "
               "worst fine/step (code) | monotonic code/vctrl | vg range V | a0 swing range V | vg, swing at the 433.92 code | P mW |",
               "|" + "---|" * 11]
        for k, s in ms.items():
            sw = s["swing_near"][0]
            ln.append(f"| {k} | {M(s['fmin'])} | {M(s['fmax'])} | {s['near']} ({M(s['f_near'])}) | {s['codes433']} | "
                      f"{s['worst_ratio']:.2f} ({s['worst_code']}) | {'y' if s['mono_code'] else 'N'}/{'y' if s['mono_vctrl'] else 'N'} | "
                      f"{s['vg_min']:.2f}–{s['vg_max']:.2f} | {s['amin_min']:.2f}–{s['amax_max']:.2f} | "
                      f"{s['vg_near']:.2f}, {sw[0]:.2f}–{sw[1]:.2f} | {s['p_near'] * 1e3:.3f} |")
        allv = list(ms.values())
        ln += ["", f"Overall: fmin worst {M(max(s['fmin'] for s in allv))} MHz, fmax worst {M(min(s['fmax'] for s in allv))} MHz, "
               f"worst fine/step {min(s['worst_ratio'] for s in allv):.2f}, all monotonic: "
               f"{all(s['mono_code'] and s['mono_vctrl'] for s in allv)}, vg {min(s['vg_min'] for s in allv):.2f}–"
               f"{max(s['vg_max'] for s in allv):.2f} V, a0 {min(s['amin_min'] for s in allv):.2f}–{max(s['amax_max'] for s in allv):.2f} V, "
               f"nan points {sum(s['n_nan'] for s in allv)}"]
    npth = a.out / "job3/noise.json"
    if npth.exists():
        nz = json.loads(npth.read_text())
        ln += ["", "## Job 3 (winner, VDD 3.3, vctrl 1.65)", "", "| corner T | code | f MHz | I_DAC µA | vg V | K_I MHz/µA | "
               "FM 1–10k: total (ref / DAC / vdd) kHz | FM 1–100k: total (ref / DAC / vdd) kHz | L(100k) dBc/Hz |", "|" + "---|" * 9]
        for k, r in nz["points"].items():
            f1, f2 = r["fm"]["1000-10000"], r["fm"]["1000-100000"]
            ln.append(f"| {k} | {r['code']} | {M(r['f0'])} | {r['I'] * 1e6:.1f} | {r['vg']:.2f} | {r['K_I'] / 1e12:.2f} | "
                      f"{f1['total'] / 1e3:.2f} ({f1['ref'] / 1e3:.2f} / {f1['dac'] / 1e3:.2f} / {f1['vdd'] / 1e3:.2f}) | "
                      f"{f2['total'] / 1e3:.2f} ({f2['ref'] / 1e3:.2f} / {f2['dac'] / 1e3:.2f} / {f2['vdd'] / 1e3:.2f}) | "
                      f"{r['L']['100000']['total']:.1f} |")
        wk = max(nz["points"].values(), key=lambda r: r["fm"]["1000-10000"]["total"])
        i = nz["isf"]
        ln += ["", f"Worst 1–10 kHz: {wk['corner']} {wk['temp']:g} °C, {wk['fm']['1000-10000']['total'] / 1e3:.2f} kHz "
               f"(limit 15 kHz: {'pass' if wk['fm']['1000-10000']['total'] < 15e3 else 'FAIL'})",
               f"ISF (tt 27 °C, code {i['code']}, m = {i['m']}, f0 {M(i['f0'])} MHz): inverter FM "
               + "; ".join(f"{b}: " + ", ".join(f"{k} {v / 1e3:.2f} kHz" for k, v in fm.items()) for b, fm in i["fm"].items())
               + "; L " + "; ".join(f"{b}: " + ", ".join(f"{k} {v:.1f}" for k, v in L.items()) for b, L in i["L"].items())]
    (a.out / "summary.md").write_text("\n".join(ln) + "\n")
    print("\n".join(ln))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["null", "check", "pick", "map", "noise", "summary"])
    ap.add_argument("--out", default=str(REPO / "build/cfed_sizing"))
    ap.add_argument("--jobs", type=int, default=20)
    ap.add_argument("--ws", default=",".join(f"{w:g}" for w in WS))
    ap.add_argument("--iters", type=int, default=6)
    ap.add_argument("--m", type=int, default=80)
    a = ap.parse_args()
    a.out = Path(a.out).resolve()
    (a.out / "job1").mkdir(parents=True, exist_ok=True)
    try:
        dict(null=do_null, check=do_check, pick=do_pick, map=do_map, noise=do_noise, summary=do_summary)[a.mode](a)
    except Fail as e:
        print(f"FAIL {a.mode}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
