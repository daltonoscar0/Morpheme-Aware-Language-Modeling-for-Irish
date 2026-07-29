# ARCHITECTURE — Irish mutation layer (Phase 1, session 1)

## Status caveat (read first)
**Revised in session 2, after reading Scalpel's actual source.** The original
assumption ("compose replace rules with Scalpel's existing FSTs") was wrong:
Scalpel is a character-level FSM *tokenizer + sentence segmenter* (recognizer,
not transducer) — it has no FST/replace-rule machinery to compose with. The
port therefore *adds* the transducer layer to Scalpel rather than composing
with one:

- `vendor/scalpel/mutation_fst.{h,cpp}` — the mutation FST module (C++17,
  zero-dep, namespace `ga`), semantics pinned by the Python reference below
  and by the shared attested-form TSV (parity: 17200/17201, test-enforced).
- `vendor/scalpel/utf8.h` + tokenizer/char_classes edits — codepoint-aware
  classification. Stock Scalpel byte-classified via `isalpha`, shattering
  every accented Irish vowel (`Bhí` -> `Bh`); fixed with a minimal UTF-8
  decoder while preserving the single-pass FSM and all 31 upstream tests.
  Also fixed: EOF flush mislabelled trailing tokens as WORD.

The session-1 layers below remain the executable specification:

1. **Declarative rule tables** (`src/mutations.py`) — the linguistic content,
   independent of any engine.
2. **A reference transducer engine** (`src/fst.py`) — small, stdlib-only,
   with explicit FST semantics (states/arcs, inversion, candidate sets), so
   behavior is pinned down by tests *before* porting.
3. **A foma-style replace-rule emitter** (`mutations.py:foma_grammar()`) —
   every rule table row compiles to a `[ x -> y || .#. _ ctx ]` replace rule,
   which is the porting contract to Scalpel (or foma, for cross-validation).

Porting contract (session 2, done): the C++ module implements the same rule
tables; the identical attested-form test file is the cross-engine oracle, and
`build/ga_mutations.foma` remains available for third-engine validation in
foma proper if ever needed. Tests are engine-agnostic on purpose.

## Where mutation sits in the pipeline

```
raw text ──► tokenizer ──► [trigger assigner] ──► [mutation FST] ──► analyses
                             (triggers.py)          (mutations.py)
                             context features        surface ⇄ base
```

Two hard design commitments, per the project brief:

**(A) Trigger assignment is separable from mutation application.**
`triggers.py` maps a *preceding* token (lemma + feats) to an expected
mutation feature on the next token (e.g. `ar` → `Len`, `i` → `Ecl`,
`a`+Poss3SgFem → `HPref`). `mutations.py` knows nothing about triggers; it is
a pure function surface ⇄ (mutation tag, base form). This lets Phase 2's
tokenizer consume mutation analyses without dragging syntax in, and lets
trigger coverage grow independently (triggers are the long tail; application
is closed-class).

**(B) Analysis is a candidate set, not a decision.**
Demutation over-generates by design: `bhfear` → {Ecl:fear, Len:*bfear,
none:bhfear}. No lexicon or phonotactic heuristics filter candidates inside
the mutation layer (INSTRUCTIONS.md: no heuristics in mutation logic).
Disambiguation belongs to later layers (lexicon lookup in the full analyzer,
trigger agreement, or the LM itself). The coverage report quantifies the
resulting ambiguity load so we know what we're paying.

## The rules as FSTs

All four processes are word-initial prefix operations, so each compiles to a
start-anchored replace rule; composition with the rest of Scalpel's pipeline
is left-composition ahead of morphotactics:

```
Analyzer  = Demutate .o. Morphotactics(lexicon ∘ inflection)
Generator = Morphotactics⁻¹ .o. Mutate(feature-selected)
```

Rule inventory (S = mutation slot; exactly one applies per token — the four
mutations are mutually exclusive at the initial position, so ordering between
them is a non-issue; each is its own transducer selected by feature):

