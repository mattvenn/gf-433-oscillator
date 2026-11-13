v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {qenb = VSS: Q tap copy always on} -420 -730 0 0 0.25 0.25 {}
T {DC supply decap ~4.9 pF} 2900 1000 0 0 0.3 0.3 {}
T {rx_top: 433.92 MHz zero-IF receiver (option B)} -900 -1300 0 0 0.7 0.7 {}
T {ua pins -> two-stage LNA -> I / Q passive mixers (LO: ls and the a2 tap, 72 deg apart) -> baseband (LPF ~145 kHz, HPF ~9 kHz) -> limiter + comparator -> q_i / q_q (uo[4] / uo[5])} -900 -1240 0 0 0.42 0.42 {}
T {about 7 mA at tt; the RP2350 PIO decodes q_i / q_q as a quadrature counter; source: sim/rx/rx_top.py} -900 -1206 0 0 0.42 0.42 {}
N -900 -60 -120 -60 {}
N -900 -20 -120 -20 {}
N -900 -860 -120 -860 {}
N -900 -820 -120 -820 {}
N -120 -740 -160 -740 {}
N 120 -60 500 -60 {}
N 500 -60 500 -360 {}
N 500 -360 900 -360 {}
N 120 -20 540 -20 {}
N 540 -20 540 -320 {}
N 540 -320 900 -320 {}
N 120 20 580 20 {}
N 580 20 580 340 {}
N 580 340 900 340 {}
N 120 60 620 60 {}
N 620 60 620 380 {}
N 620 380 900 380 {}
N 120 -860 660 -860 {}
N 660 -860 660 -280 {}
N 660 -280 900 -280 {}
N 120 -820 700 -820 {}
N 700 -820 700 -240 {}
N 700 -240 900 -240 {}
N 120 -780 740 -780 {}
N 740 -780 740 420 {}
N 740 420 900 420 {}
N 120 -740 780 -740 {}
N 780 -740 780 460 {}
N 780 460 900 460 {}
N 1100 -360 1260 -360 {}
N 1260 -360 1590 -360 {}
N 1100 -320 1300 -320 {}
N 1300 -320 1590 -320 {}
N 1810 -360 2060 -360 {}
N 2060 -360 2400 -360 {}
N 1810 -320 2100 -320 {}
N 2100 -320 2400 -320 {}
N 1100 340 1260 340 {}
N 1260 340 1590 340 {}
N 1100 380 1300 380 {}
N 1300 380 1590 380 {}
N 1810 340 2060 340 {}
N 2060 340 2400 340 {}
N 1810 380 2100 380 {}
N 2100 380 2400 380 {}
N 2600 -360 3500 -360 {}
N 2600 340 3500 340 {}
N -800 780 -800 -780 {}
N -800 -780 -120 -780 {}
N -900 780 -800 780 {}
N -800 780 -600 780 {}
N -120 20 -180 20 {}
N -180 20 -180 1100 {}
N -120 60 -220 60 {}
N -220 60 -220 1160 {}
N 1590 -280 1450 -280 {}
N 1450 -280 1450 1100 {}
N 1590 -240 1410 -240 {}
N 1410 -240 1410 1160 {}
N 1590 420 1530 420 {}
N 1530 420 1530 1100 {}
N 1590 460 1490 460 {}
N 1490 460 1490 1160 {}
N 2400 -280 2260 -280 {}
N 2260 -280 2260 1100 {}
N 2400 -240 2220 -240 {}
N 2220 -240 2220 1160 {}
N 2400 420 2340 420 {}
N 2340 420 2340 1100 {}
N 2400 460 2300 460 {}
N 2300 460 2300 1160 {}
N -400 780 -340 780 {}
N -340 780 -340 1100 {}
N -340 1100 -180 1100 {}
N -180 1100 1450 1100 {}
N 1450 1100 1530 1100 {}
N 1530 1100 2260 1100 {}
N 2260 1100 2340 1100 {}
N -400 820 -300 820 {}
N -300 820 -300 1160 {}
N -300 1160 -220 1160 {}
N -220 1160 1410 1160 {}
N 1410 1160 1490 1160 {}
N 1490 1160 2220 1160 {}
N 2220 1160 2300 1160 {}
N 3020 870 3040 870 {}
N 3020 900 3040 900 {}
N 3040 870 3040 900 {}
N 3040 900 3040 930 {}
N 3020 930 3040 930 {}
N 2980 900 2940 900 {}
N -900 1350 -840 1350 {}
N -900 1410 -840 1410 {}
C {devices/iopin.sym} -900 1350 0 1 {name=p8
lab=VDD}
C {devices/iopin.sym} -900 1410 0 1 {name=p9
lab=VSS}
C {devices/ipin.sym} -900 -60 0 0 {name=p1
lab=inp}
C {devices/ipin.sym} -900 -20 0 0 {name=p2
lab=inn}
C {devices/ipin.sym} -900 -860 0 0 {name=p3
lab=ls}
C {devices/ipin.sym} -900 -820 0 0 {name=p4
lab=aq}
C {devices/ipin.sym} -900 780 0 0 {name=p7
lab=en}
C {devices/opin.sym} 3500 -360 0 0 {name=p5
lab=q_i}
C {devices/opin.sym} 3500 340 0 0 {name=p6
lab=q_q}
C {rx_bias.sym} -500 800 0 0 {name=xb}
C {rx_lna.sym} 0 0 0 0 {name=xlna}
C {rx_lo.sym} 0 -800 0 0 {name=xlo}
C {rx_mix.sym} 1000 -300 0 0 {name=xmi}
C {rx_mix.sym} 1000 400 0 0 {name=xmq}
C {rx_bb.sym} 1700 -300 0 0 {name=xbbi}
C {rx_bb.sym} 1700 400 0 0 {name=xbbq}
C {rx_lim.sym} 2500 -300 0 0 {name=xli}
C {rx_lim.sym} 2500 400 0 0 {name=xlq}
C {symbols/vdd.sym} -550 730 0 0 {name=l1
lab=VDD}
C {symbols/gnd.sym} -550 870 0 0 {name=l2
lab=VSS}
C {symbols/vdd.sym} -70 -110 0 0 {name=l3
lab=VDD}
C {symbols/gnd.sym} -70 110 0 0 {name=l4
lab=VSS}
C {symbols/vdd.sym} -70 -910 0 0 {name=l5
lab=VDD}
C {symbols/gnd.sym} -70 -690 0 0 {name=l6
lab=VSS}
C {symbols/vdd.sym} 950 -410 0 0 {name=l7
lab=VDD}
C {symbols/gnd.sym} 950 -190 0 0 {name=l8
lab=VSS}
C {symbols/vdd.sym} 950 290 0 0 {name=l9
lab=VDD}
C {symbols/gnd.sym} 950 510 0 0 {name=l10
lab=VSS}
C {symbols/vdd.sym} 1640 -410 0 0 {name=l11
lab=VDD}
C {symbols/gnd.sym} 1640 -190 0 0 {name=l12
lab=VSS}
C {symbols/vdd.sym} 1640 290 0 0 {name=l13
lab=VDD}
C {symbols/gnd.sym} 1640 510 0 0 {name=l14
lab=VSS}
C {symbols/vdd.sym} 2450 -410 0 0 {name=l15
lab=VDD}
C {symbols/gnd.sym} 2450 -190 0 0 {name=l16
lab=VSS}
C {symbols/vdd.sym} 2450 290 0 0 {name=l17
lab=VDD}
C {symbols/gnd.sym} 2450 510 0 0 {name=l18
lab=VSS}
C {symbols/gnd.sym} -160 -740 0 0 {name=l19
lab=VSS}
C {symbols/nfet_03v3.sym} 3000 900 0 0 {name=DC
L=10.0u
W=10.0u
nf=1
m=12
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
val="10/10 ×12"}
C {symbols/gnd.sym} 3040 930 0 0 {name=l20
lab=VSS}
C {symbols/vdd.sym} 2940 900 0 0 {name=l21
lab=VDD}
C {symbols/vdd.sym} -840 1350 0 0 {name=l22
lab=VDD}
C {symbols/gnd.sym} -840 1410 0 0 {name=l23
lab=VSS}
