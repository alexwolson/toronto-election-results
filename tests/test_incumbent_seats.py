"""The seat behind each incumbency: appointment, held district and change of district."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import Point, box

from toronto_election_results.census_points import PopulationPoints
from toronto_election_results.incumbent_seats import add_incumbent_seat_fields

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"

# Two small squares near Toronto. The new west ward is the smaller part of old ward A by area,
# but holds three of its four polls.
OLD_A = box(-79.40, 43.70, -79.39, 43.71)
OLD_B = box(-79.39, 43.70, -79.38, 43.71)
NEW_W = box(-79.40, 43.70, -79.396, 43.71)
NEW_E = box(-79.396, 43.70, -79.38, 43.71)
POLLS = {
    "dst_a": [
        Point(-79.399, 43.701),
        Point(-79.398, 43.705),
        Point(-79.397, 43.709),
        Point(-79.391, 43.705),
    ]
}


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
            "official_district_id": [
                "city" if row[0].startswith("dst_city") else row[0] for row in rows
            ],
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
        pd.DataFrame(candidacies), pd.DataFrame(tenures), _districts(), POLLS
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


def test_a_boundary_change_follows_the_held_wards_polls():
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
        & results["election_date"].eq("2007-10-10")
    ]
    assert tory["incumbent_changed_district"].tolist() == ["True"]
    # In 2018 most of Lucy Troisi's old Ward 28 polls lie in the new Ward 13, where she ran,
    # but most of Mike Layton's old Ward 19 polls do not lie in Ward 11, where he ran.
    in_2018 = results.loc[results["election_date"].eq("2018-10-22")].set_index("candidate_name")
    assert in_2018.loc["Lucy Troisi", "incumbent_changed_district"] == "False"
    assert in_2018.loc["Mike Layton", "incumbent_changed_district"] == "True"
    assert in_2018.loc["Lucy Troisi", "incumbent_appointed"] == "True"
    # Ridings follow census population (ADR 0013). Toronto Centre's successor is the new Toronto
    # Centre, not University—Rosedale; York West's is Humber River—Black Creek; and most of Don
    # Valley East's people stayed in Don Valley East, so Joe Daniel's run in Don Valley North was
    # a change of seat.
    federal = results.loc[results["represented_body"].eq("canada_house_of_commons")]
    changed = federal.set_index(["election_date", "candidate_name"])["incumbent_changed_district"]
    assert changed.loc[("2015-10-19", "Chrystia Freeland")] == "True"
    assert changed.loc[("2015-10-19", "Joe Daniel")] == "True"
    assert changed.loc[("2015-10-19", "Judy Sgro")] == "False"
    assert changed.loc[("2025-04-28", "Michael Coteau")] == "True"


def test_a_move_within_one_regime_after_a_boundary_change_is_still_a_change():
    # The boundary-change row comes first, so the same-regime row is judged after it. Ward B
    # has no polls, so only the same-regime rule can settle the move.
    out = _fields(
        [
            _candidacy("most_of_seat", "t_1", "dst_w", "new"),
            _candidacy("moved", "t_2", "dst_a", "old"),
        ],
        [_tenure("t_1", "dst_a"), _tenure("t_2", "dst_b")],
    )
    assert out.loc["moved", "incumbent_changed_district"] == True


# A riding redistribution: old riding A against new ridings W and E. W holds three of A's four
# census points but E holds most of A's population.
CENSUS = {
    "riding_new_shaped": PopulationPoints(
        points=(
            Point(-79.399, 43.701),
            Point(-79.398, 43.705),
            Point(-79.397, 43.709),
            Point(-79.391, 43.705),
            Point(-79.385, 43.705),
        ),
        weights=(100.0, 100.0, 100.0, 900.0, 5000.0),
    )
}


def _riding_fields(candidacies, tenures, census=CENSUS):
    ridings = pd.DataFrame(
        {
            "district_id": ["dst_ra", "dst_rw", "dst_re"],
            "boundary_regime": ["riding_old_shaped", "riding_new_shaped", "riding_new_shaped"],
            "official_district_id": ["35001", "35101", "35102"],
            "geometry_status": ["available"] * 3,
            "geometry": [OLD_A, NEW_W, NEW_E],
        }
    )
    out = add_incumbent_seat_fields(
        pd.DataFrame(candidacies),
        pd.DataFrame(tenures),
        pd.concat([_districts(), ridings], ignore_index=True),
        POLLS,
        census,
    ).set_index("candidacy_id")
    return out["incumbent_changed_district"]


def test_a_riding_redistribution_follows_the_held_ridings_population():
    mp = {"office": "mp", "body": "canada_house_of_commons"}
    out = _riding_fields(
        [
            _candidacy("east", "t_1", "dst_re", "riding_new_shaped", **mp),
            _candidacy("west", "t_2", "dst_rw", "riding_new_shaped", **mp),
        ],
        [_tenure("t_1", "dst_ra"), _tenure("t_2", "dst_ra")],
    )
    # Only population inside the held riding counts: the point east of A is not A's.
    assert out["east"] == False
    assert out["west"] == True


def test_a_riding_redistribution_without_census_points_stays_null():
    mp = {"office": "mp", "body": "canada_house_of_commons"}
    out = _riding_fields(
        [_candidacy("east", "t_1", "dst_re", "riding_new_shaped", **mp)],
        [_tenure("t_1", "dst_ra")],
        census={},
    )
    assert pd.isna(out["east"])
