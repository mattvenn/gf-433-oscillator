v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {rx_lna2: LNA second stage (one per arm)} -500 -760 0 0 0.7 0.7 {}
T {NMOS pair 10/0.28 ×6 um, poly loads, tail 2/0.5 ×40 from nb; gates DC-coupled to stage 1 (~2.15 V); op = !ip side} -500 -700 0 0 0.42 0.42 {}
T {source: sim/rx/rx_lna.py stage2()} -500 -666 0 0 0.42 0.42 {}
N -100 0 -80 0 {}
N 100 0 80 0 {}
N 20 200 40 200 {}
N -100 30 -100 70 {}
N -100 70 20 70 {}
N 100 30 100 70 {}
N 100 70 20 70 {}
N 20 70 20 170 {}
N -100 -170 -100 -100 {}
N -100 -100 -100 -30 {}
N 100 -170 100 -100 {}
N 100 -100 100 -30 {}
N -120 -200 -140 -200 {}
N 80 -200 60 -200 {}
N -500 0 -140 0 {}
N -500 330 220 330 {}
N 220 330 220 0 {}
N 220 0 140 0 {}
N -500 200 -20 200 {}
N -100 -100 -300 -100 {}
N -300 -100 -300 -420 {}
N -300 -420 500 -420 {}
N 100 -100 300 -100 {}
N 300 -100 300 -360 {}
N 300 -360 500 -360 {}
N -500 520 -440 520 {}
N -500 580 -440 580 {}
C {devices/iopin.sym} -500 520 0 1 {name=p6
lab=VDD}
C {devices/iopin.sym} -500 580 0 1 {name=p7
lab=VSS}
C {devices/ipin.sym} -500 0 0 0 {name=p1
lab=ip}
C {devices/ipin.sym} -500 330 0 0 {name=p2
lab=im}
C {devices/opin.sym} 500 -360 0 0 {name=p5
lab=op}
C {devices/opin.sym} 500 -420 0 0 {name=p4
lab=om}
C {devices/ipin.sym} -500 200 0 0 {name=p3
lab=nb}
C {symbols/nfet_03v3.sym} -120 0 0 0 {name=M1
L=0.28u
W=10.0u
nf=1
m=6
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
val="10/0.28 ×6"}
C {symbols/nfet_03v3.sym} 120 0 0 1 {name=M2
L=0.28u
W=10.0u
nf=1
m=6
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
val="10/0.28 ×6"}
C {symbols/nfet_03v3.sym} 0 200 0 0 {name=Mt
L=0.5u
W=2.0u
nf=1
m=40
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
val="2/0.5 ×40"}
C {symbols/ppolyf_u.sym} -100 -200 0 0 {name=RLp
W=2.0e-6
L=9.143e-6
model=ppolyf_u
spiceprefix=X
m=1
val="2/9.143 (1.6k)"}
C {symbols/ppolyf_u.sym} 100 -200 0 0 {name=RLn
W=2.0e-6
L=9.143e-6
model=ppolyf_u
spiceprefix=X
m=1
val="2/9.143 (1.6k)"}
C {symbols/gnd.sym} -80 0 0 0 {name=l1
lab=VSS}
C {symbols/gnd.sym} 80 0 0 0 {name=l2
lab=VSS}
C {symbols/gnd.sym} 40 200 0 0 {name=l3
lab=VSS}
C {symbols/gnd.sym} 20 230 0 0 {name=l4
lab=VSS}
C {symbols/vdd.sym} -100 -230 0 0 {name=l5
lab=VDD}
C {symbols/vdd.sym} 100 -230 0 0 {name=l6
lab=VDD}
C {symbols/gnd.sym} -140 -200 0 0 {name=l7
lab=VSS}
C {symbols/gnd.sym} 60 -200 0 0 {name=l8
lab=VSS}
C {symbols/vdd.sym} -440 520 0 0 {name=l9
lab=VDD}
C {symbols/gnd.sym} -440 580 0 0 {name=l10
lab=VSS}
