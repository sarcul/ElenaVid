"""The singing voice (tier 1: VOX). Formant synthesis with an Italian/ecclesiastical-Latin phonemiser.

Source: band-limited glottal-flow-derivative wavetables (Rosenberg pulses: a soft, open-quotient
shape and a pressed, abrupt-closure shape, cross-faded by vocal effort), with jitter, shimmer and
aspiration gated by the glottal cycle. Tract: five cascaded formant resonators updated at block rate,
with soprano formant tuning (F1 follows f0 on high notes). A parallel noise branch makes the
fricatives and plosive bursts. Consonants are sung before the beat so vowels land on it.
"""
from __future__ import annotations

import math
import unicodedata

import numpy as np
from numba import njit

from ..config import SR
from . import dsp

# ------------------------------------------------------------------ formant tables (Hz)
VOWELS = {
    "soprano": {"a": ([800, 1150, 2900, 3900, 4950], [80, 90, 120, 130, 140]),
                "e": ([400, 2000, 2800, 3600, 4950], [60, 100, 120, 150, 200]),
                "i": ([270, 2140, 2950, 3900, 4950], [60, 90, 100, 120, 120]),
                "o": ([450, 800, 2830, 3800, 4950], [40, 80, 100, 120, 120]),
                "u": ([325, 700, 2700, 3800, 4950], [50, 60, 170, 180, 200])},
    "alto": {"a": ([800, 1150, 2800, 3500, 4950], [80, 90, 120, 130, 140]),
             "e": ([400, 1600, 2700, 3300, 4950], [60, 80, 120, 150, 200]),
             "i": ([350, 1700, 2700, 3700, 4950], [50, 100, 120, 150, 200]),
             "o": ([450, 800, 2830, 3500, 4950], [70, 80, 100, 130, 135]),
             "u": ([325, 700, 2530, 3500, 4950], [50, 60, 170, 180, 200])},
    "tenor": {"a": ([650, 1080, 2650, 2900, 3250], [80, 90, 120, 130, 140]),
              "e": ([400, 1700, 2600, 3200, 3580], [70, 80, 100, 120, 120]),
              "i": ([290, 1870, 2800, 3250, 3540], [40, 90, 100, 120, 120]),
              "o": ([400, 800, 2600, 2800, 3000], [40, 80, 100, 120, 120]),
              "u": ([350, 600, 2700, 2900, 3300], [40, 60, 100, 120, 120])},
    "bass": {"a": ([600, 1040, 2250, 2450, 2750], [60, 70, 110, 120, 130]),
             "e": ([400, 1620, 2400, 2800, 3100], [40, 80, 100, 120, 120]),
             "i": ([250, 1750, 2600, 3050, 3340], [60, 90, 100, 120, 120]),
             "o": ([400, 750, 2400, 2600, 2900], [40, 80, 100, 120, 120]),
             "u": ([350, 600, 2400, 2675, 2950], [40, 80, 100, 120, 120])},
}

# voice types: table, formant scale, vibrato rate, vibrato cents, breathiness, ring (dB), octave
VOICE_TYPES = {
    "sop": ("soprano", 1.0, 5.8, 48.0, 0.05, 2.0),
    "mez": ("alto", 1.0, 5.5, 40.0, 0.06, 3.0),
    "ten": ("tenor", 1.0, 5.5, 34.0, 0.05, 6.0),
    "bar": ("bass", 1.06, 5.3, 30.0, 0.05, 7.0),
    "bbar": ("bass", 1.0, 5.1, 26.0, 0.05, 6.0),
    "treble": ("soprano", 1.08, 5.0, 0.0, 0.10, 0.0),
    "ch_s": ("soprano", 1.0, 5.6, 26.0, 0.07, 1.0),
    "ch_a": ("alto", 1.0, 5.5, 24.0, 0.07, 2.0),
    "ch_t": ("tenor", 1.0, 5.4, 22.0, 0.07, 4.0),
    "ch_b": ("bass", 1.0, 5.2, 20.0, 0.07, 4.0),
}

