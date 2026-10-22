"""loads the .mem files written by scripts/gen_rom.py, the rtl reads the
same files so the tables cannot drift between model and hardware
"""

import os
from functools import lru_cache

import numpy as np

MEM_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "rtl", "mem")


def _read_mem(name):
    path = os.path.join(MEM_DIR, name)
    with open(path) as f:
        return [int(line.strip(), 16) for line in f if line.strip()]


def _to_signed(v, bits):
    return v - (1 << bits) if v >= (1 << (bits - 1)) else v


@lru_cache(maxsize=None)
def hann(n):
    """u16 window coefficients, n is 64 or 256"""
    return np.array(_read_mem(f"hann{n}.mem"), dtype=np.int64)


@lru_cache(maxsize=None)
def twiddles():
    """(re, im) int64 arrays of 128 entries, Q1.17, W_256^k for k 0..127"""
    packed = _read_mem("twiddle128.mem")
    re = np.array([_to_signed(p >> 18, 18) for p in packed], dtype=np.int64)
    im = np.array([_to_signed(p & 0x3FFFF, 18) for p in packed],
                  dtype=np.int64)
    return re, im


@lru_cache(maxsize=None)
def log_lut():
    """u8 lut of round(256*log2(1 + m/256)) for m 0..255"""
    return np.array(_read_mem("log_lut.mem"), dtype=np.int64)


@lru_cache(maxsize=None)
def nco():
    """(cos, sin) int64 arrays of 256 entries, Q1.17, exp(+j*2*pi*k/256)"""
    packed = _read_mem("nco256.mem")
    re = np.array([_to_signed(p >> 18, 18) for p in packed], dtype=np.int64)
    im = np.array([_to_signed(p & 0x3FFFF, 18) for p in packed],
                  dtype=np.int64)
    return re, im


@lru_cache(maxsize=None)
def colormap():
    """256 x (r, g, b) int64 for the display path"""
    packed = _read_mem("colormap.mem")
    return np.array([[(p >> 16) & 0xFF, (p >> 8) & 0xFF, p & 0xFF]
                     for p in packed], dtype=np.int64)
