"""Elections Canada adapter for federal contests wholly contained in Toronto.

The public parsing seam returns one row per :term:`Candidacy` with ``NORMALIZED_COLUMNS``. Raw
poll/subdivision rows are used only to calculate official Contest totals; no poll-level result is
published. ``incumbent_reported`` deliberately preserves Elections Canada's source flag without
claiming that it satisfies this project's cross-boundary incumbency definition.

Elections Canada publishes two raw layouts in the coverage window. Format 2 is long (one
candidate per polling division) and carries party, elected, and incumbent fields. The 2004 general
election and several early by-elections are available only in the older wide layout (one candidate
column per poll); those poll files do not carry party or incumbent flags. For 2004, EC's official
Table 12 CSV supplies affiliation, incumbent, and declared-winner fields and is joined strictly to
the poll-derived contest totals. EC's structured Historical Results tables supply affiliation for
the early by-elections. They do not publish an incumbent indicator there, so it remains null rather
than being invented; the certified poll totals still identify only a unique top vote-getter.
"""

from __future__ import annotations

import io
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import pandas as pd
import requests

ELECTION_AUTHORITY = "Elections Canada"
REPRESENTED_BODY = "House of Commons of Canada"
OFFICE_TYPE = "mp"
SOURCE_RESOURCE = "Official Voting Results — Raw Data"
CUTOFF_DATE = date(2026, 8, 20)

NORMALIZED_COLUMNS = [
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
    "turnout_scope",
    "outcome_method",
    "coverage_status",
    "source_authority",
    "source_resource",
    "source_detail",
]


@dataclass(frozen=True)
class FederalEvent:
    """One official Elections Canada event and its Toronto-contained contests."""

    event_id: str
    election_date: date
    election_type: str
    boundary_regime: str
    districts: tuple[tuple[str, str], ...]
    source_urls: tuple[str, ...]
    summary_source_urls: tuple[str, ...] = ()


_RO_2003 = "federal-2003-representation-order"
_RO_2013 = "federal-2013-representation-order"
_RO_2023 = "federal-2023-representation-order"

_TORONTO_2003 = (
    ("35005", "Beaches—East York"),
    ("35015", "Davenport"),
    ("35016", "Don Valley East"),
    ("35017", "Don Valley West"),
    ("35019", "Eglinton—Lawrence"),
    ("35022", "Etobicoke Centre"),
    ("35023", "Etobicoke—Lakeshore"),
    ("35024", "Etobicoke North"),
    ("35068", "Parkdale—High Park"),
    ("35077", "St. Paul's"),
    ("35080", "Scarborough—Agincourt"),
    ("35081", "Scarborough Centre"),
    ("35082", "Scarborough—Guildwood"),
    ("35083", "Scarborough—Rouge River"),
    ("35084", "Scarborough Southwest"),
    ("35093", "Toronto Centre"),
    ("35094", "Toronto—Danforth"),
    ("35095", "Trinity—Spadina"),
    ("35100", "Willowdale"),
    ("35103", "York Centre"),
    ("35105", "York South—Weston"),
    ("35106", "York West"),
)

_TORONTO_2013 = (
    ("35007", "Beaches—East York"),
    ("35018", "Davenport"),
    ("35019", "Don Valley East"),
    ("35020", "Don Valley North"),
    ("35021", "Don Valley West"),
    ("35024", "Eglinton—Lawrence"),
    ("35027", "Etobicoke Centre"),
    ("35028", "Etobicoke—Lakeshore"),
    ("35029", "Etobicoke North"),
    ("35081", "Parkdale—High Park"),
    ("35090", "Toronto—St. Paul's"),
    ("35093", "Scarborough—Agincourt"),
    ("35094", "Scarborough Centre"),
    ("35095", "Scarborough—Guildwood"),
    ("35096", "Scarborough North"),
    ("35097", "Scarborough—Rouge Park"),
    ("35098", "Scarborough Southwest"),
    ("35101", "Spadina—Fort York"),
    ("35108", "Toronto Centre"),
    ("35109", "Toronto—Danforth"),
    ("35110", "University—Rosedale"),
    ("35115", "Willowdale"),
    ("35118", "York Centre"),
    ("35120", "York South—Weston"),
    ("35121", "Humber River—Black Creek"),
)

_TORONTO_2023 = (
    ("35007", "Beaches—East York"),
    ("35022", "Davenport"),
    ("35023", "Don Valley North"),
    ("35024", "Don Valley West"),
    ("35026", "Eglinton—Lawrence"),
    ("35029", "Etobicoke Centre"),
    ("35030", "Etobicoke—Lakeshore"),
    ("35031", "Etobicoke North"),
    ("35041", "Humber River—Black Creek"),
    ("35092", "Scarborough—Agincourt"),
    ("35093", "Scarborough Centre—Don Valley East"),
    ("35094", "Scarborough—Guildwood—Rouge Park"),
    ("35095", "Scarborough North"),
    ("35096", "Scarborough Southwest"),
    ("35097", "Scarborough—Woburn"),
    ("35100", "Spadina—Harbourfront"),
    ("35105", "Taiaiako'n—Parkdale—High Park"),
    ("35109", "Toronto Centre"),
    ("35110", "Toronto—Danforth"),
    ("35111", "Toronto—St. Paul's"),
    ("35112", "University—Rosedale"),
    ("35117", "Willowdale"),
    ("35120", "York Centre"),
    ("35122", "York South—Weston—Etobicoke"),
)


