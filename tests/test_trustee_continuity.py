"""Contracts for explicit 2026 trustee contest continuity."""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.trustee_2026 import load_trustee_ward_crosswalk
from toronto_election_results.trustee_continuity import (
    load_trustee_continuity,
    validate_trustee_continuity,
)

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data/reference"


def _inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        load_trustee_continuity(REFERENCE / "trustee_contest_continuity_2026.csv"),
        pd.read_csv(ROOT / "data/out/election_results.csv", low_memory=False),
        load_trustee_ward_crosswalk(REFERENCE / "trustee_ward_crosswalk_2026.csv"),
    )


def test_continuity_covers_all_contests_and_uses_the_latest_completed_results():
    continuity, results, crosswalk = _inputs()

    validate_trustee_continuity(continuity, results, crosswalk)

    assert len(continuity) == 29
    assert continuity.loc[continuity["board_id"].eq("tdsb"), "prior_contest_id"].eq("").all()
    assert (
        continuity.loc[continuity["board_id"].eq("tdsb"), "continuity_status"].eq("redrawn").all()
    )
    french_reruns = continuity.loc[
        continuity["prior_contest_id"].isin(
            {
                "con_8adca43ff9ce5d0daac685c3f3930acd",
                "con_713b1959968153d8af4c329a0caa1b82",
            }
        )
    ]
    assert set(french_reruns["board_id"]) == {"viamonde", "monavenir"}


def test_redrawn_tdsb_ward_cannot_gain_a_same_number_prior_result():
    continuity, results, crosswalk = _inputs()
    row = continuity["board_id"].eq("tdsb") & continuity["ward_id"].eq(1)
    continuity.loc[row, "continuity_status"] = "continuous"
    continuity.loc[row, "prior_contest_id"] = "con_6416117a71045bfbb98fdbadeac07e04"

    with pytest.raises(ValueError, match="redrawn TDSB"):
        validate_trustee_continuity(continuity, results, crosswalk)


def test_continuity_rejects_a_cross_board_prior_contest():
    continuity, results, crosswalk = _inputs()
    row = continuity["board_id"].eq("tcdsb") & continuity["ward_id"].eq(1)
    continuity.loc[row, "prior_contest_id"] = "con_5434720239ac5bd29fea88c00e9aedb0"

    with pytest.raises(ValueError, match="cross boards"):
        validate_trustee_continuity(continuity, results, crosswalk)


def test_continuity_rejects_a_pending_current_contest_as_prior():
    continuity, results, crosswalk = _inputs()
    row = continuity["board_id"].eq("tcdsb") & continuity["ward_id"].eq(1)
    continuity.loc[row, "prior_contest_id"] = "con_73b70ffb6b6f58899e27e95e50a0d118"

    with pytest.raises(ValueError, match="must be final"):
        validate_trustee_continuity(continuity, results, crosswalk)


def test_continuity_rejects_one_prior_contest_assigned_twice():
    continuity, results, crosswalk = _inputs()
    ward_one = continuity["board_id"].eq("tcdsb") & continuity["ward_id"].eq(1)
    ward_two = continuity["board_id"].eq("tcdsb") & continuity["ward_id"].eq(2)
    continuity.loc[ward_two, "prior_contest_id"] = continuity.loc[
        ward_one, "prior_contest_id"
    ].iloc[0]

    with pytest.raises(ValueError, match="assigned more than once"):
        validate_trustee_continuity(continuity, results, crosswalk)
