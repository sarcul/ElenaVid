"""Orchestral instrument models (tier 2: SCORE).

Strings: Helmholtz-motion source (band-limited sawtooth) with bow-position comb, rosin noise at
the slip, dynamic brightness, intonation drift, delayed vibrato, free bowing, and a modal body.
Sections are ensembles of individually varied players. Winds and brass are source-filter models
with formants, breath and lip behaviour. Percussion, harp, bells and celesta are modal/plucked.
"""
from __future__ import annotations

import math

import numpy as np
from numba import njit
from scipy.signal import oaconvolve

from ..config import SR
from . import dsp
from .dsp import _polyblep, mtof, db

RNG = np.random.default_rng(1953)


# ============================================================================ string section

SECTIONS = {   # players, base pan, width, body family, vibrato cents, octave range for brightness
    "vn1": (8, -0.55, 0.22, "violin", 16.0),
    "vn2": (7, -0.18, 0.2, "violin", 14.0),
    "va": (5, 0.25, 0.18, "viola", 13.0),
    "vc": (5, 0.5, 0.16, "cello", 12.0),
    "cb": (3, 0.68, 0.12, "bass", 8.0),
    "vn_solo": (1, -0.25, 0.0, "violin", 22.0),
    "va_solo": (1, 0.15, 0.0, "viola", 18.0),
    "vc_solo": (1, 0.3, 0.0, "cello", 20.0),
    "vc_harm": (1, 0.05, 0.0, "cello", 0.0),
}

BODY_MODES = {  # (centre Hz, spread, amp) clusters per family
    "violin": [(275, 25, 1.0), (460, 30, 0.9), (540, 30, 0.9), (700, 80, 0.5), (1000, 150, 0.4),
               (2400, 500, 0.55), (3200, 400, 0.35), (4500, 800, 0.2)],
    "viola": [(220, 20, 1.0), (360, 30, 0.9), (430, 30, 0.8), (600, 80, 0.5), (900, 150, 0.4),
              (2000, 450, 0.45), (2900, 400, 0.3)],
    "cello": [(100, 10, 1.0), (180, 20, 0.9), (220, 25, 0.8), (330, 60, 0.5), (600, 120, 0.4),
              (1500, 400, 0.35), (2400, 400, 0.2)],
    "bass": [(60, 8, 1.0), (100, 12, 0.9), (130, 20, 0.7), (250, 50, 0.4), (500, 120, 0.3),
             (1100, 300, 0.2)],
}
_BODY_CACHE = {}


def body_ir(family: str, variant: int):
    key = (family, variant)
    if key in _BODY_CACHE:
        return _BODY_CACHE[key]
    rng = np.random.default_rng(hash(key) % 2 ** 32)
    freqs, decs, amps = [], [], []
    for c, sp, a in BODY_MODES[family]:
        for _ in range(6):
            f = c + rng.normal(0, sp)
            freqs.append(max(40.0, f))
            decs.append(rng.uniform(0.03, 0.09) * (300.0 / max(f, 150.0)) ** 0.3)
            amps.append(a * rng.uniform(0.4, 1.0) * rng.choice([-1, 1]))
    n = int(0.12 * SR)
    ir = dsp.modal(np.array(freqs), np.array(decs), np.array(amps), n, 6.28, int(rng.integers(1e9)))
    ir[0] += 6.0                                  # direct (dry) path through the bridge
    ir = dsp.eq(ir, "lp", 9000 if family == "violin" else 7000, 0.6)
    ir /= np.sqrt(np.sum(ir ** 2))
    _BODY_CACHE[key] = ir
    return ir


@njit(cache=True, fastmath=True)
def bowed_core(freq, env, lp_a, beta, noise_amt, comb_g, seed):
    n = freq.shape[0]
    np.random.seed(seed)
    out = np.empty(n)
    ph = np.random.uniform(0.0, 1.0)
    L = 16384
    buf = np.zeros(L)
    w = 0
    z1 = 0.0
    z2 = 0.0
    hp = 0.0
    for i in range(n):
        f = freq[i]
        dt = f / SR
        saw = 2.0 * ph - 1.0 - _polyblep(ph, dt)
        ph += dt
        if ph >= 1.0:
            ph -= 1.0
        gate = 1.0 if ph < 0.12 else 0.3            # rosin noise concentrates at the slip
        nz = (np.random.random() * 2.0 - 1.0) * noise_amt[i] * gate
        x = saw + nz
        buf[w] = x
        D = beta * SR / f
        rp = w - D
        if rp < 0.0:
            rp += L
        i0 = int(rp)
        fr = rp - i0
        xd = buf[i0] * (1.0 - fr) + buf[(i0 + 1) % L] * fr
        y = x - comb_g * xd
        w += 1
        if w >= L:
            w = 0
        a = lp_a[i]
        z1 = (1.0 - a) * y + a * z1
        z2 = (1.0 - a) * z1 + a * z2
        hp = 0.995 * hp + 0.005 * z2               # remove DC
        out[i] = (z2 - hp) * env[i]
    return out


