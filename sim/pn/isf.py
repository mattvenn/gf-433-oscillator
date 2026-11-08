#!/usr/bin/env python3
"""Phase noise of the candidate ring VCOs by the impulse sensitivity function (ISF) method
(Hajimiri & Lee, JSSC 1998). ngspice has no PSS/pnoise and no device noise in transient, so:

  A. reference run: steady oscillation -> period T, power, a reference edge t0, node waveform
  B. ISF: inject a small charge dq into one ring node at M phases across one period; the
     permanent shift of a later edge gives g(phi) = dphi/dq  (= Gamma/qmax)
  C. device noise: .noise of one stage's head (PMOS) and foot (NMOS) networks at their gate
     voltages -> current PSD S_i(f) = white + flicker
  D. common-mode paths: df/dV of the bias line (vbn for const-gm, vctrl for the others) and of VDD,
     times that line's noise PSD
  combine:  S_phi(f) = Nnodes * sum_{head,foot} [ rms(g_x)^2 * S_w,x + mean(g_x)^2 * S_fl,x(f) ] / (2 pi f)^2
            + K_bias^2 * S_bias(f) / f^2 + K_vdd^2 * S_vdd / f^2 ;   L(f) = S_phi / 2
  g_x = g weighted by which device conducts at that phase (node rising -> head, falling -> foot).

Variants: se (vco_cand se N=5), diff (vco_cand diff N=4), cgm (vco_bias N=5, n-well + n+ resistor),
cgmf (cgm + 1 Mohm / 20 pF RC between vbn and its loads; vbnf starts at its DC value, see stage_a),
cgmq (cgmf + the quiet reference from docs/bias_tuning_results.md, code 5).
--set K=V overrides a vco_bias.P parameter of a bias variant (repeatable); without it results are unchanged.

Usage (repo root):
  python3 sim/pn/isf.py <variant> [--corner typical] [--temp 27] [--m 60] [--jobs 1] [--out build/pn] [--set K=V] [--tag _x]
Writes <out>/<variant>_<corner>_t<temp>/ : decks, logs, isf.csv, noise_*.txt, result.json, L.png
Run time: about 5-10 s per ISF phase per job on a laptop core; --m 60 is the production setting.
"""
import argparse, json, math, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/vco"))
import vco_cand, vco_bias  # noqa: E402

OSIC = os.environ.get("OSIC", str(REPO / "tools/osic-mac"))
KT = 1.380649e-23 * 300.15
MODELS = """.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice {corner}
.lib /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice res_typical
"""
SIZES = dict(wn=2.0, wp=5.0, whead=6.0, wpb=1.0, wmb=0.25, wfu=0.25, k=8, ls=1.0, wx=0.5)
# operating points close to 433.92 MHz at tt 27 C (from the vco sweeps)
VARIANTS = {
    "se":   dict(kind="cand", topo="se", n=5, code=7, vctrl=1.36, nodes=5, inj="a2", out="a0"),
    "diff": dict(kind="cand", topo="diff", n=4, code=7, vctrl=1.67, nodes=8, inj="a2", out="a0"),
    "cgm":  dict(kind="bias", n=5, code=10, vctrl=1.65, nodes=5, inj="a2", out="a0",
                 set=dict(rideal=0, lnw=4.5, lnp=100.0)),
    # cgm + RC low-pass (1 Mohm ppolyf_u_1k (3k before 2026-11-08), 20 pF) between the reference and every vbn load
    "cgmf": dict(kind="bias", n=5, code=10, vctrl=1.65, nodes=5, inj="a2", out="a0",
                 set=dict(rideal=0, lnw=4.5, lnp=100.0, rf=1e6, cf=20e-12)),
    # cgmf + the quiet reference of docs/bias_tuning_results.md (Job 1): MN1/MN2 as 14 x 14 series-parallel arrays of
    # the 2/1 um unit, PMOS mirror x14 (56/14 um), master leg x4, lnw retuned for zero tempco. Code 5 is the code
    # nearest 433.92 MHz at tt 27 C, vctrl 1.65 V with cw = 2 fF (436.3 MHz). The reference starts at its DC point.
    "cgmq": dict(kind="bias", n=5, code=5, vctrl=1.65, nodes=5, inj="a2", out="a0", ic_ref=True,
                 set=dict(rideal=0, lnw=3.665, lnp=100.0, rf=1e6, cf=20e-12, nsn=14, wpm=56.0, lpm=14.0, mr=4.0)),
}
VDD = 3.3
R_VCTRL = 100e3      # assumed source resistance of the vctrl filter (thermal noise only)
S_VDD = (100e-9) ** 2  # assumed VDD noise PSD, V^2/Hz (100 nV/rtHz white); reported separately too


