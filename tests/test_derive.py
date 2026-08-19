"""Per-contest derived fields: winner, acclamation, vote share, rank."""

import pandas as pd

from toronto_election_results.derive import derive_contest_fields


def _base(rows):
    return pd.DataFrame(rows, columns=["contest_id", "candidate_name_raw", "votes"])


def test_contested_race_shares_ranks_and_winner():
    df = derive_contest_fields(
        _base(
            [
                ("2022-councillor-1", "A", 100),
                ("2022-councillor-1", "B", 50),
                ("2022-councillor-1", "C", 10),
            ]
        )
    )
    df = df.set_index("candidate_name_raw")
    assert df.loc["A", "elected"] and not df.loc["B", "elected"]
    assert df.loc["A", "vote_rank"] == 1 and df.loc["C", "vote_rank"] == 3
    assert df.loc["A", "total_contest_votes"] == 160
    assert abs(df.loc["A", "vote_share"] - 100 / 160) < 1e-9
    assert (df["n_candidates"] == 3).all()
    assert not df["acclaimed"].any()


def test_acclaimed_race_has_null_votes_and_share():
    df = derive_contest_fields(_base([("2003-councillor-7", "Solo", 0)]))
    row = df.iloc[0]
    assert row["acclaimed"]
    assert row["elected"]
    assert pd.isna(row["votes"])
    assert pd.isna(row["vote_share"])
    assert pd.isna(row["vote_rank"])
    assert pd.isna(row["total_contest_votes"])
    assert row["n_candidates"] == 1


def test_vote_share_sums_to_one_per_contested_contest():
    df = derive_contest_fields(
        _base(
            [
                ("c1", "A", 3),
                ("c1", "B", 1),
                ("c2", "X", 10),
                ("c2", "Y", 10),
            ]
        )
    )
    sums = df.groupby("contest_id")["vote_share"].sum()
    assert abs(sums["c1"] - 1.0) < 1e-9
    assert abs(sums["c2"] - 1.0) < 1e-9


def test_tie_for_first_flags_both_elected():
    df = derive_contest_fields(_base([("c2", "X", 10), ("c2", "Y", 10)]))
    assert df["elected"].sum() == 2
