"""Published review states for adjudicated Candidacy-Person proposals."""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.identity import attach_confirmed_people
from toronto_election_results.identity_dispositions import (
    apply_identity_review_decisions,
    read_identity_review_decisions,
)
from toronto_election_results.mayoral_career import exclude_superseded_identity_decisions

REPO_ROOT = Path(__file__).parents[1]

COUNCIL_BATCH_2_EXPECTED = {
    "can_e93f5ad6bae3581da052d5f6634f7c41": (
        "per_7b66a05627cf557db879bb07990a8aa6",
        "521",
        "0.012459941646338547",
    ),
    "can_e5b5388c503753a1a4ff9636316c72a1": (
        "per_7b66a05627cf557db879bb07990a8aa6",
        "298",
        "0.011006870059836004",
    ),
    "can_ff720c09d20c55ad85d5d9d941fb7b12": (
        "per_7b66a05627cf557db879bb07990a8aa6",
        "254",
        "0.012277648878576953",
    ),
    "can_faf4051924815062b3907d7d5aa59010": (
        "per_7b66a05627cf557db879bb07990a8aa6",
        "23",
        "0.0019027134348113832",
    ),
    "can_85a1b9a890cb57f0aa88d996133cb45f": (
        "per_7b66a05627cf557db879bb07990a8aa6",
        "677",
        "0.0402233973025964",
    ),
    "can_0825ef06a4b555b4bb30a2f7e9e4d184": (
        "per_7b66a05627cf557db879bb07990a8aa6",
        "27",
        "0.001592920353982301",
    ),
    "can_cb1965935fbb5c708a8c28e8f138282f": (
        "per_16a4d886ecfe59668937ad0291a82e3d",
        "17",
        "0.0014063534083388484",
    ),
    "can_d13a0869b0075217869233373f77fb51": (
        "per_16a4d886ecfe59668937ad0291a82e3d",
        "5",
        "0.00021226915729144556",
    ),
    "can_446014dfa14f56e7a4a75af7ab098dc9": (
        "per_fb1330040a9f58b2a6e7de8bae16bf3e",
        "35",
        "0.0018172377985462098",
    ),
    "can_dcfe9a4846675145871f9087c3a5c005": (
        "per_a89824be70535923ae6dbc585cff3fc0",
        "1633",
        "0.03672716640802465",
    ),
    "can_2e95d69c77ed5130998c182d591c6c8a": (
        "per_a89824be70535923ae6dbc585cff3fc0",
        "872",
        "0.022608244749805547",
    ),
    "can_fba4d12130e3580dab26f538a5669f12": (
        "per_a89824be70535923ae6dbc585cff3fc0",
        "1784",
        "0.05108673863864151",
    ),
    "can_9a0249cc1c4053b280b20e9d5fa703ad": (
        "per_a89824be70535923ae6dbc585cff3fc0",
        "3940",
        "0.1826780415430267",
    ),
    "can_c5c8fe730b8b567ea1a64839b752db62": (
        "per_4fb75ca0f2ba54879735652aa701181a",
        "616",
        "0.010500477294422474",
    ),
    "can_a2f7cfe910b15022984c8ecd48d5bf69": (
        "per_4fb75ca0f2ba54879735652aa701181a",
        "2780",
        "0.12782196882615293",
    ),
    "can_85f12ca63c63581ebf80d9710560d3c5": (
        "per_4fb75ca0f2ba54879735652aa701181a",
        "575",
        "0.02441095308851624",
    ),
    "can_a1b147c5edd45d65a8b495e830bf5c81": (
        "per_ace9396f014150ff94149657a1e256ab",
        "8673",
        "0.15726771596431421",
    ),
    "can_8ca2fe3ee27555b0ad486f10f4645d0d": (
        "per_ace9396f014150ff94149657a1e256ab",
        "12098",
        "0.29845812261009",
    ),
    "can_146bb6a90bec54569862f99cbb327e46": (
        "per_ace9396f014150ff94149657a1e256ab",
        "1564",
        "0.05414762498268938",
    ),
    "can_6f426cc8521d5180a8ed2e9d54644297": (
        "per_3194bffe8a495100879505eee54d1891",
        "570",
        "0.03156670543279615",
    ),
    "can_231ac513022254bca65c011eb4e87f40": (
        "per_8c27d890a1015ef28cfa3ff79384ef59",
        "1233",
        "0.08885846065148457",
    ),
    "can_c02fa9387c7857aba4dee1a4ab505441": (
        "per_8c27d890a1015ef28cfa3ff79384ef59",
        "225",
        "0.0003104998633800601",
    ),
    "can_748f347a62d6572787e517fe49da020f": (
        "per_a9fa93f9d3fa5bd7aa6054726c7faeeb",
        "286",
        "0.009626712444040526",
    ),
    "can_aa014c1fb1a855059c9784b9e8e42061": (
        "per_a9fa93f9d3fa5bd7aa6054726c7faeeb",
        "69",
        "0.006614263803680982",
    ),
    "can_ba76a75e1163519b9ab885118308a83d": (
        "per_a9fa93f9d3fa5bd7aa6054726c7faeeb",
        "413",
        "0.015824361086631673",
    ),
    "can_9de03d1a39345f93864f96aadbb9c6fb": (
        "per_a9fa93f9d3fa5bd7aa6054726c7faeeb",
        "700",
        "0.03838982121311835",
    ),
    "can_7dcf344ea050543a953d55f4f26c6dca": (
        "per_022858fa191a541eaa442dd0e9cefd5d",
        "13",
        "0.0007669616519174041",
    ),
    "can_d16ec7ae123b5ddd93726e119be6e0a2": (
        "per_9a0d84374b165724a2e8e92bdf92bfa5",
        "415",
        "0.017042421255800584",
    ),
    "can_d61ecb46f8f45feda51476da5f4af62b": (
        "per_353b9c4a63ac57ab9ee85eb011797754",
        "1521",
        "0.07897196261682243",
    ),
    "can_57bff83947fe5a07a99a4ddf20349df1": (
        "per_726c6d2c05a559c7b78640513d4c5f43",
        "377",
        "0.0195742471443406",
    ),
    "can_d8fd23b509175a1080507d3ad0c821ef": (
        "per_1857a6857e5f556ab0c0424377838d56",
        "709",
        "0.030262933242274203",
    ),
    "can_99bdda3c83d358cdba248a2411c0b039": (
        "per_1857a6857e5f556ab0c0424377838d56",
        "162",
        "0.009557522123893806",
    ),
    "can_ece0a797928b509bb3aba62bdc67cb29": (
        "per_2afc661b78b15020889552f8f43a6f89",
        "70",
        "0.0029717682020802376",
    ),
    "can_81f3f0e725685fc6b289feee06fb735e": (
        "per_2afc661b78b15020889552f8f43a6f89",
        "71",
        "0.015465040296231757",
    ),
}

