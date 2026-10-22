SIM ?= verilator
TOPLEVEL_LANG ?= verilog

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VERILOG_SOURCES = $(REPO_ROOT)/rtl/common/uart_rx.sv
TOPLEVEL = uart_rx
MODULE = test_uart_rx
EXTRA_ARGS += -GCLKS_PER_BIT=16

include $(shell cocotb-config --makefiles)/Makefile.sim
