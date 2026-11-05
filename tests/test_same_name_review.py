"""The review of same-name Persons, November 2026, and the fixes made with it."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from toronto_election_results.identity_curations import PERSON_RECORD_MERGE_ASSERTIONS

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
REVIEW_DIR = REPO_ROOT / "docs" / "verification" / "same-name-review-2026-11-03"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / name, dtype="string")


def _review(name: str) -> pd.DataFrame:
    return pd.read_csv(REVIEW_DIR / name, dtype="string", keep_default_na=False)


def test_review_covers_every_same_name_group_once():
    groups = _review("groups.csv")
    assert groups["group_id"].is_unique
    assert len(groups) == 155
    assert groups["same_name_pairs"].astype(int).sum() == 177
    assert groups["outcome"].value_counts().to_dict() == {
        "undetermined": 87,
        "joined": 63,
        "partly joined": 3,
        "different people": 2,
    }
    # A group is joined only on a join that a second check accepted.
    joined = groups.loc[groups["outcome"].isin({"joined", "partly joined"})]
    assert joined["second_check"].str.contains("ACCEPT").all()
    assert joined["assertion_ids"].ne("").all()


def test_review_joins_are_record_merges_in_the_release():
    joins = _review("joins.csv")
    merges = {assertion.assertion_id: assertion for assertion in PERSON_RECORD_MERGE_ASSERTIONS}
    results = _read("election_results.csv").set_index("candidacy_id")
    people = _read("people.csv").set_index("person_id")

    assert len(joins) == 71
    for row in joins.itertuples(index=False):
        merge = merges[row.assertion_id]
        assert merge.canonical_person_id == row.canonical_person_id
        pinned = row.pinned_candidacy_ids.split(";")
        assert {o.candidacy_id for o in merge.occurrences} == set(pinned)
        assert results.loc[pinned, "person_id"].eq(row.canonical_person_id).all(), row.group_id
        assert people.loc[row.canonical_person_id, "preferred_name"] == row.preferred_name
        for merged in filter(None, row.merged_person_ids.split(";")):
            assert merged not in people.index, merged


# Missed links the check of authority incumbency flags found, with every run each Person holds.
INCUMBENT_CAREERS = {
    # Joseph Cordiano: 1995 Lawrence and 1999 and 2003 York South—Weston.
    "per_388439f4a559551a93ee9f577b3b7df6": [
        "can_2da22b86c97a520db9524642b115dfbd",
        "can_ff256783dfae54358db4d8f5fa430062",
        "can_718b880aa85058f9aae0f64efa2da74f",
    ],
}


def test_flagged_incumbents_have_an_earlier_win_or_predate_the_release():
    results = pd.read_csv(OUT / "election_results.csv", dtype="string", keep_default_na=False)
    for person_id, candidacy_ids in INCUMBENT_CAREERS.items():
        own = results.loc[results["person_id"].eq(person_id), "candidacy_id"]
        assert sorted(own) == sorted(candidacy_ids), person_id

    first_general = (
        results.loc[results["election_type"].eq("general")]
        .groupby("represented_body")["election_date"]
        .min()
    )
    elected = results.loc[results["elected"].eq("True") & results["person_id"].ne("")]
    unexplained = []
    for row in results.loc[results["incumbent_reported"].eq("True")].itertuples(index=False):
        if row.election_date <= first_general[row.represented_body]:
            continue
        earlier = elected.loc[
            elected["person_id"].eq(row.person_id)
            & elected["represented_body"].eq(row.represented_body)
            & (elected["election_date"] < row.election_date)
        ]
        if earlier.empty:
            unexplained.append((row.election_date, row.candidate_name))
    # John Tory first won a 2005 by-election outside Toronto.
    assert unexplained == [("2007-10-10", "JOHN TORY")]


def test_incumbent_flags_that_contradict_the_record_are_corrected():
    results = _read("election_results.csv").set_index("candidacy_id")
    tenures = _read("office_tenures.csv")

    # Elections Ontario flags John Sewell as the incumbent in Toronto Centre—Rosedale in 1999;
    # he never sat in the legislature.
    sewell = results.loc["can_c6fb75a0c3d254a6aa82b704a7ed1ab0"]
    assert sewell["incumbent_reported"] == "False"
    assert sewell["incumbent"] == "False"
    assert not (
        tenures["person_id"].eq(sewell["person_id"])
        & tenures["represented_body"].eq("ontario_legislative_assembly")
    ).any()

    # Elections Canada flags both John Carmichael and Natalie Hunt in Don Valley West in 2015.
    assert results.loc["can_8a6c7337bdf7579891dd95c0dab5e033", "incumbent_reported"] == "False"


def test_parkdale_high_park_2006_has_one_liberal():
    results = _read("election_results.csv")
    contest = results.loc[
        results["election_date"].eq("2006-09-14")
        & results["district_name"].eq("Parkdale—High Park")
    ].set_index("candidate_name")
    assert contest.loc["JIM MCINTOSH", "party_name"] == "Ontario Libertarian Party"
    assert contest.loc["SYLVIA WATSON", "party_name"] == "Ontario Liberal Party"
    party_ids = results.loc[results["party_id"].notna()].groupby("contest_id")["party_id"]
    assert party_ids.apply(lambda ids: ids.is_unique).all()


def test_the_2003_john_steele_run_is_held():
    results = _read("election_results.csv").set_index("candidacy_id")
    links = _read("candidacy_person_links.csv")

    assert pd.isna(results.loc["can_45191a44a24353f682ec876f44cf2a27", "person_id"])
    held = links.loc[links["candidacy_id"].eq("can_45191a44a24353f682ec876f44cf2a27")]
    assert held["link_status"].tolist() == ["unresolved"]


def test_review_results_carry_no_contact_details():
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    phone = re.compile(r"\(?\b\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b")
    paths = sorted(REVIEW_DIR.glob("*.csv"))
    assert [path.name for path in paths] == [
        "groups.csv",
        "held_run_pairings.csv",
        "joins.csv",
        "near_name_pairs.csv",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not email.search(text), path.name
        assert not phone.search(text), path.name
        assert "file://" not in text, path.name
