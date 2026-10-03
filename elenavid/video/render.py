"""Render the picture: scenes -> transitions -> typography & leitmotif lines -> bloom -> grade -> H.264.

Usage:  python -m elenavid.video.render [start_s] [end_s] [--out=name.mp4] [--audio] [--half]
                                        [--png=t1,t2,...] [--encoder=auto|nvenc|x264]
                                        [--cq=] [--crf=] [--rate=] [--maxrate=] [--preset=]

The encoder is NVENC when an NVIDIA GPU can run it and x264 otherwise (elenavid/video/encode.py).
"""
from __future__ import annotations

import bisect
import math
import subprocess
import sys
import time

import moderngl
import numpy as np
from PIL import Image, ImageFilter

from ..config import FPS, W, H, OUT, QC_OUT, AUDIO_OUT, DURATION, EDITION
from . import text as T
from . import encode
from .gl import GPU
from .timeline import Timeline, ease

if EDITION == "full":
    from . import shots_full as SH
    from .shots_full import SCENES, build
else:
    from . import shots as SH
    from .shots import SCENES, TITLES, build

STYLE_TINT = {
    "aria": (1.0, 0.92, 0.78), "duet": (1.0, 0.92, 0.78), "lullaby": (1.0, 0.9, 0.8), "vow": (1.0, 0.88, 0.7),
    "heat": (1.0, 0.86, 0.7), "parlato": (0.95, 0.9, 0.82), "chorus": (1.0, 0.8, 0.46),
    "latin": (0.96, 0.82, 0.56), "vision": (0.64, 0.78, 1.0), "offstage": (0.7, 0.76, 0.88),
    "aside": (0.86, 0.8, 0.76), "letter_read": (0.82, 0.8, 0.76), "fragment": (0.86, 0.86, 0.8),
    "title": (1.0, 0.88, 0.62),
}
TOP_STYLES = {"vision", "offstage"}


class TextBank:
    """Pre-rendered textures for every libretto line and title card."""

    def __init__(self, tl, gpu):
        self.gpu = gpu
        self.items = []
        TITLES = SH.TITLES
        for i, ln in enumerate(tl.lines):
            if ln["style"] == "letter":
                continue
            syl = [s[2] for s in ln["syllables"]] if ln["syllables"] else None
            img, spans = T.render_line(ln["it"], ln["en"], syl, ln["style"])
            self.items.append(dict(kind="line", idx=i, ln=ln, img=img, spans=spans,
                                   t0=ln["start"], t1=ln["end"], style=ln["style"]))
        for k, (t0, t1, main, sub, sub2) in enumerate(TITLES):
            img = T.render_title(main or " ", sub, sub2, size=96 if main == "Elena" else 74)
            self.items.append(dict(kind="title", idx=k, img=img, spans=[], t0=t0, t1=t1, style="title"))
        self.tex = {}

    def texture(self, item):
        key = (item["kind"], item["idx"])
        if key not in self.tex:
            img = item["img"]
            t = self.gpu.ctx.texture((img.shape[1], img.shape[0]), 4,
                                     data=np.ascontiguousarray(img[::-1]).tobytes())
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.tex[key] = t
        return self.tex[key]

    def active(self, t):
        out = []
        for it in self.items:
            pre, post = (0.6, 0.6) if it["kind"] in ("title", "caption") else (0.35, 0.9)
            if it["t0"] - pre <= t <= it["t1"] + post:
                a = ease((t - (it["t0"] - pre)) / pre) * (1 - ease((t - it["t1"]) / post))
                out.append((it, a))
        return out


