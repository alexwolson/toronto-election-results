"""Contracts for the complete 2026 Toronto mayoral career review."""

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.mayoral_career import (
    BACKFILL_COLUMNS,
    DECISION_COLUMNS,
    EXPECTED_COHORT_SIZE,
    MAPPING_COLUMNS,
    REVIEW_COLUMNS,
    _assertion_identity_target,
    exclude_superseded_identity_decisions,
    load_contract_table,
    load_mayoral_career_backfills,
    load_mayoral_career_cohort,
    validate_mayoral_career_cohort,
    validate_mayoral_career_contracts,
)
from toronto_election_results.schema import (
    derive_result_metrics,
    normalize_adapter_frame,
    stable_id,
)

ROOT = Path(__file__).resolve().parents[1]
COHORT_PATH = ROOT / "data/reference/mayoral_career_cohort_2026.csv"
RESULTS_PATH = ROOT / "data/out/election_results.csv"


def _real_inputs():
    return load_mayoral_career_cohort(COHORT_PATH), pd.read_csv(RESULTS_PATH, low_memory=False)


def test_frozen_cohort_exactly_matches_certified_mayoral_field():
    rows, results = _real_inputs()

    validate_mayoral_career_cohort(rows, results)

    assert len(rows) == EXPECTED_COHORT_SIZE
    assert len({row.subject_candidacy_id for row in rows}) == EXPECTED_COHORT_SIZE


def test_duplicate_subject_is_rejected():
    rows, results = _real_inputs()
    rows[-1] = replace(rows[-1], subject_candidacy_id=rows[0].subject_candidacy_id)

    with pytest.raises(ValueError, match="duplicate subject_candidacy_id"):
        validate_mayoral_career_cohort(rows, results)


def test_missing_subject_is_rejected():
    rows, results = _real_inputs()

    with pytest.raises(ValueError, match="must contain 53 rows"):
        validate_mayoral_career_cohort(rows[:-1], results)


def test_non_mayoral_contest_is_rejected():
    rows, results = _real_inputs()
    rows = [replace(row, contest_id="con_not_mayor") for row in rows]

    with pytest.raises(ValueError, match="does not match certified contest"):
        validate_mayoral_career_cohort(rows, results)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("certified_name", "Changed Name", "candidate_name changed"),
        ("event_id", "evt_changed", "cohort must use one event_id"),
    ],
)
def test_frozen_source_mutation_is_rejected(field: str, value: str, message: str):
    rows, results = _real_inputs()
    rows[0] = replace(rows[0], **{field: value})

    with pytest.raises(ValueError, match=message):
        validate_mayoral_career_cohort(rows, results)


def _contract_inputs(tmp_path: Path):
    cohort = load_mayoral_career_cohort(COHORT_PATH)
    subject = cohort[0]
    report_dir = tmp_path / "docs/research/mayoral-career/2026"
    report_dir.mkdir(parents=True)
    for agent in ["luna", "terra"]:
        (report_dir / f"{subject.subject_candidacy_id}-{agent}.md").write_text(
            f"# {agent}\n", encoding="utf-8"
        )
    reviews = pd.DataFrame(
        [
            {
                "cohort_id": subject.cohort_id,
                "subject_candidacy_id": subject.subject_candidacy_id,
                "certified_name": subject.certified_name,
                "resulting_person_id": subject.current_person_id or "",
                "luna_report_path": (
                    f"docs/research/mayoral-career/2026/{subject.subject_candidacy_id}-luna.md"
                ),
                "terra_report_path": (
                    f"docs/research/mayoral-career/2026/{subject.subject_candidacy_id}-terra.md"
                ),
                "review_date": "2026-08-26",
                "source_release": subject.source_release,
                "review_status": "reviewed",
                "limitations": "",
                "confirmed_count": "1",
                "held_count": "0",
                "split_count": "0",
                "rejected_count": "0",
                "primary_rationale": "Independent reports and authoritative results agree.",
            }
        ],
        columns=REVIEW_COLUMNS,
        dtype="string",
    )
    decisions = pd.DataFrame(
        [
            {
                "decision_id": "mcd_test",
                "cohort_id": subject.cohort_id,
                "subject_candidacy_id": subject.subject_candidacy_id,
                "proposed_occurrence_key": "test-2022-mayor",
                "observed_ballot_name": subject.certified_name,
                "election_date": "2022-10-24",
                "jurisdiction": "Ontario",
                "office": "mayor",
                "district": "Example",
                "decision": "confirm",
                "ingestion_action": "add_backfill",
                "identity_bridge": "Candidate-controlled biography identifies the contest.",
                "result_source_authority": "Example Clerk",
                "result_source_resource": "Official results",
                "result_source_locator": "https://example.ca/results",
                "rationale": "Exact result and independent identity evidence agree.",
            }
        ],
        columns=DECISION_COLUMNS,
        dtype="string",
    )
    backfill = pd.DataFrame(
        [
            {
                "backfill_id": "mcb_test",
                "decision_id": "mcd_test",
                "subject_candidacy_id": subject.subject_candidacy_id,
                "election_date": "2022-10-24",
                "election_type": "general",
                "election_authority": "Example Clerk",
                "represented_body": "example_council",
                "office_type": "mayor",
                "district_name": "Example",
                "candidate_name_raw": subject.certified_name,
                "party_name_raw": "",
                "votes": "100",
                "total_contest_votes": "1000",
                "vote_share": "0.1",
                "vote_rank": "2",
                "n_candidates": "3",
                "elected": "false",
                "acclaimed": "false",
                "result_status": "official",
                "source_authority": "Example Clerk",
                "source_resource": "Official results",
                "source_locator": "https://example.ca/results",
            }
        ],
        columns=BACKFILL_COLUMNS,
        dtype="string",
    )
    mappings = pd.DataFrame(columns=MAPPING_COLUMNS, dtype="string")
    return cohort, reviews, decisions, backfill, mappings


