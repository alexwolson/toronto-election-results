"""Freeze the certified 2026 trustee field as an identity-review cohort."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd

from toronto_election_results.trustee_career import (
    COHORT_COLUMNS,
    COHORT_ID,
    CURRENT_ELECTION_DATE,
    EXPECTED_CONTEST_COUNTS,
)

DEFAULT_RESULTS = Path("data/out/election_results.csv")
DEFAULT_LINKS = Path("data/out/candidacy_person_links.csv")
DEFAULT_OUTPUT = Path("data/reference/trustee_career_cohort_2026.csv")


def freeze_cohort(
    results_path: Path,
    links_path: Path,
    output_path: Path,
    *,
    source_release: str,
    source_commit: str,
) -> None:
    results = pd.read_csv(results_path, dtype="string", keep_default_na=False)
    current = results.loc[
        results["election_date"].eq(CURRENT_ELECTION_DATE)
        & results["office_type"].eq("trustee")
        & results["represented_body"].isin(EXPECTED_CONTEST_COUNTS)
    ].copy()
    if current["contest_id"].nunique() != sum(EXPECTED_CONTEST_COUNTS.values()):
        raise ValueError("current Results output does not contain all 29 trustee contests")
    if current["candidacy_id"].duplicated().any():
        raise ValueError("current Results output repeats a trustee candidacy")
    current["source_order"] = current.groupby("contest_id", sort=False).cumcount() + 1

    links = pd.read_csv(links_path, dtype="string")
    proposed = links.loc[
        links["valid_to_release"].isna()
        & links["link_status"].eq("proposed")
        & links["candidacy_id"].isin(current["candidacy_id"]),
        ["candidacy_id", "person_id"],
    ]
    if proposed["candidacy_id"].duplicated().any():
        raise ValueError("current trustee candidacy has multiple active identity proposals")
    proposed_by_id = proposed.set_index("candidacy_id")["person_id"].to_dict()

    rows = []
    for row in current.itertuples(index=False):
        rows.append(
            {
                "cohort_id": COHORT_ID,
                "subject_candidacy_id": row.candidacy_id,
                "certified_name": row.candidate_name,
                "certified_name_raw": row.candidate_name_raw,
                "represented_body": row.represented_body,
                "official_district_id": row.official_district_id,
                "contest_id": row.contest_id,
                "source_order": int(row.source_order),
                "current_person_id": row.person_id,
                "proposed_target_person_id": proposed_by_id.get(row.candidacy_id, ""),
                "source_release": source_release,
                "source_commit": source_commit,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COHORT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-release", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    freeze_cohort(
        args.results,
        args.links,
        args.output,
        source_release=args.source_release,
        source_commit=args.source_commit,
    )


if __name__ == "__main__":
    main()
