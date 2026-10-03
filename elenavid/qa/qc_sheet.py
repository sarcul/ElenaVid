"""Sheets of the renderer's QC stills (the frame_TTTT.TT.png files that `--png=` writes to frames_qc/).

    elenavid qa qc-sheet [--edition film|full] [--cols=4] [--per=16] [--times=t1,t2,...]

Writes frames_qc/sheet_NN.png, labelled with each still's time.
"""
from __future__ import annotations

import sys

from PIL import Image, ImageDraw

from ..config import QC_OUT
from ._media import hms, options, sheet_font


def main(argv=None):
    o = options(argv)
    cols, per = int(o.get("cols", 4)), int(o.get("per", 16))
    files = sorted(QC_OUT.glob("frame_*.png"))
    if "times" in o:
        want = {f"frame_{float(t):07.2f}" for t in o["times"].split(",")}
        files = [f for f in files if f.stem in want]
    if not files:
        print(f"no QC stills in {QC_OUT}: render some with `elenavid video --png=t1,t2,...`")
        return 2
    tw, th = 480, 270
    font = sheet_font(18)
    written = []
    for s in range(0, len(files), per):
        batch = files[s:s + per]
        rows = (len(batch) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + 24)), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, f in enumerate(batch):
            im = Image.open(f).convert("RGB").resize((tw, th), Image.LANCZOS)
            x, y = (i % cols) * tw, (i // cols) * (th + 24)
            sheet.paste(im, (x, y + 24))
            t = float(f.stem.split("_")[1])
            d.text((x + 6, y + 2), f"{t:8.2f} s   {hms(t)}", fill=(230, 230, 230), font=font)
        p = QC_OUT / f"sheet_{s // per:02d}.png"
        sheet.save(p)
        written.append(p)
    print("wrote", *written, sep="\n  ")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
