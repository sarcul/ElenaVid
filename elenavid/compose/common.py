"""Shared helpers for the section composers."""
from __future__ import annotations

from ..notation import Ev, parse, attach_lyrics, length
from ..score_model import Section, TempoMap

# (key, title, start, length) -- the film's running order, exactly 600 s
PLAN = [
    ("s00", "Prologo: il teatro", 0.0, 26.0),
    ("s01", "Atto I, scena 1: la piazza, Veneto, estate 1948", 26.0, 34.0),
    ("s02", "Atto I, scena 2: il salotto, la chiesa, primavera 1950", 60.0, 62.0),
    ("s03", "Atto I, scena 3: la casa di Verona, autunno 1953", 122.0, 40.0),
    ("s04", "Atto II, scena 1: la stazione, notte", 162.0, 22.0),
    ("s05", "Atto II, scena 2: Trieste, 1955", 184.0, 62.0),
    ("s06", "Atto II, scena 3: una strada di Trieste, 1957", 246.0, 30.0),
    ("s07", "Atto III, scena 1: mesi; la visione; Stabat Mater", 276.0, 88.0),
    ("s08", "Atto III, scena 2: la trattoria; il figlio", 364.0, 44.0),
    ("s09", "Atto III, scena 3: Requiem", 408.0, 22.0),
    ("s10", "Atto III, scena 3: la lettera", 430.0, 46.0),
    ("s11", "Atto III, scena 3: scena ed aria finale", 476.0, 124.0),
]
assert abs(sum(p[3] for p in PLAN) - 600.0) < 1e-9

NO_A = {9}   # after Tommaso's funeral the score never again sounds the pitch class A


def section(key, tempo, meters):
    k, title, start, ln = next(p for p in PLAN if p[0] == key)
    return Section(k, title, start, ln, TempoMap(tempo), meters=meters)


def sing(sec, inst, voice, mel, lyr, it, en, origin, vel=None, style="aria", pos="low",
         bar=None, show=True, transpose=0, **tags):
    evs = parse(mel, bar=bar, origin=origin, vel=vel if vel is not None else 0.58,
                transpose=transpose)
    attach_lyrics(evs, lyr)
    for e in evs:
        e.tags.update(tags)
        e.tags.setdefault("style", style)
    sec.add(inst, evs, voice=voice)
    if show:
        sec.line(voice, evs, it, en, style=style, pos=pos)
    return evs


def P(text, origin=0.0, vel=0.5, bar=None, transpose=0):
    return parse(text, bar=bar, origin=origin, vel=vel, transpose=transpose)


def add_lines(sec, inst, lines, vel=None, **tags):
    for evs in lines:
        if evs:
            if vel is not None:
                for e in evs:
                    e.vel = vel
            sec.add(inst, evs, **tags)


def tone(sec, start, dur, vel=0.3, inst="vc_harm", voice="tommaso_tone", **tags):
    """Tommaso's tone: A4, as a cello harmonic (or cor anglais / treble when inst says so)."""
    ev = Ev(start, dur, 69, vel, "", None, None, {"tommaso": True, **tags})
    sec.add(inst, [ev], voice=voice)
    return ev
