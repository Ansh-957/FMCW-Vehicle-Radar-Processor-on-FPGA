"""dc_remove bit exact against the integer model"""

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
from model.fixed.frontend import dc_remove  #noqa: E402


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


async def send_chirp(dut, i_s, q_s, sof=False, stall_in=0.0, rng=None):
    n = len(i_s)
    for k in range(n):
        while True:
            if rng is not None and rng.random() < stall_in:
                dut.s_valid_i.value = 0
                await RisingEdge(dut.clk)
                continue
            dut.s_valid_i.value = 1
            dut.s_i_i.value = int(i_s[k])
            dut.s_q_i.value = int(q_s[k])
            dut.s_sof_i.value = 1 if (sof and k == 0) else 0
            dut.s_eoc_i.value = 1 if k == n - 1 else 0
            dut.s_idx_i.value = k
            await ReadOnly()
            ready = bool(dut.s_ready_o.value)
            await RisingEdge(dut.clk)
            if ready:
                break
    dut.s_valid_i.value = 0
    dut.s_eoc_i.value = 0
    dut.s_sof_i.value = 0


async def recv_chirp(dut, n, stall_out=0.0, rng=None):
    i_o, q_o, idx, sof, eoc = [], [], [], [], []
    while len(i_o) < n:
        dut.m_ready_i.value = 0 if (rng is not None and rng.random() < stall_out) else 1
        await ReadOnly()
        if bool(dut.m_valid_o.value) and bool(dut.m_ready_i.value):
            i_o.append(to_signed(dut.m_i_o.value, P.W_DC))
            q_o.append(to_signed(dut.m_q_o.value, P.W_DC))
            idx.append(int(dut.m_idx_o.value))
            sof.append(int(dut.m_sof_o.value))
            eoc.append(int(dut.m_eoc_o.value))
        await RisingEdge(dut.clk)
    dut.m_ready_i.value = 0
    return (np.array(i_o), np.array(q_o), idx, sof, eoc)


@cocotb.test()
async def test_constant_offset(dut):
    await start(dut)
    i_s = np.full(P.NS, 400, dtype=np.int64)
    q_s = np.full(P.NS, -200, dtype=np.int64)
    exp_i = dc_remove(i_s[None, :])[0]
    exp_q = dc_remove(q_s[None, :])[0]
    sender = cocotb.start_soon(send_chirp(dut, i_s, q_s, sof=True))
    got_i, got_q, idx, sof, eoc = await recv_chirp(dut, P.NS)
    await sender
    assert np.array_equal(got_i, exp_i)
    assert np.array_equal(got_q, exp_q)
    assert idx == list(range(P.NS))
    assert sof[0] == 1 and sum(sof) == 1
    assert eoc[-1] == 1 and sum(eoc) == 1
    assert np.all(got_i == 0) and np.all(got_q == 0)


@cocotb.test()
async def test_random_two_chirps(dut):
    await start(dut)
    rng = random.Random(4)
    for c in range(2):
        i_s = np.array([rng.randrange(-2048, 2048) for _ in range(P.NS)],
                       dtype=np.int64)
        q_s = np.array([rng.randrange(-2048, 2048) for _ in range(P.NS)],
                       dtype=np.int64)
        exp_i = dc_remove(i_s[None, :])[0]
        exp_q = dc_remove(q_s[None, :])[0]
        sender = cocotb.start_soon(
            send_chirp(dut, i_s, q_s, sof=(c == 0), stall_in=0.3, rng=rng))
        got_i, got_q, idx, sof, eoc = await recv_chirp(
            dut, P.NS, stall_out=0.4, rng=rng)
        await sender
        assert np.array_equal(got_i, exp_i), f"chirp {c} i"
        assert np.array_equal(got_q, exp_q), f"chirp {c} q"
        assert idx == list(range(P.NS))
        assert sof[0] == (1 if c == 0 else 0)
        assert eoc[-1] == 1