| tag   | rule (foma-style, lowercase shown)                          | notes |
|-------|--------------------------------------------------------------|-------|
| Len   | `b→bh, c→ch, d→dh, f→fh, g→gh, m→mh, p→ph, t→th ‖ .#. _`     | h inserted after initial |
| Len   | `s→sh ‖ .#. _ [V | l | n | r]`                               | blocked before c,m,p,t (sc/sm/sp/st) |
| Ecl   | `b→mb, c→gc, d→nd, f→bhf, g→ng, p→bp, t→dt ‖ .#. _`          | prefix, base letter kept |
| Ecl   | `∅→n- ‖ .#. _ V` (lowercase) ; `∅→n ‖ .#. _ V�«cap»`          | hyphen dropped before capital: *nÉan* |
| HPref | `∅→h ‖ .#. _ V`                                              | never hyphenated: *hÉireann* |
| TPref | `∅→t- ‖ .#. _ V` (lowercase) ; `∅→t ‖ .#. _ V�«cap»`          | *t-ainm* / *tAthair* |
| TPref | `∅→t ‖ .#. _ s [V | l | n | r]`                              | *tsúil*, *tSín*; s kept in spelling |

Non-targets are identity: l, n, r, h, vowels under Len; l, m, n, r, s, h
under Ecl; consonant-initial under HPref/TPref(vowel case). Applying a
mutation to a non-target returns the word unchanged (vacuous application),
which matches how triggers behave in text ("ar lá" — trigger present,
no surface change).

Case is handled as a two-track alphabet: the mutating machinery preserves the
base letter's case and inserts prefix material in lowercase (`Conradh →
Chonradh`, `Baile → mBaile`, `Frainc → bhFrainc`, `Sín → tSín`). All-caps
input (acronyms/shouting) is out of scope this session (QUESTIONS.md).

Demutation is the inverted union of the four transducers, plus identity.
Longest-prefix-first matching order in the reference engine: `bhf` before
`bh`, `ts`/`t-` before `th`... — in a real FST this falls out of the
automaton; in the reference engine it's an explicit ordered scan, tested.

## Feature naming (decided, logged)
Follow UD-IDT's vocabulary where it exists — `Len`, `Ecl`, `HPref` — and
extend with `TPref` (IDT leaves t-prefix unmarked; we detect it from
surface/lemma). Trigger expectations reuse the same tags. Rationale: the test
suite is generated from IDT, so sharing its names removes a mapping layer.

## Test strategy (data over intuition)
- `scripts/gen_tests.py` walks all three IDT splits and emits one test row
  per mutated token: `(surface, lemma, tag, POS)`. A row passes iff
  demutate(surface) contains (tag, base) with base's initial grapheme
  matching the lemma's (case-insensitive), **and** mutate(tag, base) ==
  surface exactly (round trip). Lemma-initial check (not full lemma match)
  because surface forms are inflected; inflection is later in Phase 1.
- t-prefix rows are mined from surface patterns (`t-V`, `tV«cap»`, `tsX`)
  restricted to `Definite=Def` nominals, since IDT doesn't tag them.
- Hand-written grammar-rule tests (attested citation forms from standard
  grammar) cover the corners a treebank sample may miss: s-blocking, capital
  hyphen-dropping, vacuous application, non-mutating initials.
- Failures are never silently skipped: they land in
  `tests/failures_*.tsv` and, where they look like judgment calls rather
  than bugs, in QUESTIONS.md.

## Coverage report
`scripts/coverage_report.py` → RESULTS.md: for every IDT token carrying a
mutation feat, does the analyzer round-trip it (by tag, by POS)? Plus the
ambiguity load: mean demutation candidates per token over all tokens, and the
spurious-candidate rate on unmutated tokens. This session's "coverage" is
mutation-layer coverage; full analyzer coverage (declension/conjugation)
arrives with the rest of Phase 1.
