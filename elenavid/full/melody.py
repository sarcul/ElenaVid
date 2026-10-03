"""Melody for the full score.

  set_rhythm   verse syllables -> onsets and durations: dynamic programming over metrical positions,
               stressed syllables on strong beats, the line's last stress on the downbeat of its last bar
  set_pitches  rhythm -> pitches: beam search over chord tones and stepwise passing notes, shaped by a
               contour and a cadence (the Italian falling appoggiatura on the last stress)
  retext       a model phrase (from the film, or an earlier phrase of the same aria) sung to new words:
               the musical way an aria's stanzas share one tune
  recit        recitative: speech rhythm on a reciting tone, with the feminine cadence formula

Beats are crotchets. Phrases are built relative to their first downbeat (beat 0); an anacrusis has
negative beats.
"""
from __future__ import annotations

import math
import random

from ..notation import Ev
from .harmony import Key
from .prosody import Syl, last_stress

U = 0.25                               # the rhythmic grid: a semiquaver

# small costs that make each style's rhythms idiomatic (6/8 lilts in crotchet-quaver, not semiquavers)
DUR_PREF = {
    "compound": {0.25: 0.9, 0.75: 0.35, 1.0: 0.0, 0.5: 0.0, 1.5: 0.1, 2.0: 0.3, 3.0: 0.4},
    "cantabile": {0.75: 0.15, 3.0: 0.2},
    "chorus": {0.75: 0.2},
    "allegro": {0.25: 0.15},
}

DURS = {
    "cantabile": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
    "andante": [0.5, 0.75, 1.0, 1.5, 2.0],
    "allegro": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0],
    "parlante": [0.25, 0.5, 0.75, 1.0, 1.5],
    "chorus": [0.5, 0.75, 1.0, 1.5, 2.0],
    "compound": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
    "march": [0.5, 0.75, 1.0, 1.5, 2.0],
    "chant": [0.5, 1.0, 1.5, 2.0, 3.0],
}


def weight(beat: float, bar_len: float, num: int, den: int) -> float:
    """Metrical weight of a position: 4 downbeat, 3 half-bar (or compound beat), 2 beat, 1 quaver, 0."""
    pos = beat % bar_len
    if pos < 1e-6 or abs(pos - bar_len) < 1e-6:
        return 4.0
    if den == 8 and num % 3 == 0:
        if abs(pos % 1.5) < 1e-6:
            return 3.0
        if abs(pos % 0.5) < 1e-6:
            return 1.0
        return 0.0
    if num == 4 and abs(pos - 2.0) < 1e-6:
        return 3.0
    if abs(pos % 1.0) < 1e-6:
        return 2.0
    if abs(pos % 0.5) < 1e-6:
        return 1.0
    return 0.0


