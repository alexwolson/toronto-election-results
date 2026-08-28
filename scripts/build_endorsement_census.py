"""Write the frozen-panel endorsement source-package research census."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from toronto_election_results.endorsement_census import (
    build_endorsement_source_package_census,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/out"))
    parser.add_argument(
        "--panel",
        type=Path,
        default=Path("data/reference/endorser_panel_curations.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/research/endorsement_source_package_census.csv"),
    )
    args = parser.parse_args()

    census = build_endorsement_source_package_census(
        election_results=pd.read_csv(args.data_dir / "election_results.csv"),
        contests=pd.read_csv(args.data_dir / "contests.csv"),
        panel_curations=pd.read_csv(args.panel),
        endorsement_assertions=pd.read_csv(args.data_dir / "endorsement_assertions.csv"),
        endorsement_coverage=pd.read_csv(args.data_dir / "endorsement_coverage.csv"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    census.to_csv(args.output, index=False)
    print(f"endorsement source-package census written to {args.output}")
    print(f"  {len(census)} packages across {census['endorser_key'].nunique()} Endorsers")
    for disposition, count in census["disposition"].value_counts().sort_index().items():
        print(f"  {disposition}: {count}")


if __name__ == "__main__":
    main()
