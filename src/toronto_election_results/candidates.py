"""Candidate name normalization and cross-election identity.

Names arrive in three formats — ``Last, First`` (2003), ``LAST FIRST`` (2006–2014, upper), and
``Last First`` (2018+) — all **surname-first**. Splitting a comma-less name into surname vs given
name is ambiguous for multi-word surnames, so two signals are used: **known multi-word surnames**
learned from the comma-form years (ground truth), and a **particle rule** (a leading run of
particles like ``Di``/``De``/``Van`` plus the next token is the surname) that only fires with 3+
tokens, so a two-token name whose surname happens to be a particle word (``Le Nha``) is left alone.

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

# Surname prefixes that attach to the following token (e.g. "Di Giorgio", "De La Rose").
PARTICLES = frozenset(
    {
        "di",
        "de",
        "del",
        "della",
        "da",
        "dos",
        "des",
        "der",
        "den",
        "du",
        "van",
        "von",
        "la",
        "le",
        "lo",
        "mac",
        "mc",
        "san",
        "santa",
        "st",
    }
)


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def known_multiword_surnames(raw_names) -> set[str]:
    """Collect multi-word surnames from comma-form (``Last, First``) names — the ground truth."""
    surnames = set()
    for raw in raw_names:
        text = str(raw)
        if "," in text:
            surname = " ".join(text.split(",")[0].split())
            if " " in surname:
                surnames.add(surname.lower())
    return surnames


def _split_surname_first(tokens: list[str], known_surnames) -> tuple[list[str], list[str]]:
    """Split surname-first tokens into (surname tokens, given-name tokens)."""
    lower = [t.lower() for t in tokens]
    # 1) Longest known multi-word surname that prefixes the tokens (leaving a given name).
    for k in range(min(len(tokens) - 1, 4), 1, -1):
        if " ".join(lower[:k]) in known_surnames:
            return tokens[:k], tokens[k:]
    # 2) Particle rule — only with 3+ tokens, so "Le Nha" (surname Le) is untouched.
    if len(tokens) >= 3 and lower[0] in PARTICLES:
        end = 0
        while end < len(tokens) - 1 and lower[end] in PARTICLES:
            end += 1
        if end + 1 < len(tokens):  # keep at least one given-name token
            return tokens[: end + 1], tokens[end + 1 :]
    # 3) Default: first token is the surname.
    return tokens[:1], tokens[1:]


def normalize_name(raw: str, *, known_surnames=frozenset()) -> tuple[str, str | None, str | None]:
    """Return (display "First Last", first_name, last_name) for a raw ballot name.

    Comma-less names are surname-first (``Crisanti Vincent``); a comma means ``Last, First``.
    ``known_surnames`` (multi-word surnames learned from the comma-form years) improves the split
    of comma-less multi-word surnames.
    """
    collapsed = " ".join(raw.split())
    if "," in collapsed:
        last, _, first = collapsed.partition(",")
    else:
        surname_tokens, first_tokens = _split_surname_first(collapsed.split(" "), known_surnames)
        last, first = " ".join(surname_tokens), " ".join(first_tokens)
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
