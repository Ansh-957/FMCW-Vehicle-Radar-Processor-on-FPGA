"""cdc_sync propagates a stable value in exactly two clocks"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_two_clock_latency(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.d_i.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    for v in (0x5, 0xA, 0xF, 0x0):
        dut.d_i.value = v
        await RisingEdge(dut.clk)  #into meta
        await RisingEdge(dut.clk)  #into q
        await RisingEdge(dut.clk)  #settle for reading
        assert dut.q_o.value == v
