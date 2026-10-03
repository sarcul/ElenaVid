# Elena: the score

### *Tragedia lirica in tre atti*: composer's notes and the film score

## Executive summary

The music was composed in the order the treatment demands: the **wedding melody first**, then **Vittorio's vision-phrase**, then the libretto, then everything else. The opera rests on five governing ideas, each a musical device rather than a mood:

1. **The wedding melody** (*"Sia per sempre"*): a village furlana in D major. In Act III it returns slowed into F minor in the cellos beneath the *Stabat Mater*, fragmenting and re-forming exactly as the treatment specifies. In the final aria it returns untouched, in D♭ major, as memory.
2. **Vittorio's phrase**: one A♭-major melody, identical in pitch and rhythm on every appearance, while only the words descend (husband, then parasite, then ruin). The accompaniment thins from full strings and harp, to low strings and a single horn, to a lone A♭ pedal, to nothing.
3. **Tommaso's tone**: A4 (440 Hz), a cello harmonic. It is the first sound in the film, because the oboe's tuning A *is* his note. His death is the moment that note fails to return. The cadence it should complete arrives as a bare fifth, F and C, with no third.
4. **The lost note**: after the funeral the score never again sounds the pitch class A. This is enforced by the build: the score fails validation if an A appears after the Requiem. Davide's F major loses its third. Marco's letter is written in G♭. The final aria is in D♭, the key without A.
5. **Marco's motif** (*"Ti scriverò"*, "I will write"): it rises a sixth and hangs on the fourth degree, unresolved, every time. It resolves only once, when his letter finally arrives in Act III and detonates everything.

All the music is data in [`elenavid/compose/`](../elenavid/compose/): 5,014 notes over twelve sections, exported by `elenavid score` as `output/midi/elena_film_score.mid`. The engraved themes are in [`score_themes.html`](score_themes.html).

---

## The governing themes

### 1. The wedding melody, *"Sia per sempre"* (composed first)

D major, 6/8, *tempo di furlana* (dotted crotchet = 66). The furlana is the Friulian and Venetian couple-dance in 6/8, so the tune is native to the opera's own region.

```abc
X:1
T:Coro nuziale "Sia per sempre"
M:6/8
L:1/8
Q:3/8=66
K:D
F2G A2d | c2B A2F | G2A B2e | d2c B2A | F2G A2d | f2e d2B | B2c d2B | A d2 c2 d |
w: Suo-nin le cam-pa-ne~a fe-sta cor-ra~il vi-no per la vi-a fio-ri bian-chi sul-la te-sta Dio vi guar-di~e co-sì si-a
A2d a2g | f2e d2c | B2c d2e | f2g a3 | A2d b2a | g2f e2d | f2e d2B | A2c d3 |]
w: Sia per sem-pre sia per sem-pre ciò che~il cie-lo~in ter-ra~u-nì sia per sem-pre sia per sem-pre sia per sem-pre~il vo-stro sì
```

**Why it is built this way:**

| Feature | Purpose |
|---|---|
| Verse in sequence (bars 1-4 rise by step: A-D, then B-E) | Sequence is the most memorable melodic device; the verse is a dance anyone can hum |
| The refrain's octave leap A4-D5-A5 on *"Sia per SEM-pre"* | The hook: a single, joyful shout, recognisable from three notes, which is why it survives fragmentation in Act III |
| A scale climbing to A5 on *"ciò che il cielo"* ("what heaven joined") | Word-painting: the line climbs to heaven |
| F major under the held A5 (bar 12), then straight to D major | A chromatic-mediant "sunburst": the goosebump chord |
| The peak B5 over G major (bar 13) | A plagal glow, the warmth of a hymn, at the climax |
| The vow "*il vostro sì*" ("your yes") on the cadence | The opera's central word ends its central tune |

**Its transformations:**

| Where | Form |
|---|---|
| Act I.2, the wedding | Full chorus SATB, furlana strings, horns, bells rung in rotation (D-A-F♯-D) |
| Act III.1, *Stabat Mater* | Remapped to F harmonic minor, two octaves down in the cellos at dotted crotchet = 40. Full for verse 1; fragmenting for verses 2 and 8 (only the downbeats survive); fully stated again for verse 9 (*Eia, Mater*), when the refrain is heard in minor; dissolving for verse 14 into a single unresolved chord (D♭maj7 over F). |
| Final aria, the dolly-in | The refrain in the horns in D♭ major, untouched, beneath Elena's cantabile *"e lui, Vittorio, sull'altare, bello: era il mio sogno"* |

The minor remap turns bar 10 (*F♯ E D C♯*) into the classic lament tetrachord (*F E D C♯* over a falling bass): the wedding was always one step from a lament.

