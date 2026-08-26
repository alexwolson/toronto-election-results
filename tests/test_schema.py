"""Shared v2 contract for every election-authority adapter."""

import pandas as pd
import pytest

from toronto_election_results.schema import (
    attach_parties,
    build_contests,
    build_districts,
    build_events,
    build_parties,
    derive_result_metrics,
    normalize_adapter_frame,
    stable_id,
)


def _rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": ["ec-2025-general", "ec-2025-general"],
            "election_date": ["2025-04-28", "2025-04-28"],
            "election_type": ["general", "general"],
            "election_authority": ["elections_canada", "elections_canada"],
            "represented_body": ["canada_house_of_commons", "canada_house_of_commons"],
            "office_type": ["mp", "mp"],
            "boundary_regime": ["federal_2023_order", "federal_2023_order"],
            "official_district_id": ["35099", "35099"],
            "district_name": ["Test Centre", "Test Centre"],
            "candidate_name_raw": ["Alex Example", "Bailey Sample"],
            "party_name_raw": ["Example Party", "Independent"],
            "votes": [100, 40],
            "elected": [True, False],
            "outcome_method": ["vote", "vote"],
            "coverage_status": ["complete", "complete"],
            "source_detail": ["official.csv", "official.csv"],
        }
    )


def test_stable_id_is_deterministic_and_namespaced():
    assert stable_id("con", "a", "b") == stable_id("con", "a", "b")
    assert stable_id("con", "a", "b").startswith("con_")
    assert stable_id("evt", "a", "b") != stable_id("con", "a", "b")


def test_adapter_frame_gets_collision_safe_ids_and_types():
    out = normalize_adapter_frame(_rows())

    assert out["contest_id"].nunique() == 1
    assert out["candidacy_id"].nunique() == 2
    assert out["district_id"].nunique() == 1
    assert out["election_year"].tolist() == [2025, 2025]
    assert str(out["election_date"].dtype) == "object"  # datetime.date, Parquet-friendly


def test_adapter_requires_concrete_source_detail():
    rows = _rows()
    rows["source_detail"] = pd.NA

    with pytest.raises(ValueError, match="source_detail cannot be null"):
        normalize_adapter_frame(rows)


def test_provenance_fallbacks_use_canonical_authority_and_resource_family():
    rows = _rows()
    rows["source_authority"] = "elections_canada"

    out = normalize_adapter_frame(rows)

    assert out["source_authority"].unique().tolist() == ["Elections Canada"]
    assert out["source_resource"].unique().tolist() == ["Official Voting Results — Raw Data"]
    assert out["source_detail"].unique().tolist() == ["official.csv"]


def test_official_winner_is_not_rederived_from_tied_votes():
    rows = _rows()
    rows["votes"] = [100, 100]
    rows["elected"] = [True, False]  # authority resolved the tie

    out = derive_result_metrics(normalize_adapter_frame(rows))

    assert out["elected"].tolist() == [True, False]
    assert out["vote_rank"].tolist() == [1, 1]
    assert out["vote_share"].tolist() == [0.5, 0.5]


def test_tied_votes_without_official_outcome_remain_unknown():
    rows = _rows()
    rows["votes"] = [100, 100]
    rows["elected"] = [pd.NA, pd.NA]

    out = derive_result_metrics(normalize_adapter_frame(rows))

    assert out["elected"].isna().all()


def test_pending_roster_does_not_derive_result_metrics():
    rows = _rows()
    rows["election_date"] = "2026-10-26"
    rows["result_status"] = "pending"
    rows["outcome_method"] = "pending"
    rows["votes"] = pd.NA
    rows["elected"] = pd.NA

    out = derive_result_metrics(normalize_adapter_frame(rows))

    assert out["result_status"].eq("pending").all()
    assert not out["acclaimed"].any()
    assert out[["votes", "total_contest_votes", "vote_share", "vote_rank"]].isna().all().all()


def test_acclamation_has_null_vote_fields_and_official_winner():
    rows = _rows().iloc[[0]].copy()
    rows["votes"] = 0
    rows["elected"] = True
    rows["outcome_method"] = "acclamation"

    out = derive_result_metrics(normalize_adapter_frame(rows)).iloc[0]

    assert out["elected"]
    assert out["acclaimed"]
    assert pd.isna(out["votes"])
    assert pd.isna(out["total_contest_votes"])
    assert pd.isna(out["vote_share"])
    assert pd.isna(out["vote_rank"])


def test_party_is_a_candidacy_relationship_not_a_person_attribute():
    normalized = normalize_adapter_frame(_rows())
    attached = attach_parties(normalized)
    parties = build_parties(attached)

    assert attached.loc[0, "affiliation_status"] == "party"
    assert pd.notna(attached.loc[0, "party_id"])
    assert attached.loc[1, "affiliation_status"] == "independent"
    assert pd.isna(attached.loc[1, "party_id"])
    assert parties["canonical_name"].tolist() == ["Example Party"]


