"""Mutation-layer coverage on UD Irish-IDT -> RESULTS.md.

Reports, over all three splits:
  1. Round-trip accuracy on mutation-tagged tokens, by tag and by POS.
  2. Ambiguity load: mean demutation candidates per token (all tokens), and
     the share of untagged tokens that nonetheless receive >=1 mutation
     candidate (spurious-candidate rate — the price of no-lexicon
     over-generation, to be paid down by the lexicon layer later).
Note: this is MUTATION-layer coverage only; full analyzer coverage arrives
with declension/conjugation later in Phase 1.
"""
import os
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from conllu import tokens                                    # noqa: E402
from mutations import demutate, inverse_ok                   # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "UD_Irish-IDT")
RESULTS = os.path.join(os.path.dirname(__file__), "..", "RESULTS.md")
MUT_FEATS = {"Len", "Ecl", "HPref"}


def main():
    paths = [os.path.join(DATA, f"ga_idt-ud-{s}.conllu")
             for s in ("train", "dev", "test")]
    by_tag, by_pos = defaultdict(Counter), defaultdict(Counter)
    n_tokens = n_cands = untagged = untagged_with_cand = 0
    for tok in tokens(paths):
        form, feats = tok["form"], tok["featdict"]
        cands = demutate(form)
        n_tokens += 1
        n_cands += len(cands)
        tags = set(feats.get("Form", "").split(",")) & MUT_FEATS
        if not tags:
            untagged += 1
            untagged_with_cand += bool(cands)
            continue
        for tag in tags:
            ok = any(t == tag and inverse_ok(t, b, form) for t, b in cands)
            by_tag[tag][ok] += 1
            by_pos[tok["upos"]][ok] += 1

    def rate(c):
        return c[True] / (c[True] + c[False])

    lines = [f"| {date.today()} | mutation FST (session 1) | "
             f"attested round-trip by tag: "
             + ", ".join(f"{t} {rate(by_tag[t]):.2%} "
                         f"(n={sum(by_tag[t].values())})"
                         for t in ("Len", "Ecl", "HPref"))
             + f"; ambiguity {n_cands / n_tokens:.2f} cand/token, "
               f"spurious-candidate rate {untagged_with_cand / untagged:.1%}"
               " | mutation layer round-trips IDT; ambiguity is the "
               "no-lexicon price |"]
    lines.append("")
    lines.append("### Mutation round-trip by POS "
                 f"({date.today()}, IDT all splits)")
    lines.append("| POS | pass | total | rate |")
    lines.append("|---|---|---|---|")
    for pos in sorted(by_pos, key=lambda p: -sum(by_pos[p].values())):
        c = by_pos[pos]
        lines.append(f"| {pos} | {c[True]} | {sum(c.values())} "
                     f"| {rate(c):.2%} |")
    with open(RESULTS, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
