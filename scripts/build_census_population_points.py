"""Compile the City's census population points from Statistics Canada's Geographic Attribute Files.

The release compares a riding seat across a redistribution by census population
(``toronto_election_results.census_points``). This script reads the Geographic Attribute File
of the 2011 and 2021 Censuses, keeps the dissemination blocks of the City of Toronto (census
subdivision 3520005), sums their population by dissemination area and writes one row per area
with its representative point:

    census_year, dauid, latitude, longitude, population

The 2011 points are weighted by population, as Statistics Canada's guide to the file says. The
coordinates are NAD83 latitude and longitude. Both files are saved from Statistics Canada's pages
by hand, because the pages put a bot check in front of the download, and the build manifest
records each with its page URL.

Usage:
    uv run python scripts/build_census_population_points.py
"""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from toronto_election_results.census_points import (
    CENSUS_FILES,
    CENSUS_POINTS_FILENAME,
)

GAF_2011 = REPO_ROOT / CENSUS_FILES[2011][0]
GAF_2021 = REPO_ROOT / CENSUS_FILES[2021][0]
OUTPUT = REPO_ROOT / "data" / "reference" / CENSUS_POINTS_FILENAME
TORONTO_CSD = "3520005"
COLUMNS = ["census_year", "dauid", "latitude", "longitude", "population"]


def _code(value: object) -> str:
    """A geographic code as text, whether the file stores it as text or as a number."""

    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _member(archive: zipfile.ZipFile, suffix: str) -> str:
    names = [name for name in archive.namelist() if name.lower().endswith(suffix)]
    if len(names) != 1:
        raise ValueError(f"expected one {suffix} file in the archive, found {names}")
    return names[0]


def _read_2021(path: Path) -> pd.DataFrame:
    columns = {
        "CSDUID_SDRIDU": "csd",
        "DAUID_ADIDU": "dauid",
        "DARPLAT_ADLAT": "latitude",
        "DARPLONG_ADLONG": "longitude",
        "DBPOP2021_IDPOP2021": "population",
    }
    with zipfile.ZipFile(path) as archive, archive.open(_member(archive, ".csv")) as handle:
        frame = pd.read_csv(handle, usecols=list(columns), dtype=str, encoding="latin-1")
    return frame.rename(columns=columns)


# The 2011 file has no header row. Its fields follow the record layout of the reference guide
# (92-151-G, 2011, section 4): DBuid, DBpop2011, ..., DAuid, DAlamx, DAlamy, DAlat, DAlong, ...,
# CSDuid at these zero-based positions.
LAYOUT_2011 = {"population": 1, "dauid": 6, "latitude": 9, "longitude": 10, "csd": 24}


def _read_2011(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        book = load_workbook(io.BytesIO(archive.read(_member(archive, ".xlsx"))), read_only=True)
    records = []
    for row in book.worksheets[0].iter_rows(values_only=True):
        if len(row) <= max(LAYOUT_2011.values()) or not str(row[0]).isdigit():
            raise ValueError(f"a row of the 2011 file does not follow the record layout: {row[:3]}")
        if _code(row[LAYOUT_2011["csd"]]) != TORONTO_CSD:
            continue
        records.append({name: row[i] for name, i in LAYOUT_2011.items()})
    book.close()
    frame = pd.DataFrame.from_records(records, columns=list(LAYOUT_2011))
    return frame.astype(str)


def _areas(frame: pd.DataFrame, year: int) -> pd.DataFrame:
    frame = frame.assign(csd=frame["csd"].map(_code)).loc[lambda f: f["csd"].eq(TORONTO_CSD)]
    frame = frame.assign(
        dauid=frame["dauid"].map(_code),
        latitude=frame["latitude"].astype(float),
        longitude=frame["longitude"].astype(float),
        population=frame["population"].astype(float).astype(int),
    )
    points = frame.drop_duplicates(["dauid", "latitude", "longitude"])
    if points["dauid"].duplicated().any():
        raise ValueError(f"{year}: a dissemination area has two representative points")
    population = frame.groupby("dauid", sort=True)["population"].sum()
    out = points.set_index("dauid")[["latitude", "longitude"]].join(population)
    out = out.reset_index().assign(census_year=year)
    return out[COLUMNS].sort_values("dauid", ignore_index=True)


def compile_points(gaf_2011: Path, gaf_2021: Path) -> pd.DataFrame:
    frames = [_areas(_read_2011(gaf_2011), 2011), _areas(_read_2021(gaf_2021), 2021)]
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    for path in (GAF_2011, GAF_2021):
        if not path.is_file():
            raise SystemExit(f"{path} is missing; save it from Statistics Canada's page by hand")
    frame = compile_points(GAF_2011, GAF_2021)
    frame.to_csv(OUTPUT, index=False)
    for year, rows in frame.groupby("census_year"):
        print(f"{year}: {len(rows):,} dissemination areas, population {rows['population'].sum():,}")


if __name__ == "__main__":
    main()
