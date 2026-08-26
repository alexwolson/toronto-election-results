"""Persistent Person linkage and same-office incumbency semantics."""

import pandas as pd
import pytest

from toronto_election_results.identity import (
    attach_confirmed_people,
    derive_incumbency,
    new_person_id,
    validate_identity_tables,
)


def _candidacies() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidacy_id": ["can_old", "can_new", "can_mayor", "can_unknown"],
            "event_id": ["evt_old", "evt_new", "evt_new", "evt_new"],
            "represented_body": [
                "toronto_city_council",
                "toronto_city_council",
                "toronto_city_council",
                "toronto_city_council",
            ],
            "office_type": ["councillor", "councillor", "mayor", "councillor"],
        }
    )


def _people_and_links():
    people = pd.DataFrame(
        {
            "person_id": ["per_alex", "per_bailey"],
            "preferred_name": ["Alex Example", "Bailey Sample"],
            "identity_status": ["active", "active"],
            "redirect_to_person_id": [pd.NA, pd.NA],
        }
    )
    links = pd.DataFrame(
        {
            "candidacy_id": ["can_old", "can_new", "can_mayor", "can_unknown"],
            "person_id": ["per_alex", "per_alex", "per_alex", "per_bailey"],
            "link_status": ["confirmed", "confirmed", "confirmed", "proposed"],
            "method": ["official_biography", "official_biography", "curated", "exact_name"],
            "evidence": ["source-a", "source-b", "source-c", pd.NA],
            "reviewer": ["agent", "agent", "agent", pd.NA],
            "valid_from_release": ["v1", "v1", "v1", "v1"],
            "valid_to_release": [pd.NA, pd.NA, pd.NA, pd.NA],
        }
    )
    return people, links


def test_person_ids_are_opaque_and_never_reused():
    first = new_person_id()
    second = new_person_id()

    assert first.startswith("per_")
    assert second.startswith("per_")
    assert first != second


def test_only_confirmed_active_links_attach_to_candidacies():
    people, links = _people_and_links()

    attached = attach_confirmed_people(_candidacies(), people, links)

    assert attached.loc[attached.candidacy_id == "can_old", "person_id"].item() == "per_alex"
    assert attached.loc[attached.candidacy_id == "can_unknown", "person_id"].isna().item()


def test_registry_rejects_two_active_confirmed_people_for_one_candidacy():
    people, links = _people_and_links()
    links = pd.concat(
        [
            links,
            pd.DataFrame(
                [
                    {
                        **links.iloc[0].to_dict(),
                        "person_id": "per_bailey",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="multiple active confirmed"):
        validate_identity_tables(people, links)


def test_registry_rejects_two_active_person_claims_for_one_candidacy():
    people, links = _people_and_links()
    links = pd.concat(
        [
            links,
            pd.DataFrame(
                [
                    {
                        **links.iloc[-1].to_dict(),
                        "person_id": "per_alex",
                        "link_status": "unresolved",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    with pytest.raises(ValueError, match="multiple active Person claims"):
        validate_identity_tables(people, links)


def test_incumbency_uses_last_roster_for_same_body_and_office_not_district():
    people, links = _people_and_links()
    attached = attach_confirmed_people(_candidacies(), people, links)
    rosters = pd.DataFrame(
        {
            "event_id": ["evt_new", "evt_new"],
            "person_id": ["per_alex", pd.NA],
            "represented_body": ["toronto_city_council", "toronto_city_council"],
            "office_type": ["councillor", "mayor"],
            "office_tenure_id": ["ten_alex_councillor", pd.NA],
            "roster_complete": [True, True],
            "reference_date": ["2022-08-19", "2022-08-19"],
            "source_detail": [
                "certified pre-election council roster",
                "certified pre-election mayor roster",
            ],
        }
    )

    out = derive_incumbency(attached, rosters)

    assert out.loc[out.candidacy_id == "can_new", "incumbent"].item()
    assert not out.loc[out.candidacy_id == "can_mayor", "incumbent"].item()
    assert pd.isna(out.loc[out.candidacy_id == "can_unknown", "incumbent"].item())
    assert (
        out.loc[out.candidacy_id == "can_new", "incumbent_office_tenure_id"].item()
        == "ten_alex_councillor"
    )


def test_complete_empty_roster_proves_false_but_incomplete_roster_is_unknown():
    people, links = _people_and_links()
    attached = attach_confirmed_people(_candidacies().iloc[[1]], people, links)
    complete = pd.DataFrame(
        {
            "event_id": ["evt_new"],
            "person_id": [pd.NA],
            "represented_body": ["toronto_city_council"],
            "office_type": ["councillor"],
            "office_tenure_id": [pd.NA],
            "roster_complete": [True],
            "reference_date": ["2022-08-19"],
            "source_detail": ["complete empty roster"],
        }
    )

    assert not derive_incumbency(attached, complete)["incumbent"].item()
    incomplete = complete.copy()
    incomplete["roster_complete"] = False
    assert pd.isna(derive_incumbency(attached, incomplete)["incumbent"].item())
