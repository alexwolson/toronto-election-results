from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.ward_geography import (
    CITY_WARD_REGIMES,
    build_ward_geography_catalogue,
    derive_trustee_ward_geography,
    enrich_electoral_districts,
    load_city_ward_geographic_names,
    load_trustee_ward_crosswalks,
)

REFERENCE = Path(__file__).parents[1] / "data" / "reference"


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_city_ward_geographic_names_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "city.csv",
        "boundary_regime,official_district_id,geographic_name,source_authority,source_url,source_date\n"
        "toronto_council_44_wards,19,Trinity-Spadina,City of Toronto,https://example.com/wards,2014-10-27\n"
        "toronto_council_44_wards,19,Trinity-Spadina,City of Toronto,https://example.com/wards,2014-10-27\n",
    )

    with pytest.raises(ValueError, match="repeats a boundary-regime/ward key"):
        load_city_ward_geographic_names(path)


def test_canonical_city_ward_catalogue_covers_both_complete_regimes() -> None:
    city = load_city_ward_geographic_names(REFERENCE / "city_ward_geographic_names.csv")

    assert len(city) == 69
    assert {
        regime: set(rows["official_district_id"])
        for regime, rows in city.groupby("boundary_regime")
    } == {regime: set(wards) for regime, wards in CITY_WARD_REGIMES.items()}
    old = city.set_index(["boundary_regime", "official_district_id"])
    assert old.loc[("toronto_council_44_wards", 19), "geographic_name"] == ("Trinity-Spadina")
    assert old.loc[("toronto_council_44_wards", 20), "geographic_name"] == ("Trinity-Spadina")


def test_generalized_crosswalk_reproduces_2026_trustee_labels() -> None:
    city = load_city_ward_geographic_names(REFERENCE / "city_ward_geographic_names.csv")
    crosswalk = load_trustee_ward_crosswalks(REFERENCE / "trustee_ward_crosswalks.csv", city)
    assert len(crosswalk) == 263
    current = crosswalk[crosswalk["boundary_regime"].str.endswith("-2026")]
    derived = derive_trustee_ward_geography(current, city).set_index(["board_id", "ward_id"])

    assert len(derived) == 29
    assert derived.loc[("tdsb", 10), "district_display_name"] == (
        "Ward 10 — Beaches-East York; Scarborough Southwest"
    )
    assert derived.loc[("viamonde", 3), "district_display_name"] == "Ward 3 — Centre"
    assert derived.loc[("monavenir", 3), "district_display_name"] == ("Ward 3 — Toronto Ouest")


def test_each_2026_board_partitions_all_25_city_wards_exactly_once() -> None:
    city = load_city_ward_geographic_names(REFERENCE / "city_ward_geographic_names.csv")
    crosswalk = load_trustee_ward_crosswalks(REFERENCE / "trustee_ward_crosswalks.csv", city)
    current = crosswalk[crosswalk["boundary_regime"].str.endswith("-2026")]

    expected_counts = {"tdsb": 12, "tcdsb": 12, "viamonde": 3, "monavenir": 2}
    for board_id, expected_count in expected_counts.items():
        board = current[current["board_id"] == board_id]
        component_wards = [ward for wards in board["city_wards"] for ward in wards]

        assert len(board) == expected_count
        assert len(component_wards) == len(set(component_wards))
        assert set(component_wards) == set(range(1, 26))
        assert board["source_authority"].eq("City of Toronto").all()
        assert board["source_url"].str.contains("2026-School-board-ward-reference-chart").all()
        assert board["source_date"].eq("2026-04-23").all()