# ============================================================================================ rhythm
def set_rhythm(syls: list[Syl], bars: int, bar_len: float, meter=(4, 4), style="andante",
               anac: float | None = None, final_at: float | None = None, end_rest: float = 0.5,
               model=None, rests=True, rng=None):
    """Onsets and durations for each syllable, or None if the line cannot fit."""
    num, den = meter
    n = len(syls)
    if n == 0:
        return []
    f = last_stress(syls)
    D = [d for d in DURS.get(style, DURS["andante"])]
    if anac is None:
        anac = {4.0: 1.5, 3.0: 1.0, 2.0: 1.0}.get(bar_len, 1.0) if den == 4 else 1.0
    if final_at is None:
        final_at = (bars - 1) * bar_len
    total = bars * bar_len
    Pf = int(round(final_at / U))
    P_lo = -int(round(anac / U))
    E_hi = int(round((total - end_rest) / U))
    E_lo = E_hi - int(round(max(1.5, bar_len) / U))
    model_on = {}
    if model:
        for b, d in model:
            model_on[int(round(b / U))] = d
    post = set(range(f + 1, n))

    def place(i, p, d):
        b = p * U
        w = weight(b, bar_len, num, den)
        s = syls[i].stress
        c = 0.0
        if s == 2:
            c += (4.0 - w) * 1.4
            if d < 0.5:
                c += 1.2
            c -= 0.25 * min(d, 2.0)
        elif s == 1:
            c += abs(w - 2.0) * 0.3
        else:
            c += max(0.0, w - 2.0) * 1.1
            if i not in post and d > 1.0:
                c += (d - 1.0) * 1.2
        # syncopation: a weak start held across a stronger position
        k = p + 1
        endp = p + int(round(d / U))
        while k < endp:
            if weight(k * U, bar_len, num, den) > w + 1.0 and weight(k * U, bar_len, num, den) >= 3.0:
                c += 1.0
                break
            k += 1
        c += DUR_PREF.get(style, {}).get(d, 0.0)
        if model_on:
            md = model_on.get(p)
            if md is None:
                c += 0.9
            else:
                c += 0.4 * abs(d - md) / 0.5
        return c

    INF = 1e18
    # states: (p, dprev) -> (cost, back)
    layer = {}
    first_end = Pf if f == 0 else Pf - 1
    for p in range(P_lo, first_end + 1):
        if f == 0 and p != Pf:
            continue
        layer[(p, None)] = (0.15 * max(0, -p) * U + 0.6 * max(0, p) * U, None)
    back = [layer]
    for i in range(n):
        nxt = {}
        Di = D if i < n - 1 else sorted(set(D + [2.0, 3.0, bar_len]))
        if i == n - 1:
            # a final syllable may be held: anything in half-beats up to two bars
            Di = sorted(set(D + [k * 0.5 for k in range(2, int(bar_len * 4) + 1)]))
        for (p, dprev), (cost, _) in back[-1].items():
            for d in Di:
                dp = int(round(d / U))
                pc = place(i, p, d)
                if dprev is not None and syls[i].stress < 2 and (i == 0 or syls[i - 1].stress < 2):
                    if abs(d - dprev) > 1e-9:
                        pc += 0.35
                if dprev is not None and abs(dprev - 0.75) < 1e-9:
                    pc += -0.2 if abs(d - 0.25) < 1e-9 else 0.5
                gaps = [0]
                if rests and syls[i].pause and i < n - 1:
                    gaps = [0, int(round(0.5 / U))] + ([int(round(1.0 / U))] if any(ch in ".!?" for ch in syls[i].pause) else [])
                for g in gaps:
                    p2 = p + dp + g
                    c2 = cost + pc + (0.0 if g == 0 else (0.1 if syls[i].pause else 1.0))
                    if i == n - 1:
                        if not (E_lo <= p + dp <= E_hi):
                            continue
                        c2 += 0.25 * (E_hi - (p + dp)) * U
                        key = ("end", d)
                    else:
                        if i + 1 == f and p2 != Pf:
                            continue
                        if i + 1 < f and p2 >= Pf:
                            continue
                        if p2 > E_hi:
                            continue
                        key = (p2, d)
                    if c2 < nxt.get(key, (INF, None))[0]:
                        nxt[key] = (c2, (p, dprev, d))
        if not nxt:
            return None
        back.append(nxt)
    # trace back
    best_key = min(back[-1], key=lambda k: back[-1][k][0])
    out = []
    key = best_key
    for i in range(n, 0, -1):
        cost, (p, dprev, d) = back[i][key]
        out.append((p * U, d))
        key = (p, dprev)
    out.reverse()
    return out


def fit_rhythm(syls, bar_len, meter, style="andante", bars=None, **kw):
    """set_rhythm with automatic relaxation: more bars, finer values, smaller end rest."""
    n = len(syls)
    if bars is None:
        per_bar = {4.0: 6, 3.0: 5, 2.0: 3, 6.0: 9}.get(bar_len, 5)
        bars = max(1, math.ceil(n / per_bar))
    tries = [(bars, style, kw.get("end_rest", 0.5)), (bars, "allegro", 0.5), (bars + 1, style, 0.5),
             (bars + 1, "allegro", 0.25), (bars + 2, "parlante", 0.25)]
    for b, st, er in tries:
        k2 = dict(kw)
        k2["end_rest"] = er
        if "final_at" in kw and kw["final_at"] is not None and b != bars:
            k2["final_at"] = kw["final_at"] + (b - bars) * bar_len
        r = set_rhythm(syls, b, bar_len, meter, st, **k2)
        if r:
            return r, b
    raise ValueError(f"cannot fit {n} syllables in {bars} bars of {bar_len}: {' '.join(s.text for s in syls)}")


