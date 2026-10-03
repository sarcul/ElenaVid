"""Render all five tiers, apply film-mix automation, master, and export stems + master.

Tier 1 VOX     - soloists and the six-voice-per-part chorus (formant singers)
Tier 2 SCORE   - the orchestra (modelled strings, winds, brass, percussion, harp, organ, bells)
Tier 3 FOLEY   - close, diegetic, human-scale sound (steps, silk, paper, doors, breath)
Tier 4 ATMOS   - environments (hall, village, rail, bora, sea, gulls, church, rooms)
Tier 5 DESIGN  - sub/LFE and psychoacoustic design (pressure, heartbeat, hits, the ghost, swells)
"""
from __future__ import annotations

import json
import math
import time
from collections import defaultdict

import numpy as np
from scipy.io import wavfile
from scipy.signal import oaconvolve, resample_poly

from ..config import SR, DURATION, AUDIO_OUT, TIMELINE_JSON
from . import dsp, fx, reverb, voice
from . import instruments as ins
from .sounddesign import cue_sheet

N = int(DURATION * SR)
STRINGS = set(ins.SECTIONS)
TIERS = ("vox", "score", "foley", "atmos", "design")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


class Bus:
    """A stereo dry bus plus per-space reverb sends."""

    def __init__(self):
        self.dry = np.zeros((2, N), dtype=np.float32)
        self.sends = defaultdict(lambda: np.zeros((2, N), dtype=np.float32))

    def add(self, st, s0, send=0.0, space=None, gain=1.0):
        """st: (2, n) array placed at sample s0."""
        if s0 >= N:
            return
        if s0 < 0:
            st = st[:, -s0:]
            s0 = 0
        s1 = min(N, s0 + st.shape[1])
        seg = st[:, : s1 - s0] * gain
        self.dry[:, s0:s1] += seg
        if send > 0 and space:
            self.sends[space][:, s0:s1] += seg * send

    def wet(self):
        out = np.zeros((2, N), dtype=np.float32)
        for space, s in self.sends.items():
            wl, wr = reverb.convolve_stereo(s[0], s[1], space)
            out[0] += wl
            out[1] += wr
        return out


def window_mask(ranges, fade=0.25):
    """Smooth 0..1 mask over absolute-time ranges."""
    m = np.zeros(N, dtype=np.float32)
    t = np.arange(N) / SR
    for a, b in ranges:
        m = np.maximum(m, (np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)).astype(np.float32))
    return m


CHURCH = [(80.0, 122.0), (408.0, 430.0)]


_CM = None


def split_by_space(st, default="hall"):
    """Divide a stereo send between the hall and the church according to time."""
    global _CM
    if _CM is None:
        _CM = window_mask(CHURCH, 0.4)
    return {"church": st * _CM, default: st * (1 - _CM)}


# ============================================================================ tier 2: SCORE

SEND = {"strings": 0.32, "fl": 0.42, "ob": 0.4, "eh": 0.42, "cl": 0.4, "bn": 0.36, "hn": 0.5,
        "tpt": 0.45, "tbn": 0.45, "tuba": 0.4, "timp": 0.5, "bd": 0.5, "tamtam": 0.55, "cym": 0.5,
        "tri": 0.5, "tamb": 0.45, "tubbells": 0.55, "churchbell": 0.65, "celesta": 0.5,
        "harp": 0.42, "organ": 0.75}
GAIN = {"vn1": 0.9, "vn2": 0.8, "va": 0.8, "vc": 0.85, "cb": 0.9, "vn_solo": 0.75, "va_solo": 0.7,
        "vc_solo": 0.7, "vc_harm": 0.55, "fl": 0.7, "ob": 0.75, "eh": 0.7, "cl": 0.75, "bn": 0.7,
        "hn": 0.85, "tpt": 0.6, "tbn": 0.7, "tuba": 0.7, "timp": 0.8, "bd": 0.8, "tamtam": 0.7,
        "cym": 0.45, "tri": 0.4, "tamb": 0.4, "tubbells": 0.55, "churchbell": 0.6, "celesta": 0.6,
        "harp": 0.65, "organ": 0.7}


def note_dict(n):
    return dict(t=n["t"], dur=n["dur"], midi=n["midi"], vel=n["vel"], tech=n["tags"].get("tech", ""),
                art=n.get("art", ""), tags=n["tags"], lyric=n.get("lyric"))


