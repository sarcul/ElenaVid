"""Per-frame queries over the score timeline and the rendered audio envelopes."""
from __future__ import annotations

import bisect
import json
import math

import numpy as np

from ..config import TIMELINE_JSON, AUDIO_OUT, FPS
from ..audio.voice import phonemise

OPEN = {"a": 1.0, "o": 0.8, "e": 0.68, "u": 0.5, "i": 0.42}


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease_io(x):
    x = min(1.0, max(0.0, x))
    return 0.5 - 0.5 * math.cos(math.pi * x)


def lerp(a, b, x):
    return a + (b - a) * x


def lerp3(a, b, x):
    return tuple(lerp(ai, bi, x) for ai, bi in zip(a, b))


class Timeline:
    def __init__(self):
        d = json.loads(TIMELINE_JSON.read_text(encoding="utf-8"))
        self.notes = d["notes"]
        self.lines = d["lines"]
        self.cues = d["cues"]
        self.beats = d["beats"]
        self.sections = d["sections"]
        self.meta = d.get("meta", {})          # the full opera's per-section staging data (absent in the film)
        self.beat_t = [b["t"] for b in self.beats]
        env_path = AUDIO_OUT / "envelopes.json"
        self.env = json.loads(env_path.read_text()) if env_path.exists() else None
        # per-voice note lists, sorted
        self.by_voice = {}
        for n in self.notes:
            self.by_voice.setdefault((n["inst"], n["voice"]), []).append(n)
        for v in self.by_voice.values():
            v.sort(key=lambda n: n["t"])
        self.tommaso = sorted([n for n in self.notes if n["tags"].get("tommaso") or
                               (n["inst"] == "ob" and n["tags"].get("tuning") and n["midi"] == 69)],
                              key=lambda n: n["t"])
        self.tuning = [n for n in self.notes if n["tags"].get("tuning") and n["inst"] != "ob"
                       and n["inst"] in ("vn1", "vn2", "va", "vc", "cb")]
        self.motif = {}
        for n in self.notes:
            m = n["tags"].get("motif")
            if m:
                self.motif.setdefault(m, []).append(n)
        for v in self.motif.values():
            v.sort(key=lambda n: n["t"])
        if self.env:
            self.env_e = np.array(self.env["elena"])
            self.env_e = self.env_e / (np.percentile(self.env_e[self.env_e > 1e-5], 95) + 1e-9)
            self.env_s = np.array(self.env["score"])
            self.env_s = self.env_s / (np.percentile(self.env_s[self.env_s > 1e-5], 95) + 1e-9)
        else:
            self.env_e = self.env_s = None

    def c(self, name):
        return self.cues[name]

    # ------------------------------------------------------------- audio-driven values
    def voice_env(self, t):
        if self.env_e is None:
            n = self.note_at("sop", "elena", t)
            return 0.0 if n is None else 0.6 * n["vel"] + 0.2
        i = int(t * FPS)
        if 0 <= i < len(self.env_e):
            return float(np.clip(self.env_e[i], 0, 1.5))
        return 0.0

    def score_env(self, t):
        if self.env_s is None:
            return 0.5
        i = int(t * FPS)
        return float(np.clip(self.env_s[i], 0, 1.5)) if 0 <= i < len(self.env_s) else 0.0

    def note_at(self, inst, voice, t):
        ns = self.by_voice.get((inst, voice), [])
        lo, hi = 0, len(ns)
        while lo < hi:
            mid = (lo + hi) // 2
            if ns[mid]["t"] <= t:
                lo = mid + 1
            else:
                hi = mid
        k = lo - 1
        if k >= 0 and ns[k]["t"] <= t < ns[k]["t"] + ns[k]["dur"]:
            return ns[k]
        return None

    def jaw(self, t):
        """Mouth opening for Elena from the vowel she is singing and the voice envelope."""
        n = self.note_at("sop", "elena", t)
        if n is None:
            return 0.06
        lyr = n["lyric"] or "a"
        if lyr == "_":
            ns = self.by_voice[("sop", "elena")]
            i = ns.index(n)
            while i > 0 and (ns[i]["lyric"] in (None, "_")):
                i -= 1
            lyr = ns[i]["lyric"] or "a"
        _, vs, _ = phonemise(lyr)
        o = OPEN.get(vs[0][0], 0.7)
        return 0.08 + 0.9 * o * min(1.0, 0.4 + 0.7 * self.voice_env(t))

    # ------------------------------------------------------------- the conductor
    def baton(self, t):
        k = bisect.bisect_right(self.beat_t, t) - 1
        if k < 0 or k + 1 >= len(self.beats):
            return (0.0, 0.0, 0.0), 0.0, 0.0
        b, nb = self.beats[k], self.beats[k + 1]
        ph = (t - b["t"]) / max(1e-3, nb["t"] - b["t"])
        n = b["beats_in_bar"]
        i = b["beat_in_bar"]
        pats = {4: [(0, -1), (-0.8, -0.6), (0.9, -0.6), (0.1, 0.7)],
                3: [(0, -1), (0.9, -0.6), (0.1, 0.7)],
                2: [(0, -1), (0.05, 0.7)],
                1: [(0, -1)]}
        pat = pats.get(n, pats[2] if n % 2 == 0 else pats[3])
        a = pat[i % len(pat)]
        bb = pat[(i + 1) % len(pat)]
        # ictus then rebound: the hand bounces off the beat point
        s = ease_io(ph)
        x = lerp(a[0], bb[0], s)
        y = lerp(a[1], bb[1], s) + 0.35 * math.sin(math.pi * ph) * (1 - abs(a[1] - bb[1]) * 0.3)
        return (0.17 * x, 0.15 * y, 0.04 * math.sin(math.pi * ph)), ph, i

    # ------------------------------------------------------------- lines on screen
    def active_lines(self, t, pre=0.35, post=0.9):
        out = []
        for i, ln in enumerate(self.lines):
            if ln["start"] - pre <= t <= ln["end"] + post:
                out.append((i, ln))
        return out

    def tone_level(self, t):
        """Tommaso's tone (and the tuning A): envelope 0..1."""
        lvl = 0.0
        for n in self.tommaso:
            if n["t"] - 0.05 <= t <= n["t"] + n["dur"] + 0.6:
                a = min(1.0, (t - n["t"]) / 0.3) if t >= n["t"] else 0.0
                end = n["t"] + n["dur"]
                if n["tags"].get("fade_end"):
                    a *= max(0.0, 1.0 - (t - n["t"]) / n["dur"]) ** 0.7
                if t > end:
                    a *= max(0.0, 1.0 - (t - end) / 0.6)
                lvl = max(lvl, a * min(1.0, 0.4 + n["vel"] * 2.2))
        return lvl
