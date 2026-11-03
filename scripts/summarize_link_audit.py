"""Summarize the audit of Person links with stratified estimates and intervals.

Reads the adjudicated samples written next to the draw (``joins_results.csv`` and
``splits_results.csv``) and prints Markdown tables. A same-name pair counts as one person when the
auditor said so and a second check accepted the evidence (``final_verdict``). Each stratum's rate has a Jeffreys posterior;
the release-wide rate weights the strata by the size of their frames, and its interval comes from
Monte Carlo draws of the independent posteriors. Because the false-merge rate may be zero, it is
reported with a one-sided 95% upper bound. Run from the repository root.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_DIR = Path("docs/verification/link-audit-2026-11-03")
DRAWS = 200_000
SEED = 20261103
STRATUM_ORDER = ["assertion", "review", "incumbency", "official_record", "roster"]


def jeffreys(successes: int, trials: int, rng: np.random.Generator) -> np.ndarray:
    return rng.beta(successes + 0.5, trials - successes + 0.5, size=DRAWS)


def interval(draws: np.ndarray) -> str:
    low, high = np.quantile(draws, [0.025, 0.975])
    return f"{low:.1%} to {high:.1%}"


def summarize_joins(path: Path) -> None:
    rows = pd.read_csv(path, dtype="string", keep_default_na=False)
    rng = np.random.default_rng(SEED)
    frame = rows.groupby("stratum")["stratum_frame_size"].first().astype(int)
    total = int(frame.sum())
    print("| Stratum | Pairs in release | Sampled | Confirmed | Contradicted | Not confirmed |")
    print("|---|---|---|---|---|---|")
    weighted = {verdict: np.zeros(DRAWS) for verdict in ("CONFIRMED", "CONTRADICTED")}
    point = {verdict: 0.0 for verdict in weighted}
    for stratum in STRATUM_ORDER:
        group = rows.loc[rows["stratum"].eq(stratum)]
        n = len(group)
        counts = group["verdict"].value_counts()
        cells = [str(int(counts.get(v, 0))) for v in ("CONFIRMED", "CONTRADICTED", "NOT_CONFIRMED")]
        print(f"| {stratum} | {frame[stratum]:,} | {n} | " + " | ".join(cells) + " |")
        weight = frame[stratum] / total
        for verdict in weighted:
            k = int(counts.get(verdict, 0))
            weighted[verdict] += weight * jeffreys(k, n, rng)
            point[verdict] += weight * k / n
    print()
    false_merges = weighted["CONTRADICTED"]
    print(
        f"Weighted share of pairs that join two different people: {point['CONTRADICTED']:.1%} "
        f"(one-sided 95% upper bound {np.quantile(false_merges, 0.95):.1%})"
    )
    print(
        f"Weighted share of pairs independently confirmed: {point['CONFIRMED']:.1%} "
        f"(95% interval {interval(weighted['CONFIRMED'])})"
    )


def summarize_splits(path: Path) -> None:
    rows = pd.read_csv(path, dtype="string", keep_default_na=False)
    rng = np.random.default_rng(SEED)
    frame = int(rows["frame_size"].iloc[0])
    n = len(rows)
    auditor = rows["verdict"].value_counts()
    final = rows["final_verdict"].value_counts()
    print()
    print("| Verdict | Auditor | After second check |")
    print("|---|---|---|")
    for verdict in ("SAME_PERSON", "DIFFERENT_PEOPLE", "UNDETERMINED"):
        print(f"| {verdict} | {int(auditor.get(verdict, 0))} | {int(final.get(verdict, 0))} |")
    same = int(final.get("SAME_PERSON", 0))
    draws = jeffreys(same, n, rng)
    print()
    print(
        f"Share of same-name pairs that are one person: {same / n:.1%} "
        f"(95% interval {interval(draws)}), about {round(frame * same / n)} of {frame} pairs"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()
    summarize_joins(args.dir / "joins_results.csv")
    summarize_splits(args.dir / "splits_results.csv")


if __name__ == "__main__":
    main()
