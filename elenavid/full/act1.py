"""Prologue and Act I of the full opera: Giovinezza e prigionia.

Each function returns a Num (see forms). Keys follow the opera's key scheme (opera/02_score.md);
wherever the film set a line, the film's melody is the line's melody.
"""
from __future__ import annotations

from ..compose.themes import WEDDING, WEDDING_HARM, VITTORIO, VITTORIO_HARM, MARCO
from ..notation import Ev
from .forms import Num
from .libretto import Direction


BAND_TUNE = ("D5:.5 D5:.5 B4:.5 G4:.5 | A4:.5 B4:.5 C5:.5 A4:.5 | D5:.5 D5:.5 B4:.5 G4:.5 | A4:.5 C5:.5 B4:.5 A4:.5 | "
             "G4:.5 B4:.5 D5:.5 G5:.5 | F#5:.5 E5:.5 D5:.5 B4:.5 | C5:.5 E5:.5 D5:.5 B4:.5 | B4:.5 A4:.5 F#4:.5 G4:.5")


def bars_of(text, a, b):
    """Bars a..b (1-based, inclusive) of a melody or progression string."""
    bars = [x.strip() for x in text.split("|")]
    return " | ".join(bars[a - 1:b])


def prologue():
    n = Num("P0", "Prologo: il teatro", "D", 60, (4, 4), location="house_prologue", act=0)
    n.island("s00", 0.0, 26.0)
    for k, v in (("tuning", 2.5), ("applause", 9.5), ("hush", 14.5), ("upbeat", 16.0), ("title_in", 18.0),
                 ("title_out", 24.6)):
        n.cue(k, v)
    return n


