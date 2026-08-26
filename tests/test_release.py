"""End-to-end assembly of normalized adapters into public v2 tables."""

from datetime import date

import pandas as pd
import pytest

from toronto_election_results import release as release_module
from toronto_election_results.identity_curations import (
    CandidacyLocator,
    CuratedIdentityAssertion,
)
from toronto_election_results.release import (
    assemble_bootstrapped_release,
    assemble_release,
    write_release,
)


def _adapter() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": ["ec-ge-45", "ec-ge-45"],
            "election_date": ["2025-04-28", "2025-04-28"],
            "election_type": ["general", "general"],
            "election_authority": ["Elections Canada", "Elections Canada"],
            "represented_body": ["House of Commons of Canada", "House of Commons of Canada"],
            "office_type": ["Member of Parliament", "Member of Parliament"],
            "boundary_regime": ["federal-2023-order", "federal-2023-order"],
            "official_district_id": ["35001", "35001"],
            "district_name": ["Example", "Example"],
            "candidate_name_raw": ["Alex Example", "Bailey Sample"],
            "source_candidacy_id": ["candidate-1", "candidate-2"],
            "party_name_raw": ["Example Party", "Independent"],
            "votes": [60, 40],
            "elected": [True, False],
            "incumbent_reported": [True, False],
            "eligible_electors": [200, 200],
            "ballots_cast": [110, 110],
            "turnout_scope": ["federal_district", "federal_district"],
            "outcome_method": ["vote", "vote"],
            "coverage_status": ["complete", "complete"],
            "source_detail": ["official.csv", "official.csv"],
        }
    )


def _void_manifest() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": "city-general",
                "election_date": "2022-10-24",
                "election_type": "general",
                "election_authority": "toronto_city_clerk",
                "represented_body": "Conseil scolaire Viamonde",
                "office_type": "School Board Trustee",
                "boundary_regime": "viamonde-2022",
                "official_district_id": "3",
                "district_name": "Ward 3",
                "outcome_method": "void",
                "coverage_status": "complete",
                "source_detail": "certified declaration",
            }
        ]
    )


def _municipal_adapters() -> list[pd.DataFrame]:
    common = {
        "election_type": "general",
        "election_authority": "Toronto City Clerk",
        "represented_body": "Toronto City Council",
        "office_type": "City Councillor",
        "official_district_id": "1",
        "district_name": "Ward 1",
        "outcome_method": "vote",
        "coverage_status": "complete",
        "source_authority": "City of Toronto",
        "source_resource": "Elections — Official Results",
    }
    prior = pd.DataFrame(
        [
            {
                **common,
                "event_id": "city-2018",
                "election_date": "2018-10-22",
                "boundary_regime": "toronto-25-wards",
                "candidate_name_raw": "Ward, Alex",
                "votes": 60,
                "elected": True,
                "source_detail": "official-2018.xlsx",
            },
            {
                **common,
                "event_id": "city-2018",
                "election_date": "2018-10-22",
                "boundary_regime": "toronto-25-wards",
                "candidate_name_raw": "Prior, Bailey",
                "votes": 40,
                "elected": False,
                "source_detail": "official-2018.xlsx",
            },
        ]
    )
    current = pd.DataFrame(
        [
            {
                **common,
                "event_id": "city-2022",
                "election_date": "2022-10-24",
                "boundary_regime": "toronto-25-wards",
                "candidate_name_raw": "Ward, Alex",
                "votes": 70,
                "elected": True,
                "source_detail": "official-2022.xlsx",
            },
            {
                **common,
                "event_id": "city-2022",
                "election_date": "2022-10-24",
                "boundary_regime": "toronto-25-wards",
                "candidate_name_raw": "Current, Casey",
                "votes": 30,
                "elected": False,
                "source_detail": "official-2022.xlsx",
            },
        ]
    )
    return [prior, current]


def test_release_combines_adapters_and_dimensions_with_canonical_labels():
    release = assemble_release([_adapter()], contest_manifest=_void_manifest())

    assert len(release.election_results) == 2
    assert set(release.election_results["office_type"]) == {"mp"}
    assert set(release.election_results["represented_body"]) == {"canada_house_of_commons"}
    assert len(release.election_events) == 2
    assert len(release.contests) == 2
    assert len(release.electoral_districts) == 2
    assert len(release.parties) == 1


def test_void_manifest_adds_contest_without_fabricating_candidacy():
    release = assemble_release([_adapter()], contest_manifest=_void_manifest())

    void = release.contests[release.contests["outcome_method"] == "void"]
    assert len(void) == 1
    assert void["n_candidates"].isna().all()
    assert not release.election_results["contest_id"].isin(void["contest_id"]).any()


