SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = $(REPO_ROOT)/rtl/common/skid_buffer.sv
TOPLEVEL = skid_buffer
MODULE = test_skid_buffer

include $(shell cocotb-config --makefiles)/Makefile.sim
