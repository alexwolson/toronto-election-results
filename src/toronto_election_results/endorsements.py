"""Assemble evidence-backed endorsement companion tables.

Endorsements are open-world facts: the module publishes only positive edges supported by a
confirmed source assertion.  Search coverage is retained at Endorser-by-Contest grain and never
expanded into negative candidate observations.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import pandas as pd

from .schema import stable_id

ENDORSEMENT_REVIEW_STATES = frozenset(
    {"proposed", "confirmed", "unresolved", "rejected", "withdrawn"}
)
ENDORSEMENT_COVERAGE_STATES = frozenset(
    {
        "not_applicable",
        "not_searched",
        "partially_searched",
        "searched_no_endorsement_found",
        "comprehensive_source_found",
        "source_unavailable",
    }
)
ENDORSER_TYPES = frozenset({"person", "organization", "editorial_board"})
ENDORSEMENT_TARGET_OFFICES = frozenset({"mayor", "councillor"})

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class EndorsementTables:
    """Validated source assertions, positive facts, and independent search coverage."""

    endorsers: pd.DataFrame
    endorsement_assertions: pd.DataFrame
    endorsements: pd.DataFrame
    endorsement_coverage: pd.DataFrame


def _required(frame: pd.DataFrame, columns: set[str], table: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{table} is missing required columns: {', '.join(missing)}")


def _clean_text(value: object) -> object:
    if value is None or value is pd.NA or pd.isna(value):
        return pd.NA
    cleaned = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", str(value))).strip()
    return cleaned if cleaned else pd.NA


def _clean_required_text(frame: pd.DataFrame, columns: list[str], table: str) -> None:
    for column in columns:
        frame[column] = frame[column].map(_clean_text).astype("string")
        if frame[column].isna().any():
            raise ValueError(f"{table}.{column} must be non-null and non-blank")


def _clean_optional_text(frame: pd.DataFrame, column: str) -> None:
    frame[column] = frame[column].map(_clean_text).astype("string")


def _require_unique(frame: pd.DataFrame, column: str, table: str) -> None:
    duplicates = frame[column].duplicated(keep=False)
    if duplicates.any():
        duplicate = frame.loc[duplicates, column].iloc[0]
        raise ValueError(f"{table}.{column} must be unique; duplicate {duplicate!r}")


def _validate_values(
    frame: pd.DataFrame,
    column: str,
    allowed: frozenset[str],
    table: str,
) -> None:
    invalid = ~frame[column].isin(allowed)
    if invalid.any():
        value = frame.loc[invalid, column].iloc[0]
        raise ValueError(f"unknown {table}.{column}: {value!r}")


def _validate_foreign_key(
    frame: pd.DataFrame,
    column: str,
    valid_ids: set[str],
    table: str,
    target: str,
    *,
    nullable: bool = False,
) -> None:
    values = frame[column]
    missing = values.notna() & ~values.isin(valid_ids) if nullable else ~values.isin(valid_ids)
    if missing.any():
        value = frame.loc[missing, column].iloc[0]
        raise ValueError(f"{table}.{column} references unknown {target} {value!r}")


def _prepare_dimensions(
    candidacies: pd.DataFrame,
    contests: pd.DataFrame,
    people: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    candidacy_out = candidacies.copy()
    contest_out = contests.copy()
    people_out = people.copy()

    _required(candidacy_out, {"candidacy_id", "contest_id"}, "candidacies")
    _required(contest_out, {"contest_id", "office_type"}, "contests")
    _required(people_out, {"person_id"}, "people")

    _clean_required_text(candidacy_out, ["candidacy_id", "contest_id"], "candidacies")
    _clean_required_text(contest_out, ["contest_id", "office_type"], "contests")
    _clean_required_text(people_out, ["person_id"], "people")
    _require_unique(candidacy_out, "candidacy_id", "candidacies")
    _require_unique(contest_out, "contest_id", "contests")
    _require_unique(people_out, "person_id", "people")

    _validate_foreign_key(
        candidacy_out,
        "contest_id",
        set(contest_out["contest_id"]),
        "candidacies",
        "Contest",
    )
    return candidacy_out, contest_out, people_out


def _prepare_endorsers(endorsers: pd.DataFrame, people: pd.DataFrame) -> pd.DataFrame:
    out = endorsers.copy()
    _required(
        out,
        {
            "endorser_id",
            "canonical_name",
            "endorser_type",
            "person_id",
            "is_panel_endorser",
        },
        "endorsers",
    )
    _clean_required_text(
        out,
        ["endorser_id", "canonical_name", "endorser_type"],
        "endorsers",
    )
    _clean_optional_text(out, "person_id")
    _require_unique(out, "endorser_id", "endorsers")
    _validate_values(out, "endorser_type", ENDORSER_TYPES, "endorsers")

    try:
        out["is_panel_endorser"] = out["is_panel_endorser"].astype("boolean")
    except (TypeError, ValueError) as exc:
        raise ValueError("endorsers.is_panel_endorser must contain booleans") from exc
    if out["is_panel_endorser"].isna().any():
        raise ValueError("endorsers.is_panel_endorser must contain booleans")

    person_endorsers = out["endorser_type"].eq("person")
    if (person_endorsers & out["person_id"].isna()).any():
        raise ValueError("a person Endorser must reference a Person")
    if ((~person_endorsers) & out["person_id"].notna()).any():
        raise ValueError("only a person Endorser may reference a Person")
    _validate_foreign_key(
        out,
        "person_id",
        set(people["person_id"]),
        "endorsers",
        "Person",
        nullable=True,
    )
    duplicate_people = out.loc[person_endorsers, "person_id"].duplicated(keep=False)
    if duplicate_people.any():
        duplicate = out.loc[person_endorsers].loc[duplicate_people, "person_id"].iloc[0]
        raise ValueError(f"Person {duplicate!r} is represented by multiple Endorsers")
    return out.sort_values("endorser_id", kind="stable").reset_index(drop=True)


def _target_contest_ids(contests: pd.DataFrame) -> set[str]:
    return set(contests.loc[contests["office_type"].isin(ENDORSEMENT_TARGET_OFFICES), "contest_id"])


def _prepare_assertions(
    assertions: pd.DataFrame,
    *,
    endorsers: pd.DataFrame,
    candidacies: pd.DataFrame,
    contests: pd.DataFrame,
) -> pd.DataFrame:
    out = assertions.drop(columns="endorsement_id", errors="ignore").copy()
    _required(
        out,
        {
            "assertion_id",
            "endorser_id",
            "contest_id",
            "candidacy_id",
            "review_state",
        },
        "endorsement_assertions",
    )
    _clean_required_text(
        out,
        ["assertion_id", "endorser_id", "contest_id", "review_state"],
        "endorsement_assertions",
    )
    _clean_optional_text(out, "candidacy_id")
    _require_unique(out, "assertion_id", "endorsement_assertions")
    _validate_values(
        out,
        "review_state",
        ENDORSEMENT_REVIEW_STATES,
        "endorsement_assertions",
    )

    _validate_foreign_key(
        out,
        "endorser_id",
        set(endorsers["endorser_id"]),
        "endorsement_assertions",
        "Endorser",
    )
    _validate_foreign_key(
        out,
        "contest_id",
        _target_contest_ids(contests),
        "endorsement_assertions",
        "target Mayor/City Councillor Contest",
    )
    _validate_foreign_key(
        out,
        "candidacy_id",
        set(candidacies["candidacy_id"]),
        "endorsement_assertions",
        "Candidacy",
        nullable=True,
    )

    missing_target = out["candidacy_id"].isna()
    if (missing_target & ~out["review_state"].eq("unresolved")).any():
        raise ValueError("only an unresolved Endorsement assertion may omit candidacy_id")

    candidacy_contests = candidacies.set_index("candidacy_id")["contest_id"]
    mapped = out.loc[out["candidacy_id"].notna(), ["assertion_id", "candidacy_id", "contest_id"]]
    expected_contests = mapped["candidacy_id"].map(candidacy_contests)
    mismatch = ~mapped["contest_id"].eq(expected_contests)
    if mismatch.any():
        row = mapped.loc[mismatch].iloc[0]
        raise ValueError(
            f"endorsement assertion {row['assertion_id']!r} maps Candidacy "
            f"{row['candidacy_id']!r} to the wrong Contest"
        )

    confirmed = out["review_state"].eq("confirmed")
    out["endorsement_id"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out.loc[confirmed, "endorsement_id"] = [
        stable_id("end", endorser_id, contest_id, candidacy_id)
        for endorser_id, contest_id, candidacy_id in out.loc[
            confirmed, ["endorser_id", "contest_id", "candidacy_id"]
        ].itertuples(index=False, name=None)
    ]

    columns = ["assertion_id", "endorsement_id"] + [
        column for column in out.columns if column not in {"assertion_id", "endorsement_id"}
    ]
    return out[columns].sort_values("assertion_id", kind="stable").reset_index(drop=True)


def _derive_endorsements(assertions: pd.DataFrame) -> pd.DataFrame:
    confirmed = assertions.loc[
        assertions["review_state"].eq("confirmed"),
        ["endorsement_id", "endorser_id", "contest_id", "candidacy_id"],
    ]
    return (
        confirmed.drop_duplicates(["endorser_id", "contest_id", "candidacy_id"])
        .sort_values(["contest_id", "endorser_id", "candidacy_id"], kind="stable")
        .reset_index(drop=True)
    )


def _prepare_coverage(
    coverage: pd.DataFrame,
    *,
    endorsers: pd.DataFrame,
    contests: pd.DataFrame,
    endorsements: pd.DataFrame,
) -> pd.DataFrame:
    out = coverage.copy()
    _required(
        out,
        {"endorser_id", "contest_id", "coverage_state"},
        "endorsement_coverage",
    )
    _clean_required_text(
        out,
        ["endorser_id", "contest_id", "coverage_state"],
        "endorsement_coverage",
    )
    _validate_values(
        out,
        "coverage_state",
        ENDORSEMENT_COVERAGE_STATES,
        "endorsement_coverage",
    )
    _validate_foreign_key(
        out,
        "endorser_id",
        set(endorsers["endorser_id"]),
        "endorsement_coverage",
        "Endorser",
    )
    _validate_foreign_key(
        out,
        "contest_id",
        _target_contest_ids(contests),
        "endorsement_coverage",
        "target Mayor/City Councillor Contest",
    )

    duplicate_cells = out.duplicated(["endorser_id", "contest_id"], keep=False)
    if duplicate_cells.any():
        row = out.loc[duplicate_cells].iloc[0]
        raise ValueError(
            "endorsement_coverage must have one row per Endorser and Contest; "
            f"duplicate ({row['endorser_id']!r}, {row['contest_id']!r})"
        )

    no_positive_states = {"not_applicable", "searched_no_endorsement_found"}
    negative_cells = set(
        out.loc[
            out["coverage_state"].isin(no_positive_states), ["endorser_id", "contest_id"]
        ].itertuples(index=False, name=None)
    )
    positive_cells = set(
        endorsements[["endorser_id", "contest_id"]].itertuples(index=False, name=None)
    )
    contradictions = sorted(negative_cells & positive_cells)
    if contradictions:
        endorser_id, contest_id = contradictions[0]
        raise ValueError(
            "endorsement_coverage contradicts a confirmed Endorsement for "
            f"({endorser_id!r}, {contest_id!r})"
        )

    return out.sort_values(["endorser_id", "contest_id"], kind="stable").reset_index(drop=True)


def _validate_published_assertion_links(assertions: pd.DataFrame, expected: pd.DataFrame) -> None:
    _required(assertions, {"assertion_id", "endorsement_id"}, "endorsement_assertions")
    provided = assertions[["assertion_id", "endorsement_id"]].copy()
    _clean_required_text(provided, ["assertion_id"], "endorsement_assertions")
    _clean_optional_text(provided, "endorsement_id")
    _require_unique(provided, "assertion_id", "endorsement_assertions")

    expected_links = expected[["assertion_id", "endorsement_id"]]
    comparison = provided.merge(
        expected_links,
        on="assertion_id",
        how="outer",
        suffixes=("_provided", "_expected"),
        validate="one_to_one",
        indicator=True,
    )
    mismatched = ~comparison["_merge"].eq("both") | ~comparison["endorsement_id_provided"].fillna(
        ""
    ).eq(comparison["endorsement_id_expected"].fillna(""))
    if mismatched.any():
        assertion_id = comparison.loc[mismatched, "assertion_id"].iloc[0]
        raise ValueError(
            "endorsement_assertions.endorsement_id must identify exactly the fact produced by "
            f"its confirmed review state; mismatch for {assertion_id!r}"
        )


def _validate_published_facts(
    endorsements: pd.DataFrame,
    *,
    expected: pd.DataFrame,
    endorsers: pd.DataFrame,
    candidacies: pd.DataFrame,
    contests: pd.DataFrame,
) -> None:
    out = endorsements.copy()
    fact_columns = ["endorsement_id", "endorser_id", "contest_id", "candidacy_id"]
    _required(out, set(fact_columns), "endorsements")
    _clean_required_text(out, fact_columns, "endorsements")
    _require_unique(out, "endorsement_id", "endorsements")
    duplicate_edges = out.duplicated(["endorser_id", "contest_id", "candidacy_id"], keep=False)
    if duplicate_edges.any():
        raise ValueError("endorsements must contain one fact per Endorser, Contest, and Candidacy")

    _validate_foreign_key(
        out,
        "endorser_id",
        set(endorsers["endorser_id"]),
        "endorsements",
        "Endorser",
    )
    _validate_foreign_key(
        out,
        "contest_id",
        _target_contest_ids(contests),
        "endorsements",
        "target Mayor/City Councillor Contest",
    )
    _validate_foreign_key(
        out,
        "candidacy_id",
        set(candidacies["candidacy_id"]),
        "endorsements",
        "Candidacy",
    )

    candidacy_contests = candidacies.set_index("candidacy_id")["contest_id"]
    mismatch = ~out["contest_id"].eq(out["candidacy_id"].map(candidacy_contests))
    if mismatch.any():
        endorsement_id = out.loc[mismatch, "endorsement_id"].iloc[0]
        raise ValueError(f"Endorsement {endorsement_id!r} maps its Candidacy to the wrong Contest")

    expected_ids = pd.Series(
        [
            stable_id("end", endorser_id, contest_id, candidacy_id)
            for endorser_id, contest_id, candidacy_id in out[
                ["endorser_id", "contest_id", "candidacy_id"]
            ].itertuples(index=False, name=None)
        ],
        index=out.index,
        dtype="string",
    )
    bad_ids = ~out["endorsement_id"].eq(expected_ids)
    if bad_ids.any():
        endorsement_id = out.loc[bad_ids, "endorsement_id"].iloc[0]
        raise ValueError(f"Endorsement {endorsement_id!r} has an ID inconsistent with its edge")

    edge_columns = ["endorser_id", "contest_id", "candidacy_id"]
    provided_edges = set(out[edge_columns].itertuples(index=False, name=None))
    expected_edges = set(expected[edge_columns].itertuples(index=False, name=None))
    if provided_edges != expected_edges:
        missing = sorted(expected_edges - provided_edges)
        unexpected = sorted(provided_edges - expected_edges)
        raise ValueError(
            "endorsements must equal the facts derived from confirmed assertions; "
            f"missing={missing!r}, unexpected={unexpected!r}"
        )


def validate_endorsement_tables(
    tables: EndorsementTables,
    *,
    candidacies: pd.DataFrame,
    contests: pd.DataFrame,
    people: pd.DataFrame,
) -> None:
    """Validate already-built endorsement artifacts, raising ``ValueError`` on any issue.

    This is the publication validation seam.  It re-adjudicates the positive fact set from the
    persisted assertions, checks every foreign key, and verifies that persisted assertion-to-fact
    links and deterministic fact IDs have not drifted.
    """

    candidacy_dimension, contest_dimension, people_dimension = _prepare_dimensions(
        candidacies, contests, people
    )
    expected = assemble_endorsement_tables(
        candidacies=candidacy_dimension,
        contests=contest_dimension,
        people=people_dimension,
        endorsers=tables.endorsers,
        assertions=tables.endorsement_assertions,
        coverage=tables.endorsement_coverage,
    )
    _validate_published_assertion_links(
        tables.endorsement_assertions, expected.endorsement_assertions
    )
    _validate_published_facts(
        tables.endorsements,
        expected=expected.endorsements,
        endorsers=expected.endorsers,
        candidacies=candidacy_dimension,
        contests=contest_dimension,
    )


def assemble_endorsement_tables(
    *,
    candidacies: pd.DataFrame,
    contests: pd.DataFrame,
    people: pd.DataFrame,
    endorsers: pd.DataFrame,
    assertions: pd.DataFrame,
    coverage: pd.DataFrame,
) -> EndorsementTables:
    """Validate endorsement inputs and derive the adjudicated positive-edge table.

    The interface accepts the three release dimensions needed for foreign-key checks plus curated
    Endorsers, source assertions, and coverage cells.  Only ``confirmed`` assertions create an
    Endorsement.  Multiple targets by the same Endorser in one Contest are valid, while missing or
    negative-search coverage never creates candidate-level rows.

    An unresolved assertion may omit ``candidacy_id`` when no in-scope Candidacy can receive the
    claim.  All mapped assertions must target a Candidacy belonging to their stated Contest.
    """

    candidacy_dimension, contest_dimension, people_dimension = _prepare_dimensions(
        candidacies, contests, people
    )
    endorser_table = _prepare_endorsers(endorsers, people_dimension)
    assertion_table = _prepare_assertions(
        assertions,
        endorsers=endorser_table,
        candidacies=candidacy_dimension,
        contests=contest_dimension,
    )
    endorsement_table = _derive_endorsements(assertion_table)
    coverage_table = _prepare_coverage(
        coverage,
        endorsers=endorser_table,
        contests=contest_dimension,
        endorsements=endorsement_table,
    )
    return EndorsementTables(
        endorsers=endorser_table,
        endorsement_assertions=assertion_table,
        endorsements=endorsement_table,
        endorsement_coverage=coverage_table,
    )
