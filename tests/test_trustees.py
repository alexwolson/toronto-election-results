"""Trustee source adapter behavior against the City's real official workbooks."""

import json
from datetime import date
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from toronto_election_results.schema import stable_id
from toronto_election_results.trustees import (
    TRUSTEE_RESULT_COLUMNS,
    discover_trustee_by_election_sources,
    discover_trustee_workbooks,
    download_trustee_by_elections,
    load_trustee_results,
    parse_trustee_by_elections,
    parse_trustee_workbooks,
    select_trustee_events,
    trustee_event_coverage_manifest,
    trustee_event_manifest,
)

REPO_ROOT = Path(__file__).parents[1]
RESULTS = REPO_ROOT / "data" / "interim" / "results"
BY_ELECTION_CATALOG = (
    REPO_ROOT / "data" / "raw" / "ckan" / "elections-official-by-election-results.json"
)


def _workbook_bytes(wards: tuple[int, ...] = (1,)) -> bytes:
    stream = BytesIO()
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        for ward in wards:
            pd.DataFrame(
                [
                    [f"Official trustee result Ward: {ward}", pd.NA, pd.NA],
                    ["Subdivision", 1, "Total"],
                    ["Alpha Alex", ward, ward],
                    ["Beta Bailey", ward * 2, ward * 2],
                    [f"City Ward {ward} Totals", ward * 3, ward * 3],
                ]
            ).to_excel(writer, sheet_name=f"Ward {ward}", header=False, index=False)
    return stream.getvalue()


def _french_zip_bytes() -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr(
            "2023_Toronto_Poll_By_Poll_Conseil_scolaire_Viamonde.xlsx",
            _workbook_bytes((3,)),
        )
        archive.writestr(
            "2023_Toronto_Poll_By_Poll_Conseil_scolaire_catholique_MonAvenir.xlsx",
            _workbook_bytes((4,)),
        )
    return stream.getvalue()


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=65536):
        del chunk_size
        yield self.payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _Session:
    def __init__(self, payloads: dict[str, bytes]):
        self.payloads = payloads
        self.calls: list[str] = []

    def get(self, url, **_kwargs):
        self.calls.append(url)
        return _Response(self.payloads[url])


@pytest.fixture(scope="module")
def sources() -> tuple[Path, ...]:
    if not RESULTS.exists():
        pytest.skip("requires the ignored local trustee general-election cache")
    return discover_trustee_workbooks(RESULTS)


@pytest.fixture(scope="module")
def results(sources: tuple[Path, ...]) -> pd.DataFrame:
    return parse_trustee_workbooks(sources)


def test_discovers_each_nonduplicated_local_board_workbook(sources):
    """2022's combined workbook duplicates English rows and has no French result rows."""
    assert len(sources) == 21
    assert not any("All_Offices" in path.name for path in sources)


def test_one_call_loader_returns_every_local_general_event(results, tmp_path):
    loaded = load_trustee_results(results_root=RESULTS, by_election_root=tmp_path)
    pd.testing.assert_frame_equal(loaded, results)


def test_result_contract_is_analysis_ready(results):
    assert list(results.columns) == list(TRUSTEE_RESULT_COLUMNS)
    assert results["votes"].dtype == pd.Int64Dtype()
    assert results["elected"].dtype == pd.BooleanDtype()
    assert results["election_date"].map(type).eq(date).all()
    assert results["office_type"].eq("trustee").all()
    assert results["affiliation_status"].eq("non_partisan").all()
    assert results["party_name_raw"].isna().all()


def test_every_general_event_has_all_four_boards(results):
    expected = {
        "Toronto District School Board",
        "Toronto Catholic District School Board",
        "Conseil scolaire Viamonde",
        "Conseil scolaire catholique MonAvenir",
    }
    by_year = results.groupby(results["election_date"].map(lambda value: value.year))[
        "represented_body"
    ].agg(set)
    assert by_year.to_dict() == {year: expected for year in (2003, 2006, 2010, 2014, 2018, 2022)}


def test_outputs_one_row_per_candidate_per_trustee_contest(results):
    contests = results[["event_id", "represented_body", "official_district_id"]].drop_duplicates()
    assert contests.groupby("event_id").size().to_dict() == {
        stable_id("evt", "toronto_city_clerk", "2003-11-10", "general"): 39,
        stable_id("evt", "toronto_city_clerk", "2006-11-13", "general"): 39,
        stable_id("evt", "toronto_city_clerk", "2010-10-25", "general"): 39,
        stable_id("evt", "toronto_city_clerk", "2014-10-27", "general"): 39,
        stable_id("evt", "toronto_city_clerk", "2018-10-22", "general"): 39,
        # Two French-board contests were void and correctly have no Candidacy rows.
        stable_id("evt", "toronto_city_clerk", "2022-10-24", "general"): 37,
    }
    keys = [
        "event_id",
        "represented_body",
        "official_district_id",
        "candidate_name_raw",
    ]
    assert not results.duplicated(keys).any()


