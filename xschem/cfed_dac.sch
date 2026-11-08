v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {fine (vctrl)} -50 100 0 0 0.35 0.35 {}
T {base, k = 6} 210 100 0 0 0.35 0.35 {}
T {bit 0} 590 100 0 0 0.35 0.35 {}
T {bit 1} 970 100 0 0 0.35 0.35 {}
T {bit 2} 1350 100 0 0 0.35 0.35 {}
T {bit 3} 1730 100 0 0 0.35 0.35 {}
T {bit 4} 2110 100 0 0 0.35 0.35 {}
T {g0} 520 -324 0 0 0.3 0.3 {}
T {TP0} 285 -420 0 0 0.3 0.3 {}
T {5/0.28} 285 -384 0 0 0.3 0.3 {}
T {TN0} 505 -420 0 0 0.3 0.3 {}
T {2/0.28} 505 -384 0 0 0.3 0.3 {}
T {g1} 900 -324 0 0 0.3 0.3 {}
T {TP1} 665 -420 0 0 0.3 0.3 {}
T {5/0.28} 665 -384 0 0 0.3 0.3 {}
T {TN1} 885 -420 0 0 0.3 0.3 {}
T {2/0.28} 885 -384 0 0 0.3 0.3 {}
T {g2} 1280 -324 0 0 0.3 0.3 {}
T {TP2} 1045 -420 0 0 0.3 0.3 {}
T {5/0.28} 1045 -384 0 0 0.3 0.3 {}
T {TN2} 1265 -420 0 0 0.3 0.3 {}
T {2/0.28} 1265 -384 0 0 0.3 0.3 {}
T {g3} 1660 -324 0 0 0.3 0.3 {}
T {TP3} 1425 -420 0 0 0.3 0.3 {}
T {5/0.28} 1425 -384 0 0 0.3 0.3 {}
T {TN3} 1645 -420 0 0 0.3 0.3 {}
T {2/0.28} 1645 -384 0 0 0.3 0.3 {}
T {g4} 2040 -324 0 0 0.3 0.3 {}
T {TP4} 1805 -420 0 0 0.3 0.3 {}
T {5/0.28} 1805 -384 0 0 0.3 0.3 {}
T {TN4} 2025 -420 0 0 0.3 0.3 {}
T {2/0.28} 2025 -384 0 0 0.3 0.3 {}
T {cfed_dac: ring current DAC, vg -> VSS} -300 -1100 0 0 0.7 0.7 {}
T {I(vg) = (k + code) units at vbnf + the fine leg at vctrl; unit nfet 1.2/5.33 um, fine leg 1.2/21.3 um} -300 -1040 0 0 0.42 0.42 {}
T {switch cell per bit b: the transmission gate TN + TP connects g_b to vbnf when bit[b] = 1; TD pulls g_b to VSS when bit[b] = 0} -300 -1006 0 0 0.42 0.42 {}
N 0 -30 0 -80 {}
N 0 30 0 80 {}
N 0 0 20 0 {}
N 20 0 20 80 {}
N 260 -30 260 -80 {}
N 260 30 260 80 {}
N 260 0 280 0 {}
N 280 0 280 80 {}
N 640 -30 640 -80 {}
N 640 30 640 80 {}
N 640 0 660 0 {}
N 660 0 660 80 {}
N 1020 -30 1020 -80 {}
N 1020 30 1020 80 {}
N 1020 0 1040 0 {}
N 1040 0 1040 80 {}
N 1400 -30 1400 -80 {}
N 1400 30 1400 80 {}
N 1400 0 1420 0 {}
N 1420 0 1420 80 {}
N 1780 -30 1780 -80 {}
N 1780 30 1780 80 {}
N 1780 0 1800 0 {}
N 1800 0 1800 80 {}
N 2160 -30 2160 -80 {}
N 2160 30 2160 80 {}
N 2160 0 2180 0 {}
N 2180 0 2180 80 {}
N 0 -80 260 -80 {}
N 260 -80 640 -80 {}
N 640 -80 1020 -80 {}
N 1020 -80 1400 -80 {}
N 1400 -80 1780 -80 {}
N 1780 -80 2160 -80 {}
N 2160 -80 2360 -80 {}
N -300 80 0 80 {}
N 0 80 20 80 {}
N 20 80 260 80 {}
N 260 80 280 80 {}
N 280 80 640 80 {}
N 640 80 660 80 {}
N 660 80 1020 80 {}
N 1020 80 1040 80 {}
N 1040 80 1400 80 {}
N 1400 80 1420 80 {}
N 1420 80 1780 80 {}
N 1780 80 1800 80 {}
N 1800 80 2160 80 {}
N 2160 80 2180 80 {}
N -300 0 -40 0 {}
N 220 -500 220 0 {}
N 380 -390 400 -390 {}
N 460 -390 440 -390 {}
N 420 -230 440 -230 {}
N 440 -230 440 -200 {}
N 440 -200 420 -200 {}
N 380 -420 380 -440 {}
N 380 -440 420 -440 {}
N 460 -420 460 -440 {}
N 460 -440 420 -440 {}
N 420 -500 420 -440 {}
N 380 -360 380 -340 {}
N 380 -340 420 -340 {}
N 460 -360 460 -340 {}
N 460 -340 420 -340 {}
N 420 -340 420 -300 {}
N 420 -300 420 -260 {}
N 420 -300 600 -300 {}
N 600 -300 600 0 {}
N -300 -560 280 -560 {}
N 280 -560 280 -390 {}
N 280 -390 340 -390 {}
N 280 -390 280 -230 {}
N 280 -230 380 -230 {}
N -300 -600 560 -600 {}
N 560 -600 560 -390 {}
N 560 -390 500 -390 {}
N 760 -390 780 -390 {}
N 840 -390 820 -390 {}
N 800 -230 820 -230 {}
N 820 -230 820 -200 {}
N 820 -200 800 -200 {}
N 760 -420 760 -440 {}
N 760 -440 800 -440 {}
N 840 -420 840 -440 {}
N 840 -440 800 -440 {}
N 800 -500 800 -440 {}
N 760 -360 760 -340 {}
N 760 -340 800 -340 {}
N 840 -360 840 -340 {}
N 840 -340 800 -340 {}
N 800 -340 800 -300 {}
N 800 -300 800 -260 {}
N 800 -300 980 -300 {}
N 980 -300 980 0 {}
N -300 -640 660 -640 {}
N 660 -640 660 -390 {}
N 660 -390 720 -390 {}
N 660 -390 660 -230 {}
N 660 -230 760 -230 {}
N -300 -680 940 -680 {}
N 940 -680 940 -390 {}
N 940 -390 880 -390 {}
N 1140 -390 1160 -390 {}
N 1220 -390 1200 -390 {}
N 1180 -230 1200 -230 {}
N 1200 -230 1200 -200 {}
N 1200 -200 1180 -200 {}
N 1140 -420 1140 -440 {}
N 1140 -440 1180 -440 {}
N 1220 -420 1220 -440 {}
N 1220 -440 1180 -440 {}
N 1180 -500 1180 -440 {}
N 1140 -360 1140 -340 {}
N 1140 -340 1180 -340 {}
N 1220 -360 1220 -340 {}
N 1220 -340 1180 -340 {}
N 1180 -340 1180 -300 {}
N 1180 -300 1180 -260 {}
N 1180 -300 1360 -300 {}
N 1360 -300 1360 0 {}
N -300 -720 1040 -720 {}
N 1040 -720 1040 -390 {}
N 1040 -390 1100 -390 {}
N 1040 -390 1040 -230 {}
N 1040 -230 1140 -230 {}
N -300 -760 1320 -760 {}
N 1320 -760 1320 -390 {}
N 1320 -390 1260 -390 {}
N 1520 -390 1540 -390 {}
N 1600 -390 1580 -390 {}
N 1560 -230 1580 -230 {}
N 1580 -230 1580 -200 {}
N 1580 -200 1560 -200 {}
N 1520 -420 1520 -440 {}
N 1520 -440 1560 -440 {}
N 1600 -420 1600 -440 {}
N 1600 -440 1560 -440 {}
N 1560 -500 1560 -440 {}
N 1520 -360 1520 -340 {}
N 1520 -340 1560 -340 {}
N 1600 -360 1600 -340 {}
N 1600 -340 1560 -340 {}
N 1560 -340 1560 -300 {}
N 1560 -300 1560 -260 {}
N 1560 -300 1740 -300 {}
N 1740 -300 1740 0 {}
N -300 -800 1420 -800 {}
N 1420 -800 1420 -390 {}
N 1420 -390 1480 -390 {}
N 1420 -390 1420 -230 {}
N 1420 -230 1520 -230 {}
N -300 -840 1700 -840 {}
N 1700 -840 1700 -390 {}
N 1700 -390 1640 -390 {}
N 1900 -390 1920 -390 {}
N 1980 -390 1960 -390 {}
N 1940 -230 1960 -230 {}
N 1960 -230 1960 -200 {}
N 1960 -200 1940 -200 {}
N 1900 -420 1900 -440 {}
N 1900 -440 1940 -440 {}
N 1980 -420 1980 -440 {}
N 1980 -440 1940 -440 {}
N 1940 -500 1940 -440 {}
N 1900 -360 1900 -340 {}
N 1900 -340 1940 -340 {}
N 1980 -360 1980 -340 {}
N 1980 -340 1940 -340 {}
N 1940 -340 1940 -300 {}
N 1940 -300 1940 -260 {}
N 1940 -300 2120 -300 {}
N 2120 -300 2120 0 {}
N -300 -880 1800 -880 {}
N 1800 -880 1800 -390 {}
N 1800 -390 1860 -390 {}
N 1800 -390 1800 -230 {}
N 1800 -230 1900 -230 {}
N -300 -920 2080 -920 {}
N 2080 -920 2080 -390 {}
N 2080 -390 2020 -390 {}
N -300 -500 220 -500 {}
N 220 -500 420 -500 {}
N 420 -500 800 -500 {}
N 800 -500 1180 -500 {}
N 1180 -500 1560 -500 {}
N 1560 -500 1940 -500 {}
N -300 180 -240 180 {}
C {devices/iopin.sym} 2360 -80 0 0 {name=p1
lab=vg}
C {devices/ipin.sym} -300 -500 0 0 {name=p14
lab=vbnf}
C {devices/ipin.sym} -300 0 0 0 {name=p3
lab=vctrl}
C {devices/ipin.sym} -300 -600 0 0 {name=p5
lab=bit0}
C {devices/ipin.sym} -300 -680 0 0 {name=p7
lab=bit1}
C {devices/ipin.sym} -300 -760 0 0 {name=p9
lab=bit2}
C {devices/ipin.sym} -300 -840 0 0 {name=p11
lab=bit3}
C {devices/ipin.sym} -300 -920 0 0 {name=p13
lab=bit4}
C {devices/ipin.sym} -300 -560 0 0 {name=p4
lab=bitb0}
C {devices/ipin.sym} -300 -640 0 0 {name=p6
lab=bitb1}
C {devices/ipin.sym} -300 -720 0 0 {name=p8
lab=bitb2}
C {devices/ipin.sym} -300 -800 0 0 {name=p10
lab=bitb3}
C {devices/ipin.sym} -300 -880 0 0 {name=p12
lab=bitb4}
C {devices/iopin.sym} -300 180 0 1 {name=p15
lab=VDD}
C {devices/iopin.sym} -300 80 0 1 {name=p2
lab=VSS}
C {symbols/nfet_03v3.sym} -20 0 0 0 {name=FFC
L=21.333333333333332u
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
model=nfet_03v3
spiceprefix=X
val="1.2/21.3"}
C {symbols/nfet_03v3.sym} 240 0 0 0 {name=FC
L=5.333333333333333u
W=1.2u
nf=1
m=6
ad=0.6p
as=0.6p
pd=3.4u
ps=3.4u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="1.2/5.33 ×6"}
C {symbols/nfet_03v3.sym} 620 0 0 0 {name=FC_0
L=5.333333333333333u
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
model=nfet_03v3
spiceprefix=X
val="1.2/5.33"}
C {symbols/nfet_03v3.sym} 1000 0 0 0 {name=FC_1
L=5.333333333333333u
W=1.2u
nf=1
m=2
ad=0.6p
as=0.6p
pd=3.4u
ps=3.4u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="1.2/5.33 ×2"}
C {symbols/nfet_03v3.sym} 1380 0 0 0 {name=FC_2
L=5.333333333333333u
W=1.2u
nf=1
m=4
ad=0.6p
as=0.6p
pd=3.4u
ps=3.4u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="1.2/5.33 ×4"}
C {symbols/nfet_03v3.sym} 1760 0 0 0 {name=FC_3
L=5.333333333333333u
W=1.2u
nf=1
m=8
ad=0.6p
as=0.6p
pd=3.4u
ps=3.4u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="1.2/5.33 ×8"}
C {symbols/nfet_03v3.sym} 2140 0 0 0 {name=FC_4
L=5.333333333333333u
W=1.2u
nf=1
m=16
ad=0.6p
as=0.6p
pd=3.4u
ps=3.4u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="1.2/5.33 ×16"}
C {symbols/pfet_03v3.sym} 360 -390 0 0 {name=TP0
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
val="5/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 480 -390 2 0 {name=TN0
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
val="2/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 400 -230 0 0 {name=TD0
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
C {symbols/vdd.sym} 400 -390 0 0 {name=l1
lab=VDD}
C {symbols/gnd.sym} 440 -390 0 0 {name=l2
lab=VSS}
C {symbols/gnd.sym} 420 -200 0 0 {name=l3
lab=VSS}
C {symbols/pfet_03v3.sym} 740 -390 0 0 {name=TP1
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
val="5/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 860 -390 2 0 {name=TN1
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
val="2/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 780 -230 0 0 {name=TD1
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
C {symbols/vdd.sym} 780 -390 0 0 {name=l4
lab=VDD}
C {symbols/gnd.sym} 820 -390 0 0 {name=l5
lab=VSS}
C {symbols/gnd.sym} 800 -200 0 0 {name=l6
lab=VSS}
C {symbols/pfet_03v3.sym} 1120 -390 0 0 {name=TP2
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
val="5/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 1240 -390 2 0 {name=TN2
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
val="2/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 1160 -230 0 0 {name=TD2
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
C {symbols/vdd.sym} 1160 -390 0 0 {name=l7
lab=VDD}
C {symbols/gnd.sym} 1200 -390 0 0 {name=l8
lab=VSS}
C {symbols/gnd.sym} 1180 -200 0 0 {name=l9
lab=VSS}
C {symbols/pfet_03v3.sym} 1500 -390 0 0 {name=TP3
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
val="5/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 1620 -390 2 0 {name=TN3
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
val="2/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 1540 -230 0 0 {name=TD3
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
C {symbols/vdd.sym} 1540 -390 0 0 {name=l10
lab=VDD}
C {symbols/gnd.sym} 1580 -390 0 0 {name=l11
lab=VSS}
C {symbols/gnd.sym} 1560 -200 0 0 {name=l12
lab=VSS}
C {symbols/pfet_03v3.sym} 1880 -390 0 0 {name=TP4
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
val="5/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 2000 -390 2 0 {name=TN4
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
val="2/0.28"
hide_texts=true}
C {symbols/nfet_03v3.sym} 1920 -230 0 0 {name=TD4
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
C {symbols/vdd.sym} 1920 -390 0 0 {name=l13
lab=VDD}
C {symbols/gnd.sym} 1960 -390 0 0 {name=l14
lab=VSS}
C {symbols/gnd.sym} 1940 -200 0 0 {name=l15
lab=VSS}
C {symbols/vdd.sym} -240 180 0 0 {name=l16
lab=VDD}