### 2. Vittorio's phrase

A♭ major, 4/4, *Andante con moto* (crotchet = 80). Baritone, E♭3 to F4. A key with no A natural: his world turns Tommaso's A into A♭.

```abc
X:2
T:Vittorio's phrase (identical on every appearance)
M:4/4
L:1/8
Q:1/4=80
K:Ab clef=bass
C3 B, A,2 G,2 | {D}C3 A, E2 D2 | D2 C2 B,3 A, | G, A, F,4 E,2 |
w: È-le-na sei mia per sem-pre Io nel cuo-re ti ri-man-go
E, A, C4 E2 | D2 E2 F3 E | D2 C2 B,3 C | D2 B,2 G,2 A,2 |]
w: Nes-sun luo-go ti na-scon-de dal tuo spo-so tuo si-gno-re
```

- Bar 2's *"per SEM-pre"* (A♭, E♭, D♭) rises a fifth and falls a step. That is the same shape as the wedding's *"per SEM-pre"* (D, A, G): the village's blessing and the husband's claim are the same gesture.
- At the wedding his vow, *"Elena, ti prendo in sposa"*, is sung to bars 1-2. Elena's *"Sì"* on C5 resolves his dominant to the tonic: her yes completes his cadence. The orchestra then lifts a semitone (A♭ to A7) into the D-major chorus.
- The descent of the words, set to unchanging notes:

| Appearance | Line 1 | Accompaniment |
|---|---|---|
| Vow (I.2) | *Elena, ti prendo in sposa* | organ, warm |
| 1. Nightmare (II.2) | *Elena, sei mia per sempre* | muted strings, harp, solo cello a third below |
| 2. Vision (III.1) | *Elena, mi porti dentro* | low strings, one inner voice, one horn |
| 3. Offstage (final aria) | *Elena, ogni cosa è spenta* | a single low A♭ pedal |
| 4. Offstage (final aria) | *Elena, sei mia per sempre* | nothing: unaccompanied |

### 3. Marco's motif, *"Ti scriverò"*

```abc
X:3
T:Marco's motif: the promise that hangs
M:4/4
L:1/8
K:G
D | B3 A c4- | c4 z4 |]
T:...and the letter, at last (G-flat major, after the A has gone)
K:Gb
D | B3 A c3 | B8 |]
```

A rising sixth, then it climbs to the fourth degree and stops over the dominant. In Act I it is the promise to write; nine years of unsent letters live in that unresolved C. In Act III it grows warped and dominant (minor sixth, an augmented pull to C♯ that becomes the D♭ of A♭'s dominant, leading straight into Vittorio's second vision). It resolves (C♭ to B♭) exactly as Davide reads aloud *"Da quella notte, in casa mia..."*. The long-awaited resolution arrives at the worst moment imaginable: Marco as catalyst, never author.

### 4. Tommaso's tone

A4. Played as a cello natural harmonic (A string, octave node): almost a sine, glassy, with no vibrato. A cor anglais doubles it in some scenes, and a boy treble sings it once, when the child wakes after the blow.

- **Prologue:** the oboe gives the A and the orchestra tunes to it. The film's first sound is the child, before anyone knows it.
- **Lullaby (I.3):** A is the third of F major, the warm island in the cold house.
- **Davide's home (II.2):** A is the third of F major again; Davide's home holds the child.
- **The death (III.2):** the tone fades at the end of each phrase and returns at the start of the next. At the cadence where it should return as the third of F major, the orchestra plays F and C alone. The listener feels the hollowness before naming it.
- **Requiem (III.3):** it threads through as the dominant of D minor one last time, then is gone, and with it the pitch class A, for the rest of the opera.

### 5. Davide's music

F major, plain crotchet motion, plagal cadences, horns and violas, an F pedal: the sound of an actual home. In Act III scene 3 his music stays warm and never borrows Vittorio's idiom (no A♭, no seductive line, no brass stabs). But it has lost its third (F5, Fsus2, Fsus4, B♭add9/F, C7sus4): a home with the child gone from it.

The treatment's hardest problem, Elena mishearing Davide's grief as Vittorio-like, is solved by the **tier split**. The score tier stays warm and true. Elena's perception lives only in the sound design: a low-pass "tunnel" over score and voices, her panicked breathing, her heartbeat, and a reversed, dissolved ghost of Vittorio's *"Èlena"* from the first vision. The audience hears the truth and understands what she hears.

---

## Key scheme

