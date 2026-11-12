#!/usr/bin/env python3
"""The vg decap returned to VDD instead of VSS: the study behind STATUS item 3 (25 MHz supply spur).

    python3 sim/tune/vg_decap.py cv|spur|size|psr|startup|all [--jobs N]   -> build/tx_fine/vg_decap/<mode>/...

sim/tune/spur_paths.py found that the whole 25 MHz supply spur comes in through the ring inverters' VDD: vg's 3 pF
decap goes to VSS, so vg holds still while VDD ripples and the ring sees the ripple across it. An ideal 3 pF from vg
to VDD instead took the spur from -45.2 to -80.5 dBc (tt). This script checks the idea with real devices (no MIM on
TT GF: docs/platform.md) before it goes into the layout:

  cv      C(V) at the vg node of 737 um² of gate (today's decap, docs/ring_layout_v3.md: 6 x 30.71 / 4 um), all five
          corners, vg 1.4-2.4 V: (a) today: NMOS, gate vg, S/D/B VSS; (b) PMOS, gate vg, S/D/B VDD; (c) NMOS, gate VDD,
          S/D vg, B VSS (its junction C stays on VSS). Small-signal (.ac at 1 MHz) at each DC point.
  spur    the c4 bench (r12 clock charge, 4.48 pC per 25 MHz cycle, on the 1.32 ohm tile supply) at tt / ss / ff (the
          corners whose vbnf hold is known), code for 433.92 MHz: today against the PMOS decap to VDD (sized by cv).
  size    tt, ideal C from vg to VDD: 1, 2, 3, 4, 6 pF, and 3 pF split 2 to VDD + 1 to VSS (why 6 pF was worse).
  psr     tt, no macro: VDD = 3.3 V + 5 mV sine at 1, 3, 10, 25 and 60 MHz, and a +10 mV DC step: the ring's FM per mV
          of supply against frequency, today against the PMOS decap.
  pex     the extracted vco_top with its six decap fingers (NMOS, gate vg, S/D/B VSS) swapped for PMOS (gate vg,
          S/D/B on the VDD port): (a) the c4 spur bench on vco_top_rcx + the schematic medium DAC (vbnf held), tt / ss /
          ff, today against PMOS; (b) sim/tx/tb_tx_top.py's 'pg' / 'pgoff' cases (driver on / off behind TT's power
          switch) on vco_top_c with the PMOS decap (today's are in sim/tx/results/top.json).
  startup power-on from 0 V (VDD ramp 10 us; also 1 us at tt), every node from 0, the real vbn filter (no hold),
          5 corners x coarse code 0 / 31, word 512, 20 us: today against the PMOS decap. Ring start time, mode
          (a0 -> a2 phase), vg - VDD overshoot, f over the last 2 us.
"""
import argparse, json, math, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path += [str(REPO / "sim/tune"), str(REPO / "tools")]
import phase_c as pc, mdac_sim as ms  # noqa: E402
from rawread import read_raw  # noqa: E402

OUT = REPO / "build/tx_fine/vg_decap"
CORNERS = ("typical", "ss", "ff", "sf", "fs")
DEV = dict(w=30.71, l=4.0, m=6)          # today's decap gate: 737 um²
CVG_OLD = "Cvg vg 0 3e-12"


def mos(name, d, g, s, b, typ, w, l, m):
    a = w * 0.48
    return f"X{name} {d} {g} {s} {b} {typ} w={w}u l={l}u ad={a:.3f}p as={a:.3f}p pd={2*(w+0.48):.2f}u ps={2*(w+0.48):.2f}u m={m}\n"


def pmos_cap(m=DEV["m"]):
    """The proposal: PMOS, gate on vg, S/D/B (n-well) on vdd."""
    return mos("CVGP", "vdd", "vg", "vdd", "vdd", "pfet_03v3", DEV["w"], DEV["l"], m)