def render_score(notes):
    bus = Bus()
    by = defaultdict(list)
    for n in notes:
        if n["inst"] in STRINGS or n["inst"] in ins.WINDS or n["inst"] in ins.BRASS or \
                n["inst"] in ins.PERC_PAN:
            by[n["inst"]].append(note_dict(n))
    for inst, ns in sorted(by.items()):
        t0 = time.time()
        ns.sort(key=lambda x: x["t"])
        if inst in STRINGS:
            L, R, pan = ins.render_strings(inst, ns, N)
            send = SEND["strings"]
        else:
            L, R, pan = ins.render_other(inst, ns, N)
            send = SEND.get(inst, 0.4)
        st = np.stack([L, R]) * GAIN.get(inst, 0.7)
        bus.dry += st
        for space, part in split_by_space(st * send).items():
            bus.sends[space] += part
        log(f"  score {inst:9s} {len(ns):4d} notes  {time.time() - t0:5.1f}s")
    return bus


# ============================================================================ tier 1: VOX

VOICE_PAN = {"elena": 0.0, "marco": 0.22, "davide": 0.18, "vittorio": 0.0, "madre": -0.2,
             "nives": 0.3, "ferroviere": -0.5, "tommaso": 0.05}
CHORUS_PAN = {"ch_s": -0.45, "ch_a": -0.15, "ch_t": 0.15, "ch_b": 0.45}


def render_vox(notes):
    bus = Bus()
    solo = defaultdict(list)
    chorus = defaultdict(list)
    for n in notes:
        if n["inst"] in ("sop", "mez", "ten", "bar", "bbar", "treble"):
            solo[(n["inst"], n["voice"])].append(note_dict(n))
        elif n["inst"] in CHORUS_PAN:
            chorus[n["inst"]].append(note_dict(n))
    solo_env = np.zeros(N, dtype=np.float32)
    elena_dry = np.zeros((2, N), dtype=np.float32)
    vittorio_vision = np.zeros(N, dtype=np.float32)
    for (inst, vid), ns in sorted(solo.items()):
        t0 = time.time()
        classes = defaultdict(list)
        for n in ns:
            st = n["tags"].get("style", "aria")
            classes["vision" if st == "vision" else "offstage" if st == "offstage" else "normal"].append(n)
        for cls, cn in classes.items():
            y = voice.render_voice(inst, cn, N, seed=hash((inst, vid, cls)) & 0xFFFF)
            y *= 0.55
            pan = VOICE_PAN.get(vid, 0.0)
            if cls == "vision":
                vittorio_vision += y
                warm = dsp.eq(y, "peak", 250, 0.8, 2.0).astype(np.float32)
                st = fx.stereo(warm, 0.0)
                bus.dry += st * 1.05
                bus.sends["vision"] += st * 0.16
            elif cls == "offstage":
                far = dsp.eq(dsp.eq(y, "lp", 3200, 0.7), "hp", 180, 0.7).astype(np.float32)
                st = fx.stereo(far, -0.25)
                bus.dry += st * 0.42
                bus.sends["hall"] += st * 0.95
                bus.sends["dome"] += st * 0.35
            else:
                st = fx.stereo(y, pan)
                bus.dry += st
                for space, part in split_by_space(st * 0.26).items():
                    bus.sends[space] += part
                if vid == "elena":
                    elena_dry += st
                if inst != "treble":
                    solo_env += np.abs(y)
            # breaths before phrases
            for ph in voice.phrases_of(cn, gap=0.6):
                if cls == "normal" and inst != "treble" and ph[0]["t"] > 1.0:
                    b = voice.breath(0.32, 0.06, int(ph[0]["t"] * 100))
                    s0 = int((ph[0]["t"] - 0.42) * SR)
                    bus.add(fx.stereo(b.astype(np.float32), pan), s0, 0.2, "hall")
        log(f"  vox {inst:6s} {vid:10s} {len(ns):4d} notes  {time.time() - t0:5.1f}s")
    stabat = window_mask([(314.0, 364.0)], 0.5)
    for part, ns in sorted(chorus.items()):
        t0 = time.time()
        ns.sort(key=lambda x: x["t"])
        for k in range(6):
            rng = np.random.default_rng(hash((part, k)) & 0xFFFF)
            singer = dict(detune=rng.normal(0, 7), vib=rng.uniform(0.7, 1.3), rate=rng.uniform(0.9, 1.12),
                          fscale=rng.uniform(0.96, 1.04), gain=rng.uniform(0.8, 1.1),
                          breath=rng.uniform(0, 0.03))
            shifted = [dict(n, t=n["t"] + rng.normal(0, 0.012)) for n in ns]
            y = voice.render_voice(part, shifted, N, seed=1000 + k + 10 * list(CHORUS_PAN).index(part),
                                   singer=singer) * 0.2
            pan = CHORUS_PAN[part] + rng.uniform(-0.12, 0.12)
            st = fx.stereo(y, pan)
            bus.dry += st
            sends = split_by_space(st * 0.42)
            for space, p in sends.items():
                bus.sends[space] += p * (1 - stabat)
            bus.sends["church"] += st * 0.55 * stabat
        log(f"  vox chorus {part}  {len(ns):4d} notes x6  {time.time() - t0:5.1f}s")
    # smoothed solo envelope for dialogue-priority ducking of the score
    a = math.exp(-1.0 / (0.05 * SR))
    env = dsp.onepole_lp(solo_env.astype(np.float64), np.full(N, math.exp(-1.0 / (0.25 * SR))))
    return bus, env.astype(np.float32), elena_dry, vittorio_vision


