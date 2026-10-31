"""Mayor, Councillor and Metro Councillor results for 1994, 1997 and 2000, school trustee
results for 1994, 1997 and 2000, and the municipal by-elections held between 1995 and 2002
(ADR 0010).

These elections predate the City's Open Data results. The authoritative surviving source is the
City's own archived results pages, transcribed by ``scripts/transcribe_municipal_archive.py`` into
``data/reference/municipal_archive_results.csv``. Where the archive omits a Contest or reports it
incompletely (most 1994 and 1997 school-board races, and eight 1994 council races), the row comes
from the Toronto Star's printed final results and says so in ``source_authority``. The archive reports vote totals but rarely
marks winners and never states seat counts, so each Contest carries ``seats_available`` from the
council composition record and ``elected`` is derived from the top vote totals (ADR 0011). York's
1994 page marks its winners; those markers must agree with the derivation. Contests the archive
does not report become ``source_missing`` placeholders.

The by-elections are transcribed by hand into ``data/reference/municipal_by_elections_1995_2002.csv``:
the four the City's archived "Previous elections results" index lists (1998, 1999, 2001, 2002),
whose pages mark their winners, and North York's Ward 1 by-election of 1995, which only the
Toronto Star reports. The Star gives two of that Contest's six vote totals, so it is ``partial``:
the other candidates keep null votes and the Star's named winner is ``marked_elected``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .candidates import known_multiword_surnames, normalize_name
from .schema import elect_top_vote_totals, stable_id

ARCHIVE_RESULTS_FILENAME = "municipal_archive_results.csv"
BY_ELECTION_RESULTS_FILENAME = "municipal_by_elections_1995_2002.csv"
SOURCE_AUTHORITY = "City of Toronto"
STAR_AUTHORITY = "Toronto Star"
_CONTEST_KEY = ["election_date", "represented_body", "office_type", "official_district_id"]
_RESOURCES = {
    "1994-11-14": "Previous election results — 1994 General Municipal Election (archived)",
    "1997-11-10": "Previous election results — 1997 General Municipal Election (archived)",
    "2000-11-13": "Vote 2000 — final results (archived)",
    "1998-09-24": "Previous election results — 1998 Ward 1 East York By-election (archived)",
    "1999-09-23": (
        "Previous election results — 1999 Ward 16 Scarborough Highland Creek By-election (archived)"
    ),
    "2001-12-03": (
        "Previous election results — 2001 Beaches-East York Ward 31 By-election (archived)"
    ),
    "2002-03-18": (
        "Previous election results — 2002 Toronto District School Board, Etobicoke North Ward 1 "
        "By-election (archived)"
    ),
}
_EXPECTED_ROWS = {"1994-11-14": 684, "1997-11-10": 366, "2000-11-13": 285}
_EXPECTED_BY_ELECTION_ROWS = {
    "1995-09-21": 6,
    "1998-09-24": 8,
    "1999-09-23": 7,
    "2001-12-03": 11,
    "2002-03-18": 8,
}
_STAR_RESOURCES = {
    "1994-11-14": "Toronto Star, 16 November 1994, final results (ProQuest Historical Newspapers)",
    "1997-11-10": "Toronto Star, 14 November 1997, School Board Results (ProQuest Historical Newspapers)",
    "1995-09-21": (
        "Toronto Star, 22 September 1995, North York Ward 1 by-election report "
        "(ProQuest Historical Newspapers)"
    ),
}


def _read_table(path: Path, expected: dict[str, int], label: str) -> pd.DataFrame:
    table = pd.read_csv(path, dtype="string", keep_default_na=False).replace("", pd.NA)
    counts = table.groupby("election_date").size().to_dict()
    if counts != expected:
        raise ValueError(f"{label} row counts changed: {counts}")
    return table


def read_archive_results(reference_dir: str | Path) -> pd.DataFrame:
    """Return the archived general-election rows and the 1995-2002 by-election rows together."""

    reference = Path(reference_dir)
    general = _read_table(reference / ARCHIVE_RESULTS_FILENAME, _EXPECTED_ROWS, "municipal archive")
    general["election_type"] = "general"
    by_elections = _read_table(
        reference / BY_ELECTION_RESULTS_FILENAME,
        _EXPECTED_BY_ELECTION_ROWS,
        "municipal by-election",
    )
    if not by_elections["election_type"].eq("by_election").all():
        raise ValueError("municipal by-election rows must have election_type 'by_election'")
    return pd.concat([general, by_elections[general.columns]], ignore_index=True)


def _event_ids(frame: pd.DataFrame) -> list[str]:
    return [
        stable_id("evt", authority, date, election_type)
        for authority, date, election_type in zip(
            frame["election_authority"],
            frame["election_date"],
            frame["election_type"],
            strict=True,
        )
    ]


def _outcomes(contest: pd.DataFrame) -> tuple[pd.Series, str]:
    seats = int(contest["seats_available"].iloc[0])
    acclaimed = contest["acclaimed"].eq("true")
    key = contest.iloc[0][_CONTEST_KEY].tolist()
    if acclaimed.any():
        if not acclaimed.all() or len(contest) > seats:
            raise ValueError(f"mixed or oversized acclamation in {key}")
        return pd.Series(True, index=contest.index, dtype="boolean"), "acclamation"
    marked = contest["marked_elected"].eq("true")
    if contest["votes"].isna().any():
        # Only a partial Contest may lack vote totals, and then its source must name the winners.
        if not contest["coverage_status"].eq("partial").all() or int(marked.sum()) != seats:
            raise ValueError(f"null votes need a partial Contest with marked winners in {key}")
        known = contest["votes"].dropna().astype(int)
        winner_votes = known[marked.loc[known.index]]
        if not winner_votes.empty and int(known.max()) > int(winner_votes.min()):
            raise ValueError(f"a marked winner trails a known vote total in {key}")
        return marked.astype("boolean"), "vote"
    elected = elect_top_vote_totals(contest["votes"].astype(int), seats)
    if marked.any() and not marked.eq(elected.fillna(False)).all():
        raise ValueError(f"marked winners disagree with vote totals in {key}")
    return elected, "vote"


def _apply_source_fields(rows: pd.DataFrame, star: pd.Series) -> None:
    """Set source authority, resource and detail; Star rows cite the ProQuest page record."""

    rows["source_resource"] = rows["election_date"].map(_RESOURCES)
    rows.loc[star, "source_resource"] = rows.loc[star, "election_date"].map(_STAR_RESOURCES)
    archive_detail = (
        rows["source_detail"]
        + "#"
        + rows["source_locator"].str.replace(r" line \d+$", "", regex=True)
    )
    rows["source_detail"] = archive_detail.where(~star, rows["source_detail"])
    rows["source_authority"] = SOURCE_AUTHORITY
    rows.loc[star, "source_authority"] = STAR_AUTHORITY


def load_archive_results(reference_dir: str | Path) -> pd.DataFrame:
    """Return the archived Candidacy rows as an adapter frame."""

    table = read_archive_results(reference_dir)
    rows = table.loc[table["coverage_status"].isin(["complete", "partial"])].copy()
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
    rows["party_name_raw"] = pd.NA
    rows["affiliation_status"] = "non_partisan"
    rows["incumbent_reported"] = pd.NA
    rows["eligible_electors"] = pd.NA
    rows["ballots_cast"] = pd.NA
    rows["turnout_scope"] = pd.NA
    star = rows["source_authority"].eq(STAR_AUTHORITY).fillna(False)
    _apply_source_fields(rows, star)
    # 1994 names are "Last, First"; the 1997 and 2000 pages write names given-name first, which
    # the Open Data normaliser would misread as surname-first, so those keep their word order.
    # The Star prints names given-name first in mixed case, so its rows keep the printed form.
    # A line break inside a hyphenated surname leaves "Tsolakopoulos- Nunziata"; it is closed up.
    known = known_multiword_surnames(rows["candidate_name_raw"])
    rows["candidate_name"] = [
        normalize_name(name, known_surnames=known)[0]
        if "," in name
        else " ".join(name.split()).replace("- ", "-")
        if from_star
        else " ".join(name.split()).replace("- ", "-").title()
        for name, from_star in zip(rows["candidate_name_raw"], star, strict=True)
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
    missing["outcome_method"] = "source_missing"
    missing["seats_available"] = missing["seats_available"].astype(int)
    _apply_source_fields(missing, missing["source_authority"].eq(STAR_AUTHORITY).fillna(False))
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
