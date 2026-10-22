SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = $(REPO_ROOT)/rtl/common/uart_tx.sv
TOPLEVEL = uart_tx
MODULE = test_uart_tx
#small divider keeps the sim quick
EXTRA_ARGS += -GCLKS_PER_BIT=16

include $(shell cocotb-config --makefiles)/Makefile.sim
