"""Open-world endorsement facts and coverage semantics."""

from __future__ import annotations

import pandas as pd
import pytest

from toronto_election_results.endorsements import (
    EndorsementTables,
    assemble_endorsement_tables,
    validate_endorsement_tables,
)
from toronto_election_results.schema import stable_id


def _dimensions() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    candidacies = pd.DataFrame(
        {
            "candidacy_id": ["can_alex", "can_bailey", "can_casey", "can_drew", "can_mp"],
            "contest_id": [
                "con_mayor",
                "con_mayor",
                "con_mayor",
                "con_ward_1",
                "con_mp",
            ],
        }
    )
    contests = pd.DataFrame(
        {
            "contest_id": ["con_mayor", "con_ward_1", "con_mp"],
            "office_type": ["mayor", "councillor", "mp"],
        }
    )
    people = pd.DataFrame({"person_id": ["per_miller", "per_tory"]})
    return candidacies, contests, people


def _endorsers() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "endorser_id": ["edr_miller", "edr_star", "edr_outside"],
            "canonical_name": [
                "David Miller",
                "Toronto Star Editorial Board",
                "Outside Organization",
            ],
            "endorser_type": ["person", "editorial_board", "organization"],
            "person_id": ["per_miller", pd.NA, pd.NA],
            "is_panel_endorser": [True, True, False],
        }
    )


def _assertions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "assertion_id": [
                "ast_miller_alex",
                "ast_star_alex",
                "ast_star_bailey",
                "ast_star_casey_proposed",
                "ast_miller_unmapped",
            ],
            "endorser_id": [
                "edr_miller",
                "edr_star",
                "edr_star",
                "edr_star",
                "edr_miller",
            ],
            "contest_id": [
                "con_mayor",
                "con_mayor",
                "con_mayor",
                "con_mayor",
                "con_ward_1",
            ],
            "candidacy_id": ["can_alex", "can_alex", "can_bailey", "can_casey", pd.NA],
            "review_state": ["confirmed", "confirmed", "confirmed", "proposed", "unresolved"],
            "source_url": [
                "https://example.test/miller",
                "https://example.test/star-alex",
                "https://example.test/star-bailey",
                "https://example.test/candidate-claim",
                "https://example.test/unmapped",
            ],
            "asserted_candidate_name": [
                "Alex Example",
                "Alex Example",
                "Bailey Sample",
                "Casey Example",
                "Unmapped Candidate",
            ],
        }
    )


def _coverage() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "endorser_id": ["edr_miller", "edr_miller", "edr_star", "edr_outside"],
            "contest_id": ["con_mayor", "con_ward_1", "con_mayor", "con_mayor"],
            "coverage_state": [
                "partially_searched",
                "source_unavailable",
                "comprehensive_source_found",
                "not_searched",
            ],
        }
    )


def _assemble(
    *,
    candidacies: pd.DataFrame | None = None,
    contests: pd.DataFrame | None = None,
    people: pd.DataFrame | None = None,
    endorsers: pd.DataFrame | None = None,
    assertions: pd.DataFrame | None = None,
    coverage: pd.DataFrame | None = None,
):
    default_candidacies, default_contests, default_people = _dimensions()
    return assemble_endorsement_tables(
        candidacies=default_candidacies if candidacies is None else candidacies,
        contests=default_contests if contests is None else contests,
        people=default_people if people is None else people,
        endorsers=_endorsers() if endorsers is None else endorsers,
        assertions=_assertions() if assertions is None else assertions,
        coverage=_coverage() if coverage is None else coverage,
    )


def test_only_confirmed_assertions_create_positive_endorsement_facts():
    tables = _assemble()

    facts = tables.endorsements
    assert set(facts[["endorser_id", "candidacy_id"]].itertuples(index=False, name=None)) == {
        ("edr_miller", "can_alex"),
        ("edr_star", "can_alex"),
        ("edr_star", "can_bailey"),
    }
    assert "can_casey" not in set(facts["candidacy_id"])
    assert facts["endorsement_id"].str.startswith("end_").all()

    assertions = tables.endorsement_assertions.set_index("assertion_id")
    assert pd.isna(assertions.loc["ast_star_casey_proposed", "endorsement_id"])
    assert pd.isna(assertions.loc["ast_miller_unmapped", "endorsement_id"])


