"""The full opera's audio: five tiers rendered in segments (in parallel), overlap-added, then mixed and
mastered in a streaming pass. The film's mixer (elenavid.audio.mix) is untouched; it supplies the shared
constants (sends, gains, pans, generators, target levels) and the DSP helpers.

    ELENA_EDITION=full python -m elenavid.audio.mix_full [--workers=6] [--plan] [--only=3,7]

A segment is a run of whole sections (about five minutes) and renders its own reverb and event tails,
so overlap-adding segments is exact for everything linear. The non-linear stages (ducking, de-essing,
glue compression, loudness, the true-peak limiter) run afterwards on the whole programme, in chunks
with a pre-roll so that filter and envelope state carries across chunk boundaries.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time
import wave
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy.ndimage import minimum_filter1d
from scipy.signal import resample_poly

from ..config import SR, FPS, AUDIO_OUT, TIMELINE_JSON, CACHE_DIR, EDITION
from . import dsp, fx, reverb, voice, sounddesign
from . import instruments as ins
from . import mix as M
from .sounddesign_full import cue_sheet_full, CHURCHY

SEG_VERSION = 2            # bump when the segment rendering below changes
SEG_MAX = 330.0            # seconds of sections per segment (a longer single section is its own segment)
TAIL = 8.0                 # reverb and release tail rendered past a segment's last section
TIERS = M.TIERS
ENV_RATE = 1000            # control-rate envelopes (ducking, Elena's voice), Hz
CHUNK = 60.0               # mastering chunk in seconds (a whole number of video frames)
PRE = 2.0                  # mastering pre-roll, seconds
HOP = SR // FPS            # samples per video frame
TARGET_LUFS = -16.0
SOLO = ("sop", "mez", "ten", "bar", "bbar", "treble")
VISUAL_TAGS = ("motif", "appearance")
# level rides made after listening to the level map: {section key: {tier: dB}}
RIDES: dict = {
    "E1": {"atmos": -5.0}, "E2": {"atmos": -5.0}, "F0": {"atmos": -5.0},   # applause sat above the music
    "I2S": {"vox": -6.0},                                                  # the fishermen are far off
}
# each soloist's fader (the formant voices differ in level; measured against the orchestra in their own
# numbers, the men sat 3 dB under it while Elena sat 4 dB over it)
VOICE_GAIN = {"elena": 1.0, "marco": 2.0, "davide": 2.2, "vittorio": 1.8, "madre": 1.2, "nives": 1.5,
              "ferroviere": 1.4}
CEILING_DB = -1.4          # the limiter's ceiling: gain riding re-creates some overshoot; -1.2 measured -0.97 dBTP


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ================================================================================ helpers
def _add(buf, y, s0):
    n = buf.shape[-1]
    if s0 >= n:
        return
    if s0 < 0:
        y = y[..., -s0:]
        s0 = 0
    s1 = min(n, s0 + y.shape[-1])
    if s1 > s0:
        buf[..., s0:s1] += y[..., : s1 - s0]


def _mask(n, t0, ranges, fade):
    """Smooth 0..1 mask over absolute-time ranges, for a buffer starting at t0."""
    m = np.zeros(n, dtype=np.float32)
    ranges = [(a, b) for a, b in ranges if b > t0 - fade and a < t0 + n / SR + fade]
    if not ranges:
        return m
    t = np.arange(n, dtype=np.float64) / SR + t0
    for a, b in ranges:
        m = np.maximum(m, (np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)).astype(np.float32))
    return m


def _wet(send, space):
    if not send.any():
        return 0.0
    wl, wr = reverb.convolve_stereo(send[0], send[1], space)
    return np.stack([wl, wr])


def _ctl(x, rms=False):
    """Downsample a mono envelope to ENV_RATE (mean, or RMS)."""
    step = SR // ENV_RATE
    m = len(x) // step
    v = x[: m * step].reshape(m, step).astype(np.float64)
    return (np.sqrt((v ** 2).mean(axis=1)) if rms else v.mean(axis=1)).astype(np.float32)


def location_spans(tl):
    """(start, end, location) across the programme, following location changes inside sections."""
    out = []
    for s in tl["sections"]:
        m = tl["meta"].get(s["key"], {})
        loc, t = m.get("location", ""), s["start"]
        for e in sorted((e for e in m.get("events", []) if e.get("kind") == "location"), key=lambda e: e["t"]):
            if e["t"] > t:
                out.append((t, e["t"], loc))
            t, loc = e["t"], e["where"]
        out.append((t, s["end"], loc))
    return out


# ================================================================================ tier 2: score
def render_score(notes, n, cm):
    dry = np.zeros((2, n), np.float32)
    hall = np.zeros((2, n), np.float32)
    church = np.zeros((2, n), np.float32)
    has_church = bool(cm.any())
    by = defaultdict(list)
    for x in notes:
        by[x["inst"]].append(M.note_dict(x))
    for inst, ns in sorted(by.items()):
        ns.sort(key=lambda x: x["t"])
        if inst in M.STRINGS:
            L, R, _ = ins.render_strings(inst, ns, n)
            send = M.SEND["strings"]
        else:
            L, R, _ = ins.render_other(inst, ns, n)
            send = M.SEND.get(inst, 0.4)
        st = np.stack([L, R]).astype(np.float32) * np.float32(M.GAIN.get(inst, 0.7))
        del L, R
        dry += st
        if has_church:
            church += st * (send * cm)
            hall += st * (send * (1 - cm))
        else:
            hall += st * np.float32(send)
        del st
    return dry + _wet(hall, "hall") + _wet(church, "church")


# ================================================================================ tier 1: vox
def _seed(*parts):
    return int.from_bytes(hashlib.sha1("|".join(parts).encode()).digest()[:2], "little")


def _far(y, pan):
    return fx.stereo(dsp.eq(dsp.eq(y, "lp", 3200, 0.7), "hp", 180, 0.7).astype(np.float32), pan)


def render_vox(notes, n, t0, cm, stab, dome=None, close=None):
    """Soloists (normal, vision, offstage) and the chorus (six singers a part); the film's routing."""
    dry = np.zeros((2, n), np.float32)
    sends = defaultdict(lambda: np.zeros((2, n), np.float32))
    solo_env = np.zeros(n, np.float32)
    elena = np.zeros(n, np.float32)
    has_church = bool(cm.any())
    solo, chorus = defaultdict(list), defaultdict(list)
    for x in notes:
        if x["inst"] in SOLO:
            solo[(x["inst"], x["voice"])].append(M.note_dict(x))
        elif x["inst"] in M.CHORUS_PAN:
            chorus[(x["inst"], bool(x["tags"].get("offstage")))].append(M.note_dict(x))
    for (inst, vid), ns in sorted(solo.items()):
        classes = defaultdict(list)
        for x in ns:
            s = x["tags"].get("style", "aria")
            classes["vision" if s == "vision" else "offstage" if s == "offstage" else "normal"].append(x)
        pan = M.VOICE_PAN.get(vid, 0.0)
        for cls, cn in sorted(classes.items()):
            y = voice.render_voice(inst, cn, n, seed=_seed(inst, vid, cls)) * np.float32(0.55 * VOICE_GAIN.get(vid, 1.0))
            if cls == "vision":
                st = fx.stereo(dsp.eq(y, "peak", 250, 0.8, 2.0).astype(np.float32), 0.0)
                dry += st * np.float32(1.05)
                sends["vision"] += st * np.float32(0.16)
            elif cls == "offstage":
                st = _far(y, -0.25)
                dry += st * np.float32(0.42)
                sends["hall"] += st * np.float32(0.95)
                sends["dome"] += st * np.float32(0.35)
            else:
                st = fx.stereo(y, pan)
                dry += st
                if has_church:
                    sends["hall"] += st * (0.26 * (1 - cm))
                    sends["church"] += st * (0.26 * cm)
                else:
                    sends["hall"] += st * np.float32(0.26)
                if inst != "treble":
                    solo_env += np.abs(y)
                if vid == "elena":
                    elena += np.abs(y)
                    if dome is not None:
                        # the wide shot: her voice blooms under the dome; the close-up is drier and nearer
                        sends["dome"] += st * (0.55 * dome)
                        sends["hall"] -= st * (0.26 * 0.55 * close)
                        dry += st * (0.18 * close)
            # an inhale before each sung phrase
            for ph in voice.phrases_of(cn, gap=0.6):
                if cls == "normal" and inst != "treble" and ph[0]["t"] + t0 > 1.0:
                    b = fx.stereo(voice.breath(0.32, 0.06, int((ph[0]["t"] + t0) * 100)).astype(np.float32), pan)
                    s0 = int((ph[0]["t"] - 0.42) * SR)
                    _add(dry, b, s0)
                    _add(sends["hall"], b * np.float32(0.2), s0)
            del y, st
    parts = list(M.CHORUS_PAN)
    for (part, off), ns in sorted(chorus.items()):
        ns.sort(key=lambda x: x["t"])
        pi = parts.index(part)
        for k in range(6):
            rng = np.random.default_rng(7919 * pi + 104729 * k + (17 if off else 0))
            singer = dict(detune=rng.normal(0, 7), vib=rng.uniform(0.7, 1.3), rate=rng.uniform(0.9, 1.12),
                          fscale=rng.uniform(0.96, 1.04), gain=rng.uniform(0.8, 1.1), breath=rng.uniform(0, 0.03))
            shifted = [dict(x, t=x["t"] + rng.normal(0, 0.012)) for x in ns]
            y = voice.render_voice(part, shifted, n, seed=1000 + k + 10 * pi + (500 if off else 0),
                                   singer=singer) * np.float32(0.2)
            p = M.CHORUS_PAN[part] + rng.uniform(-0.12, 0.12)
            if off:
                # far off, beyond the scene (the fishermen humming in the sea interlude)
                st = _far(y, 0.6 * p - 0.25)
                dry += st * np.float32(0.42)
                sends["hall"] += st * np.float32(0.95)
                sends["dome"] += st * np.float32(0.35)
            else:
                st = fx.stereo(y, p)
                dry += st
                if has_church or stab.any():
                    sends["hall"] += st * (0.42 * (1 - cm) * (1 - stab))
                    sends["church"] += st * (0.42 * cm * (1 - stab) + 0.55 * stab)
                else:
                    sends["hall"] += st * np.float32(0.42)
            del y, st
    out = dry
    for sp in sorted(sends):
        out = out + _wet(sends[sp], sp)
    env = dsp.onepole_lp(solo_env.astype(np.float64), np.full(n, math.exp(-1.0 / (0.25 * SR))))
    return out.astype(np.float32), _ctl(env), _ctl(elena, rms=True)


