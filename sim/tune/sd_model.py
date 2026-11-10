#!/usr/bin/env python3
"""Behavioural sigma-delta (SD) model for the medium DAC's fractional bits (docs/tx_fine_tune.md, phase A).

The VCO frequency error is LSB x (y[n] - x), with y[n] the modulator's integer output added to the DAC word and x
the fractional input, held for one clock (zero-order hold). The phase is its integral. Every deterministic
modulator here with nfrac-bit accumulators is periodic in 2^(order*nfrac) clocks, so a rectangular window of that
length gives exact spectral lines (no leakage). The line at f_k = k fclk / N of the held frequency error has the
complex amplitude c_k = DFT_k(e)/N x sinc(k/N) (the hold), and the phase line is c_k / (j f_k); one sideband of a
small phase modulation is |phi_k| below the carrier (dBc = 20 log10 |phi_k|, single sideband, the phase line
amplitude phi_k being half the sinusoid's peak).

The VCO's own response (the vg node's RC, about 3 pF on the ring) low-passes the frequency error; it is ignored
here, so the numbers are an upper bound.

    python3 sim/tune/sd_model.py sweep  [--lsb 50e3] [--fclk 25e6] [--nfrac 8]   # all fractions, each modulator
    python3 sim/tune/sd_model.py bits --frac 77 --n 64                            # print a bitstream (cocotb reference)
Outputs: build/tx_fine/sd/*.json, docs/img/tx_fine_sd_*.png (with --plot)
"""
import argparse, json, math
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]


def sd1(frac, nfrac, n, acc0=0):
    """First-order SD (one accumulator), exactly as src/: acc <= (acc + frac) mod 2^nfrac, y = carry out.
    Returns y[0..n-1] (y[i] is the carry of the i-th addition, applied in clock i)."""
    m = 1 << nfrac
    i = np.arange(1, n + 1, dtype=np.int64)
    s = acc0 + i * frac
    return ((s >> nfrac) - ((s - frac) >> nfrac)).astype(np.int64)


def mash11(frac, nfrac, n):
    """MASH 1-1: y = c1[n] + c2[n] - c2[n-1]; values -1..2."""
    m = 1 << nfrac
    a1 = a2 = 0
    y = np.zeros(n, np.int64)
    c2p = 0
    for k in range(n):
        s1 = a1 + frac; c1 = s1 >> nfrac; a1 = s1 & (m - 1)
        s2 = a2 + a1; c2 = s2 >> nfrac; a2 = s2 & (m - 1)
        y[k] = c1 + c2 - c2p; c2p = c2
    return y


def sd1_dither(frac, nfrac, n, seed=1):
    """First-order SD with a 1-bit LFSR dither added to the accumulator input's LSB (mean +1/2 LSB of the fraction,
    removed by using frac - 1/2 effectively: the input is 2*frac + d in nfrac+1 bits)."""
    rng = np.random.default_rng(seed)
    d = rng.integers(0, 2, n)
    m = 1 << (nfrac + 1)
    acc = 0
    y = np.zeros(n, np.int64)
    for k in range(n):
        s = acc + 2 * frac + d[k] - (k & 1) * 0   # +d has mean 1/2 of the new LSB: a 1/2^(nfrac+2) offset, ignored
        y[k] = s >> (nfrac + 1); acc = s & (m - 1)
    return y


MODS = {"sd1": (sd1, 1), "mash11": (mash11, 2)}


def lines(e, fclk):
    """Exact lines of a periodic held frequency error e (Hz per clock), period len(e).
    Returns f (Hz), c (Hz, complex frequency line), phi (rad, complex phase line) for k = 1..N/2 and their images
    up to 2 fclk."""
    n = len(e)
    E = np.fft.fft(e) / n
    k = np.arange(1, 2 * n)                     # up to 2 fclk (images of the hold)
    f = k * fclk / n
    c = E[k % n] * np.sinc(k / n)
    return f, c, c / (1j * f)


def metrics(y, frac, nfrac, lsb, fclk, f_lo=10e3, f_hi=30e6, fm_band=(1e3, 100e3)):
    x = frac / (1 << nfrac)
    e = lsb * (y - x)
    f, c, phi = lines(e, fclk)
    sel = (f >= f_lo) & (f <= f_hi)
    a = np.abs(phi[sel])
    i = int(np.argmax(a))
    worst = 20 * math.log10(max(a[i], 1e-20))
    band = (f >= fm_band[0]) & (f <= fm_band[1])
    fm = math.sqrt(2 * np.sum(np.abs(c[band]) ** 2))
    ph = np.cumsum(e) / fclk * 2 * math.pi
    return dict(frac=frac, x=x, worst_dbc=worst, worst_f=float(f[sel][i]), fm_rms_hz=fm,
                mean_err_hz=float(np.mean(e)), phase_pp_rad=float(ph.max() - ph.min()))


