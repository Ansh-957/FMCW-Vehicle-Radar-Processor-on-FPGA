"""system parameters, mirrored in rtl/pkg/radar_pkg.sv"""

#physical constants
C = 299_792_458.0  #speed of light, m/s

#rf profile
F0 = 24.125e9           #carrier frequency, Hz
LAMBDA = C / F0         #wavelength, ~12.43 mm
B = 200e6               #chirp bandwidth, Hz
TC = 256e-6             #chirp ramp time, s
TR = 280e-6             #chirp repetition interval, s

#sampling
FS = 1e6                #adc sample rate per channel, Hz
NS = 256                #samples per chirp, range fft size
NC = 64                 #chirps per frame, doppler fft size
ADC_BITS = 12
ADC_MID = 2048          #offset binary midpoint

#frame timing
FRAME_ACQ_TIME = NC * TR          #17.92 ms
FRAME_PERIOD = 50e-3              #50 ms, 20 fps
FCLK = 60e6                       #system clock, Hz

#derived limits
RANGE_RES = C / (2 * B)                        #0.7495 m per range bin
BEAT_HZ_PER_M = 2 * B / (C * TC)               #~5.21 kHz per metre
R_MAX = (FS / 2) / BEAT_HZ_PER_M               #~95.9 m
N_RANGE_BINS = NS // 2                         #keep bins 0..127
VEL_RES = LAMBDA / (2 * NC * TR)               #0.3467 m/s per doppler bin
V_MAX = LAMBDA / (4 * TR)                      #+/- 11.09 m/s unambiguous
N_DOPPLER_BINS = NC
DOPPLER_ZERO_BIN = NC // 2                     #bin 32 is zero speed

#fixed point widths
W_ADC = 12      #s12 after mid subtraction
W_DC = 13       #s13 after dc removal
W_WIN = 16      #s16 after windowing
W_FFT = 18      #s18 fft datapath
W_FRAME = 16    #s16 frame buffer cell per component
W_POWER = 37    #u37 power
W_LOG = 16      #u16 log power
W_COEF = 16     #u16 window coefficients
W_TWIDDLE = 18  #s18 Q1.17 twiddles

#fixed point constants, frozen at M2
WIN_SHIFT_RANGE = 13     #range window product shift, gain w/8192
WIN_SHIFT_DOPPLER = 16   #doppler window product shift, gain at most 1
FB_SHIFT_DEFAULT = 0     #frame buffer narrowing shift
#  0 is lossless with the default range fft schedule since halving all
#  8 stages bounds the output to the s16 envelope, raise for other schedules
CFAR_OFFSET_DEFAULT = 1021  #threshold offset in log units, ~12 dB
LOG_MANT_BITS = 8        #mantissa bits into the log2 lut

#fft per stage halving enables, index 0 is the first stage
#range halves every stage so any s16 input is overflow free
#doppler halves 4 of 6, the 4x gain keeps the noise floor above the
#quantizer, halving all 6 rounds the floor to zero power and costs
#~20 dB of detection snr, the sticky overflow flag covers the risk
FFT_SCALE_RANGE_DEFAULT = (1, 1, 1, 1, 1, 1, 1, 1)
FFT_SCALE_DOPPLER_DEFAULT = (1, 1, 1, 1, 0, 0)

#cfar defaults
CFAR_TRAIN = 8          #training cells per side
CFAR_GUARD = 2          #guard cells per side
CFAR_OFFSET_DB = 12.0   #threshold offset above training mean
CFAR_MODE = "CA"
MAX_TARGETS = 32

#log power scaling, 256 units per octave so 256 units is 3.01 dB
LOG_UNITS_PER_LOG2 = 256
LOG_UNITS_PER_DB = LOG_UNITS_PER_LOG2 / (10 * 0.3010299956639812)  #~85.0


def range_to_bin(r_m: float) -> float:
    """range in metres to fractional range fft bin"""
    return r_m / RANGE_RES


def velocity_to_bin(v_mps: float) -> float:
    """radial velocity to fractional doppler bin after fftshift,
    positive is approaching, wraps into [0, NC)"""
    return (DOPPLER_ZERO_BIN + v_mps / VEL_RES) % NC


def bin_to_range(b: float) -> float:
    return b * RANGE_RES


def bin_to_velocity(b: float) -> float:
    return (b - DOPPLER_ZERO_BIN) * VEL_RES


#test tone nco, mirrored in radar_pkg
N_TONES = 4
PHASE_W = 32
NCO_IDX_BITS = 8          #top bits of the phase word index the 256-entry lut
LFSR_SEED = 0xACE1
NOISE_SHIFT = 15          #rhu(s12(lfsr)*gain, 15), gain 32768 is unity


def fw_for_range_bin(k: int) -> int:
    """phase word so a tone lands in range fft bin k, k * 2**32 / NS"""
    return (int(k) << (PHASE_W - 8)) & 0xFFFFFFFF


def dphi_for_doppler_bin(d: int) -> int:
    """phase step per chirp so a tone lands in fftshifted doppler bin d"""
    u = (int(d) + NC // 2) % NC
    return (u * (1 << PHASE_W) // NC) & 0xFFFFFFFF
