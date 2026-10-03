"""Numba DSP kernels shared by every tier. Everything is synthesised; no samples are used."""
from __future__ import annotations

import math

import numpy as np
from numba import njit

from ..config import SR

TWO_PI = 2.0 * math.pi


# ------------------------------------------------------------------ oscillators

@njit(cache=True, fastmath=True)
def _polyblep(t, dt):
    if t < dt:
        t /= dt
        return t + t - t * t - 1.0
    elif t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    return 0.0


@njit(cache=True, fastmath=True)
def saw_blep(freq, phase0=0.0):
    """Band-limited sawtooth from a per-sample frequency array (Hz)."""
    n = freq.shape[0]
    out = np.empty(n)
    ph = phase0
    for i in range(n):
        dt = freq[i] / SR
        out[i] = 2.0 * ph - 1.0 - _polyblep(ph, dt)
        ph += dt
        if ph >= 1.0:
            ph -= 1.0
    return out


@njit(cache=True, fastmath=True)
def pulse_blep(freq, width, phase0=0.0):
    """Band-limited pulse wave; width is a per-sample duty array (0..1)."""
    n = freq.shape[0]
    out = np.empty(n)
    ph = phase0
    for i in range(n):
        dt = freq[i] / SR
        w = width[i]
        v = 1.0 if ph < w else -1.0
        v += _polyblep(ph, dt)
        ph2 = ph - w
        if ph2 < 0.0:
            ph2 += 1.0
        v -= _polyblep(ph2, dt)
        out[i] = v
        ph += dt
        if ph >= 1.0:
            ph -= 1.0
    return out


@njit(cache=True, fastmath=True)
def phase_from_freq(freq, phase0=0.0):
    n = freq.shape[0]
    out = np.empty(n)
    ph = phase0
    for i in range(n):
        out[i] = ph
        ph += freq[i] / SR
        ph -= math.floor(ph)
    return out


@njit(cache=True, fastmath=True)
def additive(freq, amps, nharm, phases):
    """Sum of harmonics k*f with per-harmonic amplitude array amps[k] (static), anti-aliased."""
    n = freq.shape[0]
    out = np.zeros(n)
    ph = np.zeros(nharm)
    for k in range(nharm):
        ph[k] = phases[k]
    for i in range(n):
        f = freq[i]
        s = 0.0
        for k in range(nharm):
            fk = f * (k + 1)
            if fk < 0.45 * SR:
                g = amps[k]
                if fk > 0.38 * SR:
                    g *= (0.45 * SR - fk) / (0.07 * SR)
                s += g * math.sin(TWO_PI * ph[k])
            ph[k] += fk / SR
            ph[k] -= math.floor(ph[k])
        out[i] = s
    return out


# ------------------------------------------------------------------ filters

@njit(cache=True, fastmath=True)
def onepole_lp(x, a):
    """y[n] = (1-a) x[n] + a y[n-1]; a is a per-sample array."""
    n = x.shape[0]
    y = np.empty(n)
    z = 0.0
    for i in range(n):
        z = (1.0 - a[i]) * x[i] + a[i] * z
        y[i] = z
    return y


@njit(cache=True, fastmath=True)
def onepole_hp(x, a):
    n = x.shape[0]
    y = np.empty(n)
    z = 0.0
    for i in range(n):
        z = (1.0 - a[i]) * x[i] + a[i] * z
        y[i] = x[i] - z
    return y


def lp_coef(fc):
    """One-pole coefficient for cutoff fc (Hz, scalar or array)."""
    return np.exp(-2.0 * np.pi * np.asarray(fc, dtype=np.float64) / SR)


@njit(cache=True, fastmath=True)
def biquad(x, b0, b1, b2, a1, a2):
    n = x.shape[0]
    y = np.empty(n)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(n):
        v = b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2 = x1
        x1 = x[i]
        y2 = y1
        y1 = v
        y[i] = v
    return y


