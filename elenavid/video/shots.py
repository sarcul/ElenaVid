"""The shot list: what is on screen at every moment, with camera moves, blocking and grade.

Each shot: (start, end, shader key, params function, grade dict, transition in).
Params functions return (uP array, extra uniforms dict, textures list).
"""
from __future__ import annotations

import math

import numpy as np

from .timeline import ease, ease_io, lerp, lerp3

SCENES = {   # shader key -> fragment file
    "opera": "opera.frag", "closeup": "closeup.frag", "village": "village.frag",
    "street": "street.frag", "rooms": "rooms.frag", "church": "church.frag", "night": "night.frag",
    "stabat": "stabat.frag", "abstract": "abstract.frag",
}

ELENA_Y = -0.43


def P():
    return np.zeros((24, 4), dtype="f4")


# --------------------------------------------------------------------------- grades
G_DEFAULT = dict(exposure=1.0, temp=0.0, sat=1.0, contrast=1.05, lift=(0.0, 0.0, 0.0), vignette=0.45,
                 grain=0.035, bloom=0.5, aberr=0.0012)


def grade(**kw):
    g = dict(G_DEFAULT)
    g.update(kw)
    return g


# --------------------------------------------------------------------------- opera house
def opera_params(tl, cam_pos, cam_tgt, fl, lift, house, wash, spot, curtain=0.0, mode=0,
                 cold=0.0, ripple=0.0, t=0.0, cue=0.0):
    p = P()
    p[0, :3] = cam_pos
    p[1, :3] = cam_tgt
    p[1, 3] = fl
    p[2] = (lift, 0.5 + 0.5 * math.sin(t * 1.3), -0.06 - 0.06 * lift, 0.4 * math.sin(t * 0.37))
    p[3] = (spot, wash, house, curtain)
    p[4] = (min(1.5, 0.25 + 1.2 * tl.voice_env(t)), cold, ripple, 0.0)
    p[5] = (mode, 0, 0, 0)
    off, ph, bi = tl.baton(t)
    p[6] = (off[0], off[1], off[2], 1.0)
    p[7, 0] = cue
    return p


def shot_prologue(tl, t, lt):
    # the closed curtain seen from the stalls; house lights dim as the applause dies
    k = ease_io(lt / 26.0)
    pos = lerp3((0.0, 2.05, -19.0), (0.0, 2.1, -15.5), k)
    tgt = (0.0, 4.2, 2.0)
    house = lerp(0.85, 0.08, ease((t - 9.5) / 5.0))
    wash = lerp(0.15, 0.35, ease((t - 16.0) / 3.0))
    p = opera_params(tl, pos, tgt, 1.2, 0.0, house, wash, 0.0, curtain=1.0, t=t)
    p[3, 0] = 0.0
    return p, {}, []


def spline(keys, x):
    """Catmull-Rom through time-keyed values (tuples), clamped at the ends: a steady glide."""
    if x <= keys[0][0]:
        return keys[0][1]
    if x >= keys[-1][0]:
        return keys[-1][1]
    i = max(j for j in range(len(keys) - 1) if keys[j][0] <= x)
    (t1, p1), (t2, p2) = keys[i], keys[i + 1]
    p0 = keys[i - 1][1] if i > 0 else tuple(2 * a - b for a, b in zip(p1, p2))
    p3 = keys[i + 2][1] if i + 2 < len(keys) else tuple(2 * b - a for a, b in zip(p1, p2))
    u = (x - t1) / (t2 - t1)
    u2, u3 = u * u, u * u * u
    return tuple(0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u2 + (-a + 3 * b - 3 * c + d) * u3)
                 for a, b, c, d in zip(p0, p1, p2, p3))


