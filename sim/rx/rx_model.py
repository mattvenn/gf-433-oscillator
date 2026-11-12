#!/usr/bin/env python3
"""Behavioural model of the 433.92 MHz 2-FSK receiver: option A vs option B.

A: low IF, one real mixer. LO = fc - fif (low side). IF band-pass, limiter, one bit to the RP2350 PIO, which
   counts limiter transitions per bit (a zero-crossing frequency discriminator).
B: zero IF, I/Q mixers on two ring taps that are 72 deg apart (not 90), a DC-block high-pass and a low-pass per
   arm, two limiters, two bits to the PIO, which runs a quadrature decoder (signed quadrant steps per bit, as for
   a rotary encoder).

Everything is complex baseband around fc = 433.92 MHz, sampled at fs. The signal has |x|^2 = P; the input-referred
noise is complex white with E|n|^2 = k T0 F fs, so the SNR in a bandwidth B is P / (k T0 F B). The LO noise of the
ring is applied as a random phase on the whole input (reciprocal mixing included).

Limits of the model: the front end is linear (no compression or IP3), the noise figure F lumps pin, LNA, mixer and
IF noise and is flat (no flicker corner), the LO is a pure tone (no 3rd-harmonic responses of a square LO), and the
bit timing is ideal (genie), while the decision threshold is learned from the packet (the RP2350 would take it from
the preamble).
"""
import numpy as np
from scipy import signal

FC = 433.92e6
KT0 = 1.380649e-23 * 290.0
MAX_SAMPLES = 2_000_000          # per simulated packet (memory)

A_DEF = dict(fif=250e3, band=(100e3, 400e3), order=2)
B_DEF = dict(bw=150e3, order=2, hpf=10e3, dphi=18.0, dc=0.0)
HYST = 0.5          # comparator hysteresis, +-HYST x (noise rms at the comparator input)


def dbm2w(p):
    return 1e-3 * 10 ** (np.asarray(p, float) / 10)


# ---- LO noise of the current-fed ring -------------------------------------------------------------------------
# One-sided FM noise S_f(f) in Hz^2/Hz. The 1/f part fits docs/cfed_sizing_results.md (tt 27 C, code 9:
# 7.87 kHz rms over 1-10 kHz, 10.3 kHz over 1-100 kHz, L(100k) = -80 dBc/Hz); the white part is the ISF device
# floor (L(1 MHz) = -118.7 dBc/Hz). Flat below 100 Hz: slower drift is a static offset within a packet.
PN_KF, PN_WHITE, PN_FMIN = 2.7e7, 2.7, 100.0


def fm_psd(f):
    return PN_KF / np.maximum(f, PN_FMIN) + PN_WHITE


def L_dbc(f):
    f = np.asarray(f, float)
    return 10 * np.log10(fm_psd(f) / (2 * f ** 2))


def lo_freq_noise(n, fs, rng):
    """Real frequency-noise sequence (Hz) with one-sided PSD fm_psd."""
    f = np.fft.rfftfreq(n, 1 / fs)
    s = fm_psd(np.maximum(f, 1.0))
    s[0] = 0.0
    X = (rng.standard_normal(len(f)) + 1j * rng.standard_normal(len(f))) * np.sqrt(n * s * fs / 4)
    return np.fft.irfft(X, n)


# ---- signal at the antenna, referred to the receiver input -----------------------------------------------------
def rx_input(bits, rate, fs, pin_dbm, nf_db, rng, dev=100e3, df=0.0, intf=(), pn=True):
    """Complex envelope after an ideal LO at fc (the LO noise is applied here, to everything).

    bits: 0/1 array; 2-FSK NRZ with continuous phase, +dev for 1. df: carrier offset (TX - RX) in Hz.
    intf: list of (offset_Hz, power_dBm) CW interferers. nf_db None = noiseless.
    """
    sps = int(round(fs / rate))
    n = len(bits) * sps
    fi = np.repeat(np.where(bits > 0, dev, -dev), sps) + df
    x = np.sqrt(dbm2w(pin_dbm)) * np.exp(1j * (2 * np.pi * np.cumsum(fi) / fs + rng.uniform(0, 2 * np.pi)))
    t = np.arange(n) / fs
    for fo, pw in intf:
        x = x + np.sqrt(dbm2w(pw)) * np.exp(1j * (2 * np.pi * fo * t + rng.uniform(0, 2 * np.pi)))
    if nf_db is not None:
        n0 = KT0 * 10 ** (nf_db / 10)
        x = x + np.sqrt(n0 * fs / 2) * (rng.standard_normal(n) + 1j * rng.standard_normal(n))
    if pn:
        x = x * np.exp(-1j * 2 * np.pi * np.cumsum(lo_freq_noise(n, fs, rng)) / fs)
    return x, sps


