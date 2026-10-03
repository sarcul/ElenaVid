"""The film's hand-set music as material for the full opera.

Two services:
  tune(text)    the film's melody for one verse line (rhythm in beats, pitches, lyric syllables,
                metre, tempo) with the harmony the film's orchestra sounded beneath it
  island(...)   a whole passage of the film score (every part, lyrics, tempo and metre) lifted out so
                it can be placed verbatim inside a full-length number
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from functools import lru_cache

from ..notation import Ev
from ..theory import QUALITIES

VOCAL = {"sop", "mez", "ten", "bar", "bbar", "treble", "ch_s", "ch_a", "ch_t", "ch_b"}
_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
_QUALS = ["", "m", "7", "m7", "maj7", "dim", "dim7", "m7b5", "sus4", "aug"]


def norm(s: str) -> str:
    """Letters only, lower case, accents removed: the key for matching texts."""
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z]", "", "".join(c for c in s if not unicodedata.combining(c)))


@dataclass
class Tune:
    section: str
    voice: str
    inst: str
    text: str
    notes: list            # [Ev] with beats relative to the first note
    bar_len: float         # crotchets per bar where the line starts
    phase: float           # beat of the first note within its bar
    bpm: float
    style: str
    chords: list = field(default_factory=list)   # [(beat_rel, dur, symbol)]

    @property
    def length(self):
        return max(e.end for e in self.notes) if self.notes else 0.0


@lru_cache(maxsize=1)
def film_score():
    from ..compose.build_score import build
    return build()


def _analyse(sec, b0, b1, step=1.0):
    """Chord symbols for [b0, b1) of a film section from its sounding orchestra."""
    parts = [(inst, evs) for inst, voice, evs, tags in sec.parts if inst not in VOCAL]
    out = []
    b = b0
    prev = None
    while b < b1 - 1e-6:
        w = [0.0] * 12
        low = None
        for inst, evs in parts:
            for e in evs:
                ov = min(e.end, b + step) - max(e.beat, b)
                if ov <= 0:
                    continue
                pc = int(round(e.midi)) % 12
                wt = ov * (0.4 + e.vel)
                w[pc] += wt
                if low is None or e.midi < low[0]:
                    low = (e.midi, pc)
        if sum(w) < 0.05:
            sym = prev
        else:
            best = None
            for root in range(12):
                for q in _QUALS:
                    pcs = {(root + i) % 12 for i in QUALITIES[q]}
                    sc = sum(w[p] for p in pcs) - 0.7 * sum(w[p] for p in range(12) if p not in pcs)
                    sc -= 0.08 * len(pcs)
                    if low and low[1] == root:
                        sc += 0.35 * max(w)
                    if best is None or sc > best[0]:
                        best = (sc, root, q, pcs)
            _, root, q, pcs = best
            sym = _NAMES[root] + q
            if low and low[1] != root and low[1] in pcs:
                sym += "/" + _NAMES[low[1]]
        if sym:
            if out and out[-1][2] == sym:
                out[-1] = (out[-1][0], out[-1][1] + step, sym)
            else:
                out.append((b, step, sym))
        prev = sym
        b += step
    return out


@lru_cache(maxsize=1)
def _film_lines():
    sc = film_score()
    rows = []
    for sec in sc.sections:
        for ll, evs in sec.lines:
            sung = [e for e in evs if e.lyric is not None]
            if not sung:
                continue
            inst = next((i for i, v, es, t in sec.parts if es is evs), "sop")
            rows.append((sec, ll, sung, inst))
    return rows


def _letters_with_index(evs):
    s, idx = [], []
    for k, e in enumerate(evs):
        if e.lyric in (None, "_"):
            continue
        for c in norm(e.lyric):
            s.append(c)
            idx.append(k)
    return "".join(s), idx


@lru_cache(maxsize=None)
def tune(text: str, voice: str | None = None) -> Tune | None:
    """The film's setting of one verse line, if the film set it."""
    key = norm(text)
    if len(key) < 3:
        return None
    for sec, ll, sung, inst in _film_lines():
        if voice and ll.voice not in (voice, voice.split("+")[0]):
            continue
        letters, idx = _letters_with_index(sung)
        pos = letters.find(key)
        if pos < 0:
            continue
        k0 = idx[pos]
        k1 = idx[pos + len(key) - 1]
        while k1 + 1 < len(sung) and sung[k1 + 1].lyric == "_":
            k1 += 1                      # keep the melisma that finishes the last syllable
        part = [copy.deepcopy(e) for e in sung[k0:k1 + 1]]
        origin = part[0].beat
        for e in part:
            e.beat -= origin
        bl = sec.bar_len(origin)
        bar0 = 0.0
        for b0, blen, _ in sec.bars():
            if b0 <= origin + 1e-6:
                bar0 = b0
        t = Tune(sec.key, ll.voice, inst, text, part, bl, origin - bar0, sec.tempo.bpm(origin), ll.style)
        end = origin + t.length
        t.chords = [(b - origin, d, s) for b, d, s in _analyse(sec, origin, end, step=0.5)]
        return t
    return None


