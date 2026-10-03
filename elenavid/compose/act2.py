"""Act II: the platform, Trieste (the nightmare, Davide), Marco's return."""
from __future__ import annotations

from ..notation import Ev, parse, attach_lyrics
from ..theory import pitch
from . import textures as tx
from .common import section, sing, P, add_lines, tone
from .themes import (VITTORIO, VITTORIO_HARM, VITTORIO_TEXT, VITTORIO_LINES, MARCO,
                     DAVIDE_ARIA, DAVIDE_ARIA_LYR, DAVIDE_ARIA_HARM, DAVIDE_LINES)


def lines_from(sec, voice, evs, pairs, sizes, style="aria"):
    k = 0
    for (it, en), n in zip(pairs, sizes):
        sec.line(voice, evs[k:k + n], it, en, style=style)
        k += n


# =============================================================================================
# S04  LA STAZIONE. A minor, the train in the orchestra; she carries the A (cor anglais).
# =============================================================================================
def s04(score):
    sec = section("s04", [(0, 96), (32, 60)], [(0, 4, 4), (32, 2, 4)])
    sing(sec, "ten", "ferroviere", "r:1 E4:.5 E4:.5 A4:1 E4:1", "In car roz za",
         "In carrozza! Venezia, Trieste!", "All aboard! Venice, Trieste!", origin=0, vel=0.62,
         style="parlato")
    mel = ("A4:1 B4:.5 C5:.5 E5:1 D5:.5 C5:1.5 B4:1 A4:1 B4:.5 C5:.5 F5:1 E5:.5 D5:1.5 C5:1 "
           "E4:.5 A4:1 B4:.5 C5:1 B4:.5 A4:1.5 G#4:1 E4:.5 E5:1.5 D5:.5 C5:.5 B4:.5 C#5:1.5 A4:1")
    lyr = ("Por to la mia va li gia por to_il mio so lo be ne la not te_è fred da_e gri gia "
           "ma_il fi glio mi so stie ne")
    E = parse(mel, origin=4, vel=0.6)
    attach_lyrics(E, lyr)
    sec.add("sop", E, voice="elena")
    lines_from(sec, "elena", E, [("Porto la mia valigia, porto il mio solo bene;",
                                  "I carry my suitcase, I carry my only treasure;"),
                                 ("la notte è fredda e grigia, ma il figlio mi sostiene.",
                                  "the night is cold and grey, but my son holds me up.")], [14, 14])
    p = tx.prog("Am:4 Am:2 Am:1.5 F:1.5 E7:1 Am:2 Dm:2 G7:1 C:1 Am:1.5 F:2 Dm:1.5 E7:1 "
                "Am:2 Dm:1 E7:.5 A:2.5 A:4")
    # the train: semiquaver clatter in the cellos, accents on the beat, tremolo violas
    clatter = []
    for b, d, c in p:
        root = [m for m in range(43, 56) if m % 12 == c.bass][0]
        fifth = root + 7
        steps = int(round(d / 0.25))
        for k in range(steps):
            t = b + k * 0.25
            if t >= 28:   # the train pulls out: sextuplets in the last bar
                break
            m = (root, root, fifth, root)[k % 4]
            clatter.append(Ev(t, 0.22, m, 0.42 if k % 4 == 0 else 0.3, ">" if k % 4 == 0 else "'"))
    for k in range(24):
        t = 28 + k * (4 / 24)
        clatter.append(Ev(t, 0.15, (45, 45, 52, 45)[k % 4], 0.45 - 0.006 * k, "'"))
    sec.add("vc", clatter, tech="pont")
    sec.add("cb", tx.bass(p, pattern=[(0, .4), (1, .4), (2, .4), (3, .4)], lo=33, hi=45,
                          vel=0.42))
    sec.add("bn", tx.bass(p, pattern=[(0, .8), (2, .8)], lo=40, hi=52, vel=0.3))
    for i, evs in enumerate(tx.sustain(p, [(57, 69), (62, 74)], vel=0.22)):
        sec.add(("va", "vn2")[i], evs, tech="trem")
    sec.add("vn1", tx.clone(E, lyric=None, vel=0.24), tech="sord")
    sec.add("hn", [Ev(30, 2, pitch("A4"), 0.4, "", None, None, {"env": "fp"}),
                   Ev(30, 2, pitch("C#5"), 0.4, "", None, None, {"env": "fp"})])
    sec.add("timp", [Ev(24, 8, pitch("A2"), 0.2, "", None, None, {"roll": True, "cresc": True})])
    for inst, pch in (("vn1", "A5"), ("vn2", "E5"), ("va", "C#5"), ("vc", "A3"), ("cb", "A1")):
        sec.add(inst, [Ev(32, 2.0, pitch(pch), 0.22, "", None, None, {"env": "fade"})])
    tone(sec, 4.0, 26.0, vel=0.12, inst="eh", voice="tommaso_eh")
    sec.cue("call", 1)
    sec.cue("aria", 4)
    sec.cue("depart", 28)
    sec.cue("whistle", 30)
    score.add(sec)
    return sec


