"""Municipal mayor/councillor adapter into the shared v2 contract."""

import pandas as pd
import pytest

from toronto_election_results.municipal import (
    adapt_council_results,
    council_contest_manifest,
    council_event_manifest,
    validate_council_coverage,
)
from toronto_election_results.schema import derive_result_metrics, normalize_adapter_frame


def _legacy_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "election_year": [2022, 2022, 2022, 2022],
            "election_date": ["2022-10-24"] * 4,
            "election_type": ["general"] * 4,
            "ward_system": ["25-ward"] * 4,
            "office": ["mayor", "mayor", "councillor", "councillor"],
            "ward_number": [pd.NA, pd.NA, 1, 1],
            "ward_name": [pd.NA, pd.NA, "Etobicoke North", "Etobicoke North"],
            "candidate_name_raw": ["Alpha, Alex", "Beta, Bailey", "Gamma Chris", "Delta Drew"],
            "votes": [60, 40, 55, 45],
            "source": ["open_data"] * 4,
            "eligible_electors": [1000, 1000, 200, 200],
            "ballots_cast": [600, 600, 120, 120],
        }
    )


def test_adapter_separates_mayor_and_councillor_contests_and_labels_composite_turnout():
    adapted = adapt_council_results(_legacy_rows())
    out = normalize_adapter_frame(adapted)

    assert out["event_id"].nunique() == 1
    assert out["contest_id"].nunique() == 2
    assert set(out["represented_body"]) == {"toronto_city_council"}
    assert set(out["turnout_scope"]) == {"composite_municipal_ballot"}
    assert set(out["source_detail"]) == {"open_data"}
    mayor = out[out["office_type"] == "mayor"]
    assert set(mayor["official_district_id"]) == {"city"}
    assert set(mayor["district_name"]) == {"City of Toronto"}


def test_unique_vote_maximum_is_marked_from_certified_results():
    out = derive_result_metrics(normalize_adapter_frame(adapt_council_results(_legacy_rows())))

    winners = out.loc[out["elected"].fillna(False), "candidate_name_raw"].tolist()
    assert winners == ["Alpha, Alex", "Gamma Chris"]


def test_unresolved_tie_does_not_invent_a_winner():
    rows = _legacy_rows().iloc[:2].copy()
    rows["votes"] = [50, 50]

    out = adapt_council_results(rows)

    assert out["elected"].isna().all()


def test_single_candidate_is_represented_as_acclamation_without_zero_votes():
    rows = _legacy_rows().iloc[[2]].copy()
    rows["votes"] = 0

    out = derive_result_metrics(normalize_adapter_frame(adapt_council_results(rows)))

    assert out["outcome_method"].item() == "acclamation"
    assert out["elected"].item()
    assert pd.isna(out["votes"].item())


def test_fixed_council_manifest_covers_every_event_and_native_contest():
    events = council_event_manifest()
    contests = council_contest_manifest()

    assert len(events) == 13
    assert events["expected_candidacies"].sum() == 2001
    assert len(contests) == 239
    assert contests["event_id"].nunique() == 13
    general_events = set(events.loc[events["election_type"].eq("general"), "event_id"])
    assert contests.loc[contests["event_id"].isin(general_events)].shape[0] == 232


def test_full_load_coverage_guard_rejects_a_partial_event_subset():
    partial = adapt_council_results(_legacy_rows())

    with pytest.raises(ValueError, match="council event coverage mismatch"):
        validate_council_coverage(partial)
