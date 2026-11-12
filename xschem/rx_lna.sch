v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {vcm} -800 450 0 0 0.3 0.3 {}
T {outp} 380 -390 0 0 0.3 0.3 {}
T {outn} 380 -450 0 0 0.3 0.3 {}
T {rx_lna: two-stage LNA, one stage-2 per mixer} -900 -900 0 0 0.7 0.7 {}
T {stage 1: NMOS pair 10/0.28 ×24 um (the OOK amp_dp, ported), loads 9.143 um ppolyf_u, tail 2/0.5 ×120; the pins sit at vcm (~1.37 V) through Rgp / Rgn} -900 -840 0 0 0.42 0.42 {}
T {stage 2 (x2i, x2q) gives each mixer its own driver: no I/Q cross-loading; source: sim/rx/rx_lna.py block()} -900 -806 0 0 0.42 0.42 {}
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
N -900 0 -300 0 {}
N -300 0 -140 0 {}
N -300 0 -300 120 {}
N -300 180 -300 480 {}
N -280 150 -260 150 {}
N -900 620 240 620 {}
N 240 0 140 0 {}
N 240 60 300 60 {}
N 300 60 300 120 {}
N 300 180 300 480 {}
N 320 150 340 150 {}
N 240 0 240 60 {}
N 240 60 240 620 {}
N -600 120 -580 120 {}
N -900 120 -640 120 {}
N -600 150 -600 270 {}
N -580 300 -560 300 {}
N -580 660 -560 660 {}
N -600 330 -600 480 {}
N -600 480 -600 630 {}
N -780 600 -820 600 {}
N -820 600 -820 480 {}
N -740 570 -720 570 {}
N -740 600 -720 600 {}
N -720 570 -720 600 {}
N -720 600 -720 630 {}
N -740 630 -720 630 {}
N -820 480 -600 480 {}
N -600 480 -300 480 {}
N -300 480 300 480 {}
N -900 280 -120 280 {}
N -120 280 -120 200 {}
N -120 200 -20 200 {}
N -100 -100 -260 -100 {}
N -260 -100 -260 -420 {}
N -260 -420 660 -420 {}
N 100 -100 360 -100 {}
N 360 -100 360 -360 {}
N 360 -360 600 -360 {}
N 600 -360 600 -190 {}
N 600 -190 600 310 {}
N 600 -190 800 -190 {}
N 600 310 800 310 {}
N 660 -420 660 -150 {}
N 660 -150 660 350 {}
N 660 -150 800 -150 {}
N 660 350 800 350 {}
N 1000 -190 1500 -190 {}
N 1000 -150 1500 -150 {}
N 800 -110 720 -110 {}
N 1000 310 1500 310 {}
N 1000 350 1500 350 {}
N 800 390 720 390 {}
N 720 -110 720 390 {}
N 720 390 720 820 {}
N 720 820 -120 820 {}
N -120 820 -120 280 {}
N -900 900 -840 900 {}
N -900 960 -840 960 {}
C {devices/iopin.sym} -900 900 0 1 {name=p9
lab=VDD}
C {devices/iopin.sym} -900 960 0 1 {name=p10
lab=VSS}
C {devices/ipin.sym} -900 0 0 0 {name=p1
lab=inp}
C {devices/ipin.sym} -900 620 0 0 {name=p2
lab=inn}
C {devices/opin.sym} 1500 -190 0 0 {name=p5
lab=oip}
C {devices/opin.sym} 1500 -150 0 0 {name=p6
lab=oin}
C {devices/opin.sym} 1500 310 0 0 {name=p7
lab=oqp}
C {devices/opin.sym} 1500 350 0 0 {name=p8
lab=oqn}
C {devices/ipin.sym} -900 280 0 0 {name=p4
lab=nb}
C {devices/ipin.sym} -900 120 0 0 {name=p3
lab=enb}
C {symbols/nfet_03v3.sym} -120 0 0 0 {name=M1
L=0.28u
W=10.0u
nf=1
m=24
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
val="10/0.28 ×24"}
C {symbols/nfet_03v3.sym} 120 0 0 1 {name=M2
L=0.28u
W=10.0u
nf=1
m=24
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
val="10/0.28 ×24"}
C {symbols/nfet_03v3.sym} 0 200 0 0 {name=Mt
L=0.5u
W=2.0u
nf=1
m=120
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
val="2/0.5 ×120"}
C {symbols/ppolyf_u.sym} -100 -200 0 0 {name=RLp
W=4.0e-6
L=9.143e-6
model=ppolyf_u
spiceprefix=X
m=1
val="4/9.143 (800)"}
C {symbols/ppolyf_u.sym} 100 -200 0 0 {name=RLn
W=4.0e-6
L=9.143e-6
model=ppolyf_u
spiceprefix=X
m=1
val="4/9.143 (800)"}
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
C {symbols/ppolyf_u_1k.sym} -300 150 2 0 {name=Rgp
W=1.0e-6
L=20.0e-6
model=ppolyf_u_1k
spiceprefix=X
m=1
val="1/20 (20k)"}
C {symbols/gnd.sym} -260 150 0 0 {name=l9
lab=VSS}
C {symbols/ppolyf_u_1k.sym} 300 150 2 0 {name=Rgn
W=1.0e-6
L=20.0e-6
model=ppolyf_u_1k
spiceprefix=X
m=1
val="1/20 (20k)"}
C {symbols/gnd.sym} 340 150 0 0 {name=l10
lab=VSS}
C {symbols/pfet_03v3.sym} -620 120 0 0 {name=Mvs
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
model=pfet_03v3
spiceprefix=X
val="2/0.28"}
C {symbols/vdd.sym} -580 120 0 0 {name=l11
lab=VDD}
C {symbols/vdd.sym} -600 90 0 0 {name=l12
lab=VDD}
C {symbols/ppolyf_u_1k.sym} -600 300 2 0 {name=Rv1
W=1.0e-6
L=40.0e-6
model=ppolyf_u_1k
spiceprefix=X
m=1
val="1/40 (40k)"}
C {symbols/ppolyf_u_1k.sym} -600 660 2 0 {name=Rv2
W=1.0e-6
L=30.0e-6
model=ppolyf_u_1k
spiceprefix=X
m=1
val="1/30 (30k)"}
C {symbols/gnd.sym} -600 690 0 0 {name=l13
lab=VSS}
C {symbols/gnd.sym} -560 300 0 0 {name=l14
lab=VSS}
C {symbols/gnd.sym} -560 660 0 0 {name=l15
lab=VSS}
C {symbols/nfet_03v3.sym} -760 600 0 0 {name=Cvcm
L=10.0u
W=49.14u
nf=1
m=1
ad=24.57p
as=24.57p
pd=99.28u
ps=99.28u
nrd=0
nrs=0
sa=0
sb=0
sd=0
model=nfet_03v3
spiceprefix=X
val="49.1/10"}
C {symbols/gnd.sym} -720 630 0 0 {name=l16
lab=VSS}
C {rx_lna2.sym} 900 -150 0 0 {name=x2i}
C {rx_lna2.sym} 900 350 0 0 {name=x2q}
C {symbols/vdd.sym} 850 -240 0 0 {name=l17
lab=VDD}
C {symbols/gnd.sym} 850 -60 0 0 {name=l18
lab=VSS}
C {symbols/vdd.sym} 850 260 0 0 {name=l19
lab=VDD}
C {symbols/gnd.sym} 850 440 0 0 {name=l20
lab=VSS}
C {symbols/vdd.sym} -840 900 0 0 {name=l21
lab=VDD}
C {symbols/gnd.sym} -840 960 0 0 {name=l22
lab=VSS}
