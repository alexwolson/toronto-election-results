"""Quality-control gates over the assembled results table.

``validate`` returns a list of human-readable issue strings; an empty list means the table passed
every gate. The gates encode the invariants a correct unified table must hold (see
docs/data-dictionary.md).
"""

from __future__ import annotations

import pandas as pd

_SHARE_TOLERANCE = 1e-6


def validate(df: pd.DataFrame) -> list[str]:
    issues: list[str] = []

    # Every contest has at least one winner.
    elected_per_contest = df.groupby("contest_id")["elected"].sum()
    for contest_id in elected_per_contest[elected_per_contest < 1].index:
        issues.append(f"no elected candidate in contest {contest_id}")

    # No duplicate candidate rows within a contest.
    duplicates = int(df.duplicated(subset=["contest_id", "candidate_name_raw"]).sum())
    if duplicates:
        issues.append(f"{duplicates} duplicate (contest_id, candidate_name_raw) rows")

    # Acclaimed rows carry no ballots and are winners.
    acclaimed = df[df["acclaimed"]]
    if acclaimed["votes"].notna().any():
        issues.append("acclaimed rows have non-null votes")
    if not acclaimed["elected"].all():
        issues.append("acclaimed rows not marked elected")

    contested = df[~df["acclaimed"]]

    # Vote shares sum to 1 within each contested contest.
    share_sums = contested.groupby("contest_id")["vote_share"].sum()
    for contest_id, total in share_sums[(share_sums - 1).abs() > _SHARE_TOLERANCE].items():
        issues.append(f"vote_share sums to {total:.6f} (not 1) in contest {contest_id}")

    # The exposed denominator equals the actual sum of votes.
    for contest_id, group in contested.groupby("contest_id"):
        actual = int(group["votes"].sum())
        exposed = int(group["total_contest_votes"].iloc[0])
        if actual != exposed:
            issues.append(
                f"total_contest_votes {exposed} != sum(votes) {actual} in contest {contest_id}"
            )

    # No negative vote counts.
    if (contested["votes"].dropna() < 0).any():
        issues.append("negative votes present")

    # Electorate / turnout sanity (where present).
    if "eligible_electors" in df.columns:
        electorate = df[df["eligible_electors"].notna()]
        if ((electorate["turnout"] <= 0) | (electorate["turnout"] > 1)).any():
            issues.append("turnout outside (0, 1]")
        if (electorate["ballots_cast"] > electorate["eligible_electors"]).any():
            issues.append("ballots_cast exceeds eligible_electors")
        contested_stats = electorate[~electorate["acclaimed"]]
        if (contested_stats["ballots_cast"] < contested_stats["total_contest_votes"]).any():
            issues.append("more valid votes than ballots cast (ballots_cast < total_contest_votes)")

    return issues


if __name__ == "__main__":
    from pathlib import Path

    table = pd.read_parquet(Path("data/out/toronto_election_results.parquet"))
    problems = validate(table)
    if problems:
        print(f"{len(problems)} issue(s):")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print(f"OK: {len(table)} rows passed all QC gates")