def with_sets(v, sets):
    """Copy of variant v with `K=V` overrides of vco_bias.P merged into v['set'] (no sets: v unchanged)."""
    if not sets:
        return v
    if v["kind"] != "bias":
        sys.exit("--set only applies to vco_bias variants")
    st = dict(v.get("set", {}))
    for kv in sets:
        k, x = kv.split("=", 1)
        if k not in vco_bias.P:
            sys.exit(f"--set: unknown parameter {k}")
        st[k] = type(vco_bias.P[k])(float(x))
    return dict(v, set=st)


def circuit(v, corner):
    """Return (netlist text incl. sources, .ic line, params)."""
    if v["kind"] == "cand":
        p = dict(vco_cand.P); p.update(SIZES)
        body, ics, _ = vco_cand.netlist(v["topo"], v["n"], p)
        ic = " ".join(f"v({k})={x}" for k, x in ics.items())
        src = f"vdd vdd 0 {VDD}\nvctrl vctrl 0 {v['vctrl']}\n"
    else:
        p = dict(vco_bias.P); p.update(v.get("set", {}))
        body, ic = vco_bias.netlist(p)
        body = body.replace("XMN1 n1 n1 ", "XMN1 n1i n1 ", 1) + "vir n1 n1i 0\n"
        body = body.replace("Rvbn n1 vbn 1", "Vbnp n1 vbn 0")   # probe source for df/dvbn
        src = f"vdd vdd 0 {VDD}\nvctrl vctrl 0 {v['vctrl']}\n"
    for b in range(p["bits"]):
        on = (v["code"] >> b) & 1
        src += f"vbit{b} bit{b} 0 {VDD if on else 0}\nvbitb{b} bitb{b} 0 {0 if on else VDD}\n"
    return MODELS.format(corner=corner) + src + body, ic, p


def ngspice(workdir, decks, jobs=1):
    """Run decks (name -> text) in workdir, `jobs` ngspice processes in parallel (one container each)."""
    workdir.mkdir(parents=True, exist_ok=True)
    rel = workdir.relative_to(REPO)
    # ngspice reads .spiceinit from its cwd; one thread each when several run in parallel
    init = (REPO / ".spiceinit").read_text()
    (workdir / ".spiceinit").write_text(re.sub(r"num_threads=\d+", f"num_threads={1 if jobs > 1 else 4}", init))
    for n, t in decks.items():
        (workdir / f"{n}.cir").write_text(t)
    def one(n):
        subprocess.run([OSIC, "bash", "-c", f"cd {REPO}/{rel} && ngspice -b {n}.cir > {n}.log 2>&1"], check=False)
        return (workdir / f"{n}.log").read_text()
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        return dict(zip(decks, ex.map(one, decks)))


def grab(log, key):
    m = re.search(rf"^{key}\s*=\s*(\S+)", log, re.M)
    return float(m.group(1)) if m else float("nan")


