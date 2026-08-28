from __future__ import annotations

import pandas as pd
import pytest

from toronto_election_results.endorsement_census import (
    build_endorsement_source_package_census,
)
from toronto_election_results.schema import stable_id


def _frames():
    panel = pd.DataFrame(
        [
            {
                "endorser_key": "example_board",
                "canonical_name": "Example Editorial Board",
                "is_panel_endorser": True,
                "eligibility_start_date": "2003-01-01",
                "mayor_applicable": True,
                "councillor_applicable": True,
            },
            {
                "endorser_key": "later_mayor",
                "canonical_name": "Later Mayor",
                "is_panel_endorser": True,
                "eligibility_start_date": "2020-01-01",
                "mayor_applicable": True,
                "councillor_applicable": True,
            },
        ]
    )
    contests = pd.DataFrame(
        [
            {
                "contest_id": "con_mayor",
                "event_id": "evt_2018",
                "represented_body": "toronto_city_council",
                "office_type": "mayor",
            },
            {
                "contest_id": "con_w1",
                "event_id": "evt_2018",
                "represented_body": "toronto_city_council",
                "office_type": "councillor",
            },
            {
                "contest_id": "con_w2",
                "event_id": "evt_2018",
                "represented_body": "toronto_city_council",
                "office_type": "councillor",
            },
            {
                "contest_id": "con_2026",
                "event_id": "evt_2026",
                "represented_body": "toronto_city_council",
                "office_type": "mayor",
            },
        ]
    )
    result_rows = []
    for contest_id, election_date, office, district in (
        ("con_mayor", "2018-10-22", "mayor", "city"),
        ("con_w1", "2018-10-22", "councillor", "ward-1"),
        ("con_w2", "2018-10-22", "councillor", "ward-2"),
        ("con_2026", "2026-10-26", "mayor", "city"),
    ):
        result_rows.append(
            {
                "contest_id": contest_id,
                "election_date": election_date,
                "represented_body": "toronto_city_council",
                "office_type": office,
                "official_district_id": district,
            }
        )
    results = pd.DataFrame(result_rows)
    board_id = stable_id("edr", "curated_endorser", "example_board")
    later_id = stable_id("edr", "curated_endorser", "later_mayor")
    coverage_rows = []
    for endorser_id, contest_id, state, assessed in (
        (board_id, "con_mayor", "comprehensive_source_found", "2026-08-28"),
        (board_id, "con_w1", "comprehensive_source_found", "2026-08-28"),
        (board_id, "con_w2", "comprehensive_source_found", "2026-08-28"),
        (board_id, "con_2026", "partially_searched", "2026-08-28"),
        (later_id, "con_2026", "not_searched", None),
    ):
        coverage_rows.append(
            {
                "endorser_id": endorser_id,
                "contest_id": contest_id,
                "coverage_state": state,
                "assessed_through": assessed,
            }
        )
    coverage = pd.DataFrame(coverage_rows)
    assertions = pd.DataFrame(
        [
            {
                "endorser_id": board_id,
                "contest_id": "con_w1",
                "review_state": "confirmed",
            },
            {
                "endorser_id": board_id,
                "contest_id": "con_w2",
                "review_state": "unresolved",
            },
        ]
    )
    return results, contests, panel, assertions, coverage


def _build():
    results, contests, panel, assertions, coverage = _frames()
    return build_endorsement_source_package_census(
        election_results=results,
        contests=contests,
        panel_curations=panel,
        endorsement_assertions=assertions,
        endorsement_coverage=coverage,
    )


def test_groups_contests_into_source_packages_and_excludes_preeligibility_cells():
    census = _build()

    assert len(census) == 4
    board_council = census.loc[
        census["endorser_key"].eq("example_board") & census["office_type"].eq("councillor")
    ].iloc[0]
    assert board_council["disposition"] == "validated_package_found"
    assert board_council["contest_count"] == 2
    assert board_council["district_count"] == 2
    assert board_council["confirmed_assertion_count"] == 1
    assert board_council["unresolved_assertion_count"] == 1
    assert board_council["related_contest_ids"] == "con_w1|con_w2"

    later = census.loc[census["endorser_key"].eq("later_mayor")].iloc[0]
    assert later["election_date"] == "2026-10-26"
    assert later["disposition"] == "not_yet_searched"


def test_current_partial_search_remains_partial_even_without_an_assertion():
    census = _build()
    current = census.loc[
        census["endorser_key"].eq("example_board") & census["election_date"].eq("2026-10-26")
    ].iloc[0]

    assert current["disposition"] == "partial_evidence_only"
    assert current["assessed_through"] == "2026-08-28"


def test_missing_applicable_coverage_fails_closed():
    results, contests, panel, assertions, coverage = _frames()
    coverage = coverage.loc[~coverage["contest_id"].eq("con_w2")]

    with pytest.raises(ValueError, match="missing coverage"):
        build_endorsement_source_package_census(
            election_results=results,
            contests=contests,
            panel_curations=panel,
            endorsement_assertions=assertions,
            endorsement_coverage=coverage,
        )