def _vibrato(n, rate, cents, onset, seed, drift=3.0):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    r = rate * (1.0 + 0.06 * dsp.smooth_noise(n, 0.7, seed))
    ph = 2 * np.pi * np.cumsum(r) / SR + rng.uniform(0, 6.28)
    ramp = np.clip((t - onset) / 0.35, 0, 1) ** 1.5
    vib = cents * ramp * np.sin(ph) * (1.0 + 0.15 * dsp.smooth_noise(n, 1.1, seed + 1))
    dr = drift * dsp.smooth_noise(n, 0.4, seed + 2)
    return vib + dr


def string_note(midi, dur, vel, tech, player, nplayers, family, vib_cents, tags, seed):
    """One player's note. Returns (offset_samples, mono array)."""
    rng = np.random.default_rng(seed)
    f0 = float(mtof(midi))
    tail = 0.35 if tech not in ("pizz",) else 0.0
    if tech == "pizz":
        decay = float(np.clip(2.2 * (110.0 / f0) ** 0.5, 0.35, 2.5))
        n = int((min(dur, decay) + 0.25) * SR)
        y = dsp.karplus(f0 * 2 ** (rng.normal(0, 4) / 1200), n, 0.42 + 0.3 * vel, decay,
                        0.18 + 0.06 * rng.random(), int(rng.integers(1e9)))
        y *= np.minimum(1.0, np.linspace(6.0, 0.0, n) if dur < decay else 1.0)
        return int(rng.normal(0, 0.006) * SR), y * vel * 0.9
    n = int((dur + tail) * SR)
    if n < 64:
        n = 64
    t = np.arange(n) / SR
    # pitch: settle, drift, vibrato, glides
    cents = rng.normal(0, 4.0) * np.exp(-t / 0.08)
    cents += rng.normal(0, 3.0 if nplayers > 1 else 1.0)
    g = tags.get("glide", 0)
    if g:
        cents += g * np.exp(-t / 0.5) * (1 + 0.3 * rng.standard_normal())
    if tech == "harm" or family == "harm":
        cents += 0.6 * dsp.smooth_noise(n, 0.5, seed)
    elif vib_cents > 0:
        espr = 1.35 if tech == "espr" else 1.0
        cents += _vibrato(n, rng.uniform(4.9, 6.1), vib_cents * espr * rng.uniform(0.7, 1.2),
                          rng.uniform(0.12, 0.38), seed + 7)
    freq = f0 * 2 ** (cents / 1200.0)
    # amplitude envelope
    short = tech == "spicc" or dur < 0.18
    if short:
        a, r = 0.012, 0.08
    else:
        a = 0.035 + 0.2 * (1.0 - vel) + rng.uniform(0, 0.03)
        r = 0.18 + 0.1 * rng.random()
    env = dsp.adsr(n, a, 0.12, 0.88, r, sustain_len=dur)
    shape = tags.get("env")
    if shape == "swell":
        env *= np.clip(np.sin(np.pi * np.clip(t / max(dur, 0.1), 0, 1)) ** 0.8, 0.0, 1.0)
    elif shape == "fade":
        env *= np.clip(1.0 - t / max(dur, 0.1), 0.0, 1.0) ** 1.4
    elif shape == "decay":
        env *= np.exp(-1.2 * t / max(dur, 0.1))
    elif shape == "fp":
        env *= 0.45 + 0.55 * np.exp(-t / 0.12)
    # free bowing on long notes: each player changes bow at different moments
    if dur > 3.0 and nplayers > 1 and tech not in ("trem",):
        tc = rng.uniform(2.2, 4.5)
        while tc < dur - 0.5:
            env *= 1.0 - 0.28 * np.exp(-((t - tc) / 0.05) ** 2)
            tc += rng.uniform(2.5, 5.0)
    if tech == "trem":
        rate = rng.uniform(11.0, 14.5)
        strokes = np.abs(np.sin(np.pi * np.cumsum(rate * (1 + 0.1 * dsp.smooth_noise(n, 3, seed)))
                                / SR)) ** 0.6
        env *= 0.45 + 0.55 * strokes
    # brightness
    k = 5.0 + 34.0 * vel ** 1.4
    noise_amt = 0.05 + 0.06 * vel
    comb = 0.5
    beta = rng.uniform(0.08, 0.13)
    if tech == "sord":
        k *= 0.5
        noise_amt *= 0.6
    elif tech == "pont":
        k *= 2.4
        noise_amt *= 1.8
        comb = 0.75
        beta = 0.035
    elif tech == "harm" or family == "harm":
        k = 2.2
        noise_amt = 0.012
    fc = np.minimum(15000.0, f0 * k * (0.75 + 0.25 * env))
    lp_a = dsp.lp_coef(fc)
    # attack scratch: the bow catching the string
    y = bowed_core(freq, env, lp_a, beta, noise_amt * (1.0 + 3.0 * np.exp(-t / 0.05)), comb,
                   int(rng.integers(1e9)))
    if tech == "harm" or family == "harm":
        # natural harmonic: almost a sine with a glassy upper partial
        ph = dsp.phase_from_freq(freq, rng.random())
        pure = np.sin(2 * np.pi * ph) + 0.12 * np.sin(4 * np.pi * ph) + 0.05 * np.sin(6 * np.pi * ph)
        y = 0.85 * pure * env + 0.15 * y
    if tech == "pont":
        y = dsp.eq(y, "hp", 600, 0.6)
    timing = rng.normal(0, 0.012 if nplayers > 1 else 0.004)
    return int(timing * SR), y * (0.55 + 0.45 * vel)