# ============================================================================ tiers 3-5

GEN = {
    "hall_air": fx.hall_air, "walla": fx.walla, "rustle": fx.rustle, "cough": fx.cough,
    "applause": fx.applause, "footsteps": fx.footsteps, "pressure": fx.pressure,
    "swifts": fx.swifts, "cicadas": fx.cicadas, "distant_bell": fx.distant_bell, "cart": fx.cart,
    "breath": fx.breath, "room_tone": fx.room_tone, "clock": fx.clock, "silk": fx.silk,
    "rice": fx.rice, "sub_hit": fx.sub_hit, "wind": fx.wind, "cradle": fx.cradle, "door": fx.door,
    "impact_slap": fx.impact_slap, "bodyfall": fx.bodyfall, "steam": fx.steam,
    "locomotive": fx.locomotive, "pea_whistle": fx.pea_whistle, "steam_whistle": fx.steam_whistle,
    "suitcase": fx.suitcase, "shutters": fx.shutters, "sea": fx.sea, "gulls": fx.gulls,
    "ship_horn": fx.ship_horn, "tram_bell": fx.tram_bell, "paper": fx.paper, "heartbeat": fx.heartbeat,
    "clink": fx.clink, "chair": fx.chair, "curtain": fx.curtain, "air_rush": fx.air_rush,
}
POST_KEYS = ("fade_out", "duck_at", "duck_to", "recede", "wall", "soft")

# Each generated event is normalised to a target level (active RMS, dBFS) before its cue gain.
TARGET_DB = {
    # atmospheres
    "hall_air": -44, "room_tone": -47, "walla": -31, "applause": -23, "cough": -33, "rustle": -42,
    "swifts": -38, "cicadas": -43, "distant_bell": -34, "cart": -39, "clock": -41, "wind": -34,
    "shutters": -37, "sea": -34, "gulls": -37, "ship_horn": -36, "tram_bell": -38, "steam": -39,
    "locomotive": -29, "pea_whistle": -33, "steam_whistle": -29,
    # foley
    "footsteps": -33, "silk": -39, "paper": -33, "door": -29, "impact_slap": -27, "bodyfall": -31,
    "breath": -35, "clink": -35, "suitcase": -35, "curtain": -30, "rice": -39, "cradle": -41,
    "chair": -37,
    # design
    "pressure": -33, "sub_hit": -25, "heartbeat": -29, "air_rush": -31, "ghost": -33,
    "reverse_swell": -31,
}


def _norm_to(y, target_db):
    a = np.abs(y if y.ndim == 1 else y.max(axis=0))
    thr = a.max() * 1e-3
    act = a > thr
    if not act.any():
        return y
    r = float(np.sqrt(np.mean((y if y.ndim == 1 else y.mean(axis=0))[act] ** 2))) + 1e-12
    return y * (10 ** (target_db / 20) / r)


