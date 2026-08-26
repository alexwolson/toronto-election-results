"""Contracts for the complete 2026 Toronto mayoral career review."""

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.mayoral_career import (
    EXPECTED_COHORT_SIZE,
    load_mayoral_career_cohort,
    validate_mayoral_career_cohort,
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
        ("current_person_id", "per_changed", "person_id changed"),
        ("event_id", "evt_changed", "cohort must use one event_id"),
    ],
)
def test_frozen_source_mutation_is_rejected(field: str, value: str, message: str):
    rows, results = _real_inputs()
    rows[0] = replace(rows[0], **{field: value})

    with pytest.raises(ValueError, match=message):
        validate_mayoral_career_cohort(rows, results)
