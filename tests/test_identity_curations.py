"""Explicit, evidence-backed corrections to the persistent Person registry."""

import json
from pathlib import Path

import pandas as pd

from toronto_election_results.identity import attach_confirmed_people
from toronto_election_results.identity_curations import (
    DEFAULT_IDENTITY_ASSERTIONS,
    CandidacyLocator,
    CuratedIdentityAssertion,
    apply_curated_identity_assertions,
    canonicalize_person_evidence,
)

REPO_ROOT = Path(__file__).parents[1]

PENDING_2026_EVENT_ID = "evt_27c3a2e636a457f1b1f922774525b74a"
PENDING_2026_PERSON_BY_CANDIDACY = {
    "can_adcacf84e3005896a5c773986a552c96": "per_bb140e42ff6750dc95adfa2785ffef68",
    "can_4e5688e335d85ba38dea71c20fc80f46": "per_bfeb35d94dc45455987133a9e9091a58",
    "can_f0eef9233b0c57268fe3d1a894b0dc36": "per_69529146105a5d85ae577db19104ceed",
    "can_d1f0d6ec825a5e8880c7a0127fb4c0cd": "per_f1f71e7ebd7157cda9b8d44c62c4c294",
    "can_49b595a977475ca1b7477b59834817c6": "per_4569490f5d825a0ca8c7320b499d8090",
    "can_2bd1031bade45386afb939f58e00bc7c": "per_2ca884fa7ffe5c61a4bd0afcbf153fed",
    "can_3d04d5bdb8ef5da8adb96314f7e9ccff": "per_9387d636b99c5fdd8edee8549f902b74",
    "can_0a3c62f981215bf2a20a08b3860f4f01": "per_4238a9a971965995ac6c577c126f8161",
    "can_43b902d7e35c5ba797370fa0395d6d7a": "per_93dd2a3cb85f59acb3d5ea5a67b3801e",
    "can_47bbbdf2085553daba34e5d65c24be5b": "per_cb9a349d2c375d6ca82d06405b9986e0",
    "can_9fdda0e71bd5578dab7a9bab4d7f5d4d": "per_a9f196f1be635c4eaf83ff095681fa79",
    "can_71d0b0ede70a5a45a0f3ca553a2c73b0": "per_d6e9f3947fda53a490136416df97c3cf",
    "can_4c18cca55e9d5f0a9574e97613157eee": "per_fb6a517ea8b55026b7d6afdf59820e53",
    "can_7e48ff22e1285e67b903e960711b588f": "per_b5382bf239c9521faee4a4a38f1a7e1c",
    "can_b575c3cad9c45924b9ab2fd40bf439bd": "per_c0e1c9bb6045570b873969e4c462da62",
    "can_a79a57064f7351fdb16759205a1efff7": "per_19dc2d74394f53058376f79485db68e8",
    "can_10ee922a6726559e8a6169740c7e274c": "per_4df1127545935df6850849e0b72a8759",
    "can_f368a3e52d0e545bbb6ebae997fb1bdf": "per_d476ff1e2e605a88914636edbdfcb79a",
    "can_0aee4bd40f7c5ca99c87bf0689ba951b": "per_3f72f66a6a385b0eae3279e7de8d12a0",
    "can_8164ef2b771950ebbe2913e7c4b5e8fd": "per_18786ecd2dc7506794ac10340a5f68f6",
    "can_3934cc2ba6395449b323ba47fdc50951": "per_f560221dfe455207a9cc597093a3b671",
    "can_06e9de5734dd5d97a4c2cde85a5ea016": "per_b3471e8be4765e51b0381303a6c7a36d",
    "can_b71a736235545b8f8df2a3e196126428": "per_d8dfddfb642358e299f4b428292666bf",
    "can_24054bba2bed56dab41293ec7d138d41": "per_a4291ca7539b53e2acc1c4f108bc73e6",
}
CHRIS_ALEXANDER_2026_CANDIDACY_ID = "can_b43d9b5795cf5aed9b587a956e49951b"


def test_default_pinned_candidacies_are_active_checked_ledger_entries():
    ledger = pd.read_csv(
        REPO_ROOT / "data" / "reference" / "candidacy_identity_ledger.csv",
        dtype="string",
    )
    active = ledger.loc[ledger["valid_to_release"].isna()].set_index("candidacy_id")
    pinned = [
        (assertion.assertion_id, occurrence)
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        for occurrence in assertion.occurrences
        if occurrence.candidacy_id is not None
    ]

    # These pins distinguish otherwise ambiguous same-name occurrences.  They must
    # be persistent ledger IDs, never IDs copied from a pre-ledger draft build.
    assert len(pinned) == 799
    assert len({occurrence.candidacy_id for _, occurrence in pinned}) == len(pinned)
    for assertion_id, occurrence in pinned:
        assert occurrence.candidacy_id in active.index, assertion_id
        row = active.loc[occurrence.candidacy_id]
        assert row["event_id"] == occurrence.event_id, assertion_id
        assert row["represented_body"] == occurrence.represented_body, assertion_id
        assert row["office_type"] == occurrence.office_type, assertion_id

    for assertion in DEFAULT_IDENTITY_ASSERTIONS:
        assert isinstance(assertion.evidence_urls, tuple), assertion.assertion_id
        assert assertion.evidence_urls, assertion.assertion_id
        assert all(url.startswith("https://") for url in assertion.evidence_urls)


