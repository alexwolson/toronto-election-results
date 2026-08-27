"""Shared normalized contract for election-authority adapters.

The source adapters deliberately know about their own files and terminology.  This
module is the narrow boundary between those adapters and the published relational
dataset: it assigns stable source-occurrence identities, applies result semantics,
and derives the small dimension tables used by the assembler.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from collections.abc import Iterable

import pandas as pd

# A project-owned namespace makes UUID5 values deterministic without coupling them
# to display labels or Python's process-randomized hash implementation.
_ID_NAMESPACE = uuid.UUID("728a65d4-86e8-5a73-a760-24214cfe49d9")
_WHITESPACE = re.compile(r"\s+")

_REQUIRED_ADAPTER_COLUMNS = {
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
    "votes",
    "elected",
    "outcome_method",
    "coverage_status",
    "source_detail",
}

_OPTIONAL_DEFAULTS: dict[str, object] = {
    "result_status": "final",
    "candidate_name": pd.NA,
    "campaign_url": pd.NA,
    "source_candidacy_id": pd.NA,
    "party_name_raw": pd.NA,
    "affiliation_status": pd.NA,
    "incumbent_reported": pd.NA,
    "eligible_electors": pd.NA,
    "ballots_cast": pd.NA,
    "turnout_scope": pd.NA,
    "source_authority": pd.NA,
    "source_resource": pd.NA,
    "reported_total_contest_votes": pd.NA,
    "reported_vote_share": pd.NA,
    "reported_vote_rank": pd.NA,
    "reported_n_candidates": pd.NA,
}

_INDEPENDENT_LABELS = {
    "independent",
    "independant",
    "ind",
    "no affiliation",
    "no party affiliation",
}

# Election authorities have changed between abbreviations, full names, and renamed
# legal organizations across the release window.  These aliases are deliberately
# jurisdiction-scoped: a similarly named federal and provincial organization is not
# the same Party.  Every target below is itself an English label reported by the
# relevant authority in an in-scope result.
_PARTY_NAME_ALIASES = {
    "elections_canada": {
        "aacev party of canada": "Animal Protection Party",
        "aaev party of canada": "Animal Protection Party",
        "animal alliance environment voters party of canada": "Animal Protection Party",
        "animal alliance/environment voters": "Animal Protection Party",
        "animal protection party": "Animal Protection Party",
        "cap": "Canadian Action Party",
        "canadian action": "Canadian Action Party",
        "canadian action party": "Canadian Action Party",
        "chp canada": "Christian Heritage Party of Canada",
        "christian heritage party": "Christian Heritage Party of Canada",
        "christian heritage party of canada": "Christian Heritage Party of Canada",
        "conservative": "Conservative Party of Canada",
        "conservative party of canada": "Conservative Party of Canada",
        "green party": "Green Party of Canada",
        "green party of canada": "Green Party of Canada",
        "liberal": "Liberal Party of Canada",
        "liberal party of canada": "Liberal Party of Canada",
        "libertarian": "Libertarian Party of Canada",
        "libertarian party of canada": "Libertarian Party of Canada",
        "marijuana party": "Marijuana Party",
        "radical marijuana": "Marijuana Party",
        "marxist-leninist": "Marxist-Leninist",
        "ml": "Marxist-Leninist",
        "n.d.p.": "New Democratic Party",
        "ndp-new democratic party": "New Democratic Party",
        "new democratic party": "New Democratic Party",
        "pc party": "Progressive Canadian Party",
        "progressive canadian party": "Progressive Canadian Party",
        "people's party": "People's Party - PPC",
        "people's party - ppc": "People's Party - PPC",
        "united party of canada": "United Party of Canada",
        "upc": "United Party of Canada",
    },
    "elections_ontario": {
        "communist": "Communist Party of Canada (Ontario)",
        "communist party of canada (ontario)": "Communist Party of Canada (Ontario)",
        "freedom": "Freedom Party of Ontario",
        "freedom party of ontario": "Freedom Party of Ontario",
        "green": "Green Party of Ontario",
        "green party of ontario": "Green Party of Ontario",
        "the green party of ontario": "Green Party of Ontario",
        "liberal": "Ontario Liberal Party",
        "ontario liberal party": "Ontario Liberal Party",
        "new democratic": "New Democratic Party of Ontario",
        "new democratic party of ontario": "New Democratic Party of Ontario",
        "none of the above party of ontario": "None of the Above Direct Democracy Party",
        "none of the above direct democracy party": ("None of the Above Direct Democracy Party"),
        "progressive conservative": "Progressive Conservative Party of Ontario",
        "progressive conservative party of ontario": ("Progressive Conservative Party of Ontario"),
        "the peoples political party": "The People's Political Party",
        "the people's political party": "The People's Political Party",
        "vegan environmental party": "Go Vegan",
        "go vegan": "Go Vegan",
    },
}

_CANONICAL_VALUES = {
    "election_authority": {
        "Elections Canada": "elections_canada",
        "Elections Ontario": "elections_ontario",
        "Toronto City Clerk": "toronto_city_clerk",
    },
    "represented_body": {
        "House of Commons of Canada": "canada_house_of_commons",
        "Legislative Assembly of Ontario": "ontario_legislative_assembly",
        "Toronto City Council": "toronto_city_council",
        "Toronto District School Board": "toronto_district_school_board",
        "Toronto Catholic District School Board": "toronto_catholic_district_school_board",
        "Conseil scolaire Viamonde": "conseil_scolaire_viamonde",
        "Conseil scolaire catholique MonAvenir": "conseil_scolaire_catholique_monavenir",
    },
    "office_type": {
        "Mayor": "mayor",
        "City Councillor": "councillor",
        "School Board Trustee": "trustee",
        "Member of Parliament": "mp",
        "Member of Provincial Parliament": "mpp",
    },
}

_SOURCE_AUTHORITY_LABELS = {
    "elections canada": "Elections Canada",
    "elections_canada": "Elections Canada",
    "elections ontario": "Elections Ontario",
    "elections_ontario": "Elections Ontario",
    "city of toronto": "Toronto City Clerk",
    "toronto city clerk": "Toronto City Clerk",
    "toronto_city_clerk": "Toronto City Clerk",
}

_SOURCE_RESOURCE_FAMILIES = {
    ("elections_canada", "general"): "Official Voting Results — Raw Data",
    ("elections_canada", "by_election"): "Official Voting Results — Raw Data",
    ("elections_ontario", "general"): "Official election results reports",
    ("elections_ontario", "by_election"): "Official election results reports",
    ("toronto_city_clerk", "general"): "Elections — Official Results",
    ("toronto_city_clerk", "by_election"): "Elections — Official By-election Results",
}


def _id_part(value: object) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        raise ValueError("stable ID components cannot be null")
    normalized = unicodedata.normalize("NFKC", str(value)).strip()
    if not normalized:
        raise ValueError("stable ID components cannot be blank")
    return normalized


def stable_id(prefix: str, *parts: object) -> str:
    """Return a deterministic, namespaced opaque identifier.

    ``parts`` must be immutable source identity fields, never mutable presentation
    labels.  The full UUID is retained so collisions are not made more likely for
    cosmetic brevity.
    """

    clean_prefix = _id_part(prefix).lower()
    if not re.fullmatch(r"[a-z][a-z0-9]*", clean_prefix):
        raise ValueError(f"invalid ID prefix: {prefix!r}")
    if not parts:
        raise ValueError("at least one stable ID component is required")
    payload = "\x1f".join([clean_prefix, *(_id_part(part) for part in parts)])
    return f"{clean_prefix}_{uuid.uuid5(_ID_NAMESPACE, payload).hex}"


def _normalized_key(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value))
    return _WHITESPACE.sub(" ", text).strip().casefold()


def _clean_text(value: object) -> object:
    if value is None or value is pd.NA or pd.isna(value):
        return pd.NA
    cleaned = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", str(value))).strip()
    return cleaned if cleaned else pd.NA


def _canonical_party_name(jurisdiction: object, raw_name: object) -> object:
    cleaned = _clean_text(raw_name)
    if cleaned is pd.NA:
        return pd.NA
    jurisdiction_key = _normalized_key(jurisdiction)
    authority_aliases = {
        _normalized_key(source): canonical
        for source, canonical in _CANONICAL_VALUES["election_authority"].items()
    }
    jurisdiction_slug = authority_aliases.get(jurisdiction_key, str(jurisdiction))
    aliases = _PARTY_NAME_ALIASES.get(jurisdiction_slug, {})
    return aliases.get(_normalized_key(cleaned), cleaned)


def _as_nullable_boolean(series: pd.Series, name: str) -> pd.Series:
    try:
        return series.astype("boolean")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain booleans or nulls") from exc


def _as_nullable_integer(series: pd.Series, name: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    invalid = series.notna() & numeric.isna()
    if invalid.any():
        bad = series.loc[invalid].iloc[0]
        raise ValueError(f"{name} contains a non-numeric value: {bad!r}")
    fractional = numeric.notna() & (numeric % 1 != 0)
    if fractional.any():
        raise ValueError(f"{name} must contain whole numbers")
    if (numeric.dropna() < 0).any():
        raise ValueError(f"{name} cannot be negative")
    return numeric.astype("Int64")


def normalize_adapter_frame(
    frame: pd.DataFrame, *, require_persistent_candidacy_id: bool = False
) -> pd.DataFrame:
    """Normalize one source adapter's contest-level candidacy rows.

    Adapters must already have collapsed poll-level source data to one row per
    candidacy.  If a source can contain two candidates with the same displayed name
    in one contest, it must provide ``source_candidacy_id`` to disambiguate them.
    """

    missing = sorted(_REQUIRED_ADAPTER_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"adapter frame is missing required columns: {', '.join(missing)}")

    out = frame.copy()
    for column, default in _OPTIONAL_DEFAULTS.items():
        if column not in out:
            out[column] = default

    parsed_dates = pd.to_datetime(out["election_date"], errors="coerce")
    if parsed_dates.isna().any():
        bad = out.loc[parsed_dates.isna(), "election_date"].iloc[0]
        raise ValueError(f"invalid election_date: {bad!r}")
    out["election_date"] = parsed_dates.dt.date
    out["election_year"] = parsed_dates.dt.year.astype("Int64")

    text_columns = [
        "event_id",
        "election_type",
        "election_authority",
        "represented_body",
        "office_type",
        "boundary_regime",
        "official_district_id",
        "district_name",
        "candidate_name_raw",
        "candidate_name",
        "campaign_url",
        "party_name_raw",
        "source_candidacy_id",
        "outcome_method",
        "result_status",
        "coverage_status",
        "source_detail",
        "source_authority",
        "source_resource",
        "turnout_scope",
    ]
    for column in text_columns:
        out[column] = out[column].map(_clean_text).astype("string")
    for column, aliases in _CANONICAL_VALUES.items():
        out[column] = out[column].replace(aliases)
    out["candidate_name"] = out["candidate_name"].fillna(out["candidate_name_raw"])
    out["source_authority"] = out["source_authority"].fillna(out["election_authority"])
    out["source_authority"] = out["source_authority"].map(
        lambda value: _SOURCE_AUTHORITY_LABELS.get(_normalized_key(value), value)
    )
    default_resources = pd.Series(
        [
            _SOURCE_RESOURCE_FAMILIES.get((authority, election_type))
            for authority, election_type in zip(
                out["election_authority"], out["election_type"], strict=True
            )
        ],
        index=out.index,
        dtype="string",
    )
    out["source_resource"] = out["source_resource"].fillna(default_resources)
    if out["source_resource"].isna().any():
        authority = out.loc[out["source_resource"].isna(), "election_authority"].iloc[0]
        raise ValueError(f"no source resource family configured for {authority!r}")
    reported_turnout = out["eligible_electors"].notna() & out["ballots_cast"].notna()
    turnout_scopes = {
        "mp": "federal_electoral_district",
        "mpp": "provincial_electoral_district",
    }
    inferred_scope = out["office_type"].map(turnout_scopes)
    out.loc[reported_turnout & out["turnout_scope"].isna(), "turnout_scope"] = inferred_scope

    required_text = sorted(_REQUIRED_ADAPTER_COLUMNS - {"election_date", "votes", "elected"})
    for column in required_text:
        if out[column].isna().any():
            raise ValueError(f"{column} cannot be null or blank")

    out["votes"] = _as_nullable_integer(out["votes"], "votes")
    out["eligible_electors"] = _as_nullable_integer(out["eligible_electors"], "eligible_electors")
    out["ballots_cast"] = _as_nullable_integer(out["ballots_cast"], "ballots_cast")
    out["reported_total_contest_votes"] = _as_nullable_integer(
        out["reported_total_contest_votes"], "reported_total_contest_votes"
    )
    out["reported_vote_rank"] = _as_nullable_integer(
        out["reported_vote_rank"], "reported_vote_rank"
    )
    out["reported_n_candidates"] = _as_nullable_integer(
        out["reported_n_candidates"], "reported_n_candidates"
    )
    out["reported_vote_share"] = pd.to_numeric(out["reported_vote_share"], errors="coerce").astype(
        "Float64"
    )
    out["elected"] = _as_nullable_boolean(out["elected"], "elected")
    out["incumbent_reported"] = _as_nullable_boolean(
        out["incumbent_reported"], "incumbent_reported"
    )

    invalid_result_status = ~out["result_status"].isin({"final", "pending"})
    if invalid_result_status.any():
        value = out.loc[invalid_result_status, "result_status"].iloc[0]
        raise ValueError(f"unknown result_status: {value!r}")

    out["district_id"] = [
        stable_id("dst", body, regime, official_id)
        for body, regime, official_id in zip(
            out["represented_body"],
            out["boundary_regime"],
            out["official_district_id"],
            strict=True,
        )
    ]
    out["contest_id"] = [
        stable_id("con", event_id, body, office, district_id)
        for event_id, body, office, district_id in zip(
            out["event_id"],
            out["represented_body"],
            out["office_type"],
            out["district_id"],
            strict=True,
        )
    ]

    if require_persistent_candidacy_id and out["source_candidacy_id"].isna().any():
        raise ValueError(
            "published Candidacies require an authority identifier or persisted "
            "project source_candidacy_id"
        )

    # The fallback remains available only to low-level adapter diagnostics.  Every
    # public release path requests persistent IDs and therefore never reaches it.
    fallback_keys = out["candidate_name_raw"].map(_normalized_key)
    occurrence_keys = out["source_candidacy_id"].fillna(fallback_keys)
    duplicate_occurrences = pd.DataFrame(
        {"contest_id": out["contest_id"], "occurrence_key": occurrence_keys}
    ).duplicated(keep=False)
    if duplicate_occurrences.any():
        sample = out.loc[duplicate_occurrences, ["event_id", "candidate_name_raw"]].iloc[0]
        raise ValueError(
            "candidate source identity is not unique within a contest; provide a unique "
            f"source_candidacy_id (event={sample['event_id']!r}, "
            f"candidate={sample['candidate_name_raw']!r})"
        )
    out["candidacy_id"] = [
        stable_id("can", contest_id, occurrence_key)
        for contest_id, occurrence_key in zip(out["contest_id"], occurrence_keys, strict=True)
    ]

    return out.reset_index(drop=True)


def derive_result_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """Derive vote metrics without inventing legal outcomes.

    ``elected`` is an authority-reported fact.  In particular, tied maxima are not
    resolved here because Toronto, Ontario, and Canada use different legal rules.
    """

    required = {"contest_id", "votes", "elected", "outcome_method", "coverage_status"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"cannot derive result metrics without: {', '.join(missing)}")

    out = frame.copy()
    out["votes"] = _as_nullable_integer(out["votes"], "votes")
    out["elected"] = _as_nullable_boolean(out["elected"], "elected")
    out["acclaimed"] = out["outcome_method"].eq("acclamation").astype("boolean")

    acclaimed = out["acclaimed"].fillna(False)
    out.loc[acclaimed, "votes"] = pd.NA
    out.loc[acclaimed, "elected"] = True

    contest_sizes = out.groupby("contest_id", sort=False)["candidacy_id"].transform("size")
    out["n_candidates"] = contest_sizes.astype("Int64")

    complete = out["coverage_status"].eq("complete")
    has_poll = ~acclaimed & ~out["outcome_method"].isin(["void", "source_missing"])
    metrics_allowed = complete & has_poll & out["result_status"].eq("final")

    totals = out.groupby("contest_id", sort=False)["votes"].transform(
        lambda votes: votes.sum(min_count=1)
    )
    complete_contest = metrics_allowed.groupby(out["contest_id"], sort=False).transform("all")
    totals = totals.where(complete_contest).astype("Int64")
    out["total_contest_votes"] = totals

    shares = out["votes"].astype("Float64") / totals.astype("Float64")
    shares = shares.where(totals.gt(0) & metrics_allowed)
    out["vote_share"] = shares.astype("Float64")

    ranks = out.groupby("contest_id", sort=False)["votes"].rank(
        method="min", ascending=False, na_option="keep"
    )
    out["vote_rank"] = ranks.where(metrics_allowed).astype("Int64")

    candidate_record = out["coverage_status"].eq("candidate_record")
    if candidate_record.any():
        required_reported = [
            "reported_total_contest_votes",
            "reported_vote_share",
            "reported_vote_rank",
            "reported_n_candidates",
        ]
        if out.loc[candidate_record, required_reported].isna().any().any():
            raise ValueError("candidate_record coverage requires all reported contest metrics")
        out.loc[candidate_record, "total_contest_votes"] = out.loc[
            candidate_record, "reported_total_contest_votes"
        ]
        out.loc[candidate_record, "vote_share"] = out.loc[candidate_record, "reported_vote_share"]
        out.loc[candidate_record, "vote_rank"] = out.loc[candidate_record, "reported_vote_rank"]
        out.loc[candidate_record, "n_candidates"] = out.loc[
            candidate_record, "reported_n_candidates"
        ]

    if {"eligible_electors", "ballots_cast"}.issubset(out.columns):
        turnout = out["ballots_cast"].astype("Float64") / out["eligible_electors"].astype("Float64")
        turnout = turnout.where(
            out["eligible_electors"].gt(0)
            & out["eligible_electors"].notna()
            & out["ballots_cast"].notna()
        )
        out["turnout"] = turnout.astype("Float64")

    return out


def _infer_affiliation_status(row: pd.Series) -> str:
    supplied = row.get("affiliation_status")
    if supplied is not None and supplied is not pd.NA and not pd.isna(supplied):
        return str(supplied).strip().casefold()

    raw = row.get("party_name_raw")
    if raw is not None and raw is not pd.NA and not pd.isna(raw):
        if _normalized_key(raw) in _INDEPENDENT_LABELS:
            return "independent"
        return "party"

    if str(row.get("office_type", "")).casefold() in {"mayor", "councillor", "trustee"}:
        return "non_partisan"
    return "not_reported"


def attach_parties(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach a legal party identity to candidacies that report party affiliation."""

    out = frame.copy()
    if "party_name_raw" not in out:
        out["party_name_raw"] = pd.NA
    if "affiliation_status" not in out:
        out["affiliation_status"] = pd.NA

    out["party_name_raw"] = out["party_name_raw"].map(_clean_text).astype("string")
    out["affiliation_status"] = out.apply(_infer_affiliation_status, axis=1).astype("string")
    allowed = {"party", "independent", "non_partisan", "not_reported"}
    invalid = ~out["affiliation_status"].isin(allowed)
    if invalid.any():
        value = out.loc[invalid, "affiliation_status"].iloc[0]
        raise ValueError(f"unknown affiliation_status: {value!r}")

    party_without_name = out["affiliation_status"].eq("party") & out["party_name_raw"].isna()
    if party_without_name.any():
        raise ValueError("party affiliation requires party_name_raw")

    out["party_jurisdiction"] = out.get("party_jurisdiction", out["election_authority"])
    out["party_jurisdiction"] = out["party_jurisdiction"].map(_clean_text).astype("string")
    out["canonical_party_name"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out["party_id"] = pd.Series(pd.NA, index=out.index, dtype="string")
    party_rows = out["affiliation_status"].eq("party")
    out.loc[party_rows, "canonical_party_name"] = [
        _canonical_party_name(jurisdiction, name)
        for jurisdiction, name in zip(
            out.loc[party_rows, "party_jurisdiction"],
            out.loc[party_rows, "party_name_raw"],
            strict=True,
        )
    ]
    out.loc[party_rows, "party_id"] = [
        stable_id("pty", jurisdiction, _normalized_key(name))
        for jurisdiction, name in zip(
            out.loc[party_rows, "party_jurisdiction"],
            out.loc[party_rows, "canonical_party_name"],
            strict=True,
        )
    ]
    return out


def build_parties(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the one-row-per-party dimension from attached candidacies."""

    required = {"party_id", "party_jurisdiction", "canonical_party_name", "party_name_raw"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"cannot build parties without: {', '.join(missing)}")
    source_columns = [*required, *(column for column in ["election_date"] if column in frame)]
    parties = frame.loc[frame["party_id"].notna(), source_columns].copy()
    sort_columns = [column for column in ["election_date", "party_name_raw"] if column in parties]
    if sort_columns:
        parties = parties.sort_values(sort_columns, kind="stable", na_position="first")
    # Candidacies retain every exact source label.  The dimension retains the most
    # recent raw exemplar while keeping the jurisdiction-scoped canonical label used
    # to form Party identity.
    parties = parties.drop_duplicates("party_id", keep="last")
    parties = parties.rename(
        columns={"party_jurisdiction": "jurisdiction", "canonical_party_name": "canonical_name"}
    ).sort_values(["jurisdiction", "canonical_name", "party_id"], kind="stable")
    return parties[["party_id", "jurisdiction", "canonical_name", "party_name_raw"]].reset_index(
        drop=True
    )


def _assert_constant_within(frame: pd.DataFrame, key: str, columns: Iterable[str]) -> None:
    for column in columns:
        if column not in frame:
            continue
        counts = frame.groupby(key, dropna=False)[column].nunique(dropna=False)
        conflicts = counts[counts > 1]
        if not conflicts.empty:
            raise ValueError(f"{column} is inconsistent within {key}={conflicts.index[0]!r}")


def build_events(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the event dimension, rejecting contradictory adapter metadata."""

    columns = [
        "event_id",
        "election_date",
        "election_year",
        "election_type",
        "election_authority",
    ]
    _assert_constant_within(frame, "event_id", columns[1:])
    events = (
        frame[columns]
        .drop_duplicates()
        .sort_values(["election_date", "election_authority", "event_id"], kind="stable")
    )
    return events.reset_index(drop=True)


def build_contests(frame: pd.DataFrame) -> pd.DataFrame:
    """Build one Contest row from each group of Candidacy rows."""

    identity_columns = [
        "event_id",
        "represented_body",
        "office_type",
        "district_id",
        "official_district_id",
        "district_name",
        "boundary_regime",
        "outcome_method",
        "result_status",
        "coverage_status",
        "acclaimed",
        "n_candidates",
        "total_contest_votes",
        "eligible_electors",
        "ballots_cast",
        "turnout_scope",
        "source_authority",
        "source_resource",
        "source_detail",
    ]
    _assert_constant_within(frame, "contest_id", identity_columns)
    contests = frame[["contest_id", *identity_columns]].drop_duplicates("contest_id").copy()
    contests["seats_available"] = 1
    contests["turnout"] = pd.Series(pd.NA, index=contests.index, dtype="Float64")
    usable_turnout = (
        contests["eligible_electors"].notna()
        & contests["eligible_electors"].gt(0)
        & contests["ballots_cast"].notna()
    )
    contests.loc[usable_turnout, "turnout"] = contests.loc[usable_turnout, "ballots_cast"].astype(
        "Float64"
    ) / contests.loc[usable_turnout, "eligible_electors"].astype("Float64")
    return contests.sort_values(
        ["event_id", "office_type", "district_id"], kind="stable"
    ).reset_index(drop=True)


def build_districts(frame: pd.DataFrame) -> pd.DataFrame:
    """Build native as-run electoral districts without inventing missing geometry."""

    columns = [
        "represented_body",
        "boundary_regime",
        "official_district_id",
        "district_name",
    ]
    _assert_constant_within(frame, "district_id", columns)
    districts = frame[["district_id", *columns]].drop_duplicates("district_id").copy()
    districts["geometry_status"] = "not_acquired"
    districts["geometry_missing_reason"] = "official_contest_geometry_not_acquired"
    districts["geometry_crs"] = "EPSG:4326"
    districts["geometry"] = None
    return districts.sort_values(
        ["represented_body", "boundary_regime", "official_district_id"], kind="stable"
    ).reset_index(drop=True)
