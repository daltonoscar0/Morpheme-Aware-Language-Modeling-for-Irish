"""Which mutation does a preceding token license?

Kept separate from mutation application on purpose (ARCHITECTURE.md §A).
Given (lemma, upos, featdict) of the preceding token, return the mutation
tag we expect on the next one, or None.

This is a seed table — the high-frequency closed-class triggers, nowhere
near exhaustive yet. The context-dependent ones (article + gender/case,
dialectal 'sa', DNTLS blocking) can't be answered from the trigger alone,
so they return "?" and the caller has to bring the following token when
it wants a real answer. Where the standard grammar genuinely
underdetermines things I've parked the question in QUESTIONS.md rather
than guessing.
"""

VOWEL_TAGS = {"HPref"}

# lemma -> tag for the unconditional triggers
SIMPLE = {
    # simple prepositions, all leniting
    "ar": "Len", "de": "Len", "do": "Len", "faoi": "Len", "mar": "Len",
    "ó": "Len", "roimh": "Len", "trí": "Len", "thar": "Len", "um": "Len",
    "gan": "Len",          # has lexical exceptions, see QUESTIONS.md
    "i": "Ecl",
    # preverbal particles
    "ní": "Len", "níor": "Len", "gur": "Len", "ar_PART": "Len",
    "go": "Ecl", "nach": "Ecl", "an_PART": "Ecl", "cha": "Ecl",
    "má": "Len", "sula": "Ecl", "mura": "Ecl", "dá": "Ecl",
    # past-tense d' (IDT tokenizes it separately)
    "d'": "Len",
    # vocative particle
    "a_VOC": "Len",
    # numbers: 1-6 lenite, 7-10 eclipse
    "aon": "Len", "dhá": "Len", "trí_NUM": "Len", "ceithre": "Len",
    "cúig": "Len", "sé_NUM": "Len",
    "seacht": "Ecl", "ocht": "Ecl", "naoi": "Ecl", "deich": "Ecl",
    # h-prefixers — only do anything before a vowel, of course
    "go_ADV": "HPref", "le": "HPref", "chomh": "HPref", "ná": "HPref",
}

# (person, number, gender) -> tag
POSSESSIVE = {
    ("1", "Sing", None): "Len",     # mo
    ("2", "Sing", None): "Len",     # do
    ("3", "Sing", "Masc"): "Len",   # a (his)
    ("3", "Sing", "Fem"): "HPref",  # a (her): h on vowels, otherwise nothing
    ("1", "Plur", None): "Ecl",     # ár
    ("2", "Plur", None): "Ecl",     # bhur
    ("3", "Plur", None): "Ecl",     # a (their)
}


def expected_mutation(lemma, upos, feats, next_form=None):
    """Best-effort tag for the token following this trigger.

    Returns a tag, None if no mutation is licensed, or "?" for context we
    can't resolve yet (article + noun gender/case, relativizers).
    """
    if upos in ("DET",) and lemma == "a" or feats.get("Poss") == "Yes":
        key = (feats.get("Person"), feats.get("Number"),
               feats.get("Gender") if feats.get("Number") == "Sing"
               and feats.get("Person") == "3" else None)
        return POSSESSIVE.get(key)
    if lemma == "an" and upos == "DET":
        return "?"   # depends on gender/case and the next word's initial
    if lemma == "na" and upos == "DET":
        return "?"   # gen pl eclipses; fem gen sg / nom pl h-prefix vowels
    if upos == "PART" and lemma == "a":
        return "?"   # direct rel lenites, indirect eclipses — needs PartType
    if upos == "NUM":
        return SIMPLE.get(lemma + "_NUM", SIMPLE.get(lemma))
    if upos == "PART":
        return SIMPLE.get(lemma + "_PART", SIMPLE.get(lemma))
    if upos == "ADV" and lemma == "go":
        return SIMPLE.get("go_ADV")
    return SIMPLE.get(lemma)
