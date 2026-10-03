"""Procedural sound generators for tiers 3 (FOLEY), 4 (ATMOS) and 5 (SUB/DESIGN).

Every sound is modelled: crowd walla is the formant voice engine babbling random Italian-like
syllables; swifts are FM trills with Doppler; the sea is shaped noise with swell and wash; the
bora is gusting band noise with rigging whistles; the locomotive is chuffs, hiss and rail joints.
"""
from __future__ import annotations

import numpy as np

from ..config import SR
from . import dsp, voice
from .instruments import bell

R = np.random.default_rng


def _t(n):
    return np.arange(n) / SR


def _env_sweep(n, a, r):
    t = _t(n)
    dur = n / SR
    return np.clip(t / max(a, 1e-3), 0, 1) * np.clip((dur - t) / max(r, 1e-3), 0, 1)


def stereo(mono, pan=0.0):
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    return np.stack([mono * gl, mono * gr]).astype(np.float32)


def pan_sweep(mono, p0, p1):
    n = len(mono)
    p = np.linspace(p0, p1, n)
    return np.stack([mono * np.cos((p + 1) * np.pi / 4), mono * np.sin((p + 1) * np.pi / 4)]).astype(np.float32)


# =================================================================== crowds & people

def walla(dur, talkers=12, seed=0, bright=1.0, level=1.0, gender_mix=0.5):
    """Indistinct crowd speech: the voice kernel babbling random syllables."""
    rng = R(seed)
    n = int(dur * SR)
    out = np.zeros((2, n), dtype=np.float32)
    tabs = voice.tables()
    for k in range(talkers):
        female = rng.random() < gender_mix
        table = "soprano" if female else rng.choice(["tenor", "bass"])
        base_f0 = rng.uniform(170, 240) if female else rng.uniform(95, 150)
        # syllable stream with phrase gaps
        tt = rng.uniform(0, 1.5)
        f0 = np.full(n, base_f0)
        amp = np.zeros(n)
        F = np.zeros((6, n))
        B = np.zeros((6, n))
        fric = np.zeros(n)
        vowels = list("aeiou")
        last_F = np.array(voice._vowel_targets(table, "a", 1.0)[0])
        last_B = np.array(voice._vowel_targets(table, "a", 1.0)[1])
        while tt < dur:
            phr = rng.uniform(0.8, 3.0)
            p_end = min(dur, tt + phr)
            slope = rng.uniform(-0.25, 0.05)
            while tt < p_end:
                sd = rng.uniform(0.11, 0.24)
                i0, i1 = int(tt * SR), min(n, int((tt + sd) * SR))
                if i1 <= i0:
                    break
                Fv, Bv = voice._vowel_targets(table, rng.choice(vowels), rng.uniform(0.95, 1.06))
                seg = np.arange(i1 - i0)
                w = np.clip(seg / (0.3 * len(seg) + 1), 0, 1)[:, None]
                F[:, i0:i1] = (last_F[:, None] * (1 - w.T) + Fv[:, None] * w.T)
                B[:, i0:i1] = Bv[:, None]
                last_F, last_B = Fv, Bv
                env = np.sin(np.pi * seg / len(seg)) ** 0.7
                amp[i0:i1] = env * rng.uniform(0.5, 1.0)
                f0[i0:i1] = base_f0 * (1 + slope * (tt - (p_end - phr)) / phr) * \
                    2 ** (rng.normal(0, 1.2) / 12)
                if rng.random() < 0.45:
                    c0 = i0
                    c1 = min(n, i0 + int(0.04 * SR))
                    fric[c0:c1] = rng.uniform(0.05, 0.2)
                tt += sd
            tt += rng.uniform(0.3, 1.6)
        F[F == 0] = 500
        B[B == 0] = 100
        f0s = f0 * (1 + 0.02 * dsp.smooth_noise(n, 2, seed + k))
        y = voice.voice_kernel(f0s, amp, np.full(n, 0.15), np.full(n, 0.05), np.ascontiguousarray(F),
                               np.ascontiguousarray(B), fric, np.full(n, 5000.0), np.full(n, 3000.0),
                               tabs, int(rng.integers(1e9)), 64)
        dist = rng.uniform(0.3, 1.0)
        y = dsp.eq(y, "lp", 2500 + 4000 * bright * (1 - dist) + 800, 0.7) * (1.2 - dist)
        out += stereo(y.astype(np.float32), rng.uniform(-0.9, 0.9))
    out /= np.sqrt(talkers)
    return out * level * 0.18