# ---------------------------------------------------------------------------------------------------------------- cv
def cv_deck(corner, kind):
    vs = " ".join(f"{v:.2f}" for v in np.arange(1.4, 2.401, 0.05))
    if kind == "nmos_vss":
        dut = mos("D", "0", "vg", "0", "0", "nfet_03v3", **DEV)
    elif kind == "pmos_vdd":
        dut = mos("D", "vdd", "vg", "vdd", "vdd", "pfet_03v3", **DEV)
    else:  # nmos_inv: gate VDD, S/D on vg, bulk VSS
        dut = mos("D", "vg", "vgate", "vg", "0", "nfet_03v3", **DEV)
    return f"""* C(V) {kind} {corner}
{ms.HDR.format(corner=corner)}vdd vdd 0 3.3
vgate vgate 0 3.3
vsrc vg 0 dc 1.9 ac 1
{dut}.option temp=27
.control
foreach v {vs}
  alter vsrc dc = $v
  ac lin 1 1meg 1meg
  let c = -imag(i(vsrc))/(2*pi*1e6)
  let cg = imag(i(vgate))/(2*pi*1e6)
  echo CV $v $&c $&cg
end
quit
.endc
.end
"""


def cv(a):
    jobs = [(OUT / "cv" / f"{k}_{c}", cv_deck(c, k)) for c in CORNERS for k in ("nmos_vss", "pmos_vdd", "nmos_inv")]
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(lambda dt: pc.run_one(*dt), jobs))
    res = {}
    for d, _ in jobs:
        rows = [ln.split()[1:] for ln in (d / "deck.log").read_text().splitlines() if ln.startswith("CV ")]
        res[d.name] = [[float(x) for x in r] for r in rows]
    (OUT / "cv" / "cv.json").write_text(json.dumps(res))
    print("C at the vg node (pF), 737 um² of gate; nmos_inv: total (to VDD)")
    print(f"{'vg (V)':>8s}" + "".join(f"{k[:8]:>10s}{c[:3]:>4s}" for k in ("nmos_vss", "pmos_vdd", "nmos_inv") for c in ("typical",)))
    for c in CORNERS:
        vg = ms.VG_OP[c]
        line = f"{c:8s} vg {vg:.2f}:"
        for k in ("nmos_vss", "pmos_vdd", "nmos_inv"):
            r = np.array(res[f"{k}_{c}"])
            cc = np.interp(vg, r[:, 0], r[:, 1]) * 1e12
            cg = np.interp(vg, r[:, 0], r[:, 2]) * 1e12
            line += f"  {k} {cc:.2f}" + (f" ({cg:.2f})" if k == "nmos_inv" else "")
        print(line)
    return res


# -------------------------------------------------------------------------------------------------------- c4 benches
def c4_deck(corner, code, cvg_line, qclk=pc.QCLK["q_r12"]):
    ctl = pc.static_ctl(512)
    bits = pc.sd_model.sd1(77, 8, int(4.2e-6 * pc.FCLK) + 2)
    ctl["sd"] = pc.pwl_bits(list(bits), 0.2e-6)
    ipk = 2 * qclk / 1e-9
    sup = "vsup vsup 0 3.3\nRpg vsup vdd 1.32\nCdec vdd 0 9.8p\n"
    imac = ("Imdc vdd 0 0.6m\n"
            f"Imclk vdd 0 PULSE(0 {ipk:.4g} 0.2u 0.5n 0.5n 0 40n)\n"
            "Imck vdd 0 PULSE(0 4.6m 0.2u 0.2n 0.2n 0 9.2n)\n")
    t = pc.ring_tran(corner, code, ctl, 4.2e-6, "v(a0) v(vdd) v(vg)", extra=imac, supply=sup)
    assert CVG_OLD + "\n" in t
    return t.replace(CVG_OLD + "\n", cvg_line)


def line25(raw, t0=1.25e-6, fm=pc.FCLK):
    """The phase line at fm (dBc, one sideband) by a least-squares tone fit (no window leakage), and f."""
    pl = read_raw(raw)[0]["vars"]
    t = np.real(pl["time"])
    tc = pc.crossings(t, np.real(pl["v(a0)"]), t0)
    k = np.arange(len(tc)); a, b = np.polyfit(k, tc, 1)
    phi = -2 * math.pi * (tc - (a * k + b)) / a
    w = 2 * math.pi * fm
    co = np.linalg.lstsq(np.c_[np.cos(w * tc), np.sin(w * tc), np.ones_like(tc), tc], phi, rcond=None)[0]
    amp = math.hypot(co[0], co[1])
    return 20 * math.log10(amp / 2 + 1e-15), 1 / a, amp


