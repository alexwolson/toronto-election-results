"""Convert authority-reported incumbent flags into roster and tenure evidence."""

import pandas as pd

from toronto_election_results.identity import derive_incumbency
from toronto_election_results.reported_incumbency import build_reported_incumbency


def _rows():
    return pd.DataFrame(
        {
            "candidacy_id": ["can_inc", "can_non", "can_ambiguous"],
            "event_id": ["evt"] * 3,
            "election_date": [pd.Timestamp("2025-04-28").date()] * 3,
            "election_authority": ["elections_canada"] * 3,
            "represented_body": ["canada_house_of_commons"] * 3,
            "office_type": ["mp"] * 3,
            "person_id": ["per_inc", "per_non", pd.NA],
            "incumbent_reported": pd.array([True, False, False], dtype="boolean"),
            "source_detail": ["official.csv"] * 3,
        }
    )


def test_complete_official_flags_form_a_scope_roster_and_tenure():
    evidence = build_reported_incumbency(_rows())

    assert len(evidence.office_tenures) == 1
    assert evidence.office_tenures["person_id"].tolist() == ["per_inc"]
    assert evidence.rosters["roster_complete"].all()
    assert set(evidence.rosters["reference_date_rule"]) == {
        "authority_reported_pre_event_incumbency"
    }

    out = derive_incumbency(_rows(), evidence.rosters)
    assert out.loc[out.candidacy_id == "can_inc", "incumbent"].item()
    assert not out.loc[out.candidacy_id == "can_non", "incumbent"].item()
    assert pd.isna(out.loc[out.candidacy_id == "can_ambiguous", "incumbent"].item())


def test_missing_reported_flags_make_absence_unknown_but_known_true_survives():
    rows = _rows().iloc[:2].copy()
    rows.loc[rows.candidacy_id == "can_non", "incumbent_reported"] = pd.NA
    evidence = build_reported_incumbency(rows)

    assert not evidence.rosters["roster_complete"].any()
    out = derive_incumbency(rows, evidence.rosters)
    assert out.loc[out.candidacy_id == "can_inc", "incumbent"].item()
    assert pd.isna(out.loc[out.candidacy_id == "can_non", "incumbent"].item())


def test_unlinked_reported_incumbent_prevents_false_classification():
    rows = _rows().iloc[:2].copy()
    rows.loc[rows.candidacy_id == "can_inc", "person_id"] = pd.NA
    evidence = build_reported_incumbency(rows)

    assert not evidence.rosters["roster_complete"].any()
    out = derive_incumbency(rows, evidence.rosters)
    assert pd.isna(out.loc[out.candidacy_id == "can_non", "incumbent"].item())


def test_ontario_general_roster_uses_the_day_before_official_dissolution():
    rows = _rows().iloc[:2].copy()
    rows["event_id"] = "on-2022-general"
    rows["election_date"] = pd.Timestamp("2022-06-02").date()
    rows["election_authority"] = "Elections Ontario"
    rows["represented_body"] = "ontario_legislative_assembly"
    rows["office_type"] = "mpp"

    evidence = build_reported_incumbency(rows)

    assert set(evidence.rosters["reference_date"]) == {"2022-05-02"}
    assert set(evidence.rosters["reference_date_rule"]) == {
        "day_before_official_legislature_dissolution"
    }
    assert set(evidence.office_tenures["ended_on"]) == {"2022-05-02"}
