#!/usr/bin/env python3
"""RP2350-side tuning model for the on-chip fine tuning (docs/tx_fine_tune.md, phase E).

    python3 sim/tune/rp2350_model.py [--plot]      # cold start at tt / ss / ff, FSK calibration, 27 -> 35 C drift

The chip (behavioural):
  f(code, word, frac, T) = f_w0(corner, code) + (word + frac / 256) x LSB(corner), times (1 + tc (T - 27 C)),
  with f_w0(code) = f_w0(k433) + (code - k433) x step(corner) x (1 + 3 % random per code: the coarse DAC's
  mismatch), f_w0, step and LSB from the medium DAC on the schematic ring (Table II of docs/tx_fine_tune.md),
  tc = +120 ppm/C (docs/top_layout.md: +100 ... +140 ppm/C near 27 C), and white FM noise of 8 kHz rms in 1-10 kHz
  (flat S_f = 8 kHz^2 / 9 kHz), so a frequency averaged over a gate T_g has sigma = sqrt(S_f / (2 T_g)).
The RP2350 (behavioural): counts the f / 16 output (uo[1], 27.1 MHz) in a PIO program.
  gated     : edges of f / 16 in a gate T_g of its own clock: f = 16 N / T_g, quantised to 16 / T_g.
  reciprocal: its 150 MHz system clock counts the time of a whole number of f / 16 periods close to T_g, quantised
              to 6.67 ns (resolution f x 6.67 ns / T_g: 290 Hz at 10 ms).
  Its crystal is +/- 30 ppm (13 kHz at 433.92 MHz): every measurement scales by (1 + e_xtal), so the tuning is to
  433.92 MHz on the RP2350's own time base; the model uses e_xtal = +10 ppm and reports both errors.
Sequence: reset (word 512, SD off) -> binary search of the 5-bit coarse code with the medium DAC at mid-scale ->
two-point LSB measurement (words 256, 768) -> word and fraction for the target -> integral servo on the reciprocal
count -> FSK: deviation word from the LSB, then calibrated by counting both states. Drift: the servo runs once a
second (or every 0.1 s) between packets (frozen during a 20 ms packet) while the die warms from 27 to 35 C over 60 s.
"""
import argparse, json, math
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[2]
TARGET = 433.92e6
# medium DAC on the schematic ring, vctrl pulled down (Table II): 433.92 code, f(word 0), coarse step, LSB
CHIP = {"typical": dict(k=9, f_w0=441.16e6, step=21.55e6, lsb=33.4e3),
        "ss": dict(k=11, f_w0=446.94e6, step=19.09e6, lsb=29.4e3),
        "ff": dict(k=7, f_w0=432.38e6, step=24.68e6, lsb=38.5e3)}
TC = 120e-6
SF = 8e3 ** 2 / 9e3          # white FM, Hz^2/Hz
XTAL = 10e-6
SYSCLK = 150e6


class Chip:
    def __init__(self, corner, seed=1):
        self.c = CHIP[corner]
        self.rng = np.random.default_rng(seed)
        self.mis = 1 + 0.03 * self.rng.standard_normal(32)
        self.code, self.word, self.frac, self.sd = 0, 512, 0, False
        self.dev, self.fsk_en, self.fsk = 0, False, 0
        self.T = 27.0

    def f(self, fsk=None):
        c = self.c
        fw0 = c["f_w0"] + sum(c["step"] * self.mis[i] * (1 if i >= c["k"] else -1)
                              for i in (range(c["k"], self.code) if self.code > c["k"] else range(self.code, c["k"])))
        w = self.word + (self.frac / 256 if self.sd else 0)
        if self.fsk_en:
            w += (self.dev / 256) * (1 if (self.fsk if fsk is None else fsk) else -1)
        w = min(max(w, 0), 1023 + 255 / 256)
        return (fw0 + w * c["lsb"]) * (1 + TC * (self.T - 27))


