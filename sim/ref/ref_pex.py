#!/usr/bin/env python3
"""The VCO with the extracted constant-gm reference (layout/cgm_ref.gds) against the schematic reference.

  python3 sim/ref/ref_pex.py run [--jobs 10] [--only NAME,...]   # ring runs (code 9, vctrl 1.65 V) -> build/ref_pex/
  python3 sim/ref/ref_pex.py startup [--jobs 4]                  # power-on of the reference + filter alone
  python3 sim/ref/ref_pex.py summary                             # tables -> sim/ref/results.md (+ results.json)

Circuit: sim/vco/vco_bias.py netlist() with the chosen settings (sim/lsdiv/lsdiv.py WINNER + CFED: topo cfed,
lnw 5.023, nsn 14, RF ppolyf_u_1k 1 MOhm, CF nfet 10 x 49.14/10), three configurations:
  sch      schematic core + schematic reference
  xcore    extracted core (layout/pex/ring_core_v3_w30chk_rcx.spice) + schematic reference (as sim/lsdiv ring())
  xref     extracted core + extracted reference (layout/pex/cgm_ref_rcx.spice, --ref c: cgm_ref_c.spice): the
           reference elements MN*, MP*, MS*, XRB*, XRF, XCF and Rvbn are replaced by Xref
The reference's VDD (MP1, MP2, MS1 sources/bulks) is a separate 3.3 V source vddr in every configuration, so
I(vddr) = I(MP1) + I(MP2) + I(MS1) is measured the same way on schematic and layout; the schematic configurations
also report I(MN1) (= Iref) through a 0 V source. f(a0) is measured at mid-swing (the ring swings vg..VDD) over the
last 40 % of tstop; vbn / vbnf / vg are window means.
Does not modify sim/vco or sim/lsdiv (imports them read-only).
"""
import argparse, json, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/vco"))
sys.path.insert(0, str(REPO / "tools"))
import vco_bias as vb  # noqa: E402
from rawread import read_raw  # noqa: E402

OSIC = str(REPO / "tools/osic-mac")
OUT = REPO / "build/ref_pex"
CORE_PEX = REPO / "layout/pex/ring_core_v3_w30chk_rcx.spice"
REF_PEX = dict(rcx=REPO / "layout/pex/cgm_ref_rcx.spice", c=REPO / "layout/pex/cgm_ref_c.spice")
WINNER = dict(rideal=0, lnp=100.0, lnw=5.023, nsn=14, wpm=56.0, lpm=14.0, mr=4.0)       # = sim/lsdiv/lsdiv.py
CFED = dict(topo="cfed", kc=0.75, k=6, cvg=3e-12, cw=3e-15, ka=16.0, wfu=0.30, wff=0.30, rf=1e6, cf=20e-12)
CORE = re.compile(r"^(X(P|N|FC|FFC|TN|TP|TD)\S*|Cvg|Cw\d+)\s", re.I)
REF = re.compile(r"^(XMN\S*|XMP\S*|XMS\S*|XRB\S*|XRF|XCF|Rvbn)\s", re.I)
CODE, VCTRL = 9, 1.65


def params():
    return dict(vb.P, **WINNER, **CFED)


def body(cfg, ref="rcx"):
    s, ics = vb.netlist(params())
    lines = s.splitlines()
    if cfg in ("xcore", "xref"):
        lines = [ln for ln in lines if not CORE.match(ln)]
        lines.append("Xcore vdd 0 vbnf vctrl " + " ".join(f"bit{b}" for b in range(5)) + " "
                     + " ".join(f"bitb{b}" for b in range(5)) + " vg a0 a1 a2 a3 a4 ring_core")
        lines.append(f".include {CORE_PEX}")
    if cfg == "xref":
        lines = [ln for ln in lines if not REF.match(ln)]
        lines.append("Xref vddr 0 vbn vbnf vctrl cgm_ref")
        lines.append(f".include {REF_PEX[ref]}")
    else:   # reference supply on vddr; Iref through vir (MN1 drain)
        lines = [re.sub(r"^(XM(P1|P2|S1) \S+ \S+) vdd vdd ", r"\1 vddr vddr ", ln) for ln in lines]
        lines = [ln.replace("XMN1 n1 n1 ", "XMN1 n1i n1 ", 1) for ln in lines]
        lines.append("vir n1 n1i 0")
    txt = "\n".join(lines) + "\n"
    assert txt.count(" vddr vddr ") == (3 if cfg != "xref" else 0) and "vddr" in txt
    return txt, ics


def hdr(corner):
    return (".include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice\n"
            f".lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}\n"
            ".lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical\n")


