"""Act III of the full opera: Ritorno e rovina.

From N. 20 (the letter) the pitch class A never sounds: Tommaso's tone was A, and it has gone.
"""
from __future__ import annotations

from ..compose import textures as tx
from ..compose.themes import (WEDDING, VITTORIO, VITTORIO_HARM, MARCO, MARCO_WARPED, MARCO_LETTER,
                               DAVIDE_ARIA, DAVIDE_ARIA_HARM)
from ..notation import Ev, parse
from .act1 import bars_of
from .forms import Num

NO_A = (9,)

# the wedding harmony carried to F minor (degree for degree), for the Stabat Mater
STABAT_HARM = ("Fm:3 | C7:1.5 Fm:1.5 | Bbm:3 | Fm/C:1.5 C7:1.5 | Fm:3 | Db:3 | Bbm:3 | Fm/C:1.5 C7:1 Fm:.5 | "
               "Fm:1.5 C7:1.5 | Fm:1.5 Db:1.5 | Bbm:3 | Fm/C:1.5 Ab:1.5 | Fm:1.5 Bbm:1.5 | Gm7b5:1.5 C7sus4:1 C7:.5 | "
               "Fm/Ab:1.5 Bbm:1.5 | C7:1.5 Fm:1.5")


def wedding_in(key_from_pc=2, key_to_pc=5, mode_to="minor", transpose_oct=0):
    """The wedding melody carried from D major to another key and mode."""
    evs = parse(WEDDING)
    return tx.remap_line(evs, key_from_pc, "major", key_to_pc, mode_to, transpose_oct)


LULLABY = ('C5:1 A4:.5 Bb4:.5 C5:1 A4:1 | G4:2 F4:2 | A4:1 Bb4:.5 C5:.5 D5:1 F5:1 | E5:4 | C5:1 A4:.5 Bb4:.5 C5:1 A4:1 | G4:2 E4:2 | F4:1 G4:1 A4:1 G4:1 | F4:4')


def intermezzo():
    """Intermezzo (curtain down): Davide's warmth, the love duet; Marco's motif intrudes, warped."""
    n = Num("IM1", "Intermezzo", "F", 56, (4, 4), location="house_intermezzo", act=3)
    n.cue("start")
    n.orch(n.sprog(DAVIDE_ARIA_HARM), style="pad", dyn=0.24, advance=False)
    n.theme(DAVIDE_ARIA, inst="vn1", vel=0.34, transpose=12, advance=True)
    n.orch(n.sprog(DAVIDE_ARIA_HARM), style="arpeggio", dyn=0.28, advance=False)
    n.theme(DAVIDE_ARIA, inst="vc", vel=0.36, advance=True)
    piano = ("C5:1 A4:.5 C5:.5 F5:1.5 E5:.5 | D5:1 C5:1 C5:2 | Bb4:1 G4:.5 Bb4:.5 E5:1.5 D5:.5 | C5:4 | "
             "A5:1 G5:.5 F5:.5 E5:1.5 D5:.5 | C5:1 Bb4:1 A4:2 | G4:1 A4:.5 Bb4:.5 C5:1 E4:1 | F4:4")
    n.orch(n.sprog("F:4 | Dm7:2 C7:2 | C7:4 | F:4 | Dm:4 | Bb:2 F/A:2 | Gm7:2 C7:2 | F:4"), style="arpeggio", dyn=0.3,
           advance=False)
    n.theme(piano, inst="vc_solo", vel=0.38, advance=True, tech="espr")
    n.key_to("Gm").tempo(66)
    n.orch(n.sprog("Gm:4 | Eb:4 | Cm:4 | D7:4"), style="tremolo", dyn=0.35, advance=False)
    for k in range(4):
        n.theme(MARCO_WARPED, inst=("cl", "ob", "hn", "vn1")[k], vel=0.35 + 0.05 * k, origin=n.cursor + 4 * k,
                transpose=(0, 5, -2, 12)[k])
    n.rest(16.0)
    n.key_to("F").tempo(52)
    n.orch(n.sprog("F:4 | Bb:4 | C7:4 | F:4"), style="pad", dyn=0.22, advance=False)
    n.theme(piano, inst="ob", vel=0.3, advance=True)
    n.orch(n.sprog("F:8"), style="pad", dyn=0.14, sord=True)
    return n