def test_historical_crosswalk_covers_every_board_regime_and_city_ward() -> None:
    city = load_city_ward_geographic_names(REFERENCE / "city_ward_geographic_names.csv")
    crosswalk = load_trustee_ward_crosswalks(REFERENCE / "trustee_ward_crosswalks.csv", city)

    expected_counts = {
        (board, year): 12 if board == "tdsb" and year == 2026 else count
        for board, count in {"tdsb": 22, "tcdsb": 12, "viamonde": 3, "monavenir": 2}.items()
        for year in (2003, 2006, 2010, 2014, 2018, 2022, 2026)
    }
    actual_counts = {
        (row.board_id, int(row.boundary_regime.rsplit("-", 1)[1])): len(group)
        for (_, _), group in crosswalk.groupby(["board_id", "boundary_regime"])
        for row in [group.iloc[0]]
    }
    assert actual_counts == expected_counts

    for (_, regime), rows in crosswalk.groupby(["board_id", "boundary_regime"]):
        city_regime = rows["city_boundary_regime"].iloc[0]
        covered = {ward for wards in rows["city_wards"] for ward in wards}
        assert covered == set(CITY_WARD_REGIMES[city_regime]), regime


def test_catalogue_enriches_all_332_wards_without_replacing_district_name() -> None:
    city = load_city_ward_geographic_names(REFERENCE / "city_ward_geographic_names.csv")
    crosswalk = load_trustee_ward_crosswalks(REFERENCE / "trustee_ward_crosswalks.csv", city)
    catalogue = build_ward_geography_catalogue(city, crosswalk)
    districts = catalogue[["represented_body", "boundary_regime", "official_district_id"]].copy()
    districts["district_id"] = [f"dst_test_{index}" for index in range(len(districts))]
    districts["district_name"] = "source label"
    districts = pd.concat(
        [
            districts,
            pd.DataFrame(
                [
                    {
                        "represented_body": "toronto_city_council",
                        "boundary_regime": "toronto_council_25_wards",
                        "official_district_id": "citywide",
                        "district_id": "dst_mayor",
                        "district_name": "City of Toronto",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    enriched = enrich_electoral_districts(districts, city, crosswalk)
    ward = enriched.loc[
        enriched["represented_body"].eq("toronto_city_council")
        & enriched["boundary_regime"].eq("toronto_council_44_wards")
        & enriched["official_district_id"].eq("19")
    ].iloc[0]
    mayor = enriched.loc[enriched["district_id"].eq("dst_mayor")].iloc[0]

    assert len(catalogue) == 332
    assert ward["district_name"] == "source label"
    assert ward["district_display_name"] == "Ward 19 — Trinity-Spadina"
    assert pd.isna(mayor["district_display_name"])


def test_derive_trustee_geography_deduplicates_city_names_in_source_order(
    tmp_path: Path,
) -> None:
    city_path = _write(
        tmp_path / "city.csv",
        "boundary_regime,official_district_id,geographic_name,source_authority,source_url,source_date\n"
        "toronto_council_44_wards,19,Trinity-Spadina,City of Toronto,https://example.com/wards,2014-10-27\n"
        "toronto_council_44_wards,20,Trinity-Spadina,City of Toronto,https://example.com/wards,2014-10-27\n"
        "toronto_council_44_wards,21,St. Paul's,City of Toronto,https://example.com/wards,2014-10-27\n",
    )
    trustee_path = _write(
        tmp_path / "trustees.csv",
        "board_id,office_code,represented_body,display_name,short_name,boundary_regime,"
        "ward_id,official_geographic_name,city_boundary_regime,city_wards,source_authority,"
        "source_url,source_date\n"
        "tdsb,3,toronto_district_school_board,Toronto District School Board,TDSB,"
        "tdsb-trustee-wards-2014,10,,toronto_council_44_wards,19;20;21,City of Toronto,"
        "https://example.com/trustees,2014-10-27\n",
    )

    city = load_city_ward_geographic_names(city_path)
    crosswalk = load_trustee_ward_crosswalks(trustee_path, city)
    derived = derive_trustee_ward_geography(crosswalk, city)

    assert derived.loc[0, "geographic_name"] == "Trinity-Spadina; St. Paul's"
    assert derived.loc[0, "district_display_name"] == ("Ward 10 — Trinity-Spadina; St. Paul's")
    assert derived.loc[0, "name_provenance"] == "derived_from_city_wards"
    assert derived.loc[0, "city_wards"] == (19, 20, 21)


def test_official_trustee_name_takes_precedence_over_component_names(tmp_path: Path) -> None:
    city_path = _write(
        tmp_path / "city.csv",
        "boundary_regime,official_district_id,geographic_name,source_authority,source_url,source_date\n"
        "toronto_council_25_wards,10,Spadina-Fort York,City of Toronto,https://example.com/wards,2026-04-23\n"
        "toronto_council_25_wards,11,University-Rosedale,City of Toronto,https://example.com/wards,2026-04-23\n",
    )
    trustee_path = _write(
        tmp_path / "trustees.csv",
        "board_id,office_code,represented_body,display_name,short_name,boundary_regime,"
        "ward_id,official_geographic_name,city_boundary_regime,city_wards,source_authority,"
        "source_url,source_date\n"
        "viamonde,5,conseil_scolaire_viamonde,Conseil scolaire Viamonde,Viamonde,"
        "viamonde-trustee-wards-2026,3,Centre,toronto_council_25_wards,10;11,"
        "City of Toronto,https://example.com/trustees,2026-04-23\n",
    )

    city = load_city_ward_geographic_names(city_path)
    crosswalk = load_trustee_ward_crosswalks(trustee_path, city)
    derived = derive_trustee_ward_geography(crosswalk, city)

    assert derived.loc[0, "geographic_name"] == "Centre"
    assert derived.loc[0, "district_display_name"] == "Ward 3 — Centre"
    assert derived.loc[0, "name_provenance"] == "official"


def test_trustee_crosswalk_rejects_unknown_component_city_ward(tmp_path: Path) -> None:
    city_path = _write(
        tmp_path / "city.csv",
        "boundary_regime,official_district_id,geographic_name,source_authority,source_url,source_date\n"
        "toronto_council_25_wards,1,Etobicoke North,City of Toronto,https://example.com/wards,2026-04-23\n",
    )
    trustee_path = _write(
        tmp_path / "trustees.csv",
        "board_id,office_code,represented_body,display_name,short_name,boundary_regime,"
        "ward_id,official_geographic_name,city_boundary_regime,city_wards,source_authority,"
        "source_url,source_date\n"
        "tdsb,3,toronto_district_school_board,Toronto District School Board,TDSB,"
        "tdsb-trustee-wards-2026,1,,toronto_council_25_wards,1;7,City of Toronto,"
        "https://example.com/trustees,2026-04-23\n",
    )

    city = load_city_ward_geographic_names(city_path)
    with pytest.raises(ValueError, match="unknown City ward 7"):
        load_trustee_ward_crosswalks(trustee_path, city)


def test_trustee_crosswalk_rejects_duplicate_component_city_ward(tmp_path: Path) -> None:
    city_path = _write(
        tmp_path / "city.csv",
        "boundary_regime,official_district_id,geographic_name,source_authority,source_url,source_date\n"
        "toronto_council_25_wards,1,Etobicoke North,City of Toronto,https://example.com/wards,2026-04-23\n",
    )
    trustee_path = _write(
        tmp_path / "trustees.csv",
        "board_id,office_code,represented_body,display_name,short_name,boundary_regime,"
        "ward_id,official_geographic_name,city_boundary_regime,city_wards,source_authority,"
        "source_url,source_date\n"
        "tdsb,3,toronto_district_school_board,Toronto District School Board,TDSB,"
        "tdsb-trustee-wards-2026,1,,toronto_council_25_wards,1;1,City of Toronto,"
        "https://example.com/trustees,2026-04-23\n",
    )

    city = load_city_ward_geographic_names(city_path)
    with pytest.raises(ValueError, match="repeats a component City ward"):
        load_trustee_ward_crosswalks(trustee_path, city)
