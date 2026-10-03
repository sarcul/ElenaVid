"""Typography: libretto lines and title cards rendered with PIL into channel-packed textures.

Packing: R = Italian glyph coverage, G = English glyph coverage, B = soft shadow, A = union.
Each sung line also carries the pixel span of every syllable so the overlay can light the words
exactly as they are sung.
"""
from __future__ import annotations

import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# The piece was set in Windows and Office faces, which cannot be shipped with the code. Each role
# lists the original first, then macOS, Linux and matplotlib's bundled DejaVu faces; failing all of
# them, Pillow's built-in face. It runs anywhere; it looks as intended with the originals.
ROLES = {
    "italic": ["BOD_I.TTF", "DejaVuSerif-Italic.ttf", "LiberationSerif-Italic.ttf", "Times New Roman Italic.ttf",
               "timesi.ttf"],                           # Bodoni MT Italic: the Parma face of the Verdi-era scores
    "roman": ["BOD_R.TTF", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf", "Times New Roman.ttf", "times.ttf"],
    "sans": ["GIL_____.TTF", "Gill Sans.ttc", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf",
             "arial.ttf"],                              # Gill Sans MT for the English
    "hand": ["segoesc.ttf", "Apple Chancery.ttf", "DejaVuSerif-Italic.ttf",
             "LiberationSerif-Italic.ttf"],             # Segoe Script for Marco's handwriting
    "ui": ["segoeui.ttf", "Helvetica.ttc", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "arial.ttf"],
    "mono": ["consola.ttf", "Menlo.ttc", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf", "cour.ttf"],
}


def _font_dirs():
    dirs = [Path(os.environ["ELENA_FONTS"])] if os.environ.get("ELENA_FONTS") else []
    if os.name == "nt":
        dirs += [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
                 Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "Fonts"]
    dirs += [Path.home() / "Library" / "Fonts", Path("/Library/Fonts"), Path("/System/Library/Fonts"),
             Path.home() / ".local" / "share" / "fonts", Path.home() / ".fonts", Path("/usr/share/fonts"),
             Path("/usr/local/share/fonts")]
    try:
        import matplotlib
        dirs.append(Path(matplotlib.get_data_path()) / "fonts" / "ttf")
    except ImportError:
        pass
    return dirs


@lru_cache(maxsize=1)
def _font_index():
    idx = {}
    for d in _font_dirs():
        if d.is_dir():
            for p in d.rglob("*"):
                if p.suffix.lower() in (".ttf", ".otf", ".ttc"):
                    idx.setdefault(p.name.lower(), str(p))
    return idx


@lru_cache(maxsize=None)
def find_font(role):
    """The first installed face for a role, or None (then Pillow's built-in face is used)."""
    idx = _font_index()
    return next((idx[n.lower()] for n in ROLES[role] if n.lower() in idx), None)


F_IT = find_font("italic")
F_IT_ROMAN = find_font("roman")    # roman for the Latin
F_EN = find_font("sans")
F_TITLE = find_font("roman")
F_SMALL = find_font("sans")
F_HAND = find_font("hand")

SS = 2   # supersampling


@lru_cache(maxsize=64)
def font(path, size):
    if path is None:
        return ImageFont.load_default(size=size)
    return ImageFont.truetype(path, size)


def _norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def syllable_spans(text, syllables):
    """Map syllable strings (with '_' joins) onto character index ranges of the display text."""
    letters = [(i, c) for i, c in enumerate(_norm(text)) if c.isalpha()]
    spans = []
    k = 0
    for syl in syllables:
        target = [c for c in _norm(syl) if c.isalpha()]
        if not target:
            spans.append(spans[-1] if spans else (0, 0))
            continue
        # find target sequence starting at or after k
        start = None
        j = k
        m = 0
        while j < len(letters) and m < len(target):
            if letters[j][1] == target[m]:
                if start is None:
                    start = letters[j][0]
                m += 1
            elif start is not None:
                # tolerate one skipped letter (elided h, apostrophes)
                pass
            j += 1
        end = letters[j - 1][0] + 1 if j > 0 else start
        if start is None:
            start = letters[min(k, len(letters) - 1)][0]
            end = start + 1
        spans.append((start, end))
        k = j
    return spans


def _tracked(draw, xy, text, fnt, tracking, fill):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def _tracked_len(draw, text, fnt, tracking):
    return sum(draw.textlength(ch, font=fnt) + tracking for ch in text) - tracking


STYLE = {
    # it font, it size, en size, it tracking, en tracking, uppercase english
    "aria": (F_IT, 44, 22, 0.0, 2.0),
    "duet": (F_IT, 44, 22, 0.0, 2.0),
    "lullaby": (F_IT, 44, 22, 0.0, 2.0),
    "vow": (F_IT, 48, 22, 0.0, 2.0),
    "parlato": (F_IT, 40, 21, 0.0, 1.8),
    "heat": (F_IT, 46, 22, 0.0, 2.0),
    "aside": (F_IT, 40, 21, 0.0, 1.8),
    "chorus": (F_IT, 46, 22, 0.0, 2.2),
    "latin": (F_IT_ROMAN, 42, 21, 3.0, 2.2),
    "vision": (F_IT, 42, 21, 2.0, 2.2),
    "offstage": (F_IT, 40, 20, 2.0, 2.0),
    "letter_read": (F_IT, 42, 22, 0.0, 2.0),
    "fragment": (F_IT, 46, 22, 0.0, 2.0),
}


def render_line(it, en, syllables=None, style="aria", max_w=1700):
    f_path, s_it, s_en, tr_it, tr_en = STYLE.get(style, STYLE["aria"])
    fi = font(f_path, s_it * SS)
    fe = font(F_EN, s_en * SS)
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    w_it = _tracked_len(probe, it, fi, tr_it * SS)
    en_txt = en
    w_en = _tracked_len(probe, en_txt, fe, tr_en * SS)
    # shrink if too wide
    scale = min(1.0, (max_w * SS) / max(w_it, w_en, 1))
    if scale < 1.0:
        fi = font(f_path, int(s_it * SS * scale))
        fe = font(F_EN, int(s_en * SS * scale))
        w_it = _tracked_len(probe, it, fi, tr_it * SS * scale)
        w_en = _tracked_len(probe, en_txt, fe, tr_en * SS * scale)
    pad = 24 * SS
    W = int(max(w_it, w_en) + 2 * pad)
    asc_i, desc_i = fi.getmetrics()
    asc_e, desc_e = fe.getmetrics()
    H = int(pad + asc_i + desc_i + 10 * SS + asc_e + desc_e + pad)
    R = Image.new("L", (W, H), 0)
    G = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(R)
    dg = ImageDraw.Draw(G)
    x0 = (W - w_it) / 2
    y0 = pad
    # per-character x positions for syllable spans
    xs = []
    x = x0
    for ch in it:
        xs.append(x)
        dr.text((x, y0), ch, font=fi, fill=255)
        x += dr.textlength(ch, font=fi) + tr_it * SS * scale
    xs.append(x)
    xe = (W - w_en) / 2
    _tracked(dg, (xe, y0 + asc_i + desc_i + 10 * SS), en_txt, fe, tr_en * SS * scale, 255)
    union = Image.fromarray(np.maximum(np.array(R), np.array(G)))
    shadow = union.filter(ImageFilter.GaussianBlur(9 * SS))
    shadow = Image.fromarray(np.clip(np.array(shadow).astype(np.float32) * 1.6, 0, 255).astype(np.uint8))
    img = np.stack([np.array(R), np.array(G), np.array(shadow),
                    np.maximum(np.array(union), np.array(shadow))], axis=-1)
    img = np.array(Image.fromarray(img, "RGBA").resize((W // SS, H // SS), Image.LANCZOS))
    spans = []
    if syllables:
        for a, b in syllable_spans(it, syllables):
            spans.append((xs[a] / W, xs[min(b, len(xs) - 1)] / W))
    return img, spans


def render_title(main, sub=None, sub2=None, size=88):
    """Act/scene title card: Bodoni capitals, widely tracked, with place and date beneath."""
    fm = font(F_TITLE, size * SS)
    fs = font(F_SMALL, 30 * SS)
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    tr = size * 0.32 * SS
    wm = _tracked_len(probe, main.upper(), fm, tr)
    ws = _tracked_len(probe, (sub or "").upper(), fs, 9 * SS) if sub else 0
    ws2 = _tracked_len(probe, (sub2 or "").upper(), fs, 7 * SS) if sub2 else 0
    pad = 40 * SS
    W = int(max(wm, ws, ws2) + 2 * pad)
    H = int(pad * 2 + size * SS * 1.25 + 2 * 46 * SS)
    R = Image.new("L", (W, H), 0)
    G = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(R)
    dg = ImageDraw.Draw(G)
    _tracked(dr, ((W - wm) / 2, pad), main.upper(), fm, tr, 255)
    y = pad + size * SS * 1.25
    if sub:
        _tracked(dg, ((W - ws) / 2, y), sub.upper(), fs, 9 * SS, 255)
    if sub2:
        _tracked(dg, ((W - ws2) / 2, y + 46 * SS), sub2.upper(), fs, 7 * SS, 255)
    union = Image.fromarray(np.maximum(np.array(R), np.array(G)))
    shadow = union.filter(ImageFilter.GaussianBlur(14 * SS))
    img = np.stack([np.array(R), np.array(G), np.array(shadow), np.array(union)], axis=-1)
    return np.array(Image.fromarray(img, "RGBA").resize((W // SS, H // SS), Image.LANCZOS))


def render_letter(text, w=1100, h=760, size=34, lead=52, with_lines=False):
    """Marco's letter: ink on paper, as an RGBA texture (R = ink coverage); optionally with the
    number of written lines (the reveal in abstract.frag runs line by line)."""
    fnt = font(F_HAND, size * SS)
    img = Image.new("L", (w * SS, h * SS), 0)
    d = ImageDraw.Draw(img)
    x, y = 70 * SS, 70 * SS
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for wd in words:
            test = (cur + " " + wd).strip()
            if d.textlength(test, font=fnt) > (w - 140) * SS:
                lines.append(cur)
                cur = wd
            else:
                cur = test
        lines.append(cur)
    for ln in lines:
        d.text((x, y), ln, font=fnt, fill=255)
        y += lead * SS
    img = img.resize((w, h), Image.LANCZOS)
    a = np.array(img)
    out = np.stack([a, a, a, a], axis=-1)
    return (out, len(lines)) if with_lines else out
