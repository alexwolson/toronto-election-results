"""Official Elections Ontario results for contests wholly within Toronto.

The public constants in this module are the scope manifest.  Elections Ontario groups each
general election together with the by-elections since the preceding general election, so an event
is selected by polling date and official electoral-district number rather than by report title.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests


@dataclass(frozen=True)
class ReportSpec:
    report_group_id: int
    candidates_output_id: int
    statistics_output_id: int
    parties_output_id: int


@dataclass(frozen=True)
class OfficialReportFiles:
    """Stable local paths for the three official CSVs in one report group."""

    report: ReportSpec
    candidates_csv: Path
    statistics_csv: Path
    parties_csv: Path


@dataclass(frozen=True)
class DistrictSpec:
    boundary_regime: str
    source_number: int
    district_id: str
    district_name: str


@dataclass(frozen=True)
class EventSpec:
    event_id: str
    election_date: date
    election_type: str
    boundary_regime: str
    report_group_id: int
    district_numbers: tuple[int, ...]
    expected_candidate_rows: int


REPORTS = (
    ReportSpec(5, 521, 514, 519),
    ReportSpec(4, 510, 503, 508),
    ReportSpec(3, 499, 492, 497),
    ReportSpec(2, 488, 481, 486),
    ReportSpec(1, 932, 925, 930),
    ReportSpec(45, 1050, 1043, 1048),
    ReportSpec(48, 1096, 1089, 1094),
)


def _districts(regime: str, entries: tuple[tuple[int, str], ...]) -> tuple[DistrictSpec, ...]:
    return tuple(
        DistrictSpec(regime, number, f"on-{regime.removeprefix('ontario-')}-{number:03d}", name)
        for number, name in entries
    )


_DISTRICTS_1999 = _districts(
    "ontario-1999-103",
    (
        (3, "Beaches—East York"),
        (8, "Toronto—Danforth"),
        (12, "Davenport"),
        (13, "Don Valley East"),
        (14, "Don Valley West"),
        (17, "Eglinton—Lawrence"),
        (21, "Etobicoke Centre"),
        (22, "Etobicoke—Lakeshore"),
        (23, "Etobicoke North"),
        (64, "Parkdale—High Park"),
        (73, "Scarborough—Agincourt"),
        (74, "Scarborough Centre"),
        (75, "Scarborough East"),
        (76, "Scarborough—Rouge River"),
        (77, "Scarborough Southwest"),
        (81, "St. Paul's"),
        (90, "Toronto Centre—Rosedale"),
        (91, "Trinity—Spadina"),
        (97, "Willowdale"),
        (100, "York Centre"),
        (102, "York South—Weston"),
        (103, "York West"),
    ),
)

_DISTRICTS_2007 = _districts(
    "ontario-2007-107",
    (
        (5, "Beaches—East York"),
        (15, "Davenport"),
        (16, "Don Valley East"),
        (17, "Don Valley West"),
        (20, "Eglinton—Lawrence"),
        (23, "Etobicoke Centre"),
        (24, "Etobicoke—Lakeshore"),
        (25, "Etobicoke North"),
        (68, "Parkdale—High Park"),
        (77, "St. Paul's"),
        (80, "Scarborough—Agincourt"),
        (81, "Scarborough Centre"),
        (82, "Scarborough—Guildwood"),
        (83, "Scarborough—Rouge River"),
        (84, "Scarborough Southwest"),
        (94, "Toronto Centre"),
        (95, "Toronto—Danforth"),
        (96, "Trinity—Spadina"),
        (101, "Willowdale"),
        (104, "York Centre"),
        (106, "York South—Weston"),
        (107, "York West"),
    ),
)

_DISTRICTS_2018 = _districts(
    "ontario-2018-124",
    (
        (7, "Beaches—East York"),
        (19, "Davenport"),
        (20, "Don Valley East"),
        (21, "Don Valley North"),
        (22, "Don Valley West"),
        (25, "Eglinton—Lawrence"),
        (28, "Etobicoke Centre"),
        (29, "Etobicoke—Lakeshore"),
        (30, "Etobicoke North"),
        (41, "Humber River—Black Creek"),
        (83, "Parkdale—High Park"),
        (93, "Scarborough—Agincourt"),
        (94, "Scarborough Centre"),
        (95, "Scarborough—Guildwood"),
        (96, "Scarborough North"),
        (97, "Scarborough—Rouge Park"),
        (98, "Scarborough Southwest"),
        (101, "Spadina—Fort York"),
        (109, "Toronto Centre"),
        (110, "Toronto—Danforth"),
        (111, "Toronto—St. Paul's"),
        (112, "University—Rosedale"),
        (117, "Willowdale"),
        (120, "York Centre"),
        (122, "York South—Weston"),
    ),
)

DISTRICTS = _DISTRICTS_1999 + _DISTRICTS_2007 + _DISTRICTS_2018

_NUMBERS_BY_REGIME = {
    regime: tuple(d.source_number for d in DISTRICTS if d.boundary_regime == regime)
    for regime in {d.boundary_regime for d in DISTRICTS}
}

EVENTS = (
    EventSpec(
        "on-2003-general",
        date(2003, 10, 2),
        "general",
        "ontario-1999-103",
        5,
        _NUMBERS_BY_REGIME["ontario-1999-103"],
        119,
    ),
    EventSpec(
        "on-2005-11-24-by-076",
        date(2005, 11, 24),
        "by_election",
        "ontario-1999-103",
        4,
        (76,),
        7,
    ),
    EventSpec(
        "on-2006-03-30-by-008",
        date(2006, 3, 30),
        "by_election",
        "ontario-1999-103",
        4,
        (8,),
        8,
    ),
    EventSpec(
        "on-2006-09-14-by-064",
        date(2006, 9, 14),
        "by_election",
        "ontario-1999-103",
        4,
        (64,),
        8,
    ),
    EventSpec(
        "on-2007-02-08-by-102",
        date(2007, 2, 8),
        "by_election",
        "ontario-1999-103",
        4,
        (102,),
        9,
    ),
    EventSpec(
        "on-2007-general",
        date(2007, 10, 10),
        "general",
        "ontario-2007-107",
        4,
        _NUMBERS_BY_REGIME["ontario-2007-107"],
        141,
    ),
    EventSpec(
        "on-2009-09-17-by-077",
        date(2009, 9, 17),
        "by_election",
        "ontario-2007-107",
        3,
        (77,),
        10,
    ),
    EventSpec(
        "on-2010-02-04-by-094",
        date(2010, 2, 4),
        "by_election",
        "ontario-2007-107",
        3,
        (94,),
        8,
    ),
    EventSpec(
        "on-2011-general",
        date(2011, 10, 6),
        "general",
        "ontario-2007-107",
        3,
        _NUMBERS_BY_REGIME["ontario-2007-107"],
        158,
    ),
    EventSpec(
        "on-2013-08-01-by-024",
        date(2013, 8, 1),
        "by_election",
        "ontario-2007-107",
        2,
        (24,),
        8,
    ),
    EventSpec(
        "on-2013-08-01-by-082",
        date(2013, 8, 1),
        "by_election",
        "ontario-2007-107",
        2,
        (82,),
        10,
    ),
    EventSpec(
        "on-2014-general",
        date(2014, 6, 12),
        "general",
        "ontario-2007-107",
        2,
        _NUMBERS_BY_REGIME["ontario-2007-107"],
        145,
    ),
    EventSpec(
        "on-2016-09-01-by-083",
        date(2016, 9, 1),
        "by_election",
        "ontario-2007-107",
        1,
        (83,),
        11,
    ),
    EventSpec(
        "on-2018-general",
        date(2018, 6, 7),
        "general",
        "ontario-2018-124",
        1,
        _NUMBERS_BY_REGIME["ontario-2018-124"],
        176,
    ),
    EventSpec(
        "on-2022-general",
        date(2022, 6, 2),
        "general",
        "ontario-2018-124",
        45,
        _NUMBERS_BY_REGIME["ontario-2018-124"],
        198,
    ),
    EventSpec(
        "on-2023-07-27-by-095",
        date(2023, 7, 27),
        "by_election",
        "ontario-2018-124",
        48,
        (95,),
        12,
    ),
    EventSpec(
        "on-2025-general",
        date(2025, 2, 27),
        "general",
        "ontario-2018-124",
        48,
        _NUMBERS_BY_REGIME["ontario-2018-124"],
        144,
    ),
)


def ontario_event_manifest() -> pd.DataFrame:
    """Return the deterministic, cutoff-bounded Elections Ontario event manifest."""
    district_lookup = {
        (district.boundary_regime, district.source_number): district.district_id
        for district in DISTRICTS
    }
    report_lookup = {report.report_group_id: report for report in REPORTS}
    rows = []
    for event in EVENTS:
        report = report_lookup[event.report_group_id]
        rows.append(
            {
                "event_id": event.event_id,
                "election_date": event.election_date,
                "election_type": event.election_type,
                "election_authority": "Elections Ontario",
                "represented_body": "Legislative Assembly of Ontario",
                "office_type": "mpp",
                "boundary_regime": event.boundary_regime,
                "district_ids": tuple(
                    district_lookup[(event.boundary_regime, number)]
                    for number in event.district_numbers
                ),
                "report_group_id": event.report_group_id,
                "expected_candidate_rows": event.expected_candidate_rows,
                "source_urls": tuple(
                    report_csv_url(event.report_group_id, output_id)
                    for output_id in (
                        report.candidates_output_id,
                        report.statistics_output_id,
                        report.parties_output_id,
                    )
                ),
            }
        )
    return pd.DataFrame(rows)


def ontario_district_manifest() -> pd.DataFrame:
    """Return every official Toronto district identity used in the coverage window."""
    return pd.DataFrame(
        [
            {
                "boundary_regime": district.boundary_regime,
                "district_id": district.district_id,
                "district_name": district.district_name,
                "source_number": district.source_number,
            }
            for district in DISTRICTS
        ]
    )


RESULT_COLUMNS = [
    "event_id",
    "election_date",
    "election_type",
    "election_authority",
    "represented_body",
    "office_type",
    "boundary_regime",
    "official_district_id",
    "district_name",
    "candidate_name_raw",
    "party_name_raw",
    "affiliation_status",
    "votes",
    "elected",
    "incumbent_reported",
    "eligible_electors",
    "ballots_cast",
    "outcome_method",
    "coverage_status",
    "source_detail",
]

API_ROOT = "https://results.elections.on.ca/api"


def report_csv_url(report_group_id: int, report_output_id: int) -> str:
    """Return the official API URL for one report output's CSV representation."""
    return f"{API_ROOT}/report-groups/{report_group_id}/report-outputs/{report_output_id}/csv"


