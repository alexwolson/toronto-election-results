"""Cross-table quality gates for the expanded relational release."""

from datetime import date

import pandas as pd
import pytest
from shapely.geometry import box

from toronto_election_results.release_validation import validate_release
from toronto_election_results.schema import (
    attach_parties,
    build_contests,
    build_events,
    build_parties,
    derive_result_metrics,
    normalize_adapter_frame,
)


def _release():
    rows = pd.DataFrame(
        {
            "event_id": ["event-a", "event-a"],
            "election_date": ["2025-04-28", "2025-04-28"],
            "election_type": ["general", "general"],
            "election_authority": ["elections_canada", "elections_canada"],
            "represented_body": ["canada_house_of_commons", "canada_house_of_commons"],
            "office_type": ["mp", "mp"],
            "boundary_regime": ["federal_2023_order", "federal_2023_order"],
            "official_district_id": ["35099", "35099"],
            "district_name": ["Example", "Example"],
            "candidate_name_raw": ["Alex", "Bailey"],
            "source_candidacy_id": ["candidate-1", "candidate-2"],
            "party_name_raw": ["Example Party", "Independent"],
            "votes": [60, 40],
            "elected": [True, False],
            "outcome_method": ["vote", "vote"],
            "coverage_status": ["complete", "complete"],
            "source_detail": ["official", "official"],
        }
    )
    candidacies = derive_result_metrics(attach_parties(normalize_adapter_frame(rows)))
    candidacies["person_id"] = pd.Series(pd.NA, index=candidacies.index, dtype="string")
    events = build_events(candidacies)
    contests = build_contests(candidacies)
    parties = build_parties(candidacies)
    districts = candidacies[
        [
            "district_id",
            "represented_body",
            "boundary_regime",
            "official_district_id",
            "district_name",
        ]
    ].drop_duplicates()
    districts["geometry_status"] = "not_acquired"
    people = pd.DataFrame(columns=["person_id"])
    return candidacies, events, contests, parties, districts, people


def test_valid_release_has_no_issues():
    assert validate_release(*_release()) == []


def test_flags_broken_contest_foreign_key():
    release = list(_release())
    release[1] = release[1].iloc[0:0]

    issues = validate_release(*release)

    assert any("event foreign key" in issue for issue in issues)


@pytest.mark.parametrize(
    ("column", "replacement"),
    [
        ("election_date", date(2025, 4, 29)),
        ("election_year", 2024),
        ("election_type", "by_election"),
        ("election_authority", "elections_ontario"),
    ],
)
def test_flags_candidacy_event_metadata_that_disagrees_with_event_dimension(column, replacement):
    release = list(_release())
    candidacies = release[0].copy()
    candidacies.loc[candidacies.index[0], column] = replacement
    release[0] = candidacies

    issues = validate_release(*release)

    assert any(f"Candidacy.{column} must match Election event" in issue for issue in issues)


def test_flags_election_dates_after_release_cutoff():
    release = list(_release())
    events = release[1].copy()
    events["election_date"] = "2026-10-27"
    events["election_year"] = 2026
    release[1] = events

    issues = validate_release(*release)

    assert any("after the pending" in issue for issue in issues)


def test_historical_career_date_has_no_lower_bound():
    release = list(_release())
    events = release[1].copy()
    candidacies = release[0].copy()
    events["election_date"] = "1991-11-12"
    events["election_year"] = 1991
    candidacies["election_date"] = "1991-11-12"
    candidacies["election_year"] = 1991
    release[0] = candidacies
    release[1] = events

    issues = validate_release(*release)

    assert not any("election_date" in issue for issue in issues)


def test_post_result_cutoff_candidacy_requires_pending_status():
    release = list(_release())
    candidacies = release[0].copy()
    candidacies["election_date"] = date(2026, 10, 26)
    candidacies["election_year"] = 2026
    release[0] = candidacies
    release[1] = build_events(candidacies)

    issues = validate_release(*release)

    assert "post-cutoff Candidacies must have result_status=pending" in issues


