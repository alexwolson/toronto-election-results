"""Cross-check derived winners against the (authoritative) council composition.

The ``elected`` flag is derived as the top vote-getter per contest (Q9). To confirm it, every
councillor winner of election Y should be a sitting member of the council just before the *next*
election — because they took office and served. A winner who is not there is either a documented
**mid-term departure** (resignation, death, removal) or a **name-form variant** the exact-key
match missed; a fuzzy pass suppresses the variants, leaving only genuine departures to report.

If the residue is exactly the known departures, the winners are validated; anything else is a real
discrepancy to investigate.
"""

from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz, process

from .incumbency import _key

# Election Y -> the next election whose pre-election council should still hold Y's winners.
NEXT_ELECTION = {2000: 2003, 2003: 2006, 2006: 2010, 2010: 2014, 2014: 2018, 2018: 2022}
_VARIANT_THRESHOLD = 85

# Winners legitimately absent from the next council — verified, so they are not winner errors.
# Each is (election_year, ward): reason.
KNOWN_ACCOUNTED = {
    (2000, 30): "Jack Layton resigned (federal NDP leader, 2003)",
    (2000, 31): "Michael Prue resigned (MPP, 2001) -> Tziretas by-election",
    (2003, 20): "Olivia Chow resigned (MP, 2005) -> Silva appointed",
    (2003, 41): "Bas Balkissoon resigned (MPP, 2005) -> Ainslie appointed",
    (2010, 3): "Doug Holyday resigned (MPP, 2013)",
    (2014, 2): "Rob Ford died in office (2016)",
    (2014, 28): "Pam McConnell died in office (2017)",
    (2014, 42): "Raymond Cho resigned (MPP, 2016)",
    (2014, 44): "Ron Moeser died in office (2017)",
    (2018, 22): "Jim Karygiannis removed from office (2021)",
    # Name-form / attendance-window artifacts (correct winners, roster names just don't key-match):
    (2003, 10): "Michael/Mike Feldman name variant",
    (2006, 10): "Michael/Mike Feldman name variant",
    (2006, 35): "Adrian/A.A. Heaps name variant",
    (2014, 35): "Michelle Berardinetti absent from final-window attendance",
}


def crosscheck_winners(df: pd.DataFrame, composition: pd.DataFrame) -> list[tuple[int, int, str]]:
    """Return councillor winners not accounted for in the next council (expected: departures)."""
    council_names = {
        int(year): list(group["member_name"])
        for year, group in composition.groupby("election_year")
    }
    unexplained: list[tuple[int, int, str]] = []
    for year, next_year in NEXT_ELECTION.items():
        winners = df[(df["election_year"] == year) & (df["office"] == "councillor") & df["elected"]]
        pool = council_names.get(next_year, [])
        pool_keys = {_key(name) for name in pool}
        for winner in winners.itertuples(index=False):
            if _key(winner.candidate_name) in pool_keys:
                continue
            best = process.extractOne(winner.candidate_name, pool, scorer=fuzz.token_set_ratio)
            if best and best[1] >= _VARIANT_THRESHOLD:  # a name-form variant, not a departure
                continue
            unexplained.append((year, int(winner.ward_number), winner.candidate_name))
    return unexplained


def unexplained_winners(df: pd.DataFrame, composition: pd.DataFrame) -> list[tuple[int, int, str]]:
    """Winners not in the next council AND not already accounted for — should be empty."""
    return [
        residue
        for residue in crosscheck_winners(df, composition)
        if (residue[0], residue[1]) not in KNOWN_ACCOUNTED
    ]


if __name__ == "__main__":
    from pathlib import Path

    from .incumbency import build_composition

    table = pd.read_parquet(Path("data/out/toronto_election_results.parquet"))
    residue = crosscheck_winners(table, build_composition())
    print(
        f"councillor winners not in the next council (expected: mid-term departures): {len(residue)}"
    )
    for year, ward, name in residue:
        print(f"  {year} ward {ward}: {name}")
