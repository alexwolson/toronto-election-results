"""Contracts for the complete 2026 Toronto mayoral career review."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .identity_curations import CandidacyLocator, CuratedIdentityAssertion
from .schema import normalize_adapter_frame, stable_id

COHORT_ID = "toronto-mayor-2026"
EXPECTED_COHORT_SIZE = 53
REVIEW_STATUSES = {
    "reviewed",
    "no_verified_prior_candidacy",
    "reviewed_with_limitations",
}
OCCURRENCE_DECISIONS = {"confirm", "hold", "split", "reject"}
INGESTION_ACTIONS = {"add_backfill", "reuse_existing", "none"}

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

REVIEW_COLUMNS = [
    "cohort_id",
    "subject_candidacy_id",
    "certified_name",
    "resulting_person_id",
    "luna_report_path",
    "terra_report_path",
    "review_date",
    "source_release",
    "review_status",
    "limitations",
    "confirmed_count",
    "held_count",
    "split_count",
    "rejected_count",
    "primary_rationale",
]

DECISION_COLUMNS = [
    "decision_id",
    "cohort_id",
    "subject_candidacy_id",
    "proposed_occurrence_key",
    "observed_ballot_name",
    "election_date",
    "jurisdiction",
    "office",
    "district",
    "decision",
    "ingestion_action",
    "identity_bridge",
    "result_source_authority",
    "result_source_resource",
    "result_source_locator",
    "rationale",
]

BACKFILL_COLUMNS = [
    "backfill_id",
    "decision_id",
    "subject_candidacy_id",
    "election_date",
    "election_type",
    "election_authority",
    "represented_body",
    "office_type",
    "district_name",
    "candidate_name_raw",
    "party_name_raw",
    "votes",
    "total_contest_votes",
    "vote_share",
    "vote_rank",
    "n_candidates",
    "elected",
    "acclaimed",
    "result_status",
    "source_authority",
    "source_resource",
    "source_locator",
]

MAPPING_COLUMNS = [
    "cohort_id",
    "subject_candidacy_id",
    "decision_id",
    "canonical_candidacy_id",
]

_BACKFILL_METADATA = {
    "mcb_04e95c9a724c54999be8e7d630bca53e": (
        "ec-ge-41",
        "federal-2003-representation-order",
        "35001",
    ),
    "mcb_318578ea26775989886cc960cd9d578e": (
        "ec-ge-42",
        "federal-2013-representation-order",
        "35001",
    ),
    "mcb_9c7aef4fac8d5654b76124195615fb03": (
        "mississauga-2024-06-10-mayoral-by-election",
        "mississauga-2024-citywide",
        "city",
    ),
    "mcb_a14d901d7faa5d15abbbbf553bfed1b5": (
        "on-2015-09-03-by-091",
        "ontario-2007-107",
        "091",
    ),
    "mcb_f5f1e935bd9e57ff82a4507255752612": (
        "on-2022-general",
        "ontario-2018-124",
        "092",
    ),
    "mcb_acb473030b2554299e80456052ab7773": (
        "toronto-1991-general",
        "metro-toronto-1991",
        "downtown",
    ),
    "mcb_a0d89937c2e2598ea6bebe4303fa39df": (
        "toronto-1994-general",
        "metro-toronto-1994",
        "downtown",
    ),
    "mcb_9df884ee157a57d887f9b7e165384eaf": (
        "toronto-1997-general",
        "toronto-1997-wards",
        "24",
    ),
    "mcb_a63809d41357505c95f345cf0e63acf9": (
        "toronto-2000-general",
        "toronto-2000-wards",
        "20",
    ),
}


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


def load_contract_table(path: str | Path, columns: list[str]) -> pd.DataFrame:
    """Load a career-review contract table and enforce its exact schema."""

    table = pd.read_csv(path, dtype="string", keep_default_na=False)
    if table.columns.tolist() != columns:
        raise ValueError(f"{Path(path).name} columns must be exactly: {', '.join(columns)}")
    return table


def load_mayoral_career_backfills(reference_dir: str | Path) -> pd.DataFrame:
    """Adapt only adjudicated career backfills to the normalized source boundary."""

    reference = Path(reference_dir)
    backfill = load_contract_table(reference / "mayoral_career_backfill.csv", BACKFILL_COLUMNS)
    decisions = load_contract_table(reference / "mayoral_career_decisions.csv", DECISION_COLUMNS)
    allowed = decisions.loc[
        decisions["decision"].eq("confirm")
        & decisions["ingestion_action"].eq("add_backfill"),
        "decision_id",
    ]
    if set(backfill["decision_id"]) != set(allowed):
        raise ValueError("career backfills must exactly match confirmed add_backfill decisions")
    unknown = sorted(set(backfill["backfill_id"]) - set(_BACKFILL_METADATA))
    if unknown:
        raise ValueError(f"missing canonical metadata for career backfill {unknown[0]}")

    rows: list[dict[str, object]] = []
    for row in backfill.itertuples(index=False):
        event_id, boundary_regime, official_district_id = _BACKFILL_METADATA[row.backfill_id]
        rows.append(
            {
                "event_id": event_id,
                "election_date": row.election_date,
                "election_type": row.election_type,
                "election_authority": row.election_authority,
                "represented_body": row.represented_body,
                "office_type": row.office_type,
                "boundary_regime": boundary_regime,
                "official_district_id": official_district_id,
                "district_name": row.district_name,
                "candidate_name_raw": row.candidate_name_raw,
                "source_candidacy_id": row.backfill_id,
                "party_name_raw": row.party_name_raw or pd.NA,
                "votes": row.votes,
                "elected": row.elected.casefold() == "true",
                "outcome_method": "vote",
                "result_status": row.result_status,
                "coverage_status": "candidate_record",
                "reported_total_contest_votes": row.total_contest_votes,
                "reported_vote_share": row.vote_share,
                "reported_vote_rank": row.vote_rank,
                "reported_n_candidates": row.n_candidates,
                "source_authority": row.source_authority,
                "source_resource": row.source_resource,
                "source_detail": row.source_locator,
            }
        )
    return pd.DataFrame(rows)


def build_mayoral_career_identity_assertions(
    reference_dir: str | Path,
    adapter_frames: list[pd.DataFrame],
) -> tuple[CuratedIdentityAssertion, ...]:
    """Build explicit identity assertions from the completed adjudication registry."""

    reference = Path(reference_dir)
    cohort = load_mayoral_career_cohort(reference / "mayoral_career_cohort_2026.csv")
    reviews = load_contract_table(reference / "mayoral_career_reviews.csv", REVIEW_COLUMNS)
    decisions = load_contract_table(reference / "mayoral_career_decisions.csv", DECISION_COLUMNS)
    backfill = load_contract_table(reference / "mayoral_career_backfill.csv", BACKFILL_COLUMNS)
    mappings = load_contract_table(
        reference / "mayoral_career_occurrence_mapping.csv", MAPPING_COLUMNS
    )
    validate_mayoral_career_contracts(
        cohort,
        reviews,
        decisions,
        backfill,
        mappings,
        repository_root=reference.parent.parent,
        require_complete=True,
        require_ingested=False,
    )

    normalized = pd.concat(
        [
            normalize_adapter_frame(frame, require_persistent_candidacy_id=True)
            for frame in adapter_frames
            if not frame.empty
        ],
        ignore_index=True,
        sort=False,
    )
    by_candidacy = normalized.drop_duplicates("candidacy_id").set_index("candidacy_id")
    backfill_ids = normalized.loc[
        normalized["source_candidacy_id"].isin(backfill["backfill_id"]),
        ["source_candidacy_id", "candidacy_id"],
    ].set_index("source_candidacy_id")["candidacy_id"]
    mapped = mappings.set_index("decision_id")["canonical_candidacy_id"].to_dict()
    mapped.update(
        backfill.set_index("decision_id")["backfill_id"].map(backfill_ids).to_dict()
    )
    reviews_by_subject = reviews.set_index("subject_candidacy_id")
    assertions: list[CuratedIdentityAssertion] = []
    confirmed = decisions.loc[decisions["decision"].eq("confirm")]
    for subject_id, subject_decisions in confirmed.groupby("subject_candidacy_id", sort=True):
        candidacy_ids = [subject_id, *subject_decisions["decision_id"].map(mapped).tolist()]
        candidacy_ids = list(dict.fromkeys(candidacy_ids))
        missing = [value for value in candidacy_ids if value not in by_candidacy.index]
        if missing:
            raise ValueError(f"career assertion references missing candidacy {missing[0]}")
        occurrences = tuple(
            CandidacyLocator(
                event_id=str(by_candidacy.loc[candidacy_id, "event_id"]),
                represented_body=str(by_candidacy.loc[candidacy_id, "represented_body"]),
                office_type=str(by_candidacy.loc[candidacy_id, "office_type"]),
                candidate_name=str(by_candidacy.loc[candidacy_id, "candidate_name"]),
                candidacy_id=candidacy_id,
            )
            for candidacy_id in candidacy_ids
        )
        review = reviews_by_subject.loc[subject_id]
        evidence_urls = tuple(
            dict.fromkeys(
                url
                for url in subject_decisions["result_source_locator"]
                if str(url).startswith("https://")
            )
        )
        assertions.append(
            CuratedIdentityAssertion(
                assertion_id=stable_id("ast", COHORT_ID, subject_id),
                preferred_name=str(review["certified_name"]),
                occurrences=occurrences,
                evidence_urls=evidence_urls,
                rationale=str(review["primary_rationale"]),
                registry_person_ids=(str(review["resulting_person_id"]),),
                canonical_person_id=str(review["resulting_person_id"]),
            )
        )
    return tuple(assertions)


def exclude_superseded_identity_decisions(
    identity_decisions: pd.DataFrame, reference_dir: str | Path
) -> pd.DataFrame:
    """Let the newer complete-career adjudication supersede older occurrence reviews."""

    mappings = load_contract_table(
        Path(reference_dir) / "mayoral_career_occurrence_mapping.csv", MAPPING_COLUMNS
    )
    superseded = set(mappings["canonical_candidacy_id"])
    return identity_decisions.loc[
        ~identity_decisions["candidacy_id"].isin(superseded)
    ].reset_index(drop=True)


def _require_unique(table: pd.DataFrame, columns: list[str], label: str) -> None:
    if table.duplicated(columns, keep=False).any():
        values = table.loc[table.duplicated(columns, keep=False), columns].iloc[0].tolist()
        raise ValueError(f"duplicate {label}: {values}")


def _require_values(table: pd.DataFrame, columns: list[str], label: str) -> None:
    for column in columns:
        if table[column].str.strip().eq("").any():
            raise ValueError(f"{label} requires {column}")


def _validate_report_path(
    value: str, *, repository_root: Path, subject_candidacy_id: str, agent: str
) -> None:
    expected = f"docs/research/mayoral-career/2026/{subject_candidacy_id}-{agent}.md"
    if value != expected:
        raise ValueError(f"{agent} report path for {subject_candidacy_id} must be {expected}")
    resolved = (repository_root / value).resolve()
    if not resolved.is_relative_to(repository_root.resolve()) or not resolved.is_file():
        raise ValueError(f"missing {agent} report for {subject_candidacy_id}: {value}")


def validate_mayoral_career_contracts(
    cohort: list[MayoralCareerCohortRow],
    reviews: pd.DataFrame,
    decisions: pd.DataFrame,
    backfill: pd.DataFrame,
    mappings: pd.DataFrame,
    *,
    repository_root: str | Path,
    require_complete: bool = False,
    require_ingested: bool = False,
) -> None:
    """Validate research decisions separately from publishable canonical ingestion."""

    tables = [
        (reviews, REVIEW_COLUMNS, "reviews"),
        (decisions, DECISION_COLUMNS, "decisions"),
        (backfill, BACKFILL_COLUMNS, "backfill"),
        (mappings, MAPPING_COLUMNS, "mappings"),
    ]
    for table, columns, label in tables:
        if table.columns.tolist() != columns:
            raise ValueError(f"{label} columns must be exactly: {', '.join(columns)}")

    cohort_by_id = {row.subject_candidacy_id: row for row in cohort}
    cohort_ids = set(cohort_by_id)
    _require_unique(reviews, ["subject_candidacy_id"], "candidate review")
    _require_unique(decisions, ["decision_id"], "decision_id")
    _require_unique(
        decisions,
        ["subject_candidacy_id", "proposed_occurrence_key"],
        "candidate occurrence decision",
    )
    _require_unique(backfill, ["backfill_id"], "backfill_id")
    _require_unique(backfill, ["decision_id"], "backfill decision_id")
    _require_unique(mappings, ["decision_id"], "mapping decision_id")
    _require_unique(mappings, ["canonical_candidacy_id"], "canonical candidacy mapping")

    for label, table in [("review", reviews), ("decision", decisions), ("mapping", mappings)]:
        unknown = sorted(set(table["subject_candidacy_id"]) - cohort_ids)
        if unknown:
            raise ValueError(f"{label} references candidate outside cohort: {unknown[0]}")
        wrong_cohort = table.loc[~table["cohort_id"].eq(COHORT_ID)]
        if not wrong_cohort.empty:
            raise ValueError(f"{label} cohort_id must be {COHORT_ID}")
    unknown_backfill = sorted(set(backfill["subject_candidacy_id"]) - cohort_ids)
    if unknown_backfill:
        raise ValueError(f"backfill references candidate outside cohort: {unknown_backfill[0]}")

    invalid_statuses = sorted(set(reviews["review_status"]) - REVIEW_STATUSES)
    if invalid_statuses:
        raise ValueError(f"invalid review_status: {invalid_statuses[0]}")
    invalid_decisions = sorted(set(decisions["decision"]) - OCCURRENCE_DECISIONS)
    if invalid_decisions:
        raise ValueError(f"invalid occurrence decision: {invalid_decisions[0]}")
    invalid_actions = sorted(set(decisions["ingestion_action"]) - INGESTION_ACTIONS)
    if invalid_actions:
        raise ValueError(f"invalid ingestion_action: {invalid_actions[0]}")

    _require_values(
        reviews,
        [
            "certified_name",
            "luna_report_path",
            "terra_report_path",
            "review_date",
            "source_release",
            "review_status",
            "primary_rationale",
        ],
        "candidate review",
    )
    root = Path(repository_root)
    for row in reviews.itertuples(index=False):
        cohort_row = cohort_by_id[row.subject_candidacy_id]
        if row.certified_name != cohort_row.certified_name:
            raise ValueError(f"certified_name changed for {row.subject_candidacy_id}")
        if row.source_release != cohort_row.source_release:
            raise ValueError(f"source_release changed for {row.subject_candidacy_id}")
        _validate_report_path(
            row.luna_report_path,
            repository_root=root,
            subject_candidacy_id=row.subject_candidacy_id,
            agent="luna",
        )
        _validate_report_path(
            row.terra_report_path,
            repository_root=root,
            subject_candidacy_id=row.subject_candidacy_id,
            agent="terra",
        )
        if row.review_status == "reviewed_with_limitations" and not row.limitations.strip():
            raise ValueError(
                f"reviewed_with_limitations requires limitations for {row.subject_candidacy_id}"
            )
        try:
            confirmed_count = int(row.confirmed_count)
        except ValueError as exc:
            raise ValueError(f"{row.subject_candidacy_id} has invalid confirmed_count") from exc
        if row.review_status == "reviewed" and confirmed_count < 1:
            raise ValueError(
                f"reviewed status requires a confirmed occurrence for {row.subject_candidacy_id}"
            )
        if row.review_status == "no_verified_prior_candidacy" and confirmed_count != 0:
            raise ValueError(
                "no_verified_prior_candidacy cannot have confirmed occurrences for "
                f"{row.subject_candidacy_id}"
            )

    confirmation_fields = [
        "observed_ballot_name",
        "election_date",
        "jurisdiction",
        "office",
        "identity_bridge",
        "result_source_authority",
        "result_source_resource",
        "result_source_locator",
        "rationale",
    ]
    confirmed = decisions.loc[decisions["decision"].eq("confirm")]
    _require_values(confirmed, confirmation_fields, "confirmed decision")
    invalid_confirm_action = confirmed.loc[
        ~confirmed["ingestion_action"].isin({"add_backfill", "reuse_existing"})
    ]
    if not invalid_confirm_action.empty:
        raise ValueError("confirmed decision requires add_backfill or reuse_existing")
    nonconfirmed_with_ingest = decisions.loc[
        ~decisions["decision"].eq("confirm") & ~decisions["ingestion_action"].eq("none")
    ]
    if not nonconfirmed_with_ingest.empty:
        raise ValueError("held, split, or rejected decision cannot be ingested")

    decisions_by_id = decisions.set_index("decision_id", drop=False)
    required_backfill = set(
        decisions.loc[
            decisions["decision"].eq("confirm") & decisions["ingestion_action"].eq("add_backfill"),
            "decision_id",
        ]
    )
    actual_backfill = set(backfill["decision_id"])
    if actual_backfill != required_backfill:
        raise ValueError(
            "backfill decisions must exactly equal confirmed add_backfill decisions; "
            f"required={sorted(required_backfill)}, actual={sorted(actual_backfill)}"
        )
    if not backfill.empty:
        _require_values(
            backfill,
            [column for column in BACKFILL_COLUMNS if column != "party_name_raw"],
            "backfill row",
        )
        for row in backfill.itertuples(index=False):
            decision = decisions_by_id.loc[row.decision_id]
            if row.subject_candidacy_id != decision.subject_candidacy_id:
                raise ValueError(f"backfill subject does not match decision {row.decision_id}")

    confirmed_ids = set(confirmed["decision_id"])
    invalid_mapping = sorted(set(mappings["decision_id"]) - confirmed_ids)
    if invalid_mapping:
        raise ValueError(f"mapping references non-confirmed decision: {invalid_mapping[0]}")
    if not mappings.empty:
        _require_values(mappings, MAPPING_COLUMNS, "mapping row")
        for row in mappings.itertuples(index=False):
            decision = decisions_by_id.loc[row.decision_id]
            if row.subject_candidacy_id != decision.subject_candidacy_id:
                raise ValueError(f"mapping subject does not match decision {row.decision_id}")

    if require_complete:
        reviewed_ids = set(reviews["subject_candidacy_id"])
        if reviewed_ids != cohort_ids:
            missing = sorted(cohort_ids - reviewed_ids)
            extra = sorted(reviewed_ids - cohort_ids)
            raise ValueError(f"review registry is incomplete; missing={missing}, extra={extra}")
        count_columns = {
            "confirm": "confirmed_count",
            "hold": "held_count",
            "split": "split_count",
            "reject": "rejected_count",
        }
        for row in reviews.itertuples(index=False):
            subject = decisions.loc[decisions["subject_candidacy_id"].eq(row.subject_candidacy_id)]
            for decision, count_column in count_columns.items():
                actual = int(subject["decision"].eq(decision).sum())
                try:
                    expected = int(getattr(row, count_column))
                except ValueError as exc:
                    raise ValueError(
                        f"{row.subject_candidacy_id} has invalid {count_column}"
                    ) from exc
                if actual != expected:
                    raise ValueError(
                        f"{row.subject_candidacy_id} {count_column} is {expected}; expected {actual}"
                    )
    if require_ingested and set(mappings["decision_id"]) != confirmed_ids:
        missing = sorted(confirmed_ids - set(mappings["decision_id"]))
        raise ValueError(f"confirmed decisions are not fully mapped: {missing}")


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
