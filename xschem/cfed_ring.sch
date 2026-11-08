v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {cfed_ring: 5-stage current-fed ring} -200 -420 0 0 0.6 0.6 {}
T {P 5/0.28 um, N 2/0.28 um (sim/vco/vco_bias.py, topo=cfed)} -200 -370 0 0 0.35 0.35 {}
T {N sources share vg: cfed_dac sinks the ring current, decap holds vg} -200 -342 0 0 0.35 0.35 {}
T {the ring swings vg..VDD; a4 -> a0 closes the loop} -200 -314 0 0 0.35 0.35 {}
N 60 -75 60 0 {}
N 60 0 60 75 {}
N 100 -45 100 0 {}
N 100 0 100 45 {}
N 320 -75 320 0 {}
N 320 0 320 75 {}
N 360 -45 360 0 {}
N 360 0 360 45 {}
N 580 -75 580 0 {}
N 580 0 580 75 {}
N 620 -45 620 0 {}
N 620 0 620 45 {}
N 840 -75 840 0 {}
N 840 0 840 75 {}
N 880 -45 880 0 {}
N 880 0 880 45 {}
N 1100 -75 1100 0 {}
N 1100 0 1100 75 {}
N 1140 -45 1140 0 {}
N 1140 0 1140 45 {}
N 100 -105 100 -160 {}
N 360 -105 360 -160 {}
N 620 -105 620 -160 {}
N 880 -105 880 -160 {}
N 1140 -105 1140 -160 {}
N 0 -160 100 -160 {}
N 100 -160 360 -160 {}
N 360 -160 620 -160 {}
N 620 -160 880 -160 {}
N 880 -160 1140 -160 {}
N 1140 -160 1200 -160 {}
N 100 105 100 160 {}
N 360 105 360 160 {}
N 620 105 620 160 {}
N 880 105 880 160 {}
N 1140 105 1140 160 {}
N 0 160 100 160 {}
N 100 160 360 160 {}
N 360 160 620 160 {}
N 620 160 880 160 {}
N 880 160 1140 160 {}
N 1140 160 1200 160 {}
N 100 0 320 0 {}
N 360 0 580 0 {}
N 620 0 840 0 {}
N 880 0 1100 0 {}
C {devices/iopin.sym} -200 -120 0 0 {name=p19
lab=VDD}
C {devices/iopin.sym} -200 -90 0 0 {name=p20
lab=vg}
C {devices/iopin.sym} -200 -60 0 0 {name=p21
lab=VSS}
C {devices/iopin.sym} -200 -30 0 0 {name=p22
lab=a0}
C {devices/iopin.sym} -200 0 0 0 {name=p23
lab=a1}
C {devices/iopin.sym} -200 30 0 0 {name=p24
lab=a2}
C {devices/iopin.sym} -200 60 0 0 {name=p25
lab=a3}
C {devices/iopin.sym} -200 90 0 0 {name=p26
lab=a4}
C {symbols/pfet_03v3.sym} 80 -75 0 0 {name=P0
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
spiceprefix=X}
C {symbols/nfet_03v3.sym} 80 75 0 0 {name=N0
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
spiceprefix=X}
C {devices/lab_pin.sym} 100 -75 0 1 {name=p1
sig_type=std_logic
lab=VDD}
C {devices/lab_pin.sym} 100 75 0 1 {name=p2
sig_type=std_logic
lab=VSS}
C {symbols/pfet_03v3.sym} 340 -75 0 0 {name=P1
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
spiceprefix=X}
C {symbols/nfet_03v3.sym} 340 75 0 0 {name=N1
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
spiceprefix=X}
C {devices/lab_pin.sym} 360 -75 0 1 {name=p3
sig_type=std_logic
lab=VDD}
C {devices/lab_pin.sym} 360 75 0 1 {name=p4
sig_type=std_logic
lab=VSS}
C {symbols/pfet_03v3.sym} 600 -75 0 0 {name=P2
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
spiceprefix=X}
C {symbols/nfet_03v3.sym} 600 75 0 0 {name=N2
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
spiceprefix=X}
C {devices/lab_pin.sym} 620 -75 0 1 {name=p5
sig_type=std_logic
lab=VDD}
C {devices/lab_pin.sym} 620 75 0 1 {name=p6
sig_type=std_logic
lab=VSS}
C {symbols/pfet_03v3.sym} 860 -75 0 0 {name=P3
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
spiceprefix=X}
C {symbols/nfet_03v3.sym} 860 75 0 0 {name=N3
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
spiceprefix=X}
C {devices/lab_pin.sym} 880 -75 0 1 {name=p7
sig_type=std_logic
lab=VDD}
C {devices/lab_pin.sym} 880 75 0 1 {name=p8
sig_type=std_logic
lab=VSS}
C {symbols/pfet_03v3.sym} 1120 -75 0 0 {name=P4
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
spiceprefix=X}
C {symbols/nfet_03v3.sym} 1120 75 0 0 {name=N4
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
spiceprefix=X}
C {devices/lab_pin.sym} 1140 -75 0 1 {name=p9
sig_type=std_logic
lab=VDD}
C {devices/lab_pin.sym} 1140 75 0 1 {name=p10
sig_type=std_logic
lab=VSS}
C {devices/lab_pin.sym} 0 -160 0 0 {name=p11
sig_type=std_logic
lab=VDD}
C {devices/lab_pin.sym} 0 160 0 0 {name=p12
sig_type=std_logic
lab=vg}
C {devices/lab_pin.sym} 60 0 0 0 {name=p13
sig_type=std_logic
lab=a0}
C {devices/lab_pin.sym} 320 0 0 0 {name=p14
sig_type=std_logic
lab=a1}
C {devices/lab_pin.sym} 580 0 0 0 {name=p15
sig_type=std_logic
lab=a2}
C {devices/lab_pin.sym} 840 0 0 0 {name=p16
sig_type=std_logic
lab=a3}
C {devices/lab_pin.sym} 1100 0 0 0 {name=p17
sig_type=std_logic
lab=a4}
C {devices/lab_pin.sym} 1140 0 0 1 {name=p18
sig_type=std_logic
lab=a0}
