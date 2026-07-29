"""Mine UD Irish-IDT for attested mutation test cases.

Writes tests/attested_mutations.tsv (surface, lemma, upos, tag, split).
Len/Ecl/HPref rows come straight off the Form= feature. IDT doesn't mark
the t-prefix, so those rows are pattern-mined instead: the surface has to
look like t-V, t+CapV, or t+s+follower. Every mutated token in the
treebank becomes a row — nothing gets filtered out just because we expect
to fail it. tests/test_attested.py does the actual evaluation.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from conllu import tokens                                   # noqa: E402
from mutations import VOWELS, S_FOLLOWERS                   # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "UD_Irish-IDT")
OUT = os.path.join(os.path.dirname(__file__), "..", "tests",
                   "attested_mutations.tsv")

MUT_FEATS = {"Len", "Ecl", "HPref"}


def is_tpref_surface(form: str, lemma: str) -> bool:
    if len(form) < 3 or form[0] != "t":
        return False
    if form[1] == "-" and form[2].lower() in VOWELS and form[2].islower():
        return lemma[:1].lower() == form[2].lower() or True  # inflection may differ
    if form[1].lower() in VOWELS and form[1].isupper():
        return True
    if form[1] == "s" and form[2].lower() in S_FOLLOWERS:
        return lemma[:1].lower() == "s"
    return False


def main():
    rows = []
    for split in ("train", "dev", "test"):
        path = os.path.join(DATA, f"ga_idt-ud-{split}.conllu")
        for tok in tokens([path]):
            form, lemma, upos = tok["form"], tok["lemma"], tok["upos"]
            feats = tok["featdict"]
            tags = set(feats.get("Form", "").split(",")) & MUT_FEATS
            for tag in sorted(tags):
                rows.append((form, lemma, upos, tag, split))
            if not tags and is_tpref_surface(form, lemma):
                rows.append((form, lemma, upos, "TPref", split))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("# surface\tlemma\tupos\ttag\tsplit\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    print(f"wrote {len(rows)} attested test rows -> {OUT}")


if __name__ == "__main__":
    main()
