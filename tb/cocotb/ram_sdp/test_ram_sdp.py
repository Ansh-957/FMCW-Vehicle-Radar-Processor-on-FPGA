"""ram_sdp write then read, plus simultaneous ports"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.we_i.value = 0
    dut.re_i.value = 0
    dut.waddr_i.value = 0
    dut.raddr_i.value = 0
    dut.wdata_i.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_write_then_read_all(dut):
    await start(dut)
    model = {}
    rng = random.Random(0)
    for a in range(256):
        v = rng.randrange(1 << 16)
        model[a] = v
        dut.we_i.value = 1
        dut.waddr_i.value = a
        dut.wdata_i.value = v
        await RisingEdge(dut.clk)
    dut.we_i.value = 0
    for a in range(256):
        dut.re_i.value = 1
        dut.raddr_i.value = a
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        dut.re_i.value = 0
        assert dut.rdata_o.value == model[a], f"addr {a}"


@cocotb.test()
async def test_simultaneous_ports(dut):
    await start(dut)
    #preload
    for a in range(16):
        dut.we_i.value = 1
        dut.waddr_i.value = a
        dut.wdata_i.value = a + 100
        await RisingEdge(dut.clk)
    #write addr a while reading addr a-1
    for a in range(1, 16):
        dut.we_i.value = 1
        dut.waddr_i.value = a
        dut.wdata_i.value = a + 200
        dut.re_i.value = 1
        dut.raddr_i.value = a - 1
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        dut.we_i.value = 0
        dut.re_i.value = 0
        expect = (a - 1) + (200 if a - 1 >= 1 else 100)
        assert dut.rdata_o.value == expect
