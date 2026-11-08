#!/usr/bin/env python3
"""Noise and tuning checks of the current-fed ring (vco_bias topo=cfed), on the 2026-11-08 winner reference.

  tc    --lnws 3.665,5,6 --code 6      tt: f at 0/27/70 C for each n-well length -> tempco (ppm/C, LSQ slope / f27)
  pvt   --code 6                       5 corners x 0/70 C (+ tt 27 C, VDD 3.25/3.35) at vctrl 1.65
  ki    --code 6                       tt 27 C: DAC current I (series probe Vdac), vg, f; then f with +-1 % of I
                                       injected into vg (pulled to GND) -> K_I = df/dI
  dacn  --code 6                       dense .noise (dec 50, 1k-100M) of the DAC output current, vg held by a DC
                                       source at its operating value: total (reference + gate switches + DAC) and
                                       DAC-only (DAC gates on noiseless sources at their DC values)
  isf   --code 6 --m 40                ISF of the cfed ring (stage B of isf.py, crossings at mid-swing) + drain
                                       current noise of one inverter's N and P at the switching bias
  step  --code-k 6                     codes 0-31 x vctrl 0/1.65/3.3 at ss 70 / tt 27 / ff 0 C (VDD 3.3 V)
  range                                code 0 vctrl 0 and code 31 vctrl 3.3 at 5 corners x 0/70 C
Common: --set K=V (vco_bias.P) on top of WINNER + CFED; --jobs; --name (build/cfed/<name>/).
"""
import argparse, json, math, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/vco"))
sys.path.insert(0, str(REPO / "sim/pn"))
import vco_bias as vb, topo_cmp as tcm, isf  # noqa: E402

CFED = dict(topo="cfed", kc=0.75, k=6, cvg=3e-12, cw=3e-15)
SWEEP = "dec 50 1k 100Meg"
BANDS = ((1e3, 1e4), (1e3, 1e5))


def params(sets):
    p = dict(vb.P, **tcm.WINNER, **CFED)
    for kv in sets:
        k, v = kv.split("=")
        p[k] = v if isinstance(vb.P[k], str) else type(vb.P[k])(float(v))
    return p


def tc_of(rows):
    f = {r["temp"]: r["f"] for r in rows}
    ts = [0.0, 27.0, 70.0]
    tm = sum(ts) / 3; fm = sum(f[t] for t in ts) / 3
    sl = sum((t - tm) * (f[t] - fm) for t in ts) / sum((t - tm) ** 2 for t in ts)
    return sl / f[27.0] * 1e6


def probe(body):
    """DAC drain moved from vg to vgd, with Vdac (0 V) vg -> vgd: i(vdac) = DAC current."""
    body = re.sub(r"^(XF\S*C\S*) vg ", r"\1 vgd ", body, flags=re.M)
    return body + "Vdac vg vgd 0\n"


def tran_deck(p, corner, temp, code, vctrl, extra="", tstop=300e-9, t0=200e-9):
    body, ics = vb.netlist(p)
    src = f"vdd vdd 0 3.3\nvctrl vctrl 0 {vctrl}\n" + "".join(
        f"vbit{b} bit{b} 0 {3.3 if (code >> b) & 1 else 0}\nvbitb{b} bitb{b} 0 {0 if (code >> b) & 1 else 3.3}\n"
        for b in range(p["bits"]))
    return f"""* cfed tran
{tcm.HDR.format(corner=corner)}{src}{probe(body)}{extra}.ic {ics}
.control
option temp={temp}
tran 5p {tstop} 0 5p
meas tran amin MIN v(a0) FROM={t0} TO={tstop}
meas tran amax MAX v(a0) FROM={t0} TO={tstop}
let vth = (amin + amax)/2
meas tran t1 WHEN v(a0)=$&vth RISE=1 TD={t0}
meas tran t2 WHEN v(a0)=$&vth RISE=21 TD={t0}
meas tran idac AVG i(vdac) FROM={t0} TO={tstop}
meas tran vga AVG v(vg) FROM={t0} TO={tstop}
let f = 20/(t2-t1)
echo "KI $&f $&idac $&vga $&amin $&amax"
quit
.endc
.end
"""


def parse_ki(log):
    m = re.search(r"^KI (\S+) (\S+) (\S+) (\S+) (\S+)$", log, re.M)
    return dict(zip(("f", "i", "vg", "amin", "amax"), map(float, m.groups()))) if m else None


