"""A compact melody notation so the score can be written by hand, bar by bar.

Tokens (whitespace separated):
    F#4:1        note, duration in crotchet beats (1 = crotchet, .5 = quaver, 1.5 = dotted crotchet)
    Bb3:1/3      fractional durations for tuplets
    r:2          rest
    A4:1~        tie into the next note of the same pitch
    (Eb4)D4:1.5  grace note (appoggiatura) stolen from the start of the main note
    A4:1>        accent      A4:1'  staccato      A4:1-  tenuto      A4:1^  marcato
    !p !mf !ff   dynamic for following notes (pp p mp mf f ff fff sfz)
    |            barline (checked against the bar length if given)

Lyrics: syllables separated by spaces, one per sounding note after ties merge.
    '_' alone continues the previous syllable over a melisma.
    'ne_a' (underscore inside a syllable) marks synalepha: two vowels on one note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from .theory import pitch

DYN = {"ppp": 0.12, "pp": 0.2, "p": 0.32, "mp": 0.45, "mf": 0.58, "f": 0.72,
       "ff": 0.86, "fff": 0.97, "sfz": 0.95}


@dataclass
class Ev:
    beat: float          # start, in crotchet beats relative to the phrase origin
    dur: float           # duration in crotchet beats
    midi: float          # MIDI pitch (float allows microtonal inflection)
    vel: float = 0.58    # 0..1
    art: str = ""        # '>' accent, "'" staccato, '-' tenuto, '^' marcato
    lyric: str | None = None
    grace: float | None = None   # MIDI pitch of a grace note, if any
    tags: dict = field(default_factory=dict)

    @property
    def end(self):
        return self.beat + self.dur


def _dur(s: str) -> float:
    return float(Fraction(s)) if "/" in s else float(s)


def parse(text: str, bar: float | None = None, vel: float = 0.58, origin: float = 0.0,
          transpose: int = 0, check: bool = True) -> list[Ev]:
    """Parse melody text into events. bar: expected bar length in crotchets for checking."""
    evs: list[Ev] = []
    t = origin
    bar_start = origin
    tie_pending = False
    for tok in text.split():
        if tok == "|":
            if bar is not None and check:
                got = t - bar_start
                if abs(got - bar) > 1e-6:
                    raise ValueError(f"bar length {got} != {bar} near beat {t} in: {text[:80]}...")
            bar_start = t
            continue
        if tok.startswith("!"):
            vel = DYN[tok[1:]]
            continue
        grace = None
        if tok.startswith("("):
            g, tok = tok[1:].split(")", 1)
            grace = pitch(g) + transpose
        art = ""
        while tok and tok[-1] in ">'-^":
            art = tok[-1] + art
            tok = tok[:-1]
        tie = tok.endswith("~")
        if tie:
            tok = tok[:-1]
        p, d = tok.split(":")
        d = _dur(d)
        if p == "r":
            t += d
            tie_pending = False
            continue
        m = pitch(p) + transpose
        if tie_pending and evs and abs(evs[-1].midi - m) < 1e-9:
            evs[-1].dur += d
        else:
            evs.append(Ev(t, d, m, vel, art, None, grace))
        tie_pending = tie
        t += d
    if bar is not None and check and t - bar_start > 1e-6 and abs((t - bar_start) - bar) > 1e-6:
        raise ValueError(f"final bar length {t - bar_start} != {bar} in: {text[:80]}...")
    return evs


def length(text: str) -> float:
    """Total duration of a melody string in crotchets."""
    total = 0.0
    for tok in text.split():
        if tok == "|" or tok.startswith("!"):
            continue
        if tok.startswith("("):
            tok = tok.split(")", 1)[1]
        tok = tok.rstrip(">'-^~")
        total += _dur(tok.split(":")[1])
    return total


def attach_lyrics(evs: list[Ev], lyrics: str) -> list[Ev]:
    """Attach syllables to events. '_' extends the previous syllable (melisma)."""
    syls = lyrics.split()
    if len(syls) != len(evs):
        raise ValueError(f"{len(syls)} syllables for {len(evs)} notes: {lyrics!r}")
    last = None
    for ev, s in zip(evs, syls):
        if s == "_":
            ev.lyric = "_"
            ev.tags["melisma_of"] = last
        else:
            ev.lyric = s
            last = s
    return evs


def shift(evs: list[Ev], beats: float) -> list[Ev]:
    for e in evs:
        e.beat += beats
    return evs


def scale_time(evs: list[Ev], factor: float, origin: float = 0.0) -> list[Ev]:
    """Augment (factor > 1) or diminish rhythm around an origin."""
    for e in evs:
        e.beat = origin + (e.beat - origin) * factor
        e.dur *= factor
    return evs
