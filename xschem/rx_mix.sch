v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {S1} 160 90 0 0 0.35 0.35 {}
T {S4} 560 90 0 0 0.35 0.35 {}
T {S3} 960 90 0 0 0.35 0.35 {}
T {S2} 1360 90 0 0 0.35 0.35 {}
T {Cbp ~500 fF} 1760 470 0 0 0.3 0.3 {}
T {Cbn ~500 fF} 1920 550 0 0 0.3 0.3 {}
T {rx_mix: passive double-balanced mixer (one per arm)} -400 -800 0 0 0.7 0.7 {}
T {four transmission gates (N 8/0.28, P 16/0.28 um): lo connects rfp-bbp and rfn-bbn, lob crosses them; the RF nodes sit at the LNA output DC (~2.5 V), so each switch is a full TG} -400 -740 0 0 0.42 0.42 {}
T {no DC through the switches (the baseband is high-Z), so no flicker noise; source: sim/rx/rx_mix.py block()} -400 -706 0 0 0.42 0.42 {}
N 140 0 160 0 {}
N 260 0 240 0 {}
N 140 -30 140 -60 {}
N 140 -60 200 -60 {}
N 260 -30 260 -60 {}
N 260 -60 200 -60 {}
N 140 30 140 60 {}
N 140 60 200 60 {}
N 260 30 260 60 {}
N 260 60 200 60 {}
N 200 -60 200 -300 {}
N 200 60 200 300 {}
N 100 0 60 0 {}
N 60 0 60 -520 {}
N 300 0 340 0 {}
N 340 0 340 -460 {}
N 540 0 560 0 {}
N 660 0 640 0 {}
N 540 -30 540 -60 {}
N 540 -60 600 -60 {}
N 660 -30 660 -60 {}
N 660 -60 600 -60 {}
N 540 30 540 60 {}
N 540 60 600 60 {}
N 660 30 660 60 {}
N 660 60 600 60 {}
N 600 -60 600 -300 {}
N 600 60 600 380 {}
N 500 0 460 0 {}
N 460 0 460 -460 {}
N 700 0 740 0 {}
N 740 0 740 -520 {}
N 940 0 960 0 {}
N 1060 0 1040 0 {}
N 940 -30 940 -60 {}
N 940 -60 1000 -60 {}
N 1060 -30 1060 -60 {}
N 1060 -60 1000 -60 {}
N 940 30 940 60 {}
N 940 60 1000 60 {}
N 1060 30 1060 60 {}
N 1060 60 1000 60 {}
N 1000 -60 1000 -380 {}
N 1000 60 1000 300 {}
N 900 0 860 0 {}
N 860 0 860 -460 {}
N 1100 0 1140 0 {}
N 1140 0 1140 -520 {}
N 1340 0 1360 0 {}
N 1460 0 1440 0 {}
N 1340 -30 1340 -60 {}
N 1340 -60 1400 -60 {}
N 1460 -30 1460 -60 {}
N 1460 -60 1400 -60 {}
N 1340 30 1340 60 {}
N 1340 60 1400 60 {}
N 1460 30 1460 60 {}
N 1460 60 1400 60 {}
N 1400 -60 1400 -380 {}
N 1400 60 1400 380 {}
N 1300 0 1260 0 {}
N 1260 0 1260 -520 {}
N 1500 0 1540 0 {}
N 1540 0 1540 -460 {}
N -400 -300 200 -300 {}
N 200 -300 600 -300 {}
N -400 -380 1000 -380 {}
N 1000 -380 1400 -380 {}
N -400 -520 60 -520 {}
N 60 -520 740 -520 {}
N 740 -520 1140 -520 {}
N 1140 -520 1260 -520 {}
N -400 -460 340 -460 {}
N 340 -460 460 -460 {}
N 460 -460 860 -460 {}
N 860 -460 1540 -460 {}
N 1640 450 1640 300 {}
N 1680 450 1640 450 {}
N 200 300 1000 300 {}
N 1000 300 1640 300 {}
N 1640 300 1900 300 {}
N 1720 420 1740 420 {}
N 1720 450 1740 450 {}
N 1740 420 1740 450 {}
N 1740 450 1740 480 {}
N 1720 480 1740 480 {}
N 1800 530 1800 380 {}
N 1840 530 1800 530 {}
N 600 380 1400 380 {}
N 1400 380 1800 380 {}
N 1800 380 1900 380 {}
N 1880 500 1900 500 {}
N 1880 530 1900 530 {}
N 1900 500 1900 530 {}
N 1900 530 1900 560 {}
N 1880 560 1900 560 {}
N -400 700 -340 700 {}
N -400 760 -340 760 {}
C {devices/iopin.sym} -400 700 0 1 {name=p7
lab=VDD}
C {devices/iopin.sym} -400 760 0 1 {name=p8
lab=VSS}
C {devices/ipin.sym} -400 -300 0 0 {name=p1
lab=rfp}
C {devices/ipin.sym} -400 -380 0 0 {name=p2
lab=rfn}
C {devices/opin.sym} 1900 300 0 0 {name=p5
lab=bbp}
C {devices/opin.sym} 1900 380 0 0 {name=p6
lab=bbn}
C {devices/ipin.sym} -400 -520 0 0 {name=p3
lab=lo}
C {devices/ipin.sym} -400 -460 0 0 {name=p4
lab=lob}
C {symbols/nfet_03v3.sym} 120 0 2 1 {name=S1n
L=0.28u
W=8.0u
nf=1
m=1
ad=4.0p
as=4.0p
pd=17.0u
ps=17.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="8/0.28"}
C {symbols/pfet_03v3.sym} 280 0 0 1 {name=S1p
L=0.28u
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
model=pfet_03v3
spiceprefix=X
val="16/0.28"}
C {symbols/gnd.sym} 160 0 0 0 {name=l1
lab=VSS}
C {symbols/vdd.sym} 240 0 0 0 {name=l2
lab=VDD}
C {symbols/nfet_03v3.sym} 520 0 2 1 {name=S4n
L=0.28u
W=8.0u
nf=1
m=1
ad=4.0p
as=4.0p
pd=17.0u
ps=17.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="8/0.28"}
C {symbols/pfet_03v3.sym} 680 0 0 1 {name=S4p
L=0.28u
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
model=pfet_03v3
spiceprefix=X
val="16/0.28"}
C {symbols/gnd.sym} 560 0 0 0 {name=l3
lab=VSS}
C {symbols/vdd.sym} 640 0 0 0 {name=l4
lab=VDD}
C {symbols/nfet_03v3.sym} 920 0 2 1 {name=S3n
L=0.28u
W=8.0u
nf=1
m=1
ad=4.0p
as=4.0p
pd=17.0u
ps=17.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="8/0.28"}
C {symbols/pfet_03v3.sym} 1080 0 0 1 {name=S3p
L=0.28u
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
model=pfet_03v3
spiceprefix=X
val="16/0.28"}
C {symbols/gnd.sym} 960 0 0 0 {name=l5
lab=VSS}
C {symbols/vdd.sym} 1040 0 0 0 {name=l6
lab=VDD}
C {symbols/nfet_03v3.sym} 1320 0 2 1 {name=S2n
L=0.28u
W=8.0u
nf=1
m=1
ad=4.0p
as=4.0p
pd=17.0u
ps=17.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="8/0.28"}
C {symbols/pfet_03v3.sym} 1480 0 0 1 {name=S2p
L=0.28u
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
model=pfet_03v3
spiceprefix=X
val="16/0.28"}
C {symbols/gnd.sym} 1360 0 0 0 {name=l7
lab=VSS}
C {symbols/vdd.sym} 1440 0 0 0 {name=l8
lab=VDD}
C {symbols/nfet_03v3.sym} 1700 450 0 0 {name=Cbp
L=5.0u
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
val="24.6/5"}
C {symbols/gnd.sym} 1740 480 0 0 {name=l9
lab=VSS}
C {symbols/nfet_03v3.sym} 1860 530 0 0 {name=Cbn
L=5.0u
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
val="24.6/5"}
C {symbols/gnd.sym} 1900 560 0 0 {name=l10
lab=VSS}
C {symbols/vdd.sym} -340 700 0 0 {name=l11
lab=VDD}
C {symbols/gnd.sym} -340 760 0 0 {name=l12
lab=VSS}
