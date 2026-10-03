"""Orchestration for the full score: accompaniment styles driven by a chord progression.

Every function takes a progression (the textures module's list of (beat, dur, Chord)) in section beats
and returns parts as [(inst, [Ev], tags)]. Velocities scale with `dyn` (0..1). `avoid` holds pitch
classes that must not sound (after the Requiem: A).
"""
from __future__ import annotations

import random

from ..compose import textures as tx
from ..notation import Ev
from ..theory import Chord, pcs_in_range

RANGES = {
    "vn1": (55, 93), "vn2": (55, 86), "va": (48, 79), "vc": (36, 69), "cb": (28, 52),
    "fl": (62, 93), "ob": (60, 88), "eh": (53, 81), "cl": (52, 86), "bn": (36, 67),
    "hn": (43, 74), "tpt": (58, 81), "tbn": (40, 70), "tuba": (29, 55), "harp": (36, 91),
    "organ": (36, 86), "celesta": (60, 91),
}


def V(dyn, k=1.0):
    """Velocity from a dynamic level 0..1."""
    return max(0.08, min(0.95, (0.18 + 0.68 * dyn) * k))


def _clean(p, avoid):
    """Drop avoided pitch classes from every chord (an F chord without A keeps its open fifth)."""
    if not avoid:
        return p
    out = []
    for b, d, c in p:
        if c is None:
            out.append((b, d, c))
            continue
        pcs = [x for x in c.pcs if x not in avoid]
        if c.bass in avoid or not pcs:
            out.append((b, d, None))
            continue
        out.append((b, d, c))
    return out