CONSEQUENTIAL_COUNCIL_LINKS = {
    "can_8702c409b44c56869788d0fcb7ee8999": (
        "per_b05bca5a3f225453b8484ce46c8b2bb8",
        "13998",
        "0.37783416108831785",
    ),
    "can_246c0347d317593aa183f92681afb95e": (
        "per_c264c8a222ea5baea6a15b1bfeac3ae0",
        "2404",
        "0.07050680431722196",
    ),
    "can_b07911ac186c5fedbb0acd5ccd8a2bd8": (
        "per_fd89e2daa64b5513ba56eb9e1c8b51f7",
        "3410",
        "0.13065634698647458",
    ),
    "can_690689c4111c50918c06f6b446c95d0d": (
        "per_b94977f840da534caf789477d036ee8c",
        "7301",
        "0.18068204315977035",
    ),
    "can_34fbfb27258159f1b05bf2d0cb8302ff": (
        "per_d56a01f9891c5106ba8bf6281c6f713c",
        "3187",
        "0.1406939784566484",
    ),
    "can_f9f7d971b99c52cf9a48edf7b1dd38ba": (
        "per_cbad12eb2bc15f4fb7ba5a96bd68dec9",
        "3038",
        "0.2513236267372601",
    ),
    "can_cc7dfd8b06db51e592901dc4b159ca78": (
        "per_9f569a842c9e527b88cda3fc73dbfacb",
        "8491",
        "0.34869204550121147",
    ),
    "can_94c9f534cc225dbbb74ad1b9aa11a1d7": (
        "per_74212bbadc535bca8fa201bda63cee06",
        "1565",
        "0.09233038348082596",
    ),
    "can_77360db1d61055b1862abdad17f5e03c": (
        "per_3c246b205ffd55298633b81a804f8b82",
        "3374",
        "0.1751817237798546",
    ),
}

