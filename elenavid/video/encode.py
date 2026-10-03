"""Which H.264 encoder to use: NVIDIA's NVENC when this machine can run it, otherwise x264 in software.

An ffmpeg build lists h264_nvenc whether or not an NVIDIA GPU is present, so the check encodes a
fraction of a second of black with it; only a machine with a working NVIDIA driver succeeds. If
libx264 is missing too (some LGPL builds), libopenh264 is the last resort.

Override with ELENA_ENCODER=nvenc|x264|auto, or --encoder= on the renderers.
"""
from __future__ import annotations

import functools
import os
import shutil
import subprocess

# Per edition: the film's encode is near-transparent; two hours at that rate would be 21 GB, so the
# full opera's is lighter. NVENC's cq and x264's crf are roughly comparable a step or two apart.
QUALITY = {
    "film": {"cq": "17", "crf": "16", "rate": "24M", "maxrate": "48M", "preset": "medium"},
    "full": {"cq": "24", "crf": "21", "rate": "7M", "maxrate": "14M", "preset": "medium"},
}


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


@functools.lru_cache(maxsize=None)
def encoders() -> frozenset:
    """Names of the video encoders this ffmpeg build offers."""
    if not ffmpeg_path():
        return frozenset()
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True,
                             timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return frozenset()
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("V"):
            names.add(parts[1])
    return frozenset(names)


@functools.lru_cache(maxsize=None)
def nvenc_available() -> bool:
    """True if NVENC can actually encode here (an NVIDIA GPU, its driver and an NVENC-enabled ffmpeg)."""
    if "h264_nvenc" not in encoders():
        return False
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                            "-i", "color=c=black:s=256x144:r=30:d=0.2", "-c:v", "h264_nvenc", "-f", "null", "-"],
                           capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def choose(preference: str | None = None) -> str:
    """'nvenc', 'x264' or 'openh264'. preference (or ELENA_ENCODER): auto, nvenc, x264."""
    pref = (preference or os.environ.get("ELENA_ENCODER") or "auto").strip().lower()
    if pref in ("nvenc", "h264_nvenc", "gpu"):
        return "nvenc"
    if pref in ("x264", "libx264", "software", "cpu"):
        return "x264"
    if pref != "auto":
        raise ValueError(f"unknown encoder {preference!r}: use auto, nvenc or x264")
    if nvenc_available():
        return "nvenc"
    if "libx264" in encoders() or not encoders():
        return "x264"
    return "openh264" if "libopenh264" in encoders() else "x264"


def reason(kind: str) -> str:
    if kind == "nvenc":
        return "NVIDIA NVENC (hardware)"
    if not ffmpeg_path():
        return "ffmpeg not found on the path"
    if kind == "x264":
        return "x264 in software (no usable NVIDIA GPU)" if not nvenc_available() else "x264 in software (as requested)"
    return "OpenH264 in software (no NVENC, and this ffmpeg has no libx264)"


def quality(edition: str, opts: dict | None = None) -> dict:
    """The edition's defaults, overridden by renderer options (--cq=, --crf=, --rate=, --maxrate=, --preset=)."""
    q = dict(QUALITY[edition])
    for k in q:
        v = (opts or {}).get(f"--{k}")
        if v not in (None, True):
            q[k] = str(v)
    return q


def video_args(kind: str, q: dict, gop: int | None = None) -> list:
    """ffmpeg output arguments for the video stream (yuv420p, High profile)."""
    bufsize = f"{2 * int(str(q['maxrate']).rstrip('Mm'))}M"
    if kind == "nvenc":
        args = ["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", q["cq"], "-b:v", q["rate"],
                "-maxrate", q["maxrate"], "-bufsize", bufsize, "-profile:v", "high", "-pix_fmt", "yuv420p"]
    elif kind == "x264":
        args = ["-c:v", "libx264", "-preset", q["preset"], "-crf", q["crf"], "-maxrate", q["maxrate"],
                "-bufsize", bufsize, "-profile:v", "high", "-pix_fmt", "yuv420p"]
    elif kind == "openh264":
        args = ["-c:v", "libopenh264", "-b:v", q["rate"], "-maxrate", q["maxrate"], "-pix_fmt", "yuv420p"]
    else:
        raise ValueError(kind)
    return args + (["-g", str(gop)] if gop else [])


def require_ffmpeg():
    if not ffmpeg_path():
        raise SystemExit("ffmpeg was not found on the path. Install it (https://ffmpeg.org) and try again.")
