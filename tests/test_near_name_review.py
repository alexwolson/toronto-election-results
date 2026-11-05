"""The review of near-name Persons, November 2026."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pandas as pd

from toronto_election_results.identity_curations import PERSON_RECORD_MERGE_ASSERTIONS

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
REVIEW_DIR = REPO_ROOT / "docs" / "verification" / "near-name-review-2026-11-04"
FRAME = REPO_ROOT / "docs" / "verification" / "same-name-review-2026-11-03" / "near_name_pairs.csv"
OUTCOMES = {"undetermined": 44, "joined": 26, "different people": 1}
JOINS = 24


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / name, dtype="string")


def _review(name: str) -> pd.DataFrame:
    return pd.read_csv(REVIEW_DIR / name, dtype="string", keep_default_na=False)


def _load_script(name: str):
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(REPO_ROOT / "scripts"))
    return module


def test_review_covers_every_near_name_pair_once():
    pairs = _review("pairs.csv")
    frame = pd.read_csv(FRAME, dtype="string", keep_default_na=False)
    assert pairs["pair_id"].is_unique
    assert sorted(pairs["pair_id"]) == sorted(frame["pair_id"])
    by_pair = frame.set_index("pair_id")
    for row in pairs.itertuples(index=False):
        assert {row.person_a, row.person_b} == {
            by_pair.loc[row.pair_id, "person_a"],
            by_pair.loc[row.pair_id, "person_b"],
        }
    assert pairs["outcome"].value_counts().to_dict() == OUTCOMES
    # A pair is joined only on a join that a second check accepted.
    joined = pairs.loc[pairs["outcome"].eq("joined")]
    assert joined["second_check"].isin({"ACCEPT", "PARTIAL"}).all()
    assert joined["assertion_id"].ne("").all()


def test_review_joins_are_record_merges_in_the_release():
    joins = _review("joins.csv")
    pairs = _review("pairs.csv")
    merges = {assertion.assertion_id: assertion for assertion in PERSON_RECORD_MERGE_ASSERTIONS}
    results = _read("election_results.csv").set_index("candidacy_id")
    people = _read("people.csv").set_index("person_id")

    assert len(joins) == JOINS
    members = {}
    for row in joins.itertuples(index=False):
        merge = merges[row.assertion_id]
        assert merge.canonical_person_id == row.canonical_person_id
        pinned = row.pinned_candidacy_ids.split(";")
        assert {o.candidacy_id for o in merge.occurrences} == set(pinned)
        assert results.loc[pinned, "person_id"].eq(row.canonical_person_id).all(), row.item_id
        assert people.loc[row.canonical_person_id, "preferred_name"] == row.preferred_name
        merged = list(filter(None, row.merged_person_ids.split(";")))
        for person_id in merged:
            assert person_id not in people.index, person_id
        members[row.assertion_id] = {row.canonical_person_id, *merged}
    for row in pairs.loc[pairs["outcome"].eq("joined")].itertuples(index=False):
        assert {row.person_a, row.person_b} <= members[row.assertion_id], row.pair_id


def test_near_name_pairs_left_after_the_merges():
    script = _load_script("list_near_name_pairs")
    results = pd.read_csv(OUT / "election_results.csv", dtype="string", keep_default_na=False)
    left = script.near_name_frame(results)
    pairs = _review("pairs.csv")
    open_pairs = pairs.loc[pairs["outcome"].ne("joined")]
    # Every pair the review did not join is still listed, and the merges created no new ones.
    listed = set(zip(left["person_a"], left["person_b"]))
    for row in open_pairs.itertuples(index=False):
        assert tuple(sorted((row.person_a, row.person_b))) in listed, row.pair_id
    assert len(left) == len(open_pairs)


def test_review_results_carry_no_contact_details():
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    phone = re.compile(r"\(?\b\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b")
    paths = sorted(REVIEW_DIR.glob("*.csv"))
    assert [path.name for path in paths] == ["joins.csv", "pairs.csv"]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not email.search(text), path.name
        assert not phone.search(text), path.name
        assert "file://" not in text, path.name
