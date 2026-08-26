"""Cross-table quality gates for the expanded election-results release."""

from __future__ import annotations

import math

import pandas as pd

_GEOMETRY_CONTAINMENT_RELATIVE_TOLERANCE = 1e-12
_GEOMETRY_CONTAINMENT_ABSOLUTE_TOLERANCE = 1e-18
_COMPLETED_RESULTS_END = pd.Timestamp("2026-08-20")
_PENDING_EVENT_END = pd.Timestamp("2026-10-26")


def _duplicate_issue(frame: pd.DataFrame, key: str, table: str, issues: list[str]) -> None:
    if key not in frame:
        issues.append(f"{table} is missing {key}")
    elif frame[key].isna().any() or frame[key].duplicated().any():
        issues.append(f"{table}.{key} must be non-null and unique")


def _foreign_key_issue(
    child: pd.DataFrame,
    child_key: str,
    parent: pd.DataFrame,
    parent_key: str,
    label: str,
    issues: list[str],
) -> None:
    if child_key not in child or parent_key not in parent:
        issues.append(f"cannot validate {label} foreign key because its column is missing")
        return
    values = child.loc[child[child_key].notna(), child_key]
    missing = ~values.isin(parent[parent_key])
    if missing.any():
        issues.append(f"broken {label} foreign key: {values.loc[missing].iloc[0]!r}")


def _agreement_issues(
    child: pd.DataFrame,
    parent: pd.DataFrame,
    *,
    key: str,
    columns: list[str],
    child_label: str,
    parent_label: str,
    issues: list[str],
) -> None:
    """Require repeated public labels to agree with their keyed dimension."""

    missing = sorted({key, *columns} - set(child.columns))
    missing.extend(sorted({key, *columns} - set(parent.columns)))
    if missing:
        issues.append(
            f"cannot validate {child_label}/{parent_label} agreement because columns are missing: "
            f"{', '.join(sorted(set(missing)))}"
        )
        return

    if child[key].isna().any():
        issues.append(f"{child_label} requires a non-null {key}")

    # Duplicate parent keys are reported independently. Keeping one row here lets
    # agreement checks continue and disclose other release defects in the same run.
    parent_values = parent[[key, *columns]].drop_duplicates(key, keep="first")
    joined = child.loc[child[key].notna(), [key, *columns]].merge(
        parent_values,
        on=key,
        how="left",
        suffixes=("_child", "_parent"),
        indicator=True,
    )
    matched = joined["_merge"].eq("both")
    for column in columns:
        child_values = joined[f"{column}_child"]
        parent_values = joined[f"{column}_parent"]
        both_missing = child_values.isna() & parent_values.isna()
        both_present = child_values.notna() & parent_values.notna()
        equal = both_missing.copy()
        equal.loc[both_present] = child_values.loc[both_present].eq(parent_values.loc[both_present])
        disagreement = matched & ~equal
        if disagreement.any():
            bad_key = joined.loc[disagreement, key].iloc[0]
            issues.append(
                f"{child_label}.{column} must match {parent_label}.{column} via {key}={bad_key!r}"
            )


def _election_date_issues(frame: pd.DataFrame, table_label: str, issues: list[str]) -> None:
    """Enforce the public upper bound and date/year consistency.

    Historical career records intentionally have no lower date bound.
    """

    if "election_date" not in frame:
        issues.append(f"{table_label} is missing election_date")
        return
    parsed = pd.to_datetime(frame["election_date"], errors="coerce")
    if parsed.isna().any():
        issues.append(f"{table_label}.election_date must contain valid non-null dates")
        return
    outside = parsed.gt(_PENDING_EVENT_END)
    if outside.any():
        value = frame.loc[outside, "election_date"].iloc[0]
        issues.append(
            f"{table_label}.election_date {value!r} is after the pending "
            "2026-10-26 municipal event"
        )
    if "election_year" not in frame:
        issues.append(f"{table_label} is missing election_year")
        return
    reported_year = pd.to_numeric(frame["election_year"], errors="coerce")
    wrong_year = reported_year.isna() | reported_year.ne(parsed.dt.year)
    if wrong_year.any():
        issues.append(f"{table_label}.election_year must equal the year of election_date")