def render_events(events, score_mix=None, vittorio_vision=None):
    buses = {t: Bus() for t in ("foley", "atmos", "design")}
    for e in events:
        args = dict(e["args"])
        post = {k: args.pop(k) for k in POST_KEYS if k in args}
        gen = e["gen"]
        if gen == "ghost":
            # Vittorio's 'Elena' from the first vision, reversed and dissolved: her memory, not his voice
            seg = vittorio_vision[int(185.45 * SR): int(187.6 * SR)].copy()
            seg = seg[::-1] * np.hanning(len(seg)) ** 0.5
            seg = dsp.eq(dsp.eq(seg, "lp", 1600, 0.7), "hp", 200, 0.7)
            y = fx.stereo(seg.astype(np.float32), 0.0)
            wl, wr = reverb.convolve_stereo(y[0], y[1], "vision")
            y = (np.stack([wl, wr]) + y * 0.4) * 1.2
        elif gen == "reverse_swell":
            s0 = int(args["src_t"] * SR)
            L = int(args["length"] * SR)
            seg = score_mix[:, s0:s0 + int(0.8 * SR)].copy()
            wl, wr = reverb.convolve_stereo(seg[0], seg[1], "church")
            tail = np.stack([wl, wr])[:, :L]
            y = tail[:, ::-1] * np.linspace(0, 1, tail.shape[1]) ** 2
            y = _norm_to(y, TARGET_DB["reverse_swell"])
            buses["design"].add(y.astype(np.float32), int(e["t"] * SR) - y.shape[1], gain=e["gain"])
            continue
        else:
            fn = GEN[gen]
            if "seed" not in args:
                args["seed"] = 0
            y = fn(**args)
        y = np.asarray(y, dtype=np.float32)
        if gen in TARGET_DB:
            y = _norm_to(y, TARGET_DB[gen]).astype(np.float32)
        if y.ndim == 1:
            y = fx.stereo(y, e["pan"])
        n = y.shape[1]
        t = np.arange(n) / SR
        if "fade_out" in post:
            y *= np.clip((n / SR - t) / post["fade_out"], 0, 1)
        if "duck_at" in post:
            y *= np.where(t < post["duck_at"], 1.0,
                          post["duck_to"] + (1 - post["duck_to"]) * np.exp(-(t - post["duck_at"]) / 0.8))
        if post.get("recede"):
            y = np.stack([dsp.eq(y[c], "lp", 2500, 0.7) for c in range(2)]) * np.linspace(1.0, 0.45, n)
        if post.get("wall"):
            y = np.stack([dsp.eq(y[c], "lp", 1300, 0.7) for c in range(2)])
        if post.get("soft"):
            y = np.stack([dsp.eq(y[c], "lp", 3000, 0.7) for c in range(2)]) * 0.7
        y = y.astype(np.float32)
        space = e["space"]
        send = {"foley": 0.22, "atmos": 0.3, "design": 0.0}[e["tier"]]
        if space in ("hall", "church"):
            send *= 1.4
        buses[e["tier"]].add(y, int(e["t"] * SR), send if space else 0.0, space, e["gain"])
    return buses


# ============================================================================ automation & master

def k_weight(x):
    y = dsp.biquad(x.astype(np.float64), *dsp.rbj("highshelf", 1681.97, 0.7071, 4.0))
    y = dsp.biquad(y, *dsp.rbj("hp", 38.13, 0.5))
    return y


def lufs(st):
    kw = [k_weight(st[c]) for c in range(2)]
    blk = int(0.4 * SR)
    hop = int(0.1 * SR)
    ms = []
    for i in range(0, st.shape[1] - blk, hop):
        ms.append(sum(np.mean(k[i:i + blk] ** 2) for k in kw))
    ms = np.array(ms)
    l = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[l > -70]
    if len(g) == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(g)) - 10
    g2 = ms[(l > -70) & (l > rel)]
    return float(-0.691 + 10 * np.log10(np.mean(g2)))


def true_peak_limit(st, ceiling_db=-1.0, look=0.005, release=0.08):
    ceiling = 10 ** (ceiling_db / 20)
    over = np.abs(resample_poly(st, 4, 1, axis=1)).max(axis=0)
    peak = over.reshape(-1, 4).max(axis=1)[: st.shape[1]]
    if len(peak) < st.shape[1]:
        peak = np.pad(peak, (0, st.shape[1] - len(peak)))
    gain = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    la = int(look * SR)
    # look-ahead minimum, then smooth release
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(gain, size=2 * la + 1, origin=0)
    g = np.roll(g, -la)
    rel = math.exp(-1.0 / (release * SR))
    sm = dsp.onepole_lp(g.astype(np.float64), np.full(len(g), rel))
    sm = np.minimum(sm, g)
    return st * sm.astype(np.float32)