def prelude1():
    """Atto primo, preludio: the child's note; the wedding refrain; Vittorio far off; Marco's motif;
    the wedding melody in full; the village."""
    n = Num("P1", "Atto primo: Preludio", "D", 46, (6, 8), location="prelude", act=1)
    n.cue("start")
    n.tommaso(9.0, vel=0.24)
    n.rest(6.0)
    n.orch(n.sprog("D:6 | A7:3 D:3"), style="pad", dyn=0.16, sord=True)
    # the refrain, sostenuto, solo violin over muted strings
    refrain = bars_of(WEDDING, 9, 16)
    harm = bars_of(WEDDING_HARM, 9, 16)
    n.cue("refrain")
    p = n.sprog(harm)
    n.orch(p, style="pad", dyn=0.22, sord=True, advance=False)
    n.theme(refrain, inst="vn_solo", vel=0.36, advance=True, tech="espr")
    # a tritone away: Vittorio's first two bars, far off in the horns
    n.meter(4, 4).tempo(56)
    n.cue("vittorio_far")
    p = n.sprog(bars_of(VITTORIO_HARM, 1, 2))
    n.orch(p, style="pad", dyn=0.14, sord=True, advance=False)
    n.theme(bars_of(VITTORIO, 1, 2), inst="hn", vel=0.26, advance=True)
    # Marco's motif hangs on the fourth degree over the dominant
    n.key_to("G").cue("marco")
    p = n.sprog("D7:4")
    n.orch(p, style="pad", dyn=0.15, advance=False)
    n.theme(MARCO, inst="cl", vel=0.34, advance=False)
    n.rest(4.0).pause(1.5)
    # Allegro agitato: the flight and the storm (themes of Act II), Davide's calm (Act II, scene 2)
    n.meter(4, 4).tempo(126).key_to("Am").cue("allegro")
    flight = ("E5:1 A5:1 C6:1.5 B5:.5 | A5:1 E5:1 F5:2 | D5:1 F5:1 A5:1.5 G#5:.5 | A5:4 | "
              "C6:1 B5:1 A5:1 G#5:1 | F5:1 E5:1 D5:2 | B4:1 D5:1 E5:1.5 G#4:.5 | A4:4")
    n.orch(n.sprog("Am:4 | F:4 | Dm:4 | E7:4 | Am:4 | Dm:4 | E7:4 | Am:4"), style="tremolo", dyn=0.45, advance=False)
    n.theme(flight, inst="vn1", vel=0.5, advance=True)
    n.orch(n.sprog("Dm:4 | Bb:4 | Gm:4 | A7:4 | Dm:4 | Gm:4 | E7:4 | A7:4"), style="tremolo", dyn=0.55, advance=False)
    n.theme("D5:.5 F5:.5 A5:1 G5:.5 F5:.5 E5:1 | D5:.5 F5:.5 Bb5:1 A5:2 | G5:.5 Bb5:.5 D6:1 C#6:1 A5:1 | E5:4 | "
            "D6:1 A5:1 F5:1 D5:1 | Bb5:1 G5:1 E5:1 C#5:1 | E5:.5 G#5:.5 B5:1 D6:2 | C#6:4", inst="fl", vel=0.5,
            advance=False)
    n.add("timp", [Ev(n.cursor + 4 * k, 0.5, 50 if k % 2 == 0 else 45, 0.42) for k in range(8)])
    n.rest(32.0)
    n.key_to("F").tempo(66)
    n.orch(n.sprog("F:2 F/A:1 Bb:1 | F/C:2 C:1 C7:1 | F:2 C7/G:1 F/A:1 | Bb:1 F/C:1 C7:1 F:1"), style="pad", dyn=0.28,
           advance=False)
    n.theme("C4:.5 D4:.5 F4:.75 E4:.25 F4:.5 G4:.5 A4:.5 G4:.5 | A4:.5 G4:.5 F4:.75 E4:.25 D4:.5 E4:.5 D4:.5 C4:.5 | "
            "F4:.5 G4:.5 A4:.75 G4:.25 A4:.5 Bb4:.5 C5:.5 Bb4:.5 | A4:.5 G4:.5 F4:.75 D4:.25 C4:.5 E4:.5 G4:.5 F4:.5",
            inst="hn", vel=0.36, advance=True)
    n.tempo(126).key_to("Am")
    n.orch(n.sprog("Am:4 | F:4 | Dm:4 | E7:4"), style="tutti", dyn=0.6, advance=False)
    n.theme(flight.split(" | A5:4 | ")[0] + " | A5:4", inst="vn1", vel=0.6, advance=True)
    n.orch(n.sprog("E7:4 | E7:4"), style="tremolo", dyn=0.4)
    # the wedding melody, whole: verse in the strings, refrain for the orchestra
    n.meter(6, 8).tempo(60).key_to("D").cue("wedding")
    n.orch(n.sprog(bars_of(WEDDING_HARM, 1, 8)), style="furlana", dyn=0.32, advance=False)
    n.theme(bars_of(WEDDING, 1, 8), inst="vn1", vel=0.42, advance=False)
    n.theme(bars_of(WEDDING, 1, 8), inst="fl", vel=0.3, transpose=12, advance=True)
    n.cue("tutti")
    n.orch(n.sprog(bars_of(WEDDING_HARM, 9, 16)), style="tutti", dyn=0.6, advance=False)
    n.theme(bars_of(WEDDING, 9, 16), inst="vn1", vel=0.62, advance=False)
    n.theme(bars_of(WEDDING, 9, 16), inst="tpt", vel=0.5, advance=False)
    n.theme(bars_of(WEDDING, 9, 16), inst="ob", vel=0.5, advance=True)
    # a cloud: Vittorio's phrase, whole and unchanged, low in the cellos and bassoon
    n.meter(4, 4).tempo(56).key_to("Ab").cue("shadow")
    n.orch(n.sprog(VITTORIO_HARM), style="pad", dyn=0.2, sord=True, advance=False)
    n.theme(VITTORIO, inst="vc", vel=0.34, transpose=-12, advance=False)
    n.theme(VITTORIO, inst="bn", vel=0.26, transpose=-12, advance=True)
    n.tommaso(8.0, vel=0.2)
    n.orch(n.sprog("Fm:4 | Db:4"), style="pad", dyn=0.16, sord=True)
    # the refrain again, quietly, as if remembered
    n.meter(6, 8).tempo(48).key_to("D")
    n.orch(n.sprog(bars_of(WEDDING_HARM, 9, 12)), style="arpeggio", dyn=0.24, advance=False)
    n.theme(bars_of(WEDDING, 9, 12), inst="fl", vel=0.3, advance=True)
    # the light falls away into the village: G major, swifts in the flutes
    n.cue("village")
    n.orch(n.sprog("D:3 | Bm:3 | Em7:3 | A7:3 | D7:6"), style="pad", dyn=0.3)
    n.key_to("G")
    n.orch(n.sprog("G:3 | C/G:3 | G:3 | D7/G:3"), style="arpeggio", dyn=0.22, advance=False)
    for k in range(4):
        n.theme("D6:.25 E6:.25 D6:.25 E6:.25 D6:.5 r:1.75", inst="fl", vel=0.22, origin=n.cursor + 3.0 * k)
    n.rest(12.0)
    n.event("curtain", state="up")
    return n


