#!/usr/bin/env python3
"""Shared helpers for the receiver (option B) block netlisters and benches in sim/rx/.

Device helpers write the same instance lines as sim/vco/vco_bias.fet (X<name> d g s b model w l ad as pd ps m), so
xschem/gen/check.py can compare sizes. Resistors: ppolyf_u (350 ohm/sq) for the LNA / baseband loads, ppolyf_u_1k
(1 kohm/sq) for the large ones. Capacitors: nfet_03v3 / pfet_03v3 gate caps (no MIM on TT GF).
Benches run ngspice directly (we are inside the IIC-OSIC-TOOLS image on sim-0), one thread per process.
"""
import math
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'sim' / 'vco'))
sys.path.insert(0, str(REPO / 'tools'))
import vco_bias as vb  # noqa: E402
from rawread import read_raw  # noqa: E402,F401

PDK = '/foss/pdks/gf180mcuD/libs.tech/ngspice'
PAD = REPO / 'sim' / 'pad'
BUILD = REPO / 'build' / 'rx'
RES = HERE / 'results'
CORNERS = ('typical', 'ss', 'ff', 'sf', 'fs')
CN = dict(typical='tt', ss='ss', ff='ff', sf='sf', fs='fs')
VDD = 3.3
L = 0.28
COX = vb.COX            # nfet_03v3 gate C per area incl. overlap (F/m2), in inversion
RSH = {'ppolyf_u': 350.0, 'ppolyf_u_1k': 1000.0}


def fet(name, d, g, s, b, typ, w, l=L, m=1):
    return vb.fet(name, d, g, s, b, typ, round(w, 4), round(l, 4), int(m))


def nfet(name, d, g, s, w, l=L, m=1, b='VSS'):
    return fet(name, d, g, s, b, 'nfet_03v3', w, l, m)


def pfet(name, d, g, s, w, l=L, m=1, b='VDD'):
    return fet(name, d, g, s, b, 'pfet_03v3', w, l, m)


def inv(name, i, o, wn, wp, l=L, m=1, vdd='VDD', vss='VSS'):
    return fet(f'{name}p', o, i, vdd, vdd, 'pfet_03v3', wp, l, m) + fet(f'{name}n', o, i, vss, vss, 'nfet_03v3', wn, l, m)


def res(name, a, b, r, w=1.0, model='ppolyf_u_1k', sub='VSS'):
    """Poly resistor of value r (ohm, nominal sheet, end effects ignored) at width w (um)."""
    ln = r / RSH[model] * w
    return f'X{name} {a} {b} {sub} {model} r_width={w}e-6 r_length={ln:.3f}e-6\n'


def scap(name, top, c, l=10.0, nf=1, typ='nfet_03v3', rail='VSS'):
    """Shunt gate cap of about c (F) from top to a rail: nfet (gate top, S/D/B VSS) or pfet (gate top, S/D/B VDD)."""
    w = c / (nf * l * 1e-6 * COX) * 1e6
    return fet(name, rail, top, rail, rail, typ, w, l, nf)


def ccap(name, top, bot, c, l=10.0, nf=1):
    """Floating coupling cap (nfet gate cap): gate top, S/D bot, bulk VSS."""
    w = c / (nf * l * 1e-6 * COX) * 1e6
    return fet(name, bot, top, bot, 'VSS', 'nfet_03v3', w, l, nf)


def hdr(corner, pad=False, std=False):
    s = (f'.include {PDK}/design.ngspice\n.lib {PDK}/sm141064.ngspice {corner}\n'
         f'.lib {PDK}/sm141064.ngspice res_typical\n.lib {PDK}/sm141064.ngspice diode_typical\n'
         '')
    if pad:
        s += f'.include {PAD}/tt_asw_5v0.spice\n.include {PAD}/pad_model_gf180.spice\n'
    if std:
        s += '.include /foss/pdks/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/spice/gf180mcu_fd_sc_mcu7t5v0.spice\n'
    return s


BAD = ('singular', 'timestep too small', 'transient op started', 'error:', 'no such', 'unknown subckt', 'timeout')


def run(name, deck, sub='', timeout=3600):
    """Run one ngspice deck in build/rx/<sub>/<name>/. Returns (dir, log text, list of bad words in the log)."""
    d = BUILD / sub / name
    d.mkdir(parents=True, exist_ok=True)
    (d / '.spiceinit').write_text('set ng_nomodcheck\nset num_threads=1\noption noinit\n')
    (d / 'deck.cir').write_text(deck)
    for f in d.glob('*.raw'):
        f.unlink()
    t = time.time()
    try:
        subprocess.run(['nice', '-n', '10', 'ngspice', '-b', 'deck.cir'], cwd=d, stdout=open(d / 'deck.log', 'w'),
                       stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired:
        (d / 'deck.log').open('a').write('\nTIMEOUT\n')
    log = (d / 'deck.log').read_text(errors='replace')
    low = log.lower()
    bad = [w for w in BAD if w in low]
    (d / 'time.txt').write_text(f'{time.time() - t:.1f}\n')
    return d, log, bad


def meas(log):
    """name = value lines from ngspice .meas / echo (k = v)."""
    out = {}
    for m in re.finditer(r'^\s*(\w+)\s*=\s*([-+0-9.eE]+)', log, re.M):
        try:
            out[m.group(1).lower()] = float(m.group(2))
        except ValueError:
            pass
    return out


def tag(log, key):
    """Rows 'KEY v1 v2 ...' echoed by a deck."""
    rows = []
    for m in re.finditer(rf'^{key} (.*)$', log, re.M):
        rows.append([float(x) if re.match(r'^[-+0-9.eE]+$', x) else x for x in m.group(1).split()])
    return rows


def db(x):
    return 20 * np.log10(np.abs(x))


def xings(t, v, th, rising=True):
    a, b = v[:-1] - th, v[1:] - th
    idx = np.where((a < 0) & (b >= 0))[0] if rising else np.where((a > 0) & (b <= 0))[0]
    return t[idx] + (th - v[idx]) * (t[idx + 1] - t[idx]) / (v[idx + 1] - v[idx])


def duty(t, v, th):
    r, f = xings(t, v, th), xings(t, v, th, False)
    d = []
    for i in range(len(r) - 1):
        nf = f[(f > r[i]) & (f < r[i + 1])]
        if len(nf):
            d.append((nf[0] - r[i]) / (r[i + 1] - r[i]))
    return float(np.mean(d)) if d else float('nan')


def pmap(fn, items, jobs=8):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(jobs) as ex:
        return list(ex.map(fn, items))


def area_fets(netlist):
    """Sum of W*L*m (um2) of the X... fet lines and W*L of the poly resistors: a gate-area estimate."""
    a = 0.0
    for ln in netlist.splitlines():
        m = re.search(r' (nfet|pfet)_03v3 w=([\d.e+-]+)u l=([\d.e+-]+)u .* m=(\d+)', ln)
        if m:
            a += float(m.group(2)) * float(m.group(3)) * int(m.group(4))
        m = re.search(r'r_width=([\d.e+-]+)e-6 r_length=([\d.e+-]+)e-6', ln)
        if m:
            a += float(m.group(1)) * float(m.group(2))
    return a
