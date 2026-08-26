"""Conservative bootstrap of the versioned Person registry."""

import json

import pandas as pd
import pytest

from toronto_election_results.identity import attach_confirmed_people, validate_identity_tables
from toronto_election_results.identity_review import bootstrap_identity_review


def _row(
    candidacy_id: str,
    date: str,
    name: str,
    *,
    elected: object = False,
    incumbent: object = False,
    body: str = "toronto_city_council",
    office: str = "councillor",
    contest: str | None = None,
    source: object = "official-results.csv",
) -> dict[str, object]:
    return {
        "candidacy_id": candidacy_id,
        "contest_id": contest or f"con_{candidacy_id}",
        "event_id": f"evt_{date}",
        "election_date": date,
        "represented_body": body,
        "office_type": office,
        "candidate_name_raw": name,
        "elected": elected,
        "incumbent_reported": incumbent,
        "source_authority": "Toronto City Clerk",
        "source_resource": "official-result-file",
        "source_detail": source,
    }


def test_official_incumbent_continuity_reuses_one_person_with_evidence():
    candidacies = pd.DataFrame(
        [
            _row("can_2014_alex", "2014-10-27", "Alex Example", elected=True),
            _row(
                "can_2018_alex",
                "2018-10-22",
                " alex   EXAMPLE ",
                elected=True,
                incumbent=True,
                source="official-2018.csv",
            ),
            _row(
                "can_2022_alex",
                "2022-10-24",
                "Alex Example",
                incumbent=True,
                source="official-2022.csv",
            ),
        ]
    )

    review = bootstrap_identity_review(candidacies, release_id="2026-08-20")
    confirmed = review.candidacy_person_links.query("link_status == 'confirmed'")

    assert len(review.people) == 1
    assert confirmed["person_id"].nunique() == 1
    assert (
        confirmed.set_index("candidacy_id").loc["can_2018_alex", "method"]
        == "official_incumbent_continuity"
    )
    evidence = json.loads(confirmed.set_index("candidacy_id").loc["can_2018_alex", "evidence"])
    assert evidence["current"]["source_detail"] == "official-2018.csv"
    assert evidence["prior"]["source_detail"] == "official-results.csv"
    assert review.review_flags.empty
    validate_identity_tables(review.people, review.candidacy_person_links)


def test_exact_name_without_official_continuity_is_only_proposed():
    candidacies = pd.DataFrame(
        [
            _row("can_first", "2018-10-22", "Bailey Sample", elected=False),
            _row("can_second", "2022-10-24", "Bailey Sample", elected=False),
        ]
    )

    review = bootstrap_identity_review(candidacies, release_id="v2")
    links = review.candidacy_person_links
    confirmed = links.query("link_status == 'confirmed'")
    proposal = links.query("link_status == 'proposed'")

    assert len(review.people) == 1
    assert confirmed["candidacy_id"].tolist() == ["can_first"]
    assert proposal["candidacy_id"].tolist() == ["can_second"]
    assert proposal["method"].tolist() == ["exact_normalized_name_review"]
    assert (
        proposal["person_id"].item()
        == confirmed.set_index("candidacy_id").loc["can_first", "person_id"]
    )
    attached = attach_confirmed_people(candidacies, review.people, links)
    assert pd.isna(attached.set_index("candidacy_id").loc["can_second", "person_id"])


def test_person_id_uses_source_candidacy_anchor_not_display_name():
    first = pd.DataFrame([_row("can_stable_anchor", "2022-10-24", "First Display")])
    renamed = first.copy()
    renamed["candidate_name_raw"] = "Completely Different Display"

    first_id = bootstrap_identity_review(first, release_id="v2").people["person_id"].item()
    renamed_id = bootstrap_identity_review(renamed, release_id="v2").people["person_id"].item()

    assert first_id == renamed_id
    assert first_id.startswith("per_")
    assert "first" not in first_id


def test_two_prior_elected_people_with_same_exact_name_block_auto_link():
    candidacies = pd.DataFrame(
        [
            _row("can_old_east", "2018-10-22", "Chris Lee", elected=True),
            _row("can_old_west", "2018-10-22", "Chris Lee", elected=True),
            _row(
                "can_current",
                "2022-10-24",
                "Chris Lee",
                elected=True,
                incumbent=True,
            ),
        ]
    )

    review = bootstrap_identity_review(candidacies, release_id="v2")
    confirmed = review.candidacy_person_links.query("link_status == 'confirmed'")

    assert confirmed["candidacy_id"].tolist() == ["can_old_east"]
    assert "ambiguous_prior_elected_identity" in set(review.review_flags["flag_type"])
    unresolved = review.candidacy_person_links.query("link_status == 'unresolved'")
    assert unresolved["candidacy_id"].tolist() == ["can_current"]
    assert unresolved["person_id"].isna().all()
    attached = attach_confirmed_people(candidacies, review.people, review.candidacy_person_links)
    attached = attached.set_index("candidacy_id")
    assert pd.isna(attached.loc["can_old_west", "person_id"])
    assert pd.isna(attached.loc["can_current", "person_id"])