def n1():
    """N. 1 Coro d'introduzione e scena: the market chorus (the film's tune), dances, the scene."""
    n = Num("N1", "Coro d'introduzione e scena", "G", 120, (2, 4), location="village_market", act=1, scene=1)
    L = n.L()
    ch = [x for x in L if x.speaker == "coro"]
    scene = [x for x in n.lib.items if not (hasattr(x, "speaker") and x.speaker == "coro")]
    n.cue("start")
    # the square wakes: a bustle of strings and woodwind before the band strikes up
    n.orch(n.sprog("G:2 | C/G:2 | G:2 | D7/G:2 | G:2 | Am/G:2 | D7:4"), style="chitarra", dyn=0.3, advance=False)
    n.theme("G5:.25 F#5:.25 E5:.25 D5:.25 B4:.5 G4:.5 | r:2 | A5:.25 G5:.25 F#5:.25 E5:.25 C5:.5 A4:.5 | r:2 | "
            "B5:.25 A5:.25 G5:.25 F#5:.25 D5:.5 B4:.5 | r:2 | C6:.25 B5:.25 A5:.25 G5:.25 F#5:.5 D5:.5 | r:2",
            inst="fl", vel=0.32, advance=True)
    # the village band: tune in the clarinet over the big guitar
    band = n.sprog("G:2 | Am7:1 D7:1 | G:2 | Am:1 D7:1 | G:2 | D/F#:1 G:1 | C:1 G/D:1 | G/B:1 D7:1")
    n.orch(band, style="chitarra", dyn=0.4, advance=False)
    n.theme("D5:.5 D5:.5 B4:.5 G4:.5 | A4:.5 B4:.5 C5:.5 A4:.5 | D5:.5 D5:.5 B4:.5 G4:.5 | A4:.5 C5:.5 B4:.5 A4:.5 | "
            "G4:.5 B4:.5 D5:.5 G5:.5 | F#5:.5 E5:.5 D5:.5 B4:.5 | C5:.5 E5:.5 D5:.5 B4:.5 | B4:.5 A4:.5 F#4:.5 G4:.5",
            inst="cl", vel=0.45, advance=True)
    n.add("tamb", [Ev(n.cursor - 16 + k * 1.0 + 0.5, 0.2, 60, 0.16) for k in range(16)])
    # verse 1 (the film's own melody)
    n.cue("chorus")
    n.chorus(ch[0], store="A", role="open", accomp="chitarra", dyn=0.6)
    n.chorus(ch[1], store="B", role="close", accomp="chitarra", dyn=0.6)
    n.chorus(ch[2], store="C", role="open", accomp="chitarra", dyn=0.62)
    n.chorus(ch[3], store="D", role="close", accomp="chitarra", dyn=0.64)
    # a dance for the band: the tune on oboe and flute
    n.cue("dance")
    for _ in range(2):
        n.orch(band, style="chitarra", dyn=0.45, advance=False)
        n.theme("D5:.5 D5:.5 B4:.5 G4:.5 | A4:.5 B4:.5 C5:.5 A4:.5 | D5:.5 D5:.5 B4:.5 G4:.5 | A4:.5 C5:.5 B4:.5 A4:.5 | "
                "G4:.5 B4:.5 D5:.5 G5:.5 | F#5:.5 E5:.5 D5:.5 B4:.5 | C5:.5 E5:.5 D5:.5 B4:.5 | B4:.5 A4:.5 F#4:.5 G4:.5",
                inst="ob" if _ == 0 else "fl", vel=0.42, transpose=0 if _ == 0 else 12, advance=True)
        n.add("tri", [Ev(n.cursor - 16, 0.5, 84, 0.24), Ev(n.cursor - 8, 0.5, 84, 0.22)])
    # the trio: D major, the women first, then the men, then all
    n.key_to("D").cue("trio")
    trio = n.sprog("D:2 | A7:2 | D:2 | A7:2 | G:2 | D/A:2 | E7:2 | A7:2")
    n.orch(trio, style="chitarra", dyn=0.4, advance=False)
    n.theme("F#5:.5 A5:.5 F#5:.5 D5:.5 | E5:.5 G5:.5 E5:.5 C#5:.5 | D5:.5 F#5:.5 A5:.5 D6:.5 | C#6:.5 B5:.5 A5:.5 G5:.5 | "
            "B5:.5 G5:.5 E5:.5 D5:.5 | A5:.5 F#5:.5 D5:.5 F#5:.5 | G#5:.5 B5:.5 E5:.5 G#5:.5 | A5:1 r:1",
            inst="fl", vel=0.36, advance=True)
    n.orch(trio, style="chitarra", dyn=0.45, advance=False)
    n.theme("F#5:.5 A5:.5 F#5:.5 D5:.5 | E5:.5 G5:.5 E5:.5 C#5:.5 | D5:.5 F#5:.5 A5:.5 D6:.5 | C#6:.5 B5:.5 A5:.5 G5:.5 | "
            "B5:.5 G5:.5 E5:.5 D5:.5 | A5:.5 F#5:.5 D5:.5 F#5:.5 | G#5:.5 B5:.5 E5:.5 G#5:.5 | A5:1 r:1",
            inst="ob", vel=0.4, transpose=-12, advance=True)
    n.orch(n.sprog("D:2 | A7:2 | D7:2 | G:1 D7:1"), style="chitarra", dyn=0.4)
    n.key_to("G")
    # verse 2: the village sees everything
    n.cue("verse2")
    n.chorus(ch[4], model="A", role="open", accomp="chitarra", dyn=0.6)
    n.chorus(ch[5], model="B", role="close", accomp="chitarra", dyn=0.62)
    n.chorus(ch[6], model="C", role="open", accomp="chitarra", dyn=0.66)
    n.chorus(ch[7], model="D", role="close", accomp="chitarra", dyn=0.7)
    n.chorus(ch[6], model="C", role="open", accomp="tutti", dyn=0.75)
    n.chorus(ch[7], model="D", role="climax", accomp="tutti", dyn=0.8)
    # a second dance, then verse 1 da capo
    for k in range(2):
        n.orch(band, style="chitarra", dyn=0.5, advance=False)
        n.theme(BAND_TUNE, inst="cl" if k == 0 else "vn1", vel=0.46, advance=True)
    n.chorus(ch[0], model="A", role="open", accomp="chitarra", dyn=0.6)
    n.chorus(ch[1], model="B", role="close", accomp="chitarra", dyn=0.6)
    n.chorus(ch[2], model="C", role="open", accomp="chitarra", dyn=0.65)
    n.chorus(ch[3], model="D", role="climax", accomp="tutti", dyn=0.78)
    n.orch(band, style="tutti", dyn=0.6)
    n.orch(band, style="chitarra", dyn=0.28)
    # the scene: Elena finds Marco; the market goes on, quietly
    n.cue("scene")
    n.event("enter", who="elena")
    n.event("enter", who="marco")
    n.recit(scene, chords=["I", "IV", "V7", "I", "vi", "ii6", "V7", "I"], base=0.5, dyn=0.22, accomp="chitarra",
            strike_end=False)
    n.orch(n.sprog("G:2 | D7:2"), style="pad", dyn=0.2)
    return n