# consonants: kind, voicing amplitude, noise amplitude, noise centre Hz, noise bw, duration s,
#             formant locus [F1, F2, F3] (None = keep the vowel's)
CONS = {
    "p": ("stop", 0.0, 0.22, 1300, 1800, 0.055, None),
    "t": ("stop", 0.0, 0.30, 4300, 2200, 0.050, None),
    "k": ("stop", 0.0, 0.30, 2300, 1600, 0.055, None),
    "b": ("vstop", 0.12, 0.25, 1000, 2000, 0.045, [200, 900, 2300]),
    "d": ("vstop", 0.12, 0.3, 3500, 3000, 0.040, [200, 1600, 2600]),
    "g": ("vstop", 0.12, 0.3, 2000, 2000, 0.045, [200, 1900, 2400]),
    "f": ("fric", 0.0, 0.10, 5000, 4000, 0.075, None),
    "v": ("vfric", 0.42, 0.07, 4000, 5000, 0.060, [250, 1100, 2400]),
    "s": ("fric", 0.0, 0.30, 6800, 2800, 0.085, None),
    "z": ("vfric", 0.42, 0.25, 6000, 3500, 0.065, None),
    "S": ("fric", 0.0, 0.28, 3300, 1800, 0.085, None),          # sh
    "ts": ("affr", 0.0, 0.28, 6200, 2800, 0.080, None),
    "dz": ("vaffr", 0.35, 0.25, 6000, 3500, 0.070, None),
    "tS": ("affr", 0.0, 0.28, 3300, 1800, 0.085, None),
    "dZ": ("vaffr", 0.35, 0.28, 3200, 2400, 0.075, [250, 1900, 2500]),
    "m": ("nasal", 0.34, 0.0, 0, 0, 0.065, [270, 1000, 2400]),
    "n": ("nasal", 0.34, 0.0, 0, 0, 0.060, [270, 1500, 2500]),
    "N": ("nasal", 0.34, 0.0, 0, 0, 0.065, [270, 2000, 2700]),   # gn
    "l": ("liquid", 0.72, 0.0, 0, 0, 0.050, [360, 1250, 2700]),
    "L": ("liquid", 0.66, 0.0, 0, 0, 0.060, [300, 2000, 2700]),  # gli
    "r": ("trill", 0.62, 0.0, 0, 0, 0.065, None),
    "j": ("glide", 0.9, 0.0, 0, 0, 0.045, None),
    "w": ("glide", 0.9, 0.0, 0, 0, 0.045, None),
}
VOWEL_SET = set("aeiou")
HIATUS = {"mia", "mio", "mie", "dio", "sia", "tua", "tuo", "tue", "io", "via"}


# ------------------------------------------------------------------ Italian phonemiser

def _strip_accents(s):
    out = []
    for ch in unicodedata.normalize("NFD", s):
        if unicodedata.category(ch) != "Mn":
            out.append(ch)
    return "".join(out)