def dac_noise_deck(p, corner, temp, vg, vbn, code, quiet, out):
    """Noise current of the DAC into a held vg. quiet: the DAC's gates on noiseless sources (DAC devices only)."""
    body, _ = vb.netlist(dict(p, n=0))
    body = probe(body)
    body = re.sub(r"^Cvg .*\n", "", body, flags=re.M)
    if quiet:   # DAC devices' gates -> ideal sources at the DC gate voltages
        g = vb.gnet(p)
        def regate(m):
            t = m.group(0).split()
            if t[2] == g:
                t[2] = "qvbn"
            elif re.fullmatch(r"g\d", t[2]):
                t[2] = "q" + t[2]
            return " ".join(t)
        body = re.sub(r"^XF\S*C\S* .*$", regate, body, flags=re.M)
        body += f"Vqvbn qvbn 0 {vbn}\n" + "".join(
            f"Vqg{b} qg{b} 0 {vbn if (code >> b) & 1 else 0}\n" for b in range(p["bits"]))
    src = "vdd vdd 0 3.3 ac 1\nvctrl vctrl 0 1.65\n" + "".join(
        f"vbit{b} bit{b} 0 {3.3 if (code >> b) & 1 else 0}\nvbitb{b} bitb{b} 0 {0 if (code >> b) & 1 else 3.3}\n"
        for b in range(p["bits"]))
    return f"""* dac noise quiet={quiet}
{tcm.HDR.format(corner=corner)}{src}{body}Vhold vg 0 {vg}
hs no 0 vdac 1
.control
option temp={temp}
op
print i(vdac)
noise v(no) vdd {SWEEP}
setplot noise1
wrdata {out} onoise_spectrum
quit
.endc
.end
"""


def integ(fs, ys, lo, hi):
    pts = [(f, y) for f, y in zip(fs, ys) if lo * (1 - 1e-9) <= f <= hi * (1 + 1e-9)]
    return sum(0.5 * (y0 * f0 + y1 * f1) * math.log(f1 / f0) for (f0, y0), (f1, y1) in zip(pts, pts[1:]))


