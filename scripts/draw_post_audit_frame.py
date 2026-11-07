"""List every join made after the November 2026 audit drew its sample, for a census audit.

A join is a pair of consecutive Candidacies (by election date) within one Person, as in
`scripts/draw_link_audit_sample.py`. A join is new when its two runs were in different Persons, or
had no Person, in the release the audit sampled (commit `cf92e3b`). The script writes the frame with
the run descriptions the auditors see, a separate key with the link that made each join, which the
auditors do not see, and the size of each stratum of the release's joins: the new joins, and the
older joins by the November strata. When the output already holds a key, each join keeps its pair
ID and a join made since is numbered after the last; the script fails if a join in the key is no
longer in the release. Run from the repository root:

    git show cf92e3b:data/out/election_results.csv > /tmp/results-cf92e3b.csv
    python -I scripts/draw_post_audit_frame.py --baseline /tmp/results-cf92e3b.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from draw_link_audit_sample import STRATA, describe

DEFAULT_RESULTS = Path("data/out/election_results.csv")
DEFAULT_LINKS = Path("data/out/candidacy_person_links.csv")
DEFAULT_OUTPUT = Path("docs/verification/link-audit-2026-11-07")


def _joins(results: pd.DataFrame) -> pd.DataFrame:
    people = results.loc[results["person_id"].ne("")]
    people = people.sort_values(["person_id", "election_date", "candidacy_id"], kind="stable")
    people = people.assign(earlier=people.groupby("person_id")["candidacy_id"].shift())
    pairs = people.loc[people["earlier"].notna(), ["person_id", "earlier", "candidacy_id"]]
    return pairs.rename(columns={"earlier": "earlier_candidacy_id", "candidacy_id": "later"})


def _pair_ids(new: pd.DataFrame, key_path: Path) -> dict[tuple[str, str], str]:
    """Keep the pair IDs of an earlier draw, and number the joins made since after them."""

    joins = list(zip(new["earlier_candidacy_id"], new["later"], strict=True))
    kept: dict[tuple[str, str], str] = {}
    if key_path.is_file():
        earlier = pd.read_csv(key_path, dtype=str, keep_default_na=False)
        kept = dict(
            zip(
                zip(earlier["earlier_candidacy_id"], earlier["later_candidacy_id"], strict=True),
                earlier["pair_id"],
                strict=True,
            )
        )
        gone = sorted(set(kept) - set(joins))
        if gone:
            raise SystemExit(f"{len(gone)} joins in {key_path} are no longer in the release")
    last = max((int(pair_id[1:]) for pair_id in kept.values()), default=0)
    for join in joins:
        if join not in kept:
            last += 1
            kept[join] = f"P{last:03d}"
    return kept


def _link_basis(links: pd.DataFrame, candidacy_id: str) -> tuple[str, str]:
    row = links.loc[
        links["candidacy_id"].eq(candidacy_id)
        & links["link_status"].eq("confirmed")
        & links["valid_to_release"].eq("")
    ]
    if row.empty:
        return "", ""
    link = row.iloc[0]
    evidence = json.loads(link["evidence"])
    return link["method"], evidence.get("assertion_id") or link["reviewer"]


def draw(results_path: Path, links_path: Path, baseline_path: Path, output_dir: Path) -> None:
    results = pd.read_csv(results_path, dtype=str, keep_default_na=False)
    links = pd.read_csv(links_path, dtype=str, keep_default_na=False)
    baseline = pd.read_csv(baseline_path, dtype=str, keep_default_na=False)
    before = baseline.set_index("candidacy_id")["person_id"]
    joins = _joins(results)
    new = joins.loc[
        [
            before.get(earlier, "") == "" or before.get(earlier, "") != before.get(later, "")
            for earlier, later in zip(joins["earlier_candidacy_id"], joins["later"], strict=True)
        ]
    ].sort_values(["person_id", "later"], kind="stable")
    by_id = results.set_index("candidacy_id")
    pair_ids = _pair_ids(new, output_dir / "joins_key.csv")
    frame, key = [], []
    for join in new.itertuples(index=False):
        pair_id = pair_ids[(join.earlier_candidacy_id, join.later)]
        others = results.loc[
            results["person_id"].eq(join.person_id)
            & ~results["candidacy_id"].isin([join.earlier_candidacy_id, join.later])
        ].sort_values("election_date", kind="stable")
        earlier, later = by_id.loc[join.earlier_candidacy_id], by_id.loc[join.later]
        frame.append(
            {
                "pair_id": pair_id,
                "earlier_run": describe(earlier),
                "later_run": describe(later),
                "same_office": earlier["office_type"] == later["office_type"],
                "same_printed_name": earlier["candidate_name"].upper()
                == later["candidate_name"].upper(),
                "other_runs_of_person": "; ".join(describe(row) for _, row in others.iterrows()),
            }
        )
        methods = [_link_basis(links, cid) for cid in (join.earlier_candidacy_id, join.later)]
        key.append(
            {
                "pair_id": pair_id,
                "person_id": join.person_id,
                "earlier_candidacy_id": join.earlier_candidacy_id,
                "later_candidacy_id": join.later,
                "earlier_link": f"{methods[0][0]} {methods[0][1]}".strip(),
                "later_link": f"{methods[1][0]} {methods[1][1]}".strip(),
            }
        )
    active = links.loc[links["valid_to_release"].eq("") & links["link_status"].eq("confirmed")]
    method = active.set_index("candidacy_id")["method"]
    older = joins.drop(new.index)
    strata = older["later"].map(method).map(STRATA)
    if strata.isna().any():
        raise ValueError("an older join's later Candidacy has an unmapped link method")
    sizes = [{"stratum": "post_audit", "joins": len(new)}] + [
        {"stratum": stratum, "joins": int(count)}
        for stratum, count in strata.value_counts().sort_index().items()
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(frame).sort_values("pair_id").to_csv(
        output_dir / "joins_frame.csv", index=False, lineterminator="\n"
    )
    pd.DataFrame(key).sort_values("pair_id").to_csv(
        output_dir / "joins_key.csv", index=False, lineterminator="\n"
    )
    pd.DataFrame(sizes).to_csv(output_dir / "frame_strata.csv", index=False, lineterminator="\n")
    print(f"{len(frame)} joins made after the audit's sample, of {len(joins)} in the release")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    draw(args.results, args.links, args.baseline, args.output)


if __name__ == "__main__":
    main()
