from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.frontend_feeds import (
    attach_district_display_names,
    build_mayoral_candidates_feed,
    build_person_aliases_feed,
    build_trustee_races_feed,
)
from toronto_election_results.person_alias_curations import load_person_alias_curations
from toronto_election_results.trustee_2026 import load_trustee_ward_crosswalk
from toronto_election_results.trustee_continuity import load_trustee_continuity

ROOT = Path(__file__).resolve().parents[1]


def _row(**overrides):
    row = {
        "candidacy_id": "can_current",
        "person_id": "per_current",
        "event_id": "evt_2026",
        "contest_id": "con_2026_mayor",
        "election_date": "2026-10-26",
        "election_year": 2026,
        "represented_body": "toronto_city_council",
        "office_type": "mayor",
        "candidate_name": "Current Candidate",
        "candidate_name_raw": "Candidate, Current",
        "campaign_url": pd.NA,
        "party_name": pd.NA,
        "district_name": "City of Toronto",
        "result_status": "pending",
        "coverage_status": "complete",
        "source_resource": "2026 Municipal Election — Certified Candidates",
        "elected": pd.NA,
        "acclaimed": False,
        "vote_share": pd.NA,
        "vote_rank": pd.NA,
        "n_candidates": 2,
    }
    row.update(overrides)
    return row


def _reviews(*candidacy_ids):
    return pd.DataFrame(
        [
            {
                "cohort_id": "toronto-mayor-2026",
                "subject_candidacy_id": candidacy_id,
                "source_release": "results-2026-08-26.1",
                "review_date": "2026-08-26",
                "review_status": "reviewed",
                "limitations": "",
                "public_coverage_note": "",
            }
            for candidacy_id in candidacy_ids
        ]
    )


def test_candidate_feed_uses_canonical_people_for_history_and_incumbency():
    rows = pd.DataFrame(
        [
            _row(
                candidacy_id="can_chow_2026",
                person_id="per_chow",
                candidate_name="Olivia Chow",
                candidate_name_raw="Chow, Olivia",
                campaign_url="https://www.oliviachow.ca",
            ),
            _row(
                candidacy_id="can_gong_2026",
                person_id="per_gong",
                candidate_name="Edward Gong",
                candidate_name_raw="Gong, Edward",
            ),
            _row(
                candidacy_id="can_chow_2023",
                person_id="per_chow",
                event_id="evt_2023",
                contest_id="con_2023_mayor",
                election_date="2023-06-26",
                election_year=2023,
                candidate_name="Olivia Chow",
                candidate_name_raw="Chow, Olivia",
                result_status="final",
                source_resource="Official results",
                elected=True,
                vote_share=0.3717,
                vote_rank=1,
                n_candidates=102,
            ),
            _row(
                candidacy_id="can_gong_2023",
                person_id="per_gong",
                event_id="evt_2023",
                contest_id="con_2023_mayor",
                election_date="2023-06-26",
                election_year=2023,
                candidate_name="Xiao Hua Gong",
                candidate_name_raw="Gong Xiao Hua",
                result_status="final",
                source_resource="Official results",
                elected=False,
                vote_share=0.0041,
                vote_rank=11,
                n_candidates=102,
            ),
            _row(
                candidacy_id="can_gong_2025",
                person_id="per_gong",
                event_id="evt_2025",
                contest_id="con_2025_mp",
                election_date="2025-04-28",
                election_year=2025,
                represented_body="canada_house_of_commons",
                office_type="mp",
                candidate_name="Xiaohua Gong",
                candidate_name_raw="Xiaohua Gong",
                result_status="final",
                source_resource="Official results",
                elected=False,
                vote_share=0.0054,
                vote_rank=5,
                n_candidates=6,
            ),
        ]
    )

    reviews = _reviews("can_chow_2026", "can_gong_2026")
    reviews.loc[reviews["subject_candidacy_id"].eq("can_chow_2026"), "public_coverage_note"] = (
        "We identified a Toronto school trustee candidacy in 1985 "
        "but could not recover authoritative results."
    )
    reviews.loc[reviews["subject_candidacy_id"].eq("can_chow_2026"), "limitations"] = (
        "Internal technical review limitation."
    )
    feed = build_mayoral_candidates_feed(rows, reviews)

    assert feed["schema_version"] == 5
    assert feed["ballot_certified"] is True
    assert feed["coverage"]["policy"] == "full_verified_canadian_electoral_career"
    assert feed["coverage"]["year_cutoff"] is None
    assert [candidate["display_name"] for candidate in feed["candidates"]] == [
        "Olivia Chow",
        "Edward Gong",
    ]
    chow, gong = feed["candidates"]
    assert chow["is_incumbent"] is True
    assert chow["campaign_url"] == "https://www.oliviachow.ca"
    assert chow["review_limitations"] == (
        "We identified a Toronto school trustee candidacy in 1985 "
        "but could not recover authoritative results."
    )
    assert "Internal technical review limitation." not in chow.values()
    assert gong["is_incumbent"] is False
    assert gong["review_limitations"] is None
    assert gong["person_id"] == "per_gong"
    assert [(race["year"], race["office_type"]) for race in gong["past_elections"]] == [
        (2025, "mp"),
        (2023, "mayor"),
    ]
    assert gong["past_elections"][1]["rank"] == 11


