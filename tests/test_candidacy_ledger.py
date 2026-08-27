"""Persistent source-occurrence identity for published Candidacies."""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.candidacy_ledger import (
    assign_candidacy_ids,
    empty_candidacy_ledger,
    read_candidacy_ledger,
    record_candidate_name_correction,
    validate_candidacy_ledger,
    write_candidacy_ledger,
)
from toronto_election_results.schema import normalize_adapter_frame

REFERENCE_LEDGER = (
    Path(__file__).parents[1] / "data" / "reference" / "candidacy_identity_ledger.csv"
)


def _adapter(*, event_id: str = "event-2025", name: str = "Alex Example") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": [event_id],
            "election_date": ["2025-04-28"],
            "election_type": ["general"],
            "election_authority": ["Elections Canada"],
            "represented_body": ["House of Commons of Canada"],
            "office_type": ["Member of Parliament"],
            "boundary_regime": ["federal-2023-order"],
            "official_district_id": ["35001"],
            "district_name": ["Example"],
            "candidate_name_raw": [name],
            "votes": [60],
            "elected": [True],
            "outcome_method": ["vote"],
            "coverage_status": ["complete"],
            "source_detail": ["official.csv"],
        }
    )


def _published_id(frame: pd.DataFrame) -> str:
    return normalize_adapter_frame(frame, require_persistent_candidacy_id=True)[
        "candidacy_id"
    ].item()


def test_checked_in_ledger_covers_every_cutoff_candidacy():
    ledger = read_candidacy_ledger(REFERENCE_LEDGER)

    assert len(ledger) == 5_748
    assert ledger["candidacy_id"].nunique() == 5_748
    assert ledger["source_occurrence_id"].nunique() == 5_748
    assert ledger["valid_to_release"].isna().all()