def phonemise(syl: str):
    """Return (onset[list], vowels[list of (v, synalepha_full)], coda[list]) for one sung syllable."""
    s = _strip_accents(syl.lower()).replace("'", "").replace("’", "")
    full_split = "_" in s
    if s.startswith("ae"):                     # ecclesiastical Latin 'ae' = e
        s = "e" + s[2:]
    hiatus = s in HIATUS
    s = s.replace("_", "")
    ph = []
    i = 0
    n = len(s)

    def nxt(k):
        return s[k] if k < n else ""

    while i < n:
        c = s[i]
        if c in VOWEL_SET:
            ph.append(c)
            i += 1
            continue
        if s.startswith("sch", i):
            ph += ["s", "k"]
            i += 3
            continue
        if s.startswith("sc", i) and nxt(i + 2) in ("e", "i"):
            ph.append("S")
            i += 2
            if nxt(i) == "i" and nxt(i + 1) in VOWEL_SET:
                i += 1
            continue
        if s.startswith("gli", i):
            ph.append("L")
            i += 3
            if not (i < n and s[i] in VOWEL_SET):
                ph.append("i")
            continue
        if s.startswith("gn", i):
            ph.append("N")
            i += 2
            continue
        if s.startswith("ch", i):
            ph.append("k")
            i += 2
            continue
        if s.startswith("qu", i):
            ph += ["k", "w"]
            i += 2
            continue
        if c == "c":
            if nxt(i + 1) in ("e", "i"):
                ph.append("tS")
                i += 1
                if nxt(i) == "i" and nxt(i + 1) in VOWEL_SET:
                    i += 1
                continue
            ph.append("k")
            i += 1
            continue
        if c == "g":
            if nxt(i + 1) in ("e", "i"):
                ph.append("dZ")
                i += 1
                if nxt(i) == "i" and nxt(i + 1) in VOWEL_SET:
                    i += 1
                continue
            ph.append("g")
            i += 1
            continue
        if c == "z":
            ph.append("ts")
            i += 1
            continue
        if c == "x":
            ph += ["k", "s"]
            i += 1
            continue
        if c == "y":
            ph.append("i")
            i += 1
            continue
        if c == "s" and nxt(i + 1) in ("b", "d", "g", "v", "m", "n", "l", "r"):
            ph.append("z")                     # s is voiced before voiced consonants
            i += 1
            continue
        if c in CONS:                          # 'h' is silent and simply skipped
            ph.append(c)
        i += 1
    # split into onset / nucleus / coda; i and u next to vowels become glides (unless synalepha)
    vidx = [k for k, p in enumerate(ph) if p in VOWEL_SET]
    if not vidx:
        return ph, [("a", False)], []
    first, last = vidx[0], vidx[-1]
    onset = ph[:first]
    nucleus = ph[first:last + 1]
    coda = ph[last + 1:]
    vowels = []
    nv = [p for p in nucleus if p in VOWEL_SET]
    if hiatus:
        full_split = True                      # mi-a, Di-o, si-a: the stressed i/u is a vowel
    if not full_split and nv[:2] == ["u", "i"]:
        coda = ["j"] + coda                    # lui, cui: a falling diphthong
        nv = ["u"] + nv[2:]
    if not full_split and len(nv) >= 2:
        # rising diphthong (ia, ie, io, iu, ua, uo...) -> glide in onset
        while len(nv) >= 2 and nv[0] in ("i", "u") and nv[1] != nv[0]:
            onset.append("j" if nv[0] == "i" else "w")
            nv = nv[1:]
        # falling diphthong (ai, ei, oi, au) -> short glide at the end
        if len(nv) >= 2 and nv[-1] in ("i", "u"):
            coda = ["j" if nv[-1] == "i" else "w"] + coda
            nv = nv[:-1]
        vowels = [(v, False) for v in nv[-1:]]
    else:
        vowels = [(v, True) for v in nv]
    return onset, vowels, [c for c in coda if c not in VOWEL_SET]


# ------------------------------------------------------------------ glottal wavetables

_TABLES = None
LEVEL_TOPS = np.array([110.0, 220.0, 440.0, 880.0, 1760.0])


def _rosenberg(oq, sq, N):
    t = np.arange(N) / N
    Tp = oq * sq / (1 + sq)
    Tn = oq / (1 + sq)
    g = np.zeros(N)
    m1 = t < Tp
    g[m1] = 0.5 * (1 - np.cos(np.pi * t[m1] / Tp))
    m2 = (t >= Tp) & (t < Tp + Tn)
    g[m2] = np.cos(0.5 * np.pi * (t[m2] - Tp) / Tn)
    return g


