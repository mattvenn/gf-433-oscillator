#!/usr/bin/env python3
"""rms FM and phase noise of the cgm ring from its constant-gm bias, for a given reference sizing.

The const-gm reference (MN1, MN2 = kb x MN1, MP1/MP2) is scaled by s: W and L of those four devices x s
(W/L, hence the current, unchanged). The flicker density of the reference falls roughly as 1/s.

  1. quick stage A (sim/pn/isf.py stage_a on variant cgmf + sizing): f0, K_vbn (probe in series with vbn, so it
     includes the vbp tracking through the master leg), K_vdd; plus K_vbp from a probe in series with the head gates
  2. dense .noise (dec 50, 100 Hz .. 1 GHz) of
       - the filtered load-gate node vbnf (isf.bias_noise_deck, rf = 1 Mohm, cf = 20 pF), reference only
       - vbp with vbnf held by a noiseless source at its DC value: the master leg + PMOS diode's own noise only
         (the part of vbp that follows vbnf is already in K_vbn, so this avoids counting it twice)
  3. device (head + foot) and vdd terms from a stored ISF result.json (default: cgm tt 27 C), interpolated
     power-law between its 10k/100k/1M/10M points and extrapolated below 10 kHz with the 10k-100k slope
  4. S_f(f) = K_vbn^2 S_vbnf + K_vbp^2 S_vbp + f^2 S_phi,dev+vdd   (S_phi = 2 L, so S_f = 2 f^2 10^(L/10))
     rms FM = sqrt(integral of S_f) over 1-10 kHz and 1-100 kHz, on the dense .noise grid.

Usage (repo root):
  python3 sim/pn/bias_fm.py --s 4 [--set lnw=5.1] [--corner typical] [--temp 27] [--dev <result.json>] [--out build/bfm]
  python3 sim/pn/bias_fm.py --variant cgmq --corner ss --temp 0 --dev build/pnq/cgmq_ss_t0/result.json   # Job 2
Writes <out>/s<s>_<corner>_t<temp>/bias_fm.json (+ decks, logs, noise spectra).
"""
import argparse, json, math, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/pn"))
sys.path.insert(0, str(REPO / "sim/vco"))
import isf, vco_bias  # noqa: E402

DEV_DEFAULT = REPO / "sim/pn/results/2026-11-07/cgm_typical_t27/result.json"
SWEEP = "dec 50 100 1G"
BANDS = ((1e3, 1e4), (1e3, 1e5))
CF_AREA = 68 * 68            # um^2, 20 pF MOS cap (estimate from docs/pn_results.md)


def scaled(s, extra=(), variant="cgmf"):
    """vco_bias parameters of `variant` (cgmf by default) with the reference scaled by s, plus K=V overrides."""
    st = dict(isf.VARIANTS[variant]["set"])
    P = vco_bias.P
    st.update({k: st.get(k, P[k]) * s for k in ("w1", "l1", "wpm", "lpm")})
    for kv in extra:
        k, x = kv.split("=", 1)
        st[k] = type(P[k])(float(x))
    return st


def ref_area(p):
    """Device area (um^2): reference FETs incl. start-up (sum W*L*m), resistors, RC filter."""
    fets = (p["w1"] * p["l1"] * (1 + p["kb"]) * p.get("nsn", 1) ** 2 + 2 * p["wpm"] * p["lpm"]
            + 0.5 * 10.0 + 2.0 * 0.28 + 1.0 * 0.28)
    rbias = (p["rw"] * (p["lnw"] + p["lnp"])) if not p["rideal"] else 0.0
    rfil = p["rfw"] * vco_bias.rf_length(p) if p["rf"] > 0 else 0.0
    return dict(fets=fets, rbias=rbias, rf=rfil, cf=CF_AREA if p["cf"] > 0 else 0.0,
                total=fets + rbias + rfil + (CF_AREA if p["cf"] > 0 else 0.0))


def heads_on_probe(net):
    """Head gates on vbph, with Vbpp (0 V) from vbp: a probe for df/dvbp."""
    net = re.sub(r"^(XH\d+ h\d+) vbp ", r"\1 vbph ", net, flags=re.M)
    return net + "Vbpp vbp vbph 0\n"


def interp_dev(dev, f):
    """Power-law interpolation of a stored L term {freq: dBc/Hz} -> S_phi (rad^2/Hz)."""
    xs = sorted(dev)
    lx = [math.log(x) for x in xs]
    ly = [math.log(2 * 10 ** (dev[x] / 10)) for x in xs]
    t = math.log(f)
    i = 1 if t < lx[1] else len(xs) - 1
    for k in range(1, len(xs)):
        if t <= lx[k]:
            i = k
            break
    return math.exp(ly[i - 1] + (ly[i] - ly[i - 1]) * (t - lx[i - 1]) / (lx[i] - lx[i - 1]))