def intermezzo_lutto():
    """Intermezzo: senza il La. The lullaby again, its A gone: F minor. Davide's F loses its third."""
    n = Num("IM2", "Intermezzo: senza il La", "Fm", 48, (4, 4), location="letter_room_dark", act=3, scene=3,
            avoid=NO_A)
    n.cue("start")
    lull = parse(LULLABY)
    lull_m = tx.remap_line(lull, 5, "major", 5, "minor")
    n.orch(n.sprog("Fm:4 | C7:4 | Fm:4 | Db:2 C7:2 | Fm:4 | Bbm:4 | C7:4 | Fm:4"), style="pad", dyn=0.18, sord=True,
           advance=False)
    n.add("vn1", [Ev(n.cursor + e.beat, e.dur * 1.0, e.midi, 0.28, e.art) for e in lull_m])
    n.rest(32.0)
    n.orch(n.sprog("Fm:4 | C7:4 | Fm:4 | Db:2 C7:2 | Fm:4 | Bbm:4 | C7:4 | Fm:4"), style="lullaby", dyn=0.16,
           advance=False)
    n.add("celesta", [Ev(n.cursor + e.beat, e.dur, e.midi + 12, 0.22, e.art) for e in lull_m])
    n.rest(32.0)
    # Davide's tune, its F without the third
    n.key_to("F")
    dav = [Ev(n.cursor + e.beat, e.dur, e.midi - 1 if int(round(e.midi)) % 12 == 9 else e.midi, 0.3, e.art)
           for e in parse(DAVIDE_ARIA)]
    n.orch(n.sprog("F5:4 | F5:4 | Bb:4 | C7sus4:4"), style="pad", dyn=0.18, sord=True, advance=False)
    n.add("vc", [e for e in dav])
    n.rest(16.0)
    n.orch(n.sprog("F5:8"), style="pad", dyn=0.12, sord=True)
    n.pause(2.0)
    return n


def prelude3():
    n = Num("P3", "Atto terzo: Preludio", "Gm", 72, (4, 4), location="prelude", act=3)
    n.cue("start")
    n.orch(n.sprog("Gm:4 | Gm/F:4 | Eb:4 | D7:4"), style="pad", dyn=0.2, sord=True, advance=False)
    n.tommaso(16.0, vel=0.2)
    n.theme(MARCO_WARPED + " r:2", inst="cl", vel=0.32, origin=n.cursor)
    n.theme(MARCO_WARPED + " r:2", inst="ob", vel=0.3, origin=n.cursor + 4, transpose=5)
    n.theme(MARCO_WARPED + " r:2", inst="fl", vel=0.3, origin=n.cursor + 8, transpose=10)
    n.rest(16.0)
    n.orch(n.sprog("Cm:4 | Ab:4 | F7:4 | Bb:4 | Gm:4 | Eb:4 | Cm7:4 | D7:4"), style="tremolo", dyn=0.32, advance=False)
    for k in range(4):
        n.theme(MARCO_WARPED, inst=("vn1", "cl", "hn", "vn1")[k], vel=0.36 + 0.04 * k, origin=n.cursor + 8 * k,
                transpose=(0, -2, -7, 3)[k])
    n.rest(32.0)
    n.key_to("F").tempo(54).cue("child")
    n.orch(n.sprog("F:4 | C7:4 | Dm:4 | Bb:2 C7:2 | F:4 | Gm:4 | C7:4 | F:4"), style="lullaby", dyn=0.18,
           advance=False)
    n.tommaso(32.0, vel=0.22)
    n.theme("C5:1 A4:.5 Bb4:.5 C5:1 A4:1 | G4:2 F4:2 | A4:1 Bb4:.5 C5:.5 D5:1 F5:1 | E5:4 | "
            "C5:1 A4:.5 Bb4:.5 C5:1 A4:1 | G4:2 E4:2 | F4:1 G4:1 A4:1 G4:1 | F4:4", inst="cl", vel=0.26, advance=True)
    n.key_to("Gm").tempo(72)
    n.orch(n.sprog("Eb7:4 | Eb7:4 | D7:4 | Gm:4"), style="pad", dyn=0.22)
    n.event("curtain", state="up")
    return n