def render_strings(inst, notes, total_n):
    """Render a section (or a solo) to stereo, with per-player variation and modal bodies."""
    nplayers, pan, width, family, vib = SECTIONS[inst]
    fam = "cello" if inst == "vc_harm" else family
    L = np.zeros(total_n, dtype=np.float32)
    R = np.zeros(total_n, dtype=np.float32)
    nbody = min(3, nplayers)
    for p in range(nplayers):
        bus = np.zeros(total_n, dtype=np.float64)
        ppan = pan + (width * (p / max(1, nplayers - 1) - 0.5) * 2 if nplayers > 1 else 0.0)
        level = 1.0 / math.sqrt(nplayers) * (0.85 + 0.3 * RNG.random())
        for ni, n in enumerate(notes):
            tech = n["tech"]
            seed = (hash((inst, p, ni)) & 0x7FFFFFFF)
            vib_c = 0.0 if inst == "vc_harm" or n["tags"].get("tommaso") else vib
            off, y = string_note(n["midi"], n["dur"], n["vel"], tech, p, nplayers,
                                 "harm" if inst == "vc_harm" else fam, vib_c, n["tags"], seed)
            if n["tags"].get("fade_end"):
                fl = len(y)
                y = y * np.clip(np.linspace(1.6, -0.2, fl), 0, 1) ** 0.7
            s0 = int(n["t"] * SR) + off
            s0 = max(0, s0)
            s1 = min(total_n, s0 + len(y))
            bus[s0:s1] += y[: s1 - s0] * level
        ir = body_ir(fam, p % nbody)
        wet = oaconvolve(bus, ir)[:total_n]
        gl, gr = math.cos((ppan + 1) * math.pi / 4), math.sin((ppan + 1) * math.pi / 4)
        L += (wet * gl).astype(np.float32)
        R += (wet * gr).astype(np.float32)
    return L, R, pan


# ============================================================================ woodwinds

WINDS = {  # pan, formants [(f, q, gain_db)], pulse width, lowpass, vibrato cents, rate, breath
    "fl": (-0.08, [(800, 1.5, 3), (2400, 2, -4)], None, 9000, 10.0, 5.0, 0.07),
    "ob": (0.08, [(1150, 4, 9), (2750, 5, 6), (4500, 4, 0)], 0.33, 9000, 11.0, 5.6, 0.02),
    "eh": (0.12, [(850, 4, 9), (2200, 4, 5), (3600, 4, -2)], 0.38, 6500, 9.0, 5.2, 0.02),
    "cl": (-0.14, [(1550, 2.5, 4), (3000, 3, -3)], 0.5, 6000, 0.0, 5.0, 0.03),
    "bn": (0.16, [(480, 3, 10), (1150, 3, 6), (2600, 4, 1)], 0.30, 5000, 8.0, 5.0, 0.02),
}