def test_pending_2026_current_officeholder_assertions_are_exact_and_auditable():
    assertions = [
        assertion
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        if assertion.assertion_id.endswith("-2026-pending-continuity")
        or assertion.assertion_id.endswith("-2026-pending-mayor-continuity")
    ]

    assert len(assertions) == 24
    actual: dict[str, str] = {}
    for assertion in assertions:
        assert len(assertion.occurrences) == 1, assertion.assertion_id
        assert len(assertion.registry_person_ids) == 1, assertion.assertion_id
        assert assertion.canonical_person_id == assertion.registry_person_ids[0]
        occurrence = assertion.occurrences[0]
        candidacy_id = occurrence.candidacy_id
        assert candidacy_id is not None
        assert occurrence.event_id == PENDING_2026_EVENT_ID
        assert occurrence.represented_body == "toronto_city_council"
        assert occurrence.candidate_name == assertion.preferred_name
        assert assertion.evidence_urls[0] == (
            "https://www.toronto.ca/city-government/council/members-of-council/"
        )
        expected_feed = "https://www.toronto.ca/data/elections/candidate_list/" + (
            "mayorCandidates_2026.json"
            if occurrence.office_type == "mayor"
            else "councilorCandidates_2026.json"
        )
        assert assertion.evidence_urls[1] == expected_feed
        actual[candidacy_id] = assertion.registry_person_ids[0]

    assert actual == PENDING_2026_PERSON_BY_CANDIDACY
    assert CHRIS_ALEXANDER_2026_CANDIDACY_ID not in {
        occurrence.candidacy_id
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        for occurrence in assertion.occurrences
    }


def test_chloe_brown_cross_name_and_cross_office_identity_is_pinned_and_published():
    assertion = next(
        assertion
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        if assertion.assertion_id == "chloe-brown-2016-2026-toronto-candidacy-continuity"
    )
    candidacy_ids = {
        "can_c9c2e18dba7955429a08971f4d728751",
        "can_0a4ce7edba2e522ca838be9dddcdecee",
        "can_f3c0829c97525d048039948585926327",
        "can_e6be2215757451db85e79f587b054f77",
    }

    assert assertion.preferred_name == "Chloe Brown"
    assert assertion.canonical_person_id == "per_3d3501723d055766800769f77751b3bf"
    assert assertion.registry_person_ids == (
        "per_3d3501723d055766800769f77751b3bf",
        "per_abd4663f08cb5b11bbe72c502697a809",
    )
    assert {occurrence.candidacy_id for occurrence in assertion.occurrences} == candidacy_ids

    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    assert set(results.loc[list(candidacy_ids), "person_id"]) == {
        "per_3d3501723d055766800769f77751b3bf"
    }
    assert results.loc["can_c9c2e18dba7955429a08971f4d728751", "candidate_name"] == (
        "Chloe-Marie Brown"
    )
    assert results.loc["can_0a4ce7edba2e522ca838be9dddcdecee", "candidate_name"] == (
        "Chloe-Marie Brown"
    )
    assert results.loc["can_f3c0829c97525d048039948585926327", "candidate_name"] == ("Chloe Brown")
    assert results.loc["can_e6be2215757451db85e79f587b054f77", "candidate_name"] == ("Chloe Brown")

    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    assert people.loc["per_3d3501723d055766800769f77751b3bf", "preferred_name"] == ("Chloe Brown")
    assert people.loc["per_abd4663f08cb5b11bbe72c502697a809", "identity_status"] == ("deprecated")
    assert (
        people.loc["per_abd4663f08cb5b11bbe72c502697a809", "redirect_to_person_id"]
        == "per_3d3501723d055766800769f77751b3bf"
    )


def test_edward_gong_cross_name_and_cross_office_identity_is_pinned_and_published():
    assertion = next(
        assertion
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        if assertion.assertion_id == "edward-xiao-hua-gong-2023-2026-candidacy-continuity"
    )
    candidacy_ids = {
        "can_0c4d2f02396353048ccf398e170ccb59",
        "can_69f3b5c5b1f85d6db7db3003822c06a7",
        "can_52f3f65dbd5a5867b98898a8500161d5",
    }

    assert assertion.preferred_name == "Edward Gong"
    assert assertion.canonical_person_id == "per_424fd6af33ed5e0bae4177a42cde6c21"
    assert assertion.registry_person_ids == (
        "per_424fd6af33ed5e0bae4177a42cde6c21",
        "per_5067314c5e465bfb95ca0798e4854ea7",
        "per_c54d3412c98b57bbabd296e5fbb4dceb",
    )
    assert {occurrence.candidacy_id for occurrence in assertion.occurrences} == candidacy_ids

    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    assert set(results.loc[list(candidacy_ids), "person_id"]) == {
        "per_424fd6af33ed5e0bae4177a42cde6c21"
    }
    assert results.loc["can_0c4d2f02396353048ccf398e170ccb59", "candidate_name"] == (
        "Xiao Hua Gong"
    )
    assert results.loc["can_69f3b5c5b1f85d6db7db3003822c06a7", "candidate_name"] == ("Xiaohua Gong")
    assert results.loc["can_52f3f65dbd5a5867b98898a8500161d5", "candidate_name"] == ("Edward Gong")

    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    assert people.loc["per_424fd6af33ed5e0bae4177a42cde6c21", "preferred_name"] == ("Edward Gong")
    for duplicate_person_id in (
        "per_5067314c5e465bfb95ca0798e4854ea7",
        "per_c54d3412c98b57bbabd296e5fbb4dceb",
    ):
        assert people.loc[duplicate_person_id, "identity_status"] == "deprecated"
        assert (
            people.loc[duplicate_person_id, "redirect_to_person_id"]
            == "per_424fd6af33ed5e0bae4177a42cde6c21"
        )