def test_persisted_empty_or_truncated_ledger_fails_closed(tmp_path):
    truncated = tmp_path / "truncated.csv"
    truncated.write_text("candidacy_id\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        read_candidacy_ledger(truncated)

    empty_path = tmp_path / "empty.csv"
    with pytest.raises(ValueError, match="cannot persist an empty"):
        write_candidacy_ledger(empty_candidacy_ledger(), empty_path)
    empty_candidacy_ledger().to_csv(empty_path, index=False)
    with pytest.raises(ValueError, match="persisted Candidacy ledger is empty"):
        read_candidacy_ledger(empty_path)


def test_first_registration_is_deterministic_and_reused_from_the_ledger():
    first = assign_candidacy_ids([_adapter()], release_id="2026-08-20")
    clean_rebuild = assign_candidacy_ids([_adapter()], release_id="2026-08-20")
    subsequent = assign_candidacy_ids(
        [_adapter()],
        ledger=first.ledger,
        release_id="2027-01-01",
    )

    assert first.ledger["source_occurrence_id"].item().startswith("project-ledger:")
    assert first.ledger["candidate_name_raw"].item() == "Alex Example"
    assert first.ledger["valid_from_release"].item() == "2026-08-20"
    assert pd.isna(first.ledger["valid_to_release"].item())
    assert first.ledger["change_reason"].item() == "initial_registration"
    assert _published_id(first.adapter_frames[0]) == _published_id(clean_rebuild.adapter_frames[0])
    assert _published_id(first.adapter_frames[0]) == _published_id(subsequent.adapter_frames[0])
    pd.testing.assert_frame_equal(first.ledger, clean_rebuild.ledger)
    validate_candidacy_ledger(first.ledger)


def test_name_only_change_fails_closed_until_versioned_correction_is_recorded():
    first = assign_candidacy_ids([_adapter()], release_id="2026-08-20")
    original_id = _published_id(first.adapter_frames[0])

    with pytest.raises(ValueError, match="reconcile the Candidacy ledger"):
        assign_candidacy_ids(
            [_adapter(name="Alexandra Example")],
            ledger=first.ledger,
            release_id="2027-01-01",
        )

    corrected = record_candidate_name_correction(
        first.ledger,
        candidacy_id=original_id,
        candidate_name_raw="Alexandra Example",
        release_id="2027-01-01",
        reason="authority corrected the ballot spelling",
    )
    rebuilt = assign_candidacy_ids(
        [_adapter(name="Alexandra Example")],
        ledger=corrected,
        release_id="2027-01-01",
    )

    assert _published_id(rebuilt.adapter_frames[0]) == original_id
    history = rebuilt.ledger.sort_values("valid_from_release")
    assert history["candidate_name_raw"].tolist() == ["Alex Example", "Alexandra Example"]
    assert history["valid_to_release"].tolist()[0] == "2027-01-01"
    assert pd.isna(history["valid_to_release"].tolist()[1])
    assert history["candidacy_id"].nunique() == 1
    assert history.iloc[1]["change_reason"] == "authority corrected the ballot spelling"


@pytest.mark.parametrize("release_id", ["2026-08-20", "2025-01-01"])
def test_name_correction_requires_a_later_release(release_id):
    first = assign_candidacy_ids([_adapter()], release_id="2026-08-20")

    with pytest.raises(ValueError, match="later than the active locator release"):
        record_candidate_name_correction(
            first.ledger,
            candidacy_id=first.ledger["candidacy_id"].item(),
            candidate_name_raw="Alexandra Example",
            release_id=release_id,
            reason="authority corrected the ballot spelling",
        )


def test_authority_ids_disambiguate_same_named_candidates():
    same_named = pd.concat([_adapter(), _adapter()], ignore_index=True)
    same_named["source_candidacy_id"] = ["authority-candidate-1", "authority-candidate-2"]

    assignment = assign_candidacy_ids([same_named], release_id="2026-08-20")

    assert assignment.ledger["candidate_name_raw"].nunique() == 1
    assert assignment.ledger["source_occurrence_id"].nunique() == 2
    assert assignment.ledger["candidacy_id"].nunique() == 2
    assert assignment.ledger["identity_basis"].eq("authority_identifier").all()
    validate_candidacy_ledger(assignment.ledger)


def test_authority_id_name_correction_may_converge_on_an_existing_name():
    initial = pd.concat(
        [_adapter(name="Alex Example"), _adapter(name="Alexandra Example")],
        ignore_index=True,
    )
    initial["source_candidacy_id"] = ["authority-candidate-1", "authority-candidate-2"]
    first = assign_candidacy_ids([initial], release_id="2026-08-20")
    corrected = initial.copy()
    corrected["candidate_name_raw"] = ["Alex Example", "Alex Example"]

    second = assign_candidacy_ids(
        [corrected],
        ledger=first.ledger,
        release_id="2027-01-01",
    )

    active = second.ledger.loc[second.ledger["valid_to_release"].isna()]
    assert len(second.ledger) == 3
    assert active["candidate_name_raw"].tolist() == ["Alex Example", "Alex Example"]
    assert active["candidacy_id"].nunique() == 2


def test_existing_contest_inventory_cannot_silently_gain_or_lose_a_candidacy():
    first = assign_candidacy_ids([_adapter()], release_id="2026-08-20")
    added = pd.concat(
        [_adapter(), _adapter(name="Bailey Sample")],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="existing contest inventory changed"):
        assign_candidacy_ids(
            [added],
            ledger=first.ledger,
            release_id="2027-01-01",
        )

    new_event = assign_candidacy_ids(
        [_adapter(), _adapter(event_id="event-2027", name="Bailey Sample")],
        ledger=first.ledger,
        release_id="2027-01-01",
    )
    assert len(new_event.ledger) == 2
    assert new_event.ledger["candidacy_id"].nunique() == 2

    with pytest.raises(ValueError, match="existing contest inventory changed"):
        assign_candidacy_ids(
            [_adapter()],
            ledger=new_event.ledger,
            release_id="2027-03-01",
        )
