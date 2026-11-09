#!/usr/bin/env python3
"""Sweep ttgf0p2 #614 vgaringosc ring configs, read freq on scope CH1. Usage: sweep.py [ch] [nreads]"""
import sys, time, statistics, subprocess, pyvisa

CH = int(sys.argv[1]) if len(sys.argv) > 1 else 1
N = int(sys.argv[2]) if len(sys.argv) > 2 else 8
TT = "/tmp/claude-1000/-home-matt-work-asic-workshop-shuttle-ttgf26a-gf-433-oscillator/401925e9-de9f-448e-bada-5897c1ae3deb/scratchpad/tt.py"
TAPS = {2: 3, 3: 5, 4: 7, 5: 9, 6: 13, 7: 17, 8: 21, 9: 25, 10: 33, 11: 41, 12: 49, 13: 65, 14: 97, 15: 161}
CONFIGS = [(1, 10, "inv_1 x5"), (2, 10, "inv_4 x5")] + [(0, c, f"inv_2 x{TAPS[c]}") for c in sorted(TAPS)]

rm = pyvisa.ResourceManager()
s = rm.open_resource("TCPIP0::192.168.50.11::inst0::INSTR"); s.timeout = 5000
s.write(f":MEASure:FREQuency CHANnel{CH}")

def tt(code):
    r = subprocess.run(["python3", TT, code, "10"], capture_output=True, text=True)
    return r.stdout.strip()

print("clksel2,clksel,ring,f_mean_Hz,f_sd_Hz,vmax,vmin,readback")
for c2, c, name in CONFIGS:
    rb = tt(f"tt.uio_in.value={c2}\ntt.ui_in.value={c}\nprint(tt.ui_in.value, tt.uio_in.value)")
    f0 = None
    s.write(":RUN"); time.sleep(0.5)
    # pick a timebase: ~5 periods on screen from a first rough read
    raw = float(s.query(f":MEASure:FREQuency? CHANnel{CH}"))
    if raw < 1e30 and raw > 0:
        s.write(f":TIMebase:SCALe {5/raw/10:.3e}"); time.sleep(1.0)
    fs = []
    for _ in range(N):
        v = float(s.query(f":MEASure:FREQuency? CHANnel{CH}"))
        if 0 < v < 1e30: fs.append(v)
        time.sleep(0.25)
    vmax = s.query(f":MEASure:VMAX? CHANnel{CH}").strip(); vmin = s.query(f":MEASure:VMIN? CHANnel{CH}").strip()
    m = statistics.mean(fs) if fs else float("nan"); sd = statistics.pstdev(fs) if len(fs) > 1 else float("nan")
    print(f"{c2},{c},{name},{m:.6e},{sd:.3e},{float(vmax):.2f},{float(vmin):.2f},{rb.splitlines()[-1] if rb else ''}", flush=True)
