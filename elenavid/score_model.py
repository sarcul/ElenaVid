"""Sections, tempo maps and the flattened, absolute-time note list."""
from __future__ import annotations

import copy
import json
import math
import struct
from dataclasses import dataclass, field, asdict

from .notation import Ev


@dataclass
class Note:
    t: float              # absolute start, seconds
    dur: float            # seconds
    midi: float
    vel: float
    inst: str             # instrument model id
    voice: str            # performer id, e.g. 'elena', 'vn1', 'chorus_s'
    section: str
    art: str = ""
    lyric: str | None = None
    grace: float | None = None
    beat: float = 0.0     # beat within its section
    tags: dict = field(default_factory=dict)

    @property
    def end(self):
        return self.t + self.dur


class TempoMap:
    """Piecewise tempo in crotchet BPM. Segments: (beat, bpm) or (beat, bpm, 'ramp').

    A 'ramp' segment changes linearly in BPM from its bpm to the next segment's bpm.
    """

    def __init__(self, segments):
        segs = []
        for s in segments:
            if len(s) == 2:
                segs.append((float(s[0]), float(s[1]), False))
            else:
                segs.append((float(s[0]), float(s[1]), s[2] == "ramp"))
        segs.sort()
        if segs[0][0] != 0.0:
            segs.insert(0, (0.0, segs[0][1], False))
        self.segs = segs
        # cumulative time at each segment start
        self.t0 = [0.0]
        for i in range(len(segs) - 1):
            self.t0.append(self.t0[-1] + self._seg_time(i, segs[i + 1][0]))

    def _bpm_end(self, i):
        b, bpm, ramp = self.segs[i]
        if ramp and i + 1 < len(self.segs):
            return self.segs[i + 1][1]
        return bpm

    def _seg_time(self, i, beat):
        b0, bpm0, ramp = self.segs[i]
        db = beat - b0
        if not ramp or i + 1 >= len(self.segs):
            return db * 60.0 / bpm0
        b1, bpm1 = self.segs[i + 1][0], self.segs[i + 1][1]
        k = (bpm1 - bpm0) / (b1 - b0)
        if abs(k) < 1e-9:
            return db * 60.0 / bpm0
        return 60.0 / k * math.log((bpm0 + k * db) / bpm0)

    def bpm(self, beat):
        i = self._index(beat)
        b0, bpm0, ramp = self.segs[i]
        if ramp and i + 1 < len(self.segs):
            b1, bpm1 = self.segs[i + 1][0], self.segs[i + 1][1]
            return bpm0 + (bpm1 - bpm0) * (beat - b0) / (b1 - b0)
        return bpm0

    def _index(self, beat):
        i = 0
        for j, s in enumerate(self.segs):
            if s[0] <= beat + 1e-12:
                i = j
        return i

    def time(self, beat: float) -> float:
        i = self._index(beat)
        return self.t0[i] + self._seg_time(i, beat)

    def beat_at(self, t: float) -> float:
        lo, hi = 0.0, 1.0
        while self.time(hi) < t:
            hi *= 2.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if self.time(mid) < t:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)


@dataclass
class Lyricline:
    """A displayed libretto line: Italian as sung, English beneath, tied to syllable events."""
    voice: str
    it: str
    en: str
    start: float = 0.0          # absolute seconds (filled at flatten time)
    end: float = 0.0
    syllables: list = field(default_factory=list)   # [(t, dur, text)]
    style: str = "aria"          # aria | chorus | vision | latin | letter | parlato
    pos: str = "low"             # where on screen


