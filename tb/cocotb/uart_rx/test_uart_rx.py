"""uart_rx byte reception and start bit glitch rejection"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

CLKS_PER_BIT = 16


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.rx_i.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await ClockCycles(dut.clk, 4)


async def send_byte(dut, byte):
    dut.rx_i.value = 0  #start
    await ClockCycles(dut.clk, CLKS_PER_BIT)
    for i in range(8):
        dut.rx_i.value = (byte >> i) & 1
        await ClockCycles(dut.clk, CLKS_PER_BIT)
    dut.rx_i.value = 1  #stop
    await ClockCycles(dut.clk, CLKS_PER_BIT)


async def wait_valid(dut, timeout_clks=400):
    for _ in range(timeout_clks):
        await RisingEdge(dut.clk)
        if dut.valid_o.value:
            return int(dut.data_o.value)
    raise AssertionError("no valid pulse")


@cocotb.test()
async def test_bytes(dut):
    await start(dut)
    for tx in (0x55, 0xA3, 0x00, 0xFF):
        send = cocotb.start_soon(send_byte(dut, tx))
        got = await wait_valid(dut)
        await send
        assert got == tx, f"sent {tx:02x} got {got:02x}"
        await ClockCycles(dut.clk, CLKS_PER_BIT)


@cocotb.test()
async def test_glitch_rejected(dut):
    await start(dut)
    #short low glitch, gone before the mid bit check
    dut.rx_i.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rx_i.value = 1
    for _ in range(3 * CLKS_PER_BIT):
        await RisingEdge(dut.clk)
        assert dut.valid_o.value == 0, "glitch produced a byte"


@cocotb.test()
async def test_back_to_back(dut):
    await start(dut)
    data = [0x12, 0x34, 0x56]
    got = []

    async def collect():
        while len(got) < len(data):
            got.append(await wait_valid(dut))

    c = cocotb.start_soon(collect())
    for b in data:
        await send_byte(dut, b)
    await c
    assert got == data
