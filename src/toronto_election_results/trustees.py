"""Adapt Toronto school-board trustee workbooks to contest-level Candidacy rows.

The City's poll-by-poll trustee files do not have one stable physical layout:

* 2003 uses one worksheet per ``(trustee ward, City ward)`` pair;
* 2006--2018 usually puts several City-ward blocks on each trustee-ward sheet;
* 2022 still repeats blocks for trustee wards spanning more than one City ward.

This module hides those layouts behind :func:`parse_trustee_workbooks`.  It reads each block's
official ``Total`` column, then sums the repeated City-ward blocks to one row per Candidacy in one
trustee Contest.  Subdivision-level rows are never exposed.

Normalized result contract
--------------------------
``TRUSTEE_RESULT_COLUMNS`` is intentionally close to the shared Candidacy schema.  District,
Contest, and Candidacy registry identifiers are assigned by the shared integration layer; this
adapter supplies the authority's ``official_district_id`` and stable Election ``event_id``.

Party affiliation is always ``non_partisan`` and ``party_name_raw`` is null.  ``votes`` is nullable:
an Acclamation has no observed vote and therefore never becomes numeric zero.  ``elected`` is true
for a certified Acclamation or for the unique maximum of a certified single-seat vote result.
Ordinary vote Contests therefore have ``coverage_status=complete``.  A tied maximum preserves an
unknown elected outcome and ``coverage_status=partial`` pending an official declaration.  A void
Contest has no Candidacy row and is retained only in :func:`trustee_event_manifest`.

General-election parsing is local-only.  Callers can opt into downloading the eight official
by-election resources through :func:`load_trustee_results` or use the manifest's resource URLs to
manage acquisition separately.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile

import pandas as pd
import requests
from openpyxl.utils.exceptions import InvalidFileException

from .candidates import known_multiword_surnames, normalize_name
from .schema import stable_id

COVERAGE_END = date(2026, 8, 20)
ELECTION_AUTHORITY = "toronto_city_clerk"
OFFICE_TYPE = "trustee"

TDSB = "Toronto District School Board"
TCDSB = "Toronto Catholic District School Board"
VIAMONDE = "Conseil scolaire Viamonde"
MONAVENIR = "Conseil scolaire catholique MonAvenir"

_BOARD_CODE = {
    TDSB: "tdsb",
    TCDSB: "tcdsb",
    VIAMONDE: "viamonde",
    MONAVENIR: "monavenir",
}
_BOARD_ORDER = {body: order for order, body in enumerate(_BOARD_CODE)}

_GENERAL_ELECTION_DATES = {
    2003: date(2003, 11, 10),
    2006: date(2006, 11, 13),
    2010: date(2010, 10, 25),
    2014: date(2014, 10, 27),
    2018: date(2018, 10, 22),
    2022: date(2022, 10, 24),
}

_GENERAL_RESULT_URLS = {
    2003: "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/1ed53c9d-a316-465e-96ce-e72be74f8aa9/download/2003-results.zip",
    2006: "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3fb1227c-a279-4523-a1aa-f00190ba717f/download/2006-results.zip",
    2010: "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/6fbfaab0-bb84-442a-8e4b-1c14d4c10d6d/download/2010-results.zip",
    2014: "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip",
    2018: "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/2fcd5f20-90f5-4dd0-88eb-22e978b9bf89/download/2018-results.zip",
    2022: "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3ad371de-7c51-45d3-9ea4-0b4efac5fc2b/download/2022-results.zip",
}

_DECLARATION_URLS = {
    2003: "https://www.toronto.ca/wp-content/uploads/2017/08/9868-election-2003-clerkofficialdeclaration.pdf",
    2006: "https://www.toronto.ca/wp-content/uploads/2017/08/8f72-election-2006-clerksofficialdeclaration.pdf",
    2010: "https://www.toronto.ca/wp-content/uploads/2017/08/9783-election-2010-clerksofficialdeclaration.pdf",
    2014: "https://www.toronto.ca/wp-content/uploads/2017/08/9757-election-2014-declaration-trustee-ward4.pdf",
    2022: "https://www.toronto.ca/wp-content/uploads/2022/08/8e0d-Declaration-of-Acclamation.pdf",
}

TRUSTEE_RESULT_COLUMNS = (
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
    "candidate_name",
    "party_name_raw",
    "affiliation_status",
    "votes",
    "elected",
    "outcome_method",
    "coverage_status",
    "source_detail",
)

TRUSTEE_EVENT_COLUMNS = (
    "event_id",
    "election_date",
    "election_type",
    "election_authority",
    "represented_body",
    "office_type",
    "boundary_regime",
    "official_district_id",
    "district_name",
    "outcome_method",
    "coverage_status",
    "event_coverage",
    "resource_url",
    "local_source_available",
    "source_detail",
)


@dataclass(frozen=True)
class _Acclamation:
    candidate_name_raw: str
    source_url: str


# Each entry was checked against the City Clerk's official declaration, rather than inferred from
# a zero-vote/single-candidate worksheet.  Names use the exact source representation from the
# workbook where one exists; declaration-only Candidacies use the declaration's representation.
_ACCLAMATIONS: dict[tuple[int, str, int], _Acclamation] = {
    (2003, TDSB, 6): _Acclamation("Hill, Elizabeth", _DECLARATION_URLS[2003]),
    (2003, TDSB, 7): _Acclamation("Atkinson, Irene", _DECLARATION_URLS[2003]),
    (2003, TDSB, 11): _Acclamation("Matlow, Josh", _DECLARATION_URLS[2003]),
    (2003, TDSB, 14): _Acclamation("Ward, Sheila", _DECLARATION_URLS[2003]),
    (2003, TCDSB, 12): _Acclamation("Crawford, Paul", _DECLARATION_URLS[2003]),
    (2003, VIAMONDE, 2): _Acclamation("FRANCOIS GUERIN", _DECLARATION_URLS[2003]),
    (2003, VIAMONDE, 3): _Acclamation("DENYS BEGIN", _DECLARATION_URLS[2003]),
    (2003, VIAMONDE, 4): _Acclamation("ALAIN MASSON", _DECLARATION_URLS[2003]),
    (2003, MONAVENIR, 3): _Acclamation("D'Aigle, Claude", _DECLARATION_URLS[2003]),
    (2006, VIAMONDE, 4): _Acclamation("MASSON ALAIN", _DECLARATION_URLS[2006]),
    (2006, MONAVENIR, 4): _Acclamation("LEGERE CLAUDE", _DECLARATION_URLS[2006]),
    (2010, MONAVENIR, 3): _Acclamation("DUFOUR SÉGUIN NATHALIE", _DECLARATION_URLS[2010]),
    (2010, MONAVENIR, 4): _Acclamation("D'AIGLE CLAUDE-RENO", _DECLARATION_URLS[2010]),
    (2014, VIAMONDE, 4): _Acclamation("L'HEUREUX JEAN-FRANÇOIS", _DECLARATION_URLS[2014]),
    (2022, VIAMONDE, 2): _Acclamation("Benoit Fortin", _DECLARATION_URLS[2022]),
    (2022, VIAMONDE, 4): _Acclamation("Geneviève Oger", _DECLARATION_URLS[2022]),
    (2022, MONAVENIR, 3): _Acclamation("Nathalie Dufour Séguin", _DECLARATION_URLS[2022]),
}

_VOID_CONTESTS = {(2022, VIAMONDE, 3), (2022, MONAVENIR, 4)}

_GENERAL_WARDS = {
    TDSB: tuple(range(1, 23)),
    TCDSB: tuple(range(1, 13)),
    VIAMONDE: (2, 3, 4),
    MONAVENIR: (3, 4),
}

_BY_ELECTIONS = (
    (
        date(2012, 2, 27),
        TDSB,
        17,
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/79f831c8-48ec-45f2-a65e-3b514f877a93/download/2012-tdsb-wards-17-20.xls",
        2010,
    ),
    (
        date(2012, 2, 27),
        TDSB,
        20,
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/79f831c8-48ec-45f2-a65e-3b514f877a93/download/2012-tdsb-wards-17-20.xls",
        2010,
    ),
    (
        date(2012, 12, 10),
        TCDSB,
        8,
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/a75d576c-f315-4c90-b5c9-1ca7d9f8b51f/download/2012-tcdsb-ward-8.xls",
        2010,
    ),
    (
        date(2016, 1, 25),
        TDSB,
        21,
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/7b83316d-f2a7-4dbe-9b67-08138178c739/download/2016-tdsb-ward-21.xlsx",
        2014,
    ),
    (
        date(2016, 6, 20),
        TDSB,
        14,
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/0190932e-d817-4d8e-8634-8a1cc8cf5a9d/download/2016-tdsb-ward-14.xlsx",
        2014,
    ),
    (
        date(2016, 7, 25),
        TDSB,
        1,
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/836c4152-0603-4fd4-8ab4-a53cf386bc43/download/2016-tdsb-ward-1-.xlsx",
        2014,
    ),
    (
        date(2016, 7, 25),
        TDSB,
        5,
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/25343469-085b-4c9f-8a36-7d7f9115c630/download/2016-tdsb-ward-5.xlsx",
        2014,
    ),
    (
        date(2023, 1, 23),
        VIAMONDE,
        3,
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/ef7e9bbc-71ea-4d89-a412-a9ebad706fd7/download/2023-csv-ward-3-centre-csc-monavenir-ward-4-toronto-est.zip",
        2022,
    ),
    (
        date(2023, 1, 23),
        MONAVENIR,
        4,
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/ef7e9bbc-71ea-4d89-a412-a9ebad706fd7/download/2023-csv-ward-3-centre-csc-monavenir-ward-4-toronto-est.zip",
        2022,
    ),
    (
        date(2025, 3, 3),
        TDSB,
        11,
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/97d72233-8681-4b3d-828e-4929d40d122c/resource/7057b4fe-f71d-469b-bf61-c366895fc62e/download/2025-tdsb-ward-11.xlsx",
        2022,
    ),
)


def _by_election_resources() -> tuple[str, ...]:
    """Unique resource URLs in deterministic archive order."""
    return tuple(dict.fromkeys(resource_url for _, _, _, resource_url, _ in _BY_ELECTIONS))


def _resource_filename(resource_url: str) -> str:
    return Path(urlparse(resource_url).path).name


def _by_election_contests_for(resource_url: str) -> tuple[tuple[date, str, int, int], ...]:
    return tuple(
        (election_date, body, ward, regime_year)
        for election_date, body, ward, url, regime_year in _BY_ELECTIONS
        if url == resource_url
    )


_WARD_RE = re.compile(r"(?:school\s+)?ward\s*:?[ ]*(\d+)", re.IGNORECASE)
_YEAR_RE = re.compile(r"(?<!\d)(2003|2006|2010|2014|2018|2022)(?!\d)")
_HEADER_LABELS = {"name", "subdivision"}


def _cell_text(value: object) -> str:
    return "" if pd.isna(value) else " ".join(str(value).split())


def _engine_for(path: Path) -> str:
    return "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"


def _open_workbook(path: Path) -> pd.ExcelFile:
    """Open both genuine BIFF files and xlsx packages published with an .xls suffix."""
    try:
        return pd.ExcelFile(path, engine="openpyxl")
    except InvalidFileException, BadZipFile:
        return pd.ExcelFile(path, engine="xlrd")


def _year_for(path: Path) -> int:
    match = _YEAR_RE.search(path.as_posix())
    if match is None:
        raise ValueError(f"cannot identify trustee election year from {path}")
    return int(match.group(1))


def _body_for(path: Path) -> str:
    name = re.sub(r"[^a-z]+", " ", path.name.casefold())
    if "toronto catholic district school board" in name:
        return TCDSB
    if "toronto district school board" in name:
        return TDSB
    if "catholique" in name or "monavenir" in name:
        return MONAVENIR
    if "viamonde" in name or "centre sud ouest" in name:
        return VIAMONDE
    raise ValueError(f"not a board-specific trustee workbook: {path}")


def _boundary_regime(body: str, regime_year: int) -> str:
    return f"{_BOARD_CODE[body]}-trustee-wards-{regime_year}"


def _event_id(year: int) -> str:
    return stable_id("evt", ELECTION_AUTHORITY, _GENERAL_ELECTION_DATES[year], "general")


def _by_event_id(election_date: date, resource_url: str) -> str:
    event_scope = "+".join(
        f"{_BOARD_CODE[body]}-ward-{ward}"
        for contest_date, body, ward, _ in _by_election_contests_for(resource_url)
        if contest_date == election_date
    )
    if not event_scope:
        raise ValueError(f"resource does not contain a {election_date} by-election: {resource_url}")
    return stable_id(
        "evt",
        ELECTION_AUTHORITY,
        election_date,
        "by_election",
        event_scope,
    )


def _trustee_ward(raw: pd.DataFrame, sheet_name: str) -> int:
    match = _WARD_RE.search(sheet_name)
    if match is not None:
        return int(match.group(1))
    for row in range(min(4, len(raw))):
        for value in raw.iloc[row].dropna():
            match = _WARD_RE.search(_cell_text(value))
            if match is not None:
                return int(match.group(1))
    raise ValueError(f"cannot identify trustee ward from worksheet {sheet_name!r}")


def _header_rows(raw: pd.DataFrame) -> list[int]:
    return [
        idx
        for idx, value in raw.iloc[:, 0].items()
        if _cell_text(value).casefold() in _HEADER_LABELS
    ]


def _candidate_totals(workbook: pd.ExcelFile, sheet_names: Iterable[str]) -> dict[str, int]:
    """Sum candidate Total cells across every physical City-ward block supplied."""
    totals: dict[str, int] = {}
    for sheet_name in sheet_names:
        raw = workbook.parse(sheet_name, header=None)
        headers = _header_rows(raw)
        for position, header_idx in enumerate(headers):
            total_columns = [
                column
                for column, value in raw.iloc[header_idx].items()
                if _cell_text(value).casefold() == "total"
            ]
            if not total_columns:
                raise ValueError(f"no Total column in worksheet {sheet_name!r}")
            total_column = total_columns[-1]
            end = headers[position + 1] if position + 1 < len(headers) else len(raw)
            for row_idx in range(header_idx + 1, end):
                candidate = _cell_text(raw.iat[row_idx, 0])
                if not candidate:
                    continue
                if candidate.casefold() in _HEADER_LABELS or "total" in candidate.casefold():
                    continue
                votes = pd.to_numeric(raw.iat[row_idx, total_column], errors="coerce")
                if pd.isna(votes):
                    continue
                totals[candidate] = totals.get(candidate, 0) + int(votes)
    return totals


def _parse_workbook(path: Path) -> list[dict[str, object]]:
    year = _year_for(path)
    body = _body_for(path)
    workbook = pd.ExcelFile(path, engine=_engine_for(path))
    totals: dict[tuple[int, str], int] = {}

    for sheet_name in workbook.sheet_names:
        raw = workbook.parse(sheet_name, header=None)
        headers = _header_rows(raw)
        if not headers:  # Notice sheets and explicit-acclamation sheets have no vote table.
            continue
        ward = _trustee_ward(raw, sheet_name)
        for position, header_idx in enumerate(headers):
            total_columns = [
                column
                for column, value in raw.iloc[header_idx].items()
                if _cell_text(value).casefold() == "total"
            ]
            if not total_columns:
                raise ValueError(f"no Total column in {path}, worksheet {sheet_name!r}")
            total_column = total_columns[-1]
            end = headers[position + 1] if position + 1 < len(headers) else len(raw)
            for row_idx in range(header_idx + 1, end):
                candidate = _cell_text(raw.iat[row_idx, 0])
                if not candidate:
                    continue
                if candidate.casefold() in _HEADER_LABELS or "total" in candidate.casefold():
                    continue
                votes = pd.to_numeric(raw.iat[row_idx, total_column], errors="coerce")
                if pd.isna(votes):
                    continue
                key = (ward, candidate)
                totals[key] = totals.get(key, 0) + int(votes)

    source = f"{_GENERAL_RESULT_URLS[year]} :: {path.name}"
    return [
        _result_row(
            year=year,
            body=body,
            ward=ward,
            candidate_name_raw=candidate,
            votes=votes,
            elected=pd.NA,
            outcome_method="vote",
            coverage_status="partial",
            source_detail=source,
        )
        for (ward, candidate), votes in totals.items()
    ]


def _result_row(
    *,
    year: int,
    body: str,
    ward: int,
    candidate_name_raw: str,
    votes: object,
    elected: object,
    outcome_method: str,
    coverage_status: str,
    source_detail: str,
) -> dict[str, object]:
    return {
        "event_id": _event_id(year),
        "election_date": _GENERAL_ELECTION_DATES[year],
        "election_type": "general",
        "election_authority": ELECTION_AUTHORITY,
        "represented_body": body,
        "office_type": OFFICE_TYPE,
        "boundary_regime": _boundary_regime(body, year),
        "official_district_id": str(ward),
        "district_name": f"Ward {ward}",
        "candidate_name_raw": candidate_name_raw,
        "party_name_raw": pd.NA,
        "affiliation_status": "non_partisan",
        "votes": votes,
        "elected": elected,
        "outcome_method": outcome_method,
        "coverage_status": coverage_status,
        "source_detail": source_detail,
    }


def discover_trustee_workbooks(results_root: str | Path) -> tuple[Path, ...]:
    """Return the one board-specific local workbook for every available ``(year, board)``.

    The 2022 ``All_Offices`` workbook is deliberately excluded: it duplicates both English-board
    files and its readme states that it contains no French-board results.  Missing declaration-only
    Acclamations are supplied by :func:`parse_trustee_workbooks` for an included Election event.
    """
    results_root = Path(results_root)
    found: dict[tuple[int, str], Path] = {}
    for path in sorted(results_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".xls", ".xlsx"}:
            continue
        try:
            key = (_year_for(path), _body_for(path))
        except ValueError:
            continue
        previous = found.get(key)
        if previous is not None:
            raise ValueError(f"duplicate trustee workbooks for {key}: {previous} and {path}")
        found[key] = path
    return tuple(
        path
        for (_key, path) in sorted(
            found.items(), key=lambda item: (item[0][0], _BOARD_ORDER[item[0][1]])
        )
    )


def _with_certified_acclamations(
    rows: list[dict[str, object]], *, included_years: set[int]
) -> list[dict[str, object]]:
    by_contest: dict[tuple[int, str, int], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            row["election_date"].year,  # type: ignore[union-attr]
            str(row["represented_body"]),
            int(str(row["official_district_id"])),
        )
        by_contest.setdefault(key, []).append(row)

    for key, declaration in _ACCLAMATIONS.items():
        year, body, ward = key
        if year not in included_years:
            continue
        contest_rows = by_contest.get(key, [])
        if len(contest_rows) > 1:
            raise ValueError(f"certified Acclamation unexpectedly has multiple candidates: {key}")
        if contest_rows:
            row = contest_rows[0]
            row["votes"] = pd.NA
            row["elected"] = True
            row["outcome_method"] = "acclamation"
            row["coverage_status"] = "complete"
            row["source_detail"] = declaration.source_url
        else:
            row = _result_row(
                year=year,
                body=body,
                ward=ward,
                candidate_name_raw=declaration.candidate_name_raw,
                votes=pd.NA,
                elected=True,
                outcome_method="acclamation",
                coverage_status="complete",
                source_detail=declaration.source_url,
            )
            rows.append(row)
            by_contest[key] = [row]
    return rows


def _with_certified_vote_outcomes(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Apply single-seat plurality to complete certified vote totals, preserving tied uncertainty."""
    by_contest: dict[tuple[object, object, object], list[dict[str, object]]] = {}
    for row in rows:
        if row["outcome_method"] != "vote":
            continue
        key = (row["event_id"], row["represented_body"], row["official_district_id"])
        by_contest.setdefault(key, []).append(row)

    for contest_rows in by_contest.values():
        maximum = max(int(row["votes"]) for row in contest_rows)
        leaders = [row for row in contest_rows if int(row["votes"]) == maximum]
        for row in contest_rows:
            is_leader = any(row is leader for leader in leaders)
            row["elected"] = pd.NA if is_leader else False
            row["coverage_status"] = "partial" if len(leaders) > 1 else "complete"
        if len(leaders) == 1:
            leaders[0]["elected"] = True
    return rows


