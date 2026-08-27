"""Build the audited historical trustee-to-City-ward reference catalogue."""

from __future__ import annotations

import csv
from pathlib import Path

OUTPUT = Path("data/reference/trustee_ward_crosswalks.csv")

BOARDS = {
    "tdsb": ("3", "toronto_district_school_board", "Toronto District School Board", "TDSB"),
    "tcdsb": (
        "4",
        "toronto_catholic_district_school_board",
        "Toronto Catholic District School Board",
        "TCDSB",
    ),
    "viamonde": ("5", "conseil_scolaire_viamonde", "Conseil scolaire Viamonde", "Viamonde"),
    "monavenir": (
        "6",
        "conseil_scolaire_catholique_monavenir",
        "Conseil scolaire catholique MonAvenir",
        "MonAvenir",
    ),
}

SOURCES = {
    2003: (
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/1ed53c9d-a316-465e-96ce-e72be74f8aa9/download/2003-results.zip",
        "2003-11-10",
    ),
    2006: (
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/3fb1227c-a279-4523-a1aa-f00190ba717f/download/2006-results.zip",
        "2006-11-13",
    ),
    2010: (
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/6fbfaab0-bb84-442a-8e4b-1c14d4c10d6d/download/2010-results.zip",
        "2010-10-25",
    ),
    2014: (
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/96d35404-44d9-49d8-95bb-fb1e5489240d/resource/d59b5a52-33c3-4380-a136-82707e4d9aae/download/2014-results.zip",
        "2014-10-27",
    ),
    2018: (
        "https://www.toronto.ca/wp-content/uploads/2020/05/991f-Grade-10-Teacher-Guide-2020.pdf",
        "2020-05-01",
    ),
    2022: (
        "https://www.toronto.ca/wp-content/uploads/2022/04/8ef1-2022-School-Board-Ward-Reference-Chart.pdf",
        "2022-04-05",
    ),
    2026: (
        "https://www.toronto.ca/wp-content/uploads/2026/04/9600-2026-School-board-ward-reference-chart.pdf",
        "2026-04-23",
    ),
}

TDSB_22 = {ward: (ward * 2 - 1, ward * 2) for ward in range(1, 23)}
TDSB_25 = {
    1: (1,),
    2: (2,),
    3: (3,),
    4: (7,),
    5: (6,),
    6: (5,),
    7: (4,),
    8: (8, 12),
    9: (9, 10),
    10: (11, 13),
    11: (15,),
    12: (18,),
    13: (17,),
    14: (16,),
    15: (14,),
    16: (19,),
    17: (21,),
    18: (20,),
    19: (24,),
    20: (22,),
    21: (23,),
    22: (25,),
}
TDSB_2026 = {
    1: (1, 7),
    2: (2, 3),
    3: (4, 9),
    4: (6, 18),
    5: (10, 14),
    6: (5, 8),
    7: (11, 12, 13),
    8: (15, 16),
    9: (17, 22),
    10: (19, 20),
    11: (21, 23),
    12: (24, 25),
}

TCDSB_EARLY = {
    1: (1, 2, 4),
    2: (3, 5, 6),
    3: (7, 12),
    4: (8, 9, 10),
    5: (15, 16, 23, 24, 25),
    6: (11, 17, 21),
    7: (33, 37, 39, 40),
    8: (41, 42, 44),
    9: (19, 20, 22, 26, 27, 28),
    10: (13, 14, 18),
    11: (29, 30, 31, 32, 34),
    12: (35, 36, 38, 43),
}
TCDSB_2014 = {
    1: (1, 2, 4),
    2: (3, 5, 6),
    3: (7, 12),
    4: (8, 9, 10),
    5: (15, 16, 23, 25),
    6: (11, 17),
    7: (24, 37, 39, 40),
    8: (41, 42, 44),
    9: (19, 20, 21, 22, 27, 28),
    10: (13, 14, 18),
    11: (26, 29, 30, 31, 32, 33, 34),
    12: (35, 36, 38, 43),
}
TCDSB_25 = {
    1: (1,),
    2: (2,),
    3: (7,),
    4: (3, 4),
    5: (6, 8, 18),
    6: (9,),
    7: (21, 22),
    8: (23, 25),
    9: (10, 11, 12, 13),
    10: (5,),
    11: (14, 15, 16, 17, 19),
    12: (20, 24),
}

