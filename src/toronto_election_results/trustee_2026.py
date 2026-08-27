"""Authoritative board and ward metadata for Toronto's 2026 trustee contests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

TRUSTEE_CROSSWALK_FILENAME = "trustee_ward_crosswalk_2026.csv"
TRUSTEE_CROSSWALK_URL = (
    "https://www.toronto.ca/wp-content/uploads/2026/04/"
    "9600-2026-School-board-ward-reference-chart.pdf"
)

_COLUMNS = [
    "board_id",
    "office_code",
    "represented_body",
    "display_name",
    "short_name",
    "boundary_regime",
    "ward_id",
    "district_name",
    "city_wards",
    "source_url",
    "source_updated_date",
]

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
        "display_name": "Toronto District School Board",
        "short_name": "TDSB",
        "boundary_regime": "tdsb-trustee-wards-2026",
    },
    "tcdsb": {
        "office_code": 4,
        "represented_body": "toronto_catholic_district_school_board",
        "display_name": "Toronto Catholic District School Board",
        "short_name": "TCDSB",
        "boundary_regime": "tcdsb-trustee-wards-2026",
    },
    "viamonde": {
        "office_code": 5,
        "represented_body": "conseil_scolaire_viamonde",
        "display_name": "Conseil scolaire Viamonde",
        "short_name": "Viamonde",
        "boundary_regime": "viamonde-trustee-wards-2026",
    },
    "monavenir": {
        "office_code": 6,
        "represented_body": "conseil_scolaire_catholique_monavenir",
        "display_name": "Conseil scolaire catholique MonAvenir",
        "short_name": "MonAvenir",
        "boundary_regime": "monavenir-trustee-wards-2026",
    },
}

BOARD_ID_BY_OFFICE_CODE = {
    int(metadata["office_code"]): board_id for board_id, metadata in BOARD_METADATA.items()
}


def _city_wards(value: object) -> tuple[int, ...]:
    try:
        wards = tuple(int(part) for part in str(value).split(";") if part.strip())
    except ValueError as exc:
        raise ValueError(f"trustee crosswalk has invalid City wards: {value!r}") from exc
    if not wards or len(wards) != len(set(wards)) or any(ward < 1 or ward > 25 for ward in wards):
        raise ValueError(f"trustee crosswalk has invalid City wards: {value!r}")
    return wards


def load_trustee_ward_crosswalk(path: str | Path) -> pd.DataFrame:
    """Load and fail-closed validate the dated City school-board reference chart."""

    source = Path(path)
    frame = pd.read_csv(source, dtype="string", keep_default_na=False)
    if list(frame.columns) != _COLUMNS:
        raise ValueError("trustee crosswalk columns must be exactly: " + ", ".join(_COLUMNS))
    if frame.empty:
        raise ValueError("trustee crosswalk cannot be empty")

    for column in _COLUMNS:
        if frame[column].str.strip().eq("").any():
            raise ValueError(f"trustee crosswalk {column} cannot be blank")
    frame["office_code"] = pd.to_numeric(frame["office_code"], errors="raise").astype("Int64")
    frame["ward_id"] = pd.to_numeric(frame["ward_id"], errors="raise").astype("Int64")
    frame["city_wards"] = frame["city_wards"].map(_city_wards)

    if frame.duplicated(["board_id", "ward_id"]).any():
        raise ValueError("trustee crosswalk board/ward keys must be unique")
    if set(frame["board_id"]) != set(EXPECTED_WARDS):
        raise ValueError("trustee crosswalk must contain exactly the four expected boards")

    for board_id, expected_wards in EXPECTED_WARDS.items():
        board = frame.loc[frame["board_id"].eq(board_id)].sort_values("ward_id")
        if tuple(int(value) for value in board["ward_id"]) != expected_wards:
            raise ValueError(f"trustee crosswalk {board_id} wards do not match 2026 regime")
        metadata = BOARD_METADATA[board_id]
        for column, expected in metadata.items():
            if not board[column].eq(expected).all():
                raise ValueError(f"trustee crosswalk {board_id} has inconsistent {column}")

    if not frame["source_url"].eq(TRUSTEE_CROSSWALK_URL).all():
        raise ValueError("trustee crosswalk must cite the authoritative City reference chart")
    if not frame["source_updated_date"].eq("2026-04-23").all():
        raise ValueError("trustee crosswalk must use the chart updated 2026-04-23")

    return frame.sort_values(["office_code", "ward_id"], kind="stable").reset_index(drop=True)
