"""Every published record cites its source by URL, not by a download-cache path."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from toronto_election_results.assemble import BY_ELECTIONS, ELECTIONS
from toronto_election_results.official_sources import (
    BY_ELECTION_RESULT_URLS,
    COUNCIL_RECORD_URLS,
    GENERAL_RESULT_URLS,
)

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
CACHE_PATH = r"data/(?:interim|raw)/"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / f"{name}.csv", dtype=str, keep_default_na=False)


def test_every_council_file_has_a_published_url():
    assert set(GENERAL_RESULT_URLS) == {
        year for year, (_, kind, _, _) in ELECTIONS.items() if kind == "general"
    }
    by_election_files = {filename for _, _, filename, _, _ in BY_ELECTIONS}
    assert by_election_files | {"2023_office_of_the_mayor.xlsx"} == set(BY_ELECTION_RESULT_URLS)
    for url in [*GENERAL_RESULT_URLS.values(), *BY_ELECTION_RESULT_URLS.values()]:
        assert url.startswith("https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/")
    assert all(url.endswith(name) for name, url in COUNCIL_RECORD_URLS.items())


def test_no_published_record_cites_the_download_cache():
    for name, column in (
        ("election_results", "source_detail"),
        ("contests", "source_detail"),
        ("office_tenures", "source_detail"),
        ("candidacy_person_links", "evidence"),
    ):
        table = _read(name)
        assert not table[column].str.contains(CACHE_PATH, regex=True).any(), name


def test_council_rows_name_the_workbook_inside_the_results_zip():
    results = _read("election_results")
    council = results.loc[
        results["represented_body"].eq("toronto_city_council")
        & results["election_type"].eq("general")
        & results["election_date"].between("2003-01-01", "2022-12-31")
    ]
    zipped = council["source_detail"].str.extract(r"^(https://\S+\.zip) :: (.+\.xlsx?)$")
    assert zipped.notna().all().all()
    assert set(zipped[0]) == set(GENERAL_RESULT_URLS.values())
