"""Acquire, assemble, validate, and publish the expanded v2 release."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from . import download as city_download
from .build_manifest import build_manifest, sha256_file, write_manifest
from .candidacy_ledger import (
    assign_candidacy_ids,
    read_candidacy_ledger,
    write_candidacy_ledger,
)
from .district_geometry import enrich_district_geometries
from .endorsement_curations import (
    ENDORSEMENT_ASSERTIONS_FILENAME,
    ENDORSEMENT_COVERAGE_FILENAME,
    ENDORSER_PANEL_FILENAME,
    build_default_endorsement_inputs,
)
from .endorsements import assemble_endorsement_tables
from .federal import load_federal_results
from .identity import validate_identity_tables
from .identity_curations import DEFAULT_IDENTITY_ASSERTIONS
from .identity_dispositions import read_identity_review_decisions
from .mayoral_career import (
    build_mayoral_career_identity_assertions,
    exclude_superseded_identity_decisions,
    load_mayoral_career_backfills,
)
from .municipal import load_council_results
from .ontario import download_ontario_sources, load_ontario_results
from .pending_candidates import load_pending_council_candidates
from .release import assemble_bootstrapped_release, validate_tables, write_release
from .schema import normalize_adapter_frame
from .trustee_2026 import TRUSTEE_CROSSWALK_FILENAME
from .trustee_career import (
    build_trustee_career_identity_assertions,
    reconcile_trustee_identity_decisions,
)
from .trustees import load_trustee_results, trustee_event_manifest

RAW = Path("data/raw")
INTERIM = Path("data/interim")
OUT = Path("data/out")
REFERENCE = Path("data/reference")
RELEASE_ID = "2026-08-21"
CANDIDACY_LEDGER_FILENAME = "candidacy_identity_ledger.csv"
IDENTITY_REVIEW_DISPOSITIONS_FILENAME = "identity_review_dispositions.csv"
_PRIOR_REGISTRY_ARTIFACTS = {
    "people.csv",
    "candidacy_person_links.csv",
    "election_results.csv",
}


class PriorRegistryCandidacyMismatch(ValueError):
    """Prior public Candidacy IDs predate or contradict the active ledger."""


def _source_files(raw: Path, reference: Path = REFERENCE) -> list[Path]:
    patterns = [
        "results/*-results.zip",
        "byelection/*",
        "voter_stats/*",
        "byelection_voter_stats/*",
        "trustee_byelections/*",
        "federal/**/*",
        "ontario/**/*",
        "council/**/*",
        "subdivisions/*",
        "ckan/*",
    ]
    source_paths = {
        path
        for pattern in patterns
        for path in raw.glob(pattern)
        if path.is_file() and not path.name.endswith(".part")
    }
    source_paths.update(reference.glob("roster_agent_*.txt"))
    ledger_path = reference / CANDIDACY_LEDGER_FILENAME
    if ledger_path.is_file():
        source_paths.add(ledger_path)
    dispositions_path = reference / IDENTITY_REVIEW_DISPOSITIONS_FILENAME
    if dispositions_path.is_file():
        source_paths.add(dispositions_path)
    for filename in (
        ENDORSER_PANEL_FILENAME,
        ENDORSEMENT_ASSERTIONS_FILENAME,
        ENDORSEMENT_COVERAGE_FILENAME,
        "mayoral_career_cohort_2026.csv",
        "mayoral_career_reviews.csv",
        "mayoral_career_decisions.csv",
        "mayoral_career_backfill.csv",
        "mayoral_career_occurrence_mapping.csv",
        "trustee_career_cohort_2026.csv",
        "trustee_career_reviews.csv",
        "trustee_career_decisions.csv",
        "trustee_career_sol_reviews.csv",
        "trustee_contest_continuity_2026.csv",
        "trustee_incumbents_2026.csv",
        TRUSTEE_CROSSWALK_FILENAME,
    ):
        endorsement_path = reference / filename
        if endorsement_path.is_file():
            source_paths.add(endorsement_path)
            if filename == ENDORSEMENT_COVERAGE_FILENAME:
                try:
                    coverage_sources = pd.read_csv(
                        endorsement_path,
                        dtype="string",
                        usecols=["verification_report_path", "search_certificate_path"],
                    )
                except ValueError, pd.errors.EmptyDataError:
                    coverage_sources = pd.DataFrame()
                for column in coverage_sources.columns:
                    for value in coverage_sources[column].dropna().unique():
                        report_path = Path(str(value))
                        if report_path.is_file():
                            source_paths.add(report_path)
    trustee_reviews_path = reference / "trustee_career_reviews.csv"
    if trustee_reviews_path.is_file():
        trustee_reviews = pd.read_csv(
            trustee_reviews_path,
            dtype="string",
            usecols=["luna_report_path", "terra_report_path"],
        )
        for column in trustee_reviews.columns:
            for value in trustee_reviews[column].dropna().unique():
                report_path = Path(str(value))
                if report_path.is_file():
                    source_paths.add(report_path)
    trustee_sol_reviews_path = reference / "trustee_career_sol_reviews.csv"
    if trustee_sol_reviews_path.is_file():
        trustee_sol_reviews = pd.read_csv(
            trustee_sol_reviews_path,
            dtype="string",
            usecols=["sol_report_path", "sol_batch_path"],
        )
        for column in trustee_sol_reviews.columns:
            for value in trustee_sol_reviews[column].dropna().unique():
                review_path = Path(str(value))
                if review_path.is_file():
                    source_paths.add(review_path)
    return sorted(
        (path for path in source_paths if path.is_file()),
        key=lambda path: path.as_posix(),
    )


def _load_existing_identity_registry(
    output_dir: Path,
    candidacy_ledger: pd.DataFrame,
    *,
    verify_artifact_hashes: bool = False,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Load the prior public registry as an operational release input."""

    people_path = output_dir / "people.csv"
    links_path = output_dir / "candidacy_person_links.csv"
    results_path = output_dir / "election_results.csv"
    if verify_artifact_hashes:
        _verify_prior_registry_artifact_hashes(output_dir)
    if not people_path.exists() and not links_path.exists():
        return None, None
    if not people_path.exists() or not links_path.exists():
        raise ValueError(
            "a prior identity registry requires both people.csv and candidacy_person_links.csv"
        )
    if not results_path.exists():
        raise ValueError("a prior identity registry also requires election_results.csv")
    people = pd.read_csv(people_path, dtype="string")
    links = pd.read_csv(links_path, dtype="string")
    prior_results = pd.read_csv(results_path, usecols=["candidacy_id"], dtype="string")
    active_ledger_ids = set(
        candidacy_ledger.loc[candidacy_ledger["valid_to_release"].isna(), "candidacy_id"].astype(
            str
        )
    )
    prior_result_ids = set(prior_results["candidacy_id"].astype(str))
    incompatible = sorted(prior_result_ids - active_ledger_ids)
    if incompatible:
        raise PriorRegistryCandidacyMismatch(
            "the prior release is incompatible with the active Candidacy ledger; "
            f"unexpected Candidacy ID {incompatible[0]!r}. Recover or rebuild the migration "
            "release before reusing its Person registry."
        )
    broken_links = sorted(set(links["candidacy_id"].astype(str)) - prior_result_ids)
    if broken_links:
        raise ValueError(
            "the prior Candidacy-Person registry does not match its election_results: "
            f"{broken_links[0]!r}"
        )
    active_link_ids = set(links.loc[links["valid_to_release"].isna(), "candidacy_id"].astype(str))
    missing_link_state = sorted(prior_result_ids - active_link_ids)
    if missing_link_state:
        raise ValueError(
            "the prior release lacks active identity-registry state for Candidacy "
            f"{missing_link_state[0]!r}"
        )
    validate_identity_tables(people, links)
    return people, links


