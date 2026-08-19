"""Parsing voter-statistics files into per-ward electorate + turnout numerator."""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.voter_statistics import (
    VOTER_STATS_FILES,
    attach_electorate,
    parse_voter_statistics_file,
    voter_statistics,
)

FIXTURES = Path(__file__).parent / "fixtures" / "voter_stats"
RAW = Path("data/raw/voter_stats")


class TestParse:
    def test_legacy_era_sums_subdivisions_excluding_total_rows(self):
        df = parse_voter_statistics_file(FIXTURES / "legacy.xlsx", year=2003)
        w1 = df[df["ward_number"] == 1].iloc[0]
        assert w1["eligible_electors"] == 330  # 110 + 220, not the 330 "Total" row nor Grand Total
        assert w1["ballots_cast"] == 150
        assert set(df["ward_number"]) == {1, 2}  # no Total/Grand rows leaked
        assert (df["election_year"] == 2003).all()

    def test_modern_era_picks_data_sheet_over_readme(self):
        df = parse_voter_statistics_file(FIXTURES / "modern.xlsx", year=2022)
        w1 = df[df["ward_number"] == 1].iloc[0]
        assert w1["eligible_electors"] == 330
        assert w1["ballots_cast"] == 160
        assert sorted(df["ward_number"]) == [1, 2]


class TestAttachElectorate:
    def _stats(self):
        return pd.DataFrame(
            {
                "election_year": [2022, 2022],
                "ward_number": [1, 2],
                "eligible_electors": [330, 400],
                "ballots_cast": [160, 250],
            }
        )

    def test_councillor_gets_ward_electorate(self):
        results = pd.DataFrame([{"election_year": 2022, "office": "councillor", "ward_number": 1}])
        out = attach_electorate(results, self._stats())
        row = out.iloc[0]
        assert row["eligible_electors"] == 330
        assert row["ballots_cast"] == 160
        assert abs(row["turnout"] - 160 / 330) < 1e-9

    def test_mayor_gets_city_wide_electorate(self):
        results = pd.DataFrame([{"election_year": 2022, "office": "mayor", "ward_number": pd.NA}])
        out = attach_electorate(results, self._stats())
        row = out.iloc[0]
        assert row["eligible_electors"] == 730  # sum of wards
        assert row["ballots_cast"] == 410


@pytest.mark.skipif(
    not (RAW / VOTER_STATS_FILES[2022]).exists(), reason="voter-stats not downloaded"
)
def test_real_city_totals_match_published_figures():
    """Integration: parsed city-wide totals match the City's published counts."""
    stats = voter_statistics()
    city = stats.groupby("election_year")[["eligible_electors", "ballots_cast"]].sum()
    # verified against the City's published voter-statistics grand totals
    assert city.loc[2022, "eligible_electors"] == 1898750
    assert city.loc[2022, "ballots_cast"] == 563124
    assert city.loc[2023, "eligible_electors"] == 1947242
    assert city.loc[2018, "ballots_cast"] == 769044