def spur(a):
    jobs = []
    for c in ("typical", "ss", "ff"):
        code = ms.CODE433[c]
        jobs += [(OUT / "spur" / f"{c}_today", c4_deck(c, code, CVG_OLD + "\n")),
                 (OUT / "spur" / f"{c}_pmos", c4_deck(c, code, pmos_cap(a.m)))]
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(lambda dt: pc.run_one(*dt), jobs))
    res = {}
    for d, _ in jobs:
        ok, bad = pc.log_ok(d)
        if not ok:
            res[d.name] = dict(error=bad); print(d.name, bad); continue
        s25, f, _ = line25(d / "out.raw"); s50, _, _ = line25(d / "out.raw", fm=50e6)
        res[d.name] = dict(spur25=s25, spur50=s50, f=f)
        print(f"{d.name:14s} 25 MHz {s25:6.1f} dBc   50 MHz {s50:6.1f} dBc   f {f/1e6:.3f} MHz")
    (OUT / "spur" / "spur.json").write_text(json.dumps(res, indent=1))


def size(a):
    cases = {f"c{c:g}p": f"Cvg vg vdd {c}e-12\n" for c in (1, 2, 3, 4, 6)}
    cases["split2v1g"] = "Cvg vg vdd 2e-12\nCvg2 vg 0 1e-12\n"
    jobs = [(OUT / "size" / k, c4_deck("typical", 9, v)) for k, v in cases.items()]
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(lambda dt: pc.run_one(*dt), jobs))
    res = {}
    for d, _ in jobs:
        s25, f, _ = line25(d / "out.raw"); s50, _, _ = line25(d / "out.raw", fm=50e6)
        res[d.name] = dict(spur25=s25, spur50=s50, f=f)
        print(f"{d.name:10s} 25 MHz {s25:6.1f} dBc   50 MHz {s50:6.1f} dBc   f {f/1e6:.3f} MHz")
    (OUT / "size" / "size.json").write_text(json.dumps(res, indent=1))


# ----------------------------------------------------------------------------------------------------------- psr
PSR_F = (1e6, 3e6, 10e6, 25e6, 60e6)


def psr_deck(cvg_line, fm=None, dv=0.0):
    sup = f"vdd vdd 0 SIN(3.3 5m {fm:g} 0.3u)\n" if fm else f"vdd vdd 0 {3.3 + dv:.4f}\n"
    t = pc.ring_tran("typical", 9, pc.static_ctl(512), 2.6e-6, "v(a0) v(vdd) v(vg)", supply=sup)
    return t.replace(CVG_OLD + "\n", cvg_line)


def psr(a):
    jobs = []
    for tag, ln in (("today", CVG_OLD + "\n"), ("pmos", pmos_cap(a.m))):
        jobs += [(OUT / "psr" / f"{tag}_dc0", psr_deck(ln)), (OUT / "psr" / f"{tag}_dc10", psr_deck(ln, dv=0.010))]
        jobs += [(OUT / "psr" / f"{tag}_{fm/1e6:g}M", psr_deck(ln, fm)) for fm in PSR_F]
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(lambda dt: pc.run_one(*dt), jobs))
    res = {}
    for tag in ("today", "pmos"):
        _, f0, _ = line25(OUT / "psr" / f"{tag}_dc0" / "out.raw", t0=0.6e-6)
        _, f1, _ = line25(OUT / "psr" / f"{tag}_dc10" / "out.raw", t0=0.6e-6)
        r = {"dc": (f1 - f0) / 10.0}                          # Hz per mV
        for fm in PSR_F:
            _, _, amp = line25(OUT / "psr" / f"{tag}_{fm/1e6:g}M" / "out.raw", t0=0.6e-6, fm=fm)
            r[f"{fm/1e6:g}M"] = amp * fm / 5.0                 # peak FM (Hz) per mV of supply sine
        res[tag] = r
        print(tag, "  ".join(f"{k}: {v/1e3:.2f} kHz/mV" for k, v in r.items()))
    (OUT / "psr" / "psr.json").write_text(json.dumps(res, indent=1))


