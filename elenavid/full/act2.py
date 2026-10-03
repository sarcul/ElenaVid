"""Act II of the full opera: Fuga e tenerezza."""
from __future__ import annotations

from ..compose import textures as tx
from ..compose.themes import VITTORIO, VITTORIO_HARM, MARCO, DAVIDE_ARIA, DAVIDE_ARIA_HARM
from ..notation import Ev, parse
from .act1 import bars_of
from .forms import Num

TRAIN = [(0.0, 0.25, 0, True), (0.25, 0.25, 1, False), (0.5, 0.25, 2, False), (0.75, 0.25, 1, False)]


def train(n, spec, dyn=0.4, origin=None):
    """The train in the cellos: semiquavers sul ponticello on root, fifth and octave."""
    p = n.sprog(spec, origin)
    evs = tx.ostinato(p, TRAIN, lo=40, hi=55, vel=0.18 + 0.5 * dyn)
    n.add("vc", evs, tech="pont")
    n.add("cb", tx.transpose([e for e in evs if e.art == ">"], -12), tech="pizz")
    return p


def prelude2():
    n = Num("P2", "Atto secondo: Preludio", "Am", 92, (4, 4), location="prelude", act=2)
    n.cue("start")
    p = train(n, "Am:4 | Am:4 | F:4 | E7:4 | Am:4 | Dm:4 | E7:4 | Am:4", dyn=0.3)
    n.orch(p, style="tremolo", dyn=0.22, low=False, advance=False)
    n.theme("E5:1 A5:1 C6:1.5 B5:.5 | A5:1 E5:1 F5:2 | D5:1 F5:1 A5:1.5 G#5:.5 | A5:4 | "
            "C6:1 B5:1 A5:1 G#5:1 | F5:1 E5:1 D5:2 | B4:1 D5:1 E5:1.5 G#4:.5 | A4:4",
            inst="ob", vel=0.4, advance=True)
    p = train(n, "F:4 | Dm:4 | Bb:4 | E7:4 | Am:4 | F:4 | E7:4 | E7:4", dyn=0.5)
    n.orch(p, style="tremolo", dyn=0.4, advance=False)
    n.theme("A4:1 C5:1 E5:1.5 D5:.5 | C5:1 A4:1 Bb4:2 | G4:1 Bb4:1 D5:1.5 C#5:.5 | E5:4 | "
            "C5:1 E5:1 A5:1.5 G#5:.5 | A5:1 E5:1 F5:2 | D5:1 B4:1 G#4:1.5 B4:.5 | E5:4",
            inst="vn1", vel=0.5, advance=True)
    # the bora: wind in the strings, the flight theme torn in the woodwind
    n.cue("bora")
    n.orch(n.sprog("Dm:4 | Bb:4 | Gm:4 | A7:4 | Dm:4 | Gm:4 | E7:4 | A7:4"), style="tremolo", dyn=0.5, advance=False)
    n.theme("D5:.5 F5:.5 A5:1 G5:.5 F5:.5 E5:1 | D5:.5 F5:.5 Bb5:1 A5:2 | G5:.5 Bb5:.5 D6:1 C#6:1 A5:1 | E5:4 | "
            "D6:1 A5:1 F5:1 D5:1 | Bb5:1 G5:1 E5:1 C#5:1 | E5:.5 G#5:.5 B5:1 D6:2 | C#6:4",
            inst="fl", vel=0.45, advance=False)
    n.theme("D4:2 A3:2 | Bb3:2 F3:2 | G3:2 D3:2 | A3:4 | D4:2 A3:2 | G3:2 Bb3:2 | E3:2 G#3:2 | A3:4",
            inst="tbn", vel=0.4, advance=True)
    n.add("timp", [Ev(n.cursor - 32 + 4 * k, 0.5, 50 if k % 2 == 0 else 45, 0.4) for k in range(8)])
    # far off, unchanged: his phrase in the horns, muted
    n.key_to("Ab").tempo(60).cue("shadow")
    n.orch(n.sprog(VITTORIO_HARM), style="pad", dyn=0.18, sord=True, advance=False)
    n.theme(VITTORIO, inst="hn", vel=0.28, advance=True, tech="mute")
    n.key_to("Am").tempo(100)
    p = train(n, "Am:4 | F:4 | Dm:4 | E7:4 | Am:4 | Dm:4 | E7:4 | Am:4", dyn=0.45)
    n.orch(p, style="tremolo", dyn=0.45, advance=False)
    n.theme("E5:1 A5:1 C6:1.5 B5:.5 | A5:1 E5:1 F5:2 | D5:1 F5:1 A5:1.5 G#5:.5 | A5:4 | "
            "C6:1 B5:1 A5:1 G#5:1 | F5:1 E5:1 D5:2 | B4:1 D5:1 E5:1.5 G#4:.5 | A4:4", inst="tpt", vel=0.48, advance=True)
    n.tempo(84)
    p = train(n, "Am:4 | Am:4 | Dm:4 | E7:4", dyn=0.2)
    n.orch(p, style="pad", dyn=0.18)
    n.event("curtain", state="up")
    return n


