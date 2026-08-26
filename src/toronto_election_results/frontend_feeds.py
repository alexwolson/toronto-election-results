"""Factual frontend feeds derived only from the canonical results release."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pandas as pd

MAYORAL_CANDIDATES_SCHEMA_VERSION = 3
PERSON_ALIASES_SCHEMA_VERSION = 1
_TORONTO_COUNCIL = "toronto_city_council"


def _present(value: object) -> bool:
    return value is not None and value is not pd.NA and not pd.isna(value)


def _text(value: object) -> str | None:
    return str(value).strip() if _present(value) and str(value).strip() else None


def _integer(value: object) -> int | None:
    return int(float(value)) if _present(value) and str(value).strip() else None


def _number(value: object) -> float | None:
    return float(value) if _present(value) and str(value).strip() else None


def _truth(value: object) -> bool:
    if not _present(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() == "true"


def _name_key(value: object) -> str:
    """Return the exact-match key published for downstream identity lookup."""

    return " ".join(unicodedata.normalize("NFKC", str(value)).split()).casefold()


def build_person_aliases_feed(results: pd.DataFrame, people: pd.DataFrame) -> dict[str, object]:
    """Publish Results-owned names without asking consumers to match people.

    Every spelling comes from a confirmed canonical candidacy or the Person
    registry. Consumers may resolve only aliases marked unambiguous; ambiguous
    spellings remain visible but deliberately do not resolve to a Person.
    """

    required_results = {"person_id", "candidate_name", "candidate_name_raw"}
    required_people = {"person_id", "preferred_name", "identity_status"}
    missing_results = sorted(required_results - set(results.columns))
    missing_people = sorted(required_people - set(people.columns))
    if missing_results:
        raise ValueError(
            f"canonical results are missing alias columns: {', '.join(missing_results)}"
        )
    if missing_people:
        raise ValueError(f"people registry is missing alias columns: {', '.join(missing_people)}")

    active_people = people.loc[people["identity_status"].eq("active")].copy()
    active_ids = set(active_people["person_id"].dropna().astype(str))
    names: set[tuple[str, str, str]] = set()
    for row in active_people.itertuples(index=False):
        if _present(row.person_id) and _present(row.preferred_name):
            alias = str(row.preferred_name).strip()
            names.add((_name_key(alias), alias, str(row.person_id)))
    for row in results.loc[results["person_id"].astype("string").isin(active_ids)].itertuples(
        index=False
    ):
        for value in (row.candidate_name, row.candidate_name_raw):
            if _present(value):
                alias = str(value).strip()
                names.add((_name_key(alias), alias, str(row.person_id)))

    people_by_key: dict[str, set[str]] = {}
    for key, _, person_id in names:
        people_by_key.setdefault(key, set()).add(person_id)
    aliases = [
        {
            "normalized_name": key,
            "reported_name": alias,
            "person_id": person_id if len(people_by_key[key]) == 1 else None,
            "is_unambiguous": len(people_by_key[key]) == 1,
        }
        for key, alias, person_id in sorted(names)
    ]
    return {"schema_version": PERSON_ALIASES_SCHEMA_VERSION, "aliases": aliases}


def _past_elections(rows: pd.DataFrame) -> list[dict[str, object]]:
    elections: list[dict[str, object]] = []
    for _, group in rows.groupby("contest_id", sort=False):
        head = group.sort_values("election_date", ascending=False, kind="stable").iloc[0]
        ranks = [_integer(value) for value in group["vote_rank"]]
        sizes = [_integer(value) for value in group["n_candidates"]]
        shares = [_number(value) for value in group["vote_share"]]
        elections.append(
            {
                "year": int(str(head["election_date"])[:4]),
                "election_date": str(head["election_date"]),
                "office_type": str(head["office_type"]),
                "represented_body": str(head["represented_body"]),
                "district_name": _text(head.get("district_name")),
                "party_name": _text(head.get("party_name")),
                "result": (
                    "won"
                    if any(_truth(value) for value in group["elected"])
                    or any(_truth(value) for value in group["acclaimed"])
                    else "lost"
                ),
                "vote_share": max((value for value in shares if value is not None), default=None),
                "rank": min((value for value in ranks if value is not None), default=None),
                "field_size": max((value for value in sizes if value is not None), default=None),
            }
        )
    return sorted(elections, key=lambda row: str(row["election_date"]), reverse=True)


def build_mayoral_candidates_feed(
    results: pd.DataFrame, career_reviews: pd.DataFrame
) -> dict[str, object]:
    """Build the certified current mayoral field with canonical identity history.

    The current field comes directly from the canonical pending Candidacies. Past
    elections join only through ``person_id``; this module performs no name match.
    """

    required = {
        "candidacy_id",
        "person_id",
        "event_id",
        "contest_id",
        "election_date",
        "election_year",
        "represented_body",
        "office_type",
        "candidate_name",
        "candidate_name_raw",
        "result_status",
        "coverage_status",
        "source_resource",
        "elected",
        "acclaimed",
        "vote_share",
        "vote_rank",
        "n_candidates",
    }
    missing = sorted(required - set(results.columns))
    if missing:
        raise ValueError(
            f"canonical results are missing candidate-feed columns: {', '.join(missing)}"
        )
    required_reviews = {
        "cohort_id",
        "subject_candidacy_id",
        "source_release",
        "review_date",
        "review_status",
        "limitations",
    }
    missing_reviews = sorted(required_reviews - set(career_reviews.columns))
    if missing_reviews:
        raise ValueError(
            f"career reviews are missing feed columns: {', '.join(missing_reviews)}"
        )
    if career_reviews["subject_candidacy_id"].duplicated().any():
        raise ValueError("career reviews must contain one row per current candidacy")

    election_year = pd.to_numeric(results["election_year"], errors="coerce")
    current = results.loc[
        election_year.eq(2026)
        & results["represented_body"].eq(_TORONTO_COUNCIL)
        & results["office_type"].eq("mayor")
        & results["result_status"].eq("pending")
    ].copy()
    if current.empty:
        raise ValueError("canonical results contain no pending 2026 Toronto mayoral field")
    if current["candidacy_id"].isna().any() or current["candidacy_id"].duplicated().any():
        raise ValueError("current mayoral candidacy_id values must be non-null and unique")
    for column in ("event_id", "contest_id", "election_date"):
        if current[column].nunique(dropna=False) != 1:
            raise ValueError(f"current mayoral field must have exactly one {column}")
    certified = (
        current["coverage_status"].eq("complete").all()
        and current["source_resource"].eq("2026 Municipal Election — Certified Candidates").all()
    )
    if not certified:
        raise ValueError("current mayoral field is not a complete certified roster")

    current_date = str(current["election_date"].iloc[0])
    historical = results.loc[
        results["result_status"].eq("final")
        & pd.to_datetime(results["election_date"], errors="coerce").lt(current_date)
    ].copy()
    elected_mayors = historical.loc[
        historical["represented_body"].eq(_TORONTO_COUNCIL)
        & historical["office_type"].eq("mayor")
        & (historical["elected"].map(_truth) | historical["acclaimed"].map(_truth))
        & historical["person_id"].notna()
    ].copy()
    if elected_mayors.empty:
        raise ValueError("canonical results cannot establish a prior elected Toronto mayor")
    latest_mayoral_date = elected_mayors["election_date"].max()
    latest_mayors = elected_mayors.loc[elected_mayors["election_date"].eq(latest_mayoral_date)]
    incumbent_people = set(latest_mayors["person_id"].dropna().astype(str))
    if len(incumbent_people) != 1:
        raise ValueError("canonical results cannot establish one current Toronto mayor")
    incumbent_person_id = next(iter(incumbent_people))

    candidates: list[dict[str, object]] = []
    reviews = career_reviews.set_index("subject_candidacy_id")
    if set(current["candidacy_id"].astype(str)) != set(reviews.index.astype(str)):
        raise ValueError("career reviews must exactly cover the certified mayoral field")
    current = current.sort_values("candidate_name_raw", key=lambda values: values.str.casefold())
    for _, candidate in current.iterrows():
        person_id = _text(candidate["person_id"])
        review = reviews.loc[str(candidate["candidacy_id"])]
        history_rows = (
            historical.loc[historical["person_id"].astype("string").eq(person_id)]
            if person_id is not None
            else historical.iloc[0:0]
        )
        candidates.append(
            {
                "candidacy_id": str(candidate["candidacy_id"]),
                "person_id": person_id,
                "display_name": str(candidate["candidate_name"]),
                "is_incumbent": person_id == incumbent_person_id,
                "review_status": str(review["review_status"]),
                "review_limitations": _text(review["limitations"]),
                "past_elections": _past_elections(history_rows),
            }
        )

    cohort_ids = career_reviews["cohort_id"].dropna().astype(str).unique()
    source_releases = career_reviews["source_release"].dropna().astype(str).unique()
    review_dates = career_reviews["review_date"].dropna().astype(str).unique()
    if len(cohort_ids) != 1 or len(source_releases) != 1 or len(review_dates) != 1:
        raise ValueError("career reviews must use one cohort, source release, and review date")
    return {
        "schema_version": MAYORAL_CANDIDATES_SCHEMA_VERSION,
        "event_id": str(current["event_id"].iloc[0]),
        "contest_id": str(current["contest_id"].iloc[0]),
        "election_date": current_date,
        "ballot_certified": True,
        "coverage": {
            "policy": "full_verified_canadian_electoral_career",
            "jurisdiction": "Canada",
            "year_cutoff": None,
            "cohort_id": cohort_ids[0],
            "source_release": source_releases[0],
            "review_date": review_dates[0],
            "methodology_note": (
                "Mayoral histories cover verified Canadian public-election candidacies "
                "nationwide with no year cutoff. Councillor histories retain the ordinary "
                "Toronto-centred Results coverage. Identity evidence standards are the same."
            ),
        },
        "candidates": candidates,
    }


def write_mayoral_candidates_feed(
    results_path: str | Path,
    career_reviews_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Read canonical CSV results and atomically write the factual JSON feed."""

    feed = build_mayoral_candidates_feed(
        pd.read_csv(results_path, low_memory=False),
        pd.read_csv(career_reviews_path, dtype="string", keep_default_na=False),
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(feed, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def write_person_aliases_feed(
    results_path: str | Path, people_path: str | Path, output_path: str | Path
) -> Path:
    """Atomically write the Results-owned exact identity crosswalk."""

    feed = build_person_aliases_feed(
        pd.read_csv(results_path, low_memory=False),
        pd.read_csv(people_path, low_memory=False),
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(feed, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination
