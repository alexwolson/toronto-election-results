"""Derive incumbency from City council-composition data (ADR 0002).

For elections 2010–2022 the sitting members immediately before the election are read from the
City's Council **meeting-attendance** and **voting-record** open datasets:

  - attendance in the final ~6 months of the term = members clearly still sitting;
  - a voting-only member is added iff their *latest* activity reaches the term's final year — this
    catches mid-term **appointees** (e.g. Jonathan Tsao) while excluding members who *departed*
    mid-term (e.g. Pam McConnell), whose latest activity predates the final year.

The mayor sits on City Council, so the incumbent mayor is captured too. Elections 2003/2006 have
no City data and are supplied by a curated compilation (data/reference/); the 2023 mayoral
by-election has no incumbent (the office was vacant).

``flag_incumbents`` matches a composition to candidates by identity key and writes
``incumbent`` / ``incumbent_source`` / ``incumbent_confidence``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .candidates import match_key, normalize_name

RAW = Path("data/raw/council")

WIKI_CONFIDENCE = 0.85  # Wikipedia-sourced rosters (2003–2006): lower tier than City data.

# Election year -> the council term whose end precedes it.
TERM_BEFORE_ELECTION = {
    2010: "2006-2010",
    2014: "2010-2014",
    2018: "2014-2018",
    2022: "2018-2022",
}

ATTENDANCE_CONFIDENCE = 0.95
VOTING_CONFIDENCE = 0.90
# How complete we believe each year's roster is (drives non-incumbent confidence).
CITY_ROSTER_CONFIDENCE = 0.95

_COMPOSITION_COLUMNS = [
    "election_year",
    "member_name",
    "match_key",
    "incumbent_source",
    "confidence",
]


def _fix_mojibake(text: str) -> str:
    """Repair latin1-decoded-as-utf8 names in the voting record (e.g. 'BailÃ£o' -> 'Bailão')."""
    try:
        return text.encode("latin1").decode("utf8")
    except UnicodeEncodeError, UnicodeDecodeError:
        return text


def _key(name: str) -> str:
    display, _, _ = normalize_name(name)
    return match_key(display)


def council_members_before(year: int, *, raw: Path = RAW, window_days: int = 183) -> pd.DataFrame:
    """Sitting members immediately before ``year``'s election, from attendance + voting."""
    term = TERM_BEFORE_ELECTION[year]

    attendance = pd.read_csv(raw / "attendance" / f"councillors-meeting-attendance-{term}.csv")
    council = attendance[attendance["Committee"] == "City Council"].copy()
    council["date"] = pd.to_datetime(council["SessionDate"], errors="coerce")
    final_window = council[
        council["date"] >= council["date"].max() - pd.Timedelta(days=window_days)
    ]
    attendees = {
        f"{f.strip()} {last.strip()}"
        for f, last in zip(final_window["FirstName"], final_window["LastName"])
    }

    voting = pd.read_csv(raw / "voting" / f"member-voting-record-{term}.csv")
    voted = voting[voting["Committee"] == "City Council"].copy()
    voted["year"] = pd.to_numeric(
        voted["Agenda Item #"].str.extract(r"^(\d{4})")[0], errors="coerce"
    )
    voted["name"] = [
        f"{_fix_mojibake(str(f)).strip()} {_fix_mojibake(str(last)).strip()}"
        for f, last in zip(voted["First Name"], voted["Last Name"])
    ]
    final_year = voted["year"].max()
    latest_by_member = voted.groupby("name")["year"].max()
    active_through_end = set(latest_by_member[latest_by_member >= final_year].index)
    voting_only = active_through_end - attendees

    rows = [
        (year, name, _key(name), "city_attendance", ATTENDANCE_CONFIDENCE) for name in attendees
    ]
    rows += [(year, name, _key(name), "city_voting", VOTING_CONFIDENCE) for name in voting_only]
    return pd.DataFrame(rows, columns=_COMPOSITION_COLUMNS)