def _general(
    number: int,
    election_date: date,
    boundary_regime: str,
    districts: tuple[tuple[str, str], ...],
    source_url: str,
    summary_source_url: str | None = None,
) -> FederalEvent:
    return FederalEvent(
        event_id=f"ec-ge-{number}",
        election_date=election_date,
        election_type="general",
        boundary_regime=boundary_regime,
        districts=districts,
        source_urls=(source_url,),
        summary_source_urls=((summary_source_url,) if summary_source_url else ()),
    )


def _by_election(
    election_date: date,
    boundary_regime: str,
    districts: tuple[tuple[str, str], ...],
    source_urls: tuple[str, ...],
    summary_source_urls: tuple[str, ...] = (),
) -> FederalEvent:
    return FederalEvent(
        event_id=f"ec-be-{election_date.isoformat()}",
        election_date=election_date,
        election_type="by_election",
        boundary_regime=boundary_regime,
        districts=districts,
        source_urls=source_urls,
        summary_source_urls=summary_source_urls,
    )


FEDERAL_EVENTS = (
    _general(
        38,
        date(2004, 6, 28),
        _RO_2003,
        _TORONTO_2003,
        "https://www.elections.ca/scripts/OVR2004/23/data/ON.zip",
        "https://www.elections.ca/scripts/OVR2004/23/data/table12.csv",
    ),
    _general(
        39,
        date(2006, 1, 23),
        _RO_2003,
        _TORONTO_2003,
        "https://www.elections.ca/Scripts/OVR2006/25/data_donnees/"
        "pollresults_resultatsbureau35.zip",
    ),
    _by_election(
        date(2008, 3, 17),
        _RO_2003,
        (("35093", "Toronto Centre"), ("35100", "Willowdale")),
        (
            "https://www.elections.ca/ele/pas/2008/csv/pollbypoll35093.csv",
            "https://www.elections.ca/ele/pas/2008/csv/pollbypoll35100.csv",
        ),
        (
            "https://www.elections.ca/Scripts/VIS/HistoricalResults/35093_e.html",
            "https://www.elections.ca/Scripts/VIS/HistoricalResults/35100_e.html",
        ),
    ),
    _general(
        40,
        date(2008, 10, 14),
        _RO_2003,
        _TORONTO_2003,
        "https://www.elections.ca/scripts/OVR2008/31/data/pollresults_resultatsbureau35.zip",
    ),
    _general(
        41,
        date(2011, 5, 2),
        _RO_2003,
        _TORONTO_2003,
        "https://www.elections.ca/scripts/OVR2011/34/data_donnees/"
        "pollresults_resultatsbureau35.zip",
    ),
    _by_election(
        date(2012, 3, 19),
        _RO_2003,
        (("35094", "Toronto—Danforth"),),
        ("https://www.elections.ca/res/rep/off/ovr_2012/pollbypoll_bureauparbureau35094.csv",),
        ("https://www.elections.ca/Scripts/VIS/HistoricalResults/35094_e.html",),
    ),
    _by_election(
        date(2013, 11, 25),
        _RO_2003,
        (("35093", "Toronto Centre"),),
        ("https://www.elections.ca/res/rep/off/ovr_2013b2/csv/35093_e.csv",),
        ("https://www.elections.ca/Scripts/VIS/HistoricalResults/35093_e.html",),
    ),
    _by_election(
        date(2014, 6, 30),
        _RO_2003,
        (("35080", "Scarborough—Agincourt"), ("35095", "Trinity—Spadina")),
        (
            "https://www.elections.ca/res/rep/off/ovr_2014/csv/35080.csv",
            "https://www.elections.ca/res/rep/off/ovr_2014/csv/35095.csv",
        ),
        (
            "https://www.elections.ca/Scripts/VIS/HistoricalResults/35080_e.html",
            "https://www.elections.ca/Scripts/VIS/HistoricalResults/35095_e.html",
        ),
    ),
    _general(
        42,
        date(2015, 10, 19),
        _RO_2013,
        _TORONTO_2013,
        "https://www.elections.ca/res/rep/off/ovr2015app/41/data_donnees/"
        "pollresults_resultatsbureau35.zip",
    ),
    _by_election(
        date(2017, 12, 11),
        _RO_2013,
        (("35093", "Scarborough—Agincourt"),),
        (
            (
                "https://www.elections.ca/res/rep/off/ovr_2017d/46/data_donnees/"
                "pollresults_resultatsbureau35093.csv"
            ),
        ),
    ),
    _general(
        43,
        date(2019, 10, 21),
        _RO_2013,
        _TORONTO_2013,
        "https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/"
        "pollresults_resultatsbureau35.zip",
    ),
    _by_election(
        date(2020, 10, 26),
        _RO_2013,
        (("35108", "Toronto Centre"), ("35118", "York Centre")),
        (
            (
                "https://www.elections.ca/res/rep/off/ovr_2020/52/data_donnees/"
                "pollresults_resultatsbureau35108.csv"
            ),
            (
                "https://www.elections.ca/res/rep/off/ovr_2020/52/data_donnees/"
                "pollresults_resultatsbureau35118.csv"
            ),
        ),
    ),
    _general(
        44,
        date(2021, 9, 20),
        _RO_2013,
        _TORONTO_2013,
        "https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/"
        "pollresults_resultatsbureau35.zip",
    ),
    _by_election(
        date(2024, 6, 24),
        _RO_2013,
        (("35090", "Toronto—St. Paul's"),),
        (
            (
                "https://www.elections.ca/res/rep/off/ovr_2024b/58/data_donnees/"
                "pollresults_resultatsbureau35090.csv"
            ),
        ),
    ),
    _general(
        45,
        date(2025, 4, 28),
        _RO_2023,
        _TORONTO_2023,
        "https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees/"
        "pollresults_resultatsbureau35.zip",
    ),
    _by_election(
        date(2026, 4, 13),
        _RO_2023,
        (("35096", "Scarborough Southwest"), ("35112", "University—Rosedale")),
        (
            (
                "https://www.elections.ca/res/rep/off/ovr_2026/64/data_donnees/"
                "pollresults_resultatsbureau35096.csv"
            ),
            (
                "https://www.elections.ca/res/rep/off/ovr_2026/64/data_donnees/"
                "pollresults_resultatsbureau35112.csv"
            ),
        ),
    ),
)