def _materially_outside(city, district) -> bool:
    """Distinguish a real containment failure from GEOS floating-point slivers."""

    if city.covers(district):
        return False
    outside_area = float(district.difference(city).area)
    tolerance = max(
        _GEOMETRY_CONTAINMENT_ABSOLUTE_TOLERANCE,
        float(district.area) * _GEOMETRY_CONTAINMENT_RELATIVE_TOLERANCE,
    )
    return not math.isfinite(outside_area) or outside_area > tolerance


def validate_release(
    candidacies: pd.DataFrame,
    events: pd.DataFrame,
    contests: pd.DataFrame,
    parties: pd.DataFrame,
    districts: pd.DataFrame,
    people: pd.DataFrame,
    office_tenures: pd.DataFrame | None = None,
    candidacy_person_links: pd.DataFrame | None = None,
) -> list[str]:
    """Return human-readable violations of the public relational contract."""

    issues: list[str] = []
    _duplicate_issue(candidacies, "candidacy_id", "candidacies", issues)
    _duplicate_issue(events, "event_id", "events", issues)
    _duplicate_issue(contests, "contest_id", "contests", issues)
    _duplicate_issue(parties, "party_id", "parties", issues)
    _duplicate_issue(districts, "district_id", "districts", issues)
    _duplicate_issue(people, "person_id", "people", issues)

    _foreign_key_issue(candidacies, "contest_id", contests, "contest_id", "contest", issues)
    _foreign_key_issue(contests, "event_id", events, "event_id", "event", issues)
    _foreign_key_issue(contests, "district_id", districts, "district_id", "district", issues)
    _foreign_key_issue(candidacies, "party_id", parties, "party_id", "party", issues)
    _foreign_key_issue(candidacies, "person_id", people, "person_id", "person", issues)

    _election_date_issues(events, "Election event", issues)
    _election_date_issues(candidacies, "Candidacy", issues)
    _agreement_issues(
        candidacies,
        events,
        key="event_id",
        columns=["election_date", "election_year", "election_type", "election_authority"],
        child_label="Candidacy",
        parent_label="Election event",
        issues=issues,
    )
    _agreement_issues(
        candidacies,
        contests,
        key="contest_id",
        columns=[
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
            "turnout",
            "turnout_scope",
            "source_authority",
            "source_resource",
            "source_detail",
        ],
        child_label="Candidacy",
        parent_label="Contest",
        issues=issues,
    )
    district_labels = [
        "represented_body",
        "boundary_regime",
        "official_district_id",
        "district_name",
    ]
    _agreement_issues(
        contests,
        districts,
        key="district_id",
        columns=district_labels,
        child_label="Contest",
        parent_label="Electoral district",
        issues=issues,
    )
    _agreement_issues(
        candidacies,
        districts,
        key="district_id",
        columns=district_labels,
        child_label="Candidacy",
        parent_label="Electoral district",
        issues=issues,
    )

    if office_tenures is not None:
        _duplicate_issue(office_tenures, "office_tenure_id", "office_tenures", issues)
        _foreign_key_issue(
            office_tenures,
            "person_id",
            people,
            "person_id",
            "office-tenure Person",
            issues,
        )
        if "incumbent_office_tenure_id" in candidacies:
            _foreign_key_issue(
                candidacies,
                "incumbent_office_tenure_id",
                office_tenures,
                "office_tenure_id",
                "incumbency tenure",
                issues,
            )

    if candidacy_person_links is not None:
        _foreign_key_issue(
            candidacy_person_links,
            "candidacy_id",
            candidacies,
            "candidacy_id",
            "identity-link Candidacy",
            issues,
        )
        _foreign_key_issue(
            candidacy_person_links,
            "person_id",
            people,
            "person_id",
            "identity-link Person",
            issues,
        )

    required = {
        "contest_id",
        "affiliation_status",
        "party_id",
        "votes",
        "total_contest_votes",
        "vote_share",
        "vote_rank",
        "elected",
        "acclaimed",
        "outcome_method",
        "result_status",
        "coverage_status",
    }
    missing = sorted(required - set(candidacies.columns))
    if missing:
        issues.append(f"candidacies is missing result columns: {', '.join(missing)}")
        return issues

    if "source_candidacy_id" not in candidacies:
        issues.append("Candidacy.source_candidacy_id must be non-null and non-blank")
    else:
        source_ids = candidacies["source_candidacy_id"]
        missing_source_id = source_ids.isna() | source_ids.astype("string").str.strip().eq("")
        if missing_source_id.any():
            issues.append("Candidacy.source_candidacy_id must be non-null and non-blank")

    party_relationship = candidacies["affiliation_status"].eq("party")
    if (party_relationship & candidacies["party_id"].isna()).any():
        issues.append("party affiliation must reference a party")
    if ((~party_relationship) & candidacies["party_id"].notna()).any():
        issues.append("non-party affiliation must not reference a party")
    if "party_name" in candidacies and "canonical_name" in parties:
        party_labels = candidacies.loc[
            candidacies["party_id"].notna(), ["party_id", "party_name"]
        ].merge(
            parties[["party_id", "canonical_name"]],
            on="party_id",
            how="left",
            validate="many_to_one",
        )
        if party_labels["party_name"].ne(party_labels["canonical_name"]).any():
            issues.append("Candidacy party_name must match the Party canonical_name")
        if candidacies.loc[candidacies["party_id"].isna(), "party_name"].notna().any():
            issues.append("a Candidacy without a Party must have null party_name")
    if (candidacies["votes"].dropna() < 0).any():
        issues.append("candidate votes cannot be negative")

    parsed_dates = pd.to_datetime(candidacies["election_date"], errors="coerce")
    future_completed = parsed_dates.gt(_COMPLETED_RESULTS_END) & ~candidacies["result_status"].eq(
        "pending"
    )
    if future_completed.any():
        issues.append("post-cutoff Candidacies must have result_status=pending")

    for contest_id, group in candidacies.groupby("contest_id", sort=False, dropna=False):
        methods = group["outcome_method"].dropna().unique()
        result_statuses = group["result_status"].dropna().unique()
        coverages = group["coverage_status"].dropna().unique()
        if len(methods) != 1 or len(result_statuses) != 1 or len(coverages) != 1:
            issues.append(
                f"contest {contest_id!r} has inconsistent result, outcome, or coverage metadata"
            )
            continue
        method = methods[0]
        result_status = result_statuses[0]
        coverage = coverages[0]

        if result_status == "pending":
            numeric = group[["votes", "total_contest_votes", "vote_share", "vote_rank"]]
            if (
                method != "pending"
                or coverage != "complete"
                or not numeric.isna().all().all()
                or group["elected"].notna().any()
                or group["acclaimed"].fillna(False).any()
            ):
                issues.append(
                    f"contest {contest_id!r} pending result must have a complete candidate "
                    "roster and null result values"
                )
            continue

        if result_status != "final":
            issues.append(f"contest {contest_id!r} has unknown result_status {result_status!r}")
            continue

        if method == "acclamation":
            numeric = group[["votes", "total_contest_votes", "vote_share", "vote_rank"]]
            if len(group) != 1 or not numeric.isna().all().all() or group["elected"].ne(True).any():
                issues.append(
                    f"contest {contest_id!r} acclamation must have one elected row and null votes"
                )
            continue

        if coverage == "candidate_record":
            numeric = group[
                ["votes", "total_contest_votes", "vote_share", "vote_rank", "n_candidates"]
            ]
            if numeric.isna().any().any():
                issues.append(
                    f"candidate-record contest {contest_id!r} requires exact reported metrics"
                )
                continue
            invalid = (
                group["total_contest_votes"].le(0)
                | group["votes"].gt(group["total_contest_votes"])
                | group["vote_share"].lt(0)
                | group["vote_share"].gt(1)
                | group["vote_rank"].lt(1)
                | group["vote_rank"].gt(group["n_candidates"])
                | group["n_candidates"].lt(len(group))
            )
            expected_share = group["votes"].astype(float) / group[
                "total_contest_votes"
            ].astype(float)
            inconsistent_share = [
                not math.isclose(float(actual), float(expected), abs_tol=1e-12)
                for actual, expected in zip(group["vote_share"], expected_share, strict=True)
            ]
            if invalid.any() or any(inconsistent_share):
                issues.append(
                    f"candidate-record contest {contest_id!r} has inconsistent reported metrics"
                )
            continue

        if coverage != "complete":
            if coverage == "source_missing":
                issues.append(
                    f"source-missing contest {contest_id!r} cannot publish Candidacy rows"
                )
            if group["total_contest_votes"].notna().any() or group["vote_share"].notna().any():
                issues.append(
                    f"contest {contest_id!r} with incomplete coverage cannot publish complete metrics"
                )
            continue

        if method not in {"void", "required_by_election", "tie_no_election", "source_missing"}:
            elected_count = int(group["elected"].fillna(False).sum())
            if elected_count != 1:
                issues.append(f"contest {contest_id!r} must have exactly one elected candidacy")

        if group["votes"].isna().any():
            issues.append(f"complete vote contest {contest_id!r} has null candidate votes")
            continue
        expected_total = int(group["votes"].sum())
        reported_totals = group["total_contest_votes"].dropna().unique()
        if len(reported_totals) != 1 or int(reported_totals[0]) != expected_total:
            issues.append(f"contest {contest_id!r} total votes do not reconcile")
        if expected_total > 0:
            share_sum = group["vote_share"].sum(min_count=1)
            if pd.isna(share_sum) or not math.isclose(float(share_sum), 1.0, abs_tol=1e-9):
                issues.append(f"contest {contest_id!r} vote shares do not sum to one")
        elif group["vote_share"].notna().any():
            issues.append(f"zero-vote contest {contest_id!r} must have null vote shares")

    if {"eligible_electors", "ballots_cast", "turnout"}.issubset(contests.columns):
        invalid_denominator = contests["eligible_electors"].notna() & contests[
            "eligible_electors"
        ].lt(0)
        if invalid_denominator.any():
            issues.append("eligible_electors cannot be negative")
        mismatched_turnout = contests["eligible_electors"].isna() ^ contests["ballots_cast"].isna()
        if mismatched_turnout.any():
            issues.append("turnout operands must be reported at the same scope")
        too_many_ballots = contests["eligible_electors"].notna() & contests["ballots_cast"].gt(
            contests["eligible_electors"]
        )
        if too_many_ballots.any():
            issues.append("ballots_cast cannot exceed eligible_electors")
        invalid_turnout = contests["turnout"].notna() & (
            contests["turnout"].lt(0) | contests["turnout"].gt(1)
        )
        if invalid_turnout.any():
            issues.append("turnout must be in [0, 1]")
        zero_denominator_with_turnout = (
            contests["eligible_electors"].eq(0) & contests["turnout"].notna()
        )
        if zero_denominator_with_turnout.any():
            issues.append("zero eligible-elector denominator requires null turnout")
        missing_turnout = (
            contests["eligible_electors"].gt(0)
            & contests["ballots_cast"].notna()
            & contests["turnout"].isna()
        )
        if missing_turnout.any():
            issues.append("positive turnout operands require a derived turnout")
        valid_denominator = (
            contests["eligible_electors"].gt(0)
            & contests["ballots_cast"].notna()
            & contests["turnout"].notna()
        )
        expected_turnout = contests.loc[valid_denominator, "ballots_cast"].astype(
            float
        ) / contests.loc[valid_denominator, "eligible_electors"].astype(float)
        reported_turnout = contests.loc[valid_denominator, "turnout"].astype(float)
        if not all(
            math.isclose(reported, expected, abs_tol=1e-12)
            for reported, expected in zip(reported_turnout, expected_turnout, strict=True)
        ):
            issues.append("turnout does not reconcile with its operands")
        if "turnout_scope" in contests:
            has_operands = contests["eligible_electors"].notna() & contests["ballots_cast"].notna()
            if (has_operands & contests["turnout_scope"].isna()).any():
                issues.append("reported turnout operands require an explicit turnout_scope")
            if ((~has_operands) & contests["turnout_scope"].notna()).any():
                issues.append("turnout_scope must be null when turnout operands are unavailable")

    if {"incumbent", "incumbent_office_tenure_id", "person_id"}.issubset(candidacies.columns):
        incumbent_true = candidacies["incumbent"].eq(True).fillna(False)
        missing_evidence = incumbent_true & (
            candidacies["person_id"].isna() | candidacies["incumbent_office_tenure_id"].isna()
        )
        if missing_evidence.any():
            issues.append("incumbent=true requires a Person and supporting Office tenure")
        stray_tenure = ~incumbent_true & candidacies["incumbent_office_tenure_id"].notna()
        if stray_tenure.any():
            issues.append("only incumbent=true may reference an Office tenure")

        if office_tenures is not None and not office_tenures.empty:
            evidence_rows = candidacies.loc[
                candidacies["incumbent_office_tenure_id"].notna(),
                [
                    "incumbent_office_tenure_id",
                    "person_id",
                    "represented_body",
                    "office_type",
                ],
            ].merge(
                office_tenures[
                    ["office_tenure_id", "person_id", "represented_body", "office_type"]
                ],
                left_on="incumbent_office_tenure_id",
                right_on="office_tenure_id",
                how="left",
                suffixes=("_candidacy", "_tenure"),
            )
            mismatch = (
                evidence_rows["person_id_candidacy"].ne(evidence_rows["person_id_tenure"])
                | evidence_rows["represented_body_candidacy"].ne(
                    evidence_rows["represented_body_tenure"]
                )
                | evidence_rows["office_type_candidacy"].ne(evidence_rows["office_type_tenure"])
            )
            if mismatch.fillna(True).any():
                issues.append(
                    "incumbency tenure must match the Candidacy Person, represented body, and office"
                )

    if candidacy_person_links is not None and "person_id" in candidacies:
        active_confirmed = candidacy_person_links.loc[
            candidacy_person_links["link_status"].eq("confirmed")
            & candidacy_person_links["valid_to_release"].isna(),
            ["candidacy_id", "person_id"],
        ].drop_duplicates()
        published_people = candidacies.loc[
            candidacies["person_id"].notna(), ["candidacy_id", "person_id"]
        ]
        supported = published_people.merge(
            active_confirmed,
            on=["candidacy_id", "person_id"],
            how="left",
            indicator=True,
        )
        if supported["_merge"].ne("both").any():
            issues.append("published Candidacy Person requires an active confirmed identity link")

    if {"geometry_status", "geometry"}.issubset(districts.columns):
        available = districts["geometry_status"].eq("available")
        if (available & districts["geometry"].isna()).any():
            issues.append("available electoral-district geometry cannot be null")
        if ((~available) & districts["geometry"].notna()).any():
            issues.append("unavailable electoral-district geometry must be null")
        for geometry in districts.loc[available, "geometry"]:
            if (
                geometry.is_empty
                or not geometry.is_valid
                or geometry.geom_type not in {"Polygon", "MultiPolygon"}
            ):
                issues.append("available electoral-district geometry must be valid polygonal data")
                break

        council = districts.loc[
            available & districts["represented_body"].eq("toronto_city_council")
        ]
        for regime, group in council.groupby("boundary_regime", sort=False):
            cities = group.loc[group["official_district_id"].eq("city"), "geometry"]
            wards = group.loc[group["official_district_id"].ne("city"), "geometry"]
            if len(cities) != 1 or any(_materially_outside(cities.iloc[0], ward) for ward in wards):
                issues.append(f"council geometry is not contained by its city union for {regime}")

    return issues
