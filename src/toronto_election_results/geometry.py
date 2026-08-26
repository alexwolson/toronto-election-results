"""Legacy v1 voting-subdivision parser retained for historical unit tests.

The City publishes subdivision polygons from 2006 onward (per ADR 0001, earlier years have no
geometry). Each subdivision carries a 5-character code = 2-digit ward + 3-digit subdivision, so
the boundaries key back to results by ``(election_year, ward_number, subdivision_id)``. Results
are ward-level, so this dataset is a pure add-on; no join is required.

Subdivision-level output is outside the v2 release scope. Public v2 geometry is
Contest-level and is assembled by ``district_geometry`` through the main pipeline.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

RAW = Path("data/raw/subdivisions")
OUT = Path("data/out")

# year -> (relative path under RAW, code column name)
SOURCES = {
    2006: ("zip://data/raw/subdivisions/voting-subdivisions-2006.zip", "AREA_LONG"),
    2010: ("data/raw/subdivisions/voting-subdivisions-2010-4326.geojson", "AREA_LONG_CODE"),
    2014: ("data/raw/subdivisions/voting-subdivisions-2014-4326.geojson", "AREA_LONG_CODE"),
    2018: ("data/raw/subdivisions/voting-subdivisions-2018-4326.geojson", "AREA_LONG_CODE"),
    2022: ("data/raw/subdivisions/voting-subdivisions-2022-4326.geojson", "AREA_LONG_CODE"),
    2023: ("data/raw/subdivisions/voting-subdivisions-2023-4326.geojson", "AREA_LONG_CODE"),
}

KEEP = ["election_year", "ward_number", "subdivision_id", "area_code", "geometry"]


def parse_area_code(code: str) -> tuple[int, int]:
    """Split a subdivision code ('11055') into (ward_number, subdivision_id) = (11, 55)."""
    code = str(code).strip()
    return int(code[:2]), int(code[2:])


def load_subdivisions(path: str | Path, *, year: int, code_col: str) -> gpd.GeoDataFrame:
    """Read one year's subdivision file into a keyed GeoDataFrame in EPSG:4326."""
    gdf = gpd.read_file(path)
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
    wards_subs = gdf[code_col].map(parse_area_code)
    gdf["election_year"] = year
    gdf["ward_number"] = [w for w, _ in wards_subs]
    gdf["subdivision_id"] = [s for _, s in wards_subs]
    gdf["area_code"] = gdf[code_col].astype(str)
    return gdf[KEEP]


def build_boundaries() -> gpd.GeoDataFrame:
    """Concatenate every available year's subdivision boundaries."""
    parts = [
        load_subdivisions(path, year=year, code_col=code_col)
        for year, (path, code_col) in SOURCES.items()
    ]
    combined = pd.concat(parts, ignore_index=True)
    return gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")


def main() -> None:
    """Refuse to recreate the deleted, out-of-scope v1 spatial artifact."""

    raise SystemExit(
        "The subdivision-geometry command is retired; run "
        "`python -m toronto_election_results.pipeline --skip-download` to build the v2 "
        "Contest-level electoral_districts artifacts."
    )


if __name__ == "__main__":
    main()
