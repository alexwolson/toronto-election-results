"""Screen for Persons who may be one individual running under a changed surname.

The same-name and near-name reviews compare Persons whose printed names match or nearly match, so a
candidate who ran again under a new surname would fall outside both. This screen lists pairs of
Persons who share a first name and ran for the same office in the same district, at most one
general election apart, never in the same election, under different surnames. The first name must
be uncommon in the release (at most six Persons). Mayoral races are left out, since every mayoral
candidate shares the one district.

Usage:
    python -I scripts/screen_surname_changes.py OUT_CSV
"""

from __future__ import annotations

import itertools
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parents[1]
RESULTS = REPO_ROOT / "data" / "out" / "election_results.csv"
MAX_FIRST_NAME_PERSONS = 6
MAX_GENERAL_ELECTIONS_BETWEEN = 1


def _words(name: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    return [word for word in re.sub(r"[^a-z ]+", " ", folded).split() if len(word) > 1]


def screen() -> pd.DataFrame:
    results = pd.read_csv(RESULTS, dtype=str, keep_default_na=False)
    general = {
        body: sorted(set(dates))
        for body, dates in results.loc[results["election_type"].eq("general")].groupby(
            "represented_body"
        )["election_date"]
    }
    runs = results.loc[results["person_id"].ne("") & results["office_type"].ne("mayor")].copy()
    runs["words"] = runs["candidate_name"].map(_words)
    runs = runs.loc[runs["words"].map(len).ge(2)]
    runs["first"] = runs["words"].str[0]
    runs["surname"] = runs["words"].str[-1]
    first_counts = runs.drop_duplicates("person_id")["first"].value_counts()

    def between(body: str, earlier: str, later: str) -> int:
        return sum(1 for day in general.get(body, []) if earlier < day < later)

    rows = []
    keys = ["represented_body", "office_type", "district_id"]
    for (body, office, _), contests in runs.groupby(keys):
        persons = contests.groupby("person_id").agg(
            first=("first", "first"),
            surnames=("surname", set),
            dates=("election_date", lambda dates: sorted(set(dates))),
            name=("candidate_name", "first"),
            district=("district_name", "first"),
        )
        for a, b in itertools.combinations(persons.index, 2):
            one, two = persons.loc[a], persons.loc[b]
            if one["first"] != two["first"] or one["surnames"] & two["surnames"]:
                continue
            if first_counts[one["first"]] > MAX_FIRST_NAME_PERSONS:
                continue
            if set(one["dates"]) & set(two["dates"]):
                continue
            earlier, later = (one, two) if one["dates"][-1] < two["dates"][0] else (two, one)
            if earlier["dates"][-1] < later["dates"][0]:
                gap = between(body, earlier["dates"][-1], later["dates"][0])
                if gap > MAX_GENERAL_ELECTIONS_BETWEEN:
                    continue
            rows.append(
                {
                    "represented_body": body,
                    "office_type": office,
                    "district_name": earlier["district"],
                    "earlier_person_id": earlier.name,
                    "earlier_name": earlier["name"],
                    "earlier_years": ";".join(day[:4] for day in earlier["dates"]),
                    "later_person_id": later.name,
                    "later_name": later["name"],
                    "later_years": ";".join(day[:4] for day in later["dates"]),
                }
            )
    return pd.DataFrame(rows)


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit(__doc__)
    found = screen()
    found.to_csv(argv[1], index=False, lineterminator="\n")
    print(f"{len(found)} pairs")


if __name__ == "__main__":
    main(sys.argv)
