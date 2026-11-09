import subprocess, sys, time, statistics, pyvisa
TT = sys.argv[1]
s = pyvisa.ResourceManager().open_resource("TCPIP0::192.168.50.11::inst0::INSTR"); s.timeout = 15000
s.write(":MEASure:CLEar")
for m in ("FREQuency", "DUTYcycle", "VTOP", "VBASe"): s.write(f":MEASure:{m} CHANnel1")
def setp(c2, c):
    subprocess.run(["python3", TT, f"import time\nfrom machine import Pin\nfor n in ('uio0','uio1'):\n    getattr(tt.pins,n).mode=Pin.OUT\n"
                    f"tt.pins.uio0.value({c2&1})\ntt.pins.uio1.value({(c2>>1)&1})\ntt.ui_in.value={c}\n"
                    "tt.reset_project(True); time.sleep_ms(5); tt.reset_project(False)\nprint(1)", "15"], capture_output=True)
def meas(tag, n=30):
    s.write(":TRIGger:SWEep AUTO"); s.write(":TIMebase:SCALe 200E-9"); time.sleep(1.0)
    f0 = float(s.query(":MEASure:FREQuency? CHANnel1"))
    if 0 < f0 < 1e30: s.write(f":TIMebase:SCALe {3/f0/10:.3e}")
    s.write(":TRIGger:SWEep NORMal"); time.sleep(0.8); s.write(":MEASure:STATistics:RESet")
    v = []
    for _ in range(n):
        x = float(s.query(":MEASure:FREQuency? CHANnel1"))
        if 0 < x < 1e30: v.append(x)
        time.sleep(0.05)
    time.sleep(2)
    r = s.query(":MEASure:RESults?").strip().split(",")
    img = s.query_binary_values(":DISPlay:DATA? PNG", datatype="B", container=bytes); open(f"chip2_{tag}.png", "wb").write(img)
    return statistics.median(v), float(r[4]), float(r[5]), int(float(r[6])), float(r[2*7+4]), float(r[3*7+4])
print("tag,clksel2,clksel,rep,f8_median,f_x8_median_MHz,stat_mean_x8_MHz,stat_sd_x8_kHz,count,vtop,vbase", flush=True)
for tag, c2, c in [("inv4x5", 2, 2), ("inv1x5", 1, 2), ("inv2x3", 0, 2), ("notclk", 3, 2), ("clk", 0, 0)]:
    for rep in range(3):
        setp(c2, c); med, mean, sd, cnt, vt, vb = meas(f"{tag}_{rep}")
        print(f"{tag},{c2},{c},{rep},{med:.6e},{med*8/1e6:.3f},{mean*8/1e6:.3f},{sd*8/1e3:.1f},{cnt},{vt:.2f},{vb:.2f}", flush=True)
