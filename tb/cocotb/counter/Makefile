#cocotb and verilator makefile for the counter smoke test
SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = $(REPO_ROOT)/rtl/common/counter.sv
TOPLEVEL = counter
COCOTB_TEST_MODULES = test_counter
EXTRA_ARGS += --trace --trace-structs

include $(shell cocotb-config --makefiles)/Makefile.sim
