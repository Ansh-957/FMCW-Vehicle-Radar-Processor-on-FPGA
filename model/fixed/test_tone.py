"""integer nco for up to 4 tones plus lfsr noise, bit exact model of
the rtl test tone generator

each tone is a 32 bit phase word, top 8 bits index a 256 entry Q1.17
cos/sin lut, amplitude is s16, product is rounded half up by 17 then
summed, noise is two lfsr steps per sample (i then q) scaled by
noise_gain, the sum saturates to s12
"""

from dataclasses import dataclass

import numpy as np

from .. import params as P
from . import roms
from .util import rhu, sat_signed


@dataclass
class Tone:
    en: bool = False
    amp: int = 0
    fw: int = 0
    dphi: int = 0


def lfsr_step(s):
    bit = ((s >> 15) ^ (s >> 14) ^ (s >> 12) ^ (s >> 3)) & 1
    return ((s << 1) | bit) & 0xFFFF


def lfsr_s12(s):
    v = (s >> 4) & 0xFFF
    return v - 4096 if v >= 2048 else v


def generate(tones, noise_gain=0, n_chirps=P.NC, seed=P.LFSR_SEED,
             flags=None):
    """returns (i, q) int64 arrays shaped (n_chirps, NS), s12"""
    tones = list(tones) + [Tone()] * (P.N_TONES - len(tones))
    tones = tones[: P.N_TONES]
    cos_lut, sin_lut = roms.nco()
    chirp_ph = [0] * P.N_TONES
    lfsr = int(seed) & 0xFFFF
    out_i = np.zeros((n_chirps, P.NS), dtype=np.int64)
    out_q = np.zeros((n_chirps, P.NS), dtype=np.int64)

    for k in range(n_chirps):
        phase = list(chirp_ph)
        for n in range(P.NS):
            acc_i = 0
            acc_q = 0
            for t in range(P.N_TONES):
                if tones[t].en:
                    idx = (phase[t] >> (P.PHASE_W - P.NCO_IDX_BITS)) & 0xFF
                    amp = int(np.int16(tones[t].amp))
                    acc_i += int(rhu(int(cos_lut[idx]) * amp, 17))
                    acc_q += int(rhu(int(sin_lut[idx]) * amp, 17))
                    phase[t] = (phase[t] + (int(tones[t].fw) & 0xFFFFFFFF)
                                ) & 0xFFFFFFFF
            ni = int(rhu(lfsr_s12(lfsr) * int(noise_gain), P.NOISE_SHIFT))
            lfsr = lfsr_step(lfsr)
            nq = int(rhu(lfsr_s12(lfsr) * int(noise_gain), P.NOISE_SHIFT))
            lfsr = lfsr_step(lfsr)
            out_i[k, n] = int(sat_signed(acc_i + ni, P.W_ADC, flags, "tone"))
            out_q[k, n] = int(sat_signed(acc_q + nq, P.W_ADC, flags, "tone"))
        for t in range(P.N_TONES):
            chirp_ph[t] = (chirp_ph[t] + (int(tones[t].dphi) & 0xFFFFFFFF)
                           ) & 0xFFFFFFFF
    return out_i, out_q
