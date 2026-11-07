"""The seat behind each incumbency: appointment, held district and change of district."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import box

from toronto_election_results.incumbent_seats import add_incumbent_seat_fields

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"

# Two small squares near Toronto; the new ward takes the west 70% of old ward A.
OLD_A = box(-79.40, 43.70, -79.39, 43.71)
OLD_B = box(-79.39, 43.70, -79.38, 43.71)
NEW_W = box(-79.40, 43.70, -79.393, 43.71)
NEW_E = box(-79.393, 43.70, -79.38, 43.71)


def _districts() -> pd.DataFrame:
    rows = [
        ("dst_a", "old", OLD_A),
        ("dst_b", "old", OLD_B),
        ("dst_w", "new", NEW_W),
        ("dst_e", "new", NEW_E),
        ("dst_city_old", "old", None),
        ("dst_city_new", "new", None),
        ("dst_r1", "riding_old", None),
        ("dst_r2", "riding_new", None),
    ]
    return pd.DataFrame(
        {
            "district_id": [row[0] for row in rows],
            "boundary_regime": [row[1] for row in rows],
            "geometry_status": [
                "available" if row[2] is not None else "not_acquired" for row in rows
            ],
            "geometry": [row[2] for row in rows],
        }
    )


def _tenure(tenure_id, district, *, entry="election", precision="election_date"):
    return {
        "office_tenure_id": tenure_id,
        "district_id": district,
        "entry_method": entry,
        "started_on_precision": precision,
    }


def _candidacy(candidacy_id, tenure_id, district, regime, *, office="councillor", body=None):
    return {
        "candidacy_id": candidacy_id,
        "incumbent": tenure_id is not None,
        "incumbent_office_tenure_id": tenure_id,
        "represented_body": body or "toronto_city_council",
        "office_type": office,
        "district_id": district,
        "boundary_regime": regime,
    }


def _fields(candidacies, tenures):
    out = add_incumbent_seat_fields(
        pd.DataFrame(candidacies), pd.DataFrame(tenures), _districts()
    ).set_index("candidacy_id")
    return out[["incumbent_appointed", "incumbent_held_district_id", "incumbent_changed_district"]]


def test_same_regime_compares_district_ids():
    out = _fields(
        [
            _candidacy("same", "t_a", "dst_a", "old"),
            _candidacy("moved", "t_a2", "dst_b", "old"),
        ],
        [_tenure("t_a", "dst_a"), _tenure("t_a2", "dst_a", entry="appointment")],
    )
    assert out.loc["same"].tolist() == [False, "dst_a", False]
    assert out.loc["moved"].tolist() == [True, "dst_a", True]


def test_a_boundary_change_compares_areas():
    out = _fields(
        [
            _candidacy("most_of_seat", "t_1", "dst_w", "new"),
            _candidacy("rest_of_seat", "t_2", "dst_e", "new"),
        ],
        [_tenure("t_1", "dst_a"), _tenure("t_2", "dst_a")],
    )
    assert not out.loc["most_of_seat", "incumbent_changed_district"]
    assert out.loc["rest_of_seat", "incumbent_changed_district"]


def test_no_geometry_across_a_boundary_change_leaves_the_change_null():
    out = _fields(
        [
            _candidacy(
                "mp", "t_r", "dst_r2", "riding_new", office="mp", body="canada_house_of_commons"
            )
        ],
        [_tenure("t_r", "dst_r1")],
    )
    assert out.loc["mp", "incumbent_held_district_id"] == "dst_r1"
    assert pd.isna(out.loc["mp", "incumbent_changed_district"])


def test_a_mayor_never_changes_district():
    out = _fields(
        [_candidacy("mayor", "t_m", "dst_city_new", "new", office="mayor")],
        [_tenure("t_m", "dst_city_old")],
    )
    assert out.loc["mayor", "incumbent_changed_district"] == False


def test_a_legislature_seat_outside_the_city_is_another_district():
    out = _fields(
        [
            _candidacy(
                "mpp",
                "t_o",
                "dst_r2",
                "riding_new",
                office="mpp",
                body="ontario_legislative_assembly",
            )
        ],
        [_tenure("t_o", None)],
    )
    assert pd.isna(out.loc["mpp", "incumbent_held_district_id"])
    assert out.loc["mpp", "incumbent_changed_district"]


def test_a_council_seat_without_a_district_fails():
    with pytest.raises(ValueError, match="no district"):
        _fields([_candidacy("c", "t_c", "dst_a", "old")], [_tenure("t_c", None)])


def test_an_unknown_start_and_a_non_incumbent_leave_every_field_null():
    out = _fields(
        [
            _candidacy(
                "flag",
                "t_f",
                "dst_r1",
                "riding_old",
                office="mpp",
                body="ontario_legislative_assembly",
            ),
            _candidacy("not", None, "dst_a", "old"),
        ],
        [_tenure("t_f", "dst_r1", entry="unknown", precision="unknown")],
    )
    assert out.loc["flag"].isna().all()
    assert out.loc["not"].isna().all()


def test_published_seat_fields():
    results = pd.read_csv(OUT / "election_results.csv", dtype=str, keep_default_na=False)
    incumbent = results["incumbent"].eq("True")
    seat = ["incumbent_appointed", "incumbent_held_district_id", "incumbent_changed_district"]
    assert results.loc[~incumbent, seat].eq("").all().all()
    appointed = results.loc[results["incumbent_appointed"].eq("True")]
    assert set(appointed["represented_body"]) == {"toronto_city_council"}
    # John Tory sat for Dufferin—Peel—Wellington—Grey when he ran in Don Valley West in 2007.
    tory = results.loc[
        results["represented_body"].eq("ontario_legislative_assembly")
        & results["incumbent"].eq("True")
        & results["incumbent_held_district_id"].eq("")
    ]
    assert tory["incumbent_changed_district"].tolist() == ["True"]