def n2():
    """N. 2 Duetto dell'addio."""
    n = Num("N2", "Duetto dell'addio", "G", 72, (4, 4), location="village_farewell", act=1, scene=1)
    L = n.L()
    marco = [x for x in L if x.speaker == "marco"]
    elena = [x for x in L if x.speaker == "elena"]
    n.cue("start")
    n.orch(n.sprog("G:4 | D7:4"), style="arpeggio", dyn=0.3, melody=MARCO, melody_inst="cl")
    # Marco's stanza: the film's melody leads it
    n.stanza("marco", marco[0:4], "A:open B:close A':open B':close", style="andante", accomp="arpeggio",
             dyn=(0.4, 0.5))
    n.ritornello("A", inst="cl", dyn=0.3, bars=2)
    # Elena answers in his melody (her own first lines are the film's)
    n.stanza("elena", elena[0:4], "E:open F:close A':open B':close", style="andante", accomp="arpeggio",
             dyn=(0.4, 0.55))
    # the teasing: lighter, quicker
    n.tempo(104).meter(2, 4).cue("teasing")
    n.stanza("marco", marco[4:6], "G:open H:close", style="allegro", accomp="chitarra", dyn=(0.4, 0.45))
    n.stanza("elena", elena[4:6], "G':open H':close", style="allegro", accomp="chitarra", dyn=(0.42, 0.48))
    n.orch(n.sprog("G:2 | D7:2"), style="chitarra", dyn=0.35)
    n.stanza("marco", marco[4:6], "G':open H':close", style="allegro", accomp="chitarra", dyn=(0.45, 0.5))
    n.stanza("elena", elena[4:6], "G':open H'':climax", style="allegro", accomp="chitarra", dyn=(0.48, 0.58))
    n.orch(n.sprog("G:2 | C:1 D7:1 | G:2 | D7:2"), style="chitarra", dyn=0.4)
    # Elena's secret, aside: E minor, slower
    n.tempo(60).meter(4, 4).key_to("Em").cue("aside")
    n.stanza("elena", elena[6:10], "I:open J:close K:contrast L:close", style="cantabile", accomp="pad",
             dyn=(0.28, 0.36), disp_style="aside", accomp_kw={"sord": True})
    # together: his promise and her reply at once
    n.key_to("G").tempo(72).cue("a_due")
    n.together(lambda m: m.sing("marco", marco[0], model="A", role="open", accomp="arpeggio", dyn=0.5),
               lambda m: m.sing("elena", elena[0], model="E", role="open", accomp=None, dyn=0.5))
    n.together(lambda m: m.sing("marco", marco[1], model="B", role="close", accomp="arpeggio", dyn=0.55),
               lambda m: m.sing("elena", elena[1], model="F", role="close", accomp=None, dyn=0.55))
    n.together(lambda m: m.sing("marco", marco[2], model="A", role="open", accomp="arpeggio", dyn=0.6),
               lambda m: m.sing("elena", elena[2], model="E", role="open", accomp=None, dyn=0.6))
    n.together(lambda m: m.sing("marco", marco[3], model="B", role="climax", contour="high", accomp="tutti", dyn=0.7),
               lambda m: m.sing("elena", elena[3], model="F", role="climax", contour="high", accomp=None, dyn=0.7))
    n.orch(n.sprog("G:4 | C:2 D7:2 | G:4"), style="arpeggio", dyn=0.45)
    # the cabaletta a due: quicker, both voices, twice
    n.tempo(116).meter(2, 4).cue("cabaletta")
    for rep in range(2):
        n.together(lambda m: m.sing("marco", marco[0], model="G", role="open", style="allegro", accomp="chitarra", dyn=0.6),
                   lambda m: m.sing("elena", elena[0], model="G", role="open", style="allegro", accomp=None, dyn=0.6))
        n.together(lambda m: m.sing("marco", marco[1], model="H", role="close", style="allegro", accomp="chitarra", dyn=0.62),
                   lambda m: m.sing("elena", elena[1], model="H", role="close", style="allegro", accomp=None, dyn=0.62))
        n.together(lambda m: m.sing("marco", marco[2], model="G", role="open", style="allegro", accomp="chitarra", dyn=0.66),
                   lambda m: m.sing("elena", elena[2], model="G", role="open", style="allegro", accomp=None, dyn=0.66))
        n.together(lambda m: m.sing("marco", marco[3], model="H", role="climax", style="allegro", accomp="tutti", dyn=0.75),
                   lambda m: m.sing("elena", elena[3], model="H", role="climax", style="allegro", accomp=None, dyn=0.75))
        n.orch(n.sprog("G:2 | C:1 D7:1 | G:2 | D7:2"), style="tutti" if rep else "chitarra", dyn=0.55)
    n.tempo(66).meter(4, 4)
    # farewell: Marco's motif hangs, unresolved
    n.cue("addio")
    n.recit([marco[6], elena[10]], chords=["V7", "V7/V"], base=0.75, dyn=0.25, strike_end=False)
    n.sing("marco", marco[7], role="open", cadence="none", accomp="pad", dyn=0.35, style="andante")
    n.orch(n.sprog("D7:4"), style="pad", dyn=0.18, melody=MARCO, melody_inst="cl")
    n.event("exit", who="marco")
    n.pause(1.5)
    return n