def build_city_composition(*, raw: Path = RAW, years=tuple(TERM_BEFORE_ELECTION)) -> pd.DataFrame:
    """Council composition before each City-data election year (2010–2022)."""
    return pd.concat([council_members_before(y, raw=raw) for y in years], ignore_index=True)


_ROSTER_LINE = re.compile(r"^(\d{4}-\d{4})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*$")
# Which term's end-of-term roster supplies incumbents for which election.
TERM_TO_ELECTION = {"2000-2003": 2003, "2003-2006": 2006}
RECONCILED_CONFIDENCE = 0.85  # both agents agree
SINGLE_SOURCE_CONFIDENCE = 0.70  # only one agent, or they disagreed


def parse_roster_text(text: str) -> pd.DataFrame:
    """Parse an agent's ``term | ward | member_name | arrival`` roster into a DataFrame."""
    rows = []
    for line in text.splitlines():
        match = _ROSTER_LINE.match(line.strip())
        if match:
            term, ward, name, arrival = (g.strip() for g in match.groups())
            rows.append((term, ward, name, arrival))
    return pd.DataFrame(rows, columns=["term", "ward", "member_name", "arrival"])


def reconcile_rosters(text_a: str, text_b: str) -> tuple[pd.DataFrame, list[str]]:
    """Reconcile two independent rosters by (term, ward). Returns (reconciled, disagreements).

    Agreement (same person by identity key) -> higher confidence; a seat present in only one
    roster, or where the two name different people, is kept from A (or B) at lower confidence and
    reported for manual review.
    """
    a = parse_roster_text(text_a).set_index(["term", "ward"])
    b = parse_roster_text(text_b).set_index(["term", "ward"])
    disagreements: list[str] = []
    rows = []
    for seat in sorted(set(a.index) | set(b.index)):
        term, ward = seat
        name_a = a.loc[seat, "member_name"] if seat in a.index else None
        name_b = b.loc[seat, "member_name"] if seat in b.index else None
        arrival = a.loc[seat, "arrival"] if seat in a.index else b.loc[seat, "arrival"]
        if name_a and name_b and _key(name_a) == _key(name_b):
            rows.append((term, ward, name_a, arrival, RECONCILED_CONFIDENCE))
        else:
            chosen = name_a or name_b
            rows.append((term, ward, chosen, arrival, SINGLE_SOURCE_CONFIDENCE))
            disagreements.append(f"{term} ward {ward}: A={name_a!r} B={name_b!r}")
    reconciled = pd.DataFrame(
        rows, columns=["term", "ward", "member_name", "arrival", "confidence"]
    )
    return reconciled, disagreements


def roster_to_composition(reconciled: pd.DataFrame) -> pd.DataFrame:
    """Turn a reconciled roster into composition rows keyed by election year."""
    rows = []
    for r in reconciled.itertuples(index=False):
        year = TERM_TO_ELECTION.get(r.term)
        if year is None:
            continue
        rows.append((year, r.member_name, _key(r.member_name), "wikipedia", r.confidence))
    return pd.DataFrame(rows, columns=_COMPOSITION_COLUMNS).drop_duplicates(
        ["election_year", "match_key"]
    )


def rosters_to_composition(
    text_a: str, text_b: str, *, confidence: float = WIKI_CONFIDENCE
) -> pd.DataFrame:
    """Composition from the **union** of both agents' rosters.

    Including both name forms is deliberate: where the agents disagree on a first-name variant
    (``George``/``Giorgio``) both refer to the same incumbent seat, so carrying both lets whichever
    form the results use match. Keyed by election year, deduplicated by identity key.
    """
    both = pd.concat([parse_roster_text(text_a), parse_roster_text(text_b)], ignore_index=True)
    rows = []
    for r in both.itertuples(index=False):
        year = TERM_TO_ELECTION.get(r.term)
        if year is not None:
            rows.append((year, r.member_name, _key(r.member_name), "wikipedia", confidence))
    return pd.DataFrame(rows, columns=_COMPOSITION_COLUMNS).drop_duplicates(
        ["election_year", "match_key"]
    )


