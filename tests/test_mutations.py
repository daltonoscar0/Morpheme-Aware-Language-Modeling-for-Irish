"""Grammar-rule tests on citation forms, plus FST parity and the
demutation round-trip invariants. Plain stdlib unittest."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mutations import (lenite, eclipse, h_prefix, t_prefix, demutate,     # noqa
                       analyze, MUTATE, fst_mutate, TAGS)

LEN = [  # (base, attested lenited form)
    ("bean", "bhean"), ("cóta", "chóta"), ("doras", "dhoras"),
    ("fear", "fhear"), ("gairdín", "ghairdín"), ("máthair", "mháthair"),
    ("póca", "phóca"), ("teach", "theach"),
    ("súil", "shúil"), ("sráid", "shráid"), ("slat", "shlat"),
    ("sneachta", "shneachta"),
    ("Conradh", "Chonradh"), ("Gaillimh", "Ghaillimh"), ("Seán", "Sheán"),
]
LEN_BLOCKED = ["scoil", "smaoineamh", "spéir", "staidéar",
               "lá", "nead", "rud", "hata", "ábhar", "uisce"]

ECL = [
    ("bó", "mbó"), ("ceist", "gceist"), ("doras", "ndoras"),
    ("fear", "bhfear"), ("gort", "ngort"), ("páirc", "bpáirc"),
    ("tír", "dtír"), ("éan", "n-éan"), ("uisce", "n-uisce"),
    ("Baile", "mBaile"), ("Frainc", "bhFrainc"), ("Tír", "dTír"),
    ("Gaillimh", "nGaillimh"), ("Éire", "nÉire"), ("Albain", "nAlbain"),
]
ECL_BLOCKED = ["lá", "máthair", "nead", "rud", "sráid", "hata"]

HPREF = [
    ("aon", "haon"), ("uimhreacha", "huimhreacha"), ("óige", "hóige"),
    ("Éirinn", "hÉirinn"), ("Éireann", "hÉireann"), ("é", "hé"),
]
HPREF_BLOCKED = ["teach", "sráid", "lá"]

TPREF = [
    ("uisce", "t-uisce"), ("ainm", "t-ainm"), ("arán", "t-arán"),
    ("Athair", "tAthair"), ("Uachtarán", "tUachtarán"),
    ("súil", "tsúil"), ("sráid", "tsráid"), ("slí", "tslí"),
    ("Sín", "tSín"), ("samhlaíocht", "tsamhlaíocht"),
]
TPREF_BLOCKED = ["scoil", "spéir", "teach", "doras", "bean"]


class TestGeneration(unittest.TestCase):
    def check(self, fn, pairs, blocked):
        for base, want in pairs:
            self.assertEqual(fn(base), want, f"{fn.__name__}({base})")
        for base in blocked:
            self.assertEqual(fn(base), base, f"{fn.__name__}({base}) vacuous")

    def test_lenition(self):
        self.check(lenite, LEN, LEN_BLOCKED)

    def test_eclipsis(self):
        self.check(eclipse, ECL, ECL_BLOCKED)

    def test_h_prefix(self):
        self.check(h_prefix, HPREF, HPREF_BLOCKED)

    def test_t_prefix(self):
        self.check(t_prefix, TPREF, TPREF_BLOCKED)


class TestAnalysis(unittest.TestCase):
    def test_round_trip_all(self):
        for tag, pairs in [("Len", LEN), ("Ecl", ECL),
                           ("HPref", HPREF), ("TPref", TPREF)]:
            for base, surface in pairs:
                cands = demutate(surface)
                self.assertIn((tag, base), cands,
                              f"demutate({surface}) missing ({tag},{base})")

    def test_genuine_h_word_keeps_identity(self):
        # 'hata' (hat) genuinely starts with h, the unmutated reading has
        # to survive alongside the HPref-of-'ata' candidate
        cands = analyze("hata")
        self.assertIn(("none", "hata"), cands)
        self.assertIn(("HPref", "ata"), cands)

    def test_overgeneration_is_exact_inverse(self):
        for w in ["bhfear", "shráid", "n-éan", "tsúil", "dtír", "nGaillimh",
                  "chat", "hÉireann", "t-uisce", "ngort", "mbliana"]:
            for tag, base in demutate(w):
                self.assertEqual(MUTATE[tag](base), w)

    def test_no_false_ts_before_blocked_cluster(self):
        # tsc- isn't a possible t-prefix shape, so no TPref reading here
        self.assertNotIn("TPref", [t for t, _ in demutate("tscoil")])


class TestOrthographyTracks(unittest.TestCase):
    def test_all_caps_generation(self):
        self.assertEqual(MUTATE["Len"]("BLIAIN"), "BHLIAIN")
        self.assertEqual(MUTATE["Ecl"]("FUIL"), "BHFUIL")
        self.assertEqual(MUTATE["Ecl"]("BRIATHAR"), "MBRIATHAR")

    def test_all_caps_analysis(self):
        self.assertIn(("Ecl", "FUIL"), demutate("BHFUIL"))
        self.assertIn(("Len", "BLIAIN"), demutate("BHLIAIN"))

    def test_variant_analysis(self):
        # hyphen before capital (Comhairle na n-Ealaíon style)
        self.assertIn(("Ecl", "Ealaíon"), demutate("n-Ealaíon"))
        # pre-standard hyphenated h-prefix
        self.assertIn(("HPref", "aoise"), demutate("h-aoise"))
        self.assertIn(("HPref", "Íde"), demutate("h-Íde"))
        # signage style: lowercase prefix on all-caps base
        self.assertIn(("TPref", "AONTAS"), demutate("tAONTAS"))

    def test_canonical_generation_unchanged(self):
        # variants are analysis-only; generation stays Caighdeán
        self.assertEqual(MUTATE["Ecl"]("Ealaíon"), "nEalaíon")
        self.assertEqual(MUTATE["HPref"]("aoise"), "haoise")


class TestEngineParity(unittest.TestCase):
    def test_fst_matches_direct_functions(self):
        words = ([b for b, _ in LEN + ECL + HPREF + TPREF]
                 + LEN_BLOCKED + ECL_BLOCKED + HPREF_BLOCKED + TPREF_BLOCKED)
        for tag in TAGS:
            for w in words:
                self.assertEqual(fst_mutate(tag, w), MUTATE[tag](w),
                                 f"parity {tag}({w})")


if __name__ == "__main__":
    unittest.main()
