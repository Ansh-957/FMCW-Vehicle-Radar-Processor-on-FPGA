#!/usr/bin/env python3
"""generates the rom .mem files, twiddles, windows, log lut and colour
map, the rtl reads them with $readmemh and the model parses the same
files so the two cannot drift, floats are fine here since this is the
table generator not the integer model

outputs one hex word per line into rtl/mem/
  hann256.mem    256 x u16 range window
  hann64.mem     64 x u16 doppler window
  twiddle128.mem 128 x 36 bit packed {re, im} Q1.17 of W_256^k, k 0 has
                 cos +1.0 which saturates to 131071
  log_lut.mem    256 x u8 of round(256*log2(1 + m/256))
  colormap.mem   256 x 24 bit rgb888 inferno palette
"""

import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "rtl", "mem")

Q17_MAX = (1 << 17) - 1


def write_mem(name, values, hex_digits):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w") as f:
        for v in values:
            f.write(f"{int(v):0{hex_digits}x}\n")
    print(f"wrote {path} ({len(values)} words)")


def hann_u16(n):
    w = np.hanning(n)
    return np.round(w * 65535).astype(np.int64)


def twiddles():
    k = np.arange(128)
    ang = -2 * np.pi * k / 256.0
    re = np.clip(np.round(np.cos(ang) * (1 << 17)), -Q17_MAX - 1, Q17_MAX)
    im = np.clip(np.round(np.sin(ang) * (1 << 17)), -Q17_MAX - 1, Q17_MAX)
    packed = []
    for r, i in zip(re.astype(np.int64), im.astype(np.int64)):
        r18 = int(r) & 0x3FFFF  #two's complement, 18 bits
        i18 = int(i) & 0x3FFFF
        packed.append((r18 << 18) | i18)
    return packed


def log_lut():
    m = np.arange(256)
    return np.round(256 * np.log2(1 + m / 256.0)).astype(np.int64)


def colormap():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rgb = (plt.get_cmap("inferno")(np.arange(256))[:, :3] * 255).round()
    rgb = rgb.astype(np.int64)
    return [(r << 16) | (g << 8) | b for r, g, b in rgb]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    write_mem("hann256.mem", hann_u16(256), 4)
    write_mem("hann64.mem", hann_u16(64), 4)
    write_mem("twiddle128.mem", twiddles(), 9)
    write_mem("log_lut.mem", log_lut(), 2)
    write_mem("colormap.mem", colormap(), 6)


if __name__ == "__main__":
    sys.exit(main())
