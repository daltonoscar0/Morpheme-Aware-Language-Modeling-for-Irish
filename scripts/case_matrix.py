"""Map the orthographic space of the mutation layer, Python against C++.

Built to spec the fix for the abort at mutation_fst.cpp:201: analysis accepts
a hyphenated marker in front of an all-caps stem (n-APP) but generation
cannot reproduce that surface, so the self-check inside demutate() fails.

Rather than fix the four known forms, this enumerates the whole space the
four live in, so the fix is specified by evidence instead of by example. The
axes are marker, marker case, hyphen, stem case and stem onset. Each cell
records, for both implementations:

    analysis   the (tag, base) readings returned
    inverse    whether each reading passes its own inverse_ok
    generation what mutate(tag, base) produces for the expected tag
    abort      whether the assert build dies on the input

The C++ side is read through ``mutation_probe``, which is built twice: with
the assert live, to find the aborting cells, and with -DNDEBUG, to see what
analysis returned in cells that would otherwise have died.

Writes docs/mutation_case_matrix.md.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mutations as M                                           # noqa: E402

SCALPEL = Path.home() / "code" / "Scalpel"
PROBE_ND = SCALPEL / "mutation_probe_nd"
PROBE_ASSERT = SCALPEL / "mutation_probe"
OUT = ROOT / "docs" / "mutation_case_matrix.md"

# Stems chosen so every marker has a legal target, in three cases each.
# 'onset' is what the marker needs to see to fire at all.
STEMS = {
    "vowel":  [("éan", "lower"), ("Éan", "Cap"), ("ÉAN", "ALLCAPS"),
               ("app", "lower"), ("App", "Cap"), ("APP", "ALLCAPS")],
    "b": [("bean", "lower"), ("Bean", "Cap"), ("BEAN", "ALLCAPS")],
    "c": [("cat", "lower"), ("Cat", "Cap"), ("CAT", "ALLCAPS")],
    "d": [("doras", "lower"), ("Doras", "Cap"), ("DORAS", "ALLCAPS")],
    "f": [("fear", "lower"), ("Fear", "Cap"), ("FEAR", "ALLCAPS")],
    "g": [("garda", "lower"), ("Garda", "Cap"), ("GARDA", "ALLCAPS")],
    "p": [("post", "lower"), ("Post", "Cap"), ("POST", "ALLCAPS")],
    "t": [("teach", "lower"), ("Teach", "Cap"), ("TEACH", "ALLCAPS")],
    "s": [("súil", "lower"), ("Súil", "Cap"), ("SÚIL", "ALLCAPS")],
}

# marker spelling -> (tag, which stem group it attaches to)
MARKERS = [
    ("n",   "Ecl",   "vowel"),   # n-éan / nÉan
    ("t",   "TPref", "vowel"),   # t-ainm / tAthair
    ("h",   "HPref", "vowel"),   # hÉireann / h-aoise
    ("t",   "TPref", "s"),       # tsúil
    ("mb",  "Ecl",   "b"),
    ("gc",  "Ecl",   "c"),
    ("nd",  "Ecl",   "d"),
    ("bhf", "Ecl",   "f"),
    ("ng",  "Ecl",   "g"),
    ("bp",  "Ecl",   "p"),
    ("dt",  "Ecl",   "t"),
]


def cells():
    """Every (surface, tag, base, axes) cell in the matrix."""
    out = []
    for marker, tag, group in MARKERS:
        for stem, stem_case in STEMS[group]:
            for marker_case in ("lower", "upper"):
                mk = marker.upper() if marker_case == "upper" else marker
                for hyphen in (False, True):
                    surface = mk + ("-" if hyphen else "") + stem
                    out.append({
                        "surface": surface, "tag": tag, "base": stem,
                        "marker": marker, "marker_case": marker_case,
                        "hyphen": "yes" if hyphen else "no",
                        "stem_case": stem_case,
                        "onset": "vowel" if group == "vowel" else "consonant",
                    })
    # Lenition is not a prefixing marker, so it gets its own small block:
    # the inserted h varies in case and the stem does too.
    for stem, stem_case in (("bean", "lower"), ("Bean", "Cap"),
                            ("BEAN", "ALLCAPS")):
        for h in ("h", "H"):
            surface = stem[0] + h + stem[1:]
            out.append({
                "surface": surface, "tag": "Len", "base": stem,
                "marker": h, "marker_case": "lower" if h == "h" else "upper",
                "hyphen": "no", "stem_case": stem_case, "onset": "consonant",
            })
    return out


def py_probe(c):
    """Python: readings, their inverse_ok, generation, and whether it raises."""
    try:
        readings = M.demutate(c["surface"])
        abort = False
    except AssertionError:
        abort = True
        # Recover the readings the assert interrupted, by rebuilding what
        # demutate() builds before it checks itself.
        readings = _py_readings_no_assert(c["surface"])
    inv = {f"{t}:{b}": M.inverse_ok(t, b, c["surface"]) for t, b in readings}
    gen = M.MUTATE[c["tag"]](c["base"]) if c["tag"] in M.MUTATE else ""
    return {"readings": readings, "inverse": inv, "gen": gen, "abort": abort}


def _py_readings_no_assert(w):
    """demutate() without its trailing self-check. Mirrors the real one."""
    out = M._demutate_core(w)
    if len(w) > 2 and w.isupper():
        for tag, base_l in M._demutate_core(w.lower()):
            cand = (tag, base_l.upper())
            if cand not in out:
                out.append(cand)
    if len(w) > 2 and w[1] == "-" and M._is_vowel(w[2]):
        for pre, tag in (("n", "Ecl"), ("h", "HPref"), ("t", "TPref")):
            if w[0] == pre and (w[2].isupper() or pre == "h"):
                cand = (tag, w[2:])
                if cand not in out:
                    out.append(cand)
    return out


def cpp_batch(cs):
    """One probe call for the whole matrix, both builds."""
    nd_in = "".join(f"A\t{c['surface']}\n" for c in cs)
    nd_in += "".join(f"G\t{c['tag']}\t{c['base']}\n" for c in cs)
    nd = subprocess.run([str(PROBE_ND)], input=nd_in, capture_output=True,
                        text=True, check=True).stdout.splitlines()
    n = len(cs)
    analysis = {}
    for line in nd[:n]:
        f = line.split("\t")
        analysis[f[1]] = f[2] if len(f) > 2 else ""
    gen = {}
    for line in nd[n:2 * n]:
        f = line.split("\t")
        if len(f) > 3:
            gen[(f[1], f[2])] = f[3]

    # Aborting cells: the assert build is fed one word at a time, because an
    # abort takes the whole process with it.
    aborts = set()
    for c in cs:
        p = subprocess.run([str(PROBE_ASSERT)], input=f"A\t{c['surface']}\n",
                           capture_output=True, text=True)
        if p.returncode != 0:
            aborts.add(c["surface"])
    return analysis, gen, aborts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    for p in (PROBE_ND, PROBE_ASSERT):
        if not p.exists():
            raise SystemExit(f"missing {p}; build it first (see "
                             f"mutation_probe.cpp header)")

    cs = cells()
    print(f"{len(cs)} cells")
    analysis, gen, aborts = cpp_batch(cs)

    rows, disagree, py_aborts, cpp_aborts = [], [], [], []
    for c in cs:
        py = py_probe(c)
        cpp_read = analysis.get(c["surface"], "")
        cpp_gen = gen.get((c["tag"], c["base"]), "")
        cpp_abort = c["surface"] in aborts

        py_read = " ".join(
            f"{t}:{b}:{1 if py['inverse'][f'{t}:{b}'] else 0}"
            for t, b in py["readings"])
        agree = (py_read == cpp_read and py["gen"] == cpp_gen
                 and py["abort"] == cpp_abort)
        if not agree:
            disagree.append((c, py_read, cpp_read, py["gen"], cpp_gen,
                             py["abort"], cpp_abort))
        if py["abort"]:
            py_aborts.append(c["surface"])
        if cpp_abort:
            cpp_aborts.append(c["surface"])

        rows.append({
            **c, "py_readings": py_read, "cpp_readings": cpp_read,
            "py_gen": py["gen"], "cpp_gen": cpp_gen,
            "py_abort": py["abort"], "cpp_abort": cpp_abort,
            "round_trips": py["gen"] == c["surface"],
            "agree": agree,
        })

    print(f"python aborts: {len(py_aborts)}")
    print(f"c++ aborts:    {len(cpp_aborts)}")
    print(f"disagreements: {len(disagree)}")

    write(rows, disagree, py_aborts, cpp_aborts, Path(args.out))
    print(f"wrote {args.out}")
    return 0


def write(rows, disagree, py_aborts, cpp_aborts, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    L = []
    L.append("# Mutation layer: orthographic case matrix\n")
    L.append("Generated by `scripts/case_matrix.py`. This is the spec for the "
             "fix to the\nself-check abort at `mutation_fst.cpp:201`, and the "
             "evidence that the fix\nneeded to be about more than the four "
             "forms that were known to abort.\n")
    L.append(f"{len(rows)} cells. Python aborts: **{len(py_aborts)}**. "
             f"C++ aborts: **{len(cpp_aborts)}**. "
             f"Python/C++ disagreements: **{len(disagree)}**.\n")

    L.append("## Cells that abort\n")
    if py_aborts:
        L.append("| surface | tag | base | marker | marker case | hyphen | "
                 "stem case | readings (NDEBUG) | generation | aborts |")
        L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for r in rows:
            if not (r["py_abort"] or r["cpp_abort"]):
                continue
            which = ("both" if r["py_abort"] and r["cpp_abort"]
                     else "python" if r["py_abort"] else "c++")
            L.append(f"| `{r['surface']}` | {r['tag']} | `{r['base']}` | "
                     f"`{r['marker']}` | {r['marker_case']} | {r['hyphen']} | "
                     f"{r['stem_case']} | `{r['py_readings']}` | "
                     f"`{r['py_gen']}` | {which} |")
    else:
        L.append("None.\n")
    L.append("")

    L.append("## Python / C++ disagreements\n")
    if disagree:
        L.append("| surface | py readings | c++ readings | py gen | c++ gen | "
                 "py abort | c++ abort |")
        L.append("| --- | --- | --- | --- | --- | --- | --- |")
        for c, pr, cr, pg, cg, pa, ca in disagree:
            L.append(f"| `{c['surface']}` | `{pr}` | `{cr}` | `{pg}` | "
                     f"`{cg}` | {pa} | {ca} |")
    else:
        L.append("None: the two implementations agree on every cell, "
                 "including which ones abort.\n")
    L.append("")

    L.append("## Full matrix\n")
    L.append("`inverse` is the `:0`/`:1` suffix on each reading: 1 means the "
             "reading passes\nits own `inverse_ok`. A reading with `:0` is "
             "what trips the assert.\n")
    L.append("| surface | marker | mk case | hyphen | stem | stem case | "
             "onset | tag | readings | generation | surface==gen |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        L.append(f"| `{r['surface']}` | `{r['marker']}` | {r['marker_case']} | "
                 f"{r['hyphen']} | `{r['base']}` | {r['stem_case']} | "
                 f"{r['onset']} | {r['tag']} | `{r['py_readings']}` | "
                 f"`{r['py_gen']}` | "
                 f"{'yes' if r['round_trips'] else 'no'} |")
    L.append("")
    dest.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
