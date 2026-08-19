"""Tests for parsing City Open Data poll-by-poll workbooks into ward-level records.

Fixtures are the real City files (2022 modern .xlsx, 2003 legacy .xls) kept under
tests/fixtures/open_data/. Asserted values were verified directly against the raw cells.
"""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.parse_results import parse_open_data_file

FIXTURES = Path(__file__).parent / "fixtures" / "open_data"
COUNCILLOR_2022 = FIXTURES / "2022_Toronto_Poll_By_Poll_Councillor.xlsx"


@pytest.fixture(scope="module")
def councillor_2022() -> pd.DataFrame:
    return parse_open_data_file(COUNCILLOR_2022, office="councillor")


def test_returns_expected_columns(councillor_2022):
    assert set(councillor_2022.columns) == {
        "ward_number",
        "ward_name",
        "office",
        "candidate_name_raw",
        "votes",
    }


def test_parses_all_25_wards(councillor_2022):
    assert sorted(councillor_2022["ward_number"].unique()) == list(range(1, 26))


def test_ward_header_gives_number_and_name(councillor_2022):
    ward1 = councillor_2022[councillor_2022["ward_number"] == 1]
    assert (ward1["ward_name"] == "Etobicoke North").all()


def test_known_candidate_votes(councillor_2022):
    """Crisanti Vincent's Total in 2022 Ward 1 is 6815 (verified against the raw cell)."""
    row = councillor_2022[
        (councillor_2022["ward_number"] == 1)
        & (councillor_2022["candidate_name_raw"] == "Crisanti Vincent")
    ]
    assert len(row) == 1
    assert row["votes"].iloc[0] == 6815


def test_excludes_totals_row(councillor_2022):
    names = councillor_2022["candidate_name_raw"].str.lower()
    assert not names.str.contains("total").any()


def test_office_is_set(councillor_2022):
    assert (councillor_2022["office"] == "councillor").all()


def test_votes_are_positive_integers(councillor_2022):
    assert councillor_2022["votes"].dtype.kind in ("i", "u")
    assert (councillor_2022["votes"] >= 0).all()


def test_votes_equal_independent_subdivision_sum(councillor_2022):
    """Parser votes must equal an independent sum of the subdivision columns (incl. 98/99)."""
    raw = pd.read_excel(COUNCILLOR_2022, engine="openpyxl", sheet_name="Ward 1", header=None)
    header = raw.iloc[1]  # 'Subdivision', 1, 2, ..., 98, 99, 'Total'
    subdiv_cols = [
        c for c in raw.columns if isinstance(header[c], (int, float)) and pd.notna(header[c])
    ]
    crisanti = raw[raw[0] == "Crisanti Vincent"].iloc[0]
    independent_sum = int(crisanti[subdiv_cols].fillna(0).sum())
    parsed = councillor_2022[
        (councillor_2022["ward_number"] == 1)
        & (councillor_2022["candidate_name_raw"] == "Crisanti Vincent")
    ]["votes"].iloc[0]
    assert parsed == independent_sum


# --- Legacy layout: 2003 .xls (comma names, ward only in sheet name, no ward name) ---

COUNCILLOR_2003 = FIXTURES / "2003_Toronto_Poll_by_Poll_Councillor.xls"


@pytest.fixture(scope="module")
def councillor_2003() -> pd.DataFrame:
    return parse_open_data_file(COUNCILLOR_2003, office="councillor")


def test_legacy_parses_all_44_wards(councillor_2003):
    assert sorted(councillor_2003["ward_number"].unique()) == list(range(1, 45))


def test_legacy_ward_name_absent(councillor_2003):
    """2003 sheets carry only the ward number (in the sheet name), no ward name."""
    assert councillor_2003["ward_name"].isna().all()


def test_legacy_known_candidate_votes(councillor_2003):
    """Rob Ford's Total in 2003 Ward 2 is 10601 (verified against the raw cell)."""
    row = councillor_2003[
        (councillor_2003["ward_number"] == 2)
        & (councillor_2003["candidate_name_raw"] == "Ford, Rob")
    ]
    assert len(row) == 1
    assert row["votes"].iloc[0] == 10601


def test_legacy_excludes_totals_row(councillor_2003):
    assert not councillor_2003["candidate_name_raw"].str.lower().str.contains("total").any()