def ring_deck(cfg, corner, temp, tstop=1.2e-6, ref="rcx"):
    b, ics = body(cfg, ref)
    bits = "".join(f"vbit{i} bit{i} 0 {3.3 if (CODE >> i) & 1 else 0}\nvbitb{i} bitb{i} 0 {0 if (CODE >> i) & 1 else 3.3}\n"
                   for i in range(5))
    save = "v(a0) v(vg) v(vbn) v(vbnf) i(vddr)" + ("" if cfg == "xref" else " i(vir)")
    return f"""* ref_pex {cfg} {corner} {temp} code {CODE} vctrl {VCTRL}
{hdr(corner)}vdd vdd 0 3.3
vddr vddr 0 3.3
vctrl vctrl 0 {VCTRL}
{bits}{b}.ic {ics}
.control
option temp={temp}
save {save}
tran 5p {tstop} {0.6 * tstop} 5p
set filetype=binary
write out.raw {save}
quit
.endc
.end
"""


def startup_deck(cfg, corner, temp, tramp=10e-6, tstop=600e-6, ref="rcx"):
    """Reference + RC filter alone (no core: the DAC gates load vbnf with a few pF at most, 20 pF CF dominates),
    every node at 0 V at t = 0 (uic), VDD and vddr ramped 0 -> 3.3 V in tramp."""
    b, _ = body(cfg, ref)
    b = "".join(ln + "\n" for ln in b.splitlines() if not ln.startswith(("Xcore", ".include")) or "cgm_ref" in ln)
    # drop the schematic core, keep the reference / filter (cfg sch or xref)
    keep = []
    for ln in b.splitlines():
        if CORE.match(ln) or re.match(r"^X(TN|TP|TD)", ln):
            continue
        keep.append(ln)
    b = "\n".join(keep) + "\n"
    save = "v(vbn) v(vbnf) i(vddr)"
    return f"""* ref_pex startup {cfg} {corner} {temp}
{hdr(corner)}vdd vdd 0 PWL(0 0 {tramp} 3.3)
vddr vddr 0 PWL(0 0 {tramp} 3.3)
vctrl vctrl 0 {VCTRL}
{b}.control
option temp={temp}
save {save}
tran 10n {tstop} 0 20n uic
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
    subprocess.run([OSIC, "bash", "-c", f"cd {d} && ngspice -b deck.cir > deck.log 2>&1"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return name, time.time() - t


def freq(t, v, th):
    a, b = v[:-1] - th, v[1:] - th
    i = np.where((a < 0) & (b >= 0))[0]
    r = t[i] + (th - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i])
    return (len(r) - 1) / (r[-1] - r[0]) if len(r) > 2 else float("nan")


def mean(t, y):
    return float(np.trapezoid(y, t) / (t[-1] - t[0]))


def log_flags(d):
    log = (d / "deck.log").read_text(errors="replace") if (d / "deck.log").exists() else ""
    return [w for w in ("singular", "timestep too small", "Transient op started", "error") if w.lower() in log.lower()]


def analyse_ring(name):
    d = OUT / name
    flags = log_flags(d)
    try:
        pl = read_raw(d / "out.raw")[0]["vars"]
    except Exception as e:  # noqa: BLE001
        return dict(name=name, error=str(e), flags=flags)
    t, a0 = pl["time"], pl["v(a0)"]
    amin, amax = float(a0.min()), float(a0.max())
    r = dict(name=name, f=freq(t, a0, (amin + amax) / 2), a0_min=amin, a0_max=amax, vbn=mean(t, pl["v(vbn)"]),
             vbnf=mean(t, pl["v(vbnf)"]), vg=mean(t, pl["v(vg)"]), i_ref_supply=-mean(t, pl["i(vddr)"]), flags=flags)
    if "i(vir)" in pl:
        r["i_mn1"] = mean(t, pl["i(vir)"])
    return r


def analyse_startup(name):
    d = OUT / name
    flags = log_flags(d)
    try:
        pl = read_raw(d / "out.raw")[0]["vars"]
    except Exception as e:  # noqa: BLE001
        return dict(name=name, error=str(e), flags=flags)
    t, vf, vn = pl["time"], pl["v(vbnf)"], pl["v(vbn)"]
    fin = float(vf[-1])
    out = np.where(np.abs(vf - fin) > 0.01 * fin)[0]
    t1 = float(t[out[-1] + 1]) if len(out) and out[-1] + 1 < len(t) else float("nan")
    tail = t > t[-1] * 0.9
    return dict(name=name, vbnf_end=fin, vbn_end=float(vn[-1]), t_settle_1pct=t1,
                vbnf_drift_last10pct=float(vf[tail].max() - vf[tail].min()), i_end=-float(pl["i(vddr)"][-1]),
                flags=flags)


def ring_cases():
    cs = []
    for cfg in ("sch", "xcore", "xref"):
        for temp in (20, 27, 35):
            cs.append((cfg, "typical", temp))
        if cfg != "sch":
            cs += [(cfg, "ss", 27), (cfg, "ff", 27)]
    return cs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["run", "startup", "summary"])
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--only", default="")
    ap.add_argument("--ref", default="rcx", choices=["rcx", "c"])
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.what in ("run", "startup"):
        if a.what == "run":
            decks = {f"{cfg}_{c}_{t}" + ("" if a.ref == "rcx" else "_c"): ring_deck(cfg, c, t, ref=a.ref)
                     for cfg, c, t in ring_cases()}
        else:
            decks = {f"su_{cfg}_{c}_{t}": startup_deck(cfg, c, t, ref=a.ref)
                     for cfg in ("sch", "xref") for c, t in (("typical", 27), ("ss", 27), ("ff", 27))}
        if a.only:
            decks = {k: v for k, v in decks.items() if k in a.only.split(",")}
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for n, dt in ex.map(lambda kv: run1(*kv), decks.items()):
                print(f"{n}: {dt:.0f} s", flush=True)
        res = [analyse_ring(n) if a.what == "run" else analyse_startup(n) for n in decks]
        f = OUT / f"{a.what}.json"
        old = {r["name"]: r for r in json.loads(f.read_text())} if f.exists() else {}
        old.update({r["name"]: r for r in res})
        f.write_text(json.dumps(list(old.values()), indent=1))
        for r in res:
            print(json.dumps(r))
        print(f"total {time.time() - t0:.0f} s")
    else:
        summary()


def summary():
    # re-analyse every ring run directory (several runners may have written run.json)
    names = sorted(d.name for d in OUT.iterdir() if d.is_dir() and not d.name.startswith("su_"))
    R = {n: analyse_ring(n) for n in names}
    (OUT / "run.json").write_text(json.dumps(list(R.values()), indent=1))
    md = ["# cgm_ref: extracted reference vs schematic (code 9, vctrl 1.65 V, VDD 3.3 V)", "",
          "| config | corner | T (°C) | vbn (V) | vbnf (V) | I(MN1) (µA) | I(vddr) (µA) | vg (V) | f(a0) (MHz) | log flags |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in R.items():
        if "error" in r:
            md.append(f"| {n} | error {r['error'][:60]} |")
            continue
        cfg, c, t = n.split("_")[:3]
        cfg += " (ref C-only)" if n.endswith("_c") else (" (ref RC)" if cfg == "xref" else "")
        im = f"{r['i_mn1'] * 1e6:.3f}" if "i_mn1" in r else "-"
        md.append(f"| {cfg} | {c} | {t} | {r['vbn']:.4f} | {r['vbnf']:.4f} | {im} | {r['i_ref_supply'] * 1e6:.3f} | "
                  f"{r['vg']:.4f} | {r['f'] / 1e6:.2f} | {', '.join(r['flags'])} |")
    md += ["", "Tempco of f (tt, 20 → 35 °C, relative to 27 °C):", ""]
    for cfg, suf in (("sch", ""), ("xcore", ""), ("xref", "_c")):
        try:
            f20, f27, f35 = (R[f"{cfg}_typical_{t}{suf}"]["f"] for t in (20, 27, 35))
            md.append(f"- {cfg}: {(f35 - f20) / f27 / 15 * 1e6:+.0f} ppm/°C (f20 {f20 / 1e6:.3f}, f27 {f27 / 1e6:.3f}, "
                      f"f35 {f35 / 1e6:.3f} MHz)")
        except KeyError:
            pass
    sj = OUT / "startup.json"
    if sj.exists():
        md += ["", "Power-on (reference + filter alone, VDD ramp 10 µs, all nodes 0 V at t = 0):", "",
               "| run | vbn end (V) | vbnf end (V) | t to within 1 % (µs) | vbnf drift last 10 % (mV) | I(vddr) end (µA) | flags |",
               "|---|---|---|---|---|---|---|"]
        for r in json.loads(sj.read_text()):
            if "error" in r:
                md.append(f"| {r['name']} | error |")
                continue
            md.append(f"| {r['name']} | {r['vbn_end']:.4f} | {r['vbnf_end']:.4f} | {r['t_settle_1pct'] * 1e6:.1f} | "
                      f"{r['vbnf_drift_last10pct'] * 1e3:.2f} | {r['i_end'] * 1e6:.3f} | {', '.join(r['flags'])} |")
    (REPO / "sim/ref/results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
