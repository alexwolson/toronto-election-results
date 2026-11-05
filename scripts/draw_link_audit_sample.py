"""Draw the random samples for the audit of Person links.

Two frames are sampled from the published release:

* Joins: every pair of consecutive Candidacies (by election date) within one Person. A pair is
  stratified by the method of the later Candidacy's confirmed link, and a fixed number of pairs
  is drawn from each stratum. A wrong pair is a false merge.
* Splits: every pair of distinct Persons that share a first and last name, ignoring middle names
  and initials. A pair that is one individual is a missed link.

The draw is reproducible from the release and the seed. Run from the repository root.
"""

from __future__ import annotations

import argparse
import itertools
import re
import unicodedata
from pathlib import Path

import pandas as pd

DEFAULT_RESULTS = Path("data/out/election_results.csv")
DEFAULT_LINKS = Path("data/out/candidacy_person_links.csv")
DEFAULT_OUTPUT = Path("docs/verification/link-audit-2026-11-03")
SEED = 20261103
STRATA = {
    "curated_official_cross_event_identity": "assertion",
    "curated_person_redirect": "assertion",
    "curated_review_confirmed": "review",
    "official_incumbent_continuity": "incumbency",
    "official_candidacy_record": "official_record",
    "municipal_authoritative_roster_exact_name": "roster",
}
JOIN_SIZES = {"assertion": 40, "review": 40, "incumbency": 15, "official_record": 15, "roster": 10}
SPLIT_SIZE = 40
BODY = {
    "canada_house_of_commons": "House of Commons",
    "ontario_legislative_assembly": "Ontario legislature",
}


def _normalise(name: str) -> list[str]:
    ascii_name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]+", " ", ascii_name.lower()).split()


def first_last(name: str) -> tuple[str, str]:
    """First and last name, ignoring single-letter initials."""

    tokens = [token for token in _normalise(name) if len(token) > 1] or _normalise(name)
    return (tokens[0], tokens[-1]) if len(tokens) > 1 else (tokens[0], "")


def describe(row: pd.Series) -> str:
    body = BODY.get(row["represented_body"], row["represented_body"].replace("_", " "))
    party = f", {row['party_name']}" if row["party_name"] else ""
    by = " by-election" if row["election_type"] == "by_election" else ""
    votes = f", {row['votes']} votes" if row["votes"] else ""
    rank = f", placed {row['vote_rank']} of {row['n_candidates']}" if row["vote_rank"] else ""
    elected = ", elected" if row["elected"] == "True" else ""
    return (
        f"{row['election_date']}{by}: {body}, {row['district_name']}{party}: "
        f"'{row['candidate_name']}'{rank}{votes}{elected}"
    )


def draw(results_path: Path, links_path: Path, output_dir: Path) -> None:
    results = pd.read_csv(results_path, dtype="string", keep_default_na=False)
    links = pd.read_csv(links_path, dtype="string", keep_default_na=False)
    active = links.loc[links["valid_to_release"].eq("") & links["link_status"].eq("confirmed")]
    method = active.set_index("candidacy_id")["method"]
    people = results.loc[results["person_id"].ne("")].copy()
    people["method"] = people["candidacy_id"].map(method)
    people = people.sort_values(["person_id", "election_date", "candidacy_id"], kind="stable")
    people["earlier"] = people.groupby("person_id")["candidacy_id"].shift()
    by_id = results.set_index("candidacy_id")

    pairs = people.loc[people["earlier"].notna()].copy()
    pairs["stratum"] = pairs["method"].map(STRATA)
    if pairs["stratum"].isna().any():
        raise ValueError(
            f"unmapped link method: {pairs.loc[pairs['stratum'].isna(), 'method'].iloc[0]}"
        )
    frame_sizes = pairs["stratum"].value_counts().to_dict()
    sampled = []
    for stratum, size in JOIN_SIZES.items():
        group = pairs.loc[pairs["stratum"].eq(stratum)].sort_values("candidacy_id", kind="stable")
        sampled.append(group.sample(n=min(size, len(group)), random_state=SEED))
    joins = pd.concat(sampled, ignore_index=True)
    rows = []
    for number, pair in enumerate(joins.itertuples(index=False), start=1):
        later = by_id.loc[pair.candidacy_id]
        earlier = by_id.loc[pair.earlier]
        others = people.loc[
            people["person_id"].eq(pair.person_id)
            & ~people["candidacy_id"].isin([pair.candidacy_id, pair.earlier])
        ]
        rows.append(
            {
                "pair_id": f"J{number:03d}",
                "stratum": pair.stratum,
                "stratum_frame_size": frame_sizes[pair.stratum],
                "person_id": pair.person_id,
                "earlier_candidacy_id": pair.earlier,
                "earlier_run": describe(earlier),
                "later_candidacy_id": pair.candidacy_id,
                "later_run": describe(later),
                "same_office": earlier["office_type"] == later["office_type"],
                "same_printed_name": earlier["candidate_name"].upper()
                == later["candidate_name"].upper(),
                "other_runs_of_person": "; ".join(
                    describe(by_id.loc[candidacy]) for candidacy in others["candidacy_id"]
                ),
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_dir / "joins_sample.csv", index=False, lineterminator="\n")

    by_name: dict[tuple[str, str], set[str]] = {}
    for row in people.itertuples(index=False):
        by_name.setdefault(first_last(row.candidate_name), set()).add(row.person_id)
    split_frame = sorted(
        {
            tuple(sorted(pair))
            for members in by_name.values()
            if len(members) > 1
            for pair in itertools.combinations(sorted(members), 2)
        }
    )
    frame = pd.DataFrame(split_frame, columns=["person_a", "person_b"])
    splits = frame.sample(n=min(SPLIT_SIZE, len(frame)), random_state=SEED)
    split_rows = []
    for number, pair in enumerate(splits.itertuples(index=False), start=1):
        runs = {}
        for side, person in (("a", pair.person_a), ("b", pair.person_b)):
            own = people.loc[people["person_id"].eq(person)]
            runs[side] = "; ".join(describe(by_id.loc[c]) for c in own["candidacy_id"])
        split_rows.append(
            {
                "pair_id": f"S{number:03d}",
                "frame_size": len(frame),
                "person_a": pair.person_a,
                "runs_a": runs["a"],
                "person_b": pair.person_b,
                "runs_b": runs["b"],
            }
        )
    pd.DataFrame(split_rows).to_csv(
        output_dir / "splits_sample.csv", index=False, lineterminator="\n"
    )
    print(f"join frame {len(pairs)} pairs {frame_sizes}; sampled {len(rows)}")
    print(f"split frame {len(frame)} pairs; sampled {len(split_rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    draw(args.results, args.links, args.output)


if __name__ == "__main__":
    main()
