"""integer model of the synthetic target generator

each tone has a 16 bit sample phase accumulator and a 16 bit chirp phase
accumulator, at chirp start the chirp phase advances by the chirp step
and reloads the sample accumulator, every sample the top 8 phase bits
index the shared twiddle rom for cos and sin, contributions are
rhu(amp * value, 17), noise comes from a 16 bit galois lfsr, the summed
sample saturates to s12 then shifts to offset binary

freq word for range bin b is b * 256, chirp step for doppler bin d is
(d - 32) * 1024 mod 65536
"""

import numpy as np

from .. import params as P
from . import roms
from .util import rhu, sat_signed

LFSR_TAPS = 0xB400
LFSR_SEED = 0xACE1


def sincos(k):
    """cos and sin of 2*pi*k/256 from the half circle twiddle rom"""
    twr, twi = roms.twiddles()
    k &= 0xFF
    if k < 128:
        return int(twr[k]), -int(twi[k])
    return -int(twr[k - 128]), int(twi[k - 128])


class ToneGenModel:
    def __init__(self, tones, noise_amp=0, seed=LFSR_SEED):
        """tones is a list of (freq_word, chirp_step, amp) with amp 0..2047"""
        self.tones = list(tones)
        self.noise_amp = noise_amp
        self.lfsr = seed
        self.phase = [0] * len(self.tones)
        self.chirp_phase = [0] * len(self.tones)

    def lfsr_step(self):
        bit = self.lfsr & 1
        self.lfsr >>= 1
        if bit:
            self.lfsr ^= LFSR_TAPS
        return self.lfsr

    def noise(self):
        v = (self.lfsr_step() & 0xFFF) - 2048
        return int(rhu(v * self.noise_amp, 11))

    def start_chirp(self):
        for t in range(len(self.tones)):
            step = self.tones[t][1]
            self.chirp_phase[t] = (self.chirp_phase[t] + step) & 0xFFFF
            self.phase[t] = self.chirp_phase[t]

    def sample(self):
        """returns one (i, q) pair of u12 offset binary codes"""
        acc_i = 0
        acc_q = 0
        for t, (freq, _step, amp) in enumerate(self.tones):
            c, s = sincos(self.phase[t] >> 8)
            acc_i += int(rhu(amp * c, 17))
            acc_q += int(rhu(amp * s, 17))
            self.phase[t] = (self.phase[t] + freq) & 0xFFFF
        if self.noise_amp:
            acc_i += self.noise()
            acc_q += self.noise()
        i12 = int(sat_signed(np.array([acc_i]), P.W_ADC)[0])
        q12 = int(sat_signed(np.array([acc_q]), P.W_ADC)[0])
        return i12 + P.ADC_MID, q12 + P.ADC_MID

    def frame(self):
        """returns (NC, NS, 2) u12 codes, one full frame"""
        out = np.zeros((P.NC, P.NS, 2), dtype=np.int64)
        for c in range(P.NC):
            self.start_chirp()
            for n in range(P.NS):
                out[c, n, 0], out[c, n, 1] = self.sample()
        return out


def bin_to_freq_word(range_bin):
    return (range_bin * 256) & 0xFFFF


def doppler_bin_to_chirp_step(doppler_bin):
    return ((doppler_bin - P.DOPPLER_ZERO_BIN) * 1024) & 0xFFFF