def sweep(a):
    out = {}
    nper = {"sd1": 1 << a.nfrac, "mash11": 1 << (2 * a.nfrac)}
    for name, (fn, _) in MODS.items():
        n = nper[name]
        rows = []
        for frac in range(1, 1 << a.nfrac):
            y = fn(frac, a.nfrac, n)
            rows.append(metrics(y, frac, a.nfrac, a.lsb, a.fclk))
        w = max(rows, key=lambda r: r["worst_dbc"])
        fmw = max(rows, key=lambda r: r["fm_rms_hz"])
        out[name] = dict(rows=rows, worst=w, worst_fm=fmw)
        print(f"{name:7s} lsb {a.lsb/1e3:.0f} kHz fclk {a.fclk/1e6:.1f} MHz nfrac {a.nfrac}: worst spur {w['worst_dbc']:.1f} dBc "
              f"(frac {w['frac']}, {w['worst_f']/1e6:.4f} MHz); worst FM 1-100 kHz {fmw['fm_rms_hz']:.0f} Hz rms (frac {fmw['frac']}); "
              f"phase p-p max {max(r['phase_pp_rad'] for r in rows):.4f} rad")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sweep", "grid", "bits", "fine"])
    ap.add_argument("--lsb", type=float, default=50e3)
    ap.add_argument("--fclk", type=float, default=25e6)
    ap.add_argument("--nfrac", type=int, default=8)
    ap.add_argument("--frac", type=int, default=77)
    ap.add_argument("--n", type=int, default=64)
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()
    od = REPO / "build/tx_fine/sd"; od.mkdir(parents=True, exist_ok=True)
    if a.mode == "bits":
        print("".join(map(str, sd1(a.frac, a.nfrac, a.n))))
        return
    if a.mode == "sweep":
        out = sweep(a)
        (od / f"sweep_l{a.lsb/1e3:g}k_c{a.fclk/1e6:g}M_n{a.nfrac}.json").write_text(
            json.dumps({k: dict(worst=v["worst"], worst_fm=v["worst_fm"], rows=v["rows"]) for k, v in out.items()}))
        if a.plot:
            plot(out, a)
        return
    if a.mode == "fine":   # sd1 with more fractional bits near 0, 1/2 and small rationals
        nf = 12
        rows = []
        for base in (0, 1 / 3, 1 / 2, 2 / 3, 1 / 4, 1 / 5):
            for d in range(-8, 9):
                frac = int(round(base * (1 << nf))) + d
                if 0 < frac < (1 << nf):
                    rows.append(metrics(sd1(frac, nf, 1 << nf), frac, nf, a.lsb, a.fclk))
        w = max(rows, key=lambda r: r["worst_dbc"]); fm = max(rows, key=lambda r: r["fm_rms_hz"])
        print(f"sd1 nfrac 12 near 0, 1/5, 1/4, 1/3, 1/2, 2/3 ({len(rows)} fractions): worst {w['worst_dbc']:.1f} dBc "
              f"(x {w['x']:.5f} at {w['worst_f']/1e3:.1f} kHz), worst FM {fm['fm_rms_hz']:.0f} Hz rms (x {fm['x']:.5f})")
        (od / f"fine_l{a.lsb/1e3:g}k_c{a.fclk/1e6:g}M.json").write_text(json.dumps(rows))
        return
    # grid: sd1 worst spur and FM over LSB x fclk
    res = []
    for lsb in (10e3, 25e3, 35e3, 50e3, 70e3):
        for fclk in (10e6, 12.5e6, 25e6, 50e6):
            rows = [metrics(sd1(fr, a.nfrac, 1 << a.nfrac), fr, a.nfrac, lsb, fclk) for fr in range(1, 1 << a.nfrac)]
            w = max(r["worst_dbc"] for r in rows); fm = max(r["fm_rms_hz"] for r in rows)
            res.append(dict(lsb=lsb, fclk=fclk, worst_dbc=w, fm_rms_hz=fm))
            print(f"sd1 lsb {lsb/1e3:4.0f} kHz fclk {fclk/1e6:5.1f} MHz: worst spur {w:6.1f} dBc, worst FM {fm:6.0f} Hz rms")
    (od / "grid.json").write_text(json.dumps(res, indent=1))


def plot(out, a):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for name, col in (("sd1", "C0"), ("mash11", "C1")):
        r = out[name]["rows"]
        xs = [q["x"] for q in r]
        ax[0].plot(xs, [q["worst_dbc"] for q in r], ".", ms=3, color=col, label={"sd1": "first order", "mash11": "MASH 1-1"}[name])
        ax[1].plot(xs, [q["fm_rms_hz"] / 1e3 for q in r], ".", ms=3, color=col)
    ax[0].axhline(-40, color="k", lw=0.8, ls="--"); ax[0].text(0.02, -39, "target -40 dBc", fontsize=8)
    ax[1].axhline(2, color="k", lw=0.8, ls="--"); ax[1].text(0.02, 2.1, "target 2 kHz rms", fontsize=8)
    ax[0].set(xlabel="fractional input x", ylabel="worst spur, 10 kHz-30 MHz (dBc)", title=f"LSB {a.lsb/1e3:g} kHz, clk {a.fclk/1e6:g} MHz")
    ax[1].set(xlabel="fractional input x", ylabel="SD-added FM, 1-100 kHz (kHz rms)")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3); ax[1].grid(alpha=0.3)
    fig.tight_layout()
    p = REPO / "docs/img/tx_fine_sd_sweep.png"; fig.savefig(p, dpi=130); print("wrote", p)


if __name__ == "__main__":
    main()
