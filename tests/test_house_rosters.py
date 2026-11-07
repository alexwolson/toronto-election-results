"""Federal incumbency from House of Commons membership, and Office tenure spells."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.federal_rosters import (
    build_house_roster_evidence,
    house_member_name_fits,
    read_house_members,
)
from toronto_election_results.tenure_spells import assign_tenure_spells

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
REFERENCE = REPO_ROOT / "data" / "reference"


def _results() -> pd.DataFrame:
    return pd.read_csv(OUT / "election_results.csv", dtype=str, keep_default_na=False)


def _tenures() -> pd.DataFrame:
    return pd.read_csv(OUT / "office_tenures.csv", dtype=str, keep_default_na=False)


def test_membership_file_covers_the_35th_to_45th_parliaments():
    members = read_house_members(REFERENCE)
    assert members is not None
    assert sorted(set(members["parliament"].astype(int))) == list(range(35, 46))
    ended = members.loc[members["to_date"].ne("")]
    assert (ended["to_date"] >= ended["from_date"]).all()
    p35 = members.loc[members["parliament"].eq("35")]
    assert p35["from_date"].ge("1993-10-25").all() and p35["to_date"].le("1997-06-01").all()
    assert members.loc[members["to_date"].eq(""), "parliament"].eq("45").all()


def test_every_toronto_federal_winner_has_a_house_tenure():
    results = _results()
    winners = results.loc[results["office_type"].eq("mp") & results["elected"].eq("True")]
    tenures = _tenures()
    house = tenures.loc[tenures["office_type"].eq("mp")]
    assert len(house) == len(winners)
    assert set(house["person_id"]) == set(winners["person_id"])
    assert (
        house["source_authority"]
        .isin({"House of Commons", "Library of Parliament (ParlInfo)"})
        .all()
    )
    assert house["started_on_precision"].eq("election_date").all()
    assert house["ended_on_precision"].isin({"exact", "ongoing"}).all()
    assert house.loc[house["ended_on_precision"].eq("ongoing"), "ended_on"].eq("").all()


def test_federal_incumbency_is_known_for_every_confirmed_person_after_1993():
    results = _results()
    federal = results.loc[results["office_type"].eq("mp")]
    first = federal["event_id"].eq("ec-ge-35")
    assert federal.loc[first, "incumbent"].eq("").all()
    later = federal.loc[~first]
    assert later.loc[later["person_id"].ne(""), "incumbent"].isin({"True", "False"}).all()
    assert later.loc[later["person_id"].eq(""), "incumbent"].eq("").all()
    assert federal["incumbent"].value_counts().to_dict() == {"False": 1242, "": 295, "True": 206}
    tenures = _tenures().set_index("office_tenure_id")
    true = later.loc[later["incumbent"].eq("True")]
    assert tenures.loc[true["incumbent_office_tenure_id"], "office_type"].eq("mp").all()


@pytest.mark.parametrize(
    ("first", "last", "ballot", "fits"),
    [
        ("Jim", "Karygiannis", "Jim Karygiannis", True),
        ("James", "Karygiannis", "Jim Karygiannis", True),
        ("Douglas Dennison", "Peters", "Doug Peters", True),
        ("Nathaniel", "Erskine-Smith", "NATE ERSKINE-SMITH", True),
        ("A. Anne", "McLellan", "Anne McLellan", True),
        ("Joy", "Smith", "Paul Smith", False),
        ("Paul", "Smith", "Paul Smyth", False),
    ],
)
def test_house_member_name_fits(first, last, ballot, fits):
    assert house_member_name_fits(first, last, ballot) is fits


def _member(name: tuple[str, str], riding: str, start: str, end: str) -> dict[str, str]:
    return {
        "parliament": "40",
        "house_person_id": "",
        "first_name": name[0],
        "last_name": name[1],
        "constituency": riding,
        "province": "Ontario",
        "caucus": "",
        "from_date": start,
        "to_date": end,
        "source": "test",
    }


def _run(candidacy_id: str, name: str, event_id: str, day: str, person_id: str, elected: bool):
    return {
        "candidacy_id": candidacy_id,
        "event_id": event_id,
        "election_date": day,
        "election_type": "general",
        "represented_body": "canada_house_of_commons",
        "office_type": "mp",
        "district_id": "dst_a",
        "district_name": "Toronto Centre",
        "candidate_name": name,
        "person_id": person_id,
        "elected": elected,
        "source_detail": "test",
    }


def test_a_candidate_who_fits_a_sitting_member_elsewhere_fails_the_build():
    members = pd.DataFrame(
        [
            _member(("Ann", "Lee"), "Toronto Centre", "2008-10-14", "2011-05-01"),
            _member(("Pat", "Ross"), "Ottawa Centre", "2008-10-14", "2011-05-01"),
        ]
    )
    candidacies = pd.DataFrame(
        [
            _run("can_1", "Ann Lee", "ec-ge-40", "2008-10-14", "per_lee", True),
            _run("can_2", "Pat Ross", "ec-ge-41", "2011-05-02", "per_ross", False),
        ]
    )
    candidacies["elected"] = candidacies["elected"].astype("boolean")
    with pytest.raises(ValueError, match="fits the sitting member Pat Ross"):
        build_house_roster_evidence(candidacies, members)


def test_house_rosters_mark_sitting_members_and_prove_absence():
    members = pd.DataFrame([_member(("Ann", "Lee"), "Toronto Centre", "2008-10-14", "2011-05-01")])
    candidacies = pd.DataFrame(
        [
            _run("can_1", "Ann Lee", "ec-ge-40", "2008-10-14", "per_lee", True),
            _run("can_2", "Ann Lee", "ec-ge-41", "2011-05-02", "per_lee", False),
            _run("can_3", "Bo Chan", "ec-ge-41", "2011-05-02", "per_chan", False),
        ]
    )
    candidacies["elected"] = candidacies["elected"].astype("boolean")
    evidence, covered = build_house_roster_evidence(candidacies, members)
    assert covered == {"ec-ge-41"}
    roster = evidence.rosters.loc[evidence.rosters["event_id"].eq("ec-ge-41")]
    assert roster["person_id"].tolist() == ["per_lee"]
    assert roster["roster_complete"].all()
    assert evidence.office_tenures["ended_on"].tolist() == ["2011-05-01"]


def _tenure(tenure_id: str, start: str, end: str) -> dict[str, str]:
    return {
        "office_tenure_id": tenure_id,
        "person_id": "per_1",
        "represented_body": "toronto_city_council",
        "office_type": "councillor",
        "started_on": start,
        "ended_on": end,
    }


def test_spells_join_touching_rows_and_split_at_a_gap():
    tenures = pd.DataFrame(
        [
            _tenure("ten_a", "2003-11-10", "2006-11-13"),
            _tenure("ten_b", "2006-11-13", "2010-10-25"),
            _tenure("ten_c", "2010-10-26", "2014-10-27"),
            _tenure("ten_d", "2018-10-22", "2022-10-24"),
            _tenure("ten_e", "", "2022-10-24"),
        ]
    )
    spells = assign_tenure_spells(tenures).set_index("office_tenure_id")["spell_id"]
    assert spells["ten_a"] == spells["ten_b"] == spells["ten_c"]
    assert spells["ten_d"] != spells["ten_a"]
    assert pd.isna(spells["ten_e"])
