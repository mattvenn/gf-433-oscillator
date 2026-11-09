#!/usr/bin/env python3
"""GF silicon factor: simulate one tt_um_algofoogle_vgaringosc ring configuration from the extracted layout.

Usage (repo root, inside the image):
  python3 sim/silicon_factor/tb.py --cfg inv1x5 --corner typical --mode c [--tstop 300e-9] [--temp 27]
Prints one CSV row: cfg,clksel2,clksel,stages,corner,mode,temp,f_Hz,f_sd_pct,n_periods,vmin,vmax,runtime_s,status

Stimulus: VPWR 3.3 V, ena = 1, clk held low (VGA logic idle), rst_n low for 10 ns then high (ring_ena = ena &&
clksel >= 2 && !reset). ui_in[3:0] = clksel, uio_in[1:0] = clksel2, other inputs 0.
Measured: uio_out[4] (the selected clock through a buf_1, = the raw-pin signal on the bench), rising crossings of
VDD/2 (full-swing logic here, unlike our current-fed ring), periods after the first 30 % of the run are averaged.
Bench comparison: silicon f = 8 x the uio_out[7] reading (docs/gf_silicon_factor.md).
"""
import argparse, os, re, subprocess, sys, time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "build" / "silicon_factor"
# measured silicon f (chip 1, MHz; inv4x5 from chip 2, unconfirmed), used for run length and the factor
F_MEAS = {"inv1x5": 319.6, "inv4x5": 206.5, "t3": 220.51, "t5": 196.22, "t9": 160.66, "t33": 77.69, "t65": 49.87,
          "t161": 23.72}
CFGS = {  # name: (clksel2, clksel, stages)
    "inv1x5": (1, 10, 5), "inv4x5": (2, 2, 5),
    "t3": (0, 2, 3), "t5": (0, 3, 5), "t9": (0, 5, 9), "t33": (0, 10, 33), "t65": (0, 13, 65), "t161": (0, 15, 161),
}
PDK = "/foss/pdks/gf180mcuD/libs.tech/ngspice"


def ports(netlist):
    txt = netlist.read_text()
    m = re.search(r"^\.subckt\s+(\S+)(.*?)\n(?!\+)", txt, re.M | re.S)
    toks = m.group(2).replace("\n+", " ").split()
    return m.group(1), toks


def node(p, c2, c):
    """Map a macro port to a testbench node."""
    if p in ("VPWR",): return "vdd"
    if p in ("VGND",): return "0"
    if p == "ena": return "vdd"
    if p == "clk": return "0"
    if p == "rst_n": return "rstn"
    m = re.fullmatch(r"(ui_in|uio_in|uio_out|uo_out|uio_oe)\[(\d)\]", p)
    if not m: return "nc_" + re.sub(r"\W", "_", p)
    bus, i = m.group(1), int(m.group(2))
    if bus == "ui_in": return "vdd" if i < 4 and (c >> i) & 1 else "0"
    if bus == "uio_in": return "vdd" if i < 2 and (c2 >> i) & 1 else "0"
    return f"{bus.replace('_', '')}{i}"  # outputs: uioout4 etc. (no brackets for ngspice)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", required=True, choices=CFGS)
    ap.add_argument("--corner", default="typical")
    ap.add_argument("--mode", default="c", choices=("c", "rc"))
    ap.add_argument("--temp", type=float, default=27)
    ap.add_argument("--vdd", type=float, default=3.3)
    ap.add_argument("--tstop", type=float, default=None)
    a = ap.parse_args()
    c2, c, n = CFGS[a.cfg]
    # 20 ns for reset release and start-up, then about 7 periods at 0.6x the silicon frequency (sim may be slower)
    tstop = a.tstop or (20e-9 + 7 / (0.6 * F_MEAS[a.cfg] * 1e6))
    net = BUILD / f"vgaringosc_{a.mode}.spice"
    top, plist = ports(net)
    tag = f"{a.cfg}_{a.corner}_{a.mode}_{a.temp:g}"
    wd = BUILD / "runs" / tag; wd.mkdir(parents=True, exist_ok=True)
    conn = " ".join(node(p, c2, c) for p in plist)
    deck = f"""* silicon factor {tag}
.include {PDK}/design.ngspice
.lib {PDK}/sm141064.ngspice {a.corner}
.include {net}
.temp {a.temp}
.option klu reltol=1e-3
vdd vdd 0 {a.vdd}
vrst rstn 0 pwl(0 0 10n 0 10.1n {a.vdd})
xdut {conn} {top}
.control
tran 10p {tstop}
wrdata out.txt v(uioout4)
quit
.endc
.end
"""
    (wd / "tb.spice").write_text(deck)
    (wd / ".spiceinit").write_text((REPO / ".spiceinit").read_text())
    t0 = time.time()
    r = subprocess.run(["ngspice", "-b", "tb.spice"], cwd=wd, capture_output=True, text=True)
    (wd / "ngspice.log").write_text(r.stdout + r.stderr)
    dt = time.time() - t0
    status = "ok"
    log = r.stdout + r.stderr
    if "singular" in log.lower() or "timestep too small" in log.lower(): status = "sim_error"
    f = sd = vmin = vmax = float("nan"); npd = 0
    try:
        d = np.loadtxt(wd / "out.txt")
        t, v = d[:, 0], d[:, 1]
        vmin, vmax = v[t > 20e-9].min(), v[t > 20e-9].max()
        th = a.vdd / 2
        i = np.where((v[:-1] < th) & (v[1:] >= th))[0]
        tc = t[i] + (th - v[i]) * (t[i + 1] - t[i]) / (v[i + 1] - v[i])
        tc = tc[tc > 15e-9][1:]  # drop the first edge after start-up
        per = np.diff(tc); npd = len(per)
        if npd >= 3:
            f = 1 / per.mean(); sd = per.std() / per.mean() * 100
        else:
            status = "no_osc" if status == "ok" else status
    except Exception as e:
        status = f"no_output:{type(e).__name__}"
    print(f"{a.cfg},{c2},{c},{n},{a.corner},{a.mode},{a.temp:g},{f:.6e},{sd:.3f},{npd},{vmin:.3f},{vmax:.3f},{dt:.0f},{status}",
          flush=True)


if __name__ == "__main__":
    main()
