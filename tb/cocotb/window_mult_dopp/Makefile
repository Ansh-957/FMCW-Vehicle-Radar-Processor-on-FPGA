SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = \
	$(REPO_ROOT)/rtl/pkg/radar_pkg.sv \
	$(REPO_ROOT)/rtl/common/rom.sv \
	$(REPO_ROOT)/rtl/dsp/window_mult.sv
TOPLEVEL = window_mult
MODULE = test_window_mult_dopp
EXTRA_ARGS += -GN=64 -GW_IN=16 -GSHIFT=16 \
	-GINIT_FILE='"$(REPO_ROOT)/rtl/mem/hann64.mem"'

include $(shell cocotb-config --makefiles)/Makefile.sim
