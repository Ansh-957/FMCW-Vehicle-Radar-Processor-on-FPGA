"""skid buffer data integrity and stream protocol under random stalls"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.s_valid_i.value = 0
    dut.s_data_i.value = 0
    dut.m_ready_i.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_passthrough(dut):
    await start(dut)
    dut.m_ready_i.value = 1
    for v in range(10):
        dut.s_valid_i.value = 1
        dut.s_data_i.value = v
        await RisingEdge(dut.clk)
    dut.s_valid_i.value = 0


@cocotb.test()
async def test_random_stalls_preserve_order(dut):
    await start(dut)
    rng = random.Random(1)
    n = 200
    sent = []
    recv = []

    async def driver():
        v = 0
        while v < n:
            if rng.random() < 0.7:
                dut.s_valid_i.value = 1
                dut.s_data_i.value = v
                await RisingEdge(dut.clk)
                while not dut.s_ready_o.value:
                    await RisingEdge(dut.clk)
                sent.append(v)
                v += 1
                dut.s_valid_i.value = 0
            else:
                dut.s_valid_i.value = 0
                await RisingEdge(dut.clk)

    async def sink():
        prev_valid = False
        prev_data = None
        while len(recv) < n:
            dut.m_ready_i.value = 1 if rng.random() < 0.6 else 0
            await RisingEdge(dut.clk)
            valid = bool(dut.m_valid_o.value)
            ready = bool(dut.m_ready_i.value)
            if valid:
                data = int(dut.m_data_o.value)
                #data must hold while valid and not ready
                if prev_valid and prev_data is not None:
                    assert data == prev_data, "data changed while stalled"
                if ready:
                    recv.append(data)
                    prev_valid = False
                    prev_data = None
                else:
                    prev_valid = True
                    prev_data = data
            else:
                #valid must not drop while a stalled beat is pending
                assert not prev_valid, "valid dropped before handshake"
        dut.m_ready_i.value = 0

    d = cocotb.start_soon(driver())
    s = cocotb.start_soon(sink())
    await s
    d.kill()
    assert recv == sent == list(range(n))
