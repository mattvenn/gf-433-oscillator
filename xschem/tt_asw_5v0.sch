v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {M3 ties mod to VGND when off} 470 270 0 0 0.3 0.3 {}
T {tt_asw_5v0: Tiny Tapeout GF180 analog switch (tnt)} -100 -480 0 0 0.7 0.7 {}
T {M2 nfet_05v0 217/0.6 (7 x 31/0.6), M1 pfet_05v0 592/0.5 (16 x 37/0.5); ctrl = 1: bus <-> mod} -100 -420 0 0 0.42 0.42 {}
T {mult: that many switches in parallel on bus (the level shifter not multiplied)} -100 -386 0 0 0.42 0.42 {}
N 120 0 200 0 {}
N 250 -50 250 -80 {}
N 330 -50 330 -80 {}
N 250 90 250 120 {}
N 520 0 540 0 {}
N 780 0 760 0 {}
N 520 -30 520 -80 {}
N 520 -80 650 -80 {}
N 780 -30 780 -80 {}
N 780 -80 650 -80 {}
N 650 -80 650 -160 {}
N 520 30 520 80 {}
N 520 80 650 80 {}
N 780 30 780 80 {}
N 780 80 650 80 {}
N 650 80 650 110 {}
N 650 110 650 150 {}
N 650 110 960 110 {}
N 650 180 670 180 {}
N 670 180 670 210 {}
N 670 210 650 210 {}
N 400 0 480 0 {}
N 400 40 440 40 {}
N 440 -240 440 40 {}
N 440 40 440 180 {}
N 440 180 610 180 {}
N 440 -240 880 -240 {}
N 880 -240 880 0 {}
N 880 0 820 0 {}
N -100 -240 -40 -240 {}
N -100 -180 -40 -180 {}
N -100 -120 -40 -120 {}
C {devices/iopin.sym} -100 -120 0 1 {name=p6
lab=VGND}
C {devices/iopin.sym} -100 -240 0 1 {name=p4
lab=VDPWR}
C {devices/iopin.sym} -100 -180 0 1 {name=p5
lab=VAPWR}
C {devices/ipin.sym} 120 0 0 0 {name=p1
lab=ctrl}
C {devices/iopin.sym} 960 110 0 0 {name=p3
lab=mod}
C {devices/iopin.sym} 650 -160 0 0 {name=p2
lab=bus}
C {lv2hv.sym} 300 20 0 0 {name=x1}
C {symbols/vdd.sym} 250 -80 0 0 {name=l1
lab=VDPWR}
C {symbols/vdd.sym} 330 -80 0 0 {name=l2
lab=VAPWR}
C {symbols/gnd.sym} 250 120 0 0 {name=l3
lab=VGND}
C {symbols/nfet_05v0.sym} 500 0 0 0 {name=M2
L=0.6u
W=31u
nf=1
m='7*mult'
ad=3.189p
as=3.189p
pd=35.63u
ps=35.63u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_05v0
spiceprefix=X}
C {symbols/pfet_05v0.sym} 800 0 0 1 {name=M1
L=0.5u
W=37u
nf=1
m='16*mult'
ad=3.330p
as=3.746p
pd=37.18u
ps=41.83u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_05v0
spiceprefix=X}
C {symbols/gnd.sym} 540 0 0 0 {name=l4
lab=VGND}
C {symbols/vdd.sym} 760 0 0 0 {name=l5
lab=VAPWR}
C {symbols/nfet_05v0.sym} 630 180 0 0 {name=M3
L=0.6u
W=31u
nf=1
m=mult
ad=5.58p
as=5.58p
pd=62.36u
ps=62.36u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_05v0
spiceprefix=X}
C {symbols/gnd.sym} 650 210 0 0 {name=l6
lab=VGND}
C {symbols/vdd.sym} -40 -240 0 0 {name=l7
lab=VDPWR}
C {symbols/vdd.sym} -40 -180 0 0 {name=l8
lab=VAPWR}
C {symbols/gnd.sym} -40 -120 0 0 {name=l9
lab=VGND}
