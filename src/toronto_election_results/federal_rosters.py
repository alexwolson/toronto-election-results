"""Same-office incumbency evidence for federal candidacies.

Elections Canada's candidate-level incumbent flag is retained as a review signal,
but it is not proof of membership in the final sitting roster under this project's
district-independent definition.

With the House of Commons membership in ``data/reference/house_of_commons_members.csv``,
each federal event from 1994 on gets the complete sitting roster on its reference date:
every member whose term covers that day, in any riding. Each Toronto member term is tied
to the Person who won the seat on the day the term began, which gives that Person an
Office tenure with the House's dates. A confirmed Person whose run is in the event is
then ``True`` if they hold a sitting term and ``False`` otherwise. The build fails if a
candidate's name fits a sitting member who is not their Person, so a namesake can never
turn into ``False`` or ``True`` without review.

The 1993 general election, the first in the release, is older than the membership file.
It keeps the earlier conservative evidence, which carries a confirmed Person forward from
verified election continuity and never emits a complete roster.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .schema import stable_id

HOUSE_MEMBERS_FILENAME = "house_of_commons_members.csv"
HOUSE_MEMBER_COLUMNS = (
    "parliament",
    "house_person_id",
    "first_name",
    "last_name",
    "constituency",
    "province",
    "caucus",
    "from_date",
    "to_date",
    "source",
)
# Short and long forms of a given name that ballots and House records use for one person.
_GIVEN_NAME_FORMS = {
    "al": "albert",
    "alex": "alexander",
    "andy": "andrew",
    "bill": "william",
    "bob": "robert",
    "chris": "christopher",
    "dan": "daniel",
    "dave": "david",
    "dick": "richard",
    "don": "donald",
    "doug": "douglas",
    "ed": "edward",
    "fred": "frederick",
    "gerry": "gerald",
    "greg": "gregory",
    "jack": "john",
    "jerry": "gerald",
    "jim": "james",
    "joe": "joseph",
    "judy": "judith",
    "ken": "kenneth",
    "larry": "lawrence",
    "len": "leonard",
    "maggie": "margaret",
    "mike": "michael",
    "nate": "nathaniel",
    "nick": "nicholas",
    "pat": "patrick",
    "peggy": "margaret",
    "phil": "philip",
    "ray": "raymond",
    "rick": "richard",
    "rob": "robert",
    "ron": "ronald",
    "sam": "samuel",
    "steve": "stephen",
    "ted": "edward",
    "tom": "thomas",
    "tony": "anthony",
    "vic": "victor",
}


def _words(text: object) -> list[str]:
    folded = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]+", " ", folded.casefold()).split()


def _given_names_fit(first: list[str], second: list[str]) -> bool:
    if first and second and len(first[0]) > 1 and len(second[0]) > 1:
        short, long = sorted((first[0], second[0]), key=len)
        if long.startswith(short):
            return True
    first = [_GIVEN_NAME_FORMS.get(word, word) for word in first]
    second = [_GIVEN_NAME_FORMS.get(word, word) for word in second]
    if not first or not second:
        return True
    if first[0] == second[0]:
        return True
    if any(a == b for a in first for b in second if len(a) > 1 and len(b) > 1):
        return True
    return first[0][0] == second[0][0] and (len(first[0]) == 1 or len(second[0]) == 1)


def house_member_name_fits(first_name: object, last_name: object, candidate_name: object) -> bool:
    """Whether a House member's name could be the person printed on a ballot.

    The surname must match, ignoring spaces within it (DiNovo and Di Novo), and the given names
    must fit: the same name, a common short form or the start of the longer name (Al for Allan),
    a shared middle name or an initial.
    """

    printed = str(candidate_name)
    if printed.count(",") == 1:
        family, given_names = printed.split(",")
        printed = f"{given_names} {family}"
    ballot = _words(printed)
    surname = _words(last_name)
    if not ballot or not surname:
        return False
    if ballot[-len(surname) :] == surname:
        given = ballot[: -len(surname)]
    elif ballot[-1] == surname[-1]:
        given = ballot[:-1]
    else:
        joined = "".join(surname)
        tails = [k for k in range(1, min(3, len(ballot)) + 1) if "".join(ballot[-k:]) == joined]
        if not tails:
            return False
        given = ballot[: -tails[0]]
    return _given_names_fit(given, _words(first_name))


def _district_key(name: object) -> str:
    # Any dash separates the parts of a district name: High Park-Swansea, High Park—Swansea.
    return " ".join(_words(re.sub(r"[^\w]+", " ", str(name))))


def read_house_members(reference: Path) -> pd.DataFrame | None:
    """Read the House of Commons member terms, or ``None`` when the file is absent."""

    path = reference / HOUSE_MEMBERS_FILENAME
    if not path.is_file():
        return None
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = sorted(set(HOUSE_MEMBER_COLUMNS) - set(table.columns))
    if missing:
        raise ValueError(f"{HOUSE_MEMBERS_FILENAME} is missing: {', '.join(missing)}")
    for column in ("from_date", "to_date"):
        filled = table[column].ne("")
        if pd.to_datetime(table.loc[filled, column], errors="coerce").isna().any():
            raise ValueError(f"{HOUSE_MEMBERS_FILENAME}.{column} holds an invalid date")
    if table["from_date"].eq("").any():
        raise ValueError(f"{HOUSE_MEMBERS_FILENAME} requires a from_date on every term")
    ended = table["to_date"].ne("")
    if (table.loc[ended, "to_date"] < table.loc[ended, "from_date"]).any():
        raise ValueError(f"{HOUSE_MEMBERS_FILENAME} has a term that ends before it starts")
    return table.loc[:, list(HOUSE_MEMBER_COLUMNS)].copy()


@dataclass(frozen=True)
class FederalRosterEvidence:
    """Event-scoped prior-holder tenures and conservative roster snapshots."""

    office_tenures: pd.DataFrame
    rosters: pd.DataFrame


@dataclass(frozen=True)
class FederalGeneralRosterReference:
    """Official dissolution evidence and the final sitting-roster date."""

    dissolution_date: str
    reference_date: str
    source_url: str


FEDERAL_GENERAL_ROSTER_REFERENCES: dict[str, FederalGeneralRosterReference] = {
    "ec-ge-35": FederalGeneralRosterReference(
        "1993-09-08",
        "1993-09-07",
        "https://www.ourcommons.ca/documentviewer/en/35-1/house/sitting-1/journals",
    ),
    "ec-ge-36": FederalGeneralRosterReference(
        "1997-04-27",
        "1997-04-26",
        "https://www.elections.ca/content.aspx?anchor=circonscription&dir=rep%2Foff%2Fdec3097&document=synopsis02&lang=e&section=res",
    ),
    "ec-ge-37": FederalGeneralRosterReference(
        "2000-10-22",
        "2000-10-21",
        "https://www.elections.ca/content.aspx?section=res&dir=rep/off/37g&document=synopsis02&lang=e",
    ),
    "ec-ge-38": FederalGeneralRosterReference(
        "2004-05-23",
        "2004-05-22",
        "https://www.elections.ca/content.aspx?dir=rep/off/sta2004&document=part2_div1&lang=e&section=res",
    ),
    "ec-ge-39": FederalGeneralRosterReference(
        "2005-11-29",
        "2005-11-28",
        "https://www.elections.ca/content.aspx?dir=rep/off/sta_2006&document=p2&lang=e&section=res",
    ),
    "ec-ge-40": FederalGeneralRosterReference(
        "2008-09-07",
        "2008-09-06",
        "https://www.elections.ca/content.aspx?dir=rep/off/sta_2008&document=p2&lang=e&section=res",
    ),
    "ec-ge-41": FederalGeneralRosterReference(
        "2011-03-26",
        "2011-03-25",
        "https://www.elections.ca/res/rep/off/sta_2011/stat_report2011_e.pdf",
    ),
    "ec-ge-42": FederalGeneralRosterReference(
        "2015-08-02",
        "2015-08-01",
        "https://www.elections.ca/content.aspx?dir=rep/off/sta_2015&document=p2&lang=e&section=res",
    ),
    "ec-ge-43": FederalGeneralRosterReference(
        "2019-09-11",
        "2019-09-10",
        "https://www.elections.ca/content.aspx?dir=rep/off/sta_ge43&document=p2&lang=e&section=res",
    ),
    "ec-ge-44": FederalGeneralRosterReference(
        "2021-08-15",
        "2021-08-14",
        "https://www.elections.ca/content.aspx?dir=rep/off/sta_ge44&document=p2&lang=e&section=res",
    ),
    "ec-ge-45": FederalGeneralRosterReference(
        "2025-03-23",
        "2025-03-22",
        "https://www.elections.ca/content.aspx?dir=rep/off/sta_ge45&document=for&lang=e&section=res",
    ),
}


TENURE_COLUMNS = [
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

ROSTER_COLUMNS = [
    "event_id",
    "person_id",
    "represented_body",
    "office_type",
    "office_tenure_id",
    "roster_complete",
    "reference_date",
    "reference_date_rule",
    "source_detail",
]


def _truth(value: object) -> bool:
    return False if pd.isna(value) else bool(value)


def _one_value(group: pd.DataFrame, column: str, scope: object) -> object:
    values = group[column].drop_duplicates()
    if len(values) != 1:
        raise ValueError(f"{column} is inconsistent in federal event {scope!r}")
    return values.iloc[0]


def build_federal_roster_evidence(candidacies: pd.DataFrame) -> FederalRosterEvidence:
    """Build true-only federal prior-holder evidence, independent of district.

    A current candidate is a roster member when their most recent earlier House
    candidacy was elected after the last preceding general election and no later
    winner replaced them in that electoral district.  This covers a prior general-
    election winner and a by-election winner even when boundaries or district names
    later change.  Authority-reported incumbent flags are deliberately ignored as
    roster proof.
    """

    required = {
        "candidacy_id",
        "event_id",
        "election_date",
        "election_type",
        "election_authority",
        "represented_body",
        "office_type",
        "person_id",
        "district_id",
        "elected",
        "incumbent_reported",
        "source_detail",
    }
    missing = sorted(required - set(candidacies.columns))
    if missing:
        raise ValueError(f"candidacies is missing federal-roster columns: {', '.join(missing)}")

    work = candidacies.loc[
        candidacies["represented_body"].eq("canada_house_of_commons")
        & candidacies["office_type"].eq("mp")
    ].copy()
    if work.empty:
        return FederalRosterEvidence(
            pd.DataFrame(columns=TENURE_COLUMNS),
            pd.DataFrame(columns=ROSTER_COLUMNS),
        )
    work["_election_date"] = pd.to_datetime(work["election_date"], errors="raise")
    if work["_election_date"].isna().any():
        raise ValueError("federal election_date cannot be null")

    event_metadata: dict[str, tuple[pd.Timestamp, str]] = {}
    for event_id, group in work.groupby("event_id", sort=False):
        event_date = _one_value(group, "_election_date", event_id)
        event_type = str(_one_value(group, "election_type", event_id))
        if event_type not in {"general", "by_election"}:
            raise ValueError(f"unknown federal election_type {event_type!r}")
        linked = group.loc[group["person_id"].notna(), "person_id"]
        if linked.duplicated().any():
            raise ValueError(f"duplicate Person candidacy in federal event {event_id!r}")
        event_metadata[str(event_id)] = (event_date, event_type)

    general_dates = sorted(
        {
            event_date
            for event_date, event_type in event_metadata.values()
            if event_type == "general"
        }
    )
    tenure_rows: list[dict[str, object]] = []
    roster_rows: list[dict[str, object]] = []

    ordered_events = sorted(event_metadata.items(), key=lambda item: (item[1][0], item[0]))
    for event_id, (event_date, event_type) in ordered_events:
        group = work.loc[work["event_id"].eq(event_id)]
        represented_body = str(_one_value(group, "represented_body", event_id))
        office_type = str(_one_value(group, "office_type", event_id))
        reference_date, reference_date_rule, reference_evidence = _roster_reference(
            event_id, event_date, event_type, group
        )
        preceding_generals = [date for date in general_dates if date < event_date]
        cycle_start = max(preceding_generals) if preceding_generals else None
        members: list[tuple[pd.Series, pd.Series | None, str]] = []

        for _, current in group.loc[group["person_id"].notna()].iterrows():
            prior: pd.Series | None = None
            evidence_rule: str | None = None
            history = work.loc[
                work["person_id"].eq(current["person_id"]) & work["_election_date"].lt(event_date)
            ].sort_values(["_election_date", "event_id", "candidacy_id"])
            if not history.empty:
                prior = history.iloc[-1]
                within_cycle = cycle_start is None or prior["_election_date"] >= cycle_start
                if within_cycle and _truth(prior["elected"]):
                    later_seat_winner = work.loc[
                        work["district_id"].eq(prior["district_id"])
                        & work["_election_date"].gt(prior["_election_date"])
                        & work["_election_date"].lt(event_date)
                        & work["elected"].eq(True).fillna(False)
                    ]
                    if later_seat_winner.empty:
                        evidence_rule = (
                            "most_recent_prior_candidacy_elected_in_cycle_without_later_seat_winner"
                        )
            if evidence_rule is not None:
                members.append((current, prior, evidence_rule))

        for current, prior, evidence_rule in members:
            person_id = str(current["person_id"])
            tenure_id = stable_id("ten", "federal_prior_holder", event_id, person_id)
            if prior is not None:
                started_on: object = prior["_election_date"].date().isoformat()
                started_precision = "election_date"
                district_id: object = prior["district_id"]
                entry_method = "election"
                prior_evidence: object = {
                    "candidacy_id": prior["candidacy_id"],
                    "event_id": prior["event_id"],
                    "election_date": prior["_election_date"].date().isoformat(),
                    "elected": True,
                    "district_id": prior["district_id"],
                    "source_detail": prior["source_detail"],
                }
            else:
                started_on = pd.NA
                started_precision = "unknown"
                district_id = current["district_id"]
                entry_method = "unknown"
                prior_evidence = None

            detail = json.dumps(
                {
                    "evidence_rule": evidence_rule,
                    "roster_reference": reference_evidence,
                    "authority_reported_flag_used_as_review_signal_only": True,
                    "current_candidacy": {
                        "candidacy_id": current["candidacy_id"],
                        "event_id": event_id,
                        "incumbent_reported": (
                            None
                            if pd.isna(current["incumbent_reported"])
                            else bool(current["incumbent_reported"])
                        ),
                        "source_detail": current["source_detail"],
                    },
                    "prior_elected_candidacy": prior_evidence,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            tenure_rows.append(
                {
                    "office_tenure_id": tenure_id,
                    "person_id": person_id,
                    "represented_body": represented_body,
                    "office_type": office_type,
                    "district_id": district_id,
                    "started_on": started_on,
                    "started_on_precision": started_precision,
                    "ended_on": reference_date,
                    "ended_on_precision": "at_or_after_reference",
                    "entry_method": entry_method,
                    "source_authority": current["election_authority"],
                    "source_detail": detail,
                }
            )
            roster_rows.append(
                {
                    "event_id": event_id,
                    "person_id": person_id,
                    "represented_body": represented_body,
                    "office_type": office_type,
                    "office_tenure_id": tenure_id,
                    "roster_complete": False,
                    "reference_date": reference_date,
                    "reference_date_rule": reference_date_rule,
                    "source_detail": detail,
                }
            )

        if not members:
            roster_rows.append(
                {
                    "event_id": event_id,
                    "person_id": pd.NA,
                    "represented_body": represented_body,
                    "office_type": office_type,
                    "office_tenure_id": pd.NA,
                    "roster_complete": False,
                    "reference_date": reference_date,
                    "reference_date_rule": reference_date_rule,
                    "source_detail": json.dumps(
                        {
                            "evidence_rule": "no_confirmed_positive_evidence",
                            "roster_reference": reference_evidence,
                            "authority_reported_flag_used_as_review_signal_only": True,
                        },
                        sort_keys=True,
                    ),
                }
            )

    tenures = pd.DataFrame(tenure_rows, columns=TENURE_COLUMNS)
    rosters = pd.DataFrame(roster_rows, columns=ROSTER_COLUMNS)
    rosters["roster_complete"] = rosters["roster_complete"].astype("boolean")
    return FederalRosterEvidence(tenures, rosters)


def _roster_reference(
    event_id: str, event_date: pd.Timestamp, event_type: str, group: pd.DataFrame
) -> tuple[str, str, dict[str, object]]:
    """The sitting-roster date of a federal event, its rule and its evidence."""

    if event_type == "general":
        official_reference = FEDERAL_GENERAL_ROSTER_REFERENCES.get(event_id)
        if official_reference is None:
            raise ValueError(
                f"federal general event {event_id!r} has no official dissolution reference"
            )
        return (
            official_reference.reference_date,
            "day_before_official_parliament_dissolution",
            {
                "dissolution_date": official_reference.dissolution_date,
                "reference_date": official_reference.reference_date,
                "source_url": official_reference.source_url,
            },
        )
    reference_date = (event_date - pd.Timedelta(days=1)).date().isoformat()
    return (
        reference_date,
        "day_before_federal_by_election_polling_day",
        {
            "polling_date": event_date.date().isoformat(),
            "reference_date": reference_date,
            "source_urls": sorted(set(group["source_detail"].astype(str))),
        },
    )


def _house_member_record(member: pd.Series) -> dict[str, object]:
    return {
        "parliament": int(member["parliament"]),
        "house_person_id": member["house_person_id"] or None,
        "name": f"{member['first_name']} {member['last_name']}",
        "constituency": member["constituency"],
        "province": member["province"],
        "caucus": member["caucus"] or None,
        "from_date": member["from_date"],
        "to_date": member["to_date"] or None,
        "source": member["source"],
    }


@dataclass(frozen=True)
class MembershipRosterSpec:
    """How one legislature's membership file becomes Office tenures and complete rosters."""

    represented_body: str
    office_type: str
    district_column: str
    member_label: str
    tenure_namespace: str
    tenure_rule: str
    member_key: str
    roster_rule: str
    membership_filename: str
    member_id_columns: tuple[str, ...]
    member_record: Callable[[pd.Series], dict[str, object]]
    source_authority: Callable[[pd.Series], str]
    roster_reference: Callable[
        [str, pd.Timestamp, str, pd.DataFrame], tuple[str, str, dict[str, object]]
    ]
    # A member whose term no winner in the release began, tied by a source to the Person of a run.
    member_persons: dict[str, MemberIdentity] = field(default_factory=dict)
    # A member whose name fits a run by a different Person, shown by a source to be someone else.
    namesakes: tuple[MemberIdentity, ...] = ()


