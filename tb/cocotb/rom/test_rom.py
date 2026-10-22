"""rom contents must match the .mem file the model loads"""

import os
import sys

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", ".."))

from model.fixed import roms  #noqa: E402


@cocotb.test()
async def test_rom_matches_mem_file(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    ref = roms.hann(64)
    await RisingEdge(dut.clk)
    for a in range(64):
        dut.addr_i.value = a
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        assert dut.data_o.value == int(ref[a]), f"addr {a}"
