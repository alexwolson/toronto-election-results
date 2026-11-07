"""Census population points for comparing a riding seat across a redistribution.

When a member runs after the riding boundaries change, the release asks which new riding took
over the seat they held: the new riding that holds the most of the held riding's people. Council
wards answer this with the City's polls (``council_poll_points``). Ridings answer it with census
population: each dissemination area of the City is a point, at Statistics Canada's representative
point, weighted by the area's population.

Each redistribution is compared with the census it was drawn from: the 2011 Census for the
federal 2013 Representation Order and Ontario's 2018 ridings, which the Representation Act, 2015
adopted from it, and the 2021 Census for the federal 2023 Representation Order. The 2001 Census,
from which the 2003 order and Ontario's 2007 ridings were drawn, is not yet acquired, so those
changes stay unknown.

``scripts/build_census_population_points.py`` compiles the points from Statistics Canada's
Geographic Attribute Files into ``data/reference/census_population_points.csv``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .district_geometry import TARGET_CRS


@dataclass(frozen=True)
class PopulationPoints:
    """Points with a population each, in EPSG:4326."""

    points: tuple[object, ...]
    weights: tuple[float, ...]


CENSUS_POINTS_FILENAME = "census_population_points.csv"

# Statistics Canada's Geographic Attribute Files, saved from these pages by hand because the pages
# put a bot check in front of the download.
CENSUS_FILES = {
    2011: (
        Path("data/raw/census/2011_92-151_XBB_xlsx.zip"),
        "https://www12.statcan.gc.ca/census-recensement/2011/geo/ref/att-eng.cfm",
    ),
    2021: (
        Path("data/raw/census/2021_92-151_X.zip"),
        "https://www12.statcan.gc.ca/census-recensement/2021/geo/aip-pia/attribute-attribs/index-eng.cfm",
    ),
}

# The census each redistribution was drawn from, keyed by the Boundary regime it drew.
CENSUS_FOR_REGIME = {
    "federal-2013-representation-order": 2011,
    "ontario-2018-124": 2011,
    "federal-2023-representation-order": 2021,
}


def read_population_points(path: str | Path) -> dict[str, PopulationPoints]:
    """Read the compiled census points, keyed by the Boundary regime each census is used for.

    The coordinates are Statistics Canada's NAD83 latitude and longitude, carried into EPSG:4326
    the way the riding shapes are. Areas without population carry no weight and are left out.
    Without the file, no regime has points.
    """

    path = Path(path)
    if not path.is_file():
        return {}
    frame = pd.read_csv(path, dtype={"dauid": "string"})
    frame = frame.loc[frame["population"].gt(0)]
    by_year: dict[int, PopulationPoints] = {}
    for year, rows in frame.groupby("census_year", sort=True):
        points = gpd.GeoSeries(
            gpd.points_from_xy(rows["longitude"], rows["latitude"]), crs="EPSG:4269"
        ).to_crs(TARGET_CRS)
        by_year[int(year)] = PopulationPoints(
            points=tuple(points), weights=tuple(float(p) for p in rows["population"])
        )
    return {regime: by_year[year] for regime, year in CENSUS_FOR_REGIME.items() if year in by_year}
