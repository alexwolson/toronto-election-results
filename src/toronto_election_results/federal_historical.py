"""Elections Canada results for 1993-2003, before the poll-by-poll CSV era.

Three official sources cover the federal elections between the last general election before
amalgamation and the 2004 adapter in :mod:`federal`:

- the 1993 general election comes from Elections Canada's Recapitulation of Votes data files,
  released through the University of Toronto Map & Data Library with Elections Canada's
  permission;
- the 1997 and 2000 general elections come from Elections Canada's poll-by-poll result files
  (``CAND`` and ``EDSUM``), which carry district codes, electors, rejected ballots and the
  elected and incumbent indicators;
- the 1999 York West by-election is pinned from the Chief Electoral Officer's official voting
  results report, checked against the report's bytes;
- the March 25, 1996 Etobicoke North by-election is pinned from Elections Canada's official
  voting results synopsis for the 1996 by-elections, checked against the archived pages' text.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from .federal import (
    ELECTION_AUTHORITY,
    NORMALIZED_COLUMNS,
    OFFICE_TYPE,
    REPRESENTED_BODY,
    _affiliation_status,
)

RO_1987 = "federal-1987-representation-order"
RO_1996 = "federal-1996-representation-order"

MDL_1993_URL = (
    "https://mdl.library.utoronto.ca/sites/default/public/mdldata/open/canada/national/"
    "elections_canada/official_voting_results/1993results.zip"
)
POLL_FILES_CAND_URL = "https://www.elections.ca/res/rep/off/37p/CAND.ZIP"
POLL_FILES_EDSUM_URL = "https://www.elections.ca/res/rep/off/37p/EDSUM.ZIP"
BY_1996_CANDIDATES_URL = (
    "https://www.elections.ca/content.aspx?section=res&dir=rep/off/dec1396"
    "&document=synopsis2&lang=e"
)
BY_1996_TOTALS_URL = (
    "https://www.elections.ca/content.aspx?section=res&dir=rep/off/dec1396"
    "&document=synopsis1a&lang=e"
)
BY_1999_URL = (
    "https://bac-lac.wayback.archive-it.org/web/20061212070736/"
    "http://dsp-psd.pwgsc.gc.ca/Collection/SE1-2-1999-2.pdf"
)

SOURCE_SHA256 = {
    MDL_1993_URL: "40dc5a1c2c498d63f37f1a8ef744abdab31f2056d1900d91a9d927cb4f5466fa",
    POLL_FILES_CAND_URL: "612c9a0dacc666af04de70ee031bf80abcd8a47caea62a0e4aa548fbcff2a7b4",
    POLL_FILES_EDSUM_URL: "f4e6d903bb7f3b0023cf12c334771a170e2d76aa628ec38fe194d20bc0b9a61b",
    BY_1999_URL: "cd9b9c7397b958d0fae2c199de23afa59e30af360f0bcf3cc07d5d4310cc0306",
}
SOURCE_FILENAMES = {
    MDL_1993_URL: "1993results.zip",
    POLL_FILES_CAND_URL: "CAND.ZIP",
    POLL_FILES_EDSUM_URL: "EDSUM.ZIP",
    BY_1999_URL: "SE1-2-1999-2.pdf",
    BY_1996_CANDIDATES_URL: "dec1396-synopsis2.html",
    BY_1996_TOTALS_URL: "dec1396-synopsis1a.html",
}
# Elections Canada serves these archived pages from a CMS, so their bytes can change; the
# adapter checks that every pinned figure appears in the page text instead of a checksum.
TEXT_VERIFIED_SOURCES = (BY_1996_CANDIDATES_URL, BY_1996_TOTALS_URL)

RESOURCE_1993 = "Official Voting Results 1993 — Recapitulation of Votes Data Files"
RESOURCE_POLL_FILES = "Poll-by-poll Result Files, 1997 and 2000 General Elections"
RESOURCE_BY_1999 = "By-elections 1999: Official Voting Results (SE1-2/1999-2)"
RESOURCE_BY_1996 = "By-elections 1996: Official Voting Results — Synopsis"

# Elections Canada's 1993 district codes for the 23 Toronto districts of the 1987 order.
TORONTO_1987 = (
    ("01077", "Beaches—Woodbine"),
    ("01078", "Broadview—Greenwood"),
    ("01079", "Davenport"),
    ("01080", "Don Valley East"),
    ("01081", "Don Valley North"),
    ("01082", "Don Valley West"),
    ("01083", "Eglinton—Lawrence"),
    ("01084", "Etobicoke Centre"),
    ("01085", "Etobicoke—Lakeshore"),
    ("01086", "Etobicoke North"),
    ("01087", "Parkdale—High Park"),
    ("01088", "Rosedale"),
    ("01089", "St. Paul's"),
    ("01090", "Scarborough—Agincourt"),
    ("01091", "Scarborough Centre"),
    ("01092", "Scarborough East"),
    ("01093", "Scarborough—Rouge River"),
    ("01094", "Scarborough West"),
    ("01095", "Trinity—Spadina"),
    ("01096", "Willowdale"),
    ("01097", "York Centre"),
    ("01098", "York South—Weston"),
    ("01099", "York West"),
)

# The 22 Toronto districts of the 1996 order, with Elections Canada's district codes. A District
# keeps one name per Boundary regime, so 35008 keeps its 1996 name, Broadview—Greenwood, for the
# 2000 election, which Elections Canada ran under its new name, Toronto—Danforth.
TORONTO_1996 = (
    ("35003", "Beaches—East York"),
    ("35008", "Broadview—Greenwood"),
    ("35012", "Davenport"),
    ("35013", "Don Valley East"),
    ("35014", "Don Valley West"),
    ("35017", "Eglinton—Lawrence"),
    ("35021", "Etobicoke Centre"),
    ("35022", "Etobicoke—Lakeshore"),
    ("35023", "Etobicoke North"),
    ("35064", "Parkdale—High Park"),
    ("35073", "Scarborough—Agincourt"),
    ("35074", "Scarborough Centre"),
    ("35075", "Scarborough East"),
    ("35076", "Scarborough—Rouge River"),
    ("35077", "Scarborough Southwest"),
    ("35081", "St. Paul's"),
    ("35090", "Toronto Centre—Rosedale"),
    ("35091", "Trinity—Spadina"),
    ("35097", "Willowdale"),
    ("35100", "York Centre"),
    ("35102", "York South—Weston"),
    ("35103", "York West"),
)


@dataclass(frozen=True)
class HistoricalFederalEvent:
    event_id: str
    election_date: date
    election_type: str
    boundary_regime: str
    districts: tuple[tuple[str, str], ...]
    source_url: str | None
    expected_candidate_rows: int


HISTORICAL_FEDERAL_EVENTS = (
    HistoricalFederalEvent(
        "ec-ge-35", date(1993, 10, 25), "general", RO_1987, TORONTO_1987, MDL_1993_URL, 214
    ),
    HistoricalFederalEvent(
        "ec-be-1996-03-25",
        date(1996, 3, 25),
        "by_election",
        RO_1987,
        (("01086", "Etobicoke North"),),
        BY_1996_CANDIDATES_URL,
        7,
    ),
    HistoricalFederalEvent(
        "ec-ge-36", date(1997, 6, 2), "general", RO_1996, TORONTO_1996, POLL_FILES_CAND_URL, 150
    ),
    HistoricalFederalEvent(
        "ec-be-1999-11-15",
        date(1999, 11, 15),
        "by_election",
        RO_1996,
        (("35103", "York West"),),
        BY_1999_URL,
        6,
    ),
    HistoricalFederalEvent(
        "ec-ge-37", date(2000, 11, 27), "general", RO_1996, TORONTO_1996, POLL_FILES_CAND_URL, 151
    ),
)
_POLL_FILE_EVENTS = {"ec-ge-36": "3600", "ec-ge-37": "3700"}

# Section 1 tables of the 1996 by-election synopsis: candidates (synopsis2) and Table 2 (synopsis1a).
_ETOBICOKE_NORTH_1996 = {
    "eligible_electors": 60_968,
    "rejected": 227,
    "candidates": (
        ("Roy Cullen", "Liberal Party of Canada", 12_290),
        ("Joe Peschisolido", "Reform Party of Canada", 9_563),
        ("Mario Annecchini", "Progressive Conservative Party of Canada", 2_812),
        ("Maxine Caron", "New Democratic Party", 1_400),
        ("Ron Gray", "Christian Heritage Party of Canada", 284),
        ("Sylvie Charbin", "No Affiliation", 96),
        ("John C. Turmel", "Abolitionist Party of Canada", 75),
    ),
}

# Table 5 and the poll-by-poll totals of the 1999 by-election report.
_YORK_WEST_1999 = {
    "eligible_electors": 49_959,
    "rejected": 154,
    "candidates": (
        ("Stephen Burega", "Canadian Action", 242),
        ("Elio Di Iorio", "Progressive Conservative", 1_721),
        ("Enzo Granzotto", "Reform", 377),
        ("Julia McCrea", "N.D.P.", 1_054),
        ("Judy Sgro", "Liberal", 10_034),
        ("Henry Zeifman", "Green Party", 101),
    ),
}


def historical_source_path(source_dir: str | Path, url: str) -> Path:
    return Path(source_dir) / "historical" / SOURCE_FILENAMES[url]


def download_historical_federal_sources(source_dir: str | Path, *, overwrite: bool = False) -> None:
    """Fetch and checksum every historical source file not already cached."""

    for url in (*SOURCE_SHA256, *TEXT_VERIFIED_SOURCES):
        path = historical_source_path(source_dir, url)
        if path.is_file() and not overwrite:
            continue
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        if url in SOURCE_SHA256:
            digest = hashlib.sha256(response.content).hexdigest()
            if digest != SOURCE_SHA256[url]:
                raise ValueError(f"checksum mismatch for {url}: {digest}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)


def _verified_bytes(source_dir: str | Path, url: str) -> bytes:
    path = historical_source_path(source_dir, url)
    if not path.is_file():
        raise FileNotFoundError(f"Missing official federal source file: {path}")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SOURCE_SHA256[url]:
        raise ValueError(f"checksum mismatch for {path}: {digest}")
    return data


def _page_text(source_dir: str | Path, url: str) -> str:
    path = historical_source_path(source_dir, url)
    if not path.is_file():
        raise FileNotFoundError(f"Missing official federal source file: {path}")
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw)).replace("\xa0", " ")
    return " ".join(text.split())


def _figure(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _dash(name: str) -> str:
    return " ".join(name.replace("--", "—").split())


def _tilde_records(data: bytes) -> list[list[str]]:
    text = data.decode("cp850").replace("\x00", "")
    return [row for row in csv.reader(io.StringIO(text), quotechar="~") if row]


def _event_frame(event: HistoricalFederalEvent, rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["event_id"] = event.event_id
    frame["election_date"] = event.election_date
    frame["election_type"] = event.election_type
    frame["election_authority"] = ELECTION_AUTHORITY
    frame["represented_body"] = REPRESENTED_BODY
    frame["office_type"] = OFFICE_TYPE
    frame["boundary_regime"] = event.boundary_regime
    frame["turnout_scope"] = "federal_electoral_district"
    frame["outcome_method"] = "vote"
    frame["coverage_status"] = "complete"
    frame["source_authority"] = ELECTION_AUTHORITY
    frame["affiliation_status"] = frame["party_name_raw"].map(_affiliation_status)
    return frame[NORMALIZED_COLUMNS]


def _unique_maximum_winner(frame: pd.DataFrame) -> pd.Series:
    maxima = frame.groupby("official_district_id")["votes"].transform("max")
    winners = frame["votes"].eq(maxima)
    ties = winners.groupby(frame["official_district_id"]).transform("sum").gt(1)
    if ties.any():
        raise ValueError("historical federal contest has a tied maximum; winner is not derivable")
    return winners


def parse_1993_results(data: bytes, event: HistoricalFederalEvent) -> pd.DataFrame:
    """Read the 1993 candidate, party and grand-total vote records from the MDL archive."""

    names = dict(event.districts)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        cand = _tilde_records(archive.read("canelr93/tcand.txt"))
        parties = _tilde_records(archive.read("canelr93/tparty.txt"))
        raw = _tilde_records(archive.read("canelr93/ersraw.txt"))
    party_names = {row[1]: row[2] for row in parties if len(row) > 2}
    totals: dict[str, dict[str, int]] = {}
    for row in raw:
        if len(row) >= 6 and row[1] in names and row[3] == "6T":
            totals.setdefault(row[1], {})[row[4]] = int(row[5] or 0)
    rows = []
    for row in cand:
        if len(row) < 9 or row[2] not in names:
            continue
        district, sequence = row[2], row[4]
        votes = totals[district][sequence]
        rows.append(
            {
                "official_district_id": district,
                "district_name": names[district],
                "candidate_name_raw": " ".join(f"{row[6]} {row[5]}".split()),
                "party_name_raw": party_names[row[8]],
                "votes": votes,
                "incumbent_reported": pd.NA,
                "eligible_electors": totals[district]["EL"],
                "ballots_cast": totals[district]["TC"],
                "source_resource": RESOURCE_1993,
                "source_detail": f"{MDL_1993_URL}#canelr93/tcand.txt,canelr93/ersraw.txt",
            }
        )
    frame = pd.DataFrame(rows)
    for district, values in totals.items():
        candidate_votes = sum(v for k, v in values.items() if k not in {"EL", "RJ", "TC", "TV"})
        if candidate_votes != values["TV"] or values["TC"] != values["TV"] + values["RJ"]:
            raise ValueError(f"1993 totals do not reconcile for district {district}")
    frame["elected"] = _unique_maximum_winner(frame)
    return _event_frame(event, frame.to_dict("records"))


def _tab_records(data: bytes, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        name = next(n for n in archive.namelist() if n.casefold() == member)
        text = archive.read(name).decode("cp1252")
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def parse_poll_file_results(
    cand_data: bytes, edsum_data: bytes, event: HistoricalFederalEvent
) -> pd.DataFrame:
    """Read one general election from Elections Canada's 1997/2000 poll-by-poll result files."""

    event_number = _POLL_FILE_EVENTS[event.event_id]
    names = dict(event.districts)

    def district_id(code: str) -> str | None:
        if not code.startswith("ED35-"):
            return None
        candidate = "35" + code.removeprefix("ED35-")
        return candidate if candidate in names else None

    summaries = {}
    for row in _tab_records(edsum_data, "edsum.txt"):
        district = district_id(row["ed_code"])
        if row["event_number"] == event_number and district:
            summaries[district] = row
    rows = []
    for row in _tab_records(cand_data, "cand.txt"):
        district = district_id(row["ed_code"])
        if row["event_number"] != event_number or not district:
            continue
        summary = summaries[district]
        name = " ".join(
            part.strip()
            for part in (
                row["candidate_first_name"],
                row["candidate_middle_name"],
                row["candidate_last_name"],
            )
            if part and part.strip()
        )
        rows.append(
            {
                "official_district_id": district,
                "district_name": names[district],
                "candidate_name_raw": name,
                "party_name_raw": row["candidate_party_english_name"].strip(),
                "votes": int(row["candidate_vote"]),
                "elected": row["elected_indicator"].strip() == "Y",
                "incumbent_reported": row["incumbent_indicator"].strip() == "Y",
                "eligible_electors": int(summary["ed_electors_on_list_count"]),
                "ballots_cast": int(summary["ed_valid_vote_count"])
                + int(summary["ed_rejected_ballot_count"]),
                "source_resource": RESOURCE_POLL_FILES,
                "source_detail": (
                    f"{POLL_FILES_CAND_URL}#event_number={event_number};"
                    f"{POLL_FILES_EDSUM_URL}#event_number={event_number}"
                ),
            }
        )
    frame = pd.DataFrame(rows)
    sums = frame.groupby("official_district_id")["votes"].sum()
    for district, summary in summaries.items():
        if int(sums[district]) != int(summary["ed_valid_vote_count"]):
            raise ValueError(f"{event.event_id} candidate votes do not reconcile for {district}")
    return _event_frame(event, frame.to_dict("records"))


