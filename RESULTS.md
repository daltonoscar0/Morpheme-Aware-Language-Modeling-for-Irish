# RESULTS - Seanchai

| date | config | metric | takeaway |
|---|---|---|---|
| 2026-07-27 | mutation FST (session 1) | attested round-trip by tag: Len 99.99% (n=11825), Ecl 100.00% (n=4094), HPref 100.00% (n=860); ambiguity 0.17 cand/token, spurious-candidate rate 1.8% | mutation layer round-trips IDT; ambiguity is the no-lexicon price |

### Mutation round-trip by POS (2026-07-27, IDT all splits)
| POS | pass | total | rate |
|---|---|---|---|
| NOUN | 10094 | 10095 | 99.99% |
| VERB | 3981 | 3981 | 100.00% |
| PROPN | 1318 | 1318 | 100.00% |
| ADJ | 926 | 926 | 100.00% |
| NUM | 261 | 261 | 100.00% |
| PRON | 65 | 65 | 100.00% |
| DET | 61 | 61 | 100.00% |
| ADP | 33 | 33 | 100.00% |
| AUX | 19 | 19 | 100.00% |
| PART | 13 | 13 | 100.00% |
| ADV | 6 | 6 | 100.00% |
| SCONJ | 1 | 1 | 100.00% |
| 2026-07-29 | Scalpel port (session 2): C++17 mutation_fst + UTF-8 tokenizer fix | attested 17200/17201 (exact parity with Python ref); 12/12 C++ tests, 31/31 upstream Scalpel tests | port done; Scalpel was FSM tokenizer not FST lib - transducer layer added, not composed |