def n9():
    """N. 9 Aria della partenza: the railwayman, the aria (the film's), the cabaletta, the train."""
    n = Num("N9", 'Aria della partenza, "Porto la mia valigia"', "Am", 84, (4, 4), location="station", act=2,
            scene=1)
    fer = n.L("ferroviere")
    el = n.L("elena")
    n.cue("start")
    n.add("churchbell", [Ev(0.0, 3.0, 79, 0.15)])
    train(n, "Am:4 | E7:4", dyn=0.2)
    n.orch(n.sprog("Am:4 | E7:4"), style="pad", dyn=0.2)
    n.cue("call")
    n.sing("ferroviere", fer[0], role="open", accomp="pad", dyn=0.5, style="andante")
    n.cue("aria")
    n.stanza("elena", el[0:4], "A:open B:close C:open D:close", style="andante", accomp="tremolo",
             dyn=(0.4, 0.55))
    train(n, "Am:4 | F:4 | Dm:4 | E7:4", dyn=0.35)
    n.orch(n.sprog("Am:4 | F:4 | Dm:4 | E7:4"), style="pad", dyn=0.3, melody="A4:1 C5:1 E5:1.5 D5:.5 | C5:1 A4:1 Bb4:2 | "
           "G4:1 Bb4:1 D5:1.5 C#5:.5 | E5:4", melody_inst="ob")
    n.stanza("elena", el[0:4], "A':open B':close C':open D'':climax", style="andante", accomp="tremolo",
             dyn=(0.45, 0.65))
    # cabaletta in A major: this time it is she who goes
    n.orch(n.sprog("Am:4 | Dm:4 | E7:4 | Am:4"), style="tremolo", dyn=0.4, advance=False)
    train(n, "Am:4 | Dm:4 | E7:4 | Am:4", dyn=0.4)
    n.rest(16.0)
    n.sing("ferroviere", fer[0], role="close", accomp="tremolo", dyn=0.55, style="andante")
    n.key_to("A").tempo(120).cue("cabaletta")
    n.orch(n.sprog("A:4 | E7:4 | A:4 | E7:4 | F#m:4 | D:4 | E7:4 | E7:4"), style="chitarra", dyn=0.45, advance=False)
    n.theme("E5:1 A5:1 C#6:1.5 B5:.5 | A5:1 E5:1 F#5:2 | D5:1 F#5:1 A5:1.5 G#5:.5 | B5:4 | "
            "C#6:1 B5:1 A5:1 G#5:1 | F#5:1 E5:1 D5:2 | B4:1 D5:1 E5:1.5 G#5:.5 | A5:4", inst="cl", vel=0.45,
            advance=True)
    for rep in range(2):
        n.stanza("elena", el[4:8], ("E:open F:close G:open H:close" if rep == 0 else
                                     "E':open F':close G':open H'':climax"), style="allegro", accomp="chitarra",
                 dyn=(0.5, 0.65) if rep == 0 else (0.6, 0.8))
        n.orch(n.sprog("A:2 D:2 | A/E:2 E7:2 | A:4"), style="tutti" if rep else "chitarra", dyn=0.6 if rep else 0.45)
    n.coda("elena", el[6:8], ["G", "H"], style="allegro", accomp="tutti", dyn=(0.7, 0.85), repeats=2)
    n.orch(n.sprog("A:4 | D:2 E7:2 | A:4"), style="tutti", dyn=0.85)
    # the train pulls out
    n.cue("depart")
    n.tempo(100).tempo(168, ramp_over=16)
    p = train(n, "A:4 | A:4 | E7:4 | A:4", dyn=0.55)
    n.orch(p, style="tremolo", dyn=0.45, low=False)
    n.cue("whistle")
    p = train(n, "A:4 | A:4", dyn=0.3)
    n.orch(p, style="pad", dyn=0.18)
    return n


