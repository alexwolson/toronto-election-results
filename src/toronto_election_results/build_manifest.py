"""Create the release's lean source/build manifest."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .coverage import ELECTION_DAY

PENDING_CANDIDATE_SNAPSHOT_THROUGH = "2026-08-27"

COVERAGE = {
    "from": "2003-01-01",
    "through": ELECTION_DAY.isoformat(),
    "pending_candidate_snapshot_through": PENDING_CANDIDATE_SNAPSHOT_THROUGH,
    "pending_event_through": ELECTION_DAY.isoformat(),
    "timezone": "America/Toronto",
}

EVENT_ARCHIVE_CAVEATS = [
    {
        "authority": "toronto_city_clerk",
        "period": "2003-01-01/2011-12-31",
        "scope": "trustee_by_elections",
        "status": "uncertain",
    }
]

EXCLUDED_CALLS = [
    {
        "label": "Don Valley West federal by-election",
        "scheduled_date": "2008-09-22",
        "reason": "cancelled when superseded by a general-election writ; no result",
    },
]

UNACQUIRED_RESULTS = [
    {
        "label": "Scarborough Southwest provincial by-election",
        "scheduled_date": "2026-09-03",
        "reason": "not yet present in Elections Ontario's official result CSV export",
        "source_url": "https://www.elections.on.ca/en/election-results/098.html",
    }
]

PENDING_EVENTS = [
    {
        "label": "2026 Toronto municipal general election",
        "scheduled_date": ELECTION_DAY.isoformat(),
        "candidate_snapshot_through": PENDING_CANDIDATE_SNAPSHOT_THROUGH,
        "status": "pending",
    }
]


def sha256_file(path: str | Path) -> str:
    """Hash a local source or artifact without loading the whole file in memory."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: Path, *, rows: int | None = None, timestamp_field: str) -> dict[str, object]:
    record: dict[str, object] = {
        "local_path": path.as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        timestamp_field: datetime.fromtimestamp(path.stat().st_mtime, UTC)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    if rows is not None:
        record["rows"] = rows
    return record


def build_manifest(
    *,
    sources: list[str | Path],
    artifacts: list[str | Path],
    row_counts: dict[str, int],
    generated_at: str,
) -> dict[str, object]:
    """Build JSON-serializable release metadata from concrete local files."""

    source_paths = sorted((Path(path) for path in sources), key=lambda path: path.as_posix())
    artifact_paths = sorted((Path(path) for path in artifacts), key=lambda path: path.as_posix())
    return {
        "schema_version": "2.2.0",
        "generated_at": generated_at,
        "coverage": COVERAGE,
        "sources": [_file_record(path, timestamp_field="retrieved_at") for path in source_paths],
        "artifacts": [
            _file_record(path, rows=row_counts.get(path.name), timestamp_field="written_at")
            for path in artifact_paths
        ],
        "event_archive_caveats": EVENT_ARCHIVE_CAVEATS,
        "excluded_calls": EXCLUDED_CALLS,
        "unacquired_results": UNACQUIRED_RESULTS,
        "pending_events": PENDING_EVENTS,
    }


def write_manifest(manifest: dict[str, object], path: str | Path) -> Path:
    """Atomically write the manifest with stable key and list ordering."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination
