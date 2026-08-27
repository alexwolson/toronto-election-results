"""Contest-level native electoral-district geometry enrichment."""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

from toronto_election_results.district_geometry import (
    DEFAULT_COUNCIL_GEOMETRY_SOURCES,
    CouncilGeometrySource,
    enrich_district_geometries,
)

FIXTURES = Path(__file__).parent / "fixtures" / "geo"


def _districts() -> pd.DataFrame:
    rows = []
    for regime in ("toronto_council_44_wards", "toronto_council_25_wards"):
        for official_id, name in (
            ("city", "City of Toronto"),
            ("ward-5", "Ward 5"),
            ("ward-6", "Ward 6"),
        ):
            rows.append(
                {
                    "district_id": f"{regime}-{official_id}",
                    "represented_body": "toronto_city_council",
                    "boundary_regime": regime,
                    "official_district_id": official_id,
                    "district_name": name,
                    "geometry_status": "not_acquired",
                    "geometry_missing_reason": "official_contest_geometry_not_acquired",
                    "geometry_crs": "EPSG:4326",
                    "geometry": None,
                }
            )
    rows.extend(
        [
            {
                "district_id": "tdsb-ward-5",
                "represented_body": "toronto_district_school_board",
                "boundary_regime": "tdsb_2022",
                "official_district_id": "ward-5",
                "district_name": "Ward 5",
            },
            {
                "district_id": "federal-35001",
                "represented_body": "canada_house_of_commons",
                "boundary_regime": "federal_2023_order",
                "official_district_id": "35001",
                "district_name": "Ajax",
            },
            {
                "district_id": "ontario-35001",
                "represented_body": "ontario_legislative_assembly",
                "boundary_regime": "ontario_2015_order",
                "official_district_id": "35001",
                "district_name": "Ajax",
            },
        ]
    )
    return pd.DataFrame(rows)


def _fixture_sources() -> dict[str, CouncilGeometrySource]:
    source = CouncilGeometrySource(
        path=FIXTURES / "subdivisions-2022-sample.geojson",
        area_code_column="AREA_LONG_CODE",
        source_year=2022,
        expected_ward_count=3,
    )
    return {
        "toronto_council_44_wards": source,
        "toronto_council_25_wards": source,
    }


def test_enriches_native_council_ward_and_city_districts_without_poll_rows():
    enriched = enrich_district_geometries(_districts(), sources=_fixture_sources())

    assert isinstance(enriched, gpd.GeoDataFrame)
    assert enriched.crs.to_epsg() == 4326
    assert len(enriched) == len(_districts())
    assert set(enriched["district_id"]) == set(_districts()["district_id"])

    council = enriched[enriched["represented_body"] == "toronto_city_council"]
    assert council["geometry_status"].eq("available").all()
    assert council["geometry_missing_reason"].isna().all()
    assert council.geometry.notna().all()
    assert council.geometry.is_valid.all()
    assert set(council.geom_type).issubset({"Polygon", "MultiPolygon"})

    # The published table retains only one row per electoral district.  Source
    # subdivision identifiers never leak into the output.
    assert "area_code" not in enriched
    assert "subdivision_id" not in enriched
    assert "ward_number" not in enriched

    for regime in ("toronto_council_44_wards", "toronto_council_25_wards"):
        regime_rows = council[council["boundary_regime"] == regime]
        city = regime_rows.loc[regime_rows["official_district_id"] == "city", "geometry"].item()
        wards = regime_rows.loc[regime_rows["official_district_id"] != "city", "geometry"]
        assert all(city.covers(ward) for ward in wards)


def test_leaves_school_board_federal_and_provincial_geometry_explicitly_missing():
    enriched = enrich_district_geometries(_districts(), sources=_fixture_sources())
    unsupported = enriched[enriched["represented_body"] != "toronto_city_council"]

    assert unsupported.geometry.isna().all()
    assert unsupported["geometry_status"].eq("not_acquired").all()
    reasons = dict(zip(unsupported["represented_body"], unsupported["geometry_missing_reason"]))
    assert reasons == {
        "toronto_district_school_board": "school_board_district_geometry_not_acquired",
        "canada_house_of_commons": "federal_district_geometry_not_acquired",
        "ontario_legislative_assembly": "provincial_district_geometry_not_acquired",
    }


