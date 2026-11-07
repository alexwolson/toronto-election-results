"""Draw the joins for the human coding of Person links.

Section 1 holds 50 joins in random order: 25 that the November 2026 audit's agents confirmed,
from its assertion, review and official-record strata, and 25 joins whose two runs were in
different Persons, or had none, in the release the audit sampled. Coders see neither group's
label nor any verdict.

Section 2 holds the 31 audit joins that the agents could not confirm, with the sources the release
cites for each, so that coders with archive access can check them.

A join is a pair of consecutive Candidacies (by election date) within one Person, as in
`scripts/draw_link_audit_sample.py`. The draw is reproducible from the release, the audit's
results, the release the audit sampled and the seed. Run from the repository root:

    git show cf92e3b:data/out/election_results.csv > /tmp/results-cf92e3b.csv
    python -I scripts/draw_human_coding_sample.py --baseline /tmp/results-cf92e3b.csv

`--key PATH` also writes each coding ID's origin, for comparing the coders' verdicts afterwards.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from draw_link_audit_sample import describe

DEFAULT_RESULTS = Path("data/out/election_results.csv")
DEFAULT_LINKS = Path("data/out/candidacy_person_links.csv")
DEFAULT_AUDIT = Path("docs/verification/link-audit-2026-11-03/joins_results.csv")
DEFAULT_OUTPUT = Path("docs/verification/human-coding-2026-11-07")
SEED = 20261107
AUDIT_STRATA = ("assertion", "review", "official_record")
SECTION_1_EACH = 25
CODING_COLUMNS = ("coder", "verdict", "evidence_urls", "quotes", "notes", "minutes")


def _joins(results: pd.DataFrame) -> pd.DataFrame:
    people = results.loc[results["person_id"].ne("")]
    people = people.sort_values(["person_id", "election_date", "candidacy_id"], kind="stable")
    people = people.assign(earlier=people.groupby("person_id")["candidacy_id"].shift())
    pairs = people.loc[people["earlier"].notna(), ["person_id", "earlier", "candidacy_id"]]
    return pairs.rename(columns={"earlier": "earlier_candidacy_id", "candidacy_id": "later"})


def _sources(links: pd.DataFrame, candidacy_ids: tuple[str, str]) -> str:
    """Evidence URLs of the curated links on either run of a join."""

    urls: list[str] = []
    for candidacy_id in candidacy_ids:
        rows = links.loc[
            links["candidacy_id"].eq(candidacy_id) & links["link_status"].eq("confirmed")
        ]
        for evidence in rows["evidence"]:
            parsed = json.loads(evidence)
            for url in parsed.get("evidence_urls", []) + parsed.get("official_evidence_urls", []):
                if url not in urls:
                    urls.append(url)
    return " | ".join(urls)


def _row(
    coding_id: str,
    section: int,
    earlier: str,
    later: str,
    results: pd.DataFrame,
    sources: str = "",
) -> dict[str, object]:
    by_id = results.set_index("candidacy_id")
    person = by_id.loc[later, "person_id"]
    others = results.loc[
        results["person_id"].eq(person) & ~results["candidacy_id"].isin([earlier, later])
    ].sort_values("election_date", kind="stable")
    return {
        "coding_id": coding_id,
        "section": section,
        "earlier_run": describe(by_id.loc[earlier]),
        "later_run": describe(by_id.loc[later]),
        "other_runs_of_person": "; ".join(describe(row) for _, row in others.iterrows()),
        "release_sources": sources,
        **{column: "" for column in CODING_COLUMNS},
    }


def draw(
    results_path: Path,
    links_path: Path,
    audit_path: Path,
    baseline_path: Path,
    output_dir: Path,
    key_path: Path | None,
) -> None:
    results = pd.read_csv(results_path, dtype=str, keep_default_na=False)
    links = pd.read_csv(links_path, dtype=str, keep_default_na=False)
    audit = pd.read_csv(audit_path, dtype=str, keep_default_na=False)
    baseline = pd.read_csv(baseline_path, dtype=str, keep_default_na=False)

    confirmed = audit.loc[audit["verdict"].eq("CONFIRMED") & audit["stratum"].isin(AUDIT_STRATA)]
    confirmed = confirmed.sort_values("pair_id").sample(n=SECTION_1_EACH, random_state=SEED)

    before = baseline.set_index("candidacy_id")["person_id"]
    current = _joins(results)
    apart = [
        before.get(earlier, "") == "" or before.get(earlier, "") != before.get(later, "")
        for earlier, later in zip(current["earlier_candidacy_id"], current["later"], strict=True)
    ]
    new = current.loc[apart].sort_values("later", kind="stable")
    new = new.sample(n=SECTION_1_EACH, random_state=SEED)

    first = pd.concat(
        [
            pd.DataFrame(
                {
                    "origin": "audit_confirmed",
                    "audit_pair_id": confirmed["pair_id"],
                    "earlier": confirmed["earlier_candidacy_id"],
                    "later": confirmed["later_candidacy_id"],
                }
            ),
            pd.DataFrame(
                {
                    "origin": "post_audit_join",
                    "audit_pair_id": "",
                    "earlier": new["earlier_candidacy_id"],
                    "later": new["later"],
                }
            ),
        ],
        ignore_index=True,
    ).sample(frac=1, random_state=SEED)
    first["coding_id"] = [f"H{number:03d}" for number in range(1, len(first) + 1)]

    held = audit.loc[audit["verdict"].eq("NOT_CONFIRMED")].sort_values("pair_id")
    second = pd.DataFrame(
        {
            "origin": "audit_not_confirmed",
            "audit_pair_id": held["pair_id"],
            "earlier": held["earlier_candidacy_id"],
            "later": held["later_candidacy_id"],
        }
    )
    second["coding_id"] = [
        f"H{number:03d}" for number in range(len(first) + 1, len(first) + len(second) + 1)
    ]

    rows = [_row(r.coding_id, 1, r.earlier, r.later, results) for r in first.itertuples()]
    rows += [
        _row(
            r.coding_id,
            2,
            r.earlier,
            r.later,
            results,
            _sources(links, (r.earlier, r.later)),
        )
        for r in second.itertuples()
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_dir / "coding_sheet.csv", index=False, lineterminator="\n")
    key = pd.concat([first, second], ignore_index=True)
    same_person = results.set_index("candidacy_id")["person_id"]
    key["joined_in_release"] = [
        same_person.get(earlier, "") != "" and same_person.get(earlier) == same_person.get(later)
        for earlier, later in zip(key["earlier"], key["later"], strict=True)
    ]
    if key_path is not None:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key[
            ["coding_id", "origin", "audit_pair_id", "earlier", "later", "joined_in_release"]
        ].to_csv(key_path, index=False, lineterminator="\n")
    print(f"post-audit joins {int(sum(apart))}; section 1 {len(first)}; section 2 {len(second)}")
    print(f"joins no longer in one Person: {int((~key['joined_in_release']).sum())}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--key", type=Path)
    args = parser.parse_args()
    draw(args.results, args.links, args.audit, args.baseline, args.output, args.key)


if __name__ == "__main__":
    main()
