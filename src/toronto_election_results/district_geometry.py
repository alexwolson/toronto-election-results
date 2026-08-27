"""Optional native electoral-district geometry for the relational release.

The City subdivision files are an acquisition format, not a published result grain.
This module dissolves one complete subdivision snapshot for each stable council ward
regime and joins only the resulting ward/city polygons to ``electoral_districts``.
Other electoral geography families remain explicit nulls until their authoritative
boundaries are acquired.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

TARGET_CRS = "EPSG:4326"
COUNCIL_BODY = "toronto_city_council"


@dataclass(frozen=True)
class CouncilGeometrySource:
    """One official City subdivision snapshot for a stable council boundary regime."""

    path: str | Path
    area_code_column: str
    source_year: int
    expected_ward_count: int | None = None


# The ward regimes are stable within each era.  Use the last general-election
# snapshot in each regime, rather than mixing subdivision vintages across contests.
DEFAULT_COUNCIL_GEOMETRY_SOURCES: dict[str, CouncilGeometrySource] = {
    "toronto_council_44_wards": CouncilGeometrySource(
        path=Path("data/raw/subdivisions/voting-subdivisions-2014-4326.geojson"),
        area_code_column="AREA_LONG_CODE",
        source_year=2014,
        expected_ward_count=44,
    ),
    "toronto_council_25_wards": CouncilGeometrySource(
        path=Path("data/raw/subdivisions/voting-subdivisions-2022-4326.geojson"),
        area_code_column="AREA_LONG_CODE",
        source_year=2022,
        expected_ward_count=25,
    ),
}

_REQUIRED_DISTRICT_COLUMNS = {
    "district_id",
    "represented_body",
    "boundary_regime",
    "official_district_id",
}

_SCHOOL_BOARD_BODIES = {
    "toronto_district_school_board",
    "toronto_catholic_district_school_board",
    "conseil_scolaire_viamonde",
    "conseil_scolaire_catholique_monavenir",
}

_MISSING_REASON_BY_BODY = {
    "canada_house_of_commons": "federal_district_geometry_not_acquired",
    "ontario_legislative_assembly": "provincial_district_geometry_not_acquired",
}


def _missing_reason(body: object) -> str:
    body_name = str(body)
    if body_name in _SCHOOL_BOARD_BODIES:
        return "school_board_district_geometry_not_acquired"
    return _MISSING_REASON_BY_BODY.get(
        body_name, "district_geometry_not_acquired_for_represented_body"
    )


def _ward_number(area_code: object) -> int:
    """Extract the two-digit ward prefix from a City five-digit area code."""

    if area_code is None or pd.isna(area_code):
        raise ValueError("subdivision area code cannot be null")
    text = str(area_code).strip()
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    if not text.isdecimal() or len(text) > 5:
        raise ValueError(f"invalid subdivision area code: {area_code!r}")
    text = text.zfill(5)
    ward = int(text[:2])
    if ward < 1:
        raise ValueError(f"invalid ward prefix in subdivision area code: {area_code!r}")
    return ward


def _polygon_parts(geometry: BaseGeometry):
    if isinstance(geometry, Polygon):
        yield geometry
        return
    if isinstance(geometry, MultiPolygon):
        yield from geometry.geoms
        return
    if hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _polygon_parts(part)


def _valid_polygonal(geometry: BaseGeometry, *, label: str) -> Polygon | MultiPolygon:
    if geometry is None or geometry.is_empty:
        raise ValueError(f"{label} has empty geometry")
    repaired = shapely.make_valid(geometry)
    polygons = list(_polygon_parts(repaired))
    if not polygons:
        raise ValueError(f"{label} contains no polygonal geometry")
    merged = shapely.union_all(polygons)
    merged = shapely.make_valid(merged)
    if not isinstance(merged, (Polygon, MultiPolygon)) or merged.is_empty or not merged.is_valid:
        raise ValueError(f"{label} could not be converted to a valid Polygon/MultiPolygon")
    return merged


def _load_council_polygons(
    source: CouncilGeometrySource,
) -> tuple[dict[int, Polygon | MultiPolygon], Polygon | MultiPolygon]:
    raw = gpd.read_file(source.path)
    if source.area_code_column not in raw:
        raise ValueError(f"boundary source {source.path!s} is missing {source.area_code_column!r}")
    if raw.crs is None:
        raise ValueError(f"boundary source {source.path!s} has no declared CRS")
    if raw.geometry.isna().any():
        raise ValueError(f"boundary source {source.path!s} contains null geometry")

    subdivisions = raw[[source.area_code_column, "geometry"]].to_crs(TARGET_CRS).copy()
    subdivisions["ward_number"] = subdivisions[source.area_code_column].map(_ward_number)
    subdivisions["geometry"] = [
        _valid_polygonal(geometry, label=f"subdivision {area_code}")
        for area_code, geometry in zip(
            subdivisions[source.area_code_column], subdivisions.geometry, strict=True
        )
    ]
    subdivisions = gpd.GeoDataFrame(subdivisions, geometry="geometry", crs=TARGET_CRS)

    dissolved = subdivisions[["ward_number", "geometry"]].dissolve(by="ward_number", as_index=False)
    dissolved["geometry"] = [
        _valid_polygonal(geometry, label=f"ward {ward}")
        for ward, geometry in zip(dissolved["ward_number"], dissolved.geometry, strict=True)
    ]
    if source.expected_ward_count is not None and len(dissolved) != source.expected_ward_count:
        raise ValueError(
            f"boundary source {source.path!s} contains {len(dissolved)} wards; "
            f"expected {source.expected_ward_count}"
        )

    wards = dict(zip(dissolved["ward_number"], dissolved.geometry, strict=True))
    city = _valid_polygonal(
        shapely.union_all(list(wards.values())), label=f"City union from {source.source_year}"
    )
    return wards, city


def enrich_district_geometries(
    electoral_districts: pd.DataFrame,
    *,
    sources: Mapping[str, CouncilGeometrySource] | None = None,
    trustee_crosswalks: pd.DataFrame | None = None,
) -> gpd.GeoDataFrame:
    """Return ``electoral_districts`` with optional native contest-level geometry.

    The input is normally ``ReleaseTables.electoral_districts``.  Row identity and
    ordering are preserved, and the result is always a GeoDataFrame in EPSG:4326.
    A missing optional source file or unsupported geography family produces a null
    geometry with an explicit status; malformed source data raises instead of being
    silently published.
    """

    missing = sorted(_REQUIRED_DISTRICT_COLUMNS - set(electoral_districts.columns))
    if missing:
        raise ValueError("electoral_districts is missing required columns: " + ", ".join(missing))

    configured_sources = DEFAULT_COUNCIL_GEOMETRY_SOURCES if sources is None else sources
    out = pd.DataFrame(electoral_districts.copy()).reset_index(drop=True)
    geometry_values: list[BaseGeometry | None] = [None] * len(out)

    out["geometry_status"] = pd.Series("not_acquired", index=out.index, dtype="string")
    out["geometry_missing_reason"] = pd.Series(
        [_missing_reason(body) for body in out["represented_body"]], dtype="string"
    )
    out["geometry_crs"] = TARGET_CRS
    out["geometry_source_authority"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out["geometry_source_resource"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out["geometry_source_detail"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out["geometry_source_year"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
    out["geometry_derivation"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out["geometry_membership_source_authority"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out["geometry_membership_source_resource"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out["geometry_membership_source_date"] = pd.Series(pd.NA, index=out.index, dtype="string")

    council = out["represented_body"].eq(COUNCIL_BODY)
    current_wards: dict[int, Polygon | MultiPolygon] | None = None
    current_city: Polygon | MultiPolygon | None = None
    current_source: CouncilGeometrySource | None = None
    for regime, indexes in out.loc[council].groupby("boundary_regime", sort=False).groups.items():
        source = configured_sources.get(str(regime))
        if source is None:
            out.loc[indexes, "geometry_missing_reason"] = "council_boundary_regime_not_supported"
            continue

        out.loc[indexes, "geometry_source_authority"] = "City of Toronto"
        out.loc[indexes, "geometry_source_resource"] = "Elections — Voting Subdivisions"
        out.loc[indexes, "geometry_source_detail"] = str(source.path)
        out.loc[indexes, "geometry_source_year"] = source.source_year

        source_path = Path(source.path)
        if not source_path.is_file():
            out.loc[indexes, "geometry_missing_reason"] = "boundary_source_file_missing"
            continue

        wards, city = _load_council_polygons(source)
        if regime == "toronto_council_25_wards":
            current_wards = wards
            current_city = city
            current_source = source
        for index in indexes:
            official_id = str(out.at[index, "official_district_id"])
            geometry: BaseGeometry | None
            if official_id == "city":
                geometry = city
            else:
                match = re.fullmatch(r"ward-(\d+)", official_id)
                geometry = wards.get(int(match.group(1))) if match else None
            if geometry is None:
                out.at[index, "geometry_missing_reason"] = "district_not_present_in_boundary_source"
                continue
            geometry_values[index] = geometry
            out.at[index, "geometry_status"] = "available"
            out.at[index, "geometry_missing_reason"] = pd.NA

    if trustee_crosswalks is not None and not trustee_crosswalks.empty:
        current_crosswalks = trustee_crosswalks[
            trustee_crosswalks["boundary_regime"].astype(str).str.endswith("-2026")
        ]
        crosswalk_by_key = {
            (str(row.represented_body), str(row.boundary_regime), str(row.ward_id)): row
            for row in current_crosswalks.itertuples(index=False)
        }
        current_trustees = out["represented_body"].isin(_SCHOOL_BOARD_BODIES) & out[
            "boundary_regime"
        ].astype(str).str.endswith("-2026")
        if current_wards is None or current_city is None or current_source is None:
            out.loc[current_trustees, "geometry_missing_reason"] = (
                "current_city_ward_geometry_unavailable"
            )
        else:
            board_geometries: dict[str, list[Polygon | MultiPolygon]] = {}
            for index in out.index[current_trustees]:
                key = (
                    str(out.at[index, "represented_body"]),
                    str(out.at[index, "boundary_regime"]),
                    str(out.at[index, "official_district_id"]),
                )
                crosswalk = crosswalk_by_key.get(key)
                if crosswalk is None:
                    out.at[index, "geometry_missing_reason"] = "trustee_crosswalk_missing"
                    continue
                parts = [current_wards.get(int(ward)) for ward in crosswalk.city_wards]
                if any(part is None for part in parts):
                    out.at[index, "geometry_missing_reason"] = "component_city_ward_missing"
                    continue
                geometry = _valid_polygonal(
                    shapely.union_all(parts),
                    label=f"{crosswalk.board_id} trustee ward {crosswalk.ward_id}",
                )
                geometry_values[index] = geometry
                board_geometries.setdefault(str(crosswalk.board_id), []).append(geometry)
                out.at[index, "geometry_status"] = "available"
                out.at[index, "geometry_missing_reason"] = pd.NA
                out.at[index, "geometry_source_authority"] = "City of Toronto"
                out.at[index, "geometry_source_resource"] = "Elections — Voting Subdivisions"
                out.at[index, "geometry_source_detail"] = str(current_source.path)
                out.at[index, "geometry_source_year"] = current_source.source_year
                out.at[index, "geometry_derivation"] = "union_of_city_wards"
                out.at[index, "geometry_membership_source_authority"] = crosswalk.source_authority
                out.at[index, "geometry_membership_source_resource"] = crosswalk.source_url
                out.at[index, "geometry_membership_source_date"] = crosswalk.source_date

            for board_id, geometries in board_geometries.items():
                union = _valid_polygonal(
                    shapely.union_all(geometries), label=f"{board_id} trustee district union"
                )
                if not union.equals(current_city):
                    raise ValueError(f"{board_id} trustee districts do not partition Toronto")

    out["geometry"] = gpd.GeoSeries(geometry_values, index=out.index, crs=TARGET_CRS)
    return gpd.GeoDataFrame(out, geometry="geometry", crs=TARGET_CRS)
