"""Italian (and ecclesiastical Latin) prosody for setting the libretto to music.

A verse line becomes a list of sung syllables in the notation's lyric format: syllables separated
by spaces, synalepha joined with an underscore ("ne_a": two vowels on one note), so the voice engine
phonemises exactly what the score sings. Each syllable carries a stress weight:
    2  the stressed syllable of a content word
    1  the stressed syllable of a light word (articles, prepositions, clitics, auxiliaries)
    0  unstressed
The line's final stress decides its metre (settenario: last stress on syllable 6, and so on).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

VOW = set("aeiouàèéìíòóùú")
ACC = set("àèéìíòóùú")
STRONG = set("aeoàèéòó")          # a, e, o: two of these adjacent are always a hiatus
WEAK = set("iuìíùú")
ONSET2 = {"bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr", "tr", "vr"}

# stress on the antepenultimate (or on a syllable the default rule would miss): syllable index from
# the end, 1 = last. Built from the libretto's own vocabulary.
LEXICON = {
    "elena": 3, "davide": 3, "rondini": 3, "polvere": 3, "lettera": 3, "lettere": 3, "medico": 3,
    "padova": 3, "piccolo": 3, "portici": 3, "poveri": 3, "restano": 3, "scrivimi": 3, "separa": 3,
    "siediti": 3, "vattene": 3, "dicono": 3, "desidero": 3, "rispondermi": 3, "subito": 3,
    "angelo": 3, "camera": 3, "gemono": 3, "ridono": 3, "credere": 3, "vivere": 3, "piangere": 3,
    "scuote": 2, "scriverai": 1, "guarderai": 1, "ridirei": 1, "aspetteremo": 2, "addio": 1,
    "nessun": 1, "signor": 1, "amor": 1, "dolor": 1, "cuor": 1, "fantasia": 1, "paura": 2,
    "follia": 1, "poesia": 1, "armonia": 1, "linea": 3, "buio": 2,
    "anima": 3, "lacrime": 3, "dimmelo": 3, "portami": 3, "tienimi": 3, "lasciami": 3,
}
LATIN_LEXICON = {
    "animam": 3, "domine": 3, "spiritum": 3, "filius": 3, "gladius": 3, "perpetua": 3,
    "requiem": 3, "luceat": 3, "lugeam": 3, "desidero": 3, "tecum": 2, "tibi": 2, "vidit": 2,
    "suum": 2, "tuis": 2, "quia": 2, "pius": 2, "cuius": 2, "eia": 2, "iuxta": 2, "crucem": 2,
}
# light words: unstressed in the line, whatever their dictionary stress
LIGHT = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da", "in", "con", "su",
    "per", "tra", "fra", "e", "ed", "o", "od", "ma", "se", "che", "non", "mi", "ti", "si", "ci",
    "vi", "ne", "del", "dal", "al", "nel", "sul", "col", "coi", "dei", "ai", "dai", "nei", "sui",
    "della", "dello", "delle", "degli", "alla", "allo", "alle", "agli", "dalla", "dalle", "nella",
    "nelle", "sulla", "sulle", "mio", "mia", "tuo", "tua", "suo", "sua", "miei", "tuoi", "suoi",
    "ho", "hai", "ha", "son", "et", "ut", "cum", "dum", "me", "te", "lui", "quel", "quello",
}
# stressed i/u that forms a hiatus: one sung syllable mid-line (synaeresis), two at line end
HIATUS = {"mia", "mio", "mie", "tua", "tuo", "tue", "sua", "suo", "sue", "dio", "sia", "via",
          "zio", "io"}

_TOKEN = re.compile(r"[A-Za-zÀ-ÿ’']+|[.,;:!?…«»\"()\-–]+")
_SENTENCE = set(".!?…")


@dataclass
class Syl:
    text: str              # as sung, in lyric notation ('ne_a', "d'o")
    stress: int            # 0, 1 or 2
    word: str              # the word this syllable belongs to (the second word for a synalepha)
    word_end: bool         # the syllable ends a word
    pause: str = ""        # punctuation after it (',' ';' ':' '.' '?' '!' '...') - a breath point


def _base(c):
    return unicodedata.normalize("NFD", c)[0].lower()


def _split_word(w: str, latin: bool):
    """Syllabify one word. Returns list of syllable strings (original letters kept)."""
    low = w.lower()
    n = len(low)
    # nuclei: indices of vowel letters that start a vowel group, with glide handling
    is_v = [c in VOW or (latin and c == "y") for c in low]
    # 'u' after q (and after g before a vowel) and 'i' after c/g/sc before a vowel are not nuclei
    for i, c in enumerate(low):
        if c == "u" and i > 0 and low[i - 1] == "q":
            is_v[i] = False
        if not latin and c == "u" and i > 0 and low[i - 1] == "g" and i + 1 < n and low[i + 1] in VOW:
            is_v[i] = False
        if not latin and c == "i" and i > 0 and low[i - 1] in "cg" and i + 1 < n and low[i + 1] in VOW \
                and low[i + 1] not in "iì":
            is_v[i] = False
        if latin and c == "i" and i + 1 < n and low[i + 1] in VOW and (i == 0 or is_v[i - 1]):
            is_v[i] = False      # consonantal i: iuxta, cuius, eia (but not after qu: requiem)
    # group vowels into syllable nuclei
    groups = []                  # (start, end) of each nucleus
    i = 0
    while i < n:
        if not is_v[i]:
            i += 1
            continue
        j = i + 1
        while j < n and is_v[j]:
            a, b = _base(low[j - 1]), _base(low[j])
            if latin:
                if (a, b) in (("a", "e"), ("o", "e"), ("a", "u")):
                    j += 1
                    continue
                break
            # Italian: two strong vowels = hiatus; accented weak vowel = hiatus
            if low[j - 1] in STRONG and low[j] in STRONG:
                break
            # V + i + V: the i glides into the next vowel (bu-io, gio-ia, no-ia); not uoi, iei, uai
            if low[j] == "i" and j + 1 < n and low[j + 1] in VOW and low[j - 1] in "aeouàèòù"                     and low[j - 1:j + 2] not in ("uoi", "iei", "uai"):
                break
            if (low[j] in "ìíùú" and low[j - 1] in STRONG) or (low[j - 1] in "ìíùú" and low[j] in STRONG):
                break
            j += 1
        groups.append((i, j))
        i = j
    if len(groups) <= 1:
        return [w]
    # place boundaries in the consonant runs between nuclei
    cuts = []
    for (s0, e0), (s1, e1) in zip(groups, groups[1:]):
        run = low[e0:s1]
        k = len(run)
        if k == 0:
            cuts.append(e0)
        elif k == 1:
            cuts.append(e0)
        else:
            if run.endswith("i") and not is_v[s1 - 1] and k >= 2:     # cia, gio, scia: diacritic i
                head = run[:-1]
                if head.endswith("sc"):
                    cuts.append(e0 + len(head) - 2)
                elif len(head) >= 2 and head[-2] == head[-1]:          # ggia, ccio
                    cuts.append(e0 + len(head) - 1)
                else:
                    cuts.append(e0 + len(head) - 1)
            elif run[0] == run[1] and run[0] not in "h":          # double consonant: split it
                cuts.append(e0 + 1)
            elif run[0] == "s" or run[:2] in ONSET2 or run[:2] in ("ch", "gh", "gn", "gl", "sc", "qu") \
                    or (run[0] in "cgq" and run[1] in "hu"):
                cuts.append(e0)                                   # s+C, C+l/r and digraphs start the syllable
            elif k >= 3 and (run[1:3] in ONSET2 or run[1] == "s" or run[1:3] in ("ch", "gh", "gn", "sc")):
                cuts.append(e0 + 1)
            else:
                cuts.append(e0 + 1)                              # l/m/n/r + C, and the rest: split after the first
    out, prev = [], 0
    for c in cuts:
        out.append(w[prev:c])
        prev = c
    out.append(w[prev:])
    return [s for s in out if s]


def _word_stress(word: str, sylls: list[str], latin: bool) -> int:
    """Index (0-based) of the stressed syllable."""
    low = word.lower().replace("’", "'").split("'")[-1]
    for k, s in enumerate(sylls):
        if any(c in ACC for c in s.lower()):
            return k
    lex = (LATIN_LEXICON if latin else LEXICON).get(low)
    if lex:
        return max(0, len(sylls) - lex)
    if not latin and len(sylls) >= 2 and (low.endswith("rai") or low.endswith("rei")):
        return len(sylls) - 1                     # futures and conditionals: sarei, scriverai
    if len(sylls) == 1:
        return 0
    return len(sylls) - 2


def syllables(text: str, latin: bool = False) -> list[Syl]:
    """Sung syllables of one verse line, with synalepha (Italian) and stress."""
    toks = _TOKEN.findall(text)
    words = []                      # (word, pause_after)
    for t in toks:
        if re.match(r"[A-Za-zÀ-ÿ’']", t):
            words.append([t, ""])
        elif words:
            p = t.strip("«»\"()-–")
            if p:
                words[-1][1] = (words[-1][1] + p)[:3]
    out: list[Syl] = []
    for wi, (w, pause) in enumerate(words):
        w = w.replace("’", "'")
        pre = ""
        core = w
        if "'" in w and not w.endswith("'"):
            pre, core = w.rsplit("'", 1)
            pre += "'"
        low = core.lower()
        if not latin and low in HIATUS:
            core_sy = [core]                         # synaeresis by default; dieresis at line end below
        else:
            core_sy = _split_word(core, latin)
        if pre and any(c in VOW for c in pre.lower()):
            # anch'io, all'alba, un'altra: the elided word joins the next one's syllables
            joined = _split_word(pre[:-1] + core, latin)
            cut = len(pre) - 1
            sy, pos = [], 0
            for js in joined:
                a, b = pos, pos + len(js)
                sy.append(js[: cut - a] + "'" + js[cut - a:] if a < cut <= b and cut != b else
                          (js + "'" if b == cut else js))
                pos = b
            sy = [x.replace("''", "'") for x in sy]
            k = len(sy) - len(core_sy) + _word_stress(core, core_sy, latin)
        else:
            sy = list(core_sy)
            if pre:
                sy[0] = pre + sy[0]
            k = _word_stress(core, core_sy, latin)
        light = low in LIGHT
        for j, s in enumerate(sy):
            st = (1 if light else 2) if j == k else 0
            out.append(Syl(s, st, low, j == len(sy) - 1, pause if j == len(sy) - 1 else ""))
    if not out:
        return out
    # a light word before a pause is stressed (Non qui. Non lui. Non più.)
    for s in out:
        if s.stress == 1 and s.word_end and s.pause:
            s.stress = 2
    # the rhyme word: its stressed syllable is always strong
    i = len(out) - 1
    while i > 0 and not out[i - 1].word_end:
        i -= 1
    word_syls = out[i:]
    strongest = max(range(len(word_syls)), key=lambda j: word_syls[j].stress)
    word_syls[strongest].stress = 2
    # dieresis at the end of the line: 'via' -> vi-a, 'mia' -> mi-a, 'sia' -> si-a
    last = out[-1]
    lw = last.word
    if not latin and lw in HIATUS and len(lw) >= 3 and last.text.lower().endswith(lw):
        stem = last.text[:-1]
        out[-1:] = [Syl(stem, last.stress, lw, False), Syl(last.text[-1], 0, lw, True, last.pause)]
    if latin:
        return out
    # synalepha: word-final vowel + word-initial vowel (or h+vowel) on one note
    merged: list[Syl] = []
    for s in out:
        if merged:
            p = merged[-1]
            p_last = p.text.lower().rstrip("'")[-1:]
            s_first = s.text.lower().lstrip("'")
            s_first = s_first[1:] if s_first.startswith("h") else s_first
            joinable = (p.word_end and p_last in VOW and s_first[:1] in VOW
                        and not any(c in _SENTENCE for c in p.pause)
                        and not (p_last in ACC and s.stress == 2 and s_first[:1] in ACC)
                        and p.text.count("_") < 2)
            if joinable:
                merged[-1] = Syl(p.text + "_" + s.text, max(p.stress, s.stress), s.word, s.word_end,
                                 s.pause)
                continue
        merged.append(s)
    return merged


def lyric(syls: list[Syl]) -> str:
    """The notation's lyric string for these syllables."""
    return " ".join(s.text.replace(" ", "") for s in syls)


def last_stress(syls: list[Syl]) -> int:
    for i in range(len(syls) - 1, -1, -1):
        if syls[i].stress == 2:
            return i
    for i in range(len(syls) - 1, -1, -1):
        if syls[i].stress >= 1:
            return i
    return len(syls) - 1


def metre(syls: list[Syl]) -> int:
    """Italian verse length: position of the last stress plus one (settenario = 7)."""
    return last_stress(syls) + 2


def is_latin(text: str) -> bool:
    return bool(re.search(r"\b(stabat|mater|requiem|domine|aeternam|lux|iuxta|crucem|cuius|eia|vidit)\b",
                          text.lower()))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    from .libretto import parse, Line
    for n in parse():
        for x in n.items:
            if isinstance(x, Line):
                lat = x.latin
                sy = syllables(x.it, latin=lat)
                marks = " ".join(("ˈ" if s.stress == 2 else "ˌ" if s.stress == 1 else "") + s.text for s in sy)
                print(f"{n.key:4s} {len(sy):2d} m{metre(sy):2d}  {marks}")
