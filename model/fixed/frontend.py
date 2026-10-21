"""adc capture, dc removal and window multiply"""

import numpy as np

from .. import params as P
from . import roms
from .util import rhu, sat_signed


def adc_capture(codes):
    """12 bit offset binary codes to s12, exact"""
    codes = np.asarray(codes, dtype=np.int64)
    return codes - np.int64(P.ADC_MID)


def dc_remove(samples):
    """subtract the chirp's own per channel mean, s12 to s13

    mean is (sum of 256 samples + 128) >> 8, matches the hardware pre
    pass over the fft input bank, output fits s13 with no saturation
    since |s12| <= 2048 and |rounded mean| <= 2048"""
    samples = np.asarray(samples, dtype=np.int64)
    assert samples.shape[-1] == P.NS
    total = samples.sum(axis=-1, keepdims=True)
    mean = rhu(total, 8)
    return samples - mean


def window_mult(x, n, shift, flags=None, stage="window"):
    """multiply by the u16 hann rom, round half up by shift, saturate s16

    range instance n 256 shift 13, gain w/8192 spreads s13 across the
    full s16 range, 4095 * 65535 >> 13 = 32760 so nominal input cannot
    saturate
    doppler instance n 64 shift 16, gain at most 1, pure taper"""
    x = np.asarray(x, dtype=np.int64)
    assert x.shape[-1] == n
    w = roms.hann(n)
    prod = x * w  #29 bits worst case, fits int64
    return sat_signed(rhu(prod, shift), P.W_WIN, flags, stage)