def test_explicit_canonical_person_restores_a_published_registry_anchor():
    candidacies = pd.DataFrame(
        [
            {
                "candidacy_id": "can_pending",
                "event_id": "evt_pending",
                "represented_body": "toronto_city_council",
                "office_type": "councillor",
                "candidate_name": "One Candidate",
                "source_detail": "https://official.example/candidates",
            }
        ]
    )
    people = pd.DataFrame(
        [
            {
                "person_id": "per_published",
                "preferred_name": "One Candidate",
                "identity_status": "deprecated",
                "redirect_to_person_id": "per_new_occurrence",
                "created_release": "v1",
            },
            {
                "person_id": "per_new_occurrence",
                "preferred_name": "One Candidate",
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": "v2",
            },
        ]
    )
    links = pd.DataFrame(
        [
            {
                "candidacy_id": "can_pending",
                "person_id": "per_new_occurrence",
                "link_status": "confirmed",
                "method": "official_candidacy_record",
                "evidence": "official",
                "reviewer": "bootstrap",
                "valid_from_release": "v2",
                "valid_to_release": pd.NA,
            }
        ]
    )
    assertion = CuratedIdentityAssertion(
        assertion_id="preserve-published-person",
        preferred_name="One Candidate",
        occurrences=(
            CandidacyLocator(
                "evt_pending",
                "toronto_city_council",
                "councillor",
                "One Candidate",
                candidacy_id="can_pending",
            ),
        ),
        evidence_urls=("https://official.example/identity",),
        rationale="The official source connects the pending occurrence to the published Person.",
        registry_person_ids=("per_published",),
        canonical_person_id="per_published",
    )

    curated = apply_curated_identity_assertions(
        candidacies, people, links, "v2", assertions=(assertion,)
    )
    people_out = curated.people.set_index("person_id")
    assert people_out.loc["per_published", "identity_status"] == "active"
    assert pd.isna(people_out.loc["per_published", "redirect_to_person_id"])
    assert people_out.loc["per_new_occurrence", "identity_status"] == "deprecated"
    assert people_out.loc["per_new_occurrence", "redirect_to_person_id"] == "per_published"
    active = curated.candidacy_person_links.loc[
        curated.candidacy_person_links["valid_to_release"].isna()
    ]
    assert active.loc[active["candidacy_id"].eq("can_pending"), "person_id"].item() == (
        "per_published"
    )


def test_pending_2026_curations_leave_chris_alexander_identity_untouched():
    assertions = tuple(
        assertion
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        if any(occurrence.event_id == PENDING_2026_EVENT_ID for occurrence in assertion.occurrences)
    )
    candidacies = pd.DataFrame(
        [
            {
                "candidacy_id": occurrence.candidacy_id,
                "event_id": occurrence.event_id,
                "represented_body": occurrence.represented_body,
                "office_type": occurrence.office_type,
                "candidate_name": occurrence.candidate_name,
                "source_detail": assertion.evidence_urls[1],
            }
            for assertion in assertions
            for occurrence in assertion.occurrences
        ]
        + [
            {
                "candidacy_id": CHRIS_ALEXANDER_2026_CANDIDACY_ID,
                "event_id": PENDING_2026_EVENT_ID,
                "represented_body": "toronto_city_council",
                "office_type": "mayor",
                "candidate_name": "Chris Alexander",
                "source_detail": (
                    "https://www.toronto.ca/data/elections/candidate_list/mayorCandidates_2026.json"
                ),
            }
        ]
    )
    people = pd.DataFrame(
        [
            {
                "person_id": registry_person_id,
                "preferred_name": assertion.preferred_name,
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": "2026-08-20",
            }
            for assertion in assertions
            for registry_person_id in assertion.registry_person_ids
        ]
        + [
            {
                "person_id": "per_chris_alexander_new",
                "preferred_name": "Chris Alexander",
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": "2026-08-21",
            },
            {
                "person_id": "per_alexander_brown_existing",
                "preferred_name": "Alexander Brown",
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": "2026-08-20",
            },
            {
                "person_id": "per_michael_alexander_existing",
                "preferred_name": "Michael Alexander",
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": "2026-08-20",
            },
        ]
    )
    links = pd.DataFrame(
        [
            {
                "candidacy_id": CHRIS_ALEXANDER_2026_CANDIDACY_ID,
                "person_id": "per_chris_alexander_new",
                "link_status": "confirmed",
                "method": "unique_official_candidacy",
                "evidence": "official 2026 candidate feed",
                "reviewer": "identity_review.bootstrap/v1",
                "valid_from_release": "2026-08-21",
                "valid_to_release": pd.NA,
            }
        ]
    )

    curated = apply_curated_identity_assertions(
        candidacies,
        people,
        links,
        "2026-08-21",
        assertions=assertions,
    )
    active_links = curated.candidacy_person_links.loc[
        curated.candidacy_person_links["valid_to_release"].isna()
        & curated.candidacy_person_links["link_status"].eq("confirmed")
    ].set_index("candidacy_id")

    assert active_links.loc[CHRIS_ALEXANDER_2026_CANDIDACY_ID, "person_id"] == (
        "per_chris_alexander_new"
    )
    for candidacy_id, person_id in PENDING_2026_PERSON_BY_CANDIDACY.items():
        assert active_links.loc[candidacy_id, "person_id"] == person_id
    alexanders = curated.people.set_index("person_id").loc[
        [
            "per_chris_alexander_new",
            "per_alexander_brown_existing",
            "per_michael_alexander_existing",
        ]
    ]
    assert alexanders["identity_status"].tolist() == ["active", "active", "active"]
    assert alexanders["redirect_to_person_id"].isna().all()