@dataclass
class Island:
    parts: list            # [(inst, voice, [Ev], tags)] beats relative to the island start
    lines: list            # [(Lyricline, [Ev])]
    tempo: list            # [(beat, bpm[, 'ramp'])] relative
    meters: list           # [(beat, num, den)] relative
    length: float          # in beats
    cues: dict = field(default_factory=dict)


def island(section_key: str, b0: float, b1: float, keep_vocals=True) -> Island:
    """Lift beats [b0, b1) of a film section, every part, as a block for the full score."""
    sc = film_score()
    sec = next(s for s in sc.sections if s.key == section_key)
    parts = []
    for inst, voice, evs, tags in sec.parts:
        if not keep_vocals and inst in VOCAL:
            continue
        sel = []
        for e in evs:
            if b0 - 1e-6 <= e.beat < b1 - 1e-6:
                c = copy.deepcopy(e)
                c.beat -= b0
                c.dur = min(c.dur, b1 - e.beat + 4.0)
                sel.append(c)
        if sel:
            parts.append((inst, voice, sel, dict(tags)))
    lines = []
    for ll, evs in sec.lines:
        sung = [e for e in evs if e.lyric is not None and b0 - 1e-6 <= e.beat < b1 - 1e-6]
        if sung and len(sung) == len([e for e in evs if e.lyric is not None]):
            # find the copied events (same objects were deep-copied above): re-copy with offset
            cp = []
            for e in sung:
                c = copy.deepcopy(e)
                c.beat -= b0
                cp.append(c)
            lines.append((copy.copy(ll), cp))
    tempo = []
    for s in sec.tempo.segs:
        b, bpm, ramp = s
        if b < b1 and (b >= b0 or not tempo):
            tempo.append((max(0.0, b - b0), bpm, "ramp") if ramp else (max(0.0, b - b0), bpm))
    if not tempo or tempo[0][0] > 0:
        tempo.insert(0, (0.0, sec.tempo.bpm(b0)))
    meters = []
    for m in sec.meters:
        if m[0] < b1:
            meters.append((max(0.0, m[0] - b0), m[1], m[2]))
    meters = [m for i, m in enumerate(meters) if i == len(meters) - 1 or meters[i + 1][0] > m[0]]
    cues = {k: v - b0 for k, v in sec.cues.items() if b0 <= v < b1}
    return Island(parts, lines, tempo, meters, b1 - b0, cues)


def section_beats(section_key: str, t0: float, t1: float):
    """Film seconds -> that section's beats (for choosing island windows)."""
    sc = film_score()
    sec = next(s for s in sc.sections if s.key == section_key)
    return sec.tempo.beat_at(t0 - sec.start), sec.tempo.beat_at(t1 - sec.start)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    from .libretto import parse, Line
    hit = miss = 0
    for n in parse():
        for x in n.items:
            if not isinstance(x, Line):
                continue
            t = tune(x.it, x.speaker if x.speaker != "coro" else "chorus")
            if t:
                hit += 1
                ch = " ".join(s for _, _, s in t.chords[:6])
                print(f"{n.key:4s} {t.section} {len(t.notes):2d} notes  {t.bpm:5.1f} bpm  bar {t.bar_len}  "
                      f"phase {t.phase:4.2f}  [{ch}]  {x.it[:44]}")
            else:
                miss += 1
    print(f"film tunes for {hit} of {hit + miss} verse lines")
