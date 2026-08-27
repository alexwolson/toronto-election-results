"""Evidence-backed incumbency for certified 2026 Toronto trustee candidates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .schema import stable_id

FILENAME = "trustee_incumbents_2026.csv"
ELECTION_DATE = "2026-10-26"
EXPECTED_BODY_COUNTS = {
    "toronto_district_school_board": 8,
    "toronto_catholic_district_school_board": 8,
    "conseil_scolaire_viamonde": 3,
    "conseil_scolaire_catholique_monavenir": 1,
}
SOURCE_COLUMNS = [
    "subject_candidacy_id",
    "represented_body",
    "incumbent_name",
    "reference_date",
    "source_authority",
    "source_url",
    "source_detail",
]
TENURE_COLUMNS = [
    "office_tenure_id",
    "person_id",
    "represented_body",
    "office_type",
    "district_id",
    "started_on",
    "started_on_precision",
    "ended_on",
    "ended_on_precision",
    "entry_method",
    "source_authority",
    "source_detail",
]
ROSTER_COLUMNS = [
    "event_id",
    "person_id",
    "represented_body",
    "office_type",
    "office_tenure_id",
    "roster_complete",
    "reference_date",
    "reference_date_rule",
    "source_detail",
]


@dataclass(frozen=True)
class TrusteeIncumbencyEvidence:
    """Current-holder tenures and event-scoped roster members."""

    office_tenures: pd.DataFrame
    rosters: pd.DataFrame


def _empty() -> TrusteeIncumbencyEvidence:
    return TrusteeIncumbencyEvidence(
        pd.DataFrame(columns=TENURE_COLUMNS), pd.DataFrame(columns=ROSTER_COLUMNS)
    )


def build_trustee_incumbency_evidence(
    candidacies: pd.DataFrame, reference_dir: str | Path
) -> TrusteeIncumbencyEvidence:
    """Build an incomplete roster that can prove listed incumbents true, never absence."""

    source_path = Path(reference_dir) / FILENAME
    if not source_path.is_file():
        raise ValueError(f"trustee incumbency source is missing: {source_path}")
    source = pd.read_csv(source_path, dtype="string", keep_default_na=False)
    if source.columns.tolist() != SOURCE_COLUMNS:
        raise ValueError("trustee incumbency source columns do not match the contract")
    if source["subject_candidacy_id"].duplicated().any():
        raise ValueError("trustee incumbency source repeats a candidate")
    counts = source["represented_body"].value_counts().to_dict()
    if counts != EXPECTED_BODY_COUNTS:
        raise ValueError(f"unexpected trustee incumbent coverage: {counts}")
    if not source["source_url"].str.startswith("https://").all():
        raise ValueError("trustee incumbency sources require HTTPS URLs")
    if source[["incumbent_name", "source_authority", "source_detail"]].eq("").any().any():
        raise ValueError("trustee incumbency sources require names and evidence detail")

    required = {
        "candidacy_id",
        "person_id",
        "event_id",
        "election_date",
        "represented_body",
        "office_type",
        "district_id",
        "candidate_name",
        "elected",
    }
    missing = sorted(required - set(candidacies.columns))
    if missing:
        raise ValueError(f"candidacies is missing trustee incumbency fields: {', '.join(missing)}")
    by_id = candidacies.set_index("candidacy_id", drop=False)
    tenure_rows: list[dict[str, object]] = []
    roster_rows: list[dict[str, object]] = []

    for row in source.itertuples(index=False):
        if row.subject_candidacy_id not in by_id.index:
            raise ValueError(f"unknown trustee incumbent candidacy: {row.subject_candidacy_id}")
        current = by_id.loc[row.subject_candidacy_id]
        expected = {
            "election_date": ELECTION_DATE,
            "represented_body": row.represented_body,
            "office_type": "trustee",
            "candidate_name": row.incumbent_name,
        }
        for field, value in expected.items():
            if str(current[field]) != value:
                raise ValueError(
                    f"trustee incumbent {field} changed for {row.subject_candidacy_id}"
                )
        person_id = str(current["person_id"]).strip()
        if not person_id or person_id == "<NA>":
            raise ValueError(f"trustee incumbent lacks a verified Person: {row.incumbent_name}")

        prior = candidacies.loc[
            candidacies["person_id"].eq(person_id)
            & candidacies["represented_body"].eq(row.represented_body)
            & candidacies["office_type"].eq("trustee")
            & candidacies["election_date"].astype("string").lt(ELECTION_DATE)
            & candidacies["elected"].astype("boolean").fillna(False)
        ].sort_values("election_date", kind="stable")
        if prior.empty:
            raise ValueError(f"trustee incumbent has no verified election: {row.incumbent_name}")
        anchor = prior.iloc[-1]
        tenure_id = stable_id("ten", "trustee_incumbency_2026", row.represented_body, person_id)
        detail = json.dumps(
            {
                "incumbent_name": row.incumbent_name,
                "rule": "verified_current_holder_before_2026_general_election",
                "source_detail": row.source_detail,
                "source_url": row.source_url,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        tenure_rows.append(
            {
                "office_tenure_id": tenure_id,
                "person_id": person_id,
                "represented_body": row.represented_body,
                "office_type": "trustee",
                "district_id": anchor["district_id"],
                "started_on": anchor["election_date"],
                "started_on_precision": "election_date",
                "ended_on": row.reference_date,
                "ended_on_precision": "at_or_after_reference",
                "entry_method": "election",
                "source_authority": row.source_authority,
                "source_detail": detail,
            }
        )
        roster_rows.append(
            {
                "event_id": current["event_id"],
                "person_id": person_id,
                "represented_body": row.represented_body,
                "office_type": "trustee",
                "office_tenure_id": tenure_id,
                "roster_complete": False,
                "reference_date": row.reference_date,
                "reference_date_rule": "verified_current_holder_snapshot",
                "source_detail": detail,
            }
        )

    return TrusteeIncumbencyEvidence(
        pd.DataFrame(tenure_rows, columns=TENURE_COLUMNS),
        pd.DataFrame(roster_rows, columns=ROSTER_COLUMNS),
    )
