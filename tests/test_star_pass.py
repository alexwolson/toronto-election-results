"""The November 2026 search of the Toronto Star for undetermined name pairs (D15)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from toronto_election_results.identity_curations import PERSON_RECORD_MERGE_ASSERTIONS

REPO_ROOT = Path(__file__).parents[1]
ITEMS = REPO_ROOT / "docs" / "verification" / "star-pass-2026-11-07" / "items.csv"


def _items() -> pd.DataFrame:
    return pd.read_csv(ITEMS, dtype=str, keep_default_na=False)


def test_every_join_is_applied_to_one_person():
    items = _items()
    merges = {assertion.assertion_id: assertion for assertion in PERSON_RECORD_MERGE_ASSERTIONS}
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype=str, keep_default_na=False
    ).set_index("candidacy_id")
    joined = items.loc[items["outcome"].isin(["joined", "joined in part"])]
    assert len(joined) == 9
    for row in joined.itertuples(index=False):
        for assertion_id in row.assertion_ids.split(";"):
            merge = merges[assertion_id]
            pinned = [occurrence.candidacy_id for occurrence in merge.occurrences]
            assert results.loc[pinned, "person_id"].eq(merge.canonical_person_id).all()
            # The articles that settle a join are listed with the item.
            proquest = {url for url in merge.evidence_urls if "proquest.com" in url}
            assert proquest <= set(filter(None, row.source_urls.split(";"))), assertion_id
    assert items.loc[~items.index.isin(joined.index), "assertion_ids"].eq("").all()


def test_results_carry_no_contact_details():
    text = ITEMS.read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    assert not re.search(r"\(?\b\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b", text)
