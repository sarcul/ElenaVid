"""Loudness per section of the master (ITU-R BS.1770: K-weighting, 400 ms blocks, gating), streamed so a
two-hour file needs little memory; with --plot, a chart of momentary and short-term loudness.

    elenavid qa levels [--edition film|full] [--file=any audio or video file] [--plot]

Reads the master WAV by default; --file measures anything ffmpeg can decode (the delivered MP4, a stem).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

from ._media import hms, master, options, qa_dir, require_ffmpeg, timeline

FS = 48000
# BS.1770-4 K-weighting at 48 kHz: the head's high shelf, then the revised low-frequency B curve
SHELF = ([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585])
RLB = ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])
SUB = FS // 10          # 100 ms


def subblock_energies(path: Path) -> np.ndarray:
    """K-weighted mean square (summed over both channels) of every 100 ms of the file."""
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a", "-ac", "2", "-ar", str(FS),
                             "-f", "f32le", "-"], stdout=subprocess.PIPE)
    zi = [[np.zeros(2), np.zeros(2)] for _ in range(2)]
    carry = np.zeros((0, 2))
    out = []
    while True:
        buf = proc.stdout.read(SUB * 600 * 8)          # one minute at a time
        if not buf:
            break
        x = np.frombuffer(buf[: len(buf) // 8 * 8], dtype=np.float32).reshape(-1, 2).astype(np.float64)
        y = np.empty_like(x)
        for c in range(2):
            s1, zi[c][0] = lfilter(*SHELF, x[:, c], zi=zi[c][0])
            y[:, c], zi[c][1] = lfilter(*RLB, s1, zi=zi[c][1])
        y = np.concatenate([carry, y])
        n = len(y) // SUB
        out.append((y[: n * SUB] ** 2).reshape(n, SUB, 2).mean(axis=1).sum(axis=1))
        carry = y[n * SUB:]
    proc.wait()
    return np.concatenate(out) if out else np.zeros(0)


def lufs(ms):
    return -0.691 + 10 * np.log10(np.maximum(ms, 1e-12))


def integrated(blocks):
    if not len(blocks):
        return None
    g = blocks[lufs(blocks) > -70]
    if not len(g):
        return -70.0
    rel = lufs(np.mean(g)) - 10
    g2 = g[lufs(g) > rel]
    return float(lufs(np.mean(g2))) if len(g2) else float(lufs(np.mean(g)))


def loudness_range(sub):
    st = np.convolve(sub, np.ones(30) / 30, mode="valid")[::10]          # 3 s short-term, every second
    g = st[lufs(st) > -70]
    if len(g) < 3:
        return 0.0
    g = g[lufs(g) > lufs(np.mean(g)) - 20]
    return float(np.percentile(lufs(g), 95) - np.percentile(lufs(g), 10))


def main(argv=None):
    require_ffmpeg()
    o = options(argv)
    path = Path(o["file"]) if "file" in o else master()
    if not path.exists():
        print(f"no file at {path}")
        return 2
    print(f"measuring {path.name} ...", flush=True)
    sub = subblock_energies(path)
    blocks = np.convolve(sub, np.ones(4) / 4, mode="valid")              # 400 ms blocks, 100 ms apart
    t_blk = np.arange(len(blocks)) * 0.1
    print(f"{hms(len(sub) / 10)}  integrated {integrated(blocks):.1f} LUFS  range {loudness_range(sub):.1f} LU  "
          f"loudest 400 ms {lufs(blocks.max()):.1f} LUFS")
    tl = timeline()
    print(f"  {'section':8s} {'starts':>8s} {'LUFS':>6s} {'max':>6s}  title")
    for s in tl["sections"]:
        sel = (t_blk >= s["start"]) & (t_blk < s["end"] - 0.4)
        b = blocks[sel]
        if not len(b):
            continue
        print(f"  {s['key']:8s} {hms(s['start']):>8s} {integrated(b):6.1f} {lufs(b.max()):6.1f}  {s['title']}")
    if "plot" in o:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("--plot needs matplotlib (pip install matplotlib)")
            return 0
        st = np.convolve(sub, np.ones(30) / 30, mode="same")
        fig, ax = plt.subplots(figsize=(20, 5))
        ax.plot(t_blk, lufs(blocks), lw=0.3, color="0.6", label="momentary (400 ms)")
        ax.plot(np.arange(len(st)) * 0.1, lufs(st), lw=0.9, color="C3", label="short-term (3 s)")
        for s in tl["sections"]:
            ax.axvline(s["start"], color="C0", lw=0.4, alpha=0.6)
            ax.text(s["start"], -12, s["key"], fontsize=6, rotation=90, va="bottom", color="C0")
        ax.set_ylim(-60, -5)
        ax.set_xlabel("seconds")
        ax.set_ylabel("LUFS")
        ax.legend(loc="lower right")
        p = qa_dir() / "levels.png"
        fig.tight_layout()
        fig.savefig(p, dpi=80)
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
