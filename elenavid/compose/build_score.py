"""Assemble the film score, validate it, export MIDI and the shared timeline."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

from ..config import MIDI_OUT, TIMELINE_JSON, DURATION
from ..score_model import Score
from . import act1, act2, act3
from .common import PLAN, NO_A

VOICE_RANGES = {  # comfortable written ranges, MIDI
    "sop": (58, 86), "mez": (55, 81), "ten": (47, 72), "bar": (41, 67), "bbar": (38, 65),
    "treble": (60, 79), "ch_s": (58, 83), "ch_a": (52, 74), "ch_t": (46, 68), "ch_b": (38, 62),
}


def build() -> Score:
    sc = Score()
    for f in (act1.s00, act1.s01, act1.s02, act1.s03, act2.s04, act2.s05, act2.s06,
              act3.s07, act3.s08, act3.s09, act3.s10, act3.s11):
        f(sc)
    return sc


def validate(sc: Score):
    problems = []
    # contiguity
    t = 0.0
    for s in sc.sections:
        if abs(s.start - t) > 1e-6:
            problems.append(f"{s.key} starts at {s.start}, expected {t}")
        t = s.start + s.length
    if abs(t - DURATION) > 1e-6:
        problems.append(f"total {t} != {DURATION}")
    notes = sc.notes()
    # the lost note: no A after the funeral
    for n in notes:
        if n.section in ("s10", "s11") and int(round(n.midi)) % 12 in NO_A:
            problems.append(f"pitch A in {n.section} at {n.t:.2f}s ({n.inst}/{n.voice})")
    # vocal ranges
    for n in notes:
        r = VOICE_RANGES.get(n.inst)
        if r and not (r[0] <= n.midi <= r[1]):
            problems.append(f"range: {n.inst}/{n.voice} midi {n.midi} at {n.t:.2f}s")
    # monophonic overlaps in solo voices
    by_voice = defaultdict(list)
    for n in notes:
        if n.inst in ("sop", "mez", "ten", "bar", "bbar"):
            by_voice[(n.inst, n.voice)].append(n)
    for k, ns in by_voice.items():
        ns.sort(key=lambda n: n.t)
        for a, b in zip(ns, ns[1:]):
            if b.t < a.end - 0.02:
                problems.append(f"overlap {k} at {a.t:.2f}s / {b.t:.2f}s")
    return problems


def main():
    sc = build()
    probs = validate(sc)
    notes = sc.notes()
    print(f"sections: {len(sc.sections)}   notes: {len(notes)}   lines: {len(sc.lines())}")
    per_inst = Counter(n.inst for n in notes)
    print("notes per instrument:", dict(sorted(per_inst.items())))
    for s in sc.sections:
        ns = [n for n in notes if n.section == s.key]
        last = max((n.end for n in ns), default=s.start)
        print(f"  {s.key} {s.start:6.1f}-{s.start + s.length:6.1f}s  notes {len(ns):5d}  "
              f"music ends {last:6.2f}s  {s.title}")
    if probs:
        print(f"\n{len(probs)} problem(s):")
        for p in probs[:60]:
            print("  -", p)
    sc.write_midi(MIDI_OUT / "elena_film_score.mid")
    data = sc.to_json()
    data["notes"] = [
        {"t": n.t, "dur": n.dur, "midi": n.midi, "vel": n.vel, "inst": n.inst, "voice": n.voice,
         "section": n.section, "lyric": n.lyric, "art": n.art,
         "tags": {k: v for k, v in n.tags.items()
                                                         if isinstance(v, (str, int, float, bool))}}
        for n in notes]
    TIMELINE_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {MIDI_OUT / 'elena_film_score.mid'} and {TIMELINE_JSON}")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
