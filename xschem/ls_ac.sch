v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {Cc 2 fF: M2-M3 metal fingers at the a0 tap} -300 90 0 0 0.3 0.3 {}
T {(no PDK device; LVS drops it)} -300 120 0 0 0.3 0.3 {}
T {lf} 100 440 0 0 0.3 0.3 {}
T {lg} 80 -26 0 0 0.3 0.3 {}
T {C1 ~1 pF gate cap} 520 560 0 0 0.3 0.3 {}
T {R1 500k} 960 300 0 0 0.3 0.3 {}
T {ls_ac: AC-coupled level shifter with duty-correcting feedback} -400 -560 0 0 0.7 0.7 {}
T {a0 swings vg..VDD; Cc removes vg, INV1-3 restore the full rail (ls)} -400 -500 0 0 0.42 0.42 {}
T {R1/C1 low-pass ls (tau 0.5 us) back to lg through LRB: 3 inversions = negative DC feedback, so mean(ls) sits at INV1's trip point (duty ~50 %)} -400 -466 0 0 0.42 0.42 {}
N 160 -75 160 0 {}
N 160 0 160 75 {}
N 200 -45 200 0 {}
N 200 0 200 45 {}
N 200 -75 220 -75 {}
N 200 75 220 75 {}
N 460 -75 460 0 {}
N 460 0 460 75 {}
N 500 -45 500 0 {}
N 500 0 500 45 {}
N 500 -75 520 -75 {}
N 500 75 520 75 {}
N 760 -75 760 0 {}
N 760 0 760 75 {}
N 800 -45 800 0 {}
N 800 0 800 45 {}
N 800 -75 820 -75 {}
N 800 75 820 75 {}
N 200 0 460 0 {}
N 500 0 760 0 {}
N 200 -105 200 -170 {}
N 500 -105 500 -170 {}
N 800 -105 800 -170 {}
N 200 -170 500 -170 {}
N 500 -170 800 -170 {}
N 200 105 200 170 {}
N 500 105 500 170 {}
N 800 105 800 170 {}
N 200 170 500 170 {}
N 500 170 800 170 {}
N -400 0 -230 0 {}
N -170 0 60 0 {}
N 60 0 160 0 {}
N 60 300 60 0 {}
N 60 330 80 330 {}
N 20 330 -20 330 {}
N 800 0 900 0 {}
N 900 0 1100 0 {}
N 900 0 900 300 {}
N 920 330 940 330 {}
N 480 470 500 470 {}
N 480 500 500 500 {}
N 500 470 500 500 {}
N 500 500 500 530 {}
N 480 530 500 530 {}
N 60 360 60 420 {}
N 900 360 900 420 {}
N 60 420 440 420 {}
N 440 420 900 420 {}
N 440 420 440 500 {}
N -400 640 -340 640 {}
N -400 700 -340 700 {}
C {devices/iopin.sym} -400 640 0 1 {name=p3
lab=VDD}
C {devices/iopin.sym} -400 700 0 1 {name=p4
lab=VSS}
C {devices/ipin.sym} -400 0 0 0 {name=p1
lab=a0}
C {devices/opin.sym} 1100 0 0 0 {name=p2
lab=ls}
C {symbols/pfet_03v3.sym} 180 -75 0 0 {name=L1p
L=0.28u
W=0.5u
nf=1
m=1
ad=0.25p
as=0.25p
pd=2.0u
ps=2.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="0.5/0.28"}
C {symbols/nfet_03v3.sym} 180 75 0 0 {name=L1n
L=0.28u
W=0.21999999999999997u
nf=1
m=1
ad=0.10999999999999999p
as=0.10999999999999999p
pd=1.44u
ps=1.44u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.22/0.28"}
C {symbols/vdd.sym} 220 -75 0 0 {name=l1
lab=VDD}
C {symbols/gnd.sym} 220 75 0 0 {name=l2
lab=VSS}
C {symbols/pfet_03v3.sym} 480 -75 0 0 {name=L2p
L=0.28u
W=1.5u
nf=1
m=1
ad=0.75p
as=0.75p
pd=4.0u
ps=4.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="1.5/0.28"}
C {symbols/nfet_03v3.sym} 480 75 0 0 {name=L2n
L=0.28u
W=0.6u
nf=1
m=1
ad=0.3p
as=0.3p
pd=2.2u
ps=2.2u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.6/0.28"}
C {symbols/vdd.sym} 520 -75 0 0 {name=l3
lab=VDD}
C {symbols/gnd.sym} 520 75 0 0 {name=l4
lab=VSS}
C {symbols/pfet_03v3.sym} 780 -75 0 0 {name=L3p
L=0.28u
W=3.0u
nf=1
m=1
ad=1.5p
as=1.5p
pd=7.0u
ps=7.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="3/0.28"}
C {symbols/nfet_03v3.sym} 780 75 0 0 {name=L3n
L=0.28u
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
val="1.2/0.28"}
C {symbols/vdd.sym} 820 -75 0 0 {name=l5
lab=VDD}
C {symbols/gnd.sym} 820 75 0 0 {name=l6
lab=VSS}
C {symbols/vdd.sym} 200 -170 0 0 {name=l7
lab=VDD}
C {symbols/gnd.sym} 200 170 0 0 {name=l8
lab=VSS}
C {devices/capa.sym} -200 0 3 0 {name=Cc
value=2e-15
m=1}
C {symbols/pfet_03v3.sym} 40 330 2 1 {name=LRB
L=2.0u
W=0.21999999999999997u
nf=1
m=1
ad=0.10999999999999999p
as=0.10999999999999999p
pd=1.44u
ps=1.44u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=pfet_03v3
spiceprefix=X
val="0.22/2"}
C {symbols/vdd.sym} 80 330 0 0 {name=l9
lab=VDD}
C {symbols/gnd.sym} -20 330 0 0 {name=l10
lab=VSS}
C {symbols/ppolyf_u_3k.sym} 900 330 2 0 {name=R1
W=1.0e-6
L=159.125e-6
model=ppolyf_u_3k
spiceprefix=X
m=1
val="1/159"}
C {symbols/gnd.sym} 940 330 0 0 {name=l11
lab=VSS}
C {symbols/nfet_03v3.sym} 460 500 0 0 {name=C1
L=16.0u
W=16.0u
nf=1
m=1
ad=8.0p
as=8.0p
pd=33.0u
ps=33.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="16/16"}
C {symbols/gnd.sym} 500 530 0 0 {name=l12
lab=VSS}
C {symbols/vdd.sym} -340 640 0 0 {name=l13
lab=VDD}
C {symbols/gnd.sym} -340 700 0 0 {name=l14
lab=VSS}
