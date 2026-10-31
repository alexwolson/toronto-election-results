"""Official Elections Ontario results for contests wholly within Toronto.

The public constants in this module are the scope manifest.  Elections Ontario groups each
general election together with the by-elections since the preceding general election, so an event
is selected by polling date and official electoral-district number rather than by report title.
"""

from __future__ import annotations

import hashlib
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


@dataclass(frozen=True)
class VoteCorrection:
    """A pinned fix for a candidate total that the official CSV prints wrongly.

    ``source_votes`` is what the CSV says; a different value fails the load, so a corrected
    upstream file is noticed instead of being overwritten.
    """

    polling_date: date
    district_number: int
    candidate_name: str
    source_votes: int
    corrected_votes: int


# Elections Ontario's 2011 candidates CSV gives Willowdale's two Browns each other's totals
# (Amy Brown, Freedom Party, 5,556; Alexander Brown, NDP, 297).  The Toronto Star's
# election-night table of 7 Oct 2011 (page R2, 269 of 288 polls: Alexander Brown NDP 4,743,
# Amy Brown FP 269) and Wikipedia's riding page (Alexander Brown 5,556, 12.85%; Amy Brown
# 297, 0.69%) put the larger total with the NDP candidate.
VOTE_CORRECTIONS = (
    VoteCorrection(date(2011, 10, 6), 101, "ALEXANDER BROWN", 297, 5556),
    VoteCorrection(date(2011, 10, 6), 101, "AMY BROWN", 5556, 297),
)


REPORTS = (
    ReportSpec(5, 521, 514, 519),
    ReportSpec(4, 510, 503, 508),
    ReportSpec(3, 499, 492, 497),
    ReportSpec(2, 488, 481, 486),
    ReportSpec(1, 932, 925, 930),
    ReportSpec(45, 1050, 1043, 1048),
    ReportSpec(48, 1096, 1089, 1094),
    ReportSpec(6, 532, 525, 530),
    ReportSpec(7, 876, 869, 874),
)


def _districts(regime: str, entries: tuple[tuple[int, str], ...]) -> tuple[DistrictSpec, ...]:
    return tuple(
        DistrictSpec(regime, number, f"on-{regime.removeprefix('ontario-')}-{number:03d}", name)
        for number, name in entries
    )


