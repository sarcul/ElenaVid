"""A contact sheet of stills taken from the delivered file: one from every section (at 45% of its length)
plus the required shot's three moments, each labelled with its time and section.

    elenavid qa contact-sheet [--edition film|full] [--cols=6] [--width=384] [--times=t1,t2,...]
                              [--file=path.mp4] [--out=path.png]

Writes output[/full]/qa/contact_sheet.png unless --out is given, so the delivered sheets are never
overwritten. --times replaces the automatic choice of stills.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

from ..config import EDITION
from ._media import REQUIRED_SHOT, delivered, hms, options, qa_dir, require_ffmpeg, sheet_font, still, timeline


def picks(tl):
    out = [(s["start"] + 0.45 * (s["end"] - s["start"]), s["key"], s["title"]) for s in tl["sections"]]
    for label, cue, dt in REQUIRED_SHOT[EDITION]:
        if cue in tl["cues"]:
            out.append((tl["cues"][cue] + dt, cue.split(".")[0], label))
    return sorted(out)


def main(argv=None):
    require_ffmpeg()
    o = options(argv)
    mp4 = Path(o["file"]) if "file" in o else delivered()
    if not mp4.exists():
        print(f"no delivered file at {mp4}")
        return 2
    tl = timeline()
    sections = tl["sections"]
    if "times" in o:
        items = []
        for t in map(float, o["times"].split(",")):
            sec = next((s for s in sections if s["start"] <= t < s["end"]), sections[-1])
            items.append((t, sec["key"], sec["title"]))
    else:
        items = picks(tl)
    cols, tw = int(o.get("cols", 6)), int(o.get("width", 384))
    th = round(tw * 9 / 16)
    rows = (len(items) + cols - 1) // cols
    head = 50
    sheet = Image.new("RGB", (cols * tw, head + rows * (th + 40)), (14, 12, 12))
    d = ImageDraw.Draw(sheet)
    d.text((12, 12), f"ELENA  ·  {mp4.name}  ·  {len(items)} stills", fill=(235, 220, 190), font=sheet_font(22))
    label_font = sheet_font(15)
    for i, (t, key, title) in enumerate(items):
        im = still(mp4, t, tw, th)
        x, y = (i % cols) * tw, head + (i // cols) * (th + 40)
        if im is not None:
            sheet.paste(im, (x, y))
        label = f"{hms(t)}  {key}  {title}"
        if len(label) > 52:
            label = label[:51] + "…"
        d.text((x + 6, y + th + 6), label, fill=(225, 215, 200), font=label_font)
    out = Path(o["out"]) if "out" in o else qa_dir() / "contact_sheet.png"
    sheet.save(out)
    print(f"wrote {out} ({len(items)} stills)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
