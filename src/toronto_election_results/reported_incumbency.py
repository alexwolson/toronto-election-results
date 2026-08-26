"""Turn authority-reported incumbent flags into auditable roster evidence."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .schema import stable_id


@dataclass(frozen=True)
class ReportedIncumbency:
    office_tenures: pd.DataFrame
    rosters: pd.DataFrame


@dataclass(frozen=True)
class OntarioGeneralRosterReference:
    """Official dissolution evidence and the final sitting-roster date."""

    dissolution_date: str
    reference_date: str
    source_url: str


_ONTARIO_DISSOLUTION_REPORT = (
    "https://results.elections.on.ca/api/report-groups/48/report-outputs/1091/pdf/en"
)

ONTARIO_GENERAL_ROSTER_REFERENCES: dict[str, OntarioGeneralRosterReference] = {
    "on-2003-general": OntarioGeneralRosterReference(
        "2003-09-02", "2003-09-01", _ONTARIO_DISSOLUTION_REPORT
    ),
    "on-2007-general": OntarioGeneralRosterReference(
        "2007-09-10", "2007-09-09", _ONTARIO_DISSOLUTION_REPORT
    ),
    "on-2011-general": OntarioGeneralRosterReference(
        "2011-09-07", "2011-09-06", _ONTARIO_DISSOLUTION_REPORT
    ),
    "on-2014-general": OntarioGeneralRosterReference(
        "2014-05-02", "2014-05-01", _ONTARIO_DISSOLUTION_REPORT
    ),
    "on-2018-general": OntarioGeneralRosterReference(
        "2018-05-08", "2018-05-07", _ONTARIO_DISSOLUTION_REPORT
    ),
    "on-2022-general": OntarioGeneralRosterReference(
        "2022-05-03", "2022-05-02", _ONTARIO_DISSOLUTION_REPORT
    ),
    "on-2025-general": OntarioGeneralRosterReference(
        "2025-01-25", "2025-01-24", _ONTARIO_DISSOLUTION_REPORT
    ),
}


def build_reported_incumbency(candidacies: pd.DataFrame) -> ReportedIncumbency:
    """Build same-body/same-office roster snapshots from official flags.

    A scope is complete only when every Candidacy has an authority-reported flag
    and every reported incumbent has a confirmed Person link.  This means absence
    can prove ``False`` without treating an unresolved identity as a different
    individual.  Reported ``True`` remains useful even in an incomplete scope.
    """

    required = {
        "candidacy_id",
        "event_id",
        "election_date",
        "election_authority",
        "represented_body",
        "office_type",
        "person_id",
        "incumbent_reported",
        "source_detail",
    }
    missing = sorted(required - set(candidacies.columns))
    if missing:
        raise ValueError(
            f"candidacies is missing reported-incumbency columns: {', '.join(missing)}"
        )

    work = candidacies.copy()
    work["incumbent_reported"] = work["incumbent_reported"].astype("boolean")
    scope_columns = ["event_id", "represented_body", "office_type"]
    tenure_rows: list[dict[str, object]] = []
    roster_rows: list[dict[str, object]] = []

    for scope, group in work.groupby(scope_columns, sort=False, dropna=False):
        event_id, represented_body, office_type = scope
        election_dates = group["election_date"].drop_duplicates()
        if len(election_dates) != 1:
            raise ValueError(f"election_date is inconsistent in incumbency scope {scope!r}")
        election_date = election_dates.iloc[0]
        ontario_reference = ONTARIO_GENERAL_ROSTER_REFERENCES.get(str(event_id))
        if represented_body == "ontario_legislative_assembly" and ontario_reference:
            reference_date: object = ontario_reference.reference_date
            reference_date_rule = "day_before_official_legislature_dissolution"
        else:
            reference_date = election_date
            reference_date_rule = "authority_reported_pre_event_incumbency"
        reported_true = group["incumbent_reported"].eq(True)
        linked_true = reported_true & group["person_id"].notna()
        complete = bool(
            group["incumbent_reported"].notna().all()
            and group.loc[reported_true, "person_id"].notna().all()
        )
        source_details = sorted(set(group["source_detail"].dropna().astype(str)))
        roster_source = ";".join(source_details)

        members = group.loc[linked_true]
        if members["person_id"].duplicated().any():
            raise ValueError(f"duplicate incumbent Person in authority-reported scope {scope!r}")
        for member in members.itertuples(index=False):
            district_id = member.district_id if "district_id" in work.columns else pd.NA
            tenure_id = stable_id(
                "ten",
                "authority_reported",
                event_id,
                represented_body,
                office_type,
                member.person_id,
            )
            tenure_rows.append(
                {
                    "office_tenure_id": tenure_id,
                    "person_id": member.person_id,
                    "represented_body": represented_body,
                    "office_type": office_type,
                    "district_id": district_id,
                    "started_on": pd.NA,
                    "started_on_precision": "unknown",
                    "ended_on": reference_date,
                    "ended_on_precision": "at_or_after_reference",
                    "entry_method": "unknown",
                    "source_authority": member.election_authority,
                    "source_detail": member.source_detail,
                }
            )
            roster_rows.append(
                {
                    "event_id": event_id,
                    "person_id": member.person_id,
                    "represented_body": represented_body,
                    "office_type": office_type,
                    "office_tenure_id": tenure_id,
                    "roster_complete": complete,
                    "reference_date": reference_date,
                    "reference_date_rule": reference_date_rule,
                    "source_detail": member.source_detail,
                }
            )

        if members.empty:
            roster_rows.append(
                {
                    "event_id": event_id,
                    "person_id": pd.NA,
                    "represented_body": represented_body,
                    "office_type": office_type,
                    "office_tenure_id": pd.NA,
                    "roster_complete": complete,
                    "reference_date": reference_date,
                    "reference_date_rule": reference_date_rule,
                    "source_detail": roster_source,
                }
            )

    tenure_columns = [
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
    roster_columns = [
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
    tenures = pd.DataFrame(tenure_rows, columns=tenure_columns)
    rosters = pd.DataFrame(roster_rows, columns=roster_columns)
    if not rosters.empty:
        rosters["roster_complete"] = rosters["roster_complete"].astype("boolean")
    return ReportedIncumbency(tenures, rosters)
