SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = $(REPO_ROOT)/rtl/common/pulse_sync.sv
TOPLEVEL = pulse_sync
MODULE = test_pulse_sync

include $(shell cocotb-config --makefiles)/Makefile.sim
