v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {x} 20 -24 0 0 0.3 0.3 {}
T {y} 380 -24 0 0 0.3 0.3 {}
T {qb} 740 -24 0 0 0.3 0.3 {}
T {tspc_t2: TSPC toggle flip-flop (q = clk / 2)} -300 -640 0 0 0.7 0.7 {}
T {true single-phase clock DFF with D = qb: clk low precharges y and passes qb into x; the clk rising edge evaluates y and writes qb} -300 -580 0 0 0.42 0.42 {}
T {nfet / pfet 0.6/0.28 / 1.2/0.28 um, Q inverter 0.6/0.28 / 1.5/0.28} -300 -546 0 0 0.42 0.42 {}
N 0 -150 20 -150 {}
N 0 -60 20 -60 {}
N 0 60 20 60 {}
N 360 -60 380 -60 {}
N 360 60 380 60 {}
N 360 150 380 150 {}
N 720 -60 740 -60 {}
N 720 60 740 60 {}
N 720 150 740 150 {}
N 0 -120 0 -90 {}
N 360 90 360 120 {}
N 720 90 720 120 {}
N 0 -30 0 0 {}
N 0 0 0 30 {}
N 360 -30 360 0 {}
N 360 0 360 30 {}
N 720 -30 720 0 {}
N 720 0 720 30 {}
N 1040 -75 1040 0 {}
N 1040 0 1040 75 {}
N 1080 -45 1080 0 {}
N 1080 0 1080 45 {}
N 1080 -75 1100 -75 {}
N 1080 75 1100 75 {}
N 0 -180 0 -240 {}
N 360 -90 360 -240 {}
N 720 -90 720 -240 {}
N 1080 -105 1080 -240 {}
N 0 -240 360 -240 {}
N 360 -240 720 -240 {}
N 720 -240 1080 -240 {}
N 0 90 0 240 {}
N 360 180 360 240 {}
N 720 180 720 240 {}
N 1080 105 1080 240 {}
N 0 240 360 240 {}
N 360 240 720 240 {}
N 720 240 1080 240 {}
N 1080 0 1250 0 {}
N 0 0 240 0 {}
N 240 0 240 60 {}
N 240 60 320 60 {}
N 360 0 640 0 {}
N 640 -60 640 0 {}
N 640 0 640 150 {}
N 640 -60 680 -60 {}
N 640 150 680 150 {}
N 720 0 780 0 {}
N 780 0 1040 0 {}
N 780 0 780 -330 {}
N 780 -330 -120 -330 {}
N -120 -330 -120 -150 {}
N -120 -150 -120 60 {}
N -120 -150 -40 -150 {}
N -120 60 -40 60 {}
N -300 330 -80 330 {}
N -80 330 280 330 {}
N 280 330 600 330 {}
N -80 330 -80 -60 {}
N -80 -60 -40 -60 {}
N 280 -60 280 150 {}
N 280 150 280 330 {}
N 280 -60 320 -60 {}
N 280 150 320 150 {}
N 600 330 600 60 {}
N 600 60 680 60 {}
N -300 520 -240 520 {}
N -300 580 -240 580 {}
C {devices/iopin.sym} -300 520 0 1 {name=p3
lab=VDD}
C {devices/iopin.sym} -300 580 0 1 {name=p4
lab=VSS}
C {devices/ipin.sym} -300 330 0 0 {name=p2
lab=clk}
C {devices/opin.sym} 1250 0 0 0 {name=p1
lab=q}
C {symbols/pfet_03v3.sym} -20 -150 0 0 {name=p1
L=0.28u
W=1.2u
nf=1
m=1
ad=0.6p
as=0.6p
pd=3.4u
ps=3.4u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="1.2/0.28"}
C {symbols/vdd.sym} 20 -150 0 0 {name=l1
lab=VDD}
C {symbols/pfet_03v3.sym} -20 -60 0 0 {name=p2
L=0.28u
W=1.2u
nf=1
m=1
ad=0.6p
as=0.6p
pd=3.4u
ps=3.4u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="1.2/0.28"}
C {symbols/vdd.sym} 20 -60 0 0 {name=l2
lab=VDD}
C {symbols/nfet_03v3.sym} -20 60 0 0 {name=n1
L=0.28u
W=0.6u
nf=1
m=1
ad=0.3p
as=0.3p
pd=2.2u
ps=2.2u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.6/0.28"}
C {symbols/gnd.sym} 20 60 0 0 {name=l3
lab=VSS}
C {symbols/pfet_03v3.sym} 340 -60 0 0 {name=p3
L=0.28u
W=1.2u
nf=1
m=1
ad=0.6p
as=0.6p
pd=3.4u
ps=3.4u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="1.2/0.28"}
C {symbols/vdd.sym} 380 -60 0 0 {name=l4
lab=VDD}
C {symbols/nfet_03v3.sym} 340 60 0 0 {name=n2
L=0.28u
W=0.6u
nf=1
m=1
ad=0.3p
as=0.3p
pd=2.2u
ps=2.2u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.6/0.28"}
C {symbols/gnd.sym} 380 60 0 0 {name=l5
lab=VSS}
C {symbols/nfet_03v3.sym} 340 150 0 0 {name=n3
L=0.28u
W=0.6u
nf=1
m=1
ad=0.3p
as=0.3p
pd=2.2u
ps=2.2u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.6/0.28"}
C {symbols/gnd.sym} 380 150 0 0 {name=l6
lab=VSS}
C {symbols/pfet_03v3.sym} 700 -60 0 0 {name=p4
L=0.28u
W=1.2u
nf=1
m=1
ad=0.6p
as=0.6p
pd=3.4u
ps=3.4u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="1.2/0.28"}
C {symbols/vdd.sym} 740 -60 0 0 {name=l7
lab=VDD}
C {symbols/nfet_03v3.sym} 700 60 0 0 {name=n4
L=0.28u
W=0.6u
nf=1
m=1
ad=0.3p
as=0.3p
pd=2.2u
ps=2.2u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.6/0.28"}
C {symbols/gnd.sym} 740 60 0 0 {name=l8
lab=VSS}
C {symbols/nfet_03v3.sym} 700 150 0 0 {name=n5
L=0.28u
W=0.6u
nf=1
m=1
ad=0.3p
as=0.3p
pd=2.2u
ps=2.2u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.6/0.28"}
C {symbols/gnd.sym} 740 150 0 0 {name=l9
lab=VSS}
C {symbols/pfet_03v3.sym} 1060 -75 0 0 {name=qp
L=0.28u
W=1.5u
nf=1
m=1
ad=0.75p
as=0.75p
pd=4.0u
ps=4.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="1.5/0.28"}
C {symbols/nfet_03v3.sym} 1060 75 0 0 {name=qn
L=0.28u
W=0.6u
nf=1
m=1
ad=0.3p
as=0.3p
pd=2.2u
ps=2.2u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.6/0.28"}
C {symbols/vdd.sym} 1100 -75 0 0 {name=l10
lab=VDD}
C {symbols/gnd.sym} 1100 75 0 0 {name=l11
lab=VSS}
C {symbols/vdd.sym} 0 -240 0 0 {name=l12
lab=VDD}
C {symbols/gnd.sym} 0 240 0 0 {name=l13
lab=VSS}
C {symbols/vdd.sym} -240 520 0 0 {name=l14
lab=VDD}
C {symbols/gnd.sym} -240 580 0 0 {name=l15
lab=VSS}
