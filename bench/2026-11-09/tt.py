#!/usr/bin/env python3
"""Run a snippet on the TT demo board's MicroPython via raw REPL. Usage: tt.py 'code' [timeout_s]"""
import sys, time, serial

PORT = "/dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_1c7ed99f3a9d6b89-if00"
code = sys.argv[1]
tmo = float(sys.argv[2]) if len(sys.argv) > 2 else 10

s = serial.Serial(PORT, 115200, timeout=0.2)
s.write(b"\r\x03\x03")
time.sleep(0.3)
s.read(100000)
s.write(b"\x01")  # raw REPL
time.sleep(0.2)
s.read(100000)
s.write(code.encode() + b"\x04")
buf = b""
t0 = time.time()
while time.time() - t0 < tmo:
    buf += s.read(4096)
    if buf.count(b"\x04") >= 2:
        break
s.write(b"\x02")  # back to friendly REPL
out = buf.split(b"\x04")
print(out[0].lstrip(b"OK").decode(errors="replace"))
if len(out) > 1 and out[1].strip():
    print("ERR:", out[1].decode(errors="replace"))
