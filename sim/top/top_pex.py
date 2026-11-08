#!/usr/bin/env python3
"""The whole extracted VCO top level (layout/vco_top.gds -> layout/pex/vco_top_<c|rcx>.spice) in one deck.

  python3 sim/top/top_pex.py run [--jobs 4] [--only NAME,...]    # ring runs (code 9, vctrl 1.65 V) -> build/top_pex/
  python3 sim/top/top_pex.py startup [--tstop 14e-6]           # power-on, tt: VDD = VDD_LS ramp 0 -> 3.3 V in 10 us
  python3 sim/top/top_pex.py summary                            # table -> sim/top/results.md (+ results.json)

Deck: Xtop VDD VDD_LS VSS vctrl bit0-4 bitb0-4 ck a0 vbn vg vco_top (the extracted top: core + reference + filter +
level shifter / divider + the VDD_LS decap, all from layout), VDD (vdd) and VDD_LS (vls) separate 3.3 V sources,
ck loaded as in sim/lsdiv/lsdiv.py ls_x(): a 20 fF wire + one gf180mcu_fd_sc_mcu7t5v0__dffq_1 clock pin (on its own
supply vff). 27 C, code 9, vctrl 1.65 V. f(a0) is measured at mid-swing over the last 40 % of tstop; LS duty on the
extraction's monitor label ls (v(xtop.ls), VDD_LS / 2), the /4 ratio from v(ck); power = 3.3 V x the mean supply
current over the same window. .ic: a0..a4 alternating (vco_bias) on a0 only (a1..a4 are not ports), vbn and vbnf at
the schematic reference's value per corner (initial guesses for the operating point; no uic).
Imports sim/lsdiv/lsdiv.py read-only for the measurement helpers. Does not modify sim/lsdiv or sim/vco.
"""
import argparse, json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/lsdiv"))
sys.path.insert(0, str(REPO / "tools"))
import lsdiv as LD  # noqa: E402  (read-only: freq, duty, edges, STD)
from rawread import read_raw  # noqa: E402

OUT = REPO / "build/top_pex"
PEX = dict(c=REPO / "layout/pex/vco_top_c.spice", rcx=REPO / "layout/pex/vco_top_rcx.spice")
CODE, VCTRL, VDD = 9, 1.65, 3.3
VBN0 = dict(typical=1.232, ss=1.384, ff=1.083)        # schematic reference vbn at 27 C (sim/ref/results.md)
SAVE = "v(a0) v(vg) v(ck) v(vbn) v(xtop.vbnf) v(xtop.ls) v(xtop.q1) i(vdd) i(vls)"
# block-level references at code 9, vctrl 1.65 V, 27 C
REFS = dict(
    core_ref=dict(typical=425.61e6, ss=389.50e6, ff=470.22e6),      # extracted core + extracted reference, no LS (sim/ref/results.md)
    core_ls=dict(typical=417.887743e6, ss=382.668104e6, ff=461.415963e6),  # extracted core rcx + extracted LS (remap.csv)
    core_ls_duty=dict(typical=0.47949, ss=0.49760, ff=0.46481),
    core_ls_p=dict(typical=0.70274e-3, ss=0.57769e-3, ff=0.89051e-3),
    ref_i=dict(typical=70.21e-6, ss=73.77e-6, ff=67.02e-6))         # I(vddr) of the extracted reference


def hdr(corner):
    return (".include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice\n"
            f".lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}\n"
            ".lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical\n"
            f".include {LD.STD}\n")


def circuit(pex, corner, supplies):
    bits = "".join(f"vbit{i} bit{i} 0 {VDD if (CODE >> i) & 1 else 0}\nvbitb{i} bitb{i} 0 {0 if (CODE >> i) & 1 else VDD}\n"
                   for i in range(5))
    return f"""{hdr(corner)}{supplies}vctrl vctrl 0 {VCTRL}
{bits}Xtop vdd vls 0 vctrl {' '.join(f'bit{i}' for i in range(5))} {' '.join(f'bitb{i}' for i in range(5))} ck a0 vbn vg vco_top
.include {PEX[pex]}
Cwire ck 0 20f
XFF 0 ck ffq vff vff 0 0 gf180mcu_fd_sc_mcu7t5v0__dffq_1
"""


def ring_deck(pex, corner, temp=27, tstop=1.2e-6):
    v0 = VBN0[corner]
    sup = f"vdd vdd 0 {VDD}\nvls vls 0 {VDD}\nvff vff 0 {VDD}\n"
    return f"""* top_pex {pex} {corner} {temp} code {CODE} vctrl {VCTRL}
{circuit(pex, corner, sup)}.ic v(a0)=0 v(vbn)={v0} v(xtop.vbnf)={v0}
.control
option temp={temp}
save {SAVE}
tran 5p {tstop} {0.6 * tstop} 5p
set filetype=binary
write out.raw {SAVE}
quit
.endc
.end
"""


