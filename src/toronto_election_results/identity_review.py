"""Conservative, reviewable bootstrap for persistent Person identities.

An official result row with a globally unique exact name may safely anchor a
singleton Person.  In a repeated exact-name block, only the earliest occurrence may
anchor a Person without continuity evidence; later occurrences remain unlinked. This
module joins occurrences across election dates only when an official incumbent flag,
an official prior elected result, an exact normalized name, and matching
represented-body/office scope all agree.

The bootstrap output is deliberately versioned and compatible with
``identity.attach_confirmed_people``.  Exact-name-only possibilities are emitted as
proposals; ambiguity and contradictory continuity claims are emitted as unresolved
links plus explicit review flags.
"""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from dataclasses import dataclass

import pandas as pd

from .identity import validate_identity_tables

_PERSON_NAMESPACE = uuid.UUID("ec146986-00cf-5608-a69f-2a28ef1fa55e")
_REVIEWER = "identity_review.bootstrap/v1"
_WHITESPACE = re.compile(r"\s+")

_REQUIRED_COLUMNS = {
    "candidacy_id",
    "event_id",
    "election_date",
    "represented_body",
    "office_type",
    "candidate_name_raw",
    "elected",
    "incumbent_reported",
}

_PEOPLE_COLUMNS = [
    "person_id",
    "preferred_name",
    "identity_status",
    "redirect_to_person_id",
    "created_release",
]
_LINK_COLUMNS = [
    "candidacy_id",
    "person_id",
    "link_status",
    "method",
    "evidence",
    "reviewer",
    "valid_from_release",
    "valid_to_release",
]
_FLAG_COLUMNS = [
    "review_flag_id",
    "candidacy_id",
    "flag_type",
    "severity",
    "related_candidacy_ids",
    "detail",
    "release_id",
]


@dataclass(frozen=True)
class IdentityReview:
    """Versioned identity tables plus items requiring human curation."""

    people: pd.DataFrame
    candidacy_person_links: pd.DataFrame
    review_flags: pd.DataFrame


def _clean_text(value: object) -> str | None:
    if value is None or value is pd.NA or pd.isna(value):
        return None
    cleaned = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", str(value))).strip()
    return cleaned or None


def _exact_name_key(value: object) -> str:
    cleaned = _clean_text(value)
    if cleaned is None:
        raise ValueError("candidate_name_raw cannot be null or blank")
    # Punctuation and diacritics intentionally remain significant.  This is exact
    # Unicode/spacing/case normalization, not fuzzy identity matching.
    return cleaned.casefold()


def _opaque_person_id(anchor_candidacy_id: str) -> str:
    """Derive an opaque bootstrap ID from source occurrence identity, not a name."""

    return f"per_{uuid.uuid5(_PERSON_NAMESPACE, f'candidacy:{anchor_candidacy_id}').hex}"


def _review_flag_id(flag_type: str, candidacy_id: str, related: list[str]) -> str:
    payload = "\x1f".join([flag_type, candidacy_id, *sorted(related)])
    return f"irf_{uuid.uuid5(_PERSON_NAMESPACE, payload).hex}"


def _boolean(series: pd.Series, column: str) -> pd.Series:
    try:
        return series.astype("boolean")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{column} must contain booleans or nulls") from exc


def _source_record(row: pd.Series) -> dict[str, object]:
    record: dict[str, object] = {"candidacy_id": str(row["candidacy_id"])}
    for column in ["source_authority", "source_resource", "source_detail"]:
        if column not in row.index:
            continue
        value = _clean_text(row[column])
        if value is not None:
            record[column] = value
    return record


def _has_official_source_detail(row: pd.Series) -> bool:
    return any(
        _clean_text(row.get(column)) is not None for column in ["source_resource", "source_detail"]
    )