def test_candidate_feed_rejects_an_incomplete_current_field():
    rows = pd.DataFrame([_row(coverage_status="partial")])

    with pytest.raises(ValueError, match="complete certified roster"):
        build_mayoral_candidates_feed(rows, _reviews("can_current"))


def test_person_aliases_are_owned_by_results_and_ambiguous_names_do_not_resolve():
    results = pd.DataFrame(
        [
            _row(
                person_id="per_gong",
                candidate_name="Edward Gong",
                candidate_name_raw="Gong, Edward",
            ),
            _row(person_id="per_first", candidate_name="Alex Lee", candidate_name_raw="LEE Alex"),
            _row(person_id="per_second", candidate_name="Alex Lee", candidate_name_raw="Lee, Alex"),
        ]
    )
    people = pd.DataFrame(
        [
            {
                "person_id": "per_gong",
                "preferred_name": "Xiaohua Gong",
                "identity_status": "active",
            },
            {"person_id": "per_first", "preferred_name": "Alex Lee", "identity_status": "active"},
            {
                "person_id": "per_second",
                "preferred_name": "Alexander Lee",
                "identity_status": "active",
            },
        ]
    )

    feed = build_person_aliases_feed(results, people)

    by_name = {row["reported_name"]: row for row in feed["aliases"]}
    assert by_name["Edward Gong"]["person_id"] == "per_gong"
    assert by_name["Xiaohua Gong"]["person_id"] == "per_gong"
    assert by_name["Alex Lee"]["person_id"] is None
    assert by_name["Alex Lee"]["is_unambiguous"] is False


def test_person_aliases_include_evidence_backed_names_without_result_rows():
    results = pd.DataFrame([_row(person_id="per_existing", candidate_name="Gabriel Blanc")])
    people = pd.DataFrame(
        [
            {
                "person_id": "per_existing",
                "preferred_name": "Gabriel Blanc",
                "identity_status": "active",
            },
            {
                "person_id": "per_withdrawn",
                "preferred_name": "Dana Fisher",
                "identity_status": "active",
            },
        ]
    )
    curations = pd.DataFrame(
        [
            {"reported_name": "Gabe Blanc", "person_id": "per_existing"},
            {"reported_name": "Dana Fisher", "person_id": "per_withdrawn"},
        ]
    )

    feed = build_person_aliases_feed(results, people, curations)

    by_name = {row["reported_name"]: row for row in feed["aliases"]}
    assert by_name["Gabe Blanc"]["person_id"] == "per_existing"
    assert by_name["Dana Fisher"]["person_id"] == "per_withdrawn"


def test_person_aliases_keep_a_curated_collision_ambiguous():
    results = pd.DataFrame([_row(person_id="per_result", candidate_name="Shared Name")])
    people = pd.DataFrame(
        [
            {
                "person_id": "per_result",
                "preferred_name": "Result Person",
                "identity_status": "active",
            },
            {
                "person_id": "per_curated",
                "preferred_name": "Curated Person",
                "identity_status": "active",
            },
        ]
    )
    curations = pd.DataFrame([{"reported_name": "Shared Name", "person_id": "per_curated"}])

    feed = build_person_aliases_feed(results, people, curations)

    aliases = [row for row in feed["aliases"] if row["reported_name"] == "Shared Name"]
    assert {row["person_id"] for row in aliases} == {None}
    assert {row["is_unambiguous"] for row in aliases} == {False}