def parse_etobicoke_north_1996(
    candidates_text: str, totals_text: str, event: HistoricalFederalEvent
) -> pd.DataFrame:
    """Return the pinned 1996 Etobicoke North tabulation once both pages confirm it."""

    pinned = _ETOBICOKE_NORTH_1996
    valid = sum(votes for _, _, votes in pinned["candidates"])
    for name, _, votes in pinned["candidates"]:
        if f"{name} (" not in candidates_text or _figure(votes) not in candidates_text:
            raise ValueError(f"1996 Etobicoke North page no longer shows {name} with {votes}")
    row = (
        f"Etobicoke North/Etobicoke-Nord 103 014 {_figure(pinned['eligible_electors'])} "
        f"{_figure(valid)} {_figure(pinned['rejected'])} {_figure(valid + pinned['rejected'])}"
    )
    if row not in totals_text:
        raise ValueError("1996 Etobicoke North Table 2 row no longer matches the pinned totals")
    winner = max(votes for _, _, votes in pinned["candidates"])
    rows = [
        {
            "official_district_id": "01086",
            "district_name": "Etobicoke North",
            "candidate_name_raw": name,
            "party_name_raw": party,
            "votes": votes,
            "elected": votes == winner,
            "incumbent_reported": pd.NA,
            "eligible_electors": pinned["eligible_electors"],
            "ballots_cast": valid + pinned["rejected"],
            "source_resource": RESOURCE_BY_1996,
            "source_detail": f"{BY_1996_CANDIDATES_URL};{BY_1996_TOTALS_URL}",
        }
        for name, party, votes in pinned["candidates"]
    ]
    return _event_frame(event, rows)