def tables():
    global _TABLES
    if _TABLES is not None:
        return _TABLES
    N = 2048
    out = np.zeros((2, len(LEVEL_TOPS), N + 1))
    for si, (oq, sq) in enumerate(((0.72, 1.6), (0.48, 3.2))):
        flow = _rosenberg(oq, sq, N)
        der = np.roll(flow, -1) - flow
        spec = np.fft.rfft(der)
        for li, top in enumerate(LEVEL_TOPS):
            H = int(0.45 * SR / top)
            sp = spec.copy()
            sp[0] = 0
            sp[H + 1:] = 0
            tab = np.fft.irfft(sp, N)
            tab /= np.sqrt(np.mean(tab ** 2)) + 1e-12
            out[si, li, :N] = tab
            out[si, li, N] = tab[0]
    _TABLES = out
    return out


@njit(cache=True, fastmath=True)
def voice_kernel(f0, amp, press, asp, F, B, fric, fric_f, fric_bw, tabs, seed, block):
    n = f0.shape[0]
    np.random.seed(seed)
    out = np.empty(n)
    N = tabs.shape[2] - 1
    nl = tabs.shape[1]
    ph = np.random.uniform(0.0, 1.0)
    nf = F.shape[0]
    # cascade formant states
    s1 = np.zeros(nf)
    s2 = np.zeros(nf)
    c1 = np.zeros(nf)
    c2 = np.zeros(nf)
    gn = np.zeros(nf)
    # noise band-pass state (true band-pass: zeros at DC and Nyquist)
    n1 = 0.0
    n2 = 0.0
    x1 = 0.0
    x2 = 0.0
    m1 = 0.0
    m2 = 0.0
    y1b = 0.0
    y2b = 0.0
    nc1 = 0.0
    nc2 = 0.0
    ng = 0.0
    shim = 1.0
    jit = 0.0
    for i in range(n):
        if i % block == 0:
            for k in range(nf):
                f = F[k, i]
                bw = B[k, i]
                r = math.exp(-math.pi * bw / SR)
                cs = math.cos(2.0 * math.pi * f / SR)
                c1[k] = 2.0 * r * cs
                c2[k] = -r * r
                gn[k] = 1.0 - c1[k] - c2[k]          # unity gain at DC
            ff = fric_f[i]
            if ff < 100.0:
                ff = 100.0
            r = math.exp(-math.pi * fric_bw[i] / SR)
            nc1 = 2.0 * r * math.cos(2.0 * math.pi * ff / SR)
            nc2 = -r * r
            ng = (1.0 - r * r) * 0.5
        f = f0[i] * (1.0 + jit)
        dph = f / SR
        prev = ph
        ph += dph
        if ph >= 1.0:
            ph -= 1.0
            # a new glottal cycle: refresh jitter and shimmer
            jit = np.random.normal(0.0, 0.0028)
            shim = 1.0 + np.random.normal(0.0, 0.035)
        # level selection by f0 (cross-fade between adjacent band-limited tables)
        lv = math.log2(max(f, 55.0) / 110.0)
        if lv < 0.0:
            lv = 0.0
        if lv > nl - 1.001:
            lv = nl - 1.001
        li = int(lv)
        lf = lv - li
        pos = ph * N
        pi = int(pos)
        pf = pos - pi
        p = press[i]
        s_a = tabs[0, li, pi] * (1 - pf) + tabs[0, li, pi + 1] * pf
        s_b = tabs[0, li + 1, pi] * (1 - pf) + tabs[0, li + 1, pi + 1] * pf
        h_a = tabs[1, li, pi] * (1 - pf) + tabs[1, li, pi + 1] * pf
        h_b = tabs[1, li + 1, pi] * (1 - pf) + tabs[1, li + 1, pi + 1] * pf
        soft = s_a * (1 - lf) + s_b * lf
        hard = h_a * (1 - lf) + h_b * lf
        g = (soft * (1 - p) + hard * p) * amp[i] * shim
        # aspiration, gated by the open phase
        wn = np.random.normal(0.0, 1.0)
        gate = 1.0 if ph < 0.65 else 0.35
        x = g + wn * asp[i] * gate * (0.3 + amp[i])
        for k in range(nf):
            v = gn[k] * x + c1[k] * s1[k] + c2[k] * s2[k]
            s2[k] = s1[k]
            s1[k] = v
            x = v
        # frication / bursts through two cascaded constant-peak-gain band-passes (4th order)
        fn = np.random.normal(0.0, 1.0) * fric[i]
        v = ng * (fn - x2) + nc1 * n1 + nc2 * n2
        x2 = x1
        x1 = fn
        n2 = n1
        n1 = v
        u = ng * (v - y2b) + nc1 * m1 + nc2 * m2
        y2b = y1b
        y1b = v
        m2 = m1
        m1 = u
        out[i] = x + u * 3.0
    return out


