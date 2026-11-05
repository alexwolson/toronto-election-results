"""The Council roster for the November 13, 2000 general election."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.incumbency import COUNCIL_ROSTER_2000, roster_2000_composition

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
REFERENCE = REPO_ROOT / "data" / "reference"
EVENT_2000 = "evt_b4a8433485f551878400c616c3d023b2"


def _roster() -> pd.DataFrame:
    lines = [
        line
        for line in (REFERENCE / COUNCIL_ROSTER_2000).read_text(encoding="utf-8").splitlines()
        if not line.startswith("#")
    ]
    return pd.read_csv(StringIO("\n".join(lines)), dtype=str, keep_default_na=False)


def _results() -> pd.DataFrame:
    return pd.read_csv(OUT / "election_results.csv", dtype="string", keep_default_na=False)


def test_roster_is_the_council_on_the_eve_of_the_2000_election():
    roster = _roster()
    assert len(roster) == 58
    assert roster["member_name"].is_unique
    counts = roster["ward"].value_counts()
    assert counts["mayor"] == 1
    # Two councillors in each of the 28 wards, and a third East York seat added in 1998.
    assert counts.drop("mayor").to_dict() == {
        str(ward): 3 if ward == 1 else 2 for ward in range(1, 29)
    }
    # Members who left during the term and the people who took their seats.
    assert not roster["member_name"].isin({"Frank Faubert", "Judy Sgro", "Dennis Fotinos"}).any()
    changes = roster.set_index("member_name")
    assert changes.loc["David Soknacki", "ward"] == "16"
    assert changes.loc["Paul Valenti", ["ward", "arrival"]].tolist() == ["6", "appointed"]
    assert changes.loc["Cesar Palacio", ["ward", "arrival"]].tolist() == ["21", "appointed"]
    assert changes.loc["Jane Pitfield", "ward"] == "1"
    assert roster["evidence_urls"].str.startswith("https://").all()


def test_elected_roster_members_match_their_certified_results_exactly():
    roster = _roster()
    results = _results()
    seated = results.loc[
        results["represented_body"].eq("toronto_city_council")
        & results["elected"].eq("True")
        & results["election_date"].isin({"1997-11-10", "1998-09-24", "1999-09-23"})
    ]
    elected = roster.loc[roster["arrival"].eq("elected")]
    assert len(elected) == 56
    assert set(elected["member_name"]) <= set(seated["candidate_name"])
    for row in elected.itertuples(index=False):
        winner = seated.loc[seated["candidate_name"].eq(row.member_name)]
        assert len(winner) == 1, row.member_name
        expected = "City of Toronto" if row.ward == "mayor" else f"Ward {row.ward}"
        assert winner["district_name"].item() == expected, row.member_name


def test_2000_council_incumbency_comes_from_the_roster():
    results = _results()
    general = results.loc[
        results["event_id"].eq(EVENT_2000) & results["represented_body"].eq("toronto_city_council")
    ]
    assert len(general) == 167
    incumbent = general["incumbent"]
    assert incumbent.eq("True").sum() == 48
    # A complete roster proves absence, so only Candidacies without a Person stay null.
    assert general.loc[incumbent.eq(""), "person_id"].eq("").all()
    assert general.loc[general["person_id"].ne(""), "incumbent"].isin({"True", "False"}).all()
    assert general.loc[incumbent.eq("True"), "incumbent_office_tenure_id"].ne("").all()
    by_name = general.set_index("candidate_name")
    for name in ("Mel Lastman", "Jane Pitfield", "David Soknacki", "Bas Balkissoon"):
        assert by_name.loc[name, "incumbent"] == "True", name


def test_roster_members_without_a_candidacy_keep_one_person():
    results = _results()
    people = pd.read_csv(OUT / "people.csv", dtype="string").set_index("person_id")
    tenures = pd.read_csv(OUT / "office_tenures.csv", dtype="string")
    palacio = "per_f43071f7a8d95740a4fcc8890b28d327"
    assert people.loc[palacio, "preferred_name"] == "Cesar Palacio"
    assert tenures["person_id"].eq(palacio).any()
    valenti = people.loc[people["preferred_name"].eq("Paul Valenti")]
    assert len(valenti) == 1
    assert not results["person_id"].isin(valenti.index).any()
    assert tenures["person_id"].isin(valenti.index).any()


def test_missing_roster_file_leaves_2000_without_a_composition(tmp_path):
    assert roster_2000_composition(reference=tmp_path).empty


def test_roster_file_holds_only_the_1997_2000_term(tmp_path):
    (tmp_path / COUNCIL_ROSTER_2000).write_text(
        "# comment\nterm,ward,member_name,arrival,basis,evidence_urls\n"
        "2000-2003,1,Pat Example,elected,x,https://example.org\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="1997-2000"):
        roster_2000_composition(reference=tmp_path)
