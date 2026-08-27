"""Authoritative board and ward metadata for Toronto's 2026 trustee contests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .ward_geography import (
    derive_trustee_ward_geography,
    load_city_ward_geographic_names,
    load_trustee_ward_crosswalks,
)

TRUSTEE_CROSSWALK_FILENAME = "trustee_ward_crosswalks.csv"
CITY_WARD_NAMES_FILENAME = "city_ward_geographic_names.csv"
TRUSTEE_CROSSWALK_URL = (
    "https://www.toronto.ca/wp-content/uploads/2026/04/"
    "9600-2026-School-board-ward-reference-chart.pdf"
)

EXPECTED_WARDS = {
    "tdsb": tuple(range(1, 13)),
    "tcdsb": tuple(range(1, 13)),
    "viamonde": (2, 3, 4),
    "monavenir": (3, 4),
}

BOARD_METADATA = {
    "tdsb": {
        "office_code": 3,
        "represented_body": "toronto_district_school_board",
        "boundary_regime": "tdsb-trustee-wards-2026",
    },
    "tcdsb": {
        "office_code": 4,
        "represented_body": "toronto_catholic_district_school_board",
        "boundary_regime": "tcdsb-trustee-wards-2026",
    },
    "viamonde": {
        "office_code": 5,
        "represented_body": "conseil_scolaire_viamonde",
        "boundary_regime": "viamonde-trustee-wards-2026",
    },
    "monavenir": {
        "office_code": 6,
        "represented_body": "conseil_scolaire_catholique_monavenir",
        "boundary_regime": "monavenir-trustee-wards-2026",
    },
}

BOARD_ID_BY_OFFICE_CODE = {
    int(metadata["office_code"]): board_id for board_id, metadata in BOARD_METADATA.items()
}


def load_trustee_ward_crosswalk(path: str | Path) -> pd.DataFrame:
    """Load 2026 from the canonical all-election historical geography catalogue."""

    source = Path(path)
    city = load_city_ward_geographic_names(source.with_name(CITY_WARD_NAMES_FILENAME))
    all_years = load_trustee_ward_crosswalks(source, city)
    current = all_years.loc[all_years["boundary_regime"].str.endswith("-2026")].copy()
    current = derive_trustee_ward_geography(current, city)
    current["district_name"] = [
        (
            f"Ward {row.ward_id} — {row.official_geographic_name}"
            if row.official_geographic_name
            else f"Ward {row.ward_id}"
        )
        for row in current.itertuples(index=False)
    ]
    current["source_updated_date"] = current["source_date"]

    if len(current) != 29 or set(current["board_id"]) != set(EXPECTED_WARDS):
        raise ValueError("trustee crosswalk must contain the complete 2026 four-board field")
    for board_id, expected_wards in EXPECTED_WARDS.items():
        board = current.loc[current["board_id"].eq(board_id)].sort_values("ward_id")
        if tuple(int(value) for value in board["ward_id"]) != expected_wards:
            raise ValueError(f"trustee crosswalk {board_id} wards do not match 2026 regime")
    if not current["source_url"].eq(TRUSTEE_CROSSWALK_URL).all():
        raise ValueError("trustee crosswalk must cite the authoritative City reference chart")
    if not current["source_date"].eq("2026-04-23").all():
        raise ValueError("trustee crosswalk must use the chart updated 2026-04-23")

    columns = [
        "board_id",
        "office_code",
        "represented_body",
        "display_name",
        "short_name",
        "boundary_regime",
        "ward_id",
        "district_name",
        "district_display_name",
        "city_wards",
        "source_url",
        "source_updated_date",
    ]
    return (
        current[columns]
        .sort_values(["office_code", "ward_id"], kind="stable")
        .reset_index(drop=True)
    )
