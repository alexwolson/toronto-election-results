"""Parsing the 2000 archived City results HTML."""

from pathlib import Path

from toronto_election_results.candidates import normalize_name
from toronto_election_results.parse_2000 import parse_2000_page

FIXTURES = Path(__file__).parent / "fixtures" / "vote2000"


def _parse(name):
    return parse_2000_page((FIXTURES / name).read_text())


def test_mayor_is_city_wide_with_all_candidates():
    office, ward, records = _parse("mayor-000.htm")
    assert office == "mayor"
    assert ward is None
    assert len(records) == 26
    assert records[0] == ("MEL LASTMAN", 483277)  # verified against source + Wikipedia
    assert max(records, key=lambda r: r[1]) == ("MEL LASTMAN", 483277)


def test_councillor_ward_and_votes():
    office, ward, records = _parse("councillor-001.htm")
    assert office == "councillor"
    assert ward == 1
    assert ("SUZAN HALL", 2894) in records
    assert max(records, key=lambda r: r[1]) == ("SUZAN HALL", 2894)


def test_acclamation_is_single_candidate_zero_votes():
    office, ward, records = _parse("councillor-027-acclamation.htm")
    assert office == "councillor"
    assert ward == 27
    assert records == [("KYLE RAE", 0)]  # "Acclamation" -> 0; marked acclaimed downstream


def test_given_first_name_order_for_2000():
    assert normalize_name("MEL LASTMAN", order="given-first") == ("Mel Lastman", "Mel", "Lastman")
    assert normalize_name("KYLE RAE", order="given-first") == ("Kyle Rae", "Kyle", "Rae")


def test_three_column_page_skips_summary_row():
    """Some pages are Name|Votes|Percent with a trailing 'Total Votes Counted:...' summary row."""
    office, ward, records = _parse("councillor-042-3col-summary.htm")
    assert office == "councillor"
    assert ward == 42
    assert ("RAYMOND CHO", 7428) in records
    assert not any(":" in name for name, _ in records)  # no summary row leaked
    assert len(records) == 4
