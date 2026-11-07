"""Ontario incumbency from the Legislative Assembly's member records."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.federal_rosters import (
    MemberIdentity,
    build_membership_roster_evidence,
    house_member_name_fits,
)
from toronto_election_results.ontario_rosters import (
    ONTARIO_ROSTER_SPEC,
    read_ontario_members,
)

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
REFERENCE = REPO_ROOT / "data" / "reference"


def _results() -> pd.DataFrame:
    results = pd.read_csv(OUT / "election_results.csv", dtype=str, keep_default_na=False)
    return results.loc[results["represented_body"].eq("ontario_legislative_assembly")]


def _tenures() -> pd.DataFrame:
    tenures = pd.read_csv(OUT / "office_tenures.csv", dtype=str, keep_default_na=False)
    return tenures.loc[tenures["represented_body"].eq("ontario_legislative_assembly")]


def test_membership_file_covers_the_36th_to_44th_parliaments():
    members = read_ontario_members(REFERENCE)
    assert members is not None
    assert sorted(set(members["parliament"].astype(int))) == list(range(36, 45))
    assert members["from_date"].min() == "1995-06-08"
    assert members.loc[members["to_date"].eq(""), "parliament"].eq("44").all()
    assert members["source"].str.startswith("https://www.ola.org/en/members/all/").all()


def test_every_toronto_ontario_winner_has_a_dated_assembly_tenure():
    results = _results()
    winners = results.loc[results["elected"].eq("True")]
    tenures = _tenures()
    assembly = tenures["source_authority"].eq("Legislative Assembly of Ontario")
    assert tenures.loc[assembly, "started_on"].ne("").all()
    # The rows that are not the Assembly's are the 1995 election's, from Elections Ontario's flags.
    flags = tenures.loc[~assembly]
    assert len(flags) == 26 and flags["ended_on"].eq("1995-04-27").all()
    tenures = tenures.loc[assembly]
    tied = tenures["source_detail"].map(json.loads)
    winning = {
        detail["elected_candidacy"]["candidacy_id"]
        for detail in tied
        if "elected_candidacy" in detail
    }
    # Every winner with a Person; Mohamed Firin's 2025 win is held without one.
    assert winning == set(winners.loc[winners["person_id"].ne(""), "candidacy_id"])
    assert winners["person_id"].eq("").sum() == 1


def test_ontario_incumbency_comes_from_the_assembly_after_1995():
    results = _results()
    first = results["event_id"].eq("on-1995-general")
    assert results.loc[first, "incumbent"].eq(results.loc[first, "incumbent_reported"]).all()
    later = results.loc[~first]
    assert later.loc[later["person_id"].ne(""), "incumbent"].isin({"True", "False"}).all()
    assert later.loc[later["person_id"].eq(""), "incumbent"].eq("").all()
    tenures = _tenures().set_index("office_tenure_id")
    true = later.loc[later["incumbent"].eq("True")]
    assert tenures.loc[true["incumbent_office_tenure_id"], "office_type"].eq("mpp").all()


@pytest.mark.parametrize(
    ("event_id", "name"),
    [("on-1999-general", "MORLEY KELLS"), ("on-2011-general", "BRAD DUGUID")],
)
def test_sitting_members_elections_ontario_did_not_flag_are_incumbents(event_id, name):
    results = _results()
    run = results.loc[results["event_id"].eq(event_id) & results["candidate_name"].eq(name)]
    assert run[["incumbent_reported", "incumbent"]].values.tolist() == [["False", "True"]]


@pytest.mark.parametrize(
    ("first", "last", "ballot", "fits"),
    [
        ("Cheri", "DiNovo", "CHERI DI NOVO", True),
        ("Fatima", "Shaban", "SHABAN, FATIMA", True),
        ("Allan F.", "Leach", "Al Leach", True),
        ("Dave", "Smith", "DAVID SMITH", True),
        ("Ann", "Smith", "DAVID SMITH", False),
    ],
)
def test_assembly_member_name_fits(first, last, ballot, fits):
    assert house_member_name_fits(first, last, ballot) is fits


def _member(slug, name, riding, start, end):
    return {
        "parliament": "37",
        "ola_member_id": slug,
        "first_name": name[0],
        "last_name": name[1],
        "riding": riding,
        "party": "",
        "from_date": start,
        "to_date": end,
        "source": f"https://www.ola.org/en/members/all/{slug}",
    }


def _run(candidacy_id, name, event_id, day, person_id, elected, district="Riverdale"):
    return {
        "candidacy_id": candidacy_id,
        "event_id": event_id,
        "election_date": day,
        "election_type": "by_election" if "-by-" in event_id else "general",
        "represented_body": "ontario_legislative_assembly",
        "office_type": "mpp",
        "district_id": f"dst_{district}",
        "district_name": district,
        "candidate_name": name,
        "person_id": person_id,
        "elected": elected,
        "source_detail": "test",
    }


def test_a_renamed_ridings_term_continues_the_members_tenure():
    members = pd.DataFrame(
        [
            _member("ann-lee", ("Ann", "Lee"), "Riverdale", "1999-06-03", "2003-10-01"),
            _member("ann-lee", ("Ann", "Lee"), "Toronto East", "2000-06-29", "2003-09-02"),
        ]
    )
    candidacies = pd.DataFrame(
        [
            _run("can_1", "ANN LEE", "on-1999-general", "1999-06-03", "per_lee", True),
            _run("can_2", "ANN LEE", "on-2003-general", "2003-10-02", "per_lee", False),
        ]
    )
    candidacies["elected"] = candidacies["elected"].astype("boolean")
    evidence, covered = build_membership_roster_evidence(candidacies, members, ONTARIO_ROSTER_SPEC)
    assert covered == {"on-2003-general"}
    assert len(evidence.office_tenures) == 1
    tenure = evidence.office_tenures.iloc[0]
    assert tenure["ended_on"] == "2003-10-01"
    assert json.loads(tenure["source_detail"])["continued_in"][0]["riding"] == "Toronto East"
    roster = evidence.rosters.loc[evidence.rosters["event_id"].eq("on-2003-general")]
    assert roster["person_id"].tolist() == ["per_lee"]


def test_a_member_elected_outside_toronto_needs_a_source_to_join_a_person():
    members = pd.DataFrame(
        [_member("bo-chan", ("Bo", "Chan"), "Oxford", "2001-03-22", "2003-10-01")]
    )
    candidacies = pd.DataFrame(
        [_run("can_1", "BO CHAN", "on-2003-general", "2003-10-02", "per_chan", False)]
    )
    candidacies["elected"] = candidacies["elected"].astype("boolean")
    with pytest.raises(ValueError, match="fits the sitting member Bo Chan"):
        build_membership_roster_evidence(candidacies, members, ONTARIO_ROSTER_SPEC)

    identity = MemberIdentity("bo-chan", "can_1", "A source says so.", ("https://example.org",))
    spec = replace(ONTARIO_ROSTER_SPEC, member_persons={"bo-chan": identity})
    evidence, _ = build_membership_roster_evidence(candidacies, members, spec)
    assert evidence.rosters["person_id"].tolist() == ["per_chan"]
    namesake = replace(ONTARIO_ROSTER_SPEC, member_persons={}, namesakes=(identity,))
    evidence, _ = build_membership_roster_evidence(candidacies, members, namesake)
    assert evidence.rosters["person_id"].isna().all()
