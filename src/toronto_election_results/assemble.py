"""Assemble the unified Toronto election results table from the raw Open Data files.

Extracts the per-year result ZIPs, parses councillor and mayor files (all layout families),
collapses to contest level, tags election metadata + provenance, derives the per-contest fields,
normalizes names, and resolves cross-election candidate IDs.

Incumbency (``incumbent`` / ``incumbent_source`` / ``incumbent_confidence``) is derived from a
curated council composition and joined in below.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from .candidates import assign_candidate_ids, normalize_name
from .derive import derive_contest_fields
from .incumbency import ROSTER_CONFIDENCE, build_composition, flag_incumbents
from .parse_results import parse_open_data_file, to_contest_level
from .voter_statistics import attach_electorate, voter_statistics

RAW = Path("data/raw")
INTERIM = Path("data/interim")
OUT = Path("data/out")

# year -> (polling date, election type, ward system, offices present)
ELECTIONS = {
    2003: ("2003-11-10", "general", "44-ward", ("councillor", "mayor")),
    2006: ("2006-11-13", "general", "44-ward", ("councillor", "mayor")),
    2010: ("2010-10-25", "general", "44-ward", ("councillor", "mayor")),
    2014: ("2014-10-27", "general", "44-ward", ("councillor", "mayor")),
    2018: ("2018-10-22", "general", "25-ward", ("councillor", "mayor")),
    2022: ("2022-10-24", "general", "25-ward", ("councillor", "mayor")),
    2023: ("2023-06-26", "by_election", "25-ward", ("mayor",)),
}

FINAL_COLUMNS = [
    "election_year",
    "election_date",
    "election_type",
    "ward_system",
    "office",
    "ward_number",
    "ward_name",
    "contest_id",
    "candidate_name",
    "candidate_first_name",
    "candidate_last_name",
    "candidate_name_raw",
    "candidate_id",
    "candidate_id_confidence",
    "votes",
    "total_contest_votes",
    "vote_share",
    "vote_rank",
    "n_candidates",
    "eligible_electors",
    "ballots_cast",
    "turnout",
    "elected",
    "acclaimed",
    "incumbent",
    "incumbent_source",
    "incumbent_confidence",
    "source",
]


def extract_results(raw: Path = RAW, interim: Path = INTERIM) -> dict[int, Path]:
    """Extract each year's result ZIP into ``interim/results/<year>/`` (idempotent)."""
    out: dict[int, Path] = {}
    for zip_path in sorted((raw / "results").glob("*-results.zip")):
        year = int(zip_path.name[:4])
        dest = interim / "results" / str(year)
        if not dest.exists():
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(dest)
        out[year] = dest
    return out


def _office_file(directory: Path, office: str) -> Path:
    """Locate a year's councillor/mayor file, ignoring school-board files."""
    matches = [
        p
        for p in directory.rglob("*")
        if p.is_file()
        and office in p.name.lower()
        and p.suffix.lower() in {".xls", ".xlsx"}
        and "school" not in p.name.lower()
        and "board" not in p.name.lower()
    ]
    if not matches:
        raise FileNotFoundError(f"no {office} file under {directory}")
    return matches[0]


def _contest_id(year: int, office: str, ward_number) -> str:
    ward = "city" if office == "mayor" or pd.isna(ward_number) else int(ward_number)
    return f"{year}-{office}-{ward}"


def build_base(raw: Path = RAW, interim: Path = INTERIM) -> pd.DataFrame:
    """Parse every in-scope file into contest-level rows tagged with metadata + provenance."""
    extracted = extract_results(raw, interim)
    frames = []
    for year, (date, etype, ward_system, offices) in ELECTIONS.items():
        for office in offices:
            if year == 2023:  # the by-election mayor file lives outside the results ZIPs
                path = raw / "byelection" / "2023_office_of_the_mayor.xlsx"
            else:
                path = _office_file(extracted[year], office)
            wardwise = parse_open_data_file(path, office=office)
            contest = to_contest_level(wardwise, office=office)
            contest["election_year"] = year
            contest["election_date"] = date
            contest["election_type"] = etype
            contest["ward_system"] = ward_system
            contest["source"] = "open_data"
            contest["contest_id"] = [_contest_id(year, office, w) for w in contest["ward_number"]]
            frames.append(contest)
    return pd.concat(frames, ignore_index=True)


def assemble(raw: Path = RAW, interim: Path = INTERIM) -> pd.DataFrame:
    """Build the full unified table (2003–2023; incumbency joined below)."""
    df = build_base(raw, interim)
    df = derive_contest_fields(df)

    normalized = df["candidate_name_raw"].map(normalize_name)
    df["candidate_name"] = [n[0] for n in normalized]
    df["candidate_first_name"] = [n[1] for n in normalized]
    df["candidate_last_name"] = [n[2] for n in normalized]
    df = assign_candidate_ids(df)

    df = flag_incumbents(df, build_composition(), roster_confidence=ROSTER_CONFIDENCE)
    df = attach_electorate(df, voter_statistics())

    df["election_date"] = pd.to_datetime(df["election_date"]).dt.date
    df["ward_number"] = df["ward_number"].astype("Int64")
    df = df[FINAL_COLUMNS].sort_values(
        ["election_year", "office", "ward_number", "vote_rank"],
        na_position="last",
    )
    return df.reset_index(drop=True)


def main() -> None:
    df = assemble()
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "toronto_election_results.csv", index=False)
    df.to_parquet(OUT / "toronto_election_results.parquet", index=False)
    build_composition().to_csv(OUT / "council_composition.csv", index=False)
    print(f"wrote {len(df)} rows to {OUT}/toronto_election_results.{{csv,parquet}}")
    print(df.groupby(["election_year", "office"]).size().to_string())


if __name__ == "__main__":
    main()
