"""Federal and Ontario riding shapes from Elections Canada's boundary files.

Elections Canada publishes the federal electoral districts of each representation order under the
Open Government Licence – Canada. The release reads the 2003, 2013 and 2023 orders, keeps the
Toronto ridings it uses (matched by district number) and attaches their shapes in EPSG:4326.

Ontario's ridings within Toronto are the federal ridings by statute. The Representation Act, 2005
kept the federal ridings of the 2003 order for southern Ontario, and the Representation Act, 2015
did the same with the 2013 order, while giving Northern Ontario its own count. Each Ontario riding
of the 2007 and 2018 boundary sets therefore takes the shape of its federal namesake, matched by
name; the Ontario district numbers differ from the federal ones, since Ontario numbers its own
northern ridings among them. The build fails if a riding has no federal match or more than one.

The 1996 order, which Ontario used from 1999 to 2003, comes from Statistics Canada and is added
when its file is in place.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import shapely

from .district_geometry import TARGET_CRS, _valid_polygonal

ELECTIONS_CANADA = "Elections Canada"
_FTP = (
    "https://ftp.maps.canada.ca/pub/elections_elections/"
    "Electoral-districts_Circonscription-electorale/"
)
_FEDERAL_BODY = "canada_house_of_commons"
_ONTARIO_BODY = "ontario_legislative_assembly"
_DASHES = re.compile(r"[‐-―\-]+")


@dataclass(frozen=True)
class RidingSource:
    """One representation order's boundary file."""

    path: Path
    url: str
    id_column: str
    name_column: str
    resource: str
    year: int


FEDERAL_RIDING_SOURCES: dict[str, RidingSource] = {
    "federal-2003-representation-order": RidingSource(
        path=Path(
            "data/raw/boundaries/federal-2003/federal_electoral_districts_boundaries_2003_en.gdb.zip"
        ),
        url=_FTP
        + "federal_electoral_districts_boundaries_2003/"
        + "federal_electoral_districts_boundaries_2003_en.gdb.zip",
        id_column="fednum",
        name_column="name",
        resource="Federal Electoral Districts - Canada 2003",
        year=2003,
    ),
    "federal-2013-representation-order": RidingSource(
        path=Path(
            "data/raw/boundaries/federal-2013/federal_electoral_districts_boundaries_2013_en.gdb.zip"
        ),
        url=_FTP
        + "federal_electoral_districts_boundaries_2013/"
        + "federal_electoral_districts_boundaries_2013_en.gdb.zip",
        id_column="fednum",
        name_column="name",
        resource="Federal Electoral Districts - Canada 2013",
        year=2013,
    ),
    "federal-2023-representation-order": RidingSource(
        path=Path("data/raw/boundaries/federal-2023/FED_CA_2023_EN-SHP.zip"),
        url=_FTP + "federal_electoral_districts_boundaries_2023/FED_CA_2023_EN-SHP.zip",
        id_column="FED_NUM",
        name_column="ED_NAMEE",
        resource="Federal Electoral Districts - Canada 2023",
        year=2023,
    ),
}


@dataclass(frozen=True)
class OntarioRule:
    """How one Ontario boundary set takes its Toronto ridings from a federal order."""

    federal_regime: str
    statute: str


ONTARIO_FROM_FEDERAL: dict[str, OntarioRule] = {
    "ontario-2007-107": OntarioRule(
        "federal-2003-representation-order", "Representation Act, 2005"
    ),
    "ontario-2018-124": OntarioRule(
        "federal-2013-representation-order", "Representation Act, 2015"
    ),
}