def ontario_source_files(source_dir: str | Path, report: ReportSpec) -> OfficialReportFiles:
    """Return deterministic cache paths for one report group's official CSV trio."""
    directory = Path(source_dir) / f"report-group-{report.report_group_id}"
    return OfficialReportFiles(
        report=report,
        candidates_csv=directory / f"candidates-{report.candidates_output_id}.csv",
        statistics_csv=directory / f"statistics-{report.statistics_output_id}.csv",
        parties_csv=directory / f"parties-{report.parties_output_id}.csv",
    )


def download_official_csv(
    url: str,
    destination: str | Path,
    *,
    session: requests.Session | None = None,
    overwrite: bool = False,
) -> Path:
    """Download one official CSV atomically, reusing an existing file by default."""
    destination = Path(destination)
    if destination.exists() and not overwrite:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    client = session or requests
    with client.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if chunk:
                    handle.write(chunk)
    temporary.replace(destination)
    return destination


def download_ontario_sources(
    source_dir: str | Path,
    *,
    reports: tuple[ReportSpec, ...] = REPORTS,
    session: requests.Session | None = None,
    overwrite: bool = False,
) -> tuple[OfficialReportFiles, ...]:
    """Download every selected official report component to deterministic local paths."""
    downloaded = []
    for report in reports:
        files = ontario_source_files(source_dir, report)
        outputs = (
            (report.candidates_output_id, files.candidates_csv),
            (report.statistics_output_id, files.statistics_csv),
            (report.parties_output_id, files.parties_csv),
        )
        for output_id, destination in outputs:
            download_official_csv(
                report_csv_url(report.report_group_id, output_id),
                destination,
                session=session,
                overwrite=overwrite,
            )
        downloaded.append(files)
    return tuple(downloaded)


