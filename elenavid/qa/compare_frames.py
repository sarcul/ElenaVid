"""Reproducibility check: re-render frames with the current code and compare them with reference stills,
writing nothing.

    elenavid qa compare-frames [--edition film|full] [--times=42.6,262.5] [--refs=folder] [--tolerance=2]

By default every frame_TTTT.TT.png in the edition's frames_qc/ folder is compared, each at its own
resolution (half-resolution references are re-rendered at half resolution). Exit status 1 if any
pixel differs by more than the tolerance (in 8-bit code values).

Render on the same GPU and driver as the references: GPUs differ in the last bits of floating point.
On a Windows laptop with two GPUs, the variable SHIM_MCCOMPAT selects the NVIDIA one; leave it unset
to compare with stills made on the integrated GPU.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

from ..config import QC_OUT, W, H
from ._media import options


def main(argv=None):
    o = options(argv)
    refs = Path(o.get("refs", QC_OUT))
    tol = int(o.get("tolerance", 2))
    files = sorted(refs.glob("frame_*.png"))
    if "times" in o:
        want = {f"frame_{float(t):07.2f}" for t in o["times"].split(",")}
        files = [f for f in files if f.stem in want]
    if not files:
        print(f"no reference stills in {refs}")
        return 2
    from ..video.render import Renderer
    by_size = {}
    for f in files:
        with Image.open(f) as im:
            by_size.setdefault(im.size, []).append(f)
    worst = 0
    for (w, h), group in sorted(by_size.items(), reverse=True):
        if (w, h) not in ((W, H), (W // 2, H // 2)):
            print(f"skipping {len(group)} still(s) at {w}x{h}: not a renderer size")
            continue
        r = Renderer(w, h)
        print(f"renderer: {r.gpu.ctx.info['GL_RENDERER']}  ({w}x{h})")
        for f in group:
            t = float(f.stem.split("_")[1])
            ref = np.asarray(Image.open(f).convert("RGB")).astype(np.int16)
            new = r.frame(t).astype(np.int16)
            d = np.abs(ref - new)
            worst = max(worst, int(d.max()))
            print(f"  {t:9.2f} s  max difference {int(d.max()):3d}  mean {d.mean():.4f}  "
                  f"pixels differing {(d.max(axis=2) > 0).mean() * 100:.3f}%")
    print(f"\nworst difference {worst} (tolerance {tol})")
    return 1 if worst > tol else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