# ================================================================================ tiers 3-5
def render_events(events, n, t0, score_mix, ghost):
    buses = {t: (np.zeros((2, n), np.float32), defaultdict(lambda: np.zeros((2, n), np.float32)))
             for t in ("foley", "atmos", "design")}

    def add(tier, y, s0, send, space, gain):
        d, sends = buses[tier]
        seg = y * np.float32(gain)
        _add(d, seg, s0)
        if send > 0 and space:
            _add(sends[space], seg * np.float32(send), s0)

    for e in events:
        args = dict(e["args"])
        post = {k: args.pop(k) for k in M.POST_KEYS if k in args}
        gen = e["gen"]
        if gen == "ghost":
            # Vittorio's first 'Elena' (N10), reversed and dissolved: her memory, not his voice
            if ghost is None:
                continue
            seg = ghost[::-1] * np.hanning(len(ghost)) ** 0.5
            seg = dsp.eq(dsp.eq(seg, "lp", 1600, 0.7), "hp", 200, 0.7)
            y = fx.stereo(seg.astype(np.float32), 0.0)
            wl, wr = reverb.convolve_stereo(y[0], y[1], "vision")
            y = (np.stack([wl, wr]) + y * 0.4) * 1.2
        elif gen == "reverse_swell":
            s0 = max(0, int((args["src_t"] - t0) * SR))
            L = int(args["length"] * SR)
            seg = np.ascontiguousarray(score_mix[:, s0:s0 + int(0.8 * SR)])
            wl, wr = reverb.convolve_stereo(seg[0], seg[1], "church")
            tail = np.stack([wl, wr])[:, :L]
            y = tail[:, ::-1] * np.linspace(0, 1, tail.shape[1]) ** 2
            y = M._norm_to(y, M.TARGET_DB["reverse_swell"]).astype(np.float32)
            add("design", y, int((e["t"] - t0) * SR) - y.shape[1], 0.0, None, e["gain"])
            continue
        else:
            args.setdefault("seed", 0)
            y = M.GEN[gen](**args)
        y = np.asarray(y, dtype=np.float32)
        if gen in M.TARGET_DB:
            y = M._norm_to(y, M.TARGET_DB[gen]).astype(np.float32)
        if y.ndim == 1:
            y = fx.stereo(y, e["pan"])
        ln = y.shape[1]
        tt = np.arange(ln) / SR
        if "fade_out" in post:
            y = y * np.clip((ln / SR - tt) / max(1e-3, post["fade_out"]), 0, 1)
        if "duck_at" in post:
            y = y * np.where(tt < post["duck_at"], 1.0,
                             post["duck_to"] + (1 - post["duck_to"]) * np.exp(-(tt - post["duck_at"]) / 0.8))
        if post.get("recede"):
            y = np.stack([dsp.eq(y[c], "lp", 2500, 0.7) for c in range(2)]) * np.linspace(1.0, 0.45, ln)
        if post.get("wall"):
            y = np.stack([dsp.eq(y[c], "lp", 1300, 0.7) for c in range(2)])
        if post.get("soft"):
            y = np.stack([dsp.eq(y[c], "lp", 3000, 0.7) for c in range(2)]) * 0.7
        y = y.astype(np.float32)
        space = e["space"]
        send = {"foley": 0.22, "atmos": 0.3, "design": 0.0}[e["tier"]]
        if space in ("hall", "church"):
            send *= 1.4
        add(e["tier"], y, int((e["t"] - t0) * SR), send if space else 0.0, space, e["gain"])
    out = {}
    for t, (d, sends) in buses.items():
        for sp in sorted(sends):
            d = d + _wet(sends[sp], sp)
        out[t] = d.astype(np.float32)
    return out