def test_exact_scope_identity_wave_matches_public_artifacts_after_rebuild():
    assertions = {
        assertion.assertion_id: assertion
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        if assertion.assertion_id.endswith("-exact-scope")
    }
    assert len(assertions) == 173
    assert sum(len(assertion.occurrences) for assertion in assertions.values()) == 179

    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    active_confirmed = links.loc[
        links["valid_to_release"].isna() & links["link_status"].eq("confirmed")
    ]

    for assertion_id, assertion in assertions.items():
        assert len(assertion.registry_person_ids) == 1, assertion_id
        person_id = assertion.registry_person_ids[0]
        assert person_id in people.index, assertion_id
        assert people.loc[person_id, "preferred_name"] == assertion.preferred_name, assertion_id
        for occurrence in assertion.occurrences:
            candidacy_id = occurrence.candidacy_id
            assert candidacy_id is not None
            assert results.loc[candidacy_id, "person_id"] == person_id, assertion_id
            active = active_confirmed.loc[active_confirmed["candidacy_id"].eq(candidacy_id)]
            assert active["person_id"].tolist() == [person_id], assertion_id


def test_published_release_applies_first_evidence_review_wave():
    assertion_ids = {
        "adrian-heaps-council-continuity",
        "ann-andrachuk-tcdsb-continuity",
        "barbara-poplawski-tcdsb-ward10-continuity",
        "cathy-dandy-tdsb-continuity",
        "chris-bolton-tdsb-continuity",
        "chris-tonks-tdsb-continuity",
        "david-smith-tdsb-to-ontario-continuity",
        "garry-tanuan-tcdsb-continuity",
        "gerri-gershon-tdsb-continuity",
        "howard-goodman-tdsb-continuity",
        "irene-atkinson-tdsb-continuity",
        "joseph-martino-tcdsb-continuity",
        "maria-rizzo-tcdsb-continuity",
        "maria-rodrigues-tdsb-continuity",
        "mari-rutka-tdsb-continuity",
        "nancy-crawford-tcdsb-continuity",
        "sal-piccininni-tcdsb-continuity",
        "scott-harrison-tdsb-2003-2010-continuity",
        "sheila-cary-meagher-tdsb-continuity",
        "sheila-ward-tdsb-continuity",
        "shelley-laskin-tdsb-continuity",
        "soo-wong-tdsb-and-ontario-continuity",
        "stephnie-payne-tdsb-continuity",
    }
    assertions = {
        assertion.assertion_id: assertion
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        if assertion.assertion_id in assertion_ids
    }
    assert set(assertions) == assertion_ids

    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    active_confirmed = links.loc[
        links["valid_to_release"].isna() & links["link_status"].eq("confirmed")
    ]

    for assertion in assertions.values():
        assert len(assertion.registry_person_ids) == 1
        person_id = assertion.registry_person_ids[0]
        for occurrence in assertion.occurrences:
            candidacy_id = occurrence.candidacy_id
            assert candidacy_id is not None
            assert results.loc[candidacy_id, "person_id"] == person_id
            active = active_confirmed.loc[active_confirmed["candidacy_id"].eq(candidacy_id)]
            assert active[["candidacy_id", "person_id"]].to_dict("records") == [
                {"candidacy_id": candidacy_id, "person_id": person_id}
            ]


