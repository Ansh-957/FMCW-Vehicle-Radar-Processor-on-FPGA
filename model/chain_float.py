"""floating point reference chain, behavioural sketch of the pipeline

dc removal, range window and fft keeping bins 0..127, corner turn,
doppler window and fft with fftshift, log power, cfar, 3x3 peak
detect, target list

the integer model in model/fixed/ is the binding reference, this one
checks the algorithm before quantization enters the picture
"""

from dataclasses import dataclass

import numpy as np

from . import params as P


@dataclass
class Detection:
    range_bin: int
    doppler_bin: int
    power_db: float
    snr_db: float

    @property
    def range_m(self) -> float:
        return P.bin_to_range(self.range_bin)

    @property
    def velocity_mps(self) -> float:
        return P.bin_to_velocity(self.doppler_bin)


def dc_remove(chirps: np.ndarray) -> np.ndarray:
    """subtract each chirp's own mean per channel, the hardware does the
    same with a pre pass over the fft input bank"""
    return chirps - chirps.mean(axis=1, keepdims=True)


def range_fft(chirps: np.ndarray) -> np.ndarray:
    """(NC, NS) time samples to (NC, NS//2) complex range profiles"""
    win = np.hanning(P.NS)
    spec = np.fft.fft(chirps * win[None, :], axis=1)
    return spec[:, : P.N_RANGE_BINS]  #positive beat half


def doppler_fft(range_profiles: np.ndarray) -> np.ndarray:
    """corner turn then per range bin window and fft, fftshift puts
    zero speed at bin 32"""
    corner = range_profiles.T
    win = np.hanning(P.NC)
    spec = np.fft.fft(corner * win[None, :], axis=1)
    return np.fft.fftshift(spec, axes=1)


def log_power(rd_map: np.ndarray) -> np.ndarray:
    p = rd_map.real**2 + rd_map.imag**2
    return 10 * np.log10(np.maximum(p, 1e-12))


def cfar(rd_db: np.ndarray,
         train: int = P.CFAR_TRAIN,
         guard: int = P.CFAR_GUARD,
         offset_db: float = P.CFAR_OFFSET_DB,
         mode: str = P.CFAR_MODE,
         exclude_zero_doppler: bool = False) -> np.ndarray:
    """cell averaging cfar along range for each doppler column, training
    means in linear power, at the edges only the existing side is used"""
    lin = 10 ** (rd_db / 10)
    n_r, n_d = lin.shape
    detect = np.zeros((n_r, n_d), dtype=bool)

    for d in range(n_d):
        if exclude_zero_doppler and d == P.DOPPLER_ZERO_BIN:
            continue
        col = lin[:, d]
        for r in range(n_r):
            lead = col[max(0, r - guard - train): max(0, r - guard)]
            lag = col[r + guard + 1: r + guard + 1 + train]
            sides = [s.mean() for s in (lead, lag) if s.size > 0]
            if not sides:
                continue
            if mode == "CA":
                noise = np.mean(sides) if len(sides) == 2 else sides[0]
            elif mode == "GO":
                noise = max(sides)
            elif mode == "SO":
                noise = min(sides)
            else:
                raise ValueError(f"unknown CFAR mode {mode!r}")
            detect[r, d] = col[r] > noise * 10 ** (offset_db / 10)
    return detect


def peak_detect(rd_db: np.ndarray, detect: np.ndarray) -> np.ndarray:
    """keep a detection only if it beats all 8 neighbours"""
    padded = np.pad(rd_db, 1, mode="constant", constant_values=-np.inf)
    out = detect.copy()
    rows, cols = np.nonzero(detect)
    for r, d in zip(rows, cols):
        window = padded[r: r + 3, d: d + 3]
        if rd_db[r, d] < window.max() or (window == rd_db[r, d]).sum() > 1:
            if rd_db[r, d] < window.max():
                out[r, d] = False
    return out


def target_list(rd_db: np.ndarray, peaks: np.ndarray,
                noise_db: float | None = None,
                max_targets: int = P.MAX_TARGETS) -> list:
    """collect detections strongest first, capped, snr against the map
    median as a robust floor estimate"""
    if noise_db is None:
        noise_db = float(np.median(rd_db))
    dets = [Detection(int(r), int(d), float(rd_db[r, d]),
                      float(rd_db[r, d] - noise_db))
            for r, d in zip(*np.nonzero(peaks))]
    dets.sort(key=lambda t: t.power_db, reverse=True)
    return dets[:max_targets]


def process_frame(chirps: np.ndarray, **cfar_kwargs) -> tuple:
    """full chain, (NC, NS) complex samples to (rd_map_db, detections)"""
    x = dc_remove(chirps)
    rp = range_fft(x)
    rd = doppler_fft(rp)
    rd_db = log_power(rd)
    det = cfar(rd_db, **cfar_kwargs)
    peaks = peak_detect(rd_db, det)
    return rd_db, target_list(rd_db, peaks)


def plot_frame(rd_db: np.ndarray, detections: list, path: str) -> None:
    """save a range doppler heat map with detections marked"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 6))
    extent = [P.bin_to_velocity(0), P.bin_to_velocity(P.NC - 1), 0, P.R_MAX]
    im = ax.imshow(rd_db, origin="lower", aspect="auto", extent=extent,
                   cmap="inferno")
    for t in detections:
        ax.plot(t.velocity_mps, t.range_m, "c+", markersize=12, mew=2)
    ax.set_xlabel("velocity (m/s, + approaching)")
    ax.set_ylabel("range (m)")
    ax.set_title(f"Range-Doppler map, {len(detections)} target(s)")
    fig.colorbar(im, label="power (dB)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
