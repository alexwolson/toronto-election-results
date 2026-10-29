"""Mayor, Councillor and Metro Councillor results for 1994, 1997 and 2000 (ADR 0010).

These elections predate the City's Open Data results. The authoritative surviving source is the
City's own archived results pages, transcribed by ``scripts/transcribe_municipal_archive.py`` into
``data/reference/municipal_archive_results.csv``. The archive reports vote totals but rarely
marks winners and never states seat counts, so each Contest carries ``seats_available`` from the
council composition record and ``elected`` is derived from the top vote totals (ADR 0011). York's
1994 page marks its winners; those markers must agree with the derivation. Contests the archive
does not report become ``source_missing`` placeholders.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .candidates import known_multiword_surnames, normalize_name
from .schema import elect_top_vote_totals, stable_id

ARCHIVE_RESULTS_FILENAME = "municipal_archive_results.csv"
SOURCE_AUTHORITY = "City of Toronto"
_CONTEST_KEY = ["election_date", "represented_body", "office_type", "official_district_id"]
_RESOURCES = {
    "1994-11-14": "Previous election results — 1994 General Municipal Election (archived)",
    "1997-11-10": "Previous election results — 1997 General Municipal Election (archived)",
    "2000-11-13": "Vote 2000 — final results (archived)",
}
_EXPECTED_ROWS = {"1994-11-14": 333, "1997-11-10": 213, "2000-11-13": 167}


def read_archive_results(reference_dir: str | Path) -> pd.DataFrame:
    path = Path(reference_dir) / ARCHIVE_RESULTS_FILENAME
    table = pd.read_csv(path, dtype="string", keep_default_na=False).replace("", pd.NA)
    counts = table.groupby("election_date").size().to_dict()
    if counts != _EXPECTED_ROWS:
        raise ValueError(f"municipal archive row counts changed: {counts}")
    return table


def _event_ids(frame: pd.DataFrame) -> list[str]:
    return [
        stable_id("evt", authority, date, "general")
        for authority, date in zip(frame["election_authority"], frame["election_date"], strict=True)
    ]


def _outcomes(contest: pd.DataFrame) -> tuple[pd.Series, str]:
    seats = int(contest["seats_available"].iloc[0])
    acclaimed = contest["acclaimed"].eq("true")
    if acclaimed.any():
        if not acclaimed.all() or len(contest) > seats:
            raise ValueError(
                f"mixed or oversized acclamation in {contest.iloc[0][_CONTEST_KEY].tolist()}"
            )
        return pd.Series(True, index=contest.index, dtype="boolean"), "acclamation"
    elected = elect_top_vote_totals(contest["votes"].astype(int), seats)
    marked = contest["marked_elected"].eq("true")
    if marked.any() and not marked.eq(elected.fillna(False)).all():
        raise ValueError(
            f"marked winners disagree with vote totals in {contest.iloc[0][_CONTEST_KEY].tolist()}"
        )
    return elected, "vote"


def load_archive_results(reference_dir: str | Path) -> pd.DataFrame:
    """Return the archived Candidacy rows as an adapter frame."""

    table = read_archive_results(reference_dir)
    rows = table.loc[table["coverage_status"].eq("complete")].copy()
    rows["seats_available"] = rows["seats_available"].astype(int)
    elected = pd.Series(pd.NA, index=rows.index, dtype="boolean")
    methods = pd.Series(pd.NA, index=rows.index, dtype="string")
    for _, contest in rows.groupby(_CONTEST_KEY, sort=False):
        winners, method = _outcomes(contest)
        elected.loc[contest.index] = winners
        methods.loc[contest.index] = method
    rows["elected"] = elected
    rows["outcome_method"] = methods
    rows["votes"] = pd.array(
        [pd.NA if pd.isna(v) else int(v) for v in rows["votes"]], dtype="Int64"
    )
    rows["event_id"] = _event_ids(rows)
    rows["election_type"] = "general"
    rows["party_name_raw"] = pd.NA
    rows["affiliation_status"] = "non_partisan"
    rows["incumbent_reported"] = pd.NA
    rows["eligible_electors"] = pd.NA
    rows["ballots_cast"] = pd.NA
    rows["turnout_scope"] = pd.NA
    rows["source_authority"] = SOURCE_AUTHORITY
    rows["source_resource"] = rows["election_date"].map(_RESOURCES)
    rows["source_detail"] = (
        rows["source_detail"]
        + "#"
        + rows["source_locator"].str.replace(r" line \d+$", "", regex=True)
    )
    # 1994 names are "Last, First"; the 1997 and 2000 pages write names given-name first, which
    # the Open Data normaliser would misread as surname-first, so those keep their word order.
    known = known_multiword_surnames(rows["candidate_name_raw"])
    rows["candidate_name"] = [
        normalize_name(name, known_surnames=known)[0]
        if "," in name
        else " ".join(name.split()).title()
        for name in rows["candidate_name_raw"]
    ]
    columns = [
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
        "incumbent_reported",
        "eligible_electors",
        "ballots_cast",
        "turnout_scope",
        "outcome_method",
        "coverage_status",
        "seats_available",
        "source_authority",
        "source_resource",
        "source_detail",
    ]
    return rows[columns].reset_index(drop=True)


def archive_placeholder_manifest(reference_dir: str | Path) -> pd.DataFrame:
    """Contest hooks for in-scope archived Contests whose results the archive does not report."""

    table = read_archive_results(reference_dir)
    missing = table.loc[table["coverage_status"].eq("source_missing")].copy()
    missing["event_id"] = _event_ids(missing)
    missing["election_type"] = "general"
    missing["outcome_method"] = "source_missing"
    missing["seats_available"] = missing["seats_available"].astype(int)
    missing["source_authority"] = SOURCE_AUTHORITY
    missing["source_resource"] = missing["election_date"].map(_RESOURCES)
    missing["source_detail"] = (
        missing["source_detail"]
        + "#"
        + missing["source_locator"].str.replace(r" line \d+$", "", regex=True)
    )
    columns = [
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
        "seats_available",
        "source_authority",
        "source_resource",
        "source_detail",
    ]
    return missing[columns].reset_index(drop=True)
