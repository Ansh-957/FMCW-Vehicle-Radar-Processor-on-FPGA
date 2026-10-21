"""frame buffer narrowing, power, log2, cfar, peak detect, target list
and display mapping"""

from dataclasses import dataclass

import numpy as np

from .. import params as P
from . import roms
from .util import rhu, rdiv, sat_signed, sat_unsigned


def frame_narrow(x, shift=P.FB_SHIFT_DEFAULT, flags=None, stage="frame_buffer"):
    """s18 to s16 for frame buffer storage, round half up then saturate"""
    return sat_signed(rhu(x, shift), P.W_FRAME, flags, stage)


def power(i, q):
    """i*i + q*q, exact, s18 inputs give at most 2 * 131071^2 < 2^35"""
    i = np.asarray(i, dtype=np.int64)
    q = np.asarray(q, dtype=np.int64)
    return i * i + q * q


def log2_fixed(p):
    """piecewise linear log2, L = 256*e + lut[m] where e is the leading
    one position and m the next 8 bits, L(0) is 0, max L 9471 fits u16,
    hardware is a priority encoder, barrel shift and 256 entry lut"""
    lut = roms.log_lut()
    p_flat = np.asarray(p, dtype=np.int64).ravel()
    out = np.zeros_like(p_flat)
    for idx, v in enumerate(p_flat):
        v = int(v)
        if v <= 0:
            continue
        e = v.bit_length() - 1
        m = (v >> (e - 8)) & 0xFF if e >= 8 else (v << (8 - e)) & 0xFF
        out[idx] = 256 * e + int(lut[m])
    return out.reshape(np.asarray(p).shape)


def cfar_fixed(logmap,
               train=P.CFAR_TRAIN,
               guard=P.CFAR_GUARD,
               offset=P.CFAR_OFFSET_DEFAULT,
               mode="CA",
               exclude_zero_doppler=False):
    """cfar in log units so the mean is geometric, threshold is the
    rounded mean of training cell log powers plus offset, CA pools both
    sides into one sum before dividing, GO and SO compare per side means,
    at the edges only the existing side is used"""
    lm = np.asarray(logmap, dtype=np.int64)
    n_r, n_d = lm.shape
    detect = np.zeros((n_r, n_d), dtype=bool)
    for d in range(n_d):
        if exclude_zero_doppler and d == P.DOPPLER_ZERO_BIN:
            continue
        col = lm[:, d]
        for r in range(n_r):
            lead = col[max(0, r - guard - train): max(0, r - guard)]
            lag = col[r + guard + 1: r + guard + 1 + train]
            if lead.size == 0 and lag.size == 0:
                continue
            if mode == "CA":
                noise = rdiv(int(lead.sum()) + int(lag.sum()),
                             lead.size + lag.size)
            else:
                sides = [rdiv(int(s.sum()), s.size)
                         for s in (lead, lag) if s.size > 0]
                noise = max(sides) if mode == "GO" else min(sides)
            detect[r, d] = int(col[r]) > noise + offset
    return detect


def peak_detect_fixed(logmap, detect):
    """keep a detection only if it beats its 8 neighbours, an equal
    neighbour wins only if it comes first in raster order so a plateau
    yields exactly one peak, out of map neighbours count as 0"""
    lm = np.asarray(logmap, dtype=np.int64)
    n_r, n_d = lm.shape
    out = np.zeros_like(detect)
    for r, d in zip(*np.nonzero(detect)):
        v = int(lm[r, d])
        is_peak = True
        for dr in (-1, 0, 1):
            for dd in (-1, 0, 1):
                if dr == 0 and dd == 0:
                    continue
                r2, d2 = r + dr, d + dd
                if not (0 <= r2 < n_r and 0 <= d2 < n_d):
                    continue
                v2 = int(lm[r2, d2])
                if v2 > v or (v2 == v and (r2, d2) < (r, d)):
                    is_peak = False
                    break
            if not is_peak:
                break
        out[r, d] = is_peak
    return out


@dataclass
class FixedDetection:
    range_bin: int
    doppler_bin: int
    log_power: int      #u16 log units, 256 units is 3.01 dB
    snr_units: int      #log power minus the map median, floored at 0


def target_list_fixed(logmap, peaks, max_targets=P.MAX_TARGETS):
    """collect detections strongest first, capped, sort key is power desc
    then range asc then doppler asc which is total so the kept set is
    deterministic, snr reference is the map median taking the lower
    middle element"""
    lm = np.asarray(logmap, dtype=np.int64)
    flat = np.sort(lm.ravel())
    median = int(flat[flat.size // 2])
    dets = [FixedDetection(int(r), int(d), int(lm[r, d]),
                           max(0, int(lm[r, d]) - median))
            for r, d in zip(*np.nonzero(peaks))]
    dets.sort(key=lambda t: (-t.log_power, t.range_bin, t.doppler_bin))
    return dets[:max_targets]


def display_map(logmap, black_level, contrast_shift, flags=None,
                stage="display"):
    """u16 log power to u8 pixel, (L - black) >> contrast clamped,
    the subtraction floors at 0 before the shift"""
    lm = np.asarray(logmap, dtype=np.int64)
    v = np.maximum(lm - int(black_level), 0) >> np.int64(contrast_shift)
    return sat_unsigned(v, 8, flags, stage)


def render_rgb(pixels):
    """u8 map to rgb via the colour map rom"""
    cmap = roms.colormap()
    return cmap[np.asarray(pixels, dtype=np.int64)]