def applause(dur, density=180, seed=1, level=1.0):
    rng = R(seed)
    n = int(dur * SR)
    out = np.zeros((2, n), dtype=np.float32)
    grains = []
    for g in range(24):
        L = int(rng.uniform(0.006, 0.014) * SR)
        x = rng.standard_normal(L) * np.exp(-np.arange(L) / (0.0025 * SR))
        x = dsp.eq(dsp.eq(x, "bp", rng.uniform(900, 2600), 1.2), "peak", rng.uniform(300, 600), 2, 6)
        grains.append(x / np.max(np.abs(x)))
    t = _t(n)
    shape = np.clip(t / (0.18 * dur), 0, 1) * np.clip((dur - t) / (0.45 * dur), 0, 1) ** 1.2
    for c in range(density):
        rate = rng.uniform(3.2, 5.4)
        tt = rng.uniform(0, 0.4)
        gain = rng.uniform(0.2, 1.0) * (0.4 + 0.6 * rng.random())
        pan = rng.uniform(-1, 1)
        gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        while tt < dur:
            i = int(tt * SR)
            if rng.random() < shape[min(i, n - 1)] * 1.2:
                gr_ = grains[rng.integers(len(grains))]
                j = min(n, i + len(gr_))
                v = gain * rng.uniform(0.7, 1.0)
                out[0, i:j] += gr_[: j - i] * v * gl
                out[1, i:j] += gr_[: j - i] * v * gr
            tt += 1.0 / rate * rng.uniform(0.85, 1.15)
    return out / np.sqrt(density) * level * 0.5


def cough(seed, level=1.0):
    rng = R(seed)
    n = int(0.45 * SR)
    t = _t(n)
    x = rng.standard_normal(n)
    y = dsp.eq(dsp.eq(x, "bp", 700, 1.5), "peak", 1800, 2, 6)
    env = (np.exp(-t / 0.06) * (t < 0.2) + 0.5 * np.exp(-np.maximum(0, t - 0.22) / 0.05) * (t > 0.22))
    return y * env * level * 0.4


def rustle(dur, seed, level=1.0, bright=1.0):
    """Programmes, coats, seats: soft broadband rustle with crackles."""
    rng = R(seed)
    n = int(dur * SR)
    x = dsp.pink(n, seed)
    move = np.clip(dsp.smooth_noise(n, 2.5, seed + 1), 0, 1) ** 2
    y = dsp.eq(x, "hp", 900, 0.7) * move
    cr = np.zeros(n)
    k = rng.integers(0, n, int(dur * 40))
    cr[k] = rng.uniform(-1, 1, len(k))
    cr = dsp.eq(cr, "hp", 2500 * bright, 0.7) * move
    return (y * 0.4 + cr * 0.8) * level * 0.25


def breath(kind, seed, level=1.0, dur=None):
    rng = R(seed)
    d = dur or {"inhale": 0.5, "exhale": 0.6, "gasp": 0.28, "panic": 0.22, "sigh": 1.1}[kind]
    n = int(d * SR)
    t = _t(n)
    x = rng.standard_normal(n)
    if kind in ("inhale", "gasp", "panic"):
        y = dsp.eq(dsp.eq(x, "bp", 1600, 0.9), "peak", 2900, 1.4, 5)
        env = (t / d) ** 0.7 * np.clip((d - t) / 0.05, 0, 1)
    else:
        y = dsp.eq(dsp.eq(x, "bp", 900, 0.8), "peak", 1400, 1.5, 4)
        env = np.clip(t / 0.05, 0, 1) * np.exp(-t / (0.45 * d))
    if kind == "gasp":
        env *= 1.6
    return y * env * level * 0.25


# =================================================================== foley

