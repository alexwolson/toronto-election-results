"""Evidence-backed Person aliases that are not preserved by result rows."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

PERSON_ALIAS_CURATIONS_FILENAME = "person_alias_curations.csv"
_PERSON_ID = re.compile(r"per_[0-9a-f]{32}\Z")
_COLUMNS = [
    "person_id",
    "person_action",
    "preferred_name",
    "reported_name",
    "evidence_urls",
    "rationale",
]


def _text(value: object) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        return ""
    return " ".join(unicodedata.normalize("NFKC", str(value)).split())


def name_key(value: object) -> str:
    """Return the exact normalized lookup key shared with release consumers."""

    return _text(value).casefold()


def load_person_alias_curations(path: str | Path) -> pd.DataFrame:
    """Load and validate the auditable aliases used by downstream evidence feeds."""

    source = Path(path)
    rows = pd.read_csv(source, dtype="string", keep_default_na=False)
    missing = sorted(set(_COLUMNS) - set(rows.columns))
    if missing:
        raise ValueError(f"person alias curations are missing columns: {', '.join(missing)}")

    rows = rows[_COLUMNS].copy()
    for column in _COLUMNS:
        rows[column] = rows[column].map(_text).astype("string")
        if rows[column].eq("").any():
            raise ValueError(f"person alias curations.{column} cannot be blank")
    if invalid := rows.loc[~rows["person_id"].str.fullmatch(_PERSON_ID), "person_id"].tolist():
        raise ValueError(f"invalid curated person_id: {invalid[0]!r}")
    invalid_actions = rows.loc[
        ~rows["person_action"].isin({"existing", "create"}), "person_action"
    ].tolist()
    if invalid_actions:
        raise ValueError(f"invalid person_action: {invalid_actions[0]!r}")
    for evidence in rows["evidence_urls"]:
        urls = [url.strip() for url in evidence.split("|")]
        if any(not url.startswith("https://") for url in urls):
            raise ValueError("person alias curation evidence_urls must contain HTTPS URLs")

    person_metadata = rows.groupby("person_id", sort=False)[
        ["person_action", "preferred_name"]
    ].nunique()
    if (person_metadata > 1).any(axis=None):
        raise ValueError("a curated Person must have one action and preferred name")
    aliases = rows.assign(_name_key=rows["reported_name"].map(name_key))
    alias_people = aliases.groupby("_name_key")["person_id"].nunique()
    if (alias_people > 1).any():
        raise ValueError("a curated alias cannot identify multiple People")
    return rows


def apply_person_alias_curations(
    people: pd.DataFrame, curations: pd.DataFrame, *, release_id: str
) -> pd.DataFrame:
    """Ensure every curated alias target is an active, persistent Person."""

    if curations.empty:
        return people.copy()
    required_people = {
        "person_id",
        "preferred_name",
        "identity_status",
        "redirect_to_person_id",
        "created_release",
    }
    if missing := sorted(required_people - set(people.columns)):
        raise ValueError(f"people registry is missing columns: {', '.join(missing)}")
    if not str(release_id).strip():
        raise ValueError("release_id cannot be blank")

    output = people.copy()
    for row in curations.drop_duplicates("person_id").itertuples(index=False):
        matches = output["person_id"].eq(row.person_id)
        if matches.any():
            person = output.loc[matches].iloc[0]
            if person["identity_status"] != "active":
                raise ValueError(f"curated Person is not active: {row.person_id!r}")
            if name_key(person["preferred_name"]) != name_key(row.preferred_name):
                raise ValueError(f"curated preferred_name disagrees for {row.person_id!r}")
            continue
        if row.person_action != "create":
            raise ValueError(f"curated existing Person is absent: {row.person_id!r}")
        output.loc[len(output)] = {
            "person_id": row.person_id,
            "preferred_name": row.preferred_name,
            "identity_status": "active",
            "redirect_to_person_id": pd.NA,
            "created_release": release_id,
        }
    return output.sort_values("person_id", kind="stable").reset_index(drop=True)
