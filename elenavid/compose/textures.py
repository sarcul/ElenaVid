"""Orchestral texture generators driven by chord progressions.

A progression string looks like:  "D:3 | A7:1.5 D:1.5 | G:3"
(chord symbol : duration in crotchets; '|' is decorative and checked if bar is given).
"""
from __future__ import annotations

import random
from fractions import Fraction

from ..notation import Ev
from ..theory import Chord, voice_lead, pcs_in_range, remap, degree_of, MODES


def _num(s: str) -> float:
    return float(Fraction(s))


def prog(text: str, origin: float = 0.0, bar: float | None = None):
    out = []
    t = origin
    bar_start = origin
    for tok in text.split():
        if tok == "|":
            if bar is not None and abs((t - bar_start) - bar) > 1e-6:
                raise ValueError(f"progression bar {t - bar_start} != {bar} at {t}: {text[:60]}")
            bar_start = t
            continue
        sym, d = tok.rsplit(":", 1)
        d = _num(d)
        out.append((t, d, None if sym == "r" else Chord(sym)))
        t += d
    return out


def prog_len(p):
    return (p[-1][0] + p[-1][1] - p[0][0]) if p else 0.0


def voicings(p, ranges, bass_range=(36, 52), include_bass=True, avoid_pcs=None):
    chords = [c for _, _, c in p if c is not None]
    vs = voice_lead(chords, ranges, bass_range, include_bass, avoid_pcs=avoid_pcs)
    out = []
    k = 0
    for b, d, c in p:
        if c is None:
            out.append((b, d, None))
        else:
            out.append((b, d, vs[k]))
            k += 1
    return out


def sustain(p, ranges, vel=0.45, include_bass=False, bass_range=(36, 52), tie_common=True,
            avoid_pcs=None, art=""):
    """Sustained, voice-led chords. Returns a list of event lists, one per voice (low to high)."""
    vs = voicings(p, ranges, bass_range, include_bass, avoid_pcs)
    nvoices = len(ranges) + (1 if include_bass else 0)
    lines = [[] for _ in range(nvoices)]
    for b, d, v in vs:
        if v is None:
            continue
        for i, m in enumerate(v):
            if tie_common and lines[i] and abs(lines[i][-1].midi - m) < 1e-9 and \
                    abs(lines[i][-1].end - b) < 1e-6:
                lines[i][-1].dur += d
            else:
                lines[i].append(Ev(b, d, m, vel, art))
    return lines


