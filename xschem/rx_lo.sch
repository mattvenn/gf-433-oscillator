v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {rx_lo: I and Q LOs for the mixers} -500 -560 0 0 0.7 0.7 {}
T {I: lsdiv's ls (from a0, shared with the TX) -> rx_lobuf; Q: rx_lsq on aq (ring a2: +72 deg) -> rx_lobuf} -500 -500 0 0 0.42 0.42 {}
T {qenb: low keeps the Q tap copy on (rx_top ties it to VSS); source: sim/rx/rx_lo.py block()} -500 -466 0 0 0.42 0.42 {}
N -500 -120 600 -120 {}
N -500 380 100 380 {}
N -500 420 100 420 {}
N 300 380 500 380 {}
N 500 380 600 380 {}
N -500 -300 560 -300 {}
N 560 -300 560 -80 {}
N 560 -80 560 420 {}
N 560 -80 600 -80 {}
N 560 420 600 420 {}
N 800 -120 1300 -120 {}
N 800 -80 1300 -80 {}
N 800 380 1300 380 {}
N 800 420 1300 420 {}
N -500 760 -440 760 {}
N -500 820 -440 820 {}
C {devices/iopin.sym} -500 760 0 1 {name=p9
lab=VDD}
C {devices/iopin.sym} -500 820 0 1 {name=p10
lab=VSS}
C {devices/ipin.sym} -500 -120 0 0 {name=p1
lab=ls}
C {devices/ipin.sym} -500 380 0 0 {name=p2
lab=aq}
C {devices/ipin.sym} -500 -300 0 0 {name=p4
lab=en}
C {devices/ipin.sym} -500 420 0 0 {name=p3
lab=qenb}
C {devices/opin.sym} 1300 -120 0 0 {name=p5
lab=lo_i}
C {devices/opin.sym} 1300 -80 0 0 {name=p6
lab=lob_i}
C {devices/opin.sym} 1300 380 0 0 {name=p7
lab=lo_q}
C {devices/opin.sym} 1300 420 0 0 {name=p8
lab=lob_q}
C {rx_lsq.sym} 200 400 0 0 {name=xlq}
C {rx_lobuf.sym} 700 -100 0 0 {name=xbi}
C {rx_lobuf.sym} 700 400 0 0 {name=xbq}
C {symbols/vdd.sym} 150 330 0 0 {name=l1
lab=VDD}
C {symbols/gnd.sym} 150 470 0 0 {name=l2
lab=VSS}
C {symbols/vdd.sym} 650 -170 0 0 {name=l3
lab=VDD}
C {symbols/gnd.sym} 650 -30 0 0 {name=l4
lab=VSS}
C {symbols/vdd.sym} 650 330 0 0 {name=l5
lab=VDD}
C {symbols/gnd.sym} 650 470 0 0 {name=l6
lab=VSS}
C {symbols/vdd.sym} -440 760 0 0 {name=l7
lab=VDD}
C {symbols/gnd.sym} -440 820 0 0 {name=l8
lab=VSS}
