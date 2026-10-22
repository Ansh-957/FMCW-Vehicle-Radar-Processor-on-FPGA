"""window_mult doppler instance, 64 tap hann, s16 in, shift 16"""

import os
import random
import sys

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", ".."))

from model import params as P  #noqa: E402
from model.fixed.frontend import window_mult  #noqa: E402


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.s_valid_i.value = 0
    dut.s_i_i.value = 0
    dut.s_q_i.value = 0
    dut.s_sof_i.value = 0
    dut.s_eoc_i.value = 0
    dut.s_idx_i.value = 0
    dut.m_ready_i.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


def to_signed(v, bits):
    v = int(v)
    if v >= (1 << (bits - 1)):
        v -= 1 << bits
    return v


@cocotb.test()
async def test_random_row(dut):
    await start(dut)
    rng = random.Random(8)
    n = P.NC
    i_s = np.array([rng.randrange(-32768, 32768) for _ in range(n)],
                   dtype=np.int64)
    q_s = np.array([rng.randrange(-32768, 32768) for _ in range(n)],
                   dtype=np.int64)
    exp_i = window_mult(i_s[None, :], n, P.WIN_SHIFT_DOPPLER)[0]
    exp_q = window_mult(q_s[None, :], n, P.WIN_SHIFT_DOPPLER)[0]
    got_i, got_q = [], []
    sent = 0
    while len(got_i) < n:
        if sent < n:
            dut.s_valid_i.value = 1
            dut.s_i_i.value = int(i_s[sent])
            dut.s_q_i.value = int(q_s[sent])
            dut.s_eoc_i.value = 1 if sent == n - 1 else 0
            dut.s_idx_i.value = sent
        else:
            dut.s_valid_i.value = 0
        await ReadOnly()
        if bool(dut.s_valid_i.value) and bool(dut.s_ready_o.value):
            sent += 1
        if bool(dut.m_valid_o.value) and bool(dut.m_ready_i.value):
            got_i.append(to_signed(dut.m_i_o.value, P.W_WIN))
            got_q.append(to_signed(dut.m_q_o.value, P.W_WIN))
        await RisingEdge(dut.clk)
    assert np.array_equal(got_i, exp_i)
    assert np.array_equal(got_q, exp_q)
    assert int(dut.ovf_o.value) == 0
