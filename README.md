# Seanchaí — morpheme-aware language modelling for Irish

[![tests](https://github.com/daltonoscar0/Morpheme-Aware-Language-Modeling-for-Irish/actions/workflows/tests.yml/badge.svg)](https://github.com/daltonoscar0/Morpheme-Aware-Language-Modeling-for-Irish/actions/workflows/tests.yml)

A finite-state treatment of Irish initial mutations, built to ask whether a
morpheme-aware tokenizer beats BPE on a morphologically rich, lower-resource
language. **Phase 1 — the mutation layer — is done and tested. The tokenizer
comparison and the language-model comparison are not yet built.**

Irish mutates the start of a word rather than only the end, so a subword
tokenizer trained on surface forms sees `fear`, `fhear` and `bhfear` as three
unrelated strings. This repository implements the four mutations in both
directions, so those three can be related back to one lemma.

| Tag | Mutation | Example |
|---|---|---|
| `Len` | séimhiú (lenition) | `grian` → `ghrian` |
| `Ecl` | urú (eclipsis) | `fear` → `bhfear` |
| `HPref` | h-prefix | `éan` → `héan` |
| `TPref` | t-prefix | `solas` → `tsolas` |

## Results

Measured against UD Irish-IDT, all splits. Source: [RESULTS.md](RESULTS.md).

| Date | What | Result |
|---|---|---|
| 2026-07-27 | Mutation FST, round-trip on attested forms | `Len` 99.99% (n=11,825), `Ecl` 100.00% (n=4,094), `HPref` 100.00% (n=860) |
| 2026-07-27 | Ambiguity load, no lexicon | 0.17 candidates/token; 1.8% spurious-candidate rate |
| 2026-07-29 | C++17 port onto Scalpel | 17,200/17,201 attested, exact parity with the Python reference |

Round-trip accuracy is at or near 100% for every part of speech with more than
one attested form (NOUN 10,094/10,095; VERB 3,981/3,981; PROPN 1,318/1,318;
ADJ 926/926 — the full table is in [RESULTS.md](RESULTS.md)).

The honest caveat is the ambiguity number, not the accuracy number. Analysis
deliberately over-generates: with no lexicon to filter candidates, 1.8% of
untagged tokens still pick up a spurious reading. `PLAN.md` records that as the
price of running without a lexicon, to be paid down by a later lexicon layer.

### The one failure

17,200 of 17,201 is one failing row, recorded in
[tests/failures_attested.tsv](tests/failures_attested.tsv):

```
surface  lemma                 upos  tag  split
fíor-    fíor-chorr-Óglach     NOUN  Len  dev
```

A `goeswith` artifact — a hyphenated compound split across tokens in the
treebank, where the surface fragment cannot round-trip to the full lemma. It is
a treebank tokenization edge case rather than a mutation-rule error. `PLAN.md`
tracks it as a known failure (QUESTIONS.md #9).

TODO(oscar): `PLAN.md` and the test suite both cite `QUESTIONS.md`, which is not
in this repository.

## Layout

```
src/mutations.py          # reference implementation: rule tables, FST, foma emission
src/triggers.py           # trigger table (which contexts cause which mutation)
src/conllu.py             # CoNLL-U reader for UD Irish-IDT
tests/test_mutations.py   # grammar-rule, parity and round-trip tests
tests/test_attested.py    # evaluates the 17,201 mined cases
tests/attested_mutations.tsv   # the mined cases (surface, lemma, upos, tag, split)
tests/failures_attested.tsv    # rows that do not round-trip
scripts/gen_tests.py      # mines UD Irish-IDT to produce attested_mutations.tsv
scripts/coverage_report.py# appends coverage numbers to RESULTS.md
build/ga_mutations.foma   # the rules emitted in foma replace-rule notation
```

`src/mutations.py` exposes generation (`lenite`, `eclipse`, `h_prefix`,
`t_prefix`, `MUTATE`, `fst_mutate`), analysis (`demutate`, `analyze`) and
`inverse_ok`, the shared pass criterion. `fst_mutate` is an arc-based transducer
path that must agree with the direct rule functions on every input; the test
suite enforces that.

## Running the tests

Standard library only. No dependencies, no downloads, no virtualenv:

```bash
python3 -m unittest discover -s tests -v
```

That runs 14 grammar-rule, parity and orthography tests, plus the attested
evaluation over the committed TSV, which prints:

```
attested: 17200/17201 pass (99.99%); lemma-initial mismatches (suppletion diag): 655
```

Both run in CI on every push and pull request.

The two scripts in `scripts/` are **not** runnable from a clean clone: both read
a UD Irish-IDT checkout at `data/UD_Irish-IDT`, which is not in this repository.
`gen_tests.py` regenerates `tests/attested_mutations.tsv` from the treebank and
`coverage_report.py` appends to `RESULTS.md`; the committed TSV means the tests
do not need either.

TODO(oscar): document where `data/UD_Irish-IDT` should come from, or add a
fetch script, so the mining step is reproducible.

## Relationship to Scalpel

The C++17 port of this layer lives in
[Scalpel](https://github.com/daltonoscar0/Scalpel) as `mutation_fst.{h,cpp}`.
`PLAN.md` records why: Scalpel turned out to be an FSM *tokenizer* rather than
an FST library, so the port added a transducer layer rather than composing with
existing rules. It also required UTF-8 codepoint support in Scalpel's tokenizer.

The two implementations are held together by exact parity: the C++ side scores
17,200/17,201 on this repository's `tests/attested_mutations.tsv`, the same
figure as the Python reference. Scalpel's header pins its semantics to
`src/mutations.py` and that TSV by path.

Note that the fixture lives **here** and the C++ tests live **there**, so
Scalpel's `mutation_tests` reports `[SKIP] attested TSV not found` from a clean
clone and verifies 11 of its 12 checks. Pass a path to close the loop:

```bash
# from a Scalpel checkout, with this repo cloned alongside
./mutation_tests ../Morpheme-Aware-Language-Modeling-for-Irish/tests/attested_mutations.tsv
```

TODO(oscar): decide whether this repository or Scalpel's Irish layer is the
source of truth. Both implement the same four mutations and are kept in sync by
hand.

## Status

From [PLAN.md](PLAN.md):

- **Phase 1, Irish FST morphology** — mutations done in both engines at exact
  parity, with an attested-form test suite. Still open: validating the trigger
  table against IDT bigrams, article rules including DNTLS blocking, and verb
  conjugation plus noun declension.
- **Phase 2, morpheme-aware tokenizer vs BPE** — not started.
- **Phase 3, LM comparison** (matched miniGPT variants, perplexity, wug-style
  probes) — not started.
- **Phase 4, documentation tooling** (ELAN export, field-linguist CLI) — stretch.

So the headline question this repository is named for is not answered yet. What
exists is the morphology Phase 2 needs, and evidence that it is correct.

## License

MIT. See [LICENSE](LICENSE).