def interlude_journey():
    n = Num("I2J", "Interludio: il viaggio", "A", 120, (4, 4), location="journey_map", act=2, scene=1)
    p = train(n, "A:4 | F#m:4 | D:4 | E7:4 | A:4 | C#m:4 | D:4 | E7:4", dyn=0.3)
    n.orch(p, style="pad", dyn=0.25, advance=False)
    n.theme("E5:2 A5:2 | C#6:2 B5:1 A5:1 | F#5:2 A5:2 | E5:4 | E5:2 A5:2 | E6:2 C#6:1 A5:1 | B5:2 D6:2 | E6:4",
            inst="fl", vel=0.34, advance=True)
    p = train(n, "F#m:4 | D:4 | Bm:4 | E7:4 | C#m:4 | F#m:4 | D:4 | E7:4", dyn=0.35)
    n.orch(p, style="arpeggio", dyn=0.3, advance=False)
    n.theme("C#6:2 B5:1 A5:1 | F#5:2 A5:2 | B5:2 A5:1 F#5:1 | E5:4 | C#6:2 E6:2 | C#6:1 B5:1 A5:2 | "
            "F#5:1 A5:1 D6:2 | B5:4", inst="ob", vel=0.38, advance=True)
    n.tempo(70, ramp_over=8)
    n.key_to("Ab")
    p = train(n, "Ab:4 | Fm:4 | Db:4 | Eb7:4", dyn=0.15)
    n.orch(p, style="pad", dyn=0.14, sord=True)
    return n


def n10():
    """N. 10 L'incubo: the nocturne, Vittorio's first appearance (the film's), the waking."""
    n = Num("N10", "L'incubo", "Ab", 80, (4, 4), location="trieste_night", act=2, scene=2)
    vit = n.L("vittorio")
    el = n.L("elena")
    n.cue("start")
    n.orch(n.sprog("Ab:4 | Fm:4 | Db:4 | Eb7:4"), style="arpeggio", dyn=0.18, step=0.5)
    n.orch(n.sprog("Db:4 | Bbm:4 | Gb:4 | Eb7:4"), style="arpeggio", dyn=0.16, step=0.5, advance=False)
    n.theme("Eb5:2 Ab5:2 | F5:2 Db5:2 | Bb4:2 Gb5:2 | G5:4", inst="fl", vel=0.22, advance=True)
    n.orch(n.sprog("Ab:4 | Dbmaj7:4 | Bbm7:4 | Eb7:4"), style="pad", dyn=0.16, sord=True)
    n.orch(n.sprog("Fm:4 | Db:4 | Bbm:4 | C7:4"), style="arpeggio", dyn=0.18, advance=False)
    n.theme("C5:2 Eb5:2 | F5:2 Ab5:2 | Db5:2 F5:2 | E5:4", inst="cl", vel=0.26, advance=True)
    n.orch(n.sprog("Fm:4 | Bbm:4 | Eb7:4 | Ab:4"), style="pad", dyn=0.16, sord=True)
    n.cue("vision")
    n.event("vision", who="vittorio", state="on")
    for k, line in enumerate(vit):
        n.sing("vittorio", line, role="open" if k % 2 == 0 else "close", accomp="pad", dyn=0.42,
               disp_style="vision", pos="top", accomp_kw={"sord": True})
    n.orch(n.sprog("Ab:4 | Fm:4"), style="pad", dyn=0.18, sord=True)
    # she turns in her sleep: the orchestra's fear rises; his first line returns, closer
    n.orch(n.sprog("Fm:4 | Db:4 | Bbm:4 | C7:4"), style="tremolo", dyn=0.35, advance=False)
    n.add("timp", [Ev(n.cursor - 16 + k * 0.25, 0.25, 48, 0.12 + 0.02 * k) for k in range(64)])
    n.sing("vittorio", vit[0], role="open", accomp="pad", dyn=0.5, disp_style="vision", pos="top",
           accomp_kw={"sord": True})
    n.event("vision", who="vittorio", state="off")
    n.cue("wake")
    n.key_to("A")
    n.orch(n.sprog("A:2 | E7:2"), style="tremolo", dyn=0.4)
    n.recit(el, chords=["I", "V7"], base=0.5, dyn=0.3, strike_end=False)
    n.orch(n.sprog("A:4 | D/A:2 E7/A:2 | A:4"), style="pad", dyn=0.2)
    n.orch(n.sprog("F#m:4 | D:4 | E7:4 | A:4"), style="arpeggio", dyn=0.16)
    n.orch(n.sprog("A:4 | F#m:4 | Bm7:4 | E7:4 | A:8"), style="pad", dyn=0.14, sord=True, advance=False)
    n.theme("E5:2 C#5:2 | A4:2 F#5:2 | D5:2 B4:2 | E5:4 | A4:8", inst="fl", vel=0.2, advance=True)
    return n


