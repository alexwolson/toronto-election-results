from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.trustee_2026 import load_trustee_ward_crosswalk

REFERENCE = Path(__file__).parents[1] / "data" / "reference" / "trustee_ward_crosswalk_2026.csv"


def test_crosswalk_covers_all_four_boards_and_29_contests() -> None:
    crosswalk = load_trustee_ward_crosswalk(REFERENCE)

    assert len(crosswalk) == 29
    assert crosswalk.groupby("board_id")["ward_id"].apply(list).to_dict() == {
        "monavenir": [3, 4],
        "tcdsb": list(range(1, 13)),
        "tdsb": list(range(1, 13)),
        "viamonde": [2, 3, 4],
    }
    assert set(crosswalk["boundary_regime"]) == {
        "tdsb-trustee-wards-2026",
        "tcdsb-trustee-wards-2026",
        "viamonde-trustee-wards-2026",
        "monavenir-trustee-wards-2026",
    }


def test_crosswalk_preserves_the_authoritative_monavenir_ward_3_city_wards() -> None:
    crosswalk = load_trustee_ward_crosswalk(REFERENCE)
    row = crosswalk.loc[crosswalk["board_id"].eq("monavenir") & crosswalk["ward_id"].eq(3)].iloc[0]

    assert row["district_name"] == "Ward 3 — Toronto Ouest"
    assert row["city_wards"] == (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 18)
    assert row["source_updated_date"] == "2026-04-23"


def test_crosswalk_rejects_duplicate_or_invalid_rows(tmp_path: Path) -> None:
    rows = pd.read_csv(REFERENCE, dtype="string")
    rows = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)
    duplicate = tmp_path / "duplicate.csv"
    rows.to_csv(duplicate, index=False)

    with pytest.raises(ValueError, match="unique"):
        load_trustee_ward_crosswalk(duplicate)

    rows = pd.read_csv(REFERENCE, dtype="string")
    rows.loc[0, "city_wards"] = "1;26"
    invalid = tmp_path / "invalid.csv"
    rows.to_csv(invalid, index=False)

    with pytest.raises(ValueError, match="City wards"):
        load_trustee_ward_crosswalk(invalid)
