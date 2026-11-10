#!/usr/bin/env python3
"""Phase C transistor-level checks of the fine-tuning path (docs/handoff_tx_fine_tune.md, docs/tx_fine_tune.md).

    python3 sim/tune/phase_c.py driver [--jobs 24]      # every job below, chained; build/tx_fine/status.txt, DONE / FAILED
    python3 sim/tune/phase_c.py summary                 # tables from the job outputs -> build/tx_fine/phase_c.json

Jobs (27 C, VDD 3.3 V; ring = vco_bias netlist with the 2026-11-08 reference + RC filter, medium DAC = mdac_sim):
  c1 fword_pex : the extracted vco_top (layout/pex/vco_top_rcx.spice, re-extracted with the vbnf port) + schematic
                 medium DAC: f at words 0 / 512 / 513 / 1023, tt / ss / ff at codes 9 / 11 / 7     -> real LSB, range
  c2 sd        : schematic ring + DAC, tt, 4.2 us: word 512 (SD off), 513, and 512 + fraction 77 / 128 with the
                 SD bitstream (sd_model.sd1, 25 MHz clock) on the SD cell   -> mean f vs the fraction, spurs vs model
  c3 inject    : tt / ss: word 511 -> 512 at 0.6 us (the major carry), SD fraction 128 from 1.2 us  -> vbnf / vg / mo
  c4 supply    : tt: the ring's VDD through the 1.32 ohm tile power switch with 9.8 pF of decap and the macro's
                 current (1.0 mA mean, pulses at the 25 MHz clk and the 108 MHz ck edges)   -> FM spurs from digital
  c5 fsk       : tt: word 509 -> 515 at 1.0 us -> 509 at 2.0 us (+/- 3 LSB, about +/- 100 kHz)   -> step and settling
FM noise with the DAC is the .noise result of sim/tune/mdac_sim.py noise (Table IV of docs/tx_fine_tune.md).
Frequencies come from a0's mid-swing rising crossings; the phase deviation at each crossing gives the spur spectrum
(one sideband: 20 log10 of the phase line, as sd_model.py).
"""
import argparse, json, math, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "sim/tune"))
sys.path.insert(0, str(REPO / "sim/vco"))
sys.path.insert(0, str(REPO / "tools"))
import mdac_sim as ms  # noqa: E402
import sd_model  # noqa: E402
import vco_bias as vb  # noqa: E402
from rawread import read_raw  # noqa: E402

OUT = REPO / "build/tx_fine"
OSIC = str(REPO / "tools/osic-mac")
FCLK = 25e6
PEX_CODE = {"typical": 9, "ss": 11, "ff": 7}
VBN0 = dict(typical=1.232, ss=1.384, ff=1.083)


def status(msg):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "status.txt").write_text(f"{time.strftime('%H:%M:%S')} {msg}\n")
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# ---------------------------------------------------------------------------------------------------------
def pwl_bits(bits, t0, tclk=1 / FCLK, tr=100e-12, vdd=3.3, active_low=True):
    """PWL of a bitstream starting at t0 (one bit per clock); active low: bit 1 -> 0 V."""
    lv = lambda b: (0.0 if b else vdd) if active_low else (vdd if b else 0.0)
    pts = [(0.0, lv(0))]
    prev = 0
    for k, b in enumerate(bits):
        t = t0 + k * tclk
        if b != prev:
            pts += [(t, lv(prev)), (t + tr, lv(b))]
            prev = b
    return "PWL(" + " ".join(f"{t:.4e} {v:g}" for t, v in pts) + ")"


def word_pwl(name, steps, vdd=3.3, tr=100e-12):
    """PWL for group `name`'s active-low line over a list of (t, word, sd) steps (first step at t = 0)."""
    pts = []
    prev = None
    for t, w, sd in steps:
        v = vdd * (1 - ms.word_bits(w, sd)[name])
        if prev is None:
            pts.append((0.0, v))
        elif v != prev:
            pts += [(t, prev), (t + tr, v)]
        prev = v
    return "PWL(" + " ".join(f"{t:.4e} {v:g}" for t, v in pts) + ")" if len(pts) > 1 else f"{pts[0][1]:g}"


