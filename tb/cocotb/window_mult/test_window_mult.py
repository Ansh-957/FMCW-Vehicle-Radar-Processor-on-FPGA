"""window_mult bit exact against the integer model, range instance"""

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
    dut.m_ready_i.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


def to_signed(v, bits):
    v = int(v)
    if v >= (1 << (bits - 1)):
        v -= 1 << bits
    return v


async def xfer_chirp(dut, i_s, q_s, stall=0.0, rng=None):
    n = len(i_s)
    sent = 0
    got_i, got_q, idx, sof, eoc = [], [], [], [], []
    while len(got_i) < n:
        if sent < n and (rng is None or rng.random() >= stall):
            dut.s_valid_i.value = 1
            dut.s_i_i.value = int(i_s[sent])
            dut.s_q_i.value = int(q_s[sent])
            dut.s_sof_i.value = 1 if sent == 0 else 0
            dut.s_eoc_i.value = 1 if sent == n - 1 else 0
            dut.s_idx_i.value = sent
        else:
            dut.s_valid_i.value = 0
        dut.m_ready_i.value = 0 if (rng is not None and rng.random() < stall) else 1
        await ReadOnly()
        if bool(dut.s_valid_i.value) and bool(dut.s_ready_o.value):
            sent += 1
        if bool(dut.m_valid_o.value) and bool(dut.m_ready_i.value):
            got_i.append(to_signed(dut.m_i_o.value, P.W_WIN))
            got_q.append(to_signed(dut.m_q_o.value, P.W_WIN))
            idx.append(int(dut.m_idx_o.value))
            sof.append(int(dut.m_sof_o.value))
            eoc.append(int(dut.m_eoc_o.value))
        await RisingEdge(dut.clk)
    dut.s_valid_i.value = 0
    dut.m_ready_i.value = 0
    return np.array(got_i), np.array(got_q), idx, sof, eoc


@cocotb.test()
async def test_impulse(dut):
    await start(dut)
    i_s = np.zeros(P.NS, dtype=np.int64)
    q_s = np.zeros(P.NS, dtype=np.int64)
    i_s[32] = 1000
    exp_i = window_mult(i_s[None, :], P.NS, P.WIN_SHIFT_RANGE)[0]
    exp_q = window_mult(q_s[None, :], P.NS, P.WIN_SHIFT_RANGE)[0]
    got_i, got_q, idx, sof, eoc = await xfer_chirp(dut, i_s, q_s)
    assert np.array_equal(got_i, exp_i)
    assert np.array_equal(got_q, exp_q)
    assert idx == list(range(P.NS))
    assert sof[0] == 1 and eoc[-1] == 1
    assert int(dut.ovf_o.value) == 0


@cocotb.test()
async def test_random_with_stalls(dut):
    await start(dut)
    rng = random.Random(5)
    i_s = np.array([rng.randrange(-4096, 4097) for _ in range(P.NS)],
                   dtype=np.int64)
    q_s = np.array([rng.randrange(-4096, 4097) for _ in range(P.NS)],
                   dtype=np.int64)
    flags = {}
    exp_i = window_mult(i_s[None, :], P.NS, P.WIN_SHIFT_RANGE, flags, "w")[0]
    exp_q = window_mult(q_s[None, :], P.NS, P.WIN_SHIFT_RANGE, flags, "w")[0]
    got_i, got_q, idx, sof, eoc = await xfer_chirp(dut, i_s, q_s, stall=0.4,
                                                   rng=rng)
    assert np.array_equal(got_i, exp_i)
    assert np.array_equal(got_q, exp_q)
    assert idx == list(range(P.NS))
    assert sof[0] == 1 and eoc[-1] == 1
    assert int(dut.ovf_o.value) == int(flags.get("w", False))