CONSEQUENTIAL_COUNCIL_FOLLOWUP_LINKS = {
    "can_3b00773d04365f64a37bf88fce264eaf": (
        "per_656bf9ee8956529195719d111d5fe53d",
        "7277",
        "0.30299371278677606",
    ),
    "can_d0b1cdfb35165fb0acbf31c7cd5ae8c2": (
        "per_194efd592b915c2ca63859d3ebbef5e0",
        "3409",
        "0.20542332027719193",
    ),
    "can_910c3031a66e5d91978ea8cb4b25fd15": (
        "per_2d23abe818995711b696fd8b8f2af4ed",
        "3215",
        "0.22634469163615883",
    ),
}

CURRENT_COUNCIL_CROSS_OFFICE_LINKS = {
    "can_c4f7c91c618d536284f4220838791524": (
        "per_b3471e8be4765e51b0381303a6c7a36d",
        "19854",
        "0.4196841905003488",
    ),
    "can_a26678612eb353068a3c5311fb7655de": (
        "per_4238a9a971965995ac6c577c126f8161",
        "12557",
        "0.3092323983549634",
    ),
}


def test_read_identity_review_decisions_preserves_audited_fields(tmp_path):
    path = tmp_path / "identity_review_dispositions.csv"
    pd.DataFrame(
        {
            "candidacy_id": ["can_one"],
            "target_person_id": ["per_one"],
            "decision": ["unresolved"],
            "confidence": ["low"],
            "rationale": ["The result alone does not establish identity."],
            "evidence_urls": ["https://example.test/result"],
            "reviewer": ["independent-review-bucket-0"],
        }
    ).to_csv(path, index=False)

    decisions = read_identity_review_decisions(path)

    assert decisions.to_dict("records") == [
        {
            "candidacy_id": "can_one",
            "target_person_id": "per_one",
            "decision": "unresolved",
            "confidence": "low",
            "rationale": "The result alone does not establish identity.",
            "evidence_urls": "https://example.test/result",
            "reviewer": "independent-review-bucket-0",
        }
    ]


def test_read_identity_review_decisions_fails_clearly_when_source_is_missing(tmp_path):
    with pytest.raises(ValueError, match="identity review dispositions source is missing"):
        read_identity_review_decisions(tmp_path / "missing.csv")


@pytest.mark.parametrize("blank_column", ["candidacy_id", "target_person_id"])
def test_read_identity_review_decisions_rejects_blank_identity_keys(tmp_path, blank_column):
    path = tmp_path / "decisions.csv"
    row = {
        "candidacy_id": "can_one",
        "target_person_id": "per_one",
        "decision": "confirmed",
        "confidence": "high",
        "rationale": "Official evidence.",
        "evidence_urls": "https://example.test/evidence",
        "reviewer": "reviewer-a",
    }
    row[blank_column] = ""
    pd.DataFrame([row]).to_csv(path, index=False)

    with pytest.raises(ValueError, match=f"nonblank {blank_column}"):
        read_identity_review_decisions(path)