def test_published_release_applies_second_evidence_review_wave():
    assertion_ids = {
        "borys-wrzesnewskyj-house-continuity",
        "bruce-davis-tdsb-continuity",
        "chloe-robert-viamonde-continuity",
        "christine-nunziata-tcdsb-continuity",
        "dan-maclean-tdsb-continuity",
        "daniel-di-giorgio-tcdsb-to-ontario-continuity",
        "howard-kaplan-tdsb-continuity",
        "james-li-tdsb-continuity",
        "jennifer-story-tdsb-continuity",
        "jerry-chadwick-tdsb-continuity",
        "john-hastings-tdsb-2006-2014-continuity",
        "julien-baeta-viamonde-2014-2018-continuity",
        "karim-bardeesy-ontario-to-house-continuity",
        "lee-fairclough-ontario-continuity",
        "markus-de-domenico-tcdsb-continuity",
        "mary-cicogna-tcdsb-continuity",
        "michael-feldman-council-continuity",
        "michelle-aarts-tdsb-continuity",
        "oliver-carroll-tcdsb-continuity",
        "pamela-gough-tdsb-continuity",
        "patrick-nunziata-tdsb-continuity",
        "patrizia-bottoni-tcdsb-continuity",
        "paul-crawford-tcdsb-continuity",
        "preti-ida-li-tcdsb-continuity",
        "robin-pilkey-tdsb-continuity",
        "roman-baber-ontario-to-house-continuity",
        "teresa-lubinski-tcdsb-continuity",
        "vince-gasparro-ontario-to-house-continuity",
        "yalini-rajakulasingam-tdsb-continuity",
        "zakir-patel-tdsb-continuity",
    }
    assertions = {
        assertion.assertion_id: assertion
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        if assertion.assertion_id in assertion_ids
    }
    assert set(assertions) == assertion_ids

    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    active_confirmed = links.loc[
        links["valid_to_release"].isna() & links["link_status"].eq("confirmed")
    ]

    for assertion in assertions.values():
        candidacy_ids = [occurrence.candidacy_id for occurrence in assertion.occurrences]
        assert all(candidacy_id is not None for candidacy_id in candidacy_ids)
        person_ids = results.loc[candidacy_ids, "person_id"].dropna().unique().tolist()
        assert len(person_ids) == 1
        person_id = person_ids[0]
        if assertion.registry_person_ids:
            assert assertion.registry_person_ids == (person_id,)
        for candidacy_id in candidacy_ids:
            active = active_confirmed.loc[active_confirmed["candidacy_id"].eq(candidacy_id)]
            assert active[["candidacy_id", "person_id"]].to_dict("records") == [
                {"candidacy_id": candidacy_id, "person_id": person_id}
            ]


def test_published_release_applies_elected_and_collision_review_wave():
    assertion_ids = {
        "alexander-brown-tdsb-ward12-continuity",
        "alexandra-lulka-rotman-tdsb-continuity",
        "angela-kennedy-tcdsb-and-ontario-continuity",
        "anu-sriskandarajah-tdsb-continuity",
        "avtar-minhas-council-to-tdsb-continuity",
        "chi-nguyen-ontario-to-house-continuity",
        "frank-damico-tcdsb-2010-2022-continuity",
        "jean-francois-lheureux-viamonde-continuity",
        "jo-ann-davis-tcdsb-continuity",
        "john-del-grande-tcdsb-continuity",
        "ken-lister-tdsb-continuity",
        "kevin-morrison-tcdsb-ward11-to-ward9-continuity",
        "leslie-church-house-2024-2025-continuity",
        "manna-wong-tdsb-continuity",
        "matias-de-dovitiis-tdsb-continuity",
        "sam-sotiropoulos-tdsb-ward20-continuity",
    }
    assertions = {
        assertion.assertion_id: assertion
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        if assertion.assertion_id in assertion_ids
    }
    assert set(assertions) == assertion_ids

    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    active_confirmed = links.loc[
        links["valid_to_release"].isna() & links["link_status"].eq("confirmed")
    ]

    canonical_by_assertion: dict[str, str] = {}
    for assertion_id, assertion in assertions.items():
        candidacy_ids = [occurrence.candidacy_id for occurrence in assertion.occurrences]
        assert all(candidacy_id is not None for candidacy_id in candidacy_ids)
        person_ids = results.loc[candidacy_ids, "person_id"].dropna().unique().tolist()
        assert len(person_ids) == 1, assertion_id
        person_id = person_ids[0]
        canonical_by_assertion[assertion_id] = person_id
        if assertion.registry_person_ids:
            assert assertion.registry_person_ids[0] == person_id
        for candidacy_id in candidacy_ids:
            active = active_confirmed.loc[active_confirmed["candidacy_id"].eq(candidacy_id)]
            assert active[["candidacy_id", "person_id"]].to_dict("records") == [
                {"candidacy_id": candidacy_id, "person_id": person_id}
            ]

    deprecated_lulka = people.loc["per_8d7b15e532d653528a8ec8cededad6fe"]
    assert deprecated_lulka["identity_status"] == "deprecated"
    assert deprecated_lulka["redirect_to_person_id"] == "per_41f18773bdf258f1b2bda351d34274e3"

    excluded_collisions = {
        "can_bdebbc1bc209571bb822180ba1c83abe": ("angela-kennedy-tcdsb-and-ontario-continuity"),
        "can_db651bb0672758849cf4f97fb3576823": ("frank-damico-tcdsb-2010-2022-continuity"),
        "can_27eeec08461051ba9207daf09935b243": ("kevin-morrison-tcdsb-ward11-to-ward9-continuity"),
        "can_ef847ab8da2f566c94ec44c581418c22": ("sam-sotiropoulos-tdsb-ward20-continuity"),
        "can_c337f53956485bffbea1f08812a3ca14": ("alexander-brown-tdsb-ward12-continuity"),
    }
    for candidacy_id, assertion_id in excluded_collisions.items():
        collision_person_id = results.loc[candidacy_id, "person_id"]
        assert pd.isna(collision_person_id) or (
            collision_person_id != canonical_by_assertion[assertion_id]
        )