def r2():
    """Recitativo e terzetto domestico: morning, Nives, Davide with the milk and a paper boat."""
    n = Num("R2", "Recitativo e Terzetto domestico", "F", 76, (4, 4), location="trieste_morning", act=2, scene=2)
    n.cue("start")
    n.cue("morning")
    n.orch(n.sprog("F:4 | C7:4 | F:4 | Bb:2 C7:2"), style="arpeggio", dyn=0.25, melody="C6:.5 A5:.5 F5:1 G5:.5 A5:.5 Bb5:1 | "
           "A5:2 G5:2 | C6:.5 A5:.5 F5:1 D5:.5 E5:.5 F5:1 | G5:4", melody_inst="fl")
    n.event("enter", who="nives")
    items = [x for x in n.lib.items]
    nives = [x for x in items if hasattr(x, "speaker") and x.speaker == "nives"]
    dav = [x for x in items if hasattr(x, "speaker") and x.speaker == "davide"]
    n.recit(nives, chords=["I", "IV", "V7"], base=0.5, dyn=0.25, strike_end=False)
    n.event("enter", who="davide")
    n.cue("davide")
    n.sing("davide", dav[0], role="open", accomp="chitarra", dyn=0.42, style="andante")
    n.tommaso(8.0, vel=0.26)
    n.orch(n.sprog("F:4 | C7:4"), style="pad", dyn=0.18)
    n.sing("davide", dav[1], role="close", accomp="chitarra", dyn=0.45, style="andante")
    # the paper boat sails: a little tune for the boy
    n.meter(6, 8).tempo(84)
    n.orch(n.sprog("F:3 | C7:3 | F:3 | C7:3 | Bb:3 | F:3 | C7:3 | F:3"), style="barcarolle", dyn=0.24, advance=False)
    n.theme("C6:1 A5:.5 F5:1 A5:.5 | G5:1 E5:.5 C5:1.5 | A5:1 C6:.5 F6:1 E6:.5 | D6:3 | "
            "D6:1 Bb5:.5 F5:1 D6:.5 | C6:1 A5:.5 F5:1.5 | G5:1 Bb5:.5 E5:1 G5:.5 | F5:3", inst="fl", vel=0.3, advance=True)
    n.orch(n.sprog("F:3 | C7:3 | F:3 | C7:3 | Bb:3 | F:3 | C7:3 | F:3"), style="barcarolle", dyn=0.22, advance=False)
    n.theme("C6:1 A5:.5 F5:1 A5:.5 | G5:1 E5:.5 C5:1.5 | A5:1 C6:.5 F6:1 E6:.5 | D6:3 | "
            "D6:1 Bb5:.5 F5:1 D6:.5 | C6:1 A5:.5 F5:1.5 | G5:1 Bb5:.5 E5:1 G5:.5 | F5:3", inst="cl", vel=0.28, advance=True)
    n.tommaso(6.0, vel=0.24)
    n.meter(4, 4).tempo(76)
    n.orch(n.sprog("F:2 Bb:2 | C7:2 F:2"), style="arpeggio", dyn=0.25)
    return n


