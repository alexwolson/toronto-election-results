"""Date the Toronto City Council roster tenures once every Candidacy has its final Person.

A Council roster row says that a Person sat on Council on the eve of a general election. The
roster step resolves that Person before the identity curations run, and it dates the row from
the member's latest win under the exact name the roster prints. That misses a win the result
prints another way (Adrian Heaps for the roster's A.A. Heaps), and it can reach back past the
term to a seat the member had already left: Joe Mihevc's 2014 win in Ward 21 had dated the
Ward 10 seat Council appointed him to in 2022. This step dates every roster row again from the
Person's latest Council win in the term, at the term's first general election or a by-election
since, or, for a member Council appointed to fill a vacancy, from the appointment recorded in
``data/reference/council_appointments.csv``. It fails when a row fits neither, when a member
with a win in the term is also recorded as appointed, and when an appointment matches no row.
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pandas as pd

COUNCIL_APPOINTMENTS_FILENAME = "council_appointments.csv"
APPOINTMENT_COLUMNS = (
    "term",
    "official_district_id",
    "member_name",
    "predecessor",
    "appointed_on",
    "basis",
    "source_url",
)
_BODY = "toronto_city_council"
_ROSTER_RULE = "last_valid_council_composition_before_general_election"


def read_council_appointments(path: Path) -> pd.DataFrame | None:
    """Read and check the appointment reference, or return None when it is absent."""

    if not path.is_file():
        return None
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")
    ]
    frame = pd.read_csv(StringIO("\n".join(lines)), dtype=str, keep_default_na=False)
    if tuple(frame.columns) != APPOINTMENT_COLUMNS:
        raise ValueError(f"{path.name} columns must be {', '.join(APPOINTMENT_COLUMNS)}")
    blank = frame.eq("").any(axis=1)
    if blank.any():
        raise ValueError(f"{path.name} has blank cells in data row {int(blank.idxmax()) + 1}")
    if not frame["term"].str.fullmatch(r"\d{4}-\d{4}").all():
        raise ValueError(f"{path.name} terms must read like 2014-2018")
    if not frame["source_url"].str.startswith("https://").all():
        raise ValueError(f"{path.name} source URLs must be https")
    appointed = pd.to_datetime(frame["appointed_on"], format="%Y-%m-%d", errors="coerce")
    if appointed.isna().any():
        raise ValueError(f"{path.name} has an appointment date that is not YYYY-MM-DD")
    first = frame["term"].str[:4].astype(int)
    last = frame["term"].str[-4:].astype(int)
    if not appointed.dt.year.between(first, last).all():
        raise ValueError(f"{path.name} has an appointment dated outside its term")
    if frame.duplicated(["term", "member_name"]).any():
        raise ValueError(f"{path.name} lists a member twice in one term")
    return frame


def _detail(detail: dict[str, object]) -> str:
    return json.dumps(detail, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _appointed_district(
    council: pd.DataFrame, record: pd.Series, opening: pd.Timestamp, end: pd.Timestamp
) -> str:
    """Return the seat's district at the term's first election, checked against the predecessor."""

    seats = council.loc[
        council["_date"].eq(opening)
        & council["office_type"].eq("councillor")
        & council["official_district_id"].eq(record["official_district_id"])
    ]
    districts = seats["district_id"].dropna().unique()
    if len(districts) != 1:
        raise ValueError(
            f"{COUNCIL_APPOINTMENTS_FILENAME}: {record['official_district_id']} matches "
            f"{len(districts)} districts at the {opening.year} general election"
        )
    district = str(districts[0])
    predecessor = council.loc[
        council["_won"]
        & council["district_id"].eq(district).fillna(False).astype(bool)
        & council["_date"].ge(opening)
        & council["_date"].lt(end)
        & council["candidate_name"].str.casefold().eq(str(record["predecessor"]).casefold())
    ]
    if predecessor.empty:
        raise ValueError(
            f"{COUNCIL_APPOINTMENTS_FILENAME}: {record['predecessor']} did not win "
            f"{record['official_district_id']} in the {record['term']} term"
        )
    if pd.Timestamp(record["appointed_on"]) <= predecessor["_date"].max():
        raise ValueError(
            f"{COUNCIL_APPOINTMENTS_FILENAME}: {record['member_name']} is dated before "
            f"{record['predecessor']} won the seat"
        )
    return district


def date_council_rosters(
    tenures: pd.DataFrame, candidacies: pd.DataFrame, appointments: pd.DataFrame
) -> pd.DataFrame:
    """Return the tenures with each Council roster row dated from its own term."""

    out = tenures.copy()
    out["started_on"] = out["started_on"].astype(object)
    council = candidacies.loc[candidacies["represented_body"].eq(_BODY)].copy()
    for column in ("election_type", "office_type", "official_district_id", "candidate_name"):
        council[column] = council[column].astype("string").fillna("")
    council["_date"] = pd.to_datetime(council["election_date"])
    council["_won"] = council["elected"].astype("boolean").fillna(False).astype(bool)
    generals = sorted(council.loc[council["election_type"].eq("general"), "_date"].unique())
    wins = council.loc[council["_won"] & council["person_id"].notna()]
    records = {
        (int(record["term"][-4:]), record["member_name"]): record
        for _, record in appointments.iterrows()
    }
    used: set[tuple[int, str]] = set()
    for index, row in out.iterrows():
        if row["represented_body"] != _BODY or pd.isna(row["source_detail"]):
            continue
        detail = json.loads(row["source_detail"])
        if detail.get("rule") != _ROSTER_RULE:
            continue
        end = pd.Timestamp(row["ended_on"])
        earlier = [day for day in generals if day < end]
        if not earlier:
            raise ValueError(f"no Council general election precedes the {end.year} roster")
        opening = pd.Timestamp(earlier[-1])
        member = str(detail["member_name"])
        own = wins.loc[
            wins["person_id"].eq(row["person_id"])
            & wins["office_type"].eq(row["office_type"])
            & wins["_date"].ge(opening)
            & wins["_date"].lt(end)
        ]
        key = (end.year, member)
        record = records.get(key)
        if not own.empty:
            if record is not None or detail.get("entry_method") == "appointment":
                raise ValueError(
                    f"{member} won a Council seat in the term before the {end.year} election "
                    "but is recorded as appointed"
                )
            anchor = own.sort_values(["_date", "candidacy_id"], kind="stable").iloc[-1]
            out.at[index, "started_on"] = anchor["_date"].date()
            out.at[index, "started_on_precision"] = "election_date"
            out.at[index, "district_id"] = anchor["district_id"]
            out.at[index, "entry_method"] = "election"
        elif record is not None:
            if detail.get("entry_method", "appointment") != "appointment":
                raise ValueError(
                    f"{member} is recorded as appointed but the {end.year} roster says "
                    f"{detail['entry_method']}"
                )
            if row["office_type"] != "councillor":
                raise ValueError(f"{member} is recorded as appointed to a seat that is not a ward")
            out.at[index, "started_on"] = pd.Timestamp(record["appointed_on"]).date()
            out.at[index, "started_on_precision"] = "appointment_date"
            out.at[index, "district_id"] = _appointed_district(council, record, opening, end)
            out.at[index, "entry_method"] = "appointment"
            detail["appointment"] = {
                "appointed_on": record["appointed_on"],
                "predecessor": record["predecessor"],
                "source_url": record["source_url"],
            }
            out.at[index, "source_detail"] = _detail(detail)
            used.add(key)
        else:
            raise ValueError(
                f"Council roster member {member!r} at the {end.year} election has no Council win "
                f"in the term and no row in {COUNCIL_APPOINTMENTS_FILENAME}"
            )
    unused = sorted(set(records) - used)
    if unused:
        year, member = unused[0]
        raise ValueError(
            f"{COUNCIL_APPOINTMENTS_FILENAME} names {member} in the term before the {year} "
            "election, but no Council roster row is theirs"
        )
    return out


def council_by_election_rosters(
    rosters: pd.DataFrame,
    candidacies: pd.DataFrame,
    tenures: pd.DataFrame,
    *,
    pending_rule: str,
) -> pd.DataFrame:
    """Settle each council by-election's councillor scope once every Person is final.

    A council by-election fills one vacant ward. Anyone on Council the day before polling won
    a seat at the term's first general election or at a by-election since, or was appointed
    since, and every appointment is in the dated roster tenures. A Candidacy whose Person is in
    neither group cannot have sat, so the scope can prove ``incumbent=false``. The build fails
    when a candidate's Person is in either group, since that member may still sit or may have
    left, and the release has no record of which.
    """

    pending = (
        rosters["represented_body"].eq(_BODY)
        & rosters["office_type"].eq("councillor")
        & rosters["reference_date_rule"].eq(pending_rule)
    )
    if not pending.any():
        return rosters
    council = candidacies.loc[candidacies["represented_body"].eq(_BODY)].copy()
    council["_date"] = pd.to_datetime(council["election_date"])
    council["_won"] = council["elected"].astype("boolean").fillna(False).astype(bool)
    generals = sorted(council.loc[council["election_type"].eq("general"), "_date"].unique())
    seats = tenures.loc[
        tenures["represented_body"].eq(_BODY)
        & tenures["office_type"].eq("councillor")
        & tenures["entry_method"].eq("appointment")
    ].copy()
    seats["_appointed"] = pd.to_datetime(seats["started_on"])

    settled = []
    for _, row in rosters.loc[pending].iterrows():
        event = council.loc[council["event_id"].eq(row["event_id"])]
        if event.empty or not event["election_type"].eq("by_election").all():
            raise ValueError(f"council by-election roster {row['event_id']} has no by-election")
        polling = event["_date"].iloc[0]
        earlier = [day for day in generals if day < polling]
        if not earlier:
            raise ValueError(f"no Council general election precedes {row['event_id']}")
        opening = pd.Timestamp(earlier[-1])
        won = council.loc[
            council["_won"]
            & council["office_type"].eq("councillor")
            & council["person_id"].notna()
            & council["_date"].ge(opening)
            & council["_date"].lt(polling)
        ]
        appointed = seats.loc[seats["_appointed"].ge(opening) & seats["_appointed"].lt(polling)]
        members = set(won["person_id"].astype(str)) | set(appointed["person_id"].astype(str))
        running = event.loc[event["office_type"].eq("councillor") & event["person_id"].notna()]
        holders = sorted(
            running.loc[running["person_id"].astype(str).isin(members), "candidacy_id"]
        )
        if holders:
            raise ValueError(
                f"council by-election {row['event_id']}: Candidacy {holders[0]} belongs to a "
                "Person who won or was appointed to a Council seat in the term"
            )
        out = row.copy()
        out["roster_complete"] = True
        out["reference_date_rule"] = "no_candidate_won_or_was_appointed_to_a_seat_in_the_term"
        out["source_detail"] = _detail(
            {
                "appointments_in_term": len(appointed),
                "event_id": str(row["event_id"]),
                "rule": "council_by_election_candidates_hold_no_seat",
                "seats_won_in_term": len(won),
                "term_opened": opening.date().isoformat(),
            }
        )
        settled.append(out)
    return pd.concat(
        [rosters.loc[~pending], pd.DataFrame(settled)], ignore_index=True, sort=False
    ).astype({"roster_complete": "boolean"})