def footsteps(times, surface="stone", seed=0, level=1.0):
    rng = R(seed)
    span = (max(times) if times else 0) + 0.6
    n = int(span * SR)
    out = np.zeros(n)
    for k, t0 in enumerate(times):
        L = int(0.25 * SR)
        tt = _t(L)
        heel = np.sin(2 * np.pi * rng.uniform(70, 110) * tt) * np.exp(-tt / 0.03)
        click = dsp.eq(rng.standard_normal(L), "bp",
                       {"stone": 3200, "wood": 900, "boards": 1300, "gravel": 2500}[surface], 1.3)
        click *= np.exp(-tt / (0.012 if surface == "stone" else 0.02))
        y = heel * 0.8 + click * (1.0 if surface == "stone" else 0.7)
        if surface in ("wood", "boards"):
            y += dsp.modal(np.array([180.0, 420, 760]), np.array([0.12, 0.08, 0.05]),
                           np.array([0.4, 0.25, 0.15]), L, 0.0, int(rng.integers(1e9)))
        toe_off = int(rng.uniform(0.07, 0.11) * SR)
        y[toe_off:] += 0.5 * click[: L - toe_off]
        i = int(t0 * SR)
        j = min(n, i + L)
        out[i:j] += y[: j - i] * rng.uniform(0.7, 1.0)
    return out * level * 0.35


def silk(dur, seed, level=1.0, motion=None):
    """A gown: soft whoosh of fabric plus crisp taffeta crackle."""
    rng = R(seed)
    n = int(dur * SR)
    t = _t(n)
    env = motion if motion is not None else np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    w = dsp.eq(dsp.pink(n, seed), "bp", 2200, 0.6) * env
    cr = np.zeros(n)
    k = rng.integers(0, n, int(dur * 220))
    cr[k] = rng.uniform(-1, 1, len(k)) * env[k]
    cr = dsp.eq(cr, "hp", 3500, 0.7)
    return (w * 0.5 + cr * 0.7) * level * 0.3


def paper(kind, dur, seed, level=1.0):
    rng = R(seed)
    n = int(dur * SR)
    t = _t(n)
    if kind == "slide":
        x = dsp.eq(dsp.pink(n, seed), "bp", 1800, 0.9)
        env = np.clip(t / 0.08, 0, 1) * np.clip((dur - t) / 0.15, 0, 1)
        stop = np.zeros(n)
        stop[-int(0.03 * SR):] = dsp.eq(rng.standard_normal(int(0.03 * SR)), "lp", 1500, 0.7) * 0.5
        return (x * env * 0.5 + stop) * level * 0.4
    # crinkle / unfold: sparse sharp crackles with resonance
    out = np.zeros(n)
    rate = 60 if kind == "crinkle" else 25
    times = np.sort(rng.uniform(0, dur, int(dur * rate)))
    for tt in times:
        L = int(0.02 * SR)
        g = rng.standard_normal(L) * np.exp(-np.arange(L) / (0.002 * SR))
        g = dsp.eq(g, "bp", rng.uniform(2000, 6500), 2.0)
        i = int(tt * SR)
        j = min(n, i + L)
        out[i:j] += g[: j - i] * rng.uniform(0.3, 1.0)
    return out * level * 0.35


def door(kind, seed, level=1.0):
    rng = R(seed)
    n = int(1.6 * SR)
    t = _t(n)
    out = np.zeros(n)
    if kind in ("close", "slam"):
        thud = dsp.modal(np.array([95.0, 160, 240, 410]), np.array([0.35, 0.25, 0.18, 0.1]),
                         np.array([1.0, 0.6, 0.4, 0.2]), n, 0.0, int(rng.integers(1e9)))
        latch = dsp.modal(np.array([2300.0, 3700, 5200]), np.array([0.05, 0.04, 0.03]),
                          np.array([0.5, 0.4, 0.3]), n, 0.0, int(rng.integers(1e9)))
        nz = dsp.eq(rng.standard_normal(n), "lp", 1200, 0.7) * np.exp(-t / 0.02)
        out = thud * (1.4 if kind == "slam" else 0.8) + latch * 0.6 + nz * 0.4
    if kind in ("open", "creak"):
        # stick-slip creak: a jittery impulse train through wood resonances
        dur = 1.2
        m = int(dur * SR)
        rate = 60 + 120 * np.abs(dsp.smooth_noise(m, 1.5, seed))
        ph = np.cumsum(rate / SR)
        imp = (np.diff(np.floor(ph), prepend=0) > 0).astype(float) * rng.uniform(0.4, 1.0, m)
        cr = dsp.eq(dsp.eq(imp, "bp", 650, 3), "peak", 1500, 4, 6)
        out[:m] += cr * np.sin(np.pi * np.arange(m) / m)
    return out * level * 0.5