def test_repository_poll_aliases_resolve_to_the_audited_people():
    feed = build_person_aliases_feed(
        pd.read_csv(ROOT / "data/out/election_results.csv", low_memory=False),
        pd.read_csv(ROOT / "data/out/people.csv", low_memory=False),
        load_person_alias_curations(ROOT / "data/reference/person_alias_curations.csv"),
    )

    by_name = {row["reported_name"]: row for row in feed["aliases"]}
    assert by_name["David DiGiorgio"]["person_id"] == ("per_c420decb6687572fa82550c1eae3dd23")
    assert by_name["Gabe Blanc"]["person_id"] == ("per_a1e80916906e5b1a9c91b435e6499ea7")
    assert by_name["Dana Fisher"]["person_id"] == ("per_0598fabaa9a944ef91808b0f8037e884")
    assert all(
        by_name[name]["is_unambiguous"]
        for name in (
            "David DiGiorgio",
            "Gabe Blanc",
            "Dana Fisher",
        )
    )


def test_trustee_feed_publishes_the_complete_field_and_only_confirmed_history():
    results = pd.read_csv(ROOT / "data/out/election_results.csv", low_memory=False)
    results = attach_district_display_names(
        results,
        pd.read_csv(ROOT / "data/out/electoral_districts.csv", low_memory=False),
    )
    reference = ROOT / "data/reference"

    feed = build_trustee_races_feed(
        results,
        load_trustee_ward_crosswalk(reference / "trustee_ward_crosswalks.csv"),
        load_trustee_continuity(reference / "trustee_contest_continuity_2026.csv"),
        pd.read_csv(
            reference / "trustee_career_cohort_2026.csv",
            dtype="string",
            keep_default_na=False,
        ),
        pd.read_csv(
            reference / "trustee_career_reviews.csv",
            dtype="string",
            keep_default_na=False,
        ),
        pd.read_csv(
            reference / "trustee_career_decisions.csv",
            dtype="string",
            keep_default_na=False,
        ),
    )

    assert feed["schema_version"] == 3
    assert feed["ballot_certified"] is True
    assert [board["board_id"] for board in feed["boards"]] == [
        "tdsb",
        "tcdsb",
        "viamonde",
        "monavenir",
    ]
    assert [board["candidate_count"] for board in feed["boards"]] == [77, 31, 4, 6]
    assert sum(len(board["wards"]) for board in feed["boards"]) == 29
    assert sum(ward["acclaimed"] for board in feed["boards"] for ward in board["wards"]) == 4
    prior_results = {
        (board["board_id"], ward["ward_id"]): ward["comparable_prior_result"]
        for board in feed["boards"]
        for ward in board["wards"]
    }
    assert all(prior_results[("tdsb", str(ward))] is None for ward in range(1, 13))
    assert sum(result is not None for result in prior_results.values()) == 14
    assert prior_results[("tcdsb", "1")]["winner_name"] == "Joseph Martino"
    assert prior_results[("tcdsb", "1")]["margin_votes"] == 1
    assert prior_results[("viamonde", "3")]["winner_name"] == "Anna-Karyna Ruszkowski"
    assert prior_results[("monavenir", "4")]["winner_name"] == "Rhea Dechaine"
    assert prior_results[("viamonde", "2")] is None
    assert prior_results[("viamonde", "4")] is None
    assert prior_results[("monavenir", "3")] is None
    candidates = [
        candidate
        for board in feed["boards"]
        for ward in board["wards"]
        for candidate in ward["candidates"]
    ]
    assert len(candidates) == 118
    assert sum(candidate["is_incumbent"] is True for candidate in candidates) == 20
    assert sum(candidate["is_incumbent"] is None for candidate in candidates) == 98
    assert sum(bool(candidate["past_elections"]) for candidate in candidates) == 28
    assert sum(len(candidate["past_elections"]) for candidate in candidates) == 80
    assert all(
        election["election_date"] >= "2003-01-01"
        for candidate in candidates
        for election in candidate["past_elections"]
    )
    assert all(
        election["district_display_name"]
        for candidate in candidates
        for election in candidate["past_elections"]
        if election["office_type"] == "trustee"
    )
    assert all("review_status" not in candidate for candidate in candidates)
    assert all("review_limitations" not in candidate for candidate in candidates)
    rosina = next(
        candidate for candidate in candidates if candidate["display_name"] == "Rosina Bonavota"
    )
    assert rosina["past_elections"] == []
