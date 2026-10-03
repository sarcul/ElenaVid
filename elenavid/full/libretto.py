"""Parse opera/01_libretto.md into acts, scenes, numbers, sung lines and stage directions.

The libretto file is the authoritative text of the opera; the full score sets every sung line in it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import ROOT

LIBRETTO = ROOT / "opera" / "01_libretto.md"

SPEAKERS = {
    "ELENA": "elena", "MARCO": "marco", "VITTORIO": "vittorio", "DAVIDE": "davide",
    "LA MADRE": "madre", "NIVES": "nives", "UN FERROVIERE": "ferroviere", "CORO": "coro",
    "TOMMASO": "tommaso", "ELENA, DAVIDE": "elena+davide", "ELENA, MARCO": "elena+marco",
}


@dataclass
class Line:
    speaker: str          # performer id ('elena', 'coro', 'elena+davide', ...)
    it: str               # Italian (or Latin) as written
    en: str
    note: str = ""        # the speaker's annotation, e.g. 'a parte', 'in visione', 'fuori scena'
    verse: int = 0        # Latin verse number for the Stabat Mater (I-V), else 0
    latin: bool = False   # sung in ecclesiastical Latin (the table is headed 'Latino')


@dataclass
class Direction:
    it: str
    en: str


@dataclass
class Number:
    key: str              # 'N1' ... 'N22', or 'R1', 'R2'... for the unnumbered scenes
    title: str
    act: int
    scene: int
    setting: str = ""     # the scene's italic description
    preface: str = ""     # italic text directly under the number heading
    items: list = field(default_factory=list)   # Line | Direction, in order

    def lines(self, speaker=None):
        return [x for x in self.items if isinstance(x, Line) and (speaker is None or x.speaker == speaker)]


_ROMAN = {"PRIMO": 1, "SECONDO": 2, "TERZO": 3}
_SCENE = {"prima": 1, "seconda": 2, "terza": 3}
_VERSE_RE = re.compile(r"^\*(I|II|III|IV|V)\.\*\s*")
_VNUM = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}


def _cells(row: str):
    parts = [p.strip() for p in row.strip().strip("|").split("|")]
    return parts if len(parts) >= 2 else None


def _plain(s: str) -> str:
    return s.replace("**", "").replace("*", "").strip()


def parse(path: Path = LIBRETTO) -> list[Number]:
    text = path.read_text(encoding="utf-8")
    numbers: list[Number] = []
    act = 0
    scene = 0
    setting = ""
    cur: Number | None = None
    speaker = ""
    note = ""
    unnumbered = 0
    pending_setting = False
    latin = False
    for raw in text.splitlines():
        line = raw.rstrip()
        m = re.match(r"^# ATTO (PRIMO|SECONDO|TERZO)", line)
        if m:
            act = _ROMAN[m.group(1)]
            scene = 0
            continue
        m = re.match(r"^## Scena (prima|seconda|terza)", line)
        if m:
            scene = _SCENE[m.group(1)]
            pending_setting = True
            continue
        if pending_setting and line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            setting = _plain(line)
            pending_setting = False
            continue
        m = re.match(r"^### (.+)$", line)
        if m and act:
            head = m.group(1).strip()
            nm = re.match(r"^N\. (\d+): (.+)$", head)
            if nm:
                key, title = f"N{int(nm.group(1))}", nm.group(2)
            else:
                unnumbered += 1
                key, title = f"R{unnumbered}", head
            cur = Number(key, title, act, scene, setting)
            numbers.append(cur)
            speaker, note = "", ""
            continue
        if cur is None:
            continue
        if line.startswith("*") and line.endswith("*") and not line.startswith("**") and "|" not in line:
            cur.preface = (cur.preface + " " + _plain(line)).strip()
            continue
        if not line.startswith("|"):
            continue
        cells = _cells(line)
        if cells and cells[0] in ("Italiano", "Latino"):
            latin = cells[0] == "Latino"
            continue
        if not cells or set(cells[0]) <= set("-: "):
            continue
        it, en = cells[0], cells[1]
        if it.startswith("**"):
            # a speaker row: '**ELENA** *(a parte)*'
            m = re.match(r"^\*\*(.+?)\*\*\s*(?:\*\((.+?)\)\*)?", it)
            name = m.group(1).strip()
            speaker = SPEAKERS.get(name, name.lower())
            note = (m.group(2) or "").strip()
            continue
        if it.startswith("*(") or (it.startswith("*") and it.endswith("*") and not _VERSE_RE.match(it)):
            cur.items.append(Direction(_plain(it), _plain(en)))
            continue
        verse = 0
        mv = _VERSE_RE.match(it)
        if mv:
            verse = _VNUM[mv.group(1)]
            it = it[mv.end():]
            en = _VERSE_RE.sub("", en)
        if it.startswith("*") and it.endswith("*"):      # the letter: italic, unsung
            cur.items.append(Direction(_plain(it), _plain(en)))
            continue
        it = it.replace("*", "").strip()
        en = en.replace("*", "").strip()
        if speaker == "tommaso":                          # '(la sua nota)'
            cur.items.append(Direction(it, en))
            continue
        cur.items.append(Line(speaker, it, en, note, verse, latin))
    return numbers


def by_key(numbers=None) -> dict[str, Number]:
    return {n.key: n for n in (numbers or parse())}


if __name__ == "__main__":
    nums = parse()
    total = 0
    for n in nums:
        ls = n.lines()
        total += len(ls)
        print(f"{n.key:4s} A{n.act} S{n.scene}  {len(ls):3d} lines  {n.title}")
    print("sung lines:", total)