def n3():
    """N. 3 Aria di Elena, "Resta la strada"."""
    n = Num("N3", 'Aria di Elena, "Resta la strada"', "G", 54, (3, 4), location="village_road", act=1, scene=1)
    L = n.L("elena")
    n.cue("start")
    n.orch(n.sprog("Em:3 | Am:3 | B7:3 | Em:3"), style="arpeggio", dyn=0.25)
    n.stanza("elena", L[0:4], "A:open B:close A':open B':close", style="cantabile", accomp="arpeggio",
             dyn=(0.32, 0.45))
    n.ritornello("A", inst="ob", dyn=0.3)
    n.key_to("Em")
    n.stanza("elena", L[4:8], "C:contrast D:open A'':climax B'':close", style="cantabile", accomp="arpeggio",
             dyn=(0.42, 0.62), climax_accomp="pad")
    n.key_to("G")
    n.ritornello("C", inst="cl", dyn=0.3)
    n.key_to("G")
    n.stanza("elena", L[0:4], "A':open B':close A':open B':close", style="cantabile", accomp="arpeggio",
             dyn=(0.3, 0.42))
    n.coda("elena", L[6:8], ["A", "B"], style="cantabile", accomp="arpeggio", dyn=(0.45, 0.65), repeats=2)
    # the coda: the white road again, ending on Marco's hanging C
    n.cue("coda")
    n.sing("elena", L[8], model="A", role="open", cadence="none", accomp="pad", dyn=0.28, style="cantabile")
    n.orch(n.sprog("D7:3 | D7:3"), style="pad", dyn=0.15, melody=MARCO.replace(":.5", ":.75").replace(":1.5", ":2.25"),
           melody_inst="cl")
    n.event("letters")
    n.pause(2.0)
    return n


def interlude_1_2():
    """Two springs pass: the road empties, the bells, B minor."""
    n = Num("I12", "Interludio: due primavere", "G", 58, (4, 4), location="interlude_seasons", act=1, scene=2)
    n.orch(n.sprog("G:4 | Em:4 | C:4 | D7:4"), style="arpeggio", dyn=0.25, melody=MARCO, melody_inst="ob")
    n.add("tubbells", [Ev(n.cursor - 12, 4.0, 67, 0.2), Ev(n.cursor - 8, 4.0, 62, 0.18)])
    n.key_to("Bm")
    n.orch(n.sprog("C:4 | Am:4 | D7:4 | G:4"), style="arpeggio", dyn=0.2, melody="D4:.5 B4:1.5 A4:.5 C5:1.5 r:12",
           melody_inst="fl")
    n.orch(n.sprog("Bm:4 | G:4 | Em/G:4 | F#7:4"), style="pad", dyn=0.22)
    n.orch(n.sprog("Bm:4 | Em:4 | F#7:4 | Bm:4"), style="arpeggio", dyn=0.18)
    return n


def r1():
    """Recitativo: two springs, no letter; the mother; Vittorio's proposal."""
    n = Num("R1", "Recitativo", "Bm", 72, (4, 4), location="parlour", act=1, scene=2)
    n.cue("start")
    n.event("enter", who="madre")
    n.recit(n.lib.items, chords=["i", "VI", "iv", "V7", "i", "III", "VI", "iio6", "V7", "III", "V7/III"],
            base=0.5, dyn=0.25)
    return n


def n4():
    """N. 4 Arioso della Madre: B minor opening into D major."""
    n = Num("N4", 'Arioso della Madre, "Figlia mia, la vita è questa"', "Bm", 60, (4, 4), location="parlour",
            act=1, scene=2)
    L = n.L("madre")
    n.cue("start")
    n.orch(n.sprog("Bm:4 | F#7:4"), style="arpeggio", dyn=0.25)
    n.stanza("madre", L[0:4], "A:open B:close A':open B':close", style="andante", accomp="arpeggio",
             dyn=(0.35, 0.45))
    n.key_to("D").cue("hope")
    n.stanza("madre", L[4:8], "C:open D:close C':open D':close", style="andante", accomp="arpeggio",
             dyn=(0.4, 0.52))
    n.key_to("Bm")
    n.stanza("madre", L[8:10], "E:contrast F:open", style="andante", accomp="pad", dyn=(0.4, 0.45))
    n.key_to("D")
    # the film's two closing lines, then again for the cadence
    n.stanza("madre", L[10:12], "G:open H:close", style="andante", accomp="arpeggio", dyn=(0.5, 0.55))
    n.coda("madre", L[10:12], ["G", "H"], style="andante", accomp="arpeggio", dyn=(0.5, 0.62), repeats=2)
    n.orch(n.sprog("D:4 | G:2 A7:2 | D:4"), style="arpeggio", dyn=0.3)
    return n


