"""Audited inputs for the default Toronto endorsement companion tables.

The public endorsement assembler deliberately knows nothing about Toronto-specific
research.  This module is the checked-in curation boundary: it reads the approved
panel and source assertions, resolves only immutable Candidacy/Contest identifiers,
and builds open-world coverage cells for every in-scope Contest.

Curated locators fail closed.  A source row must match its expected stable IDs and
its recorded election date, office, district, and candidate display name.  There is
no fuzzy or same-name fallback.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from .schema import stable_id

REFERENCE = Path("data/reference")
ENDORSER_PANEL_FILENAME = "endorser_panel_curations.csv"
ENDORSEMENT_ASSERTIONS_FILENAME = "endorsement_assertion_curations.csv"
ENDORSEMENT_COVERAGE_FILENAME = "endorsement_coverage_curations.csv"

# These hashes make the three default inputs tamper-evident even before the release
# manifest starts publishing them as sources.  Custom fixture directories are
# validated structurally but intentionally are not compared with these hashes.
_DEFAULT_REFERENCE_SHA256 = {
    ENDORSER_PANEL_FILENAME: "43787c2056423e147749e98860318a52ee7201e1c51ba18ec94ec9f169ce0e66",
    ENDORSEMENT_ASSERTIONS_FILENAME: (
        "e0638128bebd5909750952d52afe93dad78dd77eb2822508136a4f83e4b150a4"
    ),
    ENDORSEMENT_COVERAGE_FILENAME: (
        "03f655cad5cb6a1baa4914c9f9af265561d8b6069d808e6974549113ef03ce28"
    ),
}

_TARGET_BODY = "toronto_city_council"
_TARGET_OFFICES = frozenset({"mayor", "councillor"})
_REVIEW_STATES = frozenset({"confirmed", "unresolved"})
_DATE_PRECISIONS = frozenset({"day", "month", "year", "unknown"})
_WHITESPACE = re.compile(r"\s+")

_PANEL_COLUMNS = (
    "endorser_key",
    "canonical_name",
    "endorser_type",
    "person_id",
    "expected_person_name",
    "is_panel_endorser",
    "panel_basis",
    "eligibility_start_date",
    "mayor_applicable",
    "councillor_applicable",
    "evidence_url",
)

_ASSERTION_CURATION_COLUMNS = (
    "curation_key",
    "endorser_key",
    "expected_contest_id",
    "expected_candidacy_id",
    "election_date",
    "office_type",
    "official_district_id",
    "expected_candidate_name",
    "asserted_candidate_name",
    "review_state",
    "endorsement_kind",
    "announcement_date",
    "date_precision",
    "source_type",
    "source_url",
    "secondary_source_url",
)

_COVERAGE_CURATION_COLUMNS = (
    "curation_key",
    "endorser_key",
    "expected_event_id",
    "election_date",
    "office_type",
    "official_district_id",
    "coverage_state",
    "assessed_through",
    "coverage_basis",
    "evidence_url",
    "verification_report_path",
    "search_certificate_path",
)

_CURATABLE_COVERAGE_STATES = frozenset(
    {
        "partially_searched",
        "searched_no_endorsement_found",
        "comprehensive_source_found",
        "source_unavailable",
    }
)


@dataclass(frozen=True)
class EndorsementInputs:
    """Toronto-specific inputs accepted by ``assemble_endorsement_tables``."""

    endorsers: pd.DataFrame
    assertions: pd.DataFrame
    coverage: pd.DataFrame


@dataclass(frozen=True)
class _ContestMeta:
    contest_id: str
    event_id: str
    election_date: date
    office_type: str
    official_district_id: str


def _clean_text(value: object) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        return ""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", str(value))).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_reference_csv(
    reference_dir: Path,
    filename: str,
    columns: tuple[str, ...],
) -> pd.DataFrame:
    path = reference_dir / filename
    if not path.is_file():
        raise ValueError(f"endorsement curation source is missing: {path}")
    if reference_dir.resolve() == REFERENCE.resolve():
        expected = _DEFAULT_REFERENCE_SHA256[filename]
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(
                f"endorsement curation source checksum changed for {path}: "
                f"expected {expected}, got {actual}"
            )
    frame = pd.read_csv(path, dtype="string", keep_default_na=True)
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{filename} is missing columns: {', '.join(missing)}")
    return frame.loc[:, columns].copy()


def _required_text(frame: pd.DataFrame, columns: tuple[str, ...], table: str) -> None:
    for column in columns:
        frame[column] = frame[column].map(_clean_text).astype("string")
        if frame[column].isna().any() or frame[column].eq("").any():
            raise ValueError(f"{table}.{column} must be non-null and non-blank")


def _optional_text(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    for column in columns:
        cleaned = frame[column].map(_clean_text)
        frame[column] = cleaned.mask(cleaned.eq(""), pd.NA).astype("string")


def _iso_date(value: object, *, label: str) -> date:
    clean = _clean_text(value)
    try:
        parsed = date.fromisoformat(clean)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO date: {clean!r}") from exc
    if parsed.isoformat() != clean:
        raise ValueError(f"{label} must be an ISO date: {clean!r}")
    return parsed


def _boolean(value: object, *, label: str) -> bool:
    clean = _clean_text(value).casefold()
    if clean == "true":
        return True
    if clean == "false":
        return False
    raise ValueError(f"{label} must be true or false")


def _prepare_panel(
    raw: pd.DataFrame,
    people: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, dict[str, object]]]:
    panel = raw.copy()
    _required_text(
        panel,
        (
            "endorser_key",
            "canonical_name",
            "endorser_type",
            "is_panel_endorser",
            "panel_basis",
            "eligibility_start_date",
            "mayor_applicable",
            "councillor_applicable",
            "evidence_url",
        ),
        "endorser_panel_curations",
    )
    _optional_text(panel, ("person_id", "expected_person_name"))
    if panel["endorser_key"].duplicated().any():
        raise ValueError("endorser_panel_curations.endorser_key must be unique")
    if panel["canonical_name"].duplicated().any():
        raise ValueError("endorser_panel_curations.canonical_name must be unique")
    if (~panel["evidence_url"].str.startswith("https://")).any():
        raise ValueError("endorser_panel_curations.evidence_url must use HTTPS")

    people_required = {"person_id", "preferred_name"}
    missing_people = sorted(people_required - set(people.columns))
    if missing_people:
        raise ValueError(f"people is missing endorsement columns: {', '.join(missing_people)}")
    person_dimension = people.copy()
    _required_text(person_dimension, ("person_id", "preferred_name"), "people")
    if person_dimension["person_id"].duplicated().any():
        raise ValueError("people.person_id must be unique")

    records: list[dict[str, object]] = []
    rules: dict[str, dict[str, object]] = {}
    for row in panel.itertuples(index=False):
        key = str(row.endorser_key)
        endorser_type = str(row.endorser_type)
        if endorser_type not in {"person", "organization", "editorial_board"}:
            raise ValueError(f"unknown Endorser type for {key!r}: {endorser_type!r}")
        person_id = row.person_id
        expected_person_name = row.expected_person_name
        if endorser_type == "person":
            if pd.isna(person_id) or pd.isna(expected_person_name):
                raise ValueError(f"person Endorser {key!r} requires an exact Person locator")
            matches = person_dimension["person_id"].eq(person_id)
            if int(matches.sum()) != 1:
                raise ValueError(
                    f"person Endorser {key!r} expected Person {person_id!r}; "
                    f"matched {int(matches.sum())} rows"
                )
            actual_name = str(person_dimension.loc[matches, "preferred_name"].iloc[0])
            if actual_name != expected_person_name:
                raise ValueError(
                    f"person Endorser {key!r} expected name {expected_person_name!r}, "
                    f"got {actual_name!r}"
                )
            if "identity_status" in person_dimension.columns:
                status = _clean_text(person_dimension.loc[matches, "identity_status"].iloc[0])
                if status != "active":
                    raise ValueError(f"person Endorser {key!r} is not an active Person")
        elif pd.notna(person_id) or pd.notna(expected_person_name):
            raise ValueError(f"non-person Endorser {key!r} cannot carry a Person locator")

        eligibility_start = _iso_date(
            row.eligibility_start_date,
            label=f"endorser_panel_curations[{key}].eligibility_start_date",
        )
        mayor_applicable = _boolean(
            row.mayor_applicable,
            label=f"endorser_panel_curations[{key}].mayor_applicable",
        )
        councillor_applicable = _boolean(
            row.councillor_applicable,
            label=f"endorser_panel_curations[{key}].councillor_applicable",
        )
        is_panel = _boolean(
            row.is_panel_endorser,
            label=f"endorser_panel_curations[{key}].is_panel_endorser",
        )
        if is_panel and (not mayor_applicable or not councillor_applicable):
            raise ValueError(
                f"default panel Endorser {key!r} must apply to both Mayor and City Councillor"
            )
        if not mayor_applicable and not councillor_applicable:
            raise ValueError(f"default Endorser {key!r} must apply to at least one office")
        endorser_id = stable_id("edr", "curated_endorser", key)
        records.append(
            {
                "endorser_id": endorser_id,
                "canonical_name": row.canonical_name,
                "endorser_type": endorser_type,
                "person_id": person_id,
                "is_panel_endorser": is_panel,
                "panel_basis": row.panel_basis,
                "eligibility_start_date": eligibility_start.isoformat(),
                "mayor_applicable": mayor_applicable,
                "councillor_applicable": councillor_applicable,
                "panel_evidence_url": row.evidence_url,
            }
        )
        rules[key] = {
            "endorser_id": endorser_id,
            "is_panel_endorser": is_panel,
            "eligibility_start_date": eligibility_start,
            "mayor_applicable": mayor_applicable,
            "councillor_applicable": councillor_applicable,
        }

    endorsers = (
        pd.DataFrame(records).sort_values("endorser_id", kind="stable").reset_index(drop=True)
    )
    for column in ("endorser_id", "canonical_name", "endorser_type", "person_id"):
        endorsers[column] = endorsers[column].astype("string")
    return endorsers, rules


def _prepare_dimensions(
    election_results: pd.DataFrame,
    contests: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, _ContestMeta]]:
    result_required = {
        "candidacy_id",
        "contest_id",
        "election_date",
        "represented_body",
        "office_type",
        "official_district_id",
        "candidate_name",
    }
    missing_results = sorted(result_required - set(election_results.columns))
    if missing_results:
        raise ValueError(
            f"election_results is missing endorsement columns: {', '.join(missing_results)}"
        )
    contest_required = {"contest_id", "event_id", "represented_body", "office_type"}
    missing_contests = sorted(contest_required - set(contests.columns))
    if missing_contests:
        raise ValueError(f"contests is missing endorsement columns: {', '.join(missing_contests)}")

    results = election_results.copy()
    for column in result_required:
        results[column] = results[column].map(_clean_text).astype("string")
        if results[column].isna().any() or results[column].eq("").any():
            raise ValueError(f"election_results.{column} must be non-null and non-blank")
    if results["candidacy_id"].duplicated().any():
        raise ValueError("election_results.candidacy_id must be unique")

    contest_dimension = contests.copy()
    _required_text(
        contest_dimension,
        ("contest_id", "event_id", "represented_body", "office_type"),
        "contests",
    )
    if contest_dimension["contest_id"].duplicated().any():
        raise ValueError("contests.contest_id must be unique")
    target_contests = contest_dimension.loc[
        contest_dimension["represented_body"].eq(_TARGET_BODY)
        & contest_dimension["office_type"].isin(_TARGET_OFFICES)
    ].copy()

    target_results = results.loc[results["contest_id"].isin(target_contests["contest_id"])]
    meta: dict[str, _ContestMeta] = {}
    for contest in target_contests.itertuples(index=False):
        rows = target_results.loc[target_results["contest_id"].eq(contest.contest_id)]
        if rows.empty:
            raise ValueError(f"target Contest {contest.contest_id!r} has no Candidacy rows")
        for column in (
            "election_date",
            "represented_body",
            "office_type",
            "official_district_id",
        ):
            if rows[column].nunique(dropna=False) != 1:
                raise ValueError(f"target Contest {contest.contest_id!r} has inconsistent {column}")
        body = str(rows["represented_body"].iloc[0])
        office = str(rows["office_type"].iloc[0])
        if body != _TARGET_BODY or office != contest.office_type:
            raise ValueError(
                f"target Contest {contest.contest_id!r} disagrees with election_results"
            )
        meta[str(contest.contest_id)] = _ContestMeta(
            contest_id=str(contest.contest_id),
            event_id=str(contest.event_id),
            election_date=_iso_date(
                rows["election_date"].iloc[0],
                label=f"election_results[{contest.contest_id}].election_date",
            ),
            office_type=office,
            official_district_id=str(rows["official_district_id"].iloc[0]),
        )
    return results, meta


def _validate_assertion_curations(
    curations: pd.DataFrame,
    endorser_rules: dict[str, dict[str, object]],
) -> pd.DataFrame:
    out = curations.copy()
    _required_text(
        out,
        (
            "curation_key",
            "endorser_key",
            "expected_contest_id",
            "election_date",
            "office_type",
            "official_district_id",
            "asserted_candidate_name",
            "review_state",
            "endorsement_kind",
            "date_precision",
            "source_type",
            "source_url",
        ),
        "endorsement_assertion_curations",
    )
    _optional_text(
        out,
        (
            "expected_candidacy_id",
            "expected_candidate_name",
            "announcement_date",
            "secondary_source_url",
        ),
    )
    if out["curation_key"].duplicated().any():
        raise ValueError("endorsement_assertion_curations.curation_key must be unique")
    unknown_endorsers = ~out["endorser_key"].isin(endorser_rules)
    if unknown_endorsers.any():
        key = out.loc[unknown_endorsers, "endorser_key"].iloc[0]
        raise ValueError(f"unknown curated Endorser key: {key!r}")
    invalid_review = ~out["review_state"].isin(_REVIEW_STATES)
    if invalid_review.any():
        state = out.loc[invalid_review, "review_state"].iloc[0]
        raise ValueError(f"unsupported curated review_state: {state!r}")
    invalid_precision = ~out["date_precision"].isin(_DATE_PRECISIONS)
    if invalid_precision.any():
        precision = out.loc[invalid_precision, "date_precision"].iloc[0]
        raise ValueError(f"unsupported curated date_precision: {precision!r}")
    if (~out["office_type"].isin(_TARGET_OFFICES)).any():
        raise ValueError("curated endorsements may target only Mayor or City Councillor")
    if (~out["source_url"].str.startswith("https://")).any():
        raise ValueError("curated source_url must use HTTPS")
    secondary = out["secondary_source_url"].dropna()
    if (~secondary.str.startswith("https://")).any():
        raise ValueError("curated secondary_source_url must use HTTPS")

    confirmed = out["review_state"].eq("confirmed")
    confirmed_missing = confirmed & (
        out["expected_candidacy_id"].isna() | out["expected_candidate_name"].isna()
    )
    if confirmed_missing.any():
        raise ValueError("confirmed curated assertions require an exact Candidacy locator")
    unresolved_has_target = ~confirmed & out["expected_candidacy_id"].notna()
    if unresolved_has_target.any():
        raise ValueError("unresolved curated assertions must not invent a Candidacy locator")
    duplicate_edges = out.loc[confirmed].duplicated(
        ["endorser_key", "expected_candidacy_id"], keep=False
    )
    if duplicate_edges.any():
        raise ValueError("curated source contains duplicate Endorser/Candidacy assertions")

    for row in out.itertuples(index=False):
        election_date = _iso_date(
            row.election_date,
            label=f"endorsement_assertion_curations[{row.curation_key}].election_date",
        )
        if pd.notna(row.announcement_date):
            announced = _iso_date(
                row.announcement_date,
                label=f"endorsement_assertion_curations[{row.curation_key}].announcement_date",
            )
            if announced > election_date:
                raise ValueError(
                    f"curated assertion {row.curation_key!r} was published after its election"
                )
        rule = endorser_rules[str(row.endorser_key)]
        if election_date < rule["eligibility_start_date"]:
            raise ValueError(f"curated assertion {row.curation_key!r} predates eligibility")
        if not bool(rule[f"{row.office_type}_applicable"]):
            raise ValueError(
                f"curated assertion {row.curation_key!r} targets an inapplicable office"
            )
    return out


def _build_assertions(
    curations: pd.DataFrame,
    results: pd.DataFrame,
    contest_meta: dict[str, _ContestMeta],
    endorser_rules: dict[str, dict[str, object]],
) -> pd.DataFrame:
    by_candidacy = results.set_index("candidacy_id", drop=False)
    rows: list[dict[str, object]] = []
    for curation in curations.itertuples(index=False):
        contest_id = str(curation.expected_contest_id)
        if contest_id not in contest_meta:
            raise ValueError(
                f"curated assertion {curation.curation_key!r} expected unknown target "
                f"Contest {contest_id!r}"
            )
        meta = contest_meta[contest_id]
        expected_meta = (
            _iso_date(
                curation.election_date,
                label=f"endorsement_assertion_curations[{curation.curation_key}].election_date",
            ),
            str(curation.office_type),
            str(curation.official_district_id),
        )
        actual_meta = (meta.election_date, meta.office_type, meta.official_district_id)
        if actual_meta != expected_meta:
            raise ValueError(
                f"curated assertion {curation.curation_key!r} Contest locator changed: "
                f"expected {expected_meta!r}, got {actual_meta!r}"
            )

        candidacy_id: object = pd.NA
        if curation.review_state == "confirmed":
            expected_candidacy_id = str(curation.expected_candidacy_id)
            if expected_candidacy_id not in by_candidacy.index:
                raise ValueError(
                    f"curated assertion {curation.curation_key!r} expected unknown Candidacy "
                    f"{expected_candidacy_id!r}"
                )
            candidate = by_candidacy.loc[expected_candidacy_id]
            if isinstance(candidate, pd.DataFrame):
                raise ValueError(
                    f"curated assertion {curation.curation_key!r} matched multiple Candidacies"
                )
            actual = (
                str(candidate["contest_id"]),
                _iso_date(
                    candidate["election_date"],
                    label=f"election_results[{expected_candidacy_id}].election_date",
                ),
                str(candidate["office_type"]),
                str(candidate["official_district_id"]),
                str(candidate["candidate_name"]),
            )
            expected = (
                contest_id,
                expected_meta[0],
                expected_meta[1],
                expected_meta[2],
                str(curation.expected_candidate_name),
            )
            if actual != expected:
                raise ValueError(
                    f"curated assertion {curation.curation_key!r} Candidacy locator changed: "
                    f"expected {expected!r}, got {actual!r}"
                )
            candidacy_id = expected_candidacy_id

        rows.append(
            {
                "assertion_id": stable_id(
                    "ast", "endorsement_assertion_curation", curation.curation_key
                ),
                "endorser_id": endorser_rules[str(curation.endorser_key)]["endorser_id"],
                "contest_id": contest_id,
                "candidacy_id": candidacy_id,
                "review_state": curation.review_state,
                "endorsement_kind": curation.endorsement_kind,
                "announcement_date": curation.announcement_date,
                "date_precision": curation.date_precision,
                "source_type": curation.source_type,
                "source_url": curation.source_url,
                "secondary_source_url": curation.secondary_source_url,
                "asserted_candidate_name": curation.asserted_candidate_name,
                "curation_key": curation.curation_key,
            }
        )
    assertions = (
        pd.DataFrame(rows).sort_values("assertion_id", kind="stable").reset_index(drop=True)
    )
    for column in assertions.columns:
        if column != "announcement_date":
            assertions[column] = assertions[column].astype("string")
    assertions["announcement_date"] = assertions["announcement_date"].astype("string")
    return assertions


def _resolve_coverage_curations(
    raw_curations: pd.DataFrame,
    contest_meta: dict[str, _ContestMeta],
    endorser_rules: dict[str, dict[str, object]],
) -> dict[tuple[str, str], tuple[str, str, str]]:
    """Resolve audited event/office coverage selectors into unambiguous cells."""

    curations = raw_curations.copy()
    _required_text(
        curations,
        (
            "curation_key",
            "endorser_key",
            "expected_event_id",
            "election_date",
            "office_type",
            "coverage_state",
            "assessed_through",
            "coverage_basis",
            "evidence_url",
            "verification_report_path",
            "search_certificate_path",
        ),
        "endorsement_coverage_curations",
    )
    _optional_text(curations, ("official_district_id",))
    if curations["curation_key"].duplicated().any():
        raise ValueError("endorsement_coverage_curations.curation_key must be unique")
    unknown_endorsers = ~curations["endorser_key"].isin(endorser_rules)
    if unknown_endorsers.any():
        key = curations.loc[unknown_endorsers, "endorser_key"].iloc[0]
        raise ValueError(f"unknown coverage-curation Endorser key: {key!r}")
    if (~curations["office_type"].isin(_TARGET_OFFICES)).any():
        raise ValueError("coverage curations may target only Mayor or City Councillor")
    invalid_state = ~curations["coverage_state"].isin(_CURATABLE_COVERAGE_STATES)
    if invalid_state.any():
        state = curations.loc[invalid_state, "coverage_state"].iloc[0]
        raise ValueError(f"unsupported curated coverage_state: {state!r}")
    if (~curations["evidence_url"].str.startswith("https://")).any():
        raise ValueError("coverage curations.evidence_url must use HTTPS")
    for path_column in ("verification_report_path", "search_certificate_path"):
        missing_reports = ~curations[path_column].map(lambda path: Path(path).is_file())
        if missing_reports.any():
            path = curations.loc[missing_reports, path_column].iloc[0]
            raise ValueError(f"coverage curations.{path_column} is not a checked-in report: {path}")

    resolved: dict[tuple[str, str], tuple[str, str, str]] = {}
    for curation in curations.itertuples(index=False):
        election_date = _iso_date(
            curation.election_date,
            label=f"endorsement_coverage_curations[{curation.curation_key}].election_date",
        )
        assessed_through = _iso_date(
            curation.assessed_through,
            label=f"endorsement_coverage_curations[{curation.curation_key}].assessed_through",
        )
        if assessed_through < election_date:
            raise ValueError(
                f"coverage curation {curation.curation_key!r} was assessed before its election"
            )
        rule = endorser_rules[str(curation.endorser_key)]
        if election_date < rule["eligibility_start_date"]:
            raise ValueError(f"coverage curation {curation.curation_key!r} predates eligibility")
        if not bool(rule[f"{curation.office_type}_applicable"]):
            raise ValueError(
                f"coverage curation {curation.curation_key!r} targets an inapplicable office"
            )

        matches = [
            contest
            for contest in contest_meta.values()
            if contest.election_date == election_date
            and contest.event_id == curation.expected_event_id
            and contest.office_type == curation.office_type
            and (
                pd.isna(curation.official_district_id)
                or contest.official_district_id == curation.official_district_id
            )
        ]
        if not matches:
            raise ValueError(
                f"coverage curation {curation.curation_key!r} did not match a target Contest"
            )
        for contest in matches:
            key = (str(curation.endorser_key), contest.contest_id)
            if key in resolved:
                raise ValueError(
                    "coverage curations overlap for Endorser/Contest "
                    f"{key!r}; curation {curation.curation_key!r} is ambiguous"
                )
            resolved[key] = (
                str(curation.coverage_state),
                str(curation.coverage_basis),
                assessed_through.isoformat(),
            )
    return resolved


def _coverage_state(
    endorser_key: str,
    rule: dict[str, object],
    contest: _ContestMeta,
) -> tuple[str, str]:
    office_applicable = bool(rule[f"{contest.office_type}_applicable"])
    if not office_applicable:
        return "not_applicable", "target office is outside the approved panel applicability"
    if contest.election_date < rule["eligibility_start_date"]:
        return "not_applicable", "Contest predates the Endorser eligibility window"

    # The 2026 event is live.  Every otherwise-applicable cell remains open through
    # polling day regardless of what a one-day search did or did not find.
    if contest.election_date.year == 2026:
        return "partially_searched", "current election searched through 2026-08-21"

    complete_event_office = {
        ("toronto_star_editorial_board", date(2010, 10, 25), "councillor"),
        ("progress_toronto", date(2022, 10, 24), "councillor"),
        ("atu_local_113", date(2022, 10, 24), "councillor"),
        ("john_tory", date(2022, 10, 24), "councillor"),
    }
    explicit_choice = {
        ("toronto_star_editorial_board", date(2003, 11, 10), "mayor", "city"),
        ("toronto_star_editorial_board", date(2010, 10, 25), "mayor", "city"),
        ("toronto_star_editorial_board", date(2018, 10, 22), "mayor", "city"),
        ("toronto_star_editorial_board", date(2022, 10, 24), "mayor", "city"),
        ("toronto_star_editorial_board", date(2023, 6, 26), "mayor", "city"),
        ("toronto_sun_editorial_board", date(2010, 10, 25), "mayor", "city"),
        ("toronto_sun_editorial_board", date(2014, 10, 27), "mayor", "city"),
        ("toronto_sun_editorial_board", date(2018, 10, 22), "mayor", "city"),
        ("toronto_sun_editorial_board", date(2023, 6, 26), "mayor", "city"),
        ("cupe_ontario", date(2010, 10, 25), "mayor", "city"),
        ("cupe_ontario", date(2023, 6, 26), "mayor", "city"),
        ("ett", date(2014, 10, 27), "mayor", "city"),
        ("ett", date(2018, 10, 22), "mayor", "city"),
        ("ett", date(2021, 1, 15), "councillor", "ward-22"),
        ("ett", date(2023, 6, 26), "mayor", "city"),
        ("progress_toronto", date(2023, 6, 26), "mayor", "city"),
        ("progress_toronto", date(2025, 9, 29), "councillor", "ward-25"),
        ("atu_local_113", date(2023, 6, 26), "mayor", "city"),
        ("atu_local_113", date(2023, 11, 30), "councillor", "ward-20"),
    }
    event_office_key = (endorser_key, contest.election_date, contest.office_type)
    choice_key = event_office_key + (contest.official_district_id,)
    if event_office_key in complete_event_office:
        return "comprehensive_source_found", "complete slate source recovered"
    if choice_key in explicit_choice:
        return "comprehensive_source_found", "explicit choice source recovered"

    inaccessible_star_council_dates = {
        date(2006, 11, 13),
        date(2014, 10, 27),
        date(2018, 10, 22),
        date(2022, 10, 24),
    }
    if (
        endorser_key == "toronto_star_editorial_board"
        and contest.office_type == "councillor"
        and contest.election_date in inaccessible_star_council_dates
    ):
        return "source_unavailable", "known Star council source set is inaccessible"
    return "not_searched", "no contest-specific historical search is logged"


def _build_coverage(
    contest_meta: dict[str, _ContestMeta],
    endorser_rules: dict[str, dict[str, object]],
    curated_cells: dict[tuple[str, str], tuple[str, str, str]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for endorser_key, rule in endorser_rules.items():
        if not bool(rule["is_panel_endorser"]):
            continue
        for contest in contest_meta.values():
            coverage_state, basis = _coverage_state(endorser_key, rule, contest)
            # A release-as-of date must not imply that a Contest-specific search
            # happened.  Audited curations and the live 2026 search carry dates;
            # untouched historical cells are explicitly undated.
            assessed_through: object = pd.NA if coverage_state == "not_searched" else "2026-08-21"
            curated = curated_cells.get((endorser_key, contest.contest_id))
            if curated is not None:
                coverage_state, basis, assessed_through = curated
            rows.append(
                {
                    "endorser_id": rule["endorser_id"],
                    "contest_id": contest.contest_id,
                    "coverage_state": coverage_state,
                    "assessed_through": assessed_through,
                    "coverage_basis": basis,
                }
            )
    return (
        pd.DataFrame(rows)
        .sort_values(["endorser_id", "contest_id"], kind="stable")
        .reset_index(drop=True)
    )


def build_default_endorsement_inputs(
    election_results: pd.DataFrame,
    contests: pd.DataFrame,
    people: pd.DataFrame,
    *,
    reference_dir: str | Path = REFERENCE,
) -> EndorsementInputs:
    """Resolve the approved endorsement panel and audited facts against a release.

    The returned frames are inputs to :func:`assemble_endorsement_tables`.  Missing
    sources remain coverage metadata; they never create candidate-level negative
    facts.  The sole target-less assertion is John Tory's supported 2022 Cynthia Lai
    candidacy, which is retained as ``unresolved`` because the result release has no
    Candidacy row to receive it.
    """

    source_dir = Path(reference_dir)
    raw_panel = _read_reference_csv(source_dir, ENDORSER_PANEL_FILENAME, _PANEL_COLUMNS)
    raw_curations = _read_reference_csv(
        source_dir,
        ENDORSEMENT_ASSERTIONS_FILENAME,
        _ASSERTION_CURATION_COLUMNS,
    )
    raw_coverage_curations = _read_reference_csv(
        source_dir,
        ENDORSEMENT_COVERAGE_FILENAME,
        _COVERAGE_CURATION_COLUMNS,
    )
    endorsers, rules = _prepare_panel(raw_panel, people)
    results, contest_meta = _prepare_dimensions(election_results, contests)
    curations = _validate_assertion_curations(raw_curations, rules)
    assertions = _build_assertions(curations, results, contest_meta, rules)
    curated_cells = _resolve_coverage_curations(raw_coverage_curations, contest_meta, rules)
    coverage = _build_coverage(contest_meta, rules, curated_cells)
    return EndorsementInputs(
        endorsers=endorsers,
        assertions=assertions,
        coverage=coverage,
    )