def _verify_prior_registry_artifact_hashes(output_dir: Path) -> None:
    """Fail closed when persisted identity inputs differ from their prior manifest."""

    manifest_path = output_dir / "build_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("cannot verify prior identity-registry artifact checksums") from exc

    artifacts = manifest.get("artifacts", [])
    for artifact_name in sorted(_PRIOR_REGISTRY_ARTIFACTS):
        records = [
            record
            for record in artifacts
            if isinstance(record, dict)
            and Path(str(record.get("local_path", ""))).name == artifact_name
        ]
        if len(records) != 1 or not str(records[0].get("sha256", "")).strip():
            raise ValueError(
                f"prior manifest does not uniquely checksum identity artifact {artifact_name!r}"
            )
        artifact_path = output_dir / artifact_name
        if not artifact_path.exists() or sha256_file(artifact_path) != records[0]["sha256"]:
            raise ValueError(f"prior identity-registry checksum mismatch for {artifact_name!r}")


def _prior_manifest_tracks_ledger(output_dir: Path, ledger_path: Path) -> bool:
    """Return whether prior output was built after the ledger migration."""

    manifest_path = output_dir / "build_manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError, TypeError:
        return False
    return any(
        Path(str(record.get("local_path", ""))).name == ledger_path.name
        for record in manifest.get("sources", [])
        if isinstance(record, dict)
    )