# ================================================================================ one segment
def render_segment(job):
    """Render one segment's five tiers to .npy files (worker process). Returns its manifest."""
    idx, h, d = job["idx"], job["hash"], Path(job["dir"])
    man_path = d / f"seg{idx:02d}_{h}.json"
    if man_path.exists():
        return json.loads(man_path.read_text())
    for old in d.glob(f"seg{idx:02d}_*"):
        if h not in old.name:
            old.unlink()
    t_start = time.time()
    t0 = job["t0"]
    n = int((job["end"] - t0) * SR)
    notes = [dict(x, t=x["t"] - t0) for x in job["notes"]]
    cues = job["cues"]
    cm = _mask(n, t0, [(a, b) for a, b, loc in job["spans"] if loc in CHURCHY], 0.4)
    stab = _mask(n, t0, [(a, b) for a, b, loc in job["spans"] if loc == "stabat"], 0.5)
    score = render_score([x for x in notes if x["inst"] not in voice.VOICE_TYPES], n, cm)
    t_score = time.time() - t_start
    dome = close = None
    if "N22.wide" in cues:
        dome = _mask(n, t0, [(cues["N22.wide"], cues["N22.closeup"])], 0.3)
        close = _mask(n, t0, [(cues["N22.closeup"], cues["N22.vittorio4"])], 0.3)
    vox, env, elena = render_vox([x for x in notes if x["inst"] in voice.VOICE_TYPES], n, t0, cm, stab, dome, close)
    t_vox = time.time() - t_start - t_score
    ghost = np.load(job["ghost"]) if job.get("ghost") else None
    ev = render_events(job["events"], n, t0, score, ghost)
    if "N21.heat_start" in cues:
        # Elena's perception: while Davide's grief breaks, she hears the warm score through fear
        tun = _mask(n, t0, [(cues["N21.heat_start"], cues["N21.heat_end"])], 0.6)
        for tier in (score, vox):
            lp = np.stack([dsp.eq(dsp.eq(tier[c], "lp", 700, 0.7), "lp", 700, 0.7) for c in range(2)])
            tier *= (1 - tun)
            tier += (lp * (tun * 0.8)).astype(np.float32)
        ev["atmos"] *= (1 - 0.6 * tun)
    stems = {"vox": vox, "score": score, **ev}
    files = {}
    for k in TIERS:
        f = d / f"seg{idx:02d}_{h}_{k}.npy"
        np.save(f, np.ascontiguousarray(stems[k], dtype=np.float32))
        files[k] = str(f)
    np.save(d / f"seg{idx:02d}_{h}_env.npy", env)
    np.save(d / f"seg{idx:02d}_{h}_elena.npy", elena)
    man = {"idx": idx, "t0": t0, "n": n, "keys": job["keys"], "files": files,
           "env": str(d / f"seg{idx:02d}_{h}_env.npy"), "elena": str(d / f"seg{idx:02d}_{h}_elena.npy"),
           "secs": round(time.time() - t_start, 1), "secs_score": round(t_score, 1), "secs_vox": round(t_vox, 1)}
    tmp = man_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(man))
    tmp.replace(man_path)
    return man