def _evidence(rule: str, **records: object) -> str:
    return json.dumps(
        {"rule": rule, **records}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _flag(
    *,
    release_id: str,
    candidacy_id: str,
    flag_type: str,
    severity: str,
    related: list[str],
    detail: str,
) -> dict[str, object]:
    return {
        "review_flag_id": _review_flag_id(flag_type, candidacy_id, related),
        "candidacy_id": candidacy_id,
        "flag_type": flag_type,
        "severity": severity,
        "related_candidacy_ids": json.dumps(sorted(related), separators=(",", ":")),
        "detail": detail,
        "release_id": release_id,
    }


def _validate(candidacies: pd.DataFrame, release_id: object) -> tuple[pd.DataFrame, str]:
    clean_release = _clean_text(release_id)
    if clean_release is None:
        raise ValueError("release_id cannot be null or blank")
    missing = sorted(_REQUIRED_COLUMNS - set(candidacies.columns))
    if missing:
        raise ValueError(f"candidacies is missing required columns: {', '.join(missing)}")
    if candidacies.empty:
        return candidacies.copy(), clean_release

    out = candidacies.copy()
    out["candidacy_id"] = out["candidacy_id"].map(_clean_text).astype("string")
    if out["candidacy_id"].isna().any():
        raise ValueError("candidacy_id cannot be null or blank")
    if out["candidacy_id"].duplicated().any():
        duplicate = out.loc[out["candidacy_id"].duplicated(keep=False), "candidacy_id"].iloc[0]
        raise ValueError(f"duplicate candidacy_id: {duplicate!r}")

    out["_date"] = pd.to_datetime(out["election_date"], errors="coerce")
    if out["_date"].isna().any():
        bad = out.loc[out["_date"].isna(), "election_date"].iloc[0]
        raise ValueError(f"invalid election_date: {bad!r}")
    for column in ["event_id", "represented_body", "office_type"]:
        out[column] = out[column].map(_clean_text).astype("string")
        if out[column].isna().any():
            raise ValueError(f"{column} cannot be null or blank")
    display_source = (
        out["candidate_name"].fillna(out["candidate_name_raw"])
        if "candidate_name" in out
        else out["candidate_name_raw"]
    )
    out["_display_name"] = display_source.map(_clean_text).astype("string")
    if out["_display_name"].isna().any():
        raise ValueError("candidate_name cannot be null or blank")
    out["_name_key"] = out["_display_name"].map(_exact_name_key)
    out["elected"] = _boolean(out["elected"], "elected")
    out["incumbent_reported"] = _boolean(out["incumbent_reported"], "incumbent_reported")
    return out, clean_release


def bootstrap_identity_review(candidacies: pd.DataFrame, *, release_id: str) -> IdentityReview:
    """Create a conservative Person registry and a deterministic review queue.

    A globally unique name occurrence, or the earliest occurrence in a repeated
    exact-name block, may anchor a source-backed Person.  Other repeated occurrences
    remain null unless, in chronological batches, they join an older Person under
    all of these conditions:

    * ``incumbent_reported`` is officially true;
    * prior officially elected candidacies with the exact normalized name resolve
      to exactly one Person;
    * represented body and office type are identical; and
    * both sides retain official source resource/detail evidence.

    District is deliberately not part of the confirmation rule, so boundary changes
    do not break continuity. Similar spelling, party, geography, or vote patterns
    never confirm a link. Exact-name review proposals are global across bodies and
    offices so a curator can establish cross-office careers from stronger evidence.
    """

    work, release = _validate(candidacies, release_id)
    if work.empty:
        return IdentityReview(
            pd.DataFrame(columns=_PEOPLE_COLUMNS),
            pd.DataFrame(columns=_LINK_COLUMNS),
            pd.DataFrame(columns=_FLAG_COLUMNS),
        )

    work = work.sort_values(["_date", "candidacy_id"], kind="stable").reset_index(drop=True)
    by_id = work.set_index("candidacy_id", drop=False)
    parent = {str(candidacy_id): str(candidacy_id) for candidacy_id in work["candidacy_id"]}

    def find(candidacy_id: str) -> str:
        current = candidacy_id
        while parent[current] != current:
            parent[current] = parent[parent[current]]
            current = parent[current]
        return current

    continuity_evidence: dict[str, str] = {}
    flags: list[dict[str, object]] = []
    unresolved: dict[str, tuple[str, list[str], str]] = {}

    # Process a whole date before applying links, preventing rows from the same
    # election date from serving as one another's evidence.
    for election_date, current_rows in work.groupby("_date", sort=True):
        earlier = work.loc[work["_date"] < election_date]
        edge_candidates: list[tuple[str, str, str]] = []

        for _, current in current_rows.iterrows():
            if not bool(current["incumbent_reported"] is True):
                continue
            same_scope = earlier.loc[
                earlier["represented_body"].eq(current["represented_body"])
                & earlier["office_type"].eq(current["office_type"])
                & earlier["_name_key"].eq(current["_name_key"])
                & earlier["elected"].eq(True)
            ]
            prior_roots = sorted({find(str(value)) for value in same_scope["candidacy_id"]})
            current_id = str(current["candidacy_id"])

            if not prior_roots:
                flags.append(
                    _flag(
                        release_id=release,
                        candidacy_id=current_id,
                        flag_type="incumbent_without_prior_elected_match",
                        severity="warning",
                        related=[],
                        detail=(
                            "Official incumbent flag has no earlier elected exact-name match "
                            "in the same represented body and office type."
                        ),
                    )
                )
                unresolved[current_id] = (
                    "incumbent_without_prior_elected_match",
                    [],
                    "No safe prior elected identity was available.",
                )
                continue
            if len(prior_roots) > 1:
                related = sorted(
                    str(value)
                    for value in same_scope.loc[
                        same_scope["candidacy_id"]
                        .map(lambda value: find(str(value)))
                        .isin(prior_roots),
                        "candidacy_id",
                    ]
                )
                flags.append(
                    _flag(
                        release_id=release,
                        candidacy_id=current_id,
                        flag_type="ambiguous_prior_elected_identity",
                        severity="error",
                        related=related,
                        detail=(
                            "More than one prior identity cluster has an elected exact-name "
                            "record in the same represented body and office type."
                        ),
                    )
                )
                unresolved[current_id] = (
                    "ambiguous_prior_elected_identity",
                    related,
                    "Multiple prior elected identity clusters require human resolution.",
                )
                continue

            prior_root = prior_roots[0]
            prior_candidates = same_scope.loc[
                same_scope["candidacy_id"].map(lambda value: find(str(value))).eq(prior_root)
            ].sort_values(["_date", "candidacy_id"], ascending=[False, True], kind="stable")
            prior = prior_candidates.iloc[0]
            prior_id = str(prior["candidacy_id"])
            if not (_has_official_source_detail(current) and _has_official_source_detail(prior)):
                related = [prior_id]
                flags.append(
                    _flag(
                        release_id=release,
                        candidacy_id=current_id,
                        flag_type="missing_official_source_evidence",
                        severity="error",
                        related=related,
                        detail=(
                            "The continuity rule matched, but source_resource/source_detail "
                            "was missing on the current or prior official result."
                        ),
                    )
                )
                unresolved[current_id] = (
                    "missing_official_source_evidence",
                    related,
                    "Official source evidence is incomplete.",
                )
                continue

            evidence = _evidence(
                "official_incumbent_to_prior_elected_exact_name",
                current=_source_record(current),
                prior=_source_record(prior),
                represented_body=str(current["represented_body"]),
                office_type=str(current["office_type"]),
                name_match="exact_normalized",
            )
            edge_candidates.append((current_id, prior_root, evidence))

        # It is impossible for one Person to have two candidacies for the same body
        # and office on one election date.  Block every edge in such a collision so
        # iteration order cannot silently choose a winner.
        grouped_edges: dict[tuple[str, str, str], list[tuple[str, str, str]]] = {}
        for current_id, prior_root, evidence in edge_candidates:
            current = by_id.loc[current_id]
            key = (
                str(current["represented_body"]),
                str(current["office_type"]),
                prior_root,
            )
            grouped_edges.setdefault(key, []).append((current_id, prior_root, evidence))

        for edges in grouped_edges.values():
            if len(edges) > 1:
                current_ids = sorted(current_id for current_id, _, _ in edges)
                for current_id, _, _ in edges:
                    related = [value for value in current_ids if value != current_id]
                    flags.append(
                        _flag(
                            release_id=release,
                            candidacy_id=current_id,
                            flag_type="simultaneous_candidacy_identity_conflict",
                            severity="error",
                            related=related,
                            detail=(
                                "Two simultaneous candidacies would resolve to the same "
                                "prior Person in one represented-body/office scope."
                            ),
                        )
                    )
                    unresolved[current_id] = (
                        "simultaneous_candidacy_identity_conflict",
                        related,
                        "Conflicting simultaneous continuity claims require human resolution.",
                    )
                continue

            current_id, prior_root, evidence = edges[0]
            parent[current_id] = prior_root
            continuity_evidence[current_id] = evidence

    # Resolve paths after every chronological union. A repeated display-name block
    # can publish at most one automatic Person. If authority-reported continuity
    # exists, that stronger cluster wins over an earlier name-only singleton. This
    # prevents two active People from asserting that they are the same unreviewed
    # exact-name individual; the displaced occurrence remains merely proposed.
    roots = {candidacy_id: find(candidacy_id) for candidacy_id in parent}
    eligible_roots: set[str] = set()
    for _name_key, name_group in work.groupby("_name_key", sort=False):
        group_ids = [str(value) for value in name_group["candidacy_id"]]
        continuity_roots = {
            roots[candidacy_id] for candidacy_id in group_ids if candidacy_id in continuity_evidence
        }
        if len(continuity_roots) == 1:
            eligible_roots.update(continuity_roots)
        elif not continuity_roots:
            eligible_roots.add(roots[group_ids[0]])
        else:
            related = sorted(group_ids)
            for candidacy_id in related:
                unresolved.setdefault(
                    candidacy_id,
                    (
                        "multiple_authoritative_continuity_clusters",
                        [value for value in related if value != candidacy_id],
                        "Multiple exact-name continuity clusters require curated identity evidence.",
                    ),
                )
                flags.append(
                    _flag(
                        release_id=release,
                        candidacy_id=candidacy_id,
                        flag_type="multiple_authoritative_continuity_clusters",
                        severity="error",
                        related=[value for value in related if value != candidacy_id],
                        detail=(
                            "The exact display name has more than one independent official "
                            "continuity cluster; no Person was published automatically."
                        ),
                    )
                )
    person_ids = {root: _opaque_person_id(root) for root in sorted(eligible_roots)}

    people_rows: list[dict[str, object]] = []
    for root in sorted(
        person_ids,
        key=lambda value: (by_id.loc[value, "_date"], value),
    ):
        anchor = by_id.loc[root]
        people_rows.append(
            {
                "person_id": person_ids[root],
                "preferred_name": str(anchor["_display_name"]),
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": release,
            }
        )

    link_rows: list[dict[str, object]] = []
    confirmed_candidacies: set[str] = set()
    for _, row in work.iterrows():
        candidacy_id = str(row["candidacy_id"])
        root = roots[candidacy_id]
        if root not in eligible_roots:
            continue
        continuity = continuity_evidence.get(candidacy_id)
        if continuity is None:
            method = "official_candidacy_record"
            evidence = _evidence("source_candidacy_anchor", source=_source_record(row))
        else:
            method = "official_incumbent_continuity"
            evidence = continuity
        link_rows.append(
            {
                "candidacy_id": candidacy_id,
                "person_id": person_ids[root],
                "link_status": "confirmed",
                "method": method,
                "evidence": evidence,
                "reviewer": _REVIEWER,
                "valid_from_release": release,
                "valid_to_release": pd.NA,
            }
        )
        confirmed_candidacies.add(candidacy_id)

    # Exact-name repeats that did not satisfy the continuity rule are useful review
    # candidates, but remain non-authoritative. Review scope is intentionally global:
    # an MP and MPP with the same exact name may be the same person, but office/body
    # continuity cannot prove that. Target only a unique published Person; ambiguity
    # remains an unresolved null link.
    eligible_roots_by_name: dict[str, list[str]] = {}
    for root in eligible_roots:
        eligible_roots_by_name.setdefault(str(by_id.loc[root, "_name_key"]), []).append(root)
    root_members: dict[str, list[str]] = {}
    for candidacy_id, root in roots.items():
        root_members.setdefault(root, []).append(candidacy_id)
    for members in root_members.values():
        members.sort()

    for _, current in work.iterrows():
        current_id = str(current["candidacy_id"])
        if current_id in confirmed_candidacies:
            continue
        target_roots = sorted(eligible_roots_by_name.get(str(current["_name_key"]), []))
        if len(target_roots) == 1:
            target_root = target_roots[0]
            related = root_members[target_root]
            link_rows.append(
                {
                    "candidacy_id": current_id,
                    "person_id": person_ids[target_root],
                    "link_status": "proposed",
                    "method": "exact_normalized_name_review",
                    "evidence": _evidence(
                        "exact_name_only_not_identity_evidence",
                        current=_source_record(current),
                        related_candidacy_ids=related,
                        review_scope="global_across_represented_bodies_and_office_types",
                    ),
                    "reviewer": _REVIEWER,
                    "valid_from_release": release,
                    "valid_to_release": pd.NA,
                }
            )
        elif len(target_roots) > 1:
            related = sorted(
                candidacy_id for root in target_roots for candidacy_id in root_members[root]
            )
            unresolved.setdefault(
                current_id,
                (
                    "ambiguous_exact_name_proposal",
                    related,
                    "Exact-name candidates map to multiple published People.",
                ),
            )
            flags.append(
                _flag(
                    release_id=release,
                    candidacy_id=current_id,
                    flag_type="ambiguous_exact_name_proposal",
                    severity="warning",
                    related=related,
                    detail="Exact name alone cannot choose among multiple prior People.",
                )
            )
        else:
            unresolved.setdefault(
                current_id,
                (
                    "no_confirmed_exact_name_target",
                    [],
                    "No published Person is available for a safe review proposal.",
                ),
            )

    for candidacy_id, (method, related, detail) in sorted(unresolved.items()):
        link_rows.append(
            {
                "candidacy_id": candidacy_id,
                "person_id": pd.NA,
                "link_status": "unresolved",
                "method": method,
                "evidence": _evidence(
                    "human_review_required",
                    candidacy_id=candidacy_id,
                    related_candidacy_ids=related,
                    detail=detail,
                ),
                "reviewer": _REVIEWER,
                "valid_from_release": release,
                "valid_to_release": pd.NA,
            }
        )

    people = pd.DataFrame(people_rows, columns=_PEOPLE_COLUMNS)
    links = pd.DataFrame(link_rows, columns=_LINK_COLUMNS).sort_values(
        ["candidacy_id", "link_status", "person_id"], kind="stable", na_position="last"
    )
    review_flags = pd.DataFrame(flags, columns=_FLAG_COLUMNS)
    if not review_flags.empty:
        review_flags = review_flags.drop_duplicates("review_flag_id").sort_values(
            ["severity", "flag_type", "candidacy_id"], kind="stable"
        )

    people["person_id"] = people["person_id"].astype("string")
    people["redirect_to_person_id"] = people["redirect_to_person_id"].astype("string")
    links["person_id"] = links["person_id"].astype("string")
    links["valid_to_release"] = links["valid_to_release"].astype("string")
    return IdentityReview(
        people.reset_index(drop=True),
        links.reset_index(drop=True),
        review_flags.reset_index(drop=True),
    )


def _canonical_person_ids(people: pd.DataFrame) -> dict[str, str]:
    redirects = dict(
        people.loc[
            people["redirect_to_person_id"].notna(),
            ["person_id", "redirect_to_person_id"],
        ].itertuples(index=False, name=None)
    )
    resolved: dict[str, str] = {}
    for value in people["person_id"]:
        person_id = str(value)
        current = person_id
        visited: set[str] = set()
        while current in redirects:
            if current in visited:
                raise ValueError(f"cyclic Person redirect involving {current!r}")
            visited.add(current)
            current = str(redirects[current])
        resolved[person_id] = current
    return resolved


def extend_identity_review(
    candidacies: pd.DataFrame,
    people: pd.DataFrame,
    candidacy_person_links: pd.DataFrame,
    *,
    release_id: str,
) -> IdentityReview:
    """Extend, rather than recreate, a prior versioned identity registry.

    Bootstrap evidence is recalculated for the cumulative result set, then anchored
    to every overlapping active confirmed Person from the prior release.  Existing
    Person and link rows are retained byte-for-byte; only previously unseen active
    Candidacies receive new bootstrap rows.  This makes audited IDs and closed link
    history operational inputs to later releases.
    """

    validate_identity_tables(people, candidacy_person_links)
    current_ids = set(candidacies["candidacy_id"].astype(str))
    historical_ids = set(candidacy_person_links["candidacy_id"].astype(str))
    absent = sorted(historical_ids - current_ids)
    if absent:
        raise ValueError(
            "the prior identity registry references a Candidacy absent from the "
            f"cumulative release: {absent[0]!r}"
        )

    bootstrap = bootstrap_identity_review(candidacies, release_id=release_id)
    canonical = _canonical_person_ids(people)
    active_prior = candidacy_person_links.loc[candidacy_person_links["valid_to_release"].isna()]
    prior_confirmed = active_prior.loc[
        active_prior["link_status"].eq("confirmed") & active_prior["person_id"].notna(),
        ["candidacy_id", "person_id"],
    ].copy()
    prior_confirmed["person_id"] = prior_confirmed["person_id"].astype(str).map(canonical)
    prior_by_candidacy = dict(prior_confirmed.itertuples(index=False, name=None))

    bootstrap_confirmed = bootstrap.candidacy_person_links.loc[
        bootstrap.candidacy_person_links["link_status"].eq("confirmed")
        & bootstrap.candidacy_person_links["person_id"].notna(),
        ["candidacy_id", "person_id"],
    ]
    person_mapping: dict[str, str] = {}
    existing_person_ids = set(people["person_id"].astype(str))
    for bootstrap_person_id, group in bootstrap_confirmed.groupby("person_id", sort=False):
        targets = {
            prior_by_candidacy[str(candidacy_id)]
            for candidacy_id in group["candidacy_id"]
            if str(candidacy_id) in prior_by_candidacy
        }
        if len(targets) > 1:
            raise ValueError(
                "bootstrap continuity conflicts with multiple prior People for "
                f"{bootstrap_person_id!r}"
            )
        if targets:
            person_mapping[str(bootstrap_person_id)] = next(iter(targets))
        elif str(bootstrap_person_id) in existing_person_ids:
            person_mapping[str(bootstrap_person_id)] = str(bootstrap_person_id)
        else:
            person_mapping[str(bootstrap_person_id)] = str(bootstrap_person_id)

    new_person_ids = {
        source
        for source, target in person_mapping.items()
        if source == target and target not in existing_person_ids
    }
    new_people = bootstrap.people.loc[
        bootstrap.people["person_id"].astype(str).isin(new_person_ids)
    ].copy()
    merged_people = pd.concat([people.copy(), new_people], ignore_index=True, sort=False)

    active_prior_candidacies = set(active_prior["candidacy_id"].astype(str))
    new_links = bootstrap.candidacy_person_links.loc[
        ~bootstrap.candidacy_person_links["candidacy_id"].astype(str).isin(active_prior_candidacies)
    ].copy()
    new_links["person_id"] = new_links["person_id"].map(
        lambda value: pd.NA if pd.isna(value) else person_mapping.get(str(value), str(value))
    )
    merged_links = pd.concat(
        [candidacy_person_links.copy(), new_links], ignore_index=True, sort=False
    )
    merged_people = merged_people.sort_values("person_id", kind="stable").reset_index(drop=True)
    merged_links = merged_links.sort_values(
        ["candidacy_id", "valid_from_release", "link_status", "person_id"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    merged_people["person_id"] = merged_people["person_id"].astype("string")
    merged_people["redirect_to_person_id"] = merged_people["redirect_to_person_id"].astype("string")
    merged_links["person_id"] = merged_links["person_id"].astype("string")
    merged_links["valid_to_release"] = merged_links["valid_to_release"].astype("string")
    validate_identity_tables(merged_people, merged_links)
    return IdentityReview(merged_people, merged_links, bootstrap.review_flags)
