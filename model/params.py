"""System parameters for the FMCW radar (PLAN.md section 2).

Every parameter lives HERE and in rtl/pkg/radar_pkg.sv, and nowhere else.
Any change must update both files and docs/PLAN.md in the same commit.
"""

# --- Physical constants ---
C = 299_792_458.0  # speed of light, m/s

# --- RF profile (K-LC6 / K-LC5 FMCW) ---
F0 = 24.125e9           # carrier frequency, Hz (centre of 24.05-24.25 GHz band)
LAMBDA = C / F0         # wavelength, ~12.43 mm
B = 200e6               # chirp bandwidth, Hz
TC = 256e-6             # chirp ramp time, s (exactly NS samples at FS)
TR = 280e-6             # chirp repetition interval, s (TC + 24 us flyback)

# --- Sampling ---
FS = 1e6                # ADC sample rate per channel, Hz (Pmod AD1 max)
NS = 256                # samples per chirp = range FFT size
NC = 64                 # chirps per frame = Doppler FFT size
ADC_BITS = 12           # AD7476A resolution
ADC_MID = 2048          # offset-binary midpoint

# --- Frame timing ---
FRAME_ACQ_TIME = NC * TR          # 17.92 ms
FRAME_PERIOD = 50e-3              # 50 ms -> 20 fps
FCLK = 60e6                       # system clock, Hz

# --- Derived limits ---
RANGE_RES = C / (2 * B)                        # 0.7495 m per range bin
BEAT_HZ_PER_M = 2 * B / (C * TC)               # ~5.21 kHz per metre
R_MAX = (FS / 2) / BEAT_HZ_PER_M               # ~95.9 m
N_RANGE_BINS = NS // 2                         # keep bins 0..127 (positive beat)
VEL_RES = LAMBDA / (2 * NC * TR)               # 0.3467 m/s per Doppler bin
V_MAX = LAMBDA / (4 * TR)                      # +/- 11.09 m/s unambiguous
N_DOPPLER_BINS = NC                            # 64 bins after fftshift
DOPPLER_ZERO_BIN = NC // 2                     # bin 32 = zero speed

# --- CFAR defaults (PLAN.md section 5) ---
CFAR_TRAIN = 8          # training cells per side
CFAR_GUARD = 2          # guard cells per side
CFAR_OFFSET_DB = 12.0   # threshold offset above training mean
CFAR_MODE = "CA"        # CA | GO | SO
MAX_TARGETS = 32        # target_list capacity

# --- Log-power scaling (fixed-point stage, for reference) ---
LOG_UNITS_PER_LOG2 = 256   # L = 256 * log2(P); 256 units = 3.01 dB
LOG_UNITS_PER_DB = LOG_UNITS_PER_LOG2 / (10 * 0.3010299956639812)  # ~85.0


def range_to_bin(r_m: float) -> float:
    """Range in metres -> fractional range-FFT bin index."""
    return r_m / RANGE_RES


def velocity_to_bin(v_mps: float) -> float:
    """Radial velocity in m/s (positive = approaching) -> fractional
    Doppler bin index after fftshift (DOPPLER_ZERO_BIN = stationary).
    Wraps into [0, NC)."""
    return (DOPPLER_ZERO_BIN + v_mps / VEL_RES) % NC


def bin_to_range(b: float) -> float:
    return b * RANGE_RES


def bin_to_velocity(b: float) -> float:
    return (b - DOPPLER_ZERO_BIN) * VEL_RES