# ============================================================================================ pitch
def _contour(kind):
    return {
        "arch": [(0.0, 0.35), (0.55, 0.85), (0.85, 0.6), (1.0, 0.25)],
        "rise": [(0.0, 0.3), (0.8, 0.85), (1.0, 0.75)],
        "fall": [(0.0, 0.75), (0.4, 0.6), (1.0, 0.2)],
        "open": [(0.0, 0.35), (0.6, 0.75), (1.0, 0.55)],
        "high": [(0.0, 0.5), (0.5, 1.0), (0.8, 0.8), (1.0, 0.35)],
        "low": [(0.0, 0.3), (0.5, 0.45), (1.0, 0.15)],
        "flat": [(0.0, 0.45), (1.0, 0.4)],
        "speech": [(0.0, 0.55), (0.25, 0.65), (0.7, 0.45), (1.0, 0.3)],
        "wave": [(0.0, 0.4), (0.3, 0.65), (0.6, 0.4), (0.85, 0.7), (1.0, 0.3)],
    }.get(kind, kind) if isinstance(kind, str) else kind


def _interp(pts, t):
    t = min(1.0, max(0.0, t))
    for (t0, h0), (t1, h1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            return h0 + (h1 - h0) * (t - t0) / max(1e-9, t1 - t0)
    return pts[-1][1]


def set_pitches(rhythm, syls, key: Key, chord_at, lo: int, hi: int, tess=None, contour="arch",
                cadence="full", start=None, model=None, avoid=frozenset(), style="andante", beam=28,
                peak_ok=True, rng=None):
    """Choose a pitch for each (beat, dur) in rhythm. chord_at(beat) -> Chord or None."""
    rng = rng or random.Random(0)
    n = len(rhythm)
    if n == 0:
        return []
    tess = tess or (lo + 3, hi - 3)
    pts = _contour(contour)
    b0 = rhythm[0][0]
    b1 = rhythm[-1][0] + rhythm[-1][1]
    fs = last_stress(syls) if syls else n - 1
    recit = style in ("parlante", "chant")
    targets = []
    for b, d in rhythm:
        h = _interp(pts, (b - b0) / max(1e-6, b1 - b0))
        targets.append(tess[0] + h * (tess[1] - tess[0]))
    if recit and syls:
        for i, sy in enumerate(syls[:n]):
            if sy.stress == 2:
                targets[i] += 2.5                         # declamation lifts the stressed syllables
    if model:
        for i, m in enumerate(model):
            if m is not None:
                targets[i] = m
    cands = []
    chords = []
    for i, (b, d) in enumerate(rhythm):
        ch = chord_at(b + 1e-4)
        chords.append(ch)
        pcs = key.pcs_for(ch)
        cs = [m for m in range(lo, hi + 1) if m % 12 in pcs and m % 12 not in avoid]
        cands.append(cs or [m for m in range(lo, hi + 1) if m % 12 not in avoid])
    tonic = key.tonic
    deg2 = key.degree_pc(2)
    deg5 = key.degree_pc(5)
    deg7 = key.leading() if key.minor else key.degree_pc(7)
    third = key.degree_pc(3)

    def note_cost(i, m, prev, prev2, prev_nct, reps):
        b, d = rhythm[i]
        ch = chords[i]
        s = syls[i].stress if i < len(syls) else 0
        c = 0.0
        in_ch = ch is None or (m % 12) in ch.pcs
        strong = s == 2 or d >= 1.0 or (b % 1.0) < 1e-6 and d >= 0.75
        nct = not in_ch
        if nct:
            if i == fs and style in ("cantabile", "andante", "chorus") and i + 1 < n:
                c += 0.6                                  # the appoggiatura on the last stress
            elif strong:
                c += 3.2
            else:
                c += 0.5
        if prev is not None:
            iv = m - prev
            a = abs(iv)
            c += {0: (0.4 if recit else 0.7), 1: 0.0, 2: 0.0, 3: 0.35, 4: 0.45, 5: 0.7, 7: 1.0, 8: 1.7,
                  9: 1.8, 12: 2.2}.get(a, 4.0 if a in (6, 10, 11) else 6.0)
            if prev_nct and a > 2:
                c += 3.0                                  # a non-chord tone must resolve by step
            if nct and a > 2 and not (i == fs):
                c += 1.5                                  # and be approached by step
            if prev2 is not None:
                iv0 = prev - prev2
                if abs(iv0) >= 5 and iv * iv0 > 0:
                    c += 2.0                              # two leaps the same way
                if abs(iv0) >= 5 and iv * iv0 < 0 and a <= 2:
                    c -= 0.5                              # a leap recovered by step
                if (prev2 % 12) == deg7 and (prev % 12) != tonic and key.minor:
                    c += 0.5
            if (prev % 12) == deg7 and (m % 12) != tonic and a > 2:
                c += 0.8                                  # the leading note wants the tonic
            if reps >= 2 and iv == 0 and not recit:
                c += 1.5
        chroma = (m % 12) not in key.scale and not (key.minor and (m % 12) == key.leading())
        if chroma:
            c += 0.6
            if prev is not None and (prev % 12) not in key.scale and abs(m - prev) <= 2:
                c += 1.6                                  # no chromatic-to-chromatic steps (Db-B)
        c += 0.13 * abs(m - targets[i]) * (2.5 if model and model[i] is not None else 1.0)
        if m > tess[1]:
            c += (m - tess[1]) * (0.25 if peak_ok else 0.8)
        if m < tess[0]:
            c += (tess[0] - m) * 0.5
        # cadence
        if i == n - 1:
            pc = m % 12
            if cadence == "full":
                c += 0.0 if pc == tonic else (1.2 if pc == third else 4.0)
            elif cadence == "half":
                c += 0.0 if pc in (deg2, deg5, deg7) else 2.5
            elif cadence == "question":
                if prev is not None and m <= prev:
                    c += 2.0
            if prev is not None and abs(m - prev) > 5 and cadence in ("full", "half"):
                c += 1.5
        return c, nct

    # beam: (cost, pitches, nct_last, reps)
    beams = [(0.0, [], False, 0)]
    for i in range(n):
        new = {}
        for cost, ps, pn, reps in beams:
            prev = ps[-1] if ps else start
            prev2 = ps[-2] if len(ps) >= 2 else None
            for m in cands[i]:
                if prev is not None and abs(m - prev) > 12:
                    continue
                c, nct = note_cost(i, m, prev, prev2, pn, reps)
                r = reps + 1 if (prev is not None and m == prev) else 0
                key2 = (ps[-1] if ps else None, m, nct)
                tot = cost + c + rng.random() * 0.05
                if key2 not in new or new[key2][0] > tot:
                    new[key2] = (tot, ps + [m], nct, r)
        beams = sorted(new.values(), key=lambda x: x[0])[:beam]
    return beams[0][1]


# ============================================================================================ phrases
def make_events(rhythm, pitches, syls, vel=0.58, art_long="", origin=0.0):
    evs = []
    for (b, d), m, s in zip(rhythm, pitches, syls):
        e = Ev(origin + b, d, m, vel, "", s.text)
        evs.append(e)
    return evs


def ornament(evs, key: Key, chord_at, style, rng, fs=None):
    """Light bel canto ornaments: an appoggiatura or turn on a long note at the last stress."""
    if style not in ("cantabile", "andante") or len(evs) < 3:
        return evs
    if fs is None:
        fs = len(evs) - 2
    out = []
    for k, e in enumerate(evs):
        if k == fs and e.dur >= 1.5 and rng.random() < 0.55:
            ch = chord_at(e.beat + 1e-4)
            up = next((m for m in range(int(e.midi) + 1, int(e.midi) + 3) if m % 12 in key.pcs_for(ch)), None)
            if up is None:
                out.append(e)
                continue
            if rng.random() < 0.5:
                # a turn: up, main, down, main (quavers), then the remainder
                down = next((m for m in range(int(e.midi) - 1, int(e.midi) - 3, -1) if m % 12 in key.pcs_for(ch)),
                            int(e.midi) - 1)
                seq = [(e.midi, 0.5), (up, 0.25), (e.midi, 0.25), (down, 0.25), (e.midi, e.dur - 1.25)]
            else:
                seq = [(up, min(1.0, e.dur / 2)), (e.midi, e.dur - min(1.0, e.dur / 2))]
            t = e.beat
            for j, (m, d) in enumerate(seq):
                if d <= 0:
                    continue
                out.append(Ev(t, d, m, e.vel, e.art if j == 0 else "", e.lyric if j == 0 else "_",
                              None, dict(e.tags)))
                t += d
        else:
            out.append(e)
    return out


def retext(model_evs, model_syls: list[Syl], syls: list[Syl], key: Key, chord_at, lo, hi,
           bar_len, meter, downbeat0: float, cadence=None, style="andante", contour="arch",
           avoid=frozenset(), rng=None, origin: float = 0.0):
    """Sing new words to a model phrase. model_evs are relative to the model's first note, which lies
    `downbeat0` beats before the model's first downbeat. Returns events relative to origin (= the new
    phrase's first downbeat) and the phrase length in bars."""
    rng = rng or random.Random(0)
    # the model's syllables (melisma notes fold into their syllable)
    starts = []
    for e in model_evs:
        if e.lyric == "_" and starts:
            starts[-1][1] = e.beat + e.dur - starts[-1][0]
        else:
            starts.append([e.beat, e.dur, e.midi])
    rel = [(b - downbeat0, d, m) for b, d, m in starts]
    # a model from another voice: carry it by octaves to this singer's register
    avg = sum(m for b, d, m in rel) / len(rel)
    k8 = round(((lo + hi) / 2.0 - avg) / 12.0)
    if k8:
        rel = [(b, d, m + 12 * k8) for b, d, m in rel]
    end = max(b + d for b, d, m in rel)
    bars = max(1, math.ceil((end - 1e-6) / bar_len))
    mf = last_stress(model_syls) if len(model_syls) == len(rel) else None
    final_at = rel[mf][0] if mf is not None and 0 <= mf < len(rel) else (bars - 1) * bar_len
    final_at = max(0.0, final_at)
    same = len(syls) == len(rel) and [s.stress == 2 for s in syls] == [s.stress == 2 for s in model_syls]
    if same and contour == "high":
        same = False                        # a climax is a variant, not a copy
    if same:
        rhythm = [(b, d) for b, d, m in rel]
        pitches = [int(round(m)) for b, d, m in rel]
        # another voice may sing this tune: move it by octaves into the singer's range
        mid = (lo + hi) / 2.0
        avg = sum(pitches) / len(pitches)
        k = round((mid - avg) / 12.0)
        pitches = [m + 12 * k for m in pitches]
        pitches = [m + 12 if m < lo else m - 12 if m > hi else m for m in pitches]
        if any(m < lo or m > hi for m in pitches):
            same = False
    if same:
        if cadence and cadence != "keep":
            # re-cadence the last notes only
            tail = max(2, len(rel) - last_stress(syls))
            head = pitches[:-tail]
            new_tail = set_pitches([(origin + b, d) for b, d in rhythm[-tail:]], syls[-tail:], key,
                                   chord_at, lo, hi, model=[m for m in pitches[-tail:]], cadence=cadence,
                                   start=head[-1] if head else None, style=style, avoid=avoid, rng=rng)
            pitches = head + new_tail
    else:
        model_rh = [(b, d) for b, d, m in rel]
        try:
            rhythm, bars = fit_rhythm(syls, bar_len, meter, style, bars=bars, final_at=final_at, model=model_rh,
                                      anac=max(0.5, -min(0.0, rel[0][0])) if rel[0][0] < 0 else None)
        except ValueError:
            # the model's shape cannot carry these words: compose over the same harmony instead
            return phrase(syls, key, chord_at, lo, hi, bar_len, meter, origin=origin, bars=bars, style=style,
                          contour=contour, cadence=cadence or "full", avoid=avoid, rng=rng, orn=False)
        tgt = []
        span = max(1e-6, rhythm[-1][0] - rhythm[0][0])
        for b, d in rhythm:
            m = None
            for rb, rd, rm in rel:
                if rb - 1e-6 <= b < rb + rd - 1e-6:
                    m = rm
            if m is None:
                m = min(rel, key=lambda x: abs(x[0] - b))[2]
            if contour == "high":
                x = (b - rhythm[0][0]) / span
                m += 4.0 * math.sin(math.pi * min(1.0, x / 0.85)) if x < 0.85 else 0.0
            tgt.append(int(round(m)))
        pitches = set_pitches([(origin + b, d) for b, d in rhythm], syls, key, chord_at, lo, hi,
                              model=tgt, cadence=cadence or "full", style=style, contour=contour,
                              avoid=avoid, rng=rng)
    evs = [Ev(origin + b, d, m, 0.58, "", s.text) for (b, d), m, s in zip(rhythm, pitches, syls)]
    return evs, bars


def phrase(syls: list[Syl], key: Key, chord_at, lo, hi, bar_len, meter, origin=0.0, bars=None,
           style="andante", contour="arch", cadence="full", start=None, tess=None, final_at=None,
           avoid=frozenset(), rng=None, orn=True, end_rest=0.5):
    """A newly composed phrase for one verse line (or two short lines joined)."""
    rng = rng or random.Random(0)
    rhythm, bars = fit_rhythm(syls, bar_len, meter, style, bars=bars, final_at=final_at, end_rest=end_rest)
    pitches = set_pitches([(origin + b, d) for b, d in rhythm], syls, key, chord_at, lo, hi, tess=tess,
                          contour=contour, cadence=cadence, start=start, style=style, avoid=avoid, rng=rng)
    evs = [Ev(origin + b, d, m, 0.58, "", s.text) for (b, d), m, s in zip(rhythm, pitches, syls)]
    if orn:
        evs = ornament(evs, key, chord_at, style, rng, fs=last_stress(syls))
    return evs, bars


# ============================================================================================ recitative
def recit(syls: list[Syl], key: Key, chord_at, lo, hi, origin=0.0, base=0.5, start=None,
          avoid=frozenset(), rng=None, tess=None):
    """Recitative for one line: speech rhythm, a reciting tone on the chord, falling feminine cadence
    at sentence ends, rising at questions. Returns (events, length in beats)."""
    rng = rng or random.Random(0)
    n = len(syls)
    if n == 0:
        return [], 0.0
    rh = []
    t = 0.0
    fs = last_stress(syls)
    for i, s in enumerate(syls):
        d = base
        if s.stress == 2:
            d = base * (1.5 if rng.random() < 0.6 else 1.0)
        if i == fs:
            d = max(d, base * 2)
        if i > fs:
            d = base * (2 if i == n - 1 else 1)
        if s.pause and i < n - 1 and any(c in ",;:" for c in s.pause):
            d = max(d, base * 1.5)
        rh.append((t, d))
        t += d
        if s.pause and i < n - 1:
            t += base if any(c in ".!?…" for c in s.pause) else base * 0.5
    length = t
    q = syls[-1].pause and "?" in syls[-1].pause
    excl = any("!" in (s.pause or "") for s in syls)
    tess = tess or (lo + 4, hi - 5)
    pitches = set_pitches([(origin + b, d) for b, d in rh], syls, key, chord_at, lo, hi, tess=tess,
                          contour="rise" if q else ("high" if excl else "speech"), cadence="question" if q else "none",
                          start=start, style="parlante", avoid=avoid, rng=rng)
    # the feminine cadence: last stress a step above the final note
    if not q and fs < n - 1 and n >= 3:
        fin = pitches[-1]
        ch = chord_at(origin + rh[-1][0] + 1e-4)
        if ch is not None and fin % 12 not in ch.pcs:
            near = sorted((m for m in range(fin - 4, fin + 5) if m % 12 in ch.pcs and m % 12 not in avoid),
                          key=lambda m: abs(m - fin))
            if near:
                fin = near[0]
                pitches[-1] = fin
        up = next((m for m in range(fin + 1, fin + 3) if m % 12 in key.pcs_for(ch) and m % 12 not in avoid), None)
        if up is not None and lo <= up <= hi:
            pitches[fs] = up
    evs = [Ev(origin + b, d, m, 0.55, "", s.text, None, {"style": "parlato"}) for (b, d), m, s in zip(rh, pitches, syls)]
    return evs, length
