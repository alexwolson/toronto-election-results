"""Record the published URL of every downloaded file the build manifest lists.

The build reads its official files from `data/raw/`, which is not tracked. This script writes
`data/reference/raw_source_urls.csv`, one row per file the manifest lists under `data/raw/`, with
the URL it is downloaded from, so that the manifest can name the source of each checksum.

URLs come from the adapters' own tables (Elections Canada and Elections Ontario events, the City's
result files and Council records, the 2026 candidate lists) and, for the other City of Toronto
Open Data files, from the portal's `package_show` listing, selected the way `download.py` selects
them. The script fails if any listed file is left without a URL.

Usage:
    python -I scripts/build_raw_source_urls.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from toronto_election_results.download import (
    _MANIFEST,
    CKAN_PACKAGE_SHOW,
    fetch_package,
    filename_for,
    select_resources,
)
from toronto_election_results.federal import FEDERAL_EVENTS
from toronto_election_results.federal_historical import SOURCE_FILENAMES
from toronto_election_results.official_sources import (
    BY_ELECTION_RESULT_URLS,
    COUNCIL_RECORD_URLS,
    GENERAL_RESULT_URLS,
)
from toronto_election_results.ontario import (
    REPORTS,
    TABULATIONS,
    ontario_source_files,
    report_csv_url,
    tabulation_path,
)
from toronto_election_results.pending_candidates import (
    COUNCILLOR_CANDIDATES_URL,
    MAYOR_CANDIDATES_URL,
    TRUSTEE_CANDIDATES_URL,
    pending_candidate_paths,
)
from toronto_election_results.riding_geometry import RIDING_SOURCES

RAW = Path("data/raw")
MANIFEST = REPO_ROOT / "data" / "out" / "build_manifest.json"
OUTPUT = REPO_ROOT / "data" / "reference" / "raw_source_urls.csv"
TRUSTEE_BY_ELECTION_SLUG = "elections-official-by-election-results"


def _known_urls() -> dict[str, str]:
    urls: dict[str, str] = {}

    def add(path: Path, url: str) -> None:
        key = path.as_posix()
        if urls.get(key, url) != url:
            raise ValueError(f"two URLs for {key}")
        urls[key] = url

    for year, url in GENERAL_RESULT_URLS.items():
        add(RAW / "results" / f"{year}-results.zip", url)
    for name, url in BY_ELECTION_RESULT_URLS.items():
        add(RAW / "byelection" / name, url)
    for name, url in COUNCIL_RECORD_URLS.items():
        collection = "attendance" if name.startswith("councillors-meeting") else "voting"
        add(RAW / "council" / collection / name, url)
    candidate_urls = (MAYOR_CANDIDATES_URL, COUNCILLOR_CANDIDATES_URL, TRUSTEE_CANDIDATES_URL)
    for path, url in zip(
        pending_candidate_paths(RAW / "council" / "candidates_2026"), candidate_urls, strict=True
    ):
        add(path, url)
    for event in FEDERAL_EVENTS:
        for url in (*event.source_urls, *event.summary_source_urls):
            add(RAW / "federal" / event.event_id / Path(urlparse(url).path).name, url)
    for url, filename in SOURCE_FILENAMES.items():
        add(RAW / "federal" / "historical" / filename, url)
    for report in REPORTS:
        files = ontario_source_files(RAW / "ontario", report)
        for output_id, path in (
            (report.candidates_output_id, files.candidates_csv),
            (report.statistics_output_id, files.statistics_csv),
            (report.parties_output_id, files.parties_csv),
        ):
            add(path, report_csv_url(report.report_group_id, output_id))
    for spec in TABULATIONS:
        add(tabulation_path(RAW / "ontario", spec), spec.tabulation_url)
    for source in RIDING_SOURCES.values():
        add(source.path, source.url)
    return urls


def _portal_urls() -> dict[str, str]:
    urls: dict[str, str] = {}
    packages: dict[str, list[dict]] = {}
    for slug, subdir, selector in _MANIFEST:
        resources = packages.setdefault(slug, fetch_package(slug))
        for resource in select_resources(resources, **selector):
            urls[(RAW / subdir / filename_for(resource)).as_posix()] = resource["url"]
    trustee = packages.setdefault(TRUSTEE_BY_ELECTION_SLUG, fetch_package(TRUSTEE_BY_ELECTION_SLUG))
    for resource in trustee:
        urls.setdefault(
            (RAW / "trustee_byelections" / filename_for(resource)).as_posix(), resource["url"]
        )
    for slug in packages:
        urls[(RAW / "ckan" / f"{slug}.json").as_posix()] = f"{CKAN_PACKAGE_SHOW}?id={slug}"
    return urls


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    listed = sorted(
        record["local_path"]
        for record in manifest["sources"]
        if record["local_path"].startswith("data/raw/")
    )
    known = _known_urls()
    portal = _portal_urls()
    rows = []
    for path in listed:
        url = known.get(path) or portal.get(path)
        if url is None:
            raise SystemExit(f"no published URL found for {path}")
        rows.append({"local_path": path, "source_url": url})
    OUTPUT.write_text(pd.DataFrame(rows).to_csv(index=False, lineterminator="\n"), encoding="utf-8")
    print(f"wrote {len(rows)} URLs to {OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
