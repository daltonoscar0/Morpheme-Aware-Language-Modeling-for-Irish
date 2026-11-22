"""Irish initial mutations: séimhiú, urú, h-prefix, t-prefix.

Everything here is driven off the small rule tables near the top. The same
tables feed the plain string functions (lenite, eclipse, etc.), a little
reference FST that pins down the semantics we want from the C++ port, and
foma_grammar(), which spells the rules out in foma replace-rule notation.

This layer only *applies* mutations. It knows nothing about triggers or
the lexicon: mutating a word the rule doesn't touch just hands it back
unchanged, and demutate() happily over-generates candidates — picking the
right one is a later layer's problem (see ARCHITECTURE.md). Tag names
follow UD-IDT (Len/Ecl/HPref); TPref is ours, since IDT leaves the
t-prefix unmarked.

The rules themselves are standard Caighdeán; the replace-rule shape comes
from Beesley & Karttunen ch. 3. Tested against attested forms mined from
UD Irish-IDT (scripts/gen_tests.py) plus hand-picked citation forms.
"""
import sys as _sys


VOWELS = "aeiouáéíóú"          # lowercase.lower() before membership tests
S_FOLLOWERS = VOWELS + "lnr"   # s only mutates before these (so sc/sm/sp/st are safe)

LENITABLE = set("bcdfgmpt")    # s too, but only before S_FOLLOWERS

# base letter is kept; the prefix itself is always lowercase
ECLIPSIS_PREFIX = {
    "b": "m", "c": "g", "d": "n", "f": "bh", "g": "n", "p": "b", "t": "d",
}

TAGS = ("Len", "Ecl", "HPref", "TPref")


def _is_vowel(ch: str) -> bool:
    return ch.lower() in VOWELS


# generation

def lenite(w: str) -> str:
    """séimhiú — stick an h after a lenitable initial consonant."""
    if not w:
        return w
    c0, l0 = w[0], w[0].lower()
    if l0 in LENITABLE:
        return c0 + "h" + w[1:]
    if l0 == "s" and len(w) > 1 and w[1].lower() in S_FOLLOWERS:
        return c0 + "h" + w[1:]
    return w


def eclipse(w: str) -> str:
    """urú — voiced/nasal prefix, or n- before a vowel (no hyphen if it's
    a capital: nÉire, not n-Éire)."""
    if not w:
        return w
    c0, l0 = w[0], w[0].lower()
    if l0 in ECLIPSIS_PREFIX:
        return ECLIPSIS_PREFIX[l0] + w
    if _is_vowel(c0):
        return ("n" if c0.isupper() else "n-") + w
    return w


def h_prefix(w: str) -> str:
    """h before a vowel-initial word. Never hyphenated: na hÉireann."""
    if w and _is_vowel(w[0]):
        return "h" + w
    return w


def t_prefix(w: str) -> str:
    """t before a vowel (t-ainm, tAthair) and before mutable s (tsúil)."""
    if not w:
        return w
    c0, l0 = w[0], w[0].lower()
    if _is_vowel(c0):
        return ("t" if c0.isupper() else "t-") + w
    if l0 == "s" and len(w) > 1 and w[1].lower() in S_FOLLOWERS:
        return "t" + w
    return w


def _caps_aware(fn):
    """In ALL-CAPS text the inserted material gets uppercased too:
    BLIAIN -> BHLIAIN, FUIL -> BHFUIL. Single letters are left alone."""
    def wrapped(w: str) -> str:
        if len(w) > 1 and w.isupper():
            return fn(w).upper()
        return fn(w)
    wrapped.__name__ = fn.__name__
    return wrapped


MUTATE = {"Len": _caps_aware(lenite), "Ecl": _caps_aware(eclipse),
          "HPref": _caps_aware(h_prefix), "TPref": _caps_aware(t_prefix)}


def applies(tag: str, w: str) -> bool:
    """True if the mutation actually does something to w."""
    return MUTATE[tag](w) != w


# analysis: surface -> candidate bases

PLAIN = {"Len": lenite, "Ecl": eclipse, "HPref": h_prefix,
         "TPref": t_prefix}

# The three markers that may be followed by a hyphen, and only before a
# vowel: n-Ealaíon, t-ainm, pre-standard h-aoise.
HYPHENABLE = ("n", "h", "t")


def realisations(tag: str, base: str) -> set:
    """Every surface spelling of ``mutate(tag, base)`` analysis accepts.

    Generation stays strict Caighdeán; this is the wider set the *analysis*
    side has always taken, written down so a reading can be checked against
    it instead of against a single string. Enumerating it is what lets
    'n-APP' be verified: the canonical spelling is 'NAPP', because an
    all-caps stem uppercases the inserted marker, and no amount of pairwise
    comparison gets from one to the other in a single step.

    Deliberately no wider than analysis: the uppercase marker is offered
    only when the stem is ALL-CAPS, and the hyphen only for n/h/t before a
    vowel. ``inverse_ok`` is also the pass criterion for the attested file,
    so loosening it further would quietly change that count.
    """
    out = {MUTATE[tag](base)}
    if tag == "Len":
        # Lenition has no hyphen variant, and the all-caps case is already
        # exact: _caps_aware uppercases the inserted h with everything else.
        return out

    plain = PLAIN[tag](base)
    if plain == base or not plain.endswith(base):
        return out                      # the mutation does not apply here
    marker = plain[:len(plain) - len(base)].rstrip("-")
    if not marker:
        return out

    markers = {marker}
    if base.isupper():
        # BHFUIL, NAPP. Not gated on length: the ALL-CAPS analysis track
        # fires on len(surface) > 2, which a one-letter base still satisfies
        # once a marker and a hyphen are in front of it ('N-A'), so gating
        # this on len(base) left those readings unverifiable. Found by fuzzing.
        markers.add(marker.upper())
    seps = {""}
    if marker.lower() in HYPHENABLE and base and _is_vowel(base[0]):
        seps.add("-")
    out |= {mk + sep + base for mk in markers for sep in seps}
    return out


