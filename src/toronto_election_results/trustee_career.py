"""Cohort-complete identity review for certified 2026 Toronto trustee candidates.

The public history policy is deliberately narrower than the mayoral policy: only
Toronto public-election occurrences from 2003 onward are eligible.  Candidate names
are research leads; only occurrence-level ``confirm`` decisions become Person links.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .identity_curations import CandidacyLocator, CuratedIdentityAssertion
from .identity_dispositions import IDENTITY_REVIEW_DECISION_COLUMNS
from .schema import stable_id

COHORT_ID = "toronto-trustee-2026"
CURRENT_ELECTION_DATE = "2026-10-26"
MINIMUM_HISTORY_DATE = "2003-01-01"
EXPECTED_CONTEST_COUNTS = {
    "toronto_district_school_board": 12,
    "toronto_catholic_district_school_board": 12,
    "conseil_scolaire_viamonde": 3,
    "conseil_scolaire_catholique_monavenir": 2,
}
REVIEW_STATUSES = {"reviewed", "reviewed_with_limitations"}
DECISIONS = {"confirm", "hold", "split", "reject"}

COHORT_COLUMNS = [
    "cohort_id",
    "subject_candidacy_id",
    "certified_name",
    "certified_name_raw",
    "represented_body",
    "official_district_id",
    "contest_id",
    "source_order",
    "current_person_id",
    "proposed_target_person_id",
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
    "review_status",
    "limitations",
    "confirmed_count",
    "held_count",
    "split_count",
    "rejected_count",
    "evidence_urls",
    "primary_rationale",
]

DECISION_COLUMNS = [
    "decision_id",
    "cohort_id",
    "subject_candidacy_id",
    "prior_candidacy_id",
    "observed_ballot_name",
    "election_date",
    "represented_body",
    "office_type",
    "district_name",
    "decision",
    "identity_bridge",
    "evidence_urls",
    "rationale",
]

SOL_REVIEW_COLUMNS = [
    "cohort_id",
    "subject_candidacy_id",
    "prior_candidacy_id",
    "decision_id",
    "sol_report_path",
    "sol_batch_path",
    "review_date",
    "model",
    "sol_disposition",
    "identity_bridge",
    "evidence_urls",
    "rationale",
]
SOL_DISPOSITIONS = {"upgrade_to_confirm", "retain_hold", "reject"}
SOL_REVIEW_DATE = "2026-08-27"
SOL_MODEL = "gpt-5.6-sol"
SOL_TO_CANONICAL = {
    "upgrade_to_confirm": "confirm",
    "retain_hold": "hold",
    "reject": "reject",
}

_TORONTO_MUNICIPAL_BODIES = {
    "toronto_city_council",
    *EXPECTED_CONTEST_COUNTS,
}
_CANADA_WIDE_BODIES = {
    "canada_house_of_commons",
    "ontario_legislative_assembly",
}
_TORONTO_RIDING_NAMES = {
    "Beaches—East York",
    "Broadview-Greenwood",
    "Davenport",
    "Don Valley East",
    "Don Valley North",
    "Don Valley West",
    "Eglinton—Lawrence",
    "Etobicoke Centre",
    "Etobicoke North",
    "Etobicoke—Lakeshore",
    "Humber River—Black Creek",
    "Parkdale—High Park",
    "Scarborough Centre",
    "Scarborough Centre—Don Valley East",
    "Scarborough East",
    "Scarborough North",
    "Scarborough Southwest",
    "Scarborough—Agincourt",
    "Scarborough—Guildwood",
    "Scarborough—Guildwood—Rouge Park",
    "Scarborough—Rouge Park",
    "Scarborough—Rouge River",
    "Scarborough—Woburn",
    "Spadina—Fort York",
    "Spadina—Harbourfront",
    "St. Paul's",
    "Taiaiako'n—Parkdale—High Park",
    "Toronto Centre",
    "Toronto Centre—Rosedale",
    "Toronto—Danforth",
    "Toronto—St. Paul's",
    "Trinity—Spadina",
    "University—Rosedale",
    "Willowdale",
    "York Centre",
    "York South",
    "York South—Weston",
    "York South—Weston—Etobicoke",
    "York West",
}


@dataclass(frozen=True)
class TrusteeCareerCohortRow:
    """One certified candidate in the frozen trustee review cohort."""

    cohort_id: str
    subject_candidacy_id: str
    certified_name: str
    certified_name_raw: str
    represented_body: str
    official_district_id: str
    contest_id: str
    source_order: int
    current_person_id: str | None
    proposed_target_person_id: str | None
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


def _urls(value: object, *, field: str) -> tuple[str, ...]:
    urls = tuple(part.strip() for part in str(value).split(";") if part.strip())
    if not urls or any(not url.startswith("https://") for url in urls):
        raise ValueError(f"{field} requires one or more HTTPS URLs")
    return urls


def load_trustee_career_cohort(path: str | Path) -> list[TrusteeCareerCohortRow]:
    """Load the frozen roster while preserving blank identity hypotheses as null."""

    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COHORT_COLUMNS:
            raise ValueError(
                "trustee career cohort columns must be exactly: " + ", ".join(COHORT_COLUMNS)
            )
        rows: list[TrusteeCareerCohortRow] = []
        for row in reader:
            try:
                source_order = int(_required(row["source_order"], "source_order"))
            except ValueError as exc:
                raise ValueError("source_order must be a positive integer") from exc
            if source_order < 1:
                raise ValueError("source_order must be a positive integer")
            rows.append(
                TrusteeCareerCohortRow(
                    cohort_id=_required(row["cohort_id"], "cohort_id"),
                    subject_candidacy_id=_required(
                        row["subject_candidacy_id"], "subject_candidacy_id"
                    ),
                    certified_name=_required(row["certified_name"], "certified_name"),
                    certified_name_raw=_required(row["certified_name_raw"], "certified_name_raw"),
                    represented_body=_required(row["represented_body"], "represented_body"),
                    official_district_id=_required(
                        row["official_district_id"], "official_district_id"
                    ),
                    contest_id=_required(row["contest_id"], "contest_id"),
                    source_order=source_order,
                    current_person_id=_optional(row["current_person_id"]),
                    proposed_target_person_id=_optional(row["proposed_target_person_id"]),
                    source_release=_required(row["source_release"], "source_release"),
                    source_commit=_required(row["source_commit"], "source_commit"),
                )
            )
        return rows


def _current_trustees(results: pd.DataFrame) -> pd.DataFrame:
    required = {
        "candidacy_id",
        "election_date",
        "office_type",
        "represented_body",
        "official_district_id",
        "contest_id",
        "candidate_name",
        "candidate_name_raw",
    }
    missing = sorted(required - set(results.columns))
    if missing:
        raise ValueError(f"results is missing trustee cohort fields: {', '.join(missing)}")
    return results.loc[
        results["election_date"].astype("string").eq(CURRENT_ELECTION_DATE)
        & results["office_type"].eq("trustee")
        & results["represented_body"].isin(EXPECTED_CONTEST_COUNTS)
    ].copy()


def validate_trustee_career_cohort(
    cohort: list[TrusteeCareerCohortRow], results: pd.DataFrame
) -> None:
    """Require the frozen cohort to equal, rather than approximate, the Clerk field."""

    subject_ids = [row.subject_candidacy_id for row in cohort]
    if len(subject_ids) != len(set(subject_ids)):
        raise ValueError("duplicate subject_candidacy_id in trustee career cohort")
    if any(row.cohort_id != COHORT_ID for row in cohort):
        raise ValueError(f"trustee career cohort_id must be {COHORT_ID}")

    current = _current_trustees(results)
    if set(subject_ids) != set(current["candidacy_id"].astype(str)):
        raise ValueError("cohort must equal the complete certified trustee field")
    if current["contest_id"].nunique() != sum(EXPECTED_CONTEST_COUNTS.values()):
        raise ValueError("certified trustee field must contain all 29 contests")
    actual_contests = current.groupby("represented_body")["contest_id"].nunique().to_dict()
    if actual_contests != EXPECTED_CONTEST_COUNTS:
        raise ValueError(f"unexpected trustee board contest coverage: {actual_contests}")

    by_id = current.set_index("candidacy_id")
    seen_orders: set[tuple[str, int]] = set()
    for row in cohort:
        source = by_id.loc[row.subject_candidacy_id]
        expected = {
            "certified_name": str(source["candidate_name"]),
            "certified_name_raw": str(source["candidate_name_raw"]),
            "represented_body": str(source["represented_body"]),
            "official_district_id": str(source["official_district_id"]),
            "contest_id": str(source["contest_id"]),
        }
        for field, value in expected.items():
            if str(getattr(row, field)) != value:
                raise ValueError(f"{field} changed for {row.subject_candidacy_id}")
        order_key = (row.contest_id, row.source_order)
        if order_key in seen_orders:
            raise ValueError(f"duplicate source_order within contest: {order_key}")
        seen_orders.add(order_key)


def _require_exact_columns(table: pd.DataFrame, columns: list[str], label: str) -> None:
    if table.columns.tolist() != columns:
        raise ValueError(f"{label} columns must be exactly: {', '.join(columns)}")


def is_toronto_occurrence(row: pd.Series) -> bool:
    """Return whether a canonical occurrence is inside the public trustee-history scope."""

    body = str(row["represented_body"])
    if body in _TORONTO_MUNICIPAL_BODIES:
        return True
    return body in _CANADA_WIDE_BODIES and str(row["district_name"]) in _TORONTO_RIDING_NAMES


def validate_trustee_career_contracts(
    cohort: list[TrusteeCareerCohortRow],
    reviews: pd.DataFrame,
    decisions: pd.DataFrame,
    results: pd.DataFrame,
    *,
    repository_root: str | Path | None = None,
    require_complete: bool = False,
) -> None:
    """Validate candidate-complete research and occurrence-level adjudications."""

    _require_exact_columns(reviews, REVIEW_COLUMNS, "trustee career reviews")
    _require_exact_columns(decisions, DECISION_COLUMNS, "trustee career decisions")
    validate_trustee_career_cohort(cohort, results)
    cohort_by_id = {row.subject_candidacy_id: row for row in cohort}
    cohort_ids = set(cohort_by_id)

    if reviews["subject_candidacy_id"].duplicated().any():
        raise ValueError("duplicate trustee candidate review")
    if decisions["decision_id"].duplicated().any():
        raise ValueError("duplicate trustee career decision_id")
    if decisions.duplicated(["subject_candidacy_id", "prior_candidacy_id"]).any():
        raise ValueError("duplicate trustee candidate occurrence decision")

    for label, table in (("review", reviews), ("decision", decisions)):
        outside = sorted(set(table["subject_candidacy_id"]) - cohort_ids)
        if outside:
            raise ValueError(f"{label} references candidate outside cohort: {outside[0]}")
        if not table["cohort_id"].eq(COHORT_ID).all():
            raise ValueError(f"{label} cohort_id must be {COHORT_ID}")

    invalid_status = sorted(set(reviews["review_status"]) - REVIEW_STATUSES)
    if invalid_status:
        raise ValueError(f"invalid trustee review_status: {invalid_status[0]}")
    invalid_decision = sorted(set(decisions["decision"]) - DECISIONS)
    if invalid_decision:
        raise ValueError(f"invalid trustee occurrence decision: {invalid_decision[0]}")

    for row in reviews.itertuples(index=False):
        cohort_row = cohort_by_id[row.subject_candidacy_id]
        if row.certified_name != cohort_row.certified_name:
            raise ValueError(f"certified_name changed for {row.subject_candidacy_id}")
        _urls(row.evidence_urls, field="candidate review")
        if not row.primary_rationale.strip():
            raise ValueError("candidate review requires primary_rationale")
        if repository_root is not None:
            root = Path(repository_root).resolve()
            for agent, report_path in (
                ("luna", row.luna_report_path),
                ("terra", row.terra_report_path),
            ):
                expected = (
                    f"docs/research/trustee-career/2026/{row.subject_candidacy_id}-{agent}.md"
                )
                if report_path != expected:
                    raise ValueError(
                        f"{agent} report path for {row.subject_candidacy_id} must be {expected}"
                    )
                resolved = (root / report_path).resolve()
                if not resolved.is_relative_to(root) or not resolved.is_file():
                    raise ValueError(
                        f"missing {agent} report for {row.subject_candidacy_id}: {report_path}"
                    )
        subject = decisions.loc[decisions["subject_candidacy_id"].eq(row.subject_candidacy_id)]
        counts = {
            "confirmed_count": int(subject["decision"].eq("confirm").sum()),
            "held_count": int(subject["decision"].eq("hold").sum()),
            "split_count": int(subject["decision"].eq("split").sum()),
            "rejected_count": int(subject["decision"].eq("reject").sum()),
        }
        for field, actual in counts.items():
            if int(getattr(row, field)) != actual:
                raise ValueError(f"{row.subject_candidacy_id} {field} must be {actual}")
        expected_status = "reviewed_with_limitations" if counts["held_count"] else "reviewed"
        if row.review_status != expected_status:
            raise ValueError(f"{row.subject_candidacy_id} review_status must be {expected_status}")
        if row.review_status == "reviewed_with_limitations" and not row.limitations.strip():
            raise ValueError(
                f"reviewed_with_limitations requires limitations for {row.subject_candidacy_id}"
            )

    by_candidacy = results.set_index("candidacy_id", drop=False)
    for row in decisions.itertuples(index=False):
        if row.prior_candidacy_id == row.subject_candidacy_id:
            raise ValueError("trustee decision cannot target the subject candidacy itself")
        if row.prior_candidacy_id not in by_candidacy.index:
            raise ValueError(f"unknown prior candidacy: {row.prior_candidacy_id}")
        prior = by_candidacy.loc[row.prior_candidacy_id]
        date = str(prior["election_date"])
        if not MINIMUM_HISTORY_DATE <= date < CURRENT_ELECTION_DATE or not is_toronto_occurrence(
            prior
        ):
            raise ValueError(
                "trustee history decisions require a Toronto election on or after 2003"
            )
        canonical_fields = {
            "observed_ballot_name": str(prior["candidate_name"]),
            "election_date": date,
            "represented_body": str(prior["represented_body"]),
            "office_type": str(prior["office_type"]),
            "district_name": str(prior["district_name"]),
        }
        for field, value in canonical_fields.items():
            if str(getattr(row, field)) != value:
                raise ValueError(f"trustee decision {field} must match canonical occurrence")
        _urls(row.evidence_urls, field="trustee career decision")
        if not row.rationale.strip() or not row.identity_bridge.strip():
            raise ValueError("trustee career decision requires bridge and rationale")
        if row.decision == "confirm" and "https://" not in row.evidence_urls:
            raise ValueError("confirmed trustee decision requires identity evidence")

    if require_complete and set(reviews["subject_candidacy_id"]) != cohort_ids:
        missing = sorted(cohort_ids - set(reviews["subject_candidacy_id"]))
        raise ValueError(f"trustee career review is incomplete: {missing}")


def validate_trustee_sol_reviews(
    sol_reviews: pd.DataFrame,
    decisions: pd.DataFrame,
    *,
    repository_root: str | Path | None = None,
) -> None:
    """Validate the complete third-pass audit of Terra's original holds."""

    _require_exact_columns(sol_reviews, SOL_REVIEW_COLUMNS, "trustee Sol reviews")
    if len(sol_reviews) != 60:
        raise ValueError(
            f"trustee Sol review must contain exactly 60 rows, found {len(sol_reviews)}"
        )
    if sol_reviews["decision_id"].duplicated().any():
        raise ValueError("duplicate trustee Sol decision_id")
    if sol_reviews.duplicated(["subject_candidacy_id", "prior_candidacy_id"]).any():
        raise ValueError("duplicate trustee Sol occurrence review")
    if not sol_reviews["cohort_id"].eq(COHORT_ID).all():
        raise ValueError(f"trustee Sol cohort_id must be {COHORT_ID}")
    if not sol_reviews["review_date"].eq(SOL_REVIEW_DATE).all():
        raise ValueError(f"trustee Sol review_date must be {SOL_REVIEW_DATE}")
    if not sol_reviews["model"].eq(SOL_MODEL).all():
        raise ValueError(f"trustee Sol model must be {SOL_MODEL}")
    invalid = sorted(set(sol_reviews["sol_disposition"]) - SOL_DISPOSITIONS)
    if invalid:
        raise ValueError(f"invalid trustee Sol disposition: {invalid[0]}")

    canonical = decisions.set_index("decision_id", drop=False)
    report_paths: set[str] = set()
    for row in sol_reviews.itertuples(index=False):
        expected_decision_id = stable_id(
            "trd", COHORT_ID, row.subject_candidacy_id, row.prior_candidacy_id
        )
        if row.decision_id != expected_decision_id:
            raise ValueError("trustee Sol decision_id does not match its occurrence pair")
        if row.decision_id not in canonical.index:
            raise ValueError(f"trustee Sol review has no canonical decision: {row.decision_id}")
        decision = canonical.loc[row.decision_id]
        for field in ("subject_candidacy_id", "prior_candidacy_id"):
            if str(decision[field]) != str(getattr(row, field)):
                raise ValueError(f"trustee Sol {field} does not match canonical decision")
        expected_decision = SOL_TO_CANONICAL[row.sol_disposition]
        if str(decision["decision"]) != expected_decision:
            raise ValueError(
                f"trustee Sol disposition {row.sol_disposition} requires {expected_decision}"
            )
        _urls(row.evidence_urls, field="trustee Sol review")
        if not row.identity_bridge.strip() or not row.rationale.strip():
            raise ValueError("trustee Sol review requires bridge and rationale")

        expected_report = f"docs/research/trustee-career/2026/{row.subject_candidacy_id}-sol.md"
        if row.sol_report_path != expected_report:
            raise ValueError(
                f"Sol report path for {row.subject_candidacy_id} must be {expected_report}"
            )
        if row.sol_batch_path not in {
            f"docs/research/trustee-career/2026/sol-review-batch-{batch}.csv"
            for batch in ("a", "b", "c")
        }:
            raise ValueError("trustee Sol review references an unexpected batch path")
        report_paths.add(row.sol_report_path)
        if repository_root is not None:
            root = Path(repository_root).resolve()
            for label, relative_path in (
                ("report", row.sol_report_path),
                ("batch", row.sol_batch_path),
            ):
                resolved = (root / relative_path).resolve()
                if not resolved.is_relative_to(root) or not resolved.is_file():
                    raise ValueError(f"missing trustee Sol {label}: {relative_path}")
    if len(report_paths) != 33:
        raise ValueError(
            f"trustee Sol review must cover exactly 33 candidates, found {len(report_paths)}"
        )