def test_review_confirmation_can_supersede_matching_automated_confirmation():
    people = pd.DataFrame(
        {
            "person_id": ["per_one"],
            "preferred_name": ["Alex One"],
            "identity_status": ["active"],
            "redirect_to_person_id": [pd.NA],
            "created_release": ["v1"],
        }
    )
    links = pd.DataFrame(
        {
            "candidacy_id": ["can_one"],
            "person_id": ["per_one"],
            "link_status": ["confirmed"],
            "method": ["municipal_roster_continuity"],
            "evidence": ["automated roster evidence"],
            "reviewer": ["municipal_rosters/v1"],
            "valid_from_release": ["v2"],
            "valid_to_release": [pd.NA],
        }
    )
    decisions = pd.DataFrame(
        {
            "candidacy_id": ["can_one"],
            "target_person_id": ["per_one"],
            "decision": ["confirmed"],
            "confidence": ["high"],
            "rationale": ["Independent official evidence confirms the same Person."],
            "evidence_urls": ["https://example.test/official-profile"],
            "reviewer": ["independent-reviewer"],
        }
    )

    reviewed = apply_identity_review_decisions(people, links, decisions, release_id="v2")

    assert reviewed["valid_to_release"].eq("v2").sum() == 1
    active = reviewed.loc[reviewed["valid_to_release"].isna()].iloc[0]
    assert active["link_status"] == "confirmed"
    assert active["method"] == "curated_review_confirmed"
    assert active["person_id"] == "per_one"


def test_new_evidence_can_revise_a_reviewed_hold_without_rewriting_history():
    people = pd.DataFrame(
        {
            "person_id": ["per_one"],
            "preferred_name": ["Alex One"],
            "identity_status": ["active"],
            "redirect_to_person_id": [pd.NA],
            "created_release": ["v1"],
        }
    )
    links = pd.DataFrame(
        {
            "candidacy_id": ["can_one"],
            "person_id": ["per_one"],
            "link_status": ["proposed"],
            "method": ["exact_normalized_name_review"],
            "evidence": ["name-only proposal"],
            "reviewer": ["bootstrap"],
            "valid_from_release": ["v1"],
            "valid_to_release": [pd.NA],
        }
    )
    hold = pd.DataFrame(
        {
            "candidacy_id": ["can_one"],
            "target_person_id": ["per_one"],
            "decision": ["unresolved"],
            "confidence": ["low"],
            "rationale": ["A result and exact name alone are insufficient."],
            "evidence_urls": ["https://example.test/result"],
            "reviewer": ["reviewer-a"],
        }
    )
    held = apply_identity_review_decisions(people, links, hold, release_id="v2")
    revised = hold.copy()
    revised["decision"] = "confirmed"
    revised["confidence"] = "high"
    revised["rationale"] = "A newly located official biography enumerates both candidacies."
    revised["evidence_urls"] = "https://example.test/official-biography"

    confirmed = apply_identity_review_decisions(people, held, revised, release_id="v3")

    history = confirmed.loc[confirmed["candidacy_id"].eq("can_one")]
    assert history["link_status"].tolist() == ["proposed", "unresolved", "confirmed"]
    assert history["valid_to_release"].tolist()[:2] == ["v2", "v3"]
    active = history.loc[history["valid_to_release"].isna()].iloc[0]
    assert active["link_status"] == "confirmed"
    assert active["person_id"] == "per_one"


