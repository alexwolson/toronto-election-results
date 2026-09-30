import pandas as pd
import pytest

from toronto_election_results.campaign_url_curations import apply_campaign_url_curations


def test_curated_campaign_link_survives_roster_refresh(tmp_path):
    path = tmp_path / "curations.csv"
    path.write_text(
        "candidacy_id,candidate_name,campaign_url,evidence_url,verified_on,rationale\n"
        "can_katie,Katie Andrachuk,https://www.votekatie.ca/,"
        "https://www.votekatie.ca/,2026-09-30,Candidate request\n"
    )
    official = pd.DataFrame(
        {
            "candidacy_id": ["can_katie", "can_other"],
            "candidate_name": ["Katie Andrachuk", "Other Candidate"],
            "campaign_url": [None, "https://other.example/"],
        }
    )
    updated = apply_campaign_url_curations(official, path)
    assert updated["campaign_url"].tolist() == [
        "https://www.votekatie.ca/",
        "https://other.example/",
    ]
    assert pd.isna(official.loc[0, "campaign_url"])
    assert apply_campaign_url_curations(official, path).equals(updated)


@pytest.mark.parametrize("problem", ["unknown", "duplicate", "wrong_name", "invalid_url"])
def test_rejects_incorrect_curation_targets(tmp_path, problem):
    path = tmp_path / "curations.csv"
    url = "javascript:alert(1)" if problem == "invalid_url" else "https://www.votekatie.ca/"
    path.write_text(
        "candidacy_id,candidate_name,campaign_url,evidence_url,verified_on,rationale\n"
        f"can_katie,Katie Andrachuk,{url},https://www.votekatie.ca/,2026-09-30,Request\n"
    )
    results = pd.DataFrame(
        {
            "candidacy_id": ["can_unknown" if problem == "unknown" else "can_katie"],
            "candidate_name": ["Other" if problem == "wrong_name" else "Katie Andrachuk"],
            "campaign_url": [None],
        }
    )
    if problem == "duplicate":
        results = pd.concat([results, results], ignore_index=True)
    with pytest.raises(ValueError):
        apply_campaign_url_curations(results, path)
