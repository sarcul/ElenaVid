"""Smoke test of the cue sheet: call every sound generator it uses, with its real arguments (durations
capped at two seconds), so a misspelt argument fails here in a second rather than an hour into a render.

    elenavid qa events [--edition film|full]
"""
from __future__ import annotations

import sys
import time
from collections import Counter

from ..config import EDITION
from ._media import timeline


def main(argv=None):
    from ..audio import mix as M
    tl = timeline()
    if EDITION == "full":
        from ..audio.sounddesign_full import cue_sheet_full
        events = cue_sheet_full(tl)
    else:
        from ..audio.sounddesign import cue_sheet
        events = cue_sheet(tl["cues"])
    print(f"{len(events)} events:", dict(Counter(e["tier"] for e in events)))
    print("generators:", ", ".join(f"{g} {n}" for g, n in Counter(e["gen"] for e in events).most_common()))
    T = max(s["end"] for s in tl["sections"])
    outside = [(e["gen"], round(e["t"], 1)) for e in events if e["t"] < -10.0 or e["t"] > T + 10.0]
    seen, bad = set(), []
    t0 = time.time()
    for e in events:
        if e["gen"] in ("ghost", "reverse_swell"):      # built from the rendered score, not a generator
            continue
        args = {k: v for k, v in e["args"].items() if k not in M.POST_KEYS}
        sig = (e["gen"], tuple(sorted(args)))
        if sig in seen:
            continue
        seen.add(sig)
        if "dur" in args:
            args["dur"] = min(args["dur"], 2.0)
        if args.get("depart_at") is not None:
            args["depart_at"] = min(args["depart_at"], 1.0)
        try:
            y = M.GEN[e["gen"]](**args)
            if not hasattr(y, "shape") or y.size == 0:
                bad.append((sig, "no audio returned"))
        except Exception as ex:                      # report every failure, not just the first
            bad.append((sig, repr(ex)))
    print(f"{len(seen)} distinct calls in {time.time() - t0:.1f} s")
    if outside:
        print("events far outside the programme:", outside)
    for sig, err in bad:
        print("FAILED", sig, err)
    return 1 if bad or outside else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
