"""Evidence-backed City Council roster snapshots for v2 incumbency."""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.identity import attach_confirmed_people, derive_incumbency
from toronto_election_results.incumbency import build_composition
from toronto_election_results.municipal_rosters import (
    build_municipal_roster_evidence,
    reconcile_composition_last_holders,
)

REPO_ROOT = Path(__file__).parents[1]
COUNCIL_CACHE = REPO_ROOT / "data" / "raw" / "council"
COUNCIL_REFERENCE = REPO_ROOT / "data" / "reference"


def _candidate(
    candidacy_id: str,
    date: str,
    name: str,
    office: str,
    *,
    elected: object = False,
    election_type: str = "general",
    district_id: str = "dst_ward_1",
) -> dict[str, object]:
    return {
        "candidacy_id": candidacy_id,
        "event_id": f"evt_{date}",
        "election_date": date,
        "election_type": election_type,
        "election_authority": "toronto_city_clerk",
        "represented_body": "toronto_city_council",
        "office_type": office,
        "district_id": district_id,
        # Municipal result files are surname-first; the roster is given-name first.
        "candidate_name_raw": name,
        "elected": elected,
        "source_authority": "City of Toronto",
        "source_resource": "Elections — Official Results",
        "source_detail": f"official-{date}.xlsx",
    }


def _people_and_links() -> tuple[pd.DataFrame, pd.DataFrame]:
    people = pd.DataFrame(
        {
            "person_id": ["per_alex", "per_casey", "per_rowan", "per_new"],
            "preferred_name": ["Alex Ward", "Casey Move", "Rowan Mayor", "New Person"],
            "identity_status": ["active"] * 4,
            "redirect_to_person_id": [pd.NA] * 4,
            "created_release": ["v2"] * 4,
        }
    )
    links = pd.DataFrame(
        [
            _link("can_alex_2018", "per_alex", "confirmed"),
            _link("can_alex_2022", "per_alex", "proposed"),
            _link("can_casey_2018", "per_casey", "confirmed"),
            _link("can_casey_2022_mayor", "per_casey", "proposed"),
            _link("can_rowan_2018", "per_rowan", "confirmed"),
            _link("can_new_2022", "per_new", "confirmed"),
        ]
    )
    return people, links


def _link(candidacy_id: str, person_id: str, status: str) -> dict[str, object]:
    return {
        "candidacy_id": candidacy_id,
        "person_id": person_id,
        "link_status": status,
        "method": "official_candidacy_record" if status == "confirmed" else "exact_name_review",
        "evidence": "official result" if status == "confirmed" else "name only",
        "reviewer": "test",
        "valid_from_release": "v2",
        "valid_to_release": pd.NA,
    }


def _composition() -> pd.DataFrame:
    # City attendance does not identify the mayor, so every row starts with the
    # source fallback of councillor. Rowan's prior certified mayoral win corrects it.
    return pd.DataFrame(
        {
            "election_year": [2022, 2022, 2022],
            "member_name": ["Alex Ward", "Casey Move", "Rowan Mayor"],
            "office": ["councillor", "councillor", "councillor"],
            "incumbent_source": ["city_attendance"] * 3,
            "confidence": [0.95] * 3,
            # A reduced synthetic council, explicitly certified complete for this test.
            "roster_complete": [True] * 3,
        }
    )


def test_general_roster_uses_same_office_not_district_and_confirms_exact_links():
    candidacies = pd.DataFrame(
        [
            _candidate("can_alex_2018", "2018-10-22", "Ward Alex", "councillor", elected=True),
            _candidate("can_casey_2018", "2018-10-22", "Move Casey", "councillor", elected=True),
            _candidate(
                "can_rowan_2018",
                "2018-10-22",
                "Mayor Rowan",
                "mayor",
                elected=True,
                district_id="dst_city",
            ),
            _candidate(
                "can_alex_2022",
                "2022-10-24",
                "Ward Alex",
                "councillor",
                district_id="dst_ward_17",
            ),
            _candidate(
                "can_casey_2022_mayor",
                "2022-10-24",
                "Move Casey",
                "mayor",
                district_id="dst_city",
            ),
            _candidate(
                "can_new_2022",
                "2022-10-24",
                "Person New",
                "mayor",
                district_id="dst_city",
            ),
        ]
    )
    people, links = _people_and_links()

    evidence = build_municipal_roster_evidence(
        candidacies,
        people,
        links,
        release_id="2026-08-20",
        composition=_composition(),
    )

    active_confirmed = evidence.candidacy_person_links.query(
        "link_status == 'confirmed' and valid_to_release.isna()"
    )
    assert active_confirmed.set_index("candidacy_id").loc["can_alex_2022", "person_id"] == (
        "per_alex"
    )
    assert (
        active_confirmed.set_index("candidacy_id").loc["can_casey_2022_mayor", "person_id"]
        == "per_casey"
    )
    assert evidence.rosters["roster_complete"].all()

    attached = attach_confirmed_people(
        candidacies, evidence.people, evidence.candidacy_person_links
    )
    out = derive_incumbency(attached, evidence.rosters).set_index("candidacy_id")

    # Ward boundaries are irrelevant within the councillor office scope.
    assert out.loc["can_alex_2022", "incumbent"]
    # Casey sits as a councillor, so running for mayor does not make Casey a mayor incumbent.
    assert not out.loc["can_casey_2022_mayor", "incumbent"]
    assert not out.loc["can_new_2022", "incumbent"]


def test_exact_name_without_roster_context_remains_only_a_proposal():
    candidacies = pd.DataFrame(
        [
            _candidate("can_alex_2018", "2018-10-22", "Ward Alex", "councillor", elected=True),
            _candidate("can_alex_2022", "2022-10-24", "Ward Alex", "councillor"),
        ]
    )
    people = pd.DataFrame(
        {
            "person_id": ["per_alex"],
            "preferred_name": ["Alex Ward"],
            "identity_status": ["active"],
            "redirect_to_person_id": [pd.NA],
            "created_release": ["v2"],
        }
    )
    links = pd.DataFrame(
        [
            _link("can_alex_2018", "per_alex", "confirmed"),
            _link("can_alex_2022", "per_alex", "proposed"),
        ]
    )

    evidence = build_municipal_roster_evidence(
        candidacies,
        people,
        links,
        release_id="2026-08-20",
        composition=pd.DataFrame(
            columns=[
                "election_year",
                "member_name",
                "office",
                "incumbent_source",
                "confidence",
            ]
        ),
    )

    current = evidence.candidacy_person_links.query("candidacy_id == 'can_alex_2022'")
    assert current.query("link_status == 'confirmed'").empty
    assert current.query("link_status == 'proposed'")["valid_to_release"].isna().all()


def test_global_name_proposal_cannot_confirm_cross_body_identity_from_city_roster():
    candidacies = pd.DataFrame(
        [
            {
                **_candidate(
                    "can_other_body",
                    "2018-06-07",
                    "Ward Alex",
                    "mpp",
                    elected=True,
                ),
                "represented_body": "ontario_legislative_assembly",
            },
            _candidate("can_city", "2022-10-24", "Ward Alex", "councillor"),
        ]
    )
    people = pd.DataFrame(
        {
            "person_id": ["per_other"],
            "preferred_name": ["Alex Ward"],
            "identity_status": ["active"],
            "redirect_to_person_id": [pd.NA],
            "created_release": ["v2"],
        }
    )
    links = pd.DataFrame(
        [
            _link("can_other_body", "per_other", "confirmed"),
            _link("can_city", "per_other", "proposed"),
        ]
    )
    composition = pd.DataFrame(
        {
            "election_year": [2022],
            "member_name": ["Alex Ward"],
            "office": ["councillor"],
            "incumbent_source": ["city_attendance"],
            "confidence": [0.95],
            "roster_complete": [True],
        }
    )

    evidence = build_municipal_roster_evidence(
        candidacies,
        people,
        links,
        release_id="2026-08-20",
        composition=composition,
    )

    current = evidence.candidacy_person_links.query(
        "candidacy_id == 'can_city' and link_status == 'confirmed' and valid_to_release.isna()"
    )
    assert current["person_id"].nunique() == 1
    assert current["person_id"].item() != "per_other"


