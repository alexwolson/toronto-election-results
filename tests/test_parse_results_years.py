"""Cross-year coverage: the one parser must handle all three layout families.

  - 2003 legacy .xls  : "Councillor Ward N" sheet name, "Last, First" names
  - 2006/2010/2014    : "WardN" sheet + "Ward: N" title row, UPPERCASE "LAST FIRST" names
  - 2018/2022 modern  : "City Ward N <Name>" header, "Last First" names

Each fixture is the real City councillor file. Assertions are structural plus one verified
spot-check; per-candidate votes are cross-checked against an independent subdivision sum so no
external ground truth needs hard-coding.
"""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.parse_results import parse_open_data_file

FIXTURES = Path(__file__).parent / "fixtures" / "open_data"

# (year, filename, expected ward count)
COUNCILLOR_FILES = [
    (2003, "2003_Toronto_Poll_by_Poll_Councillor.xls", 44),
    (2006, "2006_Toronto_Poll_by_Poll_Councillor.xls", 44),
    (2010, "2010_Toronto_Poll_by_Poll_Councillor.xls", 44),
    (2014, "2014_Toronto_Poll_by_Poll_Councillor.xls", 44),
    (2018, "2018_Toronto_Poll_By_Poll_Councillor.xlsx", 25),
    (2022, "2022_Toronto_Poll_By_Poll_Councillor.xlsx", 25),
]


@pytest.fixture(scope="module")
def parsed():
    return {
        year: parse_open_data_file(FIXTURES / name, office="councillor")
        for year, name, _ in COUNCILLOR_FILES
    }


@pytest.mark.parametrize("year, _name, n_wards", COUNCILLOR_FILES)
def test_all_wards_present_and_numbered(parsed, year, _name, n_wards):
    df = parsed[year]
    assert sorted(df["ward_number"].unique()) == list(range(1, n_wards + 1))
    assert df["ward_number"].notna().all()


@pytest.mark.parametrize("year, _name, _n", COUNCILLOR_FILES)
def test_no_totals_row_leaks(parsed, year, _name, _n):
    assert not parsed[year]["candidate_name_raw"].str.lower().str.contains("total").any()


@pytest.mark.parametrize("year, _name, _n", COUNCILLOR_FILES)
def test_votes_are_nonnegative_ints(parsed, year, _name, _n):
    df = parsed[year]
    assert df["votes"].dtype.kind in ("i", "u")
    assert (df["votes"] >= 0).all()


def test_2006_uppercase_name_family_spot_check(parsed):
    """SUZAN HALL's Total in 2006 Ward 1 is 4878 (verified against the raw cell)."""
    row = parsed[2006][
        (parsed[2006]["ward_number"] == 1) & (parsed[2006]["candidate_name_raw"] == "HALL SUZAN")
    ]
    assert len(row) == 1
    assert row["votes"].iloc[0] == 4878


def test_2018_mayor_notice_sheet_is_skipped():
    """The 2018 Mayor file's leading 'Notice' worksheet must not produce rows."""
    df = parse_open_data_file(FIXTURES / "2018_Toronto_Poll_By_Poll_Mayor.xlsx", office="mayor")
    assert sorted(df["ward_number"].unique()) == list(range(1, 26))
    assert df["ward_number"].notna().all()


@pytest.mark.parametrize("year, name, _n", COUNCILLOR_FILES)
def _first_ward_sheet(workbook: pd.ExcelFile):
    """The first worksheet carrying a candidate table (skips 'Notice'/empty sheets)."""
    for sheet in workbook.sheet_names:
        raw = workbook.parse(sheet, header=None)
        for i in range(min(len(raw), 10)):
            if str(raw.iat[i, 0]).strip().lower() in {"subdivision", "name"}:
                return raw, i
    raise AssertionError("no candidate-table sheet found")


@pytest.mark.parametrize("year, name, _n", COUNCILLOR_FILES)
def test_votes_equal_independent_subdivision_sum(parsed, year, name, _n):
    """Parser votes for ward 1's first candidate == an independent sum of the subdivision cells."""
    engine = "xlrd" if name.endswith(".xls") else "openpyxl"
    raw, header_idx = _first_ward_sheet(pd.ExcelFile(FIXTURES / name, engine=engine))
    numeric_header = pd.to_numeric(raw.iloc[header_idx], errors="coerce")
    subdiv_cols = [c for c in raw.columns if c != 0 and pd.notna(numeric_header[c])]
    # First real candidate row: skip the office-label row (modern files) and any totals row.
    candidate_idx = next(
        i
        for i in range(header_idx + 1, len(raw))
        if (n := str(raw.iat[i, 0]).strip())
        and n.lower() not in {"councillor", "mayor"}
        and "total" not in n.lower()
    )
    name_raw = str(raw.iat[candidate_idx, 0]).strip()
    expected = int(
        pd.to_numeric(raw.loc[candidate_idx, subdiv_cols], errors="coerce").fillna(0).sum()
    )
    got = parsed[year][
        (parsed[year]["ward_number"] == 1) & (parsed[year]["candidate_name_raw"] == name_raw)
    ]["votes"].iloc[0]
    assert got == expected
