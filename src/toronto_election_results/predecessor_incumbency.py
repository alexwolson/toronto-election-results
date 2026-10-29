"""Incumbency across amalgamation through designated predecessor bodies (ADR 0012).

ADR 0005's ``incumbent`` asks whether a Person sat in the last roster of the same Represented body
and Office type. The bodies first elected on November 10, 1997 had no prior roster, so that field
cannot show a sitting North York councillor running for the new City Council.
``predecessor_incumbent`` answers the narrower question for those first elections only: did the
Person sit, on the day before polling, in a designated predecessor body for the same Office type?

The predecessor Represented-body identifiers are provisional until the 1994 municipal adapter
publishes those bodies. ``True`` needs a confirmed Person and a supporting Office tenure; ``False``
needs a complete roster for every predecessor body of the Contest, recorded in
:data:`COMPLETE_PREDECESSOR_ROSTERS`. Everything else is null.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

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
# Empty until the predecessor rosters are acquired, so no Candidacy can be marked ``False``.
COMPLETE_PREDECESSOR_ROSTERS: frozenset[tuple[str, str]] = frozenset()


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