def wind_note(inst, midi, dur, vel, tags, seed):
    pan, forms, width, lpf, vib, vrate, breath = WINDS[inst]
    rng = np.random.default_rng(seed)
    f0 = float(mtof(midi))
    n = int((dur + 0.25) * SR)
    t = np.arange(n) / SR
    tommaso = bool(tags.get("tommaso"))
    cents = rng.normal(0, 2.0) * np.exp(-t / 0.06) + 1.5 * dsp.smooth_noise(n, 0.4, seed)
    if vib > 0 and not tommaso and dur > 0.25:
        cents += _vibrato(n, vrate * rng.uniform(0.95, 1.05), vib, 0.18, seed + 3, drift=1.5)
    freq = f0 * 2 ** (cents / 1200)
    a = 0.03 + 0.07 * (1 - vel) if not tommaso else 0.25
    env = dsp.adsr(n, a, 0.08, 0.9, 0.12, sustain_len=dur)
    if tags.get("fade_end"):
        env *= np.clip(np.linspace(1.6, -0.2, n), 0, 1) ** 0.7
    if inst == "fl":
        amps = np.array([1.0, 0.25, 0.08, 0.03, 0.012])
        y = dsp.additive(freq, amps * (0.6 + 0.4 * vel), 5, rng.uniform(0, 1, 5))
    else:
        w = np.full(n, width) + 0.03 * dsp.smooth_noise(n, 2.0, seed)
        y = dsp.pulse_blep(freq, w, rng.random())
        if inst == "cl" and midi > 70:
            y = 0.8 * y + 0.2 * dsp.saw_blep(freq)
    fo = np.zeros_like(y)
    for f, q, g in forms:
        fo += dsp.eq(y, "bp", f, q) * db(g)
    y = 0.35 * y + fo
    br = rng.standard_normal(n) * breath * (1.0 + 4.0 * np.exp(-t / 0.04))
    br = dsp.eq(br, "bp", min(6000, f0 * 4), 0.8)
    y = (y + br) * env
    y = dsp.biquad(y, *dsp.rbj("lp", lpf * (0.6 + 0.4 * vel), 0.7))
    return y * vel * 0.55


# ============================================================================ brass

BRASS = {  # pan, formant (f, q, gain), base brightness factor, mute
    "hn": (-0.32, (480, 1.4, 6), 3.0),
    "tpt": (0.24, (1350, 1.5, 6), 6.0),
    "tbn": (0.36, (620, 1.4, 6), 4.0),
    "tuba": (0.42, (300, 1.2, 5), 2.2),
}


def brass_note(inst, midi, dur, vel, tags, tech, art, seed):
    pan, (ff, fq, fg), bright = BRASS[inst]
    rng = np.random.default_rng(seed)
    f0 = float(mtof(midi))
    n = int((dur + 0.3) * SR)
    t = np.arange(n) / SR
    lip = -38.0 * np.exp(-t / 0.035) * (1.0 + 0.3 * rng.standard_normal())
    cents = lip + 1.5 * dsp.smooth_noise(n, 0.5, seed)
    if dur > 0.8 and inst != "tuba":
        cents += _vibrato(n, 5.0, 4.0, 0.4, seed + 5, drift=1.0)
    freq = f0 * 2 ** (cents / 1200)
    accent = ">" in art or "^" in art
    a = 0.02 if accent else 0.04 + 0.08 * (1 - vel)
    env = dsp.adsr(n, a, 0.1, 0.82 if accent else 0.95, 0.14, sustain_len=dur)
    if accent:
        env *= 1.0 + 0.5 * np.exp(-t / 0.08)
    if tags.get("env") == "fp":
        env *= 0.35 + 0.65 * np.exp(-t / 0.1)
    if tags.get("env") == "fade":
        env *= np.clip(1.0 - t / max(dur, 0.1), 0, 1)
    y = dsp.saw_blep(freq, rng.random())
    k = bright * (1.0 + 5.0 * (vel * env) ** 1.3)
    fc = np.minimum(14000.0, f0 * k + 200.0)
    a_c = dsp.lp_coef(fc)
    y = dsp.onepole_lp(dsp.onepole_lp(y, a_c), a_c)
    y = y + dsp.eq(y, "peak", ff, fq, fg) * 0.5
    if tech == "mute":
        y = dsp.eq(dsp.eq(y, "hp", 900, 0.7), "peak", 1900, 2.5, 9) * 0.7
    br = rng.standard_normal(n) * 0.03 * np.exp(-t / 0.03)
    return (y + br) * env * vel * 0.5


