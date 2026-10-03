"""Act III: drift, the second vision, Stabat Mater, the death, Requiem, the letter, the final aria.

After the Requiem (S09) the score never sounds the pitch class A: Tommaso's note is gone.
"""
from __future__ import annotations

from ..notation import Ev, parse, attach_lyrics
from ..theory import pitch
from . import textures as tx
from .choral import harmonize
from .common import section, sing, P, add_lines, tone, NO_A
from .themes import (WEDDING, VITTORIO, VITTORIO_HARM, VITTORIO_TEXT, VITTORIO_LINES,
                     MARCO_WARPED, MARCO_LETTER)


def lines_from(sec, voice, evs, pairs, sizes, style="aria"):
    k = 0
    for (it, en), n in zip(pairs, sizes):
        sec.line(voice, evs[k:k + n], it, en, style=style)
        k += n


def chorus_verse(sec, mel, lyr, prog, origin, it_en, vel=0.42):
    S = parse(mel, origin=origin, vel=vel)
    attach_lyrics(S, lyr)
    A, T, B = harmonize(S, prog, a_rng=(53, 70), t_rng=(48, 64), b_rng=(40, 56))
    for inst, evs in (("ch_s", S), ("ch_a", A), ("ch_t", T), ("ch_b", B)):
        sec.add(inst, evs, voice="chorus", style="latin")
    n1 = len(lyr.split()) // 2 + (len(lyr.split()) % 2)
    (it1, en1), (it2, en2) = it_en
    sec.line("chorus", S[:8], it1, en1, style="latin")
    sec.line("chorus", S[8:], it2, en2, style="latin")
    return S