VIAMONDE_EARLY = {
    2: (16, 23, 24, 25, 26, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44),
    3: (14, 17, 18, 19, 20, 21, 22, 27, 28, 29, 30, 31, 32),
    4: (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15),
}
VIAMONDE_2014 = {
    2: (8, 9, 10, 12, 15, 16, 23, 24, 25, 26, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44),
    3: (20, 21, 22, 27, 28, 29, 30, 31, 32),
    4: (1, 2, 3, 4, 5, 6, 7, 11, 13, 14, 17, 18, 19),
}
VIAMONDE_25 = {
    2: (6, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25),
    3: (10, 11, 12, 13, 14, 19),
    4: (1, 2, 3, 4, 5, 7, 8, 9),
}

MONAVENIR_EARLY = {
    3: (1, 2, 7, 8, 9, 10, 12, 15, 16, 23, 24, 25, 33, 34, 37, 38, 39, 40, 41, 42, 43, 44),
    4: (3, 4, 5, 6, 11, 13, 14, 17, 18, 19, 20, 21, 22, 26, 27, 28, 29, 30, 31, 32, 35, 36),
}
MONAVENIR_2014 = {
    3: (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 27, 28),
    4: (24, 25, 26, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44),
}
MONAVENIR_25 = {
    3: (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 18),
    4: (14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25),
}


def mapping(board: str, year: int) -> dict[int, tuple[int, ...]]:
    if board == "tdsb":
        return TDSB_2026 if year == 2026 else TDSB_25 if year >= 2018 else TDSB_22
    if board == "tcdsb":
        return TCDSB_25 if year >= 2018 else TCDSB_2014 if year == 2014 else TCDSB_EARLY
    if board == "viamonde":
        return VIAMONDE_25 if year >= 2018 else VIAMONDE_2014 if year == 2014 else VIAMONDE_EARLY
    return MONAVENIR_25 if year >= 2018 else MONAVENIR_2014 if year == 2014 else MONAVENIR_EARLY


def official_name(board: str, ward: int, year: int) -> str:
    if board == "viamonde" and year >= 2014:
        return {2: "Est", 3: "Centre", 4: "Ouest"}[ward]
    if board == "monavenir" and year >= 2018:
        return {3: "Toronto Ouest", 4: "Toronto Est"}[ward]
    return ""


def main() -> None:
    fields = [
        "board_id",
        "office_code",
        "represented_body",
        "display_name",
        "short_name",
        "boundary_regime",
        "ward_id",
        "official_geographic_name",
        "city_boundary_regime",
        "city_wards",
        "source_authority",
        "source_url",
        "source_date",
    ]
    rows = []
    for year, (source_url, source_date) in SOURCES.items():
        city_regime = "toronto_council_25_wards" if year >= 2018 else "toronto_council_44_wards"
        for board, contract in BOARDS.items():
            office_code, represented_body, display_name, short_name = contract
            for ward, city_wards in mapping(board, year).items():
                rows.append(
                    {
                        "board_id": board,
                        "office_code": office_code,
                        "represented_body": represented_body,
                        "display_name": display_name,
                        "short_name": short_name,
                        "boundary_regime": f"{board}-trustee-wards-{year}",
                        "ward_id": ward,
                        "official_geographic_name": official_name(board, ward, year),
                        "city_boundary_regime": city_regime,
                        "city_wards": ";".join(map(str, city_wards)),
                        "source_authority": "City of Toronto",
                        "source_url": source_url,
                        "source_date": source_date,
                    }
                )
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