# ============================================================================ percussion & plucked

def timpani(midi, dur, vel, tags, seed):
    rng = np.random.default_rng(seed)
    f0 = float(mtof(midi))
    ratios = np.array([1.0, 1.504, 1.742, 2.0, 2.245, 2.494, 2.8, 2.97, 3.17])
    decays = np.array([1.8, 1.2, 0.9, 0.8, 0.6, 0.5, 0.4, 0.35, 0.3]) * (1.1 - 0.3 * vel)
    amps = np.array([1.0, 0.8, 0.5, 0.45, 0.3, 0.25, 0.15, 0.1, 0.08])

    def hit(v, sd):
        n = int(2.5 * SR)
        y = dsp.modal(f0 * ratios * (1 + rng.normal(0, 0.002, 9)), decays, amps * v, n, 0.0, sd)
        nz = rng.standard_normal(int(0.03 * SR)) * v * 0.6
        nz = dsp.eq(nz, "lp", 1800, 0.7)
        y[: len(nz)] += nz * np.exp(-np.arange(len(nz)) / (0.006 * SR))
        return y

    if tags.get("roll"):
        n = int((dur + 2.0) * SR)
        out = np.zeros(n)
        tt = 0.0
        k = 0
        while tt < dur:
            frac = tt / max(dur, 0.1)
            v = vel * (0.35 + 0.65 * frac if tags.get("cresc") else 0.6) * rng.uniform(0.7, 1.0)
            h = hit(v * 0.5, int(rng.integers(1e9)))
            s0 = int(tt * SR)
            s1 = min(n, s0 + len(h))
            out[s0:s1] += h[: s1 - s0]
            tt += 1.0 / rng.uniform(13, 17)
            k += 1
        return out * 0.6
    return hit(vel, int(rng.integers(1e9)))


def bass_drum(vel, seed):
    rng = np.random.default_rng(seed)
    n = int(2.5 * SR)
    t = np.arange(n) / SR
    f = 52.0 * (1 + 0.6 * np.exp(-t / 0.05))
    ph = np.cumsum(f) / SR
    y = np.sin(2 * np.pi * ph) * np.exp(-t / 0.6)
    y += dsp.modal(np.array([88, 133, 179, 221.0]), np.array([0.5, 0.35, 0.3, 0.2]),
                   np.array([0.4, 0.3, 0.2, 0.1]), n, 0.0, int(rng.integers(1e9)))
    nz = dsp.eq(rng.standard_normal(n), "lp", 900, 0.7) * np.exp(-t / 0.05) * 0.4
    return (y + nz) * vel


def tamtam(dur, vel, seed):
    rng = np.random.default_rng(seed)
    n = int((max(dur, 6.0) + 2.0) * SR)
    t = np.arange(n) / SR
    m = 160
    freqs = np.exp(rng.uniform(np.log(45), np.log(7000), m))
    decays = rng.uniform(2.0, 9.0, m) * (300 / freqs) ** 0.25
    amps = rng.uniform(0.2, 1.0, m) / np.sqrt(freqs / 100)
    y = dsp.modal(freqs, decays, amps, n, 6.28, int(rng.integers(1e9)))
    # the bloom: high partials grow after the strike
    hi = dsp.eq(y, "hp", 1500, 0.7)
    lo = y - hi
    bloom = 1 - np.exp(-t / 0.9)
    y = lo + hi * bloom * 1.6
    strike = dsp.eq(rng.standard_normal(int(0.05 * SR)), "lp", 400, 0.7) * 2.0
    y[: len(strike)] += strike * np.exp(-np.arange(len(strike)) / (0.01 * SR))
    return y / np.max(np.abs(y)) * vel


