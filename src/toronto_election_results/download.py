"""Download the City of Toronto Open Data resources this project consumes.

Resources are resolved dynamically from the CKAN ``package_show`` API (so specific resource IDs
never get hard-coded), selected by name/format, and streamed to ``data/raw/``. Downloads are
idempotent: an already-present file is skipped unless ``overwrite=True``.

The datasets pulled:
  - election-results-official ............ six general-election result ZIPs (2003–2022)
  - elections-official-by-election-results  the 2023 Office of the Mayor by-election
  - elections-subdivisions ............... voting-subdivision boundaries (2006–2023, WGS84)
  - members-of-toronto-city-council-*  ... attendance + voting record (for incumbency)
  - elected-officials-contact-information  name→ward reference
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import requests

CKAN_PACKAGE_SHOW = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show"

RAW = Path("data/raw")

_KNOWN_EXTENSIONS = {".zip", ".xlsx", ".xls", ".csv", ".geojson", ".json", ".gpkg", ".xml", ".txt"}


def fetch_package(slug: str, *, session: requests.Session | None = None) -> list[dict]:
    """Return the resource list for a CKAN dataset slug."""
    getter = session or requests
    resp = getter.get(CKAN_PACKAGE_SHOW, params={"id": slug}, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success"):
        raise ValueError(f"CKAN package not found: {slug}")
    return payload["result"]["resources"]


def select_resources(
    resources: list[dict],
    *,
    name_contains: str | None = None,
    name_regex: str | None = None,
    formats: set[str] | None = None,
) -> list[dict]:
    """Filter CKAN resources by (case-insensitive) name substring, name regex, and/or format."""
    regex = re.compile(name_regex, re.IGNORECASE) if name_regex else None
    wanted_formats = {f.lower() for f in formats} if formats else None
    picked = []
    for res in resources:
        name = res.get("name") or ""
        if name_contains and name_contains.lower() not in name.lower():
            continue
        if regex and not regex.search(name):
            continue
        if wanted_formats and (res.get("format") or "").lower() not in wanted_formats:
            continue
        picked.append(res)
    return picked


def _slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def filename_for(res: dict) -> str:
    """A stable local filename for a resource.

    Prefer the URL basename when it carries a real extension; otherwise (e.g. datastore-dump
    URLs that end in a bare id) derive it from the resource name plus the declared format.
    """
    basename = Path(urlparse(res["url"]).path).name
    if Path(basename).suffix.lower() in _KNOWN_EXTENSIONS:
        return basename
    ext = (res.get("format") or "bin").lower()
    return f"{_slug(res.get('name') or basename)}.{ext}"


def download_resource(
    res: dict,
    dest_dir: str | Path,
    *,
    session: requests.Session | None = None,
    overwrite: bool = False,
) -> Path:
    """Stream one resource to ``dest_dir`` (atomic via a ``.part`` temp file). Skips if present."""
    getter = session or requests
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename_for(res)
    if dest.exists() and not overwrite:
        return dest
    with getter.get(res["url"], stream=True, timeout=300) as resp:
        resp.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as fh:
            fh.writelines(resp.iter_content(chunk_size=1 << 16))
        tmp.replace(dest)
    return dest


# (slug, subdir, selector-kwargs) for everything the pipeline needs.
_MANIFEST = [
    ("election-results-official", "results", {"name_regex": r"^\d{4}-results$"}),
    (
        "elections-official-by-election-results",
        "byelection",
        {"name_contains": "2023 Office of the Mayor"},
    ),
    # Council by-election results (2016–2025); all carry "Councillor", unlike mayor/school-board.
    (
        "elections-official-by-election-results",
        "byelection",
        {"name_contains": "Councillor"},
    ),
    # Council by-election voter statistics: any ward file that is not school-board or mayoral.
    (
        "elections-by-election-voter-statistics",
        "byelection_voter_stats",
        {"name_regex": r"^(?!.*(tdsb|tcdsb|mayoral)).*ward"},
    ),
    (
        "elections-subdivisions",
        "subdivisions",
        {"name_regex": r"voting-subdivisions-20(10|14|18|22|23) - 4326\.geojson"},
    ),
    ("elections-subdivisions", "subdivisions", {"name_contains": "voting-subdivisions-2006"}),
    (
        "members-of-toronto-city-council-meeting-attendance",
        "council/attendance",
        {
            "name_regex": r"councillors-meeting-attendance-(2006-2010|2010-2014|2014-2018|2018-2022)\.csv"
        },
    ),
    (
        "members-of-toronto-city-council-voting-record",
        "council/voting",
        {"name_regex": r"member-voting-record-(2006-2010|2010-2014|2014-2018|2018-2022)\.csv"},
    ),
    (
        "elected-officials-contact-information",
        "council/contact",
        {"name_regex": r"(2018-2022|2022-2026) Elected Officials Contact Info\.csv"},
    ),
    ("elections-voter-statistics", "voter_stats", {"name_regex": r"^\d{4}-voter-statistics$"}),
    (
        "elections-by-election-voter-statistics",
        "voter_stats",
        {"name_contains": "2023-mayoral"},
    ),
]


def download_all(*, root: str | Path = RAW, overwrite: bool = False) -> list[Path]:
    """Run the full manifest. Returns the paths written (or already present)."""
    session = requests.Session()
    written: list[Path] = []
    for slug, subdir, selector in _MANIFEST:
        resources = fetch_package(slug, session=session)
        picked = select_resources(resources, **selector)
        if not picked:
            print(f"  ! no resources matched for {slug} {selector}")
        for res in picked:
            path = download_resource(res, Path(root) / subdir, session=session, overwrite=overwrite)
            written.append(path)
            print(f"  {path}")
    return written


if __name__ == "__main__":
    paths = download_all()
    print(f"\n{len(paths)} resources present under {RAW}/")