def n5():
    """N. 5 Aria di Elena, "Ho smesso d'aspettare": cantabile, a cabaletta on her 'sì', Vittorio enters."""
    n = Num("N5", 'Aria di Elena, "Ho smesso d\'aspettare"', "D", 58, (4, 4), location="parlour", act=1, scene=2)
    L = n.L("elena")
    vit = n.L("vittorio")
    n.cue("start")
    n.orch(n.sprog("D:4 | G/D:2 A7/D:2"), style="arpeggio", dyn=0.28)
    n.stanza("elena", L[0:4], "A:open B:close A':open B':close", style="cantabile", accomp="arpeggio",
             dyn=(0.35, 0.48))
    n.stanza("elena", L[4:8], "C:contrast D:open A'':climax B'':close", style="cantabile", accomp="arpeggio",
             dyn=(0.42, 0.6), climax_accomp="pad")
    n.coda("elena", L[6:8], ["A", "B"], style="cantabile", accomp="arpeggio", dyn=(0.5, 0.66), repeats=1)
    # cabaletta: 'E se mi chiede «Vuoi?», risponderò di sì' (the film's melody), twice
    n.tempo(96).cue("cabaletta")
    n.orch(n.sprog("D:4 | A7:4"), style="chitarra", dyn=0.4)
    for rep in range(2):
        n.stanza("elena", L[8:12], ("E:open F:close G:open H:close" if rep == 0 else
                                     "E':open F':close G':open H'':climax"), style="allegro", accomp="chitarra",
                 dyn=(0.5, 0.75) if rep else (0.45, 0.6))
        n.orch(n.sprog("D:4 | G:2 A7:2 | D:4"), style="tutti" if rep else "chitarra", dyn=0.55 if rep else 0.4)
    n.cue("si_hope")
    # Vittorio: a different world (A-flat)
    n.key_to("Ab").tempo(72).cue("vittorio")
    n.event("enter", who="vittorio")
    n.recit(vit, chords=["I", "IV", "V7"], base=0.5, dyn=0.22, strike_end=False)
    n.orch(n.sprog("Abmaj7:4 | Eb7:4"), style="pad", dyn=0.18, sord=True)
    return n


