"""Outside identifiers for People, so the release can be joined to other career files.

`data/reference/person_external_ids.csv` is built by `scripts/build_person_external_ids.py`. Each
row gives one identifier in one scheme for one Person, how it was matched and where it can be
checked. The build publishes the rows as they are, after checking that each names an active
Person and that no identifier belongs to two Persons.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

EXTERNAL_IDS_FILENAME = "person_external_ids.csv"
EXTERNAL_ID_COLUMNS = (
    "person_id",
    "scheme",
    "external_id",
    "basis",
    "source_url",
    "retrieved_on",
)
SCHEMES = frozenset({"wikidata", "parlinfo", "house_of_commons", "ontario_legislature"})


def _empty() -> pd.DataFrame:
    return pd.DataFrame({column: pd.Series(dtype="string") for column in EXTERNAL_ID_COLUMNS})


def read_external_ids(path: Path) -> pd.DataFrame | None:
    """Read and check the external-ID reference, or return None when it is absent."""

    if not path.is_file():
        return None
    frame = pd.read_csv(path, dtype="string", keep_default_na=False)
    if tuple(frame.columns) != EXTERNAL_ID_COLUMNS:
        raise ValueError(f"{path.name} columns must be {', '.join(EXTERNAL_ID_COLUMNS)}")
    blank = frame.eq("").any(axis=1)
    if blank.any():
        raise ValueError(f"{path.name} has blank cells in row {int(blank.idxmax()) + 2}")
    unknown = sorted(set(frame["scheme"]) - SCHEMES)
    if unknown:
        raise ValueError(f"{path.name} has unknown schemes: {', '.join(unknown)}")
    if frame.duplicated(["person_id", "scheme"]).any():
        raise ValueError(f"{path.name} gives a Person two IDs in one scheme")
    if frame.duplicated(["scheme", "external_id"]).any():
        raise ValueError(f"{path.name} gives one ID to two Persons")
    return frame


def build_person_external_ids(
    people: pd.DataFrame, external_ids: pd.DataFrame | None
) -> pd.DataFrame:
    """Return the published table, failing if an ID names a Person who is not active."""

    if external_ids is None or external_ids.empty:
        return _empty()
    active = set(people.loc[people["identity_status"].eq("active"), "person_id"].astype(str))
    stale = sorted(set(external_ids["person_id"].astype(str)) - active)
    if stale:
        raise ValueError(
            "external IDs name Persons that are not active; rebuild "
            f"{EXTERNAL_IDS_FILENAME}: {', '.join(stale[:5])}"
        )
    return (
        external_ids.loc[:, list(EXTERNAL_ID_COLUMNS)]
        .sort_values(["person_id", "scheme"], kind="stable")
        .reset_index(drop=True)
    )
