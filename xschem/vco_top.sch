v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {vbnf} 392 320 0 0 0.3 0.3 {}
T {VDD_LS decap ~10 pF} 1300 -360 0 0 0.35 0.35 {}
T {vco_top: 433.92 MHz current-fed ring VCO, GF180MCU (top level)} -100 -800 0 0 0.7 0.7 {}
T {cgm_ref -> vbnf -> ring_core_v3 -> a0 -> lsdiv -> ck = f / 4; lsdiv on its own supply VDD_LS} -100 -740 0 0 0.42 0.42 {}
T {the LVS source of layout/vco_top.gds (layout/gen/check_top.sh)} -100 -706 0 0 0.42 0.42 {}
N -100 -220 480 -220 {}
N -100 -180 480 -180 {}
N -100 -140 480 -140 {}
N -100 -100 480 -100 {}
N -100 -60 480 -60 {}
N -100 -20 480 -20 {}
N -100 20 480 20 {}
N -100 60 480 60 {}
N -100 100 480 100 {}
N -100 140 480 140 {}
N -100 180 480 180 {}
N 300 400 380 400 {}
N 380 220 380 300 {}
N 380 300 380 400 {}
N 380 220 480 220 {}
N 380 300 -100 300 {}
N 300 440 340 440 {}
N 340 440 340 560 {}
N 340 560 1400 560 {}
N 720 -220 800 -220 {}
N 800 -220 860 -220 {}
N 800 -220 800 -520 {}
N 800 -520 1400 -520 {}
N 720 -140 780 -140 {}
N 780 -140 780 620 {}
N 780 620 1400 620 {}
N 1060 -220 1400 -220 {}
N 1060 -180 1400 -180 {}
N 720 -20 1400 -20 {}
N 910 -270 910 -340 {}
N 910 -340 1200 -340 {}
N 1200 -340 1200 -300 {}
N 1200 -300 1240 -300 {}
N 1280 -330 1300 -330 {}
N 1280 -300 1300 -300 {}
N 1300 -330 1300 -300 {}
N 1300 -300 1300 -270 {}
N 1280 -270 1300 -270 {}
N -100 660 -40 660 {}
N -100 720 -40 720 {}
N -100 780 -40 780 {}
C {devices/iopin.sym} -100 660 0 1 {name=p19
lab=VDD}
C {devices/iopin.sym} -100 720 0 1 {name=p20
lab=VDD_LS}
C {devices/iopin.sym} -100 780 0 1 {name=p21
lab=VSS}
C {devices/ipin.sym} -100 180 0 0 {name=p11
lab=vctrl}
C {devices/ipin.sym} -100 100 0 0 {name=p9
lab=bit0}
C {devices/ipin.sym} -100 20 0 0 {name=p7
lab=bit1}
C {devices/ipin.sym} -100 -60 0 0 {name=p5
lab=bit2}
C {devices/ipin.sym} -100 -140 0 0 {name=p3
lab=bit3}
C {devices/ipin.sym} -100 -220 0 0 {name=p1
lab=bit4}
C {devices/ipin.sym} -100 140 0 0 {name=p10
lab=bitb0}
C {devices/ipin.sym} -100 60 0 0 {name=p8
lab=bitb1}
C {devices/ipin.sym} -100 -20 0 0 {name=p6
lab=bitb2}
C {devices/ipin.sym} -100 -100 0 0 {name=p4
lab=bitb3}
C {devices/ipin.sym} -100 -180 0 0 {name=p2
lab=bitb4}
C {devices/opin.sym} 1400 -220 0 0 {name=p16
lab=ck}
C {devices/opin.sym} 1400 -520 0 0 {name=p14
lab=a0}
C {devices/opin.sym} 1400 560 0 0 {name=p13
lab=vbn}
C {devices/iopin.sym} 1400 -20 0 0 {name=p18
lab=vg}
C {devices/opin.sym} 1400 -180 0 0 {name=p17
lab=ls}
C {devices/opin.sym} -100 300 0 0 {name=p12
lab=vbnf}
C {devices/opin.sym} 1400 620 0 0 {name=p15
lab=a2}
C {ring_core_v3.sym} 600 0 0 0 {name=xcore}
C {cgm_ref.sym} 200 420 0 0 {name=xref}
C {lsdiv.sym} 960 -200 0 0 {name=xls}
C {symbols/nfet_03v3.sym} 1260 -300 0 0 {name=DCLS
L=10.0u
W=49.14u
nf=1
m=5
ad=0
as=0
pd=0
ps=0
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="49.14/10 ×5"}
C {symbols/vdd.sym} 910 -340 0 0 {name=l1
lab=VDD_LS}
C {symbols/gnd.sym} 1300 -270 0 0 {name=l2
lab=VSS}
C {symbols/vdd.sym} 530 -270 0 0 {name=l3
lab=VDD}
C {symbols/gnd.sym} 530 270 0 0 {name=l4
lab=VSS}
C {symbols/vdd.sym} 150 350 0 0 {name=l5
lab=VDD}
C {symbols/gnd.sym} 150 490 0 0 {name=l6
lab=VSS}
C {symbols/gnd.sym} 910 -130 0 0 {name=l7
lab=VSS}
C {symbols/vdd.sym} -40 660 0 0 {name=l8
lab=VDD}
C {symbols/vdd.sym} -40 720 0 0 {name=l9
lab=VDD_LS}
C {symbols/gnd.sym} -40 780 0 0 {name=l10
lab=VSS}
