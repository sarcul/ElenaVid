"""Sanity checks on the score timeline that the sound and the picture both read.

    elenavid qa timeline [--edition film|full] [--cues]

Fails (exit status 1) if a note names an instrument no renderer knows (it would be silently dropped)
or starts before its own section. Reports notes ringing past their section, the sections with their
locations, singing time per voice, leitmotif tags, and with --cues every cue.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict

from ..audio import instruments as ins
from ..audio import voice
from ._media import hms, length, options, timeline


def main(argv=None):
    o = options(argv)
    tl = timeline()
    notes, secs = tl["notes"], {s["key"]: s for s in tl["sections"]}
    meta = tl.get("meta", {})
    known = set(ins.SECTIONS) | set(ins.WINDS) | set(ins.BRASS) | set(ins.PERC_PAN) | set(voice.VOICE_TYPES)
    failures = []
    used = Counter(n["inst"] for n in notes)
    unknown = sorted(set(used) - known)
    if unknown:
        failures.append(f"instruments with no renderer: {unknown}")
    early = Counter(n["section"] for n in notes if n["t"] < secs[n["section"]]["start"] - 1e-6)
    if early:
        failures.append(f"notes starting before their section: {dict(early)}")
    late = defaultdict(float)
    for n in notes:
        late[n["section"]] = max(late[n["section"]], n["t"] + n["dur"] - secs[n["section"]]["end"])
    print(f"{len(tl['sections'])} sections, {len(notes)} notes, {len(tl['lines'])} lines, {len(tl['cues'])} cues, "
          f"{hms(length(tl))}")
    print("instruments:", ", ".join(f"{k} {v}" for k, v in sorted(used.items())))
    ringing = {k: round(v, 2) for k, v in late.items() if v > 0.05}
    if ringing:
        print("notes ringing past their section's end (s):", ringing)
    sung = defaultdict(float)
    for s in tl["sections"]:
        m = meta.get(s["key"], {})
        for x in m.get("singing", []):
            sung[x["voice"]] += x["t1"] - x["t0"]
        loc = m.get("location", "")
        print(f"  {s['key']:4s} {hms(s['start']):>8s}  {(s['end'] - s['start']) / 60:5.2f} min  {loc:20s} {s['title']}")
    if sung:
        print("singing (s):", {k: round(v) for k, v in sorted(sung.items(), key=lambda kv: -kv[1])})
    motifs = Counter(n["tags"].get("motif") for n in notes if n["tags"].get("motif"))
    if motifs:
        print("leitmotif notes:", dict(motifs))
    if "cues" in o:
        by = defaultdict(list)
        for k, v in sorted(tl["cues"].items(), key=lambda kv: kv[1]):
            sec, name = k.split(".", 1)
            by[sec].append(f"{name}@{v:.1f}")
        for s in tl["sections"]:
            print(f"  {s['key']:4s}", " ".join(by.get(s["key"], [])))
    if failures:
        print("\nFAILED:\n  " + "\n  ".join(failures))
        return 1
    print("\ntimeline OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
