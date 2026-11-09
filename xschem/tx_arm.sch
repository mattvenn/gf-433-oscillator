v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {M1} 90 120 0 0 0.3 0.3 {}
T {y1} 170 -74 0 0 0.3 0.3 {}
T {M2} 340 120 0 0 0.3 0.3 {}
T {y2} 420 -74 0 0 0.3 0.3 {}
T {M3} 590 120 0 0 0.3 0.3 {}
T {y3} 670 -74 0 0 0.3 0.3 {}
T {M4} 840 120 0 0 0.3 0.3 {}
T {y4} 920 -74 0 0 0.3 0.3 {}
T {M5} 1090 120 0 0 0.3 0.3 {}
T {y0} -180 -74 0 0 0.3 0.3 {}
T {ns} -290 26 0 0 0.3 0.3 {}
T {tx_arm: one antenna arm, out = in & en} -700 -480 0 0 0.7 0.7 {}
T {NAND2 then 5 inverters (6 inversions); en = 0 holds out low, so with both arms off there is no DC across the dipole} -700 -420 0 0 0.42 0.42 {}
T {inverter N widths 0.42 / 0.625 / 2.5 / 10 / 40 um, P = 2.5 N, L 0.28 um (taper x4)} -700 -386 0 0 0.42 0.42 {}
N -400 -150 -380 -150 {}
N -200 -150 -180 -150 {}
N -300 0 -280 0 {}
N -300 100 -280 100 {}
N -400 -120 -400 -50 {}
N -200 -120 -200 -50 {}
N -400 -50 -300 -50 {}
N -300 -50 -200 -50 {}
N -300 -50 -300 -30 {}
N -300 30 -300 70 {}
N -700 0 -460 0 {}
N -460 0 -340 0 {}
N -460 0 -460 -150 {}
N -460 -150 -440 -150 {}
N -700 100 -560 100 {}
N -560 100 -340 100 {}
N -560 100 -560 -250 {}
N -560 -250 -260 -250 {}
N -260 -250 -260 -150 {}
N -260 -150 -240 -150 {}
N 110 -150 110 -50 {}
N 110 -50 110 50 {}
N 150 -120 150 -50 {}
N 150 -50 150 20 {}
N 150 -150 170 -150 {}
N 150 50 170 50 {}
N -200 -50 110 -50 {}
N 360 -150 360 -50 {}
N 360 -50 360 50 {}
N 400 -120 400 -50 {}
N 400 -50 400 20 {}
N 400 -150 420 -150 {}
N 400 50 420 50 {}
N 150 -50 360 -50 {}
N 610 -150 610 -50 {}
N 610 -50 610 50 {}
N 650 -120 650 -50 {}
N 650 -50 650 20 {}
N 650 -150 670 -150 {}
N 650 50 670 50 {}
N 400 -50 610 -50 {}
N 860 -150 860 -50 {}
N 860 -50 860 50 {}
N 900 -120 900 -50 {}
N 900 -50 900 20 {}
N 900 -150 920 -150 {}
N 900 50 920 50 {}
N 650 -50 860 -50 {}
N 1110 -150 1110 -50 {}
N 1110 -50 1110 50 {}
N 1150 -120 1150 -50 {}
N 1150 -50 1150 20 {}
N 1150 -150 1170 -150 {}
N 1150 50 1170 50 {}
N 900 -50 1110 -50 {}
N 1150 -50 1300 -50 {}
N -700 400 -640 400 {}
N -700 460 -640 460 {}
C {devices/iopin.sym} -700 400 0 1 {name=p4
lab=VDD}
C {devices/iopin.sym} -700 460 0 1 {name=p5
lab=VSS}
C {devices/ipin.sym} -700 0 0 0 {name=p1
lab=in}
C {devices/ipin.sym} -700 100 0 0 {name=p2
lab=en}
C {devices/opin.sym} 1300 -50 0 0 {name=p3
lab=out}
C {symbols/pfet_03v3.sym} -420 -150 0 0 {name=NAp
L=0.28u
W=1.25u
nf=1
m=1
ad=0.625p
as=0.625p
pd=3.5u
ps=3.5u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="1.25/0.28"}
C {symbols/pfet_03v3.sym} -220 -150 0 0 {name=NBp
L=0.28u
W=1.25u
nf=1
m=1
ad=0.625p
as=0.625p
pd=3.5u
ps=3.5u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="1.25/0.28"}
C {symbols/nfet_03v3.sym} -320 0 0 0 {name=NAn
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
C {symbols/nfet_03v3.sym} -320 100 0 0 {name=NBn
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
C {symbols/vdd.sym} -380 -150 0 0 {name=l1
lab=VDD}
C {symbols/vdd.sym} -180 -150 0 0 {name=l2
lab=VDD}
C {symbols/gnd.sym} -280 0 0 0 {name=l3
lab=VSS}
C {symbols/gnd.sym} -280 100 0 0 {name=l4
lab=VSS}
C {symbols/vdd.sym} -400 -180 0 0 {name=l5
lab=VDD}
C {symbols/vdd.sym} -200 -180 0 0 {name=l6
lab=VDD}
C {symbols/gnd.sym} -300 130 0 0 {name=l7
lab=VSS}
C {symbols/pfet_03v3.sym} 130 -150 0 0 {name=M1p
L=0.28u
W=1.0499999999999998u
nf=1
m=1
ad=0.5249999999999999p
as=0.5249999999999999p
pd=3.0999999999999996u
ps=3.0999999999999996u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="1.05/0.28"}
C {symbols/nfet_03v3.sym} 130 50 0 0 {name=M1n
L=0.28u
W=0.41999999999999993u
nf=1
m=1
ad=0.20999999999999996p
as=0.20999999999999996p
pd=1.8399999999999999u
ps=1.8399999999999999u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.42/0.28"}
C {symbols/vdd.sym} 170 -150 0 0 {name=l8
lab=VDD}
C {symbols/gnd.sym} 170 50 0 0 {name=l9
lab=VSS}
C {symbols/vdd.sym} 150 -180 0 0 {name=l10
lab=VDD}
C {symbols/gnd.sym} 150 80 0 0 {name=l11
lab=VSS}
C {symbols/pfet_03v3.sym} 380 -150 0 0 {name=M2p
L=0.28u
W=1.5624999999999998u
nf=1
m=1
ad=0.7812499999999999p
as=0.7812499999999999p
pd=4.125u
ps=4.125u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="1.5625/0.28"}
C {symbols/nfet_03v3.sym} 380 50 0 0 {name=M2n
L=0.28u
W=0.625u
nf=1
m=1
ad=0.3125p
as=0.3125p
pd=2.25u
ps=2.25u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.625/0.28"}
C {symbols/vdd.sym} 420 -150 0 0 {name=l12
lab=VDD}
C {symbols/gnd.sym} 420 50 0 0 {name=l13
lab=VSS}
C {symbols/vdd.sym} 400 -180 0 0 {name=l14
lab=VDD}
C {symbols/gnd.sym} 400 80 0 0 {name=l15
lab=VSS}
C {symbols/pfet_03v3.sym} 630 -150 0 0 {name=M3p
L=0.28u
W=6.249999999999999u
nf=1
m=1
ad=3.1249999999999996p
as=3.1249999999999996p
pd=13.499999999999998u
ps=13.499999999999998u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="6.25/0.28"}
C {symbols/nfet_03v3.sym} 630 50 0 0 {name=M3n
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
model=nfet_03v3
spiceprefix=X
val="2.5/0.28"}
C {symbols/vdd.sym} 670 -150 0 0 {name=l16
lab=VDD}
C {symbols/gnd.sym} 670 50 0 0 {name=l17
lab=VSS}
C {symbols/vdd.sym} 650 -180 0 0 {name=l18
lab=VDD}
C {symbols/gnd.sym} 650 80 0 0 {name=l19
lab=VSS}
C {symbols/pfet_03v3.sym} 880 -150 0 0 {name=M4p
L=0.28u
W=24.999999999999996u
nf=1
m=1
ad=12.499999999999998p
as=12.499999999999998p
pd=50.99999999999999u
ps=50.99999999999999u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="25/0.28"}
C {symbols/nfet_03v3.sym} 880 50 0 0 {name=M4n
L=0.28u
W=10.0u
nf=1
m=1
ad=5.0p
as=5.0p
pd=21.0u
ps=21.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="10/0.28"}
C {symbols/vdd.sym} 920 -150 0 0 {name=l20
lab=VDD}
C {symbols/gnd.sym} 920 50 0 0 {name=l21
lab=VSS}
C {symbols/vdd.sym} 900 -180 0 0 {name=l22
lab=VDD}
C {symbols/gnd.sym} 900 80 0 0 {name=l23
lab=VSS}
C {symbols/pfet_03v3.sym} 1130 -150 0 0 {name=M5p
L=0.28u
W=99.99999999999999u
nf=1
m=1
ad=49.99999999999999p
as=49.99999999999999p
pd=200.99999999999997u
ps=200.99999999999997u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="100/0.28"}
C {symbols/nfet_03v3.sym} 1130 50 0 0 {name=M5n
L=0.28u
W=40.0u
nf=1
m=1
ad=20.0p
as=20.0p
pd=81.0u
ps=81.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="40/0.28"}
C {symbols/vdd.sym} 1170 -150 0 0 {name=l24
lab=VDD}
C {symbols/gnd.sym} 1170 50 0 0 {name=l25
lab=VSS}
C {symbols/vdd.sym} 1150 -180 0 0 {name=l26
lab=VDD}
C {symbols/gnd.sym} 1150 80 0 0 {name=l27
lab=VSS}
C {symbols/vdd.sym} -640 400 0 0 {name=l28
lab=VDD}
C {symbols/gnd.sym} -640 460 0 0 {name=l29
lab=VSS}