def startup_deck(pex, corner, tstop, temp=27, tramp=10e-6):
    sup = (f"vdd vdd 0 PWL(0 0 {tramp} {VDD})\nvls vls 0 PWL(0 0 {tramp} {VDD})\nvff vff 0 PWL(0 0 {tramp} {VDD})\n")
    save = "v(a0) v(ck) v(vg) v(vbn) v(xtop.vbnf) v(vdd)"
    return f"""* top_pex startup {pex} {corner} {temp}: all nodes 0 V at t = 0 (uic), supplies ramp in {tramp}
{circuit(pex, corner, sup)}.control
option temp={temp}
save {save}
tran 20p {tstop} 0 20p uic
set filetype=binary
write out.raw {save}
quit
.endc
.end
"""


def run1(name, text):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / ".spiceinit").write_text("set ng_nomodcheck\nset num_threads=1\noption noinit\n")
    (d / "deck.cir").write_text(text)
    (d / "out.raw").unlink(missing_ok=True)
    t = time.time()
    subprocess.run(["bash", "-c", f"cd {d} && ngspice -b deck.cir > deck.log 2>&1"], check=False)
    (d / "runtime.txt").write_text(f"{time.time() - t:.0f}\n")
    return name, time.time() - t


def log_flags(d):
    log = (d / "deck.log").read_text(errors="replace") if (d / "deck.log").exists() else ""
    return [w for w in ("singular", "timestep too small", "Transient op started", "error") if w.lower() in log.lower()]


def mean(t, y):
    return float(np.trapezoid(y, t) / (t[-1] - t[0]))


def analyse_ring(name):
    d = OUT / name
    flags = log_flags(d)
    try:
        pl = read_raw(d / "out.raw")[0]["vars"]
    except Exception as e:  # noqa: BLE001
        return dict(name=name, error=str(e), flags=flags)
    t, a0, ck, ls = pl["time"], pl["v(a0)"], pl["v(ck)"], pl["v(xtop.ls)"]
    amin, amax = float(a0.min()), float(a0.max())
    fa, _ = LD.freq(t, a0, (amin + amax) / 2)
    h = (t[0] + t[-1]) / 2
    fa1, _ = LD.freq(t[t < h], a0[t < h], (amin + amax) / 2)
    fa2, _ = LD.freq(t[t >= h], a0[t >= h], (amin + amax) / 2)
    fc, _ = LD.freq(t, ck, VDD / 2)
    fl, _ = LD.freq(t, ls, VDD / 2)
    tr, tf = LD.edges(t, ls, VDD)
    return dict(name=name, f_a0=fa, f_drift=fa2 / fa1 - 1, a0_min=amin, a0_max=amax, f_ls=fl, f_ck=fc, div_ratio=fa / fc,
                ls_duty=LD.duty(t, ls, VDD / 2), ls_tr=tr, ls_tf=tf, ck_duty=LD.duty(t, ck, VDD / 2),
                ck_min=float(ck.min()), ck_max=float(ck.max()), vg=mean(t, pl["v(vg)"]), vbn=mean(t, pl["v(vbn)"]),
                vbnf=mean(t, pl["v(xtop.vbnf)"]), p_vdd=-mean(t, pl["i(vdd)"]) * VDD, p_vls=-mean(t, pl["i(vls)"]) * VDD,
                runtime_s=float((d / "runtime.txt").read_text()) if (d / "runtime.txt").exists() else None, flags=flags)


def analyse_startup(name):
    d = OUT / name
    flags = log_flags(d)
    try:
        pl = read_raw(d / "out.raw")[0]["vars"]
    except Exception as e:  # noqa: BLE001
        return dict(name=name, error=str(e), flags=flags)
    t, a0, ck, vf = pl["time"], pl["v(a0)"], pl["v(ck)"], pl["v(xtop.vbnf)"]
    out = dict(name=name, flags=flags, t_end=float(t[-1]), vbnf_end=float(vf[-1]), vbn_end=float(pl["v(vbn)"][-1]))
    # f(a0) and f(ck) in 1 us windows (a0 at the window's mid-swing, ck at VDD/2 of the window's supply)
    win = []
    for t0 in np.arange(0, t[-1] - 0.999e-6, 1e-6):
        m = (t >= t0) & (t < t0 + 1e-6)
        if m.sum() < 10:
            continue
        a, c, vd = a0[m], ck[m], float(pl["v(vdd)"][m].mean())
        fa = LD.freq(t[m], a, (a.min() + a.max()) / 2)[0] if a.max() - a.min() > 0.3 else float("nan")
        fc = LD.freq(t[m], c, vd / 2)[0] if c.max() - c.min() > 0.5 * vd else float("nan")
        win.append(dict(t0=float(t0), vdd=vd, f_a0=fa, f_ck=fc, a0_swing=float(a.max() - a.min()),
                        vbnf=float(vf[m].mean())))
    out["windows"] = win
    return out


