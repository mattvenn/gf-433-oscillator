v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {vb} -700 306 0 0 0.3 0.3 {}
T {vgr} -700 386 0 0 0.3 0.3 {}
T {nb} -700 496 0 0 0.3 0.3 {}
T {rx_bb: baseband, three stages (one per arm)} -1300 -900 0 0 0.7 0.7 {}
T {stage 1 20/1 ×16 um, 200 uA, 10 kOhm (DC-coupled to the mixer); stages 2 / 3 4/1 ×2 um, ~4 uA, 200 kOhm + 4.0 pF: two poles near 230 kHz (-3 dB about 145 kHz)} -1300 -840 0 0 0.42 0.42 {}
T {AC couplings: pfet gate caps; Mr (gate vgr, ~60 MOhm) || pseudo-resistor to vb: high-pass about 9 kHz in all; source: sim/rx/rx_bb.py block()} -1300 -806 0 0 0.42 0.42 {}
N -800 -300 -780 -300 {}
N -780 -100 -760 -100 {}
N -800 -270 -800 -130 {}
N -780 700 -760 700 {}
N -800 -70 -800 330 {}
N -800 670 -800 330 {}
N -1000 170 -980 170 {}
N -1000 200 -980 200 {}
N -980 170 -980 200 {}
N -980 200 -980 230 {}
N -1000 230 -980 230 {}
N -1040 200 -1080 200 {}
N -1080 200 -1080 330 {}
N -600 230 -580 230 {}
N -580 230 -580 260 {}
N -580 260 -600 260 {}
N -600 260 -600 330 {}
N -600 600 -580 600 {}
N -600 200 -600 140 {}
N -600 140 -680 140 {}
N -680 140 -680 230 {}
N -680 230 -680 410 {}
N -680 230 -640 230 {}
N -600 570 -600 410 {}
N -640 600 -660 600 {}
N -660 600 -660 520 {}
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
N -100 -100 -300 -100 {}
N 100 -100 300 -100 {}
N -300 -360 -300 -100 {}
N 300 -300 300 -100 {}
N -20 200 -60 200 {}
N -60 200 -60 520 {}
N 300 -300 460 -300 {}
N 480 -230 460 -230 {}
N 480 -200 460 -200 {}
N 480 -170 460 -170 {}
N 460 -300 460 -230 {}
N 460 -230 460 -200 {}
N 460 -200 460 -170 {}
N 600 150 620 150 {}
N 620 150 620 180 {}
N 620 180 600 180 {}
N 520 -200 600 -200 {}
N 600 -200 600 0 {}
N 600 0 600 30 {}
N 600 30 600 120 {}
N 780 90 800 90 {}
N 800 90 800 60 {}
N 800 60 780 60 {}
N 780 210 800 210 {}
N 800 210 800 240 {}
N 800 240 780 240 {}
N 600 30 780 30 {}
N 780 30 780 60 {}
N 780 120 780 150 {}
N 780 150 780 180 {}
N 740 90 720 90 {}
N 740 210 720 210 {}
N 720 90 720 150 {}
N 720 150 720 210 {}
N 720 150 780 150 {}
N 600 180 600 330 {}
N 780 240 780 330 {}
N 560 150 520 150 {}
N 520 150 520 410 {}
N -300 -360 860 -360 {}
N 880 -230 860 -230 {}
N 880 -200 860 -200 {}
N 880 -170 860 -170 {}
N 860 -360 860 -230 {}
N 860 -230 860 -200 {}
N 860 -200 860 -170 {}
N 1000 150 1020 150 {}
N 1020 150 1020 180 {}
N 1020 180 1000 180 {}
N 920 -200 1000 -200 {}
N 1000 -200 1000 -60 {}
N 1000 -60 1000 30 {}
N 1000 30 1000 120 {}
N 1180 90 1200 90 {}
N 1200 90 1200 60 {}
N 1200 60 1180 60 {}
N 1180 210 1200 210 {}
N 1200 210 1200 240 {}
N 1200 240 1180 240 {}
N 1000 30 1180 30 {}
N 1180 30 1180 60 {}
N 1180 120 1180 150 {}
N 1180 150 1180 180 {}
N 1140 90 1120 90 {}
N 1140 210 1120 210 {}
N 1120 90 1120 150 {}
N 1120 150 1120 210 {}
N 1120 150 1180 150 {}
N 1000 180 1000 330 {}
N 1180 240 1180 330 {}
N 960 150 920 150 {}
N 920 150 920 410 {}
N 1600 0 1620 0 {}
N 1800 0 1780 0 {}
N 1720 200 1740 200 {}
N 1600 30 1600 70 {}
N 1600 70 1720 70 {}
N 1800 30 1800 70 {}
N 1800 70 1720 70 {}
N 1720 70 1720 170 {}
N 1600 -170 1600 -100 {}
N 1600 -100 1600 -30 {}
N 1800 -170 1800 -100 {}
N 1800 -100 1800 -30 {}
N 1580 -200 1560 -200 {}
N 1780 -200 1760 -200 {}
N 1600 -100 1400 -100 {}
N 1800 -100 2000 -100 {}
N 1400 -360 1400 -100 {}
N 1400 -100 1400 120 {}
N 2000 -300 2000 -100 {}
N 2000 -100 2000 120 {}
N 1520 90 1540 90 {}
N 1520 120 1540 120 {}
N 1540 90 1540 120 {}
N 1540 120 1540 150 {}
N 1520 150 1540 150 {}
N 1400 120 1480 120 {}
N 2120 90 2140 90 {}
N 2120 120 2140 120 {}
N 2140 90 2140 120 {}
N 2140 120 2140 150 {}
N 2120 150 2140 150 {}
N 2000 120 2080 120 {}
N 1680 200 1640 200 {}
N 1640 200 1640 520 {}
N 600 0 1560 0 {}
N 1000 -60 1920 -60 {}
N 1920 -60 1920 0 {}
N 1920 0 1840 0 {}
N 2000 -300 2160 -300 {}
N 2180 -230 2160 -230 {}
N 2180 -200 2160 -200 {}
N 2180 -170 2160 -170 {}
N 2160 -300 2160 -230 {}
N 2160 -230 2160 -200 {}
N 2160 -200 2160 -170 {}
N 2300 150 2320 150 {}
N 2320 150 2320 180 {}
N 2320 180 2300 180 {}
N 2220 -200 2300 -200 {}
N 2300 -200 2300 0 {}
N 2300 0 2300 30 {}
N 2300 30 2300 120 {}
N 2480 90 2500 90 {}
N 2500 90 2500 60 {}
N 2500 60 2480 60 {}
N 2480 210 2500 210 {}
N 2500 210 2500 240 {}
N 2500 240 2480 240 {}
N 2300 30 2480 30 {}
N 2480 30 2480 60 {}
N 2480 120 2480 150 {}
N 2480 150 2480 180 {}
N 2440 90 2420 90 {}
N 2440 210 2420 210 {}
N 2420 90 2420 150 {}
N 2420 150 2420 210 {}
N 2420 150 2480 150 {}
N 2300 180 2300 330 {}
N 2480 240 2480 330 {}
N 2260 150 2220 150 {}
N 2220 150 2220 410 {}
N 1400 -360 2560 -360 {}
N 2580 -230 2560 -230 {}
N 2580 -200 2560 -200 {}
N 2580 -170 2560 -170 {}
N 2560 -360 2560 -230 {}
N 2560 -230 2560 -200 {}
N 2560 -200 2560 -170 {}
N 2700 150 2720 150 {}
N 2720 150 2720 180 {}
N 2720 180 2700 180 {}
N 2620 -200 2700 -200 {}
N 2700 -200 2700 -60 {}
N 2700 -60 2700 30 {}
N 2700 30 2700 120 {}
N 2880 90 2900 90 {}
N 2900 90 2900 60 {}
N 2900 60 2880 60 {}
N 2880 210 2900 210 {}
N 2900 210 2900 240 {}
N 2900 240 2880 240 {}
N 2700 30 2880 30 {}
N 2880 30 2880 60 {}
N 2880 120 2880 150 {}
N 2880 150 2880 180 {}
N 2840 90 2820 90 {}
N 2840 210 2820 210 {}
N 2820 90 2820 150 {}
N 2820 150 2820 210 {}
N 2820 150 2880 150 {}
N 2700 180 2700 330 {}
N 2880 240 2880 330 {}
N 2660 150 2620 150 {}
N 2620 150 2620 410 {}
N 3300 0 3320 0 {}
N 3500 0 3480 0 {}
N 3420 200 3440 200 {}
N 3300 30 3300 70 {}
N 3300 70 3420 70 {}
N 3500 30 3500 70 {}
N 3500 70 3420 70 {}
N 3420 70 3420 170 {}
N 3300 -170 3300 -100 {}
N 3300 -100 3300 -30 {}
N 3500 -170 3500 -100 {}
N 3500 -100 3500 -30 {}
N 3280 -200 3260 -200 {}
N 3480 -200 3460 -200 {}
N 3300 -100 3100 -100 {}
N 3500 -100 3700 -100 {}
N 3100 -360 3100 -100 {}
N 3100 -100 3100 120 {}
N 3700 -300 3700 -100 {}
N 3700 -100 3700 120 {}
N 3220 90 3240 90 {}
N 3220 120 3240 120 {}
N 3240 90 3240 120 {}
N 3240 120 3240 150 {}
N 3220 150 3240 150 {}
N 3100 120 3180 120 {}
N 3820 90 3840 90 {}
N 3820 120 3840 120 {}
N 3840 90 3840 120 {}
N 3840 120 3840 150 {}
N 3820 150 3840 150 {}
N 3700 120 3780 120 {}
N 3380 200 3340 200 {}
N 3340 200 3340 520 {}
N 2300 0 3260 0 {}
N 2700 -60 3620 -60 {}
N 3620 -60 3620 0 {}
N 3620 0 3540 0 {}
N 3700 -300 3900 -300 {}
N 3100 -360 3900 -360 {}
N -1080 330 -800 330 {}
N -800 330 -600 330 {}
N -600 330 600 330 {}
N 600 330 780 330 {}
N 780 330 1000 330 {}
N 1000 330 1180 330 {}
N 1180 330 2300 330 {}
N 2300 330 2480 330 {}
N 2480 330 2700 330 {}
N 2700 330 2880 330 {}
N -680 410 -600 410 {}
N -600 410 520 410 {}
N 520 410 920 410 {}
N 920 410 2220 410 {}
N 2220 410 2620 410 {}
N -660 520 -60 520 {}
N -60 520 1640 520 {}
N 1640 520 3340 520 {}
N -1300 520 -660 520 {}
N -840 -300 -880 -300 {}
N -880 -300 -880 -420 {}
N -880 -420 -1300 -420 {}
N -1300 -560 -240 -560 {}
N -240 -560 -240 0 {}
N -240 0 -140 0 {}
N -1300 640 240 640 {}
N 240 640 240 0 {}
N 240 0 140 0 {}
N -1300 900 -1240 900 {}
N -1300 960 -1240 960 {}
C {devices/iopin.sym} -1300 900 0 1 {name=p7
lab=VDD}
C {devices/iopin.sym} -1300 960 0 1 {name=p8
lab=VSS}
C {devices/ipin.sym} -1300 -560 0 0 {name=p3
lab=inp}
C {devices/ipin.sym} -1300 640 0 0 {name=p4
lab=inn}
C {devices/opin.sym} 3900 -300 0 0 {name=p5
lab=outp}
C {devices/opin.sym} 3900 -360 0 0 {name=p6
lab=outn}
C {devices/ipin.sym} -1300 520 0 0 {name=p1
lab=nb}
C {devices/ipin.sym} -1300 -420 0 0 {name=p2
lab=enb}
C {symbols/pfet_03v3.sym} -820 -300 0 0 {name=Mvbs
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
C {symbols/vdd.sym} -780 -300 0 0 {name=l1
lab=VDD}
C {symbols/vdd.sym} -800 -330 0 0 {name=l2
lab=VDD}
C {symbols/ppolyf_u_1k.sym} -800 -100 2 0 {name=Rvb1
W=1.0e-6
L=150.0e-6
model=ppolyf_u_1k
spiceprefix=X
m=1
val="1/150 (150k)"}
C {symbols/gnd.sym} -760 -100 0 0 {name=l3
lab=VSS}
C {symbols/ppolyf_u_1k.sym} -800 700 2 0 {name=Rvb2
W=1.0e-6
L=100.0e-6
model=ppolyf_u_1k
spiceprefix=X
m=1
val="1/100 (100k)"}
C {symbols/gnd.sym} -760 700 0 0 {name=l4
lab=VSS}
C {symbols/gnd.sym} -800 730 0 0 {name=l5
lab=VSS}
C {symbols/nfet_03v3.sym} -1020 200 0 0 {name=Cvb
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
C {symbols/gnd.sym} -980 230 0 0 {name=l6
lab=VSS}
C {symbols/pfet_03v3.sym} -620 230 2 1 {name=Mvbrep
L=1.0u
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
val="4/1"}
C {symbols/nfet_03v3.sym} -620 600 0 0 {name=Mvbsnk
L=49.99999999999999u
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
val="0.42/50"}
C {symbols/gnd.sym} -580 600 0 0 {name=l7
lab=VSS}
C {symbols/gnd.sym} -600 630 0 0 {name=l8
lab=VSS}
C {symbols/nfet_03v3.sym} -120 0 0 0 {name=M1a
L=1.0u
W=20.0u
nf=1
m=16
ad=10.0p
as=10.0p
pd=41.0u
ps=41.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="20/1 ×16"}
C {symbols/nfet_03v3.sym} 120 0 0 1 {name=M1b
L=1.0u
W=20.0u
nf=1
m=16
ad=10.0p
as=10.0p
pd=41.0u
ps=41.0u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="20/1 ×16"}
C {symbols/nfet_03v3.sym} 0 200 0 0 {name=Mt1
L=0.5u
W=2.0u
nf=1
m=8
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
val="2/0.5 ×8"}
C {symbols/ppolyf_u.sym} -100 -200 0 0 {name=R1a
W=2.0e-6
L=57.143e-6
model=ppolyf_u
spiceprefix=X
m=1
val="2/57.143 (10k)"}
C {symbols/ppolyf_u.sym} 100 -200 0 0 {name=R1b
W=2.0e-6
L=57.143e-6
model=ppolyf_u
spiceprefix=X
m=1
val="2/57.143 (10k)"}
C {symbols/gnd.sym} -80 0 0 0 {name=l9
lab=VSS}
C {symbols/gnd.sym} 80 0 0 0 {name=l10
lab=VSS}
C {symbols/gnd.sym} 40 200 0 0 {name=l11
lab=VSS}
C {symbols/gnd.sym} 20 230 0 0 {name=l12
lab=VSS}
C {symbols/vdd.sym} -100 -230 0 0 {name=l13
lab=VDD}
C {symbols/vdd.sym} 100 -230 0 0 {name=l14
lab=VDD}
C {symbols/gnd.sym} -140 -200 0 0 {name=l15
lab=VSS}
C {symbols/gnd.sym} 60 -200 0 0 {name=l16
lab=VSS}
C {symbols/pfet_03v3.sym} 500 -200 0 1 {name=Cc2a
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
model=pfet_03v3
spiceprefix=X
val="24.6/10"}
C {symbols/pfet_03v3.sym} 580 150 2 1 {name=Rp2ar
L=12.0u
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
val="0.42/12"}
C {symbols/pfet_03v3.sym} 760 90 0 0 {name=Rp2aa
L=1.0u
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
val="0.42/1"}
C {symbols/pfet_03v3.sym} 760 210 2 1 {name=Rp2ab
L=1.0u
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
val="0.42/1"}
C {symbols/pfet_03v3.sym} 900 -200 0 1 {name=Cc2b
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
model=pfet_03v3
spiceprefix=X
val="24.6/10"}
C {symbols/pfet_03v3.sym} 980 150 2 1 {name=Rp2br
L=12.0u
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
val="0.42/12"}
C {symbols/pfet_03v3.sym} 1160 90 0 0 {name=Rp2ba
L=1.0u
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
val="0.42/1"}
C {symbols/pfet_03v3.sym} 1160 210 2 1 {name=Rp2bb
L=1.0u
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
val="0.42/1"}
C {symbols/nfet_03v3.sym} 1580 0 0 0 {name=M2a
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
model=nfet_03v3
spiceprefix=X
val="4/1 ×2"}
C {symbols/nfet_03v3.sym} 1820 0 0 1 {name=M2b
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
model=nfet_03v3
spiceprefix=X
val="4/1 ×2"}
C {symbols/nfet_03v3.sym} 1700 200 0 0 {name=Mt2f
L=0.5u
W=0.3u
nf=1
m=1
ad=0.15p
as=0.15p
pd=1.6u
ps=1.6u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.3/0.5"}
C {symbols/ppolyf_u_1k.sym} 1600 -200 0 0 {name=R2a
W=1.0e-6
L=200.0e-6
model=ppolyf_u_1k
spiceprefix=X
m=1
val="1/200 (200k)"}
C {symbols/ppolyf_u_1k.sym} 1800 -200 0 0 {name=R2b
W=1.0e-6
L=200.0e-6
model=ppolyf_u_1k
spiceprefix=X
m=1
val="1/200 (200k)"}
C {symbols/gnd.sym} 1620 0 0 0 {name=l17
lab=VSS}
C {symbols/gnd.sym} 1780 0 0 0 {name=l18
lab=VSS}
C {symbols/gnd.sym} 1740 200 0 0 {name=l19
lab=VSS}
C {symbols/gnd.sym} 1720 230 0 0 {name=l20
lab=VSS}
C {symbols/vdd.sym} 1600 -230 0 0 {name=l21
lab=VDD}
C {symbols/vdd.sym} 1800 -230 0 0 {name=l22
lab=VDD}
C {symbols/gnd.sym} 1560 -200 0 0 {name=l23
lab=VSS}
C {symbols/gnd.sym} 1760 -200 0 0 {name=l24
lab=VSS}
C {symbols/nfet_03v3.sym} 1500 120 0 0 {name=C2a
L=10.0u
W=98.28009999999999u
nf=1
m=1
ad=49.140049999999995p
as=49.140049999999995p
pd=197.56019999999998u
ps=197.56019999999998u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="98.3/10"}
C {symbols/gnd.sym} 1540 150 0 0 {name=l25
lab=VSS}
C {symbols/nfet_03v3.sym} 2100 120 0 0 {name=C2b
L=10.0u
W=98.28009999999999u
nf=1
m=1
ad=49.140049999999995p
as=49.140049999999995p
pd=197.56019999999998u
ps=197.56019999999998u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="98.3/10"}
C {symbols/gnd.sym} 2140 150 0 0 {name=l26
lab=VSS}
C {symbols/pfet_03v3.sym} 2200 -200 0 1 {name=Cc3a
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
model=pfet_03v3
spiceprefix=X
val="24.6/10"}
C {symbols/pfet_03v3.sym} 2280 150 2 1 {name=Rp3ar
L=12.0u
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
val="0.42/12"}
C {symbols/pfet_03v3.sym} 2460 90 0 0 {name=Rp3aa
L=1.0u
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
val="0.42/1"}
C {symbols/pfet_03v3.sym} 2460 210 2 1 {name=Rp3ab
L=1.0u
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
val="0.42/1"}
C {symbols/pfet_03v3.sym} 2600 -200 0 1 {name=Cc3b
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
model=pfet_03v3
spiceprefix=X
val="24.6/10"}
C {symbols/pfet_03v3.sym} 2680 150 2 1 {name=Rp3br
L=12.0u
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
val="0.42/12"}
C {symbols/pfet_03v3.sym} 2860 90 0 0 {name=Rp3ba
L=1.0u
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
val="0.42/1"}
C {symbols/pfet_03v3.sym} 2860 210 2 1 {name=Rp3bb
L=1.0u
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
val="0.42/1"}
C {symbols/nfet_03v3.sym} 3280 0 0 0 {name=M3a
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
model=nfet_03v3
spiceprefix=X
val="4/1 ×2"}
C {symbols/nfet_03v3.sym} 3520 0 0 1 {name=M3b
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
model=nfet_03v3
spiceprefix=X
val="4/1 ×2"}
C {symbols/nfet_03v3.sym} 3400 200 0 0 {name=Mt3f
L=0.5u
W=0.7999999999999999u
nf=1
m=1
ad=0.39999999999999997p
as=0.39999999999999997p
pd=2.5999999999999996u
ps=2.5999999999999996u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="0.8/0.5"}
C {symbols/ppolyf_u_1k.sym} 3300 -200 0 0 {name=R3a
W=1.0e-6
L=200.0e-6
model=ppolyf_u_1k
spiceprefix=X
m=1
val="1/200 (200k)"}
C {symbols/ppolyf_u_1k.sym} 3500 -200 0 0 {name=R3b
W=1.0e-6
L=200.0e-6
model=ppolyf_u_1k
spiceprefix=X
m=1
val="1/200 (200k)"}
C {symbols/gnd.sym} 3320 0 0 0 {name=l27
lab=VSS}
C {symbols/gnd.sym} 3480 0 0 0 {name=l28
lab=VSS}
C {symbols/gnd.sym} 3440 200 0 0 {name=l29
lab=VSS}
C {symbols/gnd.sym} 3420 230 0 0 {name=l30
lab=VSS}
C {symbols/vdd.sym} 3300 -230 0 0 {name=l31
lab=VDD}
C {symbols/vdd.sym} 3500 -230 0 0 {name=l32
lab=VDD}
C {symbols/gnd.sym} 3260 -200 0 0 {name=l33
lab=VSS}
C {symbols/gnd.sym} 3460 -200 0 0 {name=l34
lab=VSS}
C {symbols/nfet_03v3.sym} 3200 120 0 0 {name=C3a
L=10.0u
W=98.28009999999999u
nf=1
m=1
ad=49.140049999999995p
as=49.140049999999995p
pd=197.56019999999998u
ps=197.56019999999998u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="98.3/10"}
C {symbols/gnd.sym} 3240 150 0 0 {name=l35
lab=VSS}
C {symbols/nfet_03v3.sym} 3800 120 0 0 {name=C3b
L=10.0u
W=98.28009999999999u
nf=1
m=1
ad=49.140049999999995p
as=49.140049999999995p
pd=197.56019999999998u
ps=197.56019999999998u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="98.3/10"}
C {symbols/gnd.sym} 3840 150 0 0 {name=l36
lab=VSS}
C {symbols/vdd.sym} -1240 900 0 0 {name=l37
lab=VDD}
C {symbols/gnd.sym} -1240 960 0 0 {name=l38
lab=VSS}