# ================================================================================ planning
def plan_segments(tl):
    segs, cur, cur_t0, cur_len = [], [], 0.0, 0.0
    for s in tl["sections"]:
        d = s["end"] - s["start"]
        if cur and cur_len + d > SEG_MAX:
            segs.append((cur, cur_t0, cur_t0 + cur_len))
            cur, cur_len = [], 0.0
        if not cur:
            cur_t0 = s["start"]
        cur.append(s["key"])
        cur_len += d
    if cur:
        segs.append((cur, cur_t0, cur_t0 + cur_len))
    return segs


def _code_hash():
    h = hashlib.sha1()
    for mod in (dsp, fx, reverb, voice, ins, M, sounddesign):
        h.update(Path(mod.__file__).read_bytes())
    h.update(str(SEG_VERSION).encode())
    return h.hexdigest()


def make_ghost(tl, out_dir):
    """Vittorio's first 'Elena' from his first vision (N10): the material of Elena's ghost in N21."""
    vis = sorted((x for x in tl["notes"] if x["section"] == "N10" and x["inst"] == "bar"
                  and x["tags"].get("style") == "vision"), key=lambda x: x["t"])
    if not vis:
        return None
    t0 = vis[0]["t"]
    first = [dict(M.note_dict(x), t=x["t"] - t0 + 0.2) for x in vis if x["t"] < t0 + 2.2]
    y = voice.render_voice("bar", first, int(3.0 * SR), seed=4242) * 0.55
    p = out_dir / "ghost.npy"
    np.save(p, y[int(0.15 * SR): int(2.3 * SR)].astype(np.float32))
    return p