def test_review_decisions_distinguish_confirmation_hold_and_rejection():
    candidacies = pd.DataFrame(
        {
            "candidacy_id": ["can_confirm", "can_hold", "can_reject"],
            "candidate_name": ["Alex One", "Alex One", "Alex Two"],
        }
    )
    people = pd.DataFrame(
        {
            "person_id": ["per_one", "per_two"],
            "preferred_name": ["Alex One", "Alex Two"],
            "identity_status": ["active", "active"],
            "redirect_to_person_id": [pd.NA, pd.NA],
            "created_release": ["v1", "v1"],
        }
    )
    links = pd.DataFrame(
        {
            "candidacy_id": ["can_confirm", "can_hold", "can_reject"],
            "person_id": ["per_one", "per_one", "per_two"],
            "link_status": ["proposed", "proposed", "proposed"],
            "method": ["exact_name", "exact_name", "exact_name"],
            "evidence": ["proposal", "proposal", "proposal"],
            "reviewer": ["bootstrap", "bootstrap", "bootstrap"],
            "valid_from_release": ["v1", "v1", "v1"],
            "valid_to_release": [pd.NA, pd.NA, pd.NA],
        }
    )
    decisions = pd.DataFrame(
        {
            "candidacy_id": ["can_confirm", "can_hold", "can_reject"],
            "target_person_id": ["per_one", "per_one", "per_two"],
            "decision": ["confirmed", "unresolved", "rejected"],
            "confidence": ["high", "low", "high"],
            "rationale": [
                "Official biography bridges both appearances.",
                "No source distinguishes continuity from a namesake.",
                "Official biographies identify different people.",
            ],
            "evidence_urls": [
                "https://example.test/confirm",
                "https://example.test/hold",
                "https://example.test/reject",
            ],
            "reviewer": ["reviewer-a", "reviewer-a", "reviewer-a"],
        }
    )

    reviewed = apply_identity_review_decisions(
        people,
        links,
        decisions,
        release_id="v2",
    )

    active = reviewed.loc[reviewed["valid_to_release"].isna()].set_index("candidacy_id")
    assert active["link_status"].to_dict() == {
        "can_confirm": "confirmed",
        "can_hold": "unresolved",
        "can_reject": "rejected",
    }
    assert active["person_id"].to_dict() == {
        "can_confirm": "per_one",
        "can_hold": "per_one",
        "can_reject": "per_two",
    }
    closed = reviewed.loc[reviewed["valid_to_release"].eq("v2")]
    assert closed["link_status"].tolist() == ["proposed", "proposed", "proposed"]

    attached = attach_confirmed_people(candidacies, people, reviewed).set_index("candidacy_id")
    assert attached.loc["can_confirm", "person_id"] == "per_one"
    assert pd.isna(attached.loc["can_hold", "person_id"])
    assert pd.isna(attached.loc["can_reject", "person_id"])

    replayed = apply_identity_review_decisions(
        people,
        reviewed,
        decisions,
        release_id="v2",
    )
    pd.testing.assert_frame_equal(replayed, reviewed)


def test_all_published_proposals_have_an_audited_final_disposition():
    original_decisions = read_identity_review_decisions(
        REPO_ROOT / "data" / "reference" / "identity_review_dispositions.csv"
    )
    assert len(original_decisions) == 931
    assert original_decisions["decision"].value_counts().to_dict() == {
        "unresolved": 783,
        "confirmed": 143,
        "rejected": 5,
    }
    decisions = exclude_superseded_identity_decisions(
        original_decisions, REPO_ROOT / "data" / "reference"
    )

    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    active = links.loc[links["valid_to_release"].isna()]
    proposed = active.loc[active["link_status"].eq("proposed")]
    assert len(proposed) == 59
    assert proposed["candidacy_id"].is_unique
    proposed_results = results.loc[proposed["candidacy_id"]]
    assert proposed_results["result_status"].eq("pending").all()
    assert proposed_results["election_date"].eq("2026-10-26").all()
    assert proposed_results["person_id"].isna().all()
    completed_ids = set(results.index[results["result_status"].eq("final")])
    assert not proposed["candidacy_id"].isin(completed_ids).any()

    active_claims = active.loc[active["person_id"].notna()].set_index("candidacy_id")
    expected_status = decisions.set_index("candidacy_id")["decision"]
    actual = active_claims.loc[expected_status.index]
    assert actual.index.is_unique
    assert actual["link_status"].to_dict() == expected_status.to_dict()
    expected_people = decisions.set_index("candidacy_id")["target_person_id"]
    assert actual["person_id"].to_dict() == expected_people.to_dict()

    confirmed = expected_status.index[expected_status.eq("confirmed")]
    held = expected_status.index[~expected_status.eq("confirmed")]
    assert results.loc[confirmed, "person_id"].to_dict() == expected_people.loc[confirmed].to_dict()
    assert results.loc[held, "person_id"].isna().all()