def _verify_prior_ledger_checksum(output_dir: Path, ledger_path: Path) -> None:
    """Fail closed when the canonical ledger differs from its prior manifest."""

    manifest_path = output_dir / "build_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("cannot verify prior Candidacy ledger checksum") from exc

    records = [
        record
        for record in manifest.get("sources", [])
        if isinstance(record, dict)
        and Path(str(record.get("local_path", ""))).name == ledger_path.name
    ]
    if len(records) != 1 or not str(records[0].get("sha256", "")).strip():
        raise ValueError("prior manifest does not uniquely record a Candidacy ledger checksum")
    if not ledger_path.exists() or sha256_file(ledger_path) != records[0]["sha256"]:
        raise ValueError(
            "prior Candidacy ledger checksum mismatch; recover the ledger and prior release "
            "before rebuilding"
        )


def _load_source_adapters(
    *, raw: Path, interim: Path, reference: Path, download: bool
) -> tuple[list[pd.DataFrame], pd.DataFrame]:
    if download:
        city_download.download_all(root=raw)

    council = load_council_results(raw=raw, interim=interim)
    trustees = load_trustee_results(
        results_root=interim / "results",
        by_election_root=raw / "trustee_byelections",
        download=download,
    )
    federal = load_federal_results(raw / "federal", download=download)
    if download:
        download_ontario_sources(raw / "ontario")
    ontario = load_ontario_results(raw / "ontario")
    pending_council = load_pending_council_candidates(
        raw / "council" / "candidates_2026",
        download=download,
        trustee_crosswalk_path=reference / TRUSTEE_CROSSWALK_FILENAME,
    )
    mayoral_career = load_mayoral_career_backfills(reference)
    contest_manifest = trustee_event_manifest(
        results_root=interim / "results",
        by_election_root=raw / "trustee_byelections",
    )
    return [council, trustees, federal, ontario, pending_council, mayoral_career], contest_manifest


