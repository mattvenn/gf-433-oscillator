v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {vg decap ~3 pF} 150 -40 0 0 0.35 0.35 {}
T {ring_core_v3: cfed ring + DAC + vg decap} -300 -520 0 0 0.7 0.7 {}
T {the LVS source of layout/ring_core_v3.gds} -300 -460 0 0 0.42 0.42 {}
T {vbn here is the DAC gate bias; vco_cfed drives it from the filtered vbnf} -300 -426 0 0 0.42 0.42 {}
N -300 -220 -100 -220 {}
N -300 -180 -100 -180 {}
N -300 -140 -100 -140 {}
N -300 -100 -100 -100 {}
N -300 -60 -100 -60 {}
N -300 -20 -100 -20 {}
N -300 20 -100 20 {}
N -300 60 -100 60 {}
N -300 100 -100 100 {}
N -300 140 -100 140 {}
N -300 180 -100 180 {}
N -300 220 -100 220 {}
N 100 -220 180 -220 {}
N 180 -220 370 -220 {}
N 370 -220 400 -220 {}
N 180 -220 180 -120 {}
N 220 -150 240 -150 {}
N 220 -120 240 -120 {}
N 240 -150 240 -120 {}
N 240 -120 240 -90 {}
N 220 -90 240 -90 {}
N 370 -220 370 60 {}
N 370 60 800 60 {}
N 600 -220 800 -220 {}
N 600 -180 800 -180 {}
N 600 -140 800 -140 {}
N 600 -100 800 -100 {}
N 600 -60 800 -60 {}
N -300 360 -240 360 {}
N -300 420 -240 420 {}
C {devices/iopin.sym} -300 360 0 1 {name=p19
lab=VDD}
C {devices/iopin.sym} -300 420 0 1 {name=p20
lab=VSS}
C {devices/ipin.sym} -300 220 0 0 {name=p12
lab=vbn}
C {devices/ipin.sym} -300 180 0 0 {name=p11
lab=vctrl}
C {devices/ipin.sym} -300 100 0 0 {name=p9
lab=bit0}
C {devices/ipin.sym} -300 20 0 0 {name=p7
lab=bit1}
C {devices/ipin.sym} -300 -60 0 0 {name=p5
lab=bit2}
C {devices/ipin.sym} -300 -140 0 0 {name=p3
lab=bit3}
C {devices/ipin.sym} -300 -220 0 0 {name=p1
lab=bit4}
C {devices/ipin.sym} -300 140 0 0 {name=p10
lab=bitb0}
C {devices/ipin.sym} -300 60 0 0 {name=p8
lab=bitb1}
C {devices/ipin.sym} -300 -20 0 0 {name=p6
lab=bitb2}
C {devices/ipin.sym} -300 -100 0 0 {name=p4
lab=bitb3}
C {devices/ipin.sym} -300 -180 0 0 {name=p2
lab=bitb4}
C {devices/iopin.sym} 800 60 0 0 {name=p13
lab=vg}
C {devices/opin.sym} 800 -220 0 0 {name=p14
lab=a0}
C {devices/opin.sym} 800 -180 0 0 {name=p15
lab=a1}
C {devices/opin.sym} 800 -140 0 0 {name=p16
lab=a2}
C {devices/opin.sym} 800 -100 0 0 {name=p17
lab=a3}
C {devices/opin.sym} 800 -60 0 0 {name=p18
lab=a4}
C {cfed_dac.sym} 0 0 0 0 {name=xdac}
C {cfed_ring.sym} 500 -140 0 0 {name=xring}
C {symbols/nfet_03v3.sym} 200 -120 0 0 {name=DC
L=4.0u
W=30.71u
nf=1
m=6
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
val="30.71/4 ×6"}
C {symbols/gnd.sym} 240 -90 0 0 {name=l1
lab=VSS}
C {symbols/vdd.sym} -50 -270 0 0 {name=l2
lab=VDD}
C {symbols/gnd.sym} -50 270 0 0 {name=l3
lab=VSS}
C {symbols/vdd.sym} 450 -270 0 0 {name=l4
lab=VDD}
C {symbols/gnd.sym} 450 -10 0 0 {name=l5
lab=VSS}
C {symbols/vdd.sym} -240 360 0 0 {name=l6
lab=VDD}
C {symbols/gnd.sym} -240 420 0 0 {name=l7
lab=VSS}