# the dolly-in, keyed in shot-local seconds: from the back of the stalls, over the heads, down to
# the conductor's eye line so he stands in silhouette against the lit stage, past his left shoulder
# (his raised hand slides by the lens), then rising over the pit to her
DOLLY_POS = [(0.0, (0.25, 2.05, -16.5)), (7.0, (0.35, 1.98, -12.6)), (12.0, (0.48, 1.86, -9.6)),
             (15.5, (0.62, 1.62, -7.3)), (17.5, (0.72, 1.52, -5.95)), (20.0, (0.82, 1.5, -4.3)),
             (22.0, (0.8, 1.58, -3.0)), (24.5, (0.6, 1.88, -1.6)), (27.0, (0.32, 2.2, -0.2)),
             (30.0, (0.12, 2.4, 0.7))]
DOLLY_LOOK = [(0.0, (0.0, 4.4, 4.0, 1.15)), (13.0, (0.0, 3.2, 4.0, 1.35)), (20.0, (0.0, 2.75, 4.0, 1.5)),
              (30.0, (0.0, 2.6, 4.0, 2.0))]


def shot_dolly(tl, t, lt):
    """REQUIRED SHOT 1: slow dolly-in on the stage bathed in golden light; past the conductor."""
    pos = spline(DOLLY_POS, lt)
    tx, ty, tz, fl = spline(DOLLY_LOOK, lt)
    sing = tl.c("s11.sing")
    lift = ease((t - sing + 1.6) / 2.2)                      # hands rise as the orchestra swells
    cue = ease((t - sing + 2.6) / 1.4) * (1.0 - ease((t - sing - 5.0) / 2.5))   # he gives her the breath
    p = opera_params(tl, pos, (tx, ty, tz), fl, lift, 0.22, 0.85, 0.35 + 0.3 * lt / 30.0, t=t, cue=cue)
    return p, {}, []


def shot_wide(tl, t, lt):
    """REQUIRED SHOT 2: the wide audience shot; her voice in the dome; then the offstage voice."""
    k = lt / 30.0
    pos = lerp3((2.9, 3.3, 7.8), (1.4, 3.9, 7.2), ease_io(k))
    tgt = lerp3((0.0, 6.2, -14.0), (0.0, 8.2, -13.0), ease_io(k))
    cold = ease((t - tl.c("s11.vittorio3")) / 3.0) * (1.0 - ease((t - tl.c("s11.closeup") + 1.5) / 1.5))
    ripple = 0.7 * (1 - ease((t - tl.c("s11.vittorio3")) / 2.0)) + 0.3 * tl.voice_env(t)
    p = opera_params(tl, pos, tgt, 0.82, 0.95, 0.55, 0.8, 0.35, t=t, cold=cold, ripple=ripple)
    return p, {}, []


def shot_final(tl, t, lt):
    """Pull back to the stage; the light narrows to a single spot; she lowers her hands."""
    k = ease_io(lt / 16.5)
    pos = lerp3((0.1, 2.5, 0.8), (0.0, 2.15, -13.5), k)
    tgt = lerp3((0.0, 2.5, 4.0), (0.0, 3.2, 4.0), k)
    fl = lerp(1.9, 1.3, k)
    lift = 1.0 - ease((t - tl.c("s11.final_chord") + 2.5) / 3.0)
    wash = lerp(0.85, 0.08, ease(lt / 12.0))
    spot = lerp(0.4, 1.0, ease(lt / 10.0))
    cue = ease((t - tl.c("s11.final_chord") + 1.5) / 1.0)   # the left hand closes the last chord
    p = opera_params(tl, pos, tgt, fl, lift * 0.95, lerp(0.22, 0.05, k), wash, spot, t=t, cue=cue)
    return p, {}, []


def shot_curtain(tl, t, lt):
    pos = (0.0, 2.15, -13.5)
    tgt = (0.0, 3.2, 4.0)
    drop = ease_io(lt / 4.4)
    p = opera_params(tl, pos, tgt, 1.3, 0.0, 0.06, 0.22, 1.0, curtain=drop, t=t)
    return p, {}, []


# --------------------------------------------------------------------------- the close-up
_CLOSE = {}


