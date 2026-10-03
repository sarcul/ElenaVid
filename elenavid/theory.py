"""Music theory primitives: pitch spelling, chord symbols, modal remapping, voice-leading."""
from __future__ import annotations

import itertools
import math
import re

NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_PITCH_RE = re.compile(r"^([A-Ga-g])(##|#|bb|b|x)?(-?\d)$")


def pitch(name: str) -> int:
    """'F#4' -> 66, 'Bb3' -> 58, 'Db5' -> 73. Middle C (C4) is 60."""
    m = _PITCH_RE.match(name.strip())
    if not m:
        raise ValueError(f"bad pitch name {name!r}")
    letter, acc, octave = m.groups()
    semis = NOTE_BASE[letter.upper()]
    semis += {"#": 1, "##": 2, "x": 2, "b": -1, "bb": -2, None: 0}[acc]
    return 12 * (int(octave) + 1) + semis


def midi_to_hz(m: float, a4: float = 440.0) -> float:
    return a4 * 2.0 ** ((m - 69.0) / 12.0)


def hz_to_midi(f: float, a4: float = 440.0) -> float:
    return 69.0 + 12.0 * math.log2(f / a4)


_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def name(m: int, flats: bool = False) -> str:
    names = _NAMES_FLAT if flats else _NAMES_SHARP
    return f"{names[m % 12]}{m // 12 - 1}"


# ---------------------------------------------------------------- chord symbols

QUALITIES = {
    "": (0, 4, 7), "maj": (0, 4, 7), "M": (0, 4, 7),
    "m": (0, 3, 7), "min": (0, 3, 7),
    "5": (0, 7),
    "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9),
    "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "M7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10), "mM7": (0, 3, 7, 11),
    "dim": (0, 3, 6), "dim7": (0, 3, 6, 9), "m7b5": (0, 3, 6, 10), "o": (0, 3, 6, 9),
    "aug": (0, 4, 8), "+": (0, 4, 8),
    "sus2": (0, 2, 7), "sus4": (0, 5, 7), "sus": (0, 5, 7), "7sus4": (0, 5, 7, 10),
    "add9": (0, 4, 7, 14), "madd9": (0, 3, 7, 14), "add2": (0, 2, 4, 7),
    "9": (0, 4, 7, 10, 14), "maj9": (0, 4, 7, 11, 14), "m9": (0, 3, 7, 10, 14),
    "7b9": (0, 4, 7, 10, 13), "m11": (0, 3, 7, 10, 14, 17),
    "6/9": (0, 4, 7, 9, 14),
}

_CHORD_RE = re.compile(
    r"^([A-G](?:#|b)?)"            # root
    r"([^/(]*)"                    # quality
    r"((?:\((?:no3|no5|add\d+)\))*)"  # modifiers like (no5)
    r"(?:/([A-G](?:#|b)?))?$"      # slash bass
)


