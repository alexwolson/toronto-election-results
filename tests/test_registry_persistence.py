"""Release-to-release persistence for public Candidacy and Person identities."""

import pandas as pd

from toronto_election_results.release import assemble_bootstrapped_release


def _event(event_id: str, date: str, name: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": [event_id],
            "election_date": [date],
            "election_type": ["general"],
            "election_authority": ["Toronto City Clerk"],
            "represented_body": ["Toronto District School Board"],
            "office_type": ["School Board Trustee"],
            "boundary_regime": ["tdsb-example"],
            "official_district_id": ["35001"],
            "district_name": ["Example"],
            "candidate_name_raw": [name],
            "votes": [60],
            "elected": [True],
            "incumbent_reported": [False],
            "outcome_method": ["vote"],
            "coverage_status": ["complete"],
            "source_detail": [f"{event_id}.csv"],
        }
    )


def test_subsequent_release_reuses_prior_people_and_link_history():
    first = assemble_bootstrapped_release(
        [_event("event-2025", "2025-04-28", "Alex Example")],
        release_id="2026-08-20",
    )
    first_candidacy_id = first.tables.election_results["candidacy_id"].item()

    # A non-derived audited identifier makes it observable that the second build
    # consumed the prior registry instead of merely recreating bootstrap output.
    prior_people = first.tables.people.copy()
    old_person_id = prior_people["person_id"].item()
    prior_people.loc[:, "person_id"] = "per_audited_persistent"
    prior_links = first.tables.candidacy_person_links.copy()
    prior_links.loc[prior_links["person_id"].eq(old_person_id), "person_id"] = (
        "per_audited_persistent"
    )

    second = assemble_bootstrapped_release(
        [
            _event("event-2025", "2025-04-28", "Alex Example"),
            _event("event-2027", "2027-01-15", "Bailey Sample"),
        ],
        release_id="2027-02-01",
        candidacy_ledger=first.candidacy_ledger,
        existing_people=prior_people,
        existing_candidacy_person_links=prior_links,
    )

    alex = second.tables.election_results.query("candidate_name_raw == 'Alex Example'").iloc[0]
    assert alex["candidacy_id"] == first_candidacy_id
    assert alex["person_id"] == "per_audited_persistent"
    persisted_person = second.tables.people.query("person_id == 'per_audited_persistent'").iloc[0]
    assert persisted_person["created_release"] == "2026-08-20"
    persisted_link = second.tables.candidacy_person_links.query(
        "candidacy_id == @first_candidacy_id and link_status == 'confirmed'"
    ).iloc[0]
    assert persisted_link["valid_from_release"] == "2026-08-20"

    bailey = second.tables.election_results.query("candidate_name_raw == 'Bailey Sample'").iloc[0]
    assert pd.notna(bailey["person_id"])
    assert bailey["person_id"] != "per_audited_persistent"
    assert (
        second.tables.people.set_index("person_id").loc[bailey["person_id"], "created_release"]
        == "2027-02-01"
    )


def test_link_parquet_is_byte_stable_after_registry_csv_replay(tmp_path):
    first = assemble_bootstrapped_release(
        [_event("event-2025", "2025-04-28", "Alex Example")],
        release_id="2026-08-20",
    )
    people_csv = tmp_path / "people.csv"
    links_csv = tmp_path / "links.csv"
    first.tables.people.to_csv(people_csv, index=False)
    first.tables.candidacy_person_links.to_csv(links_csv, index=False)

    second = assemble_bootstrapped_release(
        [_event("event-2025", "2025-04-28", "Alex Example")],
        release_id="2026-08-20",
        candidacy_ledger=first.candidacy_ledger,
        existing_people=pd.read_csv(people_csv, dtype="string"),
        existing_candidacy_person_links=pd.read_csv(links_csv, dtype="string"),
    )

    first_parquet = tmp_path / "first.parquet"
    second_parquet = tmp_path / "second.parquet"
    first.tables.candidacy_person_links.to_parquet(first_parquet, index=False)
    second.tables.candidacy_person_links.to_parquet(second_parquet, index=False)

    assert first_parquet.read_bytes() == second_parquet.read_bytes()
