"""Reviewed display names for Candidacies whose ballot name the parser cannot split by rule.

The City's poll-by-poll files print names surname first with no comma, so a multi-word surname
(``Chernos Lin Rachel``) or a row printed given name first (the 2016 TDSB Ward 14 by-election)
is read in the wrong order. The Clerk's declaration of results prints every name given name
first, and each correction here cites it. A correction may only reorder the words of
``candidate_name_raw``, and it fails once the parser already produces the same display name.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from .schema import _CANONICAL_VALUES

CANDIDATE_NAME_CURATIONS_FILENAME = "candidate_name_curations.csv"
_KEY = ["event_id", "represented_body", "official_district_id", "candidate_name_raw"]
_COLUMNS = [*_KEY, "candidate_name", "evidence_url", "rationale"]
_BODIES = _CANONICAL_VALUES["represented_body"]


def _words(value: str) -> list[str]:
    return sorted(unicodedata.normalize("NFKC", value).casefold().split())


def apply_candidate_name_curations(frames: list[pd.DataFrame], path: Path) -> list[pd.DataFrame]:
    """Replace the display name of each reviewed Candidacy in the adapter frames."""

    out = [frame.copy() for frame in frames]
    if not path.exists():
        return out
    curations = pd.read_csv(path, dtype="string", keep_default_na=False)
    if list(curations.columns) != _COLUMNS:
        raise ValueError(f"candidate name curations must have columns {_COLUMNS}")
    if curations.duplicated(_KEY).any():
        raise ValueError("duplicate candidate name curation")
    for row in curations.to_dict("records"):
        if any(not row[column].strip() for column in _COLUMNS):
            raise ValueError("candidate name curation fields cannot be blank")
        parsed = urlparse(row["evidence_url"])
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"invalid candidate name evidence URL: {row['evidence_url']!r}")
        if _words(row["candidate_name"]) != _words(row["candidate_name_raw"]):
            raise ValueError(
                f"curated name {row['candidate_name']!r} must reorder the words of "
                f"{row['candidate_name_raw']!r}"
            )
        hits = []
        for index, frame in enumerate(out):
            if not set(_KEY) <= set(frame.columns):
                continue
            # Adapters may still carry display labels such as "Toronto District School Board".
            bodies = frame["represented_body"].map(lambda value: _BODIES.get(value, value))
            mask = bodies.astype("string").eq(row["represented_body"]).fillna(False)
            for column in ("event_id", "official_district_id", "candidate_name_raw"):
                mask &= frame[column].astype("string").eq(row[column]).fillna(False)
            hits.extend((index, label) for label in frame.index[mask])
        if len(hits) != 1:
            raise ValueError(
                f"candidate name curation for {row['candidate_name_raw']!r} matched "
                f"{len(hits)} Candidacies; expected 1"
            )
        index, label = hits[0]
        if out[index].at[label, "candidate_name"] == row["candidate_name"]:
            raise ValueError(
                f"candidate name curation is no longer needed: {row['candidate_name']!r}"
            )
        out[index].at[label, "candidate_name"] = row["candidate_name"]
    return out
