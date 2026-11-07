"""What each confirmed Candidacy-to-Person link rests on, published as ``evidence_basis``.

A link's ``method`` says which process made it. ``evidence_basis`` says what kind of evidence
ties the Candidacy to its Person, so users can keep only links that a source confirms:

- ``own_record``: the Person was created from this Candidacy, so nothing is joined;
- ``official_record``: an official record ties the runs, being an election authority's
  incumbency flag, a Council roster, or the same archive record printed twice;
- ``person_specific_source``: a source about the person ties the runs, such as a biography,
  a news report, a candidate profile, an official record of service, or a distinctive fact
  such as an occupation that the candidate records give for each run;
- ``structural``: no source about the person was found, and the runs are joined under the
  structural rules in ``docs/build-notes.md``.

The basis of each curated link is recorded in ``data/reference/identity_link_basis.csv``, by
identity assertion or by review disposition. The build fails if a confirmed curated link has no
recorded basis or if a recorded basis matches no published link.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

LINK_BASIS_FILENAME = "identity_link_basis.csv"
LINK_BASIS_COLUMNS = ("link_source", "key", "reviewer", "evidence_basis", "label_source")
EVIDENCE_BASES = frozenset(
    {"own_record", "official_record", "person_specific_source", "structural"}
)
_CURATED_BASES = frozenset({"official_record", "person_specific_source", "structural"})
_AUTOMATIC_BASES = {
    "official_candidacy_record": "own_record",
    "official_incumbent_continuity": "official_record",
    "municipal_authoritative_roster_exact_name": "official_record",
}
_ASSERTION_METHODS = frozenset({"curated_official_cross_event_identity", "curated_person_redirect"})
_DISPOSITION_METHOD = "curated_review_confirmed"


def read_link_basis(path: Path) -> pd.DataFrame:
    """Read and validate the recorded basis of each curated link."""

    if not path.is_file():
        raise ValueError(f"identity link basis source is missing: {path}")
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = sorted(set(LINK_BASIS_COLUMNS) - set(table.columns))
    if missing:
        raise ValueError(f"{path.name} is missing: {', '.join(missing)}")
    table = table.loc[:, list(LINK_BASIS_COLUMNS)]
    sources = table["link_source"]
    if not sources.isin({"assertion", "disposition"}).all():
        bad = table.loc[~sources.isin({"assertion", "disposition"}), "link_source"].iloc[0]
        raise ValueError(f"unknown link_source in {path.name}: {bad!r}")
    if not table["evidence_basis"].isin(_CURATED_BASES).all():
        bad = table.loc[~table["evidence_basis"].isin(_CURATED_BASES), "evidence_basis"].iloc[0]
        raise ValueError(f"unknown evidence_basis in {path.name}: {bad!r}")
    if table["key"].str.strip().eq("").any() or table["label_source"].str.strip().eq("").any():
        raise ValueError(f"{path.name} requires a key and a label_source on every row")
    dispositions = sources.eq("disposition")
    if table.loc[dispositions, "reviewer"].str.strip().eq("").any():
        raise ValueError(f"{path.name} requires the reviewer of every disposition row")
    if table.loc[~dispositions, "reviewer"].ne("").any():
        raise ValueError(f"{path.name} gives a reviewer only for disposition rows")
    if table.duplicated(["link_source", "key", "reviewer"]).any():
        raise ValueError(f"{path.name} has a duplicate row")
    return table


def add_evidence_basis(links: pd.DataFrame, basis: pd.DataFrame) -> pd.DataFrame:
    """Return the links with ``evidence_basis`` set on every active confirmed link."""

    out = links.drop(columns=["evidence_basis"], errors="ignore").copy()
    by_assertion = {
        row.key: row.evidence_basis
        for row in basis.loc[basis["link_source"].eq("assertion")].itertuples(index=False)
    }
    by_disposition = {
        (row.key, row.reviewer): row.evidence_basis
        for row in basis.loc[basis["link_source"].eq("disposition")].itertuples(index=False)
    }
    used_assertions: set[str] = set()
    used_dispositions: set[tuple[str, str]] = set()
    values: list[object] = []
    for row in out.itertuples(index=False):
        if row.link_status != "confirmed" or pd.notna(row.valid_to_release):
            values.append(pd.NA)
            continue
        method = str(row.method)
        if method in _AUTOMATIC_BASES:
            values.append(_AUTOMATIC_BASES[method])
        elif method in _ASSERTION_METHODS:
            assertion_id = str(json.loads(str(row.evidence))["assertion_id"])
            if assertion_id not in by_assertion:
                raise ValueError(
                    f"identity assertion {assertion_id!r} has no recorded evidence basis"
                )
            used_assertions.add(assertion_id)
            values.append(by_assertion[assertion_id])
        elif method == _DISPOSITION_METHOD:
            key = (str(row.candidacy_id), str(row.reviewer))
            if key not in by_disposition:
                raise ValueError(
                    f"review disposition {key[1]!r} for {key[0]!r} has no recorded evidence basis"
                )
            used_dispositions.add(key)
            values.append(by_disposition[key])
        else:
            raise ValueError(f"no evidence basis rule for link method {method!r}")
    unused = sorted(set(by_assertion) - used_assertions) + sorted(
        f"{candidacy_id} ({reviewer})"
        for candidacy_id, reviewer in set(by_disposition) - used_dispositions
    )
    if unused:
        raise ValueError(f"a recorded evidence basis matches no published link: {unused[0]!r}")
    out["evidence_basis"] = pd.Series(values, index=out.index, dtype="string")
    return out