def _polling_date(value: object) -> date:
    return pd.to_datetime(str(value).strip(), format="%Y-%b-%d").date()


def _party_names(parties: pd.DataFrame) -> dict[tuple[int, str, str], str]:
    names: dict[tuple[int, str, str], str] = {}
    for row in parties.itertuples(index=False):
        event_name = str(row.EventNameEnglish).strip()
        year_match = re.search(r"\b(?:19|20)\d{2}\b", event_name)
        if year_match is None:
            continue
        election_type = "general" if "general" in event_name.casefold() else "by_election"
        code = str(row.PoliticalInterestCode).strip()
        name = str(row.PartyFullNameEnglish).strip()
        if not code or not name:
            continue
        key = (int(year_match.group()), election_type, code)
        existing = names.get(key)
        if existing is not None and existing != name:
            raise ValueError(f"political-interest code {code!r} has conflicting names for {key}")
        names[key] = name
    return names


def parse_official_results(
    candidates_csv: str | Path,
    statistics_csv: str | Path,
    parties_csv: str | Path,
    *,
    report: ReportSpec,
) -> pd.DataFrame:
    """Normalize one Elections Ontario report group's official CSV trio.

    A report group contains a general election and, for most years, earlier by-elections.  Only
    date/district pairs declared in :data:`EVENTS` are emitted, which makes the Toronto boundary
    explicit and prevents returning-office locations from being mistaken for electoral scope.
    """
    # ``NA`` is Elections Ontario's explicit "No Affiliation" code, not a missing value.
    candidates = pd.read_csv(candidates_csv, encoding="utf-8-sig", keep_default_na=False)
    statistics = pd.read_csv(statistics_csv, encoding="utf-8-sig")
    parties = pd.read_csv(parties_csv, encoding="utf-8-sig", keep_default_na=False)

    events = [event for event in EVENTS if event.report_group_id == report.report_group_id]
    event_lookup = {
        (event.election_date, district_number): event
        for event in events
        for district_number in event.district_numbers
    }
    district_lookup = {
        (district.boundary_regime, district.source_number): district for district in DISTRICTS
    }

    stats_lookup = {}
    for row in statistics.itertuples(index=False):
        key = (_polling_date(row.PollingDate), int(row.ElectoralDistrictNumber))
        if key in stats_lookup:
            raise ValueError(f"duplicate Elections Ontario statistics row for {key}")
        stats_lookup[key] = (int(row.TotalNumberOfNames), int(row.VoterTurnoutTotal))

    party_names = _party_names(parties)
    source_detail = ";".join(
        (
            report_csv_url(report.report_group_id, report.candidates_output_id),
            report_csv_url(report.report_group_id, report.statistics_output_id),
            report_csv_url(report.report_group_id, report.parties_output_id),
        )
    )

    rows = []
    for row in candidates.itertuples(index=False):
        key = (_polling_date(row.PollingDate), int(row.ElectoralDistrictNumber))
        event = event_lookup.get(key)
        if event is None:
            continue
        stats = stats_lookup.get(key)
        if stats is None:
            raise ValueError(f"missing Elections Ontario statistics row for {key}")
        district = district_lookup[(event.boundary_regime, key[1])]
        is_general = bool(int(row.IsGeneralElection))
        if is_general != (event.election_type == "general"):
            raise ValueError(f"election-type mismatch for {event.event_id}")

        code = "" if pd.isna(row.PoliticalInterestCode) else str(row.PoliticalInterestCode).strip()
        if not code:
            affiliation_status = "not_reported"
            party_name = pd.NA
        elif code in {"IND", "NA"}:
            affiliation_status = "independent"
            party_name = party_names.get(
                (event.election_date.year, event.election_type, code), code
            )
        else:
            affiliation_status = "party"
            party_key = (event.election_date.year, event.election_type, code)
            if party_key not in party_names:
                raise ValueError(f"no party name reported for political-interest code {code!r}")
            party_name = party_names[party_key]

        incumbent_raw = str(row.IsMemberOfPreviousLegislature).strip()
        incumbent = pd.NA if not incumbent_raw else bool(int(incumbent_raw))
        rows.append(
            {
                "event_id": event.event_id,
                "election_date": event.election_date,
                "election_type": event.election_type,
                "election_authority": "Elections Ontario",
                "represented_body": "Legislative Assembly of Ontario",
                "office_type": "mpp",
                "boundary_regime": event.boundary_regime,
                "official_district_id": f"{district.source_number:03d}",
                "district_name": district.district_name,
                "candidate_name_raw": str(row.NameOfCandidates).strip(),
                "party_name_raw": party_name,
                "affiliation_status": affiliation_status,
                "votes": int(row.TotalValidBallotsCast),
                "elected": int(row.Plurality) > 0,
                "incumbent_reported": incumbent,
                "eligible_electors": stats[0],
                "ballots_cast": stats[1],
                "outcome_method": "vote",
                "coverage_status": "complete",
                "source_detail": source_detail,
            }
        )

    result = pd.DataFrame(rows, columns=RESULT_COLUMNS)
    if result.empty:
        return result
    result["votes"] = pd.array(result["votes"], dtype="Int64")
    result["eligible_electors"] = pd.array(result["eligible_electors"], dtype="Int64")
    result["ballots_cast"] = pd.array(result["ballots_cast"], dtype="Int64")
    result["elected"] = pd.array(result["elected"], dtype="boolean")
    result["incumbent_reported"] = pd.array(result["incumbent_reported"], dtype="boolean")
    result = result.sort_values(
        [
            "election_date",
            "official_district_id",
            "elected",
            "votes",
            "candidate_name_raw",
        ],
        ascending=[True, True, False, False, True],
    )
    return result.reset_index(drop=True)


