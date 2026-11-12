v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {vh} -160 -360 0 0 0.3 0.3 {}
T {n2} 260 -134 0 0 0.3 0.3 {}
T {nb} -200 -64 0 0 0.3 0.3 {}
T {x} 650 -90 0 0 0.3 0.3 {}
T {rx_bias: constant-gm reference for the receiver} -900 -940 0 0 0.7 0.7 {}
T {MN1 2/0.5, MN2 2/0.5 ×4 (K = 4), Rb 2/29.714 um ppolyf_u (5.2 kOhm): gm of the unit = 1 / Rb (x const), unit current ~25 uA} -900 -880 0 0 0.42 0.42 {}
T {every tail mirrors nb, so each stage gain gm x RL is a resistor ratio; en = 0: header off, nb and x held low; source: sim/rx/rx_bias.py block()} -900 -846 0 0 0.42 0.42 {}
N 20 -440 40 -440 {}
N -220 -200 -240 -200 {}
N 220 -200 240 -200 {}
N -220 60 -240 60 {}
N 220 60 240 60 {}
N 580 -200 600 -200 {}
N 580 60 600 60 {}
N 360 330 340 330 {}
N -460 560 -440 560 {}
N 740 200 720 200 {}
N 240 200 260 200 {}
N 220 90 220 170 {}
N 540 -200 500 -200 {}
N -220 -230 -220 -330 {}
N 220 -230 220 -330 {}
N 580 -230 580 -330 {}
N 20 -410 20 -330 {}
N -220 -330 20 -330 {}
N 20 -330 220 -330 {}
N 220 -330 580 -330 {}
N -180 -200 100 -200 {}
N 100 -200 180 -200 {}
N 100 -200 100 -110 {}
N 220 -170 220 -110 {}
N 220 -110 220 30 {}
N 360 300 360 -110 {}
N 100 -110 220 -110 {}
N 220 -110 360 -110 {}
N -220 -170 -220 -40 {}
N -220 -40 -220 30 {}
N -180 60 -120 60 {}
N -120 60 180 60 {}
N -120 -40 -120 60 {}
N -120 60 -120 460 {}
N -220 -40 -120 -40 {}
N 540 60 500 60 {}
N 500 60 500 460 {}
N 360 360 360 460 {}
N -460 530 -460 460 {}
N -280 530 -260 530 {}
N -280 560 -260 560 {}
N -260 530 -260 560 {}
N -260 560 -260 590 {}
N -280 590 -260 590 {}
N -320 560 -360 560 {}
N -360 560 -360 460 {}
N -700 460 -460 460 {}
N -460 460 -360 460 {}
N -360 460 -120 460 {}
N -120 460 360 460 {}
N 360 460 500 460 {}
N -700 460 -900 460 {}
N 580 -170 580 -60 {}
N 580 -60 580 30 {}
N 580 -60 640 -60 {}
N 640 -60 740 -60 {}
N 740 170 740 -60 {}
N 640 -60 640 330 {}
N 640 330 400 330 {}
N -600 -515 -600 -440 {}
N -600 -440 -600 -365 {}
N -560 -485 -560 -440 {}
N -560 -440 -560 -395 {}
N -560 -515 -540 -515 {}
N -560 -365 -540 -365 {}
N -900 -440 -600 -440 {}
N -560 -440 -460 -440 {}
N -460 -440 -460 -600 {}
N -20 -440 -60 -440 {}
N -60 -440 -60 -600 {}
N -460 -600 -60 -600 {}
N -60 -600 900 -600 {}
N 900 -600 1000 -600 {}
N 900 -600 900 200 {}
N 900 200 900 700 {}
N 900 200 780 200 {}
N 900 700 -560 700 {}
N -560 700 -560 560 {}
N -560 560 -500 560 {}
N -900 820 -840 820 {}
N -900 880 -840 880 {}
C {devices/iopin.sym} -900 820 0 1 {name=p4
lab=VDD}
C {devices/iopin.sym} -900 880 0 1 {name=p5
lab=VSS}
C {devices/ipin.sym} -900 -440 0 0 {name=p2
lab=en}
C {devices/opin.sym} 1000 -600 0 0 {name=p3
lab=enb}
C {devices/opin.sym} -900 460 0 0 {name=p1
lab=nb}
C {symbols/pfet_03v3.sym} 0 -440 0 0 {name=Msw
L=0.28u
W=4.0u
nf=1
m=1
ad=2.0p
as=2.0p
pd=9.0u
ps=9.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="4/0.28"}
C {symbols/vdd.sym} 40 -440 0 0 {name=l1
lab=VDD}
C {symbols/pfet_03v3.sym} -200 -200 0 1 {name=MP1
L=1.0u
W=4.0u
nf=1
m=2
ad=2.0p
as=2.0p
pd=9.0u
ps=9.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="4/1 ×2"}
C {symbols/vdd.sym} -240 -200 0 0 {name=l2
lab=VDD}
C {symbols/pfet_03v3.sym} 200 -200 0 0 {name=MP2
L=1.0u
W=4.0u
nf=1
m=2
ad=2.0p
as=2.0p
pd=9.0u
ps=9.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="4/1 ×2"}
C {symbols/vdd.sym} 240 -200 0 0 {name=l3
lab=VDD}
C {symbols/nfet_03v3.sym} -200 60 0 1 {name=MN1
L=0.5u
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
val="2/0.5"}
C {symbols/gnd.sym} -240 60 0 0 {name=l4
lab=VSS}
C {symbols/nfet_03v3.sym} 200 60 0 0 {name=MN2
L=0.5u
W=2.0u
nf=1
m=4
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
val="2/0.5 ×4"}
C {symbols/gnd.sym} 240 60 0 0 {name=l5
lab=VSS}
C {symbols/pfet_03v3.sym} 560 -200 0 0 {name=MS1
L=10.0u
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
model=pfet_03v3
spiceprefix=X
val="0.42/10"}
C {symbols/vdd.sym} 600 -200 0 0 {name=l6
lab=VDD}
C {symbols/nfet_03v3.sym} 560 60 0 0 {name=MS2
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
C {symbols/gnd.sym} 600 60 0 0 {name=l7
lab=VSS}
C {symbols/nfet_03v3.sym} 380 330 0 1 {name=MS3
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
C {symbols/gnd.sym} 340 330 0 0 {name=l8
lab=VSS}
C {symbols/nfet_03v3.sym} -480 560 0 0 {name=Moff
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
C {symbols/gnd.sym} -440 560 0 0 {name=l9
lab=VSS}
C {symbols/nfet_03v3.sym} 760 200 0 1 {name=Moff2
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
C {symbols/gnd.sym} 720 200 0 0 {name=l10
lab=VSS}
C {symbols/vdd.sym} 20 -470 0 0 {name=l11
lab=VDD}
C {symbols/gnd.sym} -220 90 0 0 {name=l12
lab=VSS}
C {symbols/gnd.sym} 580 90 0 0 {name=l13
lab=VSS}
C {symbols/gnd.sym} -460 590 0 0 {name=l14
lab=VSS}
C {symbols/gnd.sym} 740 230 0 0 {name=l15
lab=VSS}
C {symbols/ppolyf_u.sym} 220 200 2 0 {name=Rb
W=2.0e-6
L=29.714000000000002e-6
model=ppolyf_u
spiceprefix=X
m=1
val="2/29.714 (5.2k)"}
C {symbols/gnd.sym} 260 200 0 0 {name=l16
lab=VSS}
C {symbols/gnd.sym} 220 230 0 0 {name=l17
lab=VSS}
C {symbols/gnd.sym} 500 -200 0 0 {name=l18
lab=VSS}
C {symbols/nfet_03v3.sym} -300 560 0 0 {name=Cnb
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
C {symbols/gnd.sym} -260 590 0 0 {name=l19
lab=VSS}
C {symbols/pfet_03v3.sym} -580 -515 0 0 {name=Iep
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
model=pfet_03v3
spiceprefix=X
val="1/0.28"}
C {symbols/nfet_03v3.sym} -580 -365 0 0 {name=Ien
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
C {symbols/vdd.sym} -540 -515 0 0 {name=l20
lab=VDD}
C {symbols/vdd.sym} -560 -545 0 0 {name=l21
lab=VDD}
C {symbols/gnd.sym} -540 -365 0 0 {name=l22
lab=VSS}
C {symbols/gnd.sym} -560 -335 0 0 {name=l23
lab=VSS}
C {symbols/vdd.sym} -840 820 0 0 {name=l24
lab=VDD}
C {symbols/gnd.sym} -840 880 0 0 {name=l25
lab=VSS}