def n11():
    """N. 11 Aria di Davide: F major, plain, a home (the film's tune)."""
    n = Num("N11", 'Aria di Davide, "Non conosco le parole"', "F", 56, (4, 4), location="trieste_morning", act=2,
            scene=2)
    L = n.L("davide")
    n.cue("start")
    n.orch(n.sprog(DAVIDE_ARIA_HARM), style="pad", dyn=0.25, advance=False)
    n.theme(DAVIDE_ARIA, inst="vc", vel=0.38, advance=True)
    n.stanza("davide", L[0:4], "A:open B:close A':open B':close", style="andante", accomp="arpeggio",
             dyn=(0.4, 0.5))
    n.ritornello("A", inst="cl", dyn=0.3, transpose=12)
    n.stanza("davide", L[4:8], "C:contrast D:open A'':climax B'':close", style="andante", accomp="arpeggio",
             dyn=(0.42, 0.6))
    n.ritornello("B", inst="hn", dyn=0.3, transpose=0)
    n.stanza("davide", L[8:12], "E:open F:close A':open B'':climax", style="andante", accomp="arpeggio",
             dyn=(0.45, 0.65))
    n.ritornello("A", inst="vn1", dyn=0.32, transpose=12)
    n.stanza("davide", L[0:4], "A':open B':close A':open B':close", style="andante", accomp="arpeggio",
             dyn=(0.38, 0.46))
    n.coda("davide", L[10:12], ["A", "B"], style="andante", accomp="arpeggio", dyn=(0.5, 0.62), repeats=2)
    n.orch(n.sprog("F:4 | Bb:2 C7:2 | F:4"), style="arpeggio", dyn=0.3)
    return n


def n12():
    """N. 12 Duetto d'amore, "Piano, come la neve"."""
    n = Num("N12", 'Duetto d\'amore, "Piano, come la neve"', "F", 60, (4, 4), location="trieste_morning", act=2,
            scene=2)
    el = n.L("elena")
    dav = n.L("davide")
    both = n.L("elena+davide")
    n.cue("start")
    n.orch(n.sprog("F:4 | Dm:4 | Bb:4 | C7:4"), style="arpeggio", dyn=0.2)
    n.sing("elena", el[0], role="open", accomp="pad", dyn=0.32, style="andante")
    n.sing("davide", dav[0], role="close", accomp="pad", dyn=0.34, style="andante")
    n.sing("elena", el[1], role="close", accomp="pad", dyn=0.36, style="andante")
    n.orch(n.sprog("F:4 | C7:4"), style="arpeggio", dyn=0.25)
    n.cue("duet")
    # she begins it (the film's tune), he answers, then both
    n.stanza("elena", both[0:4], "A:open B:close A':open B':close", style="andante", accomp="arpeggio",
             dyn=(0.38, 0.48))
    n.stanza("davide", both[4:8], "C:contrast D:open A'':climax B'':close", style="andante", accomp="arpeggio",
             dyn=(0.4, 0.55))
    n.ritornello("A", inst="vn_solo", dyn=0.3, transpose=12)
    for k, line in enumerate(both):
        mdl = ("A", "B", "A", "B", "C", "D", "A", "B")[k]
        n.duet("elena", "davide", line, interval=-3, model=mdl,
               role=("open", "close", "open", "close", "contrast", "open", "climax", "close")[k],
               accomp="arpeggio", dyn=0.42 + 0.03 * k, contour="high" if k == 6 else "arch")
    n.cue("coda")
    for line, mdl in ((both[6], "A"), (both[7], "B")):
        n.duet("elena", "davide", line, interval=-3, model=mdl, role="close", accomp="pad", dyn=0.3)
    n.tommaso(8.0, vel=0.25)
    n.orch(n.sprog("F:4 | Dm7:2 C7:2 | C7:4 | F:4 | Dm:4 | Bb:2 F/A:2 | Gm7:2 C7:2 | F:4"), style="arpeggio", dyn=0.2,
           advance=False)
    n.theme("C5:1 A4:.5 C5:.5 F5:1.5 E5:.5 | D5:1 C5:1 C5:2 | Bb4:1 G4:.5 Bb4:.5 E5:1.5 D5:.5 | C5:4 | "
            "A5:1 G5:.5 F5:.5 E5:1.5 D5:.5 | C5:1 Bb4:1 A4:2 | G4:1 A4:.5 Bb4:.5 C5:1 E4:1 | F4:4",
            inst="vc_solo", vel=0.32, transpose=-12, advance=True, tech="espr")
    n.orch(n.sprog("F:4 | Bb/F:4 | F:4"), style="arpeggio", dyn=0.16)
    return n


