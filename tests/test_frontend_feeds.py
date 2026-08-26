import pandas as pd
import pytest

from toronto_election_results.frontend_feeds import (
    build_mayoral_candidates_feed,
    build_person_aliases_feed,
)


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


def test_candidate_feed_uses_canonical_people_for_history_and_incumbency():
    rows = pd.DataFrame(
        [
            _row(
                candidacy_id="can_chow_2026",
                person_id="per_chow",
                candidate_name="Olivia Chow",
                candidate_name_raw="Chow, Olivia",
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

    feed = build_mayoral_candidates_feed(rows)

    assert feed["schema_version"] == 2
    assert feed["ballot_certified"] is True
    assert [candidate["display_name"] for candidate in feed["candidates"]] == [
        "Olivia Chow",
        "Edward Gong",
    ]
    chow, gong = feed["candidates"]
    assert chow["is_incumbent"] is True
    assert gong["is_incumbent"] is False
    assert gong["person_id"] == "per_gong"
    assert [(race["year"], race["office_type"]) for race in gong["past_elections"]] == [
        (2025, "mp"),
        (2023, "mayor"),
    ]
    assert gong["past_elections"][1]["rank"] == 11


def test_candidate_feed_rejects_an_incomplete_current_field():
    rows = pd.DataFrame([_row(coverage_status="partial")])

    with pytest.raises(ValueError, match="complete certified roster"):
        build_mayoral_candidates_feed(rows)


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
