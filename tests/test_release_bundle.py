import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

from toronto_election_results.release_bundle import build_results_release_bundle

ROOT = Path(__file__).resolve().parents[1]


def _row(**overrides):
    row = {
        "candidacy_id": "can_chow_2026",
        "person_id": "per_chow",
        "event_id": "evt_2026",
        "contest_id": "con_2026",
        "election_date": "2026-10-26",
        "election_year": 2026,
        "represented_body": "toronto_city_council",
        "office_type": "mayor",
        "candidate_name": "Olivia Chow",
        "candidate_name_raw": "Chow, Olivia",
        "party_name": pd.NA,
        "district_name": "City of Toronto",
        "result_status": "pending",
        "outcome_method": "pending",
        "coverage_status": "complete",
        "source_resource": "2026 Municipal Election — Certified Candidates",
        "elected": pd.NA,
        "acclaimed": False,
        "incumbent": pd.NA,
        "votes": pd.NA,
        "vote_share": pd.NA,
        "vote_rank": pd.NA,
        "n_candidates": 1,
    }
    row.update(overrides)
    return row


def _trustee_fixture():
    board_counts = {
        "toronto_district_school_board": {1: 11, **{ward: 6 for ward in range(2, 13)}},
        "toronto_catholic_district_school_board": {
            1: 9,
            **{ward: 2 for ward in range(2, 13)},
        },
        "conseil_scolaire_viamonde": {2: 2, 3: 1, 4: 1},
        "conseil_scolaire_catholique_monavenir": {3: 3, 4: 3},
    }
    crosswalk = pd.read_csv(ROOT / "data/reference/trustee_ward_crosswalk_2026.csv")
    rows = []
    cohort = []
    reviews = []
    prior_rows = []
    continuity = []
    evidence_urls = (
        "https://www.toronto.ca/wp-content/uploads/2022/04/"
        "8ef1-2022-School-Board-Ward-Reference-Chart.pdf|"
        "https://www.toronto.ca/wp-content/uploads/2026/04/"
        "9600-2026-School-board-ward-reference-chart.pdf"
    )
    for body, ward_sizes in board_counts.items():
        for ward, field_size in ward_sizes.items():
            contest_id = f"con_{body}_{ward}"
            district_name = crosswalk.loc[
                crosswalk["represented_body"].eq(body) & crosswalk["ward_id"].eq(ward),
                "district_name",
            ].iloc[0]
            for source_order in range(1, field_size + 1):
                candidacy_id = f"can_{body}_{ward}_{source_order}"
                name = f"Candidate {body} {ward} {source_order}"
                rows.append(
                    _row(
                        candidacy_id=candidacy_id,
                        person_id=pd.NA,
                        contest_id=contest_id,
                        represented_body=body,
                        office_type="trustee",
                        official_district_id=str(ward),
                        district_name=district_name,
                        candidate_name=name,
                        candidate_name_raw=name,
                        n_candidates=field_size,
                    )
                )
                cohort.append(
                    {
                        "cohort_id": "toronto-trustee-2026",
                        "subject_candidacy_id": candidacy_id,
                        "source_order": source_order,
                        "source_release": "results-2026-08-27.1",
                    }
                )
                reviews.append(
                    {
                        "cohort_id": "toronto-trustee-2026",
                        "subject_candidacy_id": candidacy_id,
                        "review_date": "2026-08-27",
                        "review_status": "reviewed",
                    }
                )
            board_id = crosswalk.loc[
                crosswalk["represented_body"].eq(body) & crosswalk["ward_id"].eq(ward),
                "board_id",
            ].iloc[0]
            prior_contest_id = "" if board_id == "tdsb" else f"con_prior_{body}_{ward}"
            continuity.append(
                {
                    "current_contest_id": contest_id,
                    "board_id": board_id,
                    "ward_id": ward,
                    "continuity_status": "redrawn" if board_id == "tdsb" else "continuous",
                    "prior_contest_id": prior_contest_id,
                    "evidence_urls": evidence_urls,
                    "rationale": "Synthetic fixture continuity decision.",
                }
            )
            if prior_contest_id:
                for rank, (name, votes) in enumerate(
                    (("Prior Winner", 100), ("Prior Runner-up", 50)), start=1
                ):
                    prior_rows.append(
                        _row(
                            candidacy_id=f"can_prior_{body}_{ward}_{rank}",
                            person_id=pd.NA,
                            event_id="evt_2022",
                            contest_id=prior_contest_id,
                            election_date="2022-10-24",
                            election_year=2022,
                            represented_body=body,
                            office_type="trustee",
                            official_district_id=str(ward),
                            district_name=district_name,
                            candidate_name=name,
                            candidate_name_raw=name,
                            result_status="final",
                            outcome_method="vote",
                            coverage_status="partial",
                            source_resource="Official results",
                            elected=rank == 1,
                            acclaimed=False,
                            votes=votes,
                            vote_share=votes / 150,
                            vote_rank=rank,
                            n_candidates=2,
                        )
                    )
    return rows, prior_rows, cohort, reviews, continuity


