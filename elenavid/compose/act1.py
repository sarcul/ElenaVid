"""Prologue and Act I: tuning, the village, the wedding, the Verona house."""
from __future__ import annotations

from ..notation import Ev, parse, attach_lyrics
from ..theory import pitch
from . import textures as tx
from .choral import harmonize
from .common import section, sing, P, add_lines, tone
from .themes import (WEDDING, WEDDING_LYR, WEDDING_HARM, WEDDING_LINES, VITTORIO, VITTORIO_HARM,
                     VITTORIO_TEXT, VITTORIO_LINES, MARCO)


# =============================================================================================
# S00  PROLOGO: the dark hall. The oboe gives the A; the orchestra tunes to it. Applause, hush.
#      A solo violin plays the wedding refrain's leap A-D-A and holds the high A: the title.
# =============================================================================================
def s00(score):
    sec = section("s00", [(0, 60)], [(0, 4, 4)])   # free time: one beat = one second
    sec.add("ob", [Ev(2.5, 4.6, 69, 0.40, "", None, None, {"tuning": True})], voice="tuning_ob")
    tun = [  # (inst, start, dur, pitch, glide in cents)
        ("vn1", 3.1, 2.9, "A4", -28), ("vn2", 3.3, 2.6, "A4", 22), ("va", 3.6, 2.2, "A4", -18),
        ("vc", 3.8, 2.4, "A3", 25), ("cb", 4.1, 2.3, "A1", -20),
        ("vn1", 5.7, 1.6, "E5", 16), ("vn1", 5.7, 1.6, "A4", 0),
        ("vn2", 6.1, 1.5, "D4", -22), ("vn2", 6.1, 1.5, "A4", 0),
        ("va", 6.3, 1.6, "D4", 18), ("va", 6.3, 1.6, "A4", 0),
        ("va", 7.3, 1.2, "C3", -15), ("va", 7.3, 1.2, "G3", 0),
        ("vc", 6.5, 1.4, "D3", -18), ("vc", 6.5, 1.4, "A3", 0),
        ("vc", 7.5, 1.2, "C2", 20), ("vc", 7.5, 1.2, "G2", 0),
        ("cb", 6.6, 1.3, "D2", 15), ("cb", 7.6, 1.0, "E1", -12),
    ]
    for inst, t0, d, p, g in tun:
        sec.add(inst, [Ev(t0, d, pitch(p), 0.20, "", None, None, {"glide": g, "tuning": True})])
    noodles = [  # warm-up fragments: the opera's own motifs scattered through the pit
        ("fl", 5.2, "A5:.14 G5:.14 F#5:.14 E5:.14 D5:.5"),
        ("cl", 6.0, MARCO.replace(":.5", ":.25").replace(":1.5", ":.7")),
        ("bn", 5.4, "D2:.3 A2:.3 D3:.3 F#3:.6"),
        ("ob", 7.3, "D5:.1 E5:.1 F#5:.1 G5:.1 A5:.1 B5:.35"),
        ("hn", 6.6, "F3:.5 C4:.5 F4:.8"),
        ("tpt", 7.5, "G4:.2 C5:.2 E5:.5"),
        ("timp", 5.0, "A2:.25 r:.35 A2:.25 r:.8 D3:.25"),
        ("harp", 7.0, "A2:.3 E3:.3 A3:.6"),
    ]
    for inst, t0, mel in noodles:
        evs = P(mel, origin=t0, vel=0.22)
        for e in evs:
            e.tags["tuning"] = True
        sec.add(inst, evs, voice=inst + "_warmup", tech="mute" if inst == "tpt" else "")
    # the opening: a breath of D major, then the solo violin
    for inst, p in (("cb", "D2"), ("vc", "D3"), ("vc", "A3"), ("va", "F#4"), ("vn2", "A4"),
                    ("vn1", "D5")):
        sec.add(inst, [Ev(16.6, 8.9, pitch(p), 0.16, "", None, None, {"env": "swell"})], tech="sord")
    sec.add("vn_solo", P("A4:.6 D5:.3 A5:6.0", origin=17.4, vel=0.34), tech="espr")
    roll = [Ev(18.3 + 0.07 * i, 5.5, pitch(p), 0.28) for i, p in
            enumerate(("D3", "A3", "D4", "F#4", "A4", "D5"))]
    sec.add("harp", roll)
    sec.cue_abs("tuning", 2.5)
    sec.cue_abs("applause", 9.5)
    sec.cue_abs("hush", 14.5)
    sec.cue_abs("upbeat", 16.0)
    sec.cue_abs("title_in", 18.0)
    sec.cue_abs("title_out", 24.6)
    score.add(sec)
    return sec


