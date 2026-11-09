v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {3.3 V: in -> in_n -> in_p} -20 170 0 0 0.3 0.3 {}
T {5 V latch (n1, n2)} 470 -380 0 0 0.3 0.3 {}
T {outputs on VAPWR} 920 170 0 0 0.3 0.3 {}
T {lv2hv: 3.3 V -> VAPWR level shifter (tnt, tt_asw_5v0)} -200 -560 0 0 0.7 0.7 {}
T {3.3 V inverters 2/0.28 + 0.89/0.28; latch 0.5/0.5 + 0.5/0.6; outputs 1/0.5 nf 2 + 0.5/0.6} -200 -500 0 0 0.42 0.42 {}
T {in = 1: out_p = VAPWR, out_n = 0} -200 -466 0 0 0.42 0.42 {}
N -20 -100 -20 0 {}
N -20 0 -20 100 {}
N 20 -70 20 0 {}
N 20 0 20 70 {}
N 20 -100 40 -100 {}
N 40 -100 40 -130 {}
N 40 -130 20 -130 {}
N 20 100 40 100 {}
N 40 100 40 130 {}
N 40 130 20 130 {}
N 180 -100 180 0 {}
N 180 0 180 100 {}
N 220 -70 220 0 {}
N 220 0 220 70 {}
N 220 -100 240 -100 {}
N 240 -100 240 -130 {}
N 240 -130 220 -130 {}
N 220 100 240 100 {}
N 240 100 240 130 {}
N 240 130 220 130 {}
N -100 0 -20 0 {}
N 20 0 100 0 {}
N 100 0 180 0 {}
N 480 -100 460 -100 {}
N 460 -100 460 -130 {}
N 460 -130 480 -130 {}
N 720 -100 740 -100 {}
N 740 -100 740 -130 {}
N 740 -130 720 -130 {}
N 480 100 500 100 {}
N 500 100 500 130 {}
N 500 130 480 130 {}
N 720 100 700 100 {}
N 700 100 700 130 {}
N 700 130 720 130 {}
N 480 -70 480 -40 {}
N 480 -40 480 20 {}
N 480 20 480 70 {}
N 720 -70 720 -20 {}
N 720 -20 720 40 {}
N 720 40 720 70 {}
N 520 -100 580 -100 {}
N 580 -100 580 -20 {}
N 580 -20 720 -20 {}
N 680 -100 620 -100 {}
N 620 -100 620 20 {}
N 620 20 480 20 {}
N 220 0 400 0 {}
N 400 0 400 100 {}
N 400 100 440 100 {}
N 100 0 100 260 {}
N 100 260 780 260 {}
N 780 260 780 100 {}
N 780 100 760 100 {}
N 940 -100 940 0 {}
N 940 0 940 100 {}
N 980 -70 980 0 {}
N 980 0 980 70 {}
N 980 -100 1000 -100 {}
N 1000 -100 1000 -130 {}
N 1000 -130 980 -130 {}
N 980 100 1000 100 {}
N 1000 100 1000 130 {}
N 1000 130 980 130 {}
N 1140 -100 1140 0 {}
N 1140 0 1140 100 {}
N 1180 -70 1180 0 {}
N 1180 0 1180 70 {}
N 1180 -100 1200 -100 {}
N 1200 -100 1200 -130 {}
N 1200 -130 1180 -130 {}
N 1180 100 1200 100 {}
N 1200 100 1200 130 {}
N 1200 130 1180 130 {}
N 480 -40 420 -40 {}
N 420 -40 420 -300 {}
N 420 -300 900 -300 {}
N 900 -300 900 0 {}
N 900 0 940 0 {}
N 720 40 800 40 {}
N 800 40 800 320 {}
N 800 320 1100 320 {}
N 1100 320 1100 0 {}
N 1100 0 1140 0 {}
N 980 0 1040 0 {}
N 1040 0 1040 -220 {}
N 1040 -220 1280 -220 {}
N 1180 0 1280 0 {}
N -200 -320 -140 -320 {}
N -200 -260 -140 -260 {}
N -200 -200 -140 -200 {}
C {devices/iopin.sym} -200 -200 0 1 {name=p6
lab=VGND}
C {devices/iopin.sym} -200 -320 0 1 {name=p4
lab=VDPWR}
C {devices/iopin.sym} -200 -260 0 1 {name=p5
lab=VAPWR}
C {devices/ipin.sym} -100 0 0 0 {name=p1
lab=in}
C {devices/opin.sym} 1280 -220 0 0 {name=p2
lab=out_p}
C {devices/opin.sym} 1280 0 0 0 {name=p3
lab=out_n}
C {symbols/pfet_03v3.sym} 0 -100 0 0 {name=M1
L=0.28u
W=2.0u
nf=1
m=1
ad=0.36p
as=0.36p
pd=4.36u
ps=4.36u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X}
C {symbols/nfet_03v3.sym} 0 100 0 0 {name=M2
L=0.28u
W=0.89u
nf=1
m=1
ad=0.1602p
as=0.1602p
pd=2.14u
ps=2.14u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X}
C {symbols/vdd.sym} 20 -130 0 0 {name=l1
lab=VDPWR}
C {symbols/gnd.sym} 20 130 0 0 {name=l2
lab=VGND}
C {symbols/pfet_03v3.sym} 200 -100 0 0 {name=M3
L=0.28u
W=2.0u
nf=1
m=1
ad=0.36p
as=0.36p
pd=4.36u
ps=4.36u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X}
C {symbols/nfet_03v3.sym} 200 100 0 0 {name=M4
L=0.28u
W=0.89u
nf=1
m=1
ad=0.1602p
as=0.1602p
pd=2.14u
ps=2.14u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X}
C {symbols/vdd.sym} 220 -130 0 0 {name=l3
lab=VDPWR}
C {symbols/gnd.sym} 220 130 0 0 {name=l4
lab=VGND}
C {symbols/pfet_05v0.sym} 500 -100 0 1 {name=M5
L=0.5u
W=0.5u
nf=1
m=1
ad=0.09p
as=0.09p
pd=1.36u
ps=1.36u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_05v0
spiceprefix=X}
C {symbols/nfet_05v0.sym} 460 100 0 0 {name=M6
L=0.6u
W=0.5u
nf=1
m=1
ad=0.09p
as=0.09p
pd=1.36u
ps=1.36u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_05v0
spiceprefix=X}
C {symbols/pfet_05v0.sym} 700 -100 0 0 {name=M7
L=0.5u
W=0.5u
nf=1
m=1
ad=0.09p
as=0.09p
pd=1.36u
ps=1.36u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_05v0
spiceprefix=X}
C {symbols/nfet_05v0.sym} 740 100 0 1 {name=M8
L=0.6u
W=0.5u
nf=1
m=1
ad=0.09p
as=0.09p
pd=1.36u
ps=1.36u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_05v0
spiceprefix=X}
C {symbols/vdd.sym} 480 -130 0 0 {name=l5
lab=VAPWR}
C {symbols/vdd.sym} 720 -130 0 0 {name=l6
lab=VAPWR}
C {symbols/gnd.sym} 480 130 0 0 {name=l7
lab=VGND}
C {symbols/gnd.sym} 720 130 0 0 {name=l8
lab=VGND}
C {symbols/pfet_05v0.sym} 960 -100 0 0 {name=M9
L=0.5u
W=1.0u
nf=2
m=1
ad=0.09p
as=0.18p
pd=1.36u
ps=2.72u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_05v0
spiceprefix=X}
C {symbols/nfet_05v0.sym} 960 100 0 0 {name=M10
L=0.6u
W=0.5u
nf=1
m=1
ad=0.09p
as=0.09p
pd=1.36u
ps=1.36u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_05v0
spiceprefix=X}
C {symbols/vdd.sym} 980 -130 0 0 {name=l9
lab=VAPWR}
C {symbols/gnd.sym} 980 130 0 0 {name=l10
lab=VGND}
C {symbols/pfet_05v0.sym} 1160 -100 0 0 {name=M11
L=0.5u
W=1.0u
nf=2
m=1
ad=0.09p
as=0.18p
pd=1.36u
ps=2.72u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_05v0
spiceprefix=X}
C {symbols/nfet_05v0.sym} 1160 100 0 0 {name=M12
L=0.6u
W=0.5u
nf=1
m=1
ad=0.09p
as=0.09p
pd=1.36u
ps=1.36u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_05v0
spiceprefix=X}
C {symbols/vdd.sym} 1180 -130 0 0 {name=l11
lab=VAPWR}
C {symbols/gnd.sym} 1180 130 0 0 {name=l12
lab=VGND}
C {symbols/vdd.sym} -140 -320 0 0 {name=l13
lab=VDPWR}
C {symbols/vdd.sym} -140 -260 0 0 {name=l14
lab=VAPWR}
C {symbols/gnd.sym} -140 -200 0 0 {name=l15
lab=VGND}
