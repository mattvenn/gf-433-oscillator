import pyvisa,time,sys; rm=pyvisa.ResourceManager(); s=rm.open_resource('TCPIP0::192.168.50.11::inst0::INSTR'); s.timeout=15000
tag=sys.argv[1]; secs=float(sys.argv[2]) if len(sys.argv)>2 else 5
s.write(':MEASure:STATistics:RESet'); time.sleep(secs)
print(s.query(':MEASure:RESults?').strip())
img=s.query_binary_values(':DISPlay:DATA? PNG', datatype='B', container=bytes); open(f'scope_{tag}.png','wb').write(img)
