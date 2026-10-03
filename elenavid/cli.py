"""ElenaVid: an opera made entirely in code.

usage: elenavid COMMAND [--edition film|full] [options]

commands:
  score      compose the score and write the MIDI file and the timeline
  audio      render and master the five sound tiers         (--workers=N for the full opera)
  video      render the picture and mux the master audio    (--encoder=auto|nvenc|x264, --png=t1,t2,...)
  build      score, then audio, then video
  encoder    which H.264 encoder this machine would use, and why
  qa TOOL    quality checks; TOOL is one of:
               delivery, contact-sheet, qc-sheet, compare-frames, timeline, events, prosody, levels,
               environment
  version    print the version

--edition film  the ten-minute film (default; outputs in output/)
--edition full  the complete two-hour opera (outputs in output/full/)

examples:
  elenavid build --edition film
  elenavid video --edition full --encoder=x264 --jobs=1
  elenavid video --png=495,520,560
  elenavid qa delivery --edition full
"""
from __future__ import annotations

import os
import sys

QA_TOOLS = {"delivery": "delivery", "contact-sheet": "contact_sheet", "qc-sheet": "qc_sheet",
            "compare-frames": "compare_frames", "timeline": "timeline", "events": "events", "prosody": "prosody",
            "levels": "levels", "environment": "environment"}


def _split_edition(args):
    """Take --edition film|full out of the arguments (both '--edition=full' and '--edition full')."""
    edition, rest, it = None, [], iter(args)
    for a in it:
        if a.startswith("--edition="):
            edition = a.split("=", 1)[1]
        elif a == "--edition":
            edition = next(it, None)
        else:
            rest.append(a)
    return edition, rest


def _score(edition):
    if edition == "full":
        from .full import build
        return build.main([])
    from .compose import build_score
    return build_score.main() or 0


def _audio(edition, rest):
    if edition == "full":
        from .audio import mix_full
        return mix_full.main(rest)
    from .audio import mix
    mix.render()
    return 0


def _video(edition, rest):
    if edition == "full" and not any(a.startswith("--png") for a in rest) and not any(
            not a.startswith("--") for a in rest):
        from .video import render_full
        return render_full.main(rest)
    from .video import render
    if not any(a.startswith("--png") for a in rest) and not any(not a.startswith("--") for a in rest):
        # the whole film, with its master audio, under its delivered name
        rest = ["0", "600", *rest]
        if "--audio" not in rest and "--no-audio" not in rest:
            rest.append("--audio")
        if not any(a.startswith("--out") for a in rest):
            rest.append("--out=elena_opera.mp4")
    return render.main([a for a in rest if a != "--no-audio"])


def _encoder(edition):
    from .video import encode
    kind = encode.choose()
    print(encode.reason(kind))
    print("ffmpeg video options:", " ".join(encode.video_args(kind, encode.quality(edition))))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if argv[0] in ("-V", "--version", "version"):
        from . import __version__
        print(f"ElenaVid {__version__}")
        return 0
    cmd, rest = argv[0], argv[1:]
    edition, rest = _split_edition(rest)
    if edition:
        if edition not in ("film", "full"):
            print(f"--edition must be film or full, not {edition!r}")
            return 2
        os.environ["ELENA_EDITION"] = edition       # before anything imports elenavid.config
    edition = os.environ.get("ELENA_EDITION", "film").strip().lower()
    if cmd == "score":
        return _score(edition)
    if cmd == "audio":
        return _audio(edition, rest)
    if cmd == "video":
        return _video(edition, rest)
    if cmd == "build":
        for step in (lambda: _score(edition), lambda: _audio(edition, []), lambda: _video(edition, rest)):
            code = step()
            if code:
                return code
        return 0
    if cmd == "encoder":
        return _encoder(edition)
    if cmd == "qa":
        if not rest or rest[0] not in QA_TOOLS:
            print("usage: elenavid qa TOOL [--edition film|full]\n  TOOL: " + ", ".join(QA_TOOLS))
            return 2
        import importlib
        mod = importlib.import_module(f"elenavid.qa.{QA_TOOLS[rest[0]]}")
        return mod.main(rest[1:])
    print(f"unknown command {cmd!r}\n")
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