def cymbal(dur, vel, tags, seed):
    rng = np.random.default_rng(seed)
    n = int((dur + 3.5) * SR)
    t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    y = dsp.eq(dsp.eq(nz, "hp", 2500, 0.6), "peak", 6000, 1.0, 4)
    m = 60
    freqs = np.exp(rng.uniform(np.log(1800), np.log(12000), m))
    y2 = dsp.modal(freqs, rng.uniform(1.0, 3.5, m), rng.uniform(0.1, 0.4, m), n, 6.28,
                   int(rng.integers(1e9)))
    if tags.get("swell"):
        env = np.clip(t / max(dur, 0.2), 0, 1) ** 2 * np.exp(-np.maximum(0, t - dur) / 0.6)
    else:
        env = np.exp(-t / 1.6)
    y = (0.5 * y * env * 0.25 + y2 * env * 0.6)
    return y * vel * 0.5


def triangle(vel, seed):
    n = int(4.0 * SR)
    f = 1250.0
    ratios = np.array([1, 2.76, 5.4, 8.93, 13.34, 18.6])
    y = dsp.modal(f * ratios, np.array([3.5, 3.0, 2.4, 2.0, 1.6, 1.2]),
                  np.array([0.6, 1.0, 0.8, 0.5, 0.3, 0.2]), n, 0.0, seed)
    return y * vel * 0.25


def tambourine(vel, seed):
    rng = np.random.default_rng(seed)
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for j in range(10):
        off = int(abs(rng.normal(0, 0.01)) * SR)
        f = rng.uniform(5500, 9000)
        y[off:] += dsp.modal(np.array([f, f * 1.48]), np.array([0.25, 0.18]),
                             np.array([0.5, 0.3]), n - off, 6.28, int(rng.integers(1e9)))
    skin = dsp.eq(rng.standard_normal(n), "bp", 300, 1.2) * np.exp(-t / 0.02) * 0.6
    return (y * 0.3 + skin) * vel


def bell(midi, dur, vel, kind, seed):
    """Tubular bells and church bells (minor-third bell partials: hum, prime, tierce, quint, nominal)."""
    rng = np.random.default_rng(seed)
    f = float(mtof(midi))
    if kind == "church":
        ratios = np.array([0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 2.67, 3.0, 4.0, 5.33])
        decays = np.array([12, 8, 6, 5, 4.5, 3, 3, 2.5, 2, 1.5])
        amps = np.array([0.6, 0.8, 0.7, 0.35, 1.0, 0.4, 0.3, 0.3, 0.25, 0.15])
        n = int(10 * SR)
    else:
        f = f / 2.0          # tubular bell strike tone sits near the 4th-6th partials
        ratios = np.array([1.0, 2.76, 5.40, 8.93, 13.34, 18.64, 2.0, 3.0, 4.0])
        decays = np.array([6, 5, 4.5, 3.5, 2.5, 2, 4, 3.5, 3])
        amps = np.array([0.4, 0.6, 1.0, 0.8, 0.5, 0.3, 0.3, 0.4, 0.5])
        n = int(6 * SR)
    fr = f * ratios * (1 + rng.normal(0, 0.0015, len(ratios)))
    y = dsp.modal(fr, decays, amps, n, 0.0, int(rng.integers(1e9)))
    # doublets: slight beating
    y += dsp.modal(fr * 1.0012, decays, amps * 0.35, n, 0.0, int(rng.integers(1e9)))
    clap = dsp.eq(rng.standard_normal(int(0.02 * SR)), "bp", 2500, 0.8)
    y[: len(clap)] += clap * 0.4 * np.exp(-np.arange(len(clap)) / (0.003 * SR))
    return y * vel * (0.35 if kind == "church" else 0.3)


def celesta(midi, dur, vel, seed):
    f = float(mtof(midi))
    n = int(3.0 * SR)
    y = dsp.modal(f * np.array([1.0, 4.0, 10.0]), np.array([2.2, 0.6, 0.2]),
                  np.array([1.0, 0.18, 0.05]), n, 0.0, seed)
    a = np.minimum(1.0, np.arange(n) / (0.002 * SR))
    return y * a * vel * 0.4


def harp(midi, dur, vel, tags, seed):
    rng = np.random.default_rng(seed)
    f0 = float(mtof(midi))
    if tags.get("harmonic"):
        n = int(3.0 * SR)
        t = np.arange(n) / SR
        y = np.sin(2 * np.pi * 2 * f0 * t) * np.exp(-t / 1.2) * np.minimum(1, t / 0.004)
        return y * vel * 0.5
    decay = float(np.clip(3.5 * (130.0 / f0) ** 0.6, 0.6, 5.0))
    n = int(min(decay + 0.4, 6.0) * SR)
    y = dsp.karplus(f0, n, 0.55 + 0.25 * vel, decay, 0.13 + 0.05 * rng.random(),
                    int(rng.integers(1e9)))
    y = dsp.eq(dsp.eq(y, "lp", 7000, 0.7), "peak", 260, 1.0, 3)
    return y * vel * 0.8


