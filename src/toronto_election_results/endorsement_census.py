"""Build the research-control census for the frozen endorsement panel.

The census groups canonical Endorser-by-Contest coverage cells into the source
packages a researcher is likely to recover: one Endorser, election event, and
office.  It is a queue and status report, never a second endorsement ledger.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from .schema import stable_id

_TARGET_BODY = "toronto_city_council"
_TARGET_OFFICES = frozenset({"mayor", "councillor"})
_COVERAGE_STATES = (
    "comprehensive_source_found",
    "partially_searched",
    "searched_no_endorsement_found",
    "source_unavailable",
    "not_searched",
)


def _required(frame: pd.DataFrame, columns: set[str], table: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{table} is missing census columns: {', '.join(missing)}")


def _text(value: object) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        return ""
    return " ".join(str(value).split())


def _boolean(value: object, *, label: str) -> bool:
    if isinstance(value, bool):
        return value
    clean = _text(value).casefold()
    if clean == "true":
        return True
    if clean == "false":
        return False
    raise ValueError(f"{label} must be true or false")


def _date(value: object, *, label: str) -> date:
    clean = _text(value)
    try:
        parsed = date.fromisoformat(clean)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO date: {clean!r}") from exc
    if parsed.isoformat() != clean:
        raise ValueError(f"{label} must be an ISO date: {clean!r}")
    return parsed


def _disposition(row: pd.Series) -> str:
    contest_count = int(row["contest_count"])
    confirmed = int(row["confirmed_assertion_count"])
    unresolved = int(row["unresolved_assertion_count"])
    if int(row["comprehensive_source_found_count"]) == contest_count:
        return "validated_package_found"
    if int(row["source_unavailable_count"]) == contest_count:
        return "source_unavailable"
    if int(row["not_searched_count"]) == contest_count and confirmed == 0 and unresolved == 0:
        return "not_yet_searched"
    if (
        int(row["searched_no_endorsement_found_count"]) == contest_count
        and confirmed == 0
        and unresolved == 0
    ):
        return "searched_no_recoverable_package"
    return "partial_evidence_only"


def build_endorsement_source_package_census(
    *,
    election_results: pd.DataFrame,
    contests: pd.DataFrame,
    panel_curations: pd.DataFrame,
    endorsement_assertions: pd.DataFrame,
    endorsement_coverage: pd.DataFrame,
) -> pd.DataFrame:
    """Return one deterministic research row per Endorser/event/office package."""

    _required(
        election_results,
        {
            "contest_id",
            "election_date",
            "represented_body",
            "office_type",
            "official_district_id",
        },
        "election_results",
    )
    _required(
        contests,
        {"contest_id", "event_id", "represented_body", "office_type"},
        "contests",
    )
    _required(
        panel_curations,
        {
            "endorser_key",
            "canonical_name",
            "is_panel_endorser",
            "eligibility_start_date",
            "mayor_applicable",
            "councillor_applicable",
        },
        "endorser_panel_curations",
    )
    _required(
        endorsement_assertions,
        {"endorser_id", "contest_id", "review_state"},
        "endorsement_assertions",
    )
    _required(
        endorsement_coverage,
        {"endorser_id", "contest_id", "coverage_state", "assessed_through"},
        "endorsement_coverage",
    )

    result_meta = election_results[
        [
            "contest_id",
            "election_date",
            "represented_body",
            "office_type",
            "official_district_id",
        ]
    ].copy()
    for column in result_meta.columns:
        result_meta[column] = result_meta[column].map(_text)
    inconsistent = result_meta.groupby("contest_id", sort=False).nunique(dropna=False).gt(1)
    if inconsistent.any(axis=None):
        contest_id = inconsistent.any(axis=1).loc[lambda value: value].index[0]
        raise ValueError(f"election_results Contest {contest_id!r} has inconsistent metadata")
    result_meta = result_meta.drop_duplicates("contest_id")

    contest_meta = contests[["contest_id", "event_id", "represented_body", "office_type"]].copy()
    for column in contest_meta.columns:
        contest_meta[column] = contest_meta[column].map(_text)
    if contest_meta["contest_id"].duplicated().any():
        raise ValueError("contests.contest_id must be unique")
    contest_meta = contest_meta.merge(
        result_meta,
        on="contest_id",
        how="inner",
        suffixes=("_contest", "_result"),
        validate="one_to_one",
    )
    disagreement = ~contest_meta["represented_body_contest"].eq(
        contest_meta["represented_body_result"]
    ) | ~contest_meta["office_type_contest"].eq(contest_meta["office_type_result"])
    if disagreement.any():
        contest_id = contest_meta.loc[disagreement, "contest_id"].iloc[0]
        raise ValueError(f"Contest {contest_id!r} disagrees with election_results")
    contest_meta = contest_meta.loc[
        contest_meta["represented_body_contest"].eq(_TARGET_BODY)
        & contest_meta["office_type_contest"].isin(_TARGET_OFFICES)
    ].rename(columns={"office_type_contest": "office_type"})

    panel_rows: list[dict[str, object]] = []
    for panel in panel_curations.itertuples(index=False):
        key = _text(panel.endorser_key)
        if not _boolean(panel.is_panel_endorser, label=f"panel[{key}].is_panel_endorser"):
            continue
        panel_rows.append(
            {
                "endorser_key": key,
                "endorser_id": stable_id("edr", "curated_endorser", key),
                "canonical_name": _text(panel.canonical_name),
                "eligibility_start_date": _date(
                    panel.eligibility_start_date,
                    label=f"panel[{key}].eligibility_start_date",
                ),
                "mayor_applicable": _boolean(
                    panel.mayor_applicable,
                    label=f"panel[{key}].mayor_applicable",
                ),
                "councillor_applicable": _boolean(
                    panel.councillor_applicable,
                    label=f"panel[{key}].councillor_applicable",
                ),
            }
        )
    panel = pd.DataFrame(panel_rows)
    if panel.empty:
        raise ValueError("endorsement census has no approved panel Endorsers")
    if panel["endorser_key"].duplicated().any() or panel["endorser_id"].duplicated().any():
        raise ValueError("endorsement census panel Endorsers must be unique")

    expected_rows: list[dict[str, object]] = []
    for endorser in panel.itertuples(index=False):
        for contest in contest_meta.itertuples(index=False):
            election_date = _date(
                contest.election_date,
                label=f"Contest {contest.contest_id}.election_date",
            )
            applicable = bool(getattr(endorser, f"{contest.office_type}_applicable"))
            if not applicable or election_date < endorser.eligibility_start_date:
                continue
            expected_rows.append(
                {
                    "endorser_key": endorser.endorser_key,
                    "endorser_id": endorser.endorser_id,
                    "canonical_name": endorser.canonical_name,
                    "event_id": contest.event_id,
                    "election_date": election_date.isoformat(),
                    "office_type": contest.office_type,
                    "contest_id": contest.contest_id,
                    "official_district_id": contest.official_district_id,
                }
            )
    expected = pd.DataFrame(expected_rows)
    if expected.empty:
        raise ValueError("endorsement census has no applicable Contest cells")

    coverage = endorsement_coverage.copy()
    for column in ("endorser_id", "contest_id", "coverage_state"):
        coverage[column] = coverage[column].map(_text)
    if coverage.duplicated(["endorser_id", "contest_id"]).any():
        raise ValueError("endorsement_coverage must be unique by Endorser/Contest")
    unknown_states = set(coverage["coverage_state"]) - set(_COVERAGE_STATES) - {"not_applicable"}
    if unknown_states:
        raise ValueError(f"endorsement census found unknown coverage state: {min(unknown_states)}")
    cells = expected.merge(
        coverage,
        on=["endorser_id", "contest_id"],
        how="left",
        validate="one_to_one",
    )
    if cells["coverage_state"].isna().any():
        row = cells.loc[cells["coverage_state"].isna()].iloc[0]
        raise ValueError(
            f"endorsement census is missing coverage for {row['endorser_key']}/{row['contest_id']}"
        )
    if cells["coverage_state"].eq("not_applicable").any():
        raise ValueError("applicable endorsement census cells cannot be not_applicable")

    assertions = endorsement_assertions.copy()
    for column in ("endorser_id", "contest_id", "review_state"):
        assertions[column] = assertions[column].map(_text)
    assertion_counts = (
        assertions.loc[assertions["review_state"].isin({"confirmed", "unresolved"})]
        .groupby(["endorser_id", "contest_id", "review_state"], sort=False)
        .size()
        .unstack(fill_value=0)
        .reset_index()
        .rename(
            columns={
                "confirmed": "confirmed_assertion_count",
                "unresolved": "unresolved_assertion_count",
            }
        )
    )
    for column in ("confirmed_assertion_count", "unresolved_assertion_count"):
        if column not in assertion_counts:
            assertion_counts[column] = 0
    cells = cells.merge(
        assertion_counts,
        on=["endorser_id", "contest_id"],
        how="left",
        validate="one_to_one",
    )
    cells[["confirmed_assertion_count", "unresolved_assertion_count"]] = cells[
        ["confirmed_assertion_count", "unresolved_assertion_count"]
    ].fillna(0)

    group_columns = [
        "endorser_key",
        "endorser_id",
        "canonical_name",
        "event_id",
        "election_date",
        "office_type",
    ]
    packages: list[dict[str, object]] = []
    for keys, group in cells.groupby(group_columns, sort=False, dropna=False):
        record = dict(zip(group_columns, keys, strict=True))
        record["package_id"] = stable_id(
            "epk", record["endorser_id"], record["event_id"], record["office_type"]
        )
        record["contest_count"] = len(group)
        record["related_contest_ids"] = "|".join(sorted(group["contest_id"]))
        record["district_count"] = group["official_district_id"].nunique()
        for state in _COVERAGE_STATES:
            record[f"{state}_count"] = int(group["coverage_state"].eq(state).sum())
        record["confirmed_assertion_count"] = int(group["confirmed_assertion_count"].sum())
        record["unresolved_assertion_count"] = int(group["unresolved_assertion_count"].sum())
        assessed = sorted(value for value in group["assessed_through"].map(_text) if value)
        record["assessed_through"] = assessed[-1] if assessed else pd.NA
        packages.append(record)

    out = pd.DataFrame(packages)
    out["disposition"] = out.apply(_disposition, axis=1)
    columns = [
        "package_id",
        "endorser_key",
        "canonical_name",
        "event_id",
        "election_date",
        "office_type",
        "disposition",
        "assessed_through",
        "contest_count",
        "district_count",
        "confirmed_assertion_count",
        "unresolved_assertion_count",
        *[f"{state}_count" for state in _COVERAGE_STATES],
        "related_contest_ids",
    ]
    return (
        out[columns]
        .sort_values(
            ["canonical_name", "election_date", "office_type"],
            kind="stable",
        )
        .reset_index(drop=True)
    )
