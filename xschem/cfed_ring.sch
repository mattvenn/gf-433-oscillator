v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {cfed_ring: 5-stage current-fed ring oscillator} -60 -620 0 0 0.7 0.7 {}
T {NMOS sources share vg: cfed_dac sinks the ring current, so the ring swings vg..VDD} -60 -560 0 0 0.42 0.42 {}
T {P 5/0.28, N 2/0.28 um (sim/vco/vco_bias.py, topo=cfed)} -60 -526 0 0 0.42 0.42 {}
N 160 -75 160 0 {}
N 160 0 160 75 {}
N 200 -45 200 0 {}
N 200 0 200 45 {}
N 200 -75 220 -75 {}
N 220 -75 220 -170 {}
N 200 75 220 75 {}
N 460 -75 460 0 {}
N 460 0 460 75 {}
N 500 -45 500 0 {}
N 500 0 500 45 {}
N 500 -75 520 -75 {}
N 520 -75 520 -170 {}
N 500 75 520 75 {}
N 760 -75 760 0 {}
N 760 0 760 75 {}
N 800 -45 800 0 {}
N 800 0 800 45 {}
N 800 -75 820 -75 {}
N 820 -75 820 -170 {}
N 800 75 820 75 {}
N 1060 -75 1060 0 {}
N 1060 0 1060 75 {}
N 1100 -45 1100 0 {}
N 1100 0 1100 45 {}
N 1100 -75 1120 -75 {}
N 1120 -75 1120 -170 {}
N 1100 75 1120 75 {}
N 1360 -75 1360 0 {}
N 1360 0 1360 75 {}
N 1400 -45 1400 0 {}
N 1400 0 1400 45 {}
N 1400 -75 1420 -75 {}
N 1420 -75 1420 -170 {}
N 1400 75 1420 75 {}
N 200 -105 200 -170 {}
N 500 -105 500 -170 {}
N 800 -105 800 -170 {}
N 1100 -105 1100 -170 {}
N 1400 -105 1400 -170 {}
N -60 -170 200 -170 {}
N 200 -170 220 -170 {}
N 220 -170 500 -170 {}
N 500 -170 520 -170 {}
N 520 -170 800 -170 {}
N 800 -170 820 -170 {}
N 820 -170 1100 -170 {}
N 1100 -170 1120 -170 {}
N 1120 -170 1400 -170 {}
N 1400 -170 1420 -170 {}
N 200 105 200 170 {}
N 500 105 500 170 {}
N 800 105 800 170 {}
N 1100 105 1100 170 {}
N 1400 105 1400 170 {}
N -60 170 200 170 {}
N 200 170 500 170 {}
N 500 170 800 170 {}
N 800 170 1100 170 {}
N 1100 170 1400 170 {}
N -60 330 0 330 {}
N 200 0 330 0 {}
N 330 0 460 0 {}
N 330 0 330 -400 {}
N 330 -400 1660 -400 {}
N 500 0 630 0 {}
N 630 0 760 0 {}
N 630 0 630 -360 {}
N 630 -360 1660 -360 {}
N 800 0 930 0 {}
N 930 0 1060 0 {}
N 930 0 930 -320 {}
N 930 -320 1660 -320 {}
N 1100 0 1230 0 {}
N 1230 0 1360 0 {}
N 1230 0 1230 -280 {}
N 1230 -280 1660 -280 {}
N 1400 0 1530 0 {}
N 1530 0 1600 0 {}
N 1600 0 1600 250 {}
N 1600 250 100 250 {}
N 100 250 100 0 {}
N 100 0 160 0 {}
N 1530 0 1530 -240 {}
N 1530 -240 1660 -240 {}
C {devices/iopin.sym} -60 -170 0 1 {name=p1
lab=VDD}
C {devices/iopin.sym} -60 170 0 1 {name=p2
lab=vg}
C {devices/iopin.sym} -60 330 0 1 {name=p3
lab=VSS}
C {devices/opin.sym} 1660 -240 0 0 {name=p8
lab=a0}
C {devices/opin.sym} 1660 -400 0 0 {name=p4
lab=a1}
C {devices/opin.sym} 1660 -360 0 0 {name=p5
lab=a2}
C {devices/opin.sym} 1660 -320 0 0 {name=p6
lab=a3}
C {devices/opin.sym} 1660 -280 0 0 {name=p7
lab=a4}
C {symbols/pfet_03v3.sym} 180 -75 0 0 {name=P0
L=0.28u
W=5.0u
nf=1
m=1
ad=2.5p
as=2.5p
pd=11.0u
ps=11.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="5/0.28"}
C {symbols/nfet_03v3.sym} 180 75 0 0 {name=N0
L=0.28u
W=2.0u
nf=1
m=1
ad=1.0p
as=1.0p
pd=5.0u
ps=5.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="2/0.28"}
C {symbols/gnd.sym} 220 75 0 0 {name=l1
lab=VSS}
C {symbols/pfet_03v3.sym} 480 -75 0 0 {name=P1
L=0.28u
W=5.0u
nf=1
m=1
ad=2.5p
as=2.5p
pd=11.0u
ps=11.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="5/0.28"}
C {symbols/nfet_03v3.sym} 480 75 0 0 {name=N1
L=0.28u
W=2.0u
nf=1
m=1
ad=1.0p
as=1.0p
pd=5.0u
ps=5.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="2/0.28"}
C {symbols/gnd.sym} 520 75 0 0 {name=l2
lab=VSS}
C {symbols/pfet_03v3.sym} 780 -75 0 0 {name=P2
L=0.28u
W=5.0u
nf=1
m=1
ad=2.5p
as=2.5p
pd=11.0u
ps=11.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="5/0.28"}
C {symbols/nfet_03v3.sym} 780 75 0 0 {name=N2
L=0.28u
W=2.0u
nf=1
m=1
ad=1.0p
as=1.0p
pd=5.0u
ps=5.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="2/0.28"}
C {symbols/gnd.sym} 820 75 0 0 {name=l3
lab=VSS}
C {symbols/pfet_03v3.sym} 1080 -75 0 0 {name=P3
L=0.28u
W=5.0u
nf=1
m=1
ad=2.5p
as=2.5p
pd=11.0u
ps=11.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="5/0.28"}
C {symbols/nfet_03v3.sym} 1080 75 0 0 {name=N3
L=0.28u
W=2.0u
nf=1
m=1
ad=1.0p
as=1.0p
pd=5.0u
ps=5.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="2/0.28"}
C {symbols/gnd.sym} 1120 75 0 0 {name=l4
lab=VSS}
C {symbols/pfet_03v3.sym} 1380 -75 0 0 {name=P4
L=0.28u
W=5.0u
nf=1
m=1
ad=2.5p
as=2.5p
pd=11.0u
ps=11.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="5/0.28"}
C {symbols/nfet_03v3.sym} 1380 75 0 0 {name=N4
L=0.28u
W=2.0u
nf=1
m=1
ad=1.0p
as=1.0p
pd=5.0u
ps=5.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="2/0.28"}
C {symbols/gnd.sym} 1420 75 0 0 {name=l5
lab=VSS}
C {symbols/gnd.sym} 0 330 0 0 {name=l6
lab=VSS}
