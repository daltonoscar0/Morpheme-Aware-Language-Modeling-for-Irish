"""Irish initial mutations: séimhiú (Len), urú (Ecl), h-prefix, t-prefix.

Single source of truth is the rule tables below. Three consumers:
  1. direct string functions  (lenite / eclipse / h_prefix / t_prefix, demutate)
  2. a reference FST engine   (build_fst; parity-tested against the functions)
  3. foma_grammar()           (replace-rule emission: the Scalpel porting contract)

Design commitments (see ARCHITECTURE.md):
  - pure application layer: no triggers, no lexicon, no heuristics
  - vacuous application: mutating a non-target returns the word unchanged
  - demutation over-generates candidates; disambiguation is a later layer
  - feature names follow UD-IDT (Len/Ecl/HPref) + our TPref extension

Rules implemented from the standard grammar (Caighdeán Oifigiúil; cf.
Beesley & Karttunen ch. 3 for the replace-rule shape). Every rule is tested
against attested forms mined from UD Irish-IDT (scripts/gen_tests.py) plus
hand-picked citation forms (tests/test_mutations.py).
"""

VOWELS = "aeiouáéíóú"          # lowercase; use .lower() for membership tests
S_FOLLOWERS = VOWELS + "lnr"   # s mutates only before these (blocks sc/sm/sp/st)

# ---- rule tables -----------------------------------------------------------

LENITABLE = set("bcdfgmpt")    # + s, conditionally (S_FOLLOWERS)

ECLIPSIS_PREFIX = {            # base letter is KEPT; prefix is always lowercase
    "b": "m", "c": "g", "d": "n", "f": "bh", "g": "n", "p": "b", "t": "d",
}

TAGS = ("Len", "Ecl", "HPref", "TPref")


def _is_vowel(ch: str) -> bool:
    return ch.lower() in VOWELS


# ---- generation (surface <- base) -----------------------------------------

def lenite(w: str) -> str:
    """séimhiú: insert h after a lenitable initial consonant."""
    if not w:
        return w
    c0, l0 = w[0], w[0].lower()
    if l0 in LENITABLE:
        return c0 + "h" + w[1:]
    if l0 == "s" and len(w) > 1 and w[1].lower() in S_FOLLOWERS:
        return c0 + "h" + w[1:]
    return w


def eclipse(w: str) -> str:
    """urú: voiced/nasal prefix; n- before vowels (no hyphen before capitals)."""
    if not w:
        return w
    c0, l0 = w[0], w[0].lower()
    if l0 in ECLIPSIS_PREFIX:
        return ECLIPSIS_PREFIX[l0] + w
    if _is_vowel(c0):
        return ("n" if c0.isupper() else "n-") + w
    return w


def h_prefix(w: str) -> str:
    """h before a vowel-initial word; never hyphenated (na hÉireann)."""
    if w and _is_vowel(w[0]):
        return "h" + w
    return w


def t_prefix(w: str) -> str:
    """t before vowel-initial (t-ainm / tAthair) and before mutable s (tsúil)."""
    if not w:
        return w
    c0, l0 = w[0], w[0].lower()
    if _is_vowel(c0):
        return ("t" if c0.isupper() else "t-") + w
    if l0 == "s" and len(w) > 1 and w[1].lower() in S_FOLLOWERS:
        return "t" + w
    return w


def _caps_aware(fn):
    """ALL-CAPS orthography: inserted material is uppercased too
    (BLIAIN -> BHLIAIN, FUIL -> BHFUIL). Single letters exempt."""
    def wrapped(w: str) -> str:
        if len(w) > 1 and w.isupper():
            return fn(w).upper()
        return fn(w)
    wrapped.__name__ = fn.__name__
    return wrapped


MUTATE = {"Len": _caps_aware(lenite), "Ecl": _caps_aware(eclipse),
          "HPref": _caps_aware(h_prefix), "TPref": _caps_aware(t_prefix)}


def applies(tag: str, w: str) -> bool:
    """True if the mutation is non-vacuous on w."""
    return MUTATE[tag](w) != w


# ---- analysis (surface -> candidate bases) --------------------------------

