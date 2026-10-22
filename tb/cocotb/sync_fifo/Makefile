SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = $(REPO_ROOT)/rtl/common/sync_fifo.sv
TOPLEVEL = sync_fifo
MODULE = test_sync_fifo
EXTRA_ARGS += -GWIDTH=16 -GDEPTH=8

include $(shell cocotb-config --makefiles)/Makefile.sim
