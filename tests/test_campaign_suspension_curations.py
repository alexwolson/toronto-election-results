import pandas as pd
import pytest

from toronto_election_results.campaign_suspension_curations import (
    apply_campaign_suspension_curations,
)

HEADER = "candidacy_id,candidate_name,campaign_suspended_on,evidence_url,verified_on,rationale\n"


def _curation(**overrides):
    row = {
        "candidacy_id": "can_alexander",
        "candidate_name": "Chris Alexander",
        "campaign_suspended_on": "2026-10-06",
        "evidence_url": "https://news.example/alexander-ends-campaign",
        "verified_on": "2026-10-07",
        "rationale": "Publicly ended the campaign after the withdrawal deadline.",
    }
    row.update(overrides)
    return HEADER + ",".join(row.values()) + "\n"


def _results(**overrides):
    rows = pd.DataFrame(
        {
            "candidacy_id": ["can_alexander", "can_chow"],
            "candidate_name": ["Chris Alexander", "Olivia Chow"],
            "election_date": ["2026-10-26", "2026-10-26"],
            "election_year": [2026, 2026],
            "represented_body": ["toronto_city_council", "toronto_city_council"],
            "office_type": ["mayor", "mayor"],
        }
    )
    for column, value in overrides.items():
        rows.loc[0, column] = value
    return rows


def test_curated_suspension_dates_exactly_one_current_mayoral_candidacy(tmp_path):
    path = tmp_path / "curations.csv"
    path.write_text(_curation())
    results = _results()

    updated = apply_campaign_suspension_curations(results, path)

    assert updated["campaign_suspended_on"].tolist() == ["2026-10-06", pd.NA]
    assert "campaign_suspended_on" not in results.columns
    assert apply_campaign_suspension_curations(results, path).equals(updated)


def test_curated_suspension_dates_a_current_councillor_candidacy(tmp_path):
    path = tmp_path / "curations.csv"
    path.write_text(_curation())

    updated = apply_campaign_suspension_curations(_results(office_type="councillor"), path)

    assert updated["campaign_suspended_on"].tolist() == ["2026-10-06", pd.NA]


def test_empty_curation_leaves_every_candidacy_undated(tmp_path):
    path = tmp_path / "curations.csv"
    path.write_text(HEADER)

    updated = apply_campaign_suspension_curations(_results(), path)

    assert updated["campaign_suspended_on"].isna().all()


@pytest.mark.parametrize(
    ("curation", "results", "message"),
    [
        ({"candidacy_id": "can_unknown"}, {}, "exactly one Candidacy"),
        ({"candidate_name": "Christopher Alexander"}, {}, "candidate name mismatch"),
        ({}, {"office_type": "trustee"}, "2026 Toronto City Council Candidacy"),
        (
            {},
            {"election_year": 2022, "election_date": "2022-10-24"},
            "2026 Toronto City Council Candidacy",
        ),
        (
            {},
            {"represented_body": "canada_house_of_commons"},
            "2026 Toronto City Council Candidacy",
        ),
        ({"campaign_suspended_on": "2026-10-6"}, {}, "invalid .* campaign_suspended_on"),
        ({"campaign_suspended_on": "2026-02-30"}, {}, "invalid .* campaign_suspended_on"),
        (
            {"campaign_suspended_on": "2026-10-27", "verified_on": "2026-10-28"},
            {},
            "after election day",
        ),
        ({"campaign_suspended_on": "2026-10-08"}, {}, "after its verification"),
        ({"verified_on": "Oct 7 2026"}, {}, "invalid .* verified_on"),
        ({"evidence_url": "javascript:alert(1)"}, {}, "invalid .* evidence_url"),
        ({"rationale": " "}, {}, "cannot be blank"),
    ],
    ids=[
        "unknown",
        "wrong_name",
        "trustee",
        "not_2026",
        "not_toronto",
        "unpadded_date",
        "impossible_date",
        "after_election_day",
        "after_verification",
        "bad_verified_on",
        "invalid_evidence_url",
        "blank_rationale",
    ],
)
def test_rejects_curations_that_do_not_date_a_current_council_candidacy(
    tmp_path, curation, results, message
):
    path = tmp_path / "curations.csv"
    path.write_text(_curation(**curation))

    with pytest.raises(ValueError, match=message):
        apply_campaign_suspension_curations(_results(**results), path)


def test_rejects_a_repeated_curation_or_an_ambiguous_target(tmp_path):
    path = tmp_path / "curations.csv"
    path.write_text(_curation() + _curation().removeprefix(HEADER))
    with pytest.raises(ValueError, match="duplicate campaign suspension curation"):
        apply_campaign_suspension_curations(_results(), path)

    path.write_text(_curation())
    repeated = pd.concat([_results(), _results().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="exactly one Candidacy"):
        apply_campaign_suspension_curations(repeated, path)


def test_rejects_a_curation_missing_a_required_column(tmp_path):
    path = tmp_path / "curations.csv"
    path.write_text(
        "candidacy_id,candidate_name,campaign_suspended_on\ncan_alexander,x,2026-10-06\n"
    )

    with pytest.raises(ValueError, match="missing required columns"):
        apply_campaign_suspension_curations(_results(), path)
