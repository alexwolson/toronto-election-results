"""Conservative same-office incumbency evidence for federal candidacies.

Elections Canada's candidate-level incumbent flag is retained as a review signal,
but it is not proof of membership in the final sitting roster under this project's
district-independent definition.  This module carries a confirmed Person forward
from verified election continuity within the current parliamentary cycle.  It
never emits a complete roster, so absence can never manufacture ``False``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from .schema import stable_id


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
        if event_type == "general":
            official_reference = FEDERAL_GENERAL_ROSTER_REFERENCES.get(event_id)
            if official_reference is None:
                raise ValueError(
                    f"federal general event {event_id!r} has no official dissolution reference"
                )
            reference_date = official_reference.reference_date
            reference_date_rule = "day_before_official_parliament_dissolution"
            reference_evidence = {
                "dissolution_date": official_reference.dissolution_date,
                "reference_date": official_reference.reference_date,
                "source_url": official_reference.source_url,
            }
        else:
            reference_date = (event_date - pd.Timedelta(days=1)).date().isoformat()
            reference_date_rule = "day_before_federal_by_election_polling_day"
            reference_evidence = {
                "polling_date": event_date.date().isoformat(),
                "reference_date": reference_date,
                "source_urls": sorted(set(group["source_detail"].astype(str))),
            }
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