_DISTRICTS_1987 = _districts(
    "ontario-1987-130",
    (
        (3, "Beaches-Woodbine"),
        (17, "Don Mills"),
        (18, "Dovercourt"),
        (19, "Downsview"),
        (25, "Eglinton"),
        (29, "Etobicoke-Humber"),
        (30, "Etobicoke-Lakeshore"),
        (31, "Etobicoke-Rexdale"),
        (32, "Etobicoke West"),
        (34, "Fort York"),
        (45, "High Park-Swansea"),
        (54, "Lawrence"),
        (75, "Oakwood"),
        (76, "Oriole"),
        (84, "Parkdale"),
        (94, "Riverdale"),
        (95, "St. Andrew-St. Patrick"),
        (98, "St. George-St. David"),
        (101, "Scarborough-Agincourt"),
        (102, "Scarborough Centre"),
        (103, "Scarborough East"),
        (104, "Scarborough-Ellesmere"),
        (105, "Scarborough North"),
        (106, "Scarborough West"),
        (120, "Willowdale"),
        (121, "Wilson Heights"),
        (126, "York East"),
        (127, "York Mills"),
        (129, "York South"),
        (130, "Yorkview"),
    ),
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

DISTRICTS = _DISTRICTS_1987 + _DISTRICTS_1999 + _DISTRICTS_2007 + _DISTRICTS_2018

_NUMBERS_BY_REGIME = {
    regime: tuple(d.source_number for d in DISTRICTS if d.boundary_regime == regime)
    for regime in {d.boundary_regime for d in DISTRICTS}
}

EVENTS = (
    EventSpec(
        "on-1995-general",
        date(1995, 6, 8),
        "general",
        "ontario-1987-130",
        7,
        _NUMBERS_BY_REGIME["ontario-1987-130"],
        177,
    ),
    EventSpec(
        "on-1996-05-23-by-129",
        date(1996, 5, 23),
        "by_election",
        "ontario-1987-130",
        6,
        (129,),
        6,
    ),
    EventSpec(
        "on-1997-09-04-by-076",
        date(1997, 9, 4),
        "by_election",
        "ontario-1987-130",
        6,
        (76,),
        5,
    ),
    EventSpec(
        "on-1999-general",
        date(1999, 6, 3),
        "general",
        "ontario-1999-103",
        6,
        _NUMBERS_BY_REGIME["ontario-1999-103"],
        149,
    ),
    EventSpec(
        "on-2001-09-20-by-003",
        date(2001, 9, 20),
        "by_election",
        "ontario-1999-103",
        5,
        (3,),
        8,
    ),
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


@dataclass(frozen=True)
class TabulatedCandidate:
    name: str  # as printed in the official tabulation
    party: str  # the affiliation Elections Ontario reports for the candidacy
    votes: int


@dataclass(frozen=True)
class TabulationSpec:
    """A by-election carried by its official tabulation until a report group includes it.

    Elections Ontario adds a by-election to its CSV report groups only with the next general
    election.  Until then its "Vote Totals From Official Tabulation" PDF is the official result.
    This package reads no PDFs, so the district totals are transcribed here and the downloaded
    file is pinned by checksum: a different file fails the build instead of silently disagreeing
    with the transcription.  The tabulation prints no affiliations or elector count; affiliations
    come from Elections Ontario's results page for the district.  Turnout operands are reported
    together or not at all, so ballots cast stay null with the elector count; the rejected,
    unmarked and declined totals are kept with the transcription for audit.
    """

    event_id: str
    election_date: date
    boundary_regime: str
    district_number: int
    tabulation_url: str
    tabulation_sha256: str
    affiliations_url: str
    candidates: tuple[TabulatedCandidate, ...]
    rejected: int
    unmarked: int
    declined: int


TABULATION_RESOURCE = "Vote Totals From Official Tabulation"

TABULATIONS = (
    TabulationSpec(
        "on-2026-09-03-by-098",
        date(2026, 9, 3),
        "ontario-2018-124",
        98,
        "https://www.elections.on.ca/content/dam/NGW/sitecontent/2026/results/"
        "Vote%20Totals%20Report%20from%20Official%20Tabulation%20-%20Scarborough%20Southwest"
        "%20098.pdf",
        "d109b594e64851d8d6b00f4bf335752dfc86c21cb70819b599181905be59f998",
        "https://www.elections.on.ca/en/election-results/098.html",
        (
            TabulatedCandidate("BEKKERING, MARK", "Green Party of Ontario", 753),
            TabulatedCandidate("ELLIOTT, GORD", "Ontario Party", 237),
            TabulatedCandidate("HAFIZ, AHSANUL", "Ontario Liberal Party", 6674),
            TabulatedCandidate("PERDELWITZ, MICHAEL", "Independent", 129),
            TabulatedCandidate("REES, CHRIS", "New Blue Party of Ontario", 178),
            TabulatedCandidate("SHABAN, FATIMA", "New Democratic Party of Ontario", 8914),
            TabulatedCandidate("TARUN, NOOR", "Progressive Conservative Party of Ontario", 5148),
        ),
        rejected=34,
        unmarked=63,
        declined=16,
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


def tabulation_path(source_dir: str | Path, spec: TabulationSpec) -> Path:
    """Return the deterministic cache path for one official tabulation PDF."""
    return Path(source_dir) / "tabulations" / f"{spec.event_id}.pdf"


def download_ontario_tabulations(
    source_dir: str | Path,
    *,
    tabulations: tuple[TabulationSpec, ...] = TABULATIONS,
    session: requests.Session | None = None,
    overwrite: bool = False,
) -> tuple[Path, ...]:
    """Download each pinned official tabulation PDF atomically to its stable path."""
    return tuple(
        download_official_csv(
            spec.tabulation_url,
            tabulation_path(source_dir, spec),
            session=session,
            overwrite=overwrite,
        )
        for spec in tabulations
    )


def parse_tabulation(path: str | Path, spec: TabulationSpec) -> pd.DataFrame:
    """Normalize one pinned official tabulation into the adapter's result shape."""
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != spec.tabulation_sha256:
        raise ValueError(f"{spec.event_id}: official tabulation does not match its pinned checksum")
    if any(event.event_id == spec.event_id for event in EVENTS):
        raise ValueError(f"{spec.event_id}: a report group now carries this event")
    district_lookup = {
        (district.boundary_regime, district.source_number): district for district in DISTRICTS
    }
    district = district_lookup[(spec.boundary_regime, spec.district_number)]
    names = [candidate.name for candidate in spec.candidates]
    if len(set(names)) != len(names):
        raise ValueError(f"{spec.event_id}: tabulated candidate names must be unique")
    votes = [candidate.votes for candidate in spec.candidates]
    if votes.count(max(votes)) != 1:
        raise ValueError(f"{spec.event_id}: official tabulation must have one unique winner")
    source_detail = f"{spec.tabulation_url}; affiliations: {spec.affiliations_url}"
    rows = []
    for candidate in spec.candidates:
        independent = candidate.party in {"Independent", "No Affiliation"}
        rows.append(
            {
                "event_id": spec.event_id,
                "election_date": spec.election_date,
                "election_type": "by_election",
                "election_authority": "Elections Ontario",
                "represented_body": "Legislative Assembly of Ontario",
                "office_type": "mpp",
                "boundary_regime": spec.boundary_regime,
                "official_district_id": f"{district.source_number:03d}",
                "district_name": district.district_name,
                "candidate_name_raw": candidate.name,
                "party_name_raw": candidate.party,
                "affiliation_status": "independent" if independent else "party",
                "votes": candidate.votes,
                "elected": candidate.votes == max(votes),
                "incumbent_reported": pd.NA,
                "eligible_electors": pd.NA,
                "ballots_cast": pd.NA,
                "outcome_method": "vote",
                "coverage_status": "complete",
                "source_detail": source_detail,
                "source_resource": TABULATION_RESOURCE,
            }
        )
    result = pd.DataFrame(rows, columns=[*RESULT_COLUMNS, "source_resource"])
    for column in ("votes", "eligible_electors", "ballots_cast"):
        result[column] = pd.array(result[column], dtype="Int64")
    for column in ("elected", "incumbent_reported"):
        result[column] = pd.array(result[column], dtype="boolean")
    return result.sort_values(
        ["elected", "votes", "candidate_name_raw"], ascending=[False, False, True]
    ).reset_index(drop=True)


def _polling_date(value: object) -> date:
    return pd.to_datetime(str(value).strip(), format="%Y-%b-%d").date()


def _party_names(parties: pd.DataFrame) -> dict[tuple[int, str, str], str | None]:
    """Map (year, election type, code) to a party name.

    Older report groups hold several same-year by-elections whose party lists can spell a code
    differently.  Such a key maps to ``None`` and fails only if an in-scope Contest uses it.
    """
    names: dict[tuple[int, str, str], str | None] = {}
    conflicts: set[tuple[int, str, str]] = set()
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
        if key in conflicts:
            continue
        existing = names.get(key)
        if existing is not None and existing != name:
            conflicts.add(key)
            names[key] = None
            continue
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
    corrections = {
        (correction.polling_date, correction.district_number, correction.candidate_name): correction
        for correction in VOTE_CORRECTIONS
        if (correction.polling_date, correction.district_number) in event_lookup
    }
    applied: set[tuple[date, int, str]] = set()
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
            party_name = (
                party_names.get((event.election_date.year, event.election_type, code)) or code
            )
        else:
            affiliation_status = "party"
            party_key = (event.election_date.year, event.election_type, code)
            if party_key not in party_names:
                raise ValueError(f"no party name reported for political-interest code {code!r}")
            if party_names[party_key] is None:
                raise ValueError(f"political-interest code {code!r} has conflicting names")
            party_name = party_names[party_key]

        incumbent_raw = str(row.IsMemberOfPreviousLegislature).strip()
        incumbent = pd.NA if not incumbent_raw else bool(int(incumbent_raw))
        candidate_name = str(row.NameOfCandidates).strip()
        votes = int(row.TotalValidBallotsCast)
        correction = corrections.get((key[0], key[1], candidate_name))
        if correction is not None:
            if votes != correction.source_votes:
                raise ValueError(
                    f"Elections Ontario now reports {votes} votes for {candidate_name} "
                    f"({key[0]}, district {key[1]}); review the pinned vote correction"
                )
            votes = correction.corrected_votes
            applied.add((key[0], key[1], candidate_name))
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
                "candidate_name_raw": candidate_name,
                "party_name_raw": party_name,
                "affiliation_status": affiliation_status,
                "votes": votes,
                "elected": int(row.Plurality) > 0,
                "incumbent_reported": incumbent,
                "eligible_electors": stats[0],
                "ballots_cast": stats[1],
                "outcome_method": "vote",
                "coverage_status": "complete",
                "source_detail": source_detail,
            }
        )

    unapplied = sorted(set(corrections) - applied)
    if unapplied:
        raise ValueError(f"pinned vote correction matched no Elections Ontario row: {unapplied[0]}")

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
    tabulations: tuple[TabulationSpec, ...] = (),
    validate: bool = True,
) -> pd.DataFrame:
    """Load downloaded official report trios, then any pinned official tabulations."""
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
    if tabulations:
        results = pd.concat(
            [results]
            + [parse_tabulation(tabulation_path(source_dir, spec), spec) for spec in tabulations],
            ignore_index=True,
        )
    return results
