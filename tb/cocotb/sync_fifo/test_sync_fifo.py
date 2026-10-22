"""sync fifo fill, drain, flags and random traffic against a deque"""

import random
from collections import deque

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge

DEPTH = 8


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.wvalid_i.value = 0
    dut.wdata_i.value = 0
    dut.rready_i.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_fill_and_drain(dut):
    await start(dut)
    for v in range(DEPTH):
        assert dut.wready_o.value == 1
        dut.wvalid_i.value = 1
        dut.wdata_i.value = v
        await RisingEdge(dut.clk)
    dut.wvalid_i.value = 0
    await RisingEdge(dut.clk)
    assert dut.wready_o.value == 0  #full
    for v in range(DEPTH):
        assert dut.rvalid_o.value == 1
        assert dut.rdata_o.value == v
        dut.rready_i.value = 1
        await RisingEdge(dut.clk)
        dut.rready_i.value = 0
        await RisingEdge(dut.clk)
    assert dut.rvalid_o.value == 0  #empty


@cocotb.test()
async def test_random_traffic(dut):
    await start(dut)
    rng = random.Random(2)
    model = deque()
    sent = 0
    popped = []
    pending = False  #a beat is offered but not yet accepted
    while len(popped) < 300:
        #hold a stalled beat, otherwise maybe offer the next one
        if not pending and rng.random() < 0.6:
            dut.wvalid_i.value = 1
            dut.wdata_i.value = sent & 0xFFFF
            pending = True
        elif not pending:
            dut.wvalid_i.value = 0
        dut.rready_i.value = 1 if rng.random() < 0.5 else 0
        #sample the settled state just before the edge
        await ReadOnly()
        push = bool(dut.wvalid_i.value) and bool(dut.wready_o.value)
        pop = bool(dut.rvalid_o.value) and bool(dut.rready_i.value)
        data = int(dut.rdata_o.value) if pop else None
        await RisingEdge(dut.clk)
        if pop:
            assert data == model[0], f"got {data} expected {model[0]}"
            popped.append(data)
            model.popleft()
        if push:
            model.append(sent & 0xFFFF)
            sent += 1
            pending = False
            dut.wvalid_i.value = 0
    assert popped == list(range(300))
