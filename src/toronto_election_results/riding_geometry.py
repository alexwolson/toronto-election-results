"""Federal and Ontario riding shapes from the authorities' boundary files.

Each boundary set the release uses is read from one file, its Toronto districts are matched by
district number and checked by name, and their shapes are attached in EPSG:4326.

- Federal 2003, 2013 and 2023 orders: Elections Canada's boundary files, under the Open
  Government Licence – Canada.
- Federal 1996 order: Statistics Canada's 2001 Census cartographic boundary file, saved from its
  page by hand because the page puts a bot check in front of the download. Its names are
  bilingual and later than the 1997 election in one case: Broadview—Greenwood, renamed
  Toronto—Danforth in 2000.
- Ontario 2018 set (the 2018 and 2022 elections): Elections Ontario's own file, saved from its
  page by hand under Elections Ontario's open licence.

Ontario's 1999 and 2007 sets have no file of their own. Within Toronto they are the federal
ridings of the 1996 and 2003 orders, which the Representation Acts of 1996 and 2005 adopted for
southern Ontario, so each Ontario riding takes the shape of its federal namesake, matched by name
because Ontario numbers its ridings differently. The build fails if a riding has no match or more
than one.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
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
    authority: str = ELECTIONS_CANADA
    # The layer inside the ZIP, where the ZIP holds more than one.
    member: str | None = None
    # Districts whose name in the release, the name at the election, differs from the name the
    # file prints because the district was renamed later: number -> release name -> file name.
    renamed: Mapping[str, tuple[str, str]] = field(default_factory=dict)
    # A file that is saved from its page by hand rather than fetched by script.
    downloaded_by_hand: bool = False
    represented_body: str = "canada_house_of_commons"


RIDING_SOURCES: dict[str, RidingSource] = {
    # Statistics Canada's 2001 Census cartographic boundary file holds the 1996 order (and the
    # 2003 order, which the release takes from Elections Canada). Its download page puts a bot
    # check in front of the file, so it is saved from the page by hand.
    "federal-1996-representation-order": RidingSource(
        path=Path("data/raw/boundaries/federal-1996/gfed000b01m_e.zip"),
        url=(
            "https://www12.statcan.gc.ca/census-recensement/2011/geo/bound-limit/"
            "bound-limit-2001-eng.cfm"
        ),
        id_column="FEDUID",
        name_column="FEDNAME",
        resource=(
            "2001 Census Cartographic Boundary File, Federal Electoral Districts "
            "(1996 Representation Order)"
        ),
        year=1996,
        authority="Statistics Canada",
        member="gfed000b02m_e/gfed000b02m_e.MIF",
        # Broadview—Greenwood became Toronto—Danforth in 2000, after the 1997 election.
        renamed={"35008": ("Broadview—Greenwood", "Toronto - Danforth")},
        downloaded_by_hand=True,
    ),
    # Elections Ontario's own file for the ridings of the 2018 and 2022 elections, under its Open
    # Use Data Product Licence, which Alex accepted when he saved it from the page.
    "ontario-2018-124": RidingSource(
        path=Path(
            "data/raw/boundaries/ontario-2022/Electoral District Shapefile - 2022 General Election.zip"
        ),
        url=(
            "https://www.elections.on.ca/content/dam/NGW/sitecontent/2017/preo/shapefiles/"
            "Electoral%20District%20Shapefile%20-%202022%20General%20Election.zip"
        ),
        id_column="ED_ID",
        name_column="ENGLISH_NA",
        resource="Electoral District Shapefile - 2022 General Election",
        year=2018,
        authority="Elections Ontario",
        member="Electoral District Shapefile - 2022 General Election/ELECTORAL_DISTRICT.shp",
        downloaded_by_hand=True,
        represented_body="ontario_legislative_assembly",
    ),
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
    "ontario-1999-103": OntarioRule(
        "federal-1996-representation-order", "Representation Act, 1996"
    ),
    "ontario-2007-107": OntarioRule(
        "federal-2003-representation-order", "Representation Act, 2005"
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
    for source in (RIDING_SOURCES if sources is None else sources).values():
        if source.downloaded_by_hand:
            continue
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
    location = f"zip://{source.path}" + (f"!{source.member}" if source.member else "")
    frame = gpd.read_file(location)
    if frame.crs is None:
        raise ValueError(f"boundary file {source.path} has no declared CRS")
    frame = frame[[source.id_column, source.name_column, "geometry"]].rename(
        columns={source.id_column: "number", source.name_column: "name"}
    )
    frame["number"] = frame["number"].astype(int).astype(str)
    # Statistics Canada prints bilingual names, "English / French"; keep the English one.
    frame["name"] = frame["name"].astype(str).str.split(" / ").str[0]
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

    configured = RIDING_SOURCES if sources is None else sources
    required = {"represented_body", "boundary_regime", "official_district_id", "district_name"}
    if not required.issubset(districts.columns) or "geometry" not in districts.columns:
        return districts
    out = districts.copy()
    geometry = list(out.geometry)
    federal_shapes: dict[str, pd.DataFrame] = {}
    for regime, source in configured.items():
        rows = out.index[
            out["represented_body"].eq(source.represented_body) & out["boundary_regime"].eq(regime)
        ]
        if not source.path.is_file():
            out.loc[rows, "geometry_missing_reason"] = "boundary_source_file_missing"
            continue
        ridings = _read_ridings(source)
        federal_shapes[regime] = ridings
        by_number = ridings.set_index("number")
        for index in rows:
            number = str(int(out.at[index, "official_district_id"]))
            if number not in by_number.index:
                raise ValueError(f"{source.resource} has no district {number}")
            expected = str(out.at[index, "district_name"])
            printed = str(by_number.at[number, "name"])
            if number in source.renamed:
                if source.renamed[number] != (expected, printed):
                    raise ValueError(f"{source.resource} rename of district {number} has changed")
            elif name_key(printed) != name_key(expected):
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
    out.at[index, "geometry_source_authority"] = source.authority
    out.at[index, "geometry_source_resource"] = source.resource
    out.at[index, "geometry_source_detail"] = source.url
    out.at[index, "geometry_source_year"] = source.year
