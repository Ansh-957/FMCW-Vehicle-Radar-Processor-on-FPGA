"""the tone generator model must place targets where it promises,
checked by running its output through the fixed chain"""

import numpy as np

from model import params as P
from model.fixed.chain import process_frame_fixed
from model.fixed.test_tone_gen import (ToneGenModel, bin_to_freq_word,
                                       doppler_bin_to_chirp_step)


def test_single_tone_lands_in_its_bin():
    gen = ToneGenModel([(bin_to_freq_word(40),
                         doppler_bin_to_chirp_step(32), 1200)],
                       noise_amp=40)
    logmap, dets, flags = process_frame_fixed(gen.frame())
    assert not any(flags.values())
    assert any(d.range_bin == 40 and d.doppler_bin == 32 for d in dets)


def test_moving_tone():
    gen = ToneGenModel([(bin_to_freq_word(20),
                         doppler_bin_to_chirp_step(45), 1200)],
                       noise_amp=40)
    _, dets, flags = process_frame_fixed(gen.frame())
    assert not any(flags.values())
    assert any(d.range_bin == 20 and d.doppler_bin == 45 for d in dets)


def test_four_tones():
    cfg = [(bin_to_freq_word(10), doppler_bin_to_chirp_step(32), 1000),
           (bin_to_freq_word(45), doppler_bin_to_chirp_step(40), 700),
           (bin_to_freq_word(80), doppler_bin_to_chirp_step(20), 900),
           (bin_to_freq_word(120), doppler_bin_to_chirp_step(34), 500)]
    gen = ToneGenModel(cfg, noise_amp=40)
    _, dets, flags = process_frame_fixed(gen.frame())
    assert not any(flags.values())
    for rb, db in [(10, 32), (45, 40), (80, 20), (120, 34)]:
        assert any(abs(d.range_bin - rb) <= 1
                   and abs(d.doppler_bin - db) <= 1 for d in dets), (rb, db)


def test_lfsr_is_deterministic_and_nonrepeating_short():
    a = ToneGenModel([], noise_amp=100)
    b = ToneGenModel([], noise_amp=100)
    seq_a = [a.lfsr_step() for _ in range(1000)]
    seq_b = [b.lfsr_step() for _ in range(1000)]
    assert seq_a == seq_b
    assert len(set(seq_a)) == 1000  #period far exceeds this window


def test_codes_are_valid_u12():
    gen = ToneGenModel([(bin_to_freq_word(5), 0, 2047)], noise_amp=200)
    frame = gen.frame()
    assert frame.min() >= 0 and frame.max() <= 4095