def r3():
    """Episodi: the café, home, the pier; the months pass and Marco's motif takes hold."""
    n = Num("R3", "Episodi", "Bb", 120, (3, 4), location="montage_cafe", act=3, scene=1)
    items = [x for x in n.lib.items if hasattr(x, "speaker")]
    n.cue("start")
    waltz = "Bb:3 | F7:3 | F7:3 | Bb:3 | Bb:3 | Eb:3 | F7:3 | Bb:3"
    wtune = ("D5:1.5 Eb5:.5 F5:1 | Eb5:1.5 D5:.5 C5:1 | A4:1.5 Bb4:.5 C5:1 | D5:3 | "
             "F5:1.5 G5:.5 A5:1 | Bb5:1.5 G5:.5 Eb5:1 | D5:1 C5:1 A4:1 | Bb4:3")
    n.orch(n.sprog(waltz), style="waltz", dyn=0.3, advance=False)
    n.theme(wtune, inst="vn1", vel=0.34, advance=True)
    n.recit(items[0:3], chords=["I", "IV", "V7"], base=0.5, dyn=0.22, accomp="waltz", strike_end=False)
    n.orch(n.sprog(waltz), style="waltz", dyn=0.28, advance=False)
    n.theme(wtune, inst="cl", vel=0.3, advance=True)
    # home: Davide's F major
    n.meter(4, 4).tempo(66).key_to("F")
    n.event("location", where="montage_home")
    n.orch(n.sprog("F:4 | C7:4"), style="pad", dyn=0.2, melody=MARCO_WARPED, melody_inst="ob")
    n.recit(items[3:6], chords=["I", "vi", "IV"], base=0.5, dyn=0.22, accomp="pad", strike_end=False)
    n.tommaso(6.0, vel=0.22)
    n.orch(n.sprog("Bb:4 | C7:4 | F:4"), style="arpeggio", dyn=0.2)
    # the pier: the bora
    n.key_to("Gm").tempo(80)
    n.event("location", where="montage_pier")
    n.orch(n.sprog("Gm:4 | D7:4"), style="tremolo", dyn=0.35, melody=MARCO_WARPED, melody_inst="hn")
    n.recit(items[6:8], chords=["i", "V7"], base=0.5, dyn=0.3, accomp="tremolo", strike_end=False)
    # the months: the warped motif everywhere
    n.cue("montage")
    n.orch(n.sprog("Gm:4 | Eb:4 | Cm:4 | D7:4 | Bb:4 | Gm:4 | Eb7:4 | D7:4"), style="arpeggio", dyn=0.32, advance=False)
    for k in range(4):
        n.theme(MARCO_WARPED, inst=("cl", "vn1", "ob", "fl")[k], vel=0.34 + 0.04 * k, origin=n.cursor + 8 * k,
                transpose=(0, 3, 7, 12)[k])
    n.rest(32.0)
    n.meter(3, 4).tempo(108).key_to("Gm")
    n.orch(n.sprog("Gm:3 | D7:3 | D7:3 | Gm:3 | Cm:3 | Gm:3 | A7:3 | D7:3"), style="waltz", dyn=0.3, advance=False)
    n.theme("Bb4:1.5 C5:.5 D5:1 | C5:1.5 Bb4:.5 A4:1 | F#4:1.5 G4:.5 A4:1 | Bb4:3 | "
            "Eb5:1.5 D5:.5 C5:1 | Bb4:1.5 A4:.5 G4:1 | A4:1 F#4:1 D4:1 | G4:3", inst="ob", vel=0.3, advance=True)
    n.meter(4, 4).tempo(80)
    n.orch(n.sprog("Eb:4 | Cm:4 | Ab:4 | D7:4 | Gm:4 | Eb7:4 | D7:4 | D7:4"), style="tremolo", dyn=0.38, advance=False)
    for k in range(4):
        n.theme(MARCO_WARPED, inst=("vn1", "hn", "cl", "vn1")[k], vel=0.4 + 0.05 * k, origin=n.cursor + 8 * k,
                transpose=(5, -2, 8, 12)[k])
    n.rest(32.0)
    return n


def n15():
    """N. 15 Aria di Marco, "Dovrei partire adesso": ends on the dominant of A-flat."""
    n = Num("N15", 'Aria di Marco, "Dovrei partire adesso"', "Bb", 54, (4, 4), location="montage_pier", act=3,
            scene=1)
    L = n.L("marco")
    n.cue("start")
    n.orch(n.sprog("Bb:4 | Gm:4 | Cm7:4 | F7:4"), style="arpeggio", dyn=0.25, melody=MARCO_WARPED, melody_inst="cl",
           melody_transpose=3)
    n.stanza("marco", L[0:4], "A:open B:close A':open B':close", style="cantabile", accomp="arpeggio",
             dyn=(0.4, 0.5))
    n.ritornello("A", inst="ob", dyn=0.3)
    n.key_to("Gm")
    n.stanza("marco", L[4:8], "C:contrast D:open A'':climax B'':close", style="cantabile", accomp="arpeggio",
             dyn=(0.45, 0.68), climax_accomp="pad")
    n.key_to("Gm").tempo(120).cue("cabaletta")
    n.orch(n.sprog("Gm:4 | D7:4"), style="tremolo", dyn=0.45)
    for rep in range(2):
        n.stanza("marco", L[0:4], ("S:open T:close U:open V:close" if rep == 0 else
                                    "S':open T':close U':open V'':climax"), style="allegro", accomp="tremolo",
                 dyn=(0.55, 0.7) if rep == 0 else (0.62, 0.82))
        n.orch(n.sprog("Gm:2 Cm:2 | D7:4 | Gm:4"), style="tutti" if rep else "tremolo", dyn=0.6)
    n.key_to("Bb").tempo(54)
    n.coda("marco", L[6:8], ["A", "B"], style="cantabile", accomp="arpeggio", dyn=(0.5, 0.7), repeats=2)
    n.orch(n.sprog("Bb:4 | Eb7:4 | Eb7:4"), style="pad", dyn=0.25, melody=MARCO_WARPED, melody_inst="cl")
    return n


