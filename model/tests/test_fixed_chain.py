"""end to end fixed chain tests, must find what the float chain finds
with under 1 dB of detection snr loss and no overflow on nominal scenes"""

import numpy as np
import pytest

from model import params as P
from model.chain_float import process_frame
from model.fixed.chain import process_frame_fixed
from model.scene import Scene, Target


def doppler_err(a, b):
    d = (a - b) % P.NC
    return min(d, P.NC - d)


def find(dets, target, tol=1.0):
    for det in dets:
        if (abs(det.range_bin - target.expected_range_bin) <= tol
                and doppler_err(det.doppler_bin,
                                target.expected_doppler_bin) <= tol):
            return det
    return None


def detection_snr_db_float(rd_db, det):
    return (rd_db[det.range_bin, det.doppler_bin]
            - float(np.median(rd_db)))


def detection_snr_db_fixed(logmap, det):
    peak = int(logmap[det.range_bin, det.doppler_bin])
    flat = np.sort(np.asarray(logmap).ravel())
    median = int(flat[flat.size // 2])
    return (peak - median) / P.LOG_UNITS_PER_DB


def test_known_answer_30m_fixed():
    scene = Scene(targets=[Target(range_m=30.0, velocity_mps=0.0)])
    logmap, dets, flags = process_frame_fixed(scene.to_adc_codes())
    assert not any(flags.values()), f"overflow: {flags}"
    det = find(dets, scene.targets[0])
    assert det is not None
    assert det.range_bin == pytest.approx(40, abs=1)


def test_moving_target_fixed():
    t = Target(range_m=20.0, velocity_mps=5.0)
    logmap, dets, flags = process_frame_fixed(
        Scene(targets=[t]).to_adc_codes())
    assert not any(flags.values())
    assert find(dets, t) is not None


def test_multi_target_fixed_matches_float():
    """every target the float chain finds the fixed chain also finds"""
    targets = [
        Target(range_m=10.0, velocity_mps=0.0, amplitude=1.0),
        Target(range_m=35.0, velocity_mps=4.0, amplitude=0.5),
        Target(range_m=70.0, velocity_mps=-6.0, amplitude=0.7),
    ]
    scene = Scene(targets=targets, noise_std=0.02,
                  dc_leakage=0.3 + 0.2j, iq_gain_imbalance=0.01)
    _, dets_float = process_frame(scene.generate())
    _, dets_fixed, flags = process_frame_fixed(scene.to_adc_codes())
    assert not any(flags.values())
    for t in targets:
        assert find(dets_float, t) is not None
        assert find(dets_fixed, t) is not None


def test_snr_loss_under_1db():
    """the acceptance criterion that froze the widths"""
    cases = [
        Target(range_m=30.0, velocity_mps=0.0, amplitude=1.0),
        Target(range_m=30.0, velocity_mps=0.0, amplitude=0.1),   #-20 dB
        Target(range_m=80.0, velocity_mps=-8.0, amplitude=0.3),
        Target(range_m=8.0, velocity_mps=3.0, amplitude=0.5),
    ]
    for t in cases:
        scene = Scene(targets=[t], noise_std=0.02, seed=7)
        rd_db, dets_f = process_frame(scene.generate())
        #drive the adc like a sensibly gained front end, not the 4x
        #headroom default meant for 4 target scenes
        logmap, dets_x, flags = process_frame_fixed(
            scene.to_adc_codes(full_scale=1.5))
        assert not any(flags.values())
        df = find(dets_f, t)
        dx = find(dets_x, t)
        assert df is not None and dx is not None
        loss = (detection_snr_db_float(rd_db, df)
                - detection_snr_db_fixed(logmap, dx))
        assert loss < 1.0, f"{t}: SNR loss {loss:.2f} dB"


def test_full_scale_scene_no_overflow():
    """four strong targets at once must not saturate anywhere"""
    targets = [Target(range_m=r, velocity_mps=v, amplitude=0.9)
               for r, v in [(10, 0), (30, 5), (50, -5), (90, 10)]]
    _, _, flags = process_frame_fixed(
        Scene(targets=targets, noise_std=0.02).to_adc_codes())
    assert not any(flags.values()), f"overflow: {flags}"


def test_noise_only_fixed():
    scene = Scene(targets=[], noise_std=0.05, seed=42)
    _, dets, flags = process_frame_fixed(scene.to_adc_codes())
    assert not any(flags.values())
    assert len(dets) <= 8
