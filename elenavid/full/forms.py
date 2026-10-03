"""The number builder: how each scene of the full opera is written.

A Num accumulates parts on a beat cursor with its own tempo map, metres and key. Musical verbs:
    orch      an orchestral passage over a progression (with an optional instrumental melody)
    sing      one verse line: the film's own tune if it set this line, else a re-texting of a stored
              phrase model, else newly composed; accompanied in the chosen style
    stanza    lyric form over several lines (the Verdian a a' b a'' and its extensions)
    recit     recitative for a run of libretto items (several speakers, stage directions)
    chorus    SATB chorus (soprano tune harmonised beneath)
    duet      two voices together, the second in thirds or sixths
    theme     a named theme (wedding, Vittorio, Marco, Tommaso) in the orchestra
    island    a passage of the film score placed verbatim
Every number also records where it is set and who sings when, for the picture.
"""
from __future__ import annotations

import copy
import math
import random

from ..compose import textures as tx
from ..compose.choral import harmonize
from ..notation import Ev, parse, attach_lyrics
from ..score_model import Section, TempoMap, Lyricline
from ..theory import Chord
from . import melody as mel
from . import orch
from .harmony import Key, roman, realise, phrase_prog, allot
from .libretto import Line, Direction, by_key
from .prosody import syllables, Syl, last_stress
from .tunebank import tune as film_tune, island as film_island
from ..compose.themes import MARCO, MARCO_WARPED, MARCO_LETTER, VITTORIO, WEDDING

# the leitmotifs the picture draws as lines of light (elenavid/video/render.py motif_lines)
MOTIFS = [(MARCO_LETTER, "marco_letter"), (MARCO_WARPED, "marco_warped"), (MARCO, "marco"),
          (VITTORIO, "vittorio"), (WEDDING, "wedding")]


def motif_of(text):
    """The leitmotif a theme string states, or None (variants with altered rhythm are not matched)."""
    if not isinstance(text, str):
        return None
    s = " ".join(text.split())
    for theme, name in MOTIFS:
        if s.startswith(" ".join(theme.split())):
            return name
    return None

VOICES = {   # speaker -> (instrument, voice id, lowest, highest, tessitura low, tessitura high)
    "elena": ("sop", "elena", 60, 84, 65, 79),
    "marco": ("ten", "marco", 48, 69, 52, 66),
    "vittorio": ("bar", "vittorio", 43, 65, 46, 62),
    "davide": ("bbar", "davide", 40, 63, 43, 59),
    "madre": ("mez", "madre", 55, 76, 57, 72),
    "nives": ("mez", "nives", 55, 76, 57, 72),
    "ferroviere": ("ten", "ferroviere", 50, 67, 53, 65),
}
CHORUS = {"S": ("ch_s", 60, 79), "A": ("ch_a", 55, 72), "T": ("ch_t", 48, 67), "B": ("ch_b", 41, 60)}
VOICE_STYLES = {"aria", "duet", "vow", "parlato", "aside", "lullaby", "chorus", "latin", "vision",
                "offstage", "heat", "letter_read"}
STYLE_OF = {"aria": "aria", "duet": "duet", "chorus": "chorus", "latin": "latin", "recit": "parlato",
            "vision": "vision", "offstage": "offstage", "aside": "aside"}

_LIB = None


def lib():
    global _LIB
    if _LIB is None:
        _LIB = by_key()
    return _LIB