def ref_deck(net, ic, v, temp, tstop, extra=""):
    o = v["out"]
    return f"""* reference
{net}
.ic {ic}
.options reltol=1e-5
.control
option temp={temp}
{extra}tran 0.5p {tstop}n 0 0.5p uic
meas tran t0 WHEN v({o})={VDD/2} RISE=1 TD=100n
meas tran t10 WHEN v({o})={VDD/2} RISE=11 TD=100n
meas tran iavg AVG i(vdd) FROM=100n TO={tstop}n
meas tran vbn AVG v(vbn) FROM=100n TO={tstop}n
meas tran vbnf AVG v(vbnf) FROM=100n TO={tstop}n
meas tran vbp AVG v(vbp) FROM=100n TO={tstop}n
quit
.endc
.end
"""


def op_vbn(net, temp, wd, vdd=VDD, dv=0.0):
    """DC value of vbn (= vbnf: the filtered gates draw no DC current), at supply vdd and probe offset dv."""
    log = ngspice(wd, {f"op_{vdd:.2f}_{dv:g}": f"""* op
{net}
.control
option temp={temp}
alter vdd {vdd}
alter vbnp {dv}
op
print v(vbn)
quit
.endc
.end
"""})
    return float(re.search(r"^v\(vbn\)\s*=\s*(\S+)", list(log.values())[0], re.M).group(1))


def no_uic(deck, v):
    """ic_ref variants: start the tran from a DC operating point (only the ring nodes and vbnf held by .ic) instead
    of uic, so the reference and every PDK-subcircuit internal node start at DC. With uic, those internal nodes
    start at 0 V and a large reference does not recover within the run (vbn sagged by up to 0.5 V)."""
    return deck.replace(" 0.5p uic\n", " 0.5p\n") if v.get("ic_ref") else deck


def stage_a(v, corner, temp, wd, jobs):
    net, ic, p = circuit(v, corner)
    tstop = 140
    filt = v["kind"] == "bias" and vco_bias.gnet(p) != "vbn"
    ic0 = ic
    dc = {}
    if filt:   # DC value of vbn (= vbnf) at each stage-A operating point
        for key, vdd, dv in (("ref", VDD, 0.0), ("vdd_hi", VDD + 0.05, 0.0), ("vdd_lo", VDD - 0.05, 0.0), ("bias_hi", VDD, 0.005)):
            dc[key] = op_vbn(net, temp, wd, vdd, dv)
    def icf(key, corr=0.0):
        # the RC (tens of us) is far slower than the 140 ns run: start vbnf at its DC value. The ring's
        # start-up (uic) also pumps a few mV onto cf, which the diode would remove in ns but the RC holds
        # for tens of us, so `corr` pre-subtracts that step (measured on a first ref run).
        return ic0 + (f" v(vbnf)={dc[key] - corr:.6f}" if filt else "")
    bias = "vctrl" if v["kind"] == "cand" else "vbnp"
    corr = 0.0
    for it in range(3 if filt else 1):
        decks = {"ref": ref_deck(net, icf("ref", corr), v, temp, tstop)}
        decks = {k: no_uic(d, v) for k, d in decks.items()}
        if filt and it == 0:     # first pass: measure the start-up step only
            l = ngspice(wd, decks, 1)["ref"]
            corr = grab(l, "vbnf") - dc["ref"]
            print(f"A: vbnf start-up step {corr*1e3:+.2f} mV -> corrected .ic", flush=True)
            continue
        decks.update({"vdd_hi": ref_deck(net, icf("vdd_hi", corr), v, temp, tstop, f"alter vdd {VDD + 0.05}\n"),
                      "vdd_lo": ref_deck(net, icf("vdd_lo", corr), v, temp, tstop, f"alter vdd {VDD - 0.05}\n"),
                      "bias_hi": ref_deck(net, icf("bias_hi", corr), v, temp, tstop,
                                          f"alter {bias} {(v['vctrl'] if bias == 'vctrl' else 0) + 0.005}\n")})
        logs = ngspice(wd, {k: no_uic(d, v) for k, d in decks.items()}, jobs)
        break
    ic = icf("ref", corr)
    f = {k: 10 / (grab(l, "t10") - grab(l, "t0")) for k, l in logs.items()}
    a = dict(f0=f["ref"], T=1 / f["ref"], t0=grab(logs["ref"], "t0"), P=-grab(logs["ref"], "iavg") * VDD,
             vbn=grab(logs["ref"], "vbn"), vbnf=grab(logs["ref"], "vbnf"), vbnf_ic_corr=corr, vbp=grab(logs["ref"], "vbp"),
             K_vdd=(f["vdd_hi"] - f["vdd_lo"]) / 0.1, K_bias=(f["bias_hi"] - f["ref"]) / 0.005, bias_line=bias)
    if not all(math.isfinite(x) for x in (a["f0"], a["t0"])):
        sys.exit(f"stage A failed, see {wd}/ref.log")
    return net, ic, p, a