# =============================================================================================
# S07  Months; the second vision (thinner); Stabat Mater over the wedding tune in F minor.
# =============================================================================================
def s07(score):
    tempo = [(0, 85.714), (20, 80), (52, 60)]
    meters = [(0, 4, 4), (52, 6, 8), (100, 2, 4)]
    sec = section("s07", tempo, meters)

    # ---- the drift (bars 1-5): Marco's motif, warped, grows dominant; Davide's F between
    w1 = P(MARCO_WARPED, origin=0, vel=0.42)
    w2 = P(MARCO_WARPED, origin=8, vel=0.5, transpose=12)
    w3 = P(MARCO_WARPED, origin=12, vel=0.42, transpose=12)
    w4 = P(MARCO_WARPED, origin=16, vel=0.72)
    for evs in (w1, w2, w3, w4):
        for e in evs:
            e.tags["motif"] = "marco_warped"
    sec.add("cl", w1)
    sec.add("vn1", w2)
    sec.add("ob", w3)
    sec.add("hn", w4, art=">")
    sec.add("tpt", tx.clone(w4, vel=0.5), tech="mute")
    drift = tx.prog("Gm:4 | F:4 | Gm:2 Eb:2 | F/A:2 Bb:1 C7:1 | Ebmaj7:2 Eb7:2", bar=4)
    for i, evs in enumerate(tx.sustain(drift, [(43, 55), (50, 62), (55, 67)], vel=0.22)):
        sec.add(("vc", "va", "vn2")[i], evs, tech="trem")
    home = [x for x in drift if x[2].root == 5 or x[2].symbol in ("Bb", "C7")]
    add_lines(sec, "hn", tx.sustain(home, [(53, 62), (57, 67)], vel=0.18))
    sec.add("cb", tx.bass(drift, lo=31, hi=43, vel=0.28))
    for it, en, b0, b1 in (("Racconta.", "Tell me.", 0.5, 3.5),
                           ("Sei tardi.  La sarta. Un orlo da rifare.",
                            "You're late.  The dressmaker's. A hem to do again.", 4.2, 7.8),
                           ("Il vento ti ha sciolto i capelli.", "The wind has loosened your hair.",
                            8.5, 11.5),
                           ("È la bora. Scioglie tutto.", "It's the bora. It loosens everything.",
                            12.2, 15.8)):
        sec.text(it, en, b0, b1, style="fragment")

    # ---- Vittorio, appearance 2 (bars 6-13): the same phrase, thinner
    V = sing(sec, "bar", "vittorio", VITTORIO, VITTORIO_TEXT[2], "", "", origin=20, vel=0.55,
             bar=4, show=False, style="vision", motif="vittorio", appearance=2)
    lines_from(sec, "vittorio", V, VITTORIO_LINES[2], [8, 8, 8, 8], style="vision")
    vp = tx.prog(VITTORIO_HARM, origin=20, bar=4)
    sec.add("cb", tx.bass(vp, lo=32, hi=44, vel=0.24), tech="sord")
    sec.add("vc", tx.bass(vp, lo=44, hi=56, vel=0.2), tech="sord")
    sec.add("va", tx.sustain(vp, [(55, 65)], vel=0.16)[0], tech="sord")
    sec.add("hn", tx.sustain(vp, [(55, 64)], vel=0.14)[0])

    # ---- Stabat Mater (bars 14-29, 6/8): the wedding melody in F minor in the low strings
    O = 52
    W = parse(WEDDING, bar=3, origin=0)
    W = tx.remap_line(W, 2, "major", 5, "harmonic", octave_shift=-2)
    low = []
    for e in W:
        k = int(e.beat // 3)          # bar index 0..15
        off = e.beat - 3 * k
        e = Ev(e.beat + O, e.dur, e.midi, 0.3, "", None, None, {"motif": "wedding_lament"})
        if k <= 2:
            low.append(e)
        elif k <= 4:
            if off in (0.0, 1.5):
                e.dur = 0.9
                low.append(e)
        elif k == 5:
            if off == 0.0:
                e.dur = 3.0           # A-flat held: it becomes G-sharp under 'gladius'
                low.append(e)
        elif k <= 7:
            if off == 0.0:
                e.dur = 1.2
                low.append(e)
        elif k <= 11:
            e.vel = 0.4
            low.append(e)
        else:
            if (e.beat - O) % 1.5 < 1e-6 or off == 0.0:
                e.vel = 0.34 - 0.04 * (k - 12)
                e.dur = max(e.dur, 1.4)
                low.append(e)
    sec.add("vc", low, tech="espr")
    sec.add("cb", tx.transpose([e for e in low if e.beat >= O + 24], -12))
    sec.add("va", tx.transpose([e for e in low if O + 24 <= e.beat < O + 36], 12))
    sp = tx.prog("Fm:3 | C7:1.5 Fm:1.5 | Bbm:3 | Fm/C:1.5 C7:1.5 | Fm:3 | Db:.5 E:2.5 | Bbm:3 | "
                 "Fm/C:1.5 C7:1 Fm:.5 | Fm:1.5 C7b9:1.5 | Fm:1.5 C7sus4:1 C7:.5 | Bbm:3 | "
                 "Fm/C:1.5 Ab:1.5 | Fm:1.5 Bbm:1.5 | Gm7b5:1.5 C7sus4:1 C7:.5 | Fm/Ab:1.5 Bbm:1.5 | "
                 "C7:1.5 Dbmaj7/F:1.5 | Dbmaj7/F:2", origin=O)
    for i, evs in enumerate(tx.sustain(sp, [(60, 72), (65, 77), (70, 82)], vel=0.12)):
        sec.add(("va", "vn2", "vn1")[i], evs, tech="sord")
    sec.add("hn", [Ev(O + 15.5, 2.5, pitch(p), 0.16) for p in ("E3", "G#3", "B3")])
    chorus_verse(sec, "C5:1 Bb4:.5 Ab4:.5 G4:.5 F4:.5 G4:.5 Ab4:.5 G4:.5 "
                      "Ab4:1 Bb4:.5 C5:.5 Db5:.5 C5:.5 Bb4:.5 Ab4:.5 G4:.5",
                 "Sta bat ma ter do lo ro sa iux ta cru cem la cri mo sa", sp, O,
                 [("Stabat mater dolorosa", "The grieving mother stood"),
                  ("iuxta crucem lacrimosa,", "weeping beside the cross,")], vel=0.36)
    chorus_verse(sec, "G4:1 Ab4:.5 Bb4:.5 Ab4:.5 G4:.5 F4:.5 E4:.5 F4:.5 "
                      "F4:.5 G4:.5 Ab4:.5 Bb4:.5 B4:1.5 G#4:.5 E4:.5",
                 "Cui us a ni mam ge men tem per tran si vit gla di us", sp, O + 9,
                 [("Cuius animam gementem", "Through her soul, groaning,"),
                  ("pertransivit gladius.", "a sword has passed.")], vel=0.4)
    chorus_verse(sec, "Ab4:1 G4:.5 F4:.5 G4:.5 Ab4:.5 Bb4:.5 C5:.5 Bb4:.5 "
                      "Ab4:.5 G4:.5 F4:.5 E4:.5 F4:.5 G4:.5 Db5:1 C5:.5",
                 "Vi dit su um dul cem na tum mo ri en do de so la tum", sp, O + 18,
                 [("Vidit suum dulcem natum", "She saw her sweet son"),
                  ("moriendo desolatum,", "dying, forsaken,")], vel=0.42)
    chorus_verse(sec, "Eb5:1 Db5:.5 C5:.5 Bb4:.5 Ab4:.5 Bb4:.5 C5:.5 Bb4:.5 "
                      "Ab4:1 G4:.5 F4:.5 G4:.5 Ab4:.5 G4:.5 F4:1",
                 "Ei a Ma ter fons a mo ris fac ut te cum lu ge am", sp, O + 27,
                 [("Eia, Mater, fons amoris,", "O Mother, fountain of love,"),
                  ("fac, ut tecum lugeam.", "make me grieve with you.")], vel=0.46)
    chorus_verse(sec, "F4:1.5 G4:.5 Ab4:1 G4:.5 F4:1 E4:.5 F4:.5 G4:.5 "
                      "Ab4:.5 C5:1.5 Bb4:.5 Ab4:.5 G4:1 F4:.5 F4:1.5~ F4:2",
                 "Iux ta cru cem te cum sta re in planc tu de si de ro", sp, O + 36,
                 [("Iuxta crucem tecum stare,", "To stand beside the cross with you,"),
                  ("in planctu desidero.", "in lamentation, this I desire.")], vel=0.34)
    sec.add("harp", [Ev(O + 9 * i, 3, m, 0.14, "", None, None, {"harmonic": True})
                     for i, m in enumerate((65, 68, 72, 75, 77))])
    sec.cue("drift", 0)
    sec.cue("vision", 20)
    sec.cue("stabat", O)
    sec.cue("gladius", O + 15.5)
    sec.cue("desolatum", O + 25.5)
    sec.cue("eia", O + 27)
    sec.cue("iuxta", O + 36)
    sec.cue("held_chord", O + 48)
    score.add(sec)
    return sec


# =============================================================================================
# S08  The trattoria; Nives; the dying child. The tone fades at each phrase end and returns,
#      until the cadence where it should return arrives as a bare fifth. Silence.
# =============================================================================================
def s08(score):
    sec = section("s08", [(0, 72), (12, 120), (20, 56)], [(0, 3, 4), (12, 4, 4)])
    tp = tx.prog("F:3 | C7:2 F:1 | Dm:1.5 Bb:1.5 | F:1 C7:1 F:1", bar=3)
    sing(sec, "bbar", "davide", "C3:.5 F3:.5 F3:.5 r:.5 A3:.5 C4:.5 | A3:.5 G3:.5 F3:.5 G3:1 F3:.5",
         "as sag gia è_il vi no di pro sec co", "Assaggia. È il vino di Prosecco.",
         "Taste it. It's the wine from Prosecco.", origin=0, vel=0.5, style="parlato", bar=3)
    sing(sec, "sop", "elena", "A4:.5 C5:.5 F5:1.5 E5:.5", "Sa di so le", "Sa di sole.",
         "It tastes of sunlight.", origin=6, vel=0.5)
    sing(sec, "bbar", "davide", "C3:.25 D3:.25 F3:.5 A3:.5 C4:.5 Bb3:.5 A3:.5",
         "Sa di te quan do ri di", "Sa di te, quando ridi.", "It tastes of you, when you laugh.",
         origin=9, vel=0.5)
    sec.add("vc", tx.bass(tp, pattern=[(0, .5)], lo=36, hi=48, vel=0.3), tech="pizz")
    sec.add("va", tx.chord_hits(tp, [(1, .4), (2, .4)], [(55, 64), (60, 69)], vel=0.2),
            tech="pizz")
    sec.add("cl", P("r:1 A4:1 C5:1 | Bb4:1.5 A4:.5 G4:1 | F4:3 | A4:1 G4:1 F4:1", vel=0.24, bar=3))
    sec.add("harp", tx.arp(tp, step=0.5, lo=53, hi=77, vel=0.16, seed=21))
    # ---- Nives, the run home
    sing(sec, "mez", "nives", "C5:.5 A4:.25 A4:.25 G4:.5 G4:.5 D5:1 C#5:1", "E le na il bam bi no",
         "Elena! Davide! Il bambino... Venite, presto!", "Elena! Davide! The boy... Come, quickly!",
         origin=12, vel=0.72, style="parlato")
    for inst, pch in (("vn1", "D5"), ("vn2", "A4"), ("va", "F4"), ("vc", "D3")):
        sec.add(inst, [Ev(12, 4, pitch(pch), 0.42)], tech="trem")
    sec.add("vn1", P("D5:.25 E5:.25 F5:.25 G5:.25 A5:.25 Bb5:.25 C#6:.25 D6:.25 "
                     "D5:.25 E5:.25 F5:.25 G5:.25 A5:.25 Bb5:.25 C#6:.25 D6:.25", origin=16, vel=0.5))
    sec.add("vc", P("D3:2 A2:2", origin=16, vel=0.5), tech="trem")
    sec.add("timp", [Ev(16, 4, pitch("D3"), 0.42, "", None, None, {"roll": True})])
    # ---- the ensemble over the dying child
    ep = tx.prog("F:2 Bb:1 C7:1 | F:2 Dm:1 C:1 | F:2 Bb:1 F:1 | Dm:2 C7:2 | F:2 Bb:1 C7:1 | "
                 "F:1 Dm:1 Bb:1 C7:1 | F5:1.5", origin=20)
    sing(sec, "sop", "elena", "C5:.75 A4:.25 D5:.75 C5:.25 Bb4:.75 A4:.25 G4:.75 F4:.25",
         "Re sta_a mo re re sta_an co ra", "Resta, amore, resta ancora,",
         "Stay, my love, stay a little longer,", origin=20, vel=0.5)
    sing(sec, "sop", "elena", "F4:.5 G4:.5 A4:1 G4:.5 F4:.25 G4:.25 A4:.75 G4:.25",
         "la tua no ta la tua lu ce", "la tua nota, la tua luce...", "your note, your light...",
         origin=24, vel=0.46)
    sing(sec, "bbar", "davide", "C3:.75 D3:.25 F3:1 E3:.5 F3:.5 G3:.5 A3:.25 F3:.25",
         "Sia mo qui ci sia mo_in du e", "Siamo qui, ci siamo in due,",
         "We are here, the two of us,", origin=28, vel=0.48)
    sing(sec, "bbar", "davide", "C3:.5 D3:.5 F3:.75 E3:.25 D3:.5 E3:.5 G3:.75 C3:.25",
         "ti te nia mo ma no_e vo ce", "ti teniamo, mano e voce.", "we hold you, hand and voice.",
         origin=32, vel=0.46)
    E = sing(sec, "sop", "elena", "A4:1 G4:.5 F4:.75 E4:.25 F4:.5 G4:.25 A4:.5 Bb4:.25",
             "Dor mi fi glio non te me re", "Dormi, figlio, non temere,",
             "Sleep, my son, do not be afraid,", origin=36, vel=0.44, style="duet")
    Dv = tx.diatonic(E, -5, 5, "major")
    for e in Dv:
        e.vel = 0.4
    sec.add("bbar", Dv, voice="davide")
    sing(sec, "sop", "elena", "C5:.75 Bb4:.25 A4:.75 G4:.25 F4:.5 G4:.5 E4:1 | F4:1.5",
         "sia mo qui fi no_al mat ti no", "siamo qui fino al mattino;",
         "we are here until morning;", origin=40, vel=0.42, style="duet")
    sing(sec, "bbar", "davide", "A3:.75 G3:.25 F3:.75 E3:.25 D3:.5 Bb2:.5 C3:1 | F2:1.5",
         "sia mo qui fi no_al mat ti no", "", "", origin=40, vel=0.4, show=False)
    for i, evs in enumerate(tx.sustain(ep, [(48, 60), (55, 65), (60, 72)], vel=0.16)):
        sec.add(("vc", "va", "vn2")[i], [e for e in evs if e.beat < 44], tech="sord")
    sec.add("cb", [e for e in tx.bass(ep, lo=29, hi=41, vel=0.22) if e.beat < 44])
    sec.add("harp", [e for e in tx.arp(ep, step=1.0, lo=53, hi=77, vel=0.14, seed=23)
                     if e.beat < 44])
    # the bare fifth: F and C, no A
    for inst, pch in (("cb", "F1"), ("vc", "F2"), ("vc", "C3"), ("va", "F3"), ("va", "C4"),
                      ("hn", "F3"), ("hn", "C4")):
        sec.add(inst, [Ev(44, 1.6, pitch(pch), 0.2, "", None, None, {"env": "fade"})])
    for t0, d, v in ((20, 3.6, .26), (24, 3.6, .24), (28, 3.4, .21), (32, 3.3, .18), (36, 3.2, .15),
                     (40, 3.0, .11)):
        tone(sec, t0, d, vel=v, fade_end=True)
        if t0 <= 28:
            tone(sec, t0, d, vel=v * 0.4, inst="eh", voice="tommaso_eh", fade_end=True)
    sec.cue("trattoria", 0)
    sec.cue("nives", 12)
    sec.cue("run", 16)
    sec.cue("deathbed", 20)
    sec.cue("death", 44)
    score.add(sec)
    return sec


# =============================================================================================
# S09  Requiem, D minor. The A passes through the orchestra one last time, then is gone.
# =============================================================================================
def s09(score):
    sec = section("s09", [(0, 56)], [(0, 4, 4)])
    rp = tx.prog("Dm:2 Gm/D:1 Dm:1 | Dm:1.5 C:.5 F:1 C/E:1 | Dm:1 Gm:1 Dm/F:1 Bb:1 | "
                 "Gm:1 Dm/F:1 Bb:1 A7:1 | Gm:1 A7:1 Dm:2", bar=4)
    S = parse("A4:1.5 G4:.5 F4:1 G4:1 | A4:1.5 G4:.5 F4:1 E4:1 | F4:1 G4:.5 A4:1 G4:.5 F4:1 | "
              "D4:.5 F4:1 G4:.5 A4:.5 Bb4:.5 A4:1 | G4:1 F4:.5 E4:.5 D4:1 D4:1", bar=4, vel=0.4)
    attach_lyrics(S, "Re qui em ae ter nam do na e i Do mi ne et lux per pe tu a lu ce at e i")
    A, T, B = harmonize(S, rp, a_rng=(53, 69), t_rng=(48, 64), b_rng=(38, 55))
    for inst, evs in (("ch_s", S), ("ch_a", A), ("ch_t", T), ("ch_b", B)):
        sec.add(inst, evs, voice="chorus", style="latin")
    sec.line("chorus", S[:13], "Requiem aeternam dona ei, Domine,", "Grant him eternal rest, O Lord,",
             style="latin")
    sec.line("chorus", S[13:], "et lux perpetua luceat ei.",
             "and let perpetual light shine upon him.", style="latin")
    for i, evs in enumerate(tx.sustain(rp, [(50, 60), (55, 65), (60, 70)], vel=0.2,
                                       include_bass=True, bass_range=(26, 38))):
        sec.add("organ", evs)
    sec.add("cb", [Ev(0, 20, pitch("D1"), 0.2)])
    sec.add("vc", [Ev(0, 20, pitch("D2"), 0.16)], tech="sord")
    sec.add("churchbell", [Ev(4 * k, 4, pitch("D3"), 0.32) for k in range(5)], ring=True)
    for t0, d, v in ((0.5, 3.0, .14), (4.5, 3.0, .13), (8.5, 3.0, .12)):
        tone(sec, t0, d, vel=v)
    tone(sec, 12.0, 4.5, vel=0.15, fade_end=True, last=True)
    sec.cue("requiem", 0)
    sec.cue("last_tone", 12.0)
    sec.cue("tone_gone", 16.5)
    score.add(sec)
    return sec


# =============================================================================================
# S10  The letter (Marco's motif resolves, in G-flat, too late), confession, Davide's grief
#      breaks once (the score stays warm; the distortion is Elena's), he goes; Marco withdraws.
# =============================================================================================
def s10(score):
    sec = section("s10", [(0, 60)], [(0, 4, 4)])   # one beat = one second
    sec.add("cb", [Ev(2.0, 10.0, pitch("Db2"), 0.16)])
    sec.add("vc", [Ev(2.0, 10.0, pitch("Db3"), 0.12)], tech="sord")
    sec.add("vn1", [Ev(3.0, 8.0, pitch("F6"), 0.08, "", None, None, {"harmonic": True})],
            tech="harm")
    lm = P(MARCO_LETTER, origin=5.0, vel=0.36)
    for e in lm:
        e.tags["motif"] = "marco_letter"
    lm[-1].tags["resolution"] = True
    sec.add("cl", lm)
    for t0, d, ps in ((5.0, 2.5, ("Gb3", "Bb3", "Db4")), (7.5, 1.5, ("Ab3", "Cb4", "F4")),
                      (9.0, 3.5, ("Gb3", "Bb3", "Db4"))):
        for inst, p in zip(("va", "vn2", "vn2"), ps):
            sec.add(inst, [Ev(t0, d, pitch(p), 0.14)], tech="sord")
    sing(sec, "bbar", "davide", "Bb2:.25 Db3:.5 Db3:.25 Eb3:.5 Db3:.25 Db3:.5 C3:.25 Bb2:.5 Bb2:.5",
         "da quel la not te_in ca sa mi a", "«Da quella notte, in casa mia...»",
         "\"Since that night, in my house...\"", origin=9.0, vel=0.38, style="letter_read")
    sec.text("Trieste, novembre 1958.  Elena, questa volta la spedisco. Cento lettere ti ho scritto "
             "in dieci anni, e nessuna è partita. Questa sì. Da quella notte, in casa mia, non so più "
             "dove finisco io e dove cominci tu.  Marco",
             "Trieste, November 1958.  Elena, this time I am sending it. A hundred letters I have "
             "written you in ten years, and not one was sent. This one, yes. Since that night, in my "
             "house, I no longer know where I end and where you begin.  Marco",
             3.0, 12.5, style="letter")
    # ---- confession
    sing(sec, "sop", "elena", "F4:.75", "Sì", "Sì. È vero. Tutto.", "Yes. It is true. All of it.",
         origin=13.0, vel=0.42, style="parlato")
    sing(sec, "sop", "elena", "F4:.25 Gb4:.5 F4:.5", "è ve ro", "", "", origin=14.0, vel=0.42,
         show=False, style="parlato")
    sing(sec, "sop", "elena", "Db5:.75 Bb4:1", "tut to", "", "", origin=15.5, vel=0.5, show=False)
    sing(sec, "sop", "elena", "F4:.25 F4:.25 Gb4:.5 F4:.25 Eb4:.25 F4:.5 Db4:.25 Gb4:.5 F4:.25 "
         "Eb4:.25 F4:.5 Db4:.5", "il bam bi no te ne va chiu se le por te",
         "Il bambino teneva chiuse le porte.", "The child kept the doors shut.", origin=17.5,
         vel=0.44, style="parlato")
    cp = tx.prog("Bbm:5 Gb:2 Ebm:1.5 Fsus4:1", origin=12.5)
    for i, evs in enumerate(tx.sustain(cp, [(46, 58), (53, 65), (58, 70)], vel=0.16,
                                       avoid_pcs=NO_A)):
        sec.add(("vc", "va", "vn2")[i], evs, tech="sord")
    sec.add("cb", tx.bass(cp, lo=29, hi=41, vel=0.18))
    # ---- Davide's grief: forte, warm, no A, nothing borrowed from Vittorio
    sing(sec, "bbar", "davide", "C4:.5 Bb3:.25 Bb3:.25 D4:1 C4:.75", "e ra mio fi glio",
         "Era mio figlio! L'ho portato in braccio", "He was my son! I carried him in my arms",
         origin=22.0, vel=0.86, style="heat")
    sing(sec, "bbar", "davide", "F3:.25 G3:.25 Bb3:.5 G3:.25 C4:.75 Bb3:.75",
         "l'ho por ta to_in brac cio", "", "", origin=25.0, vel=0.82, show=False, style="heat")
    hp = tx.prog("F5:2 Bbsus2:2 Gm7:1 C7sus4:1", origin=22.0)
    for i, evs in enumerate(tx.sustain(hp, [(48, 57), (53, 62), (57, 67)], vel=0.55,
                                       include_bass=True, bass_range=(29, 41), avoid_pcs=NO_A)):
        sec.add(("cb", "vc", "hn", "hn")[i], evs)
    add_lines(sec, "va", tx.sustain(hp, [(53, 65)], vel=0.42, avoid_pcs=NO_A))
    sec.add("timp", [Ev(22.0, 0.6, pitch("F2"), 0.5), Ev(24.0, 0.6, pitch("C3"), 0.4)])
    sec.cue("heat_start", 22.0)
    sec.cue("heat_end", 28.0)
    # ---- "Vattene"
    sing(sec, "sop", "elena", "Eb5:.75 Db5:.5 C5:.25 Bb4:.5 Gb4:.25 F4:.5 F4:.75",
         "No vat te ne ti pre go", "No... no... Vattene. Ti prego.", "No... no... Go. Please.",
         origin=28.5, vel=0.55, style="parlato")
    for inst, p in (("vc", "Bb2"), ("va", "F3"), ("vn2", "Db4")):
        sec.add(inst, [Ev(28.5, 2.5, pitch(p), 0.2)], tech="trem")
    # ---- Davide: love that stays and is refused. F with no third.
    sing(sec, "bbar", "davide", "C3:.5 D3:.5 F3:1 Eb3:.5 D3:.5 C3:.5 F3:1.5", "Se re stas si sa rei lui",
         "Se restassi, sarei lui:", "If I stayed, I would become him:", origin=31.0, vel=0.5)
    sing(sec, "bbar", "davide", "C3:.5 D3:.5 F3:1 Eb3:.5 G3:1 F3:.5 D3:.75 C3:.75",
         "per a mar ti de vo_an da re", "per amarti, devo andare.", "to love you, I must go.",
         origin=36.0, vel=0.48)
    dp = tx.prog("Fsus2:2 Bbadd9/F:2 F5:1 Gm7/F:2 C7sus4:2 Fsus4:1", origin=31.0)
    for i, evs in enumerate(tx.sustain(dp, [(50, 60), (55, 65), (60, 70)], vel=0.2,
                                       avoid_pcs=NO_A)):
        sec.add(("vc", "va", "hn")[i], evs)
    sec.add("cb", tx.bass(dp, lo=29, hi=41, vel=0.24))
    sec.add("hn", [Ev(41.0, 2.0, pitch("F3"), 0.18, "", None, None, {"env": "fade"})])
    sec.cue("door", 41.5)
    # ---- Marco withdraws
    mf = P("Db4:.5 Bb4:1.5 Ab4:.75", origin=43.0, vel=0.26)
    for e in mf:
        e.tags["motif"] = "marco_letter"
    sec.add("cl", mf)
    sing(sec, "ten", "marco", "Bb3:.5 Gb3:1", "ad dio", "Addio.", "Goodbye.", origin=44.5, vel=0.4)
    sec.text("Non sono la risposta. Ero soltanto la domanda.", "I am not the answer. I was only the question.",
             43.0, 44.4, style="parlato")
    sec.cue("letter_slide", 0.5)
    sec.cue("letter_open", 3.0)
    sec.cue("resolution", 9.0)
    sec.cue("confession", 13.0)
    sec.cue("marco", 43.0)
    score.add(sec)
    return sec


# =============================================================================================
# S11  SCENA ED ARIA FINALE. D-flat major, the key without A. The required shot lives here:
#      dolly-in (14-50), wide hall (50-89), close-up (89-121), curtain (136-).
# =============================================================================================
def s11(score):
    tempo = [(0, 60), (14, 72), (56, 60), (57, 80), (89, 72), (113, 80), (121, 60)]
    meters = [(0, 4, 4), (12, 2, 4), (14, 6, 8), (56, 1, 4), (57, 4, 4), (133, 3, 4),
              (136, 4, 4), (144, 1, 4)]
    sec = section("s11", tempo, meters)

    # ---- scena: the empty apartment
    sing(sec, "sop", "elena", "F4:.25 Ab4:.5 Gb4:.25 F4:.25 Ab4:.5 F4:.25 F4:.5",
         "la se dia di da vi de", "La sedia di Davide.", "Davide's chair.", origin=1.0, vel=0.34,
         style="parlato")
    sing(sec, "sop", "elena", "Db4:.25 Eb4:.25 F4:.5 Eb4:.25 Db4:.25 Eb4:.25 F4:.5 Db4:.25 F4:.25 "
         "Gb4:.5 F4:.5", "la co per ta di tom ma so pie ga ta", "La coperta di Tommaso, piegata.",
         "Tommaso's blanket, folded.", origin=4.25, vel=0.32, style="parlato")
    sing(sec, "sop", "elena", "Ab4:.25 Bb4:.25 Db5:.5 Bb4:.5 Ab4:.25 Gb4:.5 F4:.75",
         "la fi ne stra il ma re", "La finestra. Il mare.", "The window. The sea.", origin=8.75,
         vel=0.34, style="parlato")
    sing(sec, "sop", "elena", "Ab4:.25 F4:.5 Db4:1.25", "nes su no", "Nessuno.", "No one.",
         origin=12.0, vel=0.3, style="parlato")
    sec.add("cb", [Ev(0, 14, pitch("Db2"), 0.14)])
    sec.add("va_solo", P("Ab3:5 Bb3:4 Ab3:4", origin=1.0, vel=0.18), tech="sord")
    sec.add("harp", [Ev(t, 3, pitch(p), 0.16, "", None, None, {"harmonic": True})
                     for t, p in ((3.5, "Db5"), (8.0, "Ab5"), (11.75, "F5"))])

    # ---- cantabile: the dolly-in. The orchestra swells; the wedding refrain in the horns.
    cp = tx.prog("Db:3 | Ab7sus4:1.5 Ab7:1.5 | Db:1.5 Ab7:1.5 | Db:1.5 Bbm:1.5 | Gb:3 | "
                 "Db/Ab:1.5 E:1.5 | Db:1.5 Gb:1.5 | Ebm7:1.5 Ab7sus4:1 Ab7:.5 | Db/F:1.5 Gb:1.5 | "
                 "Ab7:1.5 Db:1.5 | Db/F:1.5 Gb:1.5 | Ab7:1.5 Db:1.5", origin=14, bar=3)
    L = []
    L += sing(sec, "sop", "elena",
              "Ab4:.5 Bb4:.5 C5:.5 Db5:1 C5:.5 F5:1 Eb5:.5 Db5:.25 C5:.25 Bb4:.5 Ab4:.5",
              "Io mi ri ve do_in piaz za_a di ciot t'an ni",
              "Io mi rivedo in piazza, a diciott'anni,", "I see myself again in the square, at eighteen,",
              origin=20, vel=0.56)
    L += sing(sec, "sop", "elena",
              "Ab4:.5 Bb4:.5 Db5:1 C5:.5 Db5:.5 F5:.75 Eb5:.25 Db5:.5 B4:.5 E5:.75 Ab4:.25",
              "mi ri ve do_a ven t'an ni nel sa lot to", "mi rivedo a vent'anni, nel salotto,",
              "I see myself at twenty, in the parlour,", origin=26, vel=0.58)
    L += sing(sec, "sop", "elena",
              "F5:.5 Ab5:1 Gb5:.5 Bb5:1 Gb5:.5 F5:.5 Eb5:.5 Db5:.5 C5:.25 Eb5:.5 C5:.25",
              "e lui vit to rio sul l'al ta re bel lo", "e lui, Vittorio, sull'altare, bello:",
              "and him, Vittorio, at the altar, handsome:", origin=32, vel=0.62)
    L += sing(sec, "sop", "elena", "Db5:1 Eb5:.5 Gb5:1.5 Bb5:1.5 Ab5:1.5", "e ra_il mio so gno",
              "era il mio sogno.", "he was my dream.", origin=38, vel=0.7)
    Wf = parse(WEDDING, bar=3, origin=0)
    refrain = [Ev(e.beat - 24 + 20, e.dur, e.midi - 13, 0.4, "", None, None,
                  {"motif": "wedding_memory"}) for e in Wf if e.beat >= 24]
    sec.add("hn", refrain)
    sec.add("vn1", P("F5:1 Eb5:.5 Db5:1 Bb4:.5 | Ab4:1 C5:.5 Db5:1.5", origin=44, vel=0.5, bar=3))
    rise = tx.arp(cp[:3], step=0.25, lo=49, hi=89, vel=0.3, shape="up", seed=31)
    sec.add("vn2", rise)
    for i, evs in enumerate(tx.sustain(cp[2:], [(49, 60), (56, 67), (61, 72), (65, 77)], vel=0.3)):
        sec.add(("vc", "va", "vn2", "vn1")[i], evs)
    sec.add("cb", tx.bass(cp, lo=28, hi=41, vel=0.36))
    sec.add("harp", tx.arp(cp, step=0.5, lo=49, hi=85, vel=0.24, shape="updown", seed=33))
    add_lines(sec, "cl", tx.sustain(cp[2:], [(60, 70)], vel=0.16))
    sec.add("timp", [Ev(17, 3, pitch("Ab2"), 0.32, "", None, None, {"roll": True, "cresc": True})])
    sec.add("cym", [Ev(19.6, 1.8, 60, 0.22, "", None, None, {"swell": True})])

    # ---- the wide hall: her line echoes in the dome; then Vittorio from the dark
    sing(sec, "sop", "elena", "F5:.5 Eb5:.25 Db5:.25 Ab5:1 Gb5:.5 F5:.5 Eb5:1 Db5:.5 C5:.5 Eb5:.5 "
         "Db5:.5", "Non fan ta sia l'e vi den za che_a ve vo",
         "Non fantasia: l'evidenza che avevo.", "Not fantasy: the evidence I had.", origin=50,
         vel=0.62)
    wp = tx.prog("Gb:3 | Ab7:1.5 Db:1.5", origin=50)
    for i, evs in enumerate(tx.sustain(wp, [(49, 60), (56, 67), (61, 72)], vel=0.22)):
        sec.add(("vc", "va", "vn2")[i], evs)
    sec.add("cb", tx.bass(wp, lo=28, hi=41, vel=0.24))
    V = sing(sec, "bar", "vittorio", VITTORIO, VITTORIO_TEXT[3], "", "", origin=57, vel=0.5,
             bar=4, show=False, style="offstage", motif="vittorio", appearance=3)
    lines_from(sec, "vittorio", V, VITTORIO_LINES[3], [8, 8, 8, 8], style="offstage")
    sec.add("cb", [Ev(57, 32, pitch("Ab1"), 0.12)])
    sec.add("va", [Ev(73, 16, pitch("Eb3"), 0.08)], tech="sord")

    # ---- the close-up: the unbroken line
    up = tx.prog("Db:2 Ab/C:2 | Bbm:2 Gb:2 | Db/F:2 Gb:2 | Db/Ab:2 Ab7:2 | Gb:2 Ebm7:2 | "
                 "Db/Ab:1.5 Ab7sus4:1.5 Ab7:1", origin=89, bar=4)
    sing(sec, "sop", "elena", "Ab4:1 Bb4:.5 Db5:1.5 C5:.5 Db5:.5 F5:1 Eb5:.5 Db5:.5 Eb5:.5 Gb5:1 F5:.5",
         "O ra ve do la li ne a_u na_e so la", "Ora vedo la linea, una e sola,",
         "Now I see the line, one line, unbroken,", origin=89, vel=0.62)
    sing(sec, "sop", "elena", "F5:.5 Gb5:1 F5:.5 Eb5:.5 F5:.5 Ab5:2 Gb5:.5 F5:.5 Eb5:.5 F5:1 Db5:.5",
         "dal gior no del mio sì fi no_a sta se ra", "dal giorno del mio sì fino a stasera:",
         "from the day of my yes until tonight:", origin=97, vel=0.68)
    sing(sec, "sop", "elena", "F5:.5 Ab5:1 Gb5:.5 Bb5:1 Ab5:.5 Gb5:1 F5:.5 Ab5:.75 Bb5:.25 Db6:1.5 Ab5:.5",
         "co sì si sce glie_al bu io tut ti sem pre", "Così si sceglie: al buio, tutti, sempre.",
         "This is how we choose: in the dark, all of us, always.", origin=105, vel=0.8)
    vs = tx.sustain(up, [(49, 60), (56, 67), (61, 72), (65, 77)], vel=0.36)
    for i, evs in enumerate(vs):
        sec.add(("vc", "va", "vn2", "vn2")[i], evs)
    desc = tx.sustain(up, [(77, 91)], vel=0.4)[0]
    sec.add("vn1", desc)
    sec.add("cb", tx.bass(up, lo=28, hi=41, vel=0.42))
    add_lines(sec, "hn", tx.sustain(up, [(53, 62), (57, 67)], vel=0.3))
    sec.add("harp", tx.arp(up, step=0.5, lo=49, hi=89, vel=0.26, shape="updown", seed=37))
    sec.add("timp", [Ev(105, 6, pitch("Ab2"), 0.3, "", None, None, {"roll": True, "cresc": True})])
    sec.add("cym", [Ev(109, 2.0, 60, 0.3, "", None, None, {"swell": True})])

    # ---- the second intrusion, unaccompanied
    V4 = sing(sec, "bar", "vittorio", " | ".join(VITTORIO.split("|")[:2]), VITTORIO_TEXT[4],
              *VITTORIO_LINES[4][0], origin=113, vel=0.46, bar=4, style="offstage",
              motif="vittorio", appearance=4)

    # ---- the final close
    fp = tx.prog("Db:2 Gb/Db:2 | Bbm:2 Ab7sus4:1 Ab7:1 | Db/F:2 Gb:2 | Ebm7:1 Ab7:2", origin=121)
    sing(sec, "sop", "elena", "Ab4:.5 Bb4:.5 Db5:1 C5:.5 Db5:.5 F5:1.5 Eb5:.5 Db5:.5 C5:.5 Db5:1.5",
         "Con que gli_oc chi quel sì lo ri di rei", "Con quegli occhi, quel sì lo ridirei.",
         "With those eyes, I would say that yes again.", origin=121, vel=0.56)
    sing(sec, "sop", "elena", "F5:.5 Eb5:.5 Db5:1 C5:.5 Db5:.5 F5:1 Eb5:.5 Db5:.5 Bb4:.5 C5:.5 Db5:4",
         "C'e ra_il so le quel gior no_e mi ba sta va", "C'era il sole, quel giorno, e mi bastava.",
         "There was sunlight that day, and it was enough.", origin=129, vel=0.52)
    for i, evs in enumerate(tx.sustain(fp, [(49, 60), (56, 67), (61, 72), (65, 77)], vel=0.24)):
        sec.add(("vc", "va", "vn2", "vn1")[i], evs, tech="sord")
    sec.add("cb", tx.bass(fp, lo=28, hi=41, vel=0.26))
    add_lines(sec, "hn", tx.sustain(fp, [(53, 62)], vel=0.18))
    sec.add("harp", tx.arp(fp, step=1.0, lo=49, hi=80, vel=0.18, seed=41))
    final = [("cb", "Db2"), ("vc", "Ab2"), ("vc", "Db3"), ("va", "F3"), ("va", "Ab3"),
             ("vn2", "Db4"), ("vn2", "F4"), ("vn1", "Ab4"), ("vn1", "Db5"), ("hn", "F3"),
             ("hn", "Ab3"), ("harp", "Db3")]
    for inst, p in final:
        sec.add(inst, [Ev(136, 7.0, pitch(p), 0.2, "", None, None, {"env": "fade"})])
    sec.cue("scena", 0)
    sec.cue("dolly", 14)
    sec.cue("sing", 20)
    sec.cue("wide", 50)
    sec.cue("echo", 56)
    sec.cue("vittorio3", 57)
    sec.cue("closeup", 89)
    sec.cue("climax", 111)
    sec.cue("vittorio4", 113)
    sec.cue("close", 121)
    sec.cue("final_chord", 136)
    sec.cue("curtain", 137.5)
    sec.cue("black", 143)
    score.add(sec)
    return sec
