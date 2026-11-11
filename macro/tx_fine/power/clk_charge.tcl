# Per-instance power of the hardened tx_fine with every clock running and all data static (clk_charge.py).
#   RUN=<run dir> OUT=<file> sta -no_init -exit clk_charge.tcl
set run $::env(RUN)
read_liberty $::env(PDK_ROOT)/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__tt_025C_3v30.lib
read_verilog $run/final/nl/tx_fine.nl.v
link_design tx_fine
read_spef $run/final/spef/nom/tx_fine.nom.spef
create_clock -name clk -period 40 [get_ports clk]
set_power_activity -global -activity 0
set_power_activity -input -activity 0
report_power -instances [get_cells *] -digits 6 > $::env(OUT)
report_power
