SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = $(REPO_ROOT)/rtl/common/rom.sv
TOPLEVEL = rom
MODULE = test_rom
#load the real doppler window table
EXTRA_ARGS += -GWIDTH=16 -GDEPTH=64 -GINIT_FILE='"$(REPO_ROOT)/rtl/mem/hann64.mem"'

include $(shell cocotb-config --makefiles)/Makefile.sim
