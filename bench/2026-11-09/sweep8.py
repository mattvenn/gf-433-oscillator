#!/usr/bin/env python3
"""÷8 sweep on uio[7]: each config, R restarts (reset), median of N single readings + scope stats, screenshot."""
import sys, time, statistics, subprocess, pyvisa

TT = sys.argv[1]; R = int(sys.argv[2]) if len(sys.argv) > 2 else 3; N = int(sys.argv[3]) if len(sys.argv) > 3 else 30
TAPS = {2: 3, 3: 5, 4: 7, 5: 9, 6: 13, 7: 17, 8: 21, 9: 25, 10: 33, 11: 41, 12: 49, 13: 65, 14: 97, 15: 161}
CONFIGS = [(0, c, f"inv2x{TAPS[c]}") for c in sorted(TAPS, reverse=True)] + [(2, 10, "inv4x5"), (1, 10, "inv1x5")]
s = pyvisa.ResourceManager().open_resource("TCPIP0::192.168.50.11::inst0::INSTR"); s.timeout = 15000
s.write(":MEASure:CLEar"); s.write(":MEASure:FREQuency CHANnel1"); s.write(":MEASure:DUTYcycle CHANnel1")
s.write(":MEASure:VTOP CHANnel1"); s.write(":MEASure:VBASe CHANnel1")

def cur():
    v = float(s.query(":MEASure:FREQuency? CHANnel1"))
    return v if 0 < v < 1e30 else None

print("clksel2,clksel,ring,restart,f8_median_Hz,f8_iqr_Hz,n_valid,f_ring_Hz,stat_mean_Hz,stat_sd_Hz,duty_mean,vtop,vbase", flush=True)
for c2, c, name in CONFIGS:
    for r in range(R):
        subprocess.run(["python3", TT, f"import time\ntt.uio_in.value={c2}\ntt.ui_in.value={c}\n"
                        "tt.reset_project(True); time.sleep_ms(5); tt.reset_project(False)\nprint(1)", "10"],
                       capture_output=True)
        time.sleep(0.3)
        f0 = cur()
        if f0: s.write(f":TIMebase:SCALe {3/f0/10:.3e}"); time.sleep(0.8)
        s.write(":MEASure:STATistics:RESet")
        vals = []
        for _ in range(N):
            v = cur()
            if v: vals.append(v)
            time.sleep(0.05)
        res = s.query(":MEASure:RESults?").strip().split(",")
        # results: name,cur,min,max,mean,sd,count x4
        def field(i, k): return float(res[i * 7 + k])
        if vals:
            q = statistics.quantiles(vals, n=4) if len(vals) > 3 else [vals[0]] * 3
            med = statistics.median(vals); iqr = q[2] - q[0]
        else:
            med = iqr = float("nan")
        print(f"{c2},{c},{name},{r},{med:.6e},{iqr:.3e},{len(vals)},{med*8:.6e},{field(0,4):.6e},{field(0,5):.3e},"
              f"{field(1,4):.1f},{field(2,4):.2f},{field(3,4):.2f}", flush=True)
        if r == R - 1:
            img = s.query_binary_values(":DISPlay:DATA? PNG", datatype="B", container=bytes)
            open(f"d8_{name}.png", "wb").write(img)