_EVENT_BY_ID = {event.event_id: event for event in FEDERAL_EVENTS}
_WIDE_EVENT_IDS = frozenset(
    {
        "ec-ge-38",
        "ec-be-2008-03-17",
        "ec-be-2012-03-19",
        "ec-be-2013-11-25",
        "ec-be-2014-06-30",
    }
)

# Table 12 combines the candidate and bilingual affiliation into one field without a delimiter
# between the candidate name and English affiliation. These are the complete affiliation labels
# used in EC's 2004 Table 12; matching the full bilingual suffix avoids guessing at name boundaries.
_TABLE12_2004_AFFILIATIONS = (
    ("Christian Heritage Party", "Parti de l'Héritage Chrétien"),
    ("Marxist-Leninist", "Marxiste-Léniniste"),
    ("Canadian Action", "Action canadienne"),
    ("No Affiliation", "Aucune appartenance"),
    ("Marijuana Party", "Parti Marijuana"),
    ("Bloc Québécois", "Bloc Québécois"),
    ("Independent", "Indépendant"),
    ("Libertarian", "Libertarien"),
    ("Conservative", "conservateur"),
    ("Green Party", "Parti Vert"),
    ("Communist", "Communiste"),
    ("PC Party", "Parti PC"),
    ("Liberal", "Libéral"),
    ("N.D.P.", "N.P.D."),
)


def federal_event_manifest() -> pd.DataFrame:
    """Return the deterministic, cutoff-bounded federal Election-event manifest."""
    return pd.DataFrame(
        [
            {
                "event_id": event.event_id,
                "election_date": event.election_date,
                "election_type": event.election_type,
                "election_authority": ELECTION_AUTHORITY,
                "represented_body": REPRESENTED_BODY,
                "office_type": OFFICE_TYPE,
                "boundary_regime": event.boundary_regime,
                "official_district_ids": tuple(district_id for district_id, _ in event.districts),
                "source_urls": event.source_urls,
                "summary_source_urls": event.summary_source_urls,
                "source_layout": (
                    "wide_poll" if event.event_id in _WIDE_EVENT_IDS else "long_poll"
                ),
                "unavailable_source_fields": (
                    ()
                    if event.event_id == "ec-ge-38"
                    else (
                        ("incumbent_reported", "elected")
                        if event.event_id in _WIDE_EVENT_IDS
                        else ()
                    )
                ),
                "winner_derivation": (
                    "official_summary_indicator"
                    if event.event_id == "ec-ge-38"
                    else (
                        "unique_certified_vote_maximum"
                        if event.event_id in _WIDE_EVENT_IDS
                        else "official_elected_indicator"
                    )
                ),
            }
            for event in FEDERAL_EVENTS
        ]
    )


def federal_contest_manifest() -> pd.DataFrame:
    """Return one row for every Toronto-contained federal Contest in the manifest."""
    return pd.DataFrame(
        [
            {
                "event_id": event.event_id,
                "election_date": event.election_date,
                "election_type": event.election_type,
                "boundary_regime": event.boundary_regime,
                "official_district_id": district_id,
                "district_name": district_name,
            }
            for event in FEDERAL_EVENTS
            for district_id, district_name in event.districts
        ]
    )


