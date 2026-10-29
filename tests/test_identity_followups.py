"""Identity follow-ups of 2026-10-29 (docs/research/identity-followups-2026-10-29.md)."""

from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.identity_dispositions import read_identity_review_decisions

REPO_ROOT = Path(__file__).parents[1]
REVIEWER = "identity-followups-2026-10-29"

# Candidacy -> (target Person, evidence URL that carries the bridge)
CONFIRMED = {
    # Tony Letra, 1997 council Ward 21 -> the 2010 Ward 17 record
    "can_345785ba33dd545397a7a15ec83f710b": (
        "per_0649ecb7cb135ca7aee48b5b74b79fb3",
        "https://movimentoperpetuo.ca/political-flyers-of-portuguese-canadian-candidates/",
    ),
    # Elizabeth Hill, 2006 TDSB Ward 6 -> the 2000/2003 Ward 6 trustee
    "can_8e6c404ce2545b19b3d5413a881d754b": (
        "per_df78a26908df56398f6feaaa81ef11a4",
        "https://communist-party.ca/?p=1804",
    ),
    # Elizabeth Hill, 2015 Communist candidate in Don Valley West -> the same trustee
    "can_72c3041be0cd59bba264c3eaf28436a3": (
        "per_df78a26908df56398f6feaaa81ef11a4",
        "https://en.wikipedia.org/wiki/Communist_Party_of_Canada_candidates_in_the_2015_Canadian_federal_election",
    ),
    # Scott Harrison, 2012-02-27 TDSB Ward 20 by-election -> the 2003-2014 Ward 19 record
    "can_8eb0b96fd86159348a661a484ec38be0": (
        "per_cf67e953cc5d5813be347c92214ea37d",
        "https://www.theglobeandmail.com/news/toronto/former-trustee-to-run-in-tdsb-by-election/article4097986",
    ),
}


@pytest.fixture(scope="module")
def published() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    results = pd.read_csv(
        REPO_ROOT / "data" / "out" / "election_results.csv", dtype="string"
    ).set_index("candidacy_id")
    links = pd.read_csv(REPO_ROOT / "data" / "out" / "candidacy_person_links.csv", dtype="string")
    decisions = read_identity_review_decisions(
        REPO_ROOT / "data" / "reference" / "identity_review_dispositions.csv"
    ).set_index("candidacy_id")
    return results, links, decisions


@pytest.mark.parametrize("candidacy_id", sorted(CONFIRMED))
def test_followup_confirmations_publish_the_reviewed_person(published, candidacy_id):
    results, links, decisions = published
    person_id, bridge_url = CONFIRMED[candidacy_id]

    decision = decisions.loc[candidacy_id]
    assert decision["target_person_id"] == person_id
    assert decision["decision"] == "confirmed"
    assert decision["confidence"] == "high"
    assert decision["reviewer"] == REVIEWER
    assert bridge_url in decision["evidence_urls"].split(";")

    assert results.loc[candidacy_id, "person_id"] == person_id
    history = links.loc[links["candidacy_id"].eq(candidacy_id)]
    active = history.loc[history["valid_to_release"].isna()]
    assert active[["person_id", "link_status", "reviewer"]].values.tolist() == [
        [person_id, "confirmed", REVIEWER]
    ]
    # The earlier unresolved review of the same target stays visible as closed history.
    closed = history.loc[history["valid_to_release"].notna()]
    assert ((closed["link_status"] == "unresolved") & (closed["person_id"] == person_id)).any()