def stage_b(v, net, ic, a, temp, m, wd, jobs, dq_amp=1e-3):
    """ISF: one deck per chunk of phases; each phase is a fresh tran with the pulse delayed."""
    T, t0, o, k = a["T"], a["t0"], v["out"], v["inj"]
    tmeas = t0 + 14 * T            # edge used to read the permanent phase shift
    tstop = (tmeas + 3 * T) * 1e9
    dq = dq_amp * 1.5e-12          # 0.5 ps rise + 1 ps flat + 0.5 ps fall
    chunks = [list(range(i, m, jobs)) for i in range(jobs)]
    tw = tmeas - 0.3 * T           # meas window start; edges are measured as intervals from it
                                   # (meas/echo keep ~6-7 digits: absolute times would quantize to 0.1-1 ps)
    decks = {}
    for c, js in enumerate(chunks):
        ctl = f"""option temp={temp}
tran 0.5p {tstop:.3f}n 0 0.5p uic
meas tran trf TRIG AT={tw:.9e} TARG v({o}) VAL={VDD/2} RISE=1 TD={tw:.9e}
echo "REF $&trf"
destroy all
"""
        for j in js:
            td = t0 + j * T / m
            ctl += f"""alter @iinj[pulse] [ 0 {dq_amp} {td:.6e} 0.5p 0.5p 1p 1 ]
option temp={temp}
tran 0.5p {tstop:.3f}n 0 0.5p uic
meas tran tpf TRIG AT={tw:.9e} TARG v({o}) VAL={VDD/2} RISE=1 TD={tw:.9e}
meas tran va FIND v({k}) AT={td - 3e-12:.6e}
meas tran vb FIND v({k}) AT={td:.6e}
echo "ISF {j} $&tpf $&va $&vb"
destroy all
"""
        decks[f"isf_{c}"] = f"""* ISF chunk {c}
{net}
Iinj 0 {k} PULSE(0 0 1 0.5p 0.5p 1p 1)
.ic {ic}
.options reltol=1e-5
.control
{ctl}quit
.endc
.end
"""
    logs = ngspice(wd, {n: no_uic(d, v) for n, d in decks.items()}, jobs)
    rows = []
    for l in logs.values():
        tr = tw + float(re.search(r"^REF (\S+)", l, re.M).group(1))
        for mm in re.finditer(r"^ISF (\d+) (\S+) (\S+) (\S+)", l, re.M):
            j, tp, va, vb = int(mm.group(1)), *map(float, mm.groups()[1:])
            tp = tw + tp
            dphi = -2 * math.pi * (tp - tr) / T          # earlier edge = phase advance
            rows.append((j, j / m * 2 * math.pi, dphi / dq, va, vb))
    rows.sort()
    (wd / "isf.csv").write_text("j,phi,g_rad_per_C,v_m3ps,v_at_td\n" +
                                "".join(f"{r[0]},{r[1]:.5f},{r[2]:.6e},{r[3]:.4f},{r[4]:.4f}\n" for r in rows))
    return rows