def name_key(name: object) -> str:
    """Compare riding names across sources that print dashes and accents differently."""

    text = _DASHES.sub(" ", str(name))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def download_riding_sources(
    *,
    sources: Mapping[str, RidingSource] | None = None,
    session: requests.Session | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """Download each boundary file to its path unless it is already there."""

    getter = session or requests
    written: list[Path] = []
    for source in (FEDERAL_RIDING_SOURCES if sources is None else sources).values():
        if source.path.is_file() and not overwrite:
            written.append(source.path)
            continue
        source.path.parent.mkdir(parents=True, exist_ok=True)
        with getter.get(source.url, stream=True, timeout=600) as response:
            response.raise_for_status()
            partial = source.path.with_suffix(source.path.suffix + ".part")
            with partial.open("wb") as handle:
                handle.writelines(response.iter_content(chunk_size=1 << 16))
            partial.replace(source.path)
        written.append(source.path)
    return written


def _read_ridings(source: RidingSource) -> pd.DataFrame:
    frame = gpd.read_file(f"zip://{source.path}")
    if frame.crs is None:
        raise ValueError(f"boundary file {source.path} has no declared CRS")
    frame = frame[[source.id_column, source.name_column, "geometry"]].rename(
        columns={source.id_column: "number", source.name_column: "name"}
    )
    frame["number"] = frame["number"].astype(int).astype(str)
    names = frame.groupby("number")["name"].nunique()
    if (names > 1).any():
        raise ValueError(f"boundary file {source.path} gives one district two names")
    dissolved = frame.dissolve(by="number", aggfunc="first", as_index=False).to_crs(TARGET_CRS)
    dissolved["geometry"] = [
        _valid_polygonal(geometry, label=f"{source.resource} district {number}")
        for number, geometry in zip(dissolved["number"], dissolved.geometry, strict=True)
    ]
    return dissolved


def add_riding_geometries(
    districts: gpd.GeoDataFrame, *, sources: Mapping[str, RidingSource] | None = None
) -> gpd.GeoDataFrame:
    """Attach federal and Ontario riding shapes to the districts they belong to."""

    configured = FEDERAL_RIDING_SOURCES if sources is None else sources
    required = {"represented_body", "boundary_regime", "official_district_id", "district_name"}
    if not required.issubset(districts.columns) or "geometry" not in districts.columns:
        return districts
    out = districts.copy()
    geometry = list(out.geometry)
    federal_shapes: dict[str, pd.DataFrame] = {}
    for regime, source in configured.items():
        rows = out.index[
            out["represented_body"].eq(_FEDERAL_BODY) & out["boundary_regime"].eq(regime)
        ]
        if not source.path.is_file():
            out.loc[rows, "geometry_missing_reason"] = "boundary_source_file_missing"
            continue
        ridings = _read_ridings(source)
        federal_shapes[regime] = ridings
        by_number = ridings.set_index("number")
        for index in rows:
            number = str(out.at[index, "official_district_id"])
            if number not in by_number.index:
                raise ValueError(f"{source.resource} has no district {number}")
            if name_key(by_number.at[number, "name"]) != name_key(out.at[index, "district_name"]):
                raise ValueError(
                    f"{source.resource} district {number} is {by_number.at[number, 'name']!r}, "
                    f"not {out.at[index, 'district_name']!r}"
                )
            _attach(out, geometry, index, by_number.at[number, "geometry"], source)

    for regime, rule in ONTARIO_FROM_FEDERAL.items():
        rows = out.index[
            out["represented_body"].eq(_ONTARIO_BODY) & out["boundary_regime"].eq(regime)
        ]
        ridings = federal_shapes.get(rule.federal_regime)
        if ridings is None:
            out.loc[rows, "geometry_missing_reason"] = "boundary_source_file_missing"
            continue
        ontario = ridings.loc[ridings["number"].str.startswith("35")]
        by_name: dict[str, list[str]] = {}
        for number, name in zip(ontario["number"], ontario["name"], strict=True):
            by_name.setdefault(name_key(name), []).append(number)
        by_number = ontario.set_index("number")
        source = configured[rule.federal_regime]
        for index in rows:
            matches = by_name.get(name_key(out.at[index, "district_name"]), [])
            if len(matches) != 1:
                raise ValueError(
                    f"{regime} {out.at[index, 'district_name']} matches federal districts {matches}"
                )
            number = matches[0]
            _attach(out, geometry, index, by_number.at[number, "geometry"], source)
            out.at[index, "geometry_derivation"] = f"same_as_federal_district_{number}"
            out.at[index, "geometry_membership_source_authority"] = (
                "Legislative Assembly of Ontario"
            )
            out.at[index, "geometry_membership_source_resource"] = rule.statute

    out["geometry"] = gpd.GeoSeries(geometry, index=out.index, crs=TARGET_CRS)
    return gpd.GeoDataFrame(out, geometry="geometry", crs=TARGET_CRS)


def _attach(
    out: pd.DataFrame,
    geometry: list[object],
    index: object,
    shape: shapely.Geometry,
    source: RidingSource,
) -> None:
    geometry[out.index.get_loc(index)] = shape
    out.at[index, "geometry_status"] = "available"
    out.at[index, "geometry_missing_reason"] = pd.NA
    out.at[index, "geometry_source_authority"] = ELECTIONS_CANADA
    out.at[index, "geometry_source_resource"] = source.resource
    out.at[index, "geometry_source_detail"] = source.url
    out.at[index, "geometry_source_year"] = source.year
