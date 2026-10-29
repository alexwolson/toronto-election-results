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
    assert results.groupby(["election_date", "represented_body", "office_type"]).size().sum() == 705


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
    metro = elected[elected["represented_body"].eq("metro_toronto_council")]
    assert metro.set_index("official_district_id").loc["downtown", "candidate_name_raw"] == (
        "Chow, Olivia"
    )


def test_unreported_contests_are_placeholders():
    manifest = archive_placeholder_manifest(REFERENCE)

    assert len(manifest) == 8
    assert manifest["coverage_status"].eq("source_missing").all()
    assert set(manifest["official_district_id"]) >= {
        "ward-3",
        "ward-4",
        "ward-5",
        "kingsway-humber",
    }
