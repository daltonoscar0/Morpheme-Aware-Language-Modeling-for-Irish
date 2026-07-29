# PLAN - Seanchai

## Phase 1: Irish FST morphology (weeks 1-4)
- [x] Initial mutations (seimhiu/uru/h-prefix/t-prefix): rule tables +
      reference FST + foma replace-rule emission (Scalpel port pending source)
- [x] Test suite from attested forms: 17,201 auto-generated cases from
      UD-IDT (all splits) + hand-written grammar-rule tests; 1 known failure
      (goeswith artifact, QUESTIONS.md #9)
- [x] Port mutation rules onto Scalpel (session 2): Scalpel turned out to
      be an FSM tokenizer, not an FST lib -> added mutation_fst.{h,cpp}
      (C++17) + UTF-8 codepoint support; exact attested parity 17200/17201;
      all upstream tests kept green
- [ ] Trigger table: validate against IDT bigrams; article rules incl. DNTLS
- [ ] Verb conjugation (1st/2nd conjugation, irregulars) + noun declension
Milestone: analyzer coverage report on UD-IDT tokens.
Session-1 partial: mutation-layer coverage in RESULTS.md (Len 99.99%,
Ecl 100%, HPref 100% round-trip; ambiguity 0.17 cand/token).

## Phase 2: Morpheme-aware tokenizer vs BPE (weeks 5-7)
- [ ] Tokenizer on the analyzer; BPE baseline at matched vocab size
- [ ] Corpus prep: Vicipeid + Gaois, dedup, CC-provenance log
Milestone: segmentation comparison table (morpheme boundary F1).

## Phase 3: LM comparison (weeks 8-10)
- [ ] Train matched miniGPT variants; perplexity per morpheme / per char
- [ ] Targeted syntactic eval: wug-style generalization, mutation-trigger
      probes, agreement
Milestone: headline table - morphological tokenization vs BPE on Irish.

## Phase 4: Documentation tooling (stretch)
- [ ] ELAN-compatible annotation export; CLI for field linguists

## Status
- Current phase: 1 (mutations done in both engines, exact parity)
- Next 3 tasks:
  1. Empirically validate triggers.py against IDT trigger-bigram pairs;
     implement article (an/na) rules incl. DNTLS blocking + t-prefix
     conditions (needs QUESTIONS.md #3/#4 answers).
  2. Noun declension (1st/2nd decl.) with the same attested-form
     test-generation pattern; C++ side follows the same parity discipline.
  3. Wire mutation analyses into the token stream (extend Token with an
     analyses field or a MutationAnalyzer pass) so Phase 2's tokenizer
     consumes candidate sets directly; decide d'-elision tokenization
     policy vs IDT (D'ól currently one CONTRACTION token; IDT splits).
