"""Audited Toronto endorsement-panel curations."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.endorsement_curations import (
    ENDORSEMENT_ASSERTIONS_FILENAME,
    ENDORSEMENT_COVERAGE_FILENAME,
    ENDORSER_PANEL_FILENAME,
    REFERENCE,
    build_default_endorsement_inputs,
)
from toronto_election_results.endorsements import assemble_endorsement_tables


def _fixture_reference_dir(tmp_path: Path) -> Path:
    reference_dir = tmp_path / "reference"
    reference_dir.mkdir()
    for filename in (
        ENDORSER_PANEL_FILENAME,
        ENDORSEMENT_ASSERTIONS_FILENAME,
        ENDORSEMENT_COVERAGE_FILENAME,
    ):
        shutil.copyfile(REFERENCE / filename, reference_dir / filename)
    return reference_dir


def _add_contest(
    results: list[dict[str, str]],
    contests: list[dict[str, str]],
    *,
    contest_id: str,
    candidacy_id: str,
    election_date: str,
    office_type: str,
    official_district_id: str,
    candidate_name: str,
    event_id: str | None = None,
) -> None:
    contests.append(
        {
            "contest_id": contest_id,
            "event_id": event_id or f"evt_fixture_{contest_id}",
            "represented_body": "toronto_city_council",
            "office_type": office_type,
        }
    )
    results.append(
        {
            "candidacy_id": candidacy_id,
            "contest_id": contest_id,
            "election_date": election_date,
            "represented_body": "toronto_city_council",
            "office_type": office_type,
            "official_district_id": official_district_id,
            "candidate_name": candidate_name,
        }
    )


def _dimensions(reference_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    curations = pd.read_csv(
        reference_dir / ENDORSEMENT_ASSERTIONS_FILENAME,
        dtype="string",
    )
    coverage_curations = pd.read_csv(
        reference_dir / ENDORSEMENT_COVERAGE_FILENAME,
        dtype="string",
    )
    event_ids = {
        (str(row.election_date), str(row.office_type)): str(row.expected_event_id)
        for row in coverage_curations.itertuples(index=False)
    }
    contest_rows: dict[str, dict[str, str]] = {}
    result_rows: dict[str, dict[str, str]] = {}
    for row in curations.itertuples(index=False):
        contest_rows[str(row.expected_contest_id)] = {
            "contest_id": str(row.expected_contest_id),
            "event_id": event_ids.get(
                (str(row.election_date), str(row.office_type)),
                f"evt_fixture_{row.expected_contest_id}",
            ),
            "represented_body": "toronto_city_council",
            "office_type": str(row.office_type),
        }
        if row.review_state == "confirmed":
            result_rows[str(row.expected_candidacy_id)] = {
                "candidacy_id": str(row.expected_candidacy_id),
                "contest_id": str(row.expected_contest_id),
                "election_date": str(row.election_date),
                "represented_body": "toronto_city_council",
                "office_type": str(row.office_type),
                "official_district_id": str(row.official_district_id),
                "candidate_name": str(row.expected_candidate_name),
            }

    # The unresolved Cynthia Lai assertion still needs its real Contest to be in
    # the dimensions, but intentionally has no Candidacy of its own.
    result_rows["can_fixture_2022_w23_other"] = {
        "candidacy_id": "can_fixture_2022_w23_other",
        "contest_id": "con_c686b3ad3bd059d78db8cc44229817a0",
        "election_date": "2022-10-24",
        "represented_body": "toronto_city_council",
        "office_type": "councillor",
        "official_district_id": "ward-23",
        "candidate_name": "Another Ward 23 Candidate",
    }

    results = list(result_rows.values())
    contests = list(contest_rows.values())
    covered_dimensions = {
        (
            str(contest["event_id"]),
            str(result["office_type"]),
            str(result["official_district_id"]),
        )
        for contest in contests
        for result in results
        if contest["contest_id"] == result["contest_id"]
    }
    for row in coverage_curations.itertuples(index=False):
        if row.curation_key == "star_2022_council_complete_editorial_set":
            continue
        district = str(row.official_district_id) if pd.notna(row.official_district_id) else "city"
        key = (str(row.expected_event_id), str(row.office_type), district)
        if key in covered_dimensions:
            continue
        _add_contest(
            results,
            contests,
            contest_id=f"con_fixture_coverage_{row.curation_key}",
            candidacy_id=f"can_fixture_coverage_{row.curation_key}",
            election_date=str(row.election_date),
            office_type=str(row.office_type),
            official_district_id=district,
            candidate_name="Coverage Fixture Candidate",
            event_id=str(row.expected_event_id),
        )
        covered_dimensions.add(key)
    _add_contest(
        results,
        contests,
        contest_id="con_a1f3f1e6009c53c7a9cbb88e7e2346c0",
        candidacy_id="can_fixture_2022_w02",
        election_date="2022-10-24",
        office_type="councillor",
        official_district_id="ward-2",
        candidate_name="2022 Ward 2 Candidate",
        event_id="evt_a52ef78967f05336bdb5d591fd50f122",
    )
    _add_contest(
        results,
        contests,
        contest_id="con_c637e2ad153c516eb79ab5edb84161f8",
        candidacy_id="can_fixture_2022_w21",
        election_date="2022-10-24",
        office_type="councillor",
        official_district_id="ward-21",
        candidate_name="2022 Ward 21 Candidate",
        event_id="evt_a52ef78967f05336bdb5d591fd50f122",
    )
    _add_contest(
        results,
        contests,
        contest_id="con_fixture_2010_w39",
        candidacy_id="can_fixture_2010_w39",
        election_date="2010-10-25",
        office_type="councillor",
        official_district_id="ward-39",
        candidate_name="Ward 39 Candidate",
    )
    _add_contest(
        results,
        contests,
        contest_id="con_fixture_2014_w01",
        candidacy_id="can_fixture_2014_w01",
        election_date="2014-10-27",
        office_type="councillor",
        official_district_id="ward-1",
        candidate_name="2014 Ward Candidate",
        event_id="evt_54673fd104ab5ef08eb865e162ac040c",
    )
    _add_contest(
        results,
        contests,
        contest_id="con_fixture_2019_w01",
        candidacy_id="can_fixture_2019_w01",
        election_date="2019-01-01",
        office_type="councillor",
        official_district_id="ward-1",
        candidate_name="2019 Ward Candidate",
    )
    _add_contest(
        results,
        contests,
        contest_id="con_fixture_2026_mayor",
        candidacy_id="can_fixture_2026_mayor",
        election_date="2026-10-26",
        office_type="mayor",
        official_district_id="city",
        candidate_name="2026 Mayor Candidate",
    )
    _add_contest(
        results,
        contests,
        contest_id="con_fixture_2026_w01",
        candidacy_id="can_fixture_2026_w01",
        election_date="2026-10-26",
        office_type="councillor",
        official_district_id="ward-1",
        candidate_name="2026 Ward Candidate",
    )

    people = pd.DataFrame(
        [
            {
                "person_id": "per_ad293f1387af572cad45897886519bb6",
                "preferred_name": "David Miller",
                "identity_status": "active",
            },
            {
                "person_id": "per_a9eb70da799659daaa285f92cfed1674",
                "preferred_name": "John Tory",
                "identity_status": "active",
            },
            {
                "person_id": "per_a4291ca7539b53e2acc1c4f108bc73e6",
                "preferred_name": "Olivia Chow",
                "identity_status": "active",
            },
        ]
    )
    return pd.DataFrame(results), pd.DataFrame(contests), people


def _build(tmp_path: Path):
    reference_dir = _fixture_reference_dir(tmp_path)
    election_results, contests, people = _dimensions(reference_dir)
    inputs = build_default_endorsement_inputs(
        election_results,
        contests,
        people,
        reference_dir=reference_dir,
    )
    return inputs, election_results, contests, people, reference_dir


def _endorser_id(inputs, name: str) -> str:
    return inputs.endorsers.loc[inputs.endorsers.canonical_name.eq(name), "endorser_id"].item()


def test_default_inputs_publish_only_the_322_cleared_positive_facts(tmp_path):
    inputs, election_results, contests, people, _ = _build(tmp_path)

    assert len(inputs.endorsers) == 10
    assert inputs.endorsers["is_panel_endorser"].sum() == 9
    assert inputs.endorsers["mayor_applicable"].all()
    assert inputs.endorsers["councillor_applicable"].sum() == 9
    assert set(inputs.assertions["review_state"].value_counts().to_dict().items()) == {
        ("confirmed", 322),
        ("unresolved", 1),
    }

    assembled = assemble_endorsement_tables(
        candidacies=election_results,
        contests=contests,
        people=people,
        endorsers=inputs.endorsers,
        assertions=inputs.assertions,
        coverage=inputs.coverage,
    )
    assert len(assembled.endorsements) == 322
    assert assembled.endorsements["endorsement_id"].str.startswith("end_").all()

    unresolved = inputs.assertions.query("review_state == 'unresolved'").iloc[0]
    assert unresolved["asserted_candidate_name"] == "Cynthia Lai"
    assert unresolved["curation_key"] == "tory_2022_w23_lai_unresolved"
    assert pd.isna(unresolved["candidacy_id"])


def test_verified_miller_search_batches_are_coverage_curations_not_historical_defaults(tmp_path):
    inputs, _, _, _, _ = _build(tmp_path)
    miller_id = _endorser_id(inputs, "David Miller")

    for contest_id in (
        "con_b4c70c0c6f465c4091dce97cbbd286b3",
        "con_17c2e1a7404c5641823443ca7a6dcc10",
        "con_d6f7b1cb92f959ab9408dbb936bcf2ff",
    ):
        coverage = inputs.coverage.loc[
            inputs.coverage["endorser_id"].eq(miller_id)
            & inputs.coverage["contest_id"].eq(contest_id)
        ]
        assert coverage["coverage_state"].item() == "partially_searched"
        assert coverage["coverage_basis"].item() == (
            "audited limited historical search; no complete slate source recovered"
        )


def test_verified_miller_assertions_preserve_the_independently_audited_sources(tmp_path):
    inputs, _, _, _, _ = _build(tmp_path)
    miller_id = _endorser_id(inputs, "David Miller")
    assertions = inputs.assertions.loc[inputs.assertions["endorser_id"].eq(miller_id)]

    by_curation = assertions.set_index("curation_key")
    assert set(by_curation.index) == {
        "miller_2006_w14_perks",
        "miller_2006_w38_debaeremaeker",
        "miller_2010_mayor_pantalone",
        "miller_2010_w18_beaulieu",
    }
    assert by_curation.loc["miller_2006_w14_perks", "candidacy_id"] == (
        "can_8beb4a28087f5a58b667f68fdc297a43"
    )
    assert by_curation.loc["miller_2006_w38_debaeremaeker", "candidacy_id"] == (
        "can_3f84dacf17b85bdbad830258c4a975a8"
    )
    assert by_curation.loc["miller_2010_w18_beaulieu", "candidacy_id"] == (
        "can_7c4e23514e3b546e8fc7ea161c40a4f1"
    )
    assert by_curation.loc["miller_2006_w14_perks", "source_url"] == (
        "https://philippinereporter.com/index.php/2006/11/01/"
        "rowena-santos-talks-to-the-philippine-reporter/"
    )
    assert by_curation.loc["miller_2006_w14_perks", "secondary_source_url"] == (
        "https://www.yorku.ca/yfile/2006/11/14/york-university-charts-a-new-course/"
    )
    assert by_curation.loc["miller_2006_w38_debaeremaeker", "source_url"] == (
        "https://philippinereporter.com/?p=3703"
    )
    assert pd.isna(by_curation.loc["miller_2006_w38_debaeremaeker", "announcement_date"])
    assert by_curation.loc["miller_2010_w18_beaulieu", "source_url"] == (
        "https://spacing.ca/toronto/2010/10/19/election-council-turnover-ward-18/"
    )
    assert by_curation.loc["miller_2010_w18_beaulieu", "secondary_source_url"] == (
        "https://xtramagazine.com/power/social-services-are-in-danger-kevin-beaulieu-8909"
    )


def test_authenticated_sun_2018_editorial_imports_all_27_positive_choices(tmp_path):
    inputs, _, _, _, _ = _build(tmp_path)
    sun_id = _endorser_id(inputs, "Toronto Sun Editorial Board")
    assertions = inputs.assertions.loc[
        inputs.assertions["endorser_id"].eq(sun_id)
        & inputs.assertions["source_type"].eq("publisher_editorial_authenticated_archive")
    ]

    assert len(assertions) == 27
    assert assertions["contest_id"].nunique() == 25
    assert set(
        assertions.loc[
            assertions["contest_id"].eq("con_6a1f4d7470675d869b3b11aede0812f2"),
            "asserted_candidate_name",
        ]
    ) == {"Jon Burnside", "Jaye Robinson"}
    assert set(
        assertions.loc[
            assertions["contest_id"].eq("con_6fd864aec40c5bbc9f3eb32d2e9e4379"),
            "asserted_candidate_name",
        ]
    ) == {"Michelle Holland-Berardinetti", "Gary Crawford"}
    assert set(assertions["announcement_date"]) == {"2018-10-20"}
    assert set(assertions["endorsement_kind"]) == {"editorial_choice"}
    assert set(assertions["source_type"]) == {"publisher_editorial_authenticated_archive"}
    assert set(assertions["source_url"]) == {"https://www.proquest.com/docview/2125467176"}
    assert set(assertions["secondary_source_url"]) == {
        "https://torontosun.com/news/local-news/toronto-sun-endorsements-for-city-council"
    }


def test_authenticated_star_packages_import_all_151_validated_choices(tmp_path):
    inputs, _, _, _, _ = _build(tmp_path)
    star_id = _endorser_id(inputs, "Toronto Star Editorial Board")
    assertions = inputs.assertions.loc[
        inputs.assertions["endorser_id"].eq(star_id)
        & inputs.assertions["source_type"].eq("publisher_editorial_authenticated_archive")
    ]

    assert len(assertions) == 151
    keys = assertions["curation_key"]
    assert keys.str.startswith("star_2003_w").sum() == 40
    assert keys.str.startswith("star_2006_w").sum() == 41
    assert keys.eq("star_2006_mayor_miller").sum() == 1
    assert keys.str.startswith("star_2014_w").sum() == 44
    assert keys.str.startswith("star_2018_w").sum() == 25
    assert set(assertions["review_state"]) == {"confirmed"}
    assert set(assertions["date_precision"]) == {"day"}


def test_verified_globe_facts_import_without_expanding_the_frozen_panel(tmp_path):
    inputs, _, _, _, _ = _build(tmp_path)
    globe = inputs.endorsers.loc[
        inputs.endorsers["canonical_name"].eq("The Globe and Mail Editorial Board")
    ].iloc[0]
    assertions = inputs.assertions.loc[
        inputs.assertions["endorser_id"].eq(globe["endorser_id"])
    ].sort_values("announcement_date")

    assert not bool(globe["is_panel_endorser"])
    assert bool(globe["mayor_applicable"])
    assert not bool(globe["councillor_applicable"])
    assert list(assertions["candidacy_id"]) == [
        "can_1179f79bea135e8d82289930ed974496",
        "can_3d13fbd9fab452a5b347fb048574b6c4",
        "can_b3ecaef663ba56adbab70efbcb5004da",
    ]
    assert set(assertions["review_state"]) == {"confirmed"}
    assert set(assertions["endorsement_kind"]) == {"editorial_choice"}
    assert set(assertions["source_type"]) == {"publisher_editorial_authenticated_archive"}
    assert inputs.coverage["endorser_id"].ne(globe["endorser_id"]).all()


def test_matt_elliott_audit_recovers_the_22_star_2022_council_choices(tmp_path):
    inputs, election_results, _, _, _ = _build(tmp_path)
    star_id = _endorser_id(inputs, "Toronto Star Editorial Board")
    assertions = inputs.assertions.merge(
        election_results[["candidacy_id", "election_date", "office_type", "official_district_id"]],
        on="candidacy_id",
        how="left",
    )
    star_council = assertions.loc[
        assertions["endorser_id"].eq(star_id)
        & assertions["election_date"].eq("2022-10-24")
        & assertions["office_type"].eq("councillor")
    ]

    assert len(star_council) == 22
    assert set(star_council["official_district_id"]) == {
        *(f"ward-{ward}" for ward in range(1, 26)),
    } - {"ward-2", "ward-16", "ward-21"}
    assert set(star_council["endorsement_kind"]) == {"editorial_choice"}
    assert set(star_council["source_type"]) == {"publisher_editorial_with_archived_copy"}
    assert set(star_council["announcement_date"]) == {
        "2022-10-19",
        "2022-10-20",
        "2022-10-21",
    }

    star_coverage = inputs.coverage.loc[
        inputs.coverage["endorser_id"].eq(star_id)
        & inputs.coverage["contest_id"].isin(
            election_results.loc[
                election_results["election_date"].eq("2022-10-24")
                & election_results["office_type"].eq("councillor")
                & election_results["official_district_id"].str.startswith("ward-"),
                "contest_id",
            ]
        )
    ]
    assert len(star_coverage) == 25
    assert set(star_coverage["coverage_state"]) == {"comprehensive_source_found"}


def test_editorial_coverage_curations_preserve_prior_partial_search_decisions(tmp_path):
    inputs, _, _, _, reference_dir = _build(tmp_path)
    curations = pd.read_csv(reference_dir / ENDORSEMENT_COVERAGE_FILENAME, dtype="string")
    editorial = curations.loc[
        curations["verification_report_path"].eq(
            "docs/research/endorsement-coverage-terra-verification-editorial.md"
        )
    ]
    assert len(editorial) == 15
    assert set(editorial["search_certificate_path"]) == {
        "docs/research/endorsement-coverage-luna-editorial-2003-2025.md"
    }
    assert set(editorial["coverage_state"]) == {"partially_searched"}

    sun_id = _endorser_id(inputs, "Toronto Sun Editorial Board")
    sun_2018_council = inputs.coverage.loc[
        inputs.coverage["endorser_id"].eq(sun_id)
        & inputs.coverage["contest_id"].eq("con_922d425132ad5243b459c0ca40a6dcd9")
    ]
    assert sun_2018_council["coverage_state"].item() == "comprehensive_source_found"
    assert sun_2018_council["coverage_basis"].item() == (
        "Authenticated publisher editorial provides at least one positive choice in every "
        "Ward 1-25, including two choices in Wards 15 and 20."
    )


def test_verified_organizational_wave_imports_only_the_18_cleared_facts(tmp_path):
    inputs, election_results, _, _, _ = _build(tmp_path)
    endorser_ids = {
        name: _endorser_id(inputs, name)
        for name in ("Progress Toronto", "Amalgamated Transit Union Local 113")
    }
    assertions = inputs.assertions.merge(
        election_results[["candidacy_id", "election_date"]],
        on="candidacy_id",
        how="left",
    )

    progress = assertions.loc[assertions["endorser_id"].eq(endorser_ids["Progress Toronto"])]
    assert set(progress.loc[progress["election_date"].eq("2018-10-22"), "candidacy_id"]) == {
        "can_a4e55da62ed2509cb497ad0bfd65c11f"
    }
    assert set(progress.loc[progress["election_date"].eq("2021-01-15"), "candidacy_id"]) == {
        "can_f9f7d971b99c52cf9a48edf7b1dd38ba"
    }

    atu = assertions.loc[
        assertions["endorser_id"].eq(endorser_ids["Amalgamated Transit Union Local 113"])
        & assertions["election_date"].eq("2018-10-22")
    ]
    assert len(atu) == 16
    assert set(atu["announcement_date"]) == {"2018-10-01"}
    assert set(atu["date_precision"]) == {"month"}
    assert set(atu["source_type"]) == {"first_party_slate"}
    assert set(atu["source_url"]) == {
        "https://wemovetoronto.ca/wp-content/uploads/2018/10/ATU-Local-113_Endorsed-Candidates.pdf"
    }
    cupe = assertions.loc[
        assertions["endorser_id"].eq(_endorser_id(inputs, "CUPE Ontario"))
        & assertions["curation_key"].eq("cupe_2025_w25_shan")
    ].iloc[0]
    assert cupe["contest_id"] == "con_c8883aeeac29529eada91aebc451242b"
    assert cupe["candidacy_id"] == "can_2a0745629be0507080db6d72f4a6719b"
    assert cupe["announcement_date"] == "2025-09-15"
    assert cupe["date_precision"] == "day"
    assert cupe["source_type"] == "first_party_campaign"


def test_organizational_coverage_preserves_audited_contest_splits(tmp_path):
    inputs, _, _, _, reference_dir = _build(tmp_path)
    curations = pd.read_csv(reference_dir / ENDORSEMENT_COVERAGE_FILENAME, dtype="string")
    organizational = curations.loc[
        curations["verification_report_path"].eq(
            "docs/research/endorsement-coverage-terra-verification-organizations.md"
        )
    ]
    assert len(organizational) == 99
    assert (
        curations.loc[
            curations["curation_key"].eq("cupe_2025_w25_shan_choice"),
            "verification_report_path",
        ].item()
        == "docs/research/endorsement-coverage-terra-verification-hold-recovery.md"
    )

    progress_id = _endorser_id(inputs, "Progress Toronto")
    atu_id = _endorser_id(inputs, "Amalgamated Transit Union Local 113")
    cupe_id = _endorser_id(inputs, "CUPE Ontario")
    assert (
        inputs.coverage.loc[
            inputs.coverage["endorser_id"].eq(progress_id)
            & inputs.coverage["contest_id"].eq("con_612115bf42b450d3aeb63bb430d3aec9"),
            "coverage_state",
        ].item()
        == "comprehensive_source_found"
    )
    assert (
        inputs.coverage.loc[
            inputs.coverage["endorser_id"].eq(atu_id)
            & inputs.coverage["contest_id"].eq("con_990816d2030b592787bdf4a19382627f"),
            "coverage_state",
        ].item()
        == "comprehensive_source_found"
    )
    assert (
        inputs.coverage.loc[
            inputs.coverage["endorser_id"].eq(atu_id)
            & inputs.coverage["contest_id"].eq("con_922d425132ad5243b459c0ca40a6dcd9"),
            "coverage_state",
        ].item()
        == "partially_searched"
    )
    assert (
        inputs.coverage.loc[
            inputs.coverage["endorser_id"].eq(progress_id)
            & inputs.coverage["contest_id"].eq("con_945161409a0450f29e351ff3f263f815"),
            "coverage_state",
        ].item()
        == "not_applicable"
    )
    assert (
        inputs.coverage.loc[
            inputs.coverage["endorser_id"].eq(cupe_id)
            & inputs.coverage["contest_id"].eq("con_612115bf42b450d3aeb63bb430d3aec9"),
            "coverage_state",
        ].item()
        == "partially_searched"
    )
    assert (
        inputs.coverage.loc[
            inputs.coverage["endorser_id"].eq(cupe_id)
            & inputs.coverage["contest_id"].eq("con_c8883aeeac29529eada91aebc451242b"),
            "coverage_state",
        ].item()
        == "comprehensive_source_found"
    )


def test_default_panel_rejects_single_office_applicability(tmp_path):
    _, election_results, contests, people, reference_dir = _build(tmp_path)
    panel_path = reference_dir / ENDORSER_PANEL_FILENAME
    panel = pd.read_csv(panel_path, dtype="string")
    panel.loc[panel["endorser_key"].eq("cupe_ontario"), "councillor_applicable"] = "false"
    panel.to_csv(panel_path, index=False)

    with pytest.raises(ValueError, match="must apply to both Mayor and City Councillor"):
        build_default_endorsement_inputs(
            election_results,
            contests,
            people,
            reference_dir=reference_dir,
        )


@pytest.mark.parametrize(
    ("column", "bad_value", "message"),
    [
        ("coverage_state", "not_searched", "unsupported curated coverage_state"),
        ("evidence_url", "not-a-url", "coverage curations.evidence_url must use HTTPS"),
    ],
)
def test_coverage_curations_fail_closed(tmp_path, column, bad_value, message):
    _, election_results, contests, people, reference_dir = _build(tmp_path)
    path = reference_dir / ENDORSEMENT_COVERAGE_FILENAME
    curations = pd.read_csv(path, dtype="string")
    curations.loc[curations["curation_key"].eq("miller_2006_council_limited_search"), column] = (
        bad_value
    )
    curations.to_csv(path, index=False)

    with pytest.raises(ValueError, match=message):
        build_default_endorsement_inputs(
            election_results,
            contests,
            people,
            reference_dir=reference_dir,
        )


def test_star_2010_has_43_positive_edges_and_no_ward_39_edge(tmp_path):
    inputs, election_results, _, _, _ = _build(tmp_path)
    star_id = _endorser_id(inputs, "Toronto Star Editorial Board")
    assertions = inputs.assertions.merge(
        election_results[["candidacy_id", "election_date", "office_type", "official_district_id"]],
        on="candidacy_id",
        how="left",
    )
    star_council = assertions.loc[
        assertions["endorser_id"].eq(star_id)
        & assertions["election_date"].eq("2010-10-25")
        & assertions["office_type"].eq("councillor")
    ]

    assert len(star_council) == 43
    assert "ward-39" not in set(star_council["official_district_id"])
    assert "Richard Gosling" in set(star_council["asserted_candidate_name"])

    ward_39_coverage = inputs.coverage.loc[
        inputs.coverage["endorser_id"].eq(star_id)
        & inputs.coverage["contest_id"].eq("con_fixture_2010_w39")
    ]
    assert ward_39_coverage["coverage_state"].item() == "comprehensive_source_found"


def test_coverage_is_complete_open_world_and_respects_applicability(tmp_path):
    inputs, _, contests, _, _ = _build(tmp_path)

    assert len(inputs.coverage) == 9 * len(contests)
    assert not inputs.coverage.duplicated(["endorser_id", "contest_id"]).any()
    assert "searched_no_endorsement_found" not in set(inputs.coverage["coverage_state"])

    star_id = _endorser_id(inputs, "Toronto Star Editorial Board")
    for contest_id in ("con_fixture_2014_w01", "con_612115bf42b450d3aeb63bb430d3aec9"):
        state = inputs.coverage.loc[
            inputs.coverage["endorser_id"].eq(star_id)
            & inputs.coverage["contest_id"].eq(contest_id),
            "coverage_state",
        ].item()
        assert state == "comprehensive_source_found"

    star_2022_w03 = inputs.coverage.loc[
        inputs.coverage["endorser_id"].eq(star_id)
        & inputs.coverage["contest_id"].eq("con_bcc3da3d377f5fd3bb1d8a0c3ad7160b")
    ]
    assert star_2022_w03["coverage_state"].item() == "comprehensive_source_found"

    sun_id = _endorser_id(inputs, "Toronto Sun Editorial Board")
    verified_sun_2014 = inputs.coverage.loc[
        inputs.coverage["endorser_id"].eq(sun_id)
        & inputs.coverage["contest_id"].eq("con_fixture_2014_w01")
    ]
    assert verified_sun_2014["coverage_state"].item() == "partially_searched"
    assert verified_sun_2014["coverage_basis"].item() == (
        "Bounded publisher/archive search logged; no importable positive recovered."
    )
    historical_default = inputs.coverage.loc[
        inputs.coverage["endorser_id"].eq(sun_id)
        & inputs.coverage["contest_id"].eq("con_fixture_2019_w01")
    ]
    assert historical_default["coverage_state"].item() == "not_searched"
    assert historical_default["coverage_basis"].item() == (
        "no contest-specific historical search is logged"
    )
    assert pd.isna(historical_default["assessed_through"].item())

    mayor_2026 = inputs.coverage.query("contest_id == 'con_fixture_2026_mayor'")
    assert set(mayor_2026["coverage_state"]) == {"partially_searched"}
    council_2026 = inputs.coverage.query("contest_id == 'con_fixture_2026_w01'")
    assert set(council_2026["coverage_state"]) == {"partially_searched"}

    progress_id = _endorser_id(inputs, "Progress Toronto")
    miller_id = _endorser_id(inputs, "David Miller")
    mayor_2003 = "con_945161409a0450f29e351ff3f263f815"
    for endorser_id in (progress_id, miller_id):
        state = inputs.coverage.loc[
            inputs.coverage["endorser_id"].eq(endorser_id)
            & inputs.coverage["contest_id"].eq(mayor_2003),
            "coverage_state",
        ].item()
        assert state == "not_applicable"


def test_complete_slate_coverage_does_not_depend_on_a_candidate_edge(tmp_path):
    inputs, _, _, _, _ = _build(tmp_path)
    tory_id = _endorser_id(inputs, "John Tory")
    atu_id = _endorser_id(inputs, "Amalgamated Transit Union Local 113")
    contest_without_either_edge = "con_0d314382ba1a5d62b399c1eefc717cc1"

    for endorser_id in (tory_id, atu_id):
        state = inputs.coverage.loc[
            inputs.coverage["endorser_id"].eq(endorser_id)
            & inputs.coverage["contest_id"].eq(contest_without_either_edge),
            "coverage_state",
        ].item()
        assert state == "comprehensive_source_found"
        assert not (
            inputs.assertions["endorser_id"].eq(endorser_id)
            & inputs.assertions["contest_id"].eq(contest_without_either_edge)
        ).any()


@pytest.mark.parametrize(
    ("column", "bad_value", "message"),
    [
        ("candidate_name", "A different person", "Candidacy locator changed"),
        ("official_district_id", "ward-99", "inconsistent official_district_id"),
    ],
)
def test_curated_candidacy_locators_fail_closed(tmp_path, column, bad_value, message):
    inputs, election_results, contests, people, reference_dir = _build(tmp_path)
    del inputs
    target = election_results["candidacy_id"].eq("can_3d13fbd9fab452a5b347fb048574b6c4")
    election_results.loc[target, column] = bad_value

    with pytest.raises(ValueError, match=message):
        build_default_endorsement_inputs(
            election_results,
            contests,
            people,
            reference_dir=reference_dir,
        )


def test_ids_and_outputs_are_stable_under_dimension_row_order(tmp_path):
    inputs, election_results, contests, people, reference_dir = _build(tmp_path)
    shuffled = build_default_endorsement_inputs(
        election_results.sample(frac=1, random_state=8).reset_index(drop=True),
        contests.sample(frac=1, random_state=9).reset_index(drop=True),
        people.sample(frac=1, random_state=10).reset_index(drop=True),
        reference_dir=reference_dir,
    )

    pd.testing.assert_frame_equal(inputs.endorsers, shuffled.endorsers)
    pd.testing.assert_frame_equal(inputs.assertions, shuffled.assertions)
    pd.testing.assert_frame_equal(inputs.coverage, shuffled.coverage)
