"""test_tone_gen bit exact against the integer model"""

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
from model.fixed.test_tone import Tone, generate  #noqa: E402


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst.value = 1
    dut.run_i.value = 0
    dut.m_ready_i.value = 0
    dut.noise_gain_i.value = 0
    dut.tone_en_i.value = 0
    dut.tone_amp_i.value = 0
    dut.tone_fw_i.value = 0
    dut.tone_dphi_i.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


def to_signed(v, bits):
    v = int(v)
    if v >= (1 << (bits - 1)):
        v -= 1 << bits
    return v


def load_tones(dut, tones, noise_gain=0):
    en = amp = fw = dphi = 0
    for t in range(P.N_TONES):
        cfg = tones[t] if t < len(tones) else Tone()
        if cfg.en:
            en |= 1 << t
        amp |= (int(np.int16(cfg.amp)) & 0xFFFF) << (16 * t)
        fw |= (int(cfg.fw) & 0xFFFFFFFF) << (32 * t)
        dphi |= (int(cfg.dphi) & 0xFFFFFFFF) << (32 * t)
    dut.tone_en_i.value = en
    dut.tone_amp_i.value = amp
    dut.tone_fw_i.value = fw
    dut.tone_dphi_i.value = dphi
    dut.noise_gain_i.value = int(noise_gain) & 0xFFFF


async def collect(dut, n, stall=0.0, rng=None):
    i_o, q_o, idx, sof, eoc = [], [], [], [], []
    dut.run_i.value = 1
    while len(i_o) < n:
        dut.m_ready_i.value = 0 if (rng is not None and rng.random() < stall) else 1
        await ReadOnly()
        if bool(dut.m_valid_o.value) and bool(dut.m_ready_i.value):
            i_o.append(to_signed(dut.m_i_o.value, P.W_ADC))
            q_o.append(to_signed(dut.m_q_o.value, P.W_ADC))
            idx.append(int(dut.m_idx_o.value))
            sof.append(int(dut.m_sof_o.value))
            eoc.append(int(dut.m_eoc_o.value))
        await RisingEdge(dut.clk)
    dut.run_i.value = 0
    dut.m_ready_i.value = 0
    return (np.array(i_o), np.array(q_o), idx, sof, eoc)


@cocotb.test()
async def test_single_tone_one_chirp(dut):
    await start(dut)
    tones = [Tone(en=True, amp=1000, fw=P.fw_for_range_bin(40), dphi=0)]
    load_tones(dut, tones)
    exp_i, exp_q = generate(tones, noise_gain=0, n_chirps=1)
    got_i, got_q, idx, sof, eoc = await collect(dut, P.NS)
    assert np.array_equal(got_i, exp_i[0])
    assert np.array_equal(got_q, exp_q[0])
    assert idx == list(range(P.NS))
    assert sof[0] == 1 and sum(sof) == 1
    assert eoc[-1] == 1 and sum(eoc) == 1


@cocotb.test()
async def test_four_tones_noise_one_frame(dut):
    await start(dut)
    tones = [
        Tone(en=True, amp=800, fw=P.fw_for_range_bin(16), dphi=0),
        Tone(en=True, amp=500, fw=P.fw_for_range_bin(47),
             dphi=P.dphi_for_doppler_bin(51)),
        Tone(en=True, amp=600, fw=P.fw_for_range_bin(93),
             dphi=P.dphi_for_doppler_bin(6)),
        Tone(en=False, amp=0, fw=0, dphi=0),
    ]
    load_tones(dut, tones, noise_gain=1024)
    exp_i, exp_q = generate(tones, noise_gain=1024, n_chirps=P.NC)
    rng = random.Random(6)
    got_i, got_q, idx, sof, eoc = await collect(
        dut, P.NS * P.NC, stall=0.25, rng=rng)
    got_i = got_i.reshape(P.NC, P.NS)
    got_q = got_q.reshape(P.NC, P.NS)
    assert np.array_equal(got_i, exp_i)
    assert np.array_equal(got_q, exp_q)
    assert sof[0] == 1
    assert sof[P.NS] == 0
    assert eoc[P.NS - 1] == 1
    assert eoc[-1] == 1
