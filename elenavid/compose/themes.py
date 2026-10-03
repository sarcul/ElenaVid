"""The opera's governing themes. Composed first, as the treatment requires.

All melodies are in the notation of elenavid.notation (durations in crotchets).
"""

# ---------------------------------------------------------------------------------------------
# 1. THE WEDDING MELODY  "Sia per sempre"   D major, 6/8 (bar = 3 crotchets), tempo di furlana
#    Verse: rising fourths in sequence (a village dance). Refrain: the octave leap A-D-A on
#    "Sia per SEM-pre", a scale climbing to heaven on "ciò che il cielo", a chromatic-mediant
#    sunburst (F major under the held A5) and the peak B5 over the subdominant.
#    Range F#4-B5. In Act III it returns in F minor in the cellos beneath the Stabat Mater; in the
#    final aria it returns in D-flat major, untouched, as memory.
# ---------------------------------------------------------------------------------------------
WEDDING = (
    "F#4:1 G4:.5 A4:1 D5:.5 | C#5:1 B4:.5 A4:1 F#4:.5 | G4:1 A4:.5 B4:1 E5:.5 | D5:1 C#5:.5 B4:1 A4:.5 | "
    "F#4:1 G4:.5 A4:1 D5:.5 | F#5:1 E5:.5 D5:1 B4:.5 | B4:1 C#5:.5 D5:1 B4:.5 | A4:.5 D5:1 C#5:1 D5:.5 | "
    "A4:1 D5:.5 A5:1 G5:.5 | F#5:1 E5:.5 D5:1 C#5:.5 | B4:1 C#5:.5 D5:1 E5:.5 | F#5:1 G5:.5 A5:1.5 | "
    "A4:1 D5:.5 B5:1 A5:.5 | G5:1 F#5:.5 E5:1 D5:.5 | F#5:1 E5:.5 D5:1 B4:.5 | A4:1 C#5:.5 D5:1.5"
)
WEDDING_LYR = (
    "Suo nin le cam pa ne_a fe sta cor ra_il vi no per la vi a "
    "fio ri bian chi sul la te sta Dio vi guar di_e co sì si a "
    "Sia per sem pre sia per sem pre ciò che_il cie lo_in ter ra_u nì "
    "sia per sem pre sia per sem pre sia per sem pre_il vo stro sì"
)
WEDDING_HARM = (
    "D:3 | A7:1.5 D:1.5 | G:3 | D/A:1.5 A7:1.5 | D:3 | Bm:3 | G:3 | D/A:1.5 A7:1 D:.5 | "
    "D:1.5 A7:1.5 | D:1.5 Bm:1.5 | G:3 | D/A:1.5 F:1.5 | D:1.5 G:1.5 | Em7:1.5 A7sus4:1 A7:.5 | "
    "D/F#:1.5 G:1.5 | A7:1.5 D:1.5"
)
WEDDING_LINES = [  # (Italian, English) per two-bar line, for the typography
    ("Suonin le campane a festa,", "Let the bells ring out for the feast,"),
    ("corra il vino per la via,", "let the wine run down the street,"),
    ("fiori bianchi sulla testa,", "white flowers in her hair,"),
    ("Dio vi guardi, e così sia!", "God keep you both, and so be it!"),
    ("Sia per sempre, sia per sempre", "Let it be forever, let it be forever,"),
    ("ciò che il cielo in terra unì;", "what heaven joined on earth;"),
    ("sia per sempre, sia per sempre,", "let it be forever, let it be forever,"),
    ("sia per sempre il vostro sì!", "let your yes be forever!"),
]

