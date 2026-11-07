"""The evidence basis published on each Candidacy-to-Person link."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.link_basis import (
    EVIDENCE_BASES,
    LINK_BASIS_FILENAME,
    add_evidence_basis,
    read_link_basis,
)

REPO_ROOT = Path(__file__).parents[1]
OUT = REPO_ROOT / "data" / "out"
REFERENCE = REPO_ROOT / "data" / "reference"

# Reform's members voted in 2000 to form the Canadian Alliance, which ran in its place that year.
SUCCESSOR_PARTIES = {("reform", "canadian alliance")}
# Words that the authorities' Party labels add or drop between years, such as "Reform Party of
# Canada" (1993) and "Reform" (1997), or "LIBERTARIAN PARTY" (1995) and "Ontario Libertarian Party".
_LABEL_WORDS = re.compile(r"\b(party|of|canada|ontario|the)\b|[()]")


def _links() -> pd.DataFrame:
    return pd.read_csv(OUT / "candidacy_person_links.csv", dtype=str, keep_default_na=False)


def _results() -> pd.DataFrame:
    return pd.read_csv(OUT / "election_results.csv", dtype=str, keep_default_na=False)


def test_every_active_confirmed_link_has_a_basis_and_no_other_link_does():
    links = _links()
    confirmed = links["link_status"].eq("confirmed") & links["valid_to_release"].eq("")
    assert links.loc[confirmed, "evidence_basis"].isin(EVIDENCE_BASES).all()
    assert links.loc[~confirmed, "evidence_basis"].eq("").all()


def test_automatic_methods_have_a_fixed_basis():
    links = _links()
    confirmed = links.loc[links["link_status"].eq("confirmed")]
    by_method = confirmed.groupby("method")["evidence_basis"].unique().map(set).to_dict()
    assert by_method["official_candidacy_record"] == {"own_record"}
    assert by_method["official_incumbent_continuity"] == {"official_record"}
    assert by_method["municipal_authoritative_roster_exact_name"] == {"official_record"}
    for method in (
        "curated_official_cross_event_identity",
        "curated_person_redirect",
        "curated_review_confirmed",
    ):
        assert by_method[method] <= {"official_record", "person_specific_source", "structural"}


def test_the_recorded_basis_file_is_well_formed():
    table = read_link_basis(REFERENCE / LINK_BASIS_FILENAME)
    assert set(table["link_source"]) == {"assertion", "disposition"}
    assert table.loc[table["link_source"].eq("assertion"), "reviewer"].eq("").all()
    research = table["label_source"].ne("rationale")
    assert table.loc[research, "label_source"].str.startswith("docs/research/").all()
    for path in set(table.loc[research, "label_source"]):
        assert (REPO_ROOT / path).is_file(), path


def _general_dates(results: pd.DataFrame) -> dict[str, list[pd.Timestamp]]:
    events = pd.read_csv(OUT / "election_events.csv", dtype=str, keep_default_na=False)
    general = events.loc[events["election_type"].eq("general")]
    return {
        authority: sorted(pd.to_datetime(group["election_date"]))
        for authority, group in general.groupby("election_authority")
    }


def _party_key(label: str) -> str:
    return " ".join(_LABEL_WORDS.sub(" ", label.casefold()).split())


def _same_party(first: str, second: str) -> bool:
    first, second = _party_key(first), _party_key(second)
    if first == second:
        return True
    return (first, second) in SUCCESSOR_PARTIES or (second, first) in SUCCESSOR_PARTIES


def test_structural_links_meet_the_structural_test():
    """Each structural link has a run of its Person that it continues under the stated rule.

    Same office type: at most one general election between, and the same Party where Parties
    apply. A House of Commons run and an Ontario legislature run: a riding of the same name
    within two years. Name commonness and ward overlap are judged by the reviewers and are not
    retested here.
    """

    links = _links()
    results = _results().set_index("candidacy_id")
    results["date"] = pd.to_datetime(results["election_date"])
    general = _general_dates(results)
    party_ids = results["party_id"]
    structural = links.loc[links["evidence_basis"].eq("structural"), "candidacy_id"]
    failures = []
    for candidacy_id in structural:
        run = results.loc[candidacy_id]
        others = results.loc[
            results["person_id"].eq(run["person_id"]) & (results.index != candidacy_id)
        ]
        continues = False
        for _, other in others.iterrows():
            first, last = sorted([run["date"], other["date"]])
            if other["office_type"] == run["office_type"]:
                between = sum(first < day < last for day in general[run["election_authority"]])
                partisan = run["office_type"] in {"mp", "mpp"}
                party = not partisan or (
                    party_ids[candidacy_id] == other["party_id"]
                    or _same_party(run["party_name"], other["party_name"])
                )
                continues = between <= 1 and party
            elif {run["office_type"], other["office_type"]} == {"mp", "mpp"}:
                continues = (last - first).days <= 2 * 366 and (
                    run["district_name"] == other["district_name"]
                )
            if continues:
                break
        if not continues:
            failures.append((run["candidate_name"], run["election_year"], run["office_type"]))
    assert failures == []


def _link(candidacy_id: str, method: str, evidence: dict, reviewer: str) -> dict:
    return {
        "candidacy_id": candidacy_id,
        "person_id": "per_1",
        "link_status": "confirmed",
        "method": method,
        "evidence": json.dumps(evidence),
        "reviewer": reviewer,
        "valid_from_release": "2026-09-30",
        "valid_to_release": pd.NA,
    }


def _basis(rows: list[tuple[str, str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [(*row, "rationale") for row in rows],
        columns=["link_source", "key", "reviewer", "evidence_basis", "label_source"],
    )


def test_add_evidence_basis_labels_each_method():
    links = pd.DataFrame(
        [
            _link("can_a", "official_candidacy_record", {}, "identity_review.bootstrap/v1"),
            _link(
                "can_b",
                "curated_official_cross_event_identity",
                {"assertion_id": "ast-b"},
                "identity_curations/v1",
            ),
            _link("can_c", "curated_review_confirmed", {}, "pass-c"),
        ]
    )
    basis = _basis(
        [
            ("assertion", "ast-b", "", "person_specific_source"),
            ("disposition", "can_c", "pass-c", "structural"),
        ]
    )
    out = add_evidence_basis(links, basis)
    assert out["evidence_basis"].tolist() == ["own_record", "person_specific_source", "structural"]


def test_add_evidence_basis_fails_without_a_recorded_basis():
    links = pd.DataFrame([_link("can_c", "curated_review_confirmed", {}, "pass-c")])
    with pytest.raises(ValueError, match="no recorded evidence basis"):
        add_evidence_basis(links, _basis([]))


def test_add_evidence_basis_fails_on_a_basis_that_matches_no_link():
    links = pd.DataFrame([_link("can_a", "official_candidacy_record", {}, "bootstrap")])
    basis = _basis([("assertion", "ast-gone", "", "structural")])
    with pytest.raises(ValueError, match="matches no published link"):
        add_evidence_basis(links, basis)