@dataclass(frozen=True)
class MemberIdentity:
    """A source's statement that a member is, or is not, the Person of one run."""

    member_key: str
    candidacy_id: str
    rationale: str
    source_urls: tuple[str, ...]


def build_membership_roster_evidence(
    candidacies: pd.DataFrame, members: pd.DataFrame, spec: MembershipRosterSpec
) -> tuple[FederalRosterEvidence, frozenset[str]]:
    """Build complete rosters from a legislature's membership file.

    Each member term that began on a polling day is tied to the winner of that seat on that
    day, which gives the winner's Person an Office tenure with the legislature's dates. Every
    event whose reference date falls on or after the file's first day gets the complete
    sitting roster on that date. The build fails if a member term cannot be told apart from
    another winner, if a winner in the file's years has no term, or if a confirmed candidate's
    name fits a sitting member who is not their Person. Returns the evidence and the events it
    covers.
    """

    work = candidacies.loc[
        candidacies["represented_body"].eq(spec.represented_body)
        & candidacies["office_type"].eq(spec.office_type)
    ].copy()
    empty = FederalRosterEvidence(
        pd.DataFrame(columns=TENURE_COLUMNS), pd.DataFrame(columns=ROSTER_COLUMNS)
    )
    if work.empty or members.empty:
        return empty, frozenset()
    work["_election_date"] = pd.to_datetime(work["election_date"], errors="raise")
    work["_polling_day"] = work["_election_date"].dt.date.astype(str)
    work["_district_key"] = work["district_name"].map(_district_key)
    first_day = str(members["from_date"].min())

    winners = work.loc[work["elected"].eq(True).fillna(False)]
    seat_winner: dict[int, pd.Series] = {}
    by_district: dict[int, pd.DataFrame] = {}
    for index, member in members.iterrows():
        same_day = winners.loc[winners["_polling_day"].eq(member["from_date"])]
        if not same_day.empty:
            by_district[int(index)] = same_day.loc[
                same_day["_district_key"].eq(_district_key(member[spec.district_column]))
            ]
    # A winner whose district a member term names cannot also be tied by name to another term.
    named_seats = {seat.iloc[0]["candidacy_id"] for seat in by_district.values() if len(seat) == 1}
    for index, member in members.iterrows():
        seat = by_district.get(int(index))
        if seat is None:
            continue
        if len(seat) != 1:
            same_day = winners.loc[
                winners["_polling_day"].eq(member["from_date"])
                & ~winners["candidacy_id"].isin(named_seats)
            ]
            fits = [
                house_member_name_fits(member["first_name"], member["last_name"], name)
                for name in same_day["candidate_name"]
            ]
            seat = same_day.loc[fits]
        if len(seat) != 1:
            continue
        winner = seat.iloc[0]
        if not house_member_name_fits(
            member["first_name"], member["last_name"], winner["candidate_name"]
        ):
            raise ValueError(
                f"{spec.member_label} {member['first_name']} {member['last_name']} does not fit "
                f"the name of {winner['candidate_name']!r}, who won "
                f"{member[spec.district_column]!r}"
            )
        seat_winner[int(index)] = winner

    linked_winners = [winner["candidacy_id"] for winner in seat_winner.values()]
    if len(linked_winners) != len(set(linked_winners)):
        raise ValueError(f"two {spec.member_label} terms tie to one winner")
    covered_winners = winners.loc[winners["_polling_day"].ge(first_day), "candidacy_id"]
    without_term = sorted(set(covered_winners) - set(linked_winners))
    if without_term:
        raise ValueError(
            f"{spec.membership_filename} has no term for the winner {without_term[0]!r}"
        )

    tenure_rows: list[dict[str, object]] = []
    tenure_of_member: dict[int, tuple[str, str]] = {}
    for index, winner in sorted(seat_winner.items()):
        if pd.isna(winner["person_id"]):
            continue
        member = members.loc[index]
        person_id = str(winner["person_id"])
        tenure_id = stable_id(
            "ten",
            spec.tenure_namespace,
            person_id,
            member["from_date"],
            member[spec.district_column],
        )
        tenure_of_member[index] = (tenure_id, person_id)
        detail = {
            "evidence_rule": spec.tenure_rule,
            spec.member_key: spec.member_record(member),
            "elected_candidacy": {
                "candidacy_id": winner["candidacy_id"],
                "event_id": winner["event_id"],
                "election_date": winner["_polling_day"],
                "source_detail": winner["source_detail"],
            },
        }
        tenure_rows.append(
            {
                "office_tenure_id": tenure_id,
                "person_id": person_id,
                "represented_body": spec.represented_body,
                "office_type": spec.office_type,
                "district_id": winner["district_id"],
                "started_on": member["from_date"],
                "started_on_precision": "election_date",
                "ended_on": member["to_date"] or pd.NA,
                "ended_on_precision": "exact" if member["to_date"] else "ongoing",
                "entry_method": "election",
                "source_authority": spec.source_authority(member),
                "source_detail": json.dumps(
                    detail, ensure_ascii=False, sort_keys=True, default=str
                ),
            }
        )

    keys = _member_keys(members, spec)
    person_of_run = work.set_index("candidacy_id")["person_id"]
    for index, member in members.iterrows():
        identity = spec.member_persons.get(keys[index])
        if identity is None or int(index) in tenure_of_member:
            continue
        if identity.candidacy_id not in person_of_run.index:
            raise ValueError(f"{identity.member_key} is tied to an unknown run")
        person_id = person_of_run[identity.candidacy_id]
        if pd.isna(person_id):
            raise ValueError(f"{identity.member_key} is tied to a run with no Person")
        tenure_id = stable_id(
            "ten",
            spec.tenure_namespace,
            str(person_id),
            member["from_date"],
            member[spec.district_column],
        )
        tenure_of_member[int(index)] = (tenure_id, str(person_id))
        detail = {
            "evidence_rule": "member_tied_to_person_by_source",
            spec.member_key: spec.member_record(member),
            "identity": {
                "candidacy_id": identity.candidacy_id,
                "rationale": identity.rationale,
                "source_urls": list(identity.source_urls),
            },
        }
        tenure_rows.append(
            {
                "office_tenure_id": tenure_id,
                "person_id": str(person_id),
                "represented_body": spec.represented_body,
                "office_type": spec.office_type,
                "district_id": pd.NA,
                "started_on": member["from_date"],
                "started_on_precision": "election_date",
                "ended_on": member["to_date"] or pd.NA,
                "ended_on_precision": "exact" if member["to_date"] else "ongoing",
                "entry_method": "election",
                "source_authority": spec.source_authority(member),
                "source_detail": json.dumps(
                    detail, ensure_ascii=False, sort_keys=True, default=str
                ),
            }
        )
    namesakes = {
        (identity.member_key, str(person_of_run.get(identity.candidacy_id)))
        for identity in spec.namesakes
    }
    _continue_member_tenures(members, spec, tenure_rows, tenure_of_member)

    roster_rows: list[dict[str, object]] = []
    covered: set[str] = set()
    events = (
        work.groupby("event_id", sort=False)
        .agg(date=("_election_date", "first"), type=("election_type", "first"))
        .sort_values(["date"])
    )
    for event_id, event in events.iterrows():
        group = work.loc[work["event_id"].eq(event_id)]
        reference_date, rule, reference = spec.roster_reference(
            str(event_id), event["date"], str(event["type"]), group
        )
        if reference_date < first_day:
            continue
        covered.add(str(event_id))
        sitting = members.loc[
            members["from_date"].le(reference_date)
            & (members["to_date"].eq("") | members["to_date"].ge(reference_date))
        ]
        by_surname: dict[str, list[int]] = {}
        for index, member in sitting.iterrows():
            words = _words(member["last_name"])
            if words:
                by_surname.setdefault(words[-1], []).append(int(index))
        for _, run in group.loc[group["person_id"].notna()].iterrows():
            ballot = _words(run["candidate_name"])
            for index in by_surname.get(ballot[-1] if ballot else "", []):
                member = members.loc[index]
                if not house_member_name_fits(
                    member["first_name"], member["last_name"], run["candidate_name"]
                ):
                    continue
                if (keys[index], str(run["person_id"])) in namesakes:
                    continue
                if tenure_of_member.get(index, ("", ""))[1] != str(run["person_id"]):
                    raise ValueError(
                        f"{run['candidate_name']!r} in {event_id!r} fits the sitting member "
                        f"{member['first_name']} {member['last_name']} "
                        f"({member[spec.district_column]}), who is not their Person"
                    )
        listed = {
            tenure_of_member[index][1]: tenure_of_member[index][0]
            for index in sitting.index
            if index in tenure_of_member
        }
        detail = json.dumps(
            {
                "evidence_rule": spec.roster_rule,
                "roster_reference": reference,
                "sitting_members": len(sitting),
                "membership_source": f"data/reference/{spec.membership_filename}",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for person_id, tenure_id in sorted(listed.items()) or [(pd.NA, pd.NA)]:
            roster_rows.append(
                {
                    "event_id": event_id,
                    "person_id": person_id,
                    "represented_body": spec.represented_body,
                    "office_type": spec.office_type,
                    "office_tenure_id": tenure_id,
                    "roster_complete": True,
                    "reference_date": reference_date,
                    "reference_date_rule": rule,
                    "source_detail": detail,
                }
            )

    tenures = pd.DataFrame(tenure_rows, columns=TENURE_COLUMNS)
    rosters = pd.DataFrame(roster_rows, columns=ROSTER_COLUMNS)
    rosters["roster_complete"] = rosters["roster_complete"].astype("boolean")
    return FederalRosterEvidence(tenures, rosters), frozenset(covered)


def _member_keys(members: pd.DataFrame, spec: MembershipRosterSpec) -> pd.Series:
    return members[list(spec.member_id_columns)].astype(str).agg("|".join, axis=1)


def _continue_member_tenures(
    members: pd.DataFrame,
    spec: MembershipRosterSpec,
    tenure_rows: list[dict[str, object]],
    tenure_of_member: dict[int, tuple[str, str]],
) -> None:
    """Carry a Person's tenure into a later term of the same member that no polling day began.

    A riding renamed during a Parliament gives its member a new term from the day of the change.
    That term belongs to the tenure the member's election began, which then ends with it.
    """

    rows = {row["office_tenure_id"]: row for row in tenure_rows}
    for _, terms in members.groupby(_member_keys(members, spec), sort=False):
        current: int | None = None
        for index, member in terms.sort_values("from_date", kind="stable").iterrows():
            index = int(index)
            if index in tenure_of_member:
                current = index
                continue
            if current is None:
                continue
            tied = members.loc[current]
            day_after = (pd.Timestamp(tied["to_date"]) + pd.Timedelta(days=1)).date().isoformat()
            if tied["to_date"] and member["from_date"] > day_after:
                current = None
                continue
            tenure_of_member[index] = tenure_of_member[current]
            row = rows[tenure_of_member[current][0]]
            ends = [str(row["ended_on"]) if pd.notna(row["ended_on"]) else "", member["to_date"]]
            row["ended_on"] = pd.NA if "" in ends else max(ends)
            row["ended_on_precision"] = "ongoing" if "" in ends else "exact"
            detail = json.loads(row["source_detail"])
            detail.setdefault("continued_in", []).append(spec.member_record(member))
            row["source_detail"] = json.dumps(
                detail, ensure_ascii=False, sort_keys=True, default=str
            )


HOUSE_ROSTER_SPEC = MembershipRosterSpec(
    represented_body="canada_house_of_commons",
    office_type="mp",
    district_column="constituency",
    member_label="House member",
    tenure_namespace="house_of_commons_member",
    tenure_rule="house_member_term_of_seat_winner",
    member_key="house_member",
    roster_rule="complete_house_of_commons_membership_on_reference_date",
    membership_filename=HOUSE_MEMBERS_FILENAME,
    member_id_columns=("house_person_id", "first_name", "last_name"),
    member_record=lambda member: _house_member_record(member),
    source_authority=lambda member: (
        "Library of Parliament (ParlInfo)" if member["parliament"] == "35" else "House of Commons"
    ),
    roster_reference=lambda event_id, date, kind, group: _roster_reference(
        event_id, date, kind, group
    ),
)


def build_house_roster_evidence(
    candidacies: pd.DataFrame, members: pd.DataFrame
) -> tuple[FederalRosterEvidence, frozenset[str]]:
    """Build complete federal rosters from House of Commons membership.

    Returns the evidence and the events it covers: every federal event whose reference date
    falls on or after the first day of the membership file.
    """

    return build_membership_roster_evidence(candidacies, members, HOUSE_ROSTER_SPEC)


def federal_roster_evidence(
    candidacies: pd.DataFrame, house_members: pd.DataFrame | None = None
) -> FederalRosterEvidence:
    """House-membership rosters where they reach, the conservative evidence elsewhere."""

    prior = build_federal_roster_evidence(candidacies)
    if house_members is None:
        return prior
    house, covered = build_house_roster_evidence(candidacies, house_members)
    kept_rosters = prior.rosters.loc[~prior.rosters["event_id"].isin(covered)]
    kept_tenures = prior.office_tenures.loc[
        prior.office_tenures["office_tenure_id"].isin(kept_rosters["office_tenure_id"].dropna())
    ]
    tenures = pd.concat([kept_tenures, house.office_tenures], ignore_index=True)
    rosters = pd.concat([kept_rosters, house.rosters], ignore_index=True)
    rosters["roster_complete"] = rosters["roster_complete"].astype("boolean")
    return FederalRosterEvidence(tenures, rosters)
