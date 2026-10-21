"""full bit exact chain, adc codes in, log map and target list out,
flags collects the sticky per stage overflow bits"""

import numpy as np

from .. import params as P
from . import backend, frontend
from .fft_engine import fft_fixed


def process_frame_fixed(codes,
                        fft_scale_range=None,
                        fft_scale_doppler=None,
                        fb_shift=P.FB_SHIFT_DEFAULT,
                        cfar_kwargs=None):
    """codes is (NC, NS, 2) u12 offset binary with [..., 0] = i,
    returns (logmap, detections, flags)"""
    flags = {}
    cfar_kwargs = cfar_kwargs or {}
    if fft_scale_range is None:
        fft_scale_range = list(P.FFT_SCALE_RANGE_DEFAULT)
    if fft_scale_doppler is None:
        fft_scale_doppler = list(P.FFT_SCALE_DOPPLER_DEFAULT)

    #front of the chain, per chirp
    s12 = frontend.adc_capture(codes)
    i13 = frontend.dc_remove(s12[:, :, 0])
    q13 = frontend.dc_remove(s12[:, :, 1])
    i16 = frontend.window_mult(i13, P.NS, P.WIN_SHIFT_RANGE,
                               flags, "range_window")
    q16 = frontend.window_mult(q13, P.NS, P.WIN_SHIFT_RANGE,
                               flags, "range_window")

    #range fft per chirp, keep the positive beat half
    rr, ri = fft_fixed(i16, q16, P.NS, fft_scale_range, flags, "range_fft")
    rr = rr[:, : P.N_RANGE_BINS]
    ri = ri[:, : P.N_RANGE_BINS]

    #narrow to s16 and corner turn to (range, chirp)
    fr = backend.frame_narrow(rr, fb_shift, flags, "frame_buffer").T
    fi = backend.frame_narrow(ri, fb_shift, flags, "frame_buffer").T

    #doppler pass per range bin
    dr_in = frontend.window_mult(fr, P.NC, P.WIN_SHIFT_DOPPLER,
                                 flags, "doppler_window")
    di_in = frontend.window_mult(fi, P.NC, P.WIN_SHIFT_DOPPLER,
                                 flags, "doppler_window")
    dr, di = fft_fixed(dr_in, di_in, P.NC, fft_scale_doppler,
                       flags, "doppler_fft")

    #fftshift as an address permutation, zero speed lands on bin 32
    shift_idx = (np.arange(P.NC) + P.DOPPLER_ZERO_BIN) % P.NC
    dr = dr[:, shift_idx]
    di = di[:, shift_idx]

    logmap = backend.log2_fixed(backend.power(dr, di))

    det = backend.cfar_fixed(logmap, **cfar_kwargs)
    peaks = backend.peak_detect_fixed(logmap, det)
    targets = backend.target_list_fixed(logmap, peaks)
    return logmap, targets, flags
