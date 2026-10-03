"""Render a single scene shader with given parameters to PNG (development aid)."""
from __future__ import annotations

import sys
import time

import numpy as np
from PIL import Image

from ..config import QC_OUT
from .gl import GPU


def tonemap(img):
    x = np.clip(img, 0, None)
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    y = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
    return (y * 255).astype(np.uint8)


def render(frag, name, params=None, t=500.0, local=5.0, w=960, h=540, voice=0.5, **extra):
    gpu = GPU(w, h)
    gpu.program("s", frag)
    P = np.zeros((24, 4), dtype="f4")
    for k, v in (params or {}).items():
        P[k, : len(v)] = v
    gpu.set("s", uTime=t, uLocal=local, uDur=30.0, uRes=(float(w), float(h)), uP=P, uVoice=voice,
            uScore=0.5, uBeat=0.3, uBeatIdx=0.0, uBeatsBar=4.0, **extra)
    t0 = time.time()
    gpu.draw("s", gpu.fbo_scene[0])
    gpu.ctx.finish()
    dt = time.time() - t0
    raw = np.frombuffer(gpu.fbo_scene[0].read(components=3, dtype="f4"), dtype=np.float32)
    img = raw.reshape(h, w, 3)[::-1]
    out = QC_OUT / f"{name}.png"
    Image.fromarray(tonemap(img)).save(out)
    print(f"{name}: {dt * 1000:.0f} ms  max {img.max():.2f}  mean {img.mean():.3f}  -> {out}")
    return out


if __name__ == "__main__":
    print(sys.argv)
