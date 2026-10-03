"""Keys, Roman-numeral progressions and cadence templates for the full score.

A progression is produced as the textures module's string format ("G:2 | D7:2 | ..."), so every
existing texture generator can play it.
"""
from __future__ import annotations

import random
import re

from ..theory import Chord

PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
      "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11}
SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Db", "Gb", "Dm", "Gm", "Cm", "Fm", "Bbm", "Ebm", "Abm"}


class Key:
    def __init__(self, name: str):
        """'G', 'Bm', 'Ab', 'F#m' ..."""
        self.name = name
        self.minor = name.endswith("m")
        root = name[:-1] if self.minor else name
        self.tonic = PC[root]
        self.mode = "minor" if self.minor else "major"
        self.flats = name in FLAT_KEYS or ("b" in root)
        steps = MINOR if self.minor else MAJOR
        self.scale = [(self.tonic + s) % 12 for s in steps]

    def spell(self, pc: int) -> str:
        return (FLAT if self.flats else SHARP)[pc % 12]

    def degree_pc(self, deg: int) -> int:
        """1-based scale degree to pitch class (natural minor)."""
        return self.scale[(deg - 1) % 7]

    def leading(self) -> int:
        return (self.tonic + 11) % 12

    def pcs_for(self, chord: Chord | None) -> set[int]:
        """Melodic pitch classes available over a chord: the scale, the chord, the leading note in minor
        over the dominant."""
        s = set(self.scale)
        if chord is not None:
            s |= set(chord.pcs)
            if self.minor and chord.root == (self.tonic + 7) % 12:
                s.discard((self.tonic + 10) % 12)
                s.add(self.leading())
        return s

    def relative(self) -> "Key":
        if self.minor:
            return Key(self.spell((self.tonic + 3) % 12))
        return Key(self.spell((self.tonic + 9) % 12) + "m")

    def dominant(self) -> "Key":
        return Key(self.spell((self.tonic + 7) % 12) + ("m" if self.minor else ""))

    def __repr__(self):
        return f"Key({self.name})"


_RN = re.compile(r"^(b|#)?(VII|VI|V|IV|III|II|I|vii|vi|v|iv|iii|ii|i|N|It|Ger|Fr)(o|ø|\+)?(7|65|43|42|6|64|9)?(?:/(.+))?$")
_RN_DEG = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}


def roman(rn: str, key: Key) -> str:
    """Roman numeral -> chord symbol in a key. Supports figures, secondary chords (V7/V), flat degrees
    (bVI), the Neapolitan (N6) and the cadential six-four (Cad64 = I64)."""
    rn = rn.strip()
    if rn in ("Cad64", "cad64"):
        rn = "i64" if key.minor else "I64"
    m = _RN.match(rn)
    if not m:
        raise ValueError(f"bad roman numeral {rn!r}")
    acc, num, qual, fig, sec = m.groups()
    if sec:
        target = roman(sec if sec != "V" else ("V" if not key.minor else "V"), key)
        tc = Chord(target.split("/")[0])
        tkey = Key(key.spell(tc.root) + ("m" if tc.third is not None and (tc.third - tc.root) % 12 == 3 else ""))
        return roman(f"{acc or ''}{num}{qual or ''}{fig or ''}", tkey)
    if num == "N":
        root = (key.tonic + 1) % 12
        sym = FLAT[root]
        third = (root + 4) % 12
        return f"{sym}/{FLAT[third]}" if fig in ("6", None) else sym
    if num in ("It", "Ger", "Fr"):
        # augmented sixth on b6: spelt as a dominant seventh on b6 (Ger) or its subset
        root = (key.tonic + 8) % 12
        return key.spell(root) + ("7" if num == "Ger" else "7" if num == "Fr" else "7")
    deg = _RN_DEG[num.upper()]
    steps = MINOR if key.minor else MAJOR
    root = (key.tonic + steps[deg - 1]) % 12
    if acc == "b":
        root = (key.tonic + MAJOR[deg - 1] - 1) % 12
    elif acc == "#":
        root = (key.tonic + MAJOR[deg - 1] + 1) % 12
    upper = num.isupper()
    if key.minor and num == "V":
        upper = True
    if key.minor and num == "VII" and qual == "o":
        root = key.leading()
    if qual == "o":
        q = "dim7" if fig in ("7", "65", "43", "42") else "dim"
        if key.minor and deg == 7:
            root = key.leading()
        elif not key.minor and deg == 7:
            root = key.leading()
    elif qual == "ø":
        q = "m7b5"
    elif qual == "+":
        q = "aug"
    else:
        seventh = fig in ("7", "65", "43", "42")
        if upper:
            if seventh:
                q = "maj7" if deg in (1, 4) and not (key.minor and deg == 5) and acc is None and not (num == "I" and sec) else "7"
                if deg == 5 or (acc and deg in (3, 6, 7)):
                    q = "7" if deg == 5 else "maj7"
            else:
                q = ""
        else:
            q = "m7" if seventh else "m"
    name = (FLAT if acc == "b" else SHARP if acc == "#" else (FLAT if key.flats else SHARP))[root]
    sym = name + q
    ch = Chord(sym)
    # inversions via figures
    if fig in ("6", "65"):
        bass = ch.third
    elif fig in ("64", "43"):
        bass = ch.fifth
    elif fig == "42":
        bass = (ch.root + (10 if q in ("7", "m7", "m7b5") else 11 if q == "maj7" else 9)) % 12
    else:
        bass = None
    if bass is not None and bass != ch.root:
        sym += "/" + key.spell(bass)
    return sym


