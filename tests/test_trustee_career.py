"""Contracts for the complete certified 2026 Toronto trustee review."""

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.trustee_career import (
    DECISION_COLUMNS,
    EXPECTED_CONTEST_COUNTS,
    REVIEW_COLUMNS,
    SOL_REVIEW_COLUMNS,
    SOL_TO_CANONICAL,
    build_trustee_career_identity_assertions,
    build_trustee_hold_decisions,
    load_trustee_career_cohort,
    validate_trustee_career_cohort,
    validate_trustee_career_contracts,
    validate_trustee_sol_reviews,
)

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data/reference"


def _results() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data/out/election_results.csv", low_memory=False)


def test_frozen_cohort_exactly_matches_certified_trustee_field():
    cohort = load_trustee_career_cohort(REFERENCE / "trustee_career_cohort_2026.csv")

    validate_trustee_career_cohort(cohort, _results())

    assert len(cohort) == 118
    assert len({row.subject_candidacy_id for row in cohort}) == 118
    assert pd.Series([row.represented_body for row in cohort]).value_counts().to_dict() == {
        "toronto_district_school_board": 77,
        "toronto_catholic_district_school_board": 31,
        "conseil_scolaire_viamonde": 4,
        "conseil_scolaire_catholique_monavenir": 6,
    }


def test_cohort_requires_all_29_contests():
    cohort = load_trustee_career_cohort(REFERENCE / "trustee_career_cohort_2026.csv")
    dropped_contest = cohort[0].contest_id

    with pytest.raises(ValueError, match="complete certified trustee field"):
        validate_trustee_career_cohort(
            [row for row in cohort if row.contest_id != dropped_contest], _results()
        )


def test_cohort_rejects_duplicate_subject():
    cohort = load_trustee_career_cohort(REFERENCE / "trustee_career_cohort_2026.csv")
    cohort[-1] = replace(cohort[-1], subject_candidacy_id=cohort[0].subject_candidacy_id)

    with pytest.raises(ValueError, match="duplicate subject_candidacy_id"):
        validate_trustee_career_cohort(cohort, _results())


def test_repository_review_contract_is_complete():
    cohort = load_trustee_career_cohort(REFERENCE / "trustee_career_cohort_2026.csv")
    reviews = pd.read_csv(
        REFERENCE / "trustee_career_reviews.csv", dtype="string", keep_default_na=False
    )
    decisions = pd.read_csv(
        REFERENCE / "trustee_career_decisions.csv", dtype="string", keep_default_na=False
    )

    validate_trustee_career_contracts(
        cohort,
        reviews,
        decisions,
        _results(),
        repository_root=ROOT,
        require_complete=True,
    )

    assert reviews.columns.tolist() == REVIEW_COLUMNS
    assert decisions.columns.tolist() == DECISION_COLUMNS
    assert reviews["subject_candidacy_id"].nunique() == 118


def test_sol_review_exactly_covers_all_60_revisited_holds():
    decisions = pd.read_csv(
        REFERENCE / "trustee_career_decisions.csv", dtype="string", keep_default_na=False
    )
    sol_reviews = pd.read_csv(
        REFERENCE / "trustee_career_sol_reviews.csv", dtype="string", keep_default_na=False
    )

    validate_trustee_sol_reviews(sol_reviews, decisions, repository_root=ROOT)

    assert sol_reviews.columns.tolist() == SOL_REVIEW_COLUMNS
    assert len(sol_reviews) == 60
    assert sol_reviews["subject_candidacy_id"].nunique() == 33
    assert not sol_reviews.duplicated(["subject_candidacy_id", "prior_candidacy_id"]).any()
    canonical_by_id = decisions.set_index("decision_id")["decision"]
    expected = sol_reviews["sol_disposition"].map(SOL_TO_CANONICAL)
    actual = sol_reviews["decision_id"].map(canonical_by_id)
    assert actual.tolist() == expected.tolist()


def test_review_contract_rejects_pre_2003_and_non_toronto_occurrences():
    cohort = load_trustee_career_cohort(REFERENCE / "trustee_career_cohort_2026.csv")
    reviews = pd.read_csv(
        REFERENCE / "trustee_career_reviews.csv",
        dtype="string",
        keep_default_na=False,
    )
    decisions = pd.read_csv(
        REFERENCE / "trustee_career_decisions.csv",
        dtype="string",
        keep_default_na=False,
    )
    decisions.loc[
        0,
        [
            "prior_candidacy_id",
            "observed_ballot_name",
            "election_date",
            "represented_body",
            "office_type",
            "district_name",
        ],
    ] = ["can_pre_2003", "Example Person", "2000-11-13", "elsewhere", "trustee", "Ward 1"]
    results = pd.concat(
        [
            _results(),
            pd.DataFrame(
                [
                    {
                        "candidacy_id": "can_pre_2003",
                        "election_date": "2000-11-13",
                        "office_type": "trustee",
                        "represented_body": "elsewhere",
                        "candidate_name": "Example Person",
                        "district_name": "Ward 1",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="Toronto election on or after 2003"):
        validate_trustee_career_contracts(cohort, reviews, decisions, results)


def test_confirmed_decisions_build_occurrence_level_assertions():
    results = _results()

    assertions = build_trustee_career_identity_assertions(REFERENCE, results)

    confirmed_subjects = (
        pd.read_csv(REFERENCE / "trustee_career_decisions.csv", dtype="string")
        .loc[lambda frame: frame["decision"].eq("confirm"), "subject_candidacy_id"]
        .nunique()
    )
    assert len(assertions) == confirmed_subjects
    assert all(len(assertion.occurrences) >= 2 for assertion in assertions)
    assert all(assertion.evidence_urls for assertion in assertions)


def test_held_current_proposals_become_unresolved_identity_decisions():
    holds = build_trustee_hold_decisions(REFERENCE)

    assert set(holds.columns) == {
        "candidacy_id",
        "target_person_id",
        "decision",
        "confidence",
        "rationale",
        "evidence_urls",
        "reviewer",
    }
    assert holds["decision"].eq("unresolved").all()
    assert holds["target_person_id"].str.startswith("per_").all()


def test_a_held_alternative_does_not_override_a_confirmed_identity():
    reference = REFERENCE
    decisions = pd.read_csv(
        reference / "trustee_career_decisions.csv",
        dtype="string",
        keep_default_na=False,
    )
    mixed_subjects = set(
        decisions.groupby("subject_candidacy_id")["decision"]
        .apply(lambda values: set(values))
        .loc[lambda values: values.map(lambda value: {"confirm", "hold"} <= value)]
        .index
    )

    holds = build_trustee_hold_decisions(reference)

    assert set(holds["candidacy_id"]).isdisjoint(mixed_subjects)


def test_expected_board_contest_contract_has_29_contests():
    assert sum(EXPECTED_CONTEST_COUNTS.values()) == 29
    assert set(EXPECTED_CONTEST_COUNTS.values()) == {2, 3, 12}
