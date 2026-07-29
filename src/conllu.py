"""Minimal CoNLL-U reader (stdlib only). Yields sentences as lists of dicts.

Skips multiword-token ranges (1-2) and empty nodes (1.1); we want the
syntactic-word rows, which carry lemma/feats in IDT.
"""

FIELDS = ("id", "form", "lemma", "upos", "xpos", "feats", "head", "deprel",
          "deps", "misc")


def parse_feats(s: str) -> dict:
    if s in ("_", ""):
        return {}
    out = {}
    for kv in s.split("|"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            out[k] = v
    return out


def sentences(path):
    sent = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                if sent:
                    yield sent
                    sent = []
                continue
            if line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) != 10 or "-" in cols[0] or "." in cols[0]:
                continue
            tok = dict(zip(FIELDS, cols))
            tok["featdict"] = parse_feats(tok["feats"])
            sent.append(tok)
    if sent:
        yield sent


def tokens(paths):
    for p in paths:
        for sent in sentences(p):
            for i, tok in enumerate(sent):
                tok["prev"] = sent[i - 1] if i > 0 else None
                yield tok