class LazyTextBank(TextBank):
    """The full opera's text: lines, title cards and number captions rendered when first needed and
    released once they are over (two hours of surtitles would otherwise sit in memory throughout)."""

    def __init__(self, tl, gpu, titles, captions):
        self.gpu = gpu
        self.items = []
        for i, ln in enumerate(tl.lines):
            if ln["style"] == "letter":
                continue
            self.items.append(dict(kind="line", idx=i, ln=ln, t0=ln["start"], t1=ln["end"], style=ln["style"]))
        for k, (t0, t1, main, sub, sub2) in enumerate(titles):
            self.items.append(dict(kind="title", idx=k, t0=t0, t1=t1, style="title", text=(main, sub, sub2),
                                   big=main == "Elena"))
        for k, (t0, t1, num, name, sub) in enumerate(captions):
            self.items.append(dict(kind="caption", idx=k, t0=t0, t1=t1, style="title", text=(num, name, sub)))
        self.items.sort(key=lambda it: it["t0"])
        self.tex = {}

    def _image(self, it):
        if "img" not in it:
            if it["kind"] == "line":
                ln = it["ln"]
                syl = [s[2] for s in ln["syllables"]] if ln["syllables"] else None
                it["img"], it["spans"] = T.render_line(ln["it"], ln["en"], syl, ln["style"])
            elif it["kind"] == "title":
                main, sub, sub2 = it["text"]
                it["img"], it["spans"] = T.render_title(main or " ", sub, sub2, size=96 if it["big"] else 74), []
            else:
                num, name, sub = it["text"]
                img = T.render_title(num or " ", name, sub, size=38)
                # a broad, dense shadow so the caption reads over a bright sky as well as a dark room
                glyph = Image.fromarray(np.maximum(img[..., 0], img[..., 1]))
                halo = glyph.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(14))
                halo = np.clip(np.asarray(halo, dtype=np.float32) * 2.6, 0, 255).astype(np.uint8)
                img = img.copy()
                img[..., 2] = np.maximum(img[..., 2], halo)
                img[..., 3] = np.maximum(img[..., 3], halo)
                it["img"], it["spans"] = img, []
        return it["img"]

    def active(self, t):
        out = super().active(t)
        for it, _ in out:
            self._image(it)
        live = {(it["kind"], it["idx"]) for it, _ in out}
        for key in [k for k in self.tex if k not in live]:
            self.tex.pop(key).release()
        for it in self.items:
            if "img" in it and (it["kind"], it["idx"]) not in live and it["t1"] + 2.0 < t:
                del it["img"]
        return out


def reveal_of(item, t):
    """Fraction of the line's width that has been sung, and the active syllable centre."""
    ln = item.get("ln")
    if not ln or not ln["syllables"] or not item["spans"]:
        return 1.0, -1.0, 0.0
    sy = ln["syllables"]
    spans = item["spans"]
    if t < sy[0][0]:
        return spans[0][0], -1.0, 0.0
    for (t0, d, _), (x0, x1) in zip(sy, spans):
        if t0 <= t < t0 + d:
            f = min(1.0, (t - t0) / max(0.12, min(d, 0.5)))
            return x0 + (x1 - x0) * f, 0.5 * (x0 + x1), 1.0
    return 1.0, -1.0, 0.0


# ------------------------------------------------------------------------------- motif lines
def smooth(ctrl, n_out=90):
    """Catmull-Rom through control points (x, y, alpha, width) -> up to n_out points."""
    if len(ctrl) < 2:
        return ctrl
    P = np.array(ctrl, dtype=float)
    n = len(P)
    seg = max(1, n_out // (n - 1))
    out = []
    for i in range(n - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n - 1)]
        for k in range(seg):
            s = k / seg
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3))
    out.append(P[-1])
    return [tuple(p) for p in out[-n_out:]]


def melody(ns, prefer):
    """One line from a doubled or harmonised motif: the notes of the highest-priority part present
    (then the highest note at each onset), so the drawn contour never zigzags between voices."""
    if not ns:
        return ns
    present = {n["inst"] for n in ns}
    part = next((p for p in prefer if p in present), None)
    if part is None:
        part = max(present, key=lambda q: sum(1 for n in ns if n["inst"] == q))
    by_onset = {}
    for n in ns:
        if n["inst"] == part:
            k = round(n["t"], 3)
            if k not in by_onset or n["midi"] > by_onset[k]["midi"]:
                by_onset[k] = n
    return [by_onset[k] for k in sorted(by_onset)]


MELODY_PARTS = {
    "wedding": ("ch_s", "vn1", "fl", "ob", "cl"), "wedding_lament": ("vc", "va", "cb"),
    "wedding_memory": ("hn",), "vittorio": ("bar", "vc_solo"), "marco": ("ten", "cl"),
    "marco_warped": ("cl", "ob", "vn1", "hn", "tpt"), "marco_letter": ("cl",),
}


def note_path(ns, t, xmap, ymap, alpha_fn, width):
    """Control points at note centres for notes already sounding; the last follows the present."""
    ctrl = []
    for n in ns:
        if n["t"] > t:
            break
        tc = min(t, n["t"] + 0.5 * n["dur"])
        ctrl.append((xmap(tc), ymap(n["midi"]), alpha_fn(tc), width))
    return ctrl


def motif_lines(tl, t):
    """Up to four polylines: (points (n,4): x, y, alpha, width_px), colour (r,g,b,glow)."""
    out = []
    # Tommaso's tone: a fixed horizontal line of silver light at the height of 'A'
    lvl = tl.tone_level(t)
    pts = []
    if lvl > 0.01:
        for k in range(48):
            x = 0.05 + 0.9 * k / 47
            y = 0.585 + 0.0012 * math.sin(k * 1.7 + t * 3.0) * lvl
            edge = min(1.0, min(x - 0.05, 0.95 - x) / 0.12)
            pts.append((x, y, lvl * 0.9 * edge, 1.3))
    # the prologue's tuning lines join the same polyline (separate segments)
    for n in tl.tuning:
        if n["t"] - 0.1 <= t <= n["t"] + n["dur"] + 0.4:
            a = min(1.0, (t - n["t"]) / 0.25) * min(1.0, max(0.0, (n["t"] + n["dur"] + 0.4 - t) / 0.6))
            g = n["tags"].get("glide", 0) * math.exp(-(t - n["t"]) / 0.5)
            y = 0.585 + (n["midi"] - 69) * 0.0105 + g * 0.0004
            x0 = 0.2 + 0.6 * ((n["midi"] * 7) % 10) / 10 * 0.3
            seg = [(x0 - 0.001, y, 0.0, 1.0)] + [(x0 + 0.5 * k / 9, y + 0.0015 * math.sin(k + t * 9 * (abs(g) > 2)),
                                                  0.45 * a, 1.0) for k in range(10)] + [(x0 + 0.5, y, 0.0, 1.0)]
            pts += seg
    if pts:
        out.append((pts[:96], (0.86, 0.9, 1.0, 0.7)))
    # the wedding melody: gold ribbon trailing behind the playhead (lament: low bronze)
    for motif, base_y, ref, col, speed, amax in (
            ("wedding", 0.36, 74, (1.0, 0.74, 0.34, 1.0), 0.085, 0.9),
            ("wedding_lament", 0.2, 55, (0.72, 0.46, 0.24, 0.8), 0.06, 0.9),
            ("wedding_memory", 0.84, 61, (1.0, 0.8, 0.45, 0.5), 0.05, 0.28)):
        ns = melody([n for n in tl.motif.get(motif, []) if n["t"] <= t <= n["t"] + 7.0], MELODY_PARTS[motif])
        if not ns:
            continue
        head = 0.66
        ctrl = note_path(ns, t, lambda tt: head - (t - tt) * speed,
                         lambda m: base_y + (m - ref) * 0.011,
                         lambda tt: amax * max(0.0, 1.0 - (t - tt) / 6.5) *
                         min(1.0, max(0.0, (head - (t - tt) * speed - 0.03) / 0.1)), 1.8)
        if len(ctrl) >= 2:
            out.append((smooth(ctrl), col))
    # Vittorio's phrase: the same contour, drawn in place, on every appearance
    groups = {}
    for n in tl.motif.get("vittorio", []):
        # an appearance is one statement within one section (the full opera reuses the numbers)
        groups.setdefault((n["tags"].get("appearance", "x"), n["section"]), []).append(n)
    for (app, _sec), ns in groups.items():
        ns = melody(ns, MELODY_PARTS["vittorio"])
        t0 = ns[0]["t"]
        t_end = ns[-1]["t"] + ns[-1]["dur"]
        if not (t0 - 0.2 <= t <= t_end + 2.5):
            continue
        fade = 1.0 - ease((t - t_end - 0.8) / 1.6)
        top = app in (3, 4)
        ctrl = note_path(ns, t, lambda tt: 0.1 + 0.8 * (tt - t0) / 24.0,
                         lambda m: (0.86 if top else 0.75) + (m - 60) * 0.015,
                         lambda tt: fade * (0.4 if app == 3 else 0.75), 1.6)
        col = (1.0, 0.8, 0.45, 0.7) if app == "vow" else (0.5, 0.66, 1.0, 0.75)
        if len(ctrl) >= 2:
            out.append((smooth(ctrl), col))
    # Marco's motif: a green arc that rises and hangs, unresolved... until the letter
    for motif in ("marco", "marco_warped", "marco_letter"):
        ns = tl.motif.get(motif, [])
        stmts = []
        for n in ns:
            if stmts and n["t"] - (stmts[-1][-1]["t"] + stmts[-1][-1]["dur"]) < 0.8:
                stmts[-1].append(n)
            else:
                stmts.append([n])
        for st in stmts:
            st = melody(st, MELODY_PARTS[motif])
            s0 = st[0]["t"]
            s1 = st[-1]["t"] + st[-1]["dur"]
            if not (s0 - 0.1 <= t <= s1 + 2.0):
                continue
            fade = 1.0 - ease((t - s1) / 2.0)
            resolved = motif == "marco_letter" and len(st) >= 5 and t >= st[-1]["t"]
            span = max(1.0, s1 - s0)
            ctrl = note_path(st, t, lambda tt: 0.3 + 0.32 * (tt - s0) / span,
                             lambda m: 0.5 + (m - 66) * 0.012, lambda tt: fade * 0.85,
                             2.6 if motif == "marco_warped" else 1.6)
            glow = 2.2 if resolved and t - st[-1]["t"] < 1.2 else 0.8
            if len(ctrl) >= 2:
                out.append((smooth(ctrl), (0.45, 1.0, 0.72, glow)))
    return out[:4]