def test_general_event_identity_matches_the_council_adapter(results):
    expected = {
        stable_id("evt", "toronto_city_clerk", election_date, "general")
        for election_date in results["election_date"].unique()
    }
    assert set(results["event_id"]) == expected
    assert results["election_authority"].eq("toronto_city_clerk").all()


@pytest.mark.parametrize(
    ("year", "body", "ward", "candidate", "votes"),
    [
        (2003, "Toronto District School Board", "1", "Nemiroff, Stan", 10002),
        (2014, "Conseil scolaire Viamonde", "3", "BÉGIN DENYS", 831),
        (2018, "Toronto District School Board", "8", "Laskin Shelley", 29410),
        (2022, "Toronto District School Board", "8", "Laskin Shelley", 19779),
    ],
)
def test_sums_repeated_city_ward_blocks_to_trustee_contests(
    results, year, body, ward, candidate, votes
):
    row = results[
        (results["election_date"].map(lambda value: value.year) == year)
        & (results["represented_body"] == body)
        & (results["official_district_id"] == ward)
        & (results["candidate_name_raw"] == candidate)
    ]
    assert len(row) == 1
    assert row.iloc[0]["votes"] == votes


@pytest.mark.parametrize(
    ("year", "body", "ward", "candidate"),
    [
        (2003, "Toronto District School Board", "6", "Hill, Elizabeth"),
        (2003, "Conseil scolaire Viamonde", "2", "FRANCOIS GUERIN"),
        (2006, "Conseil scolaire Viamonde", "4", "MASSON ALAIN"),
        (2006, "Conseil scolaire catholique MonAvenir", "4", "LEGERE CLAUDE"),
        (2010, "Conseil scolaire catholique MonAvenir", "3", "DUFOUR SÉGUIN NATHALIE"),
        (2014, "Conseil scolaire Viamonde", "4", "L'HEUREUX JEAN-FRANÇOIS"),
        (2022, "Conseil scolaire Viamonde", "2", "Benoit Fortin"),
        (2022, "Conseil scolaire catholique MonAvenir", "3", "Nathalie Dufour Séguin"),
    ],
)
def test_certified_acclamations_are_not_observed_zero_votes(results, year, body, ward, candidate):
    row = results[
        (results["election_date"].map(lambda value: value.year) == year)
        & (results["represented_body"] == body)
        & (results["official_district_id"] == ward)
        & (results["candidate_name_raw"] == candidate)
    ]
    assert len(row) == 1
    assert pd.isna(row.iloc[0]["votes"])
    assert bool(row.iloc[0]["elected"])
    assert row.iloc[0]["outcome_method"] == "acclamation"
    assert row.iloc[0]["coverage_status"] == "complete"


def test_unique_maximum_in_certified_vote_source_is_elected(results):
    contest = results[
        (results["election_date"] == date(2022, 10, 24))
        & (results["represented_body"] == "Toronto District School Board")
        & (results["official_district_id"] == "8")
    ]
    assert contest.loc[contest["elected"].fillna(False), "candidate_name_raw"].tolist() == [
        "Laskin Shelley"
    ]
    assert contest["elected"].notna().all()
    assert contest["coverage_status"].eq("complete").all()


def test_event_manifest_keeps_void_contests_without_candidacies():
    manifest = trustee_event_manifest(results_root=RESULTS)
    void = manifest[
        (manifest["election_date"] == date(2022, 10, 24)) & (manifest["outcome_method"] == "void")
    ]
    assert set(zip(void["represented_body"], void["official_district_id"], strict=True)) == {
        ("Conseil scolaire Viamonde", "3"),
        ("Conseil scolaire catholique MonAvenir", "4"),
    }
    assert void["coverage_status"].eq("complete").all()


def test_by_election_selector_lists_each_official_resource_through_2025():
    manifest = trustee_event_manifest(results_root=RESULTS)
    by_elections = select_trustee_events(manifest, election_type="by_election")
    assert list(
        zip(
            by_elections["election_date"],
            by_elections["represented_body"],
            by_elections["official_district_id"],
            strict=True,
        )
    ) == [
        (date(2012, 2, 27), "Toronto District School Board", "17"),
        (date(2012, 2, 27), "Toronto District School Board", "20"),
        (date(2012, 12, 10), "Toronto Catholic District School Board", "8"),
        (date(2016, 1, 25), "Toronto District School Board", "21"),
        (date(2016, 6, 20), "Toronto District School Board", "14"),
        (date(2016, 7, 25), "Toronto District School Board", "1"),
        (date(2016, 7, 25), "Toronto District School Board", "5"),
        (date(2023, 1, 23), "Conseil scolaire Viamonde", "3"),
        (date(2023, 1, 23), "Conseil scolaire catholique MonAvenir", "4"),
        (date(2025, 3, 3), "Toronto District School Board", "11"),
    ]
    assert by_elections["local_source_available"].eq(False).all()
    assert by_elections["resource_url"].str.startswith("https://").all()