def oompah(p, lo=40, hi=52, chord_rng=((55, 67), (59, 71), (62, 74)), vel=0.4):
    """2/4 village band: bass on each beat, chord on each off-beat."""
    bass, stabs = [], []
    vs = tx.voicings(p, list(chord_rng), include_bass=False)
    alt = 0
    for (b, d, c), (_, _, v) in zip(p, vs):
        if c is None:
            continue
        roots = [m for m in range(lo, hi + 1) if m % 12 == c.bass]
        fifths = [m for m in range(lo, hi + 1) if c.fifth is not None and m % 12 == c.fifth]
        n = int(round(d / 1.0)) or 1
        for k in range(n):
            t = b + k * 1.0
            m = roots[0] if (alt % 2 == 0 or not fifths) else fifths[0]
            alt += 1
            bass.append(Ev(t, 0.45, m, vel, "'"))
            if d - k >= 0.6:
                for x in v:
                    stabs.append(Ev(t + 0.5, 0.3, x, vel * 0.7, "'"))
    return bass, stabs


# =============================================================================================
# S01  LA PIAZZA. Market chorus (2/4), farewell duet (4/4), Elena's longing (3/4).
# =============================================================================================
def s01(score):
    sec = section("s01", [(0, 120), (20, 100), (40, 76)], [(0, 2, 4), (20, 4, 4), (40, 3, 4)])

    # ---- market chorus, bars 1-10 (beats 0-20)
    intro = tx.prog("G:2 | D7:2")
    ch_prog = tx.prog("G:2 | Am7:1 D7:1 | G:2 | Am:1 D7:1 | G:2 | D/F#:1 G:1 | C:1 G/D:1 | "
                      "G/B:.5 D7:1 G:.5", origin=4)
    mel = ("D5:.5 D5:.5 B4:.5 G4:.5 | A4:.5 B4:.5 C5:.5 A4:.5 | D5:.5 D5:.5 B4:.5 G4:.5 | "
           "A4:.5 C5:.5 B4:.5 A4:.5 | G4:.5 B4:.5 D5:.5 G5:.5 | F#5:.5 E5:.5 D5:.5 B4:.5 | "
           "C5:.5 E5:.5 D5:.5 B4:.5 | B4:.5 A4:.5 F#4:.5 G4:.5")
    lyr = ("Pe sche d'o ro gra no_e vi no mie le lat te ro se_in fio re "
           "O gni fi glia_ha_il suo de sti no o gni cuo re_il suo si gno re")
    S = parse(mel, bar=2, origin=4, vel=0.62)
    attach_lyrics(S, lyr)
    A, T, B = harmonize(S, ch_prog, a_rng=(55, 72), t_rng=(48, 64), b_rng=(40, 55))
    for inst, evs in (("ch_s", S), ("ch_a", A), ("ch_t", T), ("ch_b", B)):
        sec.add(inst, evs, voice="chorus", style="chorus")
    sec.line("chorus", S[:16], "Pesche d'oro, grano e vino, miele, latte, rose in fiore!",
             "Golden peaches, grain and wine, honey, milk, roses in bloom!", style="chorus")
    sec.line("chorus", S[16:], "Ogni figlia ha il suo destino, ogni cuore il suo signore.",
             "Every daughter has her destiny, every heart its lord and master.", style="chorus")
    sec.add("cl", P("G4:.5 B4:.5 D5:.5 G5:.5 | F#5:.5 E5:.5 D5:.5 C5:.5", vel=0.5, bar=2))
    sec.add("cl", tx.clone(S, lyric=None, vel=0.42))
    sec.add("fl", tx.transpose(tx.clone(S[16:], lyric=None, vel=0.32), 12))
    bs, st = oompah(intro + ch_prog)
    sec.add("vc", bs, tech="pizz")
    sec.add("cb", tx.transpose(bs, -12), tech="pizz")
    sec.add("va", st, tech="pizz")
    sec.add("bn", tx.clone(bs, vel=0.3))
    sec.add("tri", [Ev(4, 0.5, 84, 0.3), Ev(12, 0.5, 84, 0.28)])
    sec.add("tamb", [Ev(b + 0.5, 0.2, 60, 0.18) for b in range(0, 20)])

    # ---- farewell duet, bars 11-15 (beats 20-40)
    d_prog = tx.prog("G:2 D7:1 G:1 | G:2 D/F#:1 Em:1 | C:2 D7:2 | Em:2 B7:2 | D7:4", origin=20)
    sing(sec, "ten", "marco", "D3:.5 B3:.5 A3:.5 C4:1 E4:.5 D4:.5 G3:.5",
         "Ti scri ve rò lo giu ro", "Ti scriverò, lo giuro,", "I will write to you, I swear it,",
         origin=20, vel=0.55)
    sing(sec, "sop", "elena", "B4:.5 D5:.5 G5:.5 F#5:1 E5:.5 D5:.5 B4:.5",
         "Mi scri ve rai di stra de", "Mi scriverai di strade", "You will write to me of streets",
         origin=24, vel=0.55)
    sing(sec, "sop", "elena", "C5:.5 B4:.5 A4:.5 G4:1 A4:.5 B4:.5 A4:.5",
         "che non co no sco_an co ra", "che non conosco ancora;", "I do not know yet;",
         origin=28, vel=0.52)
    sing(sec, "sop", "elena", "E5:.5 E5:1 D#5:.5 E5:.5 F#5:.5 G5:.5 F#5:.5",
         "C'è_un no me che non di co", "(C'è un nome che non dico)",
         "(There is a name I do not say)", origin=32, vel=0.40, style="aside")
    sing(sec, "ten", "marco", MARCO.replace("D4", "D3").replace("B4", "B3").replace("A4", "A3")
         .replace("C5", "C4"), "Ti scri ve rò", "Ti scriverò.", "I will write.", origin=36,
         vel=0.5, motif="marco")
    cl_motif = P(MARCO, origin=36, vel=0.36)
    for e in cl_motif:
        e.tags["motif"] = "marco"
    sec.add("cl", cl_motif)
    for i, evs in enumerate(tx.sustain(d_prog, [(50, 62), (55, 67), (60, 72)], vel=0.26)):
        sec.add(("vc", "va", "vn2")[i], evs, tech="sord")
    sec.add("cb", tx.bass(d_prog, lo=31, hi=43, vel=0.3), tech="sord")
    sec.add("harp", tx.arp(d_prog, step=0.5, lo=55, hi=79, vel=0.26, shape="updown"))

    # ---- Elena's aria, bars 16-19 (beats 40-52) + tail bar 20 (52-55)
    a_prog = tx.prog("G:3 | D7:1 G:2 | Em:1 C:2 | Am7:1 D7sus4:2 | D7sus4:1.5 D7:1.5", origin=40)
    sing(sec, "sop", "elena",
         "B4:1.5 A4:.5 G4:1 | D5:1 C5:.5 B4:1 A4:.5 | G4:1 E5:1.5 D5:.5 | C5:.5 B4:.5 D5:1.5 C5:.5",
         "Re sta la stra da bian ca la pol ve re nel so le",
         "Resta la strada bianca, la polvere nel sole;",
         "The white road remains, the dust in the sunlight;", origin=40, vel=0.5, bar=3)
    tail = P("D4:.5", origin=51.5, vel=0.3) + P("B4:1.5 A4:.5 C5:1", origin=52, vel=0.3)
    for e in tail:
        e.tags["motif"] = "marco"
    sec.add("cl", tail)
    for i, evs in enumerate(tx.sustain(a_prog, [(48, 60), (55, 67), (60, 72), (64, 76)], vel=0.24)):
        sec.add(("vc", "va", "vn2", "vn1")[i], evs, tech="sord")
    sec.add("cb", tx.bass(a_prog, lo=31, hi=43, vel=0.26), tech="sord")
    sec.add("harp", tx.arp(a_prog, step=0.5, lo=55, hi=81, vel=0.22, shape="wave", seed=3))
    sec.add("hn", [Ev(49, 6, pitch("D4"), 0.18), Ev(49, 6, pitch("A3"), 0.16)])
    sec.cue("chorus", 4)
    sec.cue("duet", 20)
    sec.cue("marco_leaves", 36)
    sec.cue("aria", 40)
    sec.cue("letters", 52)
    score.add(sec)
    return sec


