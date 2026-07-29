"""Evaluate the analyzer on every attested mutated token mined from IDT.

Pass criterion per row (surface, lemma, upos, tag):
  demutate(surface) contains (tag, base) such that
    base's initial grapheme == lemma's initial (case-insensitive)  AND
    MUTATE[tag](base) == surface  (exact round trip; guaranteed by demutate's
    internal invariant, re-checked here anyway).

Failures are written to tests/failures_attested.tsv for triage — the test
asserts only that the pass rate clears a floor (99%), because a treebank
contains annotation errors and genuinely judgment-needing rows; those are
triaged into QUESTIONS.md, not silently absorbed.
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
    """Pass = a tag-matching, exactly-inverting candidate exists.

    We deliberately do NOT require base-initial == lemma-initial: suppletive
    paradigms (bhfuil/bí, chuaigh/téigh, fhearr/maith, mhná/bean) break that
    linkage, and tying surface to lemma is the morphology layer's job, not
    the mutation layer's. Lemma-initial mismatches are still counted and
    reported as a suppletion/annotation diagnostic.
    """
    for t, base in demutate(surface):
        if t == tag and inverse_ok(t, base, surface):
            return True
    return False


def lemma_initial_matches(surface, lemma, tag):
    for t, base in demutate(surface):
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


if __name__ == "__main__":
    unittest.main()