def test_unlinked_people_and_incumbency_remain_unknown():
    release = assemble_release([_adapter()])

    assert release.election_results["person_id"].isna().all()
    assert release.election_results["incumbent"].isna().all()
    assert release.people.empty
    assert release.candidacy_person_links.empty


def test_public_assembly_rejects_name_only_candidacy_identity():
    adapter = _adapter().drop(columns="source_candidacy_id")

    with pytest.raises(ValueError, match="published Candidacies require"):
        assemble_release([adapter])


def test_bootstrap_links_official_incumbent_continuity_and_derives_same_office_status():
    prior = _adapter()
    prior["event_id"] = "ec-ge-44"
    prior["election_date"] = "2021-09-20"
    prior["incumbent_reported"] = [False, False]
    current = _adapter()
    current["candidate_name_raw"] = ["Alex Example", "Casey Current"]
    current["incumbent_reported"] = [True, False]
    current["elected"] = [True, False]

    built = assemble_bootstrapped_release([prior, current], release_id="release-2026-08-20")
    current_rows = built.tables.election_results.query("event_id == 'ec-ge-45'")

    assert current_rows.loc[current_rows.candidate_name_raw == "Alex Example", "incumbent"].item()
    assert pd.isna(
        current_rows.loc[current_rows.candidate_name_raw == "Casey Current", "incumbent"].item()
    )
    alex = built.tables.election_results.query("candidate_name_raw == 'Alex Example'")
    assert alex["person_id"].nunique() == 1
    assert len(built.tables.office_tenures) == 1


def test_bootstrap_applies_explicit_cross_office_identity_curation():
    federal = _adapter().iloc[:1].copy()
    ontario = federal.copy()
    ontario["event_id"] = "on-2025-general"
    ontario["election_date"] = "2025-02-27"
    ontario["election_authority"] = "Elections Ontario"
    ontario["represented_body"] = "Legislative Assembly of Ontario"
    ontario["office_type"] = "Member of Provincial Parliament"
    ontario["boundary_regime"] = "ontario-124-districts"
    ontario["source_candidacy_id"] = "ontario-candidate-1"
    assertion = CuratedIdentityAssertion(
        assertion_id="alex-example-cross-office",
        preferred_name="Alex Example",
        occurrences=(
            CandidacyLocator("ec-ge-45", "canada_house_of_commons", "mp", "Alex Example"),
            CandidacyLocator(
                "on-2025-general",
                "ontario_legislative_assembly",
                "mpp",
                "Alex Example",
            ),
        ),
        evidence_urls=("https://example.gov/official-biography",),
        rationale="An official biography identifies both enumerated candidacies.",
    )

    built = assemble_bootstrapped_release(
        [federal, ontario],
        release_id="release-2026-08-20",
        identity_assertions=(assertion,),
    )

    assert built.tables.election_results["person_id"].notna().all()
    assert built.tables.election_results["person_id"].nunique() == 1


def test_bootstrap_applies_occurrence_level_identity_review_decision():
    prior = _adapter().iloc[:1].copy()
    prior["event_id"] = "ec-ge-44"
    prior["election_date"] = "2021-09-20"
    prior["source_candidacy_id"] = "alex-prior"
    current = prior.copy()
    current["event_id"] = "ec-ge-45"
    current["election_date"] = "2025-04-28"
    current["source_candidacy_id"] = "alex-current"
    current["elected"] = False
    current["incumbent_reported"] = False

    first = assemble_bootstrapped_release([prior, current], release_id="release-2026-08-19")
    proposal = first.tables.candidacy_person_links.query("link_status == 'proposed'").iloc[0]
    decisions = pd.DataFrame(
        {
            "candidacy_id": [proposal["candidacy_id"]],
            "target_person_id": [proposal["person_id"]],
            "decision": ["confirmed"],
            "confidence": ["high"],
            "rationale": ["The official profile enumerates both elections."],
            "evidence_urls": ["https://example.test/official-profile"],
            "reviewer": ["reviewer-a"],
        }
    )

    reviewed = assemble_bootstrapped_release(
        [prior, current],
        release_id="release-2026-08-20",
        existing_people=first.tables.people,
        existing_candidacy_person_links=first.tables.candidacy_person_links,
        identity_review_decisions=decisions,
    )

    current_result = reviewed.tables.election_results.query("event_id == 'ec-ge-45'").iloc[0]
    assert current_result["person_id"] == proposal["person_id"]
    active = reviewed.tables.candidacy_person_links.loc[
        reviewed.tables.candidacy_person_links["valid_to_release"].isna()
        & reviewed.tables.candidacy_person_links["candidacy_id"].eq(proposal["candidacy_id"])
    ]
    assert active["link_status"].tolist() == ["confirmed"]