| Section | Key | Why |
|---|---|---|
| Prologue | the tuning A; D major breath | the child's note first |
| I.1 Village | G major | pastoral; Marco's key |
| I.2 Mother, hope | B minor to D major | the mother's realism opening into hope |
| I.2 Vow | A♭ major | Vittorio's key, a tritone from the wedding |
| I.2 Wedding | D major (via A7) | bright strings, open D and A |
| I.3 Lullaby | F major | A is the third: the child |
| I.3 The blow | E♭ minor with A natural | Vittorio's colour against the child's note |
| I.3 Resolve | D minor over an A pedal | she rests her decision on the child |
| II.1 Platform | A minor to A major | the child's note as tonic; escape |
| II.2 Nightmare | A♭ major | Vittorio |
| II.2 Morning, Davide | F major | the A returns as she wakes into Davide's home |
| II.3 Marco | G major, ending on D7 | the past returns; curtain on an unresolved dominant |
| III.1 Drift | G minor, chromatic | the motif warps toward E♭7, the dominant of A♭ |
| III.1 Vision | A♭ major | the same phrase |
| III.1 *Stabat Mater* | F minor | Pergolesi's key; A has become A♭ |
| III.2 Death | F major to a bare fifth | the missing third |
| III.3 Requiem | D minor | the A sounds for the last time |
| III.3 Letter | G♭ major, B♭ minor | the world without A |
| III.3 Davide | F with no third | warmth without the child |
| Final aria | D♭ major | the key that contains no A |

---

## The film score: ten minutes, twelve sections

| # | Time | Section | Music |
|---|---|---|---|
| S00 | 0:00 | Prologue | Orchestra tunes to the oboe's A (warm-up fragments scatter the opera's motifs through the pit); applause; a D-major breath; solo violin A-D-A, holding the high A under the title |
| S01 | 0:26 | La piazza, 1948 | Market chorus in 2/4 (village oom-pah, clarinet, tambourine); farewell duet; Marco's motif hangs; *Resta la strada bianca* ends on the same unresolved C |
| S02 | 1:00 | Salotto, chiesa, 1950 | Mother's arioso; Elena's hope (her *"sì"* on A5); the vow on Vittorio's phrase; her *"Sì"* resolves it; semitone lift; **the wedding chorus**; the celebration cools to D minor and a celesta |
| S03 | 2:02 | Verona, 1953 | Lullaby in F over Tommaso's first tone; Vittorio, trombones; the blow (tutti E♭ minor with A, tam-tam); the child's note alone; *Basta. Non qui. Non lui. Non più.* |
| S04 | 2:42 | La stazione | The train in the orchestra (cello semiquavers *sul ponticello*, accelerating); *Porto la mia valigia* ends in A major |
| S05 | 3:04 | Trieste, 1955 | Vittorio's phrase, full and seductive; she wakes, A♭ becomes A; Davide's aria; the duet *Piano, come la neve* |
| S06 | 4:06 | Una strada, 1957 | Tremolo shock; confession over sparse clarinet; *(E so che non è vero.)* in both voices; curtain on D7 |
| S07 | 4:36 | Mesi; visione; Stabat | Marco's motif warped and dominant; Vittorio's phrase over thinner strings; the *Stabat Mater* over the wedding melody in F minor, *gladius* as an F-minor-to-E-major shift on a common tone (A♭ = G♯) |
| S08 | 6:04 | Trattoria; il figlio | Café waltz; Nives; the run; the ensemble over the dying child; the bare fifth; silence |
| S09 | 6:48 | Requiem | D minor chorus and organ; funeral bell; the last A |
| S10 | 7:10 | La lettera | Marco's motif resolves in G♭; confession; Davide's grief, warm and forte; *Se restassi, sarei lui*, with no A |
| S11 | 7:56 | Scena ed aria finale | Scena over a D♭ pedal; cantabile with the wedding refrain in the horns (**the dolly-in**); her line echoes in the dome (**the wide shot**); Vittorio offstage over a lone A♭; the unbroken line to D♭6 on *"sempre"* (**the close-up**); Vittorio unaccompanied; *C'era il sole, quel giorno, e mi bastava*; D♭ major; curtain |

## Orchestra

Strings 8.7.5.5.3 (every player individually modelled), flute, oboe, cor anglais, clarinet, bassoon, horns, trumpet (with mute), trombones, timpani, bass drum, tam-tam, suspended cymbal, triangle, tambourine, tubular bells, church bell, celesta, harp, organ. Voices: soprano, mezzo-soprano (two roles), tenor (two roles), baritone, bass-baritone, boy treble, and an SATB chorus of 24.

The reference frame follows the treatment: Britten, Barber, Poulenc and late Janáček, with a tonal foundation, a conservative orchestra and no electronics.