def rbj(kind, f0, q=0.707, gain_db=0.0):
    """Audio-EQ-cookbook biquad coefficients."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / SR
    cs, sn = np.cos(w0), np.sin(w0)
    alpha = sn / (2 * q)
    if kind == "lp":
        b = [(1 - cs) / 2, 1 - cs, (1 - cs) / 2]
        a = [1 + alpha, -2 * cs, 1 - alpha]
    elif kind == "hp":
        b = [(1 + cs) / 2, -(1 + cs), (1 + cs) / 2]
        a = [1 + alpha, -2 * cs, 1 - alpha]
    elif kind == "bp":
        b = [alpha, 0.0, -alpha]
        a = [1 + alpha, -2 * cs, 1 - alpha]
    elif kind == "peak":
        b = [1 + alpha * A, -2 * cs, 1 - alpha * A]
        a = [1 + alpha / A, -2 * cs, 1 - alpha / A]
    elif kind == "lowshelf":
        sq = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cs + sq), 2 * A * ((A - 1) - (A + 1) * cs),
             A * ((A + 1) - (A - 1) * cs - sq)]
        a = [(A + 1) + (A - 1) * cs + sq, -2 * ((A - 1) + (A + 1) * cs), (A + 1) + (A - 1) * cs - sq]
    elif kind == "highshelf":
        sq = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cs + sq), -2 * A * ((A - 1) + (A + 1) * cs),
             A * ((A + 1) + (A - 1) * cs - sq)]
        a = [(A + 1) - (A - 1) * cs + sq, 2 * ((A - 1) - (A + 1) * cs), (A + 1) - (A - 1) * cs - sq]
    else:
        raise ValueError(kind)
    return b[0] / a[0], b[1] / a[0], b[2] / a[0], a[1] / a[0], a[2] / a[0]


def eq(x, kind, f0, q=0.707, gain_db=0.0):
    return biquad(np.ascontiguousarray(x, dtype=np.float64), *rbj(kind, f0, q, gain_db))


@njit(cache=True, fastmath=True)
def resonator_bank(x, freqs, bws, gains, block):
    """Parallel 2-pole band-pass resonators with block-rate parameter updates.

    freqs/bws/gains: arrays of shape (nblocks, nres). Output is the sum of the resonators.
    """
    n = x.shape[0]
    nres = freqs.shape[1]
    y = np.zeros(n)
    s1 = np.zeros(nres)
    s2 = np.zeros(nres)
    nb = freqs.shape[0]
    for b in range(nb):
        i0 = b * block
        i1 = min(n, i0 + block)
        if i0 >= n:
            break
        for r in range(nres):
            f = freqs[b, r]
            if f <= 0.0 or f >= 0.49 * SR:
                continue
            bw = bws[b, r]
            rr = math.exp(-math.pi * bw / SR)
            c1 = 2.0 * rr * math.cos(TWO_PI * f / SR)
            c2 = -rr * rr
            g = gains[b, r] * (1.0 - rr)   # normalise peak gain roughly to 'gains'
            a1 = s1[r]
            a2 = s2[r]
            for i in range(i0, i1):
                v = g * x[i] + c1 * a1 + c2 * a2
                a2 = a1
                a1 = v
                y[i] += v
            s1[r] = a1
            s2[r] = a2
    return y


# ------------------------------------------------------------------ physical models

@njit(cache=True, fastmath=True)
def karplus(f0, n, bright, decay_s, pos, seed):
    """Extended Karplus-Strong plucked string.

    bright: 0..1 loop filter brightness; decay_s: T60 at f0; pos: pluck position (0..0.5).
    """
    np.random.seed(seed)
    P = SR / f0
    s = 0.5 + 0.45 * bright            # weight of the older sample: higher = brighter
    L = int(P + (1.0 - s) - 0.1)       # loop delay = L - (1 - s) + d_ap = P
    d_ap = P + (1.0 - s) - L
    c = (1.0 - d_ap) / (1.0 + d_ap)    # first-order allpass for the fractional part
    noise = np.empty(L)
    for i in range(L):
        noise[i] = np.random.uniform(-1.0, 1.0)
    sm = 0.15 + 0.7 * (1.0 - bright)   # soften the excitation for darker plucks
    for k in range(2):
        z = 0.0
        for i in range(L):
            z = (1.0 - sm) * noise[i] + sm * z
            noise[i] = z
    buf = np.empty(L)
    pidx = int(pos * L)
    for i in range(L):
        buf[i] = noise[i] - (noise[(i + pidx) % L] if pidx > 0 else 0.0)
    out = np.zeros(n)
    g = 10.0 ** (-3.0 / (decay_s * f0))
    idx = 0
    x_prev = 0.0
    y_prev = 0.0
    for i in range(n):
        a = buf[idx]
        b = buf[(idx + 1) % L]
        out[i] = a
        v = g * (s * a + (1.0 - s) * b)
        w = c * v + x_prev - c * y_prev
        x_prev = v
        y_prev = w
        buf[idx] = w
        idx += 1
        if idx >= L:
            idx = 0
    return out


@njit(cache=True, fastmath=True)
def modal(freqs, decays, amps, n, phase_jit, seed):
    """Sum of exponentially decaying sinusoids (struck bars, membranes, bells)."""
    np.random.seed(seed)
    out = np.zeros(n)
    for m in range(freqs.shape[0]):
        f = freqs[m]
        if f <= 20.0 or f >= 0.45 * SR:
            continue
        r = math.exp(-6.907755 / (decays[m] * SR))   # T60
        w = TWO_PI * f / SR
        c = 2.0 * r * math.cos(w)
        ph = np.random.uniform(0.0, phase_jit)
        y1 = amps[m] * math.sin(ph)
        y2 = amps[m] * math.sin(ph - w) / r
        for i in range(n):
            y = c * y1 - r * r * y2
            out[i] += y1
            y2 = y1
            y1 = y
    return out


@njit(cache=True, fastmath=True)
def fdelay_read(buf, pos):
    i = int(pos)
    f = pos - i
    return buf[i] * (1.0 - f) + buf[i + 1] * f


# ------------------------------------------------------------------ envelopes & noise

def adsr(n, a, d, s, r, sustain_len=None, curve=2.0):
    """Sample-domain ADSR. a/d/r in seconds, s level. Total length n samples."""
    env = np.zeros(n)
    na = max(1, int(a * SR))
    nd = max(1, int(d * SR))
    nr = max(1, int(r * SR))
    n_sus_end = n - nr if sustain_len is None else min(n - nr, int(sustain_len * SR))
    n_sus_end = max(n_sus_end, 1)
    t = np.arange(n)
    att = np.clip(t / na, 0, 1) ** (1.0 / curve)
    env = att.copy()
    dec_mask = (t >= na) & (t < na + nd)
    env[dec_mask] = 1.0 - (1.0 - s) * ((t[dec_mask] - na) / nd)
    env[t >= na + nd] = s
    # release from the level at n_sus_end
    lvl = env[min(n_sus_end, n - 1)]
    rel = t >= n_sus_end
    env[rel] = lvl * np.exp(-5.0 * (t[rel] - n_sus_end) / nr)
    return env


def pink(n, seed=0):
    rng = np.random.default_rng(seed)
    w = rng.standard_normal(n)
    # Paul Kellet's economy pink filter
    b = np.array([0.049922035, -0.095993537, 0.050612699, -0.004408786])
    a = np.array([1.0, -2.494956002, 2.017265875, -0.522189400])
    from scipy.signal import lfilter
    return lfilter(b, a, w)


def smooth_noise(n, rate_hz, seed=0, block=64):
    """Slow random control signal (-1..1) varying at about rate_hz."""
    rng = np.random.default_rng(seed)
    pts = max(4, int(n / SR * rate_hz) + 4)
    knots = rng.uniform(-1, 1, pts)
    x = np.linspace(0, pts - 3.0001, n)
    i = np.minimum(np.floor(x).astype(int), pts - 4)
    f = x - i
    # Catmull-Rom
    p0, p1, p2, p3 = knots[i], knots[i + 1], knots[i + 2], knots[i + 3]
    return 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f +
                  (-p0 + 3 * p1 - 3 * p2 + p3) * f * f * f)


def db(x):
    return 10.0 ** (x / 20.0)


def mtof(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=np.float64) - 69.0) / 12.0)