def _result_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=TRUSTEE_RESULT_COLUMNS)
    frame["party_name_raw"] = frame["party_name_raw"].astype("string")
    frame["votes"] = pd.array(frame["votes"], dtype="Int64")
    frame["elected"] = pd.array(frame["elected"], dtype="boolean")
    if frame.empty:
        return frame
    known_surnames = known_multiword_surnames(frame["candidate_name_raw"])
    frame["candidate_name"] = [
        normalize_name(str(name), known_surnames=known_surnames)[0]
        for name in frame["candidate_name_raw"]
    ]
    frame["_body_order"] = frame["represented_body"].map(_BOARD_ORDER)
    frame["_ward_order"] = pd.to_numeric(frame["official_district_id"])
    frame = frame.sort_values(
        ["election_date", "_body_order", "_ward_order", "candidate_name_raw"],
        kind="stable",
    ).drop(columns=["_body_order", "_ward_order"])
    return frame.reset_index(drop=True)


def parse_trustee_workbooks(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Parse explicit local workbook paths into normalized contest-level Candidacy rows.

    Supplying any workbook for a general Election event opts that event into the result.  The
    adapter then adds or corrects that event's declaration-certified Acclamations, including the
    2003 Viamonde and 2022 French-board Candidacies that have no poll-by-poll workbook.  It does not
    synthesize Candidacies for void Contests.

    Raises ``ValueError`` for an unidentifiable workbook, a missing ``Total`` column, or a certified
    Acclamation that unexpectedly contains multiple candidates.
    """
    resolved = [Path(path) for path in paths]
    included_years = {_year_for(path) for path in resolved}
    rows = [row for path in resolved for row in _parse_workbook(path)]
    rows = _with_certified_acclamations(rows, included_years=included_years)
    return _result_frame(_with_certified_vote_outcomes(rows))


def _by_election_row(
    *,
    event_id: str,
    election_date: date,
    body: str,
    ward: int,
    regime_year: int,
    candidate_name_raw: str,
    votes: int,
    source_detail: str,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "election_date": election_date,
        "election_type": "by_election",
        "election_authority": ELECTION_AUTHORITY,
        "represented_body": body,
        "office_type": OFFICE_TYPE,
        "boundary_regime": _boundary_regime(body, regime_year),
        "official_district_id": str(ward),
        "district_name": f"Ward {ward}",
        "candidate_name_raw": candidate_name_raw,
        "party_name_raw": pd.NA,
        "affiliation_status": "non_partisan",
        "votes": votes,
        "elected": pd.NA,
        "outcome_method": "vote",
        "coverage_status": "partial",
        "source_detail": source_detail,
    }


def _by_rows_from_workbook(
    workbook: pd.ExcelFile,
    contests: tuple[tuple[date, str, int, int], ...],
    *,
    resource_url: str,
    source_detail: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if len(contests) == 1:
        election_date, body, ward, regime_year = contests[0]
        selected = workbook.sheet_names
        totals = _candidate_totals(workbook, selected)
        if not totals:
            raise ValueError(f"no candidate totals in trustee by-election source {source_detail}")
        return [
            _by_election_row(
                event_id=_by_event_id(election_date, resource_url),
                election_date=election_date,
                body=body,
                ward=ward,
                regime_year=regime_year,
                candidate_name_raw=candidate,
                votes=votes,
                source_detail=source_detail,
            )
            for candidate, votes in totals.items()
        ]

    sheets_by_ward: dict[int, list[str]] = {}
    for sheet_name in workbook.sheet_names:
        raw = workbook.parse(sheet_name, header=None)
        if not _header_rows(raw):
            continue
        ward = _trustee_ward(raw, sheet_name)
        sheets_by_ward.setdefault(ward, []).append(sheet_name)
    for election_date, body, ward, regime_year in contests:
        selected = sheets_by_ward.get(ward, [])
        if not selected:
            raise ValueError(f"no worksheet for trustee Ward {ward} in {source_detail}")
        totals = _candidate_totals(workbook, selected)
        rows.extend(
            _by_election_row(
                event_id=_by_event_id(election_date, resource_url),
                election_date=election_date,
                body=body,
                ward=ward,
                regime_year=regime_year,
                candidate_name_raw=candidate,
                votes=votes,
                source_detail=source_detail,
            )
            for candidate, votes in totals.items()
        )
    return rows


def _parse_by_election_source(path: Path, resource_url: str) -> list[dict[str, object]]:
    contests = _by_election_contests_for(resource_url)
    if path.suffix.lower() != ".zip":
        return _by_rows_from_workbook(
            _open_workbook(path),
            contests,
            resource_url=resource_url,
            source_detail=resource_url,
        )

    rows: list[dict[str, object]] = []
    with ZipFile(path) as archive:
        members = [
            member for member in archive.namelist() if member.lower().endswith((".xls", ".xlsx"))
        ]
        for contest in contests:
            election_date, body, ward, regime_year = contest
            matching = [member for member in members if _body_for(Path(member)) == body]
            if len(matching) != 1:
                raise ValueError(f"expected one {body} workbook in {path}, found {len(matching)}")
            workbook = pd.ExcelFile(BytesIO(archive.read(matching[0])), engine="openpyxl")
            rows.extend(
                _by_rows_from_workbook(
                    workbook,
                    ((election_date, body, ward, regime_year),),
                    resource_url=resource_url,
                    source_detail=f"{resource_url} :: {matching[0]}",
                )
            )
    return rows


def discover_trustee_by_election_sources(source_root: str | Path) -> tuple[Path, ...]:
    """Return recognized, already-downloaded trustee by-election resources in archive order."""
    source_root = Path(source_root)
    return tuple(
        source_root / _resource_filename(resource_url)
        for resource_url in _by_election_resources()
        if (source_root / _resource_filename(resource_url)).is_file()
    )


def parse_trustee_by_elections(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Parse explicit official by-election files, including the 2023 two-board ZIP."""
    url_by_filename = {
        _resource_filename(resource_url): resource_url for resource_url in _by_election_resources()
    }
    rows: list[dict[str, object]] = []
    for value in paths:
        path = Path(value)
        try:
            resource_url = url_by_filename[path.name]
        except KeyError as exc:
            raise ValueError(f"unknown trustee by-election resource: {path}") from exc
        rows.extend(_parse_by_election_source(path, resource_url))
    return _result_frame(_with_certified_vote_outcomes(rows))


def download_trustee_by_elections(
    destination: str | Path,
    *,
    session: requests.Session | None = None,
    overwrite: bool = False,
) -> tuple[Path, ...]:
    """Download all eight official trustee by-election resources atomically and idempotently."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    client = session or requests
    paths = []
    for resource_url in _by_election_resources():
        path = destination / _resource_filename(resource_url)
        paths.append(path)
        if path.exists() and not overwrite:
            continue
        temporary = path.with_suffix(path.suffix + ".part")
        try:
            with client.get(resource_url, stream=True, timeout=300) as response:
                response.raise_for_status()
                with temporary.open("wb") as stream:
                    for chunk in response.iter_content(chunk_size=1 << 16):
                        if chunk:
                            stream.write(chunk)
            temporary.replace(path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    return tuple(paths)


def load_trustee_results(
    *,
    results_root: str | Path = Path("data/interim/results"),
    by_election_root: str | Path = Path("data/raw/trustee_byelections"),
    download: bool = False,
    session: requests.Session | None = None,
    overwrite: bool = False,
) -> pd.DataFrame:
    """Load all local trustee results, optionally acquiring missing by-election resources."""
    if download:
        download_trustee_by_elections(by_election_root, session=session, overwrite=overwrite)
    general = parse_trustee_workbooks(discover_trustee_workbooks(results_root))
    by_elections = parse_trustee_by_elections(
        discover_trustee_by_election_sources(by_election_root)
    )
    return _result_frame(
        pd.concat([general, by_elections], ignore_index=True).to_dict(orient="records")
    )


def _local_source_pairs(results_root: str | Path | None) -> set[tuple[int, str]]:
    if results_root is None or not Path(results_root).exists():
        return set()
    return {(_year_for(path), _body_for(path)) for path in discover_trustee_workbooks(results_root)}


def _general_manifest_rows(local_pairs: set[tuple[int, str]]) -> list[dict[str, object]]:
    rows = []
    for year, election_date in _GENERAL_ELECTION_DATES.items():
        for body, wards in _GENERAL_WARDS.items():
            for ward in wards:
                key = (year, body, ward)
                acclamation = _ACCLAMATIONS.get(key)
                if key in _VOID_CONTESTS:
                    outcome_method = "void"
                    coverage_status = "complete"
                    resource_url = (
                        "https://www.toronto.ca/wp-content/uploads/2022/10/"
                        "9085-FinalDeclaration-of-Results-for-the-2022-Toronto-Municipal-Election.pdf"
                    )
                elif acclamation is not None:
                    outcome_method = "acclamation"
                    coverage_status = "complete"
                    resource_url = acclamation.source_url
                else:
                    outcome_method = "vote"
                    coverage_status = (
                        "complete" if (year, body) in local_pairs else "source_missing"
                    )
                    resource_url = _GENERAL_RESULT_URLS[year]
                rows.append(
                    {
                        "event_id": _event_id(year),
                        "election_date": election_date,
                        "election_type": "general",
                        "election_authority": ELECTION_AUTHORITY,
                        "represented_body": body,
                        "office_type": OFFICE_TYPE,
                        "boundary_regime": _boundary_regime(body, year),
                        "official_district_id": str(ward),
                        "district_name": f"Ward {ward}",
                        "outcome_method": outcome_method,
                        "coverage_status": coverage_status,
                        "event_coverage": "complete",
                        "resource_url": resource_url,
                        "local_source_available": (year, body) in local_pairs,
                        "source_detail": resource_url,
                    }
                )
    return rows


def _by_election_manifest_rows(local_urls: set[str]) -> list[dict[str, object]]:
    rows = []
    for election_date, body, ward, resource_url, regime_year in _BY_ELECTIONS:
        is_local = resource_url in local_urls
        rows.append(
            {
                "event_id": _by_event_id(election_date, resource_url),
                "election_date": election_date,
                "election_type": "by_election",
                "election_authority": ELECTION_AUTHORITY,
                "represented_body": body,
                "office_type": OFFICE_TYPE,
                "boundary_regime": _boundary_regime(body, regime_year),
                "official_district_id": str(ward),
                "district_name": f"Ward {ward}",
                "outcome_method": "vote",
                "coverage_status": "complete" if is_local else "source_missing",
                "event_coverage": "complete",
                "resource_url": resource_url,
                "local_source_available": is_local,
                "source_detail": (
                    resource_url
                    if is_local
                    else f"Official resource indexed but not downloaded: {resource_url}"
                ),
            }
        )
    return rows


def trustee_event_manifest(
    *,
    results_root: str | Path | None = None,
    by_election_root: str | Path | None = None,
    through: date = COVERAGE_END,
) -> pd.DataFrame:
    """Return deterministic general-Contest hooks and by-election resource selectors.

    General rows enumerate all four boards, including Acclamations and void Contests with no vote
    rows.  By-election rows enumerate the City's official archive from 2012 through 2025.  Their
    ``coverage_status`` is ``source_missing`` until callers download and parse the resource.
    """
    local_pairs = _local_source_pairs(results_root)
    local_by_election_urls = {
        resource_url
        for resource_url in _by_election_resources()
        if by_election_root is not None
        and (Path(by_election_root) / _resource_filename(resource_url)).is_file()
    }
    frame = pd.DataFrame(
        _general_manifest_rows(local_pairs) + _by_election_manifest_rows(local_by_election_urls),
        columns=TRUSTEE_EVENT_COLUMNS,
    )
    frame = frame[frame["election_date"] <= through].copy()
    frame["local_source_available"] = pd.array(frame["local_source_available"], dtype="boolean")
    frame["_body_order"] = frame["represented_body"].map(_BOARD_ORDER)
    frame["_ward_order"] = pd.to_numeric(frame["official_district_id"])
    frame = frame.sort_values(["election_date", "_body_order", "_ward_order"], kind="stable").drop(
        columns=["_body_order", "_ward_order"]
    )
    return frame.reset_index(drop=True)


def select_trustee_events(
    manifest: pd.DataFrame,
    *,
    election_type: str | None = None,
    represented_body: str | None = None,
    local_source_available: bool | None = None,
) -> pd.DataFrame:
    """Filter a trustee manifest without changing its deterministic ordering."""
    selected = pd.Series(True, index=manifest.index)
    if election_type is not None:
        selected &= manifest["election_type"].eq(election_type)
    if represented_body is not None:
        selected &= manifest["represented_body"].eq(represented_body)
    if local_source_available is not None:
        selected &= manifest["local_source_available"].eq(local_source_available)
    return manifest.loc[selected].reset_index(drop=True)


def trustee_event_coverage_manifest() -> pd.DataFrame:
    """Document archive-level coverage, including the accepted 2003--2011 uncertainty."""
    return pd.DataFrame(
        [
            {
                "start_date": date(2003, 1, 1),
                "end_date": date(2011, 12, 31),
                "election_type": "by_election",
                "event_coverage": "uncertain",
                "source_detail": "The City's official trustee by-election index begins in 2012.",
            },
            {
                "start_date": date(2012, 1, 1),
                "end_date": COVERAGE_END,
                "election_type": "by_election",
                "event_coverage": "complete",
                "source_detail": (
                    "City of Toronto Elections - Official By-Election Results resource index."
                ),
            },
        ]
    )
