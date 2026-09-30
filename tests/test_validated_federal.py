"""Validated official totals must reconcile before they become published results."""

from pathlib import Path

import pytest

from toronto_election_results.federal import federal_event_manifest, parse_federal_results
from toronto_election_results.schema import normalize_adapter_frame

FIXTURE = Path(__file__).parent / "fixtures/federal/validated-beaches-east-york-2026.html"


def test_validated_by_election_enters_the_normalized_federal_contract():
    result = parse_federal_results(FIXTURE, event_id="ec-be-2026-08-31")

    assert len(result) == 6
    assert result["votes"].sum() == 33_137
    assert result["ballots_cast"].eq(33_248).all()
    assert result["eligible_electors"].eq(81_642).all()
    assert result.loc[result["elected"], "candidate_name_raw"].tolist() == ["Tanveer Shahnawaz"]
    assert normalize_adapter_frame(result)["result_status"].eq("final").all()
    assert result["incumbent_reported"].isna().all()
    assert result["source_resource"].eq("Results Validated by the Returning Officer").all()
    event = federal_event_manifest().set_index("event_id").loc["ec-be-2026-08-31"]
    assert event["source_layout"] == "validated_contest"
    assert event["unavailable_source_fields"] == ("incumbent_reported",)
    assert event["winner_derivation"] == "unique_validated_vote_maximum"


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        ("Results Validated by the Returning Officer", "Preliminary Results", "must be validated"),
        ("August 31, 2026", "August 30, 2026", "match the event and district"),
        ("Beaches—East York", "Toronto Centre", "match the event and district"),
        ("33,137", "33,138", "candidate votes must reconcile"),
        ("33,248", "33,249", "ballot totals must reconcile"),
        ("Number of electors on list:", "Elector count unavailable:", "missing the elector count"),
        ("Shannon Devine", "Tanveer Shahnawaz", "candidate names must be unique"),
    ],
)
def test_unvalidated_or_inconsistent_source_fails_closed(tmp_path, old, new, error):
    source = tmp_path / "result.html"
    source.write_text(FIXTURE.read_text().replace(old, new), encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        parse_federal_results(source, event_id="ec-be-2026-08-31")


def test_tied_validated_totals_do_not_invent_a_winner(tmp_path):
    source = tmp_path / "tied.html"
    source.write_text(
        FIXTURE.read_text()
        .replace("8,496", "18,504")
        .replace("33,137", "43,145")
        .replace("33,248", "43,256"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="one unique vote winner"):
        parse_federal_results(source, event_id="ec-be-2026-08-31")