def parse_federal_results(
    paths: str | Path | Sequence[str | Path],
    *,
    event_id: str,
    summary_paths: str | Path | Sequence[str | Path] | None = None,
) -> pd.DataFrame:
    """Aggregate one manifested event's official files to normalized Candidacy rows."""
    try:
        event = _EVENT_BY_ID[event_id]
    except KeyError as exc:
        raise ValueError(f"Unknown federal event_id: {event_id}") from exc

    source_paths = [paths] if isinstance(paths, (str, Path)) else list(paths)
    frames = []
    for source_path in source_paths:
        path = Path(source_path)
        if path.suffix.casefold() == ".zip":
            wanted = {district_id for district_id, _ in event.districts}
            with ZipFile(path) as archive:
                members = [
                    member
                    for member in archive.namelist()
                    if member.casefold().endswith(".csv")
                    and (_member_district_id(member) in wanted)
                ]
                frames.extend(
                    _parse_source_frame(
                        _read_elections_canada_csv(archive.read(member)),
                        event,
                        district_id_hint=_member_district_id(member),
                    )
                    for member in members
                )
        else:
            raw = _read_elections_canada_csv(path.read_bytes())
            frames.append(
                _parse_source_frame(raw, event, district_id_hint=_member_district_id(path.name))
            )

    if not frames:
        return _cast_normalized(pd.DataFrame(columns=NORMALIZED_COLUMNS))
    result = pd.concat(frames, ignore_index=True)
    if summary_paths is not None:
        supplied_summary_paths = (
            [summary_paths] if isinstance(summary_paths, (str, Path)) else list(summary_paths)
        )
        if supplied_summary_paths:
            result = _enrich_with_summary(result, event, supplied_summary_paths)
    result = result.sort_values(
        ["official_district_id", "candidate_name_raw"], kind="stable"
    ).reset_index(drop=True)
    return _cast_normalized(result)


def _member_district_id(member: str) -> str | None:
    matches = re.findall(r"(?<!\d)(\d{5})(?!\d)", Path(member).stem)
    return matches[-1] if matches else None


def _parse_source_frame(
    raw: pd.DataFrame,
    event: FederalEvent,
    *,
    district_id_hint: str | None = None,
) -> pd.DataFrame:
    if "candidatesfamilyname" in raw.columns:
        return _parse_long_results(raw, event)
    return _parse_wide_results(raw, event, district_id_hint=district_id_hint)


def _header_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", _english_header(value).casefold())


def _english_header(value: object) -> str:
    return str(value).lstrip("﻿").split("/", 1)[0].strip()


def _read_elections_canada_csv(data: bytes) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - both Python codecs above always either decode or raise
        raise ValueError("Unsupported Elections Canada CSV encoding")
    frame = pd.read_csv(io.StringIO(text), dtype="object")
    names = {_header_key(column): _english_header(column) for column in frame.columns}
    frame = frame.rename(columns={column: _header_key(column) for column in frame.columns})
    frame.attrs["source_headers"] = names
    return frame


def _first_present(frame: pd.DataFrame, *keys: str) -> str:
    for key in keys:
        if key in frame.columns:
            return key
    raise ValueError(f"Elections Canada CSV lacks required field; expected one of {keys!r}")


def _numeric_values(
    series: pd.Series,
    *,
    label: str,
    allow_blank: bool = False,
    allowed_zero_pattern: str | None = None,
) -> pd.Series:
    """Parse source numbers without turning malformed source text into observed zero."""

    text = series.astype("string").str.strip()
    blank = text.isna() | text.eq("")
    allowed_zero = pd.Series(False, index=series.index)
    if allowed_zero_pattern is not None:
        allowed_zero = text.str.match(allowed_zero_pattern, case=False, na=False)
    numeric = pd.to_numeric(series, errors="coerce")
    invalid = numeric.isna() & ~allowed_zero & ~(blank & allow_blank)
    if invalid.any():
        bad = series.loc[invalid].iloc[0]
        raise ValueError(f"Elections Canada {label} contains a non-numeric value: {bad!r}")
    return numeric.mask(allowed_zero, 0)


