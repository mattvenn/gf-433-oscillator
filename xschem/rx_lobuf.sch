v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {x} -260 -74 0 0 0.3 0.3 {}
T {TGp} 370 950 0 0 0.3 0.3 {}
T {2.5/0.28} 370 986 0 0 0.3 0.3 {}
T {TGn} 740 950 0 0 0.3 0.3 {}
T {1/0.28} 740 986 0 0 0.3 0.3 {}
T {t} 120 -24 0 0 0.3 0.3 {}
T {ta} 420 -24 0 0 0.3 0.3 {}
T {tb} 420 876 0 0 0.3 0.3 {}
T {a} 780 -24 0 0 0.3 0.3 {}
T {b} 780 1076 0 0 0.3 0.3 {}
T {rx_lobuf: LO buffer with enable (one per arm)} -1100 -900 0 0 0.7 0.7 {}
T {x = NAND2(in, en) -> the TX splitter on x (a = in, b = !in, edges pulled together by the keeper) -> two arms NAND2(., en) + 3 inverters: lo = in & en, lob = !in & en} -1100 -840 0 0 0.42 0.42 {}
T {arm inverters N 0.8/0.28 / 2/0.28 / 5/0.28 um; en = 0: x high, every mixer switch off, nothing after the first NAND toggles; source: sim/rx/rx_lo.py lobuf()} -1100 -806 0 0 0.42 0.42 {}
N -480 -150 -460 -150 {}
N -280 -150 -260 -150 {}
N -380 0 -360 0 {}
N -380 100 -360 100 {}
N -480 -120 -480 -50 {}
N -280 -120 -280 -50 {}
N -480 -50 -380 -50 {}
N -380 -50 -280 -50 {}
N -380 -50 -380 -30 {}
N -380 30 -380 70 {}
N -700 0 -560 0 {}
N -560 0 -420 0 {}
N -560 0 -560 -150 {}
N -560 -150 -520 -150 {}
N -700 100 -620 100 {}
N -620 100 -420 100 {}
N -620 100 -620 -250 {}
N -620 -250 -360 -250 {}
N -360 -250 -360 -150 {}
N -360 -150 -320 -150 {}
N -1100 0 -700 0 {}
N -40 -75 -40 0 {}
N -40 0 -40 75 {}
N 0 -45 0 0 {}
N 0 0 0 45 {}
N 0 -75 20 -75 {}
N 0 75 20 75 {}
N -280 -50 -200 -50 {}
N -200 -50 -200 0 {}
N -200 0 -40 0 {}
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
N 1820 -150 1840 -150 {}
N 2020 -150 2040 -150 {}
N 1920 0 1940 0 {}
N 1920 100 1940 100 {}
N 1820 -120 1820 -50 {}
N 2020 -120 2020 -50 {}
N 1820 -50 1920 -50 {}
N 1920 -50 2020 -50 {}
N 1920 -50 1920 -30 {}
N 1920 30 1920 70 {}
N 1600 0 1740 0 {}
N 1740 0 1880 0 {}
N 1740 0 1740 -150 {}
N 1740 -150 1780 -150 {}
N 1600 100 1680 100 {}
N 1680 100 1880 100 {}
N 1680 100 1680 -250 {}
N 1680 -250 1940 -250 {}
N 1940 -250 1940 -150 {}
N 1940 -150 1980 -150 {}
N 1400 0 1600 0 {}
N 2260 -150 2260 -50 {}
N 2260 -50 2260 50 {}
N 2300 -120 2300 -50 {}
N 2300 -50 2300 20 {}
N 2300 -150 2320 -150 {}
N 2300 50 2320 50 {}
N 2020 -50 2260 -50 {}
N 2510 -150 2510 -50 {}
N 2510 -50 2510 50 {}
N 2550 -120 2550 -50 {}
N 2550 -50 2550 20 {}
N 2550 -150 2570 -150 {}
N 2550 50 2570 50 {}
N 2300 -50 2510 -50 {}
N 2760 -150 2760 -50 {}
N 2760 -50 2760 50 {}
N 2800 -120 2800 -50 {}
N 2800 -50 2800 20 {}
N 2800 -150 2820 -150 {}
N 2800 50 2820 50 {}
N 2550 -50 2760 -50 {}
N 2800 -50 3100 -50 {}
N 1820 950 1840 950 {}
N 2020 950 2040 950 {}
N 1920 1100 1940 1100 {}
N 1920 1200 1940 1200 {}
N 1820 980 1820 1050 {}
N 2020 980 2020 1050 {}
N 1820 1050 1920 1050 {}
N 1920 1050 2020 1050 {}
N 1920 1050 1920 1070 {}
N 1920 1130 1920 1170 {}
N 1600 1100 1740 1100 {}
N 1740 1100 1880 1100 {}
N 1740 1100 1740 950 {}
N 1740 950 1780 950 {}
N 1600 1200 1680 1200 {}
N 1680 1200 1880 1200 {}
N 1680 1200 1680 850 {}
N 1680 850 1940 850 {}
N 1940 850 1940 950 {}
N 1940 950 1980 950 {}
N 1400 1100 1600 1100 {}
N 2260 950 2260 1050 {}
N 2260 1050 2260 1150 {}
N 2300 980 2300 1050 {}
N 2300 1050 2300 1120 {}
N 2300 950 2320 950 {}
N 2300 1150 2320 1150 {}
N 2020 1050 2260 1050 {}
N 2510 950 2510 1050 {}
N 2510 1050 2510 1150 {}
N 2550 980 2550 1050 {}
N 2550 1050 2550 1120 {}
N 2550 950 2570 950 {}
N 2550 1150 2570 1150 {}
N 2300 1050 2510 1050 {}
N 2760 950 2760 1050 {}
N 2760 1050 2760 1150 {}
N 2800 980 2800 1050 {}
N 2800 1050 2800 1120 {}
N 2800 950 2820 950 {}
N 2800 1150 2820 1150 {}
N 2550 1050 2760 1050 {}
N 2800 1050 3100 1050 {}
N -700 100 -760 100 {}
N -760 100 -760 -520 {}
N 1550 -520 1550 100 {}
N 1550 100 1550 1200 {}
N 1550 100 1600 100 {}
N 1550 1200 1600 1200 {}
N -1100 -520 -760 -520 {}
N -760 -520 1550 -520 {}
N -1100 1500 -1040 1500 {}
N -1100 1560 -1040 1560 {}
C {devices/iopin.sym} -1100 1500 0 1 {name=p5
lab=VDD}
C {devices/iopin.sym} -1100 1560 0 1 {name=p6
lab=VSS}
C {devices/ipin.sym} -1100 0 0 0 {name=p1
lab=in}
C {devices/ipin.sym} -1100 -520 0 0 {name=p4
lab=en}
C {devices/opin.sym} 3100 -50 0 0 {name=p2
lab=lo}
C {devices/opin.sym} 3100 1050 0 0 {name=p3
lab=lob}
C {symbols/pfet_03v3.sym} -500 -150 0 0 {name=G0a
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
model=pfet_03v3
spiceprefix=X
val="0.6/0.28"}
C {symbols/pfet_03v3.sym} -300 -150 0 0 {name=G0b
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
model=pfet_03v3
spiceprefix=X
val="0.6/0.28"}
C {symbols/nfet_03v3.sym} -400 0 0 0 {name=G0c
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
C {symbols/nfet_03v3.sym} -400 100 0 0 {name=G0d
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
C {symbols/vdd.sym} -460 -150 0 0 {name=l1
lab=VDD}
C {symbols/vdd.sym} -260 -150 0 0 {name=l2
lab=VDD}
C {symbols/gnd.sym} -360 0 0 0 {name=l3
lab=VSS}
C {symbols/gnd.sym} -360 100 0 0 {name=l4
lab=VSS}
C {symbols/vdd.sym} -480 -180 0 0 {name=l5
lab=VDD}
C {symbols/vdd.sym} -280 -180 0 0 {name=l6
lab=VDD}
C {symbols/gnd.sym} -380 130 0 0 {name=l7
lab=VSS}
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
C {symbols/vdd.sym} 20 -75 0 0 {name=l8
lab=VDD}
C {symbols/vdd.sym} 0 -105 0 0 {name=l9
lab=VDD}
C {symbols/gnd.sym} 20 75 0 0 {name=l10
lab=VSS}
C {symbols/gnd.sym} 0 105 0 0 {name=l11
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
C {symbols/vdd.sym} 320 -75 0 0 {name=l12
lab=VDD}
C {symbols/vdd.sym} 300 -105 0 0 {name=l13
lab=VDD}
C {symbols/gnd.sym} 320 75 0 0 {name=l14
lab=VSS}
C {symbols/gnd.sym} 300 105 0 0 {name=l15
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
C {symbols/vdd.sym} 620 -75 0 0 {name=l16
lab=VDD}
C {symbols/vdd.sym} 600 -105 0 0 {name=l17
lab=VDD}
C {symbols/gnd.sym} 620 75 0 0 {name=l18
lab=VSS}
C {symbols/gnd.sym} 600 105 0 0 {name=l19
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
C {symbols/vdd.sym} 320 825 0 0 {name=l20
lab=VDD}
C {symbols/vdd.sym} 300 795 0 0 {name=l21
lab=VDD}
C {symbols/gnd.sym} 320 975 0 0 {name=l22
lab=VSS}
C {symbols/gnd.sym} 300 1005 0 0 {name=l23
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
C {symbols/vdd.sym} 580 980 0 0 {name=l24
lab=VDD}
C {symbols/gnd.sym} 620 980 0 0 {name=l25
lab=VSS}
C {symbols/gnd.sym} 480 980 0 0 {name=l26
lab=VSS}
C {symbols/vdd.sym} 720 980 0 0 {name=l27
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
C {symbols/vdd.sym} 1120 225 0 0 {name=l28
lab=VDD}
C {symbols/vdd.sym} 1100 195 0 0 {name=l29
lab=VDD}
C {symbols/gnd.sym} 1120 375 0 0 {name=l30
lab=VSS}
C {symbols/gnd.sym} 1100 405 0 0 {name=l31
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
C {symbols/vdd.sym} 1080 525 0 0 {name=l32
lab=VDD}
C {symbols/vdd.sym} 1100 495 0 0 {name=l33
lab=VDD}
C {symbols/gnd.sym} 1080 675 0 0 {name=l34
lab=VSS}
C {symbols/gnd.sym} 1100 705 0 0 {name=l35
lab=VSS}
C {symbols/pfet_03v3.sym} 1800 -150 0 0 {name=PGa
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
C {symbols/pfet_03v3.sym} 2000 -150 0 0 {name=PGb
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
C {symbols/nfet_03v3.sym} 1900 0 0 0 {name=PGc
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
C {symbols/nfet_03v3.sym} 1900 100 0 0 {name=PGd
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
C {symbols/vdd.sym} 1840 -150 0 0 {name=l36
lab=VDD}
C {symbols/vdd.sym} 2040 -150 0 0 {name=l37
lab=VDD}
C {symbols/gnd.sym} 1940 0 0 0 {name=l38
lab=VSS}
C {symbols/gnd.sym} 1940 100 0 0 {name=l39
lab=VSS}
C {symbols/vdd.sym} 1820 -180 0 0 {name=l40
lab=VDD}
C {symbols/vdd.sym} 2020 -180 0 0 {name=l41
lab=VDD}
C {symbols/gnd.sym} 1920 130 0 0 {name=l42
lab=VSS}
C {symbols/pfet_03v3.sym} 2280 -150 0 0 {name=P1p
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
model=pfet_03v3
spiceprefix=X
val="2/0.28"}
C {symbols/nfet_03v3.sym} 2280 50 0 0 {name=P1n
L=0.28u
W=0.7999999999999999u
nf=1
m=1
ad=0.39999999999999997p
as=0.39999999999999997p
pd=2.5999999999999996u
ps=2.5999999999999996u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.8/0.28"}
C {symbols/vdd.sym} 2320 -150 0 0 {name=l43
lab=VDD}
C {symbols/vdd.sym} 2300 -180 0 0 {name=l44
lab=VDD}
C {symbols/gnd.sym} 2320 50 0 0 {name=l45
lab=VSS}
C {symbols/gnd.sym} 2300 80 0 0 {name=l46
lab=VSS}
C {symbols/pfet_03v3.sym} 2530 -150 0 0 {name=P2p
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
C {symbols/nfet_03v3.sym} 2530 50 0 0 {name=P2n
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
C {symbols/vdd.sym} 2570 -150 0 0 {name=l47
lab=VDD}
C {symbols/vdd.sym} 2550 -180 0 0 {name=l48
lab=VDD}
C {symbols/gnd.sym} 2570 50 0 0 {name=l49
lab=VSS}
C {symbols/gnd.sym} 2550 80 0 0 {name=l50
lab=VSS}
C {symbols/pfet_03v3.sym} 2780 -150 0 0 {name=P3p
L=0.28u
W=12.499999999999998u
nf=1
m=1
ad=6.249999999999999p
as=6.249999999999999p
pd=25.999999999999996u
ps=25.999999999999996u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="12.5/0.28"}
C {symbols/nfet_03v3.sym} 2780 50 0 0 {name=P3n
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
model=nfet_03v3
spiceprefix=X
val="5/0.28"}
C {symbols/vdd.sym} 2820 -150 0 0 {name=l51
lab=VDD}
C {symbols/vdd.sym} 2800 -180 0 0 {name=l52
lab=VDD}
C {symbols/gnd.sym} 2820 50 0 0 {name=l53
lab=VSS}
C {symbols/gnd.sym} 2800 80 0 0 {name=l54
lab=VSS}
C {symbols/pfet_03v3.sym} 1800 950 0 0 {name=NGa
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
C {symbols/pfet_03v3.sym} 2000 950 0 0 {name=NGb
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
C {symbols/nfet_03v3.sym} 1900 1100 0 0 {name=NGc
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
C {symbols/nfet_03v3.sym} 1900 1200 0 0 {name=NGd
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
C {symbols/vdd.sym} 1840 950 0 0 {name=l55
lab=VDD}
C {symbols/vdd.sym} 2040 950 0 0 {name=l56
lab=VDD}
C {symbols/gnd.sym} 1940 1100 0 0 {name=l57
lab=VSS}
C {symbols/gnd.sym} 1940 1200 0 0 {name=l58
lab=VSS}
C {symbols/vdd.sym} 1820 920 0 0 {name=l59
lab=VDD}
C {symbols/vdd.sym} 2020 920 0 0 {name=l60
lab=VDD}
C {symbols/gnd.sym} 1920 1230 0 0 {name=l61
lab=VSS}
C {symbols/pfet_03v3.sym} 2280 950 0 0 {name=N1p
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
model=pfet_03v3
spiceprefix=X
val="2/0.28"}
C {symbols/nfet_03v3.sym} 2280 1150 0 0 {name=N1n
L=0.28u
W=0.7999999999999999u
nf=1
m=1
ad=0.39999999999999997p
as=0.39999999999999997p
pd=2.5999999999999996u
ps=2.5999999999999996u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.8/0.28"}
C {symbols/vdd.sym} 2320 950 0 0 {name=l62
lab=VDD}
C {symbols/vdd.sym} 2300 920 0 0 {name=l63
lab=VDD}
C {symbols/gnd.sym} 2320 1150 0 0 {name=l64
lab=VSS}
C {symbols/gnd.sym} 2300 1180 0 0 {name=l65
lab=VSS}
C {symbols/pfet_03v3.sym} 2530 950 0 0 {name=N2p
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
C {symbols/nfet_03v3.sym} 2530 1150 0 0 {name=N2n
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
C {symbols/vdd.sym} 2570 950 0 0 {name=l66
lab=VDD}
C {symbols/vdd.sym} 2550 920 0 0 {name=l67
lab=VDD}
C {symbols/gnd.sym} 2570 1150 0 0 {name=l68
lab=VSS}
C {symbols/gnd.sym} 2550 1180 0 0 {name=l69
lab=VSS}
C {symbols/pfet_03v3.sym} 2780 950 0 0 {name=N3p
L=0.28u
W=12.499999999999998u
nf=1
m=1
ad=6.249999999999999p
as=6.249999999999999p
pd=25.999999999999996u
ps=25.999999999999996u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="12.5/0.28"}
C {symbols/nfet_03v3.sym} 2780 1150 0 0 {name=N3n
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
model=nfet_03v3
spiceprefix=X
val="5/0.28"}
C {symbols/vdd.sym} 2820 950 0 0 {name=l70
lab=VDD}
C {symbols/vdd.sym} 2800 920 0 0 {name=l71
lab=VDD}
C {symbols/gnd.sym} 2820 1150 0 0 {name=l72
lab=VSS}
C {symbols/gnd.sym} 2800 1180 0 0 {name=l73
lab=VSS}
C {symbols/vdd.sym} -1040 1500 0 0 {name=l74
lab=VDD}
C {symbols/gnd.sym} -1040 1560 0 0 {name=l75
lab=VSS}
