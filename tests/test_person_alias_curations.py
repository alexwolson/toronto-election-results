import pandas as pd
import pytest

from toronto_election_results.person_alias_curations import (
    apply_person_alias_curations,
    load_person_alias_curations,
)


def _people():
    return pd.DataFrame(
        [
            {
                "person_id": "per_11111111111111111111111111111111",
                "preferred_name": "Existing Person",
                "identity_status": "active",
                "redirect_to_person_id": pd.NA,
                "created_release": "v1",
            }
        ]
    )


def _write_curations(path, *, action="create", person_id=None):
    pd.DataFrame(
        [
            {
                "person_id": person_id or "per_22222222222222222222222222222222",
                "person_action": action,
                "preferred_name": "New Person",
                "reported_name": "New Person",
                "evidence_urls": "https://example.com/evidence",
                "rationale": "A first-party source establishes the identity.",
            }
        ]
    ).to_csv(path, index=False)


def test_person_alias_curations_create_a_persistent_person_idempotently(tmp_path):
    path = tmp_path / "person_alias_curations.csv"
    _write_curations(path)
    curations = load_person_alias_curations(path)

    first = apply_person_alias_curations(_people(), curations, release_id="v2")
    second = apply_person_alias_curations(first, curations, release_id="v3")

    created = second.loc[second["person_id"].eq("per_22222222222222222222222222222222")].iloc[0]
    assert len(second) == 2
    assert created["preferred_name"] == "New Person"
    assert created["identity_status"] == "active"
    assert created["created_release"] == "v2"


def test_person_alias_curations_reject_an_absent_existing_person(tmp_path):
    path = tmp_path / "person_alias_curations.csv"
    _write_curations(
        path,
        action="existing",
        person_id="per_33333333333333333333333333333333",
    )

    with pytest.raises(ValueError, match="curated existing Person is absent"):
        apply_person_alias_curations(_people(), load_person_alias_curations(path), release_id="v2")


def test_person_alias_curations_require_https_evidence(tmp_path):
    path = tmp_path / "person_alias_curations.csv"
    _write_curations(path)
    text = path.read_text().replace("https://", "http://")
    path.write_text(text)

    with pytest.raises(ValueError, match="evidence_urls must contain HTTPS"):
        load_person_alias_curations(path)
