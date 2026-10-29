from pathlib import Path

import pytest

from toronto_election_results.federal_historical import (
    HISTORICAL_FEDERAL_EVENTS,
    MDL_1993_URL,
    historical_federal_placeholder_manifest,
    historical_source_path,
    load_historical_federal_results,
)

RAW_FEDERAL = Path(__file__).resolve().parents[1] / "data" / "raw" / "federal"
needs_sources = pytest.mark.skipif(
    not historical_source_path(RAW_FEDERAL, MDL_1993_URL).is_file(),
    reason="historical federal sources are not cached",
)


def test_manifest_covers_the_pre_2004_toronto_events():
    assert [event.event_id for event in HISTORICAL_FEDERAL_EVENTS] == [
        "ec-ge-35",
        "ec-be-1996-03-25",
        "ec-ge-36",
        "ec-be-1999-11-15",
        "ec-ge-37",
    ]
    sizes = {event.event_id: len(event.districts) for event in HISTORICAL_FEDERAL_EVENTS}
    assert sizes == {
        "ec-ge-35": 23,
        "ec-be-1996-03-25": 1,
        "ec-ge-36": 22,
        "ec-be-1999-11-15": 1,
        "ec-ge-37": 22,
    }


def test_every_historical_federal_contest_has_a_result_source():
    assert historical_federal_placeholder_manifest().empty
    assert all(event.source_url for event in HISTORICAL_FEDERAL_EVENTS)


@needs_sources
def test_historical_results_reconcile_and_elect_one_per_contest():
    results = load_historical_federal_results(RAW_FEDERAL)

    assert results.groupby("event_id").size().to_dict() == {
        "ec-be-1996-03-25": 7,
        "ec-be-1999-11-15": 6,
        "ec-ge-35": 214,
        "ec-ge-36": 150,
        "ec-ge-37": 151,
    }
    elected = results.groupby(["event_id", "official_district_id"])["elected"].sum()
    assert elected.eq(1).all()
    assert results["ballots_cast"].le(results["eligible_electors"]).all()
    york_west = results[results["event_id"].eq("ec-be-1999-11-15")]
    assert york_west.loc[york_west["elected"], "candidate_name_raw"].tolist() == ["Judy Sgro"]
    assert york_west["ballots_cast"].iloc[0] == 13_683
    etobicoke = results[results["event_id"].eq("ec-be-1996-03-25")]
    assert etobicoke.loc[etobicoke["elected"], "candidate_name_raw"].tolist() == ["Roy Cullen"]
    assert etobicoke["votes"].sum() == 26_520
    assert etobicoke["ballots_cast"].iloc[0] == 26_747
