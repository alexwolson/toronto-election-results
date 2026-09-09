"""Factual frontend feeds derived only from the canonical results release."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pandas as pd

from .person_alias_curations import load_person_alias_curations
from .trustee_2026 import load_trustee_ward_crosswalk
from .trustee_career import (
    COHORT_ID as TRUSTEE_COHORT_ID,
)
from .trustee_career import (
    CURRENT_ELECTION_DATE as TRUSTEE_ELECTION_DATE,
)
from .trustee_career import (
    EXPECTED_CONTEST_COUNTS as TRUSTEE_CONTEST_COUNTS,
)
from .trustee_career import (
    MINIMUM_HISTORY_DATE as TRUSTEE_MINIMUM_HISTORY_DATE,
)
from .trustee_career import (
    is_toronto_occurrence,
)
from .trustee_continuity import load_trustee_continuity, validate_trustee_continuity

MAYORAL_CANDIDATES_SCHEMA_VERSION = 5
TRUSTEE_RACES_SCHEMA_VERSION = 3
PERSON_ALIASES_SCHEMA_VERSION = 1
_TORONTO_COUNCIL = "toronto_city_council"
_CERTIFIED_CANDIDATES_RESOURCE = "2026 Municipal Election — Certified Candidates"


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


def attach_district_display_names(results: pd.DataFrame, districts: pd.DataFrame) -> pd.DataFrame:
    required_results = {"district_id"}
    required_districts = {"district_id", "district_display_name"}
    if missing := sorted(required_results - set(results.columns)):
        raise ValueError(f"canonical results are missing district columns: {', '.join(missing)}")
    if missing := sorted(required_districts - set(districts.columns)):
        raise ValueError(f"district dimension is missing display columns: {', '.join(missing)}")
    if districts["district_id"].duplicated().any():
        raise ValueError("district dimension repeats district_id")
    return results.drop(columns="district_display_name", errors="ignore").merge(
        districts[["district_id", "district_display_name"]],
        on="district_id",
        how="left",
        validate="many_to_one",
    )


def build_person_aliases_feed(
    results: pd.DataFrame,
    people: pd.DataFrame,
    curated_aliases: pd.DataFrame | None = None,
) -> dict[str, object]:
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
    if curated_aliases is not None:
        required_aliases = {"reported_name", "person_id"}
        if missing := sorted(required_aliases - set(curated_aliases.columns)):
            raise ValueError(f"curated aliases are missing columns: {', '.join(missing)}")
        for row in curated_aliases.itertuples(index=False):
            person_id = str(row.person_id)
            if person_id not in active_ids:
                raise ValueError(f"curated alias references inactive Person {person_id!r}")
            alias = str(row.reported_name).strip()
            if not alias:
                raise ValueError("curated alias reported_name cannot be blank")
            names.add((_name_key(alias), alias, person_id))

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
                "district_display_name": _text(head.get("district_display_name")),
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


def _comparable_prior_result(rows: pd.DataFrame) -> dict[str, object] | None:
    """Return a Council-compatible result summary when the prior contest had a vote."""

    if rows.empty or rows["outcome_method"].nunique(dropna=False) != 1:
        raise ValueError("comparable trustee contest has inconsistent outcomes")
    if str(rows["outcome_method"].iloc[0]) == "acclamation":
        return None
    if str(rows["outcome_method"].iloc[0]) != "vote":
        raise ValueError("comparable trustee contest must be a vote or acclamation")
    if not rows["result_status"].eq("final").all():
        raise ValueError("comparable trustee contest must be final")

    elected = rows.loc[rows["elected"].map(_truth) | rows["acclaimed"].map(_truth)]
    if len(elected) != 1:
        raise ValueError("comparable trustee contest must have exactly one winner")
    winner = elected.iloc[0]
    winner_share = _number(winner["vote_share"])
    winner_votes = _integer(winner["votes"])
    if winner_share is None or winner_votes is None:
        raise ValueError("comparable trustee vote is missing winner totals")

    ranked = rows.assign(_rank=pd.to_numeric(rows["vote_rank"], errors="coerce")).sort_values(
        ["_rank", "votes"], ascending=[True, False], kind="stable"
    )
    runners = ranked.loc[ranked["_rank"].eq(2)]
    runner = runners.iloc[0] if len(runners) == 1 else None
    runner_share = _number(runner["vote_share"]) if runner is not None else None
    runner_votes = _integer(runner["votes"]) if runner is not None else None
    field_size = max(
        (_integer(value) for value in rows["n_candidates"] if _integer(value) is not None),
        default=len(rows),
    )
    return {
        "year": int(str(winner["election_date"])[:4]),
        "winner_name": str(winner["candidate_name"]),
        "winner_share": winner_share,
        "winner_votes": winner_votes,
        "runner_up_name": str(runner["candidate_name"]) if runner is not None else None,
        "runner_up_share": runner_share,
        "margin_votes": winner_votes - runner_votes if runner_votes is not None else None,
        "margin_share": winner_share - runner_share if runner_share is not None else None,
        "field_size": field_size,
    }


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
        raise ValueError(f"career reviews are missing feed columns: {', '.join(missing_reviews)}")
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
        and current["source_resource"].eq(_CERTIFIED_CANDIDATES_RESOURCE).all()
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
                "campaign_url": _text(candidate.get("campaign_url")),
                "is_incumbent": person_id == incumbent_person_id,
                "review_status": str(review["review_status"]),
                "review_limitations": _text(review["public_coverage_note"]),
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


def build_trustee_races_feed(
    results: pd.DataFrame,
    ward_crosswalk: pd.DataFrame,
    contest_continuity: pd.DataFrame,
    career_cohort: pd.DataFrame,
    career_reviews: pd.DataFrame,
    career_decisions: pd.DataFrame,
) -> dict[str, object]:
    """Build the certified trustee field and only its occurrence-verified history.

    Current candidates come from the canonical pending Candidacies. Historical
    rows are admitted only when the completed Luna/Terra review records an
    occurrence-level ``confirm`` decision. No name matching happens here.
    """

    validate_trustee_continuity(contest_continuity, results, ward_crosswalk)

    required_results = {
        "candidacy_id",
        "person_id",
        "event_id",
        "contest_id",
        "election_date",
        "represented_body",
        "office_type",
        "official_district_id",
        "district_name",
        "district_display_name",
        "candidate_name",
        "candidate_name_raw",
        "party_name",
        "outcome_method",
        "result_status",
        "coverage_status",
        "source_resource",
        "elected",
        "acclaimed",
        "votes",
        "vote_share",
        "vote_rank",
        "n_candidates",
        "incumbent",
    }
    missing_results = sorted(required_results - set(results.columns))
    if missing_results:
        raise ValueError(
            "canonical results are missing trustee-feed columns: " + ", ".join(missing_results)
        )

    required_cohort = {
        "cohort_id",
        "subject_candidacy_id",
        "source_order",
        "source_release",
    }
    required_reviews = {
        "cohort_id",
        "subject_candidacy_id",
        "review_date",
        "review_status",
    }
    required_decisions = {
        "cohort_id",
        "subject_candidacy_id",
        "prior_candidacy_id",
        "decision",
    }
    required_crosswalk = {
        "board_id",
        "represented_body",
        "display_name",
        "short_name",
        "boundary_regime",
        "ward_id",
        "district_name",
        "district_display_name",
        "city_wards",
    }
    for label, table, required in (
        ("ward crosswalk", ward_crosswalk, required_crosswalk),
        ("career cohort", career_cohort, required_cohort),
        ("career reviews", career_reviews, required_reviews),
        ("career decisions", career_decisions, required_decisions),
    ):
        missing = sorted(required - set(table.columns))
        if missing:
            raise ValueError(f"trustee {label} is missing feed columns: {', '.join(missing)}")

    current = results.loc[
        results["election_date"].astype("string").eq(TRUSTEE_ELECTION_DATE)
        & results["office_type"].eq("trustee")
        & results["represented_body"].isin(TRUSTEE_CONTEST_COUNTS)
        & results["result_status"].isin({"pending", "final"})
    ].copy()
    if current.empty:
        raise ValueError("canonical results contain no certified 2026 Toronto trustee field")
    if current["candidacy_id"].isna().any() or current["candidacy_id"].duplicated().any():
        raise ValueError("current trustee candidacy_id values must be non-null and unique")
    if current["event_id"].nunique(dropna=False) != 1:
        raise ValueError("current trustee field must have exactly one event_id")
    actual_contests = current.groupby("represented_body")["contest_id"].nunique().to_dict()
    if actual_contests != TRUSTEE_CONTEST_COUNTS:
        raise ValueError(f"unexpected trustee board contest coverage: {actual_contests}")
    certified = (
        current["coverage_status"].eq("complete").all()
        and current["source_resource"].eq(_CERTIFIED_CANDIDATES_RESOURCE).all()
    )
    if not certified:
        raise ValueError("current trustee field is not a complete certified roster")

    current_ids = set(current["candidacy_id"].astype(str))
    for label, table in (("cohort", career_cohort), ("reviews", career_reviews)):
        ids = table["subject_candidacy_id"].astype(str)
        if ids.duplicated().any() or set(ids) != current_ids:
            raise ValueError(f"trustee career {label} must exactly cover the certified field")
        if not table["cohort_id"].eq(TRUSTEE_COHORT_ID).all():
            raise ValueError(f"trustee career {label} must use cohort {TRUSTEE_COHORT_ID}")
    if not career_decisions.empty and not career_decisions["cohort_id"].eq(TRUSTEE_COHORT_ID).all():
        raise ValueError(f"trustee career decisions must use cohort {TRUSTEE_COHORT_ID}")

    allowed_statuses = {"reviewed", "reviewed_with_limitations"}
    if not set(career_reviews["review_status"]).issubset(allowed_statuses):
        raise ValueError("trustee career reviews contain an unpublished review status")
    source_releases = career_cohort["source_release"].dropna().astype(str).unique()
    review_dates = career_reviews["review_date"].dropna().astype(str).unique()
    if len(source_releases) != 1 or len(review_dates) != 1:
        raise ValueError("trustee career records must use one source release and review date")

    confirmed = career_decisions.loc[career_decisions["decision"].eq("confirm")].copy()
    if confirmed.duplicated(["subject_candidacy_id", "prior_candidacy_id"]).any():
        raise ValueError("trustee career decisions repeat a confirmed occurrence")
    outside_subjects = set(confirmed["subject_candidacy_id"].astype(str)) - current_ids
    if outside_subjects:
        raise ValueError("trustee career decisions reference a candidate outside the field")

    by_candidacy = results.set_index("candidacy_id", drop=False)
    continuity_by_contest = contest_continuity.set_index("current_contest_id")
    cohort_order = career_cohort.set_index("subject_candidacy_id")["source_order"]
    boards: list[dict[str, object]] = []
    board_rows = ward_crosswalk.sort_values(["board_id", "ward_id"], kind="stable")
    board_order = ["tdsb", "tcdsb", "viamonde", "monavenir"]
    if set(board_rows["board_id"]) != set(board_order):
        raise ValueError("trustee ward crosswalk must contain the four expected boards")
    for board_id in board_order:
        board_crosswalk = board_rows.loc[board_rows["board_id"].eq(board_id)].copy()
        represented_body = str(board_crosswalk["represented_body"].iloc[0])
        board_current = current.loc[current["represented_body"].eq(represented_body)].copy()
        wards: list[dict[str, object]] = []
        for crosswalk_row in board_crosswalk.sort_values("ward_id").itertuples(index=False):
            ward_rows = board_current.loc[
                pd.to_numeric(board_current["official_district_id"], errors="coerce").eq(
                    int(crosswalk_row.ward_id)
                )
            ].copy()
            if ward_rows.empty or ward_rows["contest_id"].nunique() != 1:
                raise ValueError(
                    f"trustee crosswalk does not resolve {board_id} ward {crosswalk_row.ward_id}"
                )
            contest_id = str(ward_rows["contest_id"].iloc[0])
            continuity = continuity_by_contest.loc[contest_id]
            prior_contest_id = _text(continuity["prior_contest_id"])
            prior_result = (
                _comparable_prior_result(results.loc[results["contest_id"].eq(prior_contest_id)])
                if prior_contest_id is not None
                else None
            )
            if not ward_rows["district_name"].eq(crosswalk_row.district_name).all():
                raise ValueError(
                    f"trustee district name differs from the crosswalk for {contest_id}"
                )
            for column in ("result_status", "outcome_method"):
                if ward_rows[column].nunique(dropna=False) != 1:
                    raise ValueError(f"trustee contest has inconsistent {column}: {contest_id}")
            ward_rows = ward_rows.assign(
                _source_order=ward_rows["candidacy_id"].map(cohort_order).astype(int)
            ).sort_values("_source_order", kind="stable")
            candidates: list[dict[str, object]] = []
            for _, candidate in ward_rows.iterrows():
                candidacy_id = str(candidate["candidacy_id"])
                person_id = _text(candidate["person_id"])
                subject_decisions = confirmed.loc[
                    confirmed["subject_candidacy_id"].eq(candidacy_id)
                ]
                prior_ids = subject_decisions["prior_candidacy_id"].astype(str).tolist()
                unknown = [prior_id for prior_id in prior_ids if prior_id not in by_candidacy.index]
                if unknown:
                    raise ValueError(f"trustee career decision references unknown {unknown[0]}")
                history_rows = (
                    by_candidacy.loc[prior_ids].copy() if prior_ids else results.iloc[0:0]
                )
                if isinstance(history_rows, pd.Series):
                    history_rows = history_rows.to_frame().T
                for _, prior in history_rows.iterrows():
                    prior_date = str(prior["election_date"])
                    if not (
                        TRUSTEE_MINIMUM_HISTORY_DATE <= prior_date < TRUSTEE_ELECTION_DATE
                        and prior["result_status"] == "final"
                        and is_toronto_occurrence(prior)
                    ):
                        raise ValueError("confirmed trustee history is outside the public scope")
                    if person_id is None or _text(prior["person_id"]) != person_id:
                        raise ValueError(
                            "confirmed trustee history does not share a canonical Person"
                        )
                incumbent = True if _truth(candidate["incumbent"]) else None
                candidates.append(
                    {
                        "candidacy_id": candidacy_id,
                        "person_id": person_id,
                        "display_name": str(candidate["candidate_name"]),
                        "campaign_url": _text(candidate.get("campaign_url")),
                        "is_incumbent": incumbent,
                        "past_elections": _past_elections(history_rows),
                    }
                )
            wards.append(
                {
                    "contest_id": str(contest_id),
                    "ward_id": str(int(crosswalk_row.ward_id)),
                    "district_name": str(crosswalk_row.district_display_name),
                    "city_wards": [int(value) for value in crosswalk_row.city_wards],
                    "result_status": str(ward_rows["result_status"].iloc[0]),
                    "outcome_method": str(ward_rows["outcome_method"].iloc[0]),
                    "acclaimed": all(_truth(value) for value in ward_rows["acclaimed"]),
                    "comparable_prior_result": prior_result,
                    "candidates": candidates,
                }
            )
        boards.append(
            {
                "board_id": board_id,
                "represented_body": represented_body,
                "display_name": str(board_crosswalk["display_name"].iloc[0]),
                "short_name": str(board_crosswalk["short_name"].iloc[0]),
                "boundary_regime": str(board_crosswalk["boundary_regime"].iloc[0]),
                "candidate_count": len(board_current),
                "wards": wards,
            }
        )

    return {
        "schema_version": TRUSTEE_RACES_SCHEMA_VERSION,
        "event_id": str(current["event_id"].iloc[0]),
        "election_date": TRUSTEE_ELECTION_DATE,
        "ballot_certified": True,
        "coverage": {
            "policy": "verified_toronto_electoral_history_since_2003",
            "jurisdiction": "Toronto",
            "year_cutoff": 2003,
            "cohort_id": TRUSTEE_COHORT_ID,
            "cohort_size": len(current),
            "source_release": source_releases[0],
            "review_date": review_dates[0],
            "methodology_note": (
                "Candidate histories cover verified Toronto public-election candidacies "
                "from 2003 onward. Names are linked only when independent evidence "
                "establishes that they are the same person."
            ),
        },
        "boards": boards,
    }


def write_mayoral_candidates_feed(
    results_path: str | Path,
    districts_path: str | Path,
    career_reviews_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Read canonical CSV results and atomically write the factual JSON feed."""

    results = attach_district_display_names(
        pd.read_csv(results_path, low_memory=False),
        pd.read_csv(districts_path, low_memory=False),
    )
    feed = build_mayoral_candidates_feed(
        results,
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


def write_trustee_races_feed(
    results_path: str | Path,
    districts_path: str | Path,
    ward_crosswalk_path: str | Path,
    contest_continuity_path: str | Path,
    career_cohort_path: str | Path,
    career_reviews_path: str | Path,
    career_decisions_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Read canonical trustee inputs and atomically write the public JSON feed."""

    results = attach_district_display_names(
        pd.read_csv(results_path, low_memory=False),
        pd.read_csv(districts_path, low_memory=False),
    )
    feed = build_trustee_races_feed(
        results,
        load_trustee_ward_crosswalk(ward_crosswalk_path),
        load_trustee_continuity(contest_continuity_path),
        pd.read_csv(career_cohort_path, dtype="string", keep_default_na=False),
        pd.read_csv(career_reviews_path, dtype="string", keep_default_na=False),
        pd.read_csv(career_decisions_path, dtype="string", keep_default_na=False),
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
    results_path: str | Path,
    people_path: str | Path,
    output_path: str | Path,
    *,
    curated_aliases_path: str | Path | None = None,
) -> Path:
    """Atomically write the Results-owned exact identity crosswalk."""

    feed = build_person_aliases_feed(
        pd.read_csv(results_path, low_memory=False),
        pd.read_csv(people_path, low_memory=False),
        (
            load_person_alias_curations(curated_aliases_path)
            if curated_aliases_path is not None
            else None
        ),
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