# ------------------------------------------------------------------------------- renderer
class Renderer:
    def __init__(self, w=W, h=H):
        self.tl = Timeline()
        self.shots = build(self.tl)
        self._starts = [s["start"] for s in self.shots]
        self.gpu = GPU(w, h)
        self.w, self.h = w, h
        for key, frag in SCENES.items():
            try:
                self.gpu.program(key, frag)
            except Exception as e:
                print(f"[warn] scene {key} unavailable: {str(e)[:200]}")
        self.gpu.program("post", "post.frag")
        self.gpu.program("overlay", "overlay.frag")
        self.dyn_tex = {}
        if EDITION == "full":
            self.titles = SH.titles(self.tl)
            self.text = LazyTextBank(self.tl, self.gpu, self.titles, SH.captions(self.tl))
            letters = sorted((ln for ln in self.tl.lines if ln["style"] == "letter"), key=lambda ln: ln["start"])
            self.letter_img = T.render_letter("\n".join(ln["it"] for ln in letters))
        else:
            self.titles = SH.TITLES
            self.text = TextBank(self.tl, self.gpu)
            letter_txt = next((ln["it"] for ln in self.tl.lines if ln["style"] == "letter"), "")
            self.letter_img = T.render_letter(letter_txt.replace("  ", "\n"))

    def tex_for(self, spec):
        key, lvl, arr = spec
        if key == "letter":
            arr = self.letter_img
            k = ("letter", 0)
            if k not in self.dyn_tex:
                t = self.gpu.ctx.texture((arr.shape[1], arr.shape[0]), 4, data=np.ascontiguousarray(arr[::-1]).tobytes())
                t.filter = (moderngl.LINEAR, moderngl.LINEAR)
                self.dyn_tex[k] = t
            return self.dyn_tex[k]
        k = (key, lvl)
        if k not in self.dyn_tex:
            t = self.gpu.ctx.texture((arr.shape[1], arr.shape[0]), 4, data=np.ascontiguousarray(arr[::-1]).tobytes(),
                                     dtype="f2")
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.dyn_tex[k] = t
        return self.dyn_tex[k]

    def shot_at(self, t):
        i = bisect.bisect_right(self._starts, t) - 1
        return min(max(i, 0), len(self.shots) - 1)

    def draw_scene(self, shot, t, fbo):
        key = shot["scene"]
        if key not in self.gpu.progs:
            fbo.use()
            self.gpu.ctx.clear(0.0, 0.0, 0.0, 1.0)
            return
        lt = t - shot["start"]
        P, extra, texs = shot["fn"](self.tl, t, lt)
        extra = dict(extra)
        extra.setdefault("uCam", (0.0, 0.0, 0.0))   # GL keeps a uniform's last value: always set the framing
        beat = self.tl.baton(t)
        self.gpu.set(key, uTime=t, uLocal=lt, uDur=shot["end"] - shot["start"], uRes=(float(self.w), float(self.h)),
                     uP=P, uVoice=self.tl.voice_env(t), uScore=self.tl.score_env(t), uBeat=float(beat[1]),
                     uBeatIdx=float(beat[2]), uBeatsBar=4.0, **extra)
        textures = [(name, self.tex_for(spec)) for name, spec in texs]
        self.gpu.draw(key, fbo, textures=textures)

    def post(self, **u):
        self.gpu.set("post", **u)

    def frame(self, t, raw=False):
        g = self.gpu
        i = self.shot_at(t)
        cur = self.shots[i]
        mode, dur = cur["trans"]
        A, B, mix = None, cur, 1.0
        if dur > 0 and t < cur["start"] + dur / 2 and i > 0:
            A = self.shots[i - 1]
            mix = (t - (cur["start"] - dur / 2)) / dur
        elif i + 1 < len(self.shots):
            nxt = self.shots[i + 1]
            nm, nd = nxt["trans"]
            if nd > 0 and t >= nxt["start"] - nd / 2:
                A, B, mode = cur, nxt, nm
                mix = (t - (nxt["start"] - nd / 2)) / nd
        if A is None:
            self.draw_scene(B, t, g.fbo_scene[0])
            self.post(uPass=0, uMix=0.0, uMode=0)
            g.draw("post", g.fbo_comp, textures=[("uTexA", g.fbo_scene[0].color_attachments[0]),
                                                 ("uTexB", g.fbo_scene[0].color_attachments[0])])
            grade = B["grade"]
        else:
            self.draw_scene(A, t, g.fbo_scene[0])
            self.draw_scene(B, t, g.fbo_scene[1])
            self.post(uPass=0, uMix=float(np.clip(mix, 0, 1)), uMode=int(mode))
            g.draw("post", g.fbo_comp, textures=[("uTexA", g.fbo_scene[0].color_attachments[0]),
                                                 ("uTexB", g.fbo_scene[1].color_attachments[0])])
            ga, gb = A["grade"], B["grade"]
            m = float(np.clip(mix, 0, 1))
            grade = {k: (tuple(np.array(ga[k]) * (1 - m) + np.array(gb[k]) * m) if isinstance(ga[k], tuple)
                         else ga[k] * (1 - m) + gb[k] * m) for k in ga}
        # ---- overlay: typography and motif lines
        items = self.text.active(t)
        rects = np.zeros((4, 4), "f4")
        params = np.zeros((4, 4), "f4")
        tints = np.zeros((4, 4), "f4")
        textures = [("uScene", g.fbo_comp.color_attachments[0])]
        n = 0
        bottom_y = 0.045
        opera = cur["scene"] in ("opera", "closeup")
        for it, a in sorted(items, key=lambda x: x[0]["t0"])[:4]:
            img = it["img"]
            tw, th = img.shape[1] / self.w * (self.w / 1920), img.shape[0] / self.h * (self.h / 1080)
            if it["kind"] == "title":
                cx, cy = 0.5, 0.52 if it["idx"] in (0, len(self.titles) - 1) else 0.5
                rect = (cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2)
            elif it["kind"] == "caption":
                rect = (0.03, 0.965 - th, 0.03 + tw, 0.965)
            elif it["style"] in TOP_STYLES:
                rect = (0.5 - tw / 2, 0.955 - th, 0.5 + tw / 2, 0.955)
            elif it["style"] == "fragment":
                k = it["idx"] % 4
                cx = (0.3, 0.68, 0.36, 0.64)[k]
                cy = (0.72, 0.62, 0.3, 0.22)[k]
                rect = (cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2)
            else:
                cx = 0.3 if cur["scene"] == "closeup" else 0.5      # keep her neck clear
                rect = (cx - tw / 2, bottom_y, cx + tw / 2, bottom_y + th)
                bottom_y += th * 0.92
            rev, act, glow = reveal_of(it, t)
            if it["kind"] in ("title", "caption"):
                rev, act, glow = 1.0, -1.0, 0.0
            rects[n] = rect
            # shadow depth: captions deepest; the full opera's surtitles a little deeper than the film's
            depth = 1.0 if it["kind"] == "caption" else (0.45 if EDITION == "full" and it["kind"] == "line" else 0.0)
            params[n] = (rev, a * (0.85 if opera and it["kind"] == "line" else 1.0), depth, glow)
            tints[n] = (*STYLE_TINT.get(it["style"], (1, 1, 1)), act)
            textures.append((f"uText{n}", self.text.texture(it)))
            n += 1
        lines = motif_lines(self.tl, t)
        # a title card owns the frame: the motif lines step back while it is up
        title_a = max([a for it, a in items if it["kind"] == "title"], default=0.0)
        pts = np.zeros((384, 4), "f4")
        cnt = np.zeros(4, "i4")
        cols = np.zeros((4, 4), "f4")
        for L, (pl, col) in enumerate(lines):
            arr = np.array(pl, dtype="f4")[:96]
            arr[:, 2] *= 1.0 - 0.8 * title_a
            pts[L * 96: L * 96 + len(arr)] = arr
            cnt[L] = len(arr)
            cols[L] = col
        ov = g.progs["overlay"]
        g.set("overlay", uTextRect=rects, uTextParam=params, uTextTint=tints, uNText=n, uTime=t,
              uRes=(float(self.w), float(self.h)), uLineCol=cols, uLinePts=pts)
        ov["uLineN"].write(cnt.tobytes())
        # bind unused text samplers to something valid
        for k in range(n, 4):
            textures.append((f"uText{k}", g.fbo_comp.color_attachments[0]))
        g.draw("overlay", g.fbo_over, textures=textures)
        # ---- bloom pyramid
        src = g.fbo_over.color_attachments[0]
        # bright-pass into level 0, then blur each level (ping-pong a -> b -> a)
        self.post(uPass=1, uTexel=(1.0 / self.w, 1.0 / self.h))
        g.draw("post", g.bloom[0][0], textures=[("uTexA", src)])
        for lvl, (fa, fb) in enumerate(g.bloom):
            texel = (1.0 / fa.size[0], 1.0 / fa.size[1])
            if lvl > 0:   # downsample the previous level into this one
                self.post(uPass=2, uDir=(0.0, 0.0), uTexel=texel)
                g.draw("post", fa, textures=[("uTexA", g.bloom[lvl - 1][0].color_attachments[0])])
            self.post(uPass=2, uDir=(1.0, 0.0), uTexel=texel)
            g.draw("post", fb, textures=[("uTexA", fa.color_attachments[0])])
            self.post(uPass=2, uDir=(0.0, 1.0), uTexel=texel)
            g.draw("post", fa, textures=[("uTexA", fb.color_attachments[0])])
        # upsample and accumulate from the smallest level back to level 0
        for lvl in range(len(g.bloom) - 1, 0, -1):
            big_a, big_b = g.bloom[lvl - 1]
            self.post(uPass=3)
            g.draw("post", big_b, textures=[("uTexA", big_a.color_attachments[0]),
                                            ("uTexB", g.bloom[lvl][0].color_attachments[0])])
            g.ctx.copy_framebuffer(big_a, big_b)
        bloom_tex = g.bloom[0][0].color_attachments[0]
        # ---- final grade
        fade = 0.0
        if t < 0.8:
            fade = 1.0 - t / 0.8
        if t > DURATION - 0.5:
            fade = (t - (DURATION - 0.5)) / 0.5
        self.post(uPass=4, uTime=t, uExposure=float(grade["exposure"]), uTemp=float(grade["temp"]),
                  uSat=float(grade["sat"]), uContrast=float(grade["contrast"]), uLift=tuple(grade["lift"]),
                  uVignette=float(grade["vignette"]), uGrain=float(grade["grain"]), uFade=float(fade),
                  uBloomAmt=float(grade["bloom"]), uAberr=float(grade["aberr"]))
        g.draw("post", g.fbo_out, textures=[("uTexA", src), ("uTexB", bloom_tex)])
        if raw:   # the framebuffer's own bytes, bottom row first (ffmpeg flips them by stride, without a copy)
            return g.fbo_out.read(components=3, dtype="f1")
        return g.read()


