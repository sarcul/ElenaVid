"""Checks on the delivered file: streams, loudness and true peak, the sound's sync with the master, the
picture and the sound at the story's anchor cues, and (full opera) the joins between render chunks.

    elenavid qa delivery [--edition film|full] [--file=path.mp4]

Exit status 1 if a hard check fails: the MP4's audio not sample-aligned with the master, integrated
loudness more than 1 LU from -16 LUFS, or true peak above -1 dBTP. The anchor and join figures are
reported for a person to judge: a designed cut can sit a fraction of a second before its sound.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from ..config import EDITION, FPS, SR
from ._media import (ANCHORS, decode_audio, decode_gray, delivered, ebur128, hms, lag, length, master, options,
                     probe, require_ffmpeg, timeline)

TARGET_LUFS, LUFS_TOL, MAX_TP = -16.0, 1.0, -1.0


def picture_change(path, t0, t1):
    """The time of the largest frame-to-frame change in [t0, t1)."""
    fr = decode_gray(path, t0, t1 - t0)
    if len(fr) < 2:
        return None
    dif = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    return t0 + (int(np.argmax(dif)) + 1) / FPS


def sharpest_transient(path, t0, t1):
    """The sharpest attack in [t0, t1): a click or slap stands out among sustained music this way."""
    x = decode_audio(path, t0, t1 - t0)
    if len(x) < 100:
        return None
    env = np.convolve(np.abs(np.diff(x)), np.ones(48) / 48, mode="same")
    return t0 + int(np.argmax(env)) / SR


def main(argv=None):
    require_ffmpeg()
    o = options(argv)
    mp4 = Path(o["file"]) if "file" in o else delivered()
    wav = master()
    if not mp4.exists():
        print(f"no delivered file at {mp4}")
        return 2
    failures = []
    info = probe(mp4)
    for s in info.get("streams", []):
        if s.get("codec_type") == "video":
            enc = (s.get("tags") or {}).get("encoder", "")
            print(f"video   {s['codec_name']} {s['width']}x{s['height']} {s['r_frame_rate']} {s.get('pix_fmt', '')}  "
                  f"{s.get('nb_read_packets')} frames  {float(s.get('duration', 0)):.3f} s  {enc}")
        elif s.get("codec_type") == "audio":
            print(f"audio   {s['codec_name']} {s['sample_rate']} Hz  {s['channels']} ch  "
                  f"{int(s.get('bit_rate', 0)) // 1000} kbit/s  {float(s.get('duration', 0)):.3f} s")
    f = info.get("format", {})
    print(f"file    {int(f.get('size', 0)) / 1e9:.2f} GB  {float(f.get('duration', 0)):.3f} s  "
          f"{int(f.get('bit_rate', 0)) / 1e6:.2f} Mbit/s")
    tl = timeline()
    T = length(tl)
    print(f"score   {T:.3f} s ({hms(T)})")

    L = ebur128(mp4)
    print(f"loudness {L.get('I')} LUFS integrated, range {L.get('LRA')} LU, true peak {L.get('TP')} dBTP")
    if "I" not in L or abs(L["I"] - TARGET_LUFS) > LUFS_TOL:
        failures.append(f"integrated loudness {L.get('I')} LUFS, target {TARGET_LUFS} +- {LUFS_TOL}")
    if "TP" not in L or L["TP"] > MAX_TP:
        failures.append(f"true peak {L.get('TP')} dBTP above {MAX_TP}")

    if wav.exists():
        for frac in (0.1, 0.5, 0.9):
            t = round(frac * T, 1)
            k = lag(decode_audio(mp4, t, 4.0), decode_audio(wav, t, 4.0))
            print(f"sync    at {hms(t):>8s}: the MP4's audio is {k:+d} samples ({k / SR * 1000:+.2f} ms) from the master")
            if abs(k) > 1:
                failures.append(f"audio offset of {k} samples at {t:.1f} s")
    else:
        print(f"sync    (no master at {wav}; skipped)")

    for cue, what in ANCHORS[EDITION]:
        t = tl["cues"].get(cue)
        if t is None:
            continue
        v = picture_change(mp4, t - 1.5, t + 1.5)
        a = sharpest_transient(wav if wav.exists() else mp4, t - 0.5, t + 0.5)
        pv = f"{v - t:+.3f} s" if v is not None else "n/a"
        pa = f"{a - t:+.3f} s" if a is not None else "n/a"
        print(f"anchor  {cue:12s} at {t:9.3f} s: picture changes {pv}, sharpest sound {pa} from the cue  ({what})")

    if EDITION == "full":
        joins = [k * 300.0 for k in range(1, int(T // 300) + 1)]
        for b in joins[:: max(1, len(joins) // 6)]:
            fr = decode_gray(mp4, b - 3 / FPS, 6 / FPS)
            if len(fr) >= 6:
                d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
                ref = float(np.median(np.delete(d, 2))) + 1e-6
                print(f"join    at {hms(b):>8s}: change across the join {d[2]:.2f} against {ref:.2f} for its "
                      f"neighbours (x{d[2] / ref:.1f})")
                if d[2] / ref > 3:
                    # the picture can change on its own at a join (a cut, a flash, a light following the
                    # music); only a render of the same frames in one process tells that from a seam
                    print(f"          large: render frames {int(b * FPS) - 2}-{int(b * FPS) + 2} in one process "
                          f"(elenavid video --png=...) and compare before calling it a seam")

    if failures:
        print("\nFAILED:\n  " + "\n  ".join(failures))
        return 1
    print("\nall hard checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
