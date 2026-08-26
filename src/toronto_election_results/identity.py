"""Persistent Person registry and evidence-backed incumbency joins.

Election files describe candidacies, not durable people.  This module therefore
never equates normalized names with identity.  A Person is attached only through an
active, explicitly confirmed registry link; proposed name matches remain visible in
the link table but publish a null ``person_id`` on the modelling table.
"""

from __future__ import annotations

import uuid

import pandas as pd

PERSON_STATUSES = {"active", "deprecated"}
LINK_STATUSES = {"confirmed", "proposed", "rejected", "unresolved"}


def new_person_id() -> str:
    """Create a new opaque Person identity for persistence in the registry."""

    return f"per_{uuid.uuid4().hex}"


def _required(frame: pd.DataFrame, columns: set[str], table: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{table} is missing required columns: {', '.join(missing)}")


def _active_links(links: pd.DataFrame) -> pd.Series:
    return links["valid_to_release"].isna()


def validate_identity_tables(people: pd.DataFrame, links: pd.DataFrame) -> None:
    """Validate referential integrity and append-only correction semantics."""

    _required(
        people,
        {"person_id", "preferred_name", "identity_status", "redirect_to_person_id"},
        "people",
    )
    _required(
        links,
        {
            "candidacy_id",
            "person_id",
            "link_status",
            "method",
            "evidence",
            "reviewer",
            "valid_from_release",
            "valid_to_release",
        },
        "candidacy_person_links",
    )

    if people["person_id"].isna().any() or people["person_id"].duplicated().any():
        raise ValueError("people.person_id must be non-null and unique")
    bad_status = ~people["identity_status"].isin(PERSON_STATUSES)
    if bad_status.any():
        raise ValueError(
            f"unknown identity_status: {people.loc[bad_status, 'identity_status'].iloc[0]!r}"
        )

    person_ids = set(people["person_id"])
    missing_people = links["person_id"].notna() & ~links["person_id"].isin(person_ids)
    if missing_people.any():
        raise ValueError(
            "candidacy_person_links references unknown person_id "
            f"{links.loc[missing_people, 'person_id'].iloc[0]!r}"
        )
    invalid_links = ~links["link_status"].isin(LINK_STATUSES)
    if invalid_links.any():
        raise ValueError(
            f"unknown link_status: {links.loc[invalid_links, 'link_status'].iloc[0]!r}"
        )

    redirects = people["redirect_to_person_id"].notna()
    bad_redirect_targets = redirects & ~people["redirect_to_person_id"].isin(person_ids)
    if bad_redirect_targets.any():
        raise ValueError("redirect_to_person_id must reference an existing Person")
    active_with_redirect = people["identity_status"].eq("active") & redirects
    deprecated_without_redirect = people["identity_status"].eq("deprecated") & ~redirects
    if active_with_redirect.any() or deprecated_without_redirect.any():
        raise ValueError("only deprecated people must have a redirect_to_person_id")
    self_redirect = redirects & people["person_id"].eq(people["redirect_to_person_id"])
    if self_redirect.any():
        raise ValueError("a Person cannot redirect to itself")

    confirmed = links["link_status"].eq("confirmed") & _active_links(links)
    active_confirmed = links.loc[confirmed]
    conflicts = active_confirmed.groupby("candidacy_id")["person_id"].nunique()
    if (conflicts > 1).any():
        candidacy_id = conflicts[conflicts > 1].index[0]
        raise ValueError(f"candidacy {candidacy_id!r} has multiple active confirmed people")
    incomplete_evidence = confirmed & (
        links["person_id"].isna()
        | links["method"].isna()
        | links["evidence"].isna()
        | links["reviewer"].isna()
    )
    if incomplete_evidence.any():
        raise ValueError("active confirmed links require person, method, evidence, and reviewer")

    active_person_claims = links.loc[_active_links(links) & links["person_id"].notna()]
    claim_counts = active_person_claims.groupby("candidacy_id").size()
    if (claim_counts > 1).any():
        candidacy_id = claim_counts[claim_counts > 1].index[0]
        raise ValueError(f"candidacy {candidacy_id!r} has multiple active Person claims")


def _canonical_people(people: pd.DataFrame) -> dict[str, str]:
    redirects = dict(
        people.loc[
            people["redirect_to_person_id"].notna(), ["person_id", "redirect_to_person_id"]
        ].itertuples(index=False, name=None)
    )
    resolved: dict[str, str] = {}
    for person_id in people["person_id"]:
        current = person_id
        visited: set[str] = set()
        while current in redirects:
            if current in visited:
                raise ValueError(f"cyclic Person redirect involving {current!r}")
            visited.add(current)
            current = redirects[current]
        resolved[person_id] = current
    return resolved


def attach_confirmed_people(
    candidacies: pd.DataFrame, people: pd.DataFrame, links: pd.DataFrame
) -> pd.DataFrame:
    """Attach canonical Person IDs from active confirmed links only."""

    _required(candidacies, {"candidacy_id"}, "candidacies")
    validate_identity_tables(people, links)
    canonical = _canonical_people(people)

    confirmed = links.loc[
        links["link_status"].eq("confirmed") & _active_links(links),
        ["candidacy_id", "person_id", "method", "evidence"],
    ].drop_duplicates(["candidacy_id", "person_id"])
    confirmed["person_id"] = confirmed["person_id"].map(canonical)
    confirmed = confirmed.rename(
        columns={"method": "person_link_method", "evidence": "person_link_evidence"}
    )

    out = candidacies.drop(
        columns=["person_id", "person_link_method", "person_link_evidence"], errors="ignore"
    ).merge(confirmed, on="candidacy_id", how="left", validate="one_to_one")
    out["person_id"] = out["person_id"].astype("string")
    return out


def derive_incumbency(candidacies: pd.DataFrame, rosters: pd.DataFrame) -> pd.DataFrame:
    """Derive incumbency from the last valid same-body, same-office roster.

    A listed, confirmed Person proves ``True`` even if the roster is incomplete.
    Absence proves ``False`` only when that event/body/office roster is certified
    complete.  A missing Person link or incomplete/missing roster remains null.
    District identity is intentionally absent from the match, so boundary changes do
    not erase incumbency and a councillor running for mayor is not a mayor incumbent.
    """

    _required(
        candidacies,
        {"candidacy_id", "event_id", "represented_body", "office_type", "person_id"},
        "candidacies",
    )
    _required(
        rosters,
        {
            "event_id",
            "person_id",
            "represented_body",
            "office_type",
            "office_tenure_id",
            "roster_complete",
            "reference_date",
            "source_detail",
        },
        "incumbency_rosters",
    )

    scope = ["event_id", "represented_body", "office_type"]
    for column in ["roster_complete", "reference_date"]:
        counts = rosters.groupby(scope, dropna=False)[column].nunique(dropna=False)
        if (counts > 1).any():
            raise ValueError(f"{column} is inconsistent within an incumbency roster scope")

    roster_lookup: dict[tuple[object, object, object], dict[str, object]] = {}
    for key, group in rosters.groupby(scope, dropna=False, sort=False):
        members = group.loc[group["person_id"].notna()]
        duplicate_members = members["person_id"].duplicated(keep=False)
        if duplicate_members.any():
            raise ValueError(f"duplicate Person in incumbency roster scope {key!r}")
        roster_lookup[key] = {
            "complete": bool(group["roster_complete"].iloc[0]),
            "members": dict(
                members[["person_id", "office_tenure_id"]].itertuples(index=False, name=None)
            ),
        }

    incumbent: list[object] = []
    tenure_ids: list[object] = []
    for row in candidacies.itertuples(index=False):
        person_id = row.person_id
        if pd.isna(person_id):
            incumbent.append(pd.NA)
            tenure_ids.append(pd.NA)
            continue

        key = (row.event_id, row.represented_body, row.office_type)
        roster = roster_lookup.get(key)
        if roster is None:
            incumbent.append(pd.NA)
            tenure_ids.append(pd.NA)
            continue

        members = roster["members"]
        if person_id in members:
            incumbent.append(True)
            tenure_ids.append(members[person_id])
        elif roster["complete"]:
            incumbent.append(False)
            tenure_ids.append(pd.NA)
        else:
            incumbent.append(pd.NA)
            tenure_ids.append(pd.NA)

    out = candidacies.copy()
    out["incumbent"] = pd.array(incumbent, dtype="boolean")
    out["incumbent_office_tenure_id"] = pd.array(tenure_ids, dtype="string")
    return out
