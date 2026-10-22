"""every source pulse arrives exactly once in the destination domain,
tried with the destination both faster and slower"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


async def run_pulses(dut, s_period, d_period, n_pulses):
    cocotb.start_soon(Clock(dut.sclk, s_period, unit="ns").start())
    cocotb.start_soon(Clock(dut.dclk, d_period, unit="ns").start())
    dut.pulse_i.value = 0
    dut.srst.value = 1
    dut.drst.value = 1
    await Timer(5 * max(s_period, d_period), unit="ns")
    await RisingEdge(dut.sclk)
    dut.srst.value = 0
    dut.drst.value = 0
    await Timer(5 * max(s_period, d_period), unit="ns")

    received = 0

    async def count():
        nonlocal received
        while True:
            await RisingEdge(dut.dclk)
            if dut.pulse_o.value:
                received += 1

    counter = cocotb.start_soon(count())
    for _ in range(n_pulses):
        await RisingEdge(dut.sclk)
        dut.pulse_i.value = 1
        await RisingEdge(dut.sclk)
        dut.pulse_i.value = 0
        #space pulses several destination clocks apart
        await ClockCycles(dut.dclk, 6)
    await ClockCycles(dut.dclk, 10)
    counter.kill()
    assert received == n_pulses, f"sent {n_pulses}, got {received}"


@cocotb.test()
async def test_slow_to_fast(dut):
    await run_pulses(dut, s_period=20, d_period=7, n_pulses=20)


@cocotb.test()
async def test_fast_to_slow(dut):
    await run_pulses(dut, s_period=7, d_period=20, n_pulses=20)
