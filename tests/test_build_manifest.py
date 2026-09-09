"""Auditable, deterministic build/source manifest."""

import json

from toronto_election_results.build_manifest import build_manifest, sha256_file, write_manifest
from toronto_election_results.pipeline import _source_files


def test_manifest_records_source_and_artifact_checksums(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("official,data\n", encoding="utf-8")
    artifact = tmp_path / "results.csv"
    artifact.write_text("model,data\n", encoding="utf-8")

    manifest = build_manifest(
        sources=[source],
        artifacts=[artifact],
        row_counts={"results.csv": 1},
        generated_at="2026-08-20T12:00:00Z",
    )

    assert manifest["coverage"]["through"] == "2026-08-20"
    assert manifest["coverage"]["pending_candidate_snapshot_through"] == "2026-08-27"
    assert manifest["schema_version"] == "2.2.0"
    assert manifest["sources"][0]["sha256"] == sha256_file(source)
    assert manifest["artifacts"][0]["rows"] == 1
    assert manifest["event_archive_caveats"] == [
        {
            "authority": "toronto_city_clerk",
            "period": "2003-01-01/2011-12-31",
            "scope": "trustee_by_elections",
            "status": "uncertain",
        }
    ]

    output = write_manifest(manifest, tmp_path / "manifest.json")
    assert json.loads(output.read_text(encoding="utf-8")) == manifest


def test_manifest_discloses_cancelled_and_post_cutoff_calls(tmp_path):
    manifest = build_manifest(sources=[], artifacts=[], row_counts={}, generated_at="fixed")

    labels = {item["label"] for item in manifest["excluded_calls"]}
    assert "Don Valley West federal by-election" in labels
    assert "Beaches—East York federal by-election" in labels
    assert "Scarborough Southwest provincial by-election" in labels
    assert "2026 Toronto municipal general election" not in labels
    assert manifest["pending_events"] == [
        {
            "label": "2026 Toronto municipal general election",
            "scheduled_date": "2026-10-26",
            "candidate_snapshot_through": "2026-08-27",
            "status": "pending",
        }
    ]


def test_source_inventory_includes_historical_rosters_used_for_incumbency(tmp_path):
    raw = tmp_path / "raw"
    reference = tmp_path / "reference"
    raw.mkdir()
    reference.mkdir()
    roster_a = reference / "roster_agent_a.txt"
    roster_b = reference / "roster_agent_b.txt"
    ledger = reference / "candidacy_identity_ledger.csv"
    dispositions = reference / "identity_review_dispositions.csv"
    endorser_panel = reference / "endorser_panel_curations.csv"
    endorsement_assertions = reference / "endorsement_assertion_curations.csv"
    endorsement_coverage = reference / "endorsement_coverage_curations.csv"
    person_alias_curations = reference / "person_alias_curations.csv"
    verification_report = tmp_path / "verification-report.md"
    search_certificate = tmp_path / "search-certificate.md"
    trustee_crosswalk = reference / "trustee_ward_crosswalks.csv"
    trustee_cohort = reference / "trustee_career_cohort_2026.csv"
    trustee_reviews = reference / "trustee_career_reviews.csv"
    trustee_decisions = reference / "trustee_career_decisions.csv"
    trustee_sol_reviews = reference / "trustee_career_sol_reviews.csv"
    trustee_continuity = reference / "trustee_contest_continuity_2026.csv"
    luna_report = tmp_path / "candidate-luna.md"
    terra_report = tmp_path / "candidate-terra.md"
    sol_report = tmp_path / "candidate-sol.md"
    sol_batch = tmp_path / "sol-review-batch-a.csv"
    ignored = reference / "notes.md"
    roster_a.write_text("officially reconciled A", encoding="utf-8")
    roster_b.write_text("officially reconciled B", encoding="utf-8")
    ledger.write_text("persistent,identity\n", encoding="utf-8")
    dispositions.write_text("audited,identity\n", encoding="utf-8")
    endorser_panel.write_text("audited,endorser\n", encoding="utf-8")
    endorsement_assertions.write_text("audited,endorsement\n", encoding="utf-8")
    person_alias_curations.write_text("audited,aliases\n", encoding="utf-8")
    verification_report.write_text("verified", encoding="utf-8")
    search_certificate.write_text("searched", encoding="utf-8")
    trustee_crosswalk.write_text("official,crosswalk\n", encoding="utf-8")
    trustee_cohort.write_text("frozen,cohort\n", encoding="utf-8")
    trustee_decisions.write_text("audited,decisions\n", encoding="utf-8")
    trustee_continuity.write_text("audited,continuity\n", encoding="utf-8")
    luna_report.write_text("luna", encoding="utf-8")
    terra_report.write_text("terra", encoding="utf-8")
    sol_report.write_text("sol", encoding="utf-8")
    sol_batch.write_text("sol,batch\n", encoding="utf-8")
    trustee_reviews.write_text(
        f"luna_report_path,terra_report_path\n{luna_report},{terra_report}\n",
        encoding="utf-8",
    )
    trustee_sol_reviews.write_text(
        f"sol_report_path,sol_batch_path\n{sol_report},{sol_batch}\n",
        encoding="utf-8",
    )
    endorsement_coverage.write_text(
        "verification_report_path,search_certificate_path\n"
        f"{verification_report},{search_certificate}\n",
        encoding="utf-8",
    )
    ignored.write_text("not a build input", encoding="utf-8")

    assert _source_files(raw, reference) == sorted(
        [
            ledger,
            endorsement_assertions,
            endorsement_coverage,
            endorser_panel,
            dispositions,
            person_alias_curations,
            roster_a,
            roster_b,
            verification_report,
            search_certificate,
            trustee_crosswalk,
            trustee_cohort,
            trustee_decisions,
            trustee_sol_reviews,
            trustee_continuity,
            trustee_reviews,
            luna_report,
            terra_report,
            sol_report,
            sol_batch,
        ],
        key=lambda path: path.as_posix(),
    )
