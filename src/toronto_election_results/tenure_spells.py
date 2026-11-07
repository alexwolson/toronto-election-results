"""Group Office tenure evidence rows into continuous spells of service.

``office_tenures`` holds evidence rows: each says that a Person held one office from a start
date to at least a reference date, or, for House of Commons terms, between two exact dates. A
councillor re-elected five times therefore has many overlapping rows. ``spell_id`` gives every
row of one unbroken stretch of service the same value: rows of one Person, Represented body and
Office type belong to one spell when each starts no later than the day after the latest end so
far. A row whose start is unknown cannot be placed in a stretch, so its ``spell_id`` is null.
"""

from __future__ import annotations

import pandas as pd

from .schema import stable_id

_SCOPE = ["person_id", "represented_body", "office_type"]


def assign_tenure_spells(tenures: pd.DataFrame) -> pd.DataFrame:
    """Return the tenures with ``spell_id`` set on every row whose start date is known."""

    out = tenures.drop(columns=["spell_id"], errors="ignore").copy()
    starts = pd.to_datetime(out["started_on"], errors="coerce")
    ends = pd.to_datetime(out["ended_on"], errors="coerce")
    spells = pd.Series(pd.NA, index=out.index, dtype="string")
    dated = out.loc[starts.notna()]
    for _, group in dated.groupby(_SCOPE, sort=False, dropna=False):
        ordered = sorted(
            group.index,
            key=lambda index: (
                starts[index],
                ends[index] if pd.notna(ends[index]) else pd.Timestamp.max,
                str(out.at[index, "office_tenure_id"]),
            ),
        )
        spell_id: str | None = None
        latest_end = pd.NaT
        for index in ordered:
            end = ends[index] if pd.notna(ends[index]) else pd.Timestamp.max
            start_new = spell_id is None or (
                latest_end != pd.Timestamp.max and starts[index] > latest_end + pd.Timedelta(days=1)
            )
            if start_new:
                spell_id = stable_id("spl", str(out.at[index, "office_tenure_id"]))
                latest_end = end
            else:
                latest_end = max(latest_end, end)
            spells[index] = spell_id
    out["spell_id"] = spells
    return out