def n16():
    """N. 16 La visione: the church at dusk; Vittorio again (the film's); she goes to Marco."""
    n = Num("N16", "La visione", "Ab", 80, (4, 4), location="church_dusk", act=3, scene=1)
    vit = n.L("vittorio")
    n.cue("start")
    n.orch(n.sprog("Ab:4 | Db/Ab:4 | Eb7/Ab:4 | Ab:4"), style="chorale", dyn=0.2, family="organ")
    n.orch(n.sprog("Fm:4 | Db:4 | Bbm:4 | Eb7:4"), style="pad", dyn=0.16, sord=True)
    n.cue("vision")
    n.event("vision", who="vittorio", state="on")
    for k, line in enumerate(vit):
        n.sing("vittorio", line, role="open" if k % 2 == 0 else "close", accomp="pad", dyn=0.4,
               disp_style="vision", pos="top", accomp_kw={"sord": True, "with_bass": False})
    n.event("vision", who="vittorio", state="off")
    n.orch(n.sprog("Ab:4 | Fm:4 | Db:4 | Eb7:4"), style="pad", dyn=0.14, sord=True)
    n.orch(n.sprog("Ab/C:4 | Db:4 | Bbm7:4 | Eb7:4"), style="chorale", dyn=0.16, family="organ", advance=False)
    n.theme("C4:1.5 Bb3:.5 Ab3:1 G3:1 | Db4:1.5 Ab3:.5 Eb4:1 Db4:1", inst="vc", vel=0.24, advance=True)
    # she turns, and goes: the warped motif quickens towards F minor
    n.tempo(96).key_to("Fm").cue("goes")
    n.orch(n.sprog("Fm:4 | Db:4 | Bbm:4 | C7:4 | Fm:4 | Gb:4 | C7:4 | C7:4"), style="tremolo", dyn=0.35, advance=False)
    for k in range(4):
        n.theme(MARCO_WARPED, inst=("cl", "ob", "vn1", "hn")[k], vel=0.36 + 0.05 * k, origin=n.cursor + 8 * k,
                transpose=(-2, 3, 10, -7)[k])
    n.rest(32.0)
    n.tempo(60)
    n.orch(n.sprog("Fm:4"), style="pad", dyn=0.12, sord=True)
    return n


def n17():
    """N. 17 Stabat Mater: the unseen chorus mourns; the wedding melody, in F minor, in the cellos."""
    n = Num("N17", "Stabat Mater", "Fm", 50, (6, 8), location="stabat", act=3, scene=1)
    L = n.L("coro")
    n.cue("start")
    harm = n.sprog(STABAT_HARM)
    total = harm[-1][0] + harm[-1][1] - harm[0][0]           # 48 crotchets: the wedding melody's length
    mel_f = wedding_in()

    def cellos(origin, vel=0.3):
        evs = [Ev(origin + e.beat, e.dur, e.midi - 24, vel, e.art) for e in mel_f]
        n.add("vc", evs, voice="vc_wedding", tech="espr", motif="wedding_lament")

    def harm_at(origin, beats):
        """The F-minor wedding harmony from `origin`, looped, for `beats` crotchets."""
        out = []
        b = 0.0
        while b < beats - 1e-6:
            for hb, hd, hc in harm:
                rb = hb - harm[0][0]
                if b + rb >= beats - 1e-6:
                    break
                d = min(hd, beats - (b + rb))
                out.append((origin + b + rb, d, hc))
            b += total
        return out

    # the cellos alone, then the chorus enters over them
    cellos(n.cursor, 0.32)
    p = harm_at(n.cursor, total)
    n.add_parts([("cb", tx.bass(p, lo=28, hi=45, vel=0.22), {"tech": "sord"})])
    n.rest(total)
    start = n.cursor
    verses = [L[i:i + 3] for i in range(0, 15, 3)]
    phrase_beats = 6.0                                        # two bars of 6/8 per line
    for v, lines in enumerate(verses):
        if v in (0, 2, 4):
            cellos(n.cursor, 0.3)                             # the melody runs on beneath the verses
        for j, line in enumerate(lines):
            p = harm_at(n.cursor, phrase_beats)
            if v == 1 and j == 2:
                # gladius: F minor turns to E major on the common tone (A-flat = G-sharp)
                p = n.sprog("Fm:3 | E:3")
                n.cue("gladius")
            n.chorus(line, prog=p, use_tune=False, role=("open", "close", "close")[j], accomp="pad",
                     dyn=0.4 + 0.04 * v, bars=2)
        n.orch(harm_at(n.cursor, 6.0), style="pad", dyn=0.18, sord=True)
    # the first verse again, very softly
    n.cue("da_capo")
    cellos(n.cursor, 0.24)
    for j, line in enumerate(verses[0]):
        n.chorus(line, prog=harm_at(n.cursor, phrase_beats), use_tune=False, role=("open", "close", "close")[j],
                 accomp="pad", dyn=0.3, bars=2)
    # a single chord, unresolved; darkness
    n.cue("held_chord")
    n.orch(n.sprog("Dbmaj7/F:12"), style="pad", dyn=0.18, sord=True)
    n.pause(4.0)
    return n