def at(fs, ys, f0):
    return isf.interp_log(fs, ys, f0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["tc", "pvt", "ki", "dacn", "isf", "step", "range"])
    ap.add_argument("--name", default="a")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--code", type=int, default=6)
    ap.add_argument("--lnws", default="3.665,5,6,7,8,10")
    ap.add_argument("--m", type=int, default=40)
    ap.add_argument("--tstep", default="0.5p", help="isf: tran step (0.5p = isf.py production; 2p for a quick run)")
    ap.add_argument("--ki", default=None, help="dacn: ki.json to read I, vg, f, K_I from")
    a = ap.parse_args()
    p = params(a.set)
    out = REPO / "build/cfed" / a.name
    out.mkdir(parents=True, exist_ok=True)
    if a.mode == "tc":
        lnws = [float(x) for x in a.lnws.split(",")]
        decks = [(f"tc_lnw{x:g}", tcm.deck(dict(p, lnw=x), "typical", [(a.code, 1.65, t, 3.3) for t in (0, 27, 70)]))
                 for x in lnws]
        vb.run(out, decks, a.jobs)
        res = []
        for (n, _), x in zip(decks, lnws):
            rows = tcm.parse((out / f"{n}.log").read_text())
            r = dict(lnw=x, tc_ppm=tc_of(rows), f={r["temp"]: r["f"] for r in rows})
            res.append(r)
            print(f"lnw {x:7.4f}  tempco {r['tc_ppm']:7.1f} ppm/C  f27 {r['f'][27.0]/1e6:.2f} MHz  "
                  f"f0 {r['f'][0.0]/1e6:.2f} f70 {r['f'][70.0]/1e6:.2f}")
        (out / "tc.json").write_text(json.dumps(res, indent=1))
    elif a.mode in ("pvt", "range"):
        if a.mode == "pvt":
            cts = [(c, t, [(a.code, 1.65, t, 3.3)]) for c in vb.CORNERS for t in (0.0, 70.0)]
            cts.append(("typical", 27.0, [(a.code, 1.65, 27.0, d) for d in (3.25, 3.3, 3.35)]))
        else:
            cts = [(c, t, [(0, 0.0, t, 3.3), (31, 3.3, t, 3.3)]) for c in vb.CORNERS for t in (0.0, 70.0)]
        decks = [(f"{a.mode}_{c}_t{t:g}", tcm.deck(p, c, pts)) for c, t, pts in cts]
        vb.run(out, decks, a.jobs)
        rows = []
        for (n, _), (c, t, _) in zip(decks, cts):
            for r in tcm.parse((out / f"{n}.log").read_text()):
                rows.append(dict(corner=c, **r))
                print(f"{c:8s} {r['temp']:3.0f} {r['vdd']:.2f} c{r['code']:2d} vc{r['vctrl']:.2f} f {r['f']/1e6:7.2f} MHz "
                      f"P {r['p_w']*1e3:.3f} mW")
        (out / f"{a.mode}.json").write_text(json.dumps(rows, indent=1))
    elif a.mode == "ki":
        base = {"ki_0": tran_deck(p, "typical", 27, a.code, 1.65)}
        vb.run(out, list(base.items()), 1)
        r0 = parse_ki((out / "ki_0.log").read_text())
        di = 0.01 * abs(r0["i"])
        decks = [(f"ki_{s}", tran_deck(p, "typical", 27, a.code, 1.65, f"Iinj vg 0 {sgn * di:.6e}\n"))
                 for s, sgn in (("p", 1), ("m", -1))]
        decks.append(("ki_vp", tran_deck(p, "typical", 27, a.code, 1.65).replace("vdd vdd 0 3.3", "vdd vdd 0 3.35")))
        decks.append(("ki_vm", tran_deck(p, "typical", 27, a.code, 1.65).replace("vdd vdd 0 3.3", "vdd vdd 0 3.25")))
        vb.run(out, decks, a.jobs)
        r = {n[3:]: parse_ki((out / f"{n}.log").read_text()) for n, _ in decks}
        K_I = (r["p"]["f"] - r["m"]["f"]) / (2 * di)
        K_vdd = (r["vp"]["f"] - r["vm"]["f"]) / 0.1
        res = dict(code=a.code, f0=r0["f"], I=abs(r0["i"]), vg=r0["vg"], amin=r0["amin"], amax=r0["amax"], K_I=K_I,
                   K_vdd=K_vdd, dlnf_dlnI=K_I * abs(r0["i"]) / r0["f"], runs=r)
        print(json.dumps({k: v for k, v in res.items() if k != "runs"}, indent=1))
        (out / "ki.json").write_text(json.dumps(res, indent=1))
    elif a.mode == "dacn":
        ki = json.loads(Path(a.ki).read_text())
        op = isf.ngspice(out, {"op_vbn": f"* op\n{tcm.HDR.format(corner='typical')}vdd vdd 0 3.3\nvctrl vctrl 0 1.65\n"
                               + "".join(f"vbit{b} bit{b} 0 0\nvbitb{b} bitb{b} 0 3.3\n" for b in range(p['bits']))
                               + vb.netlist(dict(p, n=0))[0] + "\n.control\nop\nprint v(vbn)\nquit\n.endc\n.end\n"}, 1)
        vbn = float(re.search(r"^v\(vbn\)\s*=\s*(\S+)", op["op_vbn"], re.M).group(1))
        decks = {f"dacn_{q}": dac_noise_deck(p, "typical", 27, ki["vg"], vbn, a.code, q == "dac", f"dacn_{q}.txt")
                 for q in ("tot", "dac")}
        logs = isf.ngspice(out, decks, 2)
        idc = abs(float(re.search(r"^i\(vdac\)\s*=\s*(\S+)", logs["dacn_tot"], re.M).group(1)))
        ft, st = isf.read_psd(out / "dacn_tot.txt")
        fd, sd = isf.read_psd(out / "dacn_dac.txt")
        sref = [max(x - y, 0.0) for x, y in zip(st, sd)]
        # f-scaling: K_I measured at the base sizing; for a variant with current idc, scale by the log-slope
        KI = ki["dlnf_dlnI"] * ki["f0"] / idc
        terms = {"ref": [KI ** 2 * x for x in sref], "dac": [KI ** 2 * x for x in sd]}
        S_VDD = (160e-9) ** 2
        terms["vdd"] = [ki["K_vdd"] ** 2 * S_VDD for _ in ft]
        tot = [sum(t[i] for t in terms.values()) for i in range(len(ft))]
        fm = {f"{lo:g}-{hi:g}": dict(total=math.sqrt(integ(ft, tot, lo, hi)),
                                     **{k: math.sqrt(integ(ft, t, lo, hi)) for k, t in terms.items()})
              for lo, hi in BANDS}
        L = {f"{f0:g}": {k: 10 * math.log10(at(ft, t, f0) / f0 ** 2 / 2) for k, t in dict(terms, total=tot).items()}
             for f0 in (1e4, 1e5, 1e6, 1e7)}
        res = dict(set=a.set, vbn=vbn, vg=ki["vg"], I_dac_noise_op=idc, K_I=KI,
                   SI_1k=dict(tot=at(ft, st, 1e3), dac=at(fd, sd, 1e3)), SI_10M=dict(tot=at(ft, st, 1e7), dac=at(fd, sd, 1e7)),
                   fm=fm, L=L)
        (out / "dacn.json").write_text(json.dumps(res, indent=1))
        print(f"I {idc*1e6:.2f} uA  K_I {KI/1e6*1e-6:.3f} MHz/uA  vbn {vbn:.4f}  "
              f"sqrt S_I @1k tot {math.sqrt(res['SI_1k']['tot'])*1e12:.2f} dac {math.sqrt(res['SI_1k']['dac'])*1e12:.2f} pA/rtHz  "
              f"@10M tot {math.sqrt(res['SI_10M']['tot'])*1e12:.2f} dac {math.sqrt(res['SI_10M']['dac'])*1e12:.2f}")
        for k, r in fm.items():
            print(f"rms FM {k}: total {r['total']/1e3:.2f} kHz  [" + "  ".join(f"{x} {y/1e3:.2f}" for x, y in r.items() if x != 'total') + "]")
        for k, r in L.items():
            print(f"L({k}) " + "  ".join(f"{x} {y:.1f}" for x, y in r.items()))
    elif a.mode == "isf":
        isf_mode(a, p, out)
    elif a.mode == "step":
        step_mode(a, p, out)


