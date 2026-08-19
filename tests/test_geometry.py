"""Voting-subdivision boundary companion dataset."""

from pathlib import Path

from toronto_election_results.geometry import load_subdivisions, parse_area_code

FIXTURES = Path(__file__).parent / "fixtures" / "geo"


class TestParseAreaCode:
    def test_splits_ward_and_subdivision(self):
        assert parse_area_code("11055") == (11, 55)
        assert parse_area_code("05027") == (5, 27)

    def test_special_poll_code(self):
        assert parse_area_code("11097") == (11, 97)  # advance/mail special subdivision


def test_load_subdivisions_keys_and_crs():
    gdf = load_subdivisions(
        FIXTURES / "subdivisions-2022-sample.geojson", year=2022, code_col="AREA_LONG_CODE"
    )
    assert {"election_year", "ward_number", "subdivision_id", "geometry"}.issubset(gdf.columns)
    assert (gdf["election_year"] == 2022).all()
    assert gdf.crs.to_epsg() == 4326
    # first fixture feature is code 11055 -> ward 11, subdivision 55
    first = gdf[gdf["ward_number"] == 11].iloc[0]
    assert first["subdivision_id"] == 55
    assert not gdf.geometry.isna().any()
