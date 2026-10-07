"""Evidence-backed Suspended Campaign dates for the current mayoral field."""

from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

CAMPAIGN_SUSPENSION_CURATIONS_FILENAME = "campaign_suspension_curations.csv"
_CURRENT_ELECTION_YEAR = 2026
_TORONTO_COUNCIL = "toronto_city_council"


def _iso_date(value: str, column: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        parsed = None
    if parsed is None or parsed.isoformat() != value:
        raise ValueError(f"invalid campaign suspension curation {column}: {value!r}")
    return parsed


def apply_campaign_suspension_curations(results: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Date reviewed Suspended Campaigns on exact current mayoral Candidacies.

    The City's roster marks a Candidacy only Active or Withdrawn, so a campaign the
    candidate publicly ended after the withdrawal deadline is a curated fact. Every
    other Candidacy keeps a null ``campaign_suspended_on``.
    """
    updated = results.copy()
    if "campaign_suspended_on" not in updated.columns:
        updated["campaign_suspended_on"] = pd.Series(pd.NA, index=updated.index, dtype="string")
    curations = pd.read_csv(path, dtype="string", keep_default_na=False)
    required = {
        "candidacy_id",
        "candidate_name",
        "campaign_suspended_on",
        "evidence_url",
        "verified_on",
        "rationale",
    }
    if not required.issubset(curations.columns):
        raise ValueError("campaign suspension curations are missing required columns")
    if curations["candidacy_id"].duplicated().any():
        raise ValueError("duplicate campaign suspension curation Candidacy")
    for row in curations.to_dict("records"):
        if any(not row[column].strip() for column in required):
            raise ValueError("campaign suspension curation fields cannot be blank")
        parsed = urlparse(row["evidence_url"])
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("invalid campaign suspension curation evidence_url")
        suspended_on = _iso_date(row["campaign_suspended_on"], "campaign_suspended_on")
        verified_on = _iso_date(row["verified_on"], "verified_on")
        if suspended_on > verified_on:
            raise ValueError("campaign suspension curation is dated after its verification")
        target = updated["candidacy_id"].eq(row["candidacy_id"])
        if target.sum() != 1:
            raise ValueError("campaign suspension curation must identify exactly one Candidacy")
        candidacy = updated.loc[target].iloc[0]
        if candidacy["candidate_name"] != row["candidate_name"]:
            raise ValueError("campaign suspension curation candidate name mismatch")
        current_mayoral = (
            candidacy["office_type"] == "mayor"
            and candidacy["represented_body"] == _TORONTO_COUNCIL
            and int(candidacy["election_year"]) == _CURRENT_ELECTION_YEAR
        )
        if not current_mayoral:
            raise ValueError(
                "campaign suspension curation must identify a 2026 Toronto mayoral Candidacy"
            )
        if suspended_on > date.fromisoformat(str(candidacy["election_date"])):
            raise ValueError("campaign suspension curation is dated after election day")
        updated.loc[target, "campaign_suspended_on"] = row["campaign_suspended_on"]
    return updated