# ---------------------------------------------------------------------------------------------
# 2. VITTORIO'S PHRASE   A-flat major, 4/4, Andante con moto (crotchet = 80)
#    Identical in pitch and rhythm on every appearance. A key with no A natural: his world turns
#    Tommaso's A into A-flat. Bar 2 'per SEM-pre' (A-flat, E-flat, D-flat) mirrors the wedding's
#    'per SEM-pre' (D, A, G): a rising fifth and a falling step. Range E-flat 3 to F4.
# ---------------------------------------------------------------------------------------------
VITTORIO = (
    "C4:1.5 Bb3:.5 Ab3:1 G3:1 | (Db4)C4:1.5 Ab3:.5 Eb4:1 Db4:1 | Db4:1 C4:1 Bb3:1.5 Ab3:.5 | "
    "G3:.5 Ab3:.5 F3:2 Eb3:1 | Eb3:.5 Ab3:.5 C4:2 Eb4:1 | Db4:1 Eb4:1 F4:1.5 Eb4:.5 | "
    "Db4:1 C4:1 Bb3:1.5 C4:.5 | Db4:1 Bb3:1 G3:1 Ab3:1"
)
VITTORIO_HARM = (
    "Abmaj7:4 | Fm7:2 Eb7sus4:1 Eb7:1 | Dbmaj7:2 Bbm7:2 | Eb7sus4:2 Eb7:2 | "
    "Ab/Eb:2 Fm7:2 | Dbmaj9:2 Bbm7:2 | Ab/C:2 Fm7:1 Bbm7:1 | Eb7:2 Ab:2"
)
VITTORIO_TEXT = {
    1: ("E le na sei mia per sem pre Io nel cuo re ti ri man go "
        "Nes sun luo go ti na scon de dal tuo spo so tuo si gno re"),
    2: ("E le na mi por ti den tro co me fer ro nel tuo pet to "
        "Fug gi pu re_in te di mo ro tuo pa dro ne tuo re spi ro"),
    3: ("E le na_o gni co sa_è spen ta il bam bi no l'al tro_il fuo co "
        "So lo_io re sto nel si len zio tuo prin ci pio tua ro vi na"),
    4: "E le na sei mia per sem pre",
    "vow": "E le na ti pren do_in spo sa",
}
VITTORIO_LINES = {
    1: [("Elena, sei mia per sempre.", "Elena, you are mine forever."),
        ("Io nel cuore ti rimango.", "I remain within your heart."),
        ("Nessun luogo ti nasconde", "No place can hide you"),
        ("dal tuo sposo, tuo signore.", "from your husband, your lord.")],
    2: [("Elena, mi porti dentro,", "Elena, you carry me within,"),
        ("come ferro nel tuo petto.", "like iron in your breast."),
        ("Fuggi pure: in te dimoro,", "Flee if you like: in you I dwell,"),
        ("tuo padrone, tuo respiro.", "your master, your breath.")],
    3: [("Elena, ogni cosa è spenta:", "Elena, every light is out:"),
        ("il bambino, l'altro, il fuoco.", "the child, the other one, the fire."),
        ("Solo io resto nel silenzio,", "Only I remain in the silence,"),
        ("tuo principio, tua rovina.", "your beginning, your ruin.")],
    4: [("Elena, sei mia per sempre.", "Elena, you are mine forever.")],
    "vow": [("Elena, ti prendo in sposa.", "Elena, I take you as my wife.")],
}

# ---------------------------------------------------------------------------------------------
# 3. MARCO'S MOTIF   "Ti scriverò" (I will write).  G major.
#    A rising sixth, then it climbs to the fourth degree and hangs there over the dominant.
#    It never resolves... until his letter arrives in Act III, scene 3, when C finally falls to B.
#    After Tommaso's death the score loses the pitch A, so the letter version is in G-flat.
# ---------------------------------------------------------------------------------------------
MARCO = "D4:.5 B4:1.5 A4:.5 C5:1.5"                    # 4 beats incl. pickup, hangs on C5
MARCO_LYR = "Ti scri ve rò"
MARCO_WARPED = "D4:.5 Bb4:1.5 A4:.5 C#5:1.5"          # Act III: minor sixth, augmented pull
MARCO_LETTER = "Db4:.5 Bb4:1.5 Ab4:.5 Cb5:1.5 Bb4:4"   # G-flat major: it resolves, too late

# ---------------------------------------------------------------------------------------------
# 4. TOMMASO'S TONE   A4 = 440 Hz. A cello natural harmonic (A string, octave node), doubled
#    when he is present by a cor anglais without vibrato. First heard as the oboe's tuning A.
# ---------------------------------------------------------------------------------------------
TOMMASO = 69

# ---------------------------------------------------------------------------------------------
# 5. DAVIDE'S MUSIC   F major, plain crotchet motion, plagal cadences, an F pedal: a home.
#    A (Tommaso) is the third of his chord. After the child's death his F loses its third.
# ---------------------------------------------------------------------------------------------
DAVIDE_ARIA = (
    "C3:.5 D3:.5 F3:.75 E3:.25 F3:.5 G3:.5 A3:.5 G3:.5 | "
    "A3:.5 G3:.5 F3:.75 E3:.25 D3:.5 E3:.5 D3:.5 C3:.5 | "
    "F3:.5 G3:.5 A3:.75 G3:.25 A3:.5 Bb3:.5 C4:.5 Bb3:.5 | "
    "A3:.5 G3:.5 F3:.75 D3:.25 C3:.5 E3:.5 G3:.5 F3:.5"
)
DAVIDE_ARIA_LYR = ("non co no sco le pa ro le dei po e ti_e dei te no ri "
                   "non è_un so gno non è_un can to è_u na ca sa_è_un pa ne cal do")
DAVIDE_ARIA_HARM = ("F:2 F/A:1 Bb:1 | F/C:2 C:1 C7:1 | F:2 C7/G:1 F/A:1 | Bb:1 F/C:1 C7:1 F:1")
DAVIDE_LINES = [
    ("Non conosco le parole", "I do not know the words"),
    ("dei poeti e dei tenori;", "of poets and of tenors;"),
    ("non è un sogno, non è un canto:", "it is not a dream, it is not a song:"),
    ("è una casa, è un pane caldo.", "it is a home, a warm loaf of bread."),
]
