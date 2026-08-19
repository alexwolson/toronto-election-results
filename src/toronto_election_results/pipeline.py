"""End-to-end pipeline runner: download -> assemble -> geometry -> validate.

Ties the tested stages together into one command (`python -m toronto_election_results.pipeline`).
"""

from __future__ import annotations

import pandas as pd

from . import assemble, download, geometry, validate
from .assemble import OUT
from .crosscheck_winners import unexplained_winners
from .incumbency import build_composition


def run_all(*, skip_download: bool = False) -> list[str]:
    if not skip_download:
        download.download_all()
    assemble.main()
    geometry.main()

    table = pd.read_parquet(OUT / "toronto_election_results.parquet")
    issues = validate.validate(table)
    print("QC:", "OK" if not issues else f"{len(issues)} issue(s)")
    for issue in issues:
        print(f"  - {issue}")

    unexplained = unexplained_winners(table, build_composition())
    print("Winner cross-check:", "OK" if not unexplained else f"{len(unexplained)} unexplained")
    for year, ward, name in unexplained:
        print(f"  - {year} ward {ward}: {name}")

    return issues


if __name__ == "__main__":
    run_all()