def _official_district_id(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").astype("Int64")
    return numeric.astype("string")


def _district_name(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.split("/", n=1)
        .str[0]
        .str.strip()
        .str.strip('"')
        .str.replace("--", "—", regex=False)
        .str.replace("–", "—", regex=False)
    )


def _candidate_name(frame: pd.DataFrame) -> pd.Series:
    parts = frame[["candidatesfirstname", "candidatesmiddlename", "candidatesfamilyname"]].fillna(
        ""
    )
    return parts.apply(
        lambda row: " ".join(str(value).strip() for value in row if str(value).strip()), axis=1
    ).astype("string")


def _poll_identity(frame: pd.DataFrame, poll_column: str) -> pd.Series:
    number = frame[poll_column].astype("string").fillna("").str.strip()
    name_column = next(
        (column for column in ("pollingstationname", "pollingdivisionname") if column in frame),
        None,
    )
    if name_column is None:
        name = pd.Series("", index=frame.index, dtype="string")
    else:
        name = frame[name_column].astype("string").fillna("").str.strip()
    return number + "\x1f" + name


def _reported_bool(series: pd.Series) -> bool | pd.NA:
    values = {str(value).strip().upper() for value in series.dropna()}
    if "Y" in values:
        return True
    if "N" in values:
        return False
    return pd.NA


def _affiliation_status(value: object) -> str:
    if pd.isna(value) or not str(value).strip():
        return "not_reported"
    key = str(value).strip().casefold()
    if "independent" in key or "no affiliation" in key:
        return "independent"
    return "party"


def _source_for_district(event: FederalEvent, official_district_id: str) -> str:
    matching = [url for url in event.source_urls if official_district_id in Path(url).name]
    return matching[0] if matching else event.source_urls[0]


def _parse_long_results(raw: pd.DataFrame, event: FederalEvent) -> pd.DataFrame:
    poll_column = _first_present(raw, "pollingstationnumber", "pollingdivisionnumber")
    rejected_column = _first_present(
        raw,
        "rejectedballotsforpollingstation",
        "rejectedballotsforpoll",
        "rejectedballotsforpolls",
    )
    electors_column = _first_present(
        raw, "electorsforpollingstation", "electorsforpoll", "electorsforpolls"
    )
    votes_column = _first_present(raw, "candidatepollvotescount", "candidatevotecount")

    frame = raw.copy()
    frame["official_district_id"] = _official_district_id(frame["electoraldistrictnumber"])
    wanted = {district_id for district_id, _ in event.districts}
    frame = frame[frame["official_district_id"].isin(wanted)].copy()
    frame["district_name"] = _district_name(
        frame[_first_present(frame, "electoraldistrictnameenglish", "electoraldistrictname")]
    )
    frame["candidate_name_raw"] = _candidate_name(frame)
    frame["party_name_raw"] = frame["politicalaffiliationnameenglish"].astype("string").str.strip()
    frame["votes"] = _numeric_values(frame[votes_column], label="candidate votes")
    frame["_electors"] = _numeric_values(frame[electors_column], label="electors")
    frame["_rejected"] = _numeric_values(frame[rejected_column], label="rejected ballots")
    frame["_poll_identity"] = _poll_identity(frame, poll_column)

    poll_metrics = (
        frame.drop_duplicates(["official_district_id", "_poll_identity"])
        .groupby("official_district_id", sort=False, as_index=False)
        .agg(eligible_electors=("_electors", "sum"), rejected_ballots=("_rejected", "sum"))
    )
    candidate = (
        frame.groupby(
            [
                "official_district_id",
                "district_name",
                "candidate_name_raw",
                "party_name_raw",
            ],
            dropna=False,
            sort=False,
            as_index=False,
        )
        .agg(
            votes=("votes", "sum"),
            elected=("electedcandidateindicator", _reported_bool),
            incumbent_reported=("incumbentindicator", _reported_bool),
        )
        .merge(poll_metrics, on="official_district_id", how="left", validate="many_to_one")
    )
    valid_votes = candidate.groupby("official_district_id", sort=False)["votes"].transform("sum")
    candidate["ballots_cast"] = valid_votes + candidate["rejected_ballots"]
    candidate["affiliation_status"] = candidate["party_name_raw"].map(_affiliation_status)
    return _add_event_fields(candidate, event)


def _parse_wide_results(
    raw: pd.DataFrame,
    event: FederalEvent,
    *,
    district_id_hint: str | None = None,
) -> pd.DataFrame:
    district_name_column = _first_present(
        raw,
        "electoraldistrictnameenglish",
        "electoraldistrictname",
        "electoraldistrict",
    )
    poll_column = _first_present(raw, "pollingstationnumber", "pollingdivisionnumber")
    electors_column = _first_present(raw, "electors", "electorsforpollingstation")
    total_votes_column = _first_present(raw, "totalvotes")
    metadata = {
        "electoraldistrictnumber",
        district_name_column,
        poll_column,
        "pollingstationname",
        "pollingdivisionname",
        "rejectedballots",
        total_votes_column,
        electors_column,
    }
    candidate_columns = [column for column in raw.columns if column not in metadata]
    if not candidate_columns:
        raise ValueError("Elections Canada wide CSV contains no candidate columns")

    frame = raw.copy()
    source_headers = frame.attrs.get("source_headers", {})
    if "electoraldistrictnumber" in frame:
        frame["official_district_id"] = _official_district_id(frame["electoraldistrictnumber"])
    elif district_id_hint is not None:
        frame["official_district_id"] = district_id_hint
    else:
        raise ValueError(
            "Elections Canada wide CSV lacks electoral district number and no archive-member "
            "hint was available"
        )
    wanted = {district_id for district_id, _ in event.districts}
    frame = frame[frame["official_district_id"].isin(wanted)].copy()
    frame["district_name"] = _district_name(frame[district_name_column])
    frame["_electors"] = _numeric_values(frame[electors_column], label="electors", allow_blank=True)
    # In this wide layout EC's Total Votes equals candidate votes plus rejected ballots.
    frame["_ballots"] = _numeric_values(
        frame[total_votes_column], label="total votes", allow_blank=True
    )
    contest_metrics = frame.groupby("official_district_id", sort=False, as_index=False).agg(
        eligible_electors=("_electors", lambda values: values.sum(min_count=1)),
        ballots_cast=("_ballots", lambda values: values.sum(min_count=1)),
    )

    long = frame.melt(
        id_vars=["official_district_id", "district_name"],
        value_vars=candidate_columns,
        var_name="_candidate_column",
        value_name="votes",
    )
    long["candidate_name_raw"] = long["_candidate_column"].map(source_headers).astype("string")
    long["votes"] = _numeric_values(
        long["votes"],
        label="candidate votes",
        allow_blank=True,
        allowed_zero_pattern=r"^(?:merged with no\.?|void|no poll held)(?:\b|/)",
    ).fillna(0)
    candidate = (
        long.groupby(
            ["official_district_id", "district_name", "candidate_name_raw"],
            sort=False,
            as_index=False,
        )["votes"]
        .sum()
        .merge(contest_metrics, on="official_district_id", how="left", validate="many_to_one")
    )
    maximum = candidate.groupby("official_district_id", sort=False)["votes"].transform("max")
    is_maximum = candidate["votes"].eq(maximum)
    n_at_maximum = is_maximum.groupby(candidate["official_district_id"]).transform("sum")
    candidate["elected"] = pd.Series(False, index=candidate.index, dtype="boolean")
    candidate.loc[is_maximum & n_at_maximum.eq(1), "elected"] = True
    candidate.loc[is_maximum & n_at_maximum.gt(1), "elected"] = pd.NA
    candidate["incumbent_reported"] = pd.NA
    candidate["party_name_raw"] = pd.NA
    candidate["affiliation_status"] = "not_reported"
    return _add_event_fields(candidate, event)


def _summary_source_for_district(event: FederalEvent, official_district_id: str) -> str:
    matching = [
        url
        for url in event.summary_source_urls
        if _member_district_id(Path(urlparse(url).path).name) == official_district_id
    ]
    return matching[0] if matching else event.summary_source_urls[0]


def _html_text(parts: Sequence[str]) -> str:
    return re.sub(r"\s+", " ", "".join(parts).replace("\xa0", " ")).strip()


class _HistoricalResultsParser(HTMLParser):
    """Read one event table from EC's regular 2004–2014 historical-results HTML."""

    def __init__(self, event: FederalEvent):
        super().__init__(convert_charrefs=True)
        self._date_label = (
            f"{event.election_date.strftime('%B')} {event.election_date.day}, "
            f"{event.election_date.year}"
        )
        self._capture_heading = False
        self._heading_parts: list[str] = []
        self._next_table_matches = False
        self._in_table = False
        self._in_row = False
        self._capture_cell = False
        self._cell_parts: list[str] = []
        self._row: list[str] = []
        self.rows: list[tuple[str, str, int]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        del attrs
        tag = tag.casefold()
        if tag == "h4":
            self._capture_heading = True
            self._heading_parts = []
        elif tag == "table":
            self._in_table = self._next_table_matches
            self._next_table_matches = False
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._row = []
        elif self._in_row and tag in {"th", "td"}:
            self._capture_cell = True
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_heading:
            self._heading_parts.append(data)
        if self._capture_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag == "h4" and self._capture_heading:
            heading = _html_text(self._heading_parts)
            self._next_table_matches = (
                "official voting results" in heading.casefold()
                and "by-election" in heading.casefold()
                and self._date_label in heading
            )
            self._capture_heading = False
        elif tag in {"th", "td"} and self._capture_cell:
            self._row.append(_html_text(self._cell_parts))
            self._capture_cell = False
        elif tag == "tr" and self._in_row:
            self._finish_row()
            self._in_row = False
        elif tag == "table" and self._in_table:
            self._in_table = False

    def _finish_row(self) -> None:
        if len(self._row) < 3 or self._row[0].casefold() in {"candidate", "total"}:
            return
        vote_text = self._row[2].replace(",", "").strip()
        if not vote_text.isdigit():
            raise ValueError(
                "Elections Canada historical-results table contains an invalid vote total: "
                f"{self._row[2]!r}"
            )
        self.rows.append((self._row[0], self._row[1], int(vote_text)))


def _parse_historical_summary(
    data: bytes,
    event: FederalEvent,
    *,
    official_district_id: str,
) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            html = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - both codecs either decode or raise
        raise ValueError("Unsupported Elections Canada historical-results encoding")

    parser = _HistoricalResultsParser(event)
    parser.feed(html)
    parser.close()
    if not parser.rows:
        raise ValueError(
            "Elections Canada historical-results page lacks the manifested by-election table "
            f"for {event.election_date.isoformat()}"
        )
    frame = pd.DataFrame(parser.rows, columns=["candidate_name_raw", "party_name_raw", "votes"])
    frame["official_district_id"] = official_district_id
    frame["affiliation_status"] = frame["party_name_raw"].map(_affiliation_status)
    frame["elected"] = pd.Series(pd.NA, index=frame.index, dtype="boolean")
    frame["incumbent_reported"] = pd.Series(pd.NA, index=frame.index, dtype="boolean")
    frame["summary_source_detail"] = _summary_source_for_district(event, official_district_id)
    return frame[
        [
            "official_district_id",
            "candidate_name_raw",
            "party_name_raw",
            "affiliation_status",
            "votes",
            "elected",
            "incumbent_reported",
            "summary_source_detail",
        ]
    ]


def _split_2004_summary_candidate(value: object) -> tuple[str, str, bool]:
    combined = str(value).strip()
    matches = []
    for english, french in _TABLE12_2004_AFFILIATIONS:
        suffix = f" {english}/{french}"
        if combined.endswith(suffix):
            matches.append((combined[: -len(suffix)].strip(), english))
    if len(matches) != 1:
        raise ValueError(
            "Elections Canada 2004 Table 12 candidate/affiliation field has an unknown "
            f"or ambiguous suffix: {value!r}"
        )
    candidate_name, party_name = matches[0]
    incumbent = candidate_name.endswith(" **")
    if incumbent:
        candidate_name = candidate_name[:-3].rstrip()
    if not candidate_name:
        raise ValueError("Elections Canada 2004 Table 12 contains a blank candidate name")
    return candidate_name, party_name, incumbent


def _parse_2004_summary(raw: pd.DataFrame, event: FederalEvent) -> pd.DataFrame:
    required = {"electoraldistrict", "candidate", "votesobtained", "majority"}
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise ValueError(
            "Elections Canada 2004 Table 12 lacks required field(s): " + ", ".join(missing)
        )

    frame = raw.copy()
    frame["district_name"] = _district_name(frame["electoraldistrict"])
    district_lookup = {district_name: district_id for district_id, district_name in event.districts}
    frame["official_district_id"] = frame["district_name"].map(district_lookup).astype("string")
    frame = frame[frame["official_district_id"].notna()].copy()

    parsed = frame["candidate"].map(_split_2004_summary_candidate)
    frame["candidate_name_raw"] = parsed.map(lambda values: values[0]).astype("string")
    frame["party_name_raw"] = parsed.map(lambda values: values[1]).astype("string")
    frame["incumbent_reported"] = parsed.map(lambda values: values[2]).astype("boolean")
    frame["affiliation_status"] = frame["party_name_raw"].map(_affiliation_status)
    frame["votes"] = pd.to_numeric(frame["votesobtained"], errors="coerce").astype("Int64")
    if frame["votes"].isna().any():
        raise ValueError("Elections Canada 2004 Table 12 contains a missing or invalid vote total")
    majority = frame["majority"].astype("string").str.strip()
    frame["elected"] = majority.notna().astype("boolean")
    frame["summary_source_detail"] = frame["official_district_id"].map(
        lambda district_id: _summary_source_for_district(event, district_id)
    )
    return frame[
        [
            "official_district_id",
            "candidate_name_raw",
            "party_name_raw",
            "affiliation_status",
            "votes",
            "elected",
            "incumbent_reported",
            "summary_source_detail",
        ]
    ].reset_index(drop=True)


def _enrich_with_summary(
    results: pd.DataFrame,
    event: FederalEvent,
    summary_paths: Sequence[str | Path],
) -> pd.DataFrame:
    if not event.summary_source_urls:
        raise ValueError(
            f"No official structured federal summary is configured for {event.event_id}"
        )

    summary_frames = []
    for supplied_path in summary_paths:
        path = Path(supplied_path)
        if path.suffix.casefold() in {".html", ".htm"}:
            district_id = _member_district_id(path.name)
            if district_id is None:
                raise ValueError(
                    f"Elections Canada historical-results filename lacks a district ID: {path.name}"
                )
            summary_frames.append(
                _parse_historical_summary(
                    path.read_bytes(), event, official_district_id=district_id
                )
            )
        elif event.event_id == "ec-ge-38":
            summary_frames.append(
                _parse_2004_summary(_read_elections_canada_csv(path.read_bytes()), event)
            )
        else:
            raise ValueError(
                f"Unsupported federal summary format for {event.event_id}: {path.name}"
            )
    summary = pd.concat(summary_frames, ignore_index=True)
    present_districts = set(results["official_district_id"].astype("string"))
    summary = summary[summary["official_district_id"].isin(present_districts)].copy()

    keys = ["official_district_id", "candidate_name_raw"]
    if results.duplicated(keys).any() or summary.duplicated(keys).any():
        raise ValueError("Federal summary enrichment keys are not unique within a contest")

    comparison = results[keys + ["votes"]].merge(
        summary[keys + ["votes"]],
        on=keys,
        how="outer",
        suffixes=("_poll", "_summary"),
        indicator=True,
        validate="one_to_one",
    )
    if not comparison["_merge"].eq("both").all():
        missing = comparison.loc[comparison["_merge"].ne("both"), [*keys, "_merge"]].to_dict(
            "records"
        )
        raise ValueError(
            f"Federal summary coverage does not match poll-derived candidacies: {missing}"
        )
    vote_matches = comparison["votes_poll"].eq(comparison["votes_summary"]).fillna(False)
    if not vote_matches.all():
        disagreements = comparison.loc[
            ~vote_matches, [*keys, "votes_poll", "votes_summary"]
        ].to_dict("records")
        raise ValueError(
            f"Federal poll and summary vote totals disagree; refusing enrichment: {disagreements}"
        )

    supplement = summary.rename(
        columns={
            "party_name_raw": "_summary_party_name_raw",
            "affiliation_status": "_summary_affiliation_status",
            "elected": "_summary_elected",
            "incumbent_reported": "_summary_incumbent_reported",
            "summary_source_detail": "_summary_source_detail",
        }
    ).drop(columns="votes")
    enriched = results.merge(supplement, on=keys, how="left", validate="one_to_one")
    enriched["party_name_raw"] = enriched.pop("_summary_party_name_raw")
    enriched["affiliation_status"] = enriched.pop("_summary_affiliation_status")
    enriched["elected"] = enriched.pop("_summary_elected").combine_first(enriched["elected"])
    enriched["incumbent_reported"] = enriched.pop("_summary_incumbent_reported").combine_first(
        enriched["incumbent_reported"]
    )
    summary_details = enriched.pop("_summary_source_detail")
    enriched["source_detail"] = (
        enriched["source_detail"].astype("string")
        + " | summary enrichment: "
        + summary_details.astype("string")
    )
    return enriched


def _add_event_fields(frame: pd.DataFrame, event: FederalEvent) -> pd.DataFrame:
    result = frame.copy()
    result["event_id"] = event.event_id
    result["election_date"] = event.election_date
    result["election_type"] = event.election_type
    result["election_authority"] = ELECTION_AUTHORITY
    result["represented_body"] = REPRESENTED_BODY
    result["office_type"] = OFFICE_TYPE
    result["boundary_regime"] = event.boundary_regime
    result["turnout_scope"] = "federal_electoral_district"
    result["outcome_method"] = "vote"
    result["coverage_status"] = "complete"
    result["source_authority"] = ELECTION_AUTHORITY
    result["source_resource"] = SOURCE_RESOURCE
    result["source_detail"] = result["official_district_id"].map(
        lambda district_id: _source_for_district(event, district_id)
    )
    return result[NORMALIZED_COLUMNS]


def _cast_normalized(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in ("votes", "eligible_electors", "ballots_cast"):
        result[column] = pd.to_numeric(result[column], errors="coerce").round().astype("Int64")
    for column in ("elected", "incumbent_reported"):
        result[column] = result[column].astype("boolean")
    return result


def _validate_manifest_coverage(results: pd.DataFrame, event_ids: Sequence[str]) -> None:
    expected = {
        (event_id, district_id)
        for event_id in event_ids
        for district_id, _ in _EVENT_BY_ID[event_id].districts
    }
    actual = set(results[["event_id", "official_district_id"]].itertuples(index=False, name=None))
    if actual != expected:
        missing = sorted(expected.difference(actual))
        unexpected = sorted(actual.difference(expected))
        raise ValueError(
            "Federal contest coverage does not match the event manifest: "
            f"missing={missing}, unexpected={unexpected}"
        )


def load_federal_results(
    source_dir: str | Path,
    *,
    event_ids: Sequence[str] | None = None,
    download: bool = False,
    session=None,
    overwrite: bool = False,
    validate: bool = True,
) -> pd.DataFrame:
    """Load manifested events from the deterministic local cache.

    Set ``download`` to fetch official files that are not already cached. ``event_ids`` is useful
    for incremental builds; omitting it loads the complete cutoff-bounded manifest. Manifest
    coverage is checked by default; ``validate=False`` is intended for partial test extracts.
    """
    selected_ids = tuple(event_ids) if event_ids is not None else tuple(_EVENT_BY_ID)
    unknown = sorted(set(selected_ids).difference(_EVENT_BY_ID))
    if unknown:
        raise ValueError(f"Unknown federal event_id(s): {', '.join(unknown)}")

    frames = []
    for event_id in selected_ids:
        event = _EVENT_BY_ID[event_id]
        if download:
            download_federal_event(
                event_id,
                source_dir,
                session=session,
                overwrite=overwrite,
            )
        event_dir = Path(source_dir) / event_id
        paths = tuple(event_dir / Path(urlparse(url).path).name for url in event.source_urls)
        summary_paths = tuple(
            event_dir / Path(urlparse(url).path).name for url in event.summary_source_urls
        )
        missing = [path for path in (*paths, *summary_paths) if not path.is_file()]
        if missing:
            joined = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(f"Missing official federal source file(s): {joined}")
        frames.append(
            parse_federal_results(
                paths,
                event_id=event_id,
                summary_paths=summary_paths or None,
            )
        )

    if not frames:
        result = _cast_normalized(pd.DataFrame(columns=NORMALIZED_COLUMNS))
    else:
        result = (
            pd.concat(frames, ignore_index=True)
            .sort_values(
                ["election_date", "event_id", "official_district_id", "candidate_name_raw"],
                kind="stable",
            )
            .reset_index(drop=True)
        )
    if validate:
        _validate_manifest_coverage(result, selected_ids)
    return result


def download_federal_event(
    event_id: str,
    dest_dir: str | Path,
    *,
    session=None,
    overwrite: bool = False,
) -> tuple[Path, ...]:
    """Download one event's official poll and configured summary files."""
    try:
        event = _EVENT_BY_ID[event_id]
    except KeyError as exc:
        raise ValueError(f"Unknown federal event_id: {event_id}") from exc

    event_dir = Path(dest_dir) / event.event_id
    event_dir.mkdir(parents=True, exist_ok=True)
    client = session or requests
    destinations = []
    for url in (*event.source_urls, *event.summary_source_urls):
        filename = Path(urlparse(url).path).name
        if not filename:
            raise ValueError(f"Federal source URL has no filename: {url}")
        destination = event_dir / filename
        destinations.append(destination)
        if destination.exists() and not overwrite:
            continue

        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            with client.get(url, stream=True, timeout=300) as response:
                response.raise_for_status()
                with temporary.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            handle.write(chunk)
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    return tuple(destinations)
