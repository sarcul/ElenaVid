"""The full opera's cue sheet for tiers 3-5 (foley, atmos, design), built from the score timeline.

Every section has a location (set where the number was composed); each location has an
environment bed for the section's whole length, and foley and design events sit on the score's cues.
Event format is the film's (elenavid.audio.sounddesign.ev).
"""
from __future__ import annotations

from .sounddesign import ev

F, A, D = "foley", "atmos", "design"

CHURCHY = {"church_vow", "church_wedding", "church_cooling", "church_dusk", "funeral"}


def space_of(location: str) -> str:
    """The reverb space for a location's foley and atmos."""
    if location in CHURCHY:
        return "church"
    return {
        "house_prologue": "hall", "prelude": "hall", "house_intermission": "hall", "house_intermezzo": "hall",
        "house_finale": "hall", "opera_house": "hall",
        "village_market": "square", "village_farewell": "square", "village_road": "square",
        "interlude_seasons": "square", "parlour": "parlour", "interlude_verona": "tall_room",
        "verona_night": "tall_room", "station": "platform", "journey_map": "platform",
        "trieste_night": "small_room", "trieste_morning": "small_room", "interlude_sea": "street",
        "trieste_street": "street", "montage_cafe": "trattoria", "montage_home": "small_room",
        "montage_pier": "street", "stabat": "small_room", "trattoria": "trattoria", "deathbed": "small_room",
        "letter_room_dark": "small_room", "letter": "small_room", "split": "small_room",
        "marco_house": "small_room", "empty_room": "small_room",
    }.get(location, "hall")


def chained(tier, gen, t0, dur, space, chunk=45.0, gain=1.0, seed=0, **args):
    """A long bed as a chain of overlapping events (generators are built for tens of seconds)."""
    out = []
    t = t0
    k = 0
    while t < t0 + dur - 0.5:
        d = min(chunk + 2.0, t0 + dur - t)
        out.append(ev(tier, gen, t, space, gain=gain, dur=d, seed=seed + k, fade_out=min(2.0, d / 3), **args))
        t += chunk
        k += 1
    return out