def ring_tran(corner, code, ctl, tstop, save, extra="", supply="vdd vdd 0 3.3\n", temp=27):
    """Schematic ring + reference + filter + coarse DAC + medium DAC; ctl: {group: source value/PWL}."""
    p = ms.base_p()
    body, ics = vb.netlist(p)
    src = "".join(f"vbit{b} bit{b} 0 {3.3 if (code >> b) & 1 else 0}\nvbitb{b} bitb{b} 0 {0 if (code >> b) & 1 else 3.3}\n"
                  for b in range(p["bits"]))
    rv = f"XRV vctrl 0 0 ppolyf_u_1k r_width=1e-6 r_length={ms.rv_length(ms.M['rv']):.2f}e-6\n"
    md = ms.mdac_netlist(p, ms.M, g=vb.gnet(p))
    cs = "".join(f"vn{k} n{k} 0 {v}\n" for k, v in ctl.items())
    return f"""* phase C {corner} code {code}
{ms.HDR.format(corner=corner)}{supply}{rv}{src}{body}vam vg vgo 0
{md}{cs}{extra}.ic {ics}
.option temp={temp}
.control
save {save}
tran 5p {tstop} 0 5p
set filetype=binary
write out.raw {save}
quit
.endc
.end
"""


def static_ctl(word, sd=0):
    st = ms.word_bits(word, sd)
    return {k: f"{3.3 * (1 - v):g}" for k, v in st.items() if k != "off"}


def run_one(d, text):
    d.mkdir(parents=True, exist_ok=True)
    (d / ".spiceinit").write_text("set ng_nomodcheck\nset num_threads=1\noption noinit\n")
    (d / "deck.cir").write_text(text)
    (d / "out.raw").unlink(missing_ok=True)
    t = time.time()
    subprocess.run([OSIC, "bash", "-c", f"cd {d} && ngspice -b deck.cir > deck.log 2>&1"], check=False)
    (d / "runtime.txt").write_text(f"{time.time() - t:.0f}\n")
    return d


def log_ok(d):
    lg = (d / "deck.log").read_text(errors="replace").lower() if (d / "deck.log").exists() else "missing"
    bad = [w for w in ("singular", "timestep too small", "transient op started", "error") if w in lg]
    return (d / "out.raw").exists() and not bad, bad


# ---------------------------------------------------------------------------------------------------------
def crossings(t, v, t0=0.0):
    lvl = 0.5 * (v[t > t0].min() + v[t > t0].max())
    i = np.where((v[:-1] < lvl) & (v[1:] >= lvl) & (t[:-1] >= t0))[0]
    return t[i] + (lvl - v[i]) / (v[i + 1] - v[i]) * (t[i + 1] - t[i])


def freq_track(tc):
    """(t mid, f) per period."""
    T = np.diff(tc)
    return 0.5 * (tc[1:] + tc[:-1]), 1 / T


def phase_spurs(tc, f_lo=10e3, f_hi=30e6, nmax=8):
    """Phase deviation at each crossing (linear fit removed) -> one-sided phase lines (dBc) between f_lo and f_hi."""
    k = np.arange(len(tc))
    a, b = np.polyfit(k, tc, 1)
    phi = -2 * math.pi * (tc - (a * k + b)) / a           # rad
    n = len(phi)
    w = np.hanning(n)
    S = np.fft.rfft((phi - phi.mean()) * w) / w.sum()   # peak-normalised (coherent gain)
    f = np.fft.rfftfreq(n, d=a)
    amp = np.abs(S)                                        # = phase line (half the sinusoid's peak) for a tone
    sel = (f >= f_lo) & (f <= f_hi)
    idx = np.argsort(amp[sel])[::-1][:nmax]
    return [(float(f[sel][i]), 20 * math.log10(max(amp[sel][i], 1e-15))) for i in idx], float(np.std(phi))


# ---------------------------------------------------------------------------------------------------------
def jobs_c2():
    d0 = OUT / "c2"
    out = []
    t0 = 0.2e-6
    for tag, word, frac in (("w512", 512, None), ("w513", 513, None), ("f77", 512, 77), ("f128", 512, 128)):
        ctl = static_ctl(word)
        if frac is not None:
            bits = sd_model.sd1(frac, 8, int(4.2e-6 * FCLK) + 2)
            ctl["sd"] = pwl_bits(list(bits), t0)
        out.append((d0 / tag, ring_tran("typical", 9, ctl, 4.2e-6, "v(a0) v(vg) v(vbnf) v(mo)")))
    return out