def measure(chip, tg, mode="reciprocal", fsk=None):
    """What the RP2350 reports (its own time base), with the VCO's FM noise over the gate."""
    f_true = chip.f(fsk) + chip.rng.standard_normal() * math.sqrt(SF / (2 * tg))
    f_seen = f_true / (1 + XTAL)                      # the RP2350's clock runs fast by XTAL: it sees f lower
    if mode == "gated":
        n = math.floor(f_seen / 16 * tg + chip.rng.random())
        return 16 * n / tg
    m = round(f_seen / 16 * tg)                       # whole f/16 periods
    t = m * 16 / f_seen
    ticks = math.floor(t * SYSCLK + chip.rng.random())
    return m * 16 / (ticks / SYSCLK)


def cold_start(corner, seed=1, tg=10e-3, log=None):
    chip = Chip(corner, seed)
    hist = []
    lo, hi = 0, 31                                    # coarse: largest code whose word-0 frequency is below target
    chip.word = 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        chip.code = mid
        f = measure(chip, 1e-3)
        hist.append(("coarse", mid, f))
        if f <= TARGET:
            lo = mid
        else:
            hi = mid - 1
    chip.code = lo
    # medium: two-point LSB
    chip.word = 256; f1 = measure(chip, tg)
    chip.word = 768; f2 = measure(chip, tg)
    lsb = (f2 - f1) / 512
    hist.append(("lsb", lsb, None))
    x = 256 + (TARGET - f1) / lsb
    if x > 1023 or x < 0:                             # the medium range covers > 1.3 coarse steps: step the code
        chip.code += 1 if x > 1023 else -1
        chip.word = 512; f1 = measure(chip, tg)
        x = 512 + (TARGET - f1) / lsb
    def set_word(x):
        x = min(max(x, 0), 1023 + 255 / 256)
        chip.word, chip.frac, chip.sd = int(x), int(round((x - int(x)) * 256)) % 256, True
        if round((x - int(x)) * 256) == 256:
            chip.word += 1
        return x
    x = set_word(x)
    errs = []
    for it in range(6):                               # integral servo on the reciprocal count
        f = measure(chip, tg)
        errs.append((f - TARGET, chip.f() / (1 + XTAL) - TARGET, chip.f() - TARGET))
        x = set_word(x + (TARGET - f) / lsb)
    hist.append(("servo", errs, None))
    # FSK: deviation word for +/- 100 kHz, then calibrated on the measured spread
    chip.fsk_en = True
    dev = 100e3 / lsb
    for it in range(3):
        chip.dev = int(round(dev * 256))
        fh, fl = measure(chip, tg, fsk=1), measure(chip, tg, fsk=0)
        dev *= 200e3 / (fh - fl)
    chip.dev = int(round(dev * 256))
    fh, fl = chip.f(1) / (1 + XTAL), chip.f(0) / (1 + XTAL)
    return dict(corner=corner, code=chip.code, word=chip.word, frac=chip.frac, lsb_meas=lsb, coarse_steps=sum(h[0] == "coarse" for h in hist),
                servo=[dict(meas_err=a, err_rp2350=b, err_abs=c) for a, b, c in errs],
                fsk=dict(dev_word=chip.dev / 256, f_hi_minus_target=fh - TARGET, f_lo_minus_target=fl - TARGET,
                         spread=fh - fl, centre_err=(fh + fl) / 2 - TARGET),
                chip=chip, x=x)