# ---- the two receive chains -------------------------------------------------------------------------------------
def chain_a(x, fs, fif, band, order):
    """Real mixer with LO = fc - fif: IF = Re{x e^{+j w_if t}} (the image at fc - 2 fif folds onto the IF)."""
    t = np.arange(len(x)) / fs
    y = np.real(x * np.exp(2j * np.pi * fif * t))
    return signal.sosfilt(signal.butter(order, band, 'bandpass', fs=fs, output='sos'), y)


def chain_b(x, fs, bw, order, hpf, dphi, dc):
    """I = Re{x}, Q = Im{x e^{-j dphi}}: the Q tap leads I by 90 - dphi degrees (72 deg for a 5-stage ring)."""
    i = x.real + dc
    q = (x * np.exp(-1j * np.deg2rad(dphi))).imag + dc
    sos = np.vstack([signal.butter(1, hpf, 'high', fs=fs, output='sos'),
                     signal.butter(order, bw, 'low', fs=fs, output='sos')])
    return signal.sosfilt(sos, i), signal.sosfilt(sos, q)


# ---- what the PIO does with the limiter bits --------------------------------------------------------------------
def schmitt(y, h):
    """Comparator with hysteresis +-h: the output changes only when y leaves the band [-h, h]."""
    idx = np.arange(len(y))
    last = np.maximum.accumulate(np.where((y > h) | (y < -h), idx, -1))
    return np.where(last >= 0, y[np.maximum(last, 0)] > 0, False)


def noise_rms(opt, fs, p, nf_db):
    """rms of the input noise at the comparator input (each arm for B)."""
    if opt == 'A':
        sos = signal.butter(p['order'], p['band'], 'bandpass', fs=fs, output='sos')
    else:
        sos = np.vstack([signal.butter(1, p['hpf'], 'high', fs=fs, output='sos'),
                         signal.butter(p['order'], p['bw'], 'low', fs=fs, output='sos')])
    imp = np.zeros(int(fs * 2e-3)); imp[0] = 1
    g = np.sum(signal.sosfilt(sos, imp) ** 2)
    return np.sqrt(KT0 * 10 ** (nf_db / 10) * fs / 2 * g)


def steps_a(b):
    """1 at every limiter transition (b: comparator output, bool)."""
    s = np.zeros(len(b), np.int16)
    s[1:] = b[1:] != b[:-1]
    return s


_QUAD = np.array([2, 1, 3, 0])     # index (I>0)*2 + (Q>0) -> quadrant 0..3, counter-clockwise


def steps_b(i, q):
    """+1 / -1 per quadrant step counter-clockwise / clockwise (a double step, both bits at once, counts 0)."""
    quad = _QUAD[i.astype(int) * 2 + q]
    d = (quad[1:] - quad[:-1]) % 4
    s = np.zeros(len(quad), np.int16)
    s[1:] = np.where(d == 1, 1, np.where(d == 3, -1, 0))
    return s


def run_chain(opt, x, fs, p, h=0.0):
    """Chain + comparators (hysteresis h, absolute) + PIO step counter."""
    if opt == 'A':
        return steps_a(schmitt(chain_a(x, fs, **p), h))
    i, q = chain_b(x, fs, **p)
    return steps_b(schmitt(i, h), schmitt(q, h))


def counts(steps, sps, nb, start):
    return steps[start:start + nb * sps].reshape(nb, sps).sum(1)


NPRE, NPOST = 6, 6
_DELAY = {}