def impact_slap(seed, level=1.0):
    """The blow: short, restrained, mostly felt (the image cuts away)."""
    rng = R(seed)
    n = int(0.4 * SR)
    t = _t(n)
    crack = dsp.eq(rng.standard_normal(n), "hp", 1500, 0.7) * np.exp(-t / 0.0025)
    body = np.sin(2 * np.pi * 90 * t) * np.exp(-t / 0.05)
    return (crack * 0.8 + body * 0.6) * level * 0.6


def clink(kind, seed, level=1.0):
    rng = R(seed)
    if kind == "glass":
        f = rng.uniform(2300, 2900)
        fr = f * np.array([1.0, 1.57, 2.33, 3.2])
        dec = np.array([1.4, 0.9, 0.6, 0.4])
    else:  # ceramic cup / plate
        f = rng.uniform(2800, 3900)
        fr = f * np.array([1.0, 1.43, 2.1])
        dec = np.array([0.25, 0.15, 0.1])
    n = int(1.5 * SR)
    y = dsp.modal(fr, dec, np.array([1.0, 0.6, 0.4, 0.2])[: len(fr)], n, 0.0, int(rng.integers(1e9)))
    return y * level * 0.25


def suitcase(seed, level=1.0):
    rng = R(seed)
    n = int(1.0 * SR)
    creak = door("creak", seed)[:n] * 0.5
    latch = dsp.modal(np.array([3100.0, 4700]), np.array([0.04, 0.03]), np.array([0.6, 0.4]), n, 0.0, 3)
    sh = np.zeros(n)
    sh[int(0.6 * SR):] = latch[: n - int(0.6 * SR)]
    return (creak + sh) * level


def cradle(dur, seed, level=1.0, period=2.3):
    """A wooden cradle rocking: a soft creak at each end of the swing."""
    rng = R(seed)
    n = int(dur * SR)
    out = np.zeros(n)
    tt = 0.2
    while tt < dur - 1.0:
        c = door("creak", int(rng.integers(1e9)))[: int(0.5 * SR)]
        c = dsp.eq(c, "lp", 1800, 0.7) * np.hanning(len(c))
        i = int(tt * SR)
        j = min(n, i + len(c))
        out[i:j] += c[: j - i] * rng.uniform(0.5, 1.0)
        tt += period / 2 * rng.uniform(0.95, 1.05)
    return out * level * 0.5


def bodyfall(seed, level=1.0):
    rng = R(seed)
    n = int(1.0 * SR)
    t = _t(n)
    thud = np.sin(2 * np.pi * 72 * t) * np.exp(-t / 0.09) + \
        dsp.eq(rng.standard_normal(n), "lp", 700, 0.7) * np.exp(-t / 0.03) * 0.7
    cloth = silk(0.6, seed + 1)
    out = thud * 0.9
    out[: len(cloth)] += cloth * 0.6
    return out * level * 0.6


def chair(seed, level=1.0):
    """An empty wooden chair, touched: a single slow creak."""
    c = door("creak", seed)
    return dsp.eq(c, "lp", 2200, 0.7) * level * 0.7


def curtain(dur, seed, level=1.0):
    """A heavy velvet curtain descending, its weighted hem landing on the boards."""
    rng = R(seed)
    n = int((dur + 1.5) * SR)
    t = _t(n)
    sw = dsp.eq(dsp.pink(n, seed), "bp", 600, 0.5)
    env = np.clip(t / 0.8, 0, 1) ** 2 * np.clip((dur - t) / 0.2, 0, 1)
    land = np.zeros(n)
    i = int(dur * SR)
    L = n - i
    tt = _t(L)
    land[i:] = (np.sin(2 * np.pi * 65 * tt) * np.exp(-tt / 0.12) +
                dsp.eq(rng.standard_normal(L), "lp", 900, 0.7) * np.exp(-tt / 0.04) * 0.6)
    return (sw * env * 0.6 + land * 1.2) * level * 0.45


