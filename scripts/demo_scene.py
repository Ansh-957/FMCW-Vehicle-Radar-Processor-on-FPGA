#!/usr/bin/env python3
"""M1 demo: synthesize a scene, run the float chain, save a plot to out/.

Run from the repo root:  python scripts/demo_scene.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import params as P
from model.chain_float import process_frame, plot_frame
from model.scene import Scene, Target


def main():
    targets = [
        Target(range_m=12.0, velocity_mps=0.0, amplitude=1.0),   # parked car
        Target(range_m=35.0, velocity_mps=6.5, amplitude=0.6),   # approaching
        Target(range_m=70.0, velocity_mps=-9.0, amplitude=0.8),  # receding
    ]
    scene = Scene(targets=targets, noise_std=0.02,
                  dc_leakage=0.3 + 0.2j, iq_gain_imbalance=0.01)
    rd_db, dets = process_frame(scene.generate())

    print(f"{len(dets)} detection(s):")
    print(f"{'range bin':>10} {'range m':>9} {'dopp bin':>9} "
          f"{'speed m/s':>10} {'power dB':>9}")
    for d in dets:
        print(f"{d.range_bin:>10} {d.range_m:>9.2f} {d.doppler_bin:>9} "
              f"{d.velocity_mps:>10.2f} {d.power_db:>9.1f}")

    for t in targets:
        print(f"expected: range bin {t.expected_range_bin:.1f}, "
              f"Doppler bin {t.expected_doppler_bin:.1f}")

    os.makedirs("out", exist_ok=True)
    path = os.path.join("out", "rd_map.png")
    plot_frame(rd_db, dets, path)
    print(f"saved {path}")

    # False-alarm check: same chain on noise-only frames. Every detection
    # here is a false alarm (the chronic one is the DC residual at
    # range bin 0, Doppler bin 32, which windowed DC removal leaves behind).
    n_frames = 10
    total_fa = 0
    for seed in range(n_frames):
        _, fa = process_frame(Scene(targets=[], noise_std=0.02,
                                    seed=seed).generate())
        total_fa += len(fa)
    cells = P.N_RANGE_BINS * P.NC * n_frames
    print(f"noise-only: {total_fa} false alarm(s) over {n_frames} frames "
          f"({total_fa / cells:.2e} per cell)")


if __name__ == "__main__":
    main()
