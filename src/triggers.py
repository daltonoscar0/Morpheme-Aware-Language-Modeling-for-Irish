"""Trigger assignment: which mutation does a preceding token license?

Deliberately separate from mutation application (ARCHITECTURE.md §A).
Input is (lemma, upos, featdict) of the PRECEDING token; output is the
expected mutation tag for the next token, or None.

STATUS: seed table covering the high-frequency closed-class triggers.
Explicitly NON-exhaustive — expansion is a logged next task. Context-
dependent triggers (article + gender/case, dialectal 'sa', DNTLS blocking)
return conditional entries; the caller supplies the following token when
resolution needs it. Cases where the standard grammar underdetermines the
answer are listed in QUESTIONS.md rather than guessed.
"""

VOWEL_TAGS = {"HPref"}

# lemma -> tag, for unconditional simple triggers
SIMPLE = {
    # simple prepositions -> Len
    "ar": "Len", "de": "Len", "do": "Len", "faoi": "Len", "mar": "Len",
    "ó": "Len", "roimh": "Len", "trí": "Len", "thar": "Len", "um": "Len",
    "gan": "Len",          # (with lexical exceptions; QUESTIONS.md)
    "i": "Ecl",
    # preverbal particles
    "ní": "Len", "níor": "Len", "gur": "Len", "ar_PART": "Len",
    "go": "Ecl", "nach": "Ecl", "an_PART": "Ecl", "cha": "Ecl",
    "má": "Len", "sula": "Ecl", "mura": "Ecl", "dá": "Ecl",
    # past-tense d' (tokenized separately in IDT)
    "d'": "Len",
    # vocative
    "a_VOC": "Len",
    # numbers
    "aon": "Len", "dhá": "Len", "trí_NUM": "Len", "ceithre": "Len",
    "cúig": "Len", "sé_NUM": "Len",
    "seacht": "Ecl", "ocht": "Ecl", "naoi": "Ecl", "deich": "Ecl",
    # h-prefix licensers (effective only on vowel-initial words)
    "go_ADV": "HPref", "le": "HPref", "chomh": "HPref", "ná": "HPref",
}

POSSESSIVE = {
    # (person, number, gender) -> tag
    ("1", "Sing", None): "Len",     # mo
    ("2", "Sing", None): "Len",     # do
    ("3", "Sing", "Masc"): "Len",   # a (his)
    ("3", "Sing", "Fem"): "HPref",  # a (her)  — h on vowels, else nothing
    ("1", "Plur", None): "Ecl",     # ár
    ("2", "Plur", None): "Ecl",     # bhur
    ("3", "Plur", None): "Ecl",     # a (their)
}


def expected_mutation(lemma, upos, feats, next_form=None):
    """Best-effort expected tag for the token following this trigger.

    Returns a tag, None (no mutation licensed), or "?" (context we don't
    resolve yet: article+noun gender/case interactions, relativizers).
    """
    if upos in ("DET",) and lemma == "a" or feats.get("Poss") == "Yes":
        key = (feats.get("Person"), feats.get("Number"),
               feats.get("Gender") if feats.get("Number") == "Sing"
               and feats.get("Person") == "3" else None)
        return POSSESSIVE.get(key)
    if lemma == "an" and upos == "DET":
        return "?"   # needs gender/case/initial of next token; see QUESTIONS.md
    if lemma == "na" and upos == "DET":
        return "?"   # gen pl -> Ecl; fem gen sg / nom pl vowel -> HPref
    if upos == "PART" and lemma == "a":
        return "?"   # direct rel -> Len, indirect -> Ecl (needs PartType/Form)
    if upos == "NUM":
        return SIMPLE.get(lemma + "_NUM", SIMPLE.get(lemma))
    if upos == "PART":
        return SIMPLE.get(lemma + "_PART", SIMPLE.get(lemma))
    if upos == "ADV" and lemma == "go":
        return SIMPLE.get("go_ADV")
    return SIMPLE.get(lemma)
