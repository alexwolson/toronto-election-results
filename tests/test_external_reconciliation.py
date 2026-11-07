"""The reconciliation with external datasets, and the Candidacy rule it documents."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
RECONCILIATION = REPO_ROOT / "docs" / "verification" / "external-reconciliation-2026-11-07"


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def test_a_candidate_whose_votes_were_not_counted_has_no_candidacy():
    results = _read(OUT / "election_results.csv")
    ward_23 = results.loc[
        results["election_date"].eq("2022-10-24")
        & results["represented_body"].eq("toronto_city_council")
        & results["district_name"].eq("Ward 23 — Scarborough North")
    ]
    assert dict(zip(ward_23["candidate_name"], ward_23["votes"], strict=True)) == {
        "Jamaal Myers": "5315",
        "Phillip Francis": "2755",
        "Virginia Jones": "2333",
    }
    assert ward_23["total_contest_votes"].eq("10403").all()
    in_2022 = results.loc[results["election_date"].eq("2022-10-24"), "candidate_name"]
    assert not in_2022.str.casefold().eq("cynthia lai").any()


def test_reconciliation_files_match_the_report():
    contests = _read(RECONCILIATION / "contests.csv")
    status = contests.groupby(["source", "status"]).size().to_dict()
    assert status == {
        ("cmed", "agrees"): 271,
        ("cmed", "differs"): 60,
        ("sevi_federal", "agrees"): 237,
        ("sevi_federal", "differs"): 4,
        ("sevi_ontario", "agrees"): 173,
        ("sevi_ontario", "differs"): 2,
        ("sevi_ontario", "not_in_external"): 2,
    }
    differences = _read(RECONCILIATION / "differences.csv")
    assert len(differences) == 98
    assert differences["finding"].ne("").all()
    assert set(differences.loc[differences["contest_id"].ne(""), "contest_id"]) <= set(
        contests["contest_id"]
    )