def organ(midi, dur, vel, seed):
    rng = np.random.default_rng(seed)
    f0 = float(mtof(midi))
    n = int((dur + 0.15) * SR)
    t = np.arange(n) / SR
    freq = np.full(n, f0) * 2 ** ((0.8 * dsp.smooth_noise(n, 0.3, seed)) / 1200)
    amps8 = np.array([1.0, 0.45, 0.3, 0.16, 0.1, 0.06, 0.04, 0.025])
    y = dsp.additive(freq, amps8, 8, rng.uniform(0, 1, 8))
    y += 0.5 * dsp.additive(freq * 2.0 * 1.0007, amps8[:5], 5, rng.uniform(0, 1, 5))
    if midi < 48:
        y += 0.7 * dsp.additive(freq * 0.5, np.array([1.0, 0.2, 0.1]), 3, rng.uniform(0, 1, 3))
    chiff = dsp.eq(rng.standard_normal(n), "bp", min(8000, f0 * 3), 1.5) * np.exp(-t / 0.03) * 0.25
    env = dsp.adsr(n, 0.04, 0.05, 1.0, 0.08, sustain_len=dur)
    wind = dsp.eq(rng.standard_normal(n), "lp", 1200, 0.7) * 0.004
    return (y + chiff + wind) * env * vel * 0.35


# ============================================================================ dispatch

PERC_PAN = {"timp": -0.12, "bd": 0.1, "tamtam": 0.22, "cym": 0.3, "tri": 0.35, "tamb": 0.4,
            "tubbells": 0.15, "churchbell": 0.0, "celesta": -0.3, "harp": -0.45, "organ": 0.0,
            "glock": 0.3}


def render_one(inst, n, seed):
    """Render a single non-string note; returns mono array."""
    midi, dur, vel, tags = n["midi"], n["dur"], n["vel"], n["tags"]
    if inst in WINDS:
        return wind_note(inst, midi, dur, vel, tags, seed)
    if inst in BRASS:
        return brass_note(inst, midi, dur, vel, tags, n["tech"], n["art"], seed)
    if inst == "timp":
        return timpani(midi, dur, vel, tags, seed)
    if inst == "bd":
        return bass_drum(vel, seed)
    if inst == "tamtam":
        return tamtam(dur, vel, seed)
    if inst == "cym":
        return cymbal(dur, vel, tags, seed)
    if inst == "tri":
        return triangle(vel, seed)
    if inst == "tamb":
        return tambourine(vel, seed)
    if inst == "tubbells":
        return bell(midi, dur, vel, "tubular", seed)
    if inst == "churchbell":
        return bell(midi, dur, vel, "church", seed)
    if inst == "celesta":
        return celesta(midi, dur, vel, seed)
    if inst == "harp":
        return harp(midi, dur, vel, tags, seed)
    if inst == "organ":
        return organ(midi, dur, vel, seed)
    raise KeyError(inst)


def pan_of(inst):
    if inst in WINDS:
        return WINDS[inst][0]
    if inst in BRASS:
        return BRASS[inst][0]
    return PERC_PAN.get(inst, 0.0)


def render_other(inst, notes, total_n):
    L = np.zeros(total_n, dtype=np.float32)
    R = np.zeros(total_n, dtype=np.float32)
    pan = pan_of(inst)
    gl, gr = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    for i, n in enumerate(notes):
        y = render_one(inst, n, (hash((inst, i)) & 0x7FFFFFFF))
        s0 = max(0, int(n["t"] * SR))
        s1 = min(total_n, s0 + len(y))
        seg = y[: s1 - s0].astype(np.float32)
        if inst == "organ":
            # an organ is wide: spread pipes by pitch
            pp = np.clip((n["midi"] - 60) / 30.0, -0.7, 0.7)
            l2, r2 = math.cos((pp + 1) * math.pi / 4), math.sin((pp + 1) * math.pi / 4)
            L[s0:s1] += seg * l2
            R[s0:s1] += seg * r2
        else:
            L[s0:s1] += seg * gl
            R[s0:s1] += seg * gr
    return L, R, pan
