SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = $(REPO_ROOT)/rtl/common/ram_sdp.sv
TOPLEVEL = ram_sdp
MODULE = test_ram_sdp

include $(shell cocotb-config --makefiles)/Makefile.sim