def drift(corner="typical", seed=2, tg=10e-3, minutes=1.0, interval=1.0):
    st = cold_start(corner, seed, tg)
    chip, x = st["chip"], st["x"]
    chip.fsk_en = False
    lsb = st["lsb_meas"]
    out = []
    t = 0.0
    while t < 60 * minutes:
        chip.T = 27 + 8 * t / (60 * minutes)
        e_start = chip.f() / (1 + XTAL) - TARGET            # at the start of a packet (servo frozen)
        chip.T = 27 + 8 * (t + 0.02) / (60 * minutes)
        e_end = chip.f() / (1 + XTAL) - TARGET              # 20 ms later, end of the packet
        out.append((t, chip.T, e_start, e_end))
        f = measure(chip, tg)                                # servo between packets
        x = min(max(x + (TARGET - f) / lsb, 0), 1023.99)
        chip.word, chip.frac, chip.sd = int(x), int((x - int(x)) * 256), True
        t += interval
    return out, x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()
    res = {}
    for c in ("typical", "ss", "ff"):
        r = cold_start(c)
        r.pop("chip")
        res[c] = r
        s = r["servo"]
        print(f"{c:8s}: code {r['code']}, word {r['word']} + {r['frac']}/256, LSB measured {r['lsb_meas']/1e3:.2f} kHz; "
              f"servo error (RP2350 time base) " + " ".join(f"{e['err_rp2350']/1e3:+.2f}" for e in s) + " kHz; "
              f"FSK spread {r['fsk']['spread']/1e3:.2f} kHz, centre {r['fsk']['centre_err']/1e3:+.2f} kHz")
    res["drift"] = {}
    for iv in (1.0, 0.1):
        dr, _ = drift(interval=iv)
        worst = max(max(abs(e[2]), abs(e[3])) for e in dr[2:])
        in_pkt = max(abs(e[3] - e[2]) for e in dr)
        print(f"drift 27 -> 35 C in 60 s, servo every {iv:g} s: worst error at a packet {worst/1e3:.2f} kHz; "
              f"change during a 20 ms packet {in_pkt:.0f} Hz")
        res["drift"][f"{iv:g} s"] = dict(worst_khz=worst / 1e3, in_packet_hz=in_pkt, trace=dr)
    dr = res["drift"]["0.1 s"]["trace"]
    # gated vs reciprocal resolution
    res["resolution"] = {f"{tg*1e3:g} ms": dict(gated_hz=16 / tg, reciprocal_hz=TARGET / SYSCLK / tg) for tg in (1e-3, 10e-3, 16e-3)}
    for k, v in res["resolution"].items():
        print(f"gate {k}: gated counting {v['gated_hz']/1e3:.1f} kHz steps, reciprocal {v['reciprocal_hz']:.0f} Hz")
    out = REPO / "build/tx_fine"; out.mkdir(parents=True, exist_ok=True)
    (out / "rp2350_model.json").write_text(json.dumps(res, indent=1, default=float))
    if a.plot:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
        for c, col in (("typical", "C0"), ("ss", "C1"), ("ff", "C2")):
            e = [abs(s["err_rp2350"]) for s in res[c]["servo"]]
            ax[0].semilogy(range(1, len(e) + 1), e, "o-", color=col, label=f"{c} (code {res[c]['code']})")
        ax[0].axhline(1e3, color="k", ls="--", lw=0.8); ax[0].text(1, 1.15e3, "1 kHz", fontsize=8)
        ax[0].set(xlabel="servo step (10 ms reciprocal count each)", ylabel="|f - 433.92 MHz| (Hz)",
                  title="Cold start, after the coarse search and the LSB measurement")
        ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3, which="both")
        tt = [d[0] for d in dr]
        ax[1].plot(tt, [d[2] / 1e3 for d in dr], ".", ms=4, label="at the start of each packet")
        ax2 = ax[1].twinx(); ax2.plot(tt, [d[1] for d in dr], color="0.6", lw=1); ax2.set_ylabel("die temperature (C)", color="0.4")
        ax[1].set(xlabel="time (s)", ylabel="f - 433.92 MHz (kHz)", title="27 -> 35 C in 60 s, servo every 0.1 s")
        ax[1].grid(alpha=0.3); ax[1].legend(fontsize=8, loc="lower right")
        fig.tight_layout()
        p = REPO / "docs/img/tx_fine_servo.png"; fig.savefig(p, dpi=130); print("wrote", p)


if __name__ == "__main__":
    main()
