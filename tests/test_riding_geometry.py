"""Federal and Ontario riding shapes from Elections Canada's boundary files (`riding_geometry`)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from toronto_election_results.riding_geometry import (
    OntarioRule,
    RidingSource,
    add_riding_geometries,
    name_key,
)

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"


def _boundary_zip(tmp_path: Path) -> Path:
    # Two Toronto ridings in a projected CRS, one drawn as two parts that the reader dissolves.
    ridings = gpd.GeoDataFrame(
        {
            "fednum": [35005, 35005, 35015],
            "name": ["Beaches--East York", "Beaches--East York", "Davenport"],
        },
        geometry=[
            box(7210000, 920000, 7215000, 925000),
            box(7215000, 920000, 7216000, 925000),
            box(7200000, 920000, 7205000, 925000),
        ],
        crs="EPSG:3978",
    )
    folder = tmp_path / "ridings"
    folder.mkdir()
    ridings.to_file(folder / "ridings.shp")
    archive = tmp_path / "ridings.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for path in folder.iterdir():
            handle.write(path, path.name)
    return archive


def _source(path: Path) -> dict[str, RidingSource]:
    return {
        "federal-2003-representation-order": RidingSource(
            path=path,
            url="https://example.org/ridings.zip",
            id_column="fednum",
            name_column="name",
            resource="Federal Electoral Districts - Canada 2003",
            year=2003,
        )
    }


def _districts(rows: list[tuple[str, str, str, str]]) -> gpd.GeoDataFrame:
    frame = pd.DataFrame(
        rows,
        columns=["represented_body", "boundary_regime", "official_district_id", "district_name"],
    )
    for column in (
        "geometry_status",
        "geometry_missing_reason",
        "geometry_source_authority",
        "geometry_source_resource",
        "geometry_source_detail",
        "geometry_derivation",
        "geometry_membership_source_authority",
        "geometry_membership_source_resource",
    ):
        frame[column] = pd.Series(pd.NA, index=frame.index, dtype="string")
    frame["geometry_status"] = "not_acquired"
    frame["geometry_source_year"] = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    return gpd.GeoDataFrame(frame, geometry=[None] * len(frame), crs="EPSG:4326")


FEDERAL = "canada_house_of_commons"
ONTARIO = "ontario_legislative_assembly"


def test_name_key_ignores_dashes_and_accents():
    assert name_key("Beaches—East York") == name_key("Beaches--East York")
    assert name_key("Montréal") == name_key("Montreal")


def test_federal_and_ontario_ridings_take_the_federal_shapes(tmp_path, monkeypatch):
    archive = _boundary_zip(tmp_path)
    monkeypatch.setattr(
        "toronto_election_results.riding_geometry.ONTARIO_FROM_FEDERAL",
        {
            "ontario-2007-107": OntarioRule(
                "federal-2003-representation-order", "Representation Act, 2005", True
            )
        },
    )
    districts = _districts(
        [
            (FEDERAL, "federal-2003-representation-order", "35005", "Beaches—East York"),
            (FEDERAL, "federal-2003-representation-order", "35015", "Davenport"),
            (ONTARIO, "ontario-2007-107", "005", "Beaches—East York"),
        ]
    )
    out = add_riding_geometries(districts, sources=_source(archive))

    assert out["geometry_status"].eq("available").all()
    assert out.crs.to_epsg() == 4326
    federal, _, ontario = out.geometry
    assert federal.equals(ontario)
    assert out["geometry_derivation"].iloc[2] == "same_as_federal_district_35005"
    assert out["geometry_membership_source_resource"].iloc[2] == "Representation Act, 2005"
    # The two parts of district 35005 are one shape.
    assert federal.geom_type == "Polygon"


def test_a_name_that_disagrees_with_the_number_fails(tmp_path):
    districts = _districts([(FEDERAL, "federal-2003-representation-order", "35005", "Davenport")])
    with pytest.raises(ValueError, match="not 'Davenport'"):
        add_riding_geometries(districts, sources=_source(_boundary_zip(tmp_path)))


def test_a_missing_file_leaves_the_ridings_without_shapes(tmp_path):
    districts = _districts(
        [(FEDERAL, "federal-2003-representation-order", "35005", "Beaches—East York")]
    )
    out = add_riding_geometries(districts, sources=_source(tmp_path / "absent.zip"))
    assert out["geometry_status"].iloc[0] == "not_acquired"
    assert out["geometry_missing_reason"].iloc[0] == "boundary_source_file_missing"


def test_published_ridings_and_trustee_wards_since_amalgamation_have_shapes():
    districts = pd.read_csv(OUT / "electoral_districts.csv", dtype=str, keep_default_na=False)
    mapped = districts.loc[
        districts["boundary_regime"].isin(
            [
                "federal-2003-representation-order",
                "federal-2013-representation-order",
                "federal-2023-representation-order",
                "ontario-2007-107",
                "ontario-2018-124",
            ]
        )
        | districts["boundary_regime"].str.contains(r"trustee-wards-(?:2000|2003|2022)$")
    ]
    assert len(mapped) > 0
    assert mapped["geometry_status"].eq("available").all()