def test_later_repeat_root_publishes_only_after_official_continuity_confirms_it():
    candidacies = pd.DataFrame(
        [
            _row("can_2014", "2014-10-27", "Casey Example", elected=False),
            _row("can_2018", "2018-10-22", "Casey Example", elected=True),
            _row(
                "can_2022",
                "2022-10-24",
                "Casey Example",
                elected=True,
                incumbent=True,
            ),
        ]
    )

    review = bootstrap_identity_review(candidacies, release_id="v2")
    confirmed = review.candidacy_person_links.query("link_status == 'confirmed'").set_index(
        "candidacy_id"
    )

    assert len(review.people) == 1
    assert confirmed.loc["can_2018", "person_id"] == confirmed.loc["can_2022", "person_id"]
    assert "can_2014" not in confirmed.index
    proposed = review.candidacy_person_links.query(
        "candidacy_id == 'can_2014' and link_status == 'proposed'"
    )
    assert proposed["person_id"].item() == confirmed.loc["can_2018", "person_id"]


def test_one_prior_person_cannot_auto_link_to_two_simultaneous_candidacies():
    candidacies = pd.DataFrame(
        [
            _row("can_old", "2018-10-22", "Dana Same", elected=True),
            _row(
                "can_current_a",
                "2022-10-24",
                "Dana Same",
                incumbent=True,
                contest="con_a",
            ),
            _row(
                "can_current_b",
                "2022-10-24",
                "Dana Same",
                incumbent=True,
                contest="con_b",
            ),
        ]
    )

    review = bootstrap_identity_review(candidacies, release_id="v2")

    assert review.candidacy_person_links.query("link_status == 'confirmed'")[
        "candidacy_id"
    ].tolist() == ["can_old"]
    conflicts = review.review_flags.query("flag_type == 'simultaneous_candidacy_identity_conflict'")
    assert set(conflicts["candidacy_id"]) == {"can_current_a", "can_current_b"}


def test_cross_body_and_office_exact_name_is_globally_proposed_but_not_confirmed():
    candidacies = pd.DataFrame(
        [
            _row("can_councillor", "2018-10-22", "Erin Example", elected=True),
            _row(
                "can_mayor",
                "2022-10-24",
                "Erin Example",
                incumbent=True,
                body="ontario_legislative_assembly",
                office="mpp",
            ),
        ]
    )

    review = bootstrap_identity_review(candidacies, release_id="v2")

    confirmed = review.candidacy_person_links.query("link_status == 'confirmed'")
    proposed = review.candidacy_person_links.query("link_status == 'proposed'")
    assert confirmed["candidacy_id"].tolist() == ["can_councillor"]
    assert proposed["candidacy_id"].tolist() == ["can_mayor"]
    assert proposed["person_id"].item() == confirmed["person_id"].item()
    attached = attach_confirmed_people(candidacies, review.people, review.candidacy_person_links)
    assert pd.isna(attached.set_index("candidacy_id").loc["can_mayor", "person_id"])
    mayor_flag = review.review_flags.query("candidacy_id == 'can_mayor'")
    assert mayor_flag["flag_type"].tolist() == ["incumbent_without_prior_elected_match"]


def test_missing_source_detail_blocks_otherwise_eligible_auto_link():
    candidacies = pd.DataFrame(
        [
            _row("can_old", "2018-10-22", "Fran Example", elected=True, source=pd.NA),
            _row(
                "can_new",
                "2022-10-24",
                "Fran Example",
                incumbent=True,
                source=pd.NA,
            ),
        ]
    )
    candidacies["source_resource"] = pd.NA

    review = bootstrap_identity_review(candidacies, release_id="v2")

    assert review.candidacy_person_links.query("link_status == 'confirmed'")[
        "candidacy_id"
    ].tolist() == ["can_old"]
    assert review.candidacy_person_links.query("link_status == 'proposed'")[
        "candidacy_id"
    ].tolist() == ["can_new"]
    assert "missing_official_source_evidence" in set(review.review_flags["flag_type"])


def test_registry_rows_are_versioned_and_duplicate_candidacy_ids_are_rejected():
    candidacies = pd.DataFrame([_row("can_one", "2022-10-24", "Gray Example")])
    review = bootstrap_identity_review(candidacies, release_id="release-2026-08-20")

    assert review.people["created_release"].tolist() == ["release-2026-08-20"]
    assert review.candidacy_person_links["valid_from_release"].eq("release-2026-08-20").all()
    assert review.candidacy_person_links["valid_to_release"].isna().all()

    duplicated = pd.concat([candidacies, candidacies], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate candidacy_id"):
        bootstrap_identity_review(duplicated, release_id="v2")