def delay(opt, fs, rate, p, dev=100e3):
    """Filter delay (samples) that maximises the eye opening, from a noiseless run (genie timing)."""
    key = (opt, fs, rate, dev, tuple(sorted((k, str(v)) for k, v in p.items())))
    if key not in _DELAY:
        rng = np.random.default_rng(1)
        nb = 200
        bits = rng.integers(0, 2, nb + NPRE + NPOST)
        x, sps = rx_input(bits, rate, fs, -60, None, rng, dev=dev, pn=False)
        st = run_chain(opt, x, fs, p)
        sgn = np.where(bits[NPRE:NPRE + nb] > 0, 1, -1)
        best = None
        for d in range(0, 2 * sps, max(1, sps // 40)):
            c = counts(st, sps, nb, NPRE * sps + d)
            m = (c - c.mean()) * sgn
            score = (np.sum(m > 0), m.min())
            if best is None or score > best[0]:
                best = (score, d)
        _DELAY[key] = best[1]
    return _DELAY[key]


def ber(opt, pin_dbm, nf_db=10.0, rate=10e3, nbits=2000, fs=8e6, seed=0, df=0.0, intf=(), pn=True, dev=100e3,
        hyst=None, **over):
    """Bit-error rate. Same seed = same noise and bits (common random numbers for searches)."""
    p = dict(A_DEF if opt == 'A' else B_DEF)
    p.update(over)
    if opt == 'B' and p['dc'] != 0:          # dc given relative to the signal amplitude
        p['dc'] = p['dc'] * np.sqrt(dbm2w(pin_dbm))
    pd = dict(p, dc=0.0) if opt == 'B' else p
    d = delay(opt, fs, rate, pd, dev)
    h = (HYST if hyst is None else hyst) * noise_rms(opt, fs, pd, nf_db)
    sps = int(round(fs / rate))
    per = max(50, MAX_SAMPLES // sps - NPRE - NPOST)
    rng = np.random.default_rng(seed)
    err = tot = 0
    while tot < nbits:
        nb = min(per, nbits - tot)
        bits = rng.integers(0, 2, nb + NPRE + NPOST)
        x, _ = rx_input(bits, rate, fs, pin_dbm, nf_db, rng, dev=dev, df=df, intf=intf, pn=pn)
        c = counts(run_chain(opt, x, fs, p, h), sps, nb, NPRE * sps + d).astype(float)
        dec = c > c.mean()
        err += int(np.sum(dec != (bits[NPRE:NPRE + nb] > 0)))
        tot += nb
    return err / tot


def level_for_ber(opt, target=1e-2, lo=-115.0, hi=-70.0, tol=0.25, **kw):
    """Input level (dBm) where the BER crosses target (bisection, common random numbers)."""
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if ber(opt, mid, **kw) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def max_interferer(opt, sig_dbm, f_off, target=1e-2, lo=-110.0, hi=0.0, tol=0.5, **kw):
    """Largest CW interferer (dBm) at f_off that keeps the BER at or below target."""
    if ber(opt, sig_dbm, intf=[(f_off, hi)], **kw) <= target:
        return hi
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if ber(opt, sig_dbm, intf=[(f_off, mid)], **kw) > target:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


if __name__ == '__main__':
    import time
    rng = np.random.default_rng(0)
    fs = 4e6
    fn = lo_freq_noise(2 ** 22, fs, rng)
    f, s = signal.welch(fn, fs, nperseg=2 ** 18)
    for a, b in ((1e3, 1e4), (1e3, 1e5)):
        m = (f >= a) & (f <= b)
        print(f'LO rms FM {a/1e3:.0f}-{b/1e3:.0f} kHz: {np.sqrt(np.trapezoid(s[m], f[m]))/1e3:.2f} kHz')
    print('L(100k), L(1M) dBc/Hz:', L_dbc([1e5, 1e6]).round(1))
    for opt in 'AB':
        t0 = time.time()
        print(opt, 'BER at -60 dBm:', ber(opt, -60), 'at -100 dBm:', ber(opt, -100), f'({time.time()-t0:.1f} s)')
