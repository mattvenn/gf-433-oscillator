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
T {g0} 460 -244 0 0 0.3 0.3 {}
T {TN0  2/0.28} 408 -472 0 0 0.3 0.3 {}
T {TP0  5/0.28} 408 -278 0 0 0.3 0.3 {}
T {g1} 780 -244 0 0 0.3 0.3 {}
T {TN1  2/0.28} 728 -472 0 0 0.3 0.3 {}
T {TP1  5/0.28} 728 -278 0 0 0.3 0.3 {}
T {g2} 1100 -244 0 0 0.3 0.3 {}
T {TN2  2/0.28} 1048 -472 0 0 0.3 0.3 {}
T {TP2  5/0.28} 1048 -278 0 0 0.3 0.3 {}
T {g3} 1420 -244 0 0 0.3 0.3 {}
T {TN3  2/0.28} 1368 -472 0 0 0.3 0.3 {}
T {TP3  5/0.28} 1368 -278 0 0 0.3 0.3 {}
T {g4} 1740 -244 0 0 0.3 0.3 {}
T {TN4  2/0.28} 1688 -472 0 0 0.3 0.3 {}
T {TP4  5/0.28} 1688 -278 0 0 0.3 0.3 {}
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
N 220 -500 220 0 {}
N 400 -420 400 -400 {}
N 400 -300 400 -320 {}
N 430 -170 450 -170 {}
N 450 -170 450 -140 {}
N 450 -140 430 -140 {}
N 370 -500 370 -420 {}
N 370 -420 370 -300 {}
N 430 -420 430 -300 {}
N 430 -300 430 -220 {}
N 430 -220 430 -200 {}
N 430 -220 540 -220 {}
N 540 -220 540 0 {}
N -300 -600 400 -600 {}
N 400 -600 400 -460 {}
N -300 -560 340 -560 {}
N 340 -560 340 -240 {}
N 340 -240 400 -240 {}
N 400 -240 400 -260 {}
N 340 -240 340 -170 {}
N 340 -170 390 -170 {}
N 720 -420 720 -400 {}
N 720 -300 720 -320 {}
N 750 -170 770 -170 {}
N 770 -170 770 -140 {}
N 770 -140 750 -140 {}
N 690 -500 690 -420 {}
N 690 -420 690 -300 {}
N 750 -420 750 -300 {}
N 750 -300 750 -220 {}
N 750 -220 750 -200 {}
N 750 -220 860 -220 {}
N 860 -220 860 0 {}
N -300 -680 720 -680 {}
N 720 -680 720 -460 {}
N -300 -640 660 -640 {}
N 660 -640 660 -240 {}
N 660 -240 720 -240 {}
N 720 -240 720 -260 {}
N 660 -240 660 -170 {}
N 660 -170 710 -170 {}
N 1040 -420 1040 -400 {}
N 1040 -300 1040 -320 {}
N 1070 -170 1090 -170 {}
N 1090 -170 1090 -140 {}
N 1090 -140 1070 -140 {}
N 1010 -500 1010 -420 {}
N 1010 -420 1010 -300 {}
N 1070 -420 1070 -300 {}
N 1070 -300 1070 -220 {}
N 1070 -220 1070 -200 {}
N 1070 -220 1180 -220 {}
N 1180 -220 1180 0 {}
N -300 -760 1040 -760 {}
N 1040 -760 1040 -460 {}
N -300 -720 980 -720 {}
N 980 -720 980 -240 {}
N 980 -240 1040 -240 {}
N 1040 -240 1040 -260 {}
N 980 -240 980 -170 {}
N 980 -170 1030 -170 {}
N 1360 -420 1360 -400 {}
N 1360 -300 1360 -320 {}
N 1390 -170 1410 -170 {}
N 1410 -170 1410 -140 {}
N 1410 -140 1390 -140 {}
N 1330 -500 1330 -420 {}
N 1330 -420 1330 -300 {}
N 1390 -420 1390 -300 {}
N 1390 -300 1390 -220 {}
N 1390 -220 1390 -200 {}
N 1390 -220 1500 -220 {}
N 1500 -220 1500 0 {}
N -300 -840 1360 -840 {}
N 1360 -840 1360 -460 {}
N -300 -800 1300 -800 {}
N 1300 -800 1300 -240 {}
N 1300 -240 1360 -240 {}
N 1360 -240 1360 -260 {}
N 1300 -240 1300 -170 {}
N 1300 -170 1350 -170 {}
N 1680 -420 1680 -400 {}
N 1680 -300 1680 -320 {}
N 1710 -170 1730 -170 {}
N 1730 -170 1730 -140 {}
N 1730 -140 1710 -140 {}
N 1650 -500 1650 -420 {}
N 1650 -420 1650 -300 {}
N 1710 -420 1710 -300 {}
N 1710 -300 1710 -220 {}
N 1710 -220 1710 -200 {}
N 1710 -220 1820 -220 {}
N 1820 -220 1820 0 {}
N -300 -920 1680 -920 {}
N 1680 -920 1680 -460 {}
N -300 -880 1620 -880 {}
N 1620 -880 1620 -240 {}
N 1620 -240 1680 -240 {}
N 1680 -240 1680 -260 {}
N 1620 -240 1620 -170 {}
N 1620 -170 1670 -170 {}
N -300 -500 220 -500 {}
N 220 -500 370 -500 {}
N 370 -500 690 -500 {}
N 690 -500 1010 -500 {}
N 1010 -500 1330 -500 {}
N 1330 -500 1650 -500 {}
N -300 180 -240 180 {}
C {devices/iopin.sym} 2060 -80 0 0 {name=p1
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
C {symbols/nfet_03v3.sym} 400 -440 1 0 {name=TN0
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
C {symbols/pfet_03v3.sym} 400 -280 3 0 {name=TP0
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
C {symbols/nfet_03v3.sym} 410 -170 0 0 {name=TD0
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
C {symbols/gnd.sym} 400 -400 0 0 {name=l1
lab=VSS}
C {symbols/vdd.sym} 400 -320 0 0 {name=l2
lab=VDD}
C {symbols/gnd.sym} 430 -140 0 0 {name=l3
lab=VSS}
C {symbols/nfet_03v3.sym} 720 -440 1 0 {name=TN1
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
C {symbols/pfet_03v3.sym} 720 -280 3 0 {name=TP1
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
C {symbols/nfet_03v3.sym} 730 -170 0 0 {name=TD1
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
C {symbols/gnd.sym} 720 -400 0 0 {name=l4
lab=VSS}
C {symbols/vdd.sym} 720 -320 0 0 {name=l5
lab=VDD}
C {symbols/gnd.sym} 750 -140 0 0 {name=l6
lab=VSS}
C {symbols/nfet_03v3.sym} 1040 -440 1 0 {name=TN2
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
C {symbols/pfet_03v3.sym} 1040 -280 3 0 {name=TP2
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
C {symbols/nfet_03v3.sym} 1050 -170 0 0 {name=TD2
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
C {symbols/gnd.sym} 1040 -400 0 0 {name=l7
lab=VSS}
C {symbols/vdd.sym} 1040 -320 0 0 {name=l8
lab=VDD}
C {symbols/gnd.sym} 1070 -140 0 0 {name=l9
lab=VSS}
C {symbols/nfet_03v3.sym} 1360 -440 1 0 {name=TN3
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
C {symbols/pfet_03v3.sym} 1360 -280 3 0 {name=TP3
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
C {symbols/nfet_03v3.sym} 1370 -170 0 0 {name=TD3
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
C {symbols/gnd.sym} 1360 -400 0 0 {name=l10
lab=VSS}
C {symbols/vdd.sym} 1360 -320 0 0 {name=l11
lab=VDD}
C {symbols/gnd.sym} 1390 -140 0 0 {name=l12
lab=VSS}
C {symbols/nfet_03v3.sym} 1680 -440 1 0 {name=TN4
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
C {symbols/pfet_03v3.sym} 1680 -280 3 0 {name=TP4
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
C {symbols/nfet_03v3.sym} 1690 -170 0 0 {name=TD4
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
C {symbols/gnd.sym} 1680 -400 0 0 {name=l13
lab=VSS}
C {symbols/vdd.sym} 1680 -320 0 0 {name=l14
lab=VDD}
C {symbols/gnd.sym} 1710 -140 0 0 {name=l15
lab=VSS}
C {symbols/vdd.sym} -240 180 0 0 {name=l16
lab=VDD}
