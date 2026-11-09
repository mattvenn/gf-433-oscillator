import subprocess, sys, time, statistics, pyvisa
TT = sys.argv[1]
s = pyvisa.ResourceManager().open_resource("TCPIP0::192.168.50.11::inst0::INSTR"); s.timeout = 15000
s.write(":TRIGger:SWEep NORMal"); s.write(":TRIGger:EDGE:LEVel 1.65"); s.write(":MEASure:CLEar")
for m in ("FREQuency", "VTOP", "VBASe"): s.write(f":MEASure:{m} CHANnel1")
def tt(code): return subprocess.run(["python3", TT, code, "15"], capture_output=True, text=True).stdout
def setp(c2, c, ui_extra=0, reset=True):
    code = f"tt.pins.uio0.value({c2 & 1})\ntt.pins.uio1.value({(c2 >> 1) & 1})\ntt.ui_in.value={c | ui_extra}\n"
    if reset: code += "import time\ntt.reset_project(True); time.sleep_ms(5); tt.reset_project(False)\n"
    code += "print(tt.ui_in.value, tt.uio_in.value)"
    return tt(code).strip().splitlines()[-1]
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
    r = s.query(":MEASure:RESults?").strip().split(",")
    img = s.query_binary_values(":DISPlay:DATA? PNG", datatype="B", container=bytes); open(f"fin_{tag}.png", "wb").write(img)
    med = statistics.median(v) if v else float("nan")
    return med, (max(v) - min(v)) / med * 100 if v else float("nan"), float(r[2*7+4-7]) if False else r
print("tag,clksel2,clksel,readback(ui uio),f8_median,f_x8,spread_pct,vtop,vbase", flush=True)
for tag, c2, c, ex in [("inv1x5", 1, 10, 0), ("inv2x161", 0, 15, 0), ("inv2x33", 0, 10, 0), ("inv2x3", 0, 2, 0), ("clk", 0, 0, 0)]:
    for rep in range(2):
        rb = setp(c2, c, ex); med, sp, r = meas(f"{tag}_{rep}")
        print(f"{tag},{c2},{c},{rb},{med:.6e},{med*8:.6e},{sp:.2f},{float(r[1*7+4]):.2f},{float(r[2*7+4]):.2f}", flush=True)
print("harmonic test: clksel 2 -> 15 without reset", flush=True)
for i in range(8):
    setp(0, 2, 0, reset=True); time.sleep(0.2); setp(0, 15, 0, reset=False)
    med, sp, r = meas(f"harm_{i}", n=15); print(f"harm,{i},{med*8/1e6:.3f} MHz", flush=True)
print("harmonic test: clksel 15 with reset", flush=True)
for i in range(4):
    setp(0, 15, 0, reset=True); med, sp, r = meas(f"harmR_{i}", n=15); print(f"harmR,{i},{med*8/1e6:.3f} MHz", flush=True)