def jobs_c3():
    out = []
    for corner, code in (("typical", 9), ("ss", 11)):
        steps = [(0, 511, 0), (0.6e-6, 512, 0)]
        ctl = {k: word_pwl(k, steps) for k in ms.word_bits(0) if k not in ("off", "sd")}
        bits = sd_model.sd1(128, 8, int(0.8e-6 * FCLK) + 2)
        ctl["sd"] = pwl_bits(list(bits), 1.2e-6)
        out.append((OUT / "c3" / corner, ring_tran(corner, code, ctl, 2.0e-6, "v(a0) v(vg) v(vbnf) v(mo) v(pb) v(md)")))
    return out


def jobs_c4():
    ctl = static_ctl(512)
    bits = sd_model.sd1(77, 8, int(4.2e-6 * FCLK) + 2)
    ctl["sd"] = pwl_bits(list(bits), 0.2e-6)
    # tile supply: 3.3 V through the 1.32 ohm power switch onto node vdd, 9.8 pF decap (tx_drv), the macro's current
    # (5.8 mW at 50 / 140 MHz from LibreLane's tt power report, scaled to 25 MHz clk / 108 MHz ck: about 1 mA mean):
    # 0.6 mA DC + a 1 ns triangle at each clk edge (0.3 mA mean) + a 0.4 ns triangle at each ck edge (0.1 mA mean)
    sup = "vsup vsup 0 3.3\nRpg vsup vdd 1.32\nCdec vdd 0 9.8p\n"
    imac = ("Imdc vdd 0 0.6m\n"
            "Imclk vdd 0 PULSE(0 24m 0.2u 0.5n 0.5n 0 40n)\n"
            "Imck vdd 0 PULSE(0 4.6m 0.2u 0.2n 0.2n 0 9.2n)\n")
    return [(OUT / "c4" / "supply", ring_tran("typical", 9, ctl, 4.2e-6, "v(a0) v(vdd) v(vg)", extra=imac, supply=sup))]


def jobs_c5():
    steps = [(0, 509, 0), (1.0e-6, 515, 0), (2.0e-6, 509, 0)]
    ctl = {k: word_pwl(k, steps) for k in ms.word_bits(0) if k not in ("off",)}
    return [(OUT / "c5" / "fsk", ring_tran("typical", 9, ctl, 3.0e-6, "v(a0) v(vg) v(mo)"))]


def pex_deck(corner, code, word, sd=0, tstop=300e-9):
    """Extracted vco_top (rcx, vbnf port) + schematic medium DAC on its vg / vbnf ports."""
    p = ms.base_p()
    bits = "".join(f"vbit{i} bit{i} 0 {3.3 if (code >> i) & 1 else 0}\nvbitb{i} bitb{i} 0 {0 if (code >> i) & 1 else 3.3}\n"
                   for i in range(5))
    ports = re.search(r"^\.subckt vco_top (.*)$", (REPO / "layout/pex/vco_top_rcx.spice").read_text(), re.M).group(1).split()
    conn = dict(VDD="vdd", VDD_LS="vdd", VSS="0", vctrl="vctrl", ck="ck", a0="a0", vbn="vbn", vg="vg", ls="ls", vbnf="vbnf",
                **{f"bit{i}": f"bit{i}" for i in range(5)}, **{f"bitb{i}": f"bitb{i}" for i in range(5)})
    md = ms.mdac_netlist(p, ms.M, g="vbnf").replace(" vgo ", " vg ")
    cs = "".join(f"vn{k} n{k} 0 {v}\n" for k, v in static_ctl(word, sd).items())
    rv = f"XRV vctrl 0 0 ppolyf_u_1k r_width=1e-6 r_length={ms.rv_length(ms.M['rv']):.2f}e-6\n"
    return f"""* pex fword {corner} code {code} word {word}
{ms.HDR.format(corner=corner)}vdd vdd 0 3.3
{rv}{bits}Xtop {' '.join(conn[q] for q in ports)} vco_top
.include {REPO / 'layout/pex/vco_top_rcx.spice'}
Cwire ck 0 20f
{md}{cs}.ic v(a0)=0 v(vbn)={VBN0[corner]} v(vbnf)={VBN0[corner]}
.option temp=27
.control
save v(a0) v(vg)
tran 5p {tstop} {0.4 * tstop} 5p
set filetype=binary
write out.raw v(a0) v(vg)
quit
.endc
.end
"""