def _validate_contract_inputs(tmp_path: Path, inputs, **kwargs):
    validate_mayoral_career_contracts(
        *inputs, repository_root=tmp_path, require_complete=False, **kwargs
    )


def test_valid_partial_review_contract_is_accepted(tmp_path: Path):
    inputs = _contract_inputs(tmp_path)

    _validate_contract_inputs(tmp_path, inputs)


@pytest.mark.parametrize(
    ("filename", "columns"),
    [
        ("mayoral_career_reviews.csv", REVIEW_COLUMNS),
        ("mayoral_career_decisions.csv", DECISION_COLUMNS),
        ("mayoral_career_backfill.csv", BACKFILL_COLUMNS),
        ("mayoral_career_occurrence_mapping.csv", MAPPING_COLUMNS),
    ],
)
def test_repository_contract_tables_have_exact_schema(filename: str, columns: list[str]):
    table = load_contract_table(ROOT / "data/reference" / filename, columns)

    assert table.columns.tolist() == columns


def test_reconciled_registry_is_valid_before_backfill_ingestion():
    cohort = load_mayoral_career_cohort(COHORT_PATH)
    reference = ROOT / "data/reference"

    validate_mayoral_career_contracts(
        cohort,
        load_contract_table(reference / "mayoral_career_reviews.csv", REVIEW_COLUMNS),
        load_contract_table(reference / "mayoral_career_decisions.csv", DECISION_COLUMNS),
        load_contract_table(reference / "mayoral_career_backfill.csv", BACKFILL_COLUMNS),
        load_contract_table(reference / "mayoral_career_occurrence_mapping.csv", MAPPING_COLUMNS),
        repository_root=ROOT,
        require_complete=False,
        require_ingested=False,
    )


def test_complete_reconciled_registry_covers_the_entire_cohort():
    cohort = load_mayoral_career_cohort(COHORT_PATH)
    reference = ROOT / "data/reference"

    validate_mayoral_career_contracts(
        cohort,
        load_contract_table(reference / "mayoral_career_reviews.csv", REVIEW_COLUMNS),
        load_contract_table(reference / "mayoral_career_decisions.csv", DECISION_COLUMNS),
        load_contract_table(reference / "mayoral_career_backfill.csv", BACKFILL_COLUMNS),
        load_contract_table(reference / "mayoral_career_occurrence_mapping.csv", MAPPING_COLUMNS),
        repository_root=ROOT,
        require_complete=True,
        require_ingested=False,
    )


def test_all_confirmed_occurrences_have_canonical_mappings():
    cohort = load_mayoral_career_cohort(COHORT_PATH)
    reference = ROOT / "data/reference"

    validate_mayoral_career_contracts(
        cohort,
        load_contract_table(reference / "mayoral_career_reviews.csv", REVIEW_COLUMNS),
        load_contract_table(reference / "mayoral_career_decisions.csv", DECISION_COLUMNS),
        load_contract_table(reference / "mayoral_career_backfill.csv", BACKFILL_COLUMNS),
        load_contract_table(reference / "mayoral_career_occurrence_mapping.csv", MAPPING_COLUMNS),
        repository_root=ROOT,
        require_complete=True,
        require_ingested=True,
    )


def test_only_confirmed_backfills_enter_candidate_record_adapter():
    adapter = load_mayoral_career_backfills(ROOT / "data/reference")

    assert len(adapter) == 17
    assert adapter["coverage_status"].eq("candidate_record").all()
    assert set(adapter["source_candidacy_id"]) == set(
        load_contract_table(ROOT / "data/reference/mayoral_career_backfill.csv", BACKFILL_COLUMNS)[
            "backfill_id"
        ]
    )


def test_planned_assertion_person_is_created_instead_of_pinned():
    assertion_id = stable_id("ast", "toronto-mayor-2026", "can_new_subject")
    planned_person_id = stable_id("per", "curated_identity_assertion", assertion_id)

    assert _assertion_identity_target(planned_person_id, assertion_id) == ((), None)
    assert _assertion_identity_target("per_existing", assertion_id) == (
        ("per_existing",),
        "per_existing",
    )


