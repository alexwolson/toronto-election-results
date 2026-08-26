"""City of Toronto mayor and councillor adapter for the shared v2 schema."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .candidates import known_multiword_surnames, normalize_name
from .schema import stable_id

COUNCIL_EVENT_MANIFEST = (
    # General elections.
    ("2003-11-10", "general", "toronto_council_44_wards", 243),
    ("2006-11-13", "general", "toronto_council_44_wards", 313),
    ("2010-10-25", "general", "toronto_council_44_wards", 319),
    ("2014-10-27", "general", "toronto_council_44_wards", 423),
    ("2018-10-22", "general", "toronto_council_25_wards", 277),
    ("2022-10-24", "general", "toronto_council_25_wards", 194),
    # Completed mayor/councillor by-elections in the City archive.
    ("2016-07-25", "by_election", "toronto_council_44_wards", 12),
    ("2017-02-13", "by_election", "toronto_council_44_wards", 32),
    ("2021-01-15", "by_election", "toronto_council_25_wards", 27),
    ("2023-06-26", "by_election", "toronto_council_25_wards", 102),
    ("2023-11-30", "by_election", "toronto_council_25_wards", 23),
    ("2024-11-04", "by_election", "toronto_council_25_wards", 16),
    ("2025-09-29", "by_election", "toronto_council_25_wards", 20),
)

_COUNCIL_BY_ELECTION_CONTESTS = {
    "2016-07-25": ("councillor", "ward-2"),
    "2017-02-13": ("councillor", "ward-42"),
    "2021-01-15": ("councillor", "ward-22"),
    "2023-06-26": ("mayor", "city"),
    "2023-11-30": ("councillor", "ward-20"),
    "2024-11-04": ("councillor", "ward-15"),
    "2025-09-29": ("councillor", "ward-25"),
}

_BOUNDARY_REGIMES = {
    "44-ward": "toronto_council_44_wards",
    "25-ward": "toronto_council_25_wards",
}


def council_event_manifest() -> pd.DataFrame:
    """Return the fixed cutoff-bounded City Council event inventory."""

    rows = []
    for date, election_type, boundary_regime, expected_candidacies in COUNCIL_EVENT_MANIFEST:
        rows.append(
            {
                "event_id": stable_id("evt", "toronto_city_clerk", date, election_type),
                "election_date": pd.Timestamp(date).date(),
                "election_type": election_type,
                "boundary_regime": boundary_regime,
                "expected_candidacies": expected_candidacies,
            }
        )
    return pd.DataFrame(rows)


def council_contest_manifest() -> pd.DataFrame:
    """Return one expected Mayor/Councillor Contest per native as-run district."""

    rows: list[dict[str, object]] = []
    for event in council_event_manifest().itertuples(index=False):
        if event.election_type == "general":
            rows.append(
                {
                    "event_id": event.event_id,
                    "office_type": "mayor",
                    "official_district_id": "city",
                }
            )
            n_wards = 44 if event.boundary_regime == "toronto_council_44_wards" else 25
            rows.extend(
                {
                    "event_id": event.event_id,
                    "office_type": "councillor",
                    "official_district_id": f"ward-{ward}",
                }
                for ward in range(1, n_wards + 1)
            )
        else:
            office_type, official_district_id = _COUNCIL_BY_ELECTION_CONTESTS[
                event.election_date.isoformat()
            ]
            rows.append(
                {
                    "event_id": event.event_id,
                    "office_type": office_type,
                    "official_district_id": official_district_id,
                }
            )
    return pd.DataFrame(rows)


def validate_council_coverage(frame: pd.DataFrame) -> None:
    """Reject a local load that drifts from the fixed 13-event/239-Contest inventory."""

    required = {
        "event_id",
        "election_date",
        "election_type",
        "boundary_regime",
        "office_type",
        "official_district_id",
        "candidate_name_raw",
    }
    missing_columns = sorted(required - set(frame.columns))
    if missing_columns:
        raise ValueError(f"council coverage frame is missing: {', '.join(missing_columns)}")

    events = council_event_manifest()
    actual_dates = pd.to_datetime(frame["election_date"], errors="coerce").dt.date
    if actual_dates.isna().any():
        raise ValueError("council coverage contains an invalid election_date")
    event_rows = frame.assign(election_date=actual_dates)[
        ["event_id", "election_date", "election_type", "boundary_regime"]
    ].drop_duplicates()
    expected_events = events[["event_id", "election_date", "election_type", "boundary_regime"]]
    event_keys = set(event_rows.itertuples(index=False, name=None))
    expected_event_keys = set(expected_events.itertuples(index=False, name=None))
    if event_keys != expected_event_keys:
        raise ValueError(
            "council event coverage mismatch: "
            f"missing={len(expected_event_keys - event_keys)}, "
            f"unexpected={len(event_keys - expected_event_keys)}"
        )

    contest_columns = ["event_id", "office_type", "official_district_id"]
    contest_keys = set(frame[contest_columns].drop_duplicates().itertuples(index=False, name=None))
    expected_contest_keys = set(
        council_contest_manifest()[contest_columns].itertuples(index=False, name=None)
    )
    if contest_keys != expected_contest_keys:
        raise ValueError(
            "council contest coverage mismatch: "
            f"missing={len(expected_contest_keys - contest_keys)}, "
            f"unexpected={len(contest_keys - expected_contest_keys)}"
        )

    actual_counts = frame.groupby("event_id", sort=False).size().to_dict()
    expected_counts = dict(
        events[["event_id", "expected_candidacies"]].itertuples(index=False, name=None)
    )
    if actual_counts != expected_counts:
        raise ValueError("council Candidacy counts do not match the fixed official inventory")


def _district_fields(row: pd.Series) -> tuple[str, str]:
    if row["office"] == "mayor":
        return "city", "City of Toronto"
    if pd.isna(row["ward_number"]):
        raise ValueError("councillor row is missing ward_number")
    ward = int(row["ward_number"])
    ward_name = row.get("ward_name")
    label = f"Ward {ward}"
    if ward_name is not None and not pd.isna(ward_name) and str(ward_name).strip():
        label = f"{label} — {str(ward_name).strip()}"
    return f"ward-{ward}", label


def _official_outcomes(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    elected = pd.Series(pd.NA, index=frame.index, dtype="boolean")
    method = pd.Series("vote", index=frame.index, dtype="string")
    group_columns = ["election_date", "office", "_official_district_id"]

    for _, group in frame.groupby(group_columns, sort=False, dropna=False):
        if len(group) == 1:
            elected.loc[group.index] = True
            method.loc[group.index] = "acclamation"
            continue
        maximum = group["votes"].max()
        leaders = group["votes"].eq(maximum)
        elected.loc[group.index[~leaders]] = False
        if int(leaders.sum()) == 1:
            elected.loc[group.index[leaders]] = True
        # A tied maximum needs an authority declaration (lot in Toronto).  Until a
        # declaration supplement is present, the tied candidates remain unknown.
    return elected, method


def adapt_council_results(frame: pd.DataFrame) -> pd.DataFrame:
    """Map legacy mayor/councillor rows to the source-adapter contract.

    The input is already one row per candidacy and contest.  City voter statistics,
    when present, describe the composite municipal ballot and are labelled as such;
    this prevents those counts from later being mistaken for trustee-specific turnout.
    """

    required = {
        "election_date",
        "election_type",
        "ward_system",
        "office",
        "ward_number",
        "ward_name",
        "candidate_name_raw",
        "votes",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"municipal frame is missing required columns: {', '.join(missing)}")

    out = frame.copy()
    invalid_offices = ~out["office"].isin({"mayor", "councillor"})
    if invalid_offices.any():
        raise ValueError(
            f"unsupported municipal office: {out.loc[invalid_offices, 'office'].iloc[0]!r}"
        )
    invalid_systems = ~out["ward_system"].isin(_BOUNDARY_REGIMES)
    if invalid_systems.any():
        raise ValueError(
            f"unknown ward system: {out.loc[invalid_systems, 'ward_system'].iloc[0]!r}"
        )

    districts = out.apply(_district_fields, axis=1)
    out["_official_district_id"] = [district[0] for district in districts]
    out["district_name"] = [district[1] for district in districts]
    out["elected"], out["outcome_method"] = _official_outcomes(out)

    out["event_id"] = [
        stable_id("evt", "toronto_city_clerk", date, election_type)
        for date, election_type in zip(out["election_date"], out["election_type"], strict=True)
    ]
    out["election_authority"] = "toronto_city_clerk"
    out["represented_body"] = "toronto_city_council"
    out["office_type"] = out["office"]
    out["boundary_regime"] = out["ward_system"].map(_BOUNDARY_REGIMES)
    out["official_district_id"] = out["_official_district_id"]
    out["party_name_raw"] = pd.NA
    out["affiliation_status"] = "non_partisan"
    out["coverage_status"] = "complete"
    out["source_authority"] = "City of Toronto"
    out["source_resource"] = out["election_type"].map(
        {
            "general": "Elections — Official Results",
            "by_election": "Elections — Official By-election Results",
        }
    )
    source = out.get("source", pd.Series("open_data", index=out.index))
    out["source_detail"] = source.fillna("open_data").astype("string")
    out["incumbent_reported"] = pd.NA
    known_surnames = known_multiword_surnames(out["candidate_name_raw"])
    out["candidate_name"] = [
        normalize_name(name, known_surnames=known_surnames)[0] for name in out["candidate_name_raw"]
    ]

    for column in ["eligible_electors", "ballots_cast"]:
        if column not in out:
            out[column] = pd.NA
    has_turnout = out["eligible_electors"].notna() | out["ballots_cast"].notna()
    out["turnout_scope"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out.loc[has_turnout, "turnout_scope"] = "composite_municipal_ballot"

    columns = [
        "event_id",
        "election_date",
        "election_type",
        "election_authority",
        "represented_body",
        "office_type",
        "boundary_regime",
        "official_district_id",
        "district_name",
        "candidate_name_raw",
        "candidate_name",
        "party_name_raw",
        "affiliation_status",
        "votes",
        "elected",
        "incumbent_reported",
        "eligible_electors",
        "ballots_cast",
        "turnout_scope",
        "outcome_method",
        "coverage_status",
        "source_authority",
        "source_resource",
        "source_detail",
    ]
    return out[columns].reset_index(drop=True)


def load_council_results(
    *, raw: Path = Path("data/raw"), interim: Path = Path("data/interim")
) -> pd.DataFrame:
    """Parse all locally acquired mayor/councillor files into adapter rows."""

    # Local imports keep the legacy parser usable while the v2 assembler replaces
    # its old public entry point.
    from .assemble import build_base
    from .voter_statistics import (
        attach_electorate,
        by_election_voter_statistics,
        voter_statistics,
    )

    base = build_base(raw=raw, interim=interim)
    with_turnout = attach_electorate(
        base,
        voter_statistics(raw=raw / "voter_stats"),
        by_election_voter_statistics(
            raw=raw / "voter_stats", by_election_raw=raw / "byelection_voter_stats"
        ),
    )
    adapted = adapt_council_results(with_turnout)
    validate_council_coverage(adapted)
    return adapted
