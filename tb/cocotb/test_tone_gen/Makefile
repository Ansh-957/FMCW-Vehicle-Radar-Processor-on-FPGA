SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = \
	$(REPO_ROOT)/rtl/pkg/radar_pkg.sv \
	$(REPO_ROOT)/rtl/common/rom.sv \
	$(REPO_ROOT)/rtl/frontend/test_tone_gen.sv
TOPLEVEL = test_tone_gen
MODULE = test_test_tone_gen
EXTRA_ARGS += -GINIT_FILE='"$(REPO_ROOT)/rtl/mem/nco256.mem"'

include $(shell cocotb-config --makefiles)/Makefile.sim