# =============================================================================================
# S02  IL SALOTTO, LA CHIESA. Mother; Elena's hope ("Sì" on A5); the vow on Vittorio's phrase;
#      the semitone lift A-flat -> A7 -> D; the wedding chorus; the celebration cools.
# =============================================================================================
def s02(score):
    tempo = [(0, 72), (24, 80), (34, 99), (83.5, 99, "ramp"), (89.5, 64)]
    meters = [(0, 4, 4), (32, 2, 4), (34, 3, 8), (35.5, 6, 8)]
    sec = section("s02", tempo, meters)

    # ---- mother (bars 1-3)
    m_prog = tx.prog("Bm:2 G:1 F#7:1 | Bm:1 G:1 D/A:1 A7:1 | Bm:1 Em7:1 A7:1.5 D:.5")
    sec.add("va", P("B3:1 C#4:.5 D4:.5 F#4:1 E4:.5 C#4:.5", vel=0.34))
    sing(sec, "mez", "madre", "F#4:.75 G4:.25 A4:.75 B4:.25 D5:.5 C#5:.5 B4:.5 A4:.5",
         "Guar da be ne_e poi de ci di", "Guarda bene, e poi decidi,",
         "Look well, and then decide,", origin=4, vel=0.52)
    sing(sec, "mez", "madre", "D5:.75 C#5:.25 B4:.75 A4:.25 G4:.5 F#4:.5 E4:.5 F#4:.5",
         "co me guar di quan do ri di", "come guardi quando ridi.",
         "the way you look when you laugh.", origin=8, vel=0.5)
    for i, evs in enumerate(tx.sustain(m_prog, [(50, 62), (57, 69), (62, 74)], vel=0.24)):
        sec.add(("vc", "vn2", "vn1")[i], evs)
    sec.add("cb", tx.bass(m_prog, lo=30, hi=45, vel=0.28))
    sec.add("harp", tx.arp(tx.prog("Bm:4 | Bm:1 G:1 D/A:1 A7:1 | Bm:1 Em7:1 A7:1.5 D:.5"),
                           step=1 / 3, lo=50, hi=78, vel=0.2, shape="updown"))

    # ---- Elena's hope (bars 4-6)
    h_prog = tx.prog("D:1.5 G:1.5 D/F#:1 | Bm:1.5 A7:1 D:1.5 | Gmaj7:2 D:2", origin=12)
    sing(sec, "sop", "elena", "A4:.5 B4:.5 C#5:.5 D5:1 E5:.5 F#5:1",
         "e se mi chie de vuoi", "E se mi chiede «Vuoi?»,", "And if he asks me, \"Will you?\",",
         origin=12, vel=0.55)
    sing(sec, "sop", "elena", "F#5:.5 E5:.5 D5:.5 C#5:1 D5:.5 A5:1~ | A5:2 G5:.5 F#5:1.5",
         "ri spon de rò di sì _ _", "risponderò di sì:", "I shall answer yes:", origin=16,
         vel=0.62)
    for i, evs in enumerate(tx.sustain(h_prog, [(50, 62), (55, 67), (60, 72), (64, 76)], vel=0.3)):
        sec.add(("vc", "va", "vn2", "vn1")[i], evs)
    sec.add("cb", tx.bass(h_prog, lo=30, hi=45, vel=0.32))
    sec.add("harp", tx.arp(h_prog, step=0.5, lo=55, hi=83, vel=0.26, shape="updown", seed=7))
    sec.add("fl", P("r:3 F#5:1 | r:4 | A5:2 F#5:2", origin=12, vel=0.26))

    # ---- the vow (bars 7-9): organ, Vittorio's phrase bars 1-2, Elena's "Sì" resolves it
    v_mel = VITTORIO.split("|")
    vow = " | ".join(v_mel[:2])
    sing(sec, "bar", "vittorio", vow, VITTORIO_TEXT["vow"], *VITTORIO_LINES["vow"][0],
         origin=24, vel=0.52, motif="vittorio", appearance="vow")
    o_prog = tx.prog("Abmaj7:4 | Fm7:2 Eb7sus4:1 Eb7:1 | Ab:2", origin=24)
    add_lines(sec, "organ", tx.sustain(o_prog, [(51, 63), (56, 68), (60, 72)], vel=0.3,
                                       include_bass=True, bass_range=(32, 46)))
    sing(sec, "sop", "elena", "C5:2", "Sì", "Sì.", "Yes.", origin=32, vel=0.5, style="vow")
    # ---- the lift: A7, then D major (bar 10, 3/8)
    lift = [Ev(34.0, 1.5, pitch(p), 0.62, ">") for p in ("A2", "E3", "G3", "C#4", "E4", "A4")]
    for e, inst in zip(lift, ("cb", "vc", "va", "vn2", "vn1", "vn1")):
        sec.add(inst, [e])
    sec.add("hn", [Ev(34.0, 1.5, pitch(p), 0.55, ">") for p in ("E3", "A3", "C#4", "G4")])
    sec.add("tpt", [Ev(34.0, 1.5, pitch(p), 0.5, ">") for p in ("E4", "A4")])
    sec.add("timp", [Ev(34.0, 1.5, pitch("A2"), 0.5, "", None, None, {"roll": True})])
    sec.add("harp", [Ev(34.0 + 0.06 * i, 1.4, m, 0.32) for i, m in
                     enumerate(range(57, 89, 2))])
    sec.add("cym", [Ev(35.5, 2.0, 60, 0.42)])

    # ---- the wedding chorus (bars 11-26, beats 35.5-83.5)
    O = 35.5
    w_prog = tx.prog(WEDDING_HARM, origin=O, bar=3)
    S = parse(WEDDING, bar=3, origin=O, vel=0.66)
    attach_lyrics(S, WEDDING_LYR)
    for e in S:
        e.tags["motif"] = "wedding"
    tx.hairpin(S[:32], 0.6, 0.68)
    tx.hairpin(S[32:], 0.74, 0.84)
    A, T, B = harmonize(S, w_prog, a_rng=(57, 74), t_rng=(50, 67), b_rng=(41, 57))
    for inst, evs in (("ch_s", S), ("ch_a", A), ("ch_t", T), ("ch_b", B)):
        sec.add(inst, evs, voice="chorus", style="chorus")
    k = 0
    for it, en in WEDDING_LINES:
        n = 7 if it.endswith(("unì;", "sì!")) else 8
        sec.line("chorus", S[k:k + n], it, en, style="chorus")
        k += n
    sec.add("vn1", tx.clone(S, lyric=None, vel=0.5))
    sec.add("fl", tx.transpose(tx.clone(S[32:], lyric=None, vel=0.4), 12))
    sec.add("ob", tx.clone(S[32:], lyric=None, vel=0.4))
    sec.add("cl", tx.transpose(tx.clone(S[:32], lyric=None, vel=0.36), -12))
    lilt = tx.furlana(w_prog, lo=55, hi=74, vel=0.36)
    sec.add("vn2", lilt, tech="spicc")
    sec.add("va", tx.transpose([e for e in lilt if e.midi >= 62], -12), tech="spicc")
    wb = tx.bass(w_prog, pattern=[(0, 1.3), (1.5, 1.3)], lo=38, hi=50, vel=0.5)
    sec.add("vc", wb)
    sec.add("cb", tx.transpose(wb, -12))
    sec.add("bn", tx.clone(wb, vel=0.32))
    for i, evs in enumerate(tx.sustain(w_prog, [(53, 62), (57, 67), (62, 72)], vel=0.32)):
        sec.add("hn", evs)
    sec.add("tpt", tx.clone([e for e in S[32:] if e.midi >= 74], lyric=None, vel=0.42))
    sec.add("harp", tx.arp(w_prog, step=0.5, lo=50, hi=86, vel=0.24, shape="up", seed=11))
    # bells a festa (tuned D-A-F#-D, rung in rotation through the refrain)
    bells = []
    peal = [pitch(p) for p in ("D5", "A4", "F#4", "D4")]
    for k in range(32):
        bells.append(Ev(O + 24 + k * 0.75, 3.0, peal[k % 4], 0.34))
    sec.add("tubbells", bells, ring=True)
    sec.add("tri", [Ev(O + 24 + 3 * k, 0.5, 84, 0.26) for k in range(8)])
    sec.add("timp", [Ev(O + 21, 3.0, pitch("A2"), 0.4, "", None, None, {"roll": True}),
                     Ev(O + 45, 1.5, pitch("A2"), 0.5), Ev(O + 46.5, 1.5, pitch("D3"), 0.55)])
    sec.add("cym", [Ev(O + 24, 2.5, 60, 0.36), Ev(O + 46.5, 3.0, 60, 0.4)])

    # ---- coda (bars 27-28): it cools
    C = 83.5
    for inst, p in (("cb", "D2"), ("vc", "D3"), ("va", "A3"), ("vn2", "F#4"), ("vn1", "D5")):
        sec.add(inst, [Ev(C, 3.0, pitch(p), 0.34, "", None, None, {"env": "decay"})])
    for inst, p in (("cb", "D2"), ("vc", "D3"), ("va", "A3"), ("vn2", "F4"), ("vn1", "D5")):
        sec.add(inst, [Ev(C + 3.0, 2.6, pitch(p), 0.2, "", None, None, {"env": "fade"})], tech="sord")
    sec.add("celesta", P("A4:1 D5:.5 A5:1.5", origin=C + 3.0, vel=0.3))
    sec.add("tubbells", [Ev(C, 4.0, pitch("D4"), 0.3)], ring=True)
    sec.cue("mother", 4)
    sec.cue("hope", 12)
    sec.cue("si_hope", 21)
    sec.cue("church", 24)
    sec.cue("vow", 24)
    sec.cue("si_vow", 32)
    sec.cue("lift", 34)
    sec.cue("wedding", O)
    sec.cue("refrain", O + 24)
    sec.cue("cooling", C)
    score.add(sec)
    return sec


