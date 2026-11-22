"""Fuzz the mutation layer: no aborts, no dropped readings, exact parity.

Three things have to hold over every input, and all three are checked here
rather than assumed:

1. **No abort.** `demutate` is an input path. It must return for any string,
   including empty, whitespace, punctuation and mixed scripts.
2. **No dropped reading.** `demutate` now filters out a candidate that fails
   its own inverse check instead of asserting, which would be a silent loss
   if it ever fired. Comparing against `demutate_candidates` makes the drop
   count visible; it must be zero.
3. **Exact parity.** The Python reference and the C++ port must return the
   same readings, in the same order, for every input. This is the contract
   `mutation_fst.h` states, extended from the two test files to whole corpora.

Inputs: every distinct form in Jane's GA corpus, every MoirfEolas word, every
surface in the attested file, and synthetic strings built from the axes of
docs/mutation_case_matrix.md over random Irish-alphabet stems, with fadas,
both apostrophe shapes, hyphens and degenerate whitespace.

The C++ side is read through `mutation_probe` built *with* the assert live, so
an abort shows up as a non-zero exit rather than being hidden.
"""
import argparse
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mutations as M                                           # noqa: E402

SCALPEL = Path.home() / "code" / "Scalpel"
PROBE = SCALPEL / "mutation_probe"
MORPH = Path.home() / "code" / "morphology"
GA = MORPH / "external" / "tknzn4Irish" / "data" / "GA" / "all_ga_input.txt"
MOIRFEOLAS = MORPH / "external" / "tknzn4Irish" / "data" / "MoirfEolas" / "MoirfEolas.csv"
ATTESTED = ROOT / "tests" / "attested_mutations.tsv"

SEED = 20261122
N_SYNTHETIC = 100_000
BATCH = 20_000

ALPHABET = "abcdefghilmnoprstuáéíóú"
MARKERS = ["n", "t", "h", "mb", "gc", "nd", "bhf", "ng", "bp", "dt", "N", "T", "H"]
APOSTROPHES = ["'", "’", "ʼ"]
DEGENERATE = ["", " ", "  ", "\t", "\n", "-", "--", "'", "’", ".", "..",
              "a", "A", "á", "-a", "a-", "n-", "t-", "h-", "n", "t", "h",
              "  n-APP  ", " ", "n-’APP", "d'", "D'", "m'", "b'"]


def corpus_inputs():
    """Real inputs: the GA corpus, MoirfEolas, and the attested surfaces."""
    out = {}
    if GA.exists():
        with open(GA, encoding="utf-8") as f:
            ga = {line.strip() for line in f if line.strip()}
        out["ga_corpus"] = sorted(ga)
    if MOIRFEOLAS.exists():
        import csv
        with open(MOIRFEOLAS, encoding="utf-8") as f:
            out["moirfeolas"] = sorted({r["word"] for r in csv.DictReader(f)})
    if ATTESTED.exists():
        with open(ATTESTED, encoding="utf-8") as f:
            out["attested"] = sorted({
                line.split("\t")[0] for line in f
                if line.strip() and not line.startswith("#")})
    return out


def synthetic(n, rng):
    """Strings built from the matrix axes over random stems.

    The point is not plausibility: it is to walk the marker / case / hyphen /
    onset space over stems the corpus never contained, so the realisation
    enumeration is exercised outside the cells it was written against.
    """
    out = set()
    while len(out) < n:
        stem = "".join(rng.choice(ALPHABET)
                       for _ in range(rng.randint(1, 9)))
        style = rng.randrange(4)
        if style == 1:
            stem = stem.capitalize()
        elif style == 2:
            stem = stem.upper()
        elif style == 3 and len(stem) > 2:
            # mixed case, which no convention produces and all of it must survive
            stem = "".join(c.upper() if rng.random() < 0.5 else c for c in stem)

        kind = rng.randrange(6)
        if kind == 0:
            w = stem
        elif kind == 1:
            w = rng.choice(MARKERS) + stem
        elif kind == 2:
            w = rng.choice(MARKERS) + "-" + stem
        elif kind == 3:
            # lenition shapes: consonant + h, legal and illegal
            w = rng.choice("bcdfgmpstBCDFGMPST") + rng.choice("hH") + stem
        elif kind == 4:
            w = rng.choice("dmbDMB") + rng.choice(APOSTROPHES) + stem
        else:
            parts = [stem, "".join(rng.choice(ALPHABET)
                                   for _ in range(rng.randint(1, 5)))]
            w = ("-" if rng.random() < 0.5 else "").join(parts)
        out.add(w)
    return sorted(out)