def cue_sheet_full(tl) -> list:
    secs = tl["sections"]
    meta = tl.get("meta", {})
    c = tl["cues"]
    E = []
    seed = 1000
    for s in secs:
        key, t0, t1 = s["key"], s["start"], s["end"]
        dur = t1 - t0
        m = meta.get(key, {})
        loc = m.get("location", "prelude")
        sp = space_of(loc)
        seed += 50
        C = lambda name: c.get(f"{key}.{name}")
        if loc == "house_prologue":
            E += [ev(A, "hall_air", t0, "hall", dur=dur, seed=seed + 1),
                  ev(A, "walla", t0, "hall", gain=0.9, dur=min(dur, 12.0), talkers=26, seed=seed + 2, bright=0.5,
                     fade_out=3.0),
                  ev(A, "rustle", t0, "hall", gain=0.7, dur=min(dur, 18.0), seed=seed + 3),
                  ev(A, "cough", t0 + 3.4, "hall", pan=-0.4, gain=0.35, seed=seed + 4)]
            if C("applause") is not None:
                E += [ev(A, "applause", C("applause"), "hall", dur=6.2, density=230, seed=seed + 5),
                      ev(F, "footsteps", C("applause") + 0.3, "hall", pan=0.25, gain=0.45,
                         times=[0, .55, 1.1, 1.62, 2.1], surface="boards", seed=seed + 6)]
            if C("hush") is not None:
                E += [ev(A, "rustle", C("hush"), "hall", gain=0.8, dur=2.0, seed=seed + 7, bright=1.2),
                      ev(A, "cough", C("hush") + 0.9, "hall", pan=0.55, gain=0.4, seed=seed + 8)]
            if C("title_in") is not None:
                E.append(ev(D, "pressure", C("title_in") - 1.0, None, gain=0.45, dur=7.0, seed=seed + 9, f=31.0))
        elif loc in ("prelude", "house_intermezzo"):
            E += chained(A, "hall_air", t0, dur, "hall", chunk=60.0, gain=0.7, seed=seed)
            E.append(ev(A, "rustle", t0 + 2.0, "hall", gain=0.25, dur=3.0, seed=seed + 7))
        elif loc == "house_intermission":
            E += [ev(A, "hall_air", t0, "hall", dur=dur, seed=seed + 1),
                  ev(A, "applause", t0 + 0.3, "hall", gain=1.0, dur=min(dur - 6, 14.0), density=240, seed=seed + 2),
                  ev(A, "walla", t0 + 10.0, "hall", gain=0.55, dur=max(4.0, dur - 18.0), talkers=20, seed=seed + 3,
                     bright=0.6, fade_out=3.0),
                  ev(A, "rustle", t1 - 7.0, "hall", gain=0.6, dur=2.0, seed=seed + 4),
                  ev(A, "cough", t1 - 5.0, "hall", pan=-0.3, gain=0.3, seed=seed + 5)]
        elif loc == "house_finale":
            E += [ev(A, "hall_air", t0, "hall", dur=dur, seed=seed + 1),
                  ev(A, "applause", (C("applause") or t0 + 4.0), "hall", gain=1.1, dur=min(dur - 2, 20.0),
                     density=280, seed=seed + 2)]
            if C("title_in") is not None:
                E.append(ev(D, "pressure", C("title_in") - 1.0, None, gain=0.4, dur=8.0, seed=seed + 9, f=31.0))
        elif loc == "village_market":
            E += chained(A, "walla", t0, dur, "square", chunk=40.0, gain=0.55, seed=seed, talkers=16, bright=1.0)
            E += chained(A, "swifts", t0, dur, None, chunk=40.0, gain=0.8, seed=seed + 20, passes=5)
            E += chained(A, "cicadas", t0, dur, None, chunk=60.0, gain=0.6, seed=seed + 30)
            E += [ev(A, "distant_bell", t0 + 1.0, "square", pan=-0.6, gain=0.45, midi=62, seed=seed + 40),
                  ev(A, "distant_bell", t0 + 3.4, "square", pan=-0.6, gain=0.4, midi=62, seed=seed + 41),
                  ev(A, "cart", t0 + 9.0, "square", pan=0.5, gain=0.55, dur=6.0, seed=seed + 42)]
        elif loc in ("village_farewell", "village_road", "interlude_seasons"):
            E += chained(A, "cicadas", t0, dur, None, chunk=60.0, gain=0.5 if loc != "village_road" else 0.6,
                         seed=seed)
            E += chained(A, "swifts", t0, dur, None, chunk=50.0, gain=0.5, seed=seed + 20, passes=3)
            if loc == "village_road":
                E += chained(A, "wind", t0, dur, None, chunk=60.0, gain=0.25, seed=seed + 30, gusty=0.3,
                             whistle=False)
            if loc == "interlude_seasons":
                E += [ev(A, "distant_bell", t0 + 6.0, "square", pan=-0.6, gain=0.35, midi=62, seed=seed + 40),
                      ev(A, "distant_bell", t0 + 14.0, "square", pan=0.5, gain=0.3, midi=57, seed=seed + 41)]
        elif loc == "parlour":
            E += chained(A, "room_tone", t0, dur, "parlour", chunk=60.0, seed=seed, colour=1100)
            E += chained(A, "clock", t0, dur, "parlour", chunk=60.0, gain=0.5, seed=seed + 20, period=1.0)
        elif loc in CHURCHY or loc == "church_vow":
            E += chained(A, "room_tone", t0, dur, "church", chunk=60.0, gain=1.2, seed=seed, colour=500)
            E += [ev(A, "rustle", t0 + 1.0, "church", gain=0.5, dur=5.0, seed=seed + 20),
                  ev(F, "footsteps", t0 + 0.5, "church", gain=0.35, times=[0, .7, 1.4, 2.1, 2.8], surface="stone",
                     seed=seed + 21)]
            if C("vow") is not None:
                E.append(ev(F, "silk", C("vow") - 0.6, "church", gain=0.5, dur=2.4, seed=seed + 22))
            if C("wedding") is not None:
                E += [ev(D, "sub_hit", C("wedding"), None, gain=0.4, seed=seed + 23, f0=58, f1=36, decay=1.4),
                      ev(A, "distant_bell", C("wedding") + 6.0, "square", pan=-0.7, gain=0.3, midi=62, seed=seed + 24)]
            if C("cooling") is not None:
                E += [ev(F, "rice", C("cooling") - 0.5, "church", gain=0.7, dur=3.0, seed=seed + 25),
                      ev(D, "pressure", C("cooling"), None, gain=0.35, dur=5.0, seed=seed + 26, f=29.0)]
            if C("goes") is not None:
                E.append(ev(F, "footsteps", C("goes"), "church", gain=0.35, times=[0, .7, 1.4], surface="stone",
                            seed=seed + 27, recede=True))
            if loc == "funeral":
                E += [ev(F, "footsteps", t0 + 0.2, "church", gain=0.35, times=[0.9 * k for k in range(6)],
                         surface="stone", seed=seed + 28),
                      ev(A, "cough", t0 + dur * 0.4, "church", pan=0.6, gain=0.25, seed=seed + 29)]
            if loc == "church_dusk" and C("vision") is not None:
                E.append(ev(D, "pressure", C("vision"), None, gain=0.55, dur=24.0, seed=seed + 30, f=31.0))
        elif loc in ("interlude_verona", "verona_night"):
            E += chained(A, "room_tone", t0, dur, "tall_room", chunk=60.0, seed=seed, colour=600)
            E += chained(A, "clock", t0, dur, "tall_room", chunk=60.0, gain=0.6, seed=seed + 20, period=1.2)
            E += chained(A, "wind", t0, dur, None, chunk=60.0, gain=0.3, seed=seed + 30, gusty=0.5, whistle=False,
                         wall=True)
            if key == "N7":
                E += chained(F, "cradle", t0 + 2.0, dur - 4.0, "tall_room", chunk=40.0, gain=0.3, seed=seed + 40)
            if key == "N8":
                b = C("blow")
                E += [ev(F, "door", t0 + 0.4, "tall_room", pan=0.6, gain=0.55, kind="creak", seed=seed + 41),
                      ev(F, "footsteps", t0 + 1.0, "tall_room", pan=0.5, gain=0.8, times=[0, .62, 1.1, 1.85, 2.3],
                         surface="wood", seed=seed + 42),
                      ev(D, "pressure", t0 + 1.0, None, gain=0.6, dur=12.0, seed=seed + 43, f=31.0)]
                if b is not None:
                    E += [ev(F, "breath", b - 0.25, "tall_room", gain=0.6, kind="gasp", seed=seed + 44),
                          ev(F, "impact_slap", b, "tall_room", gain=0.6, seed=seed + 45),
                          ev(F, "bodyfall", b + 0.35, "tall_room", pan=-0.1, gain=0.6, seed=seed + 46),
                          ev(F, "footsteps", b + 1.2, "tall_room", pan=0.7, gain=0.4, times=[0, .38, .76, 1.14, 1.5],
                             surface="wood", seed=seed + 47, recede=True),
                          ev(F, "door", b + 3.2, "tall_room", pan=0.75, gain=0.4, kind="close", seed=seed + 48),
                          ev(D, "sub_hit", b, None, gain=1.0, seed=seed + 49, f0=50, f1=26, decay=2.2)]
                if C("resolve") is not None:
                    E += [ev(F, "breath", C("resolve") - 0.6, "tall_room", gain=0.5, kind="exhale", seed=seed + 50),
                          ev(F, "silk", C("resolve") - 0.3, "tall_room", gain=0.5, dur=1.6, seed=seed + 51)]
                E.append(ev(F, "curtain", t1 - 4.6, "hall", gain=0.9, dur=4.4, seed=seed + 52))
        elif loc == "station":
            dep = C("depart")
            E += [ev(A, "steam", t0, "platform", gain=0.85, dur=min(dur, 50.0), seed=seed, fade_out=2.0),
                  ev(A, "locomotive", t0, "platform", gain=0.8, dur=dur,
                     seed=seed + 1, depart_at=(dep - t0) if dep else None),
                  ev(A, "walla", t0, "platform", gain=0.3, dur=min(dur, 25.0), talkers=6, seed=seed + 2, bright=0.6,
                     fade_out=3),
                  ev(F, "suitcase", t0 + 1.4, "platform", pan=0.1, gain=0.6, seed=seed + 3),
                  ev(F, "footsteps", t0 + 2.0, "platform", pan=0.05, gain=0.45, times=[0.6 * k for k in range(6)],
                     surface="stone", seed=seed + 4)]
            if C("call") is not None:
                E.append(ev(A, "pea_whistle", C("call") - 0.3, "platform", pan=-0.5, gain=0.7, seed=seed + 5))
            if dep is not None:
                E += [ev(F, "door", dep - 3.0, "platform", pan=0.35, gain=0.55, kind="slam", seed=seed + 6),
                      ev(D, "pressure", dep - 0.5, None, gain=0.7, dur=6.0, seed=seed + 7, f=25.0),
                      ev(A, "steam", dep, "platform", gain=0.9, dur=min(12.0, t1 - dep), seed=seed + 8, fade_out=3.0)]
            if C("whistle") is not None:
                E.append(ev(A, "steam_whistle", C("whistle"), "platform", pan=0.3, gain=0.8, seed=seed + 9))
        elif loc == "journey_map":
            E += [ev(A, "locomotive", t0, "platform", gain=0.45, dur=dur, seed=seed, depart_at=0.0, fade_out=6.0),
                  ev(A, "wind", t0, None, gain=0.3, dur=dur, seed=seed + 1, gusty=0.6, whistle=False)]
        elif loc == "trieste_night":
            wake = C("wake") or t1
            E += chained(A, "room_tone", t0, dur, "small_room", chunk=60.0, seed=seed, colour=800)
            E += chained(A, "wind", t0, wake - t0, None, chunk=50.0, gain=0.8, seed=seed + 20, gusty=1.3,
                         whistle=True, wall=True)
            E += chained(A, "shutters", t0, wake - t0, "small_room", chunk=50.0, gain=0.5, seed=seed + 40)
            if C("vision") is not None:
                E += [ev(D, "pressure", C("vision"), None, gain=0.7, dur=max(4.0, wake - C("vision")), seed=seed + 60,
                         f=31.0),
                      ev(D, "heartbeat", max(C("vision"), wake - 14.0), None, gain=0.7, dur=13.0, bpm0=68, bpm1=108,
                         seed=seed + 61)]
            if C("wake") is not None:
                E += [ev(F, "breath", wake - 0.25, "small_room", gain=0.8, kind="gasp", seed=seed + 62),
                      ev(F, "silk", wake - 0.05, "small_room", gain=0.6, dur=1.0, seed=seed + 63),
                      ev(F, "breath", wake + 0.7, "small_room", gain=0.6, kind="panic", seed=seed + 64),
                      ev(D, "sub_hit", wake, None, gain=0.85, seed=seed + 65, f0=52, f1=27, decay=1.6)]
        elif loc in ("trieste_morning", "interlude_sea", "trieste_street", "montage_pier"):
            if loc == "trieste_morning":
                E += chained(A, "room_tone", t0, dur, "small_room", chunk=60.0, seed=seed, colour=800)
                E += chained(A, "sea", t0, dur, None, chunk=60.0, gain=0.4, seed=seed + 20, close=0.3, wall=True)
                if C("davide") is not None:
                    d = C("davide")
                    E += [ev(F, "footsteps", d - 1.6, "small_room", pan=0.4, gain=0.45, times=[0, .45, .9, 1.35],
                             surface="wood", seed=seed + 40),
                          ev(F, "door", d - 1.2, "small_room", pan=0.45, gain=0.4, kind="creak", seed=seed + 41),
                          ev(F, "paper", d + 3.0, "small_room", pan=0.15, gain=0.5, kind="crinkle", dur=1.0, seed=seed + 42)]
            else:
                E += chained(A, "sea", t0, dur, None, chunk=60.0, gain=0.55 if loc != "trieste_street" else 0.35,
                             seed=seed, close=0.6 if loc == "interlude_sea" else 0.25)
            E += chained(A, "gulls", t0 + 1.0, dur - 1.0, None, chunk=50.0, gain=0.55, seed=seed + 60, calls=3)
            if loc in ("trieste_street",):
                E += chained(A, "walla", t0, dur, "street", chunk=45.0, gain=0.35, seed=seed + 80, talkers=8, bright=0.7)
                E += [ev(A, "tram_bell", t0 + 4.0, "street", pan=0.6, gain=0.3, seed=seed + 90),
                      ev(F, "footsteps", t0 + 1.0, "street", gain=0.45, times=[0, .52, 1.04, 1.5], surface="stone",
                         seed=seed + 91)]
            if loc == "montage_pier" or loc == "interlude_sea":
                E += chained(A, "wind", t0, dur, None, chunk=60.0, gain=0.35, seed=seed + 100, gusty=0.9,
                             whistle=False)
            if loc == "trieste_morning":
                E.append(ev(A, "ship_horn", t0 + 9.0, "street", pan=-0.6, gain=0.4, seed=seed + 110))
        elif loc == "montage_cafe":
            # R3 moves café -> home -> pier; the location events say when
            evs = {e["where"]: e["t"] for e in m.get("events", []) if e.get("kind") == "location"}
            home = evs.get("montage_home", t0 + dur / 3)
            pier = evs.get("montage_pier", t0 + 2 * dur / 3)
            E += [ev(A, "walla", t0, "trattoria", gain=0.5, dur=home - t0, talkers=10, seed=seed, bright=0.8,
                     fade_out=1.0),
                  ev(F, "clink", t0 + 1.0, "trattoria", pan=0.1, gain=0.55, kind="cup", seed=seed + 1),
                  ev(F, "clink", t0 + 6.5, "trattoria", pan=-0.2, gain=0.5, kind="cup", seed=seed + 2),
                  ev(A, "room_tone", home, "small_room", gain=0.9, dur=pier - home, seed=seed + 3, colour=800),
                  ev(A, "clock", home, "small_room", pan=-0.5, gain=0.35, dur=pier - home, seed=seed + 4, period=1.0)]
            E += chained(A, "sea", pier, t1 - pier, None, chunk=60.0, gain=0.6, seed=seed + 10, close=0.6)
            E += chained(A, "wind", pier, t1 - pier, None, chunk=60.0, gain=0.4, seed=seed + 30, gusty=0.9,
                         whistle=False)
            E += chained(A, "gulls", pier + 0.5, t1 - pier - 0.5, None, chunk=50.0, gain=0.5, seed=seed + 50, calls=2)
        elif loc == "stabat":
            E += chained(A, "room_tone", t0, dur, "small_room", chunk=60.0, gain=0.6, seed=seed, colour=700)
            E += [ev(A, "ship_horn", t0 + 6.0, "street", pan=-0.7, gain=0.25, seed=seed + 20),
                  ev(F, "footsteps", t0 + 0.5, "small_room", gain=0.3, times=[0, .9, 1.8, 2.6], surface="wood",
                     seed=seed + 21),
                  ev(F, "silk", t0 + 3.0, "small_room", gain=0.35, dur=2.0, seed=seed + 22)]
            if C("gladius") is not None:
                E.append(ev(D, "pressure", C("gladius"), None, gain=0.5, dur=3.5, seed=seed + 23, f=41.2))
        elif loc == "trattoria":
            nv = C("nives") or t1
            E += [ev(A, "walla", t0, "trattoria", gain=0.75, dur=nv - t0, talkers=14, seed=seed, bright=0.9,
                     fade_out=0.3),
                  ev(F, "clink", t0 + 2.0, "trattoria", pan=0.05, gain=0.55, kind="glass", seed=seed + 1),
                  ev(F, "clink", t0 + 2.06, "trattoria", pan=-0.05, gain=0.5, kind="glass", seed=seed + 2),
                  ev(F, "clink", t0 + 7.5, "trattoria", pan=0.4, gain=0.4, kind="cup", seed=seed + 3)]
            if C("nives") is not None:
                E += [ev(F, "door", nv, "trattoria", pan=0.6, gain=0.75, kind="slam", seed=seed + 4),
                      ev(D, "sub_hit", nv, None, gain=0.45, seed=seed + 5, f0=50, f1=30, decay=1.2)]
            if C("run") is not None:
                E.append(ev(F, "footsteps", C("run"), "small_room", gain=0.65, times=[0.17 * k for k in range(24)],
                            surface="wood", seed=seed + 6))
        elif loc == "deathbed":
            E += chained(A, "room_tone", t0, dur, "small_room", chunk=60.0, seed=seed, colour=750)
            E += chained(A, "sea", t0, dur, None, chunk=60.0, gain=0.25, seed=seed + 20, close=0.1, wall=True)
            E += [ev(F, "door", t0 + 0.1, "small_room", pan=0.3, gain=0.5, kind="creak", seed=seed + 40),
                  ev(F, "breath", t0 + 0.4, "small_room", gain=0.6, kind="panic", seed=seed + 41)]
            if C("tone_fail") is not None:
                # the A fails: the room's air thickens until she dies
                E.append(ev(D, "pressure", C("tone_fail"), None, gain=0.4,
                            dur=max(3.0, (C("death") or C("tone_fail") + 6.0) - C("tone_fail") + 2.0),
                            seed=seed + 43, f=31.0))
            if C("death") is not None:
                E += [ev(F, "breath", C("death") - 3.0, "small_room", gain=0.35, kind="exhale", seed=seed + 42),
                      ev(D, "sub_hit", C("death"), None, gain=0.35, seed=seed + 44, f0=40, f1=29, decay=3.0)]
        elif loc in ("letter_room_dark", "letter", "split", "marco_house"):
            E += chained(A, "room_tone", t0, dur, "small_room", chunk=60.0, seed=seed, colour=800)
            if loc in ("letter", "letter_room_dark"):
                E += chained(A, "wind", t0, dur, None, chunk=60.0, gain=0.3, seed=seed + 20, gusty=0.6, whistle=False,
                             wall=True)
            if loc == "letter":
                E += chained(A, "clock", t0, min(dur, 60.0), "small_room", chunk=60.0, gain=0.35, seed=seed + 40,
                             period=1.0)
                if C("letter_slide") is not None:
                    E += [ev(F, "paper", C("letter_slide"), "small_room", pan=0.5, gain=0.85, kind="slide", dur=1.4,
                             seed=seed + 41),
                          ev(F, "footsteps", C("letter_slide") + 2.6, "small_room", pan=0.4, gain=0.4,
                             times=[0, .55, 1.1], surface="wood", seed=seed + 42)]
                if C("letter_open") is not None:
                    E += [ev(D, "pressure", C("letter_open") + 0.5, None, gain=0.3, dur=6.0, seed=seed + 45, f=31.0),
                          ev(F, "paper", C("letter_open"), "small_room", pan=0.3, gain=0.7, kind="crinkle", dur=1.3,
                             seed=seed + 43),
                          ev(F, "paper", C("letter_open") + 1.6, "small_room", pan=0.3, gain=0.6, kind="unfold",
                             dur=0.9, seed=seed + 44)]
            if loc == "split":
                hs, he = C("heat_start"), C("heat_end")
                if hs is not None:
                    E += [ev(F, "breath", hs + 0.3 + 1.2 * k, "small_room", gain=0.75 + 0.03 * k,
                             kind="gasp" if k == 3 else "panic", seed=seed + 50 + k) for k in range(4)]
                    E += [ev(D, "heartbeat", hs - 0.6, None, gain=1.0, dur=max(6.0, (he or hs + 7) - hs + 1.5),
                             bpm0=96, bpm1=138, seed=seed + 60),
                          ev(D, "ghost", hs + 1.4, None, gain=0.32, seed=seed + 61),
                          ev(D, "ghost", hs + 4.2, None, gain=0.26, seed=seed + 62)]
                if C("door") is not None:
                    dd = C("door")
                    E += [ev(F, "footsteps", dd - 2.0, "small_room", pan=0.4, gain=0.45, times=[0, .65, 1.3, 1.9],
                             surface="wood", seed=seed + 63, recede=True),
                          ev(F, "door", dd, "small_room", pan=0.55, gain=0.75, kind="close", seed=seed + 64),
                          ev(D, "sub_hit", dd, None, gain=0.6, seed=seed + 65, f0=48, f1=28, decay=1.6)]
            if loc == "marco_house":
                E += [ev(F, "footsteps", t0 + 0.5, "street", gain=0.35, times=[0, .5, 1.0], surface="stone",
                         seed=seed + 70),
                      ev(F, "door", t0 + 1.5, "small_room", pan=0.3, gain=0.45, kind="creak", seed=seed + 71)]
        elif loc == "empty_room":
            dl = C("dolly") or t0 + dur / 3
            E += [ev(A, "room_tone", t0, "small_room", gain=1.0, dur=dl - t0 + 0.5, seed=seed, colour=800, fade_out=1.0),
                  ev(A, "sea", t0, None, gain=0.25, dur=dl - t0, seed=seed + 1, close=0.1, wall=True, fade_out=1.0),
                  ev(A, "clock", t0, "small_room", pan=-0.5, gain=0.35, dur=max(1.0, dl - t0 - 0.5), seed=seed + 2,
                     period=1.0),
                  ev(F, "chair", t0 + 1.0, "small_room", pan=0.35, gain=0.45, seed=seed + 3),
                  ev(F, "silk", t0 + 4.6, "small_room", pan=-0.2, gain=0.3, dur=1.6, seed=seed + 4, soft=True),
                  ev(D, "air_rush", dl - 2.4, None, gain=0.55, dur=2.8, seed=seed + 5, rising=True),
                  ev(D, "reverse_swell", dl, None, gain=0.5, src_t=dl + 0.2, length=2.6, seed=seed + 6)]
            E += chained(A, "hall_air", dl - 1.0, t1 - dl + 1.0, "hall", chunk=60.0, gain=0.75, seed=seed + 10)
            if C("sing") is not None:
                E += [ev(F, "breath", C("sing") - 0.8, "hall", gain=0.35, kind="inhale", seed=seed + 30),
                      ev(F, "silk", C("sing") - 1.6, "hall", gain=0.5, dur=2.2, seed=seed + 31)]
            for nm, g, dd in (("wide", 0.45, 3.0), ("vittorio3", 0.45, 24.0), ("vittorio4", 0.35, 6.0)):
                if C(nm) is not None:
                    E.append(ev(D, "pressure", C(nm), None, gain=g, dur=dd, seed=seed + 40 + len(E) % 7, f=31.0))
            if C("final_chord") is not None:
                E.append(ev(F, "silk", C("final_chord") - 0.5, "hall", gain=0.4, dur=1.8, seed=seed + 50))
            if C("curtain") is not None:
                E += [ev(F, "curtain", C("curtain"), "hall", gain=1.0, dur=4.4, seed=seed + 51),
                      ev(D, "sub_hit", C("curtain") + 4.4, None, gain=0.7, seed=seed + 52, f0=45, f1=28, decay=2.0)]
        else:
            E += chained(A, "hall_air", t0, dur, "hall", chunk=60.0, gain=0.6, seed=seed)
        # act curtains: the prelude events say when the curtain rises; N8 and N22 place their own falls
        for e in m.get("events", []):
            if e.get("kind") == "curtain" and e.get("state") == "up":
                E.append(ev(F, "curtain", e["t"] - 1.0, "hall", gain=0.7, dur=4.0, seed=seed + 99))
            elif e.get("kind") == "curtain" and e.get("state") == "down" and key not in ("N8", "N22"):
                E += [ev(F, "curtain", e["t"], "hall", gain=0.9, dur=4.4, seed=seed + 98),
                      ev(D, "sub_hit", e["t"] + 4.4, None, gain=0.5, seed=seed + 97, f0=45, f1=26, decay=1.8)]
    return E
