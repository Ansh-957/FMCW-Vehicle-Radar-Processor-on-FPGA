SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = $(REPO_ROOT)/rtl/common/cdc_sync.sv
TOPLEVEL = cdc_sync
MODULE = test_cdc_sync
EXTRA_ARGS += -GWIDTH=4

include $(shell cocotb-config --makefiles)/Makefile.sim
