"""Persistent project ledger for source Candidacy occurrences.

Most election authorities do not publish an immutable candidate identifier.  The
ledger assigns those source occurrences an opaque, deterministic project key once,
then uses the checked-in mapping on every later release.  Candidate names are
matching locators and retained history; they are never identifier components.

An existing Contest is deliberately closed to implicit inventory changes. Name
corrections retain visible history; unsupported additions or retractions fail
closed for explicit curator recovery so a source change cannot silently mint or
erase a public Candidacy ID.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from pathlib import Path

import pandas as pd

from .schema import normalize_adapter_frame, stable_id

LEDGER_COLUMNS = [
    "candidacy_id",
    "source_occurrence_id",
    "identity_basis",
    "event_id",
    "contest_id",
    "represented_body",
    "office_type",
    "boundary_regime",
    "official_district_id",
    "candidate_name_raw",
    "source_authority",
    "source_resource",
    "source_detail",
    "valid_from_release",
    "valid_to_release",
    "change_reason",
]
_RELEASE_DATE_SUFFIX = re.compile(r"(\d{4}-\d{2}-\d{2})$")
_IDENTITY_BASES = {"authority_identifier", "project_ordinal_at_registration"}


@dataclass(frozen=True)
class CandidacyLedgerAssignment:
    """Adapter frames with persistent occurrence keys plus updated ledger history."""

    adapter_frames: list[pd.DataFrame]
    ledger: pd.DataFrame


def empty_candidacy_ledger() -> pd.DataFrame:
    """Return an empty ledger with the canonical persisted schema."""

    return pd.DataFrame(columns=LEDGER_COLUMNS)


def _text(value: object, *, label: str) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        raise ValueError(f"{label} cannot be null")
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"{label} cannot be blank")
    return cleaned


def _clean_ledger(ledger: pd.DataFrame | None) -> pd.DataFrame:
    if ledger is None:
        return empty_candidacy_ledger()
    missing = sorted(set(LEDGER_COLUMNS) - set(ledger.columns))
    if missing:
        raise ValueError(f"Candidacy ledger is missing columns: {', '.join(missing)}")
    out = ledger[LEDGER_COLUMNS].copy()
    for column in LEDGER_COLUMNS:
        out[column] = out[column].astype("string")
    return out


def _release_date(value: object, *, label: str) -> date:
    clean = _text(value, label=label)
    matched = _RELEASE_DATE_SUFFIX.search(clean)
    if matched is None:
        raise ValueError(f"{label} must end with an ISO release date (YYYY-MM-DD)")
    try:
        return date.fromisoformat(matched.group(1))
    except ValueError as exc:
        raise ValueError(f"{label} contains an invalid release date: {clean!r}") from exc


def validate_candidacy_ledger(ledger: pd.DataFrame) -> None:
    """Validate stable identity and append-only correction invariants."""

    work = _clean_ledger(ledger)
    if work.empty:
        return

    required = [
        "candidacy_id",
        "source_occurrence_id",
        "identity_basis",
        "event_id",
        "contest_id",
        "represented_body",
        "office_type",
        "boundary_regime",
        "official_district_id",
        "candidate_name_raw",
        "valid_from_release",
        "change_reason",
    ]
    for column in required:
        if work[column].isna().any() or work[column].str.strip().eq("").any():
            raise ValueError(f"Candidacy ledger {column} cannot be null or blank")
    invalid_basis = ~work["identity_basis"].isin(_IDENTITY_BASES)
    if invalid_basis.any():
        raise ValueError(
            "unknown Candidacy ledger identity_basis: "
            f"{work.loc[invalid_basis, 'identity_basis'].iloc[0]!r}"
        )

    valid_from_dates = work["valid_from_release"].map(
        lambda value: _release_date(value, label="valid_from_release")
    )
    valid_to_dates = work["valid_to_release"].map(
        lambda value: None if pd.isna(value) else _release_date(value, label="valid_to_release")
    )

    expected_ids = [
        stable_id("can", contest_id, occurrence_id)
        for contest_id, occurrence_id in zip(
            work["contest_id"], work["source_occurrence_id"], strict=True
        )
    ]
    if not work["candidacy_id"].eq(expected_ids).all():
        raise ValueError("Candidacy ledger contains an ID inconsistent with its source occurrence")

    identity_columns = [
        "candidacy_id",
        "source_occurrence_id",
        "identity_basis",
        "event_id",
        "contest_id",
        "represented_body",
        "office_type",
        "boundary_regime",
        "official_district_id",
    ]
    for candidacy_id, history in work.groupby("candidacy_id", sort=False):
        if any(history[column].nunique(dropna=False) != 1 for column in identity_columns):
            raise ValueError(f"Candidacy ledger changes immutable identity for {candidacy_id!r}")
        active = history["valid_to_release"].isna()
        if active.sum() != 1:
            raise ValueError(f"Candidacy ledger must have one active locator for {candidacy_id!r}")
        intervals = pd.DataFrame(
            {
                "valid_from": valid_from_dates.loc[history.index],
                "valid_to": valid_to_dates.loc[history.index],
            }
        ).sort_values("valid_from", kind="stable")
        if intervals["valid_from"].duplicated().any():
            raise ValueError(f"Candidacy ledger repeats a release interval for {candidacy_id!r}")
        closed = intervals["valid_to"].notna()
        if any(
            end <= start
            for start, end in intervals.loc[closed, ["valid_from", "valid_to"]].itertuples(
                index=False, name=None
            )
        ):
            raise ValueError(
                f"Candidacy ledger has a backdated release interval for {candidacy_id!r}"
            )
        interval_rows = list(intervals.itertuples(index=False))
        for earlier, later in pairwise(interval_rows):
            if earlier.valid_to != later.valid_from:
                raise ValueError(
                    f"Candidacy ledger release history is not contiguous for {candidacy_id!r}"
                )

    active = work.loc[work["valid_to_release"].isna()]
    occurrence_duplicate = active.duplicated(["contest_id", "source_occurrence_id"], keep=False)
    if occurrence_duplicate.any():
        raise ValueError("active Candidacy source occurrence IDs must be unique within a Contest")
    locator_duplicate = active.duplicated(["contest_id", "candidate_name_raw"], keep=False)
    duplicate_locators = active.loc[locator_duplicate]
    if (
        not duplicate_locators.empty
        and duplicate_locators["identity_basis"].ne("authority_identifier").any()
    ):
        raise ValueError("active name-only Candidacy locators must be unique within a Contest")


def _stage_adapter_frames(
    adapter_frames: list[pd.DataFrame],
) -> tuple[list[pd.DataFrame], pd.DataFrame]:
    staged_frames: list[pd.DataFrame] = []
    records: list[pd.DataFrame] = []
    for frame_number, frame in enumerate(adapter_frames):
        if frame.empty:
            staged_frames.append(frame.copy())
            continue
        staged = frame.copy().reset_index(drop=True)
        if "source_candidacy_id" not in staged:
            staged["source_candidacy_id"] = pd.NA
        provided = staged["source_candidacy_id"].astype("string").str.strip()
        provided = provided.mask(provided.eq(""), pd.NA)
        temporary = pd.Series(
            [f"__ledger_stage__:{frame_number}:{row_number}" for row_number in range(len(staged))],
            dtype="string",
        )
        staged["source_candidacy_id"] = provided.fillna(temporary)
        normalized = normalize_adapter_frame(
            staged,
            require_persistent_candidacy_id=True,
        )
        normalized["_ledger_frame_number"] = frame_number
        normalized["_ledger_row_number"] = range(len(normalized))
        normalized["_provided_source_occurrence_id"] = provided.reset_index(drop=True)
        records.append(normalized)
        staged_frames.append(frame.copy().reset_index(drop=True))

    if not records:
        return staged_frames, pd.DataFrame()
    all_records = pd.concat(records, ignore_index=True, sort=False)
    all_records["_contest_ordinal"] = all_records.groupby("contest_id", sort=False).cumcount() + 1
    return staged_frames, all_records


def _ledger_row(
    row: pd.Series,
    *,
    occurrence_id: str,
    identity_basis: str,
    release_id: str,
    reason: str,
) -> dict[str, object]:
    contest_id = str(row["contest_id"])
    return {
        "candidacy_id": stable_id("can", contest_id, occurrence_id),
        "source_occurrence_id": occurrence_id,
        "identity_basis": identity_basis,
        "event_id": str(row["event_id"]),
        "contest_id": contest_id,
        "represented_body": str(row["represented_body"]),
        "office_type": str(row["office_type"]),
        "boundary_regime": str(row["boundary_regime"]),
        "official_district_id": str(row["official_district_id"]),
        "candidate_name_raw": str(row["candidate_name_raw"]),
        "source_authority": row.get("source_authority", pd.NA),
        "source_resource": row.get("source_resource", pd.NA),
        "source_detail": row.get("source_detail", pd.NA),
        "valid_from_release": release_id,
        "valid_to_release": pd.NA,
        "change_reason": reason,
    }


def _register_new_contest(rows: pd.DataFrame, *, release_id: str) -> pd.DataFrame:
    additions: list[dict[str, object]] = []
    for _, row in rows.iterrows():
        provided = row["_provided_source_occurrence_id"]
        if pd.notna(provided):
            occurrence_id = str(provided)
            basis = "authority_identifier"
        else:
            occurrence_id = "project-ledger:" + stable_id(
                "occ", row["contest_id"], int(row["_contest_ordinal"])
            )
            basis = "project_ordinal_at_registration"
        additions.append(
            _ledger_row(
                row,
                occurrence_id=occurrence_id,
                identity_basis=basis,
                release_id=release_id,
                reason="initial_registration",
            )
        )
    return pd.DataFrame(additions, columns=LEDGER_COLUMNS)


def record_candidate_name_correction(
    ledger: pd.DataFrame,
    *,
    candidacy_id: str,
    candidate_name_raw: str,
    release_id: str,
    reason: str,
) -> pd.DataFrame:
    """Append a visible locator correction while retaining the public ID."""

    work = _clean_ledger(ledger)
    validate_candidacy_ledger(work)
    clean_id = _text(candidacy_id, label="candidacy_id")
    clean_name = _text(candidate_name_raw, label="candidate_name_raw")
    clean_release = _text(release_id, label="release_id")
    clean_reason = _text(reason, label="reason")
    selected = work["candidacy_id"].eq(clean_id) & work["valid_to_release"].isna()
    if selected.sum() != 1:
        raise ValueError(f"no unique active Candidacy ledger row for {clean_id!r}")
    current = work.loc[selected].iloc[0].copy()
    if str(current["candidate_name_raw"]) == clean_name:
        return work
    if _release_date(clean_release, label="release_id") <= _release_date(
        current["valid_from_release"], label="active locator valid_from_release"
    ):
        raise ValueError("correction release must be later than the active locator release")

    collision = (
        work["valid_to_release"].isna()
        & work["contest_id"].eq(current["contest_id"])
        & work["candidate_name_raw"].eq(clean_name)
        & ~work["candidacy_id"].eq(clean_id)
    )
    authority_disambiguated = (
        str(current["identity_basis"]) == "authority_identifier"
        and work.loc[collision, "identity_basis"].eq("authority_identifier").all()
    )
    if collision.any() and not authority_disambiguated:
        raise ValueError("corrected candidate name collides with another active ledger locator")

    work.loc[selected, "valid_to_release"] = clean_release
    replacement = current.copy()
    replacement["candidate_name_raw"] = clean_name
    replacement["valid_from_release"] = clean_release
    replacement["valid_to_release"] = pd.NA
    replacement["change_reason"] = clean_reason
    out = pd.concat([work, replacement.to_frame().T], ignore_index=True)
    out = (
        out[LEDGER_COLUMNS]
        .sort_values(["contest_id", "candidacy_id", "valid_from_release"], kind="stable")
        .reset_index(drop=True)
    )
    validate_candidacy_ledger(out)
    return out


def assign_candidacy_ids(
    adapter_frames: list[pd.DataFrame],
    *,
    release_id: str,
    ledger: pd.DataFrame | None = None,
) -> CandidacyLedgerAssignment:
    """Resolve every adapter row to a persisted source occurrence.

    Entirely new Contests are registered deterministically.  Once a Contest exists,
    its active inventory must match the ledger one-to-one; ambiguous changes fail
    closed and require an explicit ledger correction.
    """

    release = _text(release_id, label="release_id")
    work = _clean_ledger(ledger)
    validate_candidacy_ledger(work)
    output_frames, records = _stage_adapter_frames(adapter_frames)
    if records.empty:
        return CandidacyLedgerAssignment(output_frames, work)

    active = work.loc[work["valid_to_release"].isna()].copy()
    missing_contests = sorted(set(active["contest_id"]) - set(records["contest_id"]))
    if missing_contests:
        raise ValueError(
            f"existing contest inventory changed for {missing_contests[0]!r}; "
            "reconcile the Candidacy ledger explicitly"
        )
    assigned: dict[tuple[int, int], str] = {}
    additions: list[pd.DataFrame] = []
    automatic_corrections: list[tuple[str, str]] = []

    for contest_id, incoming in records.groupby("contest_id", sort=False):
        known = active.loc[active["contest_id"].eq(contest_id)]
        if known.empty:
            registered = _register_new_contest(incoming, release_id=release)
            additions.append(registered)
            for (_, row), (_, ledger_row) in zip(
                incoming.iterrows(), registered.iterrows(), strict=True
            ):
                assigned[(int(row["_ledger_frame_number"]), int(row["_ledger_row_number"]))] = str(
                    ledger_row["source_occurrence_id"]
                )
            continue

        if len(incoming) != len(known):
            raise ValueError(
                f"existing contest inventory changed for {contest_id!r}; "
                "reconcile the Candidacy ledger explicitly"
            )

        used: set[str] = set()
        unmatched: list[str] = []
        for _, row in incoming.iterrows():
            provided = row["_provided_source_occurrence_id"]
            if pd.notna(provided):
                matches = known.loc[known["source_occurrence_id"].eq(str(provided))]
            else:
                matches = known.loc[known["candidate_name_raw"].eq(str(row["candidate_name_raw"]))]
            if len(matches) != 1:
                unmatched.append(str(row["candidate_name_raw"]))
                continue
            match = matches.iloc[0]
            candidacy_id = str(match["candidacy_id"])
            if candidacy_id in used:
                unmatched.append(str(row["candidate_name_raw"]))
                continue
            used.add(candidacy_id)
            assigned[(int(row["_ledger_frame_number"]), int(row["_ledger_row_number"]))] = str(
                match["source_occurrence_id"]
            )
            if pd.notna(provided) and str(match["candidate_name_raw"]) != str(
                row["candidate_name_raw"]
            ):
                automatic_corrections.append((candidacy_id, str(row["candidate_name_raw"])))

        if unmatched or len(used) != len(known):
            examples = ", ".join(repr(value) for value in unmatched[:3])
            raise ValueError(
                f"could not match existing contest {contest_id!r} rows ({examples}); "
                "reconcile the Candidacy ledger explicitly"
            )

    if additions:
        work = pd.concat([work, *additions], ignore_index=True, sort=False)
    for candidacy_id, corrected_name in automatic_corrections:
        work = record_candidate_name_correction(
            work,
            candidacy_id=candidacy_id,
            candidate_name_raw=corrected_name,
            release_id=release,
            reason="authority identifier retained across source name correction",
        )

    for (frame_number, row_number), occurrence_id in assigned.items():
        frame = output_frames[frame_number]
        if "source_candidacy_id" not in frame:
            frame["source_candidacy_id"] = pd.NA
        frame.iat[row_number, frame.columns.get_loc("source_candidacy_id")] = occurrence_id

    work = (
        work[LEDGER_COLUMNS]
        .sort_values(["contest_id", "candidacy_id", "valid_from_release"], kind="stable")
        .reset_index(drop=True)
    )
    for column in LEDGER_COLUMNS:
        work[column] = work[column].astype("string")
    validate_candidacy_ledger(work)
    return CandidacyLedgerAssignment(output_frames, work)


def read_candidacy_ledger(path: str | Path) -> pd.DataFrame:
    """Read a persisted ledger, or return an empty first-build ledger."""

    source = Path(path)
    if not source.exists():
        return empty_candidacy_ledger()
    ledger = pd.read_csv(source, dtype="string")
    ledger = _clean_ledger(ledger)
    if ledger.empty:
        raise ValueError(
            "persisted Candidacy ledger is empty; a missing path is the only first-build sentinel"
        )
    validate_candidacy_ledger(ledger)
    return ledger


def write_candidacy_ledger(ledger: pd.DataFrame, path: str | Path) -> Path:
    """Atomically persist canonical ledger ordering after validation."""

    work = _clean_ledger(ledger)
    validate_candidacy_ledger(work)
    if work.empty:
        raise ValueError("cannot persist an empty Candidacy ledger")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    work.to_csv(temporary, index=False)
    temporary.replace(destination)
    return destination