def rice(dur, seed, level=1.0):
    rng = R(seed)
    n = int(dur * SR)
    out = np.zeros(n)
    k = rng.integers(0, n, int(dur * 900))
    out[k] = rng.uniform(-1, 1, len(k))
    out = dsp.eq(dsp.eq(out, "hp", 3000, 0.7), "peak", 6500, 1.0, 4)
    env = np.exp(-_t(n) / (0.5 * dur))
    return out * env * level * 0.25


# =================================================================== atmospheres

def room_tone(dur, seed, level=1.0, colour=900):
    n = int(dur * SR)
    x = dsp.pink(n, seed)
    y = dsp.eq(dsp.eq(x, "lp", colour, 0.7), "peak", colour * 0.3, 2, 4)
    return y * level * 0.04


def hall_air(dur, seed, level=1.0):
    n = int(dur * SR)
    x = dsp.pink(n, seed)
    y = dsp.eq(x, "lp", 420, 0.7) + 0.15 * dsp.eq(x, "bp", 2500, 0.5)
    return y * level * 0.05


def swifts(dur, seed, level=1.0, passes=4):
    """Apus apus: screaming flocks passing overhead (FM trills with Doppler and pan sweeps)."""
    rng = R(seed)
    n = int(dur * SR)
    out = np.zeros((2, n), dtype=np.float32)
    for p in range(passes):
        t0 = rng.uniform(0, max(0.1, dur - 2.5))
        birds = rng.integers(3, 7)
        p0, p1 = rng.choice([-1, 1]) * rng.uniform(0.6, 1.0), 0
        p1 = -p0
        for b in range(birds):
            d = rng.uniform(0.45, 1.1)
            m = int(d * SR)
            tt = _t(m)
            fc = rng.uniform(5000, 7200)
            dop = 1 + 0.06 * np.cos(np.pi * tt / d)
            fm = np.sin(2 * np.pi * rng.uniform(28, 42) * tt)
            f = fc * dop * (1 + 0.16 * fm)
            ph = np.cumsum(f) / SR
            y = np.sin(2 * np.pi * ph) * (0.6 + 0.4 * np.abs(fm))
            y += 0.3 * np.sin(4 * np.pi * ph)
            env = np.sin(np.pi * tt / d) ** 2 * (0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(6, 11) * tt) ** 2)
            y = dsp.eq(y * env, "lp", 9000, 0.7)
            i = int((t0 + rng.uniform(0, 1.2)) * SR)
            j = min(n, i + m)
            out[:, i:j] += pan_sweep(y[: j - i], p0, p1) * rng.uniform(0.4, 1.0)
    return out * level * 0.12


def cicadas(dur, seed, level=1.0, count=3):
    rng = R(seed)
    n = int(dur * SR)
    out = np.zeros((2, n), dtype=np.float32)
    t = _t(n)
    for c in range(count):
        x = rng.standard_normal(n)
        y = dsp.eq(dsp.eq(x, "bp", rng.uniform(4300, 6200), 3.5), "bp", rng.uniform(4300, 6200), 2.0)
        am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * rng.uniform(18, 34) * t))
        phrase = np.clip(dsp.smooth_noise(n, 0.12, seed + c) * 1.6 + 0.6, 0, 1)
        out += stereo(y * am * phrase, rng.uniform(-0.8, 0.8))
    return out * level * 0.05


def clock(dur, seed, level=1.0, period=1.0, kind="pendulum"):
    rng = R(seed)
    n = int(dur * SR)
    out = np.zeros(n)
    k = 0
    tt = rng.uniform(0, period)
    while tt < dur:
        L = int(0.08 * SR)
        x = rng.standard_normal(L) * np.exp(-np.arange(L) / (0.0015 * SR))
        f = 2100 if k % 2 == 0 else 1750
        y = dsp.eq(x, "bp", f, 6) + 0.4 * dsp.eq(x, "bp", f * 2.3, 8)
        i = int(tt * SR)
        j = min(n, i + L)
        out[i:j] += y[: j - i]
        tt += period
        k += 1
    return out * level * 0.3