def jobs_c1():
    return [(OUT / "c1" / f"{c}_w{w}", pex_deck(c, PEX_CODE[c], w)) for c in ("typical", "ss", "ff") for w in (0, 512, 513, 1023)]


# ---------------------------------------------------------------------------------------------------------
def analyse():
    res = {}
    # c1
    c1 = {}
    for c in ("typical", "ss", "ff"):
        fs = {}
        for w in (0, 512, 513, 1023):
            d = OUT / "c1" / f"{c}_w{w}"
            ok, bad = log_ok(d)
            if not ok:
                fs[w] = None; continue
            pl = read_raw(d / "out.raw")[0]["vars"]
            tc = crossings(np.real(pl["time"]), np.real(pl["v(a0)"]))
            fs[w] = (len(tc) - 1) / (tc[-1] - tc[0])
        if all(v is not None for v in fs.values()):
            c1[c] = dict(f0=fs[0], f512=fs[512], f1023=fs[1023], lsb_fs=(fs[1023] - fs[0]) / 1023, lsb_512=fs[513] - fs[512])
    res["c1"] = c1
    # c2
    c2 = {}
    for tag in ("w512", "w513", "f77", "f128"):
        d = OUT / "c2" / tag
        ok, bad = log_ok(d)
        if not ok:
            c2[tag] = dict(error=bad); continue
        pl = read_raw(d / "out.raw")[0]["vars"]
        t, v = np.real(pl["time"]), np.real(pl["v(a0)"])
        tc = crossings(t, v, 0.25e-6)
        sp, prms = phase_spurs(tc)
        c2[tag] = dict(f=(len(tc) - 1) / (tc[-1] - tc[0]), spurs=sp[:4], phase_rms=prms)
    if all("f" in c2.get(k, {}) for k in ("w512", "w513", "f77", "f128")):
        lsb = c2["w513"]["f"] - c2["w512"]["f"]
        for tag, fr in (("f77", 77), ("f128", 128)):
            c2[tag]["expected"] = c2["w512"]["f"] + lsb * fr / 256
            c2[tag]["err_hz"] = c2[tag]["f"] - c2[tag]["expected"]
        c2["lsb"] = lsb
        y = sd_model.sd1(77, 8, 256)
        c2["model_f77"] = sd_model.metrics(y, 77, 8, lsb, FCLK)
    res["c2"] = c2
    # c3
    c3 = {}
    for corner in ("typical", "ss"):
        d = OUT / "c3" / corner
        ok, bad = log_ok(d)
        if not ok:
            c3[corner] = dict(error=bad); continue
        pl = read_raw(d / "out.raw")[0]["vars"]
        t = np.real(pl["time"])
        r = {}
        for n in ("v(vbnf)", "v(vg)", "v(mo)", "v(pb)"):
            v = np.real(pl[n])
            b0 = v[(t > 0.45e-6) & (t < 0.59e-6)].mean()
            win = (t > 0.6e-6) & (t < 1.1e-6)
            r[n] = dict(before=float(b0), peak_dev=float(np.abs(v[win] - b0).max()),
                        after=float(v[(t > 1.0e-6) & (t < 1.19e-6)].mean()),
                        sd_ripple_pp=float(np.ptp(v[(t > 1.5e-6)])))
        tc = crossings(t, np.real(pl["v(a0)"]), 0.25e-6)
        tm, f = freq_track(tc)
        r["f_before"] = float(f[(tm > 0.4e-6) & (tm < 0.59e-6)].mean())
        r["f_after"] = float(f[(tm > 0.9e-6) & (tm < 1.19e-6)].mean())
        c3[corner] = r
    res["c3"] = c3
    # c4
    d = OUT / "c4" / "supply"
    ok, bad = log_ok(d)
    if ok:
        pl = read_raw(d / "out.raw")[0]["vars"]
        t = np.real(pl["time"])
        tc = crossings(t, np.real(pl["v(a0)"]), 0.25e-6)
        sp, prms = phase_spurs(tc)
        vdd = np.real(pl["v(vdd)"])[t > 0.3e-6]
        res["c4"] = dict(f=(len(tc) - 1) / (tc[-1] - tc[0]), spurs=sp[:6], phase_rms=prms,
                         vdd_mean=float(vdd.mean()), vdd_pp=float(np.ptp(vdd)))
    else:
        res["c4"] = dict(error=bad)
    # c5
    d = OUT / "c5" / "fsk"
    ok, bad = log_ok(d)
    if ok:
        pl = read_raw(d / "out.raw")[0]["vars"]
        t = np.real(pl["time"])
        tc = crossings(t, np.real(pl["v(a0)"]), 0.25e-6)
        tm, f = freq_track(tc)
        # 20 ns windows
        edges = np.arange(0.3e-6, 3.0e-6, 20e-9)
        fw = [float(f[(tm >= a) & (tm < a + 20e-9)].mean()) for a in edges]
        lo = np.mean([x for a, x in zip(edges, fw) if 0.6e-6 < a < 0.98e-6])
        hi = np.mean([x for a, x in zip(edges, fw) if 1.6e-6 < a < 1.98e-6])
        dev = hi - lo
        # settling: first window after the step within 2 % of the step of the final value
        def settle(t0, final):
            for a, x in zip(edges, fw):
                if a >= t0 and all(abs(y - final) < 0.02 * abs(dev) for b, y in zip(edges, fw) if a <= b < t0 + 0.9e-6):
                    return a - t0
            return None
        res["c5"] = dict(f_lo=lo, f_hi=hi, dev=dev, settle_up=settle(1.0e-6, hi), settle_dn=settle(2.0e-6, lo),
                         track=list(zip([float(a) for a in edges], fw)))
        np.savetxt(OUT / "c5_track.txt", np.c_[tm, f])
    else:
        res["c5"] = dict(error=bad)
    (OUT / "phase_c.json").write_text(json.dumps(res, indent=1))
    return res


