"""M1 acceptance tests: injected targets must appear within +/-1 bin of the
expected range and Doppler position (PLAN.md section 10, M1)."""

import os

import numpy as np
import pytest

from model import params as P
from model.chain_float import process_frame, plot_frame
from model.scene import Scene, Target


def doppler_err(a: int, b: float) -> float:
    """Circular distance in Doppler bins (the axis wraps)."""
    d = (a - b) % P.NC
    return min(d, P.NC - d)


def assert_detected(detections, target, tol=1.0):
    for det in detections:
        if (abs(det.range_bin - target.expected_range_bin) <= tol
                and doppler_err(det.doppler_bin,
                                target.expected_doppler_bin) <= tol):
            return det
    raise AssertionError(
        f"target at range bin {target.expected_range_bin:.1f}, "
        f"Doppler bin {target.expected_doppler_bin:.1f} not found in "
        f"{[(d.range_bin, d.doppler_bin) for d in detections]}")


def test_known_answer_30m():
    """PLAN.md section 9: a target at 30 m appears in range bin 40."""
    scene = Scene(targets=[Target(range_m=30.0, velocity_mps=0.0)])
    rd_db, dets = process_frame(scene.generate())
    det = assert_detected(dets, scene.targets[0])
    assert det.range_bin == pytest.approx(40, abs=1)


def test_single_stationary_target():
    t = Target(range_m=45.0, velocity_mps=0.0, amplitude=1.0)
    _, dets = process_frame(Scene(targets=[t]).generate())
    assert_detected(dets, t)


def test_single_moving_target():
    t = Target(range_m=20.0, velocity_mps=5.0)
    _, dets = process_frame(Scene(targets=[t]).generate())
    det = assert_detected(dets, t)
    assert det.velocity_mps == pytest.approx(5.0, abs=P.VEL_RES)


def test_receding_target():
    t = Target(range_m=60.0, velocity_mps=-8.0)
    _, dets = process_frame(Scene(targets=[t]).generate())
    assert_detected(dets, t)


def test_multiple_targets():
    targets = [
        Target(range_m=10.0, velocity_mps=0.0, amplitude=1.0),
        Target(range_m=35.0, velocity_mps=4.0, amplitude=0.5),
        Target(range_m=70.0, velocity_mps=-6.0, amplitude=0.7),
    ]
    _, dets = process_frame(Scene(targets=targets).generate())
    for t in targets:
        assert_detected(dets, t)


def test_dc_leakage_removed():
    """Strong transmit leakage must not produce a false target at bin 0."""
    t = Target(range_m=25.0, velocity_mps=2.0)
    scene = Scene(targets=[t], dc_leakage=0.5 + 0.3j)
    _, dets = process_frame(scene.generate())
    assert_detected(dets, t)
    for det in dets:
        assert not (det.range_bin == 0
                    and det.doppler_bin == P.DOPPLER_ZERO_BIN)


def test_iq_imbalance_tolerated():
    t = Target(range_m=40.0, velocity_mps=3.0)
    scene = Scene(targets=[t], iq_gain_imbalance=0.02,
                  iq_phase_imbalance=np.deg2rad(2.0))
    _, dets = process_frame(scene.generate())
    assert_detected(dets, t)


def test_straddling_target_isolated():
    """A weak target exactly between two range bins, far from anything
    else, must still be detected despite the ~1.4 dB Hann scalloping loss."""
    t = Target(range_m=P.bin_to_range(80.5), velocity_mps=0.0, amplitude=0.35)
    strong = Target(range_m=30.0, velocity_mps=0.0, amplitude=1.0)
    _, dets = process_frame(Scene(targets=[strong, t],
                                  noise_std=0.01, seed=1).generate())
    assert_detected(dets, t)


def test_weak_straddler_masked_in_ca_recovered_by_so():
    """A weak straddling target inside a strong target's CFAR training
    window is masked under CA/GO (the strong peak inflates the training
    mean) but recovered by SO. This documents the masking behaviour the
    CFAR mode register exists to address."""
    strong = Target(range_m=30.0, velocity_mps=0.0, amplitude=1.0)  # bin 40
    weak = Target(range_m=P.bin_to_range(46.5), velocity_mps=0.0,
                  amplitude=0.35)  # -9 dB, 6.5 bins away: inside guard+train
    data = Scene(targets=[strong, weak], noise_std=0.01, seed=1).generate()

    _, dets_ca = process_frame(data, mode="CA")
    with pytest.raises(AssertionError):
        assert_detected(dets_ca, weak)  # masked: known CA limitation

    _, dets_so = process_frame(data, mode="SO")
    assert_detected(dets_so, weak)  # SO's smaller-side mean recovers it


def test_noise_only_few_false_alarms():
    scene = Scene(targets=[], noise_std=0.05, seed=42)
    _, dets = process_frame(scene.generate())
    # CFAR controls the false-alarm rate; allow a small residue.
    assert len(dets) <= 5


def test_speed_aliasing():
    """A target beyond +/-V_MAX wraps to the predicted aliased bin."""
    t = Target(range_m=50.0, velocity_mps=15.0)  # > 11.1 m/s, aliases
    _, dets = process_frame(Scene(targets=[t]).generate())
    assert_detected(dets, t)  # expected_doppler_bin already wraps


def test_plot_frame(tmp_path):
    scene = Scene(targets=[Target(range_m=30.0, velocity_mps=5.0),
                           Target(range_m=60.0, velocity_mps=-3.0)])
    rd_db, dets = process_frame(scene.generate())
    out = os.path.join(tmp_path, "rd_map.png")
    plot_frame(rd_db, dets, out)
    assert os.path.getsize(out) > 0