class Num:
    def __init__(self, key, title, tonality, tempo, meter=(4, 4), location="", act=0, scene=0,
                 avoid=(), seed=None, lib_key=None):
        self.key = key
        self.title = title
        self.k = Key(tonality)
        self.segs = [(0.0, float(tempo))]
        self.meters = [(0.0, meter[0], meter[1])]
        self.cursor = 0.0
        self.parts = []                  # (inst, voice, evs, tags)
        self.lines = []                  # (Lyricline, evs)
        self.texts = []                  # (Lyricline, beat0, beat1)
        self.cues = {}
        self.harm = []                   # (beat, dur, Chord) for the whole number
        self.models = {}                 # phrase models for re-texting
        self.last_note = {}              # voice -> last Ev placed (for continuity and overlap)
        self.avoid = frozenset(avoid)
        self.rng = random.Random(seed if seed is not None else (sum(map(ord, key)) * 7919))
        self.act, self.scene = act, scene
        self.meta = {"location": location, "singing": [], "events": [], "act": act, "scene": scene}
        self.lib = lib().get(lib_key or key)

    # ------------------------------------------------------------------ libretto
    def L(self, speaker=None, a=0, b=None):
        if self.lib is None:
            return []
        ls = self.lib.lines(speaker)
        return ls[a:b]

    # ------------------------------------------------------------------ time
    def meter_at(self, beat=None):
        beat = self.cursor if beat is None else beat
        cur = self.meters[0]
        for m in self.meters:
            if m[0] <= beat + 1e-9:
                cur = m
        return cur[1], cur[2]

    def bl(self, beat=None):
        num, den = self.meter_at(beat)
        return num * 4.0 / den

    def bpm(self, beat=None):
        beat = self.cursor if beat is None else beat
        return TempoMap(self.segs).bpm(beat)

    def tempo(self, bpm, ramp_over=None):
        """New tempo from the cursor; ramp_over: beats over which to ramp there from the current tempo."""
        if ramp_over:
            self.segs.append((self.cursor, self.bpm(), "ramp"))
            self.segs.append((self.cursor + ramp_over, float(bpm)))
        else:
            self.segs = [s for s in self.segs if s[0] < self.cursor - 1e-9]
            self.segs.append((self.cursor, float(bpm)))
        return self

    def meter(self, num, den):
        self.bar_align()
        self.meters = [m for m in self.meters if m[0] < self.cursor - 1e-9]
        self.meters.append((self.cursor, num, den))
        return self

    def key_to(self, name):
        self.k = Key(name)
        return self

    def bar_start(self, beat=None):
        beat = self.cursor if beat is None else beat
        b = 0.0
        last = 0.0
        while b <= beat + 1e-9:
            last = b
            b += self.bl(b)
        return last

    def bar_align(self):
        """Move the cursor to the next bar line (if not already on one)."""
        b0 = self.bar_start()
        if abs(b0 - self.cursor) > 1e-6:
            self.cursor = b0 + self.bl(b0)
        return self

    def rest(self, beats):
        self.cursor += beats
        return self

    def seconds(self, s):
        """Beats that last s seconds at the cursor's tempo."""
        return s * self.bpm() / 60.0

    def cue(self, name, beat=None):
        self.cues[name] = self.cursor if beat is None else beat
        return self

    def event(self, kind, **data):
        self.meta["events"].append({"beat": self.cursor, "kind": kind, **data})
        return self

    # ------------------------------------------------------------------ material
    def add(self, inst, evs, voice=None, **tags):
        if evs:
            self.parts.append((inst, voice or inst, evs, tags))
        return evs

    def add_parts(self, parts):
        for inst, evs, tags in parts:
            self.add(inst, [e for e in evs if int(round(e.midi)) % 12 not in self.avoid], **tags)

    def show(self, voice, evs, it, en, style="aria", pos="low"):
        self.lines.append((Lyricline(voice, it, en, style=style, pos=pos), evs))

    def text(self, it, en, beats, style="letter_read", pos="low", voice=""):
        self.texts.append((Lyricline(voice, it, en, style=style, pos=pos), self.cursor, self.cursor + beats))

    def chord_at(self, beat):
        cur = None
        for b, d, c in self.harm:
            if b <= beat + 1e-6 and c is not None:
                cur = c
            if b > beat + 1e-6:
                break
        return cur

    def _set_harm(self, p):
        if not p:
            return
        b0 = p[0][0]
        b1 = p[-1][0] + p[-1][1]
        self.harm = [h for h in self.harm if h[0] + h[1] <= b0 + 1e-6 or h[0] >= b1 - 1e-6]
        self.harm += [(b, d, c) for b, d, c in p]
        self.harm.sort(key=lambda h: h[0])

    # ------------------------------------------------------------------ harmony
    def prog(self, spec, origin=None, key=None):
        """A progression at the cursor: roman numerals ('I:2 V7:2'), or symbols prefixed '@'
        ('@Ab7:2'), or a list from textures.prog. Returns textures.prog list in section beats."""
        origin = self.cursor if origin is None else origin
        key = key or self.k
        if isinstance(spec, list):
            if not spec:
                return spec
            shift = origin - spec[0][0]
            return [(b + shift, d, c) for b, d, c in spec]
        toks = []
        for tok in spec.split():
            if tok == "|":
                continue
            sym, d = tok.rsplit(":", 1)
            if sym.startswith("@") or sym == "r":
                toks.append(f"{sym.lstrip('@')}:{d}")
            else:
                toks.append(f"{roman(sym, key)}:{d}")
        p = tx.prog(" ".join(toks), origin=origin)
        return self._sanitise(p)

    def _sanitise(self, p):
        if not self.avoid:
            return p
        out = []
        for b, d, c in p:
            if c is not None and set(c.pcs) & self.avoid:
                pcs = [x for x in c.pcs if x not in self.avoid]
                if c.bass in self.avoid or len(pcs) < 2:
                    root = c.root if c.root not in self.avoid else (c.root - 1) % 12
                    c = Chord(self.k.spell(root) + "5")
                else:
                    # rebuild without the avoided tones (keep root and bass)
                    sym = self.k.spell(c.root) + ("5" if (c.third in self.avoid) else ("m" if c.third is not None and (c.third - c.root) % 12 == 3 else ""))
                    if c.bass != c.root and c.bass not in self.avoid:
                        sym += "/" + self.k.spell(c.bass)
                    c = Chord(sym)
            out.append((b, d, c))
        return out

    def sprog(self, text, origin=None):
        """A progression from chord symbols ('D:3 | A7:1.5 D:1.5'), at the cursor."""
        origin = self.cursor if origin is None else origin
        return self._sanitise(tx.prog(text, origin=origin))

    def together(self, *calls):
        """Several voices from the same downbeat (each call is a function of the builder that sings one
        line); the cursor moves to the latest end. The first call carries the accompaniment."""
        self.bar_align()
        start = self.cursor
        end = start
        for k, fn in enumerate(calls):
            self.cursor = start
            fn(self)
            end = max(end, self.cursor)
        self.cursor = end
        return self

    def role_prog(self, role, bars, origin=None, choice=None):
        origin = self.cursor if origin is None else origin
        s = phrase_prog(role, self.k, bars, self.bl(origin), self.rng, choice=choice)
        return self._sanitise(tx.prog(s, origin=origin))

    # ------------------------------------------------------------------ orchestra
    def orch(self, spec, style="pad", dyn=0.4, melody=None, melody_inst="cl", advance=True,
             melody_transpose=0, bars=None, **kw):
        """An orchestral passage. spec: progression spec (see prog) or a role name with bars."""
        if isinstance(spec, str) and spec in ("open", "close", "contrast", "climax", "pedal"):
            p = self.role_prog(spec, bars or 2)
        else:
            p = self.prog(spec)
        if not p:
            return self
        self._set_harm(p)
        self.add_parts(orch.accompany(style, p, dyn, bar_len=self.bl(), avoid=self.avoid, **kw))
        if melody is not None:
            evs = melody if isinstance(melody, list) else parse(melody, origin=p[0][0], vel=orch.V(dyn, 0.9))
            m = motif_of(melody)
            self.add(melody_inst, [Ev(e.beat, e.dur, e.midi + melody_transpose, e.vel, e.art) for e in evs
                                   if int(round(e.midi + melody_transpose)) % 12 not in self.avoid],
                     **({"motif": m, "appearance": f"{self.key}@{p[0][0]:.0f}"} if m else {}))
        if advance:
            self.cursor = p[-1][0] + p[-1][1]
        return self

    def theme(self, text, inst="cl", vel=0.45, transpose=0, origin=None, advance=False, voice=None, **tags):
        origin = self.cursor if origin is None else origin
        evs = parse(text, origin=origin, vel=vel, transpose=transpose)
        evs = [e for e in evs if int(round(e.midi)) % 12 not in self.avoid]
        m = motif_of(text)
        if m and "motif" not in tags:
            # each statement is its own appearance, so the picture draws it as one contour
            tags = dict(tags, motif=m, appearance=f"{self.key}@{origin:.0f}")
        self.add(inst, evs, voice=voice, **tags)
        if advance and evs:
            self.cursor = max(e.end for e in evs)
        return evs

    def tommaso(self, beats, vel=0.28, inst="vc_harm", origin=None, **tags):
        """Tommaso's tone: A4 held (the cello harmonic, or the cor anglais / treble)."""
        origin = self.cursor if origin is None else origin
        ev = Ev(origin, beats, 69, vel, "", None, None, {"tommaso": True, **tags})
        self.add(inst, [ev], voice="tommaso_tone")
        return ev

    # ------------------------------------------------------------------ singing
    def _fit_voice(self, voice, evs, bl):
        """How far (in whole bars) a new phrase must move to clear the number's start and this voice's
        previous note; shortens the previous note when that is enough."""
        if not evs:
            return 0.0
        first = min(e.beat for e in evs)
        shift = 0.0
        if first < -1e-6:
            shift = math.ceil(-first / bl - 1e-9) * bl
        last = self.last_note.get(voice)
        if last is not None:
            f2 = first + shift
            if last.end > f2 - 0.05:
                new_dur = f2 - 0.1 - last.beat
                if new_dur >= 0.25:
                    last.dur = new_dur
                else:
                    need = last.end + 0.1 - f2
                    shift += math.ceil(need / bl - 1e-9) * bl
        return shift

    def _place_voice(self, voice, evs):
        """Avoid overlap with the voice's previous note: shorten it if the new phrase starts early."""
        if not evs:
            return evs
        last = self.last_note.get(voice)
        first = min(evs, key=lambda e: e.beat)
        if last is not None and last.end > first.beat - 0.05:
            new_dur = first.beat - 0.1 - last.beat
            if new_dur >= 0.3:
                last.dur = new_dur
            else:
                shift = last.end + 0.25 - first.beat
                for e in evs:
                    e.beat += shift
        self.last_note[voice] = max(evs, key=lambda e: e.end)
        return evs

    def sing(self, speaker, line, model=None, store=None, role="open", cadence=None, bars=None,
             style="andante", contour="arch", accomp="arpeggio", dyn=0.45, double=None, show=True,
             prog=None, use_tune=True, transpose=0, disp_style="aria", pos="low", orn=True, vel=None,
             accomp_kw=None, final_at=None, text_override=None):
        """One verse line at the cursor. Returns its events. The phrase's first downbeat is the
        cursor (an anacrusis may sit before it); the cursor advances by the phrase's bars."""
        inst, vid, lo, hi, tlo, thi = VOICES[speaker]
        it = text_override or (line.it if isinstance(line, Line) else line)
        en = line.en if isinstance(line, Line) else ""
        latin = isinstance(line, Line) and line.latin
        syls = syllables(it, latin=latin)
        self.bar_align()
        bl = self.bl()
        num, den = self.meter_at()
        cad = cadence or {"open": "half", "close": "full", "contrast": "half", "climax": "full",
                          "pedal": "full"}.get(role, "full")
        origin = self.cursor
        evs = None
        chords = None
        t = film_tune(it, speaker) if use_tune and model is None else None
        if t is not None and abs(t.bar_len - bl) < 1e-6:
            # the film's own setting of this line
            rel0 = t.phase if t.phase < bl / 2 else t.phase - bl
            evs = []
            for e in t.notes:
                c = copy.deepcopy(e)
                c.beat = origin + rel0 + e.beat
                c.midi += transpose
                evs.append(c)
            end = rel0 + t.length
            nb = max(1, math.ceil((end - 1e-6) / bl))
            chords = tx.prog(" ".join(f"{s}:{d:g}" for _, d, s in t.chords), origin=origin + rel0) if t.chords else None
            if chords and transpose:
                chords = [(b, d, Chord(_transpose_sym(c.symbol, transpose))) for b, d, c in chords]
            if chords:
                # extend the harmony to fill the phrase's bars
                pend = origin + nb * bl
                last = chords[-1]
                if last[0] + last[1] < pend:
                    chords[-1] = (last[0], pend - last[0], last[2])
                if chords[0][0] > origin:
                    chords.insert(0, (origin, chords[0][0] - origin, chords[0][2]))
                chords = [(max(origin, b), d - max(0, origin - b), c) for b, d, c in chords if b + d > origin]
            mdl = {"evs": [copy.deepcopy(e) for e in evs], "origin": origin, "bars": nb, "syls": syls,
                   "chords": [(b - origin, d, c) for b, d, c in (chords or [])], "bl": bl}
        elif model is not None:
            m = self.models[model] if isinstance(model, str) else model
            mp = [(b - m["origin"], d, c) for b, d, c in []]
            nb = m["bars"]
            p = prog or [(origin + b, d, c) for b, d, c in m["chords"]] or self.role_prog(role, nb)
            p = self._recadence(p, cad, nb, bl, origin) if cadence or role in ("close", "climax") else p
            self._set_harm(p)
            model_evs = [copy.deepcopy(e) for e in m["evs"]]
            first = min(e.beat for e in model_evs)
            rel = [Ev(e.beat - first, e.dur, e.midi, e.vel, e.art, e.lyric) for e in model_evs]
            downbeat0 = m["origin"] - first
            evs, nb2 = mel.retext(rel, m["syls"], syls, self.k, self.chord_at, lo, hi, bl, (num, den),
                                  downbeat0, cadence=cad, style=style, contour=contour, avoid=self.avoid,
                                  rng=self.rng, origin=origin)
            if contour in ("high",) and role == "climax":
                evs = self._lift_climax(evs, hi)
            chords = p
            nb = max(nb, nb2)
            mdl = {"evs": [copy.deepcopy(e) for e in evs], "origin": origin, "bars": nb, "syls": syls,
                   "chords": [(b - origin, d, c) for b, d, c in p], "bl": bl}
        else:
            nb = bars or max(1, math.ceil(len(syls) / {4.0: 5.5, 3.0: 4.5, 2.0: 3.0, 6.0: 8.0}.get(bl, 5.0)))
            if bl == 3.0 and num == 6 and nb < 2:
                nb = 2
            p = prog or self.role_prog(role, nb)
            if isinstance(p, str):
                p = self.prog(p)
            self._set_harm(p)
            start = self.last_note.get(vid).midi if self.last_note.get(vid) is not None else None
            evs, nb2 = mel.phrase(syls, self.k, self.chord_at, lo, hi, bl, (num, den), origin=origin, bars=nb,
                                  style=style, contour=contour, cadence=cad, start=start, tess=(tlo, thi),
                                  final_at=final_at, avoid=self.avoid, rng=self.rng, orn=orn)
            if nb2 != nb:
                p = self.role_prog(role, nb2)
                self._set_harm(p)
                nb = nb2
            chords = p
            mdl = {"evs": [copy.deepcopy(e) for e in evs], "origin": origin, "bars": nb, "syls": syls,
                   "chords": [(b - origin, d, c) for b, d, c in p], "bl": bl}
        # clear the number's start and the voice's previous phrase, by whole bars only
        shift = self._fit_voice(vid, evs, bl)
        if shift:
            for e in evs:
                e.beat += shift
            origin += shift
            if chords:
                chords = [(b + shift, d, c) for b, d, c in chords]
            mdl["origin"] = origin
            mdl["evs"] = [copy.deepcopy(e) for e in evs]
        v = vel if vel is not None else orch.V(dyn, 1.05)
        for e in evs:
            e.vel = v * (1.08 if e.lyric and e.lyric != "_" and False else 1.0)
            e.tags["style"] = disp_style if disp_style in VOICE_STYLES else "aria"
        evs = [e for e in evs if int(round(e.midi)) % 12 not in self.avoid] if self.avoid else evs
        self._place_voice(vid, evs)
        self.add(inst, evs, voice=vid)
        if chords:
            self._set_harm(chords)
            if accomp:
                self.add_parts(orch.accompany(accomp, chords, dyn * 0.85, bar_len=bl, avoid=self.avoid,
                                              **(accomp_kw or {})))
        if double:
            dinst, semis = double if isinstance(double, tuple) else (double, 0)
            self.add(dinst, orch.double(evs, semis, 0.6, self.avoid))
        if show:
            self.show(vid, evs, it, en, style=STYLE_OF.get(disp_style, disp_style), pos=pos)
        self.meta["singing"].append({"voice": vid, "b0": min(e.beat for e in evs), "b1": max(e.end for e in evs)})
        if store:
            self.models[store] = mdl
        self.cursor = origin + nb * bl
        return evs

    def _recadence(self, p, cad, nb, bl, origin):
        """Rewrite the last chords of a borrowed progression for a different cadence."""
        p = list(p)
        if not p:
            return p
        end = origin + nb * bl
        tonic = Chord(roman("i" if self.k.minor else "I", self.k))
        dom = Chord(roman("V7", self.k))
        if cad == "full":
            # last bar: V7 (half) then I
            half = bl / 2 if bl >= 3 else bl
            cut = end - bl
            p = [(b, min(d, cut - b), c) for b, d, c in p if b < cut - 1e-6]
            p += [(cut, half, dom), (cut + half, end - cut - half, tonic)]
        elif cad == "half":
            cut = end - bl
            p = [(b, min(d, cut - b), c) for b, d, c in p if b < cut - 1e-6]
            p += [(cut, end - cut, Chord(roman("V", self.k)))]
        return self._sanitise([(b, d, c) for b, d, c in p if d > 1e-6])

    def _lift_climax(self, evs, hi):
        """Raise the highest stressed note of a climactic phrase by a step if there is room."""
        cand = max(evs, key=lambda e: e.midi)
        for up in (2, 1):
            m = cand.midi + up
            ch = self.chord_at(cand.beat + 1e-4)
            if m <= hi and ch is not None and int(m) % 12 in ch.pcs and int(m) % 12 not in self.avoid:
                cand.midi = m
                break
        return evs

    def stanza(self, speaker, lines, plan, style="andante", accomp="arpeggio", dyn=(0.35, 0.6),
               contour=None, double_climax=("fl", 12), disp_style="aria", climax_accomp=None, **kw):
        """Lyric form. plan: tokens 'A:open', 'B:close', "A':open", 'C:contrast', "A'':climax" ...
        A letter without a prime composes (or takes the film's tune) and stores a model; primes re-text."""
        toks = plan.split() if isinstance(plan, str) else plan
        n = len(lines)
        out = []
        d0, d1 = dyn if isinstance(dyn, tuple) else (dyn, dyn)
        for i, line in enumerate(lines):
            tok = toks[i % len(toks)]
            letter, _, role = tok.partition(":")
            role = role or ("close" if i % 2 else "open")
            base = letter.rstrip("'")
            primes = len(letter) - len(base)
            dyn_i = d0 + (d1 - d0) * (i / max(1, n - 1))
            climax = role == "climax"
            if i == n - 1 and role == "open":
                role = "close"
            ctr = contour or ("high" if climax else "open" if role in ("open", "contrast") else "arch")
            acc = climax_accomp if (climax and climax_accomp) else accomp
            dbl = double_climax if climax else None
            if primes == 0 or base not in self.models:
                evs = self.sing(speaker, line, store=base, role=role, style=style, contour=ctr,
                                accomp=acc, dyn=dyn_i, double=dbl, disp_style=disp_style, **kw)
            else:
                evs = self.sing(speaker, line, model=base, role=role, style=style, contour=ctr,
                                accomp=acc, dyn=dyn_i, double=dbl, disp_style=disp_style, **kw)
            out.append(evs)
        return out

    def coda(self, speaker, lines, models, style="andante", accomp="arpeggio", dyn=(0.5, 0.7),
             cadenza=True, disp_style="aria", repeats=2, **kw):
        """The closing lines sung again and again, rising to a climax, a cadenza, the final cadence."""
        d0, d1 = dyn
        for r in range(repeats):
            for j, (line, mdl) in enumerate(zip(lines, models)):
                last = r == repeats - 1 and j == len(lines) - 1
                role = "climax" if (r == repeats - 1 and j == 0) else ("close" if j == len(lines) - 1 else "open")
                dd = d0 + (d1 - d0) * (r * len(lines) + j) / max(1, repeats * len(lines) - 1)
                if last and cadenza:
                    self.cadenza(speaker, dyn=dd)
                self.sing(speaker, line, model=mdl, role=role, style=style, accomp=accomp, dyn=dd,
                          contour="high" if role == "climax" else None or "arch", disp_style=disp_style, **kw)
        return self

    def cadenza(self, speaker, dyn=0.55, vowel="a", length=None):
        """A free cadenza before the last line: the orchestra holds the cadential six-four, the voice
        runs up and back on one vowel, the tempo broadens."""
        inst, vid, lo, hi, tlo, thi = VOICES[speaker]
        self.bar_align()
        start = self.cursor
        bl = self.bl()
        six4 = self.prog(f"{'i64' if self.k.minor else 'I64'}:{bl * 2:g}")
        self._set_harm(six4)
        self.add_parts(orch.pad(six4, dyn * 0.5, self.avoid, sord=True))
        ch = six4[0][2]
        pcs = self.k.pcs_for(ch)
        top = max(m for m in range(lo, hi + 1) if m % 12 in ch.pcs and m % 12 not in self.avoid and m <= hi - 1)
        startp = max(m for m in range(tlo, thi) if m % 12 in ch.pcs and m % 12 not in self.avoid)
        up = [m for m in range(startp, top + 1) if m % 12 in pcs and m % 12 not in self.avoid]
        down = [m for m in range(top - 1, startp - 6, -1) if m % 12 in pcs and m % 12 not in self.avoid]
        run = up + down[:8]
        n = len(run)
        L = length or bl * 2 - 0.5
        step = (L - 1.5) / max(1, n - 1)
        evs = []
        t = start
        for k, m in enumerate(run):
            d = 1.5 if k == len(up) - 1 else step
            evs.append(Ev(t, d, m, orch.V(dyn, 1.05), "", vowel if k == 0 else "_", None, {"style": "aria"}))
            t += d
        bpm0 = self.bpm(start)
        self.segs = [x for x in self.segs if x[0] < start - 1e-9]
        self.segs += [(start, bpm0, "ramp"), (start + bl * 2 - 0.01, bpm0 * 0.7), (start + bl * 2, bpm0)]
        self._place_voice(vid, evs)
        self.add(inst, evs, voice=vid)
        self.cursor = start + bl * 2
        return self

    def ritornello(self, model, inst="cl", dyn=0.4, accomp="arpeggio", transpose=0, bars=None):
        """An instrumental restatement of a stored phrase (no words)."""
        m = self.models[model]
        self.bar_align()
        origin = self.cursor
        nb = bars or m["bars"]
        first = m["origin"]
        p = [(origin + b, d, c) for b, d, c in m["chords"] if b < nb * m["bl"]]
        if p:
            self._set_harm(p)
            self.add_parts(orch.accompany(accomp, p, dyn, bar_len=self.bl(), avoid=self.avoid))
        evs = [Ev(origin + (e.beat - first), e.dur, e.midi + transpose, orch.V(dyn), e.art)
               for e in m["evs"] if (e.beat - first) < nb * m["bl"]]
        self.add(inst, [e for e in evs if e.beat >= origin - 2 and int(round(e.midi)) % 12 not in self.avoid])
        self.cursor = origin + nb * m["bl"]
        return self

    def duet(self, sp1, sp2, line, interval=-3, model=None, store=None, role="close", style="andante",
             accomp="arpeggio", dyn=0.5, contour="arch", **kw):
        """Both voices on one line: the first leads, the second follows a third (or sixth) below in the
        key. interval: diatonic steps (-2 = third below, -5 = sixth below, +2 = third above)."""
        start = self.cursor
        evs1 = self.sing(sp1, line, model=model, store=store, role=role, style=style, accomp=accomp,
                         dyn=dyn, contour=contour, show=False, **kw)
        inst2, vid2, lo2, hi2, _, _ = VOICES[sp2]
        steps = {-3: -2, -6: -5, 3: 2, 6: 5}.get(interval, interval)
        ev2 = tx.diatonic(evs1, steps, self.k.tonic, self.k.mode)
        fixed = []
        for e in ev2:
            m = e.midi
            while m > hi2:
                m -= 12
            while m < lo2:
                m += 12
            ch = self.chord_at(e.beat + 1e-4)
            if ch is not None and int(m) % 12 not in ch.pcs and e.dur >= 1.0:
                near = min((x for x in range(int(m) - 2, int(m) + 3) if x % 12 in ch.pcs and lo2 <= x <= hi2),
                           key=lambda x: abs(x - m), default=m)
                m = near
            if int(round(m)) % 12 in self.avoid:
                m -= 1
            c = copy.deepcopy(e)
            c.midi = m
            fixed.append(c)
        self._place_voice(vid2, fixed)
        self.add(inst2, fixed, voice=vid2)
        it = line.it if isinstance(line, Line) else line
        en = line.en if isinstance(line, Line) else ""
        v1 = VOICES[sp1][1]
        self.show(f"{v1}+{vid2}", evs1, it, en, style="duet")
        self.meta["singing"].append({"voice": vid2, "b0": min(e.beat for e in fixed), "b1": max(e.end for e in fixed)})
        return evs1, fixed

    def chorus(self, line, model=None, store=None, role="open", style="chorus", accomp="pad", dyn=0.55,
               disp="chorus", contour="arch", sop_range=None, prog=None, bars=None, use_tune=True, **kw):
        """An SATB line: the soprano part composed (or the film's tune), alto/tenor/bass harmonised."""
        it = line.it if isinstance(line, Line) else line
        en = line.en if isinstance(line, Line) else ""
        latin = isinstance(line, Line) and line.latin
        syls = syllables(it, latin=latin)
        self.bar_align()
        bl = self.bl()
        num, den = self.meter_at()
        origin = self.cursor
        lo, hi = sop_range or (CHORUS["S"][1], CHORUS["S"][2])
        t = film_tune(it, "chorus") if (model is None and use_tune) else None
        cad = {"open": "half", "close": "full", "contrast": "half", "climax": "full"}.get(role, "full")
        if t is not None and abs(t.bar_len - bl) < 1e-6:
            rel0 = t.phase if t.phase < bl / 2 else t.phase - bl
            S = []
            for e in t.notes:
                c = copy.deepcopy(e)
                c.beat = origin + rel0 + e.beat
                S.append(c)
            nb = max(1, math.ceil((rel0 + t.length - 1e-6) / bl))
            p = tx.prog(" ".join(f"{s}:{d:g}" for _, d, s in t.chords), origin=origin + rel0) if t.chords else self.role_prog(role, nb)
        elif model is not None:
            m = self.models[model]
            nb = m["bars"]
            p = prog or [(origin + b, d, c) for b, d, c in m["chords"]]
            p = self._recadence(p, cad, nb, bl, origin) if role in ("close", "climax") else p
            self._set_harm(p)
            first = min(e.beat for e in m["evs"])
            rel = [Ev(e.beat - first, e.dur, e.midi, e.vel, e.art, e.lyric) for e in m["evs"]]
            S, nb2 = mel.retext(rel, m["syls"], syls, self.k, self.chord_at, lo, hi, bl, (num, den),
                                m["origin"] - first, cadence=cad, style=style, avoid=self.avoid, rng=self.rng,
                                origin=origin)
            nb = max(nb, nb2)
        else:
            nb = bars or max(1, math.ceil(len(syls) / {4.0: 5.5, 3.0: 4.5, 2.0: 3.0}.get(bl, 5.0)))
            p = prog or self.role_prog(role, nb)
            if isinstance(p, str):
                p = self.prog(p)
            self._set_harm(p)
            S, nb = mel.phrase(syls, self.k, self.chord_at, lo, hi, bl, (num, den), origin=origin, bars=nb,
                               style=style, contour=contour, cadence=cad, tess=(lo + 2, hi - 3),
                               avoid=self.avoid, rng=self.rng, orn=False)
        shift = self._fit_voice("chorus_s", S, bl)
        if shift:
            for e in S:
                e.beat += shift
            p = [(b + shift, d, c) for b, d, c in p]
            origin += shift
        self.last_note["chorus_s"] = max(S, key=lambda e: e.end)
        self._set_harm(p)
        for e in S:
            e.vel = orch.V(dyn, 1.0)
        A, T, B = harmonize(S, p, a_rng=(55, 72), t_rng=(48, 66), b_rng=(41, 59), avoid_pcs=set(self.avoid) or None)
        for inst, evs in (("ch_s", S), ("ch_a", A), ("ch_t", T), ("ch_b", B)):
            evs = [e for e in evs if int(round(e.midi)) % 12 not in self.avoid]
            for e in evs:
                e.tags["style"] = "latin" if latin else "chorus"
            self.add(inst, evs, voice="chorus")
        if accomp:
            self.add_parts(orch.accompany(accomp, p, dyn * 0.8, bar_len=bl, avoid=self.avoid, **kw))
        self.show("chorus", S, it, en, style=disp)
        self.meta["singing"].append({"voice": "chorus", "b0": min(e.beat for e in S), "b1": max(e.end for e in S)})
        if store:
            self.models[store] = {"evs": [copy.deepcopy(e) for e in S], "origin": origin, "bars": nb, "syls": syls,
                                  "chords": [(b - origin, d, c) for b, d, c in p], "bl": bl}
        self.cursor = origin + nb * bl
        return S

    def recit(self, items, chords=None, base=0.5, dyn=0.3, accomp="recit", gap=0.5, strike_end=True,
              styles=None, modulate=None):
        """Recitative for libretto items (Line and Direction). chords: a list of roman numerals cycled
        line by line ('I', 'vi', 'IV', 'V7' ...), or None for a gentle walk in the key."""
        walk = chords or (["i", "iv", "VI", "V7", "i", "iio6", "V7", "i"] if self.k.minor else
                          ["I", "vi", "IV", "V7", "I", "ii6", "V7", "I"])
        ci = 0
        prev_speaker = None
        for it in items:
            if isinstance(it, Direction):
                self.event("direction", text=it.en)
                continue
            if it.speaker not in VOICES:
                continue
            inst, vid, lo, hi, tlo, thi = VOICES[it.speaker]
            syls = syllables(it.it)
            if prev_speaker and prev_speaker != it.speaker:
                self.cursor += gap
            rn = walk[ci % len(walk)]
            ci += 1
            ch = Chord(roman(rn, self.k)) if not rn.startswith("@") else Chord(rn[1:])
            start = self.last_note.get(vid).midi if self.last_note.get(vid) is not None else None
            # the chord is in place while the line is spoken
            evs, length = mel.recit(syls, self.k, lambda b: ch, lo, hi, origin=self.cursor, base=base,
                                    start=start, avoid=self.avoid, rng=self.rng, tess=(tlo, thi))
            p = self._sanitise([(self.cursor, max(length, 1.0), ch)])
            self._set_harm(p)
            if accomp:
                self.add_parts(orch.accompany(accomp, p, dyn, bar_len=self.bl(), avoid=self.avoid))
            for e in evs:
                e.tags["style"] = "parlato"
                e.vel = orch.V(dyn + 0.2, 1.0)
            evs = [e for e in evs if int(round(e.midi)) % 12 not in self.avoid] if self.avoid else evs
            self._place_voice(vid, evs)
            self.add(inst, evs, voice=vid)
            self.show(vid, evs, it.it, it.en, style="parlato")
            self.meta["singing"].append({"voice": vid, "b0": self.cursor, "b1": self.cursor + length})
            self.cursor += length
            prev_speaker = it.speaker
        if strike_end:
            ch = Chord(roman("V7", self.k))
            tonic = Chord(roman("i" if self.k.minor else "I", self.k))
            self.add_parts(orch.strike(self.cursor, ch, dyn + 0.15, self.avoid, dur=0.5))
            self.add_parts(orch.strike(self.cursor + 1.0, tonic, dyn + 0.2, self.avoid, dur=0.8))
            self._set_harm([(self.cursor, 1.0, ch), (self.cursor + 1.0, 1.0, tonic)])
            self.cursor += 2.0
        return self

    def island(self, film_section, b0, b1, keep_vocals=True, show=True):
        """Place a passage of the film score here, verbatim (tempo and metre included)."""
        isl = film_island(film_section, b0, b1, keep_vocals=keep_vocals)
        self.bar_align()
        origin = self.cursor
        for inst, voice, evs, tags in isl.parts:
            for e in evs:
                e.beat += origin
            if self.avoid:
                evs = [e for e in evs if int(round(e.midi)) % 12 not in self.avoid]
            self.add(inst, evs, voice=voice, **tags)
            if inst in ("sop", "mez", "ten", "bar", "bbar") and evs:
                self.last_note[voice] = max(evs, key=lambda e: e.end)
                self.meta["singing"].append({"voice": voice, "b0": min(e.beat for e in evs), "b1": max(e.end for e in evs)})
        if show:
            for ll, evs in isl.lines:
                for e in evs:
                    e.beat += origin
                self.lines.append((ll, evs))
        self.segs = [s for s in self.segs if s[0] < origin - 1e-9]
        for s in isl.tempo:
            self.segs.append((origin + s[0],) + tuple(s[1:]))
        self.meters = [m for m in self.meters if m[0] < origin - 1e-9]
        for m in isl.meters:
            self.meters.append((origin + m[0], m[1], m[2]))
        for k, v in isl.cues.items():
            self.cues["film_" + k] = origin + v
        self.cursor = origin + isl.length
        return isl

    def pause(self, seconds):
        """A held silence (a general pause)."""
        self.cursor += self.seconds(seconds)
        return self

    # ------------------------------------------------------------------ finish
    def section(self, start: float) -> Section:
        segs = sorted(self.segs, key=lambda s: s[0])
        # performance tempo: the slow music taken broadly, as Romantic opera is performed
        segs = [(x[0], perf_tempo(x[1])) + tuple(x[2:]) for x in segs]
        clean = []
        for s in segs:
            if clean and abs(clean[-1][0] - s[0]) < 1e-9:
                clean[-1] = s
            else:
                clean.append(s)
        tm = TempoMap(clean)
        end_beat = self.cursor
        length = tm.time(end_beat)
        meters = sorted(self.meters, key=lambda m: m[0])
        sec = Section(self.key, self.title, start, length, tm, meters=meters)
        for inst, voice, evs, tags in self.parts:
            evs = [e for e in evs if e.beat < end_beat - 1e-6]
            if evs:
                sec.add(inst, evs, voice=voice, **tags)
        for ll, evs in self.lines:
            sec.lines.append((ll, [e for e in evs if e.beat < end_beat]))
        sec.texts = list(self.texts)
        for k, v in self.cues.items():
            sec.cue(k, v)
        meta = dict(self.meta)
        meta["singing"] = [{"voice": s["voice"], "t0": start + tm.time(max(0, s["b0"])),
                            "t1": start + tm.time(max(0, s["b1"]))} for s in self.meta["singing"]]
        meta["events"] = [dict(e, t=start + tm.time(max(0, e["beat"]))) for e in self.meta["events"]]
        sec.meta = meta
        return sec


PERF = {"slow": 0.78, "moderate": 0.9}


def perf_tempo(bpm):
    if bpm <= 72:
        return bpm * PERF["slow"]
    if bpm <= 100:
        return bpm * PERF["moderate"]
    return bpm


def _transpose_sym(sym, semis):
    from .harmony import SHARP, FLAT, PC
    import re as _re
    m = _re.match(r"^([A-G](?:#|b)?)(.*?)(?:/([A-G](?:#|b)?))?$", sym)
    root, qual, bass = m.groups()
    r = FLAT[(PC[root] + semis) % 12]
    out = r + qual
    if bass:
        out += "/" + FLAT[(PC[bass] + semis) % 12]
    return out