def test_roster_evidence_redirects_conflicting_bootstrap_singleton_person():
    candidacies = pd.DataFrame(
        [
            _candidate("can_old", "2018-10-22", "Ward Alex", "councillor", elected=True),
            _candidate("can_current", "2022-10-24", "Ward Alex", "councillor"),
        ]
    )
    people = pd.DataFrame(
        {
            "person_id": ["per_old", "per_current"],
            "preferred_name": ["Alex Ward", "Alex Ward"],
            "identity_status": ["active", "active"],
            "redirect_to_person_id": [pd.NA, pd.NA],
            "created_release": ["v2", "v2"],
        }
    )
    links = pd.DataFrame(
        [
            _link("can_old", "per_old", "confirmed"),
            _link("can_current", "per_current", "confirmed"),
        ]
    )
    composition = pd.DataFrame(
        {
            "election_year": [2022],
            "member_name": ["Alex Ward"],
            "office": ["councillor"],
            "incumbent_source": ["city_attendance"],
            "confidence": [0.95],
            "roster_complete": [True],
        }
    )

    evidence = build_municipal_roster_evidence(
        candidacies,
        people,
        links,
        release_id="2026-08-20",
        composition=composition,
    )

    current_person = evidence.people.set_index("person_id").loc["per_current"]
    assert current_person["identity_status"] == "deprecated"
    assert current_person["redirect_to_person_id"] == "per_old"
    active_current_link = evidence.candidacy_person_links.loc[
        evidence.candidacy_person_links["candidacy_id"].eq("can_current")
        & evidence.candidacy_person_links["valid_to_release"].isna()
        & evidence.candidacy_person_links["link_status"].eq("confirmed")
    ]
    assert active_current_link["person_id"].tolist() == ["per_old"]
    assert (
        active_current_link["method"].item() == "municipal_authoritative_roster_person_correction"
    )
    attached = attach_confirmed_people(
        candidacies, evidence.people, evidence.candidacy_person_links
    )
    assert attached.set_index("candidacy_id").loc["can_current", "person_id"] == "per_old"
    out = derive_incumbency(attached, evidence.rosters).set_index("candidacy_id")
    assert out.loc["can_current", "incumbent"]
    assert "municipal_roster_person_redirect" in set(evidence.review_flags["flag_type"])


@pytest.mark.skipif(
    not (COUNCIL_CACHE / "attendance").exists(),
    reason="requires the ignored local City Council attendance/voting cache",
)
def test_real_composition_reconciles_to_one_last_holder_per_council_office():
    reconciled = reconcile_composition_last_holders(
        build_composition(reference=COUNCIL_REFERENCE, raw=COUNCIL_CACHE)
    )

    assert reconciled.groupby("election_year").size().to_dict() == {
        2003: 45,
        2006: 45,
        2010: 45,
        2014: 45,
        2018: 45,
        2022: 26,
    }
    final_2022 = set(reconciled.query("election_year == 2022")["member_name"])
    assert {"Joe Mihevc", "Robin Buxton Potts", "Rose Milczyn"} <= final_2022
    assert not {"Joe Cressy", "Kristyn Wong-Tam", "Michael Ford"} & final_2022


def test_roster_arrival_method_is_preserved_in_office_tenure():
    candidacies = pd.DataFrame(
        [
            _candidate(
                "can_appointee",
                "2003-11-10",
                "Jones Laura",
                "councillor",
            )
        ]
    )
    people = pd.DataFrame(
        {
            "person_id": ["per_jones"],
            "preferred_name": ["Laura Jones"],
            "identity_status": ["active"],
            "redirect_to_person_id": [pd.NA],
            "created_release": ["v2"],
        }
    )
    links = pd.DataFrame([_link("can_appointee", "per_jones", "proposed")])
    composition = pd.DataFrame(
        {
            "election_year": [2003],
            "member_name": ["Laura Jones"],
            "office": ["councillor"],
            "incumbent_source": ["curated_roster"],
            "confidence": [0.95],
            "arrival": ["appointed"],
            "roster_complete": [True],
        }
    )

    evidence = build_municipal_roster_evidence(
        candidacies,
        people,
        links,
        release_id="2026-08-20",
        composition=composition,
    )

    assert evidence.office_tenures["entry_method"].tolist() == ["appointment"]


