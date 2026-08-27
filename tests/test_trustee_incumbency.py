"""Contracts for evidence-backed 2026 trustee incumbency."""

from pathlib import Path

import pandas as pd

from toronto_election_results.trustee_incumbency import (
    EXPECTED_BODY_COUNTS,
    build_trustee_incumbency_evidence,
)

ROOT = Path(__file__).resolve().parents[1]


def test_trustee_incumbency_has_verified_current_people_and_never_proves_absence():
    results = pd.read_csv(ROOT / "data/out/election_results.csv", low_memory=False)

    evidence = build_trustee_incumbency_evidence(results, ROOT / "data/reference")

    assert len(evidence.rosters) == 20
    assert evidence.rosters["represented_body"].value_counts().to_dict() == EXPECTED_BODY_COUNTS
    assert not evidence.rosters["roster_complete"].any()
    assert evidence.rosters["person_id"].notna().all()
    assert evidence.office_tenures["source_detail"].str.contains("https://").all()
