import hashlib
import json

import pandas as pd

from toronto_election_results.release_bundle import build_results_release_bundle


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
        "coverage_status": "complete",
        "source_resource": "2026 Municipal Election — Certified Candidates",
        "elected": pd.NA,
        "acclaimed": False,
        "vote_share": pd.NA,
        "vote_rank": pd.NA,
        "n_candidates": 1,
    }
    row.update(overrides)
    return row


def test_bundle_records_commit_checksums_and_factual_feed(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
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
        "terra_report_path,review_date,source_release,review_status,limitations,confirmed_count,"
        "held_count,split_count,rejected_count,primary_rationale\n"
        "toronto-mayor-2026,can_chow_2026,Olivia Chow,per_chow,,,2026-08-26,"
        "results-2026-08-26.1,reviewed,,1,0,0,0,Verified.\n"
    )
    (reference / "mayoral_career_occurrence_mapping.csv").write_text(
        "cohort_id,subject_candidacy_id,decision_id,canonical_candidacy_id\n"
        "toronto-mayor-2026,can_chow_2026,mcd_chow,can_chow_2023\n"
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
    assert manifest["feed_versions"]["mayoral_candidates"] == 3
    assert manifest["feeds"] == {
        "mayoral_candidates": "mayoral_candidates.json",
        "person_aliases": "person_aliases.json",
    }
    assets = {asset["filename"]: asset for asset in manifest["assets"]}
    assert {
        "build_manifest.json",
        "election_results.csv",
        "people.csv",
        "mayoral_candidates.json",
        "person_aliases.json",
        "mayoral_career_coverage.csv",
        "mayoral_career_occurrence_mapping.csv",
    } <= set(assets)
    for filename, record in assets.items():
        assert record["sha256"] == hashlib.sha256((output / filename).read_bytes()).hexdigest()
