#!/usr/bin/env python3
"""RP2350 project clock -> TT chip (clksel=0) -> uio[7] (/8). Compare integer vs fractional clocking."""
import subprocess, sys, time, pyvisa
TT = sys.argv[1]
s = pyvisa.ResourceManager().open_resource("TCPIP0::192.168.50.11::inst0::INSTR"); s.timeout = 15000
s.write(":TRIGger:SWEep NORMal"); s.write(":TRIGger:EDGE:LEVel 1.65")
s.write(":MEASure:CLEar")
for m in ("FREQuency", "PERiod", "VTOP", "VBASe"): s.write(f":MEASure:{m} CHANnel1")
s.write(":TIMebase:SCALe 200E-9")

REG = """
import machine
b=0x400a8000; d=machine.mem32[b+4]; top=machine.mem32[b+0x10]; f=0x40050000
prim=machine.mem32[f+12]
print("sys", machine.freq(), "fbdiv", machine.mem32[f+8], "pd", (prim>>16)&7, (prim>>12)&7, "pwm div", (d>>4)&0xff, d&0xf, "top", top)
"""
CASES = {
    "int_13M56": "import machine\nmachine.freq(135_600_000)\ntt.pins.rp_projclk.pwm(13_560_000, 32768)\n",
    "int_27M12": "import machine\nmachine.freq(135_600_000)\ntt.pins.rp_projclk.pwm(27_120_000, 32768)\n",
    "sdk_13M56": "tt.clock_project_PWM(13_560_000)\n",
    # fractional: sys 133 MHz, top=1 (2 counts), div 4+14/16 -> 13.641 MHz, divider alternates 4/5 sys cycles
    "frac_13M6": "import machine\nmachine.freq(133_000_000)\ntt.pins.rp_projclk.pwm(13_560_000, 32768)\n"
                 "b=0x400a8000\nmachine.mem32[b+0x10]=1\nmachine.mem32[b+0xc]=1\nmachine.mem32[b+4]=(4<<4)|14\n",
}
print("case,setup,f8_mean,f_clk,per8_sd_ps,per8_pkpk_ps,vtop,vbase,count")
for name, code in CASES.items():
    r = subprocess.run(["python3", TT, "tt.uio_in.value=0\ntt.ui_in.value=0\n" + code + REG, "15"], capture_output=True, text=True)
    setup = [l for l in r.stdout.splitlines() if l.startswith("sys")]
    time.sleep(1); s.write(":MEASure:STATistics:RESet"); time.sleep(8)
    x = s.query(":MEASure:RESults?").strip().split(",")
    g = lambda i, k: float(x[i * 7 + k])
    print(f"{name},{setup[-1] if setup else r.stdout[-200:]!r},{g(0,4):.6e},{g(0,4)*8:.6e},{g(1,5)*1e12:.1f},"
          f"{(g(1,3)-g(1,2))*1e12:.0f},{g(2,4):.2f},{g(3,4):.2f},{int(g(0,6))}", flush=True)
    img = s.query_binary_values(":DISPlay:DATA? PNG", datatype="B", container=bytes)
    open(f"ref_{name}.png", "wb").write(img)