def _validate_manifest_coverage(results: pd.DataFrame, reports: tuple[ReportSpec, ...]) -> None:
    report_ids = {report.report_group_id for report in reports}
    events = [event for event in EVENTS if event.report_group_id in report_ids]
    expected_counts = {event.event_id: event.expected_candidate_rows for event in events}
    actual_counts = results.groupby("event_id", sort=False).size().to_dict()
    if actual_counts != expected_counts:
        raise ValueError(
            "Elections Ontario candidate coverage does not match the event manifest: "
            f"expected {expected_counts}, got {actual_counts}"
        )

    expected_contests = {
        (event.event_id, f"{number:03d}") for event in events for number in event.district_numbers
    }
    actual_contests = set(
        results[["event_id", "official_district_id"]].itertuples(index=False, name=None)
    )
    if actual_contests != expected_contests:
        missing = sorted(expected_contests - actual_contests)
        unexpected = sorted(actual_contests - expected_contests)
        raise ValueError(
            "Elections Ontario contest coverage does not match the manifest: "
            f"missing={missing}, unexpected={unexpected}"
        )


def load_ontario_results(
    source_dir: str | Path,
    *,
    reports: tuple[ReportSpec, ...] = REPORTS,
    validate: bool = True,
) -> pd.DataFrame:
    """Load downloaded official report trios into one normalized Toronto result frame."""
    frames = []
    for report in reports:
        files = ontario_source_files(source_dir, report)
        frames.append(
            parse_official_results(
                files.candidates_csv,
                files.statistics_csv,
                files.parties_csv,
                report=report,
            )
        )

    results = (
        pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=RESULT_COLUMNS)
    )
    results = results.sort_values(
        [
            "election_date",
            "official_district_id",
            "elected",
            "votes",
            "candidate_name_raw",
        ],
        ascending=[True, True, False, False, True],
    ).reset_index(drop=True)
    if validate:
        _validate_manifest_coverage(results, reports)
    return results