def test_published_release_applies_repeat_identity_review_wave():
    assertion_ids = {
        "ahmad-tahir-tdsb-continuity",
        "alan-burke-council-continuity",
        "alejandra-bravo-council-continuity",
        "angela-salewsky-ontario-continuity",
        "anna-di-carlo-house-continuity",
        "annamie-paul-house-continuity",
        "christine-nugent-house-continuity",
        "dan-harris-house-continuity",
        "dave-mckee-ontario-continuity",
        "diana-hall-council-continuity",
        "george-szebik-house-continuity",
        "gerald-derome-mayoral-continuity",
        "jack-weenen-mayoral-continuity",
        "jaime-castillo-mayoral-continuity",
        "jimmy-talpa-council-continuity",
        "joe-renda-council-continuity",
        "john-carmichael-house-continuity",
        "john-kittredge-ontario-continuity",
        "john-letonja-adjudicated-council-and-mayor-continuity",
        "john-vassal-tdsb-continuity",
        "julian-heller-ontario-continuity",
        "kevin-clarke-adjudicated-mayor-and-house-continuity",
        "king-kim-tdsb-continuity",
        "kris-langenfeld-mayoral-continuity",
        "larry-perlman-council-continuity",
        "liz-white-house-continuity",
        "lorne-gershuny-house-continuity",
        "marcell-rodden-house-continuity",
        "mariangela-sanabria-ontario-continuity",
        "mazhar-shafiq-ontario-continuity",
        "mohammed-mirza-council-continuity",
        "monowar-hossain-mayoral-continuity",
        "nha-le-council-continuity",
        "nick-dominelli-council-continuity",
        "noah-ng-tdsb-continuity",
        "paul-ferreira-ontario-continuity",
        "ram-maharaj-tdsb-continuity",
        "ratan-wadhwa-mayoral-continuity",
        "renee-dionne-mayoral-continuity",
        "roger-carter-house-continuity",
        "roland-lin-council-continuity",
        "roxanne-james-house-continuity",
        "ryan-kidd-ontario-continuity",
        "terry-parker-house-continuity",
        "wayne-simmons-ontario-continuity",
    }
    assertions = {
        assertion.assertion_id: assertion
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        if assertion.assertion_id in assertion_ids
    }
    assert set(assertions) == assertion_ids
    assert sum(len(assertion.occurrences) for assertion in assertions.values()) == 124

    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    active_confirmed = links.loc[
        links["valid_to_release"].isna() & links["link_status"].eq("confirmed")
    ]

    for assertion_id, assertion in assertions.items():
        assert len(assertion.registry_person_ids) == 1, assertion_id
        person_id = assertion.registry_person_ids[0]
        for occurrence in assertion.occurrences:
            candidacy_id = occurrence.candidacy_id
            assert candidacy_id is not None
            assert results.loc[candidacy_id, "person_id"] == person_id, assertion_id
            active = active_confirmed.loc[active_confirmed["candidacy_id"].eq(candidacy_id)]
            assert active[["candidacy_id", "person_id"]].to_dict("records") == [
                {"candidacy_id": candidacy_id, "person_id": person_id}
            ]


