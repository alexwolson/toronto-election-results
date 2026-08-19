"""QC gates over the assembled table."""

import pandas as pd

from toronto_election_results.validate import validate


def _good():
    return pd.DataFrame(
        [
            # a contested councillor race
            {
                "contest_id": "c1",
                "candidate_name_raw": "A",
                "votes": 60,
                "total_contest_votes": 100,
                "vote_share": 0.6,
                "elected": True,
                "acclaimed": False,
            },
            {
                "contest_id": "c1",
                "candidate_name_raw": "B",
                "votes": 40,
                "total_contest_votes": 100,
                "vote_share": 0.4,
                "elected": False,
                "acclaimed": False,
            },
            # an acclamation
            {
                "contest_id": "c2",
                "candidate_name_raw": "Solo",
                "votes": pd.NA,
                "total_contest_votes": pd.NA,
                "vote_share": pd.NA,
                "elected": True,
                "acclaimed": True,
            },
        ]
    )


def test_clean_table_has_no_issues():
    assert validate(_good()) == []


def test_flags_contest_with_no_winner():
    df = _good()
    df.loc[df["contest_id"] == "c1", "elected"] = False
    assert any("no elected" in m for m in validate(df))


def test_flags_vote_share_not_summing_to_one():
    df = _good()
    df.loc[(df["contest_id"] == "c1") & (df["candidate_name_raw"] == "B"), "vote_share"] = 0.1
    assert any("vote_share" in m for m in validate(df))


def test_flags_duplicate_candidate_rows():
    df = pd.concat([_good(), _good().iloc[[0]]], ignore_index=True)
    assert any("duplicate" in m for m in validate(df))


def test_flags_acclaimed_with_votes():
    df = _good()
    df.loc[df["acclaimed"], "votes"] = 5
    assert any("acclaimed" in m for m in validate(df))
