"""Build and optionally publish immutable GitHub Release assets."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .build_manifest import sha256_file
from .frontend_feeds import (
    MAYORAL_CANDIDATES_SCHEMA_VERSION,
    TRUSTEE_RACES_SCHEMA_VERSION,
    write_mayoral_candidates_feed,
    write_person_aliases_feed,
    write_trustee_races_feed,
)
from .person_alias_curations import PERSON_ALIAS_CURATIONS_FILENAME
from .trustee_2026 import TRUSTEE_CROSSWALK_FILENAME

RELEASE_MANIFEST_SCHEMA_VERSION = 1
REPOSITORY = "alexwolson/toronto-election-results"


def _git(*args: str, cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def build_results_release_bundle(
    source_dir: str | Path,
    destination: str | Path,
    *,
    source_commit: str,
    dirty: bool,
    generated_at: str | None = None,
    reference_dir: str | Path | None = None,
) -> Path:
    """Atomically package canonical tables and factual frontend feeds."""

    source = Path(source_dir)
    target = Path(destination)
    results_path = source / "election_results.csv"
    districts_path = source / "electoral_districts.csv"
    people_path = source / "people.csv"
    build_manifest_path = source / "build_manifest.json"
    reference = Path(reference_dir) if reference_dir is not None else source.parent / "reference"
    career_reviews_path = reference / "mayoral_career_reviews.csv"
    career_mappings_path = reference / "mayoral_career_occurrence_mapping.csv"
    trustee_cohort_path = reference / "trustee_career_cohort_2026.csv"
    trustee_reviews_path = reference / "trustee_career_reviews.csv"
    trustee_decisions_path = reference / "trustee_career_decisions.csv"
    trustee_crosswalk_path = reference / TRUSTEE_CROSSWALK_FILENAME
    trustee_continuity_path = reference / "trustee_contest_continuity_2026.csv"
    person_alias_curations_path = reference / PERSON_ALIAS_CURATIONS_FILENAME
    for required in (
        results_path,
        districts_path,
        people_path,
        build_manifest_path,
        career_reviews_path,
        career_mappings_path,
        trustee_cohort_path,
        trustee_reviews_path,
        trustee_decisions_path,
        trustee_crosswalk_path,
        trustee_continuity_path,
        person_alias_curations_path,
    ):
        if not required.is_file():
            raise FileNotFoundError(f"missing results release input: {required}")

    assets = sorted(
        [*source.glob("*.csv"), *source.glob("*.parquet"), build_manifest_path],
        key=lambda path: path.name,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{target.name}.stage-", dir=target.parent) as tmp:
        staging = Path(tmp)
        for asset in assets:
            shutil.copy2(asset, staging / asset.name)
        reviews = pd.read_csv(career_reviews_path, dtype="string", keep_default_na=False)
        public_coverage_columns = [
            "cohort_id",
            "subject_candidacy_id",
            "certified_name",
            "resulting_person_id",
            "review_date",
            "source_release",
            "review_status",
            "public_coverage_note",
            "confirmed_count",
            "held_count",
            "split_count",
            "rejected_count",
        ]
        reviews[public_coverage_columns].to_csv(
            staging / "mayoral_career_coverage.csv", index=False
        )
        shutil.copy2(career_mappings_path, staging / career_mappings_path.name)
        write_mayoral_candidates_feed(
            results_path,
            districts_path,
            career_reviews_path,
            staging / "mayoral_candidates.json",
        )
        write_trustee_races_feed(
            results_path,
            districts_path,
            trustee_crosswalk_path,
            trustee_continuity_path,
            trustee_cohort_path,
            trustee_reviews_path,
            trustee_decisions_path,
            staging / "trustee_races.json",
        )
        write_person_aliases_feed(
            results_path,
            people_path,
            staging / "person_aliases.json",
            curated_aliases_path=person_alias_curations_path,
        )

        packaged = sorted(
            (path for path in staging.iterdir() if path.name != "release_manifest.json"),
            key=lambda path: path.name,
        )
        manifest = {
            "schema_version": RELEASE_MANIFEST_SCHEMA_VERSION,
            "repository": REPOSITORY,
            "generated_at": generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_commit": source_commit,
            "source_dirty": dirty,
            "assets": [
                {
                    "filename": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in packaged
            ],
            "feeds": {
                "mayoral_candidates": "mayoral_candidates.json",
                "trustee_races": "trustee_races.json",
                "person_aliases": "person_aliases.json",
            },
            "feed_versions": {
                "mayoral_candidates": MAYORAL_CANDIDATES_SCHEMA_VERSION,
                "trustee_races": TRUSTEE_RACES_SCHEMA_VERSION,
                "person_aliases": 1,
            },
        }
        (staging / "release_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        backup = target.with_name(f".{target.name}.backup")
        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            target.replace(backup)
        try:
            shutil.copytree(staging, target)
        except Exception:
            if backup.exists() and not target.exists():
                backup.replace(target)
            raise
        finally:
            if backup.exists():
                shutil.rmtree(backup)
    return target


def publish_results_release(tag: str, bundle: str | Path, *, root: str | Path) -> None:
    """Publish a clean bundle as a stable, immutable GitHub Release."""

    project = Path(root)
    if _git("status", "--porcelain", cwd=project):
        raise RuntimeError("refusing to publish a results release from a dirty working tree")
    bundle_path = Path(bundle)
    manifest = json.loads((bundle_path / "release_manifest.json").read_text(encoding="utf-8"))
    head = _git("rev-parse", "HEAD", cwd=project)
    if manifest.get("source_dirty") or manifest.get("source_commit") != head:
        raise RuntimeError("release bundle was not built from the current clean commit")
    files = sorted(str(path) for path in bundle_path.iterdir() if path.is_file())
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            REPOSITORY,
            "--title",
            f"Toronto election results {tag}",
            "--generate-notes",
            *files,
        ],
        cwd=project,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="build and validate release assets")
    build.add_argument("--source", type=Path, default=Path("data/out"))
    build.add_argument("--output", type=Path, default=Path("dist"))
    publish = subparsers.add_parser("publish", help="publish a prebuilt stable release")
    publish.add_argument("tag")
    publish.add_argument("--bundle", type=Path, default=Path("dist"))
    args = parser.parse_args()

    root = Path.cwd()
    if args.command == "build":
        commit = _git("rev-parse", "HEAD", cwd=root)
        dirty = bool(_git("status", "--porcelain", cwd=root))
        output = build_results_release_bundle(
            args.source,
            args.output,
            source_commit=commit,
            dirty=dirty,
        )
        print(f"results release bundle written to {output}")
        if dirty:
            print("warning: bundle is for local validation only because the source tree is dirty")
    else:
        publish_results_release(args.tag, args.bundle, root=root)


if __name__ == "__main__":
    main()
