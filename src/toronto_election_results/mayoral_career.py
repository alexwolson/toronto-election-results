"""Contracts for the complete 2026 Toronto mayoral career review."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

COHORT_ID = "toronto-mayor-2026"
EXPECTED_COHORT_SIZE = 53

_COHORT_COLUMNS = [
    "cohort_id",
    "subject_candidacy_id",
    "certified_name",
    "certified_name_raw",
    "current_person_id",
    "event_id",
    "contest_id",
    "source_release",
    "source_commit",
]


@dataclass(frozen=True)
class MayoralCareerCohortRow:
    """One frozen subject in the complete mayoral career-review cohort."""

    cohort_id: str
    subject_candidacy_id: str
    certified_name: str
    certified_name_raw: str
    current_person_id: str | None
    event_id: str
    contest_id: str
    source_release: str
    source_commit: str


def _required(value: object, field: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{field} cannot be blank")
    return text


def _optional(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def load_mayoral_career_cohort(path: str | Path) -> list[MayoralCareerCohortRow]:
    """Load the frozen cohort without treating blank Person IDs as values."""

    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != _COHORT_COLUMNS:
            raise ValueError(
                "mayoral career cohort columns must be exactly: " + ", ".join(_COHORT_COLUMNS)
            )
        return [
            MayoralCareerCohortRow(
                cohort_id=_required(row["cohort_id"], "cohort_id"),
                subject_candidacy_id=_required(row["subject_candidacy_id"], "subject_candidacy_id"),
                certified_name=_required(row["certified_name"], "certified_name"),
                certified_name_raw=_required(row["certified_name_raw"], "certified_name_raw"),
                current_person_id=_optional(row["current_person_id"]),
                event_id=_required(row["event_id"], "event_id"),
                contest_id=_required(row["contest_id"], "contest_id"),
                source_release=_required(row["source_release"], "source_release"),
                source_commit=_required(row["source_commit"], "source_commit"),
            )
            for row in reader
        ]


def validate_mayoral_career_cohort(
    rows: list[MayoralCareerCohortRow], results: pd.DataFrame
) -> None:
    """Require the frozen cohort to match one complete pending mayoral contest."""

    if len(rows) != EXPECTED_COHORT_SIZE:
        raise ValueError(
            f"mayoral career cohort must contain {EXPECTED_COHORT_SIZE} rows; got {len(rows)}"
        )

    subject_ids = [row.subject_candidacy_id for row in rows]
    duplicates = sorted({value for value in subject_ids if subject_ids.count(value) > 1})
    if duplicates:
        raise ValueError(f"duplicate subject_candidacy_id: {duplicates[0]}")

    for field in ["cohort_id", "event_id", "contest_id", "source_release", "source_commit"]:
        values = {getattr(row, field) for row in rows}
        if len(values) != 1:
            raise ValueError(f"cohort must use one {field}; got {sorted(values)}")
    if rows[0].cohort_id != COHORT_ID:
        raise ValueError(f"cohort_id must be {COHORT_ID!r}")

    required_results = {
        "candidacy_id",
        "candidate_name",
        "candidate_name_raw",
        "person_id",
        "event_id",
        "contest_id",
        "office_type",
        "result_status",
    }
    missing = sorted(required_results - set(results.columns))
    if missing:
        raise ValueError(f"results is missing required columns: {', '.join(missing)}")

    contest_id = rows[0].contest_id
    current = results.loc[
        results["contest_id"].eq(contest_id)
        & results["office_type"].eq("mayor")
        & results["result_status"].eq("pending")
    ].copy()
    if current["candidacy_id"].duplicated().any():
        duplicate = current.loc[
            current["candidacy_id"].duplicated(keep=False), "candidacy_id"
        ].iloc[0]
        raise ValueError(f"results contains duplicate candidacy_id: {duplicate}")

    actual_ids = set(current["candidacy_id"].astype(str))
    frozen_ids = set(subject_ids)
    if actual_ids != frozen_ids:
        missing_ids = sorted(actual_ids - frozen_ids)
        extra_ids = sorted(frozen_ids - actual_ids)
        raise ValueError(
            f"frozen cohort does not match certified contest; missing={missing_ids}, extra={extra_ids}"
        )

    current = current.set_index("candidacy_id")
    for row in rows:
        source = current.loc[row.subject_candidacy_id]
        expected = {
            "candidate_name": row.certified_name,
            "candidate_name_raw": row.certified_name_raw,
            "person_id": row.current_person_id,
            "event_id": row.event_id,
            "contest_id": row.contest_id,
        }
        for column, expected_value in expected.items():
            actual_value = _optional(source[column])
            if actual_value != expected_value:
                raise ValueError(
                    f"{row.subject_candidacy_id} {column} changed: "
                    f"frozen={expected_value!r}, results={actual_value!r}"
                )