def test_published_release_resolves_downstream_mayoral_identity_complaint():
    expected = {
        "can_3d13fbd9fab452a5b347fb048574b6c4": (
            "per_58016e26ffa55f6bbdc8f7490273a4a5",
            "289832",
            "0.35606596689861225",
        ),
        "can_9c393c7edd9a51abbf0033c980bdad32": (
            "per_58016e26ffa55f6bbdc8f7490273a4a5",
            "4734",
            "0.15149284777112867",
        ),
        "can_b0b70cf1154d5e858ffac38014484f05": (
            "per_6df1a502d1b450369a2cc47794639812",
            "62167",
            "0.08579042225221421",
        ),
        "can_730259967f36585598760e9f9f4b4cd8": (
            "per_3ec4e3ff861d57519f52e15b4a9449a7",
            "1105",
            "0.0015248993290442952",
        ),
        "can_95f6966eeeaf570994a1f923be18a673": (
            "per_79d654cb934c519998b37e8bfc06f367",
            "6729",
            "0.01219264708546993",
        ),
        "can_e29a2b37b9395de1bcb1af5ea59e9dcf": (
            "per_79d654cb934c519998b37e8bfc06f367",
            "195",
            "0.0002690998815960521",
        ),
        "can_c334cb1e92d255c6a441a8867418a9b4": (
            "per_79d654cb934c519998b37e8bfc06f367",
            "4042",
            "0.06755356486278705",
        ),
        "can_614e274e63b4587b90300c8c0e66cae3": (
            "per_830dd3152c6253f7b9bf701d1527612e",
            "264",
            "0.00036431983969927056",
        ),
        "can_eef751b2c751567ca5e2fef90195b6d1": (
            "per_2a0809ffec18563292e0e1363aff66f6",
            "5399",
            "0.3269149258250076",
        ),
        "can_75c8eb6bbeef5bedb5a843a5e5fbf76e": (
            "per_2a0809ffec18563292e0e1363aff66f6",
            "1988",
            "0.1499132795415127",
        ),
        "can_ed44c908817556eea92c054dd42725eb": (
            "per_2a0809ffec18563292e0e1363aff66f6",
            "378",
            "0.0005216397704785009",
        ),
    }
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    active_confirmed = links.loc[
        links["valid_to_release"].isna() & links["link_status"].eq("confirmed")
    ]
    pinned_ids = {
        occurrence.candidacy_id
        for assertion in DEFAULT_IDENTITY_ASSERTIONS
        for occurrence in assertion.occurrences
        if occurrence.candidacy_id is not None
    }

    for candidacy_id, (person_id, votes, vote_share) in expected.items():
        row = results.loc[candidacy_id]
        assert row["person_id"] == person_id
        assert row["votes"] == votes
        assert row["vote_share"] == vote_share
        assert row["elected"] == "False"
        active = active_confirmed.loc[active_confirmed["candidacy_id"].eq(candidacy_id)]
        assert active[["candidacy_id", "person_id"]].to_dict("records") == [
            {"candidacy_id": candidacy_id, "person_id": person_id}
        ]
        person = people.loc[person_id]
        assert person["identity_status"] == "active"
        assert pd.isna(person["redirect_to_person_id"])
        assert candidacy_id in pinned_ids


def test_curated_assertion_redirects_visible_history_without_blanket_name_merge():
    candidacies = pd.DataFrame(
        [
            {
                "candidacy_id": "can_city",
                "event_id": "evt_city",
                "represented_body": "toronto_city_council",
                "office_type": "councillor",
                "candidate_name": "Doug Ford",
                "district_id": "ward-2",
                "source_detail": "https://www.toronto.ca/city-result",
            },
            {
                "candidacy_id": "can_ontario",
                "event_id": "evt_ontario",
                "represented_body": "ontario_legislative_assembly",
                "office_type": "mpp",
                "candidate_name": "DOUG FORD",
                "district_id": "ed-etobicoke-north",
                "source_detail": "https://results.elections.on.ca/result",
            },
            {
                "candidacy_id": "can_same_name_unasserted",
                "event_id": "evt_elsewhere",
                "represented_body": "another_body",
                "office_type": "mpp",
                "candidate_name": "Doug Ford",
                "district_id": "ed-elsewhere",
                "source_detail": "https://example.test/official-result",
            },
        ]
    )
    people = pd.DataFrame(
        [
            {
                "person_id": "per_city",
                "preferred_name": "Doug Ford",
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": "v1",
            },
            {
                "person_id": "per_ontario",
                "preferred_name": "Doug Ford",
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": "v1",
            },
            {
                "person_id": "per_unasserted",
                "preferred_name": "Doug Ford",
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": "v1",
            },
            {
                "person_id": "per_roster_created",
                "preferred_name": "Doug Ford",
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": "v1",
            },
        ]
    )
    links = pd.DataFrame(
        [
            {
                "candidacy_id": candidacy_id,
                "person_id": person_id,
                "link_status": "confirmed",
                "method": "official_result_continuity",
                "evidence": "old evidence",
                "reviewer": "bootstrap",
                "valid_from_release": "v1",
                "valid_to_release": pd.NA,
            }
            for candidacy_id, person_id in [
                ("can_city", "per_city"),
                ("can_ontario", "per_ontario"),
                ("can_same_name_unasserted", "per_unasserted"),
            ]
        ]
    )
    assertion = CuratedIdentityAssertion(
        assertion_id="doug-ford-official-cross-office",
        preferred_name="Doug Ford",
        occurrences=(
            CandidacyLocator("evt_city", "toronto_city_council", "councillor", "Doug Ford"),
            CandidacyLocator(
                "evt_ontario",
                "ontario_legislative_assembly",
                "mpp",
                "Doug Ford",
            ),
        ),
        evidence_urls=("https://www.ola.org/official-biography",),
        rationale="The official Legislature source identifies the MPP as the former councillor.",
        registry_person_ids=("per_roster_created",),
    )

    curated = apply_curated_identity_assertions(
        candidacies, people, links, "v2", assertions=(assertion,)
    )

    canonical = curated.assertions.iloc[0]["canonical_person_id"]
    assert canonical == "per_city"
    redirected = curated.people.set_index("person_id").loc["per_ontario"]
    assert redirected["identity_status"] == "deprecated"
    assert redirected["redirect_to_person_id"] == canonical
    roster_created = curated.people.set_index("person_id").loc["per_roster_created"]
    assert roster_created["identity_status"] == "deprecated"
    assert roster_created["redirect_to_person_id"] == canonical

    old_ontario = curated.candidacy_person_links.query(
        "candidacy_id == 'can_ontario' and person_id == 'per_ontario'"
    )
    assert old_ontario["valid_to_release"].item() == "v2"
    attached = attach_confirmed_people(
        candidacies, curated.people, curated.candidacy_person_links
    ).set_index("candidacy_id")
    assert attached.loc["can_city", "person_id"] == canonical
    assert attached.loc["can_ontario", "person_id"] == canonical
    assert attached.loc["can_same_name_unasserted", "person_id"] == "per_unasserted"

    evidence = json.loads(attached.loc["can_ontario", "person_link_evidence"])
    assert evidence["assertion_id"] == assertion.assertion_id
    assert evidence["official_evidence_urls"] == list(assertion.evidence_urls)

    office_tenures = pd.DataFrame(
        {
            "office_tenure_id": ["ten_roster"],
            "person_id": ["per_roster_created"],
        }
    )
    rosters = pd.DataFrame(
        {
            "event_id": ["evt_city"],
            "represented_body": ["toronto_city_council"],
            "office_type": ["councillor"],
            "person_id": ["per_roster_created"],
            "office_tenure_id": ["ten_roster"],
        }
    )
    canonical_evidence = canonicalize_person_evidence(curated.people, office_tenures, rosters)
    assert canonical_evidence.office_tenures["person_id"].item() == canonical
    assert canonical_evidence.rosters["person_id"].item() == canonical


