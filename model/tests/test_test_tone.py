"""test tone nco known answers, a tone set for range r lands in bin r/0.75"""

import numpy as np
import pytest

from model import params as P
from model.fixed.chain import process_frame_fixed
from model.fixed.test_tone import Tone, generate


def s12_to_codes(i12, q12):
    codes = np.stack([i12 + P.ADC_MID, q12 + P.ADC_MID], axis=-1)
    return np.clip(codes, 0, 4095).astype(np.int64)


def test_nco_rom_plus_one():
    from model.fixed import roms
    c, s = roms.nco()
    assert c[0] == 131071 and s[0] == 0


def test_tone_at_30m_is_bin_40():
    tones = [Tone(en=True, amp=1200, fw=P.fw_for_range_bin(40), dphi=0)]
    i12, q12 = generate(tones, noise_gain=0, n_chirps=P.NC)
    _, dets, flags = process_frame_fixed(s12_to_codes(i12, q12))
    assert not any(flags.values())
    assert any(abs(d.range_bin - 40) <= 1
               and d.doppler_bin == P.DOPPLER_ZERO_BIN for d in dets)


def test_tone_moving_bin():
    rbin, dbin = 47, 51
    tones = [Tone(en=True, amp=1200,
                  fw=P.fw_for_range_bin(rbin),
                  dphi=P.dphi_for_doppler_bin(dbin))]
    i12, q12 = generate(tones, noise_gain=0, n_chirps=P.NC)
    _, dets, flags = process_frame_fixed(s12_to_codes(i12, q12))
    assert not any(flags.values())
    assert any(abs(d.range_bin - rbin) <= 1
               and abs(d.doppler_bin - dbin) <= 1 for d in dets)


def test_disabled_tone_is_silence():
    tones = [Tone(en=False, amp=2000, fw=P.fw_for_range_bin(10))]
    i12, q12 = generate(tones, noise_gain=0, n_chirps=1)
    assert np.all(i12 == 0) and np.all(q12 == 0)