# ------------------------------------------------------------------ phrase rendering

F6 = {"soprano": 5700.0, "alto": 5400.0, "tenor": 4300.0, "bass": 3900.0}


def _vowel_targets(vtable, v, scale):
    F, Bw = VOWELS[vtable][v]
    F = list(F) + [F6[vtable]]
    Bw = list(Bw) + [420.0]
    return np.array(F, dtype=float) * scale, np.array(Bw, dtype=float)


STYLE = {  # vibrato factor, portamento s, breath add, effort add
    "aria": (1.0, 0.09, 0.0, 0.0), "duet": (1.0, 0.09, 0.0, 0.0), "vow": (0.8, 0.1, 0.02, -0.1),
    "parlato": (0.25, 0.05, 0.03, -0.05), "aside": (0.6, 0.08, 0.06, -0.15),
    "lullaby": (0.6, 0.11, 0.05, -0.15), "chorus": (1.0, 0.07, 0.0, 0.0),
    "latin": (0.9, 0.1, 0.01, -0.05), "vision": (0.85, 0.12, 0.0, 0.0),
    "offstage": (0.85, 0.12, 0.0, -0.05), "heat": (1.25, 0.06, 0.02, 0.25),
    "letter_read": (0.15, 0.04, 0.05, -0.15),
}