def inverse_ok(tag: str, base: str, surface: str) -> bool:
    """Could mutating base have produced surface?

    True when surface is one of the orthographic realisations generation is
    allowed to have for this base. Generation itself is strict Caighdeán (no
    hyphen before capitals, no hyphenated h), but real text also has
    n-Ealaíon for nEalaíon, pre-standard h-aoise, fully uppercased BHFUIL
    and the signage style AN tAONTAS, so analysis takes those too and they
    have to verify.
    """
    if surface in realisations(tag, base):
        return True
    # Case-flexible fallback for the inserted material, kept from the
    # original: the base letters must survive untouched and only what the
    # mutation added may vary.
    if MUTATE[tag](base).lower() == surface.lower():
        if tag == "Len":
            return (bool(base) and len(surface) >= 2
                    and surface[0] == base[0] and surface[2:] == base[1:])
        return surface.endswith(base)
    return False


def demutate_candidates(w: str):
    """Every candidate the analysis tracks produce, before verification.

    Exposed so a caller can tell a reading that was never proposed from one
    that was proposed and then dropped by the inverse check. The fuzz harness
    compares this against demutate() to assert the drop count is zero.
    """
    out = _demutate_core(w)
    if len(w) > 2 and w.isupper():
        for tag, base_l in _demutate_core(w.lower()):
            cand = (tag, base_l.upper())
            if cand not in out:
                out.append(cand)
    if len(w) > 2 and w[1] == "-" and _is_vowel(w[2]):
        for pre, tag in (("n", "Ecl"), ("h", "HPref"), ("t", "TPref")):
            if w[0] == pre and (w[2].isupper() or pre == "h"):
                cand = (tag, w[2:])
                if cand not in out:
                    out.append(cand)
    return out


def demutate(w: str, strict: bool = False):
    """[(tag, base), ...] for every mutation that could have produced w.

    Over-generates on purpose — there's no lexicon here to filter with.
    The identity reading ('none', w) is not included; analyze() adds it.
    Every candidate returned passes inverse_ok(tag, base, w).

    A candidate that fails its own inverse check is *dropped* and reported on
    stderr, not raised. This runs over user text: a tokenizer about to go
    across a parallel corpus must not die on one word, and silently handing
    back a reading that cannot regenerate its surface would be worse. With
    ``strict`` the mismatch raises instead, which is what the test runners
    want: there the right behaviour is to be loud.
    """
    out = demutate_candidates(w)
    kept = []
    for tag, base in out:
        if inverse_ok(tag, base, w):
            kept.append((tag, base))
            continue
        if strict:
            raise AssertionError((tag, base, w))
        print(f"mutations: dropped unverifiable reading {tag}:{base} "
              f"for {w!r}", file=_sys.stderr)
    return kept


def _demutate_core(w: str):
    out = []
    n = len(w)
    if n >= 2:
        c0, l0, c1 = w[0], w[0].lower(), w[1]
        # Len looks like X + 'h', and the inserted h is always lowercase
        if c1 == "h":
            if l0 in LENITABLE and l0 != "s":
                out.append(("Len", c0 + w[2:]))
            # s-lenition needs a legal follower after the h
            if l0 == "s" and n >= 3 and w[2].lower() in S_FOLLOWERS:
                out.append(("Len", c0 + w[2:]))
        # eclipsed consonants: lowercase prefix, base keeps its case
        if w[:2].lower() == "bh" and n >= 3 and w[2].lower() == "f" and w[0] == "b":
            out.append(("Ecl", w[2:]))                      # bhf + ear -> fear
        else:
            for base_c, pre in ECLIPSIS_PREFIX.items():
                if base_c != "f" and c0 == pre and c1.lower() == base_c:
                    out.append(("Ecl", w[1:]))
        # eclipsed vowels
        if c0 == "n":
            if c1 == "-" and n >= 3 and _is_vowel(w[2]) and w[2].islower():
                out.append(("Ecl", w[2:]))                  # n-éan -> éan
            elif _is_vowel(c1) and c1.isupper():
                out.append(("Ecl", w[1:]))                  # nÉan -> Éan
        if c0 == "h" and _is_vowel(c1):
            out.append(("HPref", w[1:]))
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


# The reference FST: a small nondeterministic transducer with
# character-class arcs, built from the same tables as everything else.
# Semantics are priority union (Mutate .P. Id), no accepting path means
# the word comes back unchanged. It exists so the Scalpel port has an
# exact behavior to match; the tests enforce parity with the functions
# above.

_ANY = object()
_COPY = "COPY"


class FST:
    def __init__(self):
        self.arcs = {}   # state -> list[(charset|_ANY, emit(ch)->str, next_state)]

    def arc(self, state, charset, emit, nxt):
        self.arcs.setdefault(state, []).append((charset, emit, nxt))

    def apply(self, w: str):
        """Transduced string, or None when nothing accepts (the caller
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


# foma-style replace-rule emission, for the Scalpel port

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
