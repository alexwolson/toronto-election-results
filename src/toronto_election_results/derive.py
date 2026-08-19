"""Per-contest derived fields.

Given contest-level rows (grouped by ``contest_id``), compute the model-facing fields:
``n_candidates``, ``acclaimed``, ``total_contest_votes``, ``vote_share``, ``vote_rank`` and
``elected``. A contest with a single candidate is an **acclamation**: its winner is elected with
null votes / share / rank (a zero would falsely imply no support). In a contested race the
winner is the top vote-getter; an exact tie for first flags every tied candidate elected (a real,
rare state resolved by lot — surfaced, not hidden).
"""

from __future__ import annotations

import pandas as pd


def derive_contest_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Return ``df`` with per-contest derived columns added (grouped by ``contest_id``)."""
    df = df.copy()
    grouped = df.groupby("contest_id")

    n_candidates = grouped["candidate_name_raw"].transform("size")
    acclaimed = n_candidates == 1
    total = grouped["votes"].transform("sum")
    max_votes = grouped["votes"].transform("max")

    df["n_candidates"] = n_candidates.astype("int64")
    df["acclaimed"] = acclaimed
    df["elected"] = (df["votes"] == max_votes) | acclaimed

    # Acclaimed contests carry no ballots: null the count-derived fields.
    keep = ~acclaimed
    df["votes"] = df["votes"].astype("Int64").where(keep)
    df["total_contest_votes"] = total.astype("Int64").where(keep)
    df["vote_share"] = (df["votes"] / total).where(keep)
    df["vote_rank"] = (
        grouped["votes"].rank(method="min", ascending=False).astype("Int64").where(keep)
    )
    return df