class Chord:
    """A chord symbol resolved to pitch classes, with an explicit bass pitch class."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        m = _CHORD_RE.match(symbol.strip())
        if not m:
            raise ValueError(f"bad chord symbol {symbol!r}")
        root, qual, mods, bass = m.groups()
        if qual not in QUALITIES:
            raise ValueError(f"unknown chord quality {qual!r} in {symbol!r}")
        self.root = NOTE_BASE[root[0]] + (1 if "#" in root else -1 if "b" in root[1:] else 0)
        self.root %= 12
        ivs = list(QUALITIES[qual])
        if "(no3)" in mods:
            ivs = [i for i in ivs if i % 12 not in (3, 4)]
        if "(no5)" in mods:
            ivs = [i for i in ivs if i % 12 != 7]
        for add in re.findall(r"\(add(\d+)\)", mods):
            ivs.append({"9": 14, "2": 2, "4": 5, "11": 17, "6": 9, "13": 21}[add])
        self.intervals = tuple(ivs)
        self.pcs = sorted({(self.root + i) % 12 for i in ivs})
        if bass:
            b = NOTE_BASE[bass[0]] + (1 if "#" in bass else -1 if "b" in bass[1:] else 0)
            self.bass = b % 12
        else:
            self.bass = self.root
        # pitch classes in "importance" order: root, 3rd, 7th, 5th, extensions
        order = []
        for i in ivs:
            pc = (self.root + i) % 12
            if pc not in order:
                order.append(pc)
        self.ordered = order

    @property
    def third(self):
        for i in self.intervals:
            if i % 12 in (3, 4):
                return (self.root + i) % 12
        return None

    @property
    def fifth(self):
        for i in self.intervals:
            if i % 12 in (6, 7, 8):
                return (self.root + i) % 12
        return None

    def __repr__(self):
        return f"Chord({self.symbol})"


def pcs_in_range(pcs, lo: int, hi: int):
    return [m for m in range(lo, hi + 1) if m % 12 in pcs]


def bass_note(ch: Chord, lo: int = 36, hi: int = 52, prev: int | None = None) -> int:
    cands = pcs_in_range({ch.bass}, lo, hi)
    if prev is None:
        return cands[len(cands) // 2]
    return min(cands, key=lambda m: (abs(m - prev), m))


def voice_lead(chords, ranges, bass_range=(36, 52), include_bass=True, prev=None,
               avoid_pcs=None):
    """Smooth voice-leading through a list of Chord objects.

    ranges: list of (lo, hi) MIDI ranges for the upper voices, lowest first.
    Returns list of tuples (bass, v1, v2, ...) or (v1, v2, ...) when include_bass is False.
    avoid_pcs: optional set of pitch classes never to sound (used after Tommaso's death).
    """
    out = []
    prev_upper = prev
    prev_bass = None
    for ch in chords:
        pcs = [p for p in ch.pcs if not avoid_pcs or p not in avoid_pcs]
        b = bass_note(ch, *bass_range, prev=prev_bass)
        cand_lists = [pcs_in_range(set(pcs), lo, hi) for lo, hi in ranges]
        best, best_cost = None, 1e9
        for combo in itertools.product(*cand_lists):
            if any(combo[i] >= combo[i + 1] for i in range(len(combo) - 1)):
                continue  # no crossing or unisons
            got = {c % 12 for c in combo} | {b % 12}
            cost = 0.0
            # must contain the 3rd if the chord has one (and it is allowed)
            third = ch.third
            if third is not None and third in pcs and third not in got:
                cost += 30
            # prefer containing all pitch classes
            cost += 6 * len(set(pcs) - got)
            # avoid doubling the third
            if third is not None:
                cost += 4 * max(0, sum(1 for c in combo if c % 12 == third) - 1)
            # smoothness
            if prev_upper is not None and len(prev_upper) == len(combo):
                cost += sum(abs(a - p) for a, p in zip(combo, prev_upper)) * 1.0
                # soft penalty on parallel fifths/octaves between outer upper voice and bass
                if prev_bass is not None:
                    for v_prev, v in zip(prev_upper, combo):
                        i_prev = (v_prev - prev_bass) % 12
                        i_now = (v - b) % 12
                        if i_prev == i_now and i_now in (0, 7) and v != v_prev:
                            cost += 8
            else:
                # first chord: centre voices in range
                cost += sum(abs(c - (lo + hi) / 2) * 0.3 for c, (lo, hi) in zip(combo, ranges))
            # spacing: avoid gaps > octave between adjacent upper voices
            cost += sum(max(0, combo[i + 1] - combo[i] - 12) * 2 for i in range(len(combo) - 1))
            if cost < best_cost:
                best, best_cost = combo, cost
        if best is None:
            best = tuple(sorted(cl[len(cl) // 2] for cl in cand_lists))
        out.append(((b,) + best) if include_bass else best)
        prev_upper, prev_bass = best, b
    return out


# ---------------------------------------------------------------- modes / remapping

MODES = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),          # natural minor
    "harmonic": (0, 2, 3, 5, 7, 8, 11),       # harmonic minor
    "melodic": (0, 2, 3, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
}


def degree_of(m: int, tonic_pc: int, mode: str):
    """Return (octave_index, degree 0..6, chromatic offset) for MIDI pitch m."""
    scale = MODES[mode]
    rel = m - tonic_pc
    octv, pc = divmod(rel, 12)
    # nearest scale degree at or below
    best = None
    for d, s in enumerate(scale):
        off = pc - s
        if best is None or abs(off) < abs(best[1]) or (abs(off) == abs(best[1]) and off > 0):
            best = (d, off)
    return octv, best[0], best[1]


def remap(m: int, src_tonic_pc: int, src_mode: str, dst_tonic_pc: int, dst_mode: str,
          octave_shift: int = 0) -> int:
    """Map a pitch by scale degree from one key/mode to another (keeps chromatic offsets)."""
    octv, d, off = degree_of(m, src_tonic_pc, src_mode)
    return dst_tonic_pc + 12 * (octv + octave_shift) + MODES[dst_mode][d] + off
