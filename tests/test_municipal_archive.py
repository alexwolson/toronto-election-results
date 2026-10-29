from pathlib import Path

from toronto_election_results.municipal_archive import (
    archive_placeholder_manifest,
    load_archive_results,
)

REFERENCE = Path(__file__).resolve().parents[1] / "data" / "reference"


def _winners(frame, date, body, office):
    rows = frame[
        frame["election_date"].eq(date)
        & frame["represented_body"].eq(body)
        & frame["office_type"].eq(office)
    ]
    return rows.groupby("official_district_id")["elected"].sum()


def test_archive_contests_elect_their_seat_counts():
    results = load_archive_results(REFERENCE)

    council_1997 = _winners(results, "1997-11-10", "toronto_city_council", "councillor")
    assert len(council_1997) == 28 and council_1997.eq(2).all()
    east_york = _winners(results, "1994-11-14", "east_york_borough_council", "councillor")
    assert east_york.eq(2).all()
    council_2000 = _winners(results, "2000-11-13", "toronto_city_council", "councillor")
    assert len(council_2000) == 44 and council_2000.eq(1).all()
    trustee_wards = {
        "toronto_district_school_board": 22,
        "toronto_catholic_district_school_board": 12,
        "conseil_scolaire_viamonde": 3,
        "conseil_scolaire_catholique_monavenir": 2,
    }
    for body, wards in trustee_wards.items():
        trustees_2000 = _winners(results, "2000-11-13", body, "trustee")
        assert len(trustees_2000) == wards and trustees_2000.eq(1).all()
    trustees = results[results["office_type"].eq("trustee")]
    assert trustees.groupby("election_date").size().to_dict() == {
        "1994-11-14": 350,
        "1997-11-10": 153,
        "2000-11-13": 118,
    }
    assert (
        trustees.loc[trustees["election_date"].eq("2000-11-13"), "outcome_method"]
        .eq("acclamation")
        .sum()
        == 4
    )
    assert len(results) == 1_335


def test_1994_and_1997_trustee_contests_elect_their_seat_counts():
    results = load_archive_results(REFERENCE)
    wards_1994 = {
        "toronto_board_of_education": 13,
        "north_york_board_of_education": 14,
        "scarborough_board_of_education": 14,
        "etobicoke_board_of_education": 12,
        "york_board_of_education": 8,
        "east_york_board_of_education": 4,
        "metropolitan_separate_school_board": 19,
        "metro_toronto_french_language_school_council": 4,
        "mssb_french_language_section": 3,
    }
    for body, wards in wards_1994.items():
        assert len(_winners(results, "1994-11-14", body, "trustee")) == wards, body
    toronto = _winners(results, "1994-11-14", "toronto_board_of_education", "trustee")
    assert toronto[toronto.eq(2)].index.tolist() == ["10", "11", "12", "5", "7"]
    assert _winners(results, "1994-11-14", "east_york_board_of_education", "trustee").eq(2).all()
    wards_1997 = {
        "toronto_district_school_board": 22,
        "toronto_catholic_district_school_board": 12,
        "conseil_scolaire_viamonde": 2,
        "conseil_scolaire_catholique_monavenir": 2,
    }
    for body, wards in wards_1997.items():
        winners = _winners(results, "1997-11-10", body, "trustee")
        assert len(winners) == wards and winners.eq(1).all(), body
    partial = results[results["coverage_status"].eq("partial")]
    assert sorted(partial.groupby(["election_date", "represented_body"]).size().items()) == [
        (("1994-11-14", "metro_toronto_french_language_school_council"), 14),
        (("1994-11-14", "mssb_french_language_section"), 4),
        (("1997-11-10", "conseil_scolaire_catholique_monavenir"), 2),
    ]
    star = results[results["source_authority"].eq("Toronto Star")]
    assert star.groupby("election_date").size().to_dict() == {"1994-11-14": 113, "1997-11-10": 143}


def test_archive_winners_match_known_results():
    results = load_archive_results(REFERENCE)
    elected = results[results["elected"]]

    def names(date, office, district):
        rows = elected[
            elected["election_date"].eq(date)
            & elected["office_type"].eq(office)
            & elected["official_district_id"].eq(district)
        ]
        return sorted(rows["candidate_name_raw"])

    assert names("1997-11-10", "mayor", "city") == ["Mel Lastman"]
    assert names("1997-11-10", "councillor", "ward-24") == ["Kyle Rae", "Olivia Chow"]
    assert names("2000-11-13", "mayor", "city") == ["MEL LASTMAN"]
    trustees = elected[elected["represented_body"].eq("toronto_district_school_board")]
    assert (
        trustees.loc[trustees["election_date"].eq("2000-11-13")]
        .set_index("official_district_id")
        .loc["8", "candidate_name_raw"]
        == "KATHLEEN WYNNE"
    )
    assert sorted(
        trustees.loc[trustees["election_date"].eq("1997-11-10")]
        .set_index("official_district_id")
        .loc[["2", "4"], "candidate_name_raw"]
    ) == ["Irene Atkinson", "Stephnie Payne"]
    toronto_1994 = elected[elected["represented_body"].eq("toronto_board_of_education")]
    assert sorted(
        toronto_1994.loc[toronto_1994["official_district_id"].eq("12"), "candidate_name_raw"]
    ) == [
        "Sparling, Linda",
        "Vanstone, Ann",
    ]
    separate_1997 = elected[
        elected["represented_body"].eq("toronto_catholic_district_school_board")
        & elected["election_date"].eq("1997-11-10")
        & elected["official_district_id"].eq("12")
    ]
    assert separate_1997["candidate_name_raw"].tolist() == ["Lisa Romano-Dwyer"]
    metro = elected[
        elected["represented_body"].eq("metro_toronto_council")
        & elected["election_date"].eq("1994-11-14")
    ]
    assert metro.set_index("official_district_id").loc["downtown", "candidate_name_raw"] == (
        "Chow, Olivia"
    )
    assert metro.set_index("official_district_id").loc[
        "north-york-spadina", "candidate_name_raw"
    ] == ("Howard Moscoe")
    north_york = elected[elected["represented_body"].eq("north_york_city_council")]
    assert north_york.set_index("official_district_id").loc[
        ["ward-3", "ward-5"], "candidate_name_raw"
    ].tolist() == [
        "Peter Li Preti",
        "Maria Rizzo",
    ]


def test_star_supplement_fills_every_unreported_1994_contest():
    manifest = archive_placeholder_manifest(REFERENCE)
    results = load_archive_results(REFERENCE)

    assert manifest.empty
    supplemented = results[
        results["election_date"].eq("1994-11-14")
        & results["office_type"].eq("councillor")
        & results["source_authority"].eq("Toronto Star")
    ]
    assert set(supplemented["official_district_id"]) == {
        "ward-3",
        "ward-4",
        "ward-5",
        "kingsway-humber",
        "markland-centennial",
        "north-york-spadina",
        "north-york-centre-south",
        "north-york-centre",
    }
    assert supplemented["outcome_method"].eq("acclamation").sum() == 6
