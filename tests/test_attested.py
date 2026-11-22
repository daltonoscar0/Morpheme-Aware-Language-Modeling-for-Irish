"""Run the analyzer over every attested mutated token mined from IDT.

A row passes when demutate(surface) offers a candidate with the right tag
that round-trips exactly back to the surface. Failures land in
tests/failures_attested.tsv for triage; the assertion itself only demands
a 99% floor, since any treebank has annotation errors and the occasional
row that needs actual judgment — those go into QUESTIONS.md instead of
being quietly absorbed here.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mutations import demutate, MUTATE, inverse_ok                      # noqa: E402

HERE = os.path.dirname(__file__)
TSV = os.path.join(HERE, "attested_mutations.tsv")
FAIL = os.path.join(HERE, "failures_attested.tsv")


def row_passes(surface, lemma, tag):
    """A tag-matching candidate exists that inverts exactly.

    Note we don't require the base to share the lemma's initial — suppletion
    (bhfuil/bí, chuaigh/téigh, mhná/bean) breaks that link, and connecting
    surface to lemma is the morphology layer's job anyway. The mismatches
    do still get counted below, as a suppletion/annotation diagnostic.
    """
    for t, base in demutate(surface, strict=True):
        if t == tag and inverse_ok(t, base, surface):
            return True
    return False


def lemma_initial_matches(surface, lemma, tag):
    for t, base in demutate(surface, strict=True):
        if t == tag and base[:1].lower() == lemma[:1].lower():
            return True
    return False


class TestAttested(unittest.TestCase):
    def test_attested_forms(self):
        if not os.path.exists(TSV):
            self.skipTest("run scripts/gen_tests.py first")
        rows, fails = [], []
        with open(TSV, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or not line.strip():
                    continue
                surface, lemma, upos, tag, split = line.rstrip("\n").split("\t")
                rows.append((surface, lemma, upos, tag, split))
                if not row_passes(surface, lemma, tag):
                    fails.append((surface, lemma, upos, tag, split))
        with open(FAIL, "w", encoding="utf-8") as fh:
            fh.write("# surface\tlemma\tupos\ttag\tsplit\n")
            for r in fails:
                fh.write("\t".join(r) + "\n")
        rate = 1 - len(fails) / max(len(rows), 1)
        suppl = sum(1 for r in rows if row_passes(r[0], r[1], r[3])
                    and not lemma_initial_matches(r[0], r[1], r[3]))
        print(f"\nattested: {len(rows) - len(fails)}/{len(rows)} "
              f"pass ({rate:.2%}); failures -> {FAIL}; "
              f"lemma-initial mismatches (suppletion diag): {suppl}")
        self.assertGreaterEqual(rate, 0.99,
                                f"{len(fails)} failures; see {FAIL}")


VARIANTS = os.path.join(HERE, "orthographic_variants.tsv")


class TestOrthographicVariants(unittest.TestCase):
    """The spelling edge cases, kept apart from the treebank rows.

    These are constructed from docs/mutation_case_matrix.md rather than mined,
    so they are held to 100% instead of the attested file's 99% floor: a
    failure here is a bug, not an annotation judgement. The split column
    carries the expectation ('edge' must analyse, 'negative' must not).
    """

    def test_orthographic_variants(self):
        if not os.path.exists(VARIANTS):
            self.skipTest("tests/orthographic_variants.tsv missing")
        pos, neg, pos_fail, neg_fail = 0, 0, [], []
        with open(VARIANTS, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or not line.strip():
                    continue
                surface, lemma, upos, tag, split = line.rstrip("\n").split("\t")
                if split == "negative":
                    neg += 1
                    # demutate() must not raise and must offer nothing.
                    if demutate(surface, strict=True):
                        neg_fail.append(
                            (surface, demutate(surface, strict=True)))
                else:
                    pos += 1
                    if (tag, lemma) not in demutate(surface, strict=True):
                        pos_fail.append((surface, tag, lemma,
                                         demutate(surface, strict=True)))
                    elif not inverse_ok(tag, lemma, surface):
                        pos_fail.append((surface, tag, lemma, "inverse_ok"))
        print(f"\northographic variants: {pos - len(pos_fail)}/{pos} positive, "
              f"{neg - len(neg_fail)}/{neg} negative")
        self.assertEqual(pos_fail, [], f"positive cases failed: {pos_fail}")
        self.assertEqual(neg_fail, [], f"negative cases gained a reading: "
                                       f"{neg_fail}")


if __name__ == "__main__":
    unittest.main()
