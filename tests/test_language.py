"""The note language and the Italian/Latin prosody that the composer relies on."""
import unittest

from elenavid.full.prosody import syllables
from elenavid.notation import parse


def sung(text, latin=False):
    return [(s.text, s.stress) for s in syllables(text, latin=latin)]


class Notation(unittest.TestCase):
    def test_notes_and_rests(self):
        evs = parse("D4:.5 B4:1.5 r:1 A4:.5 C5:1.5")
        self.assertEqual([(e.beat, e.dur, e.midi) for e in evs],
                         [(0.0, 0.5, 62), (0.5, 1.5, 71), (3.0, 0.5, 69), (3.5, 1.5, 72)])


class Prosody(unittest.TestCase):
    def test_italian_stress(self):
        self.assertEqual(sung("Resta la strada"), [("Re", 2), ("sta", 0), ("la", 1), ("stra", 2), ("da", 0)])
        self.assertEqual(sung("Dormi, Tommaso"), [("Dor", 2), ("mi", 0), ("Tom", 0), ("ma", 2), ("so", 0)])

    def test_synalepha_joins_vowels_across_words(self):
        self.assertEqual(sung("come un fiore"), [("co", 2), ("me_un", 1), ("fio", 2), ("re", 0)])

    def test_diphthong(self):
        self.assertEqual(sung("Addio"), [("Ad", 0), ("dio", 2)])

    def test_latin_stress(self):
        self.assertEqual(sung("Stabat mater dolorosa", latin=True),
                         [("Sta", 2), ("bat", 0), ("ma", 2), ("ter", 0), ("do", 0), ("lo", 0), ("ro", 2), ("sa", 0)])


if __name__ == "__main__":
    unittest.main()