def integ(fs, ys, lo, hi):
    """Trapezoid of y df over [lo, hi] on a log grid (done in ln f: y*f dlnf)."""
    pts = [(f, y) for f, y in zip(fs, ys) if lo * (1 - 1e-9) <= f <= hi * (1 + 1e-9)]
    tot = 0.0
    for (f0, y0), (f1, y1) in zip(pts, pts[1:]):
        tot += 0.5 * (y0 * f0 + y1 * f1) * math.log(f1 / f0)
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--s", type=float, default=1.0, help="reference scale (W and L of MN1, MN2, MP1, MP2)")
    ap.add_argument("--set", action="append", default=[], metavar="K=V")
    ap.add_argument("--corner", default="typical")
    ap.add_argument("--temp", type=float, default=27)
    ap.add_argument("--dev", default=str(DEV_DEFAULT), help="ISF result.json for the device and vdd terms")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", default="build/bfm")
    ap.add_argument("--tag", default="")
    ap.add_argument("--variant", default="cgmf", help="isf.py variant giving the operating point and base sizing")
    a = ap.parse_args()
    st = scaled(a.s, a.set, a.variant)
    v = dict(isf.VARIANTS[a.variant], set=st, ic_ref=True)   # reference starts at its DC point (large s)
    wd = REPO / a.out / f"s{a.s:g}{a.tag}_{a.corner}_t{a.temp:g}"
    net, ic, p, A = isf.stage_a(v, a.corner, a.temp, wd, a.jobs)
    # K_vbp, Iref (MN1 branch) and the noise decks
    netp = heads_on_probe(net)
    op = isf.ngspice(wd, {"op_iref": f"* iref\n{net}\n.control\noption temp={a.temp}\nop\nprint i(vir)\nprint v(vbn)\n"
                                      f"quit\n.endc\n.end\n"}, 1)["op_iref"]
    iref = abs(float(re.search(r"^i\(vir\)\s*=\s*(\S+)", op, re.M).group(1)))
    vbn_dc = float(re.search(r"^v\(vbn\)\s*=\s*(\S+)", op, re.M).group(1))
    decks = {"ref_vbp0": isf.no_uic(isf.ref_deck(netp, ic, v, a.temp, 140), v),
             "ref_vbp": isf.no_uic(isf.ref_deck(netp, ic, v, a.temp, 140, "alter vbpp 0.005\n"), v),
             "noise_vbnf": isf.bias_noise_deck(p, a.corner, a.temp, SWEEP, "noise_vbnf.txt")}
    # vbp noise of the master leg alone: vbnf held by a noiseless source at its DC value (= vbn at DC)
    own = lambda body: (re.sub(r"^XRF .*\n|^CF .*\n", "", body, flags=re.M) + f"Vfix vbnf 0 {vbn_dc:.6f}\n")
    decks["noise_vbp"] = isf.bias_noise_deck(p, a.corner, a.temp, SWEEP, "noise_vbp.txt", node="vbp", edit=own)
    logs = isf.ngspice(wd, decks, a.jobs)
    fper = {k: 10 / (isf.grab(logs[k], "t10") - isf.grab(logs[k], "t0")) for k in ("ref_vbp0", "ref_vbp")}
    K_vbp = (fper["ref_vbp"] - fper["ref_vbp0"]) / 0.005
    fb, sb = isf.read_psd(wd / "noise_vbnf.txt")
    fp, sp = isf.read_psd(wd / "noise_vbp.txt")
    assert fb == fp
    dev = json.loads(Path(a.dev).read_text())
    Ld = {k: {float(f): r[k] for f, r in dev["L"].items()} for k in ("dev_head", "dev_foot", "vdd")}
    Kb = A["K_bias"]
    terms = {"vbnf": [Kb ** 2 * x for x in sb],
             "vbp": [K_vbp ** 2 * x for x in sp]}
    for k, d in Ld.items():
        terms[k] = [f * f * interp_dev(d, f) for f in fb]
    tot = [sum(t[i] for t in terms.values()) for i in range(len(fb))]
    fm = {}
    for lo, hi in BANDS:
        key = f"{lo:g}-{hi:g}"
        fm[key] = dict(total=math.sqrt(integ(fb, tot, lo, hi)),
                       **{k: math.sqrt(integ(fb, t, lo, hi)) for k, t in terms.items()})
    Lout = {}
    for f0 in (1e4, 1e5, 1e6, 1e7):
        i = min(range(len(fb)), key=lambda j: abs(math.log(fb[j] / f0)))
        Lout[f"{f0:g}"] = dict(L=10 * math.log10(tot[i] / fb[i] ** 2 / 2),
                               **{k: 10 * math.log10(t[i] / fb[i] ** 2 / 2) for k, t in terms.items()})
    out = dict(variant=a.variant, code=v["code"], s=a.s, set=st, corner=a.corner, temp=a.temp, dev=str(Path(a.dev).resolve().relative_to(REPO)),
               f0=A["f0"], P=A["P"], K_vbn=Kb, K_vbp=K_vbp, K_vdd=A["K_vdd"], vbn=vbn_dc, vbn_tran=A["vbn"], vbnf=A["vbnf"],
               vbp=A["vbp"], vbnf_ic_corr=A["vbnf_ic_corr"], iref=iref, area=ref_area(p),
               vbnf_noise_1k=math.sqrt(isf.interp_log(fb, sb, 1e3)), vbp_noise_1k=math.sqrt(isf.interp_log(fp, sp, 1e3)),
               fm=fm, L=Lout)
    (wd / "bias_fm.json").write_text(json.dumps(out, indent=1))
    print(f"s={a.s:g} {a.corner} {a.temp:g}C  f0 {A['f0']/1e6:.2f} MHz  K_vbn {Kb/1e6:.0f}  K_vbp {K_vbp/1e6:.0f} MHz/V  "
          f"Iref {iref*1e6:.2f} uA  vbnf noise @1k {out['vbnf_noise_1k']*1e9:.0f} nV/rtHz")
    for key, r in fm.items():
        print(f"rms FM {key} Hz: {r['total']/1e3:.1f} kHz  [" + "  ".join(f"{k} {x/1e3:.1f}" for k, x in r.items() if k != 'total') + "]")
    for key, r in Lout.items():
        print(f"L({key}) = {r['L']:.1f} dBc/Hz  [" + "  ".join(f"{k} {x:.1f}" for k, x in r.items() if k != 'L') + "]")
    print(f"area {out['area']['total']:.0f} um^2  wrote {wd}/bias_fm.json")


if __name__ == "__main__":
    main()