def r4():
    """Scena: the trattoria; Nives; the run."""
    n = Num("R4", "Scena", "Bb", 72, (3, 4), location="trattoria", act=3, scene=2)
    items = [x for x in n.lib.items if hasattr(x, "speaker")]
    n.cue("start")
    waltz = "Bb:3 | F7:3 | F7:3 | Bb:3 | Eb:3 | Bb:3 | F7:3 | Bb:3"
    n.orch(n.sprog(waltz), style="waltz", dyn=0.3, advance=False)
    n.theme("D5:1.5 Eb5:.5 F5:1 | Eb5:1.5 D5:.5 C5:1 | A4:1.5 Bb4:.5 C5:1 | D5:3 | "
            "G5:1.5 F5:.5 Eb5:1 | D5:1.5 C5:.5 Bb4:1 | C5:1 A4:1 F4:1 | Bb4:3", inst="cl", vel=0.32, advance=True)
    for x in items[0:3]:
        n.sing(x.speaker, x, role="open", accomp="waltz", dyn=0.38, style="andante")
    n.orch(n.sprog(waltz), style="waltz", dyn=0.3)
    n.cue("nives")
    n.meter(4, 4).tempo(120).key_to("Gm")
    n.orch(n.sprog("Gm:2 | D7:2"), style="tremolo", dyn=0.6)
    n.sing("nives", items[3], role="open", accomp="tremolo", dyn=0.65, style="allegro", cadence="none")
    n.cue("run")
    n.tempo(152)
    n.orch(n.sprog("Gm:4 | Eb:4 | Cm:4 | D7:4 | Gm:4 | Ab:4 | D7:4 | D7:4"), style="tremolo", dyn=0.6, advance=False)
    n.add("timp", [Ev(n.cursor + k * 1.0, 0.5, 43 if k % 2 == 0 else 50, 0.45) for k in range(32)])
    n.rest(32.0)
    return n


def n18():
    """N. 18 Concertato sul figlio morente: the tone fades, returns, fades; where it should return, it
    does not. The bare fifth."""
    n = Num("N18", "Concertato sul figlio morente", "F", 52, (4, 4), location="deathbed", act=3, scene=2)
    el = n.L("elena")
    dav = n.L("davide")
    both = n.L("elena+davide")
    n.cue("start")
    n.cue("deathbed")
    n.orch(n.sprog("F:4 | Bbmaj7/F:4 | C7/E:4 | F:4 | Dm:4 | Bb:4 | Gm7:4 | C7:4"), style="pad", dyn=0.18, sord=True,
           advance=False)
    n.tommaso(32.0, vel=0.28)
    n.tommaso(32.0, vel=0.18, inst="eh")
    n.theme("A5:2 G5:1 F5:1 | E5:2 D5:2 | F5:2 E5:1 D5:1 | C5:4 | D5:2 E5:1 F5:1 | G5:2 F5:2 | E5:2 D5:1 C5:1 | C5:4",
            inst="vn_solo", vel=0.28, origin=n.cursor + 16.0, tech="espr")
    n.rest(32.0)
    t0 = n.cursor
    n.stanza("elena", el, "A:open B:close", style="andante", accomp="pad", dyn=(0.35, 0.4),
             accomp_kw={"sord": True})
    n.stanza("davide", dav, "C:open D:close", style="andante", accomp="pad", dyn=(0.35, 0.42),
             accomp_kw={"sord": True})
    n.tommaso(n.cursor - t0, vel=0.26, origin=t0)
    # together: the tone fades at the end of the phrase, and returns
    t1 = n.cursor
    for k, line in enumerate(both):
        n.duet("elena", "davide", line, interval=-3, role=("open", "close", "open", "close")[k],
               accomp="pad", dyn=0.4 + 0.03 * k)
    n.tommaso(n.cursor - t1 - 1.0, vel=0.24, origin=t1, env="fade")
    n.cue("tone_returns")
    n.tommaso(8.0, vel=0.24)
    t2 = n.cursor
    for k, line in enumerate(both):
        n.duet("elena", "davide", line, interval=-3, model=("A", "B", "A", "B")[k] if k < 2 else None,
               role=("open", "close", "climax", "close")[k], accomp="pad", dyn=0.45 + 0.05 * k,
               contour="high" if k == 2 else "arch")
    n.tommaso(n.cursor - t2 - 2.0, vel=0.22, origin=t2, env="fade")
    n.cue("tone_returns2")
    n.tommaso(6.0, vel=0.2)
    t3 = n.cursor
    for k, line in enumerate(both):
        n.duet("elena", "davide", line, interval=-3, model=("A", "B", "A", "B")[k],
               role=("open", "close", "open", "close")[k], accomp="pad", dyn=0.4 - 0.04 * k)
    n.tommaso(n.cursor - t3 - 3.0, vel=0.18, origin=t3, env="fade")
    # where it should return, it does not
    n.cue("tone_fail")
    n.orch(n.sprog("F:4"), style="pad", dyn=0.12, sord=True)
    n.cue("death")
    n.pause(3.0)
    n.add_parts([("vc", [Ev(n.cursor, 10.0, 41, 0.22), Ev(n.cursor, 10.0, 48, 0.2)], {"tech": "sord"}),
                 ("cb", [Ev(n.cursor, 10.0, 29, 0.2)], {"tech": "sord"})])
    n.rest(10.0)
    n.pause(8.0)
    return n