def parse_args(argv):
    """Positional times and --key[=value] options (values split at the first '=')."""
    args = [a for a in argv if not a.startswith("--")]
    opts = {}
    for a in argv:
        if a.startswith("--"):
            k, _, v = a.partition("=")
            opts[k] = v if _ else True
    return args, opts


def main(argv=None):
    args, opts = parse_args(sys.argv[1:] if argv is None else argv)
    half = "--half" in opts
    w, h = (W // 2, H // 2) if half else (W, H)
    if "--png" not in opts:
        encode.require_ffmpeg()
        kind = encode.choose(None if opts.get("--encoder") in (None, True) else str(opts["--encoder"]))
        print(f"encoder: {encode.reason(kind)}", flush=True)
    r = Renderer(w, h)
    if "--png" in opts:
        for ts in str(opts["--png"]).split(","):
            t = float(ts)
            img = r.frame(t)
            p = QC_OUT / f"frame_{t:07.2f}.png"
            Image.fromarray(img).save(p)
            print("wrote", p)
        return 0
    t0 = float(args[0]) if args else 0.0
    t1 = float(args[1]) if len(args) > 1 else DURATION
    out = OUT / str(opts.get("--out", "elena_video.mp4"))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(FPS), "-i", "-"]
    raw = EDITION == "full"
    audio = AUDIO_OUT / ("elena_full_master.wav" if EDITION == "full" else "elena_master.wav")
    if "--audio" in opts and audio.exists():
        cmd += ["-ss", str(t0), "-i", str(audio)]
    if raw:
        cmd += ["-vf", "vflip"]          # an output option: after every input
    # the film's encode is near-transparent; the full opera's lighter (see encode.QUALITY); the full
    # opera's chunks also put a keyframe every two seconds so the joined file seeks well
    cmd += encode.video_args(kind, encode.quality(EDITION, opts), gop=60 if EDITION == "full" else None)
    if "--audio" in opts and audio.exists():
        # AAC encoding overshoots the master's -1 dBTP by about 0.1 dB: trim 0.2 dB to stay inside it
        cmd += ["-af", "volume=-0.2dB", "-c:a", "aac", "-b:a", "320k", "-shortest"]
    cmd += ["-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    tstart = time.time()
    for f in range(f0, f1):
        t = f / FPS
        if raw:
            proc.stdin.write(r.frame(t, raw=True))
        else:
            img = r.frame(t)
            proc.stdin.write(img.tobytes())
        if (f - f0) % 150 == 0:
            el = time.time() - tstart
            fps = (f - f0 + 1) / max(el, 1e-6)
            print(f"t={t:7.2f}s  frame {f}/{f1}  {fps:5.1f} fps  eta {(f1 - f) / max(fps, 1e-6) / 60:5.1f} min",
                  flush=True)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        print(f"ffmpeg failed ({proc.returncode})")
        return proc.returncode
    print("wrote", out, f"in {(time.time() - tstart) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