def _load_contracts(
    reference_dir: str | Path, results: pd.DataFrame
) -> tuple[list[TrusteeCareerCohortRow], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    reference = Path(reference_dir)
    cohort = load_trustee_career_cohort(reference / "trustee_career_cohort_2026.csv")
    reviews = pd.read_csv(
        reference / "trustee_career_reviews.csv", dtype="string", keep_default_na=False
    )
    decisions = pd.read_csv(
        reference / "trustee_career_decisions.csv", dtype="string", keep_default_na=False
    )
    sol_reviews = pd.read_csv(
        reference / "trustee_career_sol_reviews.csv", dtype="string", keep_default_na=False
    )
    validate_trustee_career_contracts(
        cohort,
        reviews,
        decisions,
        results,
        repository_root=reference.parent.parent,
        require_complete=True,
    )
    validate_trustee_sol_reviews(
        sol_reviews,
        decisions,
        repository_root=reference.parent.parent,
    )
    return cohort, reviews, decisions, sol_reviews


def build_trustee_career_identity_assertions(
    reference_dir: str | Path, results: pd.DataFrame
) -> tuple[CuratedIdentityAssertion, ...]:
    """Turn only confirmed reviewed occurrences into persistent Person assertions."""

    cohort, reviews, decisions, _sol_reviews = _load_contracts(reference_dir, results)
    cohort_by_id = {row.subject_candidacy_id: row for row in cohort}
    reviews_by_id = reviews.set_index("subject_candidacy_id")
    by_candidacy = results.set_index("candidacy_id")
    assertions: list[CuratedIdentityAssertion] = []
    confirmed = decisions.loc[decisions["decision"].eq("confirm")]
    for subject_id, subject in confirmed.groupby("subject_candidacy_id", sort=True):
        cohort_row = cohort_by_id[subject_id]
        candidacy_ids = [subject_id, *subject["prior_candidacy_id"].tolist()]
        occurrences = tuple(
            CandidacyLocator(
                event_id=str(by_candidacy.loc[candidacy_id, "event_id"]),
                represented_body=str(by_candidacy.loc[candidacy_id, "represented_body"]),
                office_type=str(by_candidacy.loc[candidacy_id, "office_type"]),
                candidate_name=str(by_candidacy.loc[candidacy_id, "candidate_name"]),
                candidacy_id=candidacy_id,
            )
            for candidacy_id in dict.fromkeys(candidacy_ids)
        )
        reviewed_target = _optional(reviews_by_id.loc[subject_id, "resulting_person_id"])
        target = (
            reviewed_target or cohort_row.proposed_target_person_id or cohort_row.current_person_id
        )
        registry_ids = (target,) if target else ()
        evidence_urls = tuple(
            dict.fromkeys(
                url
                for value in subject["evidence_urls"]
                for url in _urls(value, field="trustee career decision")
            )
        )
        assertions.append(
            CuratedIdentityAssertion(
                assertion_id=stable_id("ast", COHORT_ID, subject_id),
                preferred_name=cohort_row.certified_name,
                occurrences=occurrences,
                evidence_urls=evidence_urls,
                rationale=str(reviews_by_id.loc[subject_id, "primary_rationale"]),
                registry_person_ids=registry_ids,
                canonical_person_id=target,
            )
        )
    return tuple(assertions)


def build_trustee_hold_decisions(reference_dir: str | Path) -> pd.DataFrame:
    """Close exact-name proposals whose reviewed historical lead remains held."""

    reference = Path(reference_dir)
    cohort = load_trustee_career_cohort(reference / "trustee_career_cohort_2026.csv")
    decisions = pd.read_csv(
        reference / "trustee_career_decisions.csv", dtype="string", keep_default_na=False
    )
    cohort_by_id = {row.subject_candidacy_id: row for row in cohort}
    rows: list[dict[str, str]] = []
    held = decisions.loc[decisions["decision"].eq("hold")]
    for subject_id, subject in held.groupby("subject_candidacy_id", sort=True):
        subject_decisions = decisions.loc[decisions["subject_candidacy_id"].eq(subject_id)]
        if subject_decisions["decision"].eq("confirm").any():
            # A confirmed occurrence supplies the current candidate's reviewed
            # identity.  A different held occurrence must not unpublish it.
            continue
        cohort_row = cohort_by_id[subject_id]
        target = cohort_row.proposed_target_person_id
        if target is None:
            continue
        rows.append(
            {
                "candidacy_id": subject_id,
                "target_person_id": target,
                "decision": "unresolved",
                "confidence": "low",
                "rationale": " ".join(dict.fromkeys(subject["rationale"].tolist())),
                "evidence_urls": ";".join(
                    dict.fromkeys(
                        url
                        for value in subject["evidence_urls"]
                        for url in _urls(value, field="trustee career decision")
                    )
                ),
                "reviewer": "trustee-career-review-2026",
            }
        )
    return pd.DataFrame(rows, columns=IDENTITY_REVIEW_DECISION_COLUMNS, dtype="string")


def reconcile_trustee_identity_decisions(
    identity_decisions: pd.DataFrame,
    reference_dir: str | Path,
    assertions: tuple[CuratedIdentityAssertion, ...],
) -> pd.DataFrame:
    """Supersede older proposals with the completed trustee career review."""

    asserted_candidacies = {
        occurrence.candidacy_id
        for assertion in assertions
        for occurrence in assertion.occurrences
        if occurrence.candidacy_id is not None
    }
    retained = identity_decisions.loc[
        ~identity_decisions["candidacy_id"].isin(asserted_candidacies)
    ].copy()
    return pd.concat(
        [retained, build_trustee_hold_decisions(reference_dir)],
        ignore_index=True,
    )
