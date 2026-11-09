import subprocess,sys,time,pyvisa
TT=sys.argv[1]; c=int(sys.argv[2]); n=int(sys.argv[3])
s=pyvisa.ResourceManager().open_resource('TCPIP0::192.168.50.11::inst0::INSTR'); s.timeout=15000
for i in range(n):
    subprocess.run(["python3",TT,f"import time\ntt.ui_in.value={c}\ntt.reset_project(True); time.sleep_ms(5); tt.reset_project(False)\nprint(1)","10"],capture_output=True)
    time.sleep(0.3); s.write(':MEASure:STATistics:RESet'); time.sleep(2)
    r=s.query(':MEASure:RESults?').strip().split(',')
    print(i, 'median-ish current', r[1], 'mean', float(r[4])/1e6, 'MHz  x8 =', float(r[4])*8/1e6, flush=True)