def n6():
    """N. 6 Le nozze e Coro nuziale: the organ, the vow, the chorus (the film's), the dance, the cooling."""
    n = Num("N6", 'Le nozze e Coro nuziale, "Suonin le campane a festa"', "Ab", 60, (4, 4), location="church_vow",
            act=1, scene=2)
    n.cue("start")
    n.event("location", where="church_vow")
    n.add("churchbell", [Ev(0.0, 6.0, 55, 0.4), Ev(4.0, 6.0, 52, 0.35), Ev(8.0, 6.0, 55, 0.35)])
    n.orch(n.sprog("Ab:4 | Db/Ab:4 | Ab:4 | Eb7/Ab:4"), style="chorale", dyn=0.32, family="organ")
    n.orch(n.sprog("Fm:4 | Db:4 | Eb7:4 | Ab:4"), style="chorale", dyn=0.36, family="organ")
    n.orch(n.sprog("Db:4 | Bbm:4 | Eb7:4 | Ab:4"), style="chorale", dyn=0.4, family="organ")
    n.orch(n.sprog("Ab/C:4 | Db:2 Eb7:2 | Ab:8"), style="chorale", dyn=0.34, family="organ")
    # the vow and her 'Sì': the film's music exactly
    n.cue("vow")
    n.island("s02", 24.0, 35.5)
    n.cue("wedding")
    n.event("location", where="church_wedding")
    # the chorus, as in the film
    n.island("s02", 35.5, 83.5)
    n.cue("dance")
    # the dance: the wedding melody for the orchestra, then the chorus again with every bell
    n.orch(n.sprog(bars_of(WEDDING_HARM, 1, 8)), style="furlana", dyn=0.45, advance=False)
    n.theme(bars_of(WEDDING, 1, 8), inst="cl", vel=0.45, advance=False)
    n.theme(bars_of(WEDDING, 1, 8), inst="fl", vel=0.35, transpose=12, advance=True)
    n.orch(n.sprog(bars_of(WEDDING_HARM, 9, 16)), style="furlana", dyn=0.5, advance=False)
    n.theme(bars_of(WEDDING, 9, 16), inst="ob", vel=0.5, advance=False)
    n.theme(bars_of(WEDDING, 9, 16), inst="vn1", vel=0.45, advance=True)
    n.orch(n.sprog(bars_of(WEDDING_HARM, 1, 8)), style="furlana", dyn=0.5, advance=False)
    n.theme(bars_of(WEDDING, 1, 8), inst="vn1", vel=0.5, advance=False)
    n.theme(bars_of(WEDDING, 1, 8), inst="ob", vel=0.4, advance=True)
    n.orch(n.sprog(bars_of(WEDDING_HARM, 9, 16)), style="tutti", dyn=0.6, advance=False)
    n.theme(bars_of(WEDDING, 9, 16), inst="tpt", vel=0.5, advance=False)
    n.theme(bars_of(WEDDING, 9, 16), inst="vn1", vel=0.55, advance=True)
    n.cue("refrain2")
    n.island("s02", 35.5, 83.5)
    n.add("churchbell", [Ev(n.cursor - 24 + 3 * k, 5.0, (55, 50)[k % 2], 0.4) for k in range(8)])
    n.add("tubbells", [Ev(n.cursor - 24 + 1.5 * k, 2.0, (74, 69, 66, 62)[k % 4], 0.3) for k in range(16)])
    # the ballabile: the village dances (a furlana, a waltz, a galop), the bells still ringing
    n.cue("ballabile")
    n.meter(6, 8).tempo(104).key_to("D")
    for k in range(2):
        n.orch(n.sprog(bars_of(WEDDING_HARM, 1, 8)), style="furlana", dyn=0.5, advance=False)
        n.theme(bars_of(WEDDING, 1, 8), inst="fl" if k == 0 else "cl", vel=0.45, transpose=12 if k == 0 else 0,
                advance=True)
    n.meter(3, 4).tempo(138).key_to("G").cue("waltz")
    waltz = n.sprog("G:3 | D7:3 | D7:3 | G:3 | G:3 | C:3 | D7:3 | G:3")
    tune = ("B4:1.5 C5:.5 D5:1 | C5:1.5 B4:.5 A4:1 | F#4:1.5 G4:.5 A4:1 | B4:3 | "
            "D5:1.5 E5:.5 F#5:1 | G5:1.5 E5:.5 C5:1 | B4:1 A4:1 F#4:1 | G4:3")
    for k in range(3):
        n.orch(waltz, style="waltz", dyn=0.45, advance=False)
        n.theme(tune, inst=("vn1", "ob", "fl")[k], vel=0.44, transpose=(0, 0, 12)[k], advance=True)
    n.meter(2, 4).tempo(152).key_to("D").cue("galop")
    galop = n.sprog("D:2 | A7:2 | D:2 | A7:2 | D:2 | G:2 | A7:2 | D:2")
    gtune = ("A5:.5 F#5:.5 D5:.5 F#5:.5 | G5:.5 E5:.5 C#5:.5 E5:.5 | F#5:.5 D5:.5 A4:.5 D5:.5 | E5:1 C#5:1 | "
             "A5:.5 F#5:.5 D5:.5 F#5:.5 | B5:.5 G5:.5 D5:.5 G5:.5 | A5:.5 G5:.5 E5:.5 C#5:.5 | D5:1 r:1")
    for k in range(4):
        n.orch(galop, style="march" if k % 2 else "chitarra", dyn=0.55 + 0.05 * k, advance=False)
        n.theme(gtune, inst=("cl", "fl", "vn1", "tpt")[k], vel=0.5, transpose=(0, 12, 0, 0)[k], advance=True)
    n.add("cym", [Ev(n.cursor - 2.0, 1.5, 60, 0.4)])
    n.orch(n.sprog("D:2 | A7:2 | D:4"), style="tutti", dyn=0.75)
    # it cools
    n.cue("cooling")
    n.event("location", where="church_cooling")
    n.meter(6, 8).tempo(64)
    n.island("s02", 83.5, 98.0)
    n.key_to("Dm").meter(4, 4).tempo(50)
    n.orch(n.sprog("Dm:4 | Gm/D:4 | A7/C#:4 | Dm:4"), style="pad", dyn=0.18, sord=True, advance=False)
    n.theme("A5:2 F5:1 D5:1 | Bb5:2 G5:1 D5:1 | E5:2 C#5:1 A4:1 | D5:4", inst="celesta", vel=0.3, advance=True)
    n.pause(1.5)
    return n


def interlude_2_3():
    """Three years: Verona, autumn. A cold house."""
    n = Num("I23", "Interludio: Verona", "Dm", 56, (4, 4), location="interlude_verona", act=1, scene=3)
    n.orch(n.sprog("Dm:4 | Bb:4 | Gm/Bb:4 | A7:4"), style="tremolo", dyn=0.2, low=False)
    n.orch(n.sprog("Dm:4 | Gm:4 | E7:4 | A7:4"), style="tremolo", dyn=0.24, low=True)
    n.orch(n.sprog("Abmaj7:4 | Fm7:4"), style="pad", dyn=0.18, sord=True)
    n.theme("C4:1.5 Bb3:.5 Ab3:1 G3:1", inst="tbn", vel=0.24, origin=n.cursor - 8.0)
    n.orch(n.sprog("Db:4 | C7:4"), style="pad", dyn=0.16, sord=True)
    n.key_to("F")
    n.orch(n.sprog("C7:4 | F:4"), style="lullaby", dyn=0.18)
    return n