REFERENCE = Path("data/reference")

# How complete/trusted each election's roster is (drives non-incumbent confidence).
ROSTER_CONFIDENCE = {
    2003: WIKI_CONFIDENCE,
    2006: WIKI_CONFIDENCE,
    2010: CITY_ROSTER_CONFIDENCE,
    2014: CITY_ROSTER_CONFIDENCE,
    2018: CITY_ROSTER_CONFIDENCE,
    2022: CITY_ROSTER_CONFIDENCE,
    2023: 0.90,
}


def build_composition(*, reference: Path = REFERENCE, raw: Path = RAW) -> pd.DataFrame:
    """Assemble council composition for every election with a roster source.

    2003/2006 from the two reconciled agent rosters; 2010–2022 from the City attendance/voting
    datasets. 2023 (the mayoral by-election) is added by the assembler from the 2022 winners,
    since its sitting council is the 2022-elected one.
    """
    parts = [
        rosters_to_composition(
            (reference / "roster_agent_a.txt").read_text(),
            (reference / "roster_agent_b.txt").read_text(),
        ),
        build_city_composition(raw=raw),
    ]
    return pd.concat(parts, ignore_index=True)


# The prior in-scope election whose winners are the sitting incumbents. (2003 has no in-scope
# prior, so its incumbents come only from the composition roster. 2023's council is the 2022 one.)
PRIOR_ELECTION = {
    2006: 2003,
    2010: 2006,
    2014: 2010,
    2018: 2014,
    2022: 2018,
    2023: 2022,
}
PRIOR_WINNER_CONFIDENCE = 0.95


def flag_incumbents(
    results: pd.DataFrame,
    composition: pd.DataFrame,
    *,
    roster_confidence: dict[int, float],
) -> pd.DataFrame:
    """Add ``incumbent`` / ``incumbent_source`` / ``incumbent_confidence`` to results rows.

    Incumbency is established two ways, in priority order:

    1. **Prior-winner** — the candidate's ``candidate_id`` was ``elected`` in the immediately-prior
       in-scope election. This is the robust path: it rides on the fuzzy candidate identity, so
       name-form drift (``Norm``/``Norman``, ``A.A.``/``Adrian``) never breaks it.
    2. **Roster** — the candidate's identity key matches a sitting member in the composition. This
       supplies 2003 (no in-scope prior election) and the mid-term **appointees**/by-election
       winners who did not win the prior election.

    A candidate matching neither is not an incumbent, with confidence set by how complete that
    election's roster is.
    """
    results = results.copy()
    elected_ids = {
        int(year): set(group.loc[group["elected"], "candidate_id"].dropna())
        for year, group in results.groupby("election_year")
    }
    roster = {
        (int(r.election_year), r.match_key): (r.incumbent_source, r.confidence)
        for r in composition.itertuples(index=False)
    }
    keys = results["candidate_name"].map(_key)

    incumbent, source, confidence = [], [], []
    for year, candidate_id, key in zip(results["election_year"], results["candidate_id"], keys):
        year = int(year)
        prior = PRIOR_ELECTION.get(year)
        won_prior = (
            prior is not None
            and pd.notna(candidate_id)
            and candidate_id in elected_ids.get(prior, set())
        )
        roster_hit = roster.get((year, key))
        if won_prior:
            incumbent.append(True)
            source.append("prior_winner")
            confidence.append(PRIOR_WINNER_CONFIDENCE)
        elif roster_hit is not None:
            incumbent.append(True)
            source.append(roster_hit[0])
            confidence.append(roster_hit[1])
        else:
            incumbent.append(False)
            source.append(pd.NA)
            confidence.append(roster_confidence.get(year, 0.5))

    results["incumbent"] = incumbent
    results["incumbent_source"] = source
    results["incumbent_confidence"] = confidence
    return results