def noise_deck(p, v, a, side, corner, temp):
    """Current noise of one stage's head (PMOS) or foot (NMOS) network with its drain held at VDD/2."""
    gates = ""
    if v["kind"] == "cand":
        vb = v["vctrl"]
        for b in range(p["bits"]):
            gates += f"vg{b} g{b} 0 {vb if (v['code'] >> b) & 1 else 0}\n"
        foot = vco_cand.foot("x", p).replace("fx", "dn")
        head = vco_cand.fet("MHx", "dp", "vbp", "vdd", "vdd", "pfet_03v3", p["whead"], p["ls"])
        gates += f"vctrl vctrl 0 {vb}\n"
    else:
        vb = a["vbn"]
        for b in range(p["bits"]):
            gates += f"vg{b} g{b} 0 {vb if (v['code'] >> b) & 1 else 0}\n"
        foot = vco_bias.foot("x", p, "dn")
        head = vco_bias.fet("Hx", "dp", "vbp", "vdd", "vdd", "pfet_03v3", p["whead"], p["ls"])
        gates += f"vbn vbn 0 {vb}\nvctrl vctrl 0 {v['vctrl']}\n"
    dut = (foot + "vsn dn d 0\n") if side == "foot" else (head + "vsn d dp 0\n")
    return f"""* {side} noise
{MODELS.format(corner=corner)}
vdd vdd 0 {VDD}
vbp vbp 0 {a['vbp']}
{gates}{dut}vd d 0 {VDD/2} ac 1
hs no 0 vsn 1
.control
option temp={temp}
noise v(no) vd dec 10 1k 1G
setplot noise1
wrdata noise_{side}.txt onoise_spectrum
quit
.endc
.end
"""


def bias_noise_deck(p, corner, temp, sweep="dec 10 1k 1G", out="noise_vbn.txt", node=None, edit=None):
    """Voltage noise on the load gates (vbn, or vbnf after the RC filter) from the const-gm reference alone (no ring).
    sweep/out/node: .noise sweep, output file and probed node (default the load-gate net); edit: body -> body."""
    body, _ = vco_bias.netlist(dict(p, n=0))
    if edit:
        body = edit(body)
    node = node or vco_bias.gnet(p)
    src = f"vdd vdd 0 {VDD} ac 1\nvctrl vctrl 0 1.65\n" + "".join(f"vbit{b} bit{b} 0 0\nvbitb{b} bitb{b} 0 {VDD}\n" for b in range(p["bits"]))
    return f"""* vbn noise
{MODELS.format(corner=corner)}
{src}{body}
.control
option temp={temp}
noise v({node}) vdd {sweep}
setplot noise1
wrdata {out} onoise_spectrum
quit
.endc
.end
"""


def read_psd(path):
    f, s = [], []
    for line in path.read_text().split("\n"):
        x = line.split()
        if len(x) >= 2:
            f.append(float(x[0])); s.append(float(x[1]) ** 2)    # V/rtHz -> V^2/Hz (A^2/Hz via 1 ohm H)
    return f, s


def interp_log(fx, fs, f):
    import bisect
    i = min(max(bisect.bisect_left(fx, f), 1), len(fx) - 1)
    x0, x1 = math.log(fx[i - 1]), math.log(fx[i])
    y0, y1 = math.log(fs[i - 1]), math.log(fs[i])
    return math.exp(y0 + (y1 - y0) * (math.log(f) - x0) / (x1 - x0))