def test_by_election_urls_are_exactly_the_trustee_resources_in_the_official_index():
    if not BY_ELECTION_CATALOG.exists():
        pytest.skip("requires the ignored local City by-election catalog cache")
    catalog = json.loads(BY_ELECTION_CATALOG.read_text())
    official = {
        resource["url"]
        for resource in catalog["result"]["resources"]
        if any(marker in resource["name"].casefold() for marker in ("tdsb", "tcdsb", "csv ward"))
    }
    manifest = trustee_event_manifest(results_root=RESULTS)
    actual = set(select_trustee_events(manifest, election_type="by_election")["resource_url"])
    assert actual == official


def test_2012_tcdsb_parser_uses_resource_ward_not_city_ward_sheet_names(tmp_path):
    source = tmp_path / "2012-tcdsb-ward-8.xlsx"
    source.write_bytes(_workbook_bytes((41, 42, 44)))
    mislabeled = source.with_suffix(".xls")
    source.replace(mislabeled)  # The official .xls resource is actually an xlsx package.

    results = parse_trustee_by_elections([mislabeled])

    assert results["official_district_id"].unique().tolist() == ["8"]
    assert results["represented_body"].unique().tolist() == [
        "Toronto Catholic District School Board"
    ]
    assert results.set_index("candidate_name_raw")["votes"].to_dict() == {
        "Alpha Alex": 127,
        "Beta Bailey": 254,
    }
    assert results.set_index("candidate_name_raw")["elected"].to_dict() == {
        "Alpha Alex": False,
        "Beta Bailey": True,
    }
    assert results["coverage_status"].eq("complete").all()


def test_2023_zip_parser_routes_each_member_to_its_french_board(tmp_path):
    source = tmp_path / "2023-csv-ward-3-centre-csc-monavenir-ward-4-toronto-est.zip"
    source.write_bytes(_french_zip_bytes())

    results = parse_trustee_by_elections([source])

    assert set(
        results[["represented_body", "official_district_id"]].itertuples(index=False, name=None)
    ) == {
        ("Conseil scolaire Viamonde", "3"),
        ("Conseil scolaire catholique MonAvenir", "4"),
    }
    assert results["event_id"].nunique() == 1
    assert results["election_date"].eq(date(2023, 1, 23)).all()


def test_by_election_event_identity_follows_the_official_call():
    by_elections = select_trustee_events(trustee_event_manifest(), election_type="by_election")

    event_ids = {
        (election_date, body, ward): event_id
        for election_date, body, ward, event_id in by_elections[
            [
                "election_date",
                "represented_body",
                "official_district_id",
                "event_id",
            ]
        ].itertuples(index=False, name=None)
    }
    assert (
        event_ids[(date(2012, 2, 27), "Toronto District School Board", "17")]
        == event_ids[(date(2012, 2, 27), "Toronto District School Board", "20")]
    )
    assert (
        event_ids[(date(2023, 1, 23), "Conseil scolaire Viamonde", "3")]
        == event_ids[(date(2023, 1, 23), "Conseil scolaire catholique MonAvenir", "4")]
    )
    assert (
        event_ids[(date(2016, 7, 25), "Toronto District School Board", "1")]
        != event_ids[(date(2016, 7, 25), "Toronto District School Board", "5")]
    )


def test_downloader_is_atomic_idempotent_and_resource_scoped(tmp_path):
    manifest = trustee_event_manifest()
    urls = set(select_trustee_events(manifest, election_type="by_election")["resource_url"])
    session = _Session({url: b"official bytes" for url in urls})

    first = download_trustee_by_elections(tmp_path, session=session)
    second = download_trustee_by_elections(tmp_path, session=session)

    assert first == second
    assert len(first) == 8
    assert len(session.calls) == 8
    assert not list(tmp_path.glob("*.part"))
    assert discover_trustee_by_election_sources(tmp_path) == first


def test_loader_downloads_and_parses_all_ten_by_election_contests(tmp_path):
    manifest = trustee_event_manifest()
    urls = set(select_trustee_events(manifest, election_type="by_election")["resource_url"])
    generic = _workbook_bytes((1, 5, 8, 11, 14, 17, 20, 21))
    session = _Session(
        {url: (_french_zip_bytes() if url.endswith(".zip") else generic) for url in urls}
    )
    empty_general_root = tmp_path / "general"

    results = load_trustee_results(
        results_root=empty_general_root,
        by_election_root=tmp_path / "by-elections",
        download=True,
        session=session,
    )

    contests = results[["event_id", "represented_body", "official_district_id"]].drop_duplicates()
    assert len(contests) == 10
    assert len(session.calls) == 8
    assert results["election_type"].eq("by_election").all()


def test_manifest_cutoff_and_uncertain_early_by_election_coverage():
    manifest = trustee_event_manifest(results_root=RESULTS, through=date(2022, 12, 31))
    assert manifest["election_date"].max() == date(2022, 10, 24)

    coverage = trustee_event_coverage_manifest()
    uncertain = coverage[coverage["event_coverage"] == "uncertain"].iloc[0]
    assert uncertain["start_date"] == date(2003, 1, 1)
    assert uncertain["end_date"] == date(2011, 12, 31)
    assert uncertain["election_type"] == "by_election"
