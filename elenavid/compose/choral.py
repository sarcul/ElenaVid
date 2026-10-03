"""Homophonic choral harmonisation: alto, tenor, bass beneath a given soprano line."""
from __future__ import annotations

from ..notation import Ev
from ..theory import pcs_in_range


def chord_at(p, beat):
    cur = None
    for b, d, c in p:
        if b <= beat + 1e-6 and c is not None:
            cur = c
        if b > beat + 1e-6:
            break
    return cur


def harmonize(mel, p, a_rng=(53, 74), t_rng=(48, 67), b_rng=(40, 60), avoid_pcs=None):
    A, T, B = [], [], []
    pa = pt = pb = None
    for e in mel:
        ch = chord_at(p, e.beat)
        if ch is None:
            continue
        pcs = [x for x in ch.pcs if not avoid_pcs or x not in avoid_pcs]
        s = int(round(e.midi))
        # bass: chord bass (or root) nearest previous
        bc = pcs_in_range({ch.bass}, *b_rng) or pcs_in_range(set(pcs), *b_rng)
        b = bc[len(bc) // 2] if pb is None else min(bc, key=lambda m: (abs(m - pb), m))
        # alto: a chord tone 3..9 semitones below the soprano, close to the previous alto
        ac = [m for m in pcs_in_range(set(pcs), *a_rng) if 2 <= s - m <= 9]
        if not ac:
            ac = [m for m in pcs_in_range(set(pcs), *a_rng) if m < s] or [s - 3]
        if pa is None:
            a = max(ac)
        else:
            a = min(ac, key=lambda m: (abs(m - pa) + (0 if m % 12 != s % 12 else 3), -m))
        # tenor: a chord tone between bass+3 and alto-2, preferring a pitch class not yet used
        used = {s % 12, a % 12, b % 12}
        tc = [m for m in pcs_in_range(set(pcs), *t_rng) if b + 3 <= m <= a - 2]
        if not tc:
            tc = [m for m in pcs_in_range(set(pcs), *t_rng) if m <= a - 1] or [a - 5]

        def tcost(m):
            c = 0 if m % 12 not in used else 4
            if pt is not None:
                c += abs(m - pt) * 0.6
            return c
        t = min(tc, key=tcost)
        for lst, m in ((A, a), (T, t), (B, b)):
            lst.append(Ev(e.beat, e.dur, m, e.vel * 0.92, e.art, e.lyric, None, dict(e.tags)))
        pa, pt, pb = a, t, b
    return A, T, B