def shot_closeup(tl, t, lt):
    from . import portrait
    climax = tl.c("s11.climax")
    v4 = tl.c("s11.vittorio4")
    tension = 0.35 + 0.55 * ease((t - (climax - 7.0)) / 7.0)
    tension = tension * (1 - 0.6 * ease((t - v4) / 2.5)) + 0.3 * tl.voice_env(t)
    tension = float(np.clip(tension, 0.15, 1.0))
    jaw = tl.jaw(t)
    lvl = int(round(np.clip(jaw, 0, 1) * (portrait.JAW_LEVELS - 1)))
    cold = ease((t - v4) / 1.5) * (1 - ease((t - v4 - 5.0) / 1.0))
    pulse = 2 * math.pi * (1.15 + 0.45 * tension) * t
    p = portrait.uniforms(lt, 26.0, tension, cold, pulse)
    A, B = portrait.jaw_layers(lvl)
    return p, {}, [("uFace", ("portraitA", lvl, A)), ("uHairTex", ("portraitB", lvl, B))]


# --------------------------------------------------------------------------- 2D scenes
def fig(x, y=ELENA_Y, h=0.5, a=1.0):
    return (x, y, h, a)


def shot_village(mode):
    def f(tl, t, lt):
        p = P()
        s01 = tl.c("s01.start")
        pan = 0.02 * math.sin(lt * 0.15) + 0.004 * lt
        if mode == 0:
            p[0] = (0, pan, 1.0, 0.1)
            p[1] = fig(-0.1, ELENA_Y, 0.42, ease((t - (tl.c("s01.duet") - 4.0)) / 3.0))
            p[2] = fig(0.12, ELENA_Y, 0.45, ease((t - (tl.c("s01.duet") - 4.0)) / 3.0))
            p[3] = (0.0, 0.8, 0, 0)
        elif mode == 1:
            leave = tl.c("s01.marco_leaves")
            w = ease((t - leave) / 3.0)
            p[0] = (1, pan, 1.0 - ease(lt / 6.0), 0.25)
            p[1] = fig(-0.14, ELENA_Y, 0.5, 1.0)
            p[2] = (lerp(0.12, 0.42, w), lerp(ELENA_Y, -0.2, w), lerp(0.52, 0.18, w), 1.0 - 0.3 * w)
            p[3] = (0.0, 0.6, 0, 0)
        else:
            letters = ease((t - tl.c("s01.letters")) / 2.0)
            p[0] = (2, pan, 0.0, 0.8)
            p[1] = fig(-0.42, ELENA_Y - 0.02, 0.55, 1.0)
            # Marco: a dark speck walking away up the white road, gone before the letters rise
            k = ease_io(lt / 9.0)
            p[2] = (lerp(0.07, 0.035, k), lerp(-0.112, -0.086, k), lerp(0.03, 0.012, k), 1.0 - ease((lt - 6.0) / 3.0))
            p[3] = (letters, 0.7, 0, 0)
        return p, {}, []
    return f


def shot_street(tl, t, lt):
    p = P()
    pan = 0.004 * lt
    p[0] = (pan, 0, 0, 0)
    meet = ease(lt / 3.0)
    p[1] = fig(lerp(-0.45, -0.16, meet), ELENA_Y, 0.5, 1.0)
    p[2] = fig(lerp(0.5, 0.16, meet), ELENA_Y, 0.52, 1.0)
    p[3] = (0.6, 0.7, 0, 0)
    return p, {}, []


def rooms(mode, **kw):
    def f(tl, t, lt):
        p = P()
        p[0] = (mode, 0.01 * math.sin(lt * 0.12), kw.get("amber", lambda tl, t: 0.0)(tl, t),
                kw.get("fly", lambda tl, t: 0.0)(tl, t))
        p[1] = kw.get("elena", lambda tl, t: fig(-0.25, ELENA_Y, 0.55, 1.0))(tl, t)
        p[2] = kw.get("second", lambda tl, t: (0, 0, 0, 0))(tl, t)
        p[3] = kw.get("third", lambda tl, t: (0, 0, 0, 0))(tl, t)
        p[4] = (kw.get("tommaso", lambda tl, t: 0.0)(tl, t), kw.get("vittorio", lambda tl, t: 0.0)(tl, t),
                kw.get("portrait", lambda tl, t: 0.0)(tl, t), kw.get("door", lambda tl, t: 0.0)(tl, t))
        p[5] = kw.get("poses", lambda tl, t: (0, 0, 0, 0))(tl, t)
        p[6] = (kw.get("extra", lambda tl, t: 0.0)(tl, t), 0, 0, 0)
        return p, {}, []
    return f


