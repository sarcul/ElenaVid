"""The full opera's shot list (ELENA_EDITION=full).

The film (shots.py) was cut by hand. Two hours are staged from the score's own data instead: each
section's location picks the set; the singing intervals pick who is framed (a wide shot, a two-shot or
a single, cut on phrase starts); the composed cues place the story's events. The opera house frames the
evening: the prologue, the preludes, the intermezzo and the intervals are played to the closed curtain,
each act ends with the curtain falling, and the final aria is the required shot.

Framing in the 2D sets uses the uCam uniform (common.glsl): a frame centre and a zoom over the
composed picture, so a set built for one wide view also gives two-shots, singles and slow push-ins.
"""
from __future__ import annotations

import math
import random

import numpy as np

from .shots import SCENES, P, grade, opera_params, spline, fig, church, ELENA_Y
from .timeline import ease, ease_io, lerp, lerp3

AR = 16 / 9 / 2          # half-width of the frame in screen units


def V(v, tl, t):
    return v(tl, t) if callable(v) else v


# ============================================================================ framing
def cam_at(cx, cy, zoom):
    """uCam for a frame centred at (cx, cy) with the given zoom, kept inside the composed picture."""
    z = max(1.0, zoom)
    hx, hy = AR / z, 0.5 / z
    return (float(np.clip(cx, -AR + hx, AR - hx)), float(np.clip(cy, -0.5 + hy, 0.5 - hy)), math.log2(z))


def fr_wide(dur, z0=1.0, z1=1.06, cx=0.0, cy=0.0, cx1=None, cy1=None):
    def cam(tl, t, lt):
        k = ease_io(lt / dur)
        return cam_at(lerp(cx, cx if cx1 is None else cx1, k), lerp(cy, cy if cy1 is None else cy1, k),
                      lerp(z0, z1, k))
    return cam


def fr_one(f, dur, zoom=1.5, push=0.07, up=0.56):
    """A single: the figure from about the knees up, drifting closer through the shot."""
    def cam(tl, t, lt):
        x, y, h, a = f(tl, t)
        return cam_at(x, y + up * h, zoom * (1 + push * ease_io(lt / dur)))
    return cam


def fr_two(f1, f2, dur, push=0.05, up=0.5, margin=0.62, zmax=1.55):
    def cam(tl, t, lt):
        x1, y1, h1, _ = f1(tl, t)
        x2, y2, h2, _ = f2(tl, t)
        z = min(zmax, max(1.0, 2 * AR / (abs(x1 - x2) + margin)))
        return cam_at(0.5 * (x1 + x2), 0.5 * (y1 + up * h1 + y2 + up * h2), z * (1 + push * ease_io(lt / dur)))
    return cam


def framed(fn, cam, angle=0.0, angle_slot=None):
    """A scene function with a framing (and, for sets that allow it, a camera offset per shot)."""
    def f(tl, t, lt):
        p, extra, tex = fn(tl, t, lt)
        if angle and angle_slot is not None:
            p = p.copy()
            p[0, angle_slot] += angle
        extra = dict(extra)
        extra["uCam"] = cam(tl, t, lt)
        return p, extra, tex
    return f


# ============================================================================ coverage
def sung(tl, key, a, b):
    """Seconds each voice sings in [a, b) of a section."""
    out = {}
    for x in tl.meta.get(key, {}).get("singing", []):
        o = min(b, x["t1"]) - max(a, x["t0"])
        if o > 0:
            out[x["voice"]] = out.get(x["voice"], 0.0) + o
    return out


def cut_times(tl, t0, t1, rng, lo=14.0, hi=32.0):
    """Cuts a quarter of a second before a sung line begins, every lo..hi seconds."""
    starts = sorted(l["start"] - 0.25 for l in tl.lines if t0 + lo <= l["start"] - 0.25 <= t1 - lo)
    cuts, cur = [t0], t0
    while t1 - cur > hi:
        target = cur + rng.uniform(lo + 3.0, hi - 3.0)
        cands = [s for s in starts if cur + lo <= s <= cur + hi]
        nxt = min(cands, key=lambda s: abs(s - target)) if cands else cur + rng.uniform(lo + 4.0, hi - 2.0)
        if t1 - nxt < lo:
            break
        cuts.append(nxt)
        cur = nxt
    cuts.append(t1)
    return cuts


def cover(add, tl, key, t0, t1, scene, base, figs, g, trans=(0, 1.0), seed=1, lo=14.0, hi=32.0,
          vista=None, first="wide", zoom=1.45, angle_slot=None, two_max=1.5):
    """Sub-shots over [t0, t1): whoever sings is framed (one voice: a single; two: a two-shot; none: the
    wide or a vista), cut on phrase starts; the same framing never twice in a row."""
    rng = random.Random(seed)
    cuts = cut_times(tl, t0, t1, rng, lo, hi)
    prev = None
    for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
        dur = b - a
        mid = 0.5 * (a + b)
        vis = [v for v, f in figs.items() if f(tl, mid)[3] > 0.5]
        s = {v: d for v, d in sung(tl, key, a, b).items() if v in vis}
        if i == 0 and first:
            kind = (first,)
        elif not s:
            kind = ("vista",) if (vista and prev == ("wide",)) else ("wide",)
        else:
            top = sorted(s.items(), key=lambda kv: -kv[1])
            kind = ("two", top[0][0], top[1][0]) if len(top) > 1 and top[1][1] > 0.35 * top[0][1] else ("one", top[0][0])
        if kind == prev:
            others = [v for v in vis if kind[0] == "one" and v != kind[1]]
            if others:
                kind = ("two", kind[1], others[0])
            elif kind[0] in ("one", "two"):
                kind = ("vista",) if vista and rng.random() < 0.4 else ("wide",)
            elif vis:
                kind = ("one", vis[rng.randrange(len(vis))])
            elif vista:
                kind = ("vista",) if kind != ("vista",) else ("wide",)
        if kind[0] == "wide":
            cam = fr_wide(dur, 1.0, 1.0 + rng.uniform(0.05, 0.14))
        elif kind[0] == "vista":
            cam = vista(dur)
        elif kind[0] == "one":
            cam = fr_one(figs[kind[1]], dur, zoom * rng.uniform(0.9, 1.12))
        else:
            cam = fr_two(figs[kind[1]], figs[kind[2]], dur, zmax=two_max)
        ang = (-0.012, 0.0, 0.012)[i % 3] if kind[0] != "wide" else 0.0
        add(a, b, scene, framed(base, cam, ang, angle_slot), g, trans if i == 0 else (0, 0.0))
        prev = kind


# ============================================================================ scene functions
def village_fn(mode, T0, elena, marco, crowd=1.0, warmth=0.1, letters=0.0, swifts=0.7):
    def f(tl, t, lt):
        p = P()
        p[0] = (mode, 0.02 * math.sin(2 * math.pi * (t - T0) / 110.0), V(crowd, tl, t), V(warmth, tl, t))
        p[1] = elena(tl, t)
        p[2] = marco(tl, t)
        p[3] = (V(letters, tl, t), swifts, 0, 0)
        return p, {}, []
    return f


def rooms_fn(mode, T0, elena, second=None, third=None, amber=0.0, tommaso=0.0, vittorio=0.0, portrait=0.0,
             door=0.0, poses=(0, 0, 0, 0), extra=0.0, fly=0.0, recast=0.0, drift=0.012, period=140.0):
    def f(tl, t, lt):
        p = P()
        p[0] = (mode, drift * math.sin(2 * math.pi * (t - T0) / period), V(amber, tl, t), V(fly, tl, t))
        p[1] = elena(tl, t)
        p[2] = second(tl, t) if second else (0, 0, 0, 0)
        p[3] = third(tl, t) if third else (0, 0, 0, 0)
        p[4] = (V(tommaso, tl, t), V(vittorio, tl, t), V(portrait, tl, t), V(door, tl, t))
        p[5] = V(poses, tl, t)
        p[6] = (V(extra, tl, t), V(recast, tl, t), 0, 0)
        return p, {}, []
    return f


def night_fn(mode, elena, train=0.0, steam=0.7, route=0.0):
    def f(tl, t, lt):
        p = P()
        p[0] = (mode, V(train, tl, t), steam, 0)
        p[1] = elena(tl, t)
        p[2] = (V(route, tl, t), 1.0, 0, 0)
        return p, {}, []
    return f


