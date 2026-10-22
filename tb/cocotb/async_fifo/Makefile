SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = $(REPO_ROOT)/rtl/common/cdc_sync.sv $(REPO_ROOT)/rtl/common/async_fifo.sv
TOPLEVEL = async_fifo
MODULE = test_async_fifo
EXTRA_ARGS += -GWIDTH=16 -GDEPTH=8 --timing

include $(shell cocotb-config --makefiles)/Makefile.sim
