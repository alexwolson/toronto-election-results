"""Elections Ontario adapter: deterministic scope and official CSV normalization."""

from pathlib import Path

import pytest

from toronto_election_results.ontario import (
    DISTRICTS,
    EVENTS,
    REPORTS,
    RESULT_COLUMNS,
    download_official_csv,
    download_ontario_sources,
    load_ontario_results,
    ontario_district_manifest,
    ontario_event_manifest,
    ontario_source_files,
    parse_official_results,
)

FIXTURES = Path(__file__).parent / "fixtures" / "ontario"


def test_manifest_covers_every_in_scope_ontario_event():
    general = [event for event in EVENTS if event.election_type == "general"]
    by_elections = [event for event in EVENTS if event.election_type == "by_election"]

    assert [event.election_date.isoformat() for event in general] == [
        "2003-10-02",
        "2007-10-10",
        "2011-10-06",
        "2014-06-12",
        "2018-06-07",
        "2022-06-02",
        "2025-02-27",
    ]
    assert len(by_elections) == 10
    assert sum(event.expected_candidate_rows for event in EVENTS) == 1172
    assert len(REPORTS) == 7

    districts_per_regime = {}
    for district in DISTRICTS:
        districts_per_regime.setdefault(district.boundary_regime, set()).add(district.district_id)
    assert {regime: len(ids) for regime, ids in districts_per_regime.items()} == {
        "ontario-1999-103": 22,
        "ontario-2007-107": 22,
        "ontario-2018-124": 25,
    }

    event_manifest = ontario_event_manifest()
    district_manifest = ontario_district_manifest()
    assert event_manifest["event_id"].is_unique
    assert len(event_manifest) == 17
    assert list(event_manifest["event_id"]) == [event.event_id for event in EVENTS]
    assert list(district_manifest["district_id"]) == [
        district.district_id for district in DISTRICTS
    ]


def test_official_csvs_become_normalized_toronto_candidacies():
    report = next(report for report in REPORTS if report.report_group_id == 48)
    results = parse_official_results(
        FIXTURES / "candidates.csv",
        FIXTURES / "statistics.csv",
        FIXTURES / "parties.csv",
        report=report,
    )

    assert list(results.columns) == RESULT_COLUMNS
    assert "official_district_id" in results
    assert "district_id" not in results
    assert len(results) == 5  # the Ajax source row is outside City-of-Toronto scope
    assert results["election_authority"].eq("Elections Ontario").all()
    assert results["represented_body"].eq("Legislative Assembly of Ontario").all()
    assert results["office_type"].eq("mpp").all()
    assert results["elected"].dtype.name == "boolean"

    by_winner = results[results["candidate_name_raw"] == "ANDREA HAZELL"].iloc[0]
    assert by_winner["event_id"] == "on-2023-07-27-by-095"
    assert by_winner["election_type"] == "by_election"
    assert by_winner["official_district_id"] == "095"
    assert by_winner["district_name"] == "Scarborough—Guildwood"
    assert by_winner["party_name_raw"] == "Ontario Liberal Party"
    assert by_winner["affiliation_status"] == "party"
    assert by_winner["votes"] == 5640
    assert by_winner["elected"]
    assert not by_winner["incumbent_reported"]
    assert by_winner["eligible_electors"] == 70893
    assert by_winner["ballots_cast"] == 15509

    incumbent = results[results["candidate_name_raw"] == "MARY-MARGARET MCMAHON"].iloc[0]
    assert incumbent["event_id"] == "on-2025-general"
    assert incumbent["incumbent_reported"]

    affiliations = results.set_index("candidate_name_raw")["affiliation_status"]
    assert affiliations["ABU ALAM"] == "independent"
    assert affiliations["REGINALD TULL"] == "independent"

    assert set(results["outcome_method"]) == {"vote"}
    assert set(results["coverage_status"]) == {"complete"}
    assert results["source_detail"].str.startswith("https://results.elections.on.ca/api/").all()


def test_party_names_are_scoped_to_the_source_event_when_a_code_was_renamed():
    report = next(report for report in REPORTS if report.report_group_id == 2)
    results = parse_official_results(
        FIXTURES / "candidates-party-rename.csv",
        FIXTURES / "statistics-party-rename.csv",
        FIXTURES / "parties-party-rename.csv",
        report=report,
    )

    assert results.loc[0, "candidate_name_raw"] == "RAPHAEL ROSCH"
    assert results.loc[0, "party_name_raw"] == "FAMILY COALITION PARTY OF ONTARIO"


def test_official_csv_download_is_atomic_and_idempotent(tmp_path):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            assert chunk_size > 0
            return iter((b"official,", b"csv\n"))

    class Session:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return Response()

    session = Session()
    destination = tmp_path / "nested" / "results.csv"
    downloaded = download_official_csv(
        "https://results.elections.on.ca/official.csv", destination, session=session
    )

    assert downloaded == destination
    assert destination.read_bytes() == b"official,csv\n"
    assert not destination.with_suffix(".csv.part").exists()
    assert len(session.calls) == 1

    download_official_csv(
        "https://results.elections.on.ca/official.csv", destination, session=session
    )
    assert len(session.calls) == 1


def test_loads_downloaded_report_trios_through_one_stable_seam(tmp_path):
    report = next(report for report in REPORTS if report.report_group_id == 48)
    source_files = ontario_source_files(tmp_path, report)
    source_files.candidates_csv.parent.mkdir(parents=True)
    source_files.candidates_csv.write_bytes((FIXTURES / "candidates.csv").read_bytes())
    source_files.statistics_csv.write_bytes((FIXTURES / "statistics.csv").read_bytes())
    source_files.parties_csv.write_bytes((FIXTURES / "parties.csv").read_bytes())

    assert source_files.candidates_csv.relative_to(tmp_path).as_posix() == (
        "report-group-48/candidates-1096.csv"
    )
    results = load_ontario_results(tmp_path, reports=(report,), validate=False)

    assert list(results.columns) == RESULT_COLUMNS
    assert len(results) == 5
    assert set(results["event_id"]) == {"on-2023-07-27-by-095", "on-2025-general"}

    with pytest.raises(ValueError, match="candidate coverage does not match"):
        load_ontario_results(tmp_path, reports=(report,))


def test_downloads_each_official_report_component_to_its_stable_path(tmp_path):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            return iter((b"official csv",))

    class Session:
        def __init__(self):
            self.urls = []

        def get(self, url, **_kwargs):
            self.urls.append(url)
            return Response()

    report = next(report for report in REPORTS if report.report_group_id == 48)
    session = Session()
    downloaded = download_ontario_sources(tmp_path, reports=(report,), session=session)

    assert downloaded == (ontario_source_files(tmp_path, report),)
    assert session.urls == [
        "https://results.elections.on.ca/api/report-groups/48/report-outputs/1096/csv",
        "https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv",
        "https://results.elections.on.ca/api/report-groups/48/report-outputs/1094/csv",
    ]
    assert all(
        path.read_bytes() == b"official csv"
        for path in (
            downloaded[0].candidates_csv,
            downloaded[0].statistics_csv,
            downloaded[0].parties_csv,
        )
    )