def test_curated_assertion_fails_when_a_locator_is_ambiguous():
    candidacies = pd.DataFrame(
        [
            {
                "candidacy_id": candidacy_id,
                "event_id": "evt",
                "represented_body": "body",
                "office_type": "mp",
                "candidate_name": "Same Name",
                "district_id": district,
                "source_detail": "official",
            }
            for candidacy_id, district in [("can_a", "a"), ("can_b", "b")]
        ]
        + [
            {
                "candidacy_id": "can_prior",
                "event_id": "evt_prior",
                "represented_body": "body",
                "office_type": "mp",
                "candidate_name": "Same Name",
                "district_id": "prior",
                "source_detail": "official",
            }
        ]
    )
    assertion = CuratedIdentityAssertion(
        assertion_id="ambiguous",
        preferred_name="Same Name",
        occurrences=(
            CandidacyLocator("evt", "body", "mp", "Same Name"),
            CandidacyLocator("evt_prior", "body", "mp", "Same Name"),
        ),
        evidence_urls=("https://official.example/evidence",),
        rationale="Official evidence.",
    )
    people = pd.DataFrame(
        columns=[
            "person_id",
            "preferred_name",
            "identity_status",
            "redirect_to_person_id",
            "created_release",
        ]
    )
    links = pd.DataFrame(
        columns=[
            "candidacy_id",
            "person_id",
            "link_status",
            "method",
            "evidence",
            "reviewer",
            "valid_from_release",
            "valid_to_release",
        ]
    )

    try:
        apply_curated_identity_assertions(candidacies, people, links, "v2", assertions=(assertion,))
    except ValueError as error:
        assert "matched 2 candidacies" in str(error)
    else:
        raise AssertionError("ambiguous curation locator should fail closed")


def test_curated_assertion_is_idempotent_when_reusing_the_prior_registry():
    candidacies = pd.DataFrame(
        [
            {
                "candidacy_id": f"can_{event}",
                "event_id": event,
                "represented_body": "body",
                "office_type": "mp",
                "candidate_name": "One Person",
                "district_id": event,
                "source_detail": f"https://official.example/{event}",
            }
            for event in ("old", "new")
        ]
    )
    people = pd.DataFrame(
        columns=[
            "person_id",
            "preferred_name",
            "identity_status",
            "redirect_to_person_id",
            "created_release",
        ]
    )
    links = pd.DataFrame(
        columns=[
            "candidacy_id",
            "person_id",
            "link_status",
            "method",
            "evidence",
            "reviewer",
            "valid_from_release",
            "valid_to_release",
        ]
    )
    assertion = CuratedIdentityAssertion(
        assertion_id="one-person",
        preferred_name="One Person",
        occurrences=tuple(
            CandidacyLocator(event, "body", "mp", "One Person") for event in ("old", "new")
        ),
        evidence_urls=("https://official.example/identity",),
        rationale="Official record enumerates both occurrences.",
    )

    first = apply_curated_identity_assertions(
        candidacies, people, links, "v2", assertions=(assertion,)
    )
    second = apply_curated_identity_assertions(
        candidacies,
        first.people,
        first.candidacy_person_links,
        "v2",
        assertions=(assertion,),
    )

    pd.testing.assert_frame_equal(second.people, first.people)
    pd.testing.assert_frame_equal(second.candidacy_person_links, first.candidacy_person_links)