def driver(a):
    (OUT / "DONE").unlink(missing_ok=True); (OUT / "FAILED").unlink(missing_ok=True)
    try:
        status("step 1/3: re-extract vco_top (rc, magic 8.3.642, rcfix) for the vbnf port + schematic-DAC benches c2-c5")
        sch = jobs_c2() + jobs_c3() + jobs_c4() + jobs_c5()
        ex = ThreadPoolExecutor(max_workers=a.jobs)
        futs = [ex.submit(run_one, d, t) for d, t in sch]
        r = subprocess.run([OSIC, "bash", "-c", f"cd {REPO} && MAGIC=$HOME/.local/magic642/bin/magic bash layout/gen/pex_top.sh rc"],
                           capture_output=True, text=True)
        (OUT / "pex_top.log").write_text(r.stdout + r.stderr)
        txt = (REPO / "layout/pex/vco_top_rcx.spice").read_text()
        if "vbnf" not in re.search(r"^\.subckt vco_top (.*)$", txt, re.M).group(1):
            raise RuntimeError("vco_top_rcx.spice has no vbnf port (see build/tx_fine/pex_top.log)")
        status("step 2/3: extracted vco_top + DAC f vs word (tt/ss/ff), schematic benches running")
        futs += [ex.submit(run_one, d, t) for d, t in jobs_c1()]
        for f in futs:
            f.result()
        bad = [(str(d.relative_to(OUT)), log_ok(d)[1]) for d, _ in sch + jobs_c1() if not log_ok(d)[0]]
        if bad:
            raise RuntimeError(f"runs failed: {bad}")
        status("step 3/3: analysis")
        res = analyse()
        (OUT / "DONE").write_text(json.dumps({k: (v if k != "c5" else {x: y for x, y in v.items() if x != 'track'})
                                              for k, v in res.items()}, indent=1)[:4000] + "\n")
        status("DONE")
    except Exception as e:
        (OUT / "FAILED").write_text(f"{e}\n")
        status(f"FAILED: {e}")
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["driver", "summary"])
    ap.add_argument("--jobs", type=int, default=22)
    a = ap.parse_args()
    if a.mode == "driver":
        driver(a)
    else:
        print(json.dumps(analyse(), indent=1)[:6000])


if __name__ == "__main__":
    main()
