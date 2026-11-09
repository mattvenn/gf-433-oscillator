v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {board, bond wire} 90 -60 0 0 0.3 0.3 {}
T {asig_5p0 pad} 320 -140 0 0 0.3 0.3 {}
T {route 15-60 ohm} 560 -60 0 0 0.3 0.3 {}
T {this project (on)} 800 -140 0 0 0.3 0.3 {}
T {n_off other projects on this pin (off)} 980 300 0 0 0.3 0.3 {}
T {internal supplies (vsup)} 60 360 0 0 0.3 0.3 {}
T {pad_model_gf180: one Tiny Tapeout GF180 analog pin, board pin to ua[] (docs/pad_model.md)} 0 -400 0 0 0.7 0.7 {}
T {Cpcb / R1 / L1 / Cmod from tnt's sky130 pad_model; ESD diodes from the PDK asig_5p0 netlist;} 0 -340 0 0 0.42 0.42 {}
T {Cpad 1.29 pF extracted from the asig_5p0 GDS; Croute assumed; n_off 0..3 on ttgf0p3 (default 3)} 0 -306 0 0 0.42 0.42 {}
N 0 0 60 0 {}
N 60 0 120 0 {}
N 180 0 220 0 {}
N 280 0 360 0 {}
N 360 0 440 0 {}
N 440 0 520 0 {}
N 520 0 570 0 {}
N 630 0 680 0 {}
N 680 0 720 0 {}
N 1000 0 1020 0 {}
N 1020 0 1100 0 {}
N 720 0 720 220 {}
N 770 -50 770 -80 {}
N 850 -50 850 -80 {}
N 930 -50 930 -80 {}
N 770 50 770 80 {}
N 770 170 770 140 {}
N 850 170 850 140 {}
N 930 170 930 140 {}
N 770 270 770 300 {}
N 0 420 60 420 {}
C {devices/iopin.sym} 0 420 0 1 {name=p3
lab=VGND}
C {devices/iopin.sym} 0 0 0 1 {name=p1
lab=pin}
C {devices/iopin.sym} 1100 0 0 0 {name=p2
lab=mod}
C {devices/capa.sym} 60 30 0 0 {name=Cpcb
value=2p}
C {devices/res.sym} 150 0 1 0 {name=R1
value=1}
C {devices/ind.sym} 250 0 1 0 {name=L1
value=1n}
C {symbols/diode_pd2nw_06v0.sym} 360 -30 2 0 {name=Dp
model=diode_pd2nw_06v0
r_w=50e-6
r_l=3e-6
m=4}
C {symbols/diode_nd2ps_06v0.sym} 360 30 2 0 {name=Dn
model=diode_nd2ps_06v0
r_w=50e-6
r_l=3e-6
m=4}
C {devices/capa.sym} 440 30 0 0 {name=Cpad
value=1.29p}
C {devices/capa.sym} 520 30 0 0 {name=Cr1
value='croute/2'}
C {devices/res.sym} 600 0 1 0 {name=Rr
value='rroute'}
C {devices/capa.sym} 680 30 0 0 {name=Cr2
value='croute/2'}
C {tt_asw_5v0.sym} 860 0 0 0 {name=Xon
mult=1}
C {devices/capa.sym} 1020 30 0 0 {name=Cmod
value=250f}
C {tt_asw_5v0.sym} 860 220 0 0 {name=Xoff
mult='max(n_off,1e-6)'}
C {symbols/gnd.sym} 60 60 0 0 {name=l1
lab=VGND}
C {symbols/gnd.sym} 440 60 0 0 {name=l2
lab=VGND}
C {symbols/gnd.sym} 520 60 0 0 {name=l3
lab=VGND}
C {symbols/gnd.sym} 680 60 0 0 {name=l4
lab=VGND}
C {symbols/gnd.sym} 1020 60 0 0 {name=l5
lab=VGND}
C {symbols/gnd.sym} 360 60 0 0 {name=l6
lab=VGND}
C {symbols/vdd.sym} 360 -60 0 0 {name=l7
lab=VDDIO}
C {symbols/vdd.sym} 770 -80 0 0 {name=l8
lab=VDPWR}
C {symbols/vdd.sym} 850 -80 0 0 {name=l9
lab=VAPWR}
C {symbols/vdd.sym} 930 -80 0 0 {name=l10
lab=VDPWR}
C {symbols/gnd.sym} 770 80 0 0 {name=l11
lab=VGND}
C {symbols/vdd.sym} 770 140 0 0 {name=l12
lab=VDPWR}
C {symbols/vdd.sym} 850 140 0 0 {name=l13
lab=VAPWR}
C {symbols/gnd.sym} 930 140 0 0 {name=l14
lab=VGND}
C {symbols/gnd.sym} 770 300 0 0 {name=l15
lab=VGND}
C {devices/vsource.sym} 100 300 0 0 {name=VVDDIO
value='vsup'}
C {symbols/vdd.sym} 100 270 0 0 {name=l16
lab=VDDIO}
C {symbols/gnd.sym} 100 330 0 0 {name=l17
lab=VGND}
C {devices/vsource.sym} 220 300 0 0 {name=VVAPWR
value='vsup'}
C {symbols/vdd.sym} 220 270 0 0 {name=l18
lab=VAPWR}
C {symbols/gnd.sym} 220 330 0 0 {name=l19
lab=VGND}
C {devices/vsource.sym} 340 300 0 0 {name=VVDPWR
value='vsup'}
C {symbols/vdd.sym} 340 270 0 0 {name=l20
lab=VDPWR}
C {symbols/gnd.sym} 340 330 0 0 {name=l21
lab=VGND}
C {symbols/gnd.sym} 60 420 0 0 {name=l22
lab=VGND}
