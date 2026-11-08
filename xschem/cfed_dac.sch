v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {fine (vctrl)} -50 100 0 0 0.35 0.35 {}
T {base, k = 6} 210 100 0 0 0.35 0.35 {}
T {bit 0} 530 100 0 0 0.35 0.35 {}
T {bit 1} 850 100 0 0 0.35 0.35 {}
T {bit 2} 1170 100 0 0 0.35 0.35 {}
T {bit 3} 1490 100 0 0 0.35 0.35 {}
T {bit 4} 1810 100 0 0 0.35 0.35 {}
T {g0} 390 -274 0 0 0.3 0.3 {}
T {g1} 710 -274 0 0 0.3 0.3 {}
T {g2} 1030 -274 0 0 0.3 0.3 {}
T {g3} 1350 -274 0 0 0.3 0.3 {}
T {g4} 1670 -274 0 0 0.3 0.3 {}
T {cfed_dac: ring current DAC, vg -> VSS} -300 -1000 0 0 0.7 0.7 {}
T {I(vg) = (k + code) units at vbnf + the fine leg at vctrl; unit nfet 1.2/5.33 um, fine leg 1.2/21.3 um} -300 -940 0 0 0.42 0.42 {}
T {switch cell per bit: TN/TP pass vbnf to g_b when bit_b = 1, TD pulls g_b to VSS when bit_b = 0} -300 -906 0 0 0.42 0.42 {}
N 0 -30 0 -80 {}
N 0 30 0 80 {}
N 0 0 20 0 {}
N 20 0 20 80 {}
N 260 -30 260 -80 {}
N 260 30 260 80 {}
N 260 0 280 0 {}
N 280 0 280 80 {}
N 580 -30 580 -80 {}
N 580 30 580 80 {}
N 580 0 600 0 {}
N 600 0 600 80 {}
N 900 -30 900 -80 {}
N 900 30 900 80 {}
N 900 0 920 0 {}
N 920 0 920 80 {}
N 1220 -30 1220 -80 {}
N 1220 30 1220 80 {}
N 1220 0 1240 0 {}
N 1240 0 1240 80 {}
N 1540 -30 1540 -80 {}
N 1540 30 1540 80 {}
N 1540 0 1560 0 {}
N 1560 0 1560 80 {}
N 1860 -30 1860 -80 {}
N 1860 30 1860 80 {}
N 1860 0 1880 0 {}
N 1880 0 1880 80 {}
N 0 -80 260 -80 {}
N 260 -80 580 -80 {}
N 580 -80 900 -80 {}
N 900 -80 1220 -80 {}
N 1220 -80 1540 -80 {}
N 1540 -80 1860 -80 {}
N 1860 -80 2060 -80 {}
N -300 80 0 80 {}
N 0 80 20 80 {}
N 20 80 260 80 {}
N 260 80 280 80 {}
N 280 80 580 80 {}
N 580 80 600 80 {}
N 600 80 900 80 {}
N 900 80 920 80 {}
N 920 80 1220 80 {}
N 1220 80 1240 80 {}
N 1240 80 1540 80 {}
N 1540 80 1560 80 {}
N 1560 80 1860 80 {}
N 1860 80 1880 80 {}
N -300 0 -40 0 {}
N 220 -420 220 0 {}
N 380 -330 400 -330 {}
N 540 -330 560 -330 {}
N 380 -200 400 -200 {}
N 400 -200 400 -170 {}
N 400 -170 380 -170 {}
N 380 -360 380 -420 {}
N 540 -360 540 -420 {}
N 380 -300 380 -270 {}
N 380 -230 380 -270 {}
N 380 -270 540 -270 {}
N 540 -300 540 -270 {}
N 540 -270 540 0 {}
N -300 -480 320 -480 {}
N 320 -480 320 -330 {}
N 320 -330 340 -330 {}
N 320 -330 320 -200 {}
N 320 -200 340 -200 {}
N -300 -520 480 -520 {}
N 480 -520 480 -330 {}
N 480 -330 500 -330 {}
N 700 -330 720 -330 {}
N 860 -330 880 -330 {}
N 700 -200 720 -200 {}
N 720 -200 720 -170 {}
N 720 -170 700 -170 {}
N 700 -360 700 -420 {}
N 860 -360 860 -420 {}
N 700 -300 700 -270 {}
N 700 -230 700 -270 {}
N 700 -270 860 -270 {}
N 860 -300 860 -270 {}
N 860 -270 860 0 {}
N -300 -560 640 -560 {}
N 640 -560 640 -330 {}
N 640 -330 660 -330 {}
N 640 -330 640 -200 {}
N 640 -200 660 -200 {}
N -300 -600 800 -600 {}
N 800 -600 800 -330 {}
N 800 -330 820 -330 {}
N 1020 -330 1040 -330 {}
N 1180 -330 1200 -330 {}
N 1020 -200 1040 -200 {}
N 1040 -200 1040 -170 {}
N 1040 -170 1020 -170 {}
N 1020 -360 1020 -420 {}
N 1180 -360 1180 -420 {}
N 1020 -300 1020 -270 {}
N 1020 -230 1020 -270 {}
N 1020 -270 1180 -270 {}
N 1180 -300 1180 -270 {}
N 1180 -270 1180 0 {}
N -300 -640 960 -640 {}
N 960 -640 960 -330 {}
N 960 -330 980 -330 {}
N 960 -330 960 -200 {}
N 960 -200 980 -200 {}
N -300 -680 1120 -680 {}
N 1120 -680 1120 -330 {}
N 1120 -330 1140 -330 {}
N 1340 -330 1360 -330 {}
N 1500 -330 1520 -330 {}
N 1340 -200 1360 -200 {}
N 1360 -200 1360 -170 {}
N 1360 -170 1340 -170 {}
N 1340 -360 1340 -420 {}
N 1500 -360 1500 -420 {}
N 1340 -300 1340 -270 {}
N 1340 -230 1340 -270 {}
N 1340 -270 1500 -270 {}
N 1500 -300 1500 -270 {}
N 1500 -270 1500 0 {}
N -300 -720 1280 -720 {}
N 1280 -720 1280 -330 {}
N 1280 -330 1300 -330 {}
N 1280 -330 1280 -200 {}
N 1280 -200 1300 -200 {}
N -300 -760 1440 -760 {}
N 1440 -760 1440 -330 {}
N 1440 -330 1460 -330 {}
N 1660 -330 1680 -330 {}
N 1820 -330 1840 -330 {}
N 1660 -200 1680 -200 {}
N 1680 -200 1680 -170 {}
N 1680 -170 1660 -170 {}
N 1660 -360 1660 -420 {}
N 1820 -360 1820 -420 {}
N 1660 -300 1660 -270 {}
N 1660 -230 1660 -270 {}
N 1660 -270 1820 -270 {}
N 1820 -300 1820 -270 {}
N 1820 -270 1820 0 {}
N -300 -800 1600 -800 {}
N 1600 -800 1600 -330 {}
N 1600 -330 1620 -330 {}
N 1600 -330 1600 -200 {}
N 1600 -200 1620 -200 {}
N -300 -840 1760 -840 {}
N 1760 -840 1760 -330 {}
N 1760 -330 1780 -330 {}
N -300 -420 220 -420 {}
N 220 -420 380 -420 {}
N 380 -420 540 -420 {}
N 540 -420 700 -420 {}
N 700 -420 860 -420 {}
N 860 -420 1020 -420 {}
N 1020 -420 1180 -420 {}
N 1180 -420 1340 -420 {}
N 1340 -420 1500 -420 {}
N 1500 -420 1660 -420 {}
N 1660 -420 1820 -420 {}
N -300 180 -240 180 {}
C {devices/iopin.sym} 2060 -80 0 0 {name=p1
lab=vg}
C {devices/ipin.sym} -300 -420 0 0 {name=p14
lab=vbnf}
C {devices/ipin.sym} -300 0 0 0 {name=p3
lab=vctrl}
C {devices/ipin.sym} -300 -520 0 0 {name=p5
lab=bit0}
C {devices/ipin.sym} -300 -600 0 0 {name=p7
lab=bit1}
C {devices/ipin.sym} -300 -680 0 0 {name=p9
lab=bit2}
C {devices/ipin.sym} -300 -760 0 0 {name=p11
lab=bit3}
C {devices/ipin.sym} -300 -840 0 0 {name=p13
lab=bit4}
C {devices/ipin.sym} -300 -480 0 0 {name=p4
lab=bitb0}
C {devices/ipin.sym} -300 -560 0 0 {name=p6
lab=bitb1}
C {devices/ipin.sym} -300 -640 0 0 {name=p8
lab=bitb2}
C {devices/ipin.sym} -300 -720 0 0 {name=p10
lab=bitb3}
C {devices/ipin.sym} -300 -800 0 0 {name=p12
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
C {symbols/nfet_03v3.sym} 560 0 0 0 {name=FC_0
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
C {symbols/nfet_03v3.sym} 880 0 0 0 {name=FC_1
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
C {symbols/nfet_03v3.sym} 1200 0 0 0 {name=FC_2
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
C {symbols/nfet_03v3.sym} 1520 0 0 0 {name=FC_3
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
C {symbols/nfet_03v3.sym} 1840 0 0 0 {name=FC_4
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
C {symbols/pfet_03v3.sym} 360 -330 0 0 {name=TP0
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
C {symbols/nfet_03v3.sym} 520 -330 2 1 {name=TN0
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
C {symbols/nfet_03v3.sym} 360 -200 0 0 {name=TD0
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
C {symbols/vdd.sym} 400 -330 0 0 {name=l1
lab=VDD}
C {symbols/gnd.sym} 560 -330 0 0 {name=l2
lab=VSS}
C {symbols/gnd.sym} 380 -170 0 0 {name=l3
lab=VSS}
C {symbols/pfet_03v3.sym} 680 -330 0 0 {name=TP1
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
C {symbols/nfet_03v3.sym} 840 -330 2 1 {name=TN1
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
C {symbols/nfet_03v3.sym} 680 -200 0 0 {name=TD1
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
C {symbols/vdd.sym} 720 -330 0 0 {name=l4
lab=VDD}
C {symbols/gnd.sym} 880 -330 0 0 {name=l5
lab=VSS}
C {symbols/gnd.sym} 700 -170 0 0 {name=l6
lab=VSS}
C {symbols/pfet_03v3.sym} 1000 -330 0 0 {name=TP2
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
C {symbols/nfet_03v3.sym} 1160 -330 2 1 {name=TN2
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
C {symbols/nfet_03v3.sym} 1000 -200 0 0 {name=TD2
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
C {symbols/vdd.sym} 1040 -330 0 0 {name=l7
lab=VDD}
C {symbols/gnd.sym} 1200 -330 0 0 {name=l8
lab=VSS}
C {symbols/gnd.sym} 1020 -170 0 0 {name=l9
lab=VSS}
C {symbols/pfet_03v3.sym} 1320 -330 0 0 {name=TP3
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
C {symbols/nfet_03v3.sym} 1480 -330 2 1 {name=TN3
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
C {symbols/nfet_03v3.sym} 1320 -200 0 0 {name=TD3
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
C {symbols/vdd.sym} 1360 -330 0 0 {name=l10
lab=VDD}
C {symbols/gnd.sym} 1520 -330 0 0 {name=l11
lab=VSS}
C {symbols/gnd.sym} 1340 -170 0 0 {name=l12
lab=VSS}
C {symbols/pfet_03v3.sym} 1640 -330 0 0 {name=TP4
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
C {symbols/nfet_03v3.sym} 1800 -330 2 1 {name=TN4
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
C {symbols/nfet_03v3.sym} 1640 -200 0 0 {name=TD4
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
C {symbols/vdd.sym} 1680 -330 0 0 {name=l13
lab=VDD}
C {symbols/gnd.sym} 1840 -330 0 0 {name=l14
lab=VSS}
C {symbols/gnd.sym} 1660 -170 0 0 {name=l15
lab=VSS}
C {symbols/vdd.sym} -240 180 0 0 {name=l16
lab=VDD}