def make_jobs(tl, out_dir):
    events = cue_sheet_full(tl)
    spans = location_spans(tl)
    segs = plan_segments(tl)
    code = _code_hash()
    ghost = make_ghost(tl, out_dir)
    ghost_hash = hashlib.sha1(ghost.read_bytes()).hexdigest() if ghost else ""
    by_sec = defaultdict(list)
    for x in tl["notes"]:
        # tags that only the picture reads stay out of the audio (and out of its cache keys)
        by_sec[x["section"]].append(dict(x, tags={k: v for k, v in x["tags"].items() if k not in VISUAL_TAGS}))
    jobs = []
    for i, (keys, t0, t1) in enumerate(segs):
        first, last = i == 0, i == len(segs) - 1
        evs = [e for e in events if (first or e["t"] >= t0) and (last or e["t"] < t1)]
        notes = [x for k in keys for x in by_sec[k]]
        ks = set(keys)
        cues = {k: v for k, v in tl["cues"].items() if k.split(".")[0] in ks}
        sp = [(a, b, loc) for a, b, loc in spans if b > t0 - 1.0 and a < t1 + TAIL]
        end = max([t1 + TAIL] + [x["t"] + x["dur"] + 4.0 for x in notes] +
                  [e["t"] + e["args"].get("dur", 6.0) + 6.0 for e in evs])
        uses_ghost = any(e["gen"] == "ghost" for e in evs)
        faders = {v: VOICE_GAIN.get(v, 1.0) for v in sorted({x["voice"] for x in notes if x["inst"] in SOLO})}
        h = hashlib.sha1()
        for part in (code, keys, t0, end, notes, evs, cues, sp, ghost_hash if uses_ghost else "", faders):
            h.update(json.dumps(part, sort_keys=True).encode())
        jobs.append(dict(idx=i, keys=keys, t0=t0, t1=t1, end=end, notes=notes, events=evs, cues=cues, spans=sp,
                         ghost=str(ghost) if uses_ghost else None, hash=h.hexdigest()[:12], dir=str(out_dir)))
    return jobs, len(events)


# ================================================================================ mastering
class Programme:
    """The assembled tiers, read by overlap-adding the cached segments on demand."""

    def __init__(self, mans):
        self.segs = [(int(round(m["t0"] * SR)), {k: np.load(m["files"][k], mmap_mode="r") for k in TIERS})
                     for m in sorted(mans, key=lambda m: m["t0"])]

    def read(self, k, a, b):
        out = np.zeros((2, b - a), np.float32)
        for s0, arrs in self.segs:
            x = arrs[k]
            lo, hi = max(a, s0), min(b, s0 + x.shape[1])
            if hi > lo:
                out[:, lo - a:hi - a] += x[:, lo - s0:hi - s0]
        return out


def _ctl_track(mans, key, ne):
    v = np.zeros(ne, np.float32)
    for m in mans:
        e0 = int(round(m["t0"] * ENV_RATE))
        x = np.load(m[key])
        e1 = min(ne, e0 + len(x))
        v[e0:e1] += x[: e1 - e0]
    return v


def _chunks(total, size, pre=0, post=0):
    a = 0
    while a < total:
        b = min(total, a + size)
        yield a, b, max(0, a - pre), min(total, b + post)
        a = b


def _ride_curves(tl):
    """Per-tier gain breakpoints from RIDES, ramping over half a second at section edges."""
    out = {}
    for tier in TIERS:
        if not any(tier in r for r in RIDES.values()):
            continue
        ts, gs = [], []
        for s in tl["sections"]:
            g = 10 ** (RIDES.get(s["key"], {}).get(tier, 0.0) / 20)
            ts += [s["start"] + 0.25, s["end"] - 0.25]
            gs += [g, g]
        out[tier] = (np.array(ts), np.array(gs))
    return out


def _limit(st, ceiling_db=-1.0, look=0.005, release=0.08):
    """The film's true-peak limiter (elenavid.audio.mix.true_peak_limit), also returning its gain."""
    ceiling = 10 ** (ceiling_db / 20)
    over = np.abs(resample_poly(st, 4, 1, axis=1)).max(axis=0)
    peak = over.reshape(-1, 4).max(axis=1)[: st.shape[1]]
    if len(peak) < st.shape[1]:
        peak = np.pad(peak, (0, st.shape[1] - len(peak)))
    gain = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    la = int(look * SR)
    g = np.roll(minimum_filter1d(gain, size=2 * la + 1, origin=0), -la)
    # smooth the gain reduction (1 - g), not the gain, so the smoother starts at unity gain
    sm = 1.0 - dsp.onepole_lp(1.0 - g.astype(np.float64), np.full(len(g), math.exp(-1.0 / (release * SR))))
    sm = np.minimum(sm, g)
    return st * sm.astype(np.float32), sm


def _blocks(y, t_first):
    """BS.1770 400 ms blocks (100 ms hop) of a stereo chunk: (start times, mean-square energies)."""
    kw = [M.k_weight(y[c].astype(np.float64)) for c in range(2)]
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    sq = kw[0] ** 2 + kw[1] ** 2
    cs = np.concatenate([[0.0], np.cumsum(sq)])
    starts = np.arange(0, y.shape[1] - blk, hop)
    e = (cs[starts + blk] - cs[starts]) / blk
    return t_first + starts / SR, e


def _integrated(e):
    lv = -0.691 + 10 * np.log10(e + 1e-12)
    g = e[lv > -70]
    if not len(g):
        return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(g)) - 10
    return float(-0.691 + 10 * np.log10(np.mean(e[(lv > -70) & (lv > rel)])))


