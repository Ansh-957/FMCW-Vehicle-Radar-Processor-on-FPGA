"""uart_tx framing checked by sampling the line at mid bit"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

CLKS_PER_BIT = 16


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.valid_i.value = 0
    dut.data_i.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def recv_byte(dut):
    #wait for the start bit edge
    while dut.tx_o.value == 1:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CLKS_PER_BIT // 2)
    assert dut.tx_o.value == 0, "start bit"
    byte = 0
    for i in range(8):
        await ClockCycles(dut.clk, CLKS_PER_BIT)
        byte |= int(dut.tx_o.value) << i
    await ClockCycles(dut.clk, CLKS_PER_BIT)
    assert dut.tx_o.value == 1, "stop bit"
    return byte


@cocotb.test()
async def test_idle_high(dut):
    await start(dut)
    for _ in range(20):
        await RisingEdge(dut.clk)
        assert dut.tx_o.value == 1


@cocotb.test()
async def test_bytes(dut):
    await start(dut)
    for tx in (0x55, 0xA3, 0x00, 0xFF):
        dut.valid_i.value = 1
        dut.data_i.value = tx
        await RisingEdge(dut.clk)
        while not dut.ready_o.value:
            dut.valid_i.value = 0
            await RisingEdge(dut.clk)
        dut.valid_i.value = 0
        got = await recv_byte(dut)
        assert got == tx, f"sent {tx:02x} got {got:02x}"
        #wait for ready again before the next byte
        while not dut.ready_o.value:
            await RisingEdge(dut.clk)


@cocotb.test()
async def test_back_to_back(dut):
    await start(dut)
    data = [0x12, 0x34, 0x56]

    async def feeder():
        for b in data:
            dut.valid_i.value = 1
            dut.data_i.value = b
            await RisingEdge(dut.clk)
            while not dut.ready_o.value:
                await RisingEdge(dut.clk)
            dut.valid_i.value = 0
            await RisingEdge(dut.clk)
            while not dut.ready_o.value:
                await RisingEdge(dut.clk)

    f = cocotb.start_soon(feeder())
    got = [await recv_byte(dut) for _ in data]
    await f
    assert got == data