# ------------------------------------------------------------------------------------------------------- start-up
def startup_deck(corner, code, cvg_line, tramp):
    ms.VBNF.setdefault(corner, ms.VBNF["typical"])                      # placeholder: the hold is removed below
    ramp = f"PWL(0 0 {tramp:g} 3.3)"
    t = pc.ring_tran(corner, code, pc.static_ctl(512), 20e-6, "v(vdd) v(vg) v(vbnf) v(a0) v(a2)")
    t = t.replace(CVG_OLD + "\n", cvg_line)
    t = re.sub(r"^vhold .*\n", "", t, flags=re.M)                       # the real vbn filter
    t = re.sub(r"^\.ic .*\n", "", t, flags=re.M)                        # every node from 0
    t = re.sub(r"^vdd vdd 0 3\.3$", f"vdd vdd 0 {ramp}", t, flags=re.M)
    t = re.sub(r"^(v(?:bit|bitb|n)\w*\s+\S+\s+0)\s+3\.3$", rf"\1 {ramp}", t, flags=re.M)   # logic highs ramp with VDD
    t = t.replace("tran 5p 2e-05 0 5p", "tran 20p 2e-05 0 20p uic")
    assert "uic" in t, "tran line not found"
    return t


def startup(a):
    jobs = []
    for c in CORNERS:
        for code in (0, 31):
            for tag, ln in (("today", CVG_OLD + "\n"), ("pmos", pmos_cap(a.m))):
                jobs.append((OUT / "startup" / f"{c}_c{code}_r10_{tag}", startup_deck(c, code, ln, 10e-6)))
    for code in (0, 31):
        for tag, ln in (("today", CVG_OLD + "\n"), ("pmos", pmos_cap(a.m))):
            jobs.append((OUT / "startup" / f"typical_c{code}_r1_{tag}", startup_deck("typical", code, ln, 1e-6)))
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(lambda dt: pc.run_one(*dt), jobs))
    res = {}
    for d, _ in jobs:
        ok, bad = pc.log_ok(d)
        if not ok:
            res[d.name] = dict(error=bad); print(d.name, bad); continue
        pl = read_raw(d / "out.raw")[0]["vars"]
        t = np.real(pl["time"]); vdd, vg, a0, a2 = (np.real(pl[f"v({n})"]) for n in ("vdd", "vg", "a0", "a2"))
        mid = 0.5 * (vdd + vg)
        r0 = np.where((a0[:-1] < mid[:-1]) & (a0[1:] >= mid[1:]))[0]
        r2 = np.where((a2[:-1] < mid[:-1]) & (a2[1:] >= mid[1:]))[0]
        tr0, tr2 = t[r0], t[r2]
        late = tr0[tr0 > t[-1] - 2e-6]
        if len(late) < 10:
            res[d.name] = dict(stuck=True); print(d.name, "STUCK"); continue
        gaps = np.diff(tr0)
        bad_i = np.where(gaps > 100e-9)[0]
        t_osc = float(tr0[bad_i[-1] + 1]) if len(bad_i) else float(tr0[0])
        f = (len(late) - 1) / (late[-1] - late[0])
        ph = [((tr2[tr2 > x][0] - x) * f) % 1 for x in late[:-1] if np.any(tr2 > x)]
        res[d.name] = dict(t_osc=t_osc, f=float(f), mode=float(np.mean(ph)), vg_over_vdd=float(np.max(vg - vdd)),
                           vdd_minus_vg_min_late=float(np.min((vdd - vg)[t > t[-1] - 2e-6])))
        r = res[d.name]
        print(f"{d.name:26s} t_osc {r['t_osc']*1e6:5.2f} us  f {r['f']/1e6:7.2f} MHz  mode {r['mode']:.3f}"
              f"  max(vg-vdd) {r['vg_over_vdd']*1e3:6.1f} mV")
    (OUT / "startup" / "startup.json").write_text(json.dumps(res, indent=1))


# --------------------------------------------------------------------------------------------------- extracted
DECAP_RX = r"^(X\S+) (VSS\S*) (vg\S*) (VSS\S*) (VSS\S*) nfet_03v3 .*w=30\.71u l=4u$"


def pmos_netlist(kind):
    """vco_top_<kind>.spice with the vg decap fingers as PMOS to the VDD port."""
    src = (REPO / f"layout/pex/vco_top_{kind}.spice").read_text()
    new, n = re.subn(DECAP_RX, r"\1 VDD \3 VDD VDD pfet_03v3 ad=8.5988p pd=31.27u as=8.5988p ps=31.27u w=30.71u l=4u",
                     src, flags=re.M)
    assert n == 6, f"{n} decap fingers in vco_top_{kind}"
    out = OUT / "pex" / f"vco_top_{kind}_pmos.spice"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(new)
    return out


