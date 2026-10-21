"""per block tests for the fixed point model, known answers plus
quantization error snr against the float reference"""

import numpy as np
import pytest

from model import params as P
from model.fixed import backend, frontend, roms
from model.fixed.fft_engine import fft_fixed
from model.fixed.util import rhu, rdiv, sat_signed


def snr_db(ref, err):
    return 10 * np.log10(np.sum(np.abs(ref) ** 2)
                         / max(np.sum(np.abs(err) ** 2), 1e-30))


def test_rhu_rounds_half_up_including_negatives():
    assert rhu(3, 1) == 2          #1.5 to 2
    assert rhu(-3, 1) == -1        #-1.5 to -1, toward +inf
    assert rhu(5, 2) == 1          #1.25 to 1
    assert rhu(-5, 2) == -1        #-1.25 to -1
    assert rhu(7, 0) == 7          #no op


def test_saturation_sets_sticky_flag():
    flags = {}
    sat_signed(np.array([40000]), 16, flags, "s")
    assert flags["s"] is True
    sat_signed(np.array([100]), 16, flags, "s")
    assert flags["s"] is True  #sticky


def test_rdiv():
    assert rdiv(10, 4) == 3   #2.5 to 3
    assert rdiv(9, 4) == 2    #2.25 to 2
    assert rdiv(16, 16) == 1


def test_adc_capture():
    assert frontend.adc_capture(2048) == 0
    assert frontend.adc_capture(0) == -2048
    assert frontend.adc_capture(4095) == 2047


def test_dc_remove_exact_and_fits_s13():
    rng = np.random.default_rng(0)
    x = rng.integers(-2048, 2048, size=(P.NC, P.NS))
    y = frontend.dc_remove(x)
    mean = rhu(x.sum(axis=-1, keepdims=True), 8)
    assert np.array_equal(y, x - mean)
    assert np.all(np.abs(y) < (1 << (P.W_DC - 1)) + 1)


def test_dc_remove_kills_constant_offset():
    x = np.full((1, P.NS), 1000, dtype=np.int64)
    assert np.all(frontend.dc_remove(x) == 0)


def test_window_rom_matches_float_hann():
    for n in (64, 256):
        w = roms.hann(n)
        ref = np.round(np.hanning(n) * 65535)
        assert np.array_equal(w, ref.astype(np.int64))


def test_window_mult_no_saturation_at_full_scale():
    flags = {}
    x = np.full((1, P.NS), 4095, dtype=np.int64)
    frontend.window_mult(x, P.NS, P.WIN_SHIFT_RANGE, flags, "w")
    assert flags["w"] is False  #4095*65535 >> 13 = 32760 < 32767


def test_window_mult_snr():
    rng = np.random.default_rng(1)
    x = rng.integers(-4096, 4097, size=(8, P.NS))
    y = frontend.window_mult(x, P.NS, P.WIN_SHIFT_RANGE)
    ref = x * np.hanning(P.NS) * (65535 / (1 << P.WIN_SHIFT_RANGE))
    assert snr_db(ref, ref - y) > 60


def test_fft_twiddle_rom_q117():
    twr, twi = roms.twiddles()
    assert twr[0] == 131071 and twi[0] == 0  #+1.0 saturated in Q1.17
    ref_r = np.round(np.cos(-2 * np.pi * np.arange(128) / 256) * (1 << 17))
    ref_r[0] = 131071
    assert np.array_equal(twr, ref_r.astype(np.int64))


