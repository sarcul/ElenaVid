"""Synthetic room impulse responses: early reflections + frequency-dependent late decay.

The late tail is built frame by frame in the frequency domain (random phase, magnitude decaying
with a per-frequency RT60), so air absorption and bass bloom come out naturally.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import oaconvolve

from ..config import SR
from . import dsp

SPACES = {
    # name: rt60 (low, mid, high), predelay s, early taps [(delay s, gain)], length s, width
    "hall": ((2.5, 1.9, 1.05), 0.022, [(0.011, .55), (0.019, .45), (0.027, .40), (0.034, .33),
                                       (0.046, .30), (0.058, .24), (0.071, .2)], 4.0, 0.9),
    "dome": ((2.8, 2.2, 1.2), 0.03, [(0.18, .5), (0.186, .35), (0.365, .3), (0.372, .2),
                                     (0.55, .14)], 4.5, 1.0),
    "church": ((5.6, 4.6, 2.6), 0.035, [(0.018, .5), (0.031, .45), (0.044, .4), (0.063, .35),
                                         (0.081, .3), (0.102, .25)], 8.0, 1.0),
    "tall_room": ((1.4, 1.3, 0.9), 0.010, [(0.006, .6), (0.011, .5), (0.017, .4), (0.024, .35)],
                  2.5, 0.8),
    "parlour": ((0.65, 0.6, 0.4), 0.004, [(0.003, .5), (0.007, .45), (0.012, .35)], 1.2, 0.7),
    "small_room": ((0.55, 0.45, 0.3), 0.003, [(0.003, .55), (0.006, .45), (0.010, .35)], 1.0, 0.7),
    "platform": ((1.7, 1.4, 0.8), 0.015, [(0.009, .5), (0.021, .45), (0.033, .4), (0.045, .4),
                                          (0.057, .38), (0.069, .35)], 3.0, 1.0),
    "street": ((0.8, 0.7, 0.45), 0.008, [(0.062, .35), (0.11, .25), (0.17, .15)], 1.6, 1.0),
    "square": ((0.6, 0.55, 0.35), 0.006, [(0.045, .4), (0.09, .3), (0.14, .2), (0.21, .12)],
               1.4, 1.0),
    "trattoria": ((0.75, 0.65, 0.45), 0.005, [(0.004, .5), (0.009, .45), (0.015, .4)], 1.3, 0.8),
    "vision": ((3.8, 3.2, 1.4), 0.05, [(0.03, .3), (0.05, .25)], 5.0, 1.0),
    "cave": ((1.0, 0.9, 0.6), 0.0, [], 1.5, 0.6),
}
_CACHE = {}


def make_ir(name: str, seed: int = 7):
    if name in _CACHE:
        return _CACHE[name]
    (rl, rm, rh), pre, taps, length, width = SPACES[name]
    rng = np.random.default_rng(seed + hash(name) % 1000)
    n = int(length * SR)
    frame = 1024
    hop = 512
    freqs = np.fft.rfftfreq(frame, 1 / SR)
    # RT60 per frequency: log-interpolate low (<=200 Hz) / mid (1 kHz) / high (>=6 kHz)
    lf = np.log10(np.maximum(freqs, 20))
    rt = np.interp(lf, [np.log10(200), 3.0, np.log10(6000), np.log10(20000)],
                   [rl, rm, rh, rh * 0.6])
    win = np.hanning(frame)
    out = np.zeros((2, n + frame))
    nframes = n // hop
    # the late field: decorrelated left/right with controlled inter-channel correlation
    for ch in range(2):
        for k in range(nframes):
            t = k * hop / SR
            mag = np.exp(-6.9078 * t / rt)
            ph = rng.uniform(0, 2 * np.pi, len(freqs))
            spec = mag * np.exp(1j * ph)
            spec[0] = 0
            seg = np.fft.irfft(spec, frame) * win
            out[ch, k * hop:k * hop + frame] += seg
    out = out[:, :n]
    mid = 0.5 * (out[0] + out[1])
    side = 0.5 * (out[0] - out[1])
    out = np.stack([mid + width * side, mid - width * side])
    t = np.arange(n) / SR
    onset = np.clip((t - pre) / 0.03, 0, 1)
    out *= onset
    out /= np.sqrt(np.sum(out ** 2) / 2) + 1e-12
    # early reflections: discrete, slightly low-passed, alternating sides
    er = np.zeros((2, n))
    for i, (d, g) in enumerate(taps):
        idx = int((pre + d) * SR)
        if idx < n:
            side_g = (1.0, 0.6) if i % 2 == 0 else (0.6, 1.0)
            er[0, idx] += g * side_g[0]
            er[1, idx] += g * side_g[1]
    er = np.stack([dsp.eq(er[c], "lp", 6500, 0.7) for c in range(2)])
    ir = out * 0.9 + er * 1.6
    ir /= np.sqrt(np.sum(ir ** 2) / 2) + 1e-12
    _CACHE[name] = ir.astype(np.float32)
    return _CACHE[name]


def convolve_stereo(L, R, name):
    """Return the wet stereo signal of an L/R send through the named space."""
    ir = make_ir(name)
    n = len(L)
    wl = oaconvolve(L, ir[0])[:n] if np.any(L) else np.zeros(n, np.float32)
    wr = oaconvolve(R, ir[1])[:n] if np.any(R) else np.zeros(n, np.float32)
    # a little cross-feed so mono sends still bloom in stereo
    return (0.85 * wl + 0.15 * wr).astype(np.float32), (0.85 * wr + 0.15 * wl).astype(np.float32)