def test_federal_official_party_aliases_share_legal_party_ids_and_keep_raw_labels():
    alias_groups = {
        "Animal Protection Party": [
            "AACEV Party of Canada",
            "AAEV Party of Canada",
            "Animal Alliance Environment Voters Party of Canada",
            "Animal Alliance/Environment Voters",
            "Animal Protection Party",
        ],
        "Canadian Action Party": ["Canadian Action", "CAP", "Canadian Action Party"],
        "Christian Heritage Party of Canada": [
            "Christian Heritage Party",
            "CHP Canada",
            "Christian Heritage Party of Canada",
        ],
        "Conservative Party of Canada": ["Conservative", "Conservative Party of Canada"],
        "Green Party of Canada": ["Green Party", "Green Party of Canada"],
        "Liberal Party of Canada": ["Liberal", "Liberal Party of Canada"],
        "Libertarian Party of Canada": ["Libertarian", "Libertarian Party of Canada"],
        "Marijuana Party": ["Radical Marijuana", "Marijuana Party"],
        "Marxist-Leninist": ["ML", "Marxist-Leninist"],
        "New Democratic Party": ["N.D.P.", "NDP-New Democratic Party", "New Democratic Party"],
        "Progressive Canadian Party": ["PC Party", "Progressive Canadian Party"],
        "People's Party - PPC": ["People's Party", "People's Party - PPC"],
        "United Party of Canada": ["UPC", "United Party of Canada"],
    }
    raw_labels = [label for labels in alias_groups.values() for label in labels]
    frame = pd.DataFrame(
        {
            "election_authority": ["elections_canada"] * len(raw_labels),
            "office_type": ["mp"] * len(raw_labels),
            "party_name_raw": raw_labels,
            "affiliation_status": ["party"] * len(raw_labels),
        }
    )

    attached = attach_parties(frame)

    assert attached["party_name_raw"].tolist() == raw_labels
    offset = 0
    for canonical_name, labels in alias_groups.items():
        group = attached.iloc[offset : offset + len(labels)]
        assert group["canonical_party_name"].unique().tolist() == [canonical_name]
        assert group["party_id"].nunique() == 1
        offset += len(labels)


def test_ontario_party_code_backed_aliases_share_legal_party_ids():
    alias_groups = {
        "Communist Party of Canada (Ontario)": [
            "COMMUNIST",
            "COMMUNIST PARTY OF CANADA (ONTARIO)",
            "Communist Party of Canada (Ontario)",
        ],
        "Freedom Party of Ontario": ["FREEDOM", "FREEDOM PARTY OF ONTARIO"],
        "Green Party of Ontario": [
            "GREEN",
            "GREEN PARTY OF ONTARIO",
            "THE GREEN PARTY OF ONTARIO",
        ],
        "Ontario Liberal Party": ["LIBERAL", "ONTARIO LIBERAL PARTY"],
        "New Democratic Party of Ontario": [
            "NEW DEMOCRATIC",
            "NEW DEMOCRATIC PARTY OF ONTARIO",
        ],
        "None of the Above Direct Democracy Party": [
            "NONE OF THE ABOVE PARTY OF ONTARIO",
            "None of the Above Direct Democracy Party",
        ],
        "Progressive Conservative Party of Ontario": [
            "PROGRESSIVE CONSERVATIVE",
            "PROGRESSIVE CONSERVATIVE PARTY OF ONTARIO",
        ],
        "The People's Political Party": [
            "THE PEOPLES POLITICAL PARTY",
            "The People's Political Party",
        ],
        "Go Vegan": ["VEGAN ENVIRONMENTAL PARTY", "Go Vegan"],
    }
    raw_labels = [label for labels in alias_groups.values() for label in labels]
    frame = pd.DataFrame(
        {
            "election_authority": ["elections_ontario"] * len(raw_labels),
            "office_type": ["mpp"] * len(raw_labels),
            "party_name_raw": raw_labels,
            "affiliation_status": ["party"] * len(raw_labels),
        }
    )

    attached = attach_parties(frame)

    assert attached["party_name_raw"].tolist() == raw_labels
    offset = 0
    for canonical_name, labels in alias_groups.items():
        group = attached.iloc[offset : offset + len(labels)]
        assert group["canonical_party_name"].unique().tolist() == [canonical_name]
        assert group["party_id"].nunique() == 1
        offset += len(labels)


def test_similarly_named_parties_without_continuity_evidence_remain_separate():
    frame = pd.DataFrame(
        {
            "election_authority": [
                "elections_canada",
                "elections_canada",
                "elections_ontario",
                "elections_ontario",
            ],
            "office_type": ["mp", "mp", "mpp", "mpp"],
            "party_name_raw": [
                "Canadian Future Party",
                "CFF - Canada's Fourth Front",
                "Canadians' Choice Party",
                "The New People's Choice Party of Ontario",
            ],
            "affiliation_status": ["party"] * 4,
        }
    )

    attached = attach_parties(frame)

    assert attached["party_name_raw"].tolist() == frame["party_name_raw"].tolist()
    assert attached["party_id"].nunique() == 4


def test_party_dimension_keeps_canonical_name_when_latest_raw_label_is_shorter():
    frame = pd.DataFrame(
        {
            "election_authority": ["elections_canada", "elections_canada"],
            "office_type": ["mp", "mp"],
            "election_date": ["2014-06-30", "2026-04-13"],
            "party_name_raw": ["Liberal Party of Canada", "Liberal"],
            "affiliation_status": ["party", "party"],
        }
    )

    party = build_parties(attach_parties(frame)).iloc[0]

    assert party["canonical_name"] == "Liberal Party of Canada"
    assert party["party_name_raw"] == "Liberal"


def test_event_and_contest_dimensions_are_one_row_per_identity():
    out = derive_result_metrics(attach_parties(normalize_adapter_frame(_rows())))

    assert len(build_events(out)) == 1
    assert len(build_contests(out)) == 1
    assert build_contests(out).iloc[0]["total_contest_votes"] == 140


def test_district_identity_is_scoped_to_body_and_boundary_regime():
    first = normalize_adapter_frame(_rows())
    second_rows = _rows()
    second_rows["boundary_regime"] = "federal_future_order"
    second = normalize_adapter_frame(second_rows)
    districts = build_districts(pd.concat([first, second], ignore_index=True))

    assert len(districts) == 2
    assert districts["district_id"].nunique() == 2
    assert set(districts["geometry_status"]) == {"not_acquired"}
