# cocotb tests of the tx_fine digital macro (src/tx_fine.v): make  (RTL)  |  make GL=1  (hardened netlist)
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src
ifneq ($(GL),)
PDK_ROOT ?= /foss/pdks
SCL = $(PDK_ROOT)/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog
COMPILE_ARGS += -DFUNCTIONAL -DUNIT_DELAY=\#1 -DGL
VERILOG_SOURCES += $(SCL)/primitives.v $(SCL)/gf180mcu_fd_sc_mcu7t5v0.v $(PWD)/../macro/tx_fine/tx_fine.nl.v
else
VERILOG_SOURCES += $(SRC_DIR)/tx_fine.v
endif
TOPLEVEL = tx_fine
COCOTB_TEST_MODULES = test_tx_fine
include $(shell cocotb-config --makefiles)/Makefile.sim