class Section:
    def __init__(self, key: str, title: str, start: float, length: float, tempo, meter=(4, 4),
                 meters=None):
        self.key = key
        self.title = title
        self.start = start
        self.length = length
        self.tempo = tempo if isinstance(tempo, TempoMap) else TempoMap([(0, tempo)])
        # meters: list of (beat, num, den); bar length in crotchets = num * 4 / den
        self.meters = meters or [(0.0, meter[0], meter[1])]
        self.parts: list[tuple[str, str, list[Ev], dict]] = []
        self.lines: list[tuple[Lyricline, list[Ev]]] = []
        self.cues: dict[str, float] = {}       # named cue points in beats
        self.cues_abs: dict[str, float] = {}   # named cue points in absolute seconds
        self.texts: list[tuple] = []           # unsung display text: (Lyricline, beat0, beat1)

    # ----- bar arithmetic
    def bar_len(self, beat=0.0):
        num, den = self.meter_at(beat)
        return num * 4.0 / den

    def meter_at(self, beat):
        cur = self.meters[0]
        for m in self.meters:
            if m[0] <= beat + 1e-9:
                cur = m
        return cur[1], cur[2]

    def bar(self, n: int) -> float:
        """Beat at which bar n (1-based) starts."""
        beat = 0.0
        for _ in range(n - 1):
            beat += self.bar_len(beat)
        return beat

    def bars(self):
        out = []
        beat = 0.0
        end_beat = self.tempo.beat_at(self.length)
        while beat < end_beat - 1e-6:
            bl = self.bar_len(beat)
            out.append((beat, bl, self.meter_at(beat)))
            beat += bl
        return out

    def t(self, beat: float) -> float:
        """Absolute seconds of a beat in this section."""
        return self.start + self.tempo.time(beat)

    # ----- content
    def add(self, inst: str, evs: list[Ev], voice: str | None = None, **tags):
        self.parts.append((inst, voice or inst, evs, tags))
        return evs

    def line(self, voice: str, evs: list[Ev], it: str, en: str, style="aria", pos="low"):
        self.lines.append((Lyricline(voice, it, en, style=style, pos=pos), evs))

    def text(self, it: str, en: str, beat0: float, beat1: float, style="parlato", pos="low",
             voice=""):
        """Displayed but unsung words (letters, fragments, spoken asides)."""
        self.texts.append((Lyricline(voice, it, en, style=style, pos=pos), beat0, beat1))

    def cue(self, name: str, beat: float):
        self.cues[name] = beat

    def cue_abs(self, name: str, seconds_from_section_start: float):
        self.cues_abs[name] = self.start + seconds_from_section_start

    def notes(self) -> list[Note]:
        out = []
        for inst, voice, evs, tags in self.parts:
            for e in evs:
                t0 = self.t(e.beat)
                t1 = self.t(e.beat + e.dur)
                if t0 >= self.start + self.length - 1e-6:
                    continue
                t1 = min(t1, self.start + self.length + (0.0 if not tags.get("ring") else 30.0))
                n = Note(t0, t1 - t0, e.midi, e.vel, inst, voice, self.key, e.art, e.lyric,
                         e.grace, e.beat, {**tags, **e.tags})
                out.append(n)
        return out

    def flat_lines(self) -> list[Lyricline]:
        out = []
        for ll, evs in self.lines:
            ll = copy.copy(ll)
            sy = []
            for e in evs:
                if e.lyric is None:
                    continue
                t0 = self.t(e.beat)
                t1 = self.t(e.beat + e.dur)
                if e.lyric == "_" and sy:
                    sy[-1] = (sy[-1][0], t1 - sy[-1][0], sy[-1][2])
                else:
                    sy.append((t0, t1 - t0, e.lyric))
            ll.syllables = sy
            if sy:
                ll.start = sy[0][0]
                ll.end = sy[-1][0] + sy[-1][1]
            out.append(ll)
        for ll, b0, b1 in self.texts:
            ll = copy.copy(ll)
            ll.start, ll.end, ll.syllables = self.t(b0), self.t(b1), []
            out.append(ll)
        return out