def test_one_endorser_may_endorse_multiple_candidates_in_the_same_contest():
    facts = _assemble().endorsements.query("endorser_id == 'edr_star'")

    assert facts["contest_id"].tolist() == ["con_mayor", "con_mayor"]
    assert set(facts["candidacy_id"]) == {"can_alex", "can_bailey"}


def test_multiple_confirmed_sources_collapse_to_one_fact_and_share_its_id():
    assertions = pd.concat(
        [
            _assertions(),
            pd.DataFrame(
                [
                    {
                        "assertion_id": "ast_star_alex_second_source",
                        "endorser_id": "edr_star",
                        "contest_id": "con_mayor",
                        "candidacy_id": "can_alex",
                        "review_state": "confirmed",
                        "source_url": "https://example.test/star-alex-corroboration",
                        "asserted_candidate_name": "Alex Example",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    tables = _assemble(assertions=assertions)
    facts = tables.endorsements.query("endorser_id == 'edr_star' and candidacy_id == 'can_alex'")
    source_assertions = tables.endorsement_assertions.query(
        "endorser_id == 'edr_star' and candidacy_id == 'can_alex'"
    )

    assert len(facts) == 1
    assert source_assertions["endorsement_id"].nunique() == 1
    assert source_assertions["endorsement_id"].iloc[0] == facts["endorsement_id"].item()


def test_coverage_never_creates_candidate_level_negative_rows():
    empty_assertions = _assertions().iloc[0:0].copy()
    coverage = _coverage().copy()
    coverage["coverage_state"] = "searched_no_endorsement_found"

    tables = _assemble(assertions=empty_assertions, coverage=coverage)

    assert tables.endorsements.empty
    assert len(tables.endorsement_coverage) == len(coverage)


def test_inputs_are_not_mutated_when_fact_ids_are_attached():
    assertions = _assertions()

    _assemble(assertions=assertions)

    assert "endorsement_id" not in assertions.columns


def test_publication_validator_accepts_the_assembled_artifacts():
    candidacies, contests, people = _dimensions()
    tables = _assemble(candidacies=candidacies, contests=contests, people=people)

    assert (
        validate_endorsement_tables(
            tables,
            candidacies=candidacies,
            contests=contests,
            people=people,
        )
        is None
    )


def test_publication_validator_rejects_a_fact_without_a_confirmed_assertion():
    candidacies, contests, people = _dimensions()
    tables = _assemble(candidacies=candidacies, contests=contests, people=people)
    unexpected = tables.endorsements.iloc[[0]].copy()
    unexpected.loc[:, "endorser_id"] = "edr_outside"
    unexpected.loc[:, "candidacy_id"] = "can_casey"
    unexpected.loc[:, "endorsement_id"] = stable_id("end", "edr_outside", "con_mayor", "can_casey")
    changed = EndorsementTables(
        endorsers=tables.endorsers,
        endorsement_assertions=tables.endorsement_assertions,
        endorsements=pd.concat([tables.endorsements, unexpected], ignore_index=True),
        endorsement_coverage=tables.endorsement_coverage,
    )

    with pytest.raises(ValueError, match="facts derived from confirmed assertions"):
        validate_endorsement_tables(
            changed,
            candidacies=candidacies,
            contests=contests,
            people=people,
        )


def test_publication_validator_rejects_a_missing_confirmed_fact():
    candidacies, contests, people = _dimensions()
    tables = _assemble(candidacies=candidacies, contests=contests, people=people)
    changed = EndorsementTables(
        endorsers=tables.endorsers,
        endorsement_assertions=tables.endorsement_assertions,
        endorsements=tables.endorsements.iloc[1:].copy(),
        endorsement_coverage=tables.endorsement_coverage,
    )

    with pytest.raises(ValueError, match="facts derived from confirmed assertions"):
        validate_endorsement_tables(
            changed,
            candidacies=candidacies,
            contests=contests,
            people=people,
        )


def test_publication_validator_rejects_a_tampered_assertion_fact_link():
    candidacies, contests, people = _dimensions()
    tables = _assemble(candidacies=candidacies, contests=contests, people=people)
    assertions = tables.endorsement_assertions.copy()
    assertions.loc[assertions.review_state == "proposed", "endorsement_id"] = tables.endorsements[
        "endorsement_id"
    ].iloc[0]
    changed = EndorsementTables(
        endorsers=tables.endorsers,
        endorsement_assertions=assertions,
        endorsements=tables.endorsements,
        endorsement_coverage=tables.endorsement_coverage,
    )

    with pytest.raises(ValueError, match="confirmed review state"):
        validate_endorsement_tables(
            changed,
            candidacies=candidacies,
            contests=contests,
            people=people,
        )


def test_unresolved_assertion_may_have_no_candidacy():
    tables = _assemble()
    unresolved = tables.endorsement_assertions.query("review_state == 'unresolved'")

    assert len(unresolved) == 1
    assert unresolved["candidacy_id"].isna().all()


@pytest.mark.parametrize("review_state", ["confirmed", "proposed", "rejected", "withdrawn"])
def test_only_unresolved_assertion_may_have_no_candidacy(review_state):
    assertions = _assertions().iloc[[0]].copy()
    assertions.loc[:, "review_state"] = review_state
    assertions.loc[:, "candidacy_id"] = pd.NA

    with pytest.raises(ValueError, match="only an unresolved"):
        _assemble(assertions=assertions)


def test_assertion_candidacy_must_belong_to_its_contest():
    assertions = _assertions()
    assertions.loc[assertions.assertion_id == "ast_star_alex", "contest_id"] = "con_ward_1"

    with pytest.raises(ValueError, match="wrong Contest"):
        _assemble(assertions=assertions)


@pytest.mark.parametrize(
    ("table", "column", "bad_value", "message"),
    [
        ("assertions", "endorser_id", "edr_unknown", "unknown Endorser"),
        ("assertions", "contest_id", "con_unknown", "unknown target"),
        ("assertions", "candidacy_id", "can_unknown", "unknown Candidacy"),
        ("coverage", "endorser_id", "edr_unknown", "unknown Endorser"),
        ("coverage", "contest_id", "con_unknown", "unknown target"),
    ],
)
def test_assertion_and_coverage_foreign_keys_are_exact(table, column, bad_value, message):
    frame = _assertions() if table == "assertions" else _coverage()
    frame.loc[frame.index[0], column] = bad_value

    with pytest.raises(ValueError, match=message):
        _assemble(**{table: frame})


def test_person_endorser_must_reference_an_existing_person():
    endorsers = _endorsers()
    endorsers.loc[endorsers.endorser_id == "edr_miller", "person_id"] = "per_unknown"

    with pytest.raises(ValueError, match="unknown Person"):
        _assemble(endorsers=endorsers)


def test_organization_cannot_inherit_a_person_identity():
    endorsers = _endorsers()
    endorsers.loc[endorsers.endorser_id == "edr_star", "person_id"] = "per_tory"

    with pytest.raises(ValueError, match="only a person Endorser"):
        _assemble(endorsers=endorsers)


def test_coverage_has_exactly_one_row_per_endorser_and_contest():
    coverage = pd.concat([_coverage(), _coverage().iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="one row per Endorser and Contest"):
        _assemble(coverage=coverage)


@pytest.mark.parametrize("state", ["not_applicable", "searched_no_endorsement_found"])
def test_coverage_cannot_contradict_a_confirmed_fact(state):
    coverage = _coverage()
    coverage.loc[
        (coverage.endorser_id == "edr_miller") & (coverage.contest_id == "con_mayor"),
        "coverage_state",
    ] = state

    with pytest.raises(ValueError, match="contradicts a confirmed Endorsement"):
        _assemble(coverage=coverage)


def test_assertions_and_coverage_reject_non_target_offices():
    assertions = _assertions().iloc[[0]].copy()
    assertions.loc[:, "contest_id"] = "con_mp"
    assertions.loc[:, "candidacy_id"] = "can_mp"

    with pytest.raises(ValueError, match="target Mayor/City Councillor Contest"):
        _assemble(assertions=assertions)


@pytest.mark.parametrize(
    ("table", "column", "value", "message"),
    [
        ("assertions", "review_state", "maybe", "unknown endorsement_assertions.review_state"),
        ("coverage", "coverage_state", "complete", "unknown endorsement_coverage.coverage_state"),
    ],
)
def test_closed_state_vocabularies_are_enforced(table, column, value, message):
    frame = _assertions() if table == "assertions" else _coverage()
    frame.loc[frame.index[0], column] = value

    with pytest.raises(ValueError, match=message):
        _assemble(**{table: frame})
