SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = \
	$(REPO_ROOT)/rtl/pkg/radar_pkg.sv \
	$(REPO_ROOT)/rtl/common/rom.sv \
	$(REPO_ROOT)/rtl/dsp/window_mult.sv
TOPLEVEL = window_mult
MODULE = test_window_mult
#range instance: s13 in, shift 13, 256 tap hann
EXTRA_ARGS += -GN=256 -GW_IN=13 -GSHIFT=13 \
	-GINIT_FILE='"$(REPO_ROOT)/rtl/mem/hann256.mem"'

include $(shell cocotb-config --makefiles)/Makefile.sim