def street_fn(T0, elena, marco, passers=0.6, daylight=0.7):
    def f(tl, t, lt):
        p = P()
        p[0] = (0.02 * math.sin(2 * math.pi * (t - T0) / 120.0), 0, 0, 0)
        p[1] = elena(tl, t)
        p[2] = marco(tl, t)
        p[3] = (V(passers, tl, t), V(daylight, tl, t), 0, 0)
        return p, {}, []
    return f


def abstract_fn(mode, t0, t1, a=0.0, b=0.0, lines=0.0, prog=None):
    def f(tl, t, lt):
        p = P()
        k = prog(tl, t) if prog else min(1.0, max(0.0, (t - t0) / max(1e-3, t1 - t0)))
        p[0] = (mode, k, 0, 0)
        p[1] = (V(a, tl, t), V(b, tl, t), lines, 0)
        tex = [("uLetter", ("letter", 0, None))] if mode == 2 else []
        return p, {}, tex
    return f


def stabat_fn(T0, T1, gl, de, held):
    def f(tl, t, lt):
        p = P()
        st = t - T0
        p[0] = (ease(st / 8.0), 1.0 - ease((st - 6.0) / 6.0), ease((t - held + 1.0) / 2.5), 0.2 * st / (T1 - T0))
        p[1] = (math.exp(-((t - gl) / 0.9) ** 2), ease((t - de) / 1.5) * (1 - ease((t - de - 3.5) / 2.0)), 0, 0)
        return p, {}, []
    return f


# ---------------------------------------------------------------------------- the opera house
HOUSE = {   # camera from, camera to, target from, target to, focal length
    "stalls": ((0.0, 2.1, -15.5), (0.0, 2.2, -12.0), (0.0, 4.6, 1.0), (0.0, 4.4, 1.0), 1.25),
    "pit": ((-1.2, 1.7, -6.3), (-0.8, 1.62, -5.6), (0.15, 1.95, 0.4), (0.15, 1.9, 0.4), 1.35),
    "dome": ((0.0, 2.6, -9.0), (0.4, 2.8, -9.4), (-2.0, 16.0, -12.0), (2.0, 16.2, -11.0), 0.7),
    "tiers": ((5.0, 4.0, -3.5), (-5.0, 4.2, -3.5), (-6.0, 5.5, -16.0), (6.0, 5.5, -16.0), 0.95),
    "apron": ((2.4, 2.9, -0.9), (-2.4, 3.1, -0.9), (0.0, 5.5, -14.0), (0.0, 5.6, -14.0), 0.85),
    "curtain": ((0.0, 3.0, -5.5), (0.0, 3.2, -3.6), (0.0, 5.0, 0.3), (0.0, 5.2, 0.3), 1.5),
    "box": ((-9.5, 6.5, -9.0), (-9.0, 6.6, -8.0), (0.0, 3.5, 2.0), (0.0, 3.3, 2.0), 1.1),
    "gallery": ((0.0, 11.5, -22.5), (0.0, 10.5, -20.5), (0.0, 5.0, 2.0), (0.0, 4.6, 2.0), 1.15),
}


def house_fn(view, dur, reverse=False, house=0.1, wash=0.35, curtain=1.0, cold=0.0, ripple=0.0, spot=0.0,
             baton=True, empty=True, sparkle="score"):
    """The house with the curtain down (or rising on an empty stage): overtures, intervals, calls."""
    c0, c1, g0, g1, fl = HOUSE[view]
    if reverse:
        c0, c1, g0, g1 = c1, c0, g1, g0

    def f(tl, t, lt):
        k = ease_io(lt / dur)
        p = opera_params(tl, lerp3(c0, c1, k), lerp3(g0, g1, k), fl, 0.0, V(house, tl, t), V(wash, tl, t),
                         V(spot, tl, t), curtain=V(curtain, tl, t), t=t, cold=V(cold, tl, t), ripple=V(ripple, tl, t))
        p[3, 0] = V(spot, tl, t)
        if sparkle == "score":
            p[4, 0] = min(1.5, 0.25 + 1.0 * tl.score_env(t))
        if not baton:
            p[6, :3] = 0.0
        p[7, 1] = 1.0 if empty else 0.0
        return p, {}, []
    return f


# the dolly-in of the final aria (shots.DOLLY_POS/LOOK slowed by a fifth; then a creep to the cut)
DOLLY_POS_FULL = [(k * 1.2, v) for k, v in [(0.0, (0.25, 2.05, -16.5)), (7.0, (0.35, 1.98, -12.6)),
                                             (12.0, (0.48, 1.86, -9.6)), (15.5, (0.62, 1.62, -7.3)),
                                             (17.5, (0.72, 1.52, -5.95)), (20.0, (0.82, 1.5, -4.3)),
                                             (22.0, (0.8, 1.58, -3.0)), (24.5, (0.6, 1.88, -1.6)),
                                             (27.0, (0.32, 2.2, -0.2)), (30.0, (0.12, 2.4, 0.7))]] + \
                 [(43.5, (0.06, 2.46, 1.15))]
DOLLY_LOOK_FULL = [(k * 1.2, v) for k, v in [(0.0, (0.0, 4.4, 4.0, 1.15)), (13.0, (0.0, 3.2, 4.0, 1.35)),
                                              (20.0, (0.0, 2.75, 4.0, 1.5)), (30.0, (0.0, 2.6, 4.0, 2.0))]] + \
                  [(43.5, (0.0, 2.58, 4.0, 2.1))]


# ============================================================================ titles
def titles(tl):
    c = tl.c
    s = {x["key"]: x["start"] for x in tl.sections}
    T = [(c("P0.title_in"), c("P0.title_out"), "Elena", "tragedia lirica in tre atti", None)]
    for key, main, sub, sub2 in (
            ("N1", "Atto primo", "La piazza", "Veneto  ·  estate 1948"),
            ("R1", "", "Il salotto", "primavera 1950"),
            ("N6", "", "La chiesa", "primavera 1950"),
            ("I23", "", "La casa di Verona", "autunno 1953"),
            ("N9", "Atto secondo", "La stazione", "notte"),
            ("N10", "", "Trieste", "1955"),
            ("N13", "", "Una strada di Trieste", "1957"),
            ("R3", "Atto terzo", "Mesi", "Trieste  ·  1958"),
            ("N16", "", "Una chiesa, al tramonto", None),
            ("N17", "", "La casa di Marco", "notte"),
            ("R4", "", "Una trattoria", "sera"),
            ("N19", "", "Una chiesa", "giorni dopo")):
        t0 = s[key] + (1.6 if main else 1.0)
        T.append((t0, t0 + (5.0 if main else 4.0), main, sub, sub2))
    T.append((c("F0.title_in"), max(x["end"] for x in tl.sections) - 0.6, "Elena", "tragedia lirica in tre atti",
              "libretto, music, sound and image made in code"))
    return T


def captions(tl):
    """Each number's name, small at the top left, after any title card."""
    out = []
    tt = titles(tl)
    for s in tl.sections:
        key, title = s["key"], s["title"]
        if key in ("P0", "F0"):
            continue
        num = f"N. {key[1:]}" if key[0] == "N" else ""
        name, sub = title, None
        if ', "' in title:
            name, sub = title.split(', "', 1)
            sub = "“" + sub.rstrip('"') + "”"
        t0 = s["start"] + 1.2
        for a, b, *_ in tt:
            if a - 1.0 <= t0 <= b + 0.8:
                t0 = b + 1.2
        if t0 + 5.5 > s["end"] - 1.0:
            continue
        out.append((t0, t0 + 5.5, num, name, sub))
    return out


