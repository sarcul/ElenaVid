"""How well the full opera's music fits its words: the share of stressed syllables that fall on strong
beats, per section and overall, and the distribution of melodic intervals between sung notes.

    elenavid qa prosody [--acts=act1,act2,act3]

The full opera only. Builds the score in memory (about a minute; nothing is written).
"""
from __future__ import annotations

import importlib
import sys
from collections import Counter, defaultdict

from ..config import EDITION
from ._media import options


def main(argv=None):
    if EDITION != "full":
        print("the prosody check reads the full opera: use --edition full")
        return 2
    from ..full import build as B
    from ..full.melody import weight
    from ..full.prosody import syllables
    o = options(argv)
    seq = []
    for name in o.get("acts", "act1,act2,act3").split(","):
        seq += getattr(importlib.import_module(f"elenavid.full.{name}"), name.upper())
    sc = B.build(seq)
    iv, by_sec = Counter(), defaultdict(lambda: [0, 0])
    big = tot = strong = stressed = 0
    for s in sc.sections:
        for ll, evs in s.lines:
            sung = [e for e in evs if e.lyric and e.lyric != "_"]
            if not sung or ll.style == "parlato":
                continue
            sy = syllables(ll.it, latin=ll.style == "latin")
            if len(sy) != len(sung):
                continue
            for e, x in zip(sung, sy):
                if x.stress == 2:
                    num, den = s.meter_at(e.beat)
                    b0 = 0.0
                    for bb, _, _ in s.bars():
                        if bb <= e.beat + 1e-6:
                            b0 = bb
                    stressed += 1
                    by_sec[s.key][1] += 1
                    if weight(e.beat - b0, num * 4.0 / den, num, den) >= 2.0:
                        strong += 1
                        by_sec[s.key][0] += 1
            ps = [int(round(e.midi)) for e in evs if e.lyric]
            for a, b in zip(ps, ps[1:]):
                iv[abs(b - a)] += 1
                tot += 1
                big += abs(b - a) > 7
    print(f"stressed syllables on strong beats: {strong}/{stressed} = {100 * strong / max(1, stressed):.0f}%")
    print("per section:", ", ".join(f"{k} {100 * a / max(1, b):.0f}%" for k, (a, b) in by_sec.items()))
    print("intervals (semitones: share):", ", ".join(f"{k}: {100 * v / max(1, tot):.1f}%" for k, v in sorted(iv.items())))
    print(f"leaps wider than a fifth: {big}/{tot} = {100 * big / max(1, tot):.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
