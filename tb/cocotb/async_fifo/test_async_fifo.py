"""async fifo order and completeness across unrelated clocks"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def run(dut, w_period, r_period, n):
    cocotb.start_soon(Clock(dut.wclk, w_period, unit="ns").start())
    cocotb.start_soon(Clock(dut.rclk, r_period, unit="ns").start())
    dut.wrst.value = 1
    dut.rrst.value = 1
    dut.wvalid_i.value = 0
    dut.wdata_i.value = 0
    dut.rready_i.value = 0
    await Timer(10 * max(w_period, r_period), unit="ns")
    await RisingEdge(dut.wclk)
    dut.wrst.value = 0
    dut.rrst.value = 0
    await Timer(5 * max(w_period, r_period), unit="ns")

    rng = random.Random(3)
    recv = []

    async def writer():
        v = 0
        while v < n:
            if rng.random() < 0.7:
                dut.wvalid_i.value = 1
                dut.wdata_i.value = v
                await RisingEdge(dut.wclk)
                while not dut.wready_o.value:
                    await RisingEdge(dut.wclk)
                v += 1
                dut.wvalid_i.value = 0
            else:
                dut.wvalid_i.value = 0
                await RisingEdge(dut.wclk)

    async def reader():
        while len(recv) < n:
            dut.rready_i.value = 1 if rng.random() < 0.7 else 0
            await RisingEdge(dut.rclk)
            if dut.rvalid_o.value and dut.rready_i.value:
                recv.append(int(dut.rdata_o.value))
        dut.rready_i.value = 0

    w = cocotb.start_soon(writer())
    r = cocotb.start_soon(reader())
    await r
    w.kill()
    assert recv == list(range(n)), "data lost or reordered"


@cocotb.test()
async def test_fast_write_slow_read(dut):
    await run(dut, w_period=7, r_period=23, n=200)


@cocotb.test()
async def test_slow_write_fast_read(dut):
    await run(dut, w_period=23, r_period=7, n=200)