def n19():
    """N. 19 Requiem: the funeral; the tone passes for the last time; the last A."""
    n = Num("N19", "Requiem", "Dm", 50, (4, 4), location="funeral", act=3, scene=3)
    L = n.L("coro")
    n.cue("start")
    n.cue("march")
    n.orch(n.sprog("Dm:4 | Dm:4 | Gm:4 | Dm:4 | Bb:4 | Gm:4 | A7:4 | Dm:4"), style="pad", dyn=0.3, advance=False)
    n.add("timp", [Ev(n.cursor + k * 1.0, 0.5, 38, 0.35 if k % 4 == 0 else 0.2) for k in range(32)])
    n.theme("D4:1.5 D4:.5 D4:1 F4:1 | E4:1.5 D4:.5 C#4:2 | D4:1.5 D4:.5 D4:1 G4:1 | F4:4 | "
            "F4:1.5 F4:.5 F4:1 Bb4:1 | A4:1.5 G4:.5 F4:2 | E4:1 F4:1 G4:1 C#4:1 | D4:4", inst="tbn", vel=0.4, advance=False)
    n.theme("D4:1.5 D4:.5 D4:1 F4:1 | E4:1.5 D4:.5 C#4:2 | D4:1.5 D4:.5 D4:1 G4:1 | F4:4 | "
            "F4:1.5 F4:.5 F4:1 Bb4:1 | A4:1.5 G4:.5 F4:2 | E4:1 F4:1 G4:1 C#4:1 | D4:4", inst="bn", vel=0.32, advance=True)
    n.add("churchbell", [Ev(n.cursor - 32 + k * 8.0, 6.0, 50, 0.34) for k in range(4)])
    n.cue("requiem")
    bell = [Ev(n.cursor + k * 4.0, 5.0, 50, 0.38) for k in range(8)]
    n.add("churchbell", bell)
    n.orch(n.sprog("Dm:4 | Gm/D:4 | A7/D:4 | Dm:4"), style="chorale", dyn=0.3, family="organ", advance=False)
    n.add("timp", [Ev(n.cursor + k * 1.0, 0.5, 38, 0.3 if k % 4 == 0 else 0.18) for k in range(16)])
    n.rest(16.0)
    n.chorus(L[0], role="open", accomp="chorale", dyn=0.45, family="organ")
    n.chorus(L[1], role="close", accomp="chorale", dyn=0.45, family="organ")
    n.cue("last_tone")
    t = n.cursor
    n.chorus(L[2], role="open", accomp="chorale", dyn=0.42, family="organ")
    n.chorus(L[3], role="contrast", accomp="chorale", dyn=0.45, family="organ")
    n.tommaso(n.cursor - t, vel=0.22, origin=t, env="fade")
    n.cue("tone_gone")
    n.chorus(L[4], role="close", accomp="chorale", dyn=0.4, family="organ")
    n.chorus(L[2], role="open", accomp="chorale", dyn=0.4, family="organ")
    n.chorus(L[3], role="climax", accomp="chorale", dyn=0.5, family="organ")
    n.chorus(L[4], role="close", accomp="chorale", dyn=0.42, family="organ")
    n.add("churchbell", [Ev(n.cursor - 8 + 4 * k, 5.0, 50, 0.35) for k in range(4)])
    n.chorus(L[0], role="open", accomp="chorale", dyn=0.32, family="organ")
    n.chorus(L[1], role="close", accomp="chorale", dyn=0.28, family="organ")
    n.orch(n.sprog("Dm:8"), style="chorale", dyn=0.24, family="organ")
    n.pause(2.0)
    return n


def n20():
    """N. 20 La lettera: the letter, unsung; Marco's motif resolves in G-flat; one line aloud; her
    confession. No A from here to the end."""
    n = Num("N20", "La lettera", "Gb", 60, (4, 4), location="letter", act=3, scene=3, avoid=NO_A)
    items = n.lib.items
    from .libretto import Direction, Line
    letter = [x for x in items if isinstance(x, Direction) and x.it and not x.it.startswith("(")]
    sung = [x for x in items if isinstance(x, Line)]
    n.cue("start")
    n.cue("letter_slide", 0.5)
    n.orch(n.sprog("Gb:4 | Ebm:4"), style="pad", dyn=0.14, sord=True)
    n.cue("letter_open")
    # the orchestra plays beneath the silence; the letter is read by the eye
    t = n.cursor
    n.orch(n.sprog("Gb:4 | Cb:4 | Db7:4 | Gb:4 | Ebm:4 | Cb:4 | Db7:4 | Gb:4 | Bbm:4 | Gb:4 | Ab7:4 | Db7:4 | "
                   "Gb:4 | Ebm:4 | Db7:4 | Gb:4"), style="arpeggio", dyn=0.24, advance=False)
    n.theme(MARCO_LETTER + " r:8", inst="cl", vel=0.34, origin=t)
    n.theme(MARCO_LETTER + " r:8", inst="ob", vel=0.3, origin=t + 32.0)
    n.cue("resolution", t + 4.0)
    for k, x in enumerate(letter):
        n.cursor = t + 8.0 * k
        n.text(x.it, x.en, 8.0, style="letter")
    n.cursor = t + 64.0
    n.cue("read")
    n.sing("davide", sung[0], role="open", cadence="none", accomp="pad", dyn=0.3, disp_style="letter_read",
           accomp_kw={"sord": True})
    n.key_to("Bbm").cue("confession")
    n.stanza("elena", sung[1:9], "A:open B:close C:open D:close E:contrast F:open G:climax H:close",
             style="andante", accomp="pad", dyn=(0.35, 0.55))
    n.stanza("elena", sung[5:9], "E':contrast F':open G'':climax H':close", style="andante", accomp="pad",
             dyn=(0.45, 0.62))
    n.orch(n.sprog("Bbm:4 | Gb:4 | F7sus4:4"), style="pad", dyn=0.2, sord=True)
    return n


