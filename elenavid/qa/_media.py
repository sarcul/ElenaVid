"""Shared helpers for the QA tools: the edition's files, ffmpeg probes and decoders, sheet fonts."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from ..config import EDITION, OUT, AUDIO_OUT, TIMELINE_JSON, SR
from ..video.encode import require_ffmpeg  # noqa: F401  (re-exported for the tools)

DELIVERED = {"film": "elena_opera.mp4", "full": "elena_opera_full.mp4"}
MASTER = {"film": "elena_master.wav", "full": "elena_full_master.wav"}

# the required shot's three moments: (label, cue, seconds after the cue)
REQUIRED_SHOT = {
    "film": [("dolly: past the conductor", "s11.sing", 12.0), ("the house, the dome", "s11.wide", 15.0),
             ("close-up at the climax", "s11.climax", 0.0)],
    "full": [("dolly: past the conductor", "N22.sing", 18.0), ("the house, the dome", "N22.wide", 12.0),
             ("close-up at the climax", "N22.climax", 0.0)],
}

# story moments where a sound and a change of picture coincide by design: (cue, what to expect)
ANCHORS = {
    "film": [("s03.blow", "the blow: slap and sub hit; the picture cuts to the cracking frame"),
             ("s05.wake", "waking: gasp and sub hit; a white flash"),
             ("s08.nives", "Nives: the door slam; the door bursting open"),
             ("s11.curtain", "the final curtain")],
    "full": [("N8.blow", "the blow: slap and sub hit; the picture cuts to the cracking frame"),
             ("N10.wake", "waking: gasp and sub hit; a white flash"),
             ("R4.nives", "Nives: the door slam; the door bursting open"),
             ("N22.curtain", "the final curtain")],
}


def delivered() -> Path:
    return OUT / DELIVERED[EDITION]


def master() -> Path:
    return AUDIO_OUT / MASTER[EDITION]


def qa_dir() -> Path:
    d = OUT / "qa"
    d.mkdir(parents=True, exist_ok=True)
    return d


def timeline() -> dict:
    return json.loads(TIMELINE_JSON.read_text(encoding="utf-8"))


def length(tl: dict) -> float:
    return max(s["end"] for s in tl["sections"])


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,nb_read_packets,duration,"
                        "sample_rate,channels,bit_rate:stream_tags=encoder:format=duration,size,bit_rate",
                        "-of", "json", str(path)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def ebur128(path: Path) -> dict:
    """Integrated loudness (LUFS), loudness range (LU) and true peak (dBTP) of a file's audio."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a",
                        "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    out = {}
    for line in tail.splitlines():
        s = line.strip()
        for key, tag in (("I", "I:"), ("LRA", "LRA:"), ("TP", "Peak:")):
            if s.startswith(tag):
                out[key] = float(s.split()[1])
    return out


def decode_audio(path: Path, t0: float, dur: float, sr: int = SR) -> np.ndarray:
    """Mono float32 audio from any file ffmpeg reads (the MP4's AAC or the master WAV)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-t", f"{dur:.4f}", "-i", str(path),
                          "-map", "0:a", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def decode_gray(path: Path, t0: float, dur: float, w: int = 160, h: int = 90) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-t", f"{dur:.4f}", "-i", str(path),
                          "-map", "0:v", "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, h, w).astype(np.float32)


def still(path: Path, t: float, w: int, h: int) -> Image.Image | None:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    return Image.frombytes("RGB", (w, h), raw) if len(raw) == w * h * 3 else None


def lag(a: np.ndarray, b: np.ndarray, max_lag: int = 2400) -> int:
    """The offset of a against b in samples (positive: a is late), by cross-correlation."""
    n = min(len(a), len(b))
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    cc = np.fft.irfft(np.fft.rfft(a, 2 * n) * np.conj(np.fft.rfft(b, 2 * n)))
    return int(np.argmax(np.concatenate([cc[-max_lag:], cc[:max_lag]]))) - max_lag


def sheet_font(size: int):
    from ..video.text import find_font, font
    return font(find_font("ui"), size)


def hms(t: float) -> str:
    m, s = divmod(t, 60)
    h, m = divmod(m, 60)
    return f"{int(h)}:{int(m):02d}:{int(s):02d}" if h else f"{int(m)}:{s:04.1f}"


def options(argv) -> dict:
    """--key=value options (and bare --flags as '1')."""
    out = {}
    for a in argv or []:
        if a.startswith("--"):
            k, _, v = a[2:].partition("=")
            out[k] = v if _ else "1"
    return out