def wind(dur, seed, level=1.0, gusty=1.0, whistle=True):
    """The bora: gusting band noise with a low rumble and whistling rigging."""
    rng = R(seed)
    n = int(dur * SR)
    gust = np.clip(0.45 + 0.55 * dsp.smooth_noise(n, 0.35, seed) * gusty, 0.05, 1.2) ** 1.5
    base = dsp.pink(n, seed + 1)
    y = dsp.eq(dsp.eq(base, "bp", 600, 0.5), "lp", 2500, 0.7) * gust
    rumble = dsp.eq(dsp.pink(n, seed + 2), "lp", 120, 0.7) * gust * 1.5
    w = np.zeros(n)
    if whistle:
        for k in range(3):
            f0 = rng.uniform(700, 1600)
            fr = f0 * (1 + 0.04 * dsp.smooth_noise(n, 0.5, seed + 10 + k))
            ph = np.cumsum(fr) / SR
            w += np.sin(2 * np.pi * ph) * np.clip(gust - 0.6, 0, 1) ** 2 * 0.25
    mono = y + rumble + w
    l = mono + 0.3 * dsp.eq(dsp.pink(n, seed + 7), "bp", 800, 0.6) * gust
    r = mono + 0.3 * dsp.eq(dsp.pink(n, seed + 8), "bp", 800, 0.6) * gust
    return np.stack([l, r]).astype(np.float32) * level * 0.2


def shutters(dur, seed, level=1.0, gusts=None):
    rng = R(seed)
    n = int(dur * SR)
    out = np.zeros(n)
    tt = rng.uniform(0.2, 1.0)
    while tt < dur:
        for k in range(rng.integers(2, 5)):
            L = int(0.06 * SR)
            x = rng.standard_normal(L) * np.exp(-np.arange(L) / (0.006 * SR))
            y = dsp.eq(x, "bp", rng.uniform(500, 1100), 2.5)
            i = int((tt + k * rng.uniform(0.05, 0.11)) * SR)
            j = min(n, i + L)
            if i < n:
                out[i:j] += y[: j - i] * rng.uniform(0.4, 1.0)
        tt += rng.uniform(1.2, 3.8)
    return out * level * 0.4


def sea(dur, seed, level=1.0, close=0.5):
    """Adriatic at the Molo: slow swells, wash, lapping against stone."""
    rng = R(seed)
    n = int(dur * SR)
    t = _t(n)
    period = rng.uniform(6.5, 9.0)
    swell = 0.5 + 0.5 * np.sin(2 * np.pi * t / period + rng.uniform(0, 6)) ** 3
    swell *= 0.75 + 0.25 * dsp.smooth_noise(n, 0.1, seed)
    low = dsp.eq(dsp.pink(n, seed), "lp", 400, 0.7) * swell
    wash_env = np.roll(swell, int(1.2 * SR)) ** 2
    wash = dsp.eq(dsp.pink(n, seed + 1), "hp", 1200, 0.7) * wash_env
    lap = np.zeros(n)
    k = rng.integers(0, n, int(dur * 3))
    lap[k] = rng.uniform(-1, 1, len(k))
    lap = dsp.eq(dsp.eq(lap, "lp", 1500, 0.7), "peak", 400, 1.5, 6) * close
    l = low + 0.6 * wash + lap * 0.4
    r = np.roll(low, 1200) + 0.6 * np.roll(wash, 2400) + lap * 0.3
    return np.stack([l, r]).astype(np.float32) * level * 0.25


