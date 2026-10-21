"""cocotb smoke test for the counter"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles


async def reset(dut):
    dut.rst.value = 1
    dut.en_i.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    assert dut.count_o.value == 0


@cocotb.test()
async def test_counts_when_enabled(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    dut.en_i.value = 1
    await ClockCycles(dut.clk, 10)
    await RisingEdge(dut.clk)
    assert dut.count_o.value == 10


@cocotb.test()
async def test_holds_when_disabled(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    dut.en_i.value = 1
    await ClockCycles(dut.clk, 5)
    dut.en_i.value = 0
    await ClockCycles(dut.clk, 7)
    assert dut.count_o.value == 5


@cocotb.test()
async def test_wraps(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    dut.en_i.value = 1
    await ClockCycles(dut.clk, 256)
    await RisingEdge(dut.clk)
    assert dut.count_o.value == 0