def test_pending_candidate_roster_allows_future_event_and_null_results():
    release = list(_release())
    candidacies = release[0].copy()
    candidacies["election_date"] = date(2026, 10, 26)
    candidacies["election_year"] = 2026
    candidacies["result_status"] = "pending"
    candidacies["outcome_method"] = "pending"
    candidacies[["votes", "total_contest_votes", "vote_share", "vote_rank"]] = pd.NA
    candidacies["elected"] = pd.NA
    candidacies["acclaimed"] = False
    release[0] = candidacies
    release[1] = build_events(candidacies)
    release[2] = build_contests(candidacies)

    assert validate_release(*release) == []


@pytest.mark.parametrize(
    ("table_index", "column", "replacement", "expected"),
    [
        (0, "represented_body", "ontario_legislative_assembly", "Contest"),
        (0, "office_type", "mpp", "Contest"),
        (0, "event_id", "wrong-event", "Contest"),
        (2, "district_name", "Wrong district", "Electoral district"),
        (2, "boundary_regime", "wrong-regime", "Electoral district"),
        (0, "official_district_id", "99999", "Electoral district"),
    ],
)
def test_flags_denormalized_contest_and_district_metadata_disagreement(
    table_index, column, replacement, expected
):
    release = list(_release())
    changed = release[table_index].copy()
    changed.loc[changed.index[0], column] = replacement
    release[table_index] = changed

    issues = validate_release(*release)

    assert any(expected in issue and f".{column}" in issue for issue in issues)


def test_flags_party_link_on_independent_candidacy():
    release = list(_release())
    candidacies = release[0].copy()
    candidacies.loc[candidacies.affiliation_status == "independent", "party_id"] = "pty_bad"
    release[0] = candidacies

    issues = validate_release(*release)

    assert any("non-party affiliation" in issue for issue in issues)


@pytest.mark.parametrize("invalid_source_id", [pd.NA, "   "])
def test_flags_missing_persistent_source_candidacy_identity(invalid_source_id):
    release = list(_release())
    candidacies = release[0].copy()
    candidacies.loc[candidacies.index[0], "source_candidacy_id"] = invalid_source_id
    release[0] = candidacies

    issues = validate_release(*release)

    assert any("source_candidacy_id must be non-null and non-blank" in issue for issue in issues)


def test_flags_denormalized_party_label_that_differs_from_dimension():
    release = list(_release())
    candidacies = release[0].copy()
    canonical = release[3].set_index("party_id")["canonical_name"]
    candidacies["party_name"] = candidacies["party_id"].map(canonical)
    candidacies.loc[candidacies["party_id"].notna(), "party_name"] = "Wrong label"
    release[0] = candidacies

    issues = validate_release(*release)

    assert any("must match the Party canonical_name" in issue for issue in issues)


def test_flags_complete_resolved_contest_without_one_elected_candidate():
    release = list(_release())
    candidacies = release[0].copy()
    candidacies["elected"] = pd.array([False, False], dtype="boolean")
    release[0] = candidacies

    issues = validate_release(*release)

    assert any("must have exactly one elected" in issue for issue in issues)


def test_flags_vote_share_or_total_that_does_not_reconcile():
    release = list(_release())
    candidacies = release[0].copy()
    candidacies.loc[candidacies.candidate_name_raw == "Bailey", "vote_share"] = 0.1
    release[0] = candidacies

    issues = validate_release(*release)

    assert any("vote shares" in issue for issue in issues)


def test_flags_acclamation_with_vote_counts():
    release = list(_release())
    candidacies = release[0].iloc[[0]].copy()
    candidacies["outcome_method"] = "acclamation"
    candidacies["acclaimed"] = True
    candidacies["votes"] = 0
    candidacies["elected"] = True
    release[0] = candidacies

    issues = validate_release(*release)

    assert any("acclamation" in issue for issue in issues)


def test_flags_source_missing_contest_that_fabricates_candidacies():
    release = list(_release())
    candidacies = release[0].copy()
    candidacies["coverage_status"] = "source_missing"
    candidacies[["total_contest_votes", "vote_share", "vote_rank"]] = pd.NA
    release[0] = candidacies

    issues = validate_release(*release)

    assert any("cannot publish Candidacy rows" in issue for issue in issues)