def deess(st, f_split=4500.0, ratio=3.0, k=0.55):
    """Split-band de-esser: when the band above f_split exceeds k x the body's envelope, reduce it."""
    out = np.empty_like(st)
    a = math.exp(-1.0 / (0.004 * SR))
    r = math.exp(-1.0 / (0.06 * SR))
    for c in range(2):
        x = st[c].astype(np.float64)
        hi = dsp.eq(dsp.eq(x, "hp", f_split, 0.7), "hp", f_split, 0.7)
        lo = x - hi
        eh = dsp.onepole_lp(np.abs(hi), np.full(len(x), a))
        el = dsp.onepole_lp(np.abs(lo), np.full(len(x), r))
        over = np.maximum(1.0, eh / (k * el + 1e-6))
        g = over ** (-(1 - 1 / ratio))
        g = dsp.onepole_lp(g, np.full(len(x), math.exp(-1.0 / (0.003 * SR))))
        out[c] = (lo + hi * g).astype(np.float32)
    return out


def glue(st, thresh_db=-20.0, ratio=1.6, rms_s=0.3):
    mono = 0.5 * (st[0] + st[1])
    env = np.sqrt(dsp.onepole_lp((mono.astype(np.float64)) ** 2, np.full(N, math.exp(-1 / (rms_s * SR)))) + 1e-12)
    lvl = 20 * np.log10(env)
    over = np.maximum(0, lvl - thresh_db)
    gr = -over * (1 - 1 / ratio)
    g = 10 ** (gr / 20)
    return st * g.astype(np.float32)


def write_wav(path, st, bits=24):
    st = np.clip(st, -1.0, 1.0)
    if bits == 24:
        x = np.ascontiguousarray((st.T * (2 ** 23 - 1)).astype("<i4"))
        b = np.ascontiguousarray(x.view(np.uint8).reshape(-1, 4)[:, :3]).tobytes()
        import wave
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(3)
            w.setframerate(SR)
            w.writeframes(b)
    else:
        wavfile.write(path, SR, (st.T * 32767).astype(np.int16))


CACHE = AUDIO_OUT / "cache"


def _cached_arrays(name, key, fn):
    """Cache expensive renders as plain arrays in .npz (no pickling), keyed by input hash."""
    import hashlib
    CACHE.mkdir(exist_ok=True)
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    path = CACHE / f"{name}_{h}.npz"
    if path.exists():
        log(f"  (cache) {name}")
        with np.load(path, allow_pickle=False) as z:
            return {k: z[k] for k in z.files}
    out = fn()
    for old in CACHE.glob(f"{name}_*.npz"):
        old.unlink()
    np.savez(path, **out)
    return out


def _src_key(*modules):
    from pathlib import Path
    return "".join(Path(m.__file__).read_text(encoding="utf-8") for m in modules)


