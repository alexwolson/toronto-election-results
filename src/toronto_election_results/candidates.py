"""Candidate name normalization and cross-election identity.

Names arrive in three formats — ``Last, First`` (2003), ``LAST FIRST`` (2006–2014, upper), and
``Last First`` (2018+) — all **surname-first**. Normalization produces a display ``First Last``
plus a best-effort first/last split (imperfect for multi-word surnames in the comma-less years).

Identity is resolved with a **token-sorted, accent-stripped, case-folded key** so that ordering
and split differences collapse (``Frank Di Giorgio`` and ``Giorgio Frank Di`` share a key), then a
fuzzy pass (rapidfuzz ``token_set_ratio``) merges near-duplicate keys. Each row carries a
``candidate_id`` and a ``candidate_id_confidence`` in [0, 1] — 1.0 for exact-key links, the
linking similarity for fuzzy merges. It is a derived, uncertain link, not ground truth.
"""

from __future__ import annotations

import unicodedata

import pandas as pd
from rapidfuzz import fuzz, process

DEFAULT_THRESHOLD = 88


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_name(raw: str) -> tuple[str, str | None, str | None]:
    """Return (display "First Last", first_name, last_name) for a raw ballot name.

    Comma-less names in the City Excel files are surname-first (``Crisanti Vincent``); a comma
    means ``Last, First``.
    """
    collapsed = " ".join(raw.split())
    if "," in collapsed:
        last, _, first = collapsed.partition(",")
    else:
        tokens = collapsed.split(" ")
        last, first = tokens[0], " ".join(tokens[1:])
    first, last = first.strip().title(), last.strip().title()
    display = f"{first} {last}".strip()
    return display, (first or None), (last or None)


def match_key(name: str) -> str:
    """Order/accent/case-independent identity key from a normalized name."""
    return " ".join(sorted(_strip_accents(name).casefold().split()))


class _UnionFind:
    def __init__(self, items):
        self.parent = {x: x for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def assign_candidate_ids(df: pd.DataFrame, *, threshold: int = DEFAULT_THRESHOLD) -> pd.DataFrame:
    """Add ``candidate_id`` + ``candidate_id_confidence`` by clustering ``candidate_name``."""
    df = df.copy()
    row_keys = df["candidate_name"].map(match_key)
    keys = sorted(row_keys.unique())

    uf = _UnionFind(keys)
    confidence = {k: 1.0 for k in keys}
    if len(keys) > 1:
        scores = process.cdist(keys, keys, scorer=fuzz.token_set_ratio)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                score = scores[i][j]
                if score >= threshold:
                    uf.union(keys[i], keys[j])
                    frac = score / 100.0
                    confidence[keys[i]] = min(confidence[keys[i]], frac)
                    confidence[keys[j]] = min(confidence[keys[j]], frac)

    root_ids: dict[str, str] = {}
    for key in keys:
        root = uf.find(key)
        if root not in root_ids:
            root_ids[root] = f"c{len(root_ids) + 1:05d}"

    df["candidate_id"] = row_keys.map(lambda k: root_ids[uf.find(k)])
    df["candidate_id_confidence"] = row_keys.map(confidence)
    return df