def church(mode, **kw):
    def f(tl, t, lt):
        p = P()
        p[0] = (mode, kw.get("rise", lambda tl, t, lt: 0.0)(tl, t, lt),
                kw.get("bloom", lambda tl, t, lt: 0.0)(tl, t, lt),
                kw.get("cold", lambda tl, t, lt: 0.0)(tl, t, lt))
        p[1] = kw.get("elena", lambda tl, t: fig(-0.1, ELENA_Y, 0.5, 1.0))(tl, t)
        p[2] = kw.get("vittorio", lambda tl, t: fig(0.12, ELENA_Y, 0.55, 1.0))(tl, t)
        p[3] = (kw.get("crowd", lambda tl, t: 0.0)(tl, t), 0, 0, 0)
        p[4] = (kw.get("petals", lambda tl, t: 0.0)(tl, t), t * 1.1, kw.get("vision", lambda tl, t: 0.0)(tl, t),
                kw.get("motes", lambda tl, t: 0.0)(tl, t))
        return p, {}, []
    return f


def night(mode, **kw):
    def f(tl, t, lt):
        p = P()
        p[0] = (mode, kw.get("train", lambda tl, t: 0.0)(tl, t), 0.7, 0)
        p[1] = fig(-0.2, ELENA_Y, 0.5, 1.0)
        p[2] = (kw.get("route", lambda tl, t, lt: 0.0)(tl, t, lt), 1.0, 0, 0)
        return p, {}, []
    return f


def shot_stabat(tl, t, lt):
    p = P()
    s = tl.c("s07.stabat")
    gl = tl.c("s07.gladius")
    de = tl.c("s07.desolatum")
    held = tl.c("s07.held_chord")
    p[0] = (ease(lt / 5.0), 1.0 - ease((lt - 1.5) / 3.0), ease((t - held + 1.0) / 2.5), lt * 0.004)
    p[1] = (math.exp(-((t - gl) / 0.9) ** 2), ease((t - de) / 1.5) * (1 - ease((t - de - 3.5) / 2.0)), 0, 0)
    return p, {}, []


def abstract(mode, **kw):
    def f(tl, t, lt):
        p = P()
        p[0] = (mode, kw.get("prog", lambda tl, t, lt: 0.0)(tl, t, lt), 0, 0)
        p[1] = (kw.get("a", lambda tl, t, lt: 0.0)(tl, t, lt), kw.get("b", lambda tl, t, lt: 0.0)(tl, t, lt), 0, 0)
        tex = []
        if mode == 2:
            tex = [("uLetter", ("letter", 0, None))]
        return p, {}, tex
    return f


