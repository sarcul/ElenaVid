"""Global constants shared by the score, audio and video pipelines.

Two editions share the code:
    film  the ten-minute motion-graphics film (the default; its outputs live in output/)
    full  the complete opera, about two hours (outputs in output/full/)

Environment variables:
    ELENA_EDITION   film (default) or full
    ELENA_ROOT      the project folder holding opera/ and output/ (default: the repository, or the
                    current folder if it holds opera/01_libretto.md)
    ELENA_CACHE     where the full opera's render caches go (default: the user's cache folder)
    ELENA_ENCODER   auto (default), nvenc or x264: see elenavid/video/encode.py
"""
import json
import os
import sys
from pathlib import Path

EDITION = os.environ.get("ELENA_EDITION", "film").strip().lower()
if EDITION not in ("film", "full"):
    raise ValueError(f"ELENA_EDITION must be 'film' or 'full', not {EDITION!r}")


def _root() -> Path:
    """The project folder: the libretto is read from it and the outputs are written under it."""
    if os.environ.get("ELENA_ROOT"):
        return Path(os.environ["ELENA_ROOT"]).expanduser().resolve()
    repo = Path(__file__).resolve().parent.parent
    if (repo / "opera" / "01_libretto.md").exists():
        return repo
    cwd = Path.cwd()
    if (cwd / "opera" / "01_libretto.md").exists():
        return cwd
    return repo


def _user_cache() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches"
    return Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))


ROOT = _root()
OUT = ROOT / "output" if EDITION == "film" else ROOT / "output" / "full"
AUDIO_OUT = OUT / "audio"
MIDI_OUT = OUT / "midi"
QC_OUT = OUT / "frames_qc"
TIMELINE_JSON = OUT / "timeline.json"

# Render caches are large (gigabytes per hour of music). The film keeps its cache where it always
# was; the full opera's cache lives outside the project folder unless ELENA_CACHE says otherwise.
if EDITION == "film":
    CACHE_DIR = AUDIO_OUT / "cache"
elif os.environ.get("ELENA_CACHE"):
    CACHE_DIR = Path(os.environ["ELENA_CACHE"]).expanduser()
else:
    CACHE_DIR = _user_cache() / "elena_opera" / "cache" / "full"

SR = 48000            # audio sample rate
FPS = 30              # video frame rate
W, H = 1920, 1080     # 16:9


def _full_duration() -> float:
    """The full opera's length is whatever the composed score says it is."""
    try:
        data = json.loads(TIMELINE_JSON.read_text(encoding="utf-8"))
        return float(max(s["end"] for s in data["sections"]))
    except (OSError, ValueError, KeyError):
        return 7200.0


DURATION = 600.0 if EDITION == "film" else _full_duration()   # the film is exactly ten minutes

A4 = 440.0            # Tommaso's pitch, and the orchestra's tuning note

for _p in (OUT, AUDIO_OUT, MIDI_OUT, QC_OUT, CACHE_DIR):
    _p.mkdir(parents=True, exist_ok=True)
