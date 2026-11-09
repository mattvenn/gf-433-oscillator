v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {DC supply decap ~4.9 pF} -160 660 0 0 0.3 0.3 {}
T {tx_drv: dipole TX driver (out_p, out_n in antiphase)} -400 -560 0 0 0.7 0.7 {}
T {ls (lsdiv's level-shifter output, 0-3.3 V) -> splitter -> two arms; en_p / en_n gate each arm (both low: both outputs low); one arm alone is the monopole fallback} -400 -500 0 0 0.42 0.42 {}
T {VDD is the driver's own supply (VDPWR stripe and decap), separate from the ring's; source: sim/tx/tx_drv.py block()} -400 -466 0 0 0.42 0.42 {}
N -400 -20 -100 -20 {}
N 100 -20 250 -20 {}
N 250 -20 250 -270 {}
N 250 -270 400 -270 {}
N -400 -430 200 -430 {}
N 200 -430 200 -230 {}
N 200 -230 400 -230 {}
N 600 -270 900 -270 {}
N 100 20 300 20 {}
N 300 20 300 230 {}
N 300 230 400 230 {}
N -400 470 200 470 {}
N 200 470 200 270 {}
N 200 270 400 270 {}
N 600 230 900 230 {}
N -180 570 -160 570 {}
N -180 600 -160 600 {}
N -160 570 -160 600 {}
N -160 600 -160 630 {}
N -180 630 -160 630 {}
N -220 600 -260 600 {}
N -400 800 -340 800 {}
N -400 860 -340 860 {}
C {devices/iopin.sym} -400 800 0 1 {name=p6
lab=VDD}
C {devices/iopin.sym} -400 860 0 1 {name=p7
lab=VSS}
C {devices/ipin.sym} -400 -20 0 0 {name=p1
lab=ls}
C {devices/ipin.sym} -400 -430 0 0 {name=p2
lab=en_p}
C {devices/ipin.sym} -400 470 0 0 {name=p4
lab=en_n}
C {devices/opin.sym} 900 -270 0 0 {name=p3
lab=out_p}
C {devices/opin.sym} 900 230 0 0 {name=p5
lab=out_n}
C {tx_split.sym} 0 0 0 0 {name=xsp}
C {tx_arm.sym} 500 -250 0 0 {name=xap}
C {tx_arm.sym} 500 250 0 0 {name=xan}
C {symbols/vdd.sym} -50 -70 0 0 {name=l1
lab=VDD}
C {symbols/gnd.sym} -50 70 0 0 {name=l2
lab=VSS}
C {symbols/vdd.sym} 450 -320 0 0 {name=l3
lab=VDD}
C {symbols/gnd.sym} 450 -180 0 0 {name=l4
lab=VSS}
C {symbols/vdd.sym} 450 180 0 0 {name=l5
lab=VDD}
C {symbols/gnd.sym} 450 320 0 0 {name=l6
lab=VSS}
C {symbols/nfet_03v3.sym} -200 600 0 0 {name=DC
L=10.0u
W=10.0u
nf=1
m=12
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
val="10/10 ×12"}
C {symbols/gnd.sym} -160 630 0 0 {name=l7
lab=VSS}
C {symbols/vdd.sym} -260 600 0 0 {name=l8
lab=VDD}
C {symbols/vdd.sym} -340 800 0 0 {name=l9
lab=VDD}
C {symbols/gnd.sym} -340 860 0 0 {name=l10
lab=VSS}
