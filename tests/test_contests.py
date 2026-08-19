"""Ward-sheet rows -> contest-level rows.

Councillor ward sheets are already contests (one per candidate per ward). Mayor is city-wide but
published per ward sheet, so mayor candidates must be summed across all wards into one row each.
"""

from pathlib import Path

import pandas as pd

from toronto_election_results.parse_results import parse_open_data_file, to_contest_level

FIXTURES = Path(__file__).parent / "fixtures" / "open_data"


def test_mayor_is_summed_city_wide():
    wardwise = parse_open_data_file(
        FIXTURES / "2022_Toronto_Poll_By_Poll_Mayor.xlsx", office="mayor"
    )
    contest = to_contest_level(wardwise, office="mayor")
    # one row per candidate, ward dropped
    assert len(contest) == wardwise["candidate_name_raw"].nunique() == 31
    assert contest["ward_number"].isna().all()
    assert contest["ward_name"].isna().all()
    # verified 2022 result: John Tory 342,158
    tory = contest[contest["candidate_name_raw"] == "Tory John"]
    assert tory["votes"].iloc[0] == 342158


def test_mayor_total_is_preserved():
    wardwise = parse_open_data_file(
        FIXTURES / "2022_Toronto_Poll_By_Poll_Mayor.xlsx", office="mayor"
    )
    contest = to_contest_level(wardwise, office="mayor")
    assert contest["votes"].sum() == wardwise["votes"].sum()


def test_councillor_ward_sheets_pass_through_unchanged():
    wardwise = parse_open_data_file(
        FIXTURES / "2022_Toronto_Poll_By_Poll_Councillor.xlsx", office="councillor"
    )
    contest = to_contest_level(wardwise, office="councillor")
    assert len(contest) == len(wardwise)
    assert contest["ward_number"].notna().all()
    pd.testing.assert_frame_equal(contest.reset_index(drop=True), wardwise.reset_index(drop=True))