def interlude_sea():
    n = Num("I2S", "Interludio: il mare", "G", 66, (6, 8), location="interlude_sea", act=2, scene=3)
    n.orch(n.sprog("G:3 | C:3 | G:3 | D7:3 | G:3 | Em:3 | Am:3 | D7:3"), style="barcarolle", dyn=0.24, advance=False)
    n.theme("D5:1.5 B4:1.5 | C5:1.5 E5:1.5 | D5:1 B4:.5 G4:1.5 | A4:3 | D5:1.5 G5:1.5 | E5:1.5 C5:1.5 | "
            "A4:1 C5:.5 E5:1.5 | D5:3", inst="cl", vel=0.32, advance=True)
    n.orch(n.sprog("Em:3 | C:3 | Am:3 | B7:3 | G:3 | C:3 | Am7:3 | D7:3"), style="barcarolle", dyn=0.28, advance=False)
    n.theme("B4:1.5 E5:1.5 | G5:1 F#5:.5 E5:1.5 | C5:1.5 E5:1.5 | D#5:3 | D5:1.5 G5:1.5 | E5:1 D5:.5 C5:1.5 | "
            "A4:1 C5:.5 E5:1.5 | D5:3", inst="ob", vel=0.32, advance=True)
    # fishermen far off, humming (bocca chiusa): the sea at the end of the street
    hum = n.sprog("G:3 | C:3 | G:3 | D7:3 | Em:3 | C:3 | Am:3 | D7:3")
    n.orch(hum, style="barcarolle", dyn=0.18, advance=False)
    tune = parse("D5:1.5 B4:1.5 | C5:1.5 E5:1.5 | D5:1 B4:.5 G4:1.5 | A4:3 | B4:1.5 G4:1.5 | A4:1.5 C5:1.5 | "
                 "B4:1 G4:.5 E4:1.5 | F#4:3", origin=n.cursor, vel=0.22)
    for e in tune:
        e.lyric = "a" if e is tune[0] else "_"
        e.tags["style"] = "chorus"
    from ..compose.choral import harmonize
    A, T, B = harmonize(tune, hum, a_rng=(55, 70), t_rng=(48, 64), b_rng=(41, 57))
    for inst, evs in (("ch_s", tune), ("ch_a", A), ("ch_t", T), ("ch_b", B)):
        for e in evs:
            e.vel = 0.18
            e.tags["style"] = "chorus"
            e.tags["offstage"] = True
        n.add(inst, evs, voice="chorus_offstage")
    n.rest(24.0)
    n.meter(4, 4)
    n.orch(n.sprog("D7:4"), style="pad", dyn=0.16, melody=MARCO, melody_inst="cl")
    n.orch(n.sprog("G:4 | D7:4"), style="arpeggio", dyn=0.18)
    return n


def n13():
    """N. 13 Scena e Duetto della confessione: the street; Marco; her confession."""
    n = Num("N13", "Scena e Duetto della confessione", "G", 88, (4, 4), location="trieste_street", act=2, scene=3)
    items = [x for x in n.lib.items if hasattr(x, "speaker")]
    n.cue("start")
    n.meter(6, 8).tempo(66)
    n.orch(n.sprog("G:3 | C:3 | G:3 | D7:3 | G:3 | Em:3 | C:3 | D7:3"), style="barcarolle", dyn=0.22, advance=False)
    n.theme("D5:1.5 B4:1.5 | C5:1.5 E5:1.5 | D5:1 B4:.5 G4:1.5 | A4:3 | D5:1.5 G5:1.5 | E5:1.5 C5:1.5 | "
            "A4:1 C5:.5 E5:1.5 | D5:3", inst="cl", vel=0.28, advance=True)
    n.meter(4, 4).tempo(88)
    n.cue("meet")
    n.orch(n.sprog("G:2 | Eb/G:2"), style="tremolo", dyn=0.5)
    n.event("enter", who="marco")
    # 'Elena? ... Elena!' / 'Marco...' (the film's), then the exchange
    for x in items[:3]:
        sp = x.speaker
        n.sing(sp, x, role="open", accomp="pad", dyn=0.4, style="andante", cadence="none")
    n.recit(items[3:7], chords=["I", "vi", "IV", "V7"], base=0.5, dyn=0.28, strike_end=False)
    # her confession: an arioso in E minor
    n.key_to("Em").tempo(66).cue("confession")
    conf = items[7:15]
    n.orch(n.sprog("Em:4 | B7:4"), style="pad", dyn=0.2)
    n.stanza("elena", conf, "A:open B:close C:open D:close E:contrast F:open G:climax H:close",
             style="andante", accomp="pad", dyn=(0.32, 0.5), accomp_kw={"sord": True})
    n.orch(n.sprog("Em:4 | Am:4 | B7:4 | Em:4"), style="pad", dyn=0.24, advance=False)
    n.theme("B4:2 E5:2 | C5:2 A4:2 | D#5:2 F#5:2 | E5:4", inst="cl", vel=0.3, advance=True)
    n.stanza("elena", conf[4:8], "E':contrast F':open G'':climax H':close", style="andante", accomp="pad",
             dyn=(0.4, 0.58), accomp_kw={"sord": True})
    n.key_to("G").tempo(80)
    n.stanza("marco", items[15:17], "I:open J:close", style="andante", accomp="arpeggio", dyn=(0.42, 0.5))
    n.stanza("marco", items[15:17], "I':open J'':climax", style="andante", accomp="arpeggio", dyn=(0.5, 0.6))
    n.ritornello("I", inst="cl", dyn=0.3)
    n.cue("friends")
    n.recit(items[17:19], chords=["I", "V7"], base=0.6, dyn=0.25, strike_end=False)
    n.orch(n.sprog("G:4 | C:2 D7:2 | G:4"), style="arpeggio", dyn=0.25)
    return n


