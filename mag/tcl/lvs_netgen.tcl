set layout [readnet spice $project.lvs.spice]
set source [readnet spice /dev/null]
readnet spice $::env(PDK_ROOT)/$::env(PDK)/libs.ref/gf180mcu_fd_sc_mcu7t5v0/spice/gf180mcu_fd_sc_mcu7t5v0.spice $source

# top level GL verilog
readnet verilog ../src/project.v $source

# add an GL verilog of any digital blocks:
readnet verilog ../verilog/gl/r2r_dac_control.pnl.v $source

# add any spice files of your analog blocks:
readnet spice ../xschem/simulation/r2r.spice $source

lvs "$layout $project" "$source $project" $::env(PDK_ROOT)/$::env(PDK)/libs.tech/netgen/$::env(PDK)_setup.tcl lvs.report -blackbox
