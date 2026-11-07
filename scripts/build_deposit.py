"""Assemble the files of a frozen release for deposit in the CJPS Dataverse.

Zenodo archives the tagged repository, which holds the release tables (`data/out/`), the
documentation and the code. The Dataverse deposit mirrors the release tables and documentation
and adds the City of Toronto's raw files, which the repository does not track. Those files are
published on the City's Open Data portal under the Open Government Licence – Toronto, which lets
them be redistributed. The other raw files are cited by URL and checksum in the build manifest.

A raw file is copied only when its manifest URL is on the City's Open Data portal, its checksum
matches the manifest, and it holds no email address: the portal's package listings and its
directory of Council members carry contact details, and the deposit leaves those out.

The script checks that the working tree is clean, that HEAD carries the release tag and that
every release table matches the manifest. It writes the deposit to OUT_DIR:

- `data/`: the release tables and `build_manifest.json`;
- `docs/`, `README.md`, `CONTEXT.md`, `CITATION.cff` and `LICENSE`;
- `raw/`: the City's raw files, under their `data/raw/` paths, with `raw/SOURCES.csv`;
- `DATAVERSE.md`: the values for the Dataverse deposit form.

Usage:
    python -I scripts/build_deposit.py RELEASE_TAG ZENODO_VERSION_DOI OUT_DIR
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
CITY_PORTAL_HOST = "ckan0.cf.opendata.inter.prod-toronto.ca"
CITY_LICENCE = "Open Government Licence – Toronto"
EMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TOP_LEVEL_FILES = ("README.md", "CONTEXT.md", "CITATION.cff", "LICENSE")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _holds_email(path: Path) -> bool:
    """Search the file, and each member of a ZIP-based file (xlsx, zip), for an email address."""

    data = path.read_bytes()
    if EMAIL.search(data):
        return True
    if data[:2] == b"PK":
        with zipfile.ZipFile(path) as archive:
            return any(EMAIL.search(archive.read(name)) for name in archive.namelist())
    return False


def _check_release(tag: str) -> dict[str, object]:
    if _git("status", "--porcelain"):
        raise SystemExit("the working tree has uncommitted changes")
    if tag not in _git("tag", "--points-at", "HEAD").split():
        raise SystemExit(f"HEAD does not carry the tag {tag}")
    manifest = json.loads((OUT / "build_manifest.json").read_text(encoding="utf-8"))
    for record in manifest["artifacts"]:
        path = REPO_ROOT / record["path"]
        if _sha256(path) != record["sha256"]:
            raise SystemExit(f"{record['path']} does not match the build manifest")
    return manifest


def _city_raw_files(manifest: dict[str, object]) -> tuple[list[dict[str, object]], list[str]]:
    kept: list[dict[str, object]] = []
    left_out: list[str] = []
    for record in manifest["sources"]:
        local = str(record["local_path"])
        if not local.startswith("data/raw/"):
            continue
        if urlparse(str(record.get("source_url", ""))).hostname != CITY_PORTAL_HOST:
            continue
        path = REPO_ROOT / local
        if not path.is_file() or _sha256(path) != record["sha256"]:
            raise SystemExit(f"{local} is missing or does not match the build manifest")
        if _holds_email(path):
            left_out.append(local)
            continue
        kept.append(record)
    return kept, left_out


def _dataverse_form(tag: str, doi: str, citation: str) -> str:
    title = re.search(r'^title: "(.+)"$', citation, re.MULTILINE)
    abstract = re.search(r"^abstract: >-\n((?:  .+\n)+)", citation, re.MULTILINE)
    keywords = re.findall(
        r"^  - (?!given-names)([A-Za-z].+)$", citation.split("keywords:")[1], re.MULTILINE
    )
    description = " ".join(line.strip() for line in abstract.group(1).splitlines())
    return f"""# Dataverse deposit: {tag}

Values for the CJPS Dataverse form. The deposit mirrors release `{tag}`, archived on Zenodo at
https://doi.org/{doi}.

- **Title:** {title.group(1)}, release {tag}
- **Authors:** Olson, Alex (University of Toronto; ORCID 0000-0002-6593-2779); Elliott, Matt
- **Description:** {description} This deposit mirrors release {tag}, archived on Zenodo
  (https://doi.org/{doi}), and adds the City of Toronto raw files the build reads.
- **Subject:** Social Sciences
- **Keywords:** {"; ".join(keywords)}
- **Related dataset:** Olson, A., & Elliott, M. (2026). *Toronto Election Results* (Version
  {tag}) [Data set]. Zenodo. https://doi.org/{doi}
- **Licence:** CC BY 4.0 for the data and documentation. The raw files in `raw/` are the City of
  Toronto's, under the {CITY_LICENCE}.
- **Version:** {tag}
- **Contact:** fill in on the form.
"""


def main(argv: list[str]) -> None:
    if len(argv) != 4:
        raise SystemExit(__doc__)
    tag, doi, out_dir = argv[1], argv[2], Path(argv[3])
    if not re.fullmatch(r"results-\d{4}-\d{2}-\d{2}\.\d+", tag):
        raise SystemExit("RELEASE_TAG must read like results-2026-11-07.1")
    if not re.fullmatch(r"10\.5281/zenodo\.\d+", doi):
        raise SystemExit("ZENODO_VERSION_DOI must read like 10.5281/zenodo.12345678")
    if out_dir.exists():
        raise SystemExit(f"{out_dir} already exists")
    manifest = _check_release(tag)
    raw, left_out = _city_raw_files(manifest)

    shutil.copytree(OUT, out_dir / "data")
    shutil.copytree(REPO_ROOT / "docs", out_dir / "docs")
    for name in TOP_LEVEL_FILES:
        shutil.copy2(REPO_ROOT / name, out_dir / name)
    sources_path = out_dir / "raw" / "SOURCES.csv"
    sources_path.parent.mkdir(parents=True, exist_ok=True)
    with sources_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "source_url", "sha256", "bytes", "licence"])
        for record in raw:
            relative = str(record["local_path"]).removeprefix("data/raw/")
            target = out_dir / "raw" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / str(record["local_path"]), target)
            writer.writerow(
                [relative, record["source_url"], record["sha256"], record["bytes"], CITY_LICENCE]
            )
    citation = (REPO_ROOT / "CITATION.cff").read_text(encoding="utf-8")
    (out_dir / "DATAVERSE.md").write_text(_dataverse_form(tag, doi, citation), encoding="utf-8")
    size = sum(int(record["bytes"]) for record in raw)
    print(
        f"wrote {out_dir}: the release tables, docs and {len(raw)} City raw files ({size:,} bytes)"
    )
    for local in left_out:
        print(f"left out {local}: it holds contact details")


if __name__ == "__main__":
    main(sys.argv)
