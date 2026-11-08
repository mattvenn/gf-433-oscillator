v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {vco_cfed: current-fed ring VCO, GF180MCU} -100 -520 0 0 0.7 0.7 {}
T {cgm_ref -> vbnf -> ring_core_v3; code = bit[4:0] (coarse) + vctrl (fine); out a0..a4} -100 -460 0 0 0.42 0.42 {}
T {source of truth: sim/vco/vco_bias.py netlist(), chosen design (xschem/gen/common.py)} -100 -426 0 0 0.42 0.42 {}
N -100 -220 480 -220 {}
N -100 -180 480 -180 {}
N -100 -140 480 -140 {}
N -100 -100 480 -100 {}
N -100 -60 480 -60 {}
N -100 -20 480 -20 {}
N -100 20 480 20 {}
N -100 60 480 60 {}
N -100 100 480 100 {}
N -100 140 480 140 {}
N -100 180 480 180 {}
N 720 -220 900 -220 {}
N 720 -180 900 -180 {}
N 720 -140 900 -140 {}
N 720 -100 900 -100 {}
N 720 -60 900 -60 {}
N 720 -20 900 -20 {}
N 300 380 380 380 {}
N 380 380 380 220 {}
N 380 220 480 220 {}
N 380 380 380 540 {}
N 380 540 900 540 {}
N 300 420 320 420 {}
N 320 420 320 580 {}
N 320 580 900 580 {}
N -100 640 -40 640 {}
N -100 700 -40 700 {}
C {devices/iopin.sym} -100 640 0 1 {name=p20
lab=VDD}
C {devices/iopin.sym} -100 700 0 1 {name=p21
lab=VSS}
C {devices/ipin.sym} -100 180 0 0 {name=p11
lab=vctrl}
C {devices/ipin.sym} -100 100 0 0 {name=p9
lab=bit0}
C {devices/ipin.sym} -100 20 0 0 {name=p7
lab=bit1}
C {devices/ipin.sym} -100 -60 0 0 {name=p5
lab=bit2}
C {devices/ipin.sym} -100 -140 0 0 {name=p3
lab=bit3}
C {devices/ipin.sym} -100 -220 0 0 {name=p1
lab=bit4}
C {devices/ipin.sym} -100 140 0 0 {name=p10
lab=bitb0}
C {devices/ipin.sym} -100 60 0 0 {name=p8
lab=bitb1}
C {devices/ipin.sym} -100 -20 0 0 {name=p6
lab=bitb2}
C {devices/ipin.sym} -100 -100 0 0 {name=p4
lab=bitb3}
C {devices/ipin.sym} -100 -180 0 0 {name=p2
lab=bitb4}
C {devices/opin.sym} 900 -220 0 0 {name=p12
lab=a0}
C {devices/opin.sym} 900 -180 0 0 {name=p13
lab=a1}
C {devices/opin.sym} 900 -140 0 0 {name=p14
lab=a2}
C {devices/opin.sym} 900 -100 0 0 {name=p15
lab=a3}
C {devices/opin.sym} 900 -60 0 0 {name=p16
lab=a4}
C {devices/iopin.sym} 900 -20 0 0 {name=p17
lab=vg}
C {devices/opin.sym} 900 580 0 0 {name=p19
lab=vbn}
C {devices/opin.sym} 900 540 0 0 {name=p18
lab=vbnf}
C {ring_core_v3.sym} 600 0 0 0 {name=xcore}
C {cgm_ref.sym} 200 400 0 0 {name=xref}
C {symbols/vdd.sym} 530 -270 0 0 {name=l1
lab=VDD}
C {symbols/gnd.sym} 530 270 0 0 {name=l2
lab=VSS}
C {symbols/vdd.sym} 150 330 0 0 {name=l3
lab=VDD}
C {symbols/gnd.sym} 150 470 0 0 {name=l4
lab=VSS}
C {symbols/vdd.sym} -40 640 0 0 {name=l5
lab=VDD}
C {symbols/gnd.sym} -40 700 0 0 {name=l6
lab=VSS}
