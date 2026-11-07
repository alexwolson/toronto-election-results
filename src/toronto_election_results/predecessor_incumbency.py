"""Incumbency across amalgamation through designated predecessor bodies (ADR 0012).

ADR 0005's ``incumbent`` asks whether a Person sat in the last roster of the same Represented body
and Office type. The bodies first elected on November 10, 1997 had no prior roster, so that field
cannot show a sitting North York councillor running for the new City Council.
``predecessor_incumbent`` answers the narrower question for those first elections only: did the
Person sit, on the day before polling, in a designated predecessor body for the same Office type?

``True`` needs a confirmed Person and a supporting Office tenure; ``False`` needs a complete
roster for every predecessor body of the Contest. Everything else is null.

``data/reference/predecessor_rosters_1997.csv`` lists the members of Metropolitan Toronto Council
and the six former councils on 9 November 1997. Each member names the Candidacy that seated them,
or for an appointee the Candidacy that identifies them, so the roster gives each member's Person
an Office tenure in that body. A body's roster is complete when it lists exactly as many mayors
and councillors as the body elected in 1994. The school boards have no roster, so their
successors' ``predecessor_incumbent`` stays null.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd

from .schema import stable_id

FIRST_AMALGAMATED_ELECTION = date(1997, 11, 10)

_FORMER_COUNCILS = (
    "former_toronto_city_council",
    "north_york_city_council",
    "scarborough_city_council",
    "etobicoke_city_council",
    "york_city_council",
    "east_york_borough_council",
)


@dataclass(frozen=True)
class SuccessorOffice:
    represented_body: str
    office_type: str
    first_election: date
    predecessors: tuple[tuple[str, str], ...]


SUCCESSOR_OFFICES = (
    SuccessorOffice(
        "toronto_city_council",
        "mayor",
        FIRST_AMALGAMATED_ELECTION,
        tuple((body, "mayor") for body in _FORMER_COUNCILS),
    ),
    SuccessorOffice(
        "toronto_city_council",
        "councillor",
        FIRST_AMALGAMATED_ELECTION,
        (("metro_toronto_council", "councillor"),)
        + tuple((body, "councillor") for body in _FORMER_COUNCILS),
    ),
    SuccessorOffice(
        "toronto_district_school_board",
        "trustee",
        FIRST_AMALGAMATED_ELECTION,
        tuple(
            (f"{city}_board_of_education", "trustee")
            for city in ("toronto", "north_york", "scarborough", "etobicoke", "york", "east_york")
        ),
    ),
    SuccessorOffice(
        "toronto_catholic_district_school_board",
        "trustee",
        FIRST_AMALGAMATED_ELECTION,
        (("metropolitan_separate_school_board", "trustee"),),
    ),
    SuccessorOffice(
        "conseil_scolaire_viamonde",
        "trustee",
        FIRST_AMALGAMATED_ELECTION,
        (("cefcut", "trustee"),),
    ),
    SuccessorOffice(
        "conseil_scolaire_catholique_monavenir",
        "trustee",
        FIRST_AMALGAMATED_ELECTION,
        (("metropolitan_separate_school_board_french_section", "trustee"),),
    ),
)

# (Represented body, Office type) pairs whose last sitting roster before 1997-11-10 is complete.
# The release derives them from the predecessor roster file; this default holds none.
COMPLETE_PREDECESSOR_ROSTERS: frozenset[tuple[str, str]] = frozenset()

PREDECESSOR_ROSTERS_FILENAME = "predecessor_rosters_1997.csv"
PREDECESSOR_ROSTER_COLUMNS = (
    "represented_body",
    "office_type",
    "district_name",
    "member_name",
    "arrival",
    "candidacy_id",
    "basis",
    "evidence_urls",
    "started_on",
    "started_on_precision",
)
_ARRIVALS = {"elected", "by_election", "appointed"}
_TENURE_COLUMNS = [
    "office_tenure_id",
    "person_id",
    "represented_body",
    "office_type",
    "district_id",
    "started_on",
    "started_on_precision",
    "ended_on",
    "ended_on_precision",
    "entry_method",
    "source_authority",
    "source_detail",
]


@dataclass(frozen=True)
class PredecessorRosterEvidence:
    """Office tenures in the predecessor bodies and the rosters that are complete."""

    office_tenures: pd.DataFrame
    complete_rosters: frozenset[tuple[str, str]]


def read_predecessor_rosters(reference: Path) -> pd.DataFrame | None:
    """Read the predecessor roster file, or ``None`` when it is absent."""

    path = reference / PREDECESSOR_ROSTERS_FILENAME
    if not path.is_file():
        return None
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")
    ]
    table = pd.read_csv(StringIO("\n".join(lines)), dtype=str, keep_default_na=False)
    missing = sorted(set(PREDECESSOR_ROSTER_COLUMNS) - set(table.columns))
    if missing:
        raise ValueError(f"{PREDECESSOR_ROSTERS_FILENAME} is missing: {', '.join(missing)}")
    if not table["arrival"].isin(_ARRIVALS).all():
        raise ValueError(f"{PREDECESSOR_ROSTERS_FILENAME} has an unknown arrival")
    if table["candidacy_id"].duplicated().any():
        raise ValueError(f"{PREDECESSOR_ROSTERS_FILENAME} names one Candidacy twice")
    appointed = table["arrival"].eq("appointed")
    if table.loc[appointed, ["started_on", "started_on_precision"]].eq("").any(axis=None):
        raise ValueError(f"{PREDECESSOR_ROSTERS_FILENAME} needs a start for every appointee")
    if table.loc[~appointed, ["started_on", "started_on_precision"]].ne("").any(axis=None):
        raise ValueError(
            f"{PREDECESSOR_ROSTERS_FILENAME} takes elected members' starts from results"
        )
    urls = table["evidence_urls"].str.split(";")
    if not urls.map(lambda values: all(url.startswith("https://") for url in values)).all():
        raise ValueError(f"{PREDECESSOR_ROSTERS_FILENAME} requires HTTPS evidence on every row")
    return table.loc[:, list(PREDECESSOR_ROSTER_COLUMNS)].copy()


def build_predecessor_roster_evidence(
    candidacies: pd.DataFrame, rosters: pd.DataFrame | None
) -> PredecessorRosterEvidence:
    """Turn the predecessor rosters into Office tenures and the set of complete rosters."""

    if rosters is None or rosters.empty:
        return PredecessorRosterEvidence(
            pd.DataFrame(columns=_TENURE_COLUMNS), COMPLETE_PREDECESSOR_ROSTERS
        )
    reference = (FIRST_AMALGAMATED_ELECTION - timedelta(days=1)).isoformat()
    runs = candidacies.set_index("candidacy_id")
    missing = sorted(set(rosters["candidacy_id"]) - set(runs.index))
    if missing:
        raise ValueError(f"predecessor roster names an unknown Candidacy {missing[0]!r}")
    rows: list[dict[str, object]] = []
    for member in rosters.itertuples(index=False):
        run = runs.loc[member.candidacy_id]
        if pd.isna(run["person_id"]):
            raise ValueError(f"predecessor roster member {member.member_name!r} has no Person")
        seated_here = (
            run["represented_body"] == member.represented_body
            and run["office_type"] == member.office_type
            and run["elected"] is not pd.NA
            and bool(run["elected"])
        )
        if (member.arrival == "appointed") == seated_here:
            raise ValueError(
                f"predecessor roster Candidacy for {member.member_name!r} does not fit its arrival"
            )
        if member.arrival == "elected" and str(run["election_date"])[:10] != "1994-11-14":
            raise ValueError(f"{member.member_name!r} is listed as elected in 1994")
        dated = member.arrival != "appointed"
        person_id = str(run["person_id"])
        rows.append(
            {
                "office_tenure_id": stable_id(
                    "ten", "predecessor_roster_1997", member.represented_body, person_id
                ),
                "person_id": person_id,
                "represented_body": member.represented_body,
                "office_type": member.office_type,
                "district_id": run["district_id"] if seated_here else pd.NA,
                "started_on": str(run["election_date"])[:10] if dated else member.started_on,
                "started_on_precision": ("election_date" if dated else member.started_on_precision),
                "ended_on": reference,
                "ended_on_precision": "at_or_after_reference",
                "entry_method": "appointment" if member.arrival == "appointed" else "election",
                "source_authority": "City of Toronto",
                "source_detail": json.dumps(
                    {
                        "evidence_rule": "predecessor_roster_member_on_reference_date",
                        "roster_file": f"data/reference/{PREDECESSOR_ROSTERS_FILENAME}",
                        "member_name": member.member_name,
                        "arrival": member.arrival,
                        "candidacy_id": member.candidacy_id,
                        "basis": member.basis,
                        "evidence_urls": member.evidence_urls.split(";"),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )
    tenures = pd.DataFrame(rows, columns=_TENURE_COLUMNS)
    if tenures.duplicated(["person_id", "represented_body", "office_type"]).any():
        raise ValueError("a Person is listed twice in one predecessor roster")

    elected_1994 = candidacies.loc[
        candidacies["election_date"].astype(str).str.startswith("1994-11-14")
        & candidacies["elected"].eq(True).fillna(False)
    ]
    seats = elected_1994.groupby(["represented_body", "office_type"]).size()
    listed = rosters.groupby(["represented_body", "office_type"]).size()
    complete = frozenset(key for key, count in listed.items() if seats.get(key, 0) == count)
    short = sorted(set(listed.index) - complete)
    if short:
        raise ValueError(f"predecessor roster for {short[0]!r} does not fill every 1994 seat")
    return PredecessorRosterEvidence(tenures, complete)


def _successor_for(row: pd.Series) -> SuccessorOffice | None:
    for office in SUCCESSOR_OFFICES:
        if (
            row["represented_body"] == office.represented_body
            and row["office_type"] == office.office_type
            and pd.Timestamp(row["election_date"]).date() == office.first_election
        ):
            return office
    return None


def derive_predecessor_incumbency(
    candidacies: pd.DataFrame,
    office_tenures: pd.DataFrame,
    *,
    complete_rosters: frozenset[tuple[str, str]] = COMPLETE_PREDECESSOR_ROSTERS,
) -> pd.DataFrame:
    """Add ``predecessor_incumbent`` and ``predecessor_office_tenure_id`` to Candidacy rows."""

    out = candidacies.copy()
    flags = pd.Series(pd.NA, index=out.index, dtype="boolean")
    tenure_ids = pd.Series(pd.NA, index=out.index, dtype="string")
    tenures = office_tenures.copy()
    if not tenures.empty:
        tenures["started_on"] = pd.to_datetime(tenures["started_on"], errors="coerce")
        tenures["ended_on"] = pd.to_datetime(tenures["ended_on"], errors="coerce")

    for index, row in out.iterrows():
        office = _successor_for(row)
        if office is None or pd.isna(row.get("person_id")):
            continue
        reference = pd.Timestamp(office.first_election - timedelta(days=1))
        held = pd.DataFrame()
        if not tenures.empty:
            in_predecessor = pd.Series(
                [
                    (body, office_type) in office.predecessors
                    for body, office_type in zip(
                        tenures["represented_body"], tenures["office_type"], strict=True
                    )
                ],
                index=tenures.index,
            )
            sitting = tenures["started_on"].le(reference) & (
                tenures["ended_on"].isna() | tenures["ended_on"].ge(reference)
            )
            held = tenures.loc[
                in_predecessor & sitting & tenures["person_id"].eq(row["person_id"])
            ].sort_values("office_tenure_id", kind="stable")
        if not held.empty:
            flags[index] = True
            tenure_ids[index] = str(held["office_tenure_id"].iloc[0])
        elif set(office.predecessors) <= complete_rosters:
            flags[index] = False

    out["predecessor_incumbent"] = flags
    out["predecessor_office_tenure_id"] = tenure_ids
    return out
