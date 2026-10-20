#!/usr/bin/env python3
"""Measure the CFAR false-alarm rate on noise-only frames.

Sweeps the threshold offset so the default (12 dB ~ 1,021 log units) can be
validated or replaced with a measured value at M2. Every detection on a
noise-only frame is a false alarm.

Usage (from the repo root):
    python scripts/measure_pfa.py --frames 100
    python scripts/measure_pfa.py --frames 2000 --offsets 10,12,14
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import params as P
from model.chain_float import process_frame
from model.scene import Scene


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=100,
                    help="noise-only frames per offset (use thousands "
                         "for a trustworthy rate)")
    ap.add_argument("--offsets", default="10,12,14",
                    help="comma-separated offsets in dB")
    ap.add_argument("--noise", type=float, default=0.02,
                    help="noise std per component")
    ap.add_argument("--mode", default="CA", choices=["CA", "GO", "SO"])
    args = ap.parse_args()

    offsets = [float(x) for x in args.offsets.split(",")]
    cells_per_frame = P.N_RANGE_BINS * P.NC

    print(f"mode={args.mode}, noise_std={args.noise}, "
          f"{args.frames} frames x {cells_per_frame} cells")
    print(f"{'offset dB':>10} {'log units':>10} {'false alarms':>13} "
          f"{'per frame':>10} {'per cell':>10}")

    for off in offsets:
        total = 0
        for seed in range(args.frames):
            data = Scene(targets=[], noise_std=args.noise,
                         seed=seed).generate()
            _, dets = process_frame(data, offset_db=off, mode=args.mode)
            total += len(dets)
        per_frame = total / args.frames
        per_cell = total / (args.frames * cells_per_frame)
        print(f"{off:>10.1f} {off * P.LOG_UNITS_PER_DB:>10.0f} "
              f"{total:>13} {per_frame:>10.2f} {per_cell:>10.2e}")


if __name__ == "__main__":
    main()
