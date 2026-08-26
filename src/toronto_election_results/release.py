"""Assemble source adapters into the expanded relational release."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field, fields
from pathlib import Path

import pandas as pd

from .candidacy_ledger import CandidacyLedgerAssignment, assign_candidacy_ids
from .endorsements import EndorsementTables, validate_endorsement_tables
from .federal_rosters import build_federal_roster_evidence
from .identity import attach_confirmed_people, derive_incumbency
from .identity_curations import (
    CuratedIdentityAssertion,
    apply_curated_identity_assertions,
    canonicalize_person_evidence,
)
from .identity_dispositions import apply_identity_review_decisions
from .identity_review import (
    IdentityReview,
    bootstrap_identity_review,
    extend_identity_review,
)
from .municipal_rosters import build_municipal_roster_evidence
from .release_validation import validate_release
from .reported_incumbency import ReportedIncumbency, build_reported_incumbency
from .schema import (
    attach_parties,
    build_contests,
    build_districts,
    build_events,
    build_parties,
    derive_result_metrics,
    normalize_adapter_frame,
)

ELECTION_RESULT_COLUMNS = [
    "candidacy_id",
    "person_id",
    "event_id",
    "contest_id",
    "election_date",
    "election_year",
    "election_type",
    "election_authority",
    "represented_body",
    "office_type",
    "district_id",
    "official_district_id",
    "district_name",
    "boundary_regime",
    "candidate_name",
    "candidate_name_raw",
    "party_id",
    "party_name",
    "party_name_raw",
    "party_jurisdiction",
    "affiliation_status",
    "votes",
    "total_contest_votes",
    "vote_share",
    "vote_rank",
    "n_candidates",
    "eligible_electors",
    "ballots_cast",
    "turnout",
    "turnout_scope",
    "elected",
    "acclaimed",
    "outcome_method",
    "result_status",
    "coverage_status",
    "incumbent",
    "incumbent_office_tenure_id",
    "incumbent_reported",
    "source_authority",
    "source_resource",
    "source_detail",
    "source_candidacy_id",
]


@dataclass(frozen=True)
class ReleaseTables:
    """The published result, identity, geography, and endorsement artifacts."""

    election_results: pd.DataFrame
    election_events: pd.DataFrame
    contests: pd.DataFrame
    people: pd.DataFrame
    candidacy_person_links: pd.DataFrame
    parties: pd.DataFrame
    office_tenures: pd.DataFrame
    electoral_districts: pd.DataFrame
    endorsers: pd.DataFrame = field(default_factory=pd.DataFrame)
    endorsement_assertions: pd.DataFrame = field(default_factory=pd.DataFrame)
    endorsements: pd.DataFrame = field(default_factory=pd.DataFrame)
    endorsement_coverage: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass(frozen=True)
class BootstrappedRelease:
    """Public tables plus internal review and roster evidence for the build."""

    tables: ReleaseTables
    identity_review: IdentityReview
    reported_incumbency: ReportedIncumbency
    candidacy_ledger: pd.DataFrame


def _empty_people() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "person_id",
            "preferred_name",
            "identity_status",
            "redirect_to_person_id",
            "created_release",
        ]
    )


def _empty_links() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "candidacy_id",
            "person_id",
            "link_status",
            "method",
            "evidence",
            "reviewer",
            "valid_from_release",
            "valid_to_release",
        ]
    )


def _empty_tenures() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
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
    )


def _normalize_tenure_dates(tenures: pd.DataFrame) -> pd.DataFrame:
    """Keep date-only tenure columns Arrow-safe across source adapters."""

    out = tenures.copy()
    for column in ("started_on", "ended_on"):
        if column not in out:
            continue
        parsed = pd.to_datetime(out[column], errors="coerce")
        invalid = out[column].notna() & parsed.isna()
        if invalid.any():
            raise ValueError(
                f"office_tenures.{column} contains an invalid date: "
                f"{out.loc[invalid, column].iloc[0]!r}"
            )
        out[column] = parsed.dt.date
    return out


def _manifest_rows(manifest: pd.DataFrame | None) -> pd.DataFrame:
    if manifest is None or manifest.empty:
        return pd.DataFrame()
    synthetic = manifest.copy()
    synthetic["candidate_name_raw"] = "__contest_manifest_only__"
    synthetic["votes"] = pd.NA
    synthetic["elected"] = pd.NA
    synthetic["party_name_raw"] = pd.NA
    synthetic["affiliation_status"] = "not_reported"
    for column in ["incumbent_reported", "eligible_electors", "ballots_cast", "turnout_scope"]:
        if column not in synthetic:
            synthetic[column] = pd.NA
    return normalize_adapter_frame(synthetic)


def _placeholder_contests(normalized_manifest: pd.DataFrame) -> pd.DataFrame:
    if normalized_manifest.empty:
        return pd.DataFrame()
    columns = [
        "contest_id",
        "event_id",
        "represented_body",
        "office_type",
        "district_id",
        "official_district_id",
        "district_name",
        "boundary_regime",
        "outcome_method",
        "result_status",
        "coverage_status",
        "eligible_electors",
        "ballots_cast",
        "turnout_scope",
        "source_authority",
        "source_resource",
        "source_detail",
    ]
    contests = normalized_manifest[columns].drop_duplicates("contest_id").copy()
    contests["acclaimed"] = contests["outcome_method"].eq("acclamation").astype("boolean")
    contests["n_candidates"] = pd.Series(pd.NA, index=contests.index, dtype="Int64")
    contests["total_contest_votes"] = pd.Series(pd.NA, index=contests.index, dtype="Int64")
    contests["seats_available"] = 1
    contests["turnout"] = pd.Series(pd.NA, index=contests.index, dtype="Float64")
    usable = (
        contests["eligible_electors"].notna()
        & contests["eligible_electors"].gt(0)
        & contests["ballots_cast"].notna()
    )
    contests.loc[usable, "turnout"] = contests.loc[usable, "ballots_cast"].astype(
        "Float64"
    ) / contests.loc[usable, "eligible_electors"].astype("Float64")
    return contests


def assemble_release(
    adapter_frames: list[pd.DataFrame],
    *,
    contest_manifest: pd.DataFrame | None = None,
    people: pd.DataFrame | None = None,
    candidacy_person_links: pd.DataFrame | None = None,
    office_tenures: pd.DataFrame | None = None,
    incumbency_rosters: pd.DataFrame | None = None,
) -> ReleaseTables:
    """Normalize adapters once and build every public relational table."""

    if not adapter_frames:
        raise ValueError("at least one source adapter frame is required")
    normalized = [
        normalize_adapter_frame(frame, require_persistent_candidacy_id=True)
        for frame in adapter_frames
        if not frame.empty
    ]
    if not normalized:
        raise ValueError("source adapters returned no Candidacy rows")
    candidacies = pd.concat(normalized, ignore_index=True)
    candidacies = derive_result_metrics(attach_parties(candidacies))

    registry_people = _empty_people() if people is None else people.copy()
    registry_links = (
        _empty_links() if candidacy_person_links is None else candidacy_person_links.copy()
    )
    registry_links = registry_links.astype("string")
    if registry_people.empty and registry_links.empty:
        candidacies["person_id"] = pd.Series(pd.NA, index=candidacies.index, dtype="string")
        candidacies["person_link_method"] = pd.Series(
            pd.NA, index=candidacies.index, dtype="string"
        )
        candidacies["person_link_evidence"] = pd.Series(
            pd.NA, index=candidacies.index, dtype="string"
        )
    else:
        candidacies = attach_confirmed_people(candidacies, registry_people, registry_links)

    if incumbency_rosters is None:
        candidacies["incumbent"] = pd.Series(pd.NA, index=candidacies.index, dtype="boolean")
        candidacies["incumbent_office_tenure_id"] = pd.Series(
            pd.NA, index=candidacies.index, dtype="string"
        )
    else:
        candidacies = derive_incumbency(candidacies, incumbency_rosters)

    normalized_manifest = _manifest_rows(contest_manifest)
    all_identity_rows = (
        candidacies
        if normalized_manifest.empty
        else pd.concat([candidacies, normalized_manifest], ignore_index=True, sort=False)
    )
    events = build_events(all_identity_rows)
    districts = build_districts(all_identity_rows)
    contests = build_contests(candidacies)
    placeholders = _placeholder_contests(normalized_manifest)
    if not placeholders.empty:
        placeholders = placeholders.loc[~placeholders["contest_id"].isin(contests["contest_id"])]
        contests = pd.concat([contests, placeholders], ignore_index=True, sort=False)
        contests = contests.sort_values(
            ["event_id", "office_type", "district_id"], kind="stable"
        ).reset_index(drop=True)

    parties = build_parties(candidacies)
    tenures = _normalize_tenure_dates(
        _empty_tenures() if office_tenures is None else office_tenures
    )
    candidacies = candidacies.merge(
        parties[["party_id", "canonical_name"]].rename(columns={"canonical_name": "party_name"}),
        on="party_id",
        how="left",
        validate="many_to_one",
    )
    candidacies = candidacies.drop(
        columns=["canonical_party_name", "person_link_method", "person_link_evidence"],
        errors="ignore",
    )
    candidacies = candidacies.sort_values(
        ["election_date", "election_authority", "office_type", "district_id", "vote_rank"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    candidacies = candidacies[ELECTION_RESULT_COLUMNS]

    registry_people = registry_people.sort_values("person_id", kind="stable").reset_index(drop=True)
    registry_links = registry_links.sort_values(
        ["candidacy_id", "valid_from_release", "link_status", "person_id"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    tenures = tenures.sort_values("office_tenure_id", kind="stable").reset_index(drop=True)

    return ReleaseTables(
        election_results=candidacies,
        election_events=events,
        contests=contests,
        people=registry_people,
        candidacy_person_links=registry_links,
        parties=parties,
        office_tenures=tenures,
        electoral_districts=districts,
    )


def assemble_bootstrapped_release(
    adapter_frames: list[pd.DataFrame],
    *,
    release_id: str,
    contest_manifest: pd.DataFrame | None = None,
    municipal_composition: pd.DataFrame | None = None,
    municipal_reference: Path | None = None,
    municipal_raw: Path | None = None,
    candidacy_ledger: pd.DataFrame | None = None,
    existing_people: pd.DataFrame | None = None,
    existing_candidacy_person_links: pd.DataFrame | None = None,
    identity_assertions: tuple[CuratedIdentityAssertion, ...] = (),
    identity_review_decisions: pd.DataFrame | None = None,
) -> BootstrappedRelease:
    """Bootstrap a conservative v2 identity registry, then derive incumbency.

    Persist the returned Person/link tables between releases; this bootstrap is an
    initial-release tool, not a replacement for applying audited merge/split history.
    """

    assignment: CandidacyLedgerAssignment = assign_candidacy_ids(
        adapter_frames,
        ledger=candidacy_ledger,
        release_id=release_id,
    )
    resolved_frames = assignment.adapter_frames
    initial = assemble_release(resolved_frames, contest_manifest=contest_manifest)
    has_people = existing_people is not None
    has_links = existing_candidacy_person_links is not None
    if has_people != has_links:
        raise ValueError("existing People and Candidacy-Person links must be supplied together")
    if has_people and has_links:
        bootstrap = extend_identity_review(
            initial.election_results,
            existing_people,
            existing_candidacy_person_links,
            release_id=release_id,
        )
    else:
        bootstrap = bootstrap_identity_review(initial.election_results, release_id=release_id)
    municipal_kwargs: dict[str, object] = {"composition": municipal_composition}
    if municipal_reference is not None:
        municipal_kwargs["reference"] = municipal_reference
    if municipal_raw is not None:
        municipal_kwargs["raw"] = municipal_raw
    municipal = build_municipal_roster_evidence(
        initial.election_results,
        bootstrap.people,
        bootstrap.candidacy_person_links,
        release_id=release_id,
        **municipal_kwargs,
    )
    review_flags = pd.concat(
        [bootstrap.review_flags, municipal.review_flags], ignore_index=True, sort=False
    )
    if not review_flags.empty:
        review_flags = review_flags.drop_duplicates("review_flag_id").sort_values(
            ["severity", "flag_type", "candidacy_id"],
            kind="stable",
            na_position="last",
        )
    curated_people = municipal.people
    curated_links = municipal.candidacy_person_links
    if identity_assertions:
        curation = apply_curated_identity_assertions(
            initial.election_results,
            curated_people,
            curated_links,
            release_id,
            assertions=identity_assertions,
        )
        curated_people = curation.people
        curated_links = curation.candidacy_person_links
    if identity_review_decisions is not None and not identity_review_decisions.empty:
        curated_links = apply_identity_review_decisions(
            curated_people,
            curated_links,
            identity_review_decisions,
            release_id=release_id,
        )
    municipal_evidence = canonicalize_person_evidence(
        curated_people,
        municipal.office_tenures,
        municipal.rosters,
    )
    review = IdentityReview(
        curated_people,
        curated_links,
        review_flags.reset_index(drop=True),
    )
    linked = attach_confirmed_people(
        initial.election_results,
        review.people,
        review.candidacy_person_links,
    )
    reported = build_reported_incumbency(
        linked.loc[linked["represented_body"].eq("ontario_legislative_assembly")].copy()
    )
    federal = build_federal_roster_evidence(linked)
    office_tenures = pd.concat(
        [
            municipal_evidence.office_tenures,
            federal.office_tenures,
            reported.office_tenures,
        ],
        ignore_index=True,
        sort=False,
    )
    incumbency_rosters = pd.concat(
        [municipal_evidence.rosters, federal.rosters, reported.rosters],
        ignore_index=True,
        sort=False,
    )
    tables = assemble_release(
        resolved_frames,
        contest_manifest=contest_manifest,
        people=review.people,
        candidacy_person_links=review.candidacy_person_links,
        office_tenures=office_tenures,
        incumbency_rosters=incumbency_rosters,
    )
    return BootstrappedRelease(tables, review, reported, assignment.ledger)


def validate_tables(release: ReleaseTables) -> list[str]:
    """Run the release-level integrity and semantic checks."""

    issues = validate_release(
        release.election_results,
        release.election_events,
        release.contests,
        release.parties,
        release.electoral_districts,
        release.people,
        release.office_tenures,
        release.candidacy_person_links,
    )
    endorsement_frames = [
        release.endorsers,
        release.endorsement_assertions,
        release.endorsements,
        release.endorsement_coverage,
    ]
    if any(not frame.empty for frame in endorsement_frames):
        try:
            validate_endorsement_tables(
                EndorsementTables(
                    endorsers=release.endorsers,
                    endorsement_assertions=release.endorsement_assertions,
                    endorsements=release.endorsements,
                    endorsement_coverage=release.endorsement_coverage,
                ),
                candidacies=release.election_results,
                contests=release.contests,
                people=release.people,
            )
        except ValueError as exc:
            issues.append(str(exc))
    return issues


def write_release(release: ReleaseTables, output_dir: str | Path) -> list[Path]:
    """Validate, stage, then atomically promote every CSV and Parquet artifact.

    Serialization completes in a temporary sibling directory before any published
    file changes. Each final-path replacement is atomic; if promotion itself fails,
    files already replaced during this call are rolled back to the previous release.
    """

    issues = validate_tables(release)
    if issues:
        formatted = "\n".join(f"- {issue}" for issue in issues)
        raise ValueError(f"release validation failed:\n{formatted}")

    destination = Path(output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    artifact_names = [
        f"{field.name}.{extension}" for field in fields(release) for extension in ("csv", "parquet")
    ]

    with tempfile.TemporaryDirectory(
        prefix=f".{destination.name}.stage-", dir=destination.parent
    ) as staging_name:
        staging = Path(staging_name)
        payload = staging / "payload"
        backups = staging / "backups"
        payload.mkdir()
        backups.mkdir()

        # A serializer failure happens before destination is created or touched.
        for field in fields(release):
            frame = getattr(release, field.name)
            frame.to_csv(payload / f"{field.name}.csv", index=False)
            frame.to_parquet(payload / f"{field.name}.parquet", index=False)

        destination.mkdir(parents=True, exist_ok=True)
        promoted: list[tuple[Path, Path]] = []
        previous: dict[Path, Path] = {}
        try:
            for artifact_name in artifact_names:
                staged_path = payload / artifact_name
                final_path = destination / artifact_name
                if final_path.exists():
                    backup_path = backups / artifact_name
                    os.replace(final_path, backup_path)
                    previous[final_path] = backup_path
                os.replace(staged_path, final_path)
                promoted.append((final_path, staged_path))
        except OSError as exc:
            rollback_errors: list[OSError] = []
            for final_path, staged_path in reversed(promoted):
                try:
                    if final_path.exists():
                        os.replace(final_path, staged_path)
                except OSError as rollback_exc:
                    rollback_errors.append(rollback_exc)
            for final_path, backup_path in previous.items():
                try:
                    if backup_path.exists():
                        os.replace(backup_path, final_path)
                except OSError as rollback_exc:
                    rollback_errors.append(rollback_exc)
            detail = ""
            if rollback_errors:
                detail = f"; rollback also failed: {rollback_errors[0]}"
            raise RuntimeError(f"release promotion failed{detail}") from exc

    return [destination / artifact_name for artifact_name in artifact_names]