def combine(v, a, rows, psd, out_freqs):
    # split the ISF by which device conducts: node rising (or about to) -> head, falling -> foot
    # (both voltages are sampled before the pulse, so the injected charge does not bias the split)
    gh = [r[2] if r[4] >= r[3] else 0.0 for r in rows]
    gf = [r[2] if r[4] < r[3] else 0.0 for r in rows]
    stats = {}
    for name, g in (("head", gh), ("foot", gf)):
        stats[name] = dict(rms2=sum(x * x for x in g) / len(g), dc=sum(g) / len(g))
    res = {}
    for f in out_freqs:
        w = 2 * math.pi * f
        terms = {}
        for side in ("head", "foot"):
            fx, fs = psd[side]
            s_w = fs[-1] if fs else 0.0                       # white level at the top of the sweep
            s_fl = max(interp_log(fx, fs, f) - s_w, 0.0)
            terms[f"dev_{side}"] = v["nodes"] * (stats[side]["rms2"] * s_w + stats[side]["dc"] ** 2 * s_fl) / w ** 2
        if "vbn" in psd:
            sb = interp_log(*psd["vbn"], f)
        else:
            sb = 4 * KT * R_VCTRL                             # assumed vctrl filter resistor
        terms["bias"] = a["K_bias"] ** 2 * sb / f ** 2
        terms["vdd"] = a["K_vdd"] ** 2 * S_VDD / f ** 2
        tot = sum(terms.values())
        res[f] = dict(L=10 * math.log10(tot / 2), **{k: 10 * math.log10(x / 2) if x > 0 else None for k, x in terms.items()})
    return stats, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", choices=list(VARIANTS))
    ap.add_argument("--corner", default="typical")
    ap.add_argument("--temp", type=float, default=27)
    ap.add_argument("--m", type=int, default=60, help="ISF phases per period")
    ap.add_argument("--jobs", type=int, default=1, help="parallel ngspice processes")
    ap.add_argument("--out", default="build/pn")
    ap.add_argument("--set", action="append", default=[], metavar="K=V",
                    help="override a vco_bias.P parameter of a 'bias' variant (repeatable), e.g. --set w1=20")
    ap.add_argument("--tag", default="", help="suffix for the output directory (useful with --set)")
    a_ = ap.parse_args()
    v = with_sets(VARIANTS[a_.variant], a_.set)
    wd = REPO / a_.out / f"{a_.variant}{a_.tag}_{a_.corner}_t{a_.temp:g}"
    net, ic, p, a = stage_a(v, a_.corner, a_.temp, wd, a_.jobs)
    print(f"A: f0 {a['f0']/1e6:.2f} MHz  P {a['P']*1e3:.2f} mW  K_vdd {a['K_vdd']/1e6:.1f} MHz/V  "
          f"K_{a['bias_line']} {a['K_bias']/1e6:.1f} MHz/V  vbn {a['vbn']:.3f} vbp {a['vbp']:.3f}", flush=True)
    rows = stage_b(v, net, ic, a, a_.temp, a_.m, wd, a_.jobs)
    decks = {f"noise_{s}": noise_deck(p, v, a, s, a_.corner, a_.temp) for s in ("head", "foot")}
    if v["kind"] == "bias":
        decks["noise_vbn"] = bias_noise_deck(p, a_.corner, a_.temp)
    ngspice(wd, decks, a_.jobs)
    psd = {k[6:]: read_psd(wd / f"{k}.txt") for k in decks}
    freqs = [1e4, 1e5, 1e6, 1e7]
    stats, res = combine(v, a, rows, psd, freqs)
    fom = {f: r["L"] - 20 * math.log10(a["f0"] / f) + 10 * math.log10(a["P"] / 1e-3) for f, r in res.items()}
    out = dict(variant=a_.variant, set=v.get("set", {}), corner=a_.corner, temp=a_.temp, m=a_.m, A=a, isf=stats,
               L={f"{f:g}": r for f, r in res.items()}, FOM={f"{f:g}": x for f, x in fom.items()},
               assumptions=dict(R_vctrl=R_VCTRL, S_vdd=S_VDD))
    (wd / "result.json").write_text(json.dumps(out, indent=1))
    print(f"ISF head rms2 {stats['head']['rms2']:.3e} dc {stats['head']['dc']:.3e} | "
          f"foot rms2 {stats['foot']['rms2']:.3e} dc {stats['foot']['dc']:.3e}  (rad/C)")
    for f, r in res.items():
        parts = "  ".join(f"{k} {x:.1f}" for k, x in r.items() if k != "L" and x is not None)
        print(f"L({f:>8g} Hz) = {r['L']:7.1f} dBc/Hz   FOM {fom[f]:6.1f}   [{parts}]")
    print(f"wrote {wd}/result.json")


if __name__ == "__main__":
    main()