def n14():
    """N. 14 Duetto, "Domani, alla stessa ora": the asides; curtain on D7."""
    n = Num("N14", 'Duetto, "Domani, alla stessa ora"', "G", 88, (4, 4), location="trieste_street", act=2, scene=3)
    both = n.L("elena+marco")
    n.cue("start")
    n.cue("domani")
    n.orch(n.sprog("G:4 | D7:4"), style="chitarra", dyn=0.3)
    for rep in range(2):
        for k, line in enumerate(both[0:4]):
            mdl = ("A", "B", "A", "B")[k] if rep or k >= 2 else None
            role = ("open", "close", "open", "close" if rep == 0 else "climax")[k]
            if mdl is None:
                n.duet("elena", "marco", line, interval=-5, store=("A", "B")[k], role=role, accomp="chitarra",
                       dyn=0.45)
            else:
                n.duet("elena", "marco", line, interval=-5, model=mdl, role=role, accomp="chitarra",
                       dyn=0.45 + 0.08 * rep)
        n.orch(n.sprog("G:2 | C:1 D7:1 | G:4"), style="chitarra", dyn=0.35)
    n.tempo(112).meter(2, 4)
    for k, line in enumerate(both[0:4]):
        n.duet("elena", "marco", line, interval=-5, model=("A", "B", "A", "B")[k],
               role=("open", "close", "open", "climax")[k], style="allegro", accomp="chitarra", dyn=0.55)
    n.orch(n.sprog("G:2 | C:1 D7:1 | G:2 | G:2"), style="chitarra", dyn=0.45)
    n.meter(4, 4).tempo(72)
    for line, mdl in ((both[0], "A"), (both[1], "B")):
        n.duet("elena", "marco", line, interval=-5, model=mdl, role="close", accomp="arpeggio", dyn=0.32)
    n.cue("aside")
    aside = both[4]
    n.tempo(60)
    n.sing("elena", aside, role="open", cadence="none", accomp="pad", dyn=0.3, disp_style="aside",
           accomp_kw={"sord": True})
    n.sing("marco", aside, model="__last__" if False else None, role="open", cadence="none", accomp="pad", dyn=0.3,
           disp_style="aside", accomp_kw={"sord": True})
    n.duet("elena", "marco", aside, interval=-3, role="open", cadence="none", accomp="pad", dyn=0.26)
    n.cue("curtain")
    n.orch(n.sprog("D7:4 | D7:4"), style="pad", dyn=0.18, melody=MARCO, melody_inst="cl")
    n.meter(6, 8).tempo(60)
    n.orch(n.sprog("G:3 | C:3 | G:3 | D7:3 | Em:3 | C:3 | Am7:3 | D7:3"), style="barcarolle", dyn=0.16, advance=False)
    n.theme("D5:1.5 B4:1.5 | C5:1.5 E5:1.5 | D5:1 B4:.5 G4:1.5 | A4:3 | B4:1.5 G4:1.5 | A4:1.5 C5:1.5 | "
            "B4:1 G4:.5 E4:1.5 | F#4:3", inst="ob", vel=0.24, advance=True)
    n.meter(4, 4)
    n.orch(n.sprog("D7:8"), style="pad", dyn=0.12, sord=True)
    n.event("curtain", state="down")
    n.pause(2.0)
    return n


ACT2 = [prelude2, n9, interlude_journey, n10, r2, n11, n12, interlude_sea, n13, n14]