def gulls(dur, seed, level=1.0, calls=4):
    rng = R(seed)
    n = int(dur * SR)
    out = np.zeros((2, n), dtype=np.float32)
    for c in range(calls):
        t0 = rng.uniform(0, max(0.1, dur - 2.0))
        pan = rng.uniform(-0.9, 0.9)
        dist = rng.uniform(0.3, 1.0)
        for k in range(rng.integers(3, 7)):
            d = rng.uniform(0.18, 0.32)
            m = int(d * SR)
            tt = _t(m)
            f = rng.uniform(1300, 1800) * (1 + 0.35 * np.sin(np.pi * tt / d)) * (1 - 0.2 * tt / d)
            ph = np.cumsum(f) / SR
            y = dsp.saw_blep(f, 0.0) * 0.5 + np.sin(2 * np.pi * ph)
            y = dsp.eq(dsp.eq(y, "peak", 2600, 2, 8), "lp", 5000 * (1.2 - dist), 0.7)
            y *= np.sin(np.pi * tt / d) ** 1.2
            i = int((t0 + k * rng.uniform(0.26, 0.4)) * SR)
            j = min(n, i + m)
            out[:, i:j] += stereo(y[: j - i] * (1.1 - dist), pan)
    return out * level * 0.08


def ship_horn(seed, level=1.0, dur=3.2):
    rng = R(seed)
    n = int((dur + 1) * SR)
    t = _t(n)
    f = np.full(n, 110.0)
    y = dsp.saw_blep(f) + 0.7 * dsp.saw_blep(f * 1.26)
    y = dsp.eq(dsp.eq(y, "lp", 700, 0.7), "peak", 320, 1.5, 6)
    env = np.clip(t / 0.25, 0, 1) * np.clip((dur - t) / 0.4, 0, 1)
    return y * env * level * 0.1


def steam(dur, seed, level=1.0):
    n = int(dur * SR)
    x = dsp.pink(n, seed) + 0.5 * R(seed).standard_normal(n)
    y = dsp.eq(dsp.eq(x, "hp", 2200, 0.7), "peak", 5500, 0.8, 4)
    fl = 0.7 + 0.3 * dsp.smooth_noise(n, 0.8, seed)
    return y * fl * level * 0.06


def locomotive(dur, seed, level=1.0, depart_at=None, depart_len=4.0):
    """Idle chuffs and pump; from depart_at the chuffs accelerate and the rail joints begin."""
    rng = R(seed)
    n = int(dur * SR)
    t = _t(n)
    out = np.zeros(n)
    rate = np.full(n, 0.7)
    if depart_at is not None:
        x = np.clip((t - depart_at) / depart_len, 0, 1)
        rate = 0.7 + 5.5 * x ** 1.6
    ph = np.cumsum(rate) / SR
    hits = np.where(np.diff(np.floor(ph)) > 0)[0]
    for h in hits:
        L = int(0.35 * SR)
        y = dsp.eq(rng.standard_normal(L), "bp", rng.uniform(300, 600), 0.8) * \
            np.exp(-np.arange(L) / (0.09 * SR))
        j = min(n, h + L)
        out[h:j] += y[: j - h] * rng.uniform(0.6, 1.0)
    rumble = dsp.eq(dsp.pink(n, seed + 3), "lp", 90, 0.7) * (0.4 + 0.6 * np.clip(rate / 6, 0, 1))
    clat = np.zeros(n)
    if depart_at is not None:
        jr = np.cumsum(np.clip((t - depart_at - 1.0) / 6.0, 0, 1) * 3.5) / SR
        jh = np.where(np.diff(np.floor(jr)) > 0)[0]
        for h in jh:
            for off in (0, int(0.11 * SR)):
                L = int(0.05 * SR)
                y = dsp.modal(np.array([420.0, 980, 1700]), np.array([0.08, 0.05, 0.03]),
                              np.array([0.8, 0.5, 0.3]), L, 0.0, int(rng.integers(1e9)))
                i = h + off
                j = min(n, i + L)
                if i < n:
                    clat[i:j] += y[: j - i]
    return (out * 0.6 + rumble * 0.8 + clat * 0.5) * level * 0.35


