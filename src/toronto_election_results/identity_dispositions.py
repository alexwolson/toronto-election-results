"""Apply occurrence-level adjudications to the persistent identity registry."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from .identity import validate_identity_tables

_DECISION_STATUSES = {"confirmed", "unresolved", "rejected"}
IDENTITY_REVIEW_DECISION_COLUMNS = (
    "candidacy_id",
    "target_person_id",
    "decision",
    "confidence",
    "rationale",
    "evidence_urls",
    "reviewer",
)


def _validate_decisions(decisions: pd.DataFrame) -> None:
    missing = sorted(set(IDENTITY_REVIEW_DECISION_COLUMNS) - set(decisions.columns))
    if missing:
        raise ValueError(f"identity review decisions are missing: {', '.join(missing)}")
    required_values = [
        "candidacy_id",
        "target_person_id",
        "confidence",
        "rationale",
        "evidence_urls",
        "reviewer",
    ]
    for column in required_values:
        blank = decisions[column].isna() | decisions[column].astype("string").str.strip().eq("")
        if blank.any():
            raise ValueError(f"identity review decisions require nonblank {column}")
    if decisions["candidacy_id"].duplicated().any():
        raise ValueError("identity review decisions require unique candidacy_id values")
    invalid = ~decisions["decision"].isin(_DECISION_STATUSES)
    if invalid.any():
        value = decisions.loc[invalid, "decision"].iloc[0]
        raise ValueError(f"unknown identity review decision: {value!r}")


def read_identity_review_decisions(path: str | Path) -> pd.DataFrame:
    """Read the canonical occurrence-level identity adjudication table."""

    source = Path(path)
    if not source.is_file():
        raise ValueError(f"identity review dispositions source is missing: {source}")
    decisions = pd.read_csv(source, dtype="string")
    _validate_decisions(decisions)
    decisions = decisions.loc[:, IDENTITY_REVIEW_DECISION_COLUMNS].copy()
    for _, row in decisions.iterrows():
        _evidence_urls(row["evidence_urls"])
    return decisions.sort_values("candidacy_id", kind="stable").reset_index(drop=True)


def _evidence_urls(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            decoded = json.loads(stripped)
            values: Iterable[object] = decoded if isinstance(decoded, list) else (decoded,)
        else:
            values = stripped.split(";")
    elif isinstance(value, Iterable):
        values = value
    else:
        values = (value,)
    urls = tuple(str(item).strip() for item in values if str(item).strip())
    if not urls or any(not url.startswith("https://") for url in urls):
        raise ValueError("identity review decisions require HTTPS evidence URLs")
    return urls


def _evidence(row: pd.Series) -> str:
    return json.dumps(
        {
            "confidence": str(row["confidence"]).strip(),
            "decision": str(row["decision"]),
            "evidence_urls": list(_evidence_urls(row["evidence_urls"])),
            "rationale": str(row["rationale"]).strip(),
            "target_person_id": str(row["target_person_id"]),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _follow_redirects(person_id: str, redirects: dict[str, str]) -> str:
    seen = {person_id}
    while person_id in redirects:
        person_id = redirects[person_id]
        if person_id in seen:
            raise ValueError(f"Person redirects form a cycle at {person_id!r}")
        seen.add(person_id)
    return person_id


def apply_identity_review_decisions(
    people: pd.DataFrame,
    candidacy_person_links: pd.DataFrame,
    decisions: pd.DataFrame,
    *,
    release_id: str,
) -> pd.DataFrame:
    """Close reviewed proposals and append their audited final review state.

    ``confirmed`` is the only decision that publishes a Person ID on the modelling
    table. ``unresolved`` retains the candidate Person for audit after an
    insufficient-evidence review, while ``rejected`` records a disproved target.
    An ``unresolved`` decision may also hold a run that the pipeline linked
    automatically, but not one that a curated assertion linked.
    Replaying the same decisions is byte-stable and does not append duplicate rows.
    """

    validate_identity_tables(people, candidacy_person_links)
    _validate_decisions(decisions)
    if not str(release_id).strip():
        raise ValueError("release_id cannot be blank")

    active_people = set(people.loc[people["identity_status"].eq("active"), "person_id"].astype(str))
    redirects = {
        str(person_id): str(target)
        for person_id, target in zip(
            people["person_id"], people["redirect_to_person_id"], strict=True
        )
        if pd.notna(target)
    }
    out = candidacy_person_links.copy()
    new_rows: list[dict[str, object]] = []
    for _, row in decisions.sort_values("candidacy_id", kind="stable").iterrows():
        candidacy_id = str(row["candidacy_id"])
        # A review that named a Person later merged into another applies to the merged Person.
        target_person_id = _follow_redirects(str(row["target_person_id"]), redirects)
        decision = str(row["decision"])
        reviewer = str(row["reviewer"]).strip()
        confidence = str(row["confidence"]).strip()
        rationale = str(row["rationale"]).strip()
        if target_person_id not in active_people:
            raise ValueError(
                f"identity review decision targets non-active Person {target_person_id!r}"
            )
        if not reviewer or not confidence or not rationale:
            raise ValueError(
                "identity review decisions require reviewer, confidence, and rationale"
            )
        evidence = _evidence(row)
        method = f"curated_review_{decision}"
        active = out.loc[out["candidacy_id"].eq(candidacy_id) & out["valid_to_release"].isna()]
        active_claims = active.loc[active["person_id"].notna()]
        already_applied = (
            len(active_claims) == 1
            and active_claims["person_id"].iloc[0] == target_person_id
            and active_claims["link_status"].iloc[0] == decision
            and active_claims["method"].iloc[0] == method
            and active_claims["evidence"].iloc[0] == evidence
            and active_claims["reviewer"].iloc[0] == reviewer
        )
        if already_applied:
            continue
        proposal = active_claims.loc[
            active_claims["link_status"].eq("proposed")
            & active_claims["person_id"].eq(target_person_id)
        ]
        matching_automated_confirmation = active_claims.loc[
            active_claims["link_status"].eq("confirmed")
            & active_claims["person_id"].eq(target_person_id)
        ]
        matching_reviewed_claim = active_claims.loc[
            active_claims["person_id"].eq(target_person_id)
            & active_claims["method"].astype("string").str.startswith("curated_review_")
        ]
        # A review may confirm a link the pipeline made, or hold one whose only support falls
        # short of the standard; a curated link can only be confirmed again.
        automated = ~matching_automated_confirmation["method"].astype("string").str.startswith(
            "curated_"
        )
        can_supersede_confirmation = len(matching_automated_confirmation) == 1 and (
            decision == "confirmed" or (decision == "unresolved" and bool(automated.all()))
        )
        can_revise_review = len(matching_reviewed_claim) == 1
        if len(active_claims) != 1 or (
            len(proposal) != 1 and not can_supersede_confirmation and not can_revise_review
        ):
            raise ValueError(
                f"identity review decision for {candidacy_id!r} does not match exactly one "
                "active proposal or revisable claim to its target Person"
            )
        if len(proposal) == 1:
            prior_claim = proposal
        elif can_supersede_confirmation:
            prior_claim = matching_automated_confirmation
        else:
            prior_claim = matching_reviewed_claim
        out.loc[prior_claim.index, "valid_to_release"] = release_id
        new_row = {column: pd.NA for column in out.columns}
        new_row.update(
            {
                "candidacy_id": candidacy_id,
                "person_id": target_person_id,
                "link_status": decision,
                "method": method,
                "evidence": evidence,
                "reviewer": reviewer,
                "valid_from_release": release_id,
                "valid_to_release": pd.NA,
            }
        )
        new_rows.append(new_row)

    if new_rows:
        out = pd.concat([out, pd.DataFrame(new_rows)], ignore_index=True, sort=False)
    out = out.sort_values(
        ["candidacy_id", "valid_from_release", "link_status", "person_id"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    for column in ("person_id", "valid_to_release"):
        out[column] = out[column].astype("string")
    validate_identity_tables(people, out)
    return out