def realise(romans: str, key: Key) -> str:
    """'I:2 | ii6:1 V7:1 | I:4' -> 'G:2 | Am/C:1 D7:1 | G:4' (keeps '|')."""
    out = []
    for tok in romans.split():
        if tok == "|":
            out.append("|")
            continue
        rn, d = tok.rsplit(":", 1)
        if rn.startswith("@"):                    # a literal chord symbol escape: '@Ab7:2'
            out.append(f"{rn[1:]}:{d}")
            continue
        if rn == "r":
            out.append(f"r:{d}")
            continue
        out.append(f"{roman(rn, key)}:{d}")
    return " ".join(out)


# ---------------------------------------------------------------------------- phrase templates
# Each template covers a number of bars with a harmonic rhythm in bars; durations are filled in by
# fit(). Roles: 'open' (antecedent, half cadence), 'close' (perfect cadence), 'contrast' (the b
# phrase, away from the tonic), 'climax' (a'' with the cadential six-four), 'pedal' (static).
TEMPLATES = {
    "major": {
        "open": [["I", "IV", "I", "V"], ["I", "vi", "ii6", "V"], ["I", "V", "I", "V"], ["I", "IV", "ii6", "V"]],
        "close": [["I", "IV", "V7", "I"], ["I", "ii6", "V7", "I"], ["vi", "ii6", "V7", "I"], ["I", "IV", "Cad64", "V7", "I"]],
        "contrast": [["vi", "iii", "IV", "V"], ["V7/vi", "vi", "ii", "V7"], ["IV", "iv", "I64", "V"],
                     ["V7/V", "V", "V7/ii", "ii", "V7"], ["bVI", "IV", "ii6", "V"]],
        "climax": [["I", "IV", "Cad64", "V7", "I"], ["I", "vi", "ii65", "Cad64", "V7", "I"],
                   ["IV", "iv", "I64", "V7", "I"]],
        "pedal": [["I", "IV64", "I", "V7", "I"]],
    },
    "minor": {
        "open": [["i", "iv", "i", "V"], ["i", "VI", "iv6", "V"], ["i", "V", "i", "V"], ["i", "iio6", "V"]],
        "close": [["i", "iv", "V7", "i"], ["i", "iio6", "V7", "i"], ["VI", "N6", "V7", "i"], ["i", "iv", "Cad64", "V7", "i"]],
        "contrast": [["III", "VII", "III", "V"], ["VI", "III", "iv", "V"], ["V7/III", "III", "iv", "V7"],
                     ["iv", "VI", "N6", "V"]],
        "climax": [["i", "iv", "Cad64", "V7", "i"], ["VI", "N6", "Cad64", "V7", "i"], ["iv", "viio7", "Cad64", "V7", "i"]],
        "pedal": [["i", "iv64", "i", "V7", "i"]],
    },
}


def phrase_prog(role: str, key: Key, bars: int, bar_len: float, rng: random.Random,
                rhythm: float | None = None, choice: int | None = None) -> str:
    """A progression string for one phrase of `bars` bars."""
    pool = TEMPLATES["minor" if key.minor else "major"][role]
    t = pool[choice % len(pool)] if choice is not None else rng.choice(pool)
    total = bars * bar_len
    n = len(t)
    if rhythm:
        durs = [total / n] * n
    else:
        durs = allot(t, total, bar_len)
    return " ".join(f"{roman(rn, key)}:{d:g}" for rn, d in zip(t, durs))


def allot(t, total, bar_len):
    """Durations for a chord sequence: cadence chords take one slot each, the final chord a bar's
    worth when there is room, the opening chords share the rest (longest first)."""
    n = len(t)
    unit = bar_len / 2
    slots = int(round(total / unit))
    while slots < n + 1 and unit > 0.25:
        unit /= 2
        slots = int(round(total / unit))
    cad = {"V7", "V", "Cad64", "V65", "V43", "viio7"}
    fixed = [0] * n
    fixed[-1] = max(1, min(int(round(bar_len / unit)), slots // 4))
    for k in range(n - 1):
        if t[k] in cad and k >= n - 3:
            fixed[k] = 1
    free = [k for k in range(n) if fixed[k] == 0]
    rest = slots - sum(fixed)
    if free:
        base = [rest // len(free)] * len(free)
        for j in range(rest - sum(base)):
            base[j] += 1
        if min(base) <= 0:
            base = [max(1, x) for x in base]
        for k, v in zip(free, base):
            fixed[k] = v
    s = sum(fixed)
    if s != slots:                          # absorb rounding into the first chord
        fixed[0] += slots - s
        fixed[0] = max(1, fixed[0])
    return [f * unit for f in fixed]