def _lra(e):
    """Loudness range from short-term (about 3 s) energies built out of the 400 ms blocks."""
    k = 7
    st = np.convolve(e, np.ones(k) / k, mode="valid")[::4] if len(e) > 4 * k else e
    st = st[::10] if len(st) > 10 else st
    lv = -0.691 + 10 * np.log10(st + 1e-12)
    g = st[lv > -70]
    if len(g) < 3:
        return 0.0
    rel = -0.691 + 10 * np.log10(np.mean(g)) - 20
    l2 = -0.691 + 10 * np.log10(g[(-0.691 + 10 * np.log10(g)) > rel])
    return float(np.percentile(l2, 95) - np.percentile(l2, 10))


def master(tl, mans, scratch):
    T = max(s["end"] for s in tl["sections"])
    N = int(T * SR)
    NE = int(T * ENV_RATE) + 1
    prog = Programme(mans)
    env = _ctl_track(mans, "env", NE)
    elena = _ctl_track(mans, "elena", NE)
    p90 = float(np.percentile(env[env > 1e-4], 90)) if np.any(env > 1e-4) else 1.0
    t_env = np.arange(NE) / ENV_RATE
    rides = _ride_curves(tl)
    secs = tl["sections"]
    step = int(CHUNK * SR)
    pre_n = int(PRE * SR)

    def duck(a, b):
        tt = np.arange(a, b) / SR
        return (1.0 - 0.25 * np.clip(np.interp(tt, t_env, env) / (p90 + 1e-9), 0, 1)).astype(np.float32)

    def ride(k, a, b):
        if k not in rides:
            return 1.0
        return np.interp(np.arange(a, b) / SR, *rides[k]).astype(np.float32)

    def processed(a, b, gains, deess=True):
        """The five tiers over [a, b) after automation and calibration (pre-glue)."""
        out = {}
        v = prog.read("vox", a, b) * np.float32(gains["vox"])
        out["vox"] = (M.deess(v) if deess else v) * ride("vox", a, b)
        out["score"] = prog.read("score", a, b) * np.float32(gains["score"]) * duck(a, b) * ride("score", a, b)
        for k in ("foley", "atmos", "design"):
            out[k] = prog.read(k, a, b) * np.float32(gains[k]) * ride(k, a, b)
        return out

    # ---- calibration: active RMS (musical tiers to the film's targets; event tiers fixed)
    log(f"calibrating {T / 60:.1f} min")
    ones = {k: 1.0 for k in TIERS}
    ss, cnt = defaultdict(float), defaultdict(int)
    for a, b, _, _ in _chunks(N, step):
        x = processed(a, b, ones, deess=False)
        for k in TIERS:
            act = np.abs(x[k]).max(axis=0) > 1e-4
            if act.any():
                ss[k] += float(np.sum(x[k][:, act].astype(np.float64) ** 2))
                cnt[k] += int(act.sum()) * 2
    targets = {"score": -23.0, "vox": -20.5}
    fixed = {"foley": 0.0, "atmos": 0.0, "design": -1.0}
    gains = {}
    for k in TIERS:
        r = math.sqrt(ss[k] / cnt[k]) if cnt[k] else 1e-9
        gains[k] = 10 ** (targets[k] / 20) / r if k in targets else 10 ** (fixed[k] / 20)
        log(f"  {k:6s} active rms {20 * math.log10(r + 1e-12):6.1f} dB -> gain {20 * math.log10(gains[k]):+6.1f} dB")

    # ---- pass A: mix, high-pass, glue; per-section tier levels; loudness of the pre-gain mix
    pre_path = scratch / "master_pre.npy"
    mpre = np.lib.format.open_memmap(pre_path, mode="w+", dtype=np.float32, shape=(2, N))
    peaks = defaultdict(float)
    lvl = {s["key"]: {k: [0.0, 0] for k in TIERS} for s in secs}
    ea = []
    log("pass A: mix and glue")
    for a, b, pa, _ in _chunks(N, step, pre=pre_n):
        x = processed(pa, b, gains)
        mix = sum(x[k] for k in TIERS)
        for k in TIERS:
            seg = x[k][:, a - pa:]
            peaks[k] = max(peaks[k], float(np.abs(seg).max()))
            for s in secs:
                lo, hi = max(a, int(s["start"] * SR)), min(b, int(s["end"] * SR))
                if hi > lo:
                    part = seg[:, lo - a:hi - a]
                    act = np.abs(part).max(axis=0) > 1e-5
                    if act.any():
                        lvl[s["key"]][k][0] += float(np.sum(part[:, act].astype(np.float64) ** 2))
                        lvl[s["key"]][k][1] += int(act.sum()) * 2
        mix = np.stack([dsp.eq(mix[c], "hp", 18, 0.7) for c in range(2)]).astype(np.float32)
        mono = 0.5 * (mix[0] + mix[1])
        envg = np.sqrt(dsp.onepole_lp(mono.astype(np.float64) ** 2, np.full(len(mono), math.exp(-1 / (0.3 * SR))))
                       + 1e-12)
        gr = -np.maximum(0, 20 * np.log10(envg) + 20.0) * (1 - 1 / 1.35)
        mix = mix * (10 ** (gr / 20)).astype(np.float32)
        mpre[:, a:b] = mix[:, a - pa:]
        ea.append(_blocks(mix[:, a - pa:], a / SR)[1])
        log(f"  {b / SR / 60:6.1f} min")
    mpre.flush()
    L = _integrated(np.concatenate(ea))
    g = 10 ** ((TARGET_LUFS - L) / 20)
    headroom = max(0.0, 20 * math.log10(max(peaks.values()) * g + 1e-12) + 0.5)
    sg = g * 10 ** (-headroom / 20)
    log(f"  pre-gain loudness {L:.2f} LUFS -> gain {20 * math.log10(g):+.2f} dB; stem headroom {headroom:.1f} dB")

    # ---- pass B: gain, true-peak limit; master, stems and envelopes
    AUDIO_OUT.mkdir(parents=True, exist_ok=True)
    wav_path = AUDIO_OUT / "elena_full_master.wav"
    wav_part = wav_path.with_name(wav_path.name + ".part")      # swapped in when complete
    mw = wave.open(str(wav_part), "wb")
    mw.setnchannels(2)
    mw.setsampwidth(3)
    mw.setframerate(SR)
    procs = {}
    for i, k in enumerate(TIERS, 1):
        procs[k] = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
             "-c:a", "flac", "-sample_fmt", "s32", "-bits_per_raw_sample", "24", "-compression_level", "5",
             str(AUDIO_OUT / f"stem_{i}_{k}.flac")], stdin=subprocess.PIPE)
    envs = {"vox": [], "score": [], "master": []}
    tb, eb = [], []
    tp = 0.0
    gr_min, gr_n1 = 1.0, 0
    log("pass B: limit and write")
    for a, b, pa, pb in _chunks(N, step, pre=pre_n, post=int(0.05 * SR)):
        y, gl = _limit(np.asarray(mpre[:, pa:pb]) * np.float32(g), CEILING_DB)
        y = y[:, a - pa: a - pa + (b - a)]
        gl = gl[a - pa: a - pa + (b - a)]
        gr_min = min(gr_min, float(gl.min()))
        gr_n1 += int(np.sum(gl < 10 ** (-1 / 20)))
        tp = max(tp, float(np.abs(resample_poly(y, 4, 1, axis=1)).max()))
        yi = np.ascontiguousarray((np.clip(y, -1.0, 1.0).T * (2 ** 23 - 1)).astype("<i4"))
        mw.writeframes(np.ascontiguousarray(yi.view(np.uint8).reshape(-1, 4)[:, :3]).tobytes())
        t_b, e_b = _blocks(y, a / SR)
        tb.append(t_b)
        eb.append(e_b)
        x = processed(pa, b, gains)
        for k in TIERS:
            s = x[k][:, a - pa:] * np.float32(sg)
            procs[k].stdin.write(np.ascontiguousarray(s.T, dtype="<f4").tobytes())
        nfr = (b - a) // HOP
        for name, sig in (("master", y), ("vox", x["vox"][:, a - pa:] * np.float32(g)),
                          ("score", x["score"][:, a - pa:] * np.float32(g))):
            m = 0.5 * (np.abs(sig[0, :nfr * HOP]) + np.abs(sig[1, :nfr * HOP]))
            envs[name] += np.sqrt(np.mean(m.reshape(nfr, HOP).astype(np.float64) ** 2, axis=1)).round(6).tolist()
        log(f"  {b / SR / 60:6.1f} min")
    mw.close()
    for p in procs.values():
        p.stdin.close()
        p.wait()
    # Elena's level per frame, on the film's scale (her dry left channel: centre pan 0.707)
    nf = len(envs["master"])
    f = np.arange(nf + 1)
    idx = np.minimum(NE, (f * ENV_RATE) // FPS)
    cs = np.concatenate([[0.0], np.cumsum(elena.astype(np.float64) ** 2)])
    envs["elena"] = (0.7071 * np.sqrt((cs[idx[1:]] - cs[idx[:-1]]) / np.maximum(1, idx[1:] - idx[:-1]))).round(6).tolist()
    tmp = AUDIO_OUT / "envelopes.json.tmp"
    tmp.write_text(json.dumps(envs))
    tmp.replace(AUDIO_OUT / "envelopes.json")
    t_all, e_all = np.concatenate(tb), np.concatenate(eb)
    L2, lra = _integrated(e_all), _lra(e_all)
    sec_rep = {}
    for s in secs:
        sel = (t_all >= s["start"]) & (t_all < s["end"] - 0.4)
        e = e_all[sel]
        sec_rep[s["key"]] = {
            "title": s.get("title", ""), "start": round(s["start"], 2),
            "loudness": round(_integrated(e), 1) if len(e) else None,
            "max_momentary": round(float(-0.691 + 10 * np.log10(e.max() + 1e-12)), 1) if len(e) else None,
            "tier_db": {k: (round(10 * math.log10(v[0] / v[1] + 1e-20) + 20 * math.log10(g), 1) if v[1] else None)
                        for k, v in lvl[s["key"]].items()}}
    report = {"integrated_lufs": round(L2, 2), "loudness_range_lu": round(lra, 1),
              "true_peak_dbtp": round(20 * math.log10(tp + 1e-12), 2),
              "limiter": {"max_reduction_db": round(-20 * math.log10(gr_min + 1e-12), 2),
                          "seconds_over_1db": round(gr_n1 / SR, 1)},
              "tier_gain_db": {k: round(20 * math.log10(v), 2) for k, v in gains.items()},
              "master_gain_db": round(20 * math.log10(g), 2), "stem_headroom_db": round(headroom, 2),
              "stems_note": "stems are the five tiers after automation and calibration, pre-glue, scaled down by "
                            "stem_headroom_db so that none clips as 24-bit FLAC",
              "rides": RIDES, "sections": sec_rep}
    (AUDIO_OUT / "levels.json").write_text(json.dumps(report, indent=1))
    log(f"master {L2:.2f} LUFS, LRA {lra:.1f} LU, true peak {report['true_peak_dbtp']:.2f} dBTP, limiter max "
        f"{report['limiter']['max_reduction_db']:.1f} dB ({report['limiter']['seconds_over_1db']:.0f} s over 1 dB)")
    print(f"  {'sec':4s} {'start':>7s} {'LUFS':>6s} {'max':>6s}  " + " ".join(f"{k:>6s}" for k in TIERS))
    for k, r in sec_rep.items():
        m, s_ = divmod(r["start"], 60)
        print(f"  {k:4s} {int(m):4d}:{s_:02.0f} {r['loudness'] or -99:6.1f} {r['max_momentary'] or -99:6.1f}  " +
              " ".join(f"{(r['tier_db'][t] if r['tier_db'][t] is not None else -99):6.1f}" for t in TIERS))
    # swap in the new master last: on Windows a file another process has open (a player, or the video
    # join reading it) cannot be replaced, so wait for it rather than lose the rest of the run
    for k in range(60):
        try:
            os.replace(wav_part, wav_path)
            break
        except PermissionError:
            if k == 0:
                log(f"  {wav_path.name} is open elsewhere; waiting to swap in the new master")
            time.sleep(10)
    else:
        log(f"  could not replace {wav_path}; the new master is {wav_part}")
    del mpre                     # Windows will not delete a file that is still mapped
    try:
        pre_path.unlink(missing_ok=True)
    except PermissionError:
        log(f"  (could not remove {pre_path}; it is scratch and can be deleted)")
    return report


# ================================================================================ main
def main(argv=None):
    if EDITION != "full":
        print("set ELENA_EDITION=full")
        return 2
    argv = sys.argv[1:] if argv is None else argv
    opts = dict(a.lstrip("-").split("=", 1) if "=" in a else (a.lstrip("-"), "1") for a in argv)
    workers = int(opts.get("workers", 6))
    t_all = time.time()
    tl = json.loads(TIMELINE_JSON.read_text(encoding="utf-8"))
    out_dir = CACHE_DIR / "segments"
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs, n_events = make_jobs(tl, out_dir)
    if "plan" in opts:
        for j in jobs:
            print(f"  {j['idx']:2d} {j['t0'] / 60:6.1f}-{j['t1'] / 60:6.1f} min ({j['end'] - j['t0']:5.0f} s) "
                  f"{len(j['notes']):5d} notes {len(j['events']):3d} events  {','.join(j['keys'])}")
        return 0
    # deterministic seeds in the workers (instruments seed per-note noise from hash()), and one thread each
    os.environ["PYTHONHASHSEED"] = "0"
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ[v] = "1"
    if "only" in opts:
        for i in map(int, opts["only"].split(",")):
            man = render_segment(jobs[i])
            log(f"segment {i}: {man['secs']}s (score {man['secs_score']}s, vox {man['secs_vox']}s) "
                f"for {(jobs[i]['end'] - jobs[i]['t0']):.0f}s of audio")
        return 0
    log(f"{len(jobs)} segments, {n_events} events, {workers} workers; cache {out_dir}")
    mans, todo = [], []
    for j in jobs:
        mp = out_dir / f"seg{j['idx']:02d}_{j['hash']}.json"
        if mp.exists():
            mans.append(json.loads(mp.read_text()))
        else:
            todo.append(j)
    log(f"  {len(mans)} cached, {len(todo)} to render")
    if todo:
        audio_s = sum(j["end"] - j["t0"] for j in todo)
        done_s = 0.0
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(render_segment, j): j for j in sorted(todo, key=lambda j: -(j["end"] - j["t0"]))}
            for fut in as_completed(futs):
                j = futs[fut]
                man = fut.result()
                mans.append(man)
                done_s += j["end"] - j["t0"]
                el = time.time() - t_all
                log(f"  segment {j['idx']:2d} in {man['secs']:5.0f}s  ({done_s / audio_s:4.0%}, "
                    f"eta {el / done_s * (audio_s - done_s) / 60:4.0f} min)  {','.join(j['keys'])}")
    master(tl, mans, out_dir)
    log(f"done in {(time.time() - t_all) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