def inverse_ok(tag: str, base: str, surface: str) -> bool:
    """Does mutating base yield surface, modulo accepted orthographic
    variants? Canonical output is Caighdeán (no hyphen before capitals,
    no hyphenated h-prefix); analysis additionally accepts:
      - hyphen-before-capital:  n-Ealaíon ~ nEalaíon, t-Athair ~ tAthair
      - hyphenated h-prefix (pre-standard): h-aoise ~ haoise, h-Íde ~ hÍde
    """
    m = MUTATE[tag](base)
    if m == surface:
        return True
    if surface[1:2] == "-" and surface[0] in "nht" \
            and m == surface[0] + surface[2:]:
        return True
    # Case-flexible mutation material: ALL-CAPS text occurs both fully
    # uppercased (IDT: BHFUIL, MBRIATHAR) and with lowercase prefixes in the
    # signage/official style (AN tAONTAS, NA hÉIREANN). Base letters must be
    # unchanged; only the inserted/prefixed material may vary in case.
    if m.lower() == surface.lower():
        if tag == "Len":
            return surface[0] == base[0] and surface[2:] == base[1:]
        return surface.endswith(base)
    return False


def demutate(w: str):
    """Return [(tag, base), ...] for every mutation that could have produced w.

    Over-generates by design (no lexicon filtering here). The identity
    analysis ('none', w) is NOT included; callers add it (see analyze()).
    Every candidate satisfies inverse_ok(tag, base, w).
    """
    out = _demutate_core(w)
    # ALL-CAPS track: match against the lowercased word, keep original caps
    # in the recovered base (BHFUIL -> FUIL, NDÉILEÁLFAIDH -> DÉILEÁLFAIDH)
    if len(w) > 2 and w.isupper():
        for tag, base_l in _demutate_core(w.lower()):
            cand = (tag, base_l.upper())
            if cand not in out:
                out.append(cand)
    # hyphen-before-capital / hyphenated-h variants
    if len(w) > 2 and w[1] == "-" and _is_vowel(w[2]):
        for pre, tag in (("n", "Ecl"), ("h", "HPref"), ("t", "TPref")):
            if w[0] == pre and (w[2].isupper() or pre == "h"):
                cand = (tag, w[2:])
                if cand not in out:
                    out.append(cand)
    for tag, base in out:
        assert inverse_ok(tag, base, w), (tag, base, w)
    return out


def _demutate_core(w: str):
    out = []
    n = len(w)
    if n >= 2:
        c0, l0, c1 = w[0], w[0].lower(), w[1]
        # --- Len: X + 'h' (the inserted h is always lowercase)
        if c1 == "h":
            if l0 in LENITABLE and l0 != "s":
                out.append(("Len", c0 + w[2:]))
            # s-lenition needs a legal follower after the h
            if l0 == "s" and n >= 3 and w[2].lower() in S_FOLLOWERS:
                out.append(("Len", c0 + w[2:]))
        # --- Ecl: consonant pairs (prefix always lowercase, base case kept)
        if w[:2].lower() == "bh" and n >= 3 and w[2].lower() == "f" and w[0] == "b":
            out.append(("Ecl", w[2:]))                      # bhf + ear -> fear
        else:
            for base_c, pre in ECLIPSIS_PREFIX.items():
                if base_c != "f" and c0 == pre and c1.lower() == base_c:
                    out.append(("Ecl", w[1:]))
        # --- Ecl: vowels
        if c0 == "n":
            if c1 == "-" and n >= 3 and _is_vowel(w[2]) and w[2].islower():
                out.append(("Ecl", w[2:]))                  # n-éan -> éan
            elif _is_vowel(c1) and c1.isupper():
                out.append(("Ecl", w[1:]))                  # nÉan -> Éan
        # --- HPref
        if c0 == "h" and _is_vowel(c1):
            out.append(("HPref", w[1:]))
        # --- TPref
        if c0 == "t":
            if c1 == "-" and n >= 3 and _is_vowel(w[2]) and w[2].islower():
                out.append(("TPref", w[2:]))                # t-ainm -> ainm
            elif _is_vowel(c1) and c1.isupper():
                out.append(("TPref", w[1:]))                # tAthair -> Athair
            elif c1.lower() == "s" and n >= 3 and w[2].lower() in S_FOLLOWERS:
                out.append(("TPref", w[1:]))                # tsúil -> súil
    return out


