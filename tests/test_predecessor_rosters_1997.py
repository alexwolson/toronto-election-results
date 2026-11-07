"""Predecessor incumbency for the first amalgamated elections, 10 November 1997 (ADR 0012)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.predecessor_incumbency import (
    build_predecessor_roster_evidence,
    read_predecessor_rosters,
)

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
REFERENCE = REPO_ROOT / "data" / "reference"
COUNCILS = {
    "metro_toronto_council",
    "former_toronto_city_council",
    "north_york_city_council",
    "scarborough_city_council",
    "etobicoke_city_council",
    "york_city_council",
    "east_york_borough_council",
}


def _results() -> pd.DataFrame:
    return pd.read_csv(OUT / "election_results.csv", dtype=str, keep_default_na=False)


def test_rosters_fill_every_seat_elected_in_1994():
    rosters = read_predecessor_rosters(REFERENCE)
    assert rosters is not None
    assert set(rosters["represented_body"]) == COUNCILS
    results = _results()
    won_1994 = results.loc[
        results["election_date"].eq("1994-11-14")
        & results["represented_body"].isin(COUNCILS)
        & results["elected"].eq("True")
    ]
    seats = won_1994.groupby(["represented_body", "office_type"]).size()
    listed = rosters.groupby(["represented_body", "office_type"]).size()
    assert listed.to_dict() == seats.to_dict()
    assert len(rosters) == 106
    assert rosters["arrival"].value_counts().to_dict() == {
        "elected": 104,
        "by_election": 1,
        "appointed": 1,
    }
    names = set(rosters["member_name"])
    assert not names & {"Mario Sergio", "John Hastings"}
    assert {"George Mammoliti", "Vincent Chrisanti"} <= names


def test_1997_council_and_mayoral_runs_have_predecessor_incumbency():
    results = _results()
    first = results.loc[results["election_date"].eq("1997-11-10")]
    council = first.loc[first["represented_body"].eq("toronto_city_council")]
    flags = council.groupby("office_type")["predecessor_incumbent"].value_counts().to_dict()
    assert flags == {
        ("councillor", "False"): 101,
        ("councillor", "True"): 81,
        ("councillor", ""): 11,
        ("mayor", "False"): 17,
        ("mayor", "True"): 2,
        ("mayor", ""): 1,
    }
    assert council.loc[council["person_id"].eq(""), "predecessor_incumbent"].eq("").all()
    trustees = first.loc[first["office_type"].eq("trustee")]
    assert trustees["predecessor_incumbent"].eq("").all()
    by_name = council.set_index(["candidate_name", "office_type"])["predecessor_incumbent"]
    assert by_name[("Mel Lastman", "mayor")] == "True"
    assert by_name[("Barbara Hall", "mayor")] == "True"
    assert by_name[("George Mammoliti", "councillor")] == "True"
    assert by_name[("Vincent Crisanti", "councillor")] == "True"
    # A sitting mayor who ran for council is not a predecessor councillor (ADR 0012).
    assert by_name[("Frank Faubert", "councillor")] == "False"
    assert (
        results.loc[~results["election_date"].eq("1997-11-10"), "predecessor_incumbent"]
        .eq("")
        .all()
    )


def test_predecessor_tenures_support_every_true_flag():
    results = _results()
    tenures = pd.read_csv(OUT / "office_tenures.csv", dtype=str, keep_default_na=False)
    tenures = tenures.set_index("office_tenure_id")
    true = results.loc[results["predecessor_incumbent"].eq("True")]
    held = tenures.loc[true["predecessor_office_tenure_id"]]
    assert held["represented_body"].isin(COUNCILS).all()
    assert (held["person_id"].to_numpy() == true["person_id"].to_numpy()).all()
    assert held["ended_on"].eq("1997-11-09").all()


def test_missing_roster_file_leaves_no_predecessor_evidence(tmp_path):
    assert read_predecessor_rosters(tmp_path) is None
    evidence = build_predecessor_roster_evidence(pd.DataFrame(), None)
    assert evidence.office_tenures.empty
    assert evidence.complete_rosters == frozenset()


def test_a_roster_short_of_its_1994_seats_fails():
    candidacies = pd.DataFrame(
        [
            {
                "candidacy_id": f"can_{index}",
                "person_id": f"per_{index}",
                "election_date": "1994-11-14",
                "represented_body": "york_city_council",
                "office_type": "councillor",
                "district_id": "dst_york",
                "elected": True,
            }
            for index in range(2)
        ]
    )
    rosters = pd.DataFrame(
        [
            {
                "represented_body": "york_city_council",
                "office_type": "councillor",
                "district_name": "Ward 1",
                "member_name": "Pat Example",
                "arrival": "elected",
                "candidacy_id": "can_0",
                "basis": "test",
                "evidence_urls": "https://example.org",
                "started_on": "",
                "started_on_precision": "",
            }
        ]
    )
    with pytest.raises(ValueError, match="does not fill every 1994 seat"):
        build_predecessor_roster_evidence(candidacies, rosters)