def test_fft_impulse():
    """an impulse spreads evenly, every bin near amplitude over n with the
    default schedule, twiddle rounding can leave one lsb"""
    for n in (64, 128, 256):
        xr = np.zeros(n, dtype=np.int64)
        xr[0] = 16384
        yr, yi = fft_fixed(xr, np.zeros(n, dtype=np.int64), n)
        assert np.all(np.abs(yr - 16384 // n) <= 1)
        assert np.all(np.abs(yi) <= 1)


def test_fft_dc_input():
    """constant input lands in bin 0 at the input value, the gain of n
    cancels the 1/n scaling, other bins near zero"""
    for n in (64, 128, 256):
        xr = np.full(n, 1000, dtype=np.int64)
        yr, yi = fft_fixed(xr, np.zeros(n, dtype=np.int64), n)
        assert abs(yr[0] - 1000) <= 1
        assert np.all(np.abs(yr[1:]) <= 1) and np.all(np.abs(yi) <= 1)


@pytest.mark.parametrize("n", [64, 128, 256])
def test_fft_tone_every_bin(n):
    """a complex tone in bin k lands in bin k"""
    A = 20000
    t = np.arange(n)
    for k in range(0, n, max(1, n // 32)):  #sample 32 bins for speed
        ph = 2 * np.pi * k * t / n
        xr = np.round(A * np.cos(ph)).astype(np.int64)
        xi = np.round(A * np.sin(ph)).astype(np.int64)
        yr, yi = fft_fixed(xr, xi, n)
        mag2 = yr.astype(float) ** 2 + yi.astype(float) ** 2
        assert int(np.argmax(mag2)) == k
        assert mag2[k] > 0.9 * A * A


@pytest.mark.parametrize("n", [64, 256])
def test_fft_random_snr_vs_float(n):
    rng = np.random.default_rng(2)
    xr = rng.integers(-20000, 20001, size=(16, n))
    xi = rng.integers(-20000, 20001, size=(16, n))
    flags = {}
    yr, yi = fft_fixed(xr, xi, n, flags=flags, stage="fft")
    assert flags["fft"] is False  #full halving schedule cannot overflow
    ref = np.fft.fft(xr + 1j * xi, axis=-1) / n
    err = ref - (yr + 1j * yi)
    assert snr_db(ref, err) > 55


def test_fft_scale_schedule():
    """disabling one halving stage doubles the output"""
    rng = np.random.default_rng(3)
    xr = rng.integers(-1000, 1001, size=64)
    xi = np.zeros(64, dtype=np.int64)
    full, _ = fft_fixed(xr, xi, 64)
    sched = [True] * 5 + [False]
    double, _ = fft_fixed(xr, xi, 64, scale_sched=sched)
    assert np.all(np.abs(double - 2 * full) <= 2)


def test_fft_back_to_back_is_stateless():
    rng = np.random.default_rng(4)
    xr = rng.integers(-20000, 20001, size=256)
    xi = rng.integers(-20000, 20001, size=256)
    a = fft_fixed(xr, xi, 256)
    b = fft_fixed(xr, xi, 256)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_power_exact():
    assert backend.power(-131071, 131071) == 2 * 131071 ** 2
    assert backend.power(0, 0) == 0


def test_log2_fixed_known_answers():
    assert backend.log2_fixed(0) == 0
    assert backend.log2_fixed(1) == 0
    assert backend.log2_fixed(2) == 256      #one octave
    assert backend.log2_fixed(4) == 512
    assert backend.log2_fixed(3) == 256 + roms.log_lut()[128]


def test_log2_fixed_accuracy():
    rng = np.random.default_rng(5)
    p = rng.integers(1, 1 << 36, size=2000)
    L = backend.log2_fixed(p)
    ref = 256 * np.log2(p.astype(float))
    #8 bit mantissa truncation bounds the error near 2 log units
    assert np.max(np.abs(L - ref)) < 2.0


def test_cfar_fixed_single_target():
    lm = np.full((P.N_RANGE_BINS, P.NC), 1000, dtype=np.int64)
    lm[40, 32] = 3000
    det = backend.cfar_fixed(lm)
    assert det[40, 32]
    assert det.sum() == 1


def test_cfar_fixed_edge_cells_use_one_side():
    lm = np.full((P.N_RANGE_BINS, P.NC), 1000, dtype=np.int64)
    lm[0, 10] = 3000    #no lead cells at all
    lm[127, 20] = 3000  #no lag cells
    det = backend.cfar_fixed(lm)
    assert det[0, 10] and det[127, 20]


def test_cfar_fixed_exclude_zero_doppler():
    lm = np.full((P.N_RANGE_BINS, P.NC), 1000, dtype=np.int64)
    lm[40, P.DOPPLER_ZERO_BIN] = 5000
    det = backend.cfar_fixed(lm, exclude_zero_doppler=True)
    assert not det.any()


def test_peak_detect_tie_break_is_deterministic():
    lm = np.zeros((P.N_RANGE_BINS, P.NC), dtype=np.int64)
    lm[50, 30] = lm[50, 31] = 4000  #plateau of two equal cells
    det = np.zeros_like(lm, dtype=bool)
    det[50, 30] = det[50, 31] = True
    peaks = backend.peak_detect_fixed(lm, det)
    assert peaks[50, 30] and not peaks[50, 31]  #smaller index wins


def test_target_list_cap_and_order():
    lm = np.zeros((P.N_RANGE_BINS, P.NC), dtype=np.int64)
    peaks = np.zeros_like(lm, dtype=bool)
    for i in range(40):  #more than the cap
        lm[i * 3, 5] = 1000 + i
        peaks[i * 3, 5] = True
    dets = backend.target_list_fixed(lm, peaks)
    assert len(dets) == P.MAX_TARGETS
    powers = [d.log_power for d in dets]
    assert powers == sorted(powers, reverse=True)
    assert dets[0].log_power == 1039


def test_display_map():
    lm = np.array([[0, 5000, 70000]], dtype=np.int64)
    px = backend.display_map(lm, black_level=4000, contrast_shift=2)
    assert px[0, 0] == 0          #below black level floors at 0
    assert px[0, 1] == 250        #(5000-4000) >> 2
    assert px[0, 2] == 255        #clamped