def test_bundle_records_commit_checksums_and_factual_feed(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    trustee_rows, trustee_prior_rows, trustee_cohort, trustee_reviews, continuity = (
        _trustee_fixture()
    )
    pd.DataFrame(
        [
            _row(),
            _row(
                candidacy_id="can_chow_2023",
                event_id="evt_2023",
                contest_id="con_2023",
                election_date="2023-06-26",
                election_year=2023,
                result_status="final",
                source_resource="Official results",
                elected=True,
                vote_share=0.37,
                vote_rank=1,
                n_candidates=102,
            ),
            *trustee_rows,
            *trustee_prior_rows,
        ]
    ).to_csv(source / "election_results.csv", index=False)
    (source / "people.csv").write_text(
        "person_id,preferred_name,identity_status\nper_chow,Olivia Chow,active\n"
    )
    (source / "build_manifest.json").write_text('{"schema_version":"2.1.0"}\n')
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / "mayoral_career_reviews.csv").write_text(
        "cohort_id,subject_candidacy_id,certified_name,resulting_person_id,luna_report_path,"
        "terra_report_path,review_date,source_release,review_status,limitations,"
        "public_coverage_note,confirmed_count,held_count,split_count,rejected_count,"
        "primary_rationale\n"
        "toronto-mayor-2026,can_chow_2026,Olivia Chow,per_chow,,,2026-08-26,"
        "results-2026-08-26.1,reviewed,,,1,0,0,0,Verified.\n"
    )
    (reference / "mayoral_career_occurrence_mapping.csv").write_text(
        "cohort_id,subject_candidacy_id,decision_id,canonical_candidacy_id\n"
        "toronto-mayor-2026,can_chow_2026,mcd_chow,can_chow_2023\n"
    )
    pd.DataFrame(trustee_cohort).to_csv(reference / "trustee_career_cohort_2026.csv", index=False)
    pd.DataFrame(trustee_reviews).to_csv(reference / "trustee_career_reviews.csv", index=False)
    pd.DataFrame(
        columns=[
            "cohort_id",
            "subject_candidacy_id",
            "prior_candidacy_id",
            "decision",
        ]
    ).to_csv(reference / "trustee_career_decisions.csv", index=False)
    pd.DataFrame(continuity).to_csv(reference / "trustee_contest_continuity_2026.csv", index=False)
    shutil.copy2(
        ROOT / "data/reference/trustee_ward_crosswalk_2026.csv",
        reference / "trustee_ward_crosswalk_2026.csv",
    )

    output = build_results_release_bundle(
        source,
        tmp_path / "dist",
        source_commit="abc123",
        dirty=False,
        generated_at="2026-08-26T12:00:00Z",
        reference_dir=reference,
    )

    manifest = json.loads((output / "release_manifest.json").read_text())
    assert manifest["source_commit"] == "abc123"
    assert manifest["source_dirty"] is False
    assert manifest["feed_versions"]["mayoral_candidates"] == 4
    assert manifest["feed_versions"]["trustee_races"] == 2
    assert manifest["feeds"] == {
        "mayoral_candidates": "mayoral_candidates.json",
        "trustee_races": "trustee_races.json",
        "person_aliases": "person_aliases.json",
    }
    public_coverage = pd.read_csv(output / "mayoral_career_coverage.csv")
    assert "public_coverage_note" in public_coverage.columns
    assert "limitations" not in public_coverage.columns
    assets = {asset["filename"]: asset for asset in manifest["assets"]}
    assert {
        "build_manifest.json",
        "election_results.csv",
        "people.csv",
        "mayoral_candidates.json",
        "trustee_races.json",
        "person_aliases.json",
        "mayoral_career_coverage.csv",
        "mayoral_career_occurrence_mapping.csv",
    } <= set(assets)
    for filename, record in assets.items():
        assert record["sha256"] == hashlib.sha256((output / filename).read_bytes()).hexdigest()