# --------------------------------------------------------------------------- the shot list
def build(tl):
    c = tl.c
    S = []

    def add(t0, t1, scene, fn, g=None, trans=(0, 0.0)):
        S.append(dict(start=t0, end=t1, scene=scene, fn=fn, grade=g or grade(), trans=trans))

    # Prologue and title
    add(0.0, 26.0, "opera", shot_prologue, grade(exposure=1.1, temp=0.25, vignette=0.55, bloom=0.6))
    # Act I
    add(26.0, 36.0, "village", shot_village(0), grade(temp=0.45, sat=1.05, exposure=1.05), (1, 1.2))
    add(36.0, 48.0, "village", shot_village(1), grade(temp=0.45, sat=1.0), (0, 1.0))
    add(48.0, 60.0, "village", shot_village(2), grade(temp=0.6, sat=0.95), (0, 1.5))
    add(60.0, 80.0, "rooms", rooms(0, elena=lambda tl, t: fig(0.22, ELENA_Y, 0.55, 1.0),
                                   second=lambda tl, t: fig(-0.32, ELENA_Y, 0.5, 1.0),
                                   portrait=lambda tl, t: ease((t - c("s02.hope")) / 3.0),
                                   poses=lambda tl, t: (0, 4, 0, 0)),
        grade(temp=0.3, sat=0.95, exposure=1.05), (1, 1.6))
    add(80.0, 88.41, "church", church(0, elena=lambda tl, t: fig(-0.12, ELENA_Y, 0.5, 1.0),
                                      vittorio=lambda tl, t: fig(0.12, ELENA_Y, 0.56, 1.0)),
        grade(temp=0.45), (1, 1.2))
    add(88.41, 117.5, "church", church(1, rise=lambda tl, t, lt: ease_io(lt / 29.0),
                                       bloom=lambda tl, t, lt: 0.55 + 0.45 * tl.score_env(t),
                                       crowd=lambda tl, t: 1.0, petals=lambda tl, t: ease((t - c("s02.refrain")) / 2.0)),
        grade(temp=0.5, sat=1.1, exposure=1.08, bloom=0.75), (2, 0.6))
    add(117.5, 122.0, "church", church(2, rise=lambda tl, t, lt: 1.0, bloom=lambda tl, t, lt: 0.5 * (1 - lt / 4.5),
                                       cold=lambda tl, t, lt: ease(lt / 4.0), crowd=lambda tl, t: 1.0 - ease((t - 117.5) / 4.0)),
        grade(temp=-0.2, sat=0.75), (0, 0.4))
    add(122.0, 142.77, "rooms", rooms(1, elena=lambda tl, t: fig(-0.18, ELENA_Y, 0.52, 1.0),
                                      tommaso=lambda tl, t: 0.35 + 0.65 * tl.tone_level(t)),
        grade(temp=-0.45, sat=0.8, exposure=0.95), (1, 1.4))
    add(142.77, 150.27, "rooms", rooms(1, elena=lambda tl, t: fig(-0.18, ELENA_Y, 0.52, 1.0),
                                       tommaso=lambda tl, t: 0.4,
                                       vittorio=lambda tl, t: ease((t - c("s03.vittorio") + 0.5) / 6.0)),
        grade(temp=-0.6, sat=0.7, exposure=0.9), (0, 0.3))
    add(150.27, 152.77, "abstract", abstract(6, a=lambda tl, t, lt: ease(lt / 2.0)),
        grade(temp=-0.2, sat=0.6), (0, 0.04))
    add(152.77, 162.0, "rooms", rooms(1, elena=lambda tl, t: fig(-0.15, ELENA_Y, 0.53, 1.0),
                                      tommaso=lambda tl, t: 0.4 + 0.6 * tl.tone_level(t),
                                      poses=lambda tl, t: (1.0 if t > c("s03.resolve") + 1.0 else 0.0, 0, 0, 0)),
        grade(temp=-0.4, sat=0.8, exposure=1.0), (1, 0.8))
    # Act II
    add(162.0, 179.5, "night", night(0, train=lambda tl, t: 0.0),
        grade(temp=-0.1, sat=0.9, exposure=1.0), (3, 2.2))
    add(179.5, 184.0, "night", night(1, route=lambda tl, t, lt: ease_io(lt / 4.2)),
        grade(temp=-0.2, sat=0.95), (0, 0.8))
    add(184.0, 209.5, "rooms", rooms(2, elena=lambda tl, t: fig(-0.2, -0.3, 0.5, 1.0),
                                     vittorio=lambda tl, t: ease((t - c("s05.vision") + 0.5) / 3.0) *
                                     (1 - ease((t - c("s05.wake") + 0.6) / 0.6)),
                                     poses=lambda tl, t: (3, 0, 0, 0)),
        grade(temp=-0.7, sat=0.75, exposure=0.95), (1, 1.0))
    add(209.5, 211.5, "rooms", rooms(2, elena=lambda tl, t: fig(-0.2, -0.3, 0.5, 1.0),
                                     poses=lambda tl, t: (3, 0, 0, 0)),
        grade(temp=-0.5, sat=0.6, exposure=1.3), (2, 0.4))
    add(211.5, 246.0, "rooms", rooms(3, elena=lambda tl, t: fig(-0.3, ELENA_Y, 0.55, 1.0),
                                     second=lambda tl, t: fig(lerp(0.55, 0.18, ease((t - c("s05.morning") + 0.5) / 2.5)),
                                                              ELENA_Y, 0.58, 1.0),
                                     tommaso=lambda tl, t: 0.4 + 0.6 * tl.tone_level(t),
                                     amber=lambda tl, t: ease((t - c("s05.davide") + 1.0) / 3.0),
                                     extra=lambda tl, t: 1.0),
        grade(temp=0.35, sat=1.0, exposure=1.05), (2, 0.6))
    add(246.0, 276.0, "street", shot_street, grade(temp=-0.15, sat=0.85, exposure=1.0), (1, 1.2))
    # Act III
    add(276.0, 290.0, "abstract", abstract(0, prog=lambda tl, t, lt: lt / 14.0, a=lambda tl, t, lt: ease(lt / 14.0)),
        grade(temp=0.0, sat=0.8), (3, 2.2))
    add(290.0, 314.0, "church", church(3, elena=lambda tl, t: fig(-0.18, ELENA_Y, 0.48, 1.0),
                                       vittorio=lambda tl, t: fig(0.2, ELENA_Y, 0.62, 1.0),
                                       vision=lambda tl, t: ease((t - c("s07.vision")) / 3.0) *
                                       (1 - ease((t - c("s07.stabat") + 1.5) / 1.5))),
        grade(temp=-0.4, sat=0.8, exposure=0.95), (1, 1.0))
    add(314.0, 364.0, "stabat", shot_stabat, grade(temp=0.15, sat=0.85, exposure=1.0, bloom=0.7), (1, 1.2))
    add(364.0, 374.0, "rooms", rooms(4, elena=lambda tl, t: fig(-0.18, -0.38, 0.45, 1.0),
                                     second=lambda tl, t: fig(0.18, -0.38, 0.47, 1.0),
                                     amber=lambda tl, t: 0.8, poses=lambda tl, t: (4, 4, 0, 0),
                                     extra=lambda tl, t: ease((t - c("s08.nives") + 0.3) / 0.3)),
        grade(temp=0.45, sat=1.0, exposure=1.05), (1, 1.0))
    add(374.0, 378.0, "abstract", abstract(1, prog=lambda tl, t, lt: lt / 4.0), grade(temp=0.2), (0, 0.15))
    add(378.0, 408.0, "rooms", rooms(5, elena=lambda tl, t: fig(-0.26, ELENA_Y, 0.42, 1.0),
                                     second=lambda tl, t: fig(0.26, ELENA_Y, 0.45, 1.0),
                                     # his light ebbs as the tone fails to return; it is not an event
                                     tommaso=lambda tl, t: (0.2 + 0.8 * tl.tone_level(t)) *
                                     (1.0 - ease((t - c("s08.death") + 1.0) / 2.5)),
                                     poses=lambda tl, t: (2, 2, 0, 0.6), amber=lambda tl, t: 0.25),
        grade(temp=-0.1, sat=0.75, exposure=0.95), (0, 0.4))
    add(408.0, 430.0, "church", church(4, elena=lambda tl, t: fig(-0.05, ELENA_Y, 0.4, 1.0),
                                       vittorio=lambda tl, t: (0, 0, 0, 0), crowd=lambda tl, t: 1.0,
                                       motes=lambda tl, t: ease((t - c("s09.last_tone")) / 5.0)),
        grade(temp=-0.25, sat=0.6, exposure=0.95), (1, 2.0))
    add(430.0, 443.0, "abstract", abstract(2, prog=lambda tl, t, lt: lt / 13.0, a=lambda tl, t, lt: ease((lt - 2.5) / 3.0)),
        grade(temp=0.2, sat=0.85), (1, 1.2))
    add(443.0, 452.0, "abstract", abstract(3, prog=lambda tl, t, lt: ease_io(lt / 9.0)), grade(temp=0.0, sat=0.9), (0, 0.6))
    add(452.0, 458.0, "abstract", abstract(4, prog=lambda tl, t, lt: lt / 6.0,
                                           a=lambda tl, t, lt: math.sin(math.pi * min(1, lt / 6.0)),
                                           b=lambda tl, t, lt: 0.5 + 0.5 * math.cos(2 * math.pi * 2.0 * lt)),
        grade(temp=0.0, sat=0.9), (0, 0.3))
    add(458.0, 471.5, "rooms", rooms(7, elena=lambda tl, t: fig(-0.42, ELENA_Y, 0.52, 1.0),
                                     second=lambda tl, t: fig(0.42, ELENA_Y, 0.56, 1.0 - ease((t - c("s10.door") + 1.2) / 1.0)),
                                     door=lambda tl, t: 1.0 - ease((t - c("s10.door") + 0.3) / 0.6),
                                     amber=lambda tl, t: 0.5 * (1 - ease((t - c("s10.door")) / 1.0))),
        grade(temp=0.1, sat=0.85, exposure=0.95), (0, 0.6))
    add(471.5, 476.0, "abstract", abstract(5, prog=lambda tl, t, lt: lt / 4.5, a=lambda tl, t, lt: ease(lt / 4.5)),
        grade(temp=-0.1, sat=0.8), (0, 0.5))
    # the final aria
    add(476.0, 490.0, "rooms", rooms(6, elena=lambda tl, t: fig(-0.05, ELENA_Y, 0.55, 1.0),
                                     fly=lambda tl, t: ease((t - (c("s11.dolly") - 2.4)) / 2.4)),
        grade(temp=-0.3, sat=0.7, exposure=0.95), (1, 1.0))
    add(490.0, 520.0, "opera", shot_dolly, grade(temp=0.35, exposure=0.88, bloom=0.55, vignette=0.5), (0, 0.8))
    add(520.0, 550.0, "opera", shot_wide, grade(temp=0.3, exposure=1.05, bloom=0.7, vignette=0.45), (0, 0.0))
    add(550.0, 576.0, "closeup", shot_closeup, grade(temp=0.25, exposure=1.0, bloom=0.55, vignette=0.55,
                                                     grain=0.03), (0, 0.0))
    add(576.0, 592.5, "opera", shot_final, grade(temp=0.3, exposure=1.0, bloom=0.65, vignette=0.55), (0, 0.6))
    add(592.5, 597.0, "opera", shot_curtain, grade(temp=0.3, exposure=1.0, vignette=0.6), (0, 0.0))
    add(597.0, 600.0, "abstract", abstract(7), grade(temp=0.1), (1, 0.8))
    return S


TITLES = [
    # (t0, t1, main, sub, sub2)
    (18.2, 24.4, "Elena", "tragedia lirica in tre atti", None),
    (26.6, 30.6, "Atto primo", "La piazza", "Veneto  ·  estate 1948"),
    (60.8, 64.2, "", "Il salotto, la chiesa", "primavera 1950"),
    (122.6, 126.0, "", "La casa di Verona", "autunno 1953"),
    (162.8, 166.6, "Atto secondo", "La stazione", "notte"),
    (211.9, 215.3, "", "Trieste", "1955"),
    (246.6, 249.9, "", "Una strada di Trieste", "1957"),
    (276.6, 280.0, "Atto terzo", "Mesi", "Trieste  ·  1958"),
    (597.2, 600.0, "Elena", "tragedia lirica in tre atti", "libretto, music, sound and image made in code"),
]