# =============================================================================================
# S05  TRIESTE 1955. The nightmare: Vittorio's phrase, full and seductive. She wakes: A-flat
#      gives way to A (the child). Davide: F major, plain and warm, A sounding as his third.
# =============================================================================================
def s05(score):
    tempo = [(0, 80), (34, 60), (36, 66)]
    meters = [(0, 2, 4), (2, 4, 4), (34, 2, 4), (36, 4, 4), (72, 2, 4)]
    sec = section("s05", tempo, meters)
    # ---- intro: eerie A-flat shimmer
    sec.add("vn1", [Ev(0, 2.2, pitch("Eb5"), 0.12), Ev(0, 2.2, pitch("Ab5"), 0.1)], tech="pont")
    sec.add("harp", [Ev(0.5, 2, pitch("Ab5"), 0.16, "", None, None, {"harmonic": True})])
    # ---- Vittorio, appearance 1
    V = sing(sec, "bar", "vittorio", VITTORIO, VITTORIO_TEXT[1], "", "", origin=2, vel=0.55,
             bar=4, show=False, style="vision", motif="vittorio", appearance=1)
    lines_from(sec, "vittorio", V, VITTORIO_LINES[1], [8, 8, 8, 8], style="vision")
    vp = tx.prog(VITTORIO_HARM, origin=2, bar=4)
    for i, evs in enumerate(tx.sustain(vp, [(48, 60), (53, 65), (58, 70), (63, 76)], vel=0.22)):
        sec.add(("vc", "va", "vn2", "vn1")[i], evs, tech="sord")
    sec.add("cb", tx.bass(vp, lo=32, hi=44, vel=0.26), tech="sord")
    sec.add("harp", tx.arp(vp, step=0.5, lo=51, hi=80, vel=0.2, shape="updown", seed=5))
    sec.add("vc_solo", tx.clone(tx.diatonic(V, -2, 8, "major"), lyric=None, vel=0.3), tech="espr")
    sec.add("cl", tx.clone(tx.sustain(tx.prog("Ab/Eb:2 Fm7:2 | Dbmaj9:2 Bbm7:2 | Ab/C:2 Fm7:1 "
                                              "Bbm7:1 | Eb7:2 Ab:2", origin=18),
                                      [(60, 70)], vel=0.16)[0], lyric=None))
    # ---- waking (bar 10)
    sec.add("sop", [Ev(34.0, 0.5, pitch("F5"), 0.7, ">", "No", None, {"style": "parlato"})],
            voice="elena")
    sec.line("elena", sec.parts[-1][2], "No! ... È solo il vento.", "No! ... It is only the wind.",
             style="parlato")
    for inst, pch in (("vn1", "A5"), ("vn1", "Ab5"), ("vn2", "Eb5"), ("va", "A4")):
        sec.add(inst, [Ev(34.0, 1.2, pitch(pch), 0.55, "^")], tech="trem")
    sec.cue("wake", 34.0)
    # ---- morning: Davide, the paper boat, Tommaso laughs (bars 11-12)
    mp = tx.prog("F:2 Bb/F:1 F:1 | F:2 C7:1 F:1", origin=36)
    sing(sec, "bbar", "davide", "C3:.5 F3:.5 F3:.5 G3:.25 A3:.25 C4:1 A3:1",
         "Buon gior no ca pi ta no", "Buongiorno, capitano. Ecco la tua nave.",
         "Good morning, captain. Here is your ship.", origin=36, vel=0.5, style="parlato")
    sing(sec, "bbar", "davide", "r:1 A3:.5 F3:.5 G3:.5 A3:1 F3:.5", "Ri de hai vi sto",
         "Ride! Hai visto? Ride, il capitano.", "He's laughing! Did you see? The captain's laughing.",
         origin=40, vel=0.52, style="parlato")
    sing(sec, "treble", "tommaso", "A4:1.5", "a", "", "", origin=40.2, vel=0.2, show=False,
         tommaso=True)
    tone(sec, 37.0, 7.0, vel=0.24)
    for i, evs in enumerate(tx.sustain(mp, [(53, 62), (57, 67), (60, 72)], vel=0.2)):
        sec.add(("hn", "va", "vn2")[i], evs)
    sec.add("cb", tx.bass(mp, lo=29, hi=41, vel=0.24))
    # ---- Davide's aria (bars 13-16)
    D = sing(sec, "bbar", "davide", DAVIDE_ARIA, DAVIDE_ARIA_LYR, "", "", origin=44, vel=0.55,
             bar=4, show=False)
    lines_from(sec, "davide", D, DAVIDE_LINES, [8, 8, 8, 8])
    dp = tx.prog(DAVIDE_ARIA_HARM, origin=44, bar=4)
    hns = tx.sustain(dp, [(53, 62), (57, 67)], vel=0.22)
    add_lines(sec, "hn", hns)
    for i, evs in enumerate(tx.sustain(dp, [(50, 60), (55, 65), (60, 70)], vel=0.2)):
        sec.add(("vc", "va", "vn2")[i], evs)
    sec.add("cb", tx.bass(dp, lo=29, hi=41, vel=0.3))
    sec.add("bn", tx.bass(dp, lo=41, hi=53, vel=0.18))
    sec.add("harp", tx.arp(dp, step=1.0, lo=53, hi=77, vel=0.18, shape="up", seed=9))
    for t0, d in ((44, 7.5), (52, 7.5)):
        tone(sec, t0, d, vel=0.22)
    # ---- duet (bars 17-20)
    du = tx.prog("F:2 F/A:1 Bb:1 | F/C:1.5 C7:2.5 | F:4 | F:2", origin=60)
    E = sing(sec, "sop", "elena", "A4:1 G4:.5 F4:.5 G4:.5 A4:.5 C5:.5 Bb4:.5 | "
             "A4:.5 Bb4:1 A4:.5 G4:.5 F4:.5 G4:.5 E4:.5 | F4:4~ | F4:2",
             "Pia no co me la ne ve che ca de_e non fa ma le _",
             "Piano, come la neve che cade e non fa male,",
             "Gently, like the snow that falls and does no harm,", origin=60, vel=0.46,
             style="duet")
    Dv = tx.diatonic(E[:14], -5, 5, "major")
    Dv.append(Ev(68, 6, pitch("A3"), 0.4, "", "_"))
    for e in Dv:
        e.vel = 0.42
    sec.add("bbar", Dv, voice="davide")
    for i, evs in enumerate(tx.sustain(du, [(50, 60), (55, 65), (60, 70), (65, 77)], vel=0.2)):
        sec.add(("vc", "va", "vn2", "vn1")[i], evs, tech="sord")
    add_lines(sec, "hn", tx.sustain(du, [(53, 62)], vel=0.16))
    sec.add("cb", tx.bass(du, lo=29, hi=41, vel=0.24))
    sec.add("harp", tx.arp(du, step=0.5, lo=53, hi=81, vel=0.18, shape="wave", seed=13))
    tone(sec, 60, 14, vel=0.24)
    sec.cue("vision", 2)
    sec.cue("morning", 36)
    sec.cue("davide", 44)
    sec.cue("duet", 60)
    score.add(sec)
    return sec


