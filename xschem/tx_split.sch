v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {t} 120 -24 0 0 0.3 0.3 {}
T {ta} 420 -24 0 0 0.3 0.3 {}
T {tb} 420 876 0 0 0.3 0.3 {}
T {a} 780 -24 0 0 0.3 0.3 {}
T {b} 780 1076 0 0 0.3 0.3 {}
T {TGp} 370 950 0 0 0.3 0.3 {}
T {2.5/0.28} 370 986 0 0 0.3 0.3 {}
T {TGn} 740 950 0 0 0.3 0.3 {}
T {1/0.28} 740 986 0 0 0.3 0.3 {}
T {keeper (weak)} 1160 420 0 0 0.3 0.3 {}
T {tx_split: tap on ls + phase splitter (a = !ls, b = ls)} -300 -330 0 0 0.7 0.7 {}
T {T is the only load on lsdiv's ls node; path a has two inverters, path b one inverter and an always-on transmission gate that stands in for the second inverter's delay} -300 -270 0 0 0.42 0.42 {}
T {the weak cross-coupled pair XA / XB pulls the a and b edges together (target skew <= 10 ps)} -300 -236 0 0 0.42 0.42 {}
N -40 -75 -40 0 {}
N -40 0 -40 75 {}
N 0 -45 0 0 {}
N 0 0 0 45 {}
N 0 -75 20 -75 {}
N 0 75 20 75 {}
N -300 0 -40 0 {}
N 260 -75 260 0 {}
N 260 0 260 75 {}
N 300 -45 300 0 {}
N 300 0 300 45 {}
N 300 -75 320 -75 {}
N 300 75 320 75 {}
N 560 -75 560 0 {}
N 560 0 560 75 {}
N 600 -45 600 0 {}
N 600 0 600 45 {}
N 600 -75 620 -75 {}
N 600 75 620 75 {}
N 260 825 260 900 {}
N 260 900 260 975 {}
N 300 855 300 900 {}
N 300 900 300 945 {}
N 300 825 320 825 {}
N 300 975 320 975 {}
N 0 0 100 0 {}
N 100 0 260 0 {}
N 100 0 100 900 {}
N 100 900 260 900 {}
N 300 0 560 0 {}
N 560 980 580 980 {}
N 640 980 620 980 {}
N 520 980 480 980 {}
N 680 980 720 980 {}
N 560 950 560 930 {}
N 560 930 600 930 {}
N 640 950 640 930 {}
N 640 930 600 930 {}
N 300 900 600 900 {}
N 600 900 600 930 {}
N 560 1010 560 1030 {}
N 560 1030 600 1030 {}
N 640 1010 640 1030 {}
N 640 1030 600 1030 {}
N 600 1030 600 1100 {}
N 1060 225 1060 300 {}
N 1060 300 1060 375 {}
N 1100 255 1100 300 {}
N 1100 300 1100 345 {}
N 1100 225 1120 225 {}
N 1100 375 1120 375 {}
N 1140 525 1140 600 {}
N 1140 600 1140 675 {}
N 1100 555 1100 600 {}
N 1100 600 1100 645 {}
N 1100 525 1080 525 {}
N 1100 675 1080 675 {}
N 600 0 950 0 {}
N 950 0 1400 0 {}
N 950 0 950 300 {}
N 950 300 950 600 {}
N 950 300 1060 300 {}
N 1100 600 950 600 {}
N 600 1100 1250 1100 {}
N 1250 1100 1400 1100 {}
N 1250 300 1250 600 {}
N 1250 600 1250 1100 {}
N 1100 300 1250 300 {}
N 1140 600 1250 600 {}
N -300 1300 -240 1300 {}
N -300 1360 -240 1360 {}
C {devices/iopin.sym} -300 1300 0 1 {name=p4
lab=VDD}
C {devices/iopin.sym} -300 1360 0 1 {name=p5
lab=VSS}
C {devices/ipin.sym} -300 0 0 0 {name=p1
lab=ls}
C {devices/opin.sym} 1400 0 0 0 {name=p2
lab=a}
C {devices/opin.sym} 1400 1100 0 0 {name=p3
lab=b}
C {symbols/pfet_03v3.sym} -20 -75 0 0 {name=Tp
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
C {symbols/nfet_03v3.sym} -20 75 0 0 {name=Tn
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
C {symbols/vdd.sym} 20 -75 0 0 {name=l1
lab=VDD}
C {symbols/gnd.sym} 20 75 0 0 {name=l2
lab=VSS}
C {symbols/vdd.sym} 0 -105 0 0 {name=l3
lab=VDD}
C {symbols/gnd.sym} 0 105 0 0 {name=l4
lab=VSS}
C {symbols/pfet_03v3.sym} 280 -75 0 0 {name=A1p
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
C {symbols/nfet_03v3.sym} 280 75 0 0 {name=A1n
L=0.28u
W=0.5u
nf=1
m=1
ad=0.25p
as=0.25p
pd=2.0u
ps=2.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.5/0.28"}
C {symbols/vdd.sym} 320 -75 0 0 {name=l5
lab=VDD}
C {symbols/gnd.sym} 320 75 0 0 {name=l6
lab=VSS}
C {symbols/vdd.sym} 300 -105 0 0 {name=l7
lab=VDD}
C {symbols/gnd.sym} 300 105 0 0 {name=l8
lab=VSS}
C {symbols/pfet_03v3.sym} 580 -75 0 0 {name=A2p
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
C {symbols/nfet_03v3.sym} 580 75 0 0 {name=A2n
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
C {symbols/vdd.sym} 620 -75 0 0 {name=l9
lab=VDD}
C {symbols/gnd.sym} 620 75 0 0 {name=l10
lab=VSS}
C {symbols/vdd.sym} 600 -105 0 0 {name=l11
lab=VDD}
C {symbols/gnd.sym} 600 105 0 0 {name=l12
lab=VSS}
C {symbols/pfet_03v3.sym} 280 825 0 0 {name=B1p
L=0.28u
W=3.7499999999999996u
nf=1
m=1
ad=1.8749999999999998p
as=1.8749999999999998p
pd=8.5u
ps=8.5u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="3.75/0.28"}
C {symbols/nfet_03v3.sym} 280 975 0 0 {name=B1n
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
model=nfet_03v3
spiceprefix=X
val="1.5/0.28"}
C {symbols/vdd.sym} 320 825 0 0 {name=l13
lab=VDD}
C {symbols/gnd.sym} 320 975 0 0 {name=l14
lab=VSS}
C {symbols/vdd.sym} 300 795 0 0 {name=l15
lab=VDD}
C {symbols/gnd.sym} 300 1005 0 0 {name=l16
lab=VSS}
C {symbols/pfet_03v3.sym} 540 980 0 0 {name=TGp
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
val="2.5/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 660 980 2 0 {name=TGn
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
val="1/0.28"
hide_texts=true}
C {symbols/vdd.sym} 580 980 0 0 {name=l17
lab=VDD}
C {symbols/gnd.sym} 620 980 0 0 {name=l18
lab=VSS}
C {symbols/gnd.sym} 480 980 0 0 {name=l19
lab=VSS}
C {symbols/vdd.sym} 720 980 0 0 {name=l20
lab=VDD}
C {symbols/pfet_03v3.sym} 1080 225 0 0 {name=XBp
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
C {symbols/nfet_03v3.sym} 1080 375 0 0 {name=XBn
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
C {symbols/vdd.sym} 1120 225 0 0 {name=l21
lab=VDD}
C {symbols/gnd.sym} 1120 375 0 0 {name=l22
lab=VSS}
C {symbols/vdd.sym} 1100 195 0 0 {name=l23
lab=VDD}
C {symbols/gnd.sym} 1100 405 0 0 {name=l24
lab=VSS}
C {symbols/pfet_03v3.sym} 1120 525 0 1 {name=XAp
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
C {symbols/nfet_03v3.sym} 1120 675 0 1 {name=XAn
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
C {symbols/vdd.sym} 1080 525 0 0 {name=l25
lab=VDD}
C {symbols/gnd.sym} 1080 675 0 0 {name=l26
lab=VSS}
C {symbols/vdd.sym} 1100 495 0 0 {name=l27
lab=VDD}
C {symbols/gnd.sym} 1100 705 0 0 {name=l28
lab=VSS}
C {symbols/vdd.sym} -240 1300 0 0 {name=l29
lab=VDD}
C {symbols/gnd.sym} -240 1360 0 0 {name=l30
lab=VSS}
