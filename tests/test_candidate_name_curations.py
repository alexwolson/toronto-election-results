"""Reviewed display names for Candidacies the parser cannot split by rule."""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.candidate_name_curations import (
    CANDIDATE_NAME_CURATIONS_FILENAME,
    apply_candidate_name_curations,
)

REPO_ROOT = Path(__file__).parents[1]
HEADER = (
    "event_id,represented_body,official_district_id,candidate_name_raw,candidate_name,"
    "evidence_url,rationale\n"
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": ["evt_1", "evt_1"],
            "represented_body": ["Toronto District School Board", "toronto_city_council"],
            "official_district_id": [11, "ward-11"],
            "candidate_name_raw": ["Chernos Lin Rachel", "Ford Rob"],
            "candidate_name": ["Lin Rachel Chernos", "Rob Ford"],
        }
    )


def _write(tmp_path: Path, row: str) -> Path:
    path = tmp_path / CANDIDATE_NAME_CURATIONS_FILENAME
    path.write_text(HEADER + row + "\n", encoding="utf-8")
    return path


def test_curation_reorders_the_display_name(tmp_path: Path):
    path = _write(
        tmp_path,
        "evt_1,toronto_district_school_board,11,Chernos Lin Rachel,Rachel Chernos Lin,"
        "https://example.test/declaration.pdf,Declared given name first.",
    )

    (out,) = apply_candidate_name_curations([_frame()], path)

    assert out["candidate_name"].tolist() == ["Rachel Chernos Lin", "Rob Ford"]


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (
            (
                "evt_1,toronto_district_school_board,11,Chernos Lin Rachel,Rachel Chernos,"
                "https://example.test/d.pdf,Drops a word."
            ),
            "must reorder the words",
        ),
        (
            (
                "evt_1,toronto_district_school_board,12,Chernos Lin Rachel,Rachel Chernos Lin,"
                "https://example.test/d.pdf,Wrong ward."
            ),
            "matched 0 Candidacies",
        ),
        (
            (
                "evt_1,toronto_city_council,ward-11,Ford Rob,Rob Ford,"
                "https://example.test/d.pdf,Already right."
            ),
            "no longer needed",
        ),
        (
            (
                "evt_1,toronto_district_school_board,11,Chernos Lin Rachel,Rachel Chernos Lin,"
                "http://example.test/d.pdf,Not HTTPS."
            ),
            "invalid candidate name evidence URL",
        ),
    ],
)
def test_curation_fails_closed(tmp_path: Path, row: str, message: str):
    with pytest.raises(ValueError, match=message):
        apply_candidate_name_curations([_frame()], _write(tmp_path, row))


def test_published_names_follow_the_curations():
    curations = pd.read_csv(
        REPO_ROOT / "data" / "reference" / CANDIDATE_NAME_CURATIONS_FILENAME, dtype="string"
    )
    results = pd.read_csv(REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string")
    published = curations.merge(
        results,
        on=["event_id", "represented_body", "official_district_id", "candidate_name_raw"],
        suffixes=("", "_published"),
    )

    assert len(curations) == len(published) == 39
    assert published["candidate_name"].eq(published["candidate_name_published"]).all()