# =============================================================================================
# S06  UNA STRADA DI TRIESTE. Marco. The confession. "(E so che non è vero.)" Curtain on D7.
# =============================================================================================
def s06(score):
    sec = section("s06", [(0, 88)], [(0, 4, 4)])
    p = tx.prog("G:4 | Em:2 Am7:1 D7:1 | Em:2 C:2 | D:2 G/B:1 Am:1 | G:2 C:1 Am:1 | "
                "D7sus4:2 D7:1 G:1 | G:2 Em:2 | C:2 D7:2 | G:2 D7:1 G:1 | G:1.5 C:1 D7:1.5 | D7:4",
                bar=4)
    sing(sec, "ten", "marco", "r:2 B3:1 A3:.5 D4:.5", "E le na", "Elena?", "Elena?", origin=0,
         vel=0.5)
    sing(sec, "ten", "marco", "G4:1 F#4:.5 B3:.5", "E le na", "Elena!", "Elena!", origin=4,
         vel=0.62)
    sing(sec, "sop", "elena", "E5:1 C5:1", "Mar co", "Marco...", "Marco...", origin=6, vel=0.45)
    E = sing(sec, "sop", "elena",
             "E4:.5 A4:1 G4:.5 F#4:.5 G4:.5 A4:.5 F#4:.5 | D4:.5 E4:.5 F#4:.5 G4:1 F#4:.5 E4:.5 D4:.5 | "
             "G4:.5 G4:.5 B4:.5 A4:.5 C5:.75 B4:.25 A4:.5 G4:.5 | B4:1.5 A4:.5 G4:.5 E4:1 D4:.5",
             "ho_un fi glio che non par la che non cam mi na_e vi vo con un uo mo buo no che non "
             "è mio ma ri to", "", "", origin=8, vel=0.48, style="parlato", show=False, bar=4)
    lines_from(sec, "elena", E, [("Ho un figlio che non parla, che non cammina; e vivo",
                                  "I have a son who does not speak, who does not walk; and I live"),
                                 ("con un uomo buono, che non è mio marito.",
                                  "with a good man, who is not my husband.")], [14, 13])
    sing(sec, "ten", "marco", "D4:.5 G4:1 F#4:.5 r:.5 D4:.5 B4:.75 A4:.25 | G4:.5 A4:.5 B4:1.5 G4:1.5",
         "non fug go ti_ho per so già_u na vol ta", "Non fuggo. Ti ho perso già una volta.",
         "I am not running. I have lost you once already.", origin=24, vel=0.55, bar=4)
    Ed = sing(sec, "sop", "elena", "B4:.5 D5:1 C5:.5 B4:.5 A4:.75 B4:.25 G4:.5",
              "do ma ni_al la stes sa_o ra", "Domani, alla stessa ora...",
              "Tomorrow, at the same hour...", origin=32, vel=0.5, style="duet")
    Md = tx.diatonic(Ed, -2, 7, "major")
    for e in Md:
        e.midi -= 0
        e.vel = 0.46
    sec.add("ten", Md, voice="marco")
    sing(sec, "sop", "elena", "D5:.5 B4:1 A4:.5 G4:.5 A4:.5 C5:.5 C5:.5~ | C5:4",
         "e so che non è ve ro", "(E so che non è vero.)", "(And I know it is not true.)",
         origin=36, vel=0.42, style="aside")
    sing(sec, "ten", "marco", "B3:.5 G4:1 F#4:.5 D4:.5 F#4:.5 A4:.5 A4:.5~ | A4:4",
         "e so che non è ve ro", "", "", origin=36, vel=0.4, show=False, style="aside")
    cm = P(MARCO, origin=40, vel=0.34)
    for e in cm:
        e.tags["motif"] = "marco"
    sec.add("cl", cm)
    # strings: tremolo at the meeting, sparse under the confession, warm after
    shock = tx.prog("G:4 | Em:2 Am7:1 D7:1")
    for i, evs in enumerate(tx.sustain(shock, [(55, 67), (59, 71), (64, 76)], vel=0.3)):
        sec.add(("va", "vn2", "vn1")[i], evs, tech="trem")
    conf = [x for x in p if 8 <= x[0] < 24]
    for i, evs in enumerate(tx.sustain(conf, [(48, 60), (55, 67)], vel=0.16)):
        sec.add(("vc", "va")[i], evs, tech="sord")
    sec.add("cl", tx.clone(tx.sustain(conf, [(58, 67)], vel=0.14)[0]))
    warm = [x for x in p if x[0] >= 24]
    for i, evs in enumerate(tx.sustain(warm, [(50, 62), (55, 67), (60, 72), (64, 76)], vel=0.24)):
        sec.add(("vc", "va", "vn2", "vn1")[i], evs)
    add_lines(sec, "hn", tx.sustain([x for x in warm if x[0] < 32], [(53, 62), (57, 67)], vel=0.2))
    sec.add("cb", tx.bass(p, lo=31, hi=43, vel=0.26))
    sec.add("harp", tx.arp([x for x in p if x[0] >= 32], step=0.5, lo=55, hi=81, vel=0.2,
                           shape="updown", seed=17))
    sec.cue("meet", 0)
    sec.cue("confession", 8)
    sec.cue("friends", 24)
    sec.cue("domani", 32)
    sec.cue("aside", 36)
    sec.cue("curtain", 40)
    score.add(sec)
    return sec
