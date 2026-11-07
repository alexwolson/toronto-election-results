"""Estimate false merges across the released joins from the census and the November sample.

The released joins fall into two parts. The joins made after the November audit drew its sample
were all checked (``link-audit-2026-11-07/joins_results.csv``), so their rates are known without
sampling error. The older joins are estimated from the November sample, stratum by stratum, with
each stratum weighted by its size in the released frame (``frame_strata.csv``). Each sampled
stratum's rate has a Jeffreys posterior, and the release-wide interval comes from Monte Carlo draws.
A census join counts as confirmed only when the second check accepted the auditor's evidence.
Because the false-merge rate may be zero, it is reported with a one-sided 95% upper bound. Run from
the repository root.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CENSUS_DIR = Path("docs/verification/link-audit-2026-11-07")
SAMPLE_DIR = Path("docs/verification/link-audit-2026-11-03")
DRAWS = 200_000
SEED = 20261107
VERDICTS = ("CONFIRMED", "CONTRADICTED", "NOT_CONFIRMED")
STRATUM_ORDER = ["assertion", "review", "incumbency", "official_record", "roster"]
LABELS = {
    "post_audit": "Made after the November sample (census)",
    "assertion": "Curated assertion",
    "review": "Review disposition",
    "incumbency": "Reported incumbency",
    "official_record": "Official record",
    "roster": "Council roster",
}


def jeffreys(successes: int, trials: int, rng: np.random.Generator) -> np.ndarray:
    return rng.beta(successes + 0.5, trials - successes + 0.5, size=DRAWS)


def summarize(census_dir: Path, sample_dir: Path) -> None:
    census = pd.read_csv(census_dir / "joins_results.csv", dtype="string", keep_default_na=False)
    sizes = pd.read_csv(census_dir / "frame_strata.csv").set_index("stratum")["joins"]
    sample = pd.read_csv(sample_dir / "joins_results.csv", dtype="string", keep_default_na=False)
    if len(census) != sizes["post_audit"]:
        raise ValueError("the census results do not cover every post-audit join")
    total = int(sizes.sum())
    rng = np.random.default_rng(SEED)

    auditor = census["verdict"].value_counts()
    final = census["final_verdict"].value_counts()
    print("| Verdict | Auditor | After second check |")
    print("|---|---:|---:|")
    for verdict in VERDICTS:
        print(f"| {verdict} | {int(auditor.get(verdict, 0))} | {int(final.get(verdict, 0))} |")
    print()

    print("| Stratum | Joins in release | Checked | Confirmed | Contradicted | Not confirmed |")
    print("|---|---:|---:|---:|---:|---:|")
    weighted = {verdict: np.zeros(DRAWS) for verdict in VERDICTS[:2]}
    point = dict.fromkeys(VERDICTS[:2], 0.0)
    rows = [("post_audit", census["final_verdict"])] + [
        (stratum, sample.loc[sample["stratum"].eq(stratum), "verdict"]) for stratum in STRATUM_ORDER
    ]
    for stratum, verdicts in rows:
        counts = verdicts.value_counts()
        n = len(verdicts)
        cells = " | ".join(str(int(counts.get(verdict, 0))) for verdict in VERDICTS)
        print(f"| {LABELS[stratum]} | {int(sizes[stratum]):,} | {n} | {cells} |")
        weight = sizes[stratum] / total
        for verdict in weighted:
            k = int(counts.get(verdict, 0))
            share = np.full(DRAWS, k / n) if stratum == "post_audit" else jeffreys(k, n, rng)
            weighted[verdict] += weight * share
            point[verdict] += weight * k / n
    print()
    low, high = np.quantile(weighted["CONFIRMED"], [0.025, 0.975])
    print(
        f"Weighted share of the {total:,} joins that tie two different people: "
        f"{point['CONTRADICTED']:.1%} (one-sided 95% upper bound "
        f"{np.quantile(weighted['CONTRADICTED'], 0.95):.1%})"
    )
    print(
        f"Weighted share confirmed from the auditors' own sources: {point['CONFIRMED']:.1%} "
        f"(95% interval {low:.1%} to {high:.1%})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", type=Path, default=CENSUS_DIR)
    parser.add_argument("--sample", type=Path, default=SAMPLE_DIR)
    args = parser.parse_args()
    summarize(args.census, args.sample)


if __name__ == "__main__":
    main()