def analyze(w: str):
    """Candidate analyses including the unmutated reading."""
    return [("none", w)] + demutate(w)


# ---- reference FST engine ---------------------------------------------------
# Small nondeterministic transducer with character-class arcs, built from the
# same tables. Semantics: priority union (Mutate .P. Id) — if no accepting
# path, the word is returned unchanged. Exists to pin down FST behavior for
# the Scalpel port; parity with the direct functions is enforced in tests.

_ANY = object()
_COPY = "COPY"


class FST:
    def __init__(self):
        self.arcs = {}   # state -> list[(charset|_ANY, emit(ch)->str, next_state)]

    def arc(self, state, charset, emit, nxt):
        self.arcs.setdefault(state, []).append((charset, emit, nxt))

    def apply(self, w: str):
        """Return transduced string, or None if no accepting path (caller
        falls back to identity)."""

        def step(state, i, acc):
            if state == _COPY:
                return acc + w[i:]
            for charset, emit, nxt in self.arcs.get(state, []):
                if i < len(w) and (charset is _ANY or w[i].lower() in charset):
                    r = step(nxt, i + 1, acc + emit(w[i]))
                    if r is not None:
                        return r
            return None

        return step(0, 0, "")


def _lower_pre(pre):
    return lambda ch: pre + ch


def build_fst(tag: str) -> FST:
    f = FST()
    vs = set(VOWELS)
    if tag == "Len":
        f.arc(0, LENITABLE - {"s"}, lambda ch: ch + "h", _COPY)
        f.arc(0, {"s"}, lambda ch: ch + "h", 1)
        f.arc(1, set(S_FOLLOWERS), lambda ch: ch, _COPY)
    elif tag == "Ecl":
        for base_c, pre in ECLIPSIS_PREFIX.items():
            f.arc(0, {base_c}, _lower_pre(pre), _COPY)
        f.arc(0, vs, lambda ch: ("n" + ch) if ch.isupper() else ("n-" + ch), _COPY)
    elif tag == "HPref":
        f.arc(0, vs, lambda ch: "h" + ch, _COPY)
    elif tag == "TPref":
        f.arc(0, vs, lambda ch: ("t" + ch) if ch.isupper() else ("t-" + ch), _COPY)
        f.arc(0, {"s"}, lambda ch: "t" + ch, 1)
        f.arc(1, set(S_FOLLOWERS), lambda ch: ch, _COPY)
    else:
        raise ValueError(tag)
    return f


def fst_mutate(tag: str, w: str) -> str:
    out = build_fst(tag).apply(w)
    return w if out is None else out


# ---- foma-style replace-rule emission (Scalpel porting contract) -----------

def foma_grammar() -> str:
    V = " | ".join(VOWELS) + " | " + " | ".join(VOWELS.upper())
    SF = " | ".join(S_FOLLOWERS) + " | " + " | ".join(S_FOLLOWERS.upper())
    lines = [
        "# Irish initial mutations as start-anchored replace rules.",
        "# Case tracks omitted for brevity: lowercase shown; prefixes/inserted",
        "# h are always lowercase, base letter keeps its case; the vowel rules",
        "# with hyphen apply to lowercase bases, hyphen-less to capitals.",
        f"define V [ {V} ];",
        f"define SF [ {SF} ];",
        "define Len  [ b -> b h , c -> c h , d -> d h , f -> f h , g -> g h ,"
        " m -> m h , p -> p h , t -> t h || .#. _ ] .o."
        " [ s -> s h || .#. _ SF ];",
        "define Ecl  [ b -> m b , c -> g c , d -> n d , f -> b h f ,"
        " g -> n g , p -> b p , t -> d t || .#. _ ] .o."
        " [ [..] -> n \"-\" || .#. _ V ];   # capitals: [..] -> n, no hyphen",
        "define HPref [ [..] -> h || .#. _ V ];",
        "define TPref [ [..] -> t \"-\" || .#. _ V ] .o."
        " [ [..] -> t || .#. _ s SF ];      # capitals: t, no hyphen",
        "# Analyzer side: [Len | Ecl | HPref | TPref].i .P. Id",
    ]
    return "\n".join(lines)