# =============================================================================================
# S03  LA CASA DI VERONA. Lullaby (Tommaso's tone first identified), Vittorio, the blow,
#      the child's note alone, Elena's resolve over the A pedal.
# =============================================================================================
def s03(score):
    tempo = [(0, 78), (27, 96), (43, 60), (45, 66.4)]
    meters = [(0, 6, 8), (27, 4, 4), (43, 2, 4), (45, 4, 4)]
    sec = section("s03", tempo, meters)

    l_prog = tx.prog("F:3 | F:3 | C7:1.5 F:1.5 | Dm:1.5 Bb:1.5 | F/C:1.5 C7:1.5 | Bb:1.5 F/A:1.5 | "
                     "C7:3 | F:1.5 Bb:1.5 | C7:1.5 F:1.5")
    mel = ("C5:.5 A4:.5 Bb4:.5 C5:1 A4:.5 | G4:1 F4:.5 r:1 A4:.5 | F4:1 G4:.5 A4:1 Bb4:.5 | "
           "C5:1 A4:.5 r:1 C5:.5 | D5:1 C5:.5 Bb4:1 A4:.5 | G4:1 F4:.5 r:1 E4:.5 | "
           "F4:1 G4:.5 A4:1 Bb4:.5 | A4:1.5 F4:1.5")
    lyr = ("Dor mi Tom ma so dor mi la not te_è_u na bar chet ta e_il mon do coi suoi stor mi "
           "ti_a spet ta_e non ha fret ta")
    E = parse(mel, bar=3, origin=3, vel=0.46)
    attach_lyrics(E, lyr)
    for e in E:
        e.tags["style"] = "lullaby"
    sec.add("sop", E, voice="elena")
    sec.line("elena", E[:8], "Dormi, Tommaso, dormi: la notte è una barchetta,",
             "Sleep, Tommaso, sleep: the night is a little boat,", style="aria")
    sec.line("elena", E[8:], "e il mondo coi suoi stormi ti aspetta e non ha fretta.",
             "and the world, with its flocks of birds, waits for you and is in no hurry.")
    sec.add("harp", tx.rocking(l_prog, lo=53, hi=77, vel=0.24))
    for i, evs in enumerate(tx.sustain(l_prog, [(53, 64), (57, 69)], vel=0.16)):
        sec.add(("va", "vn2")[i], evs, tech="sord")
    sec.add("vc", tx.bass(l_prog, pattern=[(0, 0.5), (1.5, 0.5)], lo=36, hi=50, vel=0.3),
            tech="pizz")
    cl = tx.diatonic([e for e in E if e.beat >= 15], -2, 5, "major")
    sec.add("cl", tx.clone(cl, lyric=None, vel=0.24))
    for t0, d in ((1.5, 5.5), (7.5, 6.0), (14.0, 6.5), (21.0, 6.0)):
        tone(sec, t0, d, vel=0.26)
    tone(sec, 9.0, 4.0, vel=0.12, inst="eh", voice="tommaso_eh")

    # ---- Vittorio (bars 10-12)
    vp = tx.prog("Cm:2 Ab:2 | Fm:2 G7:2 | Ab:1.5 G7b9:2.5", origin=27)
    sing(sec, "bar", "vittorio",
         "Eb3:.5 Eb3:.5 F3:.5 G3:1 Eb3:.5 r:1 | G3:.5 G3:.5 Ab3:.5 Bb3:.5 Bb3:.5 C4:1 G3:.5",
         "an co ra sve glia an co ra quel la ne nia", "Ancora sveglia? Ancora quella nenia?",
         "Still awake? Still that dirge?", origin=27, vel=0.7, style="parlato", bar=4)
    sing(sec, "sop", "elena", "G4:1 Ab4:.5 C5:1.5 B4:1", "È tuo fi glio", "È tuo figlio.",
         "He is your son.", origin=35, vel=0.6)
    for i, evs in enumerate(tx.sustain(vp, [(43, 55), (48, 60), (53, 65)], vel=0.5)):
        sec.add(("tbn", "tbn", "hn")[i], evs, art="^")
    sec.add("cb", tx.bass(vp, lo=28, hi=40, vel=0.55), tech="trem")
    sec.add("vc", tx.bass(vp, lo=36, hi=48, vel=0.5), tech="trem")
    sec.add("timp", [Ev(35, 4, pitch("G2"), 0.3, "", None, None, {"roll": True, "cresc": True})])
    tone(sec, 27.0, 8.0, vel=0.08)

    # ---- the blow (bar 13, beat 39)
    blow = ["Eb2", "Bb2", "Eb3", "Gb3", "A3", "Eb4", "A4", "Eb5"]
    insts = ["cb", "vc", "va", "tbn", "hn", "vn2", "vn1", "vn1"]
    for p, inst in zip(blow, insts):
        sec.add(inst, [Ev(39.0, 0.35, pitch(p), 0.95, "^")])
    sec.add("tpt", [Ev(39.0, 0.35, pitch("A4"), 0.9, "^"), Ev(39.0, 0.35, pitch("Eb5"), 0.9, "^")])
    sec.add("tamtam", [Ev(39.0, 6.0, 40, 0.8)], ring=True)
    sec.add("bd", [Ev(39.0, 1.0, 36, 0.9)])
    sec.cue("blow", 39.0)

    # ---- the child's note alone (bar 14) and Elena's resolve (bars 15-16) on an A pedal
    sing(sec, "treble", "tommaso", "A4:2", "a", "", "", origin=43, vel=0.3, show=False,
         tommaso=True)
    tone(sec, 43.0, 10.0, vel=0.24)
    rp = tx.prog("Dm/A:2 Gm/A:2 | A7:2 Dm/A:2", origin=45)
    sing(sec, "sop", "elena", "F5:1 E5:1 A4:.5 D5:1.5 | A4:.5 E5:1.5 A4:.5 F5:1.5",
         "Ba sta non qui non lui non più", "Basta. Non qui. Non lui. Non più.",
         "Enough. Not here. Not him. No more.", origin=45, vel=0.66, bar=4)
    for i, evs in enumerate(tx.sustain(rp, [(50, 62), (55, 67), (62, 74)], vel=0.34)):
        sec.add(("vc", "va", "vn2")[i], evs)
    sec.add("cb", [Ev(45, 8, pitch("A1"), 0.42)])
    sec.add("timp", [Ev(45, 8, pitch("A2"), 0.22, "", None, None, {"roll": True})])
    sec.cue("lullaby", 3)
    sec.cue("vittorio", 27)
    sec.cue("alone", 43)
    sec.cue("resolve", 45)
    sec.cue("curtain", 51)
    score.add(sec)
    return sec
