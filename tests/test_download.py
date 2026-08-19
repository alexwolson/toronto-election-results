"""Tests for the resource-selection logic used by the downloader.

The live HTTP fetch is glue (exercised by running the module); the risk is in *which* CKAN
resources get selected, so that pure logic is tested against a saved package_show response.
"""

import json
from pathlib import Path

from toronto_election_results.download import filename_for, select_resources

RESULTS_PKG = Path(__file__).parent / "fixtures" / "ckan" / "election-results-official.json"


def _results_resources():
    pkg = json.loads(RESULTS_PKG.read_text())
    return pkg["result"]["resources"]


def test_select_by_regex_picks_the_six_year_zips():
    picked = select_resources(_results_resources(), name_regex=r"^\d{4}-results$")
    names = sorted(r["name"] for r in picked)
    assert names == [
        "2003-results",
        "2006-results",
        "2010-results",
        "2014-results",
        "2018-results",
        "2022-results",
    ]


def test_select_by_name_contains_is_case_insensitive():
    picked = select_resources(_results_resources(), name_contains="2014")
    assert [r["name"] for r in picked] == ["2014-results"]


def test_select_by_format():
    picked = select_resources(_results_resources(), formats={"zip"})
    assert len(picked) == 6


def test_filename_for_uses_url_basename_when_it_has_an_extension():
    res = {"name": "2014-results", "format": "ZIP", "url": "https://x/download/2014-results.zip"}
    assert filename_for(res) == "2014-results.zip"


def test_filename_for_falls_back_to_slug_plus_format_for_datastore_dumps():
    res = {
        "name": "Councillors Meeting Attendance 2018-2022",
        "format": "CSV",
        "url": "https://x/datastore/dump/abc123",
    }
    assert filename_for(res) == "councillors-meeting-attendance-2018-2022.csv"