def test_derives_current_trustee_geometry_from_verified_city_ward_membership():
    districts = pd.concat(
        [
            _districts(),
            pd.DataFrame(
                [
                    {
                        "district_id": "tdsb-2026-1",
                        "represented_body": "toronto_district_school_board",
                        "boundary_regime": "tdsb-trustee-wards-2026",
                        "official_district_id": "1",
                        "district_name": "Ward 1",
                    },
                    {
                        "district_id": "tdsb-2026-2",
                        "represented_body": "toronto_district_school_board",
                        "boundary_regime": "tdsb-trustee-wards-2026",
                        "official_district_id": "2",
                        "district_name": "Ward 2",
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    crosswalk = pd.DataFrame(
        [
            {
                "board_id": "tdsb",
                "represented_body": "toronto_district_school_board",
                "boundary_regime": "tdsb-trustee-wards-2026",
                "ward_id": 1,
                "city_wards": (5, 6),
                "source_authority": "City of Toronto",
                "source_url": "https://example.com/2026-trustees",
                "source_date": "2026-04-23",
            },
            {
                "board_id": "tdsb",
                "represented_body": "toronto_district_school_board",
                "boundary_regime": "tdsb-trustee-wards-2026",
                "ward_id": 2,
                "city_wards": (11,),
                "source_authority": "City of Toronto",
                "source_url": "https://example.com/2026-trustees",
                "source_date": "2026-04-23",
            },
        ]
    )

    enriched = enrich_district_geometries(
        districts, sources=_fixture_sources(), trustee_crosswalks=crosswalk
    )
    trustees = enriched[enriched["boundary_regime"] == "tdsb-trustee-wards-2026"]
    city = enriched[
        (enriched["boundary_regime"] == "toronto_council_25_wards")
        & (enriched["official_district_id"] == "city")
    ].geometry.item()

    assert len(trustees) == 2
    assert trustees["geometry_status"].eq("available").all()
    assert trustees.geometry.is_valid.all()
    assert shapely.union_all(trustees.geometry).equals(city)
    assert trustees["geometry_derivation"].eq("union_of_city_wards").all()
    assert trustees["geometry_membership_source_authority"].eq("City of Toronto").all()
    assert trustees["geometry_membership_source_date"].eq("2026-04-23").all()


def test_missing_source_file_is_reported_without_excluding_the_district(tmp_path: Path):
    districts = _districts().iloc[[1]].copy()
    source = CouncilGeometrySource(
        path=tmp_path / "absent.geojson",
        area_code_column="AREA_LONG_CODE",
        source_year=2014,
        expected_ward_count=44,
    )

    enriched = enrich_district_geometries(districts, sources={"toronto_council_44_wards": source})

    assert len(enriched) == 1
    assert enriched.geometry.isna().all()
    assert enriched["geometry_status"].item() == "not_acquired"
    assert enriched["geometry_missing_reason"].item() == "boundary_source_file_missing"


def test_result_round_trips_as_geoparquet(tmp_path: Path):
    enriched = enrich_district_geometries(_districts(), sources=_fixture_sources())
    path = tmp_path / "electoral_districts.parquet"

    enriched.to_parquet(path, index=False)
    restored = gpd.read_parquet(path)

    assert restored.crs.to_epsg() == 4326
    assert restored.geometry.isna().sum() == 3
    assert restored.loc[restored.geometry.notna()].geometry.is_valid.all()


def test_default_sources_use_one_native_as_run_snapshot_per_council_regime():
    assert DEFAULT_COUNCIL_GEOMETRY_SOURCES["toronto_council_44_wards"].source_year == 2014
    assert DEFAULT_COUNCIL_GEOMETRY_SOURCES["toronto_council_25_wards"].source_year == 2022
