SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = \
	$(REPO_ROOT)/rtl/pkg/radar_pkg.sv \
	$(REPO_ROOT)/rtl/common/ram_sdp.sv \
	$(REPO_ROOT)/rtl/dsp/dc_remove.sv
TOPLEVEL = dc_remove
MODULE = test_dc_remove

include $(shell cocotb-config --makefiles)/Makefile.sim