def py_side(words):
    """{word: (readings_str, n_dropped)} from the Python reference."""
    out = {}
    for w in words:
        cands = M.demutate_candidates(w)
        kept = [(t, b) for t, b in cands if M.inverse_ok(t, b, w)]
        out[w] = (" ".join(f"{t}:{b}:1" for t, b in kept),
                  len(cands) - len(kept))
    return out


def cpp_side(words):
    """{word: (readings_str, n_dropped)} from the C++ port, via the probe.

    Runs in batches with the assert build, so an abort surfaces as a non-zero
    exit and the batch is then bisected to name the offending input.
    """
    out, aborted = {}, []

    def run(batch):
        if not batch:
            return
        payload = "".join(f"A\t{w}\nC\t{w}\n" for w in batch)
        p = subprocess.run([str(PROBE)], input=payload,
                           capture_output=True, text=True)
        if p.returncode != 0:
            if len(batch) == 1:
                aborted.append(batch[0])
                return
            mid = len(batch) // 2
            run(batch[:mid])
            run(batch[mid:])
            return
        lines = p.stdout.splitlines()
        # A and C alternate, two lines per word.
        for i, w in enumerate(batch):
            a = lines[2 * i].split("\t")
            c = lines[2 * i + 1].split("\t")
            kept = a[2] if len(a) > 2 else ""
            cands = c[2] if len(c) > 2 else ""
            n_c = len(cands.split()) if cands else 0
            n_k = len(kept.split()) if kept else 0
            out[w] = (kept, n_c - n_k)

    # A word containing a newline or tab cannot go through a line protocol;
    # those are checked on the Python side only and reported as such.
    safe = [w for w in words if "\n" not in w and "\t" not in w]
    for i in range(0, len(safe), BATCH):
        run(safe[i:i + BATCH])
    return out, aborted, len(words) - len(safe)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--synthetic", type=int, default=N_SYNTHETIC)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    if not PROBE.exists():
        raise SystemExit(f"missing {PROBE}; build it (see mutation_probe.cpp)")

    rng = random.Random(args.seed)
    groups = corpus_inputs()
    groups["synthetic"] = synthetic(args.synthetic, rng)
    groups["degenerate"] = DEGENERATE

    total = failures = 0
    print(f"{'group':<14}{'inputs':>9}{'py drops':>10}{'cpp drops':>11}"
          f"{'aborts':>8}{'mismatch':>10}{'skipped':>9}")
    bad_examples = []
    for name, words in groups.items():
        py = py_side(words)
        cpp, aborted, skipped = cpp_side(words)
        py_drops = sum(d for _, d in py.values())
        cpp_drops = sum(d for _, d in cpp.values())
        mism = [w for w in cpp if py[w][0] != cpp[w][0]]
        total += len(words)
        failures += py_drops + cpp_drops + len(aborted) + len(mism)
        if mism and len(bad_examples) < 10:
            for w in mism[:5]:
                bad_examples.append((name, w, py[w][0], cpp[w][0]))
        if aborted:
            bad_examples.append((name, "ABORTED", str(aborted[:5]), ""))
        print(f"{name:<14}{len(words):>9}{py_drops:>10}{cpp_drops:>11}"
              f"{len(aborted):>8}{len(mism):>10}{skipped:>9}")

    print(f"\n{total} inputs checked")
    if bad_examples:
        print("\nfailures:")
        for name, w, a, b in bad_examples:
            print(f"  [{name}] {w!r}\n    py  {a!r}\n    cpp {b!r}")
    print("\nRESULT:", "clean" if failures == 0
          else f"{failures} problem(s)")
    print("skipped = inputs containing a newline or tab, which cannot cross "
          "the probe's\n          line protocol; those are Python-side only.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