def isf_mode(a, p, out):
    """Inverter noise by the ISF (Hajimiri): isf.stage_b on the cfed ring, crossings at mid-swing."""
    ki = json.loads((out.parent / a.ki).read_text()) if a.ki and not a.ki.startswith("/") else json.loads(Path(a.ki).read_text())
    v = dict(kind="bias", n=5, code=a.code, vctrl=1.65, nodes=5, inj="a2", out="a0", ic_ref=True,
             set={k: p[k] for k in p if p[k] != vb.P[k]})
    net, ic, _ = isf.circuit(v, "typical")
    vmid = (ki["amin"] + ki["amax"]) / 2
    if a.tstep != "0.5p":   # coarser time step for a quick ISF (isf.py's decks use 0.5 ps and reltol 1e-5)
        run0 = isf.ngspice
        isf.ngspice = lambda wd, decks, jobs=1: run0(wd, {k: d.replace(" 0.5p", f" {a.tstep}").replace("reltol=1e-5", "reltol=1e-4")
                                                         for k, d in decks.items()}, jobs)
    isf.VDD = 2 * vmid          # isf.py measures crossings at VDD/2; the vdd source is already in `net`
    ref = isf.ngspice(out, {"isf_ref": isf.no_uic(isf.ref_deck(net, ic, v, 27, 160), v)}, 1)["isf_ref"]
    t0, t10 = isf.grab(ref, "t0"), isf.grab(ref, "t10")
    A = dict(T=(t10 - t0) / 10, t0=t0, f0=10 / (t10 - t0))
    print(f"ISF ref: f0 {A['f0']/1e6:.2f} MHz, vmid {vmid:.3f}", flush=True)
    rows = isf.stage_b(v, net, ic, A, 27, a.m, out, a.jobs)
    gp = [r[2] if r[4] >= r[3] else 0.0 for r in rows]   # node rising: P conducts
    gn = [r[2] if r[4] < r[3] else 0.0 for r in rows]
    st = {k: dict(rms2=sum(x * x for x in g) / len(g), dc=sum(g) / len(g)) for k, g in (("P", gp), ("N", gn))}
    # drain-current noise of one inverter's N and P: switching bias (gate = drain = vmid) and fully on (gate at
    # the opposite rail of the swing, drain at vmid)
    vg, vdd = ki["vg"], 3.3
    W = dict(N=(p["wn"], "nfet_03v3", vg, "0"), P=(p["wp"], "pfet_03v3", vdd, "vdd"))
    decks = {}
    for dev, (w, typ, vs, bulk) in W.items():
        for bias, vgate in (("sw", vmid), ("on", vdd if dev == "N" else ki["amin"])):
            fet = vb.fet("D", "dd", "gg", "ss", bulk, typ, w, p["L"])
            decks[f"inv_{dev}_{bias}"] = f"""* inverter {dev} {bias}
{isf.MODELS.format(corner='typical')}vdd vdd 0 3.3
vss ss 0 {vs}
vgg gg 0 {vgate}
{fet}vsn dd d 0
vd d 0 {vmid} ac 1
hs no 0 vsn 1
.control
option temp=27
noise v(no) vd {SWEEP}
setplot noise1
wrdata inv_{dev}_{bias}.txt onoise_spectrum
quit
.endc
.end
"""
    isf.ngspice(out, decks, 4)
    res = dict(A=A, vmid=vmid, isf=st, L={})
    for bias in ("sw", "on"):
        psd = {d: isf.read_psd(out / f"inv_{d}_{bias}.txt") for d in ("N", "P")}
        Lb = {}
        fgrid = psd["N"][0]
        Sf = []
        for f in fgrid:
            tot = 0.0
            for d in ("N", "P"):
                fx, fs = psd[d]
                s_w = fs[-1]
                s_fl = max(isf.interp_log(fx, fs, f) - s_w, 0.0)
                tot += 5 * (st[d]["rms2"] * s_w + st[d]["dc"] ** 2 * s_fl) / (2 * math.pi) ** 2   # S_phi * f^2
            Sf.append(tot)                                                                     # = S_f (Hz^2/Hz)
        for f0 in (1e4, 1e5, 1e6, 1e7):
            Lb[f"{f0:g}"] = 10 * math.log10(at(fgrid, Sf, f0) / f0 ** 2 / 2)
        fm = {f"{lo:g}-{hi:g}": math.sqrt(integ(fgrid, Sf, lo, hi)) for lo, hi in BANDS}
        res["L"][bias] = Lb
        res.setdefault("fm", {})[bias] = fm
        res.setdefault("SI", {})[bias] = {d: dict(white=psd[d][1][-1], at1k=at(*psd[d], 1e3)) for d in ("N", "P")}
        print(f"inverters ({bias}): L " + "  ".join(f"{k} {x:.1f}" for k, x in Lb.items())
              + "  FM " + "  ".join(f"{k} {x/1e3:.2f} kHz" for k, x in fm.items()))
    print(f"ISF P rms2 {st['P']['rms2']:.3e} dc {st['P']['dc']:.3e} | N rms2 {st['N']['rms2']:.3e} dc {st['N']['dc']:.3e}")
    (out / "isf.json").write_text(json.dumps(res, indent=1))


