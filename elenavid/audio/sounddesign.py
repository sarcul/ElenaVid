"""The cue sheet for tiers 3-5: every foley, ambience and design event, placed on score cues."""
from __future__ import annotations


def ev(tier, gen, t, space=None, pan=0.0, gain=1.0, **args):
    return dict(tier=tier, gen=gen, t=t, space=space, pan=pan, gain=gain, args=args)


def cue_sheet(c):
    """c: dict of cue name -> absolute seconds (from the score timeline)."""
    E = []
    F, A, D = "foley", "atmos", "design"
    # ------------------------------------------------------------ S00 the hall
    E += [ev(A, "hall_air", 0.0, "hall", gain=1.0, dur=26.0, seed=1),
          ev(A, "walla", 0.0, "hall", gain=0.9, dur=11.0, talkers=26, seed=2, bright=0.5, fade_out=3.0),
          ev(A, "rustle", 0.0, "hall", gain=0.7, dur=16.5, seed=3),
          ev(A, "cough", 3.1, "hall", pan=-0.4, gain=0.35, seed=4),
          ev(A, "applause", c["s00.applause"], "hall", gain=1.0, dur=5.6, density=230, seed=5),
          ev(F, "footsteps", 9.7, "hall", pan=0.25, gain=0.45, times=[0, .55, 1.1, 1.62, 2.1],
             surface="boards", seed=6),
          ev(A, "rustle", 14.4, "hall", gain=0.8, dur=1.8, seed=7, bright=1.2),
          ev(A, "cough", 15.2, "hall", pan=0.55, gain=0.4, seed=8),
          ev(D, "pressure", c["s00.title_in"] - 1.0, None, gain=0.45, dur=7.0, seed=9, f=31.0)]
    # ------------------------------------------------------------ S01 the village square
    s = c["s01.start"]
    E += [ev(A, "walla", s, "square", gain=0.85, dur=34.0, talkers=18, seed=11, bright=1.0,
             duck_at=c["s01.aria"] - s, duck_to=0.35),
          ev(A, "swifts", s, None, gain=1.0, dur=34.0, seed=12, passes=6),
          ev(A, "cicadas", s, None, gain=0.8, dur=34.0, seed=13),
          ev(A, "distant_bell", s + 1.0, "square", pan=-0.6, gain=0.45, midi=62, seed=14),
          ev(A, "distant_bell", s + 3.4, "square", pan=-0.6, gain=0.4, midi=62, seed=15),
          ev(A, "cart", s + 8.0, "square", pan=0.5, gain=0.6, dur=6.0, seed=16),
          ev(F, "footsteps", c["s01.marco_leaves"], "square", pan=0.3, gain=0.6,
             times=[0.55 * k for k in range(8)], surface="stone", seed=17, recede=True),
          ev(F, "breath", c["s01.aria"] - 0.7, "square", gain=0.45, kind="sigh", seed=18)]
    # ------------------------------------------------------------ S02 parlour, church
    E += [ev(A, "room_tone", c["s02.start"], "parlour", gain=1.0, dur=20.0, seed=21, colour=1100),
          ev(A, "clock", c["s02.start"], "parlour", pan=0.5, gain=0.55, dur=20.0, seed=22, period=1.0),
          ev(A, "room_tone", c["s02.church"], "church", gain=1.2, dur=42.0, seed=23, colour=500),
          ev(A, "rustle", c["s02.church"], "church", gain=0.6, dur=6.0, seed=24),
          ev(F, "footsteps", c["s02.church"] + 0.3, "church", gain=0.4,
             times=[0, .7, 1.4, 2.1, 2.8], surface="stone", seed=25),
          ev(F, "silk", c["s02.church"] + 0.4, "church", gain=0.55, dur=2.6, seed=26),
          ev(A, "distant_bell", c["s02.refrain"] - 8.0, "square", pan=-0.7, gain=0.3, midi=62, seed=27),
          ev(A, "distant_bell", c["s02.refrain"] + 4.0, "square", pan=0.7, gain=0.28, midi=57, seed=28),
          ev(F, "rice", c["s02.cooling"] - 0.5, "church", gain=0.7, dur=3.0, seed=29),
          ev(D, "pressure", c["s02.lift"] - 0.9, None, gain=0.5, dur=1.8, seed=30, f=36.0),
          ev(D, "sub_hit", c["s02.wedding"], None, gain=0.4, seed=31, f0=58, f1=36, decay=1.4),
          ev(D, "pressure", c["s02.cooling"], None, gain=0.35, dur=4.5, seed=32, f=29.0)]
    # ------------------------------------------------------------ S03 the Verona house
    s = c["s03.start"]
    E += [ev(A, "room_tone", s, "tall_room", gain=1.0, dur=40.0, seed=41, colour=600),
          ev(A, "clock", s, "tall_room", pan=-0.45, gain=0.7, dur=40.0, seed=42, period=1.2),
          ev(A, "wind", s, None, gain=0.3, dur=40.0, seed=43, gusty=0.5, whistle=False, wall=True),
          ev(F, "cradle", c["s03.lullaby"], "tall_room", pan=0.15, gain=0.35, dur=17.0, seed=44),
          ev(F, "door", c["s03.vittorio"] - 1.2, "tall_room", pan=0.6, gain=0.55, kind="creak", seed=45),
          ev(F, "footsteps", c["s03.vittorio"] - 0.6, "tall_room", pan=0.5, gain=0.8,
             times=[0, .62, 1.1, 1.85, 2.3], surface="wood", seed=46),
          ev(F, "breath", c["s03.blow"] - 0.25, "tall_room", gain=0.6, kind="gasp", seed=47),
          ev(F, "impact_slap", c["s03.blow"], "tall_room", gain=0.6, seed=48),
          ev(F, "bodyfall", c["s03.blow"] + 0.35, "tall_room", pan=-0.1, gain=0.6, seed=49),
          ev(F, "footsteps", c["s03.blow"] + 1.2, "tall_room", pan=0.7, gain=0.4,
             times=[0, .38, .76, 1.14, 1.5], surface="wood", seed=50, recede=True),
          ev(F, "door", c["s03.blow"] + 3.2, "tall_room", pan=0.75, gain=0.4, kind="close", seed=51),
          ev(F, "breath", c["s03.alone"] - 0.6, "tall_room", gain=0.5, kind="exhale", seed=52),
          ev(F, "silk", c["s03.resolve"] - 0.4, "tall_room", gain=0.5, dur=1.6, seed=53),
          ev(D, "pressure", c["s03.vittorio"], None, gain=0.6, dur=7.5, seed=54, f=31.0),
          ev(D, "sub_hit", c["s03.blow"], None, gain=1.0, seed=55, f0=50, f1=26, decay=2.2)]
    # ------------------------------------------------------------ S04 the platform
    s = c["s04.start"]
    E += [ev(A, "steam", s, "platform", gain=0.9, dur=22.0, seed=61),
          ev(A, "locomotive", s, "platform", gain=1.0, dur=22.0, seed=62, depart_at=c["s04.depart"] - s),
          ev(A, "pea_whistle", s + 0.15, "platform", pan=-0.5, gain=0.7, seed=63),
          ev(A, "walla", s, "platform", gain=0.35, dur=14.0, talkers=6, seed=64, bright=0.6, fade_out=3),
          ev(A, "steam_whistle", c["s04.whistle"], "platform", pan=0.3, gain=0.8, seed=65),
          ev(F, "suitcase", s + 1.4, "platform", pan=0.1, gain=0.6, seed=66),
          ev(F, "footsteps", s + 2.0, "platform", pan=0.05, gain=0.45, times=[0.6 * k for k in range(6)],
             surface="stone", seed=67),
          ev(F, "door", c["s04.depart"] - 3.0, "platform", pan=0.35, gain=0.55, kind="slam", seed=68),
          ev(D, "pressure", c["s04.depart"] - 0.5, None, gain=0.7, dur=5.0, seed=69, f=25.0)]
    # ------------------------------------------------------------ S05 Trieste: night, morning
    s = c["s05.start"]
    m = c["s05.morning"]
    E += [ev(A, "room_tone", s, "small_room", gain=1.0, dur=62.0, seed=71, colour=800),
          ev(A, "wind", s, None, gain=0.85, dur=m - s, seed=72, gusty=1.3, whistle=True, wall=True),
          ev(A, "shutters", s, "small_room", pan=0.4, gain=0.55, dur=m - s - 1, seed=73),
          ev(F, "breath", c["s05.wake"] - 0.25, "small_room", gain=0.8, kind="gasp", seed=74),
          ev(F, "silk", c["s05.wake"] - 0.05, "small_room", gain=0.6, dur=1.0, seed=75),
          ev(F, "breath", c["s05.wake"] + 0.7, "small_room", gain=0.6, kind="panic", seed=76),
          ev(A, "sea", m, None, gain=0.5, dur=246 - m, seed=77, close=0.3, wall=True),
          ev(A, "gulls", m + 0.3, None, gain=0.8, dur=246 - m - 0.5, seed=78, calls=6),
          ev(A, "ship_horn", m + 4.5, "street", pan=-0.6, gain=0.5, seed=79),
          ev(A, "tram_bell", m + 17.0, "street", pan=0.7, gain=0.25, seed=80),
          ev(F, "footsteps", m - 0.6, "small_room", pan=0.4, gain=0.45, times=[0, .45, .9, 1.35],
             surface="wood", seed=81),
          ev(F, "door", m - 0.3, "small_room", pan=0.45, gain=0.4, kind="creak", seed=82),
          ev(F, "paper", m + 1.3, "small_room", pan=0.15, gain=0.5, kind="crinkle", dur=1.0, seed=83),
          ev(D, "pressure", c["s05.vision"], None, gain=0.7, dur=24.0, seed=84, f=31.0),
          ev(D, "heartbeat", c["s05.vision"] + 12.0, None, gain=0.7, dur=12.0, bpm0=68, bpm1=108, seed=85),
          ev(D, "sub_hit", c["s05.wake"], None, gain=0.85, seed=86, f0=52, f1=27, decay=1.6)]
    # ------------------------------------------------------------ S06 a Trieste street
    s = c["s06.start"]
    E += [ev(A, "walla", s, "street", gain=0.45, dur=30.0, talkers=8, seed=91, bright=0.7),
          ev(A, "sea", s, None, gain=0.35, dur=30.0, seed=92, close=0.2),
          ev(A, "gulls", s + 2.0, None, gain=0.5, dur=26.0, seed=93, calls=2),
          ev(A, "tram_bell", s + 3.0, "street", pan=0.6, gain=0.35, seed=94),
          ev(F, "footsteps", s, "street", pan=-0.05, gain=0.5, times=[0, .52, 1.04, 1.5], surface="stone",
             seed=95)]
    # ------------------------------------------------------------ S07 months; vision; Stabat Mater
    s = c["s07.start"]
    E += [ev(A, "walla", s, "trattoria", gain=0.55, dur=7.5, talkers=10, seed=101, bright=0.8, fade_out=1.0),
          ev(F, "clink", s + 0.6, "trattoria", pan=0.1, gain=0.6, kind="cup", seed=102),
          ev(F, "clink", s + 4.3, "trattoria", pan=-0.2, gain=0.5, kind="cup", seed=103),
          ev(A, "sea", s + 7.0, None, gain=0.7, dur=7.5, seed=104, close=0.7),
          ev(A, "wind", s + 7.0, None, gain=0.45, dur=7.5, seed=105, gusty=0.8, whistle=False),
          ev(A, "gulls", s + 7.5, None, gain=0.6, dur=6.0, seed=106, calls=2),
          ev(A, "room_tone", c["s07.vision"], "church", gain=1.0, dur=24.0, seed=107, colour=500),
          ev(F, "footsteps", c["s07.stabat"] - 1.6, "church", gain=0.35, times=[0, .7, 1.4],
             surface="stone", seed=108, recede=True),
          ev(A, "room_tone", c["s07.stabat"], "small_room", gain=0.6, dur=50.0, seed=109, colour=700),
          ev(A, "ship_horn", c["s07.stabat"] + 6.0, "street", pan=-0.7, gain=0.25, seed=110),
          ev(F, "footsteps", c["s07.stabat"] + 0.5, "small_room", gain=0.3, times=[0, .9, 1.8, 2.6],
             surface="wood", seed=111),
          ev(F, "silk", c["s07.stabat"] + 3.0, "small_room", gain=0.35, dur=2.0, seed=112),
          ev(D, "pressure", c["s07.vision"], None, gain=0.6, dur=24.0, seed=113, f=31.0),
          ev(D, "pressure", c["s07.gladius"], None, gain=0.5, dur=3.5, seed=114, f=41.2)]
    # ------------------------------------------------------------ S08 trattoria; the deathbed
    s = c["s08.start"]
    E += [ev(A, "walla", s, "trattoria", gain=0.75, dur=10.3, talkers=14, seed=121, bright=0.9, fade_out=0.25),
          ev(F, "clink", s + 1.8, "trattoria", pan=0.05, gain=0.55, kind="glass", seed=122),
          ev(F, "clink", s + 1.86, "trattoria", pan=-0.05, gain=0.5, kind="glass", seed=123),
          ev(F, "clink", s + 5.5, "trattoria", pan=0.4, gain=0.4, kind="cup", seed=124),
          ev(F, "door", c["s08.nives"], "trattoria", pan=0.6, gain=0.75, kind="slam", seed=125),
          ev(F, "footsteps", c["s08.run"], "small_room", gain=0.65, times=[0.17 * k for k in range(11)],
             surface="wood", seed=126),
          ev(F, "door", c["s08.deathbed"] - 0.2, "small_room", pan=0.3, gain=0.5, kind="creak", seed=127),
          ev(F, "breath", c["s08.deathbed"] + 0.1, "small_room", gain=0.6, kind="panic", seed=128),
          ev(A, "room_tone", c["s08.deathbed"], "small_room", gain=1.0, dur=30.0, seed=129, colour=750),
          ev(A, "sea", c["s08.deathbed"], None, gain=0.25, dur=30.0, seed=130, close=0.1, wall=True),
          ev(F, "breath", c["s08.deathbed"] + 10.5, "small_room", gain=0.35, kind="exhale", seed=131),
          ev(D, "sub_hit", c["s08.nives"], None, gain=0.45, seed=132, f0=50, f1=30, decay=1.2)]
    # ------------------------------------------------------------ S09 Requiem
    s = c["s09.start"]
    E += [ev(A, "room_tone", s, "church", gain=1.2, dur=22.0, seed=141, colour=450),
          ev(A, "rustle", s, "church", gain=0.45, dur=4.0, seed=142),
          ev(F, "footsteps", s, "church", gain=0.35, times=[0, .9, 1.8, 2.7, 3.6], surface="stone", seed=143),
          ev(A, "cough", s + 8.0, "church", pan=0.6, gain=0.25, seed=144)]
    # ------------------------------------------------------------ S10 the letter
    s = c["s10.start"]
    E += [ev(A, "room_tone", s, "small_room", gain=1.0, dur=46.0, seed=151, colour=800),
          ev(A, "wind", s, None, gain=0.35, dur=46.0, seed=152, gusty=0.7, whistle=False, wall=True),
          ev(A, "clock", s, "small_room", pan=-0.5, gain=0.35, dur=21.0, seed=153, period=1.0),
          ev(F, "paper", c["s10.letter_slide"], "small_room", pan=0.5, gain=0.85, kind="slide", dur=1.4, seed=154),
          ev(F, "footsteps", s + 2.6, "small_room", pan=0.4, gain=0.4, times=[0, .55, 1.1], surface="wood",
             seed=155),
          ev(F, "paper", c["s10.letter_open"], "small_room", pan=0.3, gain=0.7, kind="crinkle", dur=1.3, seed=156),
          ev(F, "paper", c["s10.letter_open"] + 1.6, "small_room", pan=0.3, gain=0.6, kind="unfold", dur=0.9, seed=157),
          ev(F, "breath", c["s10.heat_start"] + 0.3, "small_room", gain=0.75, kind="panic", seed=158),
          ev(F, "breath", c["s10.heat_start"] + 1.5, "small_room", gain=0.8, kind="panic", seed=159),
          ev(F, "breath", c["s10.heat_start"] + 2.6, "small_room", gain=0.85, kind="panic", seed=160),
          ev(F, "breath", c["s10.heat_start"] + 3.8, "small_room", gain=0.85, kind="gasp", seed=161),
          ev(F, "footsteps", c["s10.heat_end"] + 0.3, "small_room", pan=-0.3, gain=0.4, times=[0, .4],
             surface="wood", seed=162),
          ev(F, "footsteps", c["s10.door"] - 2.0, "small_room", pan=0.4, gain=0.45, times=[0, .65, 1.3, 1.9],
             surface="wood", seed=163, recede=True),
          ev(F, "door", c["s10.door"], "small_room", pan=0.55, gain=0.75, kind="close", seed=164),
          ev(F, "footsteps", c["s10.marco"], "street", gain=0.35, times=[0, .5, 1.0], surface="stone", seed=165),
          ev(F, "door", c["s10.marco"] + 1.0, "small_room", pan=0.3, gain=0.45, kind="creak", seed=166),
          ev(D, "heartbeat", c["s10.heat_start"] - 0.6, None, gain=1.0, dur=7.5, bpm0=96, bpm1=138, seed=167),
          ev(D, "ghost", c["s10.heat_start"] + 1.4, None, gain=0.32, seed=168),
          ev(D, "ghost", c["s10.heat_start"] + 4.2, None, gain=0.26, seed=169),
          ev(D, "sub_hit", c["s10.door"], None, gain=0.6, seed=170, f0=48, f1=28, decay=1.6)]
    # ------------------------------------------------------------ S11 the final aria
    s = c["s11.start"]
    d = c["s11.dolly"]
    E += [ev(A, "room_tone", s, "small_room", gain=1.0, dur=d - s + 0.5, seed=181, colour=800, fade_out=1.0),
          ev(A, "sea", s, None, gain=0.25, dur=d - s, seed=182, close=0.1, wall=True, fade_out=1.0),
          ev(A, "clock", s, "small_room", pan=-0.5, gain=0.35, dur=d - s - 0.5, seed=183, period=1.0),
          ev(F, "chair", s + 1.0, "small_room", pan=0.35, gain=0.45, seed=184),
          ev(F, "silk", s + 4.6, "small_room", pan=-0.2, gain=0.3, dur=1.6, seed=185, soft=True),
          ev(D, "air_rush", d - 2.4, None, gain=0.55, dur=2.8, seed=186, rising=True),
          ev(D, "reverse_swell", d, None, gain=0.5, src_t=d + 0.2, length=2.6, seed=187),
          ev(A, "hall_air", d - 1.0, "hall", gain=0.75, dur=600 - d + 1.0, seed=188),
          ev(A, "rustle", d + 0.5, "hall", gain=0.12, dur=6.0, seed=189),
          ev(F, "breath", c["s11.sing"] - 0.8, "hall", gain=0.35, kind="inhale", seed=190),
          ev(F, "silk", c["s11.sing"] - 1.6, "hall", gain=0.5, dur=2.2, seed=191),
          ev(D, "pressure", c["s11.wide"], None, gain=0.45, dur=3.0, seed=192, f=35.0),
          ev(D, "pressure", c["s11.vittorio3"], None, gain=0.45, dur=24.0, seed=193, f=31.0),
          ev(D, "pressure", c["s11.vittorio4"], None, gain=0.35, dur=6.0, seed=194, f=31.0),
          ev(A, "rustle", c["s11.wide"] + 12.0, "hall", pan=0.6, gain=0.12, dur=0.6, seed=195),
          ev(F, "silk", c["s11.final_chord"] - 0.5, "hall", gain=0.4, dur=1.8, seed=196),
          ev(F, "curtain", c["s11.curtain"], "hall", gain=1.0, dur=4.4, seed=197),
          ev(D, "sub_hit", c["s11.curtain"] + 4.4, None, gain=0.7, seed=198, f0=45, f1=25, decay=2.0)]
    return E