def render_phrase(notes, vtype, seed, singer=None):
    """Render one legato phrase. notes: list of dicts with t, dur, midi, vel, lyric, tags.

    Returns (start_time_s, mono array).
    """
    singer = singer or {}
    table, fscale, vrate, vcents, breath0, ring = VOICE_TYPES[vtype]
    fscale *= singer.get("fscale", 1.0)
    rng = np.random.default_rng(seed)
    style = notes[0]["tags"].get("style", "aria")
    vfac, porta, b_add, e_add = STYLE.get(style, STYLE["aria"])
    # ---- syllable plans
    plans = []
    last_vowels = [("a", False)]
    for nt in notes:
        lyr = nt.get("lyric") or "a"
        if lyr == "_":
            plans.append(([], [(last_vowels[-1][0], False)], []))
            continue
        on, vs, co = phonemise(lyr)
        plans.append((on, vs, co))
        last_vowels = vs
    pre = 0.0
    if plans[0][0]:
        pre = sum(CONS[c][5] for c in plans[0][0]) + 0.01
    t0 = notes[0]["t"] - pre - 0.06
    t_end = notes[-1]["t"] + notes[-1]["dur"] + 0.25
    n = int((t_end - t0) * SR) + 1
    tt = t0 + np.arange(n) / SR
    # ---- breakpoint lists
    seg = []   # (start, end, kind, vowel or consonant, extra)
    for k, (nt, (on, vs, co)) in enumerate(zip(notes, plans)):
        s, e = nt["t"], nt["t"] + nt["dur"]
        ons_d = [CONS[c][5] for c in on]
        cod_d = [CONS[c][5] for c in co]
        # next onset steals from this note's end if legato
        nxt_on = 0.0
        if k + 1 < len(notes):
            nxt = notes[k + 1]
            if nxt["t"] - e < 0.05 and plans[k + 1][0]:
                nxt_on = sum(CONS[c][5] for c in plans[k + 1][0])
        vend = e - sum(cod_d) - nxt_on
        avail = vend - s
        if avail < 0.4 * (e - s):
            squeeze = max(0.2, (0.6 * (e - s)) / max(1e-6, sum(cod_d) + nxt_on))
            cod_d = [d * squeeze for d in cod_d]
            vend = e - sum(cod_d) - nxt_on * squeeze
        # onset consonants before s
        tc = s - sum(ons_d)
        for c, d in zip(on, ons_d):
            seg.append((tc, tc + d, "c", c, k))
            tc += d
        # vowels
        vs_list = vs
        if len(vs_list) == 1:
            seg.append((s, vend, "v", vs_list[0][0], k))
        else:
            # Italian sung diction: sustain the first vowel, articulate the rest at the end
            short = min(0.11, 0.22 * (vend - s) / (len(vs_list) - 1))
            tv = s
            for j, (v, _) in enumerate(vs_list):
                d = (vend - s) - short * (len(vs_list) - 1) if j == 0 else short
                seg.append((tv, tv + d, "v", v, k))
                tv += d
        tc = vend
        for c, d in zip(co, cod_d):
            seg.append((tc, tc + d, "c", c, k))
            tc += d
    seg.sort(key=lambda x: x[0])
    # ---- formant tracks: targets at segment centres (vowels hold), linear interpolation
    bp_t = []
    bp_F = []
    bp_B = []
    amp_t = []
    amp_v = []
    fric_t = []
    fric_v = []
    fricf_v = []
    fricbw_v = []
    prevF = None
    prevB = None
    for si_, (a, b, kind, sym, k) in enumerate(seg):
        if kind == "v":
            F, Bw = _vowel_targets(table, sym, fscale)
            m = notes[k]["midi"]
            f0 = 440 * 2 ** ((m - 69) / 12)
            if F[0] < f0 * 1.08 and f0 > 300:        # soprano formant tuning
                F[0] = f0 * 1.1
                F[1] = max(F[1], F[0] + 250)
            edge = min(0.03, (b - a) * 0.25)
            for x in (a + edge, b - edge):
                bp_t.append(x)
                bp_F.append(F)
                bp_B.append(Bw)
            prevF, prevB = F, Bw
            amp_t += [a, b]
            amp_v += [1.0, 1.0]
            fric_t += [a, b]
            fric_v += [0.0, 0.0]
            fricf_v += [3000, 3000]
            fricbw_v += [2000, 2000]
        else:
            ck, voi, nz, nf, nbw, dur, locus = CONS[sym]
            base = prevF if prevF is not None else _vowel_targets(table, "a", fscale)[0]
            baseB = prevB if prevB is not None else _vowel_targets(table, "a", fscale)[1]
            # look ahead to the next vowel for coarticulation
            nxtv = next((x for x in seg[si_ + 1:] if x[2] == "v"), None)
            if nxtv is not None:
                nF, nB = _vowel_targets(table, nxtv[3], fscale)
                base = 0.4 * base + 0.6 * nF
                baseB = 0.4 * baseB + 0.6 * nB
            F = base.copy()
            Bw = baseB.copy()
            if locus is not None:
                F[:3] = np.array(locus) * fscale
            if sym == "j":
                F[:3] = np.array(VOWELS[table]["i"][0][:3]) * fscale
            if sym == "w":
                F[:3] = np.array(VOWELS[table]["u"][0][:3]) * fscale
            if ck == "nasal":
                Bw = Bw.copy()
                Bw[1] *= 2.5
                Bw[2] *= 2.0
            bp_t.append(0.5 * (a + b))
            bp_F.append(F)
            bp_B.append(Bw)
            # voicing amplitude
            if ck in ("stop",):
                amp_t += [a + 0.008, b - 0.006]
                amp_v += [0.0, 0.0]
                fric_t += [a, b - 0.014, b - 0.012, b - 0.001]
                fric_v += [0.0, 0.0, nz, 0.0]
                fricf_v += [nf] * 4
                fricbw_v += [nbw] * 4
            elif ck == "vstop":
                amp_t += [a + 0.006, b - 0.008]
                amp_v += [voi, voi]
                fric_t += [a, b - 0.01, b - 0.008, b]
                fric_v += [0.0, 0.0, nz * 0.6, 0.0]
                fricf_v += [nf] * 4
                fricbw_v += [nbw] * 4
            elif ck in ("affr", "vaffr"):
                mid = a + 0.4 * (b - a)
                amp_t += [a + 0.004, b - 0.004]
                amp_v += [voi * 0.5, voi]
                fric_t += [a, mid, mid + 0.003, b - 0.008, b]
                fric_v += [0.0, 0.0, nz, nz * 0.7, 0.0]
                fricf_v += [nf] * 5
                fricbw_v += [nbw] * 5
            elif ck in ("fric", "vfric"):
                amp_t += [a + 0.01, b - 0.01]
                amp_v += [voi, voi]
                fric_t += [a, a + 0.015, b - 0.015, b]
                fric_v += [0.0, nz, nz, 0.0]
                fricf_v += [nf] * 4
                fricbw_v += [nbw] * 4
            elif ck == "trill":
                taps = 2 if (b - a) > 0.05 else 1
                pts = np.linspace(a, b, 2 * taps + 2)
                for j, x in enumerate(pts):
                    amp_t.append(x)
                    amp_v.append(voi if j % 2 == 0 else 0.15)
                fric_t += [a, b]
                fric_v += [0.0, 0.0]
                fricf_v += [3000, 3000]
                fricbw_v += [2000, 2000]
            else:   # nasal, liquid, glide
                amp_t += [a + 0.01, b - 0.01]
                amp_v += [voi, voi]
                fric_t += [a, b]
                fric_v += [0.0, 0.0]
                fricf_v += [3000, 3000]
                fricbw_v += [2000, 2000]
    order = np.argsort(bp_t)
    bp_t = np.array(bp_t)[order]
    bp_F = np.array(bp_F)[order]
    bp_B = np.array(bp_B)[order]
    F = np.stack([np.interp(tt, bp_t, bp_F[:, j]) for j in range(6)])
    Bm = np.stack([np.interp(tt, bp_t, bp_B[:, j]) for j in range(6)])
    o2 = np.argsort(amp_t)
    voicing = np.interp(tt, np.array(amp_t)[o2], np.array(amp_v)[o2])
    o3 = np.argsort(fric_t)
    fric = np.interp(tt, np.array(fric_t)[o3], np.array(fric_v)[o3])
    fric_f = np.interp(tt, np.array(fric_t)[o3], np.array(fricf_v)[o3])
    fric_bw = np.interp(tt, np.array(fric_t)[o3], np.array(fricbw_v)[o3])
    # ---- pitch: portamento, scoop, vibrato, drift
    pt, pm = [], []
    for k, nt in enumerate(notes):
        s, e = nt["t"], nt["t"] + nt["dur"]
        g = min(porta, 0.3 * nt["dur"])
        pt += [s + (0.0 if k == 0 else g * 0.5), e - g * 0.5]
        pm += [nt["midi"], nt["midi"]]
    pt = [t0] + pt + [t_end]
    pm = [pm[0]] + pm + [pm[-1]]
    midi = np.interp(tt, pt, pm)
    midi += -0.45 * np.exp(-np.maximum(0, tt - notes[0]["t"] + 0.02) / 0.09) * \
        (tt >= notes[0]["t"] - 0.1)
    detune = singer.get("detune", 0.0)
    vib_c = vcents * vfac * singer.get("vib", 1.0)
    vib = np.zeros(n)
    if vib_c > 0:
        rate = vrate * singer.get("rate", 1.0) * (1 + 0.05 * dsp.smooth_noise(n, 0.6, seed))
        phv = 2 * np.pi * np.cumsum(rate) / SR + rng.uniform(0, 6.28)
        depth = np.zeros(n)
        for nt in notes:
            s, e = nt["t"], nt["t"] + nt["dur"]
            if e - s < 0.28:
                continue
            on = s + min(0.22, 0.35 * (e - s))
            m = (tt >= s) & (tt <= e + 0.1)
            depth[m] = np.maximum(depth[m], np.clip((tt[m] - on) / 0.3, 0, 1))
        depth = np.convolve(depth, np.ones(2400) / 2400, mode="same")
        vib = vib_c / 100.0 * depth * np.sin(phv)
    midi = midi + vib + (detune + 4.0 * dsp.smooth_noise(n, 0.5, seed + 3)) / 100.0
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    # ---- loudness, effort, breath
    vel = np.interp(tt, [nt["t"] for nt in notes] + [notes[-1]["t"] + notes[-1]["dur"]],
                    [nt["vel"] for nt in notes] + [notes[-1]["vel"]])
    env = np.clip((tt - (notes[0]["t"] - pre - 0.05)) / 0.05, 0, 1)
    env *= np.clip((t_end - 0.2 - tt) / 0.12, 0, 1)
    # messa di voce on long notes
    for nt in notes:
        if nt["dur"] > 1.2:
            m = (tt >= nt["t"]) & (tt <= nt["t"] + nt["dur"])
            x = (tt[m] - nt["t"]) / nt["dur"]
            env[m] *= 0.88 + 0.22 * np.sin(np.pi * x) ** 1.5
        if nt["tags"].get("fade_end"):
            m = (tt >= nt["t"])
            env[m] *= np.clip(1 - (tt[m] - nt["t"]) / nt["dur"], 0, 1)
    amp = voicing * env * (0.25 + 0.75 * vel) * singer.get("gain", 1.0)
    press = np.clip((vel - 0.3) / 0.55 + e_add, 0.0, 1.0) * np.ones(n)
    asp = (breath0 + b_add + singer.get("breath", 0.0)) * np.ones(n) * 0.6
    fric = fric * env * (0.4 + 0.6 * vel)
    y = voice_kernel(f0, amp, press, asp, np.ascontiguousarray(F), np.ascontiguousarray(Bm), fric,
                     fric_f, fric_bw, tables(), int(rng.integers(1e9)), 32)
    if ring > 0:
        y = dsp.eq(y, "peak", 2900 * fscale, 1.6, ring)          # the singer's formant
    if vtype in ("ten", "bar", "bbar", "ch_t", "ch_b"):
        y = dsp.eq(y, "highshelf", 3200, 0.7, 5.0)                 # restore brilliance
    y = dsp.eq(y, "hp", 70 if vtype in ("bar", "bbar", "ch_b") else 110, 0.7)
    return t0, y


def phrases_of(notes, gap=0.1):
    notes = sorted(notes, key=lambda n: n["t"])
    out = []
    cur = []
    for nt in notes:
        if cur and nt["t"] - (cur[-1]["t"] + cur[-1]["dur"]) > gap:
            out.append(cur)
            cur = []
        cur.append(nt)
    if cur:
        out.append(cur)
    return out


def render_voice(vtype, notes, total_n, seed=0, singer=None):
    """Render all notes of one singer into a mono buffer."""
    buf = np.zeros(total_n, dtype=np.float32)
    for pi, ph in enumerate(phrases_of(notes)):
        t0, y = render_phrase(ph, vtype, seed * 1000 + pi, singer)
        s0 = int(round(t0 * SR))
        if s0 < 0:
            y = y[-s0:]
            s0 = 0
        s1 = min(total_n, s0 + len(y))
        buf[s0:s1] += y[: s1 - s0].astype(np.float32)
    return buf


def breath(dur, level, seed):
    """An inhale before a phrase."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    y = dsp.eq(dsp.eq(nz, "bp", 1500, 0.9), "peak", 2800, 1.5, 4)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    return y * env * level