def pex_c4_deck(corner, pmos):
    code = pc.PEX_CODE[corner] if hasattr(pc, "PEX_CODE") else ms.CODE433[corner]
    t = pc.pex_deck(corner, code, 512, tstop=4.2e-6)
    ipk = 2 * pc.QCLK["q_r12"] / 1e-9
    sup = ("vsup vsup 0 3.3\nRpg vsup vdd 1.32\nCdec vdd 0 9.8p\nImdc vdd 0 0.6m\n"
           f"Imclk vdd 0 PULSE(0 {ipk:.4g} 0.2u 0.5n 0.5n 0 40n)\nImck vdd 0 PULSE(0 4.6m 0.2u 0.2n 0.2n 0 9.2n)\n"
           f"vhold vbnf 0 {ms.VBNF[corner]}\n")
    assert "vdd vdd 0 3.3\n" in t
    t = t.replace("vdd vdd 0 3.3\n", sup)
    t = t.replace("save v(a0) v(vg)", "save v(a0) v(vg) v(vdd)").replace("write out.raw v(a0) v(vg)", "write out.raw v(a0) v(vg) v(vdd)")
    if pmos:
        t = t.replace(str(REPO / "layout/pex/vco_top_rcx.spice"), str(pmos_netlist("rcx")))
    return t


def pex(a):
    sys.path += [str(REPO / "sim/tx"), str(REPO / "sim/top"), str(REPO / "sim/lsdiv")]
    import tb_tx_top as tbt, top_pex as TP
    TP.PEX["cp"] = pmos_netlist("c")
    tbt.OUT = OUT / "pex" / "tx"
    jobs = [(OUT / "pex" / f"c4_{c}_{tag}", pex_c4_deck(c, tag == "pmos")) for c in ("typical", "ss", "ff")
            for tag in ("today", "pmos")]
    tx = {f"{c}_{case}": dict(pex="cp", corner=c, case=case) for c in ("typical", "ss", "ff") for case in ("pg", "pgoff")}
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        fs = [ex.submit(pc.run_one, *j) for j in jobs] + [ex.submit(tbt.run1, k, kw, 1.2e-6) for k, kw in tx.items()]
        [f.result() for f in fs]
    res = {}
    for d, _ in jobs:
        ok, bad = pc.log_ok(d)
        if not ok:
            res[d.name] = dict(error=bad); print(d.name, bad); continue
        s25, f, _ = line25(d / "out.raw", t0=1.7e-6); s50, _, _ = line25(d / "out.raw", t0=1.7e-6, fm=50e6)
        res[d.name] = dict(spur25=s25, spur50=s50, f=f)
        print(f"{d.name:18s} 25 MHz {s25:6.1f} dBc   50 MHz {s50:6.1f} dBc   f {f/1e6:.3f} MHz")
    old = {r["name"]: r for r in json.loads((REPO / "sim/tx/results/top.json").read_text())}
    for c in ("typical", "ss", "ff"):
        r = {case: tbt.analyse(f"{c}_{case}") for case in ("pg", "pgoff")}
        o = {case: old.get(f"c_{c}_{case}", {}) for case in ("pg", "pgoff")}
        sh = r["pg"]["f_a0"] / r["pgoff"]["f_a0"] - 1
        osh = o["pg"]["f_a0"] / o["pgoff"]["f_a0"] - 1 if o["pg"] and o["pgoff"] else float("nan")
        res[f"tx_{c}"] = dict(new={k: {q: v.get(q) for q in ("f_a0", "jit_rms_ps", "vdd_ripple_mv", "p1_dbm", "flags")}
                                   for k, v in r.items()}, shift_new=sh, shift_old=osh)
        print(f"tx {c:8s} driver-on shift {sh*100:+.3f} % (today {osh*100:+.3f} %)  jitter on {r['pg']['jit_rms_ps']:.2f} ps"
              f" (today {o['pg'].get('jit_rms_ps', float('nan')):.2f})  P1 {r['pg']['p1_dbm']:+.2f} dBm"
              f" (today {o['pg'].get('p1_dbm', float('nan')):+.2f})")
    (OUT / "pex" / "pex.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["cv", "spur", "size", "psr", "startup", "pex", "all"])
    ap.add_argument("--jobs", type=int, default=28)
    ap.add_argument("--m", type=int, default=DEV["m"], help="PMOS decap fingers (30.71 / 4 um each)")
    a = ap.parse_args()
    for mode in (["cv", "spur", "size", "psr", "startup"] if a.mode == "all" else [a.mode]):
        print(f"== {mode}")
        globals()[mode](a)
