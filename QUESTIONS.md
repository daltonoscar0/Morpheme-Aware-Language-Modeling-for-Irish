# QUESTIONS — needs your Irish judgment (session 1)

Per working rules: not guessed; best hypothesis given for each; code
continues past them with the hypothesis noted where a choice was forced.

1. **All-caps vowel eclipsis.** IDT attests fully-uppercased mutations
   (BHFUIL, MBRIATHAR) and signage-style lowercase prefixes (tAONTAS).
   I generate fully-upper for all-caps input and *accept* both in analysis.
   But what should the generator emit for vowel eclipsis in caps text:
   `N-ÉAN` or `NÉAN`? Hypothesis: `N-ÉAN` (hyphen retained, parallel to
   lowercase), but no attested case decided it.
2. **Hyphen before capitals after n-.** Caighdeán says no hyphen (nÉan),
   yet official names write it: *Comhairle na n-Ealaíon*. Current policy:
   generate no-hyphen, accept both. Is no-hyphen the right canonical
   everywhere, with hyphenated forms treated as lexicalized names?
3. **DNTLS blocking.** d/t resisting lenition after the article (an doras,
   not *an dhoras*) is implemented nowhere yet — I've put it trigger-side
   (blocking is a property of the an+noun context, not of the mutation).
   Confirm scope: after *an* and *aon* only, or also *chéad* and the
   dental-final preps? Hypothesis: article + aon at minimum.
4. **Dialect policy for prep+article.** Standard *ar an bhfear* (Ecl) vs
   Ulster *ar an fhear* (Len); also *sa tsráid* for feminine s after *sa*.
   Hypothesis: Caighdeán default now, a dialect parameter on the trigger
   table later (Phase 1 stretch). Which dialects do you want represented?
5. **gan.** Lenites in *gan fhios* but famously not everywhere (gan +
   d/t/s and some nouns). Trigger table currently marks gan→Len with a
   TODO. What's your rule of thumb / preferred reference?
6. **h-initial loanwords.** *hata*, *heicteár* etc. mean `hV-` surfaces keep
   both `none` and `HPref` readings; disambiguation deferred to the lexicon
   layer. Confirm that's acceptable for the tokenizer downstream (Phase 2
   will see candidate sets, not decisions).
7. **Copula vowel-forms.** `Form=VF` items (b', gurb, mb', níorbh) are
   lexicalized copula morphology, excluded from the mutation FST.
   Hypothesis: they live in the irregular lexicon with `bí`/`is`.
8. **go dtí.** IDT lemma is *dtí* (frozen eclipsis). Treat as lexicalized,
   not productive? Hypothesis: yes.
9. **One residual test failure.** `fíor-` (goeswith fragment of
   *fíor-chorr-Óglach*, tagged Len) — annotation artifact. Exclude goeswith
   tokens from the test generator, or keep as a standing known-failure?
   Hypothesis: exclude goeswith; kept as visible failure for now.
10. **Pre-standard spellings.** IDT contains pre-reform forms (shuidhte ~
    suite). Mutation layer is agnostic (it operates on surfaces), but the
    Phase-1 lexicon will need a policy: normalize, or dual entries?
