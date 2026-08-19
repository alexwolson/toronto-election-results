"""Parsing voter-statistics files into per-ward electorate + turnout numerator."""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.voter_statistics import (
    VOTER_STATS_FILES,
    attach_electorate,
    by_election_voter_statistics,
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
    GENERAL = pd.DataFrame(
        {
            "election_year": [2022, 2022],
            "ward_number": [1, 2],
            "eligible_electors": [330, 400],
            "ballots_cast": [160, 250],
        }
    )
    # by-election stats: a 2023 council ward and a 2023 mayoral (city-wide) — same year, different contests
    BY_ELECTION = pd.DataFrame(
        {
            "election_year": [2023, 2023],
            "office": ["councillor", "mayor"],
            "ward_number": [20, pd.NA],
            "eligible_electors": [78906, 1947242],
            "ballots_cast": [16974, 724638],
        }
    )

    def _attach(self, rows):
        return attach_electorate(pd.DataFrame(rows), self.GENERAL, self.BY_ELECTION)

    def test_general_councillor_gets_ward_electorate(self):
        out = self._attach(
            [
                {
                    "election_year": 2022,
                    "election_type": "general",
                    "office": "councillor",
                    "ward_number": 1,
                }
            ]
        )
        assert out.iloc[0]["eligible_electors"] == 330
        assert abs(out.iloc[0]["turnout"] - 160 / 330) < 1e-9

    def test_general_mayor_gets_city_wide(self):
        out = self._attach(
            [
                {
                    "election_year": 2022,
                    "election_type": "general",
                    "office": "mayor",
                    "ward_number": pd.NA,
                }
            ]
        )
        assert out.iloc[0]["eligible_electors"] == 730  # sum of wards

    def test_by_election_council_and_mayor_dont_collide(self):
        """2023 has both a mayoral by-election (city-wide) and a Ward 20 councillor by-election."""
        out = self._attach(
            [
                {
                    "election_year": 2023,
                    "election_type": "by_election",
                    "office": "councillor",
                    "ward_number": 20,
                },
                {
                    "election_year": 2023,
                    "election_type": "by_election",
                    "office": "mayor",
                    "ward_number": pd.NA,
                },
            ]
        )
        council, mayor = out.iloc[0], out.iloc[1]
        assert council["eligible_electors"] == 78906 and council["ballots_cast"] == 16974
        assert mayor["eligible_electors"] == 1947242  # city-wide, not the ward figure


@pytest.mark.skipif(
    not (RAW / VOTER_STATS_FILES[2022]).exists(), reason="voter-stats not downloaded"
)
def test_real_totals_match_published_figures():
    """Integration: parsed totals match the City's published counts (general + by-election)."""
    general = (
        voter_statistics().groupby("election_year")[["eligible_electors", "ballots_cast"]].sum()
    )
    assert general.loc[2022, "eligible_electors"] == 1898750
    assert general.loc[2018, "ballots_cast"] == 769044
    by_election = by_election_voter_statistics().set_index(["election_year", "office"])
    assert by_election.loc[(2023, "mayor"), "eligible_electors"] == 1947242
