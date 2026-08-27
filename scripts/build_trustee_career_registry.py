"""Build the audited trustee-career registries from completed Terra dossiers.

Terra's occurrence-level conclusion is the controlling adjudication.  The script
copies only in-scope canonical candidacy IDs into structured reference data; prose
about out-of-scope or otherwise non-canonical leads remains in the dossiers.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

import pandas as pd

from toronto_election_results.identity_curations import DEFAULT_IDENTITY_ASSERTIONS
from toronto_election_results.schema import stable_id
from toronto_election_results.trustee_career import (
    COHORT_ID,
    DECISION_COLUMNS,
    REVIEW_COLUMNS,
    SOL_MODEL,
    SOL_REVIEW_COLUMNS,
    SOL_REVIEW_DATE,
    SOL_TO_CANONICAL,
    load_trustee_career_cohort,
    validate_trustee_career_contracts,
    validate_trustee_sol_reviews,
)

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data" / "reference"
DOSSIERS = ROOT / "docs" / "research" / "trustee-career" / "2026"
REVIEW_DATE = "2026-08-27"
SOL_BATCH_FILES = (
    "sol-review-batch-a.csv",
    "sol-review-batch-b.csv",
    "sol-review-batch-c.csv",
)
SOL_BATCH_COLUMNS = [
    "subject_candidacy_id",
    "prior_candidacy_id",
    "sol_disposition",
    "identity_bridge",
    "evidence_urls",
    "rationale",
]

_CONCLUSION = re.compile(r"^## Verification conclusion\s*$", re.MULTILINE)
_NEXT_SECTION = re.compile(r"^## ", re.MULTILINE)
_CANDIDACY_ID = re.compile(r"`(?P<candidacy_id>can_[0-9a-f]{32})`")
_DECISION_WORD = re.compile(r"\b(?P<decision>confirm|hold|split|reject)\b", re.IGNORECASE)
_URL = re.compile(r"https://[^\s)>\]]+")


def _conclusion(text: str, *, path: Path) -> str:
    match = _CONCLUSION.search(text)
    if match is None:
        raise ValueError(f"missing Verification conclusion: {path}")
    start = match.end()
    following = _NEXT_SECTION.search(text, start)
    return text[start : following.start() if following else None]


def _urls(text: str, *, path: Path) -> list[str]:
    urls = list(dict.fromkeys(url.rstrip(".,;") for url in _URL.findall(text)))
    if not urls:
        raise ValueError(f"dossier contains no HTTPS evidence URL: {path}")
    return urls


def _dispositions(text: str, *, path: Path) -> list[tuple[str, str]]:
    dispositions: list[tuple[str, str]] = []
    for line in _conclusion(text, path=path).splitlines():
        candidacy_ids = [match.group("candidacy_id") for match in _CANDIDACY_ID.finditer(line)]
        if not candidacy_ids:
            continue
        decisions = {match.group("decision").lower() for match in _DECISION_WORD.finditer(line)}
        if len(decisions) != 1:
            raise ValueError(
                f"conclusion line with canonical IDs requires one disposition: {path}: {line}"
            )
        decision = decisions.pop()
        dispositions.extend((candidacy_id, decision) for candidacy_id in candidacy_ids)
    return dispositions


def _sol_urls(value: object, *, path: Path) -> list[str]:
    urls = list(dict.fromkeys(part.strip() for part in str(value).split("|") if part.strip()))
    if not urls or any(not url.startswith("https://") for url in urls):
        raise ValueError(f"Sol review requires pipe-separated HTTPS evidence URLs: {path}")
    return urls


def _load_sol_batches() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for filename in SOL_BATCH_FILES:
        path = DOSSIERS / filename
        if not path.is_file():
            raise ValueError(f"missing Sol review batch: {path}")
        frame = pd.read_csv(path, dtype="string", keep_default_na=False)
        if frame.columns.tolist() != SOL_BATCH_COLUMNS:
            raise ValueError(f"Sol review batch columns changed: {path}")
        frame["sol_batch_path"] = str(path.relative_to(ROOT))
        frames.append(frame)
    reviews = pd.concat(frames, ignore_index=True)
    if len(reviews) != 60:
        raise ValueError(f"Sol review must cover exactly 60 Terra holds, found {len(reviews)}")
    if reviews.duplicated(["subject_candidacy_id", "prior_candidacy_id"]).any():
        raise ValueError("Sol review repeats a held occurrence")
    invalid = sorted(set(reviews["sol_disposition"]) - set(SOL_TO_CANONICAL))
    if invalid:
        raise ValueError(f"unknown Sol disposition: {invalid[0]}")
    for row in reviews.itertuples(index=False):
        report = DOSSIERS / f"{row.subject_candidacy_id}-sol.md"
        if not report.is_file():
            raise ValueError(f"missing Sol dossier: {report}")
        if row.prior_candidacy_id not in report.read_text(encoding="utf-8"):
            raise ValueError(f"Sol dossier omits {row.prior_candidacy_id}: {report}")
        _sol_urls(row.evidence_urls, path=report)
        if not row.identity_bridge.strip() or not row.rationale.strip():
            raise ValueError(f"Sol review requires bridge and rationale: {report}")
    return reviews


def _resulting_person_id(
    subject_id: str,
    confirmed_ids: list[str],
    cohort_row: object,
    by_candidacy: pd.DataFrame,
) -> str:
    if not confirmed_ids:
        return cohort_row.current_person_id or ""
    confirmed_set = {subject_id, *confirmed_ids}
    curated_targets: set[str] = set()
    for assertion in DEFAULT_IDENTITY_ASSERTIONS:
        target = assertion.canonical_person_id
        if target is None and len(assertion.registry_person_ids) == 1:
            target = assertion.registry_person_ids[0]
        if target is not None and any(
            occurrence.candidacy_id in confirmed_set
            for occurrence in assertion.occurrences
            if occurrence.candidacy_id is not None
        ):
            curated_targets.add(target)
    if len(curated_targets) > 1:
        raise ValueError(
            f"confirmed occurrences for {subject_id} span conflicting curated Person IDs: "
            f"{sorted(curated_targets)}"
        )
    if curated_targets:
        return curated_targets.pop()
    person_ids = [
        str(by_candidacy.loc[candidacy_id, "person_id"]).strip()
        for candidacy_id in confirmed_ids
        if str(by_candidacy.loc[candidacy_id, "person_id"]).strip()
        and str(by_candidacy.loc[candidacy_id, "person_id"]).strip() != "<NA>"
    ]
    unique = set(person_ids)
    if not unique:
        return cohort_row.current_person_id or ""
    if len(unique) == 1:
        return unique.pop()
    current = cohort_row.current_person_id
    if current and current in unique:
        return current
    if person_ids:
        counts = Counter(person_ids)
        most_common = counts.most_common()
        if len(most_common) == 1 or most_common[0][1] > most_common[1][1]:
            return most_common[0][0]
    proposed = cohort_row.proposed_target_person_id
    if proposed and proposed in unique:
        return proposed
    raise ValueError(
        f"confirmed occurrences for {subject_id} span ambiguous Person IDs: {sorted(unique)}"
    )


def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    results = pd.read_csv(
        ROOT / "data" / "out" / "election_results.csv",
        dtype="string",
        keep_default_na=False,
        low_memory=False,
    )
    by_candidacy = results.set_index("candidacy_id", drop=False)
    cohort = load_trustee_career_cohort(REFERENCE / "trustee_career_cohort_2026.csv")
    decision_rows: list[dict[str, str]] = []
    review_inputs: list[tuple[object, Path, list[str]]] = []

    for row in cohort:
        luna_path = DOSSIERS / f"{row.subject_candidacy_id}-luna.md"
        terra_path = DOSSIERS / f"{row.subject_candidacy_id}-terra.md"
        if not luna_path.is_file():
            raise ValueError(f"missing Luna dossier: {luna_path}")
        if not terra_path.is_file():
            raise ValueError(f"missing Terra dossier: {terra_path}")
        terra_text = terra_path.read_text(encoding="utf-8")
        evidence_urls = _urls(terra_text, path=terra_path)
        dispositions = _dispositions(terra_text, path=terra_path)
        if len({candidacy_id for candidacy_id, _ in dispositions}) != len(dispositions):
            raise ValueError(f"duplicate conclusion disposition: {terra_path}")

        for prior_id, decision in dispositions:
            if prior_id not in by_candidacy.index:
                raise ValueError(f"unknown canonical candidacy {prior_id}: {terra_path}")
            prior = by_candidacy.loc[prior_id]
            bridge = (
                "Terra independently verified that this canonical occurrence "
                "belongs to the certified candidate."
                if decision == "confirm"
                else "Terra did not find a sufficient identity bridge to the certified candidate."
            )
            rationale = (
                "The independent Terra conclusion confirms the occurrence after checking "
                "the Luna evidence and collision risks."
                if decision == "confirm"
                else "The independent Terra conclusion controls after checking the Luna "
                "lead, available evidence, and collision risks."
            )
            decision_rows.append(
                {
                    "decision_id": stable_id("trd", COHORT_ID, row.subject_candidacy_id, prior_id),
                    "cohort_id": COHORT_ID,
                    "subject_candidacy_id": row.subject_candidacy_id,
                    "prior_candidacy_id": prior_id,
                    "observed_ballot_name": str(prior["candidate_name"]),
                    "election_date": str(prior["election_date"]),
                    "represented_body": str(prior["represented_body"]),
                    "office_type": str(prior["office_type"]),
                    "district_name": str(prior["district_name"]),
                    "decision": decision,
                    "identity_bridge": bridge,
                    "evidence_urls": ";".join(evidence_urls),
                    "rationale": rationale,
                }
            )
        review_inputs.append((row, terra_path, evidence_urls))

    decisions = pd.DataFrame(decision_rows, columns=DECISION_COLUMNS, dtype="string")
    sol_inputs = _load_sol_batches()
    terra_holds = decisions.loc[
        decisions["decision"].eq("hold"),
        ["subject_candidacy_id", "prior_candidacy_id"],
    ]
    hold_pairs = set(terra_holds.itertuples(index=False, name=None))
    sol_pairs = set(
        sol_inputs[["subject_candidacy_id", "prior_candidacy_id"]].itertuples(
            index=False, name=None
        )
    )
    if sol_pairs != hold_pairs:
        missing = sorted(hold_pairs - sol_pairs)
        extra = sorted(sol_pairs - hold_pairs)
        raise ValueError(
            "Sol review must exactly overlay Terra's original holds; "
            f"missing={missing[:1]}, extra={extra[:1]}"
        )

    sol_review_rows: list[dict[str, str]] = []
    for sol in sol_inputs.itertuples(index=False):
        mask = decisions["subject_candidacy_id"].eq(sol.subject_candidacy_id) & decisions[
            "prior_candidacy_id"
        ].eq(sol.prior_candidacy_id)
        if int(mask.sum()) != 1:
            raise ValueError("Sol occurrence must resolve to exactly one Terra hold")
        index = decisions.index[mask][0]
        sol_urls = _sol_urls(
            sol.evidence_urls,
            path=DOSSIERS / f"{sol.subject_candidacy_id}-sol.md",
        )
        terra_urls = str(decisions.at[index, "evidence_urls"]).split(";")
        decisions.at[index, "decision"] = SOL_TO_CANONICAL[sol.sol_disposition]
        decisions.at[index, "identity_bridge"] = sol.identity_bridge
        decisions.at[index, "evidence_urls"] = ";".join(dict.fromkeys([*terra_urls, *sol_urls]))
        decisions.at[index, "rationale"] = (
            f"{decisions.at[index, 'rationale']} Sol third-pass review: {sol.rationale}"
        )
        decision_id = str(decisions.at[index, "decision_id"])
        sol_review_rows.append(
            {
                "cohort_id": COHORT_ID,
                "subject_candidacy_id": sol.subject_candidacy_id,
                "prior_candidacy_id": sol.prior_candidacy_id,
                "decision_id": decision_id,
                "sol_report_path": (
                    f"docs/research/trustee-career/2026/{sol.subject_candidacy_id}-sol.md"
                ),
                "sol_batch_path": sol.sol_batch_path,
                "review_date": SOL_REVIEW_DATE,
                "model": SOL_MODEL,
                "sol_disposition": sol.sol_disposition,
                "identity_bridge": sol.identity_bridge,
                "evidence_urls": ";".join(sol_urls),
                "rationale": sol.rationale,
            }
        )

    sol_reviews = pd.DataFrame(sol_review_rows, columns=SOL_REVIEW_COLUMNS, dtype="string")
    review_rows: list[dict[str, str]] = []
    sol_subjects = set(sol_reviews["subject_candidacy_id"])
    for row, terra_path, evidence_urls in review_inputs:
        subject_decisions = decisions.loc[
            decisions["subject_candidacy_id"].eq(row.subject_candidacy_id)
        ]
        counts = Counter(subject_decisions["decision"].tolist())
        confirmed_ids = subject_decisions.loc[
            subject_decisions["decision"].eq("confirm"), "prior_candidacy_id"
        ].tolist()
        holds = counts["hold"]
        all_evidence = list(
            dict.fromkeys(
                [
                    *evidence_urls,
                    *(
                        url
                        for value in subject_decisions["evidence_urls"]
                        for url in str(value).split(";")
                        if url
                    ),
                ]
            )
        )
        summary = (
            f"Terra independently reviewed the complete Toronto 2003+ search and "
            f"confirmed {counts['confirm']} prior occurrence(s); its adjudication "
            "controls after comparison with Luna."
            if counts["confirm"]
            else "Terra independently reviewed the complete Toronto 2003+ search; "
            "its adjudication controls after comparison with Luna."
        )
        if row.subject_candidacy_id in sol_subjects:
            summary += " Sol independently re-reviewed every occurrence Terra had held."
        review_rows.append(
            {
                "cohort_id": COHORT_ID,
                "subject_candidacy_id": row.subject_candidacy_id,
                "certified_name": row.certified_name,
                "resulting_person_id": _resulting_person_id(
                    row.subject_candidacy_id, confirmed_ids, row, by_candidacy
                ),
                "luna_report_path": (
                    f"docs/research/trustee-career/2026/{row.subject_candidacy_id}-luna.md"
                ),
                "terra_report_path": str(terra_path.relative_to(ROOT)),
                "review_date": REVIEW_DATE,
                "review_status": "reviewed_with_limitations" if holds else "reviewed",
                "limitations": (
                    "One or more plausible prior occurrences could not be linked with "
                    "sufficient evidence."
                    if holds
                    else ""
                ),
                "confirmed_count": str(counts["confirm"]),
                "held_count": str(holds),
                "split_count": str(counts["split"]),
                "rejected_count": str(counts["reject"]),
                "evidence_urls": ";".join(all_evidence),
                "primary_rationale": summary,
            }
        )

    reviews = pd.DataFrame(review_rows, columns=REVIEW_COLUMNS, dtype="string")
    validate_trustee_career_contracts(
        cohort,
        reviews,
        decisions,
        results,
        repository_root=ROOT,
        require_complete=True,
    )
    validate_trustee_sol_reviews(sol_reviews, decisions, repository_root=ROOT)
    return reviews, decisions, sol_reviews


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate that generated registries are already byte-for-byte current.",
    )
    args = parser.parse_args()
    reviews, decisions, sol_reviews = build()
    outputs = {
        REFERENCE / "trustee_career_reviews.csv": reviews,
        REFERENCE / "trustee_career_decisions.csv": decisions,
        REFERENCE / "trustee_career_sol_reviews.csv": sol_reviews,
    }
    for path, frame in outputs.items():
        rendered = frame.to_csv(index=False, lineterminator="\n")
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != rendered:
                raise SystemExit(f"generated trustee career registry is stale: {path}")
        else:
            path.write_text(rendered, encoding="utf-8")
    print(
        f"Validated {len(reviews)} candidates, {len(decisions)} occurrences, "
        f"and {len(sol_reviews)} Sol reviews."
    )


if __name__ == "__main__":
    main()