def n7():
    """N. 7 Ninna nanna: F major, 6/8; Tommaso's note at the end."""
    n = Num("N7", 'Ninna nanna di Elena, "Dormi, Tommaso"', "F", 44, (6, 8), location="verona_night", act=1,
            scene=3)
    L = n.L("elena")
    n.cue("start")
    n.event("enter", who="tommaso")
    n.orch(n.sprog("F:3 | C7:3 | F:3 | C7:3"), style="lullaby", dyn=0.22)
    n.stanza("elena", L[0:4], "A:open B:close A':open B':close", style="compound", accomp="lullaby",
             dyn=(0.28, 0.38), disp_style="lullaby")
    n.ritornello("A", inst="cl", dyn=0.24, accomp="lullaby")
    n.key_to("Dm")
    n.stanza("elena", L[4:8], "C:contrast D:open A'':climax B'':close", style="compound", accomp="lullaby",
             dyn=(0.32, 0.5), disp_style="lullaby")
    n.key_to("F")
    n.ritornello("B", inst="ob", dyn=0.22, accomp="lullaby")
    n.stanza("elena", L[8:12], "A':open B':close A'':climax B'':close", style="compound", accomp="lullaby",
             dyn=(0.3, 0.42), disp_style="lullaby")
    n.ritornello("A", inst="fl", dyn=0.2, accomp="lullaby")
    n.stanza("elena", L[0:4], "A':open B':close A':open B':close", style="compound", accomp="lullaby",
             dyn=(0.26, 0.32), disp_style="lullaby")
    n.cue("coda")
    n.sing("elena", L[0], model="A", role="open", accomp="lullaby", dyn=0.22, style="compound",
           disp_style="lullaby")
    n.sing("elena", L[0], model="A", role="close", accomp="lullaby", dyn=0.18, style="compound",
           disp_style="lullaby")
    n.cue("tone")
    n.tommaso(9.0, vel=0.27)
    n.orch(n.sprog("F:3 | Bb/F:3 | F:3"), style="lullaby", dyn=0.14)
    return n


def n8():
    """N. 8 Scena e terzetto: Vittorio, the blow (the film's), the child's note alone, her resolve."""
    n = Num("N8", "Scena e terzetto", "Ebm", 72, (4, 4), location="verona_night", act=1, scene=3)
    vit = n.L("vittorio")
    el = n.L("elena")
    n.cue("start")
    n.event("enter", who="vittorio")
    n.orch(n.sprog("Ebm:4 | Cb:4 | Abm:4 | Bb7:4"), style="tremolo", dyn=0.3)
    n.orch(n.sprog("Ebm:2 | Bbm/Db:2 | Cb:2 | Bb7:2"), style="chorale", dyn=0.42, family="brass")
    n.add("timp", [Ev(n.cursor - 8.0 + k * 0.25, 0.25, 46, 0.25 + 0.03 * k) for k in range(16)])
    items = [x for x in n.lib.items if not (hasattr(x, "speaker") and x.it.startswith(("Basta", "Non qui",
                                                                                       "Prenderò", "e andrò")))]
    dialogue = [x for x in items if hasattr(x, "speaker")][:9]
    n.recit(dialogue, chords=["i", "VI", "iv", "V7", "i", "iio6", "V7", "VI", "V7"], base=0.5, dyn=0.32,
            accomp="tremolo", strike_end=False)
    n.cue("blow")
    n.island("s03", 39.0, 45.0)
    n.cue("resolve")
    n.key_to("Dm").tempo(66)
    basta = [x for x in n.lib.items if hasattr(x, "speaker") and x.it.startswith(("Basta", "Non qui"))]
    for x in basta:
        n.sing("elena", x, role="close", accomp="pad", dyn=0.4, style="andante")
    n.tempo(112).cue("stretta")
    rest = [x for x in n.lib.items if hasattr(x, "speaker") and x.it.startswith(("Prenderò", "e andrò"))]
    n.stanza("elena", rest, "S:open T:climax", style="allegro", accomp="tremolo", dyn=(0.6, 0.8))
    n.orch(n.sprog("Dm:2 | A7:2"), style="tremolo", dyn=0.6)
    n.stanza("elena", rest, "S':open T'':climax", style="allegro", accomp="tutti", dyn=(0.7, 0.9))
    n.stanza("elena", rest, "S':open T'':climax", style="allegro", accomp="tutti", dyn=(0.75, 0.95))
    n.orch(n.sprog("Dm:4 | Gm/D:2 A7/D:2 | Dm:4"), style="tutti", dyn=0.85)
    n.orch(n.sprog("Bb:2 | Gm:2 | A7:4 | Dm:4"), style="tutti", dyn=0.9)
    n.add("tamtam", [Ev(n.cursor - 4.0, 6.0, 40, 0.5)])
    n.event("curtain", state="down")
    n.pause(2.0)
    return n


ACT1 = [prologue, prelude1, n1, n2, n3, interlude_1_2, r1, n4, n5, n6, interlude_2_3, n7, n8]
