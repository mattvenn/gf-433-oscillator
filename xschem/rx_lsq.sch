v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {tt (open)} 820 396 0 0 0.3 0.3 {}
T {vq} 40 -224 0 0 0.3 0.3 {}
T {q1 (open)} 920 76 0 0 0.3 0.3 {}
T {rx_lsq: the Q tap level shifter (a copy of lsdiv's, with the same load)} -700 -760 0 0 0.7 0.7 {}
T {ls_ac (the 2 fF metal-finger Cc level shifter) drives a dummy tspc_t1 and a dummy TX tap inverter TT, as lsdiv's ls does: its delay (about 120 deg at 434 MHz) then matches the I tap's} -700 -700 0 0 0.42 0.42 {}
T {header Hq (qenb low = on) feeds vq; Dq holds lsq low when off; the layout must copy lsdiv's LS cell; source: sim/rx/rx_lo.py lsq()} -700 -666 0 0 0.42 0.42 {}
N 20 -300 40 -300 {}
N -240 -90 -220 -90 {}
N -240 -60 -220 -60 {}
N -220 -90 -220 -60 {}
N -220 -60 -220 -30 {}
N -240 -30 -220 -30 {}
N 760 345 760 420 {}
N 760 420 760 495 {}
N 800 375 800 420 {}
N 800 420 800 465 {}
N 800 345 820 345 {}
N 820 345 820 315 {}
N 820 315 800 315 {}
N 800 495 820 495 {}
N -280 -60 -320 -60 {}
N -320 -60 -320 -200 {}
N 20 -270 20 -200 {}
N 800 315 800 295 {}
N 800 295 1100 295 {}
N 1100 295 1100 -200 {}
N 250 50 250 -200 {}
N 750 50 750 -200 {}
N -320 -200 20 -200 {}
N 20 -200 250 -200 {}
N 250 -200 750 -200 {}
N 750 -200 1100 -200 {}
N -700 100 200 100 {}
N 400 100 620 100 {}
N 700 100 660 100 {}
N 1220 640 1240 640 {}
N 620 100 620 260 {}
N 660 100 660 260 {}
N 760 420 720 420 {}
N 720 420 720 260 {}
N 1220 610 1220 260 {}
N 620 260 660 260 {}
N 660 260 720 260 {}
N 720 260 1220 260 {}
N 1220 260 1500 260 {}
N -20 -300 -40 -300 {}
N -40 -300 -40 -400 {}
N 1180 640 1140 640 {}
N 1140 640 1140 760 {}
N 1140 760 -560 760 {}
N -560 760 -560 -400 {}
N -700 -400 -560 -400 {}
N -560 -400 -40 -400 {}
N -700 880 -640 880 {}
N -700 940 -640 940 {}
C {devices/iopin.sym} -700 880 0 1 {name=p4
lab=VDD}
C {devices/iopin.sym} -700 940 0 1 {name=p5
lab=VSS}
C {devices/ipin.sym} -700 100 0 0 {name=p1
lab=aq}
C {devices/ipin.sym} -700 -400 0 0 {name=p3
lab=qenb}
C {devices/opin.sym} 1500 260 0 0 {name=p2
lab=lsq}
C {symbols/pfet_03v3.sym} 0 -300 0 0 {name=Hq
L=0.28u
W=10.0u
nf=1
m=2
ad=5.0p
as=5.0p
pd=21.0u
ps=21.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="10/0.28 ×2"}
C {symbols/vdd.sym} 40 -300 0 0 {name=l1
lab=VDD}
C {symbols/vdd.sym} 20 -330 0 0 {name=l2
lab=VDD}
C {symbols/nfet_03v3.sym} -260 -60 0 0 {name=Cq
L=10.0u
W=24.57u
nf=1
m=1
ad=12.285p
as=12.285p
pd=50.14u
ps=50.14u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="24.6/10"}
C {symbols/gnd.sym} -220 -30 0 0 {name=l3
lab=VSS}
C {ls_ac.sym} 300 100 0 0 {name=xls}
C {tspc_t1.sym} 800 100 0 0 {name=xd1}
C {symbols/pfet_03v3.sym} 780 345 0 0 {name=TTp
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
C {symbols/nfet_03v3.sym} 780 495 0 0 {name=TTn
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
C {symbols/gnd.sym} 820 495 0 0 {name=l4
lab=VSS}
C {symbols/gnd.sym} 800 525 0 0 {name=l5
lab=VSS}
C {symbols/gnd.sym} 250 150 0 0 {name=l6
lab=VSS}
C {symbols/gnd.sym} 750 150 0 0 {name=l7
lab=VSS}
C {symbols/nfet_03v3.sym} 1200 640 0 0 {name=Dq
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
C {symbols/gnd.sym} 1240 640 0 0 {name=l8
lab=VSS}
C {symbols/gnd.sym} 1220 670 0 0 {name=l9
lab=VSS}
C {symbols/vdd.sym} -640 880 0 0 {name=l10
lab=VDD}
C {symbols/gnd.sym} -640 940 0 0 {name=l11
lab=VSS}