def parse_york_west_1999(data: bytes, event: HistoricalFederalEvent) -> pd.DataFrame:
    """Return the pinned 1999 York West tabulation once the report's bytes are verified."""

    del data  # verified by checksum; the PDF's tables are pinned below
    valid = sum(votes for _, _, votes in _YORK_WEST_1999["candidates"])
    winner = max(votes for _, _, votes in _YORK_WEST_1999["candidates"])
    rows = [
        {
            "official_district_id": "35103",
            "district_name": "York West",
            "candidate_name_raw": name,
            "party_name_raw": party,
            "votes": votes,
            "elected": votes == winner,
            "incumbent_reported": pd.NA,
            "eligible_electors": _YORK_WEST_1999["eligible_electors"],
            "ballots_cast": valid + _YORK_WEST_1999["rejected"],
            "source_resource": RESOURCE_BY_1999,
            "source_detail": f"{BY_1999_URL}#Table 5 and York West poll-by-poll totals",
        }
        for name, party, votes in _YORK_WEST_1999["candidates"]
    ]
    return _event_frame(event, rows)


def historical_federal_placeholder_manifest() -> pd.DataFrame:
    """Contest hooks for in-scope federal Contests with no acquired result source."""

    rows = []
    for event in HISTORICAL_FEDERAL_EVENTS:
        if event.source_url is not None:
            continue
        for district, name in event.districts:
            rows.append(
                {
                    "event_id": event.event_id,
                    "election_date": event.election_date,
                    "election_type": event.election_type,
                    "election_authority": ELECTION_AUTHORITY,
                    "represented_body": REPRESENTED_BODY,
                    "office_type": OFFICE_TYPE,
                    "boundary_regime": event.boundary_regime,
                    "official_district_id": district,
                    "district_name": name,
                    "outcome_method": "source_missing",
                    "coverage_status": "source_missing",
                    "source_authority": ELECTION_AUTHORITY,
                    "source_resource": "By-elections 1996: Official Voting Results (not online)",
                    "source_detail": "No official Elections Canada result source located online.",
                }
            )
    return pd.DataFrame(rows)


