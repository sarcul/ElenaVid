"""Assemble the full opera, validate it, and export MIDI and the shared timeline (output/full/).

Run with the full edition selected:
    ELENA_EDITION=full python -m elenavid.full.build
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict

from ..config import EDITION, MIDI_OUT, TIMELINE_JSON
from ..score_model import Score
from .forms import Num

VOICE_RANGES = {
    "sop": (58, 86), "mez": (55, 81), "ten": (47, 72), "bar": (41, 67), "bbar": (38, 65),
    "treble": (60, 79), "ch_s": (58, 83), "ch_a": (52, 74), "ch_t": (46, 68), "ch_b": (38, 62),
}
SOLO = ("sop", "mez", "ten", "bar", "bbar")
NO_A_FROM = "IM2"          # after the Requiem (N19) the pitch class A never sounds again


def entracte(key, title, act_after, seconds=30.0):
    """Between acts: the curtain is down, the house applauds, the lights dim again."""
    n = Num(key, title, "C", 120, (4, 4), location="house_intermission", act=act_after)
    n.cue("applause", 0.5)
    n.pause(seconds)
    n.cue("hush", n.cursor - n.seconds(8.0))
    return n


def finale_calls():
    """After the final curtain: silence, then the house applauds; the title."""
    n = Num("F0", "Fine", "C", 120, (4, 4), location="house_finale", act=3)
    n.cue("silence", 0.0)
    n.pause(4.0)
    n.cue("applause")
    n.pause(22.0)
    n.cue("title_in", n.cursor - n.seconds(16.0))
    return n


def acts():
    from . import act1, act2, act3
    seq = list(act1.ACT1)
    seq.append(lambda: entracte("E1", "Intervallo", 2))
    seq += act2.ACT2
    seq.append(lambda: entracte("E2", "Intervallo", 3))
    seq += act3.ACT3
    seq.append(finale_calls)
    return seq


def build(seq=None) -> Score:
    sc = Score()
    t = 0.0
    for fn in (seq or acts()):
        num = fn()
        sec = num.section(t)
        sc.add(sec)
        t += sec.length
    return sc


def validate(sc: Score):
    problems = []
    notes = sc.notes()
    keys = [s.key for s in sc.sections]
    no_a = set(keys[keys.index(NO_A_FROM):]) if NO_A_FROM in keys else set()
    for n in notes:
        if n.section in no_a and int(round(n.midi)) % 12 == 9:
            problems.append(f"pitch A in {n.section} at {n.t:.2f}s ({n.inst}/{n.voice})")
        r = VOICE_RANGES.get(n.inst)
        if r and not (r[0] <= n.midi <= r[1]):
            problems.append(f"range: {n.inst}/{n.voice} midi {n.midi} at {n.t:.2f}s ({n.section})")
    by_voice = defaultdict(list)
    for n in notes:
        if n.inst in SOLO:
            by_voice[(n.inst, n.voice)].append(n)
    for k, ns in by_voice.items():
        ns.sort(key=lambda n: n.t)
        for a, b in zip(ns, ns[1:]):
            if b.t < a.end - 0.03:
                problems.append(f"overlap {k} at {a.t:.2f}s / {b.t:.2f}s ({a.section})")
    return problems


def export(sc: Score):
    notes = sc.notes()
    sc.write_midi(MIDI_OUT / "elena_full_score.mid")
    data = sc.to_json()
    data["edition"] = "full"
    data["meta"] = {s.key: getattr(s, "meta", {}) for s in sc.sections}
    data["notes"] = [
        {"t": n.t, "dur": n.dur, "midi": n.midi, "vel": n.vel, "inst": n.inst, "voice": n.voice,
         "section": n.section, "lyric": n.lyric, "art": n.art,
         "tags": {k: v for k, v in n.tags.items() if isinstance(v, (str, int, float, bool))}}
        for n in notes]
    TIMELINE_JSON.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def report(sc: Score):
    notes = sc.notes()
    per_sec = Counter(n.section for n in notes)
    act_len = defaultdict(float)
    for s in sc.sections:
        act = getattr(s, "meta", {}).get("act", 0)
        act_len[act] += s.length
        m, ss = divmod(s.start, 60)
        print(f"  {s.key:4s} {int(m):3d}:{ss:04.1f}  {s.length / 60:5.2f} min  notes {per_sec[s.key]:5d}  {s.title}")
    total = sum(s.length for s in sc.sections)
    print("  acts:", {k: f"{v / 60:.1f} min" for k, v in sorted(act_len.items())})
    print(f"  total {total / 60:.1f} min ({total:.0f} s), {len(notes)} notes, {len(sc.lines())} lines")


def main(argv=None):
    if EDITION != "full":
        print("set ELENA_EDITION=full to build the full opera (outputs go to output/full/)")
        return 2
    t0 = time.time()
    sc = build()
    report(sc)
    probs = validate(sc)
    if probs:
        print(f"\n{len(probs)} problem(s):")
        for p in probs[:80]:
            print("  -", p)
    export(sc)
    print(f"\nwrote {MIDI_OUT / 'elena_full_score.mid'} and {TIMELINE_JSON} in {time.time() - t0:.1f}s")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
