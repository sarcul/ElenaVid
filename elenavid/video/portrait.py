"""The close-up portrait: a full profile facing the follow-spot (left), lit low-key in closeup.frag.

Python rasterises the silhouette, fine features and a smooth height field into textures. Static
layers (hair, lashes, brow, ear) are built once; the jaw is quantised into cached poses. The neck's
sternocleidomastoid and jugular are drawn analytically in the shader so they can tighten and pulse
every frame with her voice.

Face units: head (crown to chin) about 0.24; canvas covers X0..X1, Y0..Y1.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, zoom

X0, X1, Y0, Y1 = -0.26, 0.38, -0.46, 0.21
RES = 1200
PX = RES / (X1 - X0)
H_RES = int((Y1 - Y0) * PX)
JAW_LEVELS = 12


def to_px(pts, ss=1):
    p = np.asarray(pts, dtype=float)
    return np.stack([(p[:, 0] - X0) * PX * ss, (Y1 - p[:, 1]) * PX * ss], axis=1)


def catmull(points, per_seg=8, closed=True):
    P = np.array(points, dtype=float)
    n = len(P)
    out = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        if closed:
            p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        else:
            p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n - 1)]
        for k in range(per_seg):
            s = k / per_seg
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3))
    if not closed:
        out.append(P[-1])
    return np.array(out)


def silhouette(j):
    return [
        (0.035, 0.162), (-0.012, 0.158), (-0.045, 0.145), (-0.064, 0.122), (-0.074, 0.096),
        (-0.0785, 0.074), (-0.0765, 0.058), (-0.081, 0.046), (-0.091, 0.031), (-0.1005, 0.0175),
        (-0.0975, 0.0095), (-0.0885, 0.0065), (-0.0815, 0.0035), (-0.0835, -0.0055),
        (-0.0895, -0.0135), (-0.0875, -0.0185), (-0.0795, -0.0215 - 0.004 * j),
        (-0.0745, -0.0255 - 0.012 * j), (-0.0815, -0.0285 - 0.024 * j), (-0.0855, -0.0345 - 0.026 * j),
        (-0.0775, -0.0435 - 0.03 * j), (-0.0805, -0.0545 - 0.034 * j), (-0.0815, -0.0645 - 0.035 * j),
        (-0.0705, -0.0775 - 0.034 * j), (-0.046, -0.0855 - 0.025 * j), (-0.02, -0.088 - 0.012 * j),
        (-0.008, -0.096), (-0.015, -0.118), (-0.0175, -0.135), (-0.012, -0.165), (-0.004, -0.205),
        (-0.022, -0.255), (-0.065, -0.32), (-0.13, -0.40), (-0.2, -0.47),
        (0.39, -0.47), (0.33, -0.33), (0.2, -0.245), (0.118, -0.17), (0.096, -0.11),
        (0.094, -0.06), (0.1, -0.01), (0.112, 0.04), (0.109, 0.09), (0.088, 0.135),
    ]


def hair_shape():
    return [(-0.062, 0.128), (-0.04, 0.155), (0.0, 0.178), (0.055, 0.177), (0.1, 0.158),
            (0.128, 0.13), (0.15, 0.1), (0.172, 0.088), (0.19, 0.06), (0.188, 0.025),
            (0.168, 0.0), (0.14, -0.012), (0.118, -0.03), (0.1, -0.052), (0.086, -0.048),
            (0.074, -0.02), (0.06, 0.02), (0.052, 0.045), (0.035, 0.058), (0.01, 0.07),
            (-0.012, 0.082), (-0.035, 0.096), (-0.052, 0.11)]


def ear_shape():
    return [(0.022, 0.035), (0.03, 0.05), (0.045, 0.052), (0.054, 0.04), (0.055, 0.02),
            (0.05, 0.0), (0.042, -0.014), (0.032, -0.02), (0.026, -0.012), (0.026, 0.005),
            (0.021, 0.018)]


def _poly_mask(pts, ss=2, per=8):
    img = Image.new("L", (RES * ss, H_RES * ss), 0)
    ImageDraw.Draw(img).polygon([tuple(p) for p in to_px(catmull(pts, per), ss)], fill=255)
    return np.array(img.resize((RES, H_RES), Image.LANCZOS)).astype(np.float32) / 255.0


def _gauss(cx, cy, sx, sy, amp):
    ys, xs = np.mgrid[0:H_RES, 0:RES]
    c = to_px([(cx, cy)])[0]
    return amp * np.exp(-(((xs - c[0]) / (sx * PX)) ** 2 + ((ys - c[1]) / (sy * PX)) ** 2))


def _blur(a, sigma_units):
    """Large Gaussian blur done at reduced resolution."""
    s = sigma_units * PX
    if s < 6:
        return gaussian_filter(a, s)
    f = 4
    small = zoom(a, 1 / f, order=1)
    small = gaussian_filter(small, s / f)
    big = zoom(small, (a.shape[0] / small.shape[0], a.shape[1] / small.shape[1]), order=1)
    return big[: a.shape[0], : a.shape[1]]


@lru_cache(maxsize=1)
def static_layers():
    ss = 2
    rng = np.random.default_rng(7)
    dark = Image.new("L", (RES * ss, H_RES * ss), 0)
    dd = ImageDraw.Draw(dark)
    lid = catmull([(-0.071, 0.0435), (-0.063, 0.0405), (-0.054, 0.0402), (-0.045, 0.0425)], 6, closed=False)
    dd.line([tuple(p) for p in to_px(lid, ss)], fill=235, width=int(0.0016 * PX * ss), joint="curve")
    for k in range(15):
        s = k / 14
        base = lid[int(s * (len(lid) - 1))]
        ln = 0.0055 + 0.0045 * math.sin(math.pi * s)
        tip = base + np.array([-0.0048 - 0.0018 * s, -ln])
        mid = base + np.array([-0.0011, -ln * 0.55])
        curve = catmull([tuple(base), tuple(mid), tuple(tip)], 5, closed=False)
        dd.line([tuple(p) for p in to_px(curve, ss)], fill=255, width=max(1, int(0.00065 * PX * ss)))
    crease = catmull([(-0.068, 0.0495), (-0.058, 0.0505), (-0.048, 0.049)], 6, closed=False)
    dd.line([tuple(p) for p in to_px(crease, ss)], fill=80, width=int(0.0011 * PX * ss))
    for k in range(80):
        s = rng.random()
        x = -0.075 + 0.045 * s
        y = 0.0655 + 0.0065 * math.sin(math.pi * s) - 0.001 * s
        a = np.array([x, y + rng.normal(0, 0.0011)])
        b = a + np.array([0.0045, 0.0011 + rng.normal(0, 0.0005)])
        dd.line([tuple(p) for p in to_px([a, b], ss)], fill=int(140 + 90 * rng.random()),
                width=max(1, int(0.0006 * PX * ss)))
    c = to_px([(-0.0875, 0.0105)], ss)[0]
    dd.ellipse([c[0] - 0.0035 * PX * ss, c[1] - 0.0015 * PX * ss, c[0] + 0.0035 * PX * ss,
                c[1] + 0.0015 * PX * ss], fill=170)
    # the ear's inner folds
    for curve_pts, wgt in (([(0.028, 0.03), (0.04, 0.044), (0.049, 0.035), (0.048, 0.012), (0.04, -0.006)], 120),
                           ([(0.033, 0.016), (0.04, 0.026), (0.043, 0.012), (0.037, 0.0)], 160)):
        cv = catmull(curve_pts, 6, closed=False)
        dd.line([tuple(p) for p in to_px(cv, ss)], fill=wgt, width=int(0.0016 * PX * ss), joint="curve")
    dark = np.array(dark.resize((RES, H_RES), Image.LANCZOS)).astype(np.float32) / 255.0
    dark = gaussian_filter(dark, 0.5)
    ear = _poly_mask(ear_shape(), per=6)
    ear_h = gaussian_filter(ear, 0.004 * PX) * 0.08
    hmask = _poly_mask(hair_shape(), per=8)
    st = Image.new("L", (RES, H_RES), 0)
    ds = ImageDraw.Draw(st)
    for k in range(520):
        s0 = rng.random()
        start = np.array([-0.058 + 0.12 * s0, 0.122 - 0.11 * s0 + rng.normal(0, 0.006)])
        ctrl = start + np.array([0.06, 0.045 - 0.03 * s0])
        end = np.array([0.155, 0.06]) + rng.normal(0, 0.016, 2)
        curve = catmull([tuple(start), tuple(ctrl), tuple(end)], 10, closed=False)
        ds.line([tuple(p) for p in to_px(curve)], fill=int(50 + 205 * rng.random()), width=1)
    # chignon coils
    for k in range(60):
        r = 0.018 + 0.014 * rng.random()
        a0 = rng.uniform(0, 2 * math.pi)
        arc = [(0.158 + r * math.cos(a0 + u), 0.045 + 0.8 * r * math.sin(a0 + u))
               for u in np.linspace(0, 2.2, 12)]
        ds.line([tuple(p) for p in to_px(arc)], fill=int(80 + 170 * rng.random()), width=1)
    strands = np.array(st).astype(np.float32) / 255.0 * hmask
    hheight = _blur(hmask, 0.018) * hmask
    return dark, ear, ear_h, hmask, strands, hheight


@lru_cache(maxsize=JAW_LEVELS + 2)
def jaw_layers(level):
    j = level / (JAW_LEVELS - 1)
    dark_s, ear, ear_h, hmask, strands, hheight = static_layers()
    mask = _poly_mask(silhouette(j), per=10)
    h = 0.55 * _blur(mask, 0.03) + 0.45 * _blur(mask, 0.009)
    h += _gauss(-0.042, 0.022, 0.024, 0.018, 0.10)                 # cheekbone
    h += _gauss(-0.06, 0.068, 0.024, 0.006, 0.05)                  # brow
    h += _gauss(-0.056, 0.043, 0.013, 0.008, 0.07)                 # eyeball beneath the lid
    h += _gauss(-0.07, -0.06 - 0.035 * j, 0.012, 0.011, 0.05)      # chin
    h += _gauss(-0.083, -0.011, 0.007, 0.004, 0.035)               # upper lip
    h += _gauss(-0.082, -0.032 - 0.025 * j, 0.007, 0.005, 0.04)    # lower lip
    h += _gauss(0.002, -0.2, 0.02, 0.01, -0.03)                    # the hollow above the collarbone
    h = h * mask + ear_h
    ss = 2
    lips = Image.new("L", (RES * ss, H_RES * ss), 0)
    dl = ImageDraw.Draw(lips)
    up = catmull([(-0.0895, -0.0135), (-0.081, -0.0105), (-0.07, -0.0145), (-0.068, -0.0205),
                  (-0.0795, -0.0215 - 0.004 * j), (-0.0875, -0.0185)], 6)
    lo = catmull([(-0.0815, -0.0285 - 0.024 * j), (-0.0855, -0.0345 - 0.026 * j),
                  (-0.0775, -0.0405 - 0.028 * j), (-0.068, -0.0345 - 0.022 * j),
                  (-0.069, -0.0285 - 0.018 * j)], 6)
    dl.polygon([tuple(p) for p in to_px(up, ss)], fill=255)
    dl.polygon([tuple(p) for p in to_px(lo, ss)], fill=255)
    lips = gaussian_filter(np.array(lips.resize((RES, H_RES), Image.LANCZOS)).astype(np.float32) / 255.0, 1.0)
    dark = Image.new("L", (RES * ss, H_RES * ss), 0)
    if j > 0.05:
        cav = catmull([(-0.0795, -0.0215 - 0.004 * j), (-0.067, -0.023 - 0.01 * j),
                       (-0.066, -0.029 - 0.02 * j), (-0.0815, -0.0285 - 0.024 * j),
                       (-0.0745, -0.0255 - 0.012 * j)], 6)
        ImageDraw.Draw(dark).polygon([tuple(p) for p in to_px(cav, ss)], fill=255)
    dark = np.maximum(dark_s, np.array(dark.resize((RES, H_RES), Image.LANCZOS)).astype(np.float32) / 255.0)
    face_mask = np.maximum(mask, ear)
    texA = np.stack([face_mask, np.clip(h, 0, 2) / 2.0, lips, dark], axis=-1).astype(np.float16)
    texB = np.stack([hmask, strands, hheight, ear], axis=-1).astype(np.float16)
    return texA, texB


def uniforms(lt, dur, tension, cold, pulse):
    P = np.zeros((24, 4), dtype="f4")
    push = lt / max(dur, 1.0)
    scale = 2.5 + 0.35 * push
    tilt = 0.05 + 0.12 * tension
    P[0] = (0.12 + 0.015 * math.sin(lt * 0.21), 0.02 + 0.01 * math.sin(lt * 0.33), scale, tilt)
    P[1] = (X0, Y0, X1, Y1)
    P[2] = (tension, cold, pulse, 1.0)
    P[3] = (0.033, -0.026, lt * 0.05, 0.0)
    # neck anatomy: sternocleidomastoid (mastoid to sternum) and the external jugular, which runs
    # from below the angle of the jaw obliquely down and back across the muscle to the clavicle
    P[4] = (0.036, -0.012, -0.006, -0.215)
    P[5] = (0.014, -0.074, 0.036, -0.205)
    return P
