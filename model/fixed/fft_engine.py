"""memory based radix 2 dif fft, bit exact model of the rtl engine

butterfly is X = A + B and Y = (A - B) * W with an optional halving per
stage, round half up, both results saturate to the s18 datapath, twiddles
are Q1.17 from the single 128 entry W_256 rom, smaller sizes stride
through it with index j * (256 // (2*span)), results come out bit
reversed and are reordered to natural before returning

widest intermediate is s19 * s18 = 37 bits so int64 is safe
"""

import numpy as np

from .. import params as P
from . import roms
from .util import rhu, sat_signed


def _bit_reverse_indices(n):
    bits = n.bit_length() - 1
    return np.array([int(format(i, f"0{bits}b")[::-1], 2) for i in range(n)])


def fft_fixed(xr, xi, n, scale_sched=None, flags=None, stage="fft"):
    """transforms the last axis, xr and xi are int64 s16 range input,
    scale_sched[s] true halves stage s output, default halves every
    stage, returns (yr, yi) in natural order as s18"""
    xr = np.asarray(xr, dtype=np.int64).copy()
    xi = np.asarray(xi, dtype=np.int64).copy()
    assert xr.shape[-1] == n and n in (64, 128, 256)
    n_stages = n.bit_length() - 1
    if scale_sched is None:
        scale_sched = [True] * n_stages
    assert len(scale_sched) == n_stages
    twr, twi = roms.twiddles()

    span = n // 2
    for s in range(n_stages):
        scale = 1 if scale_sched[s] else 0
        #group the last axis as (..., groups, 2, span), [...,0,:] is the A half
        shp = xr.shape[:-1] + (n // (2 * span), 2, span)
        ar = xr.reshape(shp)
        ai = xi.reshape(shp)
        A_r, B_r = ar[..., 0, :], ar[..., 1, :]
        A_i, B_i = ai[..., 0, :], ai[..., 1, :]

        sum_r, sum_i = A_r + B_r, A_i + B_i          #s19
        dif_r, dif_i = A_r - B_r, A_i - B_i          #s19

        idx = np.arange(span) * (256 // (2 * span))  #twiddle rom addresses
        wr, wi = twr[idx], twi[idx]

        x_out_r = sat_signed(rhu(sum_r, scale), P.W_FFT, flags, stage)
        x_out_i = sat_signed(rhu(sum_i, scale), P.W_FFT, flags, stage)
        #complex multiply then drop the Q1.17 scaling, plus 1 on halving stages
        y_out_r = sat_signed(rhu(dif_r * wr - dif_i * wi, 17 + scale),
                             P.W_FFT, flags, stage)
        y_out_i = sat_signed(rhu(dif_r * wi + dif_i * wr, 17 + scale),
                             P.W_FFT, flags, stage)

        new_r = np.empty_like(ar)
        new_i = np.empty_like(ai)
        new_r[..., 0, :], new_r[..., 1, :] = x_out_r, y_out_r
        new_i[..., 0, :], new_i[..., 1, :] = x_out_i, y_out_i
        xr = new_r.reshape(xr.shape)
        xi = new_i.reshape(xi.shape)
        span //= 2

    rev = _bit_reverse_indices(n)  #dif leaves results bit reversed
    return xr[..., rev], xi[..., rev]