# ============================================================================ the shot list
def build(tl):
    c = tl.c
    sec = {s["key"]: (s["start"], s["end"]) for s in tl.sections}
    S = []

    def add(t0, t1, scene, fn, g=None, trans=(0, 0.0)):
        if t1 - t0 > 1e-3:
            S.append(dict(start=t0, end=t1, scene=scene, fn=fn, grade=g or grade(), trans=trans))

    def ev(key, kind, who=None):
        for e in tl.meta.get(key, {}).get("events", []):
            if e.get("kind") == kind and (who is None or e.get("who") == who or e.get("state") == who):
                return e["t"]
        return None

    def hs(t0, t1, view, g, trans=(0, 0.0), **kw):
        add(t0, t1, "opera", house_fn(view, t1 - t0, **kw), g, trans)

    G_HOUSE = grade(exposure=1.1, temp=0.25, vignette=0.55, bloom=0.6)
    G_COLD = grade(exposure=1.0, temp=-0.1, vignette=0.55, bloom=0.55, sat=0.85)
    A_VILLAGE = 1   # p[0].y is the pan in the village, the camera drift in the rooms
    A_ROOMS = 1

    def curtain_falls(t_down, g=G_HOUSE):
        """The act ends: the house, the curtain coming down on the stage."""
        def f(tl, t, lt):
            drop = ease_io((t - t_down) / 4.4)
            p = opera_params(tl, (0.0, 2.15, -13.5), (0.0, 3.4, 4.0), 1.3, 0.0, 0.06, 0.4, 0.0, curtain=0.88 + 0.12 * drop,
                             t=t)
            p[7, 1] = 1.0
            return p, {}, []
        add(t_down - 1.2, t_down + 5.0, "opera", f, g, (0, 1.2))

    def curtain_rises(t0, t_up, view="stalls", g=G_HOUSE, **kw):
        """The prelude's last bars: the curtain rises on an empty, lit stage; the scene dissolves in."""
        wash0 = kw.pop("wash", 0.4)
        hs(t0, t_up, view, g, curtain=lambda tl, t: 1.0 - 0.45 * ease((t - (t_up - 3.5)) / 3.5),
           wash=lambda tl, t: wash0 + 0.4 * ease((t - (t_up - 3.5)) / 3.0), **kw)

    # ------------------------------------------------------------------ prologue and Act I prelude
    T0, T1 = sec["P0"]
    app, hush = c("P0.applause"), c("P0.hush")

    def prologue(tl, t, lt):
        k = ease_io((t - T0) / (T1 - T0))
        house = lerp(0.85, 0.08, ease((t - (app - 4.0)) / 5.0))
        wash = lerp(0.15, 0.38, ease((t - hush) / 3.0))
        p = opera_params(tl, lerp3((0.0, 2.05, -19.0), (0.0, 2.1, -15.0), k), (0.0, 4.2, 2.0), 1.2, 0.0, house, wash,
                         0.0, curtain=1.0, t=t)
        p[3, 0] = 0.0
        return p, {}, []
    add(T0, T1, "opera", prologue, G_HOUSE)

    T0, T1 = sec["P1"]
    q = {k: c(f"P1.{k}") for k in ("refrain", "vittorio_far", "marco", "allegro", "wedding", "tutti", "shadow",
                                    "village")}
    hs(T0, q["refrain"], "pit", G_HOUSE)
    hs(q["refrain"], q["vittorio_far"], "stalls", G_HOUSE, wash=0.45)
    hs(q["vittorio_far"], q["marco"], "dome", G_COLD, cold=0.6, ripple=0.5)
    hs(q["marco"], q["allegro"], "tiers", G_HOUSE, (0, 0.6))
    a1, a2 = q["allegro"] + 19.5, q["allegro"] + 34.5
    hs(q["allegro"], a1, "pit", G_HOUSE, reverse=True)
    hs(a1, a2, "curtain", G_HOUSE, wash=lambda tl, t: 0.25 + 0.45 * tl.score_env(t))
    hs(a2, q["wedding"], "box", G_HOUSE)
    hs(q["wedding"], q["tutti"], "gallery", G_HOUSE, (0, 1.0), wash=0.55)
    hs(q["tutti"], q["shadow"], "apron", G_HOUSE, house=0.14)
    hs(q["shadow"], q["shadow"] + 37.0, "tiers", G_COLD, (0, 1.5), reverse=True, cold=0.45, wash=0.2)
    hs(q["shadow"] + 37.0, q["village"], "dome", G_COLD, cold=0.25, ripple=0.2)
    curtain_rises(q["village"], T1, "stalls", G_HOUSE, wash=0.45)

    # ------------------------------------------------------------------ Act I, scene 1: the square
    T0, T1 = sec["N1"]
    scn = c("N1.scene")
    E = lambda tl, t: fig(-0.1, ELENA_Y, 0.42, ease((t - (scn - 2.0)) / 2.5))
    M = lambda tl, t: fig(0.13, ELENA_Y, 0.45, ease((t - (scn - 1.0)) / 2.5))
    base = village_fn(0, T0, E, M, crowd=1.0, warmth=0.1, swifts=0.8)
    G = grade(temp=0.45, sat=1.05, exposure=1.05)
    d0, d1, d2 = c("N1.dance"), c("N1.trio"), c("N1.verse2")
    add(T0, d0, "village", framed(base, fr_wide(d0 - T0, 1.0, 1.12)), G, (0, 2.0))
    add(d0, d1, "village", framed(base, fr_wide(d1 - d0, 1.45, 1.5, -0.32, -0.12, -0.24, -0.12)), G)
    add(d1, d2, "village", framed(base, fr_wide(d2 - d1, 1.35, 1.42, 0.3, -0.1, 0.24, -0.1)), G)
    add(d2, scn - 4.0, "village", framed(base, fr_wide(scn - 4.0 - d2, 1.0, 1.16)), G)
    add(scn - 4.0, T1, "village", framed(base, fr_two(E, M, T1 - scn + 4.0)), G)

    T0, T1 = sec["N2"]
    ex = ev("N2", "exit", "marco") or T1 - 2.0
    E = lambda tl, t: fig(-0.14, ELENA_Y, 0.5, 1.0)

    def M(tl, t, ex=ex):
        w = ease((t - (ex - 16.0)) / 16.0)
        return (lerp(0.12, 0.42, w), lerp(ELENA_Y, -0.2, w), lerp(0.52, 0.18, w), 1.0 - 0.3 * w)
    T0n2 = T0
    base = village_fn(1, T0, E, M, crowd=lambda tl, t: 1.0 - ease((t - T0n2) / 80.0),
                      warmth=lambda tl, t: lerp(0.25, 0.45, (t - T0n2) / (T1 - T0n2)), swifts=0.6)
    G = grade(temp=0.45, sat=1.0)
    cover(add, tl, "N2", T0, ex - 16.0, "village", base, {"elena": E, "marco": M}, G, (0, 1.2), seed=2,
          angle_slot=A_VILLAGE)
    add(ex - 16.0, T1, "village", framed(base, fr_wide(T1 - ex + 16.0, 1.2, 1.0, 0.1, -0.05, 0.0, 0.0)), G)

    T0, T1 = sec["N3"]
    let_t = ev("N3", "letters") or T1 - 3.0
    E3 = lambda tl, t: fig(-0.42, ELENA_Y - 0.02, 0.55, 1.0)
    T0n3 = T0

    def M3(tl, t):
        k = ease_io((t - T0n3) / 9.0)
        return (lerp(0.07, 0.035, k), lerp(-0.112, -0.086, k), lerp(0.03, 0.012, k), 1.0 - ease((t - T0n3 - 6.0) / 3.0))
    base = village_fn(2, T0, E3, M3, crowd=0.0, warmth=0.8, letters=lambda tl, t: ease((t - let_t) / 2.0), swifts=0.5)
    G = grade(temp=0.6, sat=0.95)
    road = lambda dur: fr_wide(dur, 1.5, 1.66, 0.06, -0.08)      # the far end of the road, where he went
    add(T0, T0 + 12.0, "village", framed(base, fr_wide(12.0, 1.0, 1.04)), G, (0, 1.5))
    cover(add, tl, "N3", T0 + 12.0, T1, "village", base, {"elena": E3}, G, seed=3, vista=road, first=None,
          angle_slot=A_VILLAGE)

    T0, T1 = sec["I12"]
    T0i = T0
    base = village_fn(2, T0, E3, lambda tl, t: (0, 0, 0, 0), crowd=0.0,
                      warmth=lambda tl, t: 0.55 + 0.3 * math.cos(2 * math.pi * (t - T0i) / 42.0),
                      letters=lambda tl, t: 1.0 - ease((t - T0i - 30.0) / 20.0), swifts=0.8)
    add(T0, T0 + 42.0, "village", framed(base, fr_wide(42.0, 1.3, 1.0, -0.2, 0.0, 0.0, 0.0)), grade(temp=0.5, sat=0.95))
    add(T0 + 42.0, T1, "village", framed(base, road(T1 - T0 - 42.0)), grade(temp=0.55, sat=0.95))

    # ------------------------------------------------------------------ Act I, scene 2: the parlour, the church
    t_par = sec["R1"][0]
    hope = c("N4.hope")
    vit = ev("N5", "enter", "vittorio") or sec["N5"][1] - 30.0
    cab5 = c("N5.cabaletta")
    E0 = lambda tl, t: fig(0.22, ELENA_Y, 0.55, 1.0)
    Mo = lambda tl, t: fig(-0.32, ELENA_Y, 0.5, ease((t - t_par) / 2.0))
    base0 = rooms_fn(0, t_par, E0, second=Mo, portrait=lambda tl, t: ease((t - hope) / 3.0),
                     poses=lambda tl, t: (0.45 * ease((t - cab5) / 4.0), 4, 0, 0))
    G0 = grade(temp=0.3, sat=0.95, exposure=1.05)
    figs0 = {"elena": E0, "madre": Mo}
    cover(add, tl, "R1", *sec["R1"], "rooms", base0, figs0, G0, (1, 1.6), seed=4, angle_slot=A_ROOMS)
    cover(add, tl, "N4", *sec["N4"], "rooms", base0, figs0, G0, (0, 0.8), seed=5, angle_slot=A_ROOMS, first=None)
    cover(add, tl, "N5", sec["N5"][0], vit, "rooms", base0, figs0, G0, (0, 0.8), seed=6, angle_slot=A_ROOMS, first=None)
    # Vittorio comes to ask for her: the third figure, recast
    Vp = lambda tl, t: (lerp(0.62, 0.5, ease((t - vit) / 3.0)), ELENA_Y + 0.01, 0.57, ease((t - vit + 0.5) / 2.5))
    base0v = rooms_fn(0, t_par, E0, second=Mo, third=Vp, portrait=1.0, recast=1.0,
                      poses=lambda tl, t: (0.45, 4, 0, 0))
    add(vit, vit + 12.0, "rooms", framed(base0v, fr_wide(12.0, 1.0, 1.08)), G0)
    cover(add, tl, "N5", vit + 12.0, sec["N5"][1], "rooms", base0v, {"elena": E0, "vittorio": Vp}, G0, seed=7,
          angle_slot=A_ROOMS, first=None)

    T0, T1 = sec["N6"]
    wed, cool, vow = c("N6.wedding"), c("N6.cooling"), c("N6.vow")
    Ec = lambda tl, t: fig(-0.12, ELENA_Y, 0.5, 1.0)
    Vc = lambda tl, t: fig(0.12, ELENA_Y, 0.56, 1.0)
    vow_fn = church(0, elena=Ec, vittorio=Vc)
    add(T0, vow - 22.0, "church", framed(vow_fn, fr_wide(vow - 22.0 - T0, 1.0, 1.12)), grade(temp=0.45), (0, 1.2))
    add(vow - 22.0, wed, "church", framed(vow_fn, fr_two(Ec, Vc, wed - vow + 22.0, zmax=1.7)), grade(temp=0.45))
    rf2, bal, wz, gp = c("N6.refrain2"), c("N6.ballabile"), c("N6.waltz"), c("N6.galop")
    wed_fn = church(1, rise=lambda tl, t, lt: ease_io((t - wed) / 40.0),
                    bloom=lambda tl, t, lt: 0.55 + 0.45 * tl.score_env(t), crowd=lambda tl, t: 1.0,
                    petals=lambda tl, t: ease((t - rf2) / 2.0))
    GW = grade(temp=0.5, sat=1.1, exposure=1.08, bloom=0.75)
    dn = c("N6.dance")
    add(wed, dn, "church", wed_fn, GW, (2, 0.6))
    for i, (a, b) in enumerate([(dn, dn + 34.0), (dn + 34.0, dn + 68.0), (dn + 68.0, rf2)]):
        cx, cy, z = [(-0.38, -0.18, 1.6), (0.36, -0.16, 1.55), (0.0, 0.18, 1.35)][i]
        add(a, b, "church", framed(wed_fn, fr_wide(b - a, z, z * 1.06, cx, cy)), GW)
    add(rf2, bal, "church", framed(wed_fn, fr_wide(bal - rf2, 1.0, 1.1)), GW)
    for i, (a, b) in enumerate([(bal, wz), (wz, gp), (gp, cool)]):
        cx, cy, z = [(-0.3, -0.2, 1.5), (0.3, -0.18, 1.5), (0.0, 0.0, 1.05)][i]
        add(a, b, "church", framed(wed_fn, fr_wide(b - a, z, z * 1.08, cx, cy)), GW)
    add(cool, T1, "church", church(2, rise=lambda tl, t, lt: 1.0,
                                   bloom=lambda tl, t, lt: 0.5 * (1 - ease((t - cool) / 6.0)),
                                   cold=lambda tl, t, lt: ease((t - cool) / 8.0),
                                   crowd=lambda tl, t: 1.0 - ease((t - cool - 4.0) / 10.0)),
        grade(temp=-0.2, sat=0.75), (0, 0.4))

    # ------------------------------------------------------------------ Act I, scene 3: Verona
    T0, T1 = sec["I23"]
    t_ver = T0
    E1 = lambda tl, t: fig(-0.18, ELENA_Y, 0.52, 1.0)
    tom = lambda tl, t: 0.35 + 0.65 * tl.tone_level(t)
    base1 = rooms_fn(1, t_ver, E1, tommaso=tom, poses=(1, 0, 0, 0))
    G1 = grade(temp=-0.45, sat=0.8, exposure=0.95)
    add(T0, T0 + 40.0, "rooms", framed(base1, fr_wide(40.0, 1.0, 1.1)), G1, (1, 1.6))
    add(T0 + 40.0, T1, "rooms", framed(base1, fr_one(E1, T1 - T0 - 40.0, 1.3, 0.1)), G1, (0, 1.2))
    cover(add, tl, "N7", *sec["N7"], "rooms", base1, {"elena": E1}, G1, (0, 0.6), seed=8, first=None,
          angle_slot=A_ROOMS, vista=lambda dur: fr_wide(dur, 1.25, 1.35, 0.25, 0.1))
    T0, T1 = sec["N8"]
    blow, res, stretta = c("N8.blow"), c("N8.resolve"), c("N8.stretta")
    cdown = ev("N8", "curtain", "down") or T1 - 2.0
    T0n8 = T0
    V1 = lambda tl, t: fig(0.3, ELENA_Y, 0.58, ease((t - T0n8 - 2.0) / 2.5) * (1.0 - ease((t - (blow + 2.0)) / 1.5)))
    base8 = rooms_fn(1, t_ver, E1, second=V1, tommaso=tom,
                     vittorio=lambda tl, t: ease((t - T0n8) / 3.0) * (1 - ease((t - T0n8 - 5.0) / 2.0)),
                     door=lambda tl, t: ease((t - T0n8) / 1.0) * (1 - ease((t - T0n8 - 6.0) / 3.0)),
                     poses=lambda tl, t: (1.0 if t > res + 1.0 else 0.0, 0, 0, 0))
    G8 = grade(temp=-0.6, sat=0.7, exposure=0.9)
    cover(add, tl, "N8", T0, blow - 0.1, "rooms", base8, {"elena": E1, "vittorio": V1}, G8, (0, 0.6), seed=9,
          angle_slot=A_ROOMS)
    add(blow - 0.1, blow + 2.4, "abstract", abstract_fn(6, blow - 0.1, blow + 2.4,
                                                        a=lambda tl, t: ease((t - blow + 0.1) / 2.0)),
        grade(temp=-0.2, sat=0.6), (0, 0.04))
    G8b = grade(temp=-0.4, sat=0.8, exposure=1.0)
    add(blow + 2.4, stretta, "rooms", framed(base8, fr_one(E1, stretta - blow - 2.4, 1.4, 0.12)), G8b, (1, 0.8))
    cover(add, tl, "N8", stretta, cdown - 1.2, "rooms", base8, {"elena": E1}, G8b, seed=10, first=None, lo=10.0,
          hi=20.0, angle_slot=A_ROOMS)
    curtain_falls(cdown)

    # ------------------------------------------------------------------ the first interval
    T0, T1 = sec["E1"]

    def interval(key, t_from):
        T0, T1 = sec[key]
        app, hush = c(f"{key}.applause"), c(f"{key}.hush")
        up = lambda tl, t: lerp(0.1, 0.85, ease((t - (app + 1.0)) / 3.0))
        hs(t_from, T0 + 13.0, "apron", G_HOUSE, (0, 0.8), house=up, wash=0.2, baton=False)
        hs(T0 + 13.0, hush + 1.5, "box", G_HOUSE, house=0.85, wash=0.2, baton=False)
        hs(hush + 1.5, T1, "stalls", G_HOUSE, (0, 1.0), house=lambda tl, t: lerp(0.85, 0.1, ease((t - hush) / 5.0)),
           wash=0.3, baton=False)
    interval("E1", cdown + 5.0)

    # ------------------------------------------------------------------ Act II prelude
    T0, T1 = sec["P2"]
    bora, shadow = c("P2.bora"), c("P2.shadow")
    hs(T0, bora, "pit", G_HOUSE)
    hs(bora, shadow, "dome", G_COLD, (0, 1.0), cold=0.5, ripple=0.6)
    hs(shadow, T1 - 30.0, "tiers", G_COLD, (0, 1.0), cold=0.3, wash=0.25)
    curtain_rises(T1 - 30.0, T1, "stalls", G_COLD, cold=0.25, wash=0.3)

    # ------------------------------------------------------------------ Act II, scene 1: the station
    T0, T1 = sec["N9"]
    dep = c("N9.depart")
    E9 = lambda tl, t: fig(-0.2, ELENA_Y, 0.5, 1.0 - ease((t - (dep - 4.0)) / 2.0))
    base9 = night_fn(0, E9, train=lambda tl, t: min(1.0, max(0.0, (t - dep) / 10.5)), steam=0.75)
    G9 = grade(temp=-0.1, sat=0.9)
    cover(add, tl, "N9", T0, dep - 6.0, "night", base9, {"elena": E9}, G9, (0, 2.0), seed=11,
          vista=lambda dur: fr_wide(dur, 1.3, 1.4, 0.3, 0.0))
    add(dep - 6.0, T1, "night", framed(base9, fr_wide(T1 - dep + 6.0, 1.12, 1.0)), G9)
    T0, T1 = sec["I2J"]
    add(T0, T1, "night", night_fn(1, lambda tl, t: (0, 0, 0, 0), route=lambda tl, t: ease_io((t - T0) / (T1 - T0 - 3.0))),
        grade(temp=-0.2, sat=0.95), (0, 0.8))

    # ------------------------------------------------------------------ Act II, scene 2: Trieste
    T0, T1 = sec["N10"]
    vis, wake = c("N10.vision"), c("N10.wake")
    sleeper = lambda tl, t: fig(-0.2, -0.3, 0.5, 1.0)
    base10 = rooms_fn(2, T0, sleeper, poses=(3, 0, 0, 0),
                      vittorio=lambda tl, t: ease((t - vis + 0.5) / 3.0) * (1 - ease((t - wake + 0.6) / 0.6)))
    G10 = grade(temp=-0.7, sat=0.75, exposure=0.95)
    add(T0, vis - 8.0, "rooms", framed(base10, fr_wide(vis - 8.0 - T0, 1.0, 1.25, 0.0, 0.0, -0.12, -0.1)), G10, (1, 1.0))
    add(vis - 8.0, wake - 0.2, "rooms", framed(base10, fr_wide(wake - vis + 7.8, 1.05, 1.35, 0.05, 0.0)), G10)
    sitting = lambda tl, t: fig(-0.15, -0.36, 0.5, 1.0)
    base10w = rooms_fn(2, T0, sitting, poses=(4, 0, 0, 0))
    add(wake - 0.2, wake + 2.0, "rooms", base10w, grade(temp=-0.5, sat=0.6, exposure=1.3), (2, 0.4))
    add(wake + 2.0, T1, "rooms", framed(base10w, fr_one(sitting, T1 - wake - 2.0, 1.45, 0.1)), G10, (0, 1.0))

    t_tr = sec["R2"][0]
    dav = c("R2.davide")
    niv = ev("R2", "enter", "nives") or t_tr + 14.0
    r2end = sec["R2"][1]
    coda12 = c("N12.coda")
    E3r = lambda tl, t: fig(lerp(-0.3, -0.12, ease((t - coda12) / 8.0)), ELENA_Y, 0.55, 1.0)
    D3 = lambda tl, t: fig(lerp(lerp(0.62, 0.2, ease((t - dav + 0.5) / 3.0)), 0.1, ease((t - coda12) / 8.0)), ELENA_Y,
                           0.58, ease((t - dav + 0.5) / 1.0))
    N3f = lambda tl, t: fig(0.45, ELENA_Y + 0.05, 0.48, ease((t - niv) / 1.5) * (1 - ease((t - (r2end - 4.0)) / 2.5)))
    base3 = rooms_fn(3, t_tr, E3r, second=D3, third=N3f, tommaso=tom, amber=lambda tl, t: ease((t - dav + 1.0) / 3.0),
                     extra=1.0)
    G3 = grade(temp=0.35, sat=1.0, exposure=1.05)
    figs3 = {"elena": E3r, "davide": D3, "nives": N3f}
    cover(add, tl, "R2", *sec["R2"], "rooms", base3, figs3, G3, (2, 0.6), seed=12, angle_slot=A_ROOMS)
    cover(add, tl, "N11", *sec["N11"], "rooms", base3, figs3, G3, (0, 0.8), seed=13, first=None, angle_slot=A_ROOMS)
    cover(add, tl, "N12", *sec["N12"], "rooms", base3, figs3, G3, (0, 0.8), seed=14, first=None, angle_slot=A_ROOMS)

    # ------------------------------------------------------------------ the sea, and the street (scene 3)
    T0, T1 = sec["I2S"]
    nobody = lambda tl, t: (0, 0, 0, 0)
    base_s = street_fn(T0, nobody, nobody, passers=0.4, daylight=0.8)
    GS = grade(temp=-0.15, sat=0.85, exposure=1.0)
    sea = lambda dur: fr_wide(dur, 1.6, 1.9, 0.0, 0.06)
    add(T0, T0 + 45.0, "street", framed(base_s, fr_wide(45.0, 1.0, 1.12)), GS, (1, 1.2))
    add(T0 + 45.0, T1, "street", framed(base_s, sea(T1 - T0 - 45.0)), GS, (0, 1.5))
    t_st = sec["N13"][0]
    meet = ev("N13", "enter", "marco") or c("N13.meet")
    cur14 = c("N14.curtain")
    cdown2 = ev("N14", "curtain", "down") or sec["N14"][1] - 2.0
    Es = lambda tl, t: fig(lerp(lerp(-0.6, -0.3, ease((t - t_st) / 8.0)), -0.16, ease((t - meet) / 3.0)), ELENA_Y, 0.5,
                           1.0 - ease((t - (cur14 + 6.0)) / 4.0))
    Ms = lambda tl, t: fig(lerp(lerp(0.62, 0.16, ease((t - meet) / 4.0)), 0.6, ease((t - (cur14 + 2.0)) / 10.0)), ELENA_Y,
                           0.52, ease((t - meet) / 1.0) * (1.0 - ease((t - (cur14 + 9.0)) / 3.0)))
    base13 = street_fn(t_st, Es, Ms, passers=0.6, daylight=0.7)
    figs13 = {"elena": Es, "marco": Ms}
    cover(add, tl, "N13", *sec["N13"], "street", base13, figs13, GS, (0, 1.5), seed=15, vista=sea)
    cover(add, tl, "N14", sec["N14"][0], cur14, "street", base13, figs13, GS, (0, 0.8), seed=16, first=None, vista=sea)
    add(cur14, cur14 + 16.0, "street", framed(base13, fr_wide(16.0, 1.15, 1.0)), GS)
    add(cur14 + 16.0, cdown2 - 1.2, "street", framed(base13, sea(cdown2 - 1.2 - cur14 - 16.0)), GS, (0, 2.0))
    curtain_falls(cdown2)

    interval("E2", cdown2 + 5.0)

    # ------------------------------------------------------------------ Intermezzo and Act III prelude
    T0, T1 = sec["IM1"]
    warp = [n["t"] for n in tl.motif.get("marco_warped", []) if T0 <= n["t"] < T1]
    w0 = min(warp) - 1.0 if warp else T0 + 0.6 * (T1 - T0)
    amber = lambda tl, t: 0.35 + 0.25 * tl.score_env(t)
    k1 = T0 + (w0 - T0) / 3.0
    k2 = T0 + 2.0 * (w0 - T0) / 3.0
    hs(T0, k1, "curtain", G_HOUSE, (0, 1.0), wash=amber)
    hs(k1, k2, "box", G_HOUSE, wash=amber)
    hs(k2, w0, "stalls", G_HOUSE, wash=amber)
    hs(w0, w0 + 26.0, "tiers", G_COLD, (0, 1.0), cold=0.4, ripple=0.3, wash=0.25)
    hs(w0 + 26.0, T1, "curtain", G_HOUSE, (0, 1.5), reverse=True, wash=amber)
    T0, T1 = sec["P3"]
    child = c("P3.child")
    hs(T0, child, "pit", G_HOUSE)
    hs(child, T1 - 22.0, "dome", G_HOUSE, (0, 1.0))
    curtain_rises(T1 - 22.0, T1, "stalls", G_HOUSE)

    # ------------------------------------------------------------------ Act III, scene 1
    T0, T1 = sec["R3"]
    evs3 = {e["where"]: e["t"] for e in tl.meta["R3"].get("events", []) if e.get("kind") == "location"}
    home, pier = evs3.get("montage_home", T0 + 30.0), evs3.get("montage_pier", T0 + 72.8)
    add(T0, home, "abstract", abstract_fn(0, T0, home, a=0.25, prog=lambda tl, t: 0.35 * (t - T0) / (home - T0)),
        grade(temp=0.0, sat=0.8), (0, 2.0))
    add(home, pier, "rooms", framed(base3, fr_two(E3r, D3, pier - home, zmax=1.4)), G3, (0, 1.2))
    add(pier, T1, "abstract", abstract_fn(0, pier, T1, a=lambda tl, t: lerp(0.4, 1.0, (t - pier) / (T1 - pier)),
                                          prog=lambda tl, t: 0.35 + 0.65 * (t - pier) / (T1 - pier)),
        grade(temp=0.0, sat=0.8), (0, 1.2))

    T0, T1 = sec["N15"]
    Mm = lambda tl, t: fig(0.15, ELENA_Y, 0.52, 1.0)
    base15 = street_fn(T0, nobody, Mm, passers=0.15, daylight=0.4)
    G15 = grade(temp=-0.25, sat=0.8, exposure=0.92)
    cover(add, tl, "N15", T0, T1, "street", base15, {"marco": Mm}, G15, (0, 1.0), seed=17, vista=sea)

    T0, T1 = sec["N16"]
    von = c("N16.vision")
    offs = [e["t"] for e in tl.meta["N16"]["events"] if e.get("kind") == "vision"]
    voff = offs[-1] if len(offs) > 1 else von + 26.6
    goes = c("N16.goes")
    Ed = lambda tl, t: fig(lerp(-0.18, -0.62, ease((t - goes) / 9.0)), ELENA_Y, 0.48, 1.0 - ease((t - goes - 6.0) / 3.0))
    Vd = lambda tl, t: fig(0.2, ELENA_Y, 0.62, 1.0)
    dusk = church(3, elena=Ed, vittorio=Vd,
                  vision=lambda tl, t: ease((t - von) / 3.0) * (1 - ease((t - voff) / 1.5)))
    G16 = grade(temp=-0.4, sat=0.8, exposure=0.95)
    add(T0, von - 3.0, "church", framed(dusk, fr_wide(von - 3.0 - T0, 1.0, 1.15)), G16, (1, 1.0))
    add(von - 3.0, voff + 2.0, "church", framed(dusk, fr_two(Ed, Vd, voff - von + 5.0, zmax=1.6)), G16)
    add(voff + 2.0, goes, "church", framed(dusk, fr_one(Ed, goes - voff - 2.0, 1.5)), G16)
    add(goes, T1, "church", framed(dusk, fr_wide(T1 - goes, 1.1, 1.0)), G16)

    T0, T1 = sec["N17"]
    gl, held = c("N17.gladius"), c("N17.held_chord")
    de = next((l["start"] for l in tl.lines if T0 <= l["start"] < T1 and "desolat" in l["it"].lower()), gl + 10.0)
    st_fn = stabat_fn(T0, T1, gl, de, held)
    G17 = grade(temp=0.15, sat=0.85, exposure=1.0, bloom=0.7)
    rng = random.Random(18)
    cuts = cut_times(tl, T0, held - 4.0, rng, 26.0, 48.0)
    views = [(1.0, 1.08, 0.0, 0.0), (1.35, 1.45, -0.28, -0.04), (1.3, 1.4, 0.3, 0.02), (1.15, 1.3, 0.0, 0.08)]
    for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
        z0, z1, cx, cy = views[i % len(views)]
        add(a, b, "stabat", framed(st_fn, fr_wide(b - a, z0, z1, cx, cy)), G17, (1, 1.2) if i == 0 else (0, 1.5))
    add(held - 4.0, T1, "stabat", framed(st_fn, fr_wide(T1 - held + 4.0, 1.0, 1.1)), G17, (0, 1.5))

    # ------------------------------------------------------------------ Act III, scene 2: the trattoria, the bedside
    T0, T1 = sec["R4"]
    nv, run = c("R4.nives"), c("R4.run")
    Et = lambda tl, t: fig(-0.18, -0.38, 0.45, 1.0)
    Dt = lambda tl, t: fig(0.18, -0.38, 0.47, 1.0)
    Nt = lambda tl, t: fig(0.52, ELENA_Y, 0.5, ease((t - nv) / 0.4))
    base4 = rooms_fn(4, T0, Et, second=Dt, third=Nt, amber=0.8, poses=(4, 4, 0, 0),
                     extra=lambda tl, t: ease((t - nv + 0.3) / 0.3))
    G4 = grade(temp=0.45, sat=1.0, exposure=1.05)
    cover(add, tl, "R4", T0, nv - 0.4, "rooms", base4, {"elena": Et, "davide": Dt}, G4, (1, 1.0), seed=19, lo=12.0,
          hi=26.0, angle_slot=A_ROOMS)
    add(nv - 0.4, run, "rooms", framed(base4, fr_wide(run - nv + 0.4, 1.0, 1.05)), G4)
    add(run, T1, "abstract", abstract_fn(1, run, T1), grade(temp=0.2), (0, 0.15))

    T0, T1 = sec["N18"]
    death = c("N18.death")
    Eb = lambda tl, t: fig(-0.26, ELENA_Y, 0.42, 1.0)
    Db = lambda tl, t: fig(0.26, ELENA_Y, 0.45, 1.0)
    base5 = rooms_fn(5, T0, Eb, second=Db, amber=0.25, poses=(2, 2, 0, 0.6),
                     tommaso=lambda tl, t: (0.2 + 0.8 * tl.tone_level(t)) * (1.0 - ease((t - death + 1.0) / 2.5)))
    G5 = grade(temp=-0.1, sat=0.75, exposure=0.95)
    cover(add, tl, "N18", T0, death - 6.0, "rooms", base5, {"elena": Eb, "davide": Db}, G5, (0, 0.4), seed=20,
          angle_slot=A_ROOMS)
    add(death - 6.0, T1, "rooms", framed(base5, fr_wide(T1 - death + 6.0, 1.3, 1.0)), G5)

    # ------------------------------------------------------------------ Act III, scene 3
    T0, T1 = sec["N19"]
    req, last, gone = c("N19.requiem"), c("N19.last_tone"), c("N19.tone_gone")
    Ef = lambda tl, t: fig(-0.05, ELENA_Y, 0.4, 1.0)
    fun = church(4, elena=Ef, vittorio=lambda tl, t: (0, 0, 0, 0), crowd=lambda tl, t: 1.0,
                 motes=lambda tl, t: ease((t - last) / 5.0))
    G19 = grade(temp=-0.25, sat=0.6, exposure=0.95)
    add(T0, req, "church", framed(fun, fr_wide(req - T0, 1.0, 1.12)), G19, (1, 2.0))
    mid = 0.5 * (req + last)
    add(req, mid, "church", framed(fun, fr_wide(mid - req, 1.5, 1.6, 0.0, -0.14)), G19)
    add(mid, last, "church", framed(fun, fr_one(Ef, last - mid, 1.5)), G19)
    add(last, gone, "church", framed(fun, fr_wide(gone - last, 1.3, 1.22, 0.0, -0.08, 0.0, 0.14)), G19)
    add(gone, gone + 45.0, "church", framed(fun, fr_wide(45.0, 1.1, 1.0)), G19)
    add(gone + 45.0, T1, "church", framed(fun, fr_one(Ef, T1 - gone - 45.0, 1.35, 0.1)), G19, (0, 1.5))

    T0, T1 = sec["IM2"]
    Ee = lambda tl, t: fig(-0.2, ELENA_Y, 0.42, 1.0)
    base5e = rooms_fn(5, T0, Ee, amber=0.08, poses=(4, 0, 0, 0.3))
    GE = grade(temp=-0.2, sat=0.6, exposure=0.95)
    k1, k2 = T0 + 0.45 * (T1 - T0), T0 + 0.75 * (T1 - T0)
    add(T0, k1, "rooms", framed(base5e, fr_wide(k1 - T0, 1.0, 1.25)), GE, (1, 1.5))
    add(k1, k2, "rooms", framed(base5e, fr_one(Ee, k2 - k1, 1.45)), GE)
    add(k2, T1, "rooms", framed(base5e, fr_wide(T1 - k2, 1.2, 1.0)), GE)

    T0, T1 = sec["N20"]
    slide, lo_, rd, conf = c("N20.letter_slide"), c("N20.letter_open"), c("N20.read"), c("N20.confession")
    letters = sorted((l for l in tl.lines if l["style"] == "letter"), key=lambda l: l["start"])
    n_lines = float(len(letters)) if letters else 6.0
    t_hi = rd

    def reveal(tl, t):
        for k, l in enumerate(letters):
            if t < l["end"]:
                return (k + max(0.0, (t - l["start"]) / (l["end"] - l["start"]))) / n_lines
        return 1.0
    Ea = lambda tl, t: fig(-0.42, ELENA_Y, 0.52, 1.0)
    Da = lambda tl, t: fig(lerp(0.42, 0.55, ease((t - slide - 0.5) / 2.0) * (1 - ease((t - slide - 5.0) / 2.5))),
                           ELENA_Y, 0.56, 1.0)
    base7 = rooms_fn(7, T0, Ea, second=Da, amber=0.35,
                     door=lambda tl, t: 0.85 + 0.15 * math.exp(-((t - slide - 0.6) / 1.2) ** 2))
    G7 = grade(temp=0.1, sat=0.85, exposure=0.95)
    add(T0, lo_, "rooms", framed(base7, fr_wide(lo_ - T0, 1.0, 1.08)), G7, (1, 1.2))
    add(lo_, t_hi, "abstract", abstract_fn(2, lo_, t_hi, a=reveal, lines=n_lines), grade(temp=0.2, sat=0.85), (1, 1.2))
    add(t_hi, conf, "rooms", framed(base7, fr_one(Da, conf - t_hi, 1.5)), G7, (1, 1.0))
    add(conf, conf + 30.0, "abstract", abstract_fn(3, conf, conf + 30.0), grade(temp=0.0, sat=0.9), (0, 1.0))
    cover(add, tl, "N20", conf + 30.0, T1, "rooms", base7, {"elena": Ea, "davide": Da}, G7, (0, 1.0), seed=21,
          angle_slot=A_ROOMS)

    T0, T1 = sec["N21"]
    hs_, he, door = c("N21.heat_start"), c("N21.heat_end"), c("N21.door")
    Dx = lambda tl, t: fig(lerp(0.42, 0.62, ease((t - (door - 6.0)) / 4.8)), ELENA_Y, 0.56,
                           1.0 - ease((t - door + 1.2) / 1.0))
    base7b = rooms_fn(7, T0, Ea, second=Dx, amber=lambda tl, t: 0.5 * (1 - ease((t - door) / 1.0)),
                      door=lambda tl, t: 0.85 * (1 - ease((t - door + 0.3) / 0.6)))
    cover(add, tl, "N21", T0, hs_, "rooms", base7b, {"elena": Ea, "davide": Dx}, G7, (0, 0.8), seed=22, lo=6.0,
          angle_slot=A_ROOMS)
    add(hs_, he, "abstract", abstract_fn(4, hs_, he, a=lambda tl, t: ease((t - hs_) / 2.0) * (1 - ease((t - he + 1.5) / 1.5)),
                                         b=lambda tl, t: 0.5 + 0.5 * math.cos(2 * math.pi * 2.0 * (t - hs_))),
        grade(temp=0.0, sat=0.9), (0, 0.3))
    cover(add, tl, "N21", he, door - 6.0, "rooms", base7b, {"elena": Ea, "davide": Dx}, G7, (0, 0.6), seed=23,
          first=None, angle_slot=A_ROOMS)
    add(door - 6.0, door + 3.0, "rooms", framed(base7b, fr_wide(9.0, 1.15, 1.0)), G7)
    add(door + 3.0, T1, "rooms", framed(base7b, fr_one(Ea, T1 - door - 3.0, 1.5, 0.12)), G7)

    T0, T1 = sec["R5"]
    mex = ev("R5", "exit", "marco") or T0 + 50.0
    Er = lambda tl, t: fig(-0.3, ELENA_Y, 0.52, 1.0)
    Mr = lambda tl, t: (lerp(0.2, 0.05, ease((t - mex) / 12.0)), lerp(ELENA_Y + 0.02, -0.12, ease((t - mex) / 12.0)),
                        lerp(0.5, 0.15, ease((t - mex) / 12.0)), 1.0 - ease((t - mex - 8.0) / 4.0))
    base_r5 = street_fn(T0, Er, Mr, passers=0.0, daylight=0.2)
    GR5 = grade(temp=-0.35, sat=0.75, exposure=0.78)
    cover(add, tl, "R5", T0, mex, "street", base_r5, {"elena": Er, "marco": Mr}, GR5, (1, 1.2), seed=24, lo=10.0,
          hi=22.0)
    add(mex, mex + 8.0, "street", framed(base_r5, fr_wide(8.0, 1.0, 1.1)), GR5)
    add(mex + 8.0, T1, "abstract", abstract_fn(5, mex + 8.0, T1, a=lambda tl, t: ease((t - mex - 8.0) / (T1 - mex - 10.0))),
        grade(temp=-0.1, sat=0.8), (0, 1.0))

    # ------------------------------------------------------------------ N. 22: the empty room, then the stage
    T0, T1 = sec["N22"]
    q = {k: c(f"N22.{k}") for k in ("dolly", "sing", "wide", "echo", "vittorio3", "closeup", "climax", "vittorio4",
                                     "close", "final_chord", "curtain", "black")}
    En = lambda tl, t: fig(-0.05, ELENA_Y, 0.55, 1.0)
    base6 = rooms_fn(6, T0, En, fly=lambda tl, t: ease((t - (q["dolly"] - 2.4)) / 2.4))
    G6 = grade(temp=-0.3, sat=0.7, exposure=0.95)
    add(T0, q["dolly"] - 10.0, "rooms", framed(base6, fr_wide(q["dolly"] - 10.0 - T0, 1.0, 1.12)), G6, (1, 1.2))
    add(q["dolly"] - 10.0, q["dolly"], "rooms", framed(base6, fr_one(En, 10.0, 1.35, -0.2)), G6)
    sg, dl = q["sing"], q["dolly"]
    GD = grade(temp=0.35, exposure=0.88, bloom=0.55, vignette=0.5)

    def establish(tl, t, lt):
        """The house revealed: from the gallery, down to the back of the stalls, the stage in golden light."""
        k = ease_io(lt / (sg - 5.0 - dl))
        pos = lerp3((0.0, 9.8, -22.0), (0.22, 2.1, -17.2), k)
        tgt = lerp3((0.0, 5.2, -2.0), (0.0, 4.35, 4.0), k)
        return opera_params(tl, pos, tgt, lerp(1.0, 1.15, k), 0.0, 0.22, 0.85, 0.35, t=t), {}, []
    add(dl, sg - 5.0, "opera", establish, GD, (0, 1.0))

    def dolly(tl, t, lt):
        """REQUIRED SHOT 1: the slow dolly-in on the stage in golden light; past the conductor."""
        pos = spline(DOLLY_POS_FULL, lt)
        tx, ty, tz, fl = spline(DOLLY_LOOK_FULL, lt)
        lift = ease((t - sg + 1.6) / 2.2)
        cue = ease((t - sg + 2.6) / 1.4) * (1.0 - ease((t - sg - 5.0) / 2.5))
        p = opera_params(tl, pos, (tx, ty, tz), fl, lift, 0.22, 0.85, 0.35 + 0.3 * min(1.0, lt / 36.0), t=t, cue=cue)
        return p, {}, []
    add(sg - 5.0, q["wide"], "opera", dolly, GD)

    def wide(tl, t, lt):
        """REQUIRED SHOT 2: the audience, tier upon tier; her voice in the dome; the chandeliers."""
        k = ease_io(lt / (q["echo"] - q["wide"]))
        pos = lerp3((2.9, 3.3, 7.8), (1.4, 3.9, 7.2), k)
        tgt = lerp3((0.0, 6.2, -14.0), (0.0, 8.2, -13.0), k)
        p = opera_params(tl, pos, tgt, 0.82, 0.95, 0.55, 0.8, 0.35, t=t, ripple=0.3 * tl.voice_env(t))
        return p, {}, []
    GWd = grade(temp=0.3, exposure=1.05, bloom=0.7, vignette=0.45)
    add(q["wide"], q["echo"], "opera", wide, GWd)

    def dome(tl, t, lt):
        """Her voice echoing in the dome: from the stage, looking up past the chandelier; Vittorio's cold."""
        k = ease_io(lt / (q["closeup"] - q["echo"]))
        pos = lerp3((-1.2, 3.0, 5.6), (-0.6, 3.4, 5.2), k)
        tgt = lerp3((0.0, 11.0, -9.0), (0.0, 15.5, -11.0), k)
        cold = ease((t - q["vittorio3"]) / 3.0) * (1.0 - ease((t - q["closeup"] + 1.5) / 1.5))
        ripple = 0.7 * (1 - ease((t - q["vittorio3"]) / 2.0)) * ease((t - q["echo"]) / 1.0) + 0.3 * tl.voice_env(t)
        return opera_params(tl, pos, tgt, 0.75, 0.95, 0.55, 0.8, 0.35, t=t, cold=cold, ripple=ripple), {}, []
    add(q["echo"], q["closeup"], "opera", dome, GWd, (0, 0.8))

    def closeup(t_a, t_b):
        from . import portrait

        def f(tl, t, lt):
            tension = 0.35 + 0.55 * ease((t - (q["climax"] - 7.0)) / 7.0)
            tension = tension * (1 - 0.6 * ease((t - q["vittorio4"]) / 2.5)) + 0.3 * tl.voice_env(t)
            tension = float(np.clip(tension, 0.15, 1.0))
            lvl = int(round(np.clip(tl.jaw(t), 0, 1) * (portrait.JAW_LEVELS - 1)))
            cold = ease((t - q["vittorio4"]) / 1.5) * (1 - ease((t - q["vittorio4"] - 5.0) / 1.0))
            p = portrait.uniforms(lt, t_b - t_a, tension, cold, 2 * math.pi * (1.15 + 0.45 * tension) * t)
            A, B = portrait.jaw_layers(lvl)
            return p, {}, [("uFace", ("portraitA", lvl, A)), ("uHairTex", ("portraitB", lvl, B))]
        return f
    GC = grade(temp=0.25, exposure=1.0, bloom=0.55, vignette=0.55, grain=0.03)
    cu = q["closeup"]
    add(cu, cu + 34.0, "closeup", closeup(cu, cu + 34.0), GC)

    def wings(tl, t, lt):
        """From the wings, at her height: hands lifted, the conductor below, the house beyond."""
        k = ease_io(lt / 18.0)
        pos = lerp3((5.2, 2.9, 5.6), (4.6, 2.85, 5.0), k)
        return opera_params(tl, pos, (0.0, 2.55, 3.4), 1.25, 0.95, 0.22, 0.85, 0.45, t=t), {}, []
    add(cu + 34.0, cu + 52.0, "opera", wings, GD, (0, 0.6))
    add(cu + 52.0, q["close"], "closeup", closeup(cu + 52.0, q["close"]), GC, (0, 0.6))
    cs, fc, cur = q["close"], q["final_chord"], q["curtain"]

    def back(tl, t, lt):
        k = ease_io(lt / 40.0)
        pos = lerp3((0.0, 10.4, -21.5), (0.0, 9.6, -19.5), k)
        return opera_params(tl, pos, (0.0, 3.6, 4.0), 1.4, 1.0, 0.18, 0.75, 0.6, t=t), {}, []
    add(cs, cs + 40.0, "opera", back, GWd, (0, 1.0))

    def pit_low(tl, t, lt):
        k = ease_io(lt / (fc - 18.0 - cs - 40.0))
        pos = lerp3((-2.2, 1.25, -2.4), (2.2, 1.3, -2.6), k)
        return opera_params(tl, pos, (0.0, 2.6, 4.0), 1.5, 1.0, 0.2, 0.8, 0.5, t=t), {}, []
    add(cs + 40.0, fc - 18.0, "opera", pit_low, GD, (0, 1.0))

    def final(tl, t, lt):
        k = ease_io(lt / (cur - fc + 18.0))
        pos = lerp3((0.1, 2.5, 0.8), (0.0, 2.15, -13.5), k)
        tgt = lerp3((0.0, 2.5, 4.0), (0.0, 3.2, 4.0), k)
        lift = 1.0 - ease((t - fc + 2.5) / 3.0)
        wash = lerp(0.85, 0.08, ease(lt / 14.0))
        spot = lerp(0.4, 1.0, ease(lt / 12.0))
        cue = ease((t - fc + 1.5) / 1.0)
        return opera_params(tl, pos, tgt, lerp(1.9, 1.3, k), lift * 0.95, lerp(0.22, 0.05, k), wash, spot, t=t,
                            cue=cue), {}, []
    add(fc - 18.0, cur, "opera", final, grade(temp=0.3, exposure=1.0, bloom=0.65, vignette=0.55), (0, 0.6))

    def curtain(tl, t, lt):
        drop = ease_io(lt / 4.4)
        return opera_params(tl, (0.0, 2.15, -13.5), (0.0, 3.2, 4.0), 1.3, 0.0, 0.06, 0.22, 1.0, curtain=drop, t=t), {}, []
    add(cur, q["black"], "opera", curtain, grade(temp=0.3, exposure=1.0, vignette=0.6))
    add(q["black"], T1, "abstract", abstract_fn(7, q["black"], T1), grade(temp=0.1), (1, 0.8))

    # ------------------------------------------------------------------ the calls
    T0, T1 = sec["F0"]
    app = c("F0.applause")
    add(T0, app, "abstract", abstract_fn(7, T0, app), grade(temp=0.1))
    hs(app, T1, "apron", G_HOUSE, (1, 1.2), house=lambda tl, t: lerp(0.1, 0.85, ease((t - app) / 4.0)), wash=0.3,
       baton=False)

    S.sort(key=lambda s: s["start"])
    return S


def check(S, total):
    """Gaps and overlaps in the shot list (seconds)."""
    probs = []
    if S[0]["start"] > 1e-6:
        probs.append(("gap", 0.0, S[0]["start"]))
    for a, b in zip(S, S[1:]):
        if abs(b["start"] - a["end"]) > 1e-6:
            probs.append(("gap" if b["start"] > a["end"] else "overlap", a["end"], b["start"], a["scene"], b["scene"]))
    if abs(S[-1]["end"] - total) > 1e-3:
        probs.append(("end", S[-1]["end"], total))
    return probs
