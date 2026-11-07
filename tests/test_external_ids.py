"""Outside identifiers for People (`person_external_ids`)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.external_ids import (
    EXTERNAL_ID_COLUMNS,
    EXTERNAL_IDS_FILENAME,
    build_person_external_ids,
    read_external_ids,
)

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
REFERENCE = REPO_ROOT / "data" / "reference"


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _assembly_members(tenures: pd.DataFrame) -> dict[str, str]:
    ontario = tenures.loc[tenures["represented_body"].eq("ontario_legislative_assembly")]
    return {
        row.person_id: json.loads(row.source_detail)["ontario_member"]["ola_member_id"]
        for row in ontario.itertuples()
        if row.source_detail.startswith("{")
    }


def test_published_ids_cover_the_house_and_assembly_members():
    published = _read(OUT / "person_external_ids.csv")
    assert tuple(published.columns) == EXTERNAL_ID_COLUMNS
    reference = read_external_ids(REFERENCE / EXTERNAL_IDS_FILENAME)
    assert reference is not None
    assert len(published) == len(reference)
    people = _read(OUT / "people.csv")
    assert set(published["person_id"]) <= set(people["person_id"])
    tenures = _read(OUT / "office_tenures.csv")
    house = tenures.loc[tenures["represented_body"].eq("canada_house_of_commons")]
    assembly = _assembly_members(tenures)
    members = set(house["person_id"]) | set(assembly)
    by_scheme = published.groupby("scheme")["person_id"].apply(set).to_dict()
    assert by_scheme["wikidata"] <= members
    names = people.set_index("person_id")["preferred_name"]
    # Both won 2026 by-elections. The Person from Elections Ontario's tabulation keeps the
    # tabulation's FAMILY, GIVEN print as its preferred name.
    assert sorted(names[sorted(members - by_scheme["wikidata"])]) == [
        "SHABAN, FATIMA",
        "Tanveer Shahnawaz",
    ]
    ola = published.loc[published["scheme"].eq("ontario_legislature")]
    assert dict(zip(ola["person_id"], ola["external_id"], strict=True)) == assembly
    later = {
        row.person_id
        for row in house.itertuples()
        if int(json.loads(row.source_detail)["house_member"]["parliament"]) >= 36
    }
    assert by_scheme["house_of_commons"] == later
    assert by_scheme["parlinfo"] <= by_scheme["wikidata"]
    assert (
        published.loc[published["scheme"].eq("wikidata"), "external_id"].str.match(r"^Q\d+$").all()
    )
    numeric = published["scheme"].isin({"house_of_commons", "parlinfo"})
    assert published.loc[numeric, "external_id"].str.isdigit().all()


def test_house_ids_match_the_tenure_evidence():
    published = _read(OUT / "person_external_ids.csv")
    house_ids = published.loc[published["scheme"].eq("house_of_commons")]
    tenures = _read(OUT / "office_tenures.csv")
    cited = {
        (row.person_id, json.loads(row.source_detail)["house_member"].get("house_person_id"))
        for row in tenures.loc[
            tenures["represented_body"].eq("canada_house_of_commons")
        ].itertuples()
    }
    assert set(zip(house_ids["person_id"], house_ids["external_id"], strict=True)) <= cited


def _write(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / EXTERNAL_IDS_FILENAME
    pd.DataFrame(rows, columns=list(EXTERNAL_ID_COLUMNS)).to_csv(path, index=False)
    return path


def _row(person_id: str, scheme: str, external_id: str) -> dict[str, str]:
    return {
        "person_id": person_id,
        "scheme": scheme,
        "external_id": external_id,
        "basis": "test",
        "source_url": "https://example.org",
        "retrieved_on": "2026-11-07",
    }


def test_missing_reference_publishes_an_empty_table(tmp_path):
    assert read_external_ids(tmp_path / EXTERNAL_IDS_FILENAME) is None
    table = build_person_external_ids(pd.DataFrame(), None)
    assert table.empty and tuple(table.columns) == EXTERNAL_ID_COLUMNS


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([_row("per_a", "wikidata", "Q1"), _row("per_a", "wikidata", "Q2")], "two IDs"),
        ([_row("per_a", "wikidata", "Q1"), _row("per_b", "wikidata", "Q1")], "two Persons"),
        ([_row("per_a", "linkedin", "x")], "unknown schemes"),
    ],
)
def test_reference_rejects_ambiguous_rows(tmp_path, rows, message):
    with pytest.raises(ValueError, match=message):
        read_external_ids(_write(tmp_path, rows))


def test_an_id_for_a_person_who_is_not_active_fails(tmp_path):
    ids = read_external_ids(_write(tmp_path, [_row("per_gone", "wikidata", "Q1")]))
    people = pd.DataFrame({"person_id": ["per_here"], "identity_status": ["active"]})
    with pytest.raises(ValueError, match="not active"):
        build_person_external_ids(people, ids)