def test_zero_eligible_electors_and_ballots_have_null_turnout_without_being_missing():
    release = list(_release())
    for table_index in (0, 2):
        result_table = release[table_index].copy()
        result_table["eligible_electors"] = 0
        result_table["ballots_cast"] = 0
        result_table["turnout"] = pd.NA
        result_table["turnout_scope"] = "federal_electoral_district"
        release[table_index] = result_table

    assert validate_release(*release) == []


def test_flags_true_incumbency_without_supporting_tenure():
    release = list(_release())
    candidacies = release[0].copy()
    candidacies["person_id"] = pd.array(["per_alex", pd.NA], dtype="string")
    candidacies["incumbent"] = pd.array([True, pd.NA], dtype="boolean")
    candidacies["incumbent_office_tenure_id"] = pd.array([pd.NA, pd.NA], dtype="string")
    release[0] = candidacies
    release[5] = pd.DataFrame({"person_id": ["per_alex"]})
    tenures = pd.DataFrame(
        columns=["office_tenure_id", "person_id", "represented_body", "office_type"]
    )

    issues = validate_release(*release, office_tenures=tenures)

    assert any("supporting Office tenure" in issue for issue in issues)


def test_flags_person_or_scope_mismatch_in_incumbency_tenure():
    release = list(_release())
    candidacies = release[0].copy()
    candidacies["person_id"] = pd.array(["per_alex", pd.NA], dtype="string")
    candidacies["incumbent"] = pd.array([True, pd.NA], dtype="boolean")
    candidacies["incumbent_office_tenure_id"] = pd.array(["ten_wrong", pd.NA], dtype="string")
    release[0] = candidacies
    release[5] = pd.DataFrame({"person_id": ["per_alex", "per_other"]})
    tenures = pd.DataFrame(
        {
            "office_tenure_id": ["ten_wrong"],
            "person_id": ["per_other"],
            "represented_body": ["ontario_legislative_assembly"],
            "office_type": ["mpp"],
        }
    )

    issues = validate_release(*release, office_tenures=tenures)

    assert any("must match the Candidacy Person" in issue for issue in issues)


def test_flags_published_person_without_active_confirmed_link():
    release = list(_release())
    candidacies = release[0].copy()
    candidacies["person_id"] = pd.array(["per_alex", pd.NA], dtype="string")
    release[0] = candidacies
    release[5] = pd.DataFrame({"person_id": ["per_alex"]})
    links = pd.DataFrame(
        {
            "candidacy_id": [candidacies.iloc[0]["candidacy_id"]],
            "person_id": ["per_alex"],
            "link_status": ["proposed"],
            "valid_to_release": [pd.NA],
        }
    )

    issues = validate_release(*release, candidacy_person_links=links)

    assert any("active confirmed identity link" in issue for issue in issues)


def test_geometry_containment_ignores_only_numerically_negligible_slivers():
    release = list(_release())
    districts = release[4].copy()
    districts["geometry"] = None
    council = pd.DataFrame(
        {
            "district_id": ["dst_city", "dst_ward"],
            "represented_body": ["toronto_city_council"] * 2,
            "boundary_regime": ["toronto_council_25_wards"] * 2,
            "official_district_id": ["city", "ward-1"],
            "district_name": ["City of Toronto", "Ward 1"],
            "geometry_status": ["available", "available"],
            "geometry": [box(0, 0, 1, 1), box(0, 0, 1 + 1e-13, 1)],
        }
    )
    release[4] = pd.concat([districts, council], ignore_index=True)

    issues = validate_release(*release)

    assert not any("council geometry is not contained" in issue for issue in issues)


def test_geometry_containment_still_rejects_a_materially_outside_ward():
    release = list(_release())
    districts = release[4].copy()
    districts["geometry"] = None
    council = pd.DataFrame(
        {
            "district_id": ["dst_city", "dst_ward"],
            "represented_body": ["toronto_city_council"] * 2,
            "boundary_regime": ["toronto_council_25_wards"] * 2,
            "official_district_id": ["city", "ward-1"],
            "district_name": ["City of Toronto", "Ward 1"],
            "geometry_status": ["available", "available"],
            "geometry": [box(0, 0, 1, 1), box(0, 0, 1.01, 1)],
        }
    )
    release[4] = pd.concat([districts, council], ignore_index=True)

    issues = validate_release(*release)

    assert any("council geometry is not contained" in issue for issue in issues)
