v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {ls} 130 -24 0 0 0.3 0.3 {}
T {q1} 430 -24 0 0 0.3 0.3 {}
T {q2} 730 -24 0 0 0.3 0.3 {}
T {lsdiv: a0 level shifter + TSPC /4 + clock buffer} -300 -400 0 0 0.7 0.7 {}
T {ck = f(a0) / 4 at full rail, for the digital dividers; ls (the full-rail level-shifter output) is a port for the TX driver tap; give it its own VDD/VSS branch and ~10 pF decap (docs/lsdiv_design.md)} -300 -340 0 0 0.42 0.42 {}
T {source: sim/lsdiv/lsdiv.py block()} -300 -306 0 0 0.42 0.42 {}
N -300 0 -100 0 {}
N 100 0 150 0 {}
N 150 0 200 0 {}
N 150 0 150 -200 {}
N 150 -200 1100 -200 {}
N 400 0 500 0 {}
N 860 -75 860 0 {}
N 860 0 860 75 {}
N 900 -45 900 0 {}
N 900 0 900 45 {}
N 900 -75 920 -75 {}
N 900 75 920 75 {}
N 700 0 860 0 {}
N 900 0 1100 0 {}
N -300 260 -240 260 {}
N -300 320 -240 320 {}
C {devices/iopin.sym} -300 260 0 1 {name=p4
lab=VDD}
C {devices/iopin.sym} -300 320 0 1 {name=p5
lab=VSS}
C {devices/ipin.sym} -300 0 0 0 {name=p1
lab=a0}
C {devices/opin.sym} 1100 0 0 0 {name=p3
lab=ck}
C {devices/opin.sym} 1100 -200 0 0 {name=p2
lab=ls}
C {ls_ac.sym} 0 0 0 0 {name=xls}
C {tspc_t1.sym} 300 0 0 0 {name=xd1}
C {tspc_t2.sym} 600 0 0 0 {name=xd2}
C {symbols/pfet_03v3.sym} 880 -75 0 0 {name=B1p
L=0.28u
W=2.5u
nf=1
m=1
ad=1.25p
as=1.25p
pd=6.0u
ps=6.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="2.5/0.28"}
C {symbols/nfet_03v3.sym} 880 75 0 0 {name=B1n
L=0.28u
W=1.0u
nf=1
m=1
ad=0.5p
as=0.5p
pd=3.0u
ps=3.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="1/0.28"}
C {symbols/vdd.sym} 920 -75 0 0 {name=l1
lab=VDD}
C {symbols/gnd.sym} 920 75 0 0 {name=l2
lab=VSS}
C {symbols/vdd.sym} 900 -105 0 0 {name=l3
lab=VDD}
C {symbols/gnd.sym} 900 105 0 0 {name=l4
lab=VSS}
C {symbols/vdd.sym} -50 -50 0 0 {name=l5
lab=VDD}
C {symbols/gnd.sym} -50 50 0 0 {name=l6
lab=VSS}
C {symbols/vdd.sym} 250 -50 0 0 {name=l7
lab=VDD}
C {symbols/gnd.sym} 250 50 0 0 {name=l8
lab=VSS}
C {symbols/vdd.sym} 550 -50 0 0 {name=l9
lab=VDD}
C {symbols/gnd.sym} 550 50 0 0 {name=l10
lab=VSS}
C {symbols/vdd.sym} -240 260 0 0 {name=l11
lab=VDD}
C {symbols/gnd.sym} -240 320 0 0 {name=l12
lab=VSS}