def test_council_batch_2_identity_corrections_are_published_without_result_changes():
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    decisions = read_identity_review_decisions(
        REPO_ROOT / "data" / "reference" / "identity_review_dispositions.csv"
    ).set_index("candidacy_id")

    for candidacy_id, (person_id, votes, vote_share) in COUNCIL_BATCH_2_EXPECTED.items():
        assert results.loc[candidacy_id, "person_id"] == person_id
        assert results.loc[candidacy_id, "votes"] == votes
        assert results.loc[candidacy_id, "vote_share"] == vote_share
        assert results.loc[candidacy_id, "elected"] == "False"
        assert decisions.loc[candidacy_id, "decision"] == "confirmed"
        assert decisions.loc[candidacy_id, "reviewer"] == "council-batch-2-evidence-review"

        active = links.loc[
            links["candidacy_id"].eq(candidacy_id) & links["valid_to_release"].isna()
        ]
        assert len(active) == 1
        assert active.iloc[0]["person_id"] == person_id
        assert active.iloc[0]["link_status"] == "confirmed"
        history = links.loc[links["candidacy_id"].eq(candidacy_id)]
        assert {"proposed", "unresolved", "confirmed"} <= set(history["link_status"])
        assert (
            history.loc[history["link_status"].eq("unresolved"), "valid_to_release"].notna().all()
        )
        assert people.loc[person_id, "identity_status"] == "active"
        assert pd.isna(people.loc[person_id, "redirect_to_person_id"])


def test_consequential_council_identity_review_publishes_only_evidence_backed_links():
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    decisions = read_identity_review_decisions(
        REPO_ROOT / "data" / "reference" / "identity_review_dispositions.csv"
    ).set_index("candidacy_id")

    for candidacy_id, (person_id, votes, vote_share) in CONSEQUENTIAL_COUNCIL_LINKS.items():
        assert results.loc[candidacy_id, "person_id"] == person_id
        assert results.loc[candidacy_id, "votes"] == votes
        assert results.loc[candidacy_id, "vote_share"] == vote_share
        assert results.loc[candidacy_id, "elected"] == "False"
        assert decisions.loc[candidacy_id, "decision"] == "confirmed"
        assert decisions.loc[candidacy_id, "reviewer"] == "consequential-council-evidence-review"

        history = links.loc[links["candidacy_id"].eq(candidacy_id)]
        active = history.loc[history["valid_to_release"].isna()]
        assert len(active) == 1
        assert active.iloc[0]["person_id"] == person_id
        assert active.iloc[0]["link_status"] == "confirmed"
        assert {"proposed", "unresolved", "confirmed"} <= set(history["link_status"])

    for candidacy_id, (
        person_id,
        votes,
        vote_share,
    ) in CONSEQUENTIAL_COUNCIL_FOLLOWUP_LINKS.items():
        assert results.loc[candidacy_id, "person_id"] == person_id
        assert results.loc[candidacy_id, "votes"] == votes
        assert results.loc[candidacy_id, "vote_share"] == vote_share
        assert results.loc[candidacy_id, "elected"] == "False"
        assert decisions.loc[candidacy_id, "decision"] == "confirmed"
        assert decisions.loc[candidacy_id, "target_person_id"] == person_id
        assert decisions.loc[candidacy_id, "reviewer"] == ("consequential-council-hold-followup")

        history = links.loc[links["candidacy_id"].eq(candidacy_id)]
        active = history.loc[history["valid_to_release"].isna()]
        assert len(active) == 1
        assert active.iloc[0]["person_id"] == person_id
        assert active.iloc[0]["link_status"] == "confirmed"
        assert {"proposed", "unresolved", "confirmed"} <= set(history["link_status"])


def test_current_council_cross_office_careers_are_linked_in_the_public_release():
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    decisions = read_identity_review_decisions(
        REPO_ROOT / "data" / "reference" / "identity_review_dispositions.csv"
    ).set_index("candidacy_id")

    for candidacy_id, (
        person_id,
        votes,
        vote_share,
    ) in CURRENT_COUNCIL_CROSS_OFFICE_LINKS.items():
        result = results.loc[candidacy_id]
        assert result["person_id"] == person_id
        assert result["votes"] == votes
        assert result["vote_share"] == vote_share
        assert result["elected"] == "False"
        assert decisions.loc[candidacy_id, "decision"] == "confirmed"
        assert decisions.loc[candidacy_id, "target_person_id"] == person_id
        assert decisions.loc[candidacy_id, "reviewer"] == "current-council-linkage-audit"

        history = links.loc[links["candidacy_id"].eq(candidacy_id)]
        active = history.loc[history["valid_to_release"].isna()]
        assert len(active) == 1
        assert active.iloc[0]["person_id"] == person_id
        assert active.iloc[0]["link_status"] == "confirmed"
        assert {"proposed", "unresolved", "confirmed"} <= set(history["link_status"])