def step_mode(a, p, out):
    pvts = (("ss", 70.0), ("typical", 27.0), ("ff", 0.0))
    chunks = [range(0, 11), range(11, 22), range(22, 32)]
    decks = [(f"step_{c}_t{t:g}_{i}", tcm.deck(p, c, [(code, vc, t, 3.3) for code in ch for vc in (0.0, 1.65, 3.3)]))
             for c, t in pvts for i, ch in enumerate(chunks)]
    vb.run(out, decks, a.jobs)
    res = []
    for c, t in pvts:
        d = {}
        for i in range(len(chunks)):
            for r in tcm.parse((out / f"step_{c}_t{t:g}_{i}.log").read_text()):
                d[(r["code"], r["vctrl"])] = r["f"]
        f = lambda co, v: d.get((co, v), float("nan"))
        worst, fails = 9e9, []
        for co in range(31):
            step = f(co + 1, 1.65) - f(co, 1.65)
            fine = min(f(co, 3.3) - f(co, 0.0), f(co + 1, 3.3) - f(co + 1, 0.0))
            ratio = fine / step if step > 0 else float("nan")
            worst = min(worst, ratio)
            if not ratio >= 1.3:
                fails.append((co, round(step / 1e6, 2), round(fine / 1e6, 2), round(ratio, 2)))
        rr = dict(corner=c, temp=t, worst_ratio=worst, fails=fails, fmin=f(0, 0.0), fmax=f(31, 3.3),
                  f={f"{k[0]}_{k[1]}": x for k, x in d.items()})
        res.append(rr)
        print(f"{c:8s} {t:3.0f}: f {rr['fmin']/1e6:.1f}..{rr['fmax']/1e6:.1f} MHz  worst fine/step {worst:.2f}  "
              f"fails (code, step, fine, ratio) {fails}")
    (out / "step.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
