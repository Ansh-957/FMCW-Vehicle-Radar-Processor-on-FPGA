"""synthetic radar scenes, builds the complex baseband i/q samples the adc
would capture for point targets plus noise, dc leakage and i/q imbalance

per target the beat frequency is 2*B*R/(c*Tc) + 2*v/lambda and the phase
advances 2*pi*(2*v/lambda)*Tr per chirp, built from physics so the chain
tests stay independent of the chain's own bin math
"""

from dataclasses import dataclass, field

import numpy as np

from . import params as P


@dataclass
class Target:
    range_m: float          #0 to ~96 m
    velocity_mps: float     #positive is approaching, aliases past the limit
    amplitude: float = 1.0
    phase0: float = 0.0

    @property
    def expected_range_bin(self) -> float:
        return P.range_to_bin(self.range_m)

    @property
    def expected_doppler_bin(self) -> float:
        return P.velocity_to_bin(self.velocity_mps)


@dataclass
class Scene:
    targets: list = field(default_factory=list)
    noise_std: float = 0.01        #complex noise std per component
    dc_leakage: complex = 0.0      #constant transmit leakage offset
    iq_gain_imbalance: float = 0.0  #fractional q gain error
    iq_phase_imbalance: float = 0.0  #q phase error, rad
    seed: int = 0

    def generate(self) -> np.ndarray:
        """returns a (NC, NS) complex array, one row per chirp"""
        rng = np.random.default_rng(self.seed)
        n = np.arange(P.NS)
        k = np.arange(P.NC)
        data = np.zeros((P.NC, P.NS), dtype=np.complex128)

        for t in self.targets:
            f_beat = (2 * P.B * t.range_m / (P.C * P.TC)
                      + 2 * t.velocity_mps / P.LAMBDA)
            dphi_chirp = 2 * np.pi * (2 * t.velocity_mps / P.LAMBDA) * P.TR
            phase = (2 * np.pi * f_beat * n[None, :] / P.FS
                     + dphi_chirp * k[:, None] + t.phase0)
            data += t.amplitude * np.exp(1j * phase)

        if self.noise_std > 0:
            data += self.noise_std * (rng.standard_normal(data.shape)
                                      + 1j * rng.standard_normal(data.shape))

        data += self.dc_leakage

        #imbalance applied to the q channel
        if self.iq_gain_imbalance or self.iq_phase_imbalance:
            i = data.real
            q = data.imag
            g = 1.0 + self.iq_gain_imbalance
            q = g * (q * np.cos(self.iq_phase_imbalance)
                     + i * np.sin(self.iq_phase_imbalance))
            data = i + 1j * q

        return data

    def to_adc_codes(self, full_scale: float = 4.0) -> np.ndarray:
        """quantize to 12 bit offset binary codes, shape (NC, NS, 2)
        with [..., 0] = i and [..., 1] = q"""
        data = self.generate()
        scale = (P.ADC_MID - 1) / full_scale
        i = np.clip(np.round(data.real * scale) + P.ADC_MID, 0, 2**P.ADC_BITS - 1)
        q = np.clip(np.round(data.imag * scale) + P.ADC_MID, 0, 2**P.ADC_BITS - 1)
        return np.stack([i, q], axis=-1).astype(np.uint16)
