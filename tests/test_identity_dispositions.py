"""Published review states for adjudicated Candidacy-Person proposals."""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.identity import attach_confirmed_people
from toronto_election_results.identity_curations import exclude_person_record_merge_decisions
from toronto_election_results.identity_dispositions import (
    apply_identity_review_decisions,
    read_identity_review_decisions,
)
from toronto_election_results.mayoral_career import exclude_superseded_identity_decisions
from toronto_election_results.schema import stable_id
from toronto_election_results.trustee_career import (
    build_trustee_career_identity_assertions,
    reconcile_trustee_identity_decisions,
)

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
    # 2017 Ward 42: the share is of the 29 candidates' 10,418 votes, without the workbook's
    # ballot-accounting lines.
    "can_aa014c1fb1a855059c9784b9e8e42061": (
        "per_a9fa93f9d3fa5bd7aa6054726c7faeeb",
        "69",
        "0.006623152236513726",
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
    assert len(original_decisions) == 1610
    assert original_decisions["decision"].value_counts().to_dict() == {
        "unresolved": 767,
        "confirmed": 840,
        "rejected": 3,
    }
    decisions = exclude_superseded_identity_decisions(
        original_decisions, REPO_ROOT / "data" / "reference"
    )

    result_rows = pd.read_csv(REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string")
    decisions = reconcile_trustee_identity_decisions(
        decisions,
        REPO_ROOT / "data" / "reference",
        build_trustee_career_identity_assertions(REPO_ROOT / "data" / "reference", result_rows),
    )
    decisions = exclude_person_record_merge_decisions(decisions)
    results = result_rows.set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    active = links.loc[links["valid_to_release"].isna()]
    # With the 2026 results declared, no Candidacy is pending, so no proposal may stay open.
    proposed = active.loc[active["link_status"].eq("proposed")]
    assert proposed.empty
    assert not results["result_status"].eq("pending").any()

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


def test_2026_federal_repeat_candidacy_uses_the_explicit_party_identity_bridge():
    results = pd.read_csv(REPO_ROOT / "data/out/election_results.csv", dtype="string").set_index(
        "candidacy_id"
    )
    decisions = read_identity_review_decisions(
        REPO_ROOT / "data/reference/identity_review_dispositions.csv"
    ).set_index("candidacy_id")
    current = "can_3276cb4ff23b5a5ebb50591cae7884c3"
    prior = "can_badbc189906252d8b0dee7f0e4158c58"

    assert results.loc[current, "person_id"] == results.loc[prior, "person_id"]
    assert results.loc[current, "person_id"] == "per_2d514d5238de53a28cb16b664d6c38b1"
    assert results.loc[current, "votes"] == "8496"
    assert decisions.loc[current, "decision"] == "confirmed"
    assert (
        "ndp-announces-candidates-august-31-federal-byelections"
        in decisions.loc[current, "evidence_urls"]
    )


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


def test_person_record_merges_join_biography_backed_careers():
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string")
    active = links.loc[links["valid_to_release"].isna() & links["person_id"].notna()]
    confirmed = active.loc[active["link_status"].eq("confirmed")].set_index("candidacy_id")
    expected = {
        # David Miller: 1993 federal, 1996 provincial, 2003 mayor.
        "can_a648abaafa76540fbcdd0c7b8260d82d": "per_ad293f1387af572cad45897886519bb6",
        "can_07dca60e733959a19d4da077883f5ce6": "per_ad293f1387af572cad45897886519bb6",
        "can_63e1ea224f9a5132ae24d181a6bd7ca2": "per_ad293f1387af572cad45897886519bb6",
        # Denzil Minnan-Wong, listed in 1997 as Denzil Wong-Minnan.
        "can_4c067bdd1cb656eda20a29c8e32f880a": "per_cacdaf09421e5b0e98d0138141449f29",
        # Elizabeth Rowley's 2019 federal run, previously unresolved.
        "can_2e8a945cf8ef5a6fa674861ebd1c6391": "per_aa1078f5c83b568188c98224c0b71f58",
        # Mike Feldman, 1997 and 2006.
        "can_f74895fe25385bccbaf2316f6b2146a0": "per_a91b6e0f34fc5ad894ceeecfe6f286ca",
        "can_21292996478554dd9696fe813d2bee9c": "per_a91b6e0f34fc5ad894ceeecfe6f286ca",
        # Maria Augimeri's and Adam Giambrone's later provincial/federal runs.
        "can_3969a285f02754068d6aeb8ab44662cb": "per_a39385ec8fc65555a86f30b50d338a33",
        "can_fb1e7879c831534288610a41f5f91115": "per_2058e961126e5e8499b3ea8046068164",
        # Second pass on the hard cases: Verdecchia's 1997 federal run, Papadakis's 1993
        # federal run, Kalevar's 1993 federal and 2019 Davenport runs, Yaqoob Khan's 2006
        # Ward 28 run, Van Schouwen's 1997 council run and Mulhall's 1997 and 2006 runs.
        "can_56f5a6a9fd6a57d6806904de02528459": "per_3997000aca965ed98716d39d8bf36311",
        "can_0375c057e7595add855af804ab66e056": "per_ea45e9b94d525274a5445c574fd8e1f1",
        "can_45feeeb8acb552f6816da3ce7e48846b": "per_7a6c09e82feb52cdbcd1fa757f7c708d",
        "can_3a2322c5bf575c04ae6b9578cdd36be1": "per_7a6c09e82feb52cdbcd1fa757f7c708d",
        "can_6321ff70309a5eee9e7fdf6502173a9c": "per_8e9d36e1b43653b6a469e5c9b87e95e7",
        "can_c9ad2fc1d2335e80a32646c199e4cba6": "per_eeea104c1cce54a382c006cdb50f38aa",
        "can_c09ca8c2088d5f9d8bef60319f713fcc": "per_5903ae015a9e52259eb7b89b21d09855",
        "can_14fc3bff7c6a52a491b57e1949ecfb91": "per_5903ae015a9e52259eb7b89b21d09855",
        # Trustees who ran provincially in their own area: Irene Atkinson (1999 NDP
        # Parkdale—High Park), Stephnie Payne (1999 NDP York West) and Christopher Caldwell
        # (2018 Green Etobicoke—Lakeshore).
        "can_bd38105deb035513b41a00bb71037116": "per_4fce2dffe8095bee8c68ca1d2c8ac324",
        "can_d8da435540f6568e9e0d1f4673e56b22": "per_4fce2dffe8095bee8c68ca1d2c8ac324",
        "can_aee8a5d409595b2e8bcf5e83b774b92e": "per_4fce2dffe8095bee8c68ca1d2c8ac324",
        "can_d7b5d29839895ef09bfb228255c3bffc": "per_a7badd21391e5d63b1661d0519a7d7d2",
        "can_75e01768c0335714ad84f6fdb52fdbef": "per_a7badd21391e5d63b1661d0519a7d7d2",
        "can_530f3dc85c045cb2826dcc1146242e6b": "per_a7badd21391e5d63b1661d0519a7d7d2",
        "can_cde8d0d89b3f5a58927f60085f219dfa": "per_e1baa72d43c95abba5db0f3235581d4c",
        "can_3a05e85b5138523db95b7ccb0db75715": "per_e1baa72d43c95abba5db0f3235581d4c",
    }
    assert confirmed.loc[list(expected), "person_id"].to_dict() == expected
    redirects = people.set_index("person_id")
    assert redirects.loc["per_b04a5fd11b4951368dcd05cb899898f5", "identity_status"] == "deprecated"
    assert (
        redirects.loc["per_b04a5fd11b4951368dcd05cb899898f5", "redirect_to_person_id"]
        == "per_ad293f1387af572cad45897886519bb6"
    )
    for provincial_person_id, trustee_person_id in {
        "per_e07eaecf868050639b1cbe712c83663a": "per_4fce2dffe8095bee8c68ca1d2c8ac324",
        "per_6d724de5779557149c7eceadeff15e1b": "per_a7badd21391e5d63b1661d0519a7d7d2",
    }.items():
        assert redirects.loc[provincial_person_id, "identity_status"] == "deprecated"
        assert redirects.loc[provincial_person_id, "redirect_to_person_id"] == trustee_person_id
        assert redirects.loc[trustee_person_id, "identity_status"] == "active"
    # Bruce Davis's 1995 provincial run stays on its own Person: no source names that contest.
    assert redirects.loc["per_2550e04d307f56558ceba2a6c7f2df26", "identity_status"] == "active"
    # Caldwell's 2010 Ward 29 council run keeps its own Person and his 2019 federal run
    # stays an unresolved claim to it.
    assert (
        confirmed.loc["can_656ab05636855a8f856c3d8cde842334", "person_id"]
        == "per_4cdca864f8055243963b86909ed39038"
    )
    assert redirects.loc["per_4cdca864f8055243963b86909ed39038", "identity_status"] == "active"
    # Mulhall's 2014 run and Caldwell's 2019 federal run stay unresolved. (Kalevar's
    # 1994-2000 council runs were later confirmed from the Toronto Star's profiles.)
    unresolved = active.loc[active["link_status"].eq("unresolved")].set_index("candidacy_id")
    assert {
        "can_227eaae6d22652989e68a0314620f2e3",
        "can_98f13c94ab1f560994954198b31935dd",
    } <= set(unresolved.index)
    assert (
        unresolved.loc["can_98f13c94ab1f560994954198b31935dd", "person_id"]
        == "per_4cdca864f8055243963b86909ed39038"
    )
    # Paul Sutherland's 1995 Oriole run is not covered by his biography.
    assert (
        confirmed.loc["can_f14b32f044585ca490d383a9295eddf9", "person_id"]
        == "per_81a4729b82615321ab2157051003edf5"
    )


def test_2010_tcdsb_ward_9_runner_up_is_the_sitting_ward_9_trustee():
    """The 2010 rejection rested on a Ward 6 row that a parser error created and that is retired."""

    results = pd.read_csv(REPO_ROOT / "data/out/election_results.csv", dtype="string").set_index(
        "candidacy_id"
    )
    decisions = read_identity_review_decisions(
        REPO_ROOT / "data/reference/identity_review_dispositions.csv"
    ).set_index("candidacy_id")
    current = "can_bfb4251aac145441b5ec9fd4ac7c75ac"
    earlier_wins = ["can_dced59fe77ad5682a90e4bffd42645b6", "can_d1005a8210675119a0356ed070ee51a7"]

    assert "can_708733b1951f5dfea952d00789d95e74" not in results.index
    assert results.loc[current, "votes"] == "5636"
    assert results.loc[[current, *earlier_wins], "person_id"].unique().tolist() == [
        "per_1532e26a4057567c93e20e166067edcc"
    ]
    assert results.loc[earlier_wins, "official_district_id"].tolist() == ["9", "9"]
    assert decisions.loc[current, "decision"] == "confirmed"
    assert decisions.loc[current, "confidence"] == "high"
    assert (
        "voters-choose-at-least-12-new-school-trustees" in decisions.loc[current, "evidence_urls"]
    )


def test_variant_name_merges_join_split_careers():
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    active = links.loc[links["valid_to_release"].isna() & links["person_id"].notna()]
    confirmed = active.loc[active["link_status"].eq("confirmed")].set_index("candidacy_id")
    careers = {
        # Michael/Mike Del Grande: 1994 MSSB, 1997 and 2000 TCDSB.
        "per_5d4ed9a602615789a5ed8bde2ae82e62": [
            "can_0b7cd890417859f6808a807cbefacfe3",
            "can_a425763a34f75800969f26270367a518",
            "can_b3019b205d9550edbdf45f01e0612ebb",
        ],
        # Elizebeth/Elizabeth Moyer: 1994, 1997, 2000, 2010 and 2014 trustee races.
        "per_526d2746efd55198a90b1e6c06dbc83c": [
            "can_e6aaeb1031a95c3a934afed707e890a0",
            "can_8f3ccc57c513570193163230d6023fd0",
            "can_e1574306d9a85c9f851c54051ec04ab8",
            "can_0ab8f6a4ce795dd9818519bca08626d8",
            "can_e9be77407e6b54fbb418a114a27290ab",
        ],
        # Iqbal (S.) Dhanju: 1994, 1997, 2000.
        "per_6f6434dc6b37567890cd76d347d1c7b2": [
            "can_1b7a8da0e9ce5231ac8f6996c313769c",
            "can_f96b4b4d8dd65a428ae5026b49450810",
            "can_8d2f68d7d2da56f8a59d74747e32ab42",
        ],
        # Luis A. Lopes Silva / Luis Silva: 1994, 1997, 2000 trustee and 2003 mayor.
        "per_620960c232f85db6b87db233834b5a4b": [
            "can_4b17f6cb00d052c0b540fde5b9551f9c",
            "can_12d8aaf9450056aab6e423772fb5a3da",
            "can_dd1dc5a5be9b5a1bbbaaf1f1b597ef75",
            "can_c542909642f754f0878c8d17b56350e4",
        ],
        # Norm/Norman Gardner: 1994 Metro, 1997 federal, 1997 and 2018 council.
        "per_940597ecad835bb39f145cd085e3f791": [
            "can_60fad535ce8e5a059439e2cf040b38f7",
            "can_1bcbb73f4c7e5f57b5a22ab4a90a7c78",
            "can_2bb5543b9fe6513caef7dde2ad618828",
            "can_97cccfc87fce5dac8f2fc2916ae439ee",
        ],
        # Constantine Kritsonis: 1995 Oakwood and the York Centre federal runs.
        "per_7bc0075b9dc654e0bc0cd0f8ba293879": [
            "can_69b9b9adc1cc5504884c0d93b0549f6c",
            "can_9d041f0580fd58d1a27fe5f6413a9cc3",
            "can_40187923ba7b5efd9873ea2964c7d311",
            "can_cd970a3b3c0e5ee881be85d7a62aa280",
            "can_3d6529e8861f5d7b947e46b79ae816d6",
            "can_44fc83800bf55475b694fea79eb3e0d1",
        ],
        # Claude-Reno D'Aigle: French Catholic trustee races 1994-2018.
        "per_19437117d92857d9ac07198a36e10a37": [
            "can_32c54b77892c57619c78fc57f3b6a075",
            "can_72e11b63044d504482c836963351cd14",
            "can_d494a4a555835cb6823270b2d3941411",
            "can_54f6046303d25e5d96b4cd2fc06a07de",
            "can_34ac365b41fe538e882fa0a2500c27fd",
            "can_613e10c620db55a09d05aaf1d8b45902",
            "can_064774a3fa9755b69ee37c1eeac543f3",
            "can_f434f54386fe5069b5ce83058d2c1b3b",
        ],
    }
    for person_id, candidacy_ids in careers.items():
        assert confirmed.loc[candidacy_ids, "person_id"].eq(person_id).all(), person_id
        assert people.loc[person_id, "identity_status"] == "active"
    merged_away = {
        "per_a279ecb0a6d25718832d86201659833f": "per_5d4ed9a602615789a5ed8bde2ae82e62",
        "per_ee6719ea2e2750fa812eace9e3ae5f45": "per_6f6434dc6b37567890cd76d347d1c7b2",
        "per_a0343b9bd41e5487828af187ca743698": "per_620960c232f85db6b87db233834b5a4b",
        "per_2a6a1579a6b95b6fb0a4011fa5f01f24": "per_940597ecad835bb39f145cd085e3f791",
        "per_c51eea41d6dc504185534c80c1545791": "per_19437117d92857d9ac07198a36e10a37",
        "per_0d4cf29bc1c4569ab45bbd86b3c12bb4": "per_19437117d92857d9ac07198a36e10a37",
    }
    for person_id, canonical in merged_away.items():
        assert people.loc[person_id, "identity_status"] == "deprecated"
        assert people.loc[person_id, "redirect_to_person_id"] == canonical
    # Not established, so left as they were: Elizabeth Moyer's 2006 council run and
    # Kritsonis's 2003 provincial run. (The 2000 and 2003 André Duclos records were joined
    # later from the Star's 2003 profile; see test_star_profiles_settle_backlog_runs.)
    for person_id in (
        "per_f285f0621dbe566cadb4c7cee0d4a752",
        "per_6ae741fa1fc65281a8b7aea106352cb1",
        "per_01d27f754bc75218aa848e00887a9d36",
    ):
        assert people.loc[person_id, "identity_status"] == "active"
    assert confirmed.loc["can_2293417524625b80b2790e8b10c7ee9b", "person_id"] == (
        "per_f285f0621dbe566cadb4c7cee0d4a752"
    )
    assert confirmed.loc["can_e60111ecd5f45c6e80d7d39e39d3ebf6", "person_id"] == (
        "per_6ae741fa1fc65281a8b7aea106352cb1"
    )


def test_star_profiles_link_interior_trustee_runs():
    """Toronto Star candidate profiles join runs that sat unlinked between linked ones."""

    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    active = links.loc[links["valid_to_release"].isna() & links["person_id"].notna()]
    confirmed = active.loc[active["link_status"].eq("confirmed")].set_index("candidacy_id")
    careers = {
        # Ron McNaughton: 1994 Scarborough, 1997 and 2000 TDSB wins, 2006 TDSB Ward 20.
        "per_efb9299062b15bd2abb7245d2003637e": [
            "can_4bd1365d2e785bfab4295318c016127a",
            "can_97ee1b95680954a38de953dcce46dc95",
            "can_49142cdd5fff580e902467ae86fe927e",
            "can_dd5358979159513cba2c1ebff7de6229",
        ],
        # Ron Gillis, insurance broker: 1994 Separate School Board, TCDSB Ward 2 1997-2006.
        "per_57886ab346255d2fb7f769a5ae8f03f0": [
            "can_7642af517dae5fefa2288d6176fa07f8",
            "can_1c2184b57e725b80b49df391e782d00e",
            "can_318e767db7f75756b34a029808e3cdd8",
            "can_adf9754e21ef560ab39632234c38c2ec",
            "can_127d1719b4ab58e0a5c111c6c16a1232",
        ],
        # Nellie Pedro: 1994 trustee, 2000 TDSB Ward 9, 2003 Liberal MPP run, 2006 Ward 9.
        "per_03b6008242f554e59fa8bb05090a7262": [
            "can_7fbd53056d95515c88def2bd03e84a48",
            "can_f3163d9a8aeb569199f5905c4d3fd0ef",
            "can_15ddab4ce6965febad2feb8e87938d9c",
            "can_8bb9b57903825e7cbd6728c3739e5e1c",
        ],
        # Joseph Martino: 2000 council run and the 2003 "Joe Martino" trustee win.
        "per_09a4cbae05385a73bdd309e7d767549f": [
            "can_9ce067e1505b5b86bdaf6edf19ffe7ae",
            "can_25d1c914e203511d95369912e2f5b604",
            "can_ced36ce6c10e5418aa4bd089cf31b71f",
            "can_c5ea382fa99158c5bb8f1784c7ef5a00",
            "can_14606696456d5af7a865205fcd7b7e68",
        ],
        # Doug Stephens's North York trustee terms, 1994-2000, as a new Person.
        "per_0941986dbdc45b0293aacf7cc9eaeb3a": [
            "can_c53dbd91c1df5ac68b84e5ef94e0758c",
            "can_d7525997644c53e3ba6f7786451c7ba2",
            "can_2275b55463c75a7791fe9ae1b717cdd7",
        ],
    }
    for person_id, candidacy_ids in careers.items():
        assert confirmed.loc[candidacy_ids, "person_id"].eq(person_id).all(), person_id
        assert results.loc[candidacy_ids, "person_id"].eq(person_id).all(), person_id
        assert people.loc[person_id, "identity_status"] == "active"
    assert people.loc["per_66464a384b635f5c8f99de40022bb7f6", "identity_status"] == "deprecated"
    assert people.loc["per_66464a384b635f5c8f99de40022bb7f6", "redirect_to_person_id"] == (
        "per_09a4cbae05385a73bdd309e7d767549f"
    )
    # No source covers these, so they stay as they were: the 2006 Willowdale Doug
    # Stephens keeps his own Person, and McNaughton's 2016 by-election run is unresolved.
    assert people.loc["per_1418d2b1662d56c6a097199de2deb696", "identity_status"] == "active"
    assert confirmed.loc["can_3601f1f04d685a6388912dd4809cd435", "person_id"] == (
        "per_1418d2b1662d56c6a097199de2deb696"
    )
    unresolved = active.loc[active["link_status"].eq("unresolved")].set_index("candidacy_id")
    assert unresolved.loc["can_3c9323a2d4f45193bd554ec993be451a", "person_id"] == (
        "per_efb9299062b15bd2abb7245d2003637e"
    )
    assert pd.isna(results.loc["can_3c9323a2d4f45193bd554ec993be451a", "person_id"])


def test_star_profiles_settle_backlog_runs():
    """The Star's 1994-2006 profiles and election coverage confirm, join or regroup backlog runs."""

    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    decisions = read_identity_review_decisions(
        REPO_ROOT / "data" / "reference" / "identity_review_dispositions.csv"
    )
    revised = decisions.loc[decisions["reviewer"].eq("star-candidate-profiles-backlog-2026-10-30")]
    assert revised["decision"].value_counts().to_dict() == {
        "confirmed": 68,
        "unresolved": 4,
        "rejected": 2,
    }
    revised_confirmed = revised.loc[revised["decision"].eq("confirmed")]
    assert revised_confirmed["confidence"].eq("high").all()
    assert (
        results.loc[revised_confirmed["candidacy_id"], "person_id"].tolist()
        == revised_confirmed["target_person_id"].tolist()
    )

    active = links.loc[links["valid_to_release"].isna() & links["person_id"].notna()]
    confirmed = active.loc[active["link_status"].eq("confirmed")].set_index("candidacy_id")
    careers = {
        # Mike Armstrong, the insurance agent, 1994-2003; the 2003 ward preview says the 2003
        # candidate ran against McConnell in 2000.
        "per_ad2c9444d6df5c9c9097a61b9e0419e4": [
            "can_9b9e42045cfd56e89b805a66b034ad5d",
            "can_0dadd286dd4b5b159266f2aded94a91a",
            "can_bd54c82af91a515f8e7e7fb1d8cb53cb",
            "can_75df7fdf41715b34a8e9359c4c08e3ad",
        ],
        # Michael Yorke, the carpenter: 1994 East Danforth council and 1999 NDP.
        "per_2fa2c5b28feb5461bf34c6a202f437ec": [
            "can_c1b2ebeb7d0a58bfbd93f5d3b78353d6",
            "can_0e4e3f5711765d8385541f70bb5607ee",
        ],
        # David Hutcheon, Ward 1 councillor and Progressive Conservative candidate.
        "per_e63900f9e4325c71a9f2a5bebc34a2b0": [
            "can_949ba4bf657d53d7bbdc21bbaa22c210",
            "can_2e40d7cc27755b22b2abd6d4db99e979",
            "can_34a0052c6db158f9ba973b841b887a15",
            "can_5c71ca76050c5064ad28b932a633b112",
        ],
        # Paul Fernandes, the East York separate school trustee who ran for council.
        "per_50f496d43c915062a9f5ef7cf9174952": [
            "can_ba3c1a3ecac659de9a342a5209ca6f6c",
            "can_3b90de3ccd095104bfc0b3cb04503178",
            "can_29de57954f1e5cd4aed9fd73c42dfaf8",
        ],
        # Marlene Ciarrocchi, Catholic board runs from 1994 to 2010.
        "per_38f3be6e70dd5d27bd78f8eca7820a02": [
            "can_5cc1dffeac385a53a52eca54685139e2",
            "can_becc096f64af5413abd8a76a1f4709c3",
            "can_3709dce81620517b9df33de6cd941dae",
            "can_7685c3cc373b5d0ba7ec032229e61f04",
        ],
        # Stephen Thiele, the Etobicoke lawyer, 1997-2014.
        "per_4426f79f0e8d5e639aa007a3e6712197": [
            "can_97da5b13caed58e78b8134e62eb263a2",
            "can_b7aa7a34550e57a4a2dd79c265951f7a",
            "can_615768da2daf5074b4732694ea28a8c5",
            "can_4b4d13ab93a95ddeb7ff12670bc0b962",
        ],
        # Mike Thomas, the 1994 Scarborough council candidate and 1995 PC candidate.
        "per_d9d8cf88891157b6bdc0fcbe54546451": [
            "can_9997e03f04b35d24b8e33d665936d868",
            "can_1fa4ade626445c5ca88c85f0d12f912a",
        ],
        # Adrian Heaps, 1999 Liberal candidate and Ward 35 councillor (2003 preview).
        "per_9074ce6d34475a738c239ee5c8847102": [
            "can_5823017f88725df9915e7ac7046606bc",
            "can_db3e3fd34eef531aa040aee8d5257d34",
            "can_85e98fc56eac54c39d4b9cc70b1017ae",
            "can_e9906b69c72d5566b85bddc4bb613e4a",
        ],
        # Paulette Senior, NDP candidate in 1999 and 2000 and council candidate in 2003.
        "per_64c4d8aafccc58afab7b7c9f395b5918": [
            "can_231cd8720910586ab75623d319dc7525",
            "can_ce7de351c7d9593c9ee23189f7c489b6",
            "can_b8bbec7dce94558da4d68ce3e5179885",
        ],
        # Worrick Russell, including the 1997 run printed "Russell Worrick".
        "per_879ab85d24c6595f849d3aed56623719": [
            "can_20de29c63af5510d8ed59d31951e0465",
            "can_dde07065effc503088169b9e836c72e9",
            "can_79891fe7920d5d88be3970857fb99226",
        ],
        # André Duclos, MonAvenir 2000 and 2003.
        "per_01d27f754bc75218aa848e00887a9d36": [
            "can_42a0198bb1bb5b53aa91b7b6e032fd23",
            "can_e3dd5923bfce53868bd76e2e25ce6aac",
        ],
        # Nicolò Fortunato, former York councillor, 1997 and 2000.
        "per_2fe800d296a3557586d010943ea11673": [
            "can_76010df7f8295873b55faf7ea227d689",
            "can_5437dbccafbc53d4b7fe9d6f5bce38bd",
        ],
    }
    for person_id, candidacy_ids in careers.items():
        assert confirmed.loc[candidacy_ids, "person_id"].eq(person_id).all(), person_id
        assert people.loc[person_id, "identity_status"] == "active"
    for person_id, canonical in {
        "per_f94551f7f5d15eb591afa5ecdef01b89": "per_879ab85d24c6595f849d3aed56623719",
        "per_26f0cdfdce3b5437b5c0ba6d680019c4": "per_01d27f754bc75218aa848e00887a9d36",
        "per_ca41cb415bd95ffdaf07d6f8b35892a8": "per_d9d8cf88891157b6bdc0fcbe54546451",
        "per_6dc8ecc8a94955c98e70758653a50e44": "per_9074ce6d34475a738c239ee5c8847102",
        "per_37004acfd3bb522f85fbcc6aba56a0c4": "per_64c4d8aafccc58afab7b7c9f395b5918",
    }.items():
        assert people.loc[person_id, "identity_status"] == "deprecated"
        assert people.loc[person_id, "redirect_to_person_id"] == canonical

    # Runs that tie to each other but not to the proposed Person: the travel agent Michael
    # Yorke, who is not the carpenter, and the trustee Mike Thomas.
    new_people = {
        "michael-yorke-north-toronto-trustee-runs": [
            "can_c546f369813d5ec1b86563222cbd9fa8",
            "can_8eaab9d5d7895a13aa9091d45f41b028",
        ],
        "mike-thomas-scarborough-trustee-1997-2000": [
            "can_04ed6458b6405ea5b0a6ded8be0d5ce6",
            "can_e8daf8b5b96050b48617f989a2a46a36",
        ],
    }
    for assertion_id, candidacy_ids in new_people.items():
        person_id = stable_id("per", "curated_identity_assertion", assertion_id)
        assert people.loc[person_id, "identity_status"] == "active", assertion_id
        assert confirmed.loc[candidacy_ids, "person_id"].eq(person_id).all(), assertion_id
    rejected = revised.loc[revised["decision"].eq("rejected")]
    assert sorted(rejected["candidacy_id"]) == sorted(
        new_people["michael-yorke-north-toronto-trustee-runs"]
    )
    assert rejected["target_person_id"].eq("per_2fa2c5b28feb5461bf34c6a202f437ec").all()
    for assertion_id in (
        "mike-armstrong-insurance-agent-1994-2000",
        "david-hutcheon-toronto-councillor-1994-1997",
        "paul-fernandes-east-york-separate-trustee",
        "marlene-ciarrocchi-etobicoke-separate-trustee-runs",
    ):
        assert stable_id("per", "curated_identity_assertion", assertion_id) not in people.index

    # Runs the sources leave open keep their unresolved review: Stephen Thiele's 1994 race in
    # the old City of Toronto and Bert Dandy's 1997 Catholic board race.
    unresolved = active.loc[active["link_status"].eq("unresolved")].set_index("candidacy_id")
    for candidacy_id, person_id in {
        "can_5006059932405a11981de93be680bf82": "per_4426f79f0e8d5e639aa007a3e6712197",
        "can_9e60d7fb88a450128e5ea99a7c030c28": "per_53d7005a342155888e0e566d7245b877",
    }.items():
        assert unresolved.loc[candidacy_id, "person_id"] == person_id
        assert pd.isna(results.loc[candidacy_id, "person_id"])


def test_2026_proposals_are_settled_from_candidate_guides_and_election_pages():
    """The 59 proposals on 2026 Candidacies were reviewed once the results were declared."""

    decisions = read_identity_review_decisions(
        REPO_ROOT / "data" / "reference" / "identity_review_dispositions.csv"
    )
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    reviewed = decisions.loc[decisions["reviewer"].eq("results-2026-proposals-2026-10-30")]
    # John Kladitis's 2026 row was settled later, with his other runs.
    assert len(reviewed) == 58
    assert results.loc[reviewed["candidacy_id"], "election_date"].eq("2026-10-26").all()
    assert reviewed["decision"].value_counts().to_dict() == {"confirmed": 52, "unresolved": 6}
    accepted = reviewed.loc[reviewed["decision"].eq("confirmed")]
    assert accepted["confidence"].eq("high").all()
    assert (
        results.loc[accepted["candidacy_id"], "person_id"].tolist()
        == accepted["target_person_id"].tolist()
    )
    held = reviewed.loc[reviewed["decision"].eq("unresolved"), "candidacy_id"]
    assert set(results.loc[held, "candidate_name"]) == {
        "Peter De Marco",
        "Joseph Osuji",
        "Bob Murphy",
        "Michael Mitchell",
        "Adam Pham",
        "Michael Connor",
    }
    # Bob Murphy's 2026 run joins his 2018-2023 runs on a new Person instead of the 2014 one.
    held_names = results.loc[held, "candidate_name"]
    assert results.loc[held[held_names.ne("Bob Murphy").to_numpy()], "person_id"].isna().all()


def test_star_ward_previews_link_backlog_runs():
    """The Star's ward previews, race stories and riding stories bridge more backlog runs."""

    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    people = pd.read_csv(REPO_ROOT / "data" / "out" / "people.csv", dtype="string").set_index(
        "person_id"
    )
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    decisions = read_identity_review_decisions(
        REPO_ROOT / "data" / "reference" / "identity_review_dispositions.csv"
    )
    revised = decisions.loc[decisions["reviewer"].eq("star-ward-previews-2026-10-30")]
    assert len(revised) == 38
    assert revised.groupby(["decision", "confidence"]).size().to_dict() == {
        ("confirmed", "high"): 37,
        ("unresolved", "medium"): 1,
    }
    accepted = revised.loc[revised["decision"].eq("confirmed")]
    assert (
        results.loc[accepted["candidacy_id"], "person_id"].tolist()
        == accepted["target_person_id"].tolist()
    )
    # Paul Crawford's 2000 TCDSB win stays apart: a second trustee of that name sat on the
    # Durham public board, and no source calls the 2003 candidate the incumbent.
    held = revised.loc[revised["decision"].eq("unresolved"), "candidacy_id"].tolist()
    assert held == ["can_5fbf667080165d6da7d8df6a05ae986e"]
    assert pd.isna(results.loc[held[0], "person_id"])

    active = links.loc[links["valid_to_release"].isna() & links["person_id"].notna()]
    confirmed = active.loc[active["link_status"].eq("confirmed")].set_index("candidacy_id")
    careers = {
        # Chai Kalevar: 1993 National Party, 1994-2000 council runs, later mayoral runs.
        "per_7a6c09e82feb52cdbcd1fa757f7c708d": [
            "can_45feeeb8acb552f6816da3ce7e48846b",
            "can_69d13f11fbcc5d80889e72901424377e",
            "can_a8b8878648c65af2a75fe974865c078c",
            "can_524a3ab594925691a736de3baeb5e24d",
        ],
        # John Doherty: 1993 NDP Davenport, Toronto trustee, 1997 council.
        "per_ed96a950": [
            "can_204ac98a9b6f5b7780b8426d6bcbd7c0",
            "can_f275f1db0b365b798ddf1b8928b8272f",
        ],
        # John Steele: Communist League mayoral runs and the 2003 provincial run.
        "per_d0086333": [
            "can_bd305cd075c9575e8712a875b83681f5",
            "can_2fe5215fa60e5a369a3fea55f59955bc",
            "can_45191a44a24353f682ec876f44cf2a27",
        ],
        # Paul Ferreira: federal, council and provincial runs.
        "per_3ec6d8e6": [
            "can_89b7defefff958269ec338774bb2c680",
            "can_86da1c90cd6751a9ab45ba6015b295f3",
            "can_271502d6684958e3a8c8216768cb7828",
            "can_397c1de19421507db009c27ec598c96a",
        ],
        # Janaki Bala-Krishnan, including the 1997 run printed "Bala-Krishan".
        "per_a95f21e1f60a599d88049ca9742753f0": [
            "can_3488b2de8de75306bc7a9913fb06f440",
            "can_de5e1ee3416c5e6dbcb32903e8ecacbf",
            "can_1b7310a50d0652e4a4f4f95706086bbd",
        ],
        # Al Chumak, printed "Alex Chumak" in 1997.
        "per_956cde49edc25791b2761b3156d46707": [
            "can_6361e989519b56789271681c61fc3cd3",
            "can_dfb362d413b75e4a8cd18b60d0d2d9be",
        ],
        # Bob Smith: 2003 Ward 31, 2006 mayor and 2014 Ward 31.
        "per_17e2dabe": [
            "can_bb6e6f84d844518fa414d8de1a034460",
            "can_98e4815b33ec543795f6d28ed05ad4a1",
            "can_48932970021a5fc68e44c30c115d9899",
        ],
        # Gael Hepworth: 1993 NDP Eglinton-Lawrence and the 1994 York trustee run.
        "per_d2b0366a": [
            "can_b240556453c45d34ac7bd0e1a1d5caf7",
            "can_68527bb2d940554ea9bdac1fbf58a256",
        ],
        # Benson Lau: 1994 council run and 2008 Conservative run.
        "per_8da86474": [
            "can_a5c16b3fe67e5ed0a81a9ed740307f9a",
            "can_5e81472e3c12582cba2343b9a0e8b9c3",
        ],
    }
    for person_prefix, candidacy_ids in careers.items():
        person_ids = confirmed.loc[candidacy_ids, "person_id"]
        assert person_ids.nunique() == 1, person_prefix
        assert person_ids.iloc[0].startswith(person_prefix), person_prefix
        assert people.loc[person_ids.iloc[0], "identity_status"] == "active"
    for person_id, canonical in {
        "per_80acd45c49e95f828a087d11e1e96179": "per_a95f21e1f60a599d88049ca9742753f0",
        "per_750a7d8da88459489fa9127a283d9481": "per_956cde49edc25791b2761b3156d46707",
    }.items():
        assert people.loc[person_id, "identity_status"] == "deprecated"
        assert people.loc[person_id, "redirect_to_person_id"] == canonical

    new_people = {
        "jeffery-zajac-public-board-runs-1994-2000": [
            "can_f15795fa3dd5572e949fd5a550e211e7",
            "can_fd8a391d667755bdaf88693bd5271be8",
            "can_d35ad89d16c25f50a73d14117e343ba3",
        ],
        "gaye-dale-scarborough-trustee-1994-1997": [
            "can_ee92471c86c45b65b2e88eb242a09330",
            "can_e3437f1214255505b5976870e9284535",
        ],
    }
    for assertion_id, candidacy_ids in new_people.items():
        person_id = stable_id("per", "curated_identity_assertion", assertion_id)
        assert people.loc[person_id, "identity_status"] == "active", assertion_id
        assert confirmed.loc[candidacy_ids, "person_id"].eq(person_id).all(), assertion_id
    # Their 2014 namesakes keep their own records.
    for candidacy_id, person_prefix in {
        "can_750bcde5393e5d779e35ca070b47e339": "per_5d02c5ba",
        "can_6649b3f9eb045bf28d1528ccede19d62": "per_336293d6",
    }.items():
        assert confirmed.loc[candidacy_id, "person_id"].startswith(person_prefix)