def ring_cases(which="all"):
    cs = [("c", "typical"), ("c", "ss"), ("c", "ff"), ("rcx", "typical")]
    return cs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["run", "startup", "summary"])
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", default="")
    ap.add_argument("--tstop", type=float, default=1.2e-6)
    ap.add_argument("--pex", default="c")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.what == "run":
        jobs = {f"ring_{p}_{c}": ring_deck(p, c, tstop=a.tstop) for p, c in ring_cases()}
        if a.only:
            jobs = {k: v for k, v in jobs.items() if k in a.only.split(",")}
        with ThreadPoolExecutor(min(a.jobs, 16)) as ex:
            for name, dt in ex.map(lambda kv: run1(*kv), jobs.items()):
                print(f"{name}: {dt:.0f} s", flush=True)
                print(json.dumps(analyse_ring(name)), flush=True)
    elif a.what == "startup":
        name = f"startup_{a.pex}_typical"
        n, dt = run1(name, startup_deck(a.pex, "typical", a.tstop))
        print(f"{n}: {dt:.0f} s")
        print(json.dumps(analyse_startup(name), indent=1))
    else:
        res = {}
        for d in sorted(OUT.glob("ring_*")):
            res[d.name] = analyse_ring(d.name)
        for d in sorted(OUT.glob("startup_*")):
            res[d.name] = analyse_startup(d.name)
        (REPO / "sim/top/results.json").write_text(json.dumps(res, indent=1))
        write_md(res)


def write_md(res):
    cn = dict(typical="tt", ss="ss", ff="ff")
    L = ["# Extracted vco_top: results", "",
         "Generated by `python3 sim/top/top_pex.py summary` from `build/top_pex/`. Settings: 27 °C, code 9, vctrl 1.65 V,",
         "VDD = VDD_LS = 3.3 V, 1.2 µs, measured over the last 40 %. Block-level references: extracted core + extracted",
         "reference without the level shifter (`sim/ref/results.md`); extracted core (rcx) + extracted level shifter",
         "with the schematic reference (`sim/lsdiv/results/remap.csv`).", "",
         "| Netlist, corner | f(a0) (MHz) | vs core + ref | vs core + LS | f(a0)/f(ck) | LS duty (block) | ck duty | P(VDD) (mW) | P(VDD_LS) (mW) (block) | vbnf (V) | log flags |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in res.items():
        if not k.startswith("ring_") or "error" in r:
            if k.startswith("ring_"):
                L.append(f"| {k} | error: {r.get('error')} |")
            continue
        _, pex, c = k.split("_", 2)
        L.append(f"| {pex}, {cn[c]} | {r['f_a0'] / 1e6:.2f} | {(r['f_a0'] / REFS['core_ref'][c] - 1) * 100:+.2f} % "
                 f"| {(r['f_a0'] / REFS['core_ls'][c] - 1) * 100:+.2f} % | {r['div_ratio']:.4f} "
                 f"| {r['ls_duty'] * 100:.1f} % ({REFS['core_ls_duty'][c] * 100:.1f} %) | {r['ck_duty'] * 100:.1f} % "
                 f"| {r['p_vdd'] * 1e3:.3f} | {r['p_vls'] * 1e3:.3f} ({REFS['core_ls_p'][c] * 1e3:.3f}) | {r['vbnf']:.4f} "
                 f"| {', '.join(r['flags']) or 'none'} |")
    for k, r in res.items():
        if k.startswith("startup_") and "windows" in r:
            L += ["", f"## {k}", "", "| window start (µs) | VDD (V) | a0 swing (V) | f(a0) (MHz) | f(ck) (MHz) | vbnf (V) |",
                  "|---|---|---|---|---|---|"]
            for w in r["windows"]:
                L.append(f"| {w['t0'] * 1e6:.0f} | {w['vdd']:.2f} | {w['a0_swing']:.2f} | {w['f_a0'] / 1e6:.1f} | "
                         f"{w['f_ck'] / 1e6:.1f} | {w['vbnf']:.3f} |")
            L.append(f"\nlog flags: {', '.join(r['flags']) or 'none'}")
    (REPO / "sim/top/results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