def load_historical_federal_results(source_dir: str | Path) -> pd.DataFrame:
    """Load 1993-2000 federal results from the verified local cache."""

    frames = []
    for event in HISTORICAL_FEDERAL_EVENTS:
        if event.source_url is None:
            continue
        if event.event_id == "ec-ge-35":
            frame = parse_1993_results(_verified_bytes(source_dir, MDL_1993_URL), event)
        elif event.event_id == "ec-be-1996-03-25":
            frame = parse_etobicoke_north_1996(
                _page_text(source_dir, BY_1996_CANDIDATES_URL),
                _page_text(source_dir, BY_1996_TOTALS_URL),
                event,
            )
        elif event.event_id in _POLL_FILE_EVENTS:
            frame = parse_poll_file_results(
                _verified_bytes(source_dir, POLL_FILES_CAND_URL),
                _verified_bytes(source_dir, POLL_FILES_EDSUM_URL),
                event,
            )
        else:
            frame = parse_york_west_1999(_verified_bytes(source_dir, BY_1999_URL), event)
        expected = {d for d, _ in event.districts}
        if set(frame["official_district_id"]) != expected:
            raise ValueError(f"{event.event_id} district coverage does not match the manifest")
        if len(frame) != event.expected_candidate_rows:
            raise ValueError(
                f"{event.event_id} has {len(frame)} candidates; "
                f"expected {event.expected_candidate_rows}"
            )
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    for column in ("votes", "eligible_electors", "ballots_cast"):
        result[column] = result[column].astype("Int64")
    for column in ("elected", "incumbent_reported"):
        result[column] = result[column].astype("boolean")
    return result.sort_values(
        ["election_date", "official_district_id", "candidate_name_raw"], kind="stable"
    ).reset_index(drop=True)