class Score:
    def __init__(self):
        self.sections: list[Section] = []
        self.extra_lines: list[Lyricline] = []

    def add(self, sec: Section):
        self.sections.append(sec)
        return sec

    def notes(self) -> list[Note]:
        out = []
        for s in self.sections:
            out.extend(s.notes())
        out.sort(key=lambda n: (n.t, n.inst))
        return out

    def lines(self) -> list[Lyricline]:
        out = []
        for s in self.sections:
            out.extend(s.flat_lines())
        out.extend(self.extra_lines)
        out.sort(key=lambda l: l.start)
        return out

    def beat_grid(self):
        """Every beat and downbeat with absolute time: used by the conductor and edit points."""
        grid = []
        for s in self.sections:
            for b0, bl, (num, den) in s.bars():
                # conducting beats: in compound metres conduct the dotted crotchet
                if den == 8 and num % 3 == 0:
                    step = 1.5
                else:
                    step = 4.0 / den
                nb = int(round(bl / step))
                for k in range(nb):
                    beat = b0 + k * step
                    t = s.t(beat)
                    if t < s.start + s.length:
                        grid.append({"t": t, "section": s.key, "beat_in_bar": k, "beats_in_bar": nb,
                                     "downbeat": k == 0, "bpm": s.tempo.bpm(beat) / step})
        return grid

    def cues(self):
        out = {}
        for s in self.sections:
            for k, b in s.cues.items():
                out[f"{s.key}.{k}"] = s.t(b)
            for k, t in s.cues_abs.items():
                out[f"{s.key}.{k}"] = t
            out[f"{s.key}.start"] = s.start
            out[f"{s.key}.end"] = s.start + s.length
        return out

    # ----- MIDI export (performance timing, one track per performer)
    def write_midi(self, path, ppq=480):
        bpm = 120.0
        ticks_per_s = ppq * bpm / 60.0
        notes = self.notes()
        voices = sorted({(n.voice, n.inst) for n in notes})
        programs = {
            "strings": 48, "vn_solo": 40, "vc_solo": 42, "harm": 42, "fl": 73, "ob": 68, "eh": 69,
            "cl": 71, "bn": 70, "hn": 60, "tpt": 56, "tbn": 57, "tuba": 58, "timp": 47,
            "harp": 46, "organ": 19, "celesta": 8, "voice": 52, "bells": 14, "glock": 9, "perc": 0,
        }

        def prog_for(inst):
            if inst in ("vn1", "vn2", "va", "vc", "cb"):
                return programs["strings"]
            for k in programs:
                if inst.startswith(k):
                    return programs[k]
            if inst in ("sop", "mez", "ten", "bar", "bbar", "treble") or inst.startswith("ch_"):
                return programs["voice"]
            if "bell" in inst:
                return programs["bells"]
            return 0

        def vlq(n):
            b = [n & 0x7F]
            n >>= 7
            while n:
                b.append((n & 0x7F) | 0x80)
                n >>= 7
            return bytes(reversed(b))

        tracks = []
        # conductor track
        tr = bytearray()
        tr += vlq(0) + b"\xff\x51\x03" + struct.pack(">I", int(60e6 / bpm))[1:]
        tr += vlq(0) + b"\xff\x03" + vlq(len(b"Elena")) + b"Elena"
        tr += vlq(0) + b"\xff\x2f\x00"
        tracks.append(bytes(tr))
        for ch_i, (voice, inst) in enumerate(voices):
            ch = ch_i % 16
            if ch == 9:
                ch = 10
            evs = []
            for n in notes:
                if n.voice != voice or n.inst != inst:
                    continue
                k = int(round(min(127, max(0, n.midi))))
                v = int(max(1, min(127, n.vel * 127)))
                evs.append((int(n.t * ticks_per_s), 1, k, v))
                evs.append((int(n.end * ticks_per_s), 0, k, 0))
            evs.sort(key=lambda e: (e[0], e[1]))
            tr = bytearray()
            nm = f"{voice}:{inst}".encode()
            tr += vlq(0) + b"\xff\x03" + vlq(len(nm)) + nm
            tr += vlq(0) + bytes([0xC0 | ch, prog_for(inst)])
            last = 0
            for tick, on, k, v in evs:
                tr += vlq(max(0, tick - last)) + bytes([(0x90 if on else 0x80) | ch, k, v])
                last = tick
            tr += vlq(0) + b"\xff\x2f\x00"
            tracks.append(bytes(tr))
        with open(path, "wb") as f:
            f.write(b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), ppq))
            for t in tracks:
                f.write(b"MTrk" + struct.pack(">I", len(t)) + t)

    def to_json(self):
        return {
            "sections": [{"key": s.key, "title": s.title, "start": s.start, "end": s.start + s.length}
                         for s in self.sections],
            "lines": [asdict(l) for l in self.lines()],
            "beats": self.beat_grid(),
            "cues": self.cues(),
        }
