"""Explicit, evidence-backed continuity for 2026 Toronto trustee contests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .trustee_2026 import BOARD_METADATA, EXPECTED_WARDS

FILENAME = "trustee_contest_continuity_2026.csv"
CURRENT_ELECTION_DATE = "2026-10-26"
PRIOR_CHART_URL = (
    "https://www.toronto.ca/wp-content/uploads/2022/04/"
    "8ef1-2022-School-Board-Ward-Reference-Chart.pdf"
)
CURRENT_CHART_URL = (
    "https://www.toronto.ca/wp-content/uploads/2026/04/"
    "9600-2026-School-board-ward-reference-chart.pdf"
)

_COLUMNS = [
    "current_contest_id",
    "board_id",
    "ward_id",
    "continuity_status",
    "prior_contest_id",
    "evidence_urls",
    "rationale",
]
_STATUSES = {"continuous", "redrawn"}


def load_trustee_continuity(path: str | Path) -> pd.DataFrame:
    """Load the hand-curated current-to-prior contest decisions."""

    frame = pd.read_csv(path, dtype="string", keep_default_na=False)
    if list(frame.columns) != _COLUMNS:
        raise ValueError("trustee continuity columns must be exactly: " + ", ".join(_COLUMNS))
    if frame.empty:
        raise ValueError("trustee continuity table cannot be empty")
    if frame.duplicated("current_contest_id").any():
        raise ValueError("trustee continuity repeats a current contest")
    if frame.duplicated(["board_id", "ward_id"]).any():
        raise ValueError("trustee continuity repeats a board/ward decision")
    if not set(frame["continuity_status"]).issubset(_STATUSES):
        raise ValueError("trustee continuity contains an unknown status")
    for row in frame.itertuples(index=False):
        urls = str(row.evidence_urls).split("|")
        if not urls or any(not value.startswith("https://") for value in urls):
            raise ValueError("trustee continuity evidence URLs must use HTTPS")
        if PRIOR_CHART_URL not in urls or CURRENT_CHART_URL not in urls:
            raise ValueError("trustee continuity must cite both official boundary charts")
        if not str(row.rationale).strip():
            raise ValueError("trustee continuity decisions require a rationale")
    frame["ward_id"] = pd.to_numeric(frame["ward_id"], errors="raise").astype("Int64")
    return frame


def validate_trustee_continuity(
    continuity: pd.DataFrame,
    results: pd.DataFrame,
    ward_crosswalk: pd.DataFrame,
) -> None:
    """Require a safe, complete decision for each certified 2026 trustee contest."""

    required_results = {
        "contest_id",
        "election_date",
        "represented_body",
        "office_type",
        "official_district_id",
        "result_status",
        "outcome_method",
    }
    missing = sorted(required_results - set(results.columns))
    if missing:
        raise ValueError("canonical results are missing continuity columns: " + ", ".join(missing))

    expected_keys = {
        (board_id, ward_id) for board_id, wards in EXPECTED_WARDS.items() for ward_id in wards
    }
    actual_keys = {
        (str(row.board_id), int(row.ward_id)) for row in continuity.itertuples(index=False)
    }
    if actual_keys != expected_keys:
        raise ValueError("trustee continuity must cover all 29 current contests")

    current = results.loc[
        results["election_date"].astype("string").eq(CURRENT_ELECTION_DATE)
        & results["office_type"].eq("trustee")
        & results["represented_body"].isin(
            metadata["represented_body"] for metadata in BOARD_METADATA.values()
        )
    ].copy()
    if current.empty:
        raise ValueError("canonical results contain no 2026 trustee contests")
    current_contests = current[
        ["contest_id", "represented_body", "official_district_id"]
    ].drop_duplicates()
    if current_contests["contest_id"].duplicated().any() or len(current_contests) != 29:
        raise ValueError("canonical results do not contain 29 unique 2026 trustee contests")
    if set(continuity["current_contest_id"].astype(str)) != set(
        current_contests["contest_id"].astype(str)
    ):
        raise ValueError("trustee continuity does not match the certified current contests")

    crosswalk_keys = {
        (str(row.board_id), int(row.ward_id)) for row in ward_crosswalk.itertuples(index=False)
    }
    if crosswalk_keys != expected_keys:
        raise ValueError("trustee continuity requires the complete 2026 ward crosswalk")

    results_by_contest = {str(key): group for key, group in results.groupby("contest_id")}
    seen_prior: set[str] = set()
    for decision in continuity.itertuples(index=False):
        board_id = str(decision.board_id)
        ward_id = int(decision.ward_id)
        body = str(BOARD_METADATA[board_id]["represented_body"])
        current_rows = results_by_contest[str(decision.current_contest_id)]
        if (
            not current_rows["represented_body"].eq(body).all()
            or not pd.to_numeric(current_rows["official_district_id"], errors="coerce")
            .eq(ward_id)
            .all()
        ):
            raise ValueError("trustee continuity current contest does not match its board/ward")

        prior_id = str(decision.prior_contest_id).strip()
        if board_id == "tdsb":
            if decision.continuity_status != "redrawn" or prior_id:
                raise ValueError("redrawn TDSB contests cannot have a comparable prior result")
            continue
        if decision.continuity_status != "continuous" or not prior_id:
            raise ValueError("unchanged trustee districts require a prior contest")
        if prior_id in seen_prior:
            raise ValueError("one prior trustee contest cannot be assigned more than once")
        seen_prior.add(prior_id)
        if prior_id not in results_by_contest:
            raise ValueError(f"trustee continuity references unknown prior contest {prior_id}")

        prior = results_by_contest[prior_id]
        if (
            not prior["represented_body"].eq(body).all()
            or not prior["office_type"].eq("trustee").all()
        ):
            raise ValueError("trustee continuity cannot cross boards or offices")
        if not pd.to_numeric(prior["official_district_id"], errors="coerce").eq(ward_id).all():
            raise ValueError("trustee continuity prior contest does not match its ward")
        if not prior["result_status"].eq("final").all():
            raise ValueError("trustee continuity prior contest must be final")
        if prior["outcome_method"].nunique(dropna=False) != 1 or prior["outcome_method"].iloc[
            0
        ] not in {"vote", "acclamation"}:
            raise ValueError("trustee continuity prior contest has no completed outcome")
        prior_date = str(prior["election_date"].iloc[0])
        if prior_date >= CURRENT_ELECTION_DATE:
            raise ValueError("trustee continuity prior contest must predate 2026")

        eligible = results.loc[
            results["represented_body"].eq(body)
            & results["office_type"].eq("trustee")
            & pd.to_numeric(results["official_district_id"], errors="coerce").eq(ward_id)
            & results["result_status"].eq("final")
            & results["election_date"].astype("string").lt(CURRENT_ELECTION_DATE)
        ]
        if eligible.empty or prior_date != str(eligible["election_date"].max()):
            raise ValueError("trustee continuity must use the latest completed prior contest")