def bass(p, pattern=None, lo=28, hi=48, vel=0.5, art="", octave_double=False):
    """Bass notes. pattern: list of (offset, dur) relative to each chord, None = whole chord."""
    out = []
    prev = None
    for b, d, c in p:
        if c is None:
            continue
        cands = pcs_in_range({c.bass}, lo, hi)
        m = cands[len(cands) // 2] if prev is None else min(cands, key=lambda x: abs(x - prev))
        prev = m
        pat = pattern or [(0.0, d)]
        for off, dd in pat:
            if off >= d - 1e-9:
                continue
            out.append(Ev(b + off, min(dd, d - off), m, vel, art))
            if octave_double:
                out.append(Ev(b + off, min(dd, d - off), m - 12, vel * 0.8, art))
    return out


def chord_hits(p, pattern, ranges, vel=0.4, art="", avoid_pcs=None):
    """Repeated chord stabs inside each chord span: pattern = [(offset, dur), ...]."""
    vs = voicings(p, ranges, include_bass=False, avoid_pcs=avoid_pcs)
    out = []
    for b, d, v in vs:
        if v is None:
            continue
        for off, dd in pattern:
            if off >= d - 1e-9:
                continue
            for m in v:
                out.append(Ev(b + off, min(dd, d - off), m, vel, art))
    return out


def arp(p, step=0.5, lo=48, hi=84, vel=0.4, shape="up", notes_per=None, avoid_pcs=None,
        seed=1):
    """Harp-style arpeggio through each chord's tones between lo and hi."""
    rnd = random.Random(seed)
    out = []
    for b, d, c in p:
        if c is None:
            continue
        pcs = [x for x in c.pcs if not avoid_pcs or x not in avoid_pcs]
        tones = pcs_in_range(set(pcs) | {c.bass}, lo, hi)
        if not tones:
            continue
        if shape == "updown":
            seq = tones + tones[-2:0:-1]
        elif shape == "down":
            seq = tones[::-1]
        elif shape == "wave":
            seq = tones[::2] + tones[1::2][::-1]
        else:
            seq = tones
        n = int(round(d / step)) if notes_per is None else notes_per
        for k in range(n):
            m = seq[k % len(seq)]
            out.append(Ev(b + k * step, step * 1.8, m, vel * (0.9 + 0.2 * rnd.random()), ""))
    return out


def furlana(p, lo=50, hi=74, vel=0.42):
    """6/8 forlana lilt for strings: dotted quaver-semiquaver-quaver on each dotted crotchet."""
    out = []
    vs = voicings(p, [(lo, hi)] * 3, include_bass=False)
    for b, d, v in vs:
        if v is None:
            continue
        nb = int(round(d / 1.5))
        for k in range(nb):
            t = b + k * 1.5
            for m in v:
                out.append(Ev(t + 0.0, 0.7, m, vel * 0.55, "'"))
                out.append(Ev(t + 0.75, 0.22, m, vel * 0.75, "'"))
                out.append(Ev(t + 1.0, 0.45, m, vel, "'"))
    return out


def rocking(p, lo=53, hi=72, vel=0.3, step=0.5, avoid_pcs=None):
    """Lullaby rocking: alternate low and high chord tones in quavers."""
    out = []
    for b, d, c in p:
        if c is None:
            continue
        pcs = {x for x in c.pcs if not avoid_pcs or x not in avoid_pcs}
        tones = pcs_in_range(pcs, lo, hi)
        if len(tones) < 2:
            continue
        lowt = tones[: max(1, len(tones) // 2)]
        hight = tones[len(tones) // 2:]
        n = int(round(d / step))
        for k in range(n):
            pool = lowt if k % 2 == 0 else hight
            m = pool[(k // 2) % len(pool)]
            out.append(Ev(b + k * step, step * 1.6, m, vel * (1.0 if k % 3 == 0 else 0.8), ""))
    return out


def ostinato(p, pattern, lo=40, hi=60, vel=0.5):
    """pattern: list of (offset, dur, which, accent) - which 0=bass, 1=fifth, 2=octave."""
    out = []
    span = pattern[-1][0] + pattern[-1][1]
    for b, d, c in p:
        if c is None:
            continue
        root = pcs_in_range({c.bass}, lo, hi)[0]
        fifth = root + 7 if c.fifth is not None else root + 12
        choices = [root, fifth, root + 12]
        reps = int(round(d / span))
        for r in range(max(1, reps)):
            for off, dd, which, acc in pattern:
                t = b + r * span + off
                if t >= b + d - 1e-9:
                    continue
                out.append(Ev(t, dd, choices[which], vel * (1.25 if acc else 0.85),
                              ">" if acc else "'"))
    return out


def chorale(p, ranges=((48, 62), (55, 69), (60, 74), (64, 79)), bass_range=(40, 57), vel=0.5,
            avoid_pcs=None):
    """Four-part chorale (bass + 3 upper) from chords, returned as [B, T, A, S] event lists."""
    return sustain(p, list(ranges[1:]), vel, include_bass=True, bass_range=bass_range,
                   avoid_pcs=avoid_pcs)


# ------------------------------------------------------------------ line utilities

def hairpin(evs, v0, v1):
    """Linear dynamic change across a list of events (by time)."""
    if not evs:
        return evs
    t0 = evs[0].beat
    t1 = max(e.beat for e in evs)
    for e in evs:
        a = 0.0 if t1 == t0 else (e.beat - t0) / (t1 - t0)
        e.vel = v0 + (v1 - v0) * a
    return evs


def diatonic(evs, steps: int, tonic_pc: int, mode: str = "major"):
    """Shift a line by diatonic steps (e.g. -5 = a sixth below) inside a key."""
    scale = MODES[mode]
    out = []
    for e in evs:
        octv, d, off = degree_of(int(round(e.midi)), tonic_pc, mode)
        nd = d + steps
        o2, d2 = divmod(nd, 7)
        m = tonic_pc + 12 * (octv + o2) + scale[d2] + off
        out.append(Ev(e.beat, e.dur, m, e.vel, e.art, e.lyric, None, dict(e.tags)))
    return out


def transpose(evs, semis):
    return [Ev(e.beat, e.dur, e.midi + semis, e.vel, e.art, e.lyric,
               None if e.grace is None else e.grace + semis, dict(e.tags)) for e in evs]


def remap_line(evs, src_pc, src_mode, dst_pc, dst_mode, octave_shift=0):
    return [Ev(e.beat, e.dur, remap(int(round(e.midi)), src_pc, src_mode, dst_pc, dst_mode,
                                   octave_shift), e.vel, e.art, e.lyric, None, dict(e.tags))
            for e in evs]


def clone(evs, **kw):
    out = []
    for e in evs:
        n = Ev(e.beat, e.dur, e.midi, e.vel, e.art, e.lyric, e.grace, dict(e.tags))
        for k, v in kw.items():
            setattr(n, k, v)
        out.append(n)
    return out


def strip_lyrics(evs):
    return clone(evs, lyric=None)


def vel_scale(evs, f):
    for e in evs:
        e.vel *= f
    return evs


def held(beat, dur, midis, vel=0.4, art=""):
    """One sustained chord as separate event lists per pitch."""
    return [[Ev(beat, dur, m, vel, art)] for m in midis]