def steam_whistle(seed, level=1.0, dur=1.6):
    rng = R(seed)
    n = int((dur + 0.5) * SR)
    t = _t(n)
    y = np.zeros(n)
    for f in (480.0, 600.0, 720.0):
        fr = f * (1 + 0.004 * dsp.smooth_noise(n, 3, int(f)))
        y += np.sin(2 * np.pi * np.cumsum(fr) / SR)
    y += 0.4 * dsp.eq(rng.standard_normal(n), "bp", 1500, 1.0)
    env = np.clip(t / 0.08, 0, 1) * np.clip((dur - t) / 0.3, 0, 1)
    return y * env * level * 0.12


def pea_whistle(seed, level=1.0, dur=0.7):
    n = int(dur * SR)
    t = _t(n)
    am = 0.55 + 0.45 * np.sin(2 * np.pi * 38 * t)
    y = np.sin(2 * np.pi * np.cumsum(np.full(n, 2900.0) * (1 + 0.02 * am)) / SR) * am
    env = np.clip(t / 0.02, 0, 1) * np.clip((dur - t) / 0.05, 0, 1)
    return y * env * level * 0.1


def distant_bell(midi, seed, level=1.0):
    y = bell(midi, 4.0, 0.6, "church", seed)
    return dsp.eq(dsp.eq(y, "lp", 2500, 0.7), "hp", 120, 0.7) * level


def tram_bell(seed, level=1.0):
    y = dsp.modal(np.array([1850.0, 2950, 4600]), np.array([0.9, 0.6, 0.4]), np.array([1, .5, .3]),
                  int(1.5 * SR), 0.0, seed)
    y2 = np.roll(y, int(0.18 * SR)) * 0.8
    return (y + y2) * level * 0.12


def cart(dur, seed, level=1.0):
    rng = R(seed)
    n = int(dur * SR)
    rumble = dsp.eq(dsp.pink(n, seed), "lp", 300, 0.7)
    cob = np.zeros(n)
    k = rng.integers(0, n, int(dur * 14))
    cob[k] = rng.uniform(-1, 1, len(k))
    cob = dsp.eq(cob, "bp", 800, 1.0)
    creak = door("creak", seed)[:n] if n <= int(1.6 * SR) else np.resize(door("creak", seed), n)
    env = np.sin(np.pi * _t(n) / dur) ** 1.5
    return (rumble * 0.5 + cob * 0.6 + creak * 0.3) * env * level * 0.25


# =================================================================== design (sub / LFE / psychoacoustic)

def sub_hit(seed, level=1.0, f0=55.0, f1=28.0, decay=1.6):
    n = int((decay + 0.5) * SR)
    t = _t(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.12)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (decay / 3)) * np.clip(t / 0.004, 0, 1)
    return y * level * 0.8


def heartbeat(dur, bpm0, bpm1, seed, level=1.0):
    n = int(dur * SR)
    out = np.zeros(n)
    t = 0.0
    while t < dur:
        bpm = bpm0 + (bpm1 - bpm0) * t / dur
        for off, f, g in ((0.0, 56.0, 1.0), (0.26 * 60 / bpm, 48.0, 0.7)):
            L = int(0.16 * SR)
            tt = _t(L)
            y = np.sin(2 * np.pi * f * tt * (1 - 0.3 * tt / 0.16)) * np.sin(np.pi * tt / 0.16) ** 2
            i = int((t + off) * SR)
            j = min(n, i + L)
            if i < n:
                out[i:j] += y[: j - i] * g
        t += 60.0 / bpm
    return out * level * 0.9


def pressure(dur, seed, level=1.0, f=31.0):
    n = int(dur * SR)
    t = _t(n)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    y = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t + 1.0)
    y *= 1 + 0.2 * np.sin(2 * np.pi * 0.31 * t)
    return y * env * level * 0.35


def air_rush(dur, seed, level=1.0, rising=True):
    """A transition made from moving air (flats flying out), not a synthetic sweep."""
    n = int(dur * SR)
    t = _t(n)
    x = dsp.pink(n, seed)
    out = np.zeros(n)
    blk = 2048
    for i in range(0, n, blk):
        j = min(n, i + blk)
        a = i / n
        fc = 300 + (2600 if rising else 900) * (a if rising else 1 - a)
        out[i:j] = dsp.eq(x[max(0, i - 4096):j], "bp", fc, 0.7)[-(j - i):]
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    return out * env * level * 0.4
