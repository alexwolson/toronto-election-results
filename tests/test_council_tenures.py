"""Dating Council roster tenures from the member's own term (`council_tenures`)."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.council_tenures import (
    APPOINTMENT_COLUMNS,
    COUNCIL_APPOINTMENTS_FILENAME,
    date_council_rosters,
    read_council_appointments,
)

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
REFERENCE = REPO_ROOT / "data" / "reference"
RULE = "last_valid_council_composition_before_general_election"


def _run(candidacy_id, person_id, date, district, ward, name, *, elected, general=True):
    return {
        "candidacy_id": candidacy_id,
        "person_id": person_id,
        "represented_body": "toronto_city_council",
        "office_type": "councillor",
        "election_date": date,
        "election_type": "general" if general else "by_election",
        "elected": elected,
        "district_id": district,
        "official_district_id": ward,
        "candidate_name": name,
    }


def _candidacies() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _run("c1", "per_a", "2010-10-25", "dst_21", "ward-21", "Norman Able", elected=True),
            _run("c2", "per_a", "2014-10-27", "dst_21", "ward-21", "Norm Able", elected=True),
            _run("c3", "per_m", "2014-10-27", "dst_22", "ward-22", "Joe Mint", elected=True),
            _run("c4", "per_m", "2018-10-22", "dst_n12", "ward-12", "Joe Mint", elected=False),
            _run("c5", "per_c", "2018-10-22", "dst_n10", "ward-10", "Joe Cress", elected=True),
            _run("c6", "per_x", "2022-10-24", "dst_n10", "ward-10", "Ann Other", elected=True),
        ]
    )


def _roster_row(tenure_id, person_id, ended_on, member_name, *, started_on=None, entry=None):
    detail = {"member_name": member_name, "rule": RULE, "source": "city_voting"}
    if entry is not None:
        detail["entry_method"] = entry
    return {
        "office_tenure_id": tenure_id,
        "person_id": person_id,
        "represented_body": "toronto_city_council",
        "office_type": "councillor",
        "district_id": "dst_21" if started_on else pd.NA,
        "started_on": started_on if started_on else pd.NA,
        "started_on_precision": "election_date" if started_on else "unknown",
        "ended_on": ended_on,
        "ended_on_precision": "at_or_after_reference",
        "entry_method": entry or "unknown",
        "source_authority": "City of Toronto",
        "source_detail": json.dumps(detail, sort_keys=True, separators=(",", ":")),
    }


def _appointments(**overrides) -> pd.DataFrame:
    record = {
        "term": "2018-2022",
        "official_district_id": "ward-10",
        "member_name": "Joe Mint",
        "predecessor": "Joe Cress",
        "appointed_on": "2022-06-01",
        "basis": "By-law 524-2022 appoints Joe Mint.",
        "source_url": "https://www.toronto.ca/legdocs/bylaws/2022/law0524.pdf",
    }
    record.update(overrides)
    return pd.DataFrame([record], columns=list(APPOINTMENT_COLUMNS))


def test_a_roster_row_is_dated_from_the_persons_latest_win_in_the_term():
    tenures = pd.DataFrame(
        [
            _roster_row(
                "ten_a", "per_a", "2018-10-22", "Norman Able", started_on="2010-10-25", entry=None
            )
        ]
    )
    dated = date_council_rosters(tenures, _candidacies(), _appointments().iloc[0:0])
    row = dated.iloc[0]
    assert row["started_on"] == datetime.date(2014, 10, 27)
    assert row["started_on_precision"] == "election_date"
    assert row["district_id"] == "dst_21"
    assert row["entry_method"] == "election"


def test_an_appointed_member_is_dated_from_the_appointment_not_an_earlier_term():
    tenures = pd.DataFrame(
        [
            _roster_row(
                "ten_m",
                "per_m",
                "2022-10-24",
                "Joe Mint",
                started_on="2014-10-27",
                entry="appointment",
            )
        ]
    )
    dated = date_council_rosters(tenures, _candidacies(), _appointments())
    row = dated.iloc[0]
    assert row["started_on"] == datetime.date(2022, 6, 1)
    assert row["started_on_precision"] == "appointment_date"
    assert row["district_id"] == "dst_n10"
    assert row["entry_method"] == "appointment"
    assert json.loads(row["source_detail"])["appointment"] == {
        "appointed_on": "2022-06-01",
        "predecessor": "Joe Cress",
        "source_url": "https://www.toronto.ca/legdocs/bylaws/2022/law0524.pdf",
    }


def test_a_roster_row_with_neither_a_win_nor_an_appointment_fails():
    tenures = pd.DataFrame(
        [_roster_row("ten_m", "per_m", "2022-10-24", "Joe Mint", entry="appointment")]
    )
    with pytest.raises(ValueError, match="no Council win in the term"):
        date_council_rosters(tenures, _candidacies(), _appointments().iloc[0:0])


def test_a_member_with_a_win_in_the_term_cannot_be_recorded_as_appointed():
    tenures = pd.DataFrame([_roster_row("ten_a", "per_a", "2018-10-22", "Joe Mint")])
    appointments = _appointments(term="2014-2018", appointed_on="2016-01-01")
    with pytest.raises(ValueError, match="recorded as appointed"):
        date_council_rosters(tenures, _candidacies(), appointments)


def test_an_appointment_that_matches_no_roster_row_fails():
    tenures = pd.DataFrame([_roster_row("ten_a", "per_a", "2018-10-22", "Norm Able")])
    with pytest.raises(ValueError, match="no Council roster row is theirs"):
        date_council_rosters(tenures, _candidacies(), _appointments())


def test_an_appointment_must_name_the_member_who_won_the_seat():
    tenures = pd.DataFrame(
        [_roster_row("ten_m", "per_m", "2022-10-24", "Joe Mint", entry="appointment")]
    )
    with pytest.raises(ValueError, match="did not win ward-10"):
        date_council_rosters(tenures, _candidacies(), _appointments(predecessor="Ann Other"))


def test_the_reference_file_is_checked(tmp_path: Path):
    path = tmp_path / COUNCIL_APPOINTMENTS_FILENAME
    _appointments(appointed_on="2023-01-05").to_csv(path, index=False)
    with pytest.raises(ValueError, match="outside its term"):
        read_council_appointments(path)
    _appointments(source_url="http://example.org").to_csv(path, index=False)
    with pytest.raises(ValueError, match="https"):
        read_council_appointments(path)
    assert read_council_appointments(tmp_path / "missing.csv") is None


def test_every_published_council_roster_row_is_dated():
    tenures = pd.read_csv(OUT / "office_tenures.csv", dtype=str, keep_default_na=False)
    council = tenures.loc[tenures["represented_body"].eq("toronto_city_council")]
    assert council["started_on"].ne("").all()
    assert council["district_id"].ne("").all()
    assert council["spell_id"].ne("").all()
    assert set(council["entry_method"]) == {"election", "appointment"}
    appointed = council.loc[council["entry_method"].eq("appointment")]
    assert set(appointed["started_on_precision"]) == {"appointment_date"}
    reference = read_council_appointments(REFERENCE / COUNCIL_APPOINTMENTS_FILENAME)
    assert reference is not None
    details = appointed["source_detail"].map(json.loads)
    published = sorted(
        (detail["member_name"], started_on)
        for detail, started_on in zip(details, appointed["started_on"], strict=True)
    )
    assert published == sorted(zip(reference["member_name"], reference["appointed_on"]))


def test_joe_mihevc_2022_seat_is_his_appointment_to_ward_10():
    tenures = pd.read_csv(OUT / "office_tenures.csv", dtype=str, keep_default_na=False)
    districts = pd.read_csv(
        OUT / "electoral_districts.csv",
        dtype=str,
        keep_default_na=False,
        usecols=["district_id", "district_name"],
    ).set_index("district_id")["district_name"]
    rows = tenures.loc[
        tenures["source_detail"].str.contains('"member_name":"Joe Mihevc"', regex=False)
        & tenures["ended_on"].eq("2022-10-24")
    ]
    assert len(rows) == 1
    row = rows.iloc[0]
    assert (row["started_on"], row["entry_method"]) == ("2022-06-01", "appointment")
    assert districts[row["district_id"]] == "Ward 10 — Spadina-Fort York"