def _bass_line(p, lo, hi, vel, pattern=None, art="", avoid=frozenset()):
    evs = []
    prev = None
    for b, d, c in p:
        if c is None or c.bass in avoid:
            continue
        cands = pcs_in_range({c.bass}, lo, hi)
        if not cands:
            continue
        m = cands[len(cands) // 2] if prev is None else min(cands, key=lambda x: abs(x - prev))
        prev = m
        for off, dd in (pattern or [(0.0, d)]):
            if off < d - 1e-9:
                evs.append(Ev(b + off, min(dd, d - off), m, vel, art))
    return evs


def _sust(p, insts, vel, avoid, tech="", tie=True, env=None):
    ranges = [RANGES[i] if i in RANGES else (48, 79) for i in insts]
    # narrow each range a little so the voicing spreads across instruments
    lines = tx.sustain(p, ranges, vel=vel, include_bass=False, avoid_pcs=set(avoid) or None)
    out = []
    for inst, evs in zip(insts, lines):
        evs = [e for e in evs if int(round(e.midi)) % 12 not in avoid]
        tags = {}
        if tech:
            tags["tech"] = tech
        if env:
            for e in evs:
                e.tags["env"] = env
        out.append((inst, evs, tags))
    return out


def pad(p, dyn, avoid=frozenset(), sord=False, with_bass=True, high=False):
    """Sustained strings (no synthesiser: five modelled string sections)."""
    p = _clean(p, avoid)
    insts = ["vn2", "va", "vc"] if not high else ["vn1", "vn2", "va"]
    parts = _sust(p, insts, V(dyn, 0.75), avoid, tech="sord" if sord else "")
    if with_bass:
        parts.append(("cb", _bass_line(p, 28, 50, V(dyn, 0.7), avoid=avoid), {"tech": "sord"} if sord else {}))
    return parts


def arpeggio(p, dyn, avoid=frozenset(), step=0.5, shape="updown", lo=43, hi=84, strings=True, seed=1):
    """Harp arpeggios over a soft string sustain: the cantabile's bed."""
    p = _clean(p, avoid)
    parts = [("harp", tx.arp(p, step=step, lo=lo, hi=hi, vel=V(dyn, 0.8), shape=shape,
                             avoid_pcs=set(avoid) or None, seed=seed), {})]
    if strings:
        parts += _sust(p, ["va", "vc"], V(dyn, 0.55), avoid, tech="sord")
        parts.append(("cb", _bass_line(p, 28, 48, V(dyn, 0.55), avoid=avoid), {}))
    return parts


def chitarra(p, dyn, bar_len=4.0, avoid=frozenset(), arco=False):
    """Verdi's 'big guitar': bass on the beat, chords off it (2/4, 4/4); um-pa-pa in 3/4."""
    p = _clean(p, avoid)
    beat = 1.0
    bass_pat, chord_pat = [], []
    if abs(bar_len - 3.0) < 1e-6:
        bass_pat = [(0.0, 0.5)]
        chord_pat = [(1.0, 0.4), (2.0, 0.4)]
    else:
        bass_pat = [(k * beat, 0.45) for k in range(int(bar_len))]
        chord_pat = [(k * beat + 0.5, 0.3) for k in range(int(bar_len))]
    bass_evs, stab_evs = [], []
    vs = tx.voicings(p, [(55, 67), (59, 71), (62, 74)], include_bass=False, avoid_pcs=set(avoid) or None)
    prev = None
    for (b, d, c), (_, _, v) in zip(p, vs):
        if c is None or v is None:
            continue
        cands = pcs_in_range({c.bass}, 36, 50)
        m = cands[len(cands) // 2] if prev is None else min(cands, key=lambda x: abs(x - prev))
        prev = m
        span = d
        k = 0.0
        while k < span - 1e-9:
            for off, dd in bass_pat:
                if k + off < span - 1e-9:
                    bass_evs.append(Ev(b + k + off, dd, m, V(dyn, 0.85), "'"))
            for off, dd in chord_pat:
                if k + off < span - 1e-9:
                    for x in v:
                        if x % 12 not in avoid:
                            stab_evs.append(Ev(b + k + off, dd, x, V(dyn, 0.6), "'"))
            k += bar_len
    tech = {} if arco else {"tech": "pizz"}
    return [("vc", bass_evs, tech), ("cb", tx.transpose(bass_evs, -12), tech),
            ("va", [e for e in stab_evs if e.midi < 66], tech), ("vn2", [e for e in stab_evs if e.midi >= 66], tech),
            ("bn", tx.vel_scale(tx.clone(bass_evs), 0.5), {})]


def waltz(p, dyn, avoid=frozenset()):
    return chitarra(p, dyn, bar_len=3.0, avoid=avoid)


def barcarolle(p, dyn, avoid=frozenset()):
    """6/8 rocking for the sea and the cradle: bass on the dotted beats, rocking quavers above."""
    p = _clean(p, avoid)
    bass = _bass_line(p, 36, 52, V(dyn, 0.75), pattern=[(0.0, 1.4), (1.5, 1.4), (3.0, 1.4), (4.5, 1.4)], avoid=avoid)
    rock = tx.rocking(p, lo=55, hi=76, vel=V(dyn, 0.6), step=0.5, avoid_pcs=set(avoid) or None)
    return [("vc", bass, {}), ("harp", rock, {}), ("cb", tx.transpose(bass, -12), {"tech": "pizz"})] + \
        _sust(p, ["va"], V(dyn, 0.45), avoid, tech="sord")


def lullaby(p, dyn, avoid=frozenset()):
    p = _clean(p, avoid)
    rock = tx.rocking(p, lo=57, hi=77, vel=V(dyn, 0.55), step=0.5, avoid_pcs=set(avoid) or None)
    parts = [("harp", rock, {})] + _sust(p, ["vn2", "va", "vc"], V(dyn, 0.5), avoid, tech="sord")
    parts.append(("cb", _bass_line(p, 28, 45, V(dyn, 0.45), avoid=avoid), {"tech": "sord"}))
    return parts


def furlana(p, dyn, avoid=frozenset()):
    p = _clean(p, avoid)
    return [("vn2", tx.furlana(p, 55, 74, V(dyn, 0.7)), {}),
            ("vc", _bass_line(p, 36, 52, V(dyn, 0.8), pattern=[(0.0, 1.2), (1.5, 1.2)], avoid=avoid), {}),
            ("cb", _bass_line(p, 28, 43, V(dyn, 0.7), pattern=[(0.0, 1.2)], avoid=avoid), {"tech": "pizz"})]


def tremolo(p, dyn, avoid=frozenset(), low=True):
    """Agitation: tremolo strings, the basses pulsing."""
    p = _clean(p, avoid)
    parts = _sust(p, ["vn1", "vn2", "va"], V(dyn, 0.7), avoid, tech="trem")
    if low:
        parts.append(("vc", _bass_line(p, 36, 55, V(dyn, 0.75), pattern=[(k * 0.5, 0.4) for k in range(16)],
                                       art="'", avoid=avoid), {}))
        parts.append(("cb", _bass_line(p, 28, 45, V(dyn, 0.7), avoid=avoid), {"tech": "trem"}))
    return parts


def recit_bed(p, dyn, avoid=frozenset()):
    """Accompanied recitative: a held chord in the lower strings, the bass on the root."""
    p = _clean(p, avoid)
    parts = _sust(p, ["va", "vc"], V(dyn, 0.5), avoid)
    parts.append(("cb", _bass_line(p, 28, 48, V(dyn, 0.55), avoid=avoid), {}))
    return parts


def strike(beat, chord: Chord, dyn, avoid=frozenset(), dur=0.5, brass=True):
    """A punctuating tutti chord (accompagnato), short."""
    parts = []
    tones = [m for m in pcs_in_range(set(chord.pcs) - set(avoid), 52, 79)][:6]
    bassn = pcs_in_range({chord.bass}, 33, 47)
    for inst, lo, hi in (("vn1", 64, 84), ("vn2", 57, 76), ("va", 50, 69)):
        sel = [m for m in tones if lo <= m <= hi][:2]
        parts.append((inst, [Ev(beat, dur, m, V(dyn), ">") for m in sel], {}))
    if bassn and chord.bass not in avoid:
        parts.append(("vc", [Ev(beat, dur, bassn[-1], V(dyn), ">")], {}))
        parts.append(("cb", [Ev(beat, dur, bassn[0], V(dyn), ">")], {}))
    if brass:
        hs = [m for m in pcs_in_range(set(chord.pcs) - set(avoid), 50, 67)][:3]
        parts.append(("hn", [Ev(beat, dur * 1.2, m, V(dyn, 0.8), ">") for m in hs], {}))
    return parts


def chorale(p, dyn, family="winds", avoid=frozenset()):
    p = _clean(p, avoid)
    if family == "brass":
        insts = ["tbn", "hn", "hn", "tpt"]
    elif family == "organ":
        lines = tx.chorale(p, vel=V(dyn, 0.8), avoid_pcs=set(avoid) or None)
        return [("organ", [e for ln in lines for e in ln if int(e.midi) % 12 not in avoid], {})]
    else:
        insts = ["bn", "cl", "cl", "ob"]
    lines = tx.chorale(p, vel=V(dyn, 0.8), avoid_pcs=set(avoid) or None)
    return [(i, [e for e in ln if int(e.midi) % 12 not in avoid], {}) for i, ln in zip(insts, lines)]


def tutti(p, dyn, avoid=frozenset(), timp=True):
    """Full orchestra sustain for climaxes."""
    p = _clean(p, avoid)
    parts = _sust(p, ["vn1", "vn2", "va", "vc"], V(dyn, 0.85), avoid)
    parts.append(("cb", _bass_line(p, 28, 48, V(dyn, 0.85), avoid=avoid), {}))
    parts += [(i, e, t) for i, e, t in chorale(p, dyn * 0.9, "brass", avoid)]
    parts += [(i, e, t) for i, e, t in chorale(p, dyn * 0.8, "winds", avoid)]
    if timp:
        roots = []
        for b, d, c in p:
            if c is None:
                continue
            for m in (c.root, c.fifth):
                if m is not None and m not in avoid:
                    cands = pcs_in_range({m}, 38, 53)
                    if cands:
                        roots.append(Ev(b, min(d, 1.0), cands[0], V(dyn, 0.7), ">"))
                        break
        parts.append(("timp", roots, {}))
    return parts


def march(p, dyn, avoid=frozenset()):
    p = _clean(p, avoid)
    parts = chitarra(p, dyn, 2.0, avoid, arco=True)
    hn = tx.chord_hits(p, [(0.5, 0.3), (1.5, 0.3)], [(52, 64), (55, 67)], vel=V(dyn, 0.6), art="'",
                       avoid_pcs=set(avoid) or None)
    parts.append(("hn", hn, {}))
    return parts


STYLES = {
    "pad": pad, "arpeggio": arpeggio, "chitarra": chitarra, "waltz": waltz, "barcarolle": barcarolle,
    "lullaby": lullaby, "furlana": furlana, "tremolo": tremolo, "recit": recit_bed, "tutti": tutti,
    "march": march, "chorale": chorale,
}


def accompany(style: str, p, dyn, bar_len=4.0, avoid=frozenset(), **kw):
    fn = STYLES[style]
    if style == "chitarra":
        return fn(p, dyn, bar_len=bar_len, avoid=avoid, **kw)
    return fn(p, dyn, avoid=avoid, **kw)


def double(evs, semis=0, vel_k=0.7, avoid=frozenset()):
    """Colla voce: an instrument doubling the singer (no lyrics)."""
    out = []
    for e in evs:
        m = e.midi + semis
        if int(round(m)) % 12 in avoid:
            continue
        out.append(Ev(e.beat, e.dur, m, e.vel * vel_k, e.art))
    return out