def n21():
    """N. 21 Aria di Davide, "Se restassi, sarei lui": F without its third."""
    n = Num("N21", 'Aria di Davide, "Se restassi, sarei lui"', "F", 60, (4, 4), location="split", act=3, scene=3,
            avoid=NO_A)
    items = [x for x in n.lib.items if hasattr(x, "speaker")]
    dav = [x for x in items if x.speaker == "davide"]
    el = [x for x in items if x.speaker == "elena"]
    n.cue("start")
    n.recit(dav[0:2], chords=["I", "IV"], base=0.6, dyn=0.22, strike_end=False)
    # once only, grief overwhelms him
    n.cue("heat_start")
    n.tempo(76)
    for x in dav[2:5]:
        n.sing("davide", x, role="open", accomp="tutti", dyn=0.8, style="allegro", disp_style="heat",
               cadence="none")
    n.cue("heat_end")
    n.tempo(60)
    n.orch(n.sprog("Bbm:4 | Gb:4 | Db/F:4 | C7sus4:4"), style="tremolo", dyn=0.35, low=False)
    n.sing("elena", el[0], role="open", accomp="tremolo", dyn=0.4, disp_style="parlato", cadence="none")
    # understanding, on the threshold, too late
    n.key_to("Db").cue("aria")
    aria = dav[5:17]
    n.orch(n.sprog("Db:4 | Gb:4 | Ebm7:4 | Ab7:4"), style="arpeggio", dyn=0.25)
    n.stanza("davide", aria[0:4], "A:open B:close A':open B':close", style="andante", accomp="arpeggio",
             dyn=(0.38, 0.48))
    n.stanza("davide", aria[4:8], "C:contrast D:open A'':climax B'':close", style="andante", accomp="arpeggio",
             dyn=(0.42, 0.62))
    n.key_to("F")
    n.stanza("davide", aria[8:12], "E:open F:close G:open H:close", style="andante", accomp="pad",
             dyn=(0.45, 0.55))
    n.coda("davide", aria[8:10], ["E", "F"], style="andante", accomp="pad", dyn=(0.5, 0.62), repeats=2)
    n.stanza("davide", aria[10:12], "G':open H'':climax", style="andante", accomp="arpeggio", dyn=(0.45, 0.55))
    n.cue("door")
    n.event("exit", who="davide")
    n.orch(n.sprog("F5:4 | Bb:4 | C7sus4:4 | F5:4"), style="pad", dyn=0.2, sord=True)
    n.pause(2.0)
    return n


def r5():
    """Scena: Marco. 'Non sono la risposta. Ero soltanto la domanda.'"""
    n = Num("R5", "Scena: Marco", "Ebm", 66, (4, 4), location="marco_house", act=3, scene=3, avoid=NO_A)
    items = [x for x in n.lib.items if hasattr(x, "speaker")]
    n.cue("start")
    n.cue("marco")
    n.orch(n.sprog("Ebm:4 | Bb7:4"), style="pad", dyn=0.18, melody="Bb3:.5 Gb4:1.5 F4:.5 Ab4:1.5 Gb4:4",
           melody_inst="cl")
    n.recit(items[:-1], chords=["i", "VI", "iv", "V7", "i"], base=0.5, dyn=0.25, strike_end=False)
    n.sing("marco", items[-1], role="close", accomp="pad", dyn=0.3, style="andante")
    n.event("exit", who="marco")
    n.orch(n.sprog("Ebm:4 | Cb:4 | Bb7:4 | Ebm:4"), style="pad", dyn=0.16, sord=True)
    return n


