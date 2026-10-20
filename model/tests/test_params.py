"""Sanity checks on derived parameters (PLAN.md section 2)."""

import pytest

from model import params as P


def test_range_resolution():
    assert P.RANGE_RES == pytest.approx(0.75, abs=0.001)


def test_max_range():
    assert P.R_MAX == pytest.approx(96, abs=0.5)


def test_beat_slope():
    # ~5.21 kHz per metre
    assert P.BEAT_HZ_PER_M == pytest.approx(5210, rel=0.01)


def test_velocity_resolution():
    assert P.VEL_RES == pytest.approx(0.347, abs=0.001)


def test_max_velocity():
    assert P.V_MAX == pytest.approx(11.1, abs=0.05)


def test_frame_timing_budget():
    # acquisition must leave >30 ms for processing in a 50 ms frame
    assert P.FRAME_ACQ_TIME == pytest.approx(17.92e-3)
    assert P.FRAME_PERIOD - P.FRAME_ACQ_TIME > 30e-3


def test_bin_conversions_roundtrip():
    assert P.bin_to_range(P.range_to_bin(30.0)) == pytest.approx(30.0)
    assert P.bin_to_velocity(P.velocity_to_bin(5.0)) == pytest.approx(5.0)
    assert P.velocity_to_bin(0.0) == P.DOPPLER_ZERO_BIN