def run_all(
    *,
    skip_download: bool = False,
    raw: Path = RAW,
    interim: Path = INTERIM,
    out: Path = OUT,
    reference: Path = REFERENCE,
) -> list[str]:
    """Run the complete cutoff-bounded build and return any QC issues."""

    ledger_path = reference / CANDIDACY_LEDGER_FILENAME
    ledger_existed = ledger_path.exists()
    manifest_tracks_ledger = _prior_manifest_tracks_ledger(out, ledger_path)
    if manifest_tracks_ledger:
        if not ledger_existed:
            raise ValueError(
                "persisted Candidacy ledger is missing from a ledger-backed release; "
                "recover it before rebuilding"
            )
        _verify_prior_ledger_checksum(out, ledger_path)
    candidacy_ledger = read_candidacy_ledger(ledger_path)
    adapters, contest_manifest = _load_source_adapters(
        raw=raw, interim=interim, reference=reference, download=not skip_download
    )
    resolved = assign_candidacy_ids(
        adapters,
        ledger=candidacy_ledger,
        release_id=RELEASE_ID,
    )
    if not ledger_existed:
        existing_people, existing_links = None, None
    else:
        try:
            existing_people, existing_links = _load_existing_identity_registry(
                out,
                resolved.ledger,
                verify_artifact_hashes=manifest_tracks_ledger,
            )
        except PriorRegistryCandidacyMismatch:
            if manifest_tracks_ledger:
                raise
            # Draft v2 output predates the occurrence ledger and contains
            # name-derived Candidacy IDs. It must never seed the first persistent
            # registry.
            existing_people, existing_links = None, None
        if existing_people is not None and not manifest_tracks_ledger:
            raise RuntimeError(
                "the prior registry is ledger-compatible but its manifest does not track "
                "the ledger; recover or explicitly rebuild after an interrupted publication"
            )
    normalized_frames = [
        normalize_adapter_frame(frame, require_persistent_candidacy_id=True)
        for frame in resolved.adapter_frames
        if not frame.empty
    ]
    normalized_results = (
        pd.concat(normalized_frames, ignore_index=True, sort=False)
        if normalized_frames
        else pd.DataFrame()
    )
    trustee_identity_assertions = build_trustee_career_identity_assertions(
        reference, normalized_results
    )
    identity_review_decisions = exclude_superseded_identity_decisions(
        read_identity_review_decisions(reference / IDENTITY_REVIEW_DISPOSITIONS_FILENAME),
        reference,
    )
    identity_review_decisions = reconcile_trustee_identity_decisions(
        identity_review_decisions,
        reference,
        trustee_identity_assertions,
    )
    built = assemble_bootstrapped_release(
        resolved.adapter_frames,
        release_id=RELEASE_ID,
        contest_manifest=contest_manifest,
        municipal_reference=reference,
        municipal_raw=raw / "council",
        candidacy_ledger=resolved.ledger,
        existing_people=existing_people,
        existing_candidacy_person_links=existing_links,
        identity_assertions=(
            DEFAULT_IDENTITY_ASSERTIONS
            + build_mayoral_career_identity_assertions(reference, resolved.adapter_frames)
            + trustee_identity_assertions
        ),
        identity_review_decisions=identity_review_decisions,
    )
    release = replace(
        built.tables,
        electoral_districts=enrich_district_geometries(built.tables.electoral_districts),
    )
    endorsement_inputs = build_default_endorsement_inputs(
        release.election_results,
        release.contests,
        release.people,
        reference_dir=reference,
    )
    endorsement_tables = assemble_endorsement_tables(
        candidacies=release.election_results,
        contests=release.contests,
        people=release.people,
        endorsers=endorsement_inputs.endorsers,
        assertions=endorsement_inputs.assertions,
        coverage=endorsement_inputs.coverage,
    )
    release = replace(
        release,
        endorsers=endorsement_tables.endorsers,
        endorsement_assertions=endorsement_tables.endorsement_assertions,
        endorsements=endorsement_tables.endorsements,
        endorsement_coverage=endorsement_tables.endorsement_coverage,
    )
    issues = validate_tables(release)
    if issues:
        print(f"QC: {len(issues)} issue(s)")
        for issue in issues:
            print(f"  - {issue}")
        return issues

    write_candidacy_ledger(built.candidacy_ledger, ledger_path)
    artifacts = write_release(release, out)
    row_counts = {
        f"{table_name}.{extension}": len(getattr(release, table_name))
        for table_name in release.__dataclass_fields__
        for extension in ("csv", "parquet")
    }
    manifest = build_manifest(
        sources=_source_files(raw, reference),
        artifacts=artifacts,
        row_counts=row_counts,
        generated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    write_manifest(manifest, out / "build_manifest.json")

    results = release.election_results
    print(
        f"wrote {len(results):,} Candidacies, {len(release.contests):,} Contests, "
        f"and {len(release.election_events):,} Election events to {out}"
    )
    print(results.groupby(["office_type", "election_type"]).size().to_string())
    print(
        f"identity: {len(release.people):,} People, "
        f"{results['person_id'].isna().sum():,} unresolved Candidacies, "
        f"{len(built.identity_review.review_flags):,} review flags"
    )
    print(
        f"endorsements: {len(release.endorsements):,} confirmed facts from "
        f"{len(release.endorsement_assertions):,} reviewed assertions"
    )
    print("QC: OK")
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="reuse the existing local official-source cache",
    )
    args = parser.parse_args()
    issues = run_all(skip_download=args.skip_download)
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