def test_candidate_record_preserves_authority_reported_metrics():
    adapter = load_mayoral_career_backfills(ROOT / "data/reference")
    results = derive_result_metrics(
        normalize_adapter_frame(adapter, require_persistent_candidacy_id=True)
    )
    alexander = results.loc[results["candidate_name_raw"].eq("Chris Alexander")].sort_values(
        "election_date"
    )

    assert alexander["total_contest_votes"].tolist() == [56268, 56307]
    assert alexander["n_candidates"].tolist() == [5, 5]
    assert alexander["vote_rank"].tolist() == [1, 2]
    assert alexander.iloc[1]["vote_share"] == pytest.approx(19374 / 56307)


def test_complete_career_review_supersedes_older_occurrence_dispositions():
    mappings = load_contract_table(
        ROOT / "data/reference/mayoral_career_occurrence_mapping.csv", MAPPING_COLUMNS
    )
    mapped_id = mappings.iloc[0]["canonical_candidacy_id"]
    decisions = pd.DataFrame(
        [
            {"candidacy_id": mapped_id, "decision": "unresolved"},
            {"candidacy_id": "can_unrelated", "decision": "confirmed"},
        ]
    )

    filtered = exclude_superseded_identity_decisions(decisions, ROOT / "data/reference")

    assert filtered["candidacy_id"].tolist() == ["can_unrelated"]


def test_invalid_review_status_is_rejected(tmp_path: Path):
    inputs = list(_contract_inputs(tmp_path))
    inputs[1].loc[0, "review_status"] = "probably_reviewed"

    with pytest.raises(ValueError, match="invalid review_status"):
        _validate_contract_inputs(tmp_path, inputs)


def test_missing_or_wrong_candidate_report_is_rejected(tmp_path: Path):
    inputs = list(_contract_inputs(tmp_path))
    inputs[1].loc[0, "luna_report_path"] = "docs/research/mayoral-career/2026/other-luna.md"

    with pytest.raises(ValueError, match="luna report path"):
        _validate_contract_inputs(tmp_path, inputs)


def test_duplicate_occurrence_decision_is_rejected(tmp_path: Path):
    inputs = list(_contract_inputs(tmp_path))
    inputs[2] = pd.concat([inputs[2], inputs[2]], ignore_index=True)

    with pytest.raises(ValueError, match="duplicate decision_id"):
        _validate_contract_inputs(tmp_path, inputs)


@pytest.mark.parametrize(
    ("column", "message"),
    [
        ("identity_bridge", "confirmed decision requires identity_bridge"),
        ("result_source_locator", "confirmed decision requires result_source_locator"),
    ],
)
def test_confirmed_decision_requires_identity_and_result_evidence(
    tmp_path: Path, column: str, message: str
):
    inputs = list(_contract_inputs(tmp_path))
    inputs[2].loc[0, column] = ""

    with pytest.raises(ValueError, match=message):
        _validate_contract_inputs(tmp_path, inputs)


def test_nonconfirmed_decision_cannot_enter_backfill(tmp_path: Path):
    inputs = list(_contract_inputs(tmp_path))
    inputs[2].loc[0, "decision"] = "hold"

    with pytest.raises(ValueError, match="cannot be ingested"):
        _validate_contract_inputs(tmp_path, inputs)


def test_complete_review_requires_every_cohort_candidate(tmp_path: Path):
    inputs = _contract_inputs(tmp_path)

    with pytest.raises(ValueError, match="review registry is incomplete"):
        validate_mayoral_career_contracts(*inputs, repository_root=tmp_path, require_complete=True)


def test_limited_review_requires_a_concrete_limitation(tmp_path: Path):
    inputs = list(_contract_inputs(tmp_path))
    inputs[1].loc[0, "review_status"] = "reviewed_with_limitations"
    inputs[1].loc[0, "limitations"] = ""

    with pytest.raises(ValueError, match="requires limitations"):
        _validate_contract_inputs(tmp_path, inputs)


def test_no_verified_prior_candidacy_cannot_count_confirmation(tmp_path: Path):
    inputs = list(_contract_inputs(tmp_path))
    inputs[1].loc[0, "review_status"] = "no_verified_prior_candidacy"

    with pytest.raises(ValueError, match="cannot have confirmed occurrences"):
        _validate_contract_inputs(tmp_path, inputs)


def test_mapping_subject_must_match_confirmed_decision(tmp_path: Path):
    inputs = list(_contract_inputs(tmp_path))
    inputs[4] = pd.DataFrame(
        [
            {
                "cohort_id": "toronto-mayor-2026",
                "subject_candidacy_id": inputs[0][1].subject_candidacy_id,
                "decision_id": "mcd_test",
                "canonical_candidacy_id": "can_existing",
            }
        ],
        columns=MAPPING_COLUMNS,
        dtype="string",
    )

    with pytest.raises(ValueError, match="mapping subject does not match"):
        _validate_contract_inputs(tmp_path, inputs)