def test_mayoral_by_election_uses_last_certified_holder():
    candidacies = pd.DataFrame(
        [
            _candidate(
                "can_holder_2022",
                "2022-10-24",
                "Holder Jordan",
                "mayor",
                elected=True,
                district_id="dst_city",
            ),
            _candidate(
                "can_sitting_councillor_2022",
                "2022-10-24",
                "Councillor Sidney",
                "councillor",
                elected=True,
                district_id="dst_ward_9",
            ),
            _candidate(
                "can_challenger_2023",
                "2023-06-26",
                "Challenger Pat",
                "mayor",
                election_type="by_election",
                district_id="dst_city",
            ),
            _candidate(
                "can_sitting_councillor_2023",
                "2023-06-26",
                "Councillor Sidney",
                "mayor",
                election_type="by_election",
                district_id="dst_city",
            ),
        ]
    )
    people = pd.DataFrame(
        {
            "person_id": ["per_holder", "per_challenger", "per_councillor"],
            "preferred_name": ["Jordan Holder", "Pat Challenger", "Sidney Councillor"],
            "identity_status": ["active", "active", "active"],
            "redirect_to_person_id": [pd.NA, pd.NA, pd.NA],
            "created_release": ["v2", "v2", "v2"],
        }
    )
    links = pd.DataFrame(
        [
            _link("can_holder_2022", "per_holder", "confirmed"),
            _link("can_challenger_2023", "per_challenger", "confirmed"),
            _link("can_sitting_councillor_2022", "per_councillor", "confirmed"),
            _link("can_sitting_councillor_2023", "per_councillor", "proposed"),
        ]
    )

    evidence = build_municipal_roster_evidence(
        candidacies,
        people,
        links,
        release_id="2026-08-20",
        composition=pd.DataFrame(),
    )
    roster = evidence.rosters.query("event_id == 'evt_2023-06-26'")

    assert roster["person_id"].tolist() == ["per_holder"]
    assert roster["roster_complete"].all()
    assert roster["reference_date_rule"].tolist() == ["last_person_in_role_before_event"]
    attached = attach_confirmed_people(
        candidacies, evidence.people, evidence.candidacy_person_links
    )
    out = derive_incumbency(attached, evidence.rosters).set_index("candidacy_id")
    assert not out.loc["can_challenger_2023", "incumbent"]
    assert not out.loc["can_sitting_councillor_2023", "incumbent"]
    confirmed = evidence.candidacy_person_links.query(
        "candidacy_id == 'can_sitting_councillor_2023' and link_status == 'confirmed'"
    )
    assert confirmed["person_id"].tolist() == ["per_councillor"]


def test_councillor_by_election_known_holder_proves_true_but_absence_is_unknown():
    candidacies = pd.DataFrame(
        [
            _candidate("can_holder_2022", "2022-10-24", "Holder Jules", "councillor", elected=True),
            _candidate(
                "can_holder_2023",
                "2023-11-30",
                "Holder Jules",
                "councillor",
                election_type="by_election",
            ),
            _candidate(
                "can_new_2023",
                "2023-11-30",
                "New Taylor",
                "councillor",
                election_type="by_election",
            ),
        ]
    )
    people = pd.DataFrame(
        {
            "person_id": ["per_holder", "per_new"],
            "preferred_name": ["Jules Holder", "Taylor New"],
            "identity_status": ["active", "active"],
            "redirect_to_person_id": [pd.NA, pd.NA],
            "created_release": ["v2", "v2"],
        }
    )
    links = pd.DataFrame(
        [
            _link("can_holder_2022", "per_holder", "confirmed"),
            _link("can_holder_2023", "per_holder", "proposed"),
            _link("can_new_2023", "per_new", "confirmed"),
        ]
    )

    evidence = build_municipal_roster_evidence(
        candidacies,
        people,
        links,
        release_id="2026-08-20",
        composition=pd.DataFrame(),
    )
    roster = evidence.rosters.query("event_id == 'evt_2023-11-30'")

    assert not roster["roster_complete"].any()
    attached = attach_confirmed_people(
        candidacies, evidence.people, evidence.candidacy_person_links
    )
    out = derive_incumbency(attached, evidence.rosters).set_index("candidacy_id")
    assert out.loc["can_holder_2023", "incumbent"]
    assert pd.isna(out.loc["can_new_2023", "incumbent"])
