"""The City Clerk's 2026 Declaration of Results applied to the certified 2026 roster."""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results import pending_candidates
from toronto_election_results.pending_candidates import (
    DECLARATION_URL,
    apply_declaration_results,
    load_declaration_results,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DECLARATION = REPO_ROOT / "data" / "reference" / "results_2026_declaration.csv"


def _declaration_rows(*rows):
    return pd.DataFrame(
        [
            {
                "board_id": board,
                "office_type": office,
                "official_district_id": district,
                "candidate_name": name,
                "votes": votes,
                "marked_elected": marked,
                "acclaimed": acclaimed,
                "page": "1",
                "source_url": DECLARATION_URL,
            }
            for board, office, district, name, votes, marked, acclaimed in rows
        ]
    )


def test_pinned_declaration_covers_the_whole_field_with_one_winner_per_contest():
    declaration = load_declaration_results(DECLARATION)
    assert len(declaration) == 361
    contests = declaration.groupby(["represented_body", "office_type", "official_district_id"])
    assert contests.ngroups == 55
    assert contests["elected"].sum().eq(1).all()
    assert int(declaration["acclaimed"].sum()) == 4
    mayor = declaration.loc[declaration["office_type"].eq("mayor")].set_index("candidate_name")
    assert len(mayor) == 53
    assert mayor.loc["Olivia Chow", "votes"] == 532201
    assert bool(mayor.loc["Olivia Chow", "elected"])
    # The declaration prints no "X" in Viamonde Ward 3; its top vote-getter is elected.
    viamonde = declaration.loc[
        declaration["represented_body"].eq("conseil_scolaire_viamonde")
        & declaration["official_district_id"].eq("3")
    ].set_index("candidate_name")
    assert not viamonde["marked_elected"].any()
    assert viamonde["elected"].to_dict() == {
        "Anna-Karyna Ruszkowski": True,
        "Jean-François L'Heureux": False,
    }


def test_a_printed_mark_that_disagrees_with_the_votes_is_rejected(tmp_path):
    path = tmp_path / "declaration.csv"
    _declaration_rows(
        ("city", "councillor", "ward-1", "A Person", "10", "false", "false"),
        ("city", "councillor", "ward-1", "B Person", "5", "true", "false"),
    ).to_csv(path, index=False)
    with pytest.raises(ValueError, match="marks"):
        load_declaration_results(path)


def test_an_unmarked_winner_outside_the_known_omission_is_rejected(tmp_path):
    path = tmp_path / "declaration.csv"
    _declaration_rows(
        ("city", "councillor", "ward-1", "A Person", "10", "false", "false"),
        ("city", "councillor", "ward-1", "B Person", "5", "false", "false"),
    ).to_csv(path, index=False)
    with pytest.raises(ValueError, match="marks"):
        load_declaration_results(path)


def test_a_first_place_tie_is_rejected(tmp_path):
    path = tmp_path / "declaration.csv"
    _declaration_rows(
        ("city", "councillor", "ward-1", "A Person", "10", "true", "false"),
        ("city", "councillor", "ward-1", "B Person", "10", "false", "false"),
    ).to_csv(path, index=False)
    with pytest.raises(ValueError, match="tie"):
        load_declaration_results(path)


def test_the_declaration_must_match_the_roster_one_to_one(tmp_path):
    path = tmp_path / "declaration.csv"
    _declaration_rows(
        ("city", "mayor", "city", "A Person", "10", "true", "false"),
    ).to_csv(path, index=False)
    roster = pending_candidates._pending_frame(
        [
            pending_candidates._candidate_row(
                {"office": 1, "name": "PERSON, B", "firstName": "B", "lastName": "Person"},
                office_type="mayor",
                official_district_id="city",
                district_name="City of Toronto",
                source_detail=pending_candidates.MAYOR_CANDIDATES_URL,
            )
        ]
    )
    with pytest.raises(ValueError, match="disagree"):
        apply_declaration_results(roster, load_declaration_results(path))


def test_published_2026_results_are_final_and_match_the_declaration():
    results = pd.read_csv(REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string")
    current = results.loc[results["election_date"].eq("2026-10-26")]
    assert len(current) == 361
    assert current["result_status"].eq("final").all()
    assert current["source_resource"].eq("2026 Municipal Election — Declaration of Results").all()
    assert current["source_detail"].str.endswith(DECLARATION_URL).all()
    assert current["elected"].eq("True").sum() == 55
    declared = load_declaration_results(DECLARATION)
    published = (
        current.loc[current["acclaimed"].ne("True")]
        .assign(votes=lambda frame: frame["votes"].astype(float).astype(int))
        .groupby("represented_body")["votes"]
        .sum()
        .to_dict()
    )
    expected = declared.groupby("represented_body")["votes"].sum().astype(int).to_dict()
    assert published == expected