def render():
    t_all = time.time()
    tl = json.loads(TIMELINE_JSON.read_text(encoding="utf-8"))
    notes, cues = tl["notes"], tl["cues"]
    score_notes = [n for n in notes if n["inst"] not in voice.VOICE_TYPES]
    vox_notes = [n for n in notes if n["inst"] in voice.VOICE_TYPES]
    log("TIER 2: SCORE")

    def _score():
        sb = render_score(score_notes)
        return {"score": sb.dry + sb.wet()}
    score = _cached_arrays("score", json.dumps(score_notes) + _src_key(ins, dsp, reverb), _score)["score"]
    log("TIER 1: VOX")

    def _vox():
        vb_, env_, el_, vi_ = render_vox(vox_notes)
        out = {"dry": vb_.dry, "env": env_, "elena": el_, "vitt": vi_}
        for sp, arr in vb_.sends.items():
            out["send_" + sp] = arr
        return out
    vz = _cached_arrays("vox", json.dumps(vox_notes) + _src_key(voice, dsp), _vox)
    vb = Bus()
    vb.dry = vz["dry"].copy()
    for k in vz:
        if k.startswith("send_"):
            vb.sends[k[5:]] = vz[k].copy()
    solo_env, elena_dry, vitt = vz["env"], vz["elena"], vz["vitt"]
    # the wide shot: Elena's voice blooms under the dome; the close-up is drier and nearer
    wide = window_mask([(cues["s11.wide"], cues["s11.closeup"])], 0.3)
    close = window_mask([(cues["s11.closeup"], cues["s11.vittorio4"])], 0.3)
    vb.sends["dome"] += elena_dry * 0.55 * wide
    vb.sends["hall"] -= elena_dry * 0.26 * 0.55 * close
    vox = vb.dry + vb.wet() + elena_dry * 0.18 * close
    log("TIERS 3-5: FOLEY, ATMOS, DESIGN")
    events = cue_sheet(cues)
    eb = render_events(events, score_mix=score, vittorio_vision=vitt)
    foley = eb["foley"].dry + eb["foley"].wet()
    atmos = eb["atmos"].dry + eb["atmos"].wet()
    design = eb["design"].dry + eb["design"].wet()
    # ---- automation: dialogue priority (the orchestra yields a little to the singers)
    e = solo_env / (np.percentile(solo_env[solo_env > 1e-4], 90) + 1e-9)
    duck = 1.0 - 0.25 * np.clip(e, 0, 1)
    score *= duck.astype(np.float32)
    # ---- automation: Elena's perception (S10). The score is warm; she hears it through fear.
    tun = window_mask([(cues["s10.heat_start"], cues["s10.heat_end"])], 0.6)
    for tier in (score, vox):
        lp = np.stack([dsp.eq(dsp.eq(tier[c], "lp", 700, 0.7), "lp", 700, 0.7) for c in range(2)]).astype(np.float32)
        tier[:] = tier * (1 - tun) + lp * tun * 0.8
    atmos *= (1 - 0.6 * tun)
    # ---- the trattoria waltz is written very softly (pizzicato); lift it to sit with the voices
    tr = window_mask([(cues["s08.start"], cues["s08.nives"])], 0.5)
    score *= (1.0 + 6.0 * tr).astype(np.float32)
    # ---- de-ess the voices: tame 4.5-10 kHz bursts relative to the body of the voice
    vox = deess(vox)
    # ---- calibrate the musical tiers (RMS over active time); event tiers are already levelled
    def act_rms(x):
        m = np.abs(x).max(axis=0) > 1e-4
        return float(np.sqrt(np.mean(x[:, m] ** 2))) if m.any() else 1e-9
    targets = {"score": -23.0, "vox": -20.5}
    fixed = {"foley": 0.0, "atmos": 0.0, "design": -1.0}
    stems = {"vox": vox, "score": score, "foley": foley, "atmos": atmos, "design": design}
    for k, x in stems.items():
        if k in targets:
            r = act_rms(x)
            g = 10 ** (targets[k] / 20) / r
        else:
            g = 10 ** (fixed[k] / 20)
            r = act_rms(x)
        stems[k] = x * g
        log(f"  {k:6s} active rms {20 * math.log10(r):6.1f} dB -> gain {20 * math.log10(g):+6.1f} dB")
    master = sum(stems.values())
    master = np.stack([dsp.eq(master[c], "hp", 18, 0.7) for c in range(2)]).astype(np.float32)
    master = glue(master, ratio=1.35)
    L = lufs(master)
    g = 10 ** ((-16.0 - L) / 20)
    master *= g
    for k in stems:
        stems[k] = stems[k] * g
    master = true_peak_limit(master, -1.0)
    L2 = lufs(master)
    log(f"loudness: pre {L:.1f} LUFS -> master {L2:.1f} LUFS, peak {20 * np.log10(np.abs(master).max()):.2f} dBFS")
    for i, k in enumerate(TIERS, 1):
        # stems are pre-limiter, so they are delivered as 32-bit float (no clipping)
        wavfile.write(AUDIO_OUT / f"stem_{i}_{k}.wav", SR, np.ascontiguousarray(stems[k].T.astype(np.float32)))
    write_wav(AUDIO_OUT / "elena_master.wav", master)
    # envelopes for the picture: Elena's voice level (chandeliers, neck tension) and per-tier RMS
    fps = 30
    hop = SR // fps
    def env_of(x):
        m = x if x.ndim == 1 else 0.5 * (np.abs(x[0]) + np.abs(x[1]))
        frames = len(m) // hop
        return np.sqrt(np.mean(m[: frames * hop].reshape(frames, hop) ** 2, axis=1)).tolist()
    envs = {"elena": env_of(elena_dry[0]), "vox": env_of(stems["vox"]), "score": env_of(stems["score"]),
            "master": env_of(master)}
    (AUDIO_OUT / "envelopes.json").write_text(json.dumps(envs))
    log(f"done in {time.time() - t_all:.0f}s")


if __name__ == "__main__":
    render()