def test_bootstrap_uses_complete_city_roster_to_confirm_identity_and_incumbency():
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

    built = assemble_bootstrapped_release(
        _municipal_adapters(),
        release_id="release-2026-08-20",
        municipal_composition=composition,
    )
    current = built.tables.election_results.query("event_id == 'city-2022'").set_index(
        "candidate_name_raw"
    )

    assert current.loc["Ward, Alex", "incumbent"]
    assert not current.loc["Current, Casey", "incumbent"]
    assert (
        current.loc["Ward, Alex", "person_id"]
        == built.tables.election_results.query(
            "event_id == 'city-2018' and candidate_name_raw == 'Ward, Alex'"
        )["person_id"].item()
    )
    assert current.loc["Ward, Alex", "incumbent_office_tenure_id"] in set(
        built.tables.office_tenures["office_tenure_id"]
    )


def test_published_registry_and_tenure_rows_have_deterministic_order():
    built = assemble_bootstrapped_release([_adapter()], release_id="release-2026-08-20")

    assert built.tables.people["person_id"].tolist() == sorted(
        built.tables.people["person_id"].tolist()
    )
    assert built.tables.office_tenures["office_tenure_id"].tolist() == sorted(
        built.tables.office_tenures["office_tenure_id"].tolist()
    )
    links = built.tables.candidacy_person_links
    expected = links.sort_values(
        ["candidacy_id", "valid_from_release", "link_status", "person_id"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(links, expected)


def test_write_release_publishes_every_table_without_leaving_staging_files(tmp_path):
    release = assemble_release([_adapter()])

    written = write_release(release, tmp_path / "out")

    assert len(written) == 24
    assert all(path.is_file() for path in written)
    assert not list(tmp_path.glob(".out.stage-*"))


def test_release_normalizes_mixed_office_tenure_dates_before_parquet_write(tmp_path):
    people = pd.DataFrame(
        {
            "person_id": ["per_example"],
            "preferred_name": ["Alex Example"],
            "identity_status": ["active"],
            "redirect_to_person_id": [pd.NA],
            "created_release": ["release-2026-08-20"],
        }
    )
    tenures = pd.DataFrame(
        {
            "office_tenure_id": ["ten_native", "ten_iso"],
            "person_id": ["per_example", "per_example"],
            "represented_body": ["canada_house_of_commons"] * 2,
            "office_type": ["mp"] * 2,
            "district_id": [pd.NA, pd.NA],
            "started_on": [date(2021, 9, 20), "2025-01-01"],
            "started_on_precision": ["election_date", "exact"],
            "ended_on": [date(2025, 3, 22), "2026-01-01"],
            "ended_on_precision": ["at_or_after_reference"] * 2,
            "entry_method": ["election"] * 2,
            "source_authority": ["Elections Canada"] * 2,
            "source_detail": ["official source"] * 2,
        }
    )

    release = assemble_release([_adapter()], people=people, office_tenures=tenures)
    written = write_release(release, tmp_path / "out")

    assert len(written) == 24
    assert {type(value) for value in release.office_tenures["started_on"]} == {date}


def test_write_release_serialization_failure_leaves_existing_release_untouched(
    tmp_path, monkeypatch
):
    release = assemble_release([_adapter()])
    destination = tmp_path / "out"
    destination.mkdir()
    existing = destination / "election_results.csv"
    existing.write_text("previous release\n")

    def fail_to_parquet(*args, **kwargs):
        raise OSError("simulated serialization failure")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fail_to_parquet)

    with pytest.raises(OSError, match="simulated serialization failure"):
        write_release(release, destination)

    assert existing.read_text() == "previous release\n"
    assert sorted(path.name for path in destination.iterdir()) == ["election_results.csv"]
    assert not list(tmp_path.glob(".out.stage-*"))


def test_write_release_promotion_failure_rolls_back_every_replaced_artifact(tmp_path, monkeypatch):
    destination = tmp_path / "out"
    write_release(assemble_release([_adapter()]), destination)
    previous = {path.name: path.read_bytes() for path in destination.iterdir()}
    changed = assemble_release([_adapter()])
    changed.election_results.loc[0, "candidate_name"] = "Changed display name"

    real_replace = release_module.os.replace
    failed = False

    def fail_during_promotion(source, target):
        nonlocal failed
        source_path = release_module.Path(source)
        if (
            not failed
            and source_path.parent.name == "payload"
            and source_path.name == "contests.csv"
        ):
            failed = True
            raise OSError("simulated promotion failure")
        return real_replace(source, target)

    monkeypatch.setattr(release_module.os, "replace", fail_during_promotion)

    with pytest.raises(RuntimeError, match="release promotion failed"):
        write_release(changed, destination)

    assert {path.name: path.read_bytes() for path in destination.iterdir()} == previous
    assert not list(tmp_path.glob(".out.stage-*"))