def n22():
    """N. 22 Scena ed aria finale di Elena (the required shot: dolly, wide, close-up, final, curtain)."""
    n = Num("N22", "Scena ed aria finale di Elena", "Db", 60, (4, 4), location="empty_room", act=3, scene=3,
            avoid=NO_A)
    items = [x for x in n.lib.items if hasattr(x, "speaker")]
    el = [x for x in items if x.speaker == "elena"]
    vit = [x for x in items if x.speaker == "vittorio"]
    n.cue("start")
    n.cue("scena")
    n.orch(n.sprog("Db:4"), style="pad", dyn=0.14, sord=True)
    for x in el[0:4]:
        n.sing("elena", x, role="close", accomp="pad", dyn=0.26, disp_style="parlato", cadence="none",
               accomp_kw={"sord": True})
    n.event("walls", state="fly")
    # the memory of the wedding refrain, in D-flat, in the horns: the opera house appears
    n.meter(6, 8).tempo(72).cue("dolly")
    n.event("location", where="opera_house")
    refrain = tx.remap_line(parse(bars_of(WEDDING, 9, 16)), 2, "major", 1, "major")
    n.orch(n.sprog("Db:3 | Ab7:3 | Db:3 | Bbm:3 | Gb:3 | Db/Ab:3 | Eb7:3 | Ab7:3"), style="arpeggio", dyn=0.3,
           advance=False)
    n.add("hn", [Ev(n.cursor + e.beat, e.dur, e.midi - 12, 0.34, e.art) for e in refrain])
    n.rest(24.0)
    n.orch(n.sprog("Gb:3 | Db/F:3 | Ebm7:3 | Ab7:3 | Db:3 | Bbm:3 | Eb7:3 | Ab7:3"), style="arpeggio", dyn=0.36,
           advance=False)
    n.add("vn1", [Ev(n.cursor + e.beat, e.dur, e.midi, 0.36, e.art) for e in refrain])
    n.rest(24.0)
    # cantabile: 'Io mi rivedo in piazza, a diciott'anni'
    n.cue("sing")
    cant = el[4:12]
    n.stanza("elena", cant[0:4], "A:open B:close C:open D:close", style="cantabile", accomp="arpeggio",
             dyn=(0.42, 0.52))
    n.cue("wide")
    n.stanza("elena", cant[4:8], "E:contrast F:open G:climax H:close", style="cantabile", accomp="arpeggio",
             dyn=(0.48, 0.66))
    n.cue("echo")
    n.orch(n.sprog("Db:3 | Ab7:3 | Db:6"), style="arpeggio", dyn=0.24)
    # Vittorio, offstage, over a lone A-flat
    n.meter(4, 4).tempo(80).cue("vittorio3")
    t = n.cursor
    for k, line in enumerate(vit[0:4]):
        n.sing("vittorio", line, role="open" if k % 2 == 0 else "close", accomp=None, dyn=0.42,
               disp_style="offstage", pos="top")
    n.add("cb", [Ev(t, n.cursor - t, 32, 0.18)], tech="sord")
    n.add("vc", [Ev(t, n.cursor - t, 44, 0.14)], tech="sord")
    # the second movement: the unbroken line
    n.tempo(72).cue("closeup")
    sec = el[12:19]
    n.stanza("elena", sec[0:6], "I:open J:close K:open L:close M:contrast N:open", style="cantabile",
             accomp="arpeggio", dyn=(0.5, 0.7))
    n.cue("climax")
    n.sing("elena", sec[6], role="climax", contour="high", accomp="tutti", dyn=0.82, style="cantabile",
           double=("fl", 12))
    # the orchestra answers with the wedding refrain, whole, in D-flat
    n.meter(6, 8).tempo(72)
    n.orch(n.sprog("Db:3 | Ab7:3 | Db:3 | Bbm:3 | Gb:3 | Db/Ab:3 | Eb7:3 | Ab7:3"), style="tutti", dyn=0.6, advance=False)
    n.add("vn1", [Ev(n.cursor + e.beat, e.dur, e.midi, 0.6, e.art) for e in refrain])
    n.add("tpt", [Ev(n.cursor + e.beat, e.dur, e.midi - 12, 0.45, e.art) for e in refrain])
    n.rest(24.0)
    n.orch(n.sprog("Gb:6 | Ab7sus4:3 Ab7:3"), style="pad", dyn=0.2, sord=True)
    n.meter(4, 4).tempo(72)
    # unaccompanied
    n.cue("vittorio4")
    n.sing("vittorio", vit[4], role="close", accomp=None, dyn=0.38, disp_style="offstage", pos="top")
    # the final close
    n.tempo(60).cue("close")
    n.stanza("elena", el[19:23], "O:open P:close Q:open R:close", style="cantabile", accomp="arpeggio",
             dyn=(0.4, 0.34))
    n.coda("elena", el[21:23], ["Q", "R"], style="cantabile", accomp="arpeggio", dyn=(0.38, 0.28), repeats=2)
    n.cue("final_chord")
    n.orch(n.sprog("Db:4 | Gb/Db:4 | Db:8"), style="arpeggio", dyn=0.22)
    n.cue("curtain")
    n.event("curtain", state="down")
    n.pause(5.0)
    n.cue("black")
    n.pause(3.0)
    return n


ACT3 = [intermezzo, prelude3, r3, n15, n16, n17, r4, n18, n19, intermezzo_lutto, n20, n21, r5, n22]
