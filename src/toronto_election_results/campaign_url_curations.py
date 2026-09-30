"""Evidence-backed campaign links supplementing official candidate rosters."""

from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

CAMPAIGN_URL_CURATIONS_FILENAME = "campaign_url_curations.csv"


def apply_campaign_url_curations(results: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Apply reviewed links to exact Candidacies, preserving the official source cache."""
    updated = results.copy()
    if not path.exists():
        return updated
    curations = pd.read_csv(path, dtype="string", keep_default_na=False)
    required = {
        "candidacy_id",
        "candidate_name",
        "campaign_url",
        "evidence_url",
        "verified_on",
        "rationale",
    }
    if not required.issubset(curations.columns):
        raise ValueError("campaign URL curations are missing required columns")
    if curations["candidacy_id"].duplicated().any():
        raise ValueError("duplicate campaign URL curation Candidacy")
    for row in curations.to_dict("records"):
        if any(not row[column].strip() for column in required):
            raise ValueError("campaign URL curation fields cannot be blank")
        for column in ("campaign_url", "evidence_url"):
            parsed = urlparse(row[column])
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError(f"invalid campaign URL curation {column}")
        pd.to_datetime(row["verified_on"], format="%Y-%m-%d", errors="raise")
        target = updated["candidacy_id"].eq(row["candidacy_id"])
        if target.sum() != 1:
            raise ValueError("campaign URL curation must identify exactly one Candidacy")
        if updated.loc[target, "candidate_name"].iloc[0] != row["candidate_name"]:
            raise ValueError("campaign URL curation candidate name mismatch")
        updated.loc[target, "campaign_url"] = row["campaign_url"]
    return updated
