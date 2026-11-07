"""Complete Ontario legislature rosters from the Legislative Assembly's member records.

Elections Ontario flags the candidates it counts as incumbents. With the Assembly's own
membership in ``data/reference/ontario_legislature_members.csv`` (every member's riding terms
by Parliament, from the 36th on), each Ontario event gets the complete sitting roster on its
reference date instead: every member whose term covers the day before the Legislature was
dissolved, or the day before a by-election, in any riding. Each Toronto member term is tied to
the Person who won the seat on the day the term began, which gives that Person an Office
tenure with the Assembly's dates. A confirmed Person whose run is in the event is then ``True``
if they hold a sitting term and ``False`` otherwise, and the authority's flag stays in
``incumbent_reported``. The rules are those of the House of Commons rosters in
``federal_rosters``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .federal_rosters import (
    FederalRosterEvidence,
    MemberIdentity,
    MembershipRosterSpec,
    build_membership_roster_evidence,
)
from .reported_incumbency import ONTARIO_GENERAL_ROSTER_REFERENCES, ReportedIncumbency

ONTARIO_MEMBERS_FILENAME = "ontario_legislature_members.csv"
ONTARIO_MEMBER_COLUMNS = (
    "parliament",
    "ola_member_id",
    "first_name",
    "last_name",
    "riding",
    "party",
    "from_date",
    "to_date",
    "source",
)
OLA_PROFILE_URL = "https://www.ola.org/en/members/all/"


def read_ontario_members(reference: Path) -> pd.DataFrame | None:
    """Read the Ontario legislature member terms, or ``None`` when the file is absent."""

    path = reference / ONTARIO_MEMBERS_FILENAME
    if not path.is_file():
        return None
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    if tuple(table.columns) != ONTARIO_MEMBER_COLUMNS:
        raise ValueError(f"{ONTARIO_MEMBERS_FILENAME} columns must be {ONTARIO_MEMBER_COLUMNS}")
    for column in ("from_date", "to_date"):
        filled = table[column].ne("")
        dates = pd.to_datetime(table.loc[filled, column], format="%Y-%m-%d", errors="coerce")
        if dates.isna().any():
            raise ValueError(f"{ONTARIO_MEMBERS_FILENAME}.{column} holds an invalid date")
    blank = table[["parliament", "ola_member_id", "last_name", "riding", "from_date"]].eq("")
    if blank.any(axis=None):
        raise ValueError(f"{ONTARIO_MEMBERS_FILENAME} has a term without a required value")
    ended = table["to_date"].ne("")
    if (table.loc[ended, "to_date"] < table.loc[ended, "from_date"]).any():
        raise ValueError(f"{ONTARIO_MEMBERS_FILENAME} has a term that ends before it starts")
    if table.duplicated(["ola_member_id", "from_date"]).any():
        raise ValueError(f"{ONTARIO_MEMBERS_FILENAME} lists a member's term twice")
    return table


def _roster_reference(
    event_id: str, event_date: pd.Timestamp, event_type: str, group: pd.DataFrame
) -> tuple[str, str, dict[str, object]]:
    if event_type == "general":
        official = ONTARIO_GENERAL_ROSTER_REFERENCES.get(event_id)
        if official is None:
            raise ValueError(f"Ontario general event {event_id!r} has no dissolution reference")
        return (
            official.reference_date,
            "day_before_official_legislature_dissolution",
            {
                "dissolution_date": official.dissolution_date,
                "reference_date": official.reference_date,
                "source_url": official.source_url,
            },
        )
    reference_date = (event_date - pd.Timedelta(days=1)).date().isoformat()
    return (
        reference_date,
        "day_before_ontario_by_election_polling_day",
        {
            "polling_date": event_date.date().isoformat(),
            "reference_date": reference_date,
            "source_urls": sorted(set(group["source_detail"].astype(str))),
        },
    )


def _member_record(member: pd.Series) -> dict[str, object]:
    return {
        "parliament": int(member["parliament"]),
        "ola_member_id": member["ola_member_id"],
        "name": f"{member['first_name']} {member['last_name']}".strip(),
        "riding": member["riding"],
        "party": member["party"] or None,
        "from_date": member["from_date"],
        "to_date": member["to_date"] or None,
        "source": member["source"],
    }


# Members whose term no winner in the release began, tied by sources to the Person of a run.
ONTARIO_MEMBER_PERSONS = {
    "john-tory": MemberIdentity(
        member_key="john-tory",
        candidacy_id="can_b6ef5f14d0f9578f986e6ae34122b3e7",
        rationale=(
            "The Assembly's profile of John Tory, member for Dufferin—Peel—Wellington—Grey from "
            "his by-election on 17 March 2005 to 9 October 2007, lists him as Leader of the "
            "Progressive Conservative Party of Ontario. Wikipedia's page on Don Valley West says "
            "that party's leader, John Tory, was defeated there by Kathleen Wynne in 2007, and "
            "Elections Ontario flagged his 2007 run as an incumbent's."
        ),
        source_urls=(
            "https://www.ola.org/en/members/all/john-tory",
            "https://en.wikipedia.org/wiki/Don_Valley_West_(provincial_electoral_district)",
        ),
    ),
}

# Members whose name fits a run by a different Person.
ONTARIO_MEMBER_NAMESAKES = (
    MemberIdentity(
        member_key="dave-smith",
        candidacy_id="can_6c197d0f33bb5eadbd064bd28f92bb56",
        rationale=(
            "The Assembly lists Dave Smith, member for Peterborough—Kawartha from 2018, and "
            "David Smith, member for Scarborough Centre from 2022, as two members who both sat "
            "from 2 June 2022."
        ),
        source_urls=(
            "https://www.ola.org/en/members/all/dave-smith",
            "https://www.ola.org/en/members/all/david-smith",
        ),
    ),
)

ONTARIO_ROSTER_SPEC = MembershipRosterSpec(
    represented_body="ontario_legislative_assembly",
    office_type="mpp",
    district_column="riding",
    member_label="Ontario member",
    tenure_namespace="ontario_legislature_member",
    tenure_rule="ontario_member_term_of_seat_winner",
    member_key="ontario_member",
    roster_rule="complete_ontario_legislature_membership_on_reference_date",
    membership_filename=ONTARIO_MEMBERS_FILENAME,
    member_id_columns=("ola_member_id",),
    member_record=_member_record,
    source_authority=lambda member: "Legislative Assembly of Ontario",
    roster_reference=_roster_reference,
    member_persons=ONTARIO_MEMBER_PERSONS,
    namesakes=ONTARIO_MEMBER_NAMESAKES,
)


def ontario_roster_evidence(
    candidacies: pd.DataFrame, reported: ReportedIncumbency, members: pd.DataFrame | None
) -> FederalRosterEvidence:
    """Assembly-membership rosters where the file reaches, the authority's flags elsewhere."""

    if members is None:
        return FederalRosterEvidence(reported.office_tenures, reported.rosters)
    assembly, covered = build_membership_roster_evidence(candidacies, members, ONTARIO_ROSTER_SPEC)
    kept_rosters = reported.rosters.loc[~reported.rosters["event_id"].isin(covered)]
    kept_tenures = reported.office_tenures.loc[
        reported.office_tenures["office_tenure_id"].isin(kept_rosters["office_tenure_id"].dropna())
    ]
    tenures = pd.concat([kept_tenures, assembly.office_tenures], ignore_index=True)
    rosters = pd.concat([kept_rosters, assembly.rosters], ignore_index=True)
    rosters["roster_complete"] = rosters["roster_complete"].astype("boolean")
    return FederalRosterEvidence(tenures, rosters)
