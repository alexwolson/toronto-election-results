"""Official Mayor, Councillor, and Trustee Candidacies for Toronto's 2026 election.

The City publishes the certified candidate roster separately from completed election
results.  This adapter keeps that lifecycle distinction explicit: it emits the same
source-adapter contract as the completed-result adapters, but every result field is
unknown and ``result_status`` is ``pending``.

The source also publishes contact details and social links.  They are intentionally
not part of the adapter output; the roster is used only to establish Candidacy facts.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
import requests

from .schema import stable_id
from .trustee_2026 import (
    BOARD_ID_BY_OFFICE_CODE,
    BOARD_METADATA,
    EXPECTED_WARDS,
    TRUSTEE_CROSSWALK_FILENAME,
    load_trustee_ward_crosswalk,
)

ELECTION_DATE = "2026-10-26"
BOUNDARY_REGIME = "toronto_council_25_wards"
MAYOR_CANDIDATES_URL = (
    "https://www.toronto.ca/data/elections/candidate_list/mayorCandidates_2026.json"
)
COUNCILLOR_CANDIDATES_URL = (
    "https://www.toronto.ca/data/elections/candidate_list/councilorCandidates_2026.json"
)
TRUSTEE_CANDIDATES_URL = (
    "https://www.toronto.ca/data/elections/candidate_list/trusteeCandidates_2026.json"
)
TRUSTEE_ACCLAMATION_URL = (
    "https://www.toronto.ca/wp-content/uploads/2026/08/8ed9-2026-Declaration-of-Acclamation.pdf"
)

MAYOR_CANDIDATES_FILENAME = "mayorCandidates_2026.json"
COUNCILLOR_CANDIDATES_FILENAME = "councilorCandidates_2026.json"
TRUSTEE_CANDIDATES_FILENAME = "trusteeCandidates_2026.json"

_EVENT_ID = stable_id("evt", "toronto_city_clerk", ELECTION_DATE, "general")
_SOURCE_RESOURCE = "2026 Municipal Election — Certified Candidates"
_WHITESPACE = re.compile(r"\s+")

_TRUSTEE_ACCLAMATIONS = {
    ("tcdsb", 6): "Frank D'Amico",
    ("tcdsb", 12): "Nancy Crawford",
    ("viamonde", 2): "Benoit Fortin",
    ("viamonde", 4): "Geneviève Oger",
}

_WARD_NAMES = {
    1: "Etobicoke North",
    2: "Etobicoke Centre",
    3: "Etobicoke-Lakeshore",
    4: "Parkdale-High Park",
    5: "York South-Weston",
    6: "York Centre",
    7: "Humber River-Black Creek",
    8: "Eglinton-Lawrence",
    9: "Davenport",
    10: "Spadina-Fort York",
    11: "University-Rosedale",
    12: "Toronto-St. Paul's",
    13: "Toronto Centre",
    14: "Toronto-Danforth",
    15: "Don Valley West",
    16: "Don Valley East",
    17: "Don Valley North",
    18: "Willowdale",
    19: "Beaches-East York",
    20: "Scarborough Southwest",
    21: "Scarborough Centre",
    22: "Scarborough-Agincourt",
    23: "Scarborough North",
    24: "Scarborough-Guildwood",
    25: "Scarborough-Rouge Park",
}

PENDING_ADAPTER_COLUMNS = [
    "event_id",
    "election_date",
    "election_type",
    "election_authority",
    "represented_body",
    "office_type",
    "boundary_regime",
    "official_district_id",
    "district_name",
    "candidate_name_raw",
    "candidate_name",
    "party_name_raw",
    "affiliation_status",
    "votes",
    "elected",
    "incumbent_reported",
    "eligible_electors",
    "ballots_cast",
    "turnout_scope",
    "outcome_method",
    "result_status",
    "coverage_status",
    "source_authority",
    "source_resource",
    "source_detail",
]


def pending_candidate_paths(source_dir: str | Path) -> tuple[Path, Path, Path]:
    """Return the deterministic local cache paths for all official rosters."""

    root = Path(source_dir)
    return (
        root / MAYOR_CANDIDATES_FILENAME,
        root / COUNCILLOR_CANDIDATES_FILENAME,
        root / TRUSTEE_CANDIDATES_FILENAME,
    )


def _download_json(
    url: str,
    destination: Path,
    *,
    session: requests.Session | None,
    overwrite: bool,
) -> Path:
    if destination.exists() and not overwrite:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    client = session or requests
    try:
        with client.get(url, stream=True, timeout=300) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        handle.write(chunk)
        # Reject an error page or truncated response before it replaces a good cache.
        with temporary.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise TypeError(f"official candidate roster at {url} is not a JSON object")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def download_pending_candidate_rosters(
    source_dir: str | Path,
    *,
    session: requests.Session | None = None,
    overwrite: bool = False,
) -> tuple[Path, Path, Path]:
    """Download all official 2026 candidate rosters atomically and idempotently."""

    mayor_path, councillor_path, trustee_path = pending_candidate_paths(source_dir)
    _download_json(
        MAYOR_CANDIDATES_URL,
        mayor_path,
        session=session,
        overwrite=overwrite,
    )
    _download_json(
        COUNCILLOR_CANDIDATES_URL,
        councillor_path,
        session=session,
        overwrite=overwrite,
    )
    _download_json(
        TRUSTEE_CANDIDATES_URL,
        trustee_path,
        session=session,
        overwrite=overwrite,
    )
    return mayor_path, councillor_path, trustee_path


def _load_json(path: str | Path) -> dict[str, object]:
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid official candidate JSON: {source}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"official candidate JSON is not an object: {source}")
    return payload


def _text(value: object, *, field: str) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        raise ValueError(f"official candidate {field} cannot be null")
    cleaned = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", str(value))).strip()
    if not cleaned:
        raise ValueError(f"official candidate {field} cannot be blank")
    return cleaned


def _optional_text(value: object) -> str | None:
    if value is None or value is pd.NA or pd.isna(value):
        return None
    cleaned = _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", str(value))).strip()
    return cleaned or None


def _active_candidate(candidate: object) -> dict[str, object] | None:
    if not isinstance(candidate, dict):
        raise TypeError("official candidate entry is not an object")
    status = _text(candidate.get("status"), field="status")
    return candidate if status.casefold() == "active" else None


def _candidate_row(
    candidate: dict[str, object],
    *,
    office_type: str,
    official_district_id: str,
    district_name: str,
    source_detail: str,
    represented_body: str = "toronto_city_council",
    boundary_regime: str = BOUNDARY_REGIME,
    expected_office: int | None = None,
    outcome_method: str = "pending",
    result_status: str = "pending",
) -> dict[str, object]:
    office_code = (
        expected_office if expected_office is not None else (1 if office_type == "mayor" else 2)
    )
    if candidate.get("office") != office_code:
        raise ValueError(
            f"official {office_type} candidate has unexpected office code: "
            f"{candidate.get('office')!r}"
        )
    # The live City feed currently has one candidate whose full name is carried in
    # ``lastName`` and whose ``firstName`` is blank.  The canonical display remains
    # constructed solely from these structured components, in their supplied order.
    name_parts = [
        part
        for value in [candidate.get("firstName"), candidate.get("lastName")]
        if (part := _optional_text(value)) is not None
    ]
    if not name_parts:
        raise ValueError("official candidate firstName and lastName cannot both be blank")
    return {
        "event_id": _EVENT_ID,
        "election_date": pd.Timestamp(ELECTION_DATE).date(),
        "election_type": "general",
        "election_authority": "toronto_city_clerk",
        "represented_body": represented_body,
        "office_type": office_type,
        "boundary_regime": boundary_regime,
        "official_district_id": official_district_id,
        "district_name": district_name,
        "candidate_name_raw": _text(candidate.get("name"), field="name"),
        "candidate_name": " ".join(name_parts),
        "party_name_raw": pd.NA,
        "affiliation_status": "non_partisan",
        "votes": pd.NA,
        "elected": True if outcome_method == "acclamation" else pd.NA,
        "incumbent_reported": pd.NA,
        "eligible_electors": pd.NA,
        "ballots_cast": pd.NA,
        "turnout_scope": pd.NA,
        "outcome_method": outcome_method,
        "result_status": result_status,
        "coverage_status": "complete",
        "source_authority": "City of Toronto",
        "source_resource": _SOURCE_RESOURCE,
        "source_detail": source_detail,
    }


def _mayor_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise TypeError("official mayor roster is missing its candidates array")
    rows = []
    for value in candidates:
        candidate = _active_candidate(value)
        if candidate is not None:
            rows.append(
                _candidate_row(
                    candidate,
                    office_type="mayor",
                    official_district_id="city",
                    district_name="City of Toronto",
                    source_detail=MAYOR_CANDIDATES_URL,
                )
            )
    if not rows:
        raise ValueError("official mayor roster contains no active candidates")
    return rows


def _councillor_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    wards = payload.get("ward")
    if not isinstance(wards, list):
        raise TypeError("official councillor roster is missing its ward array")

    rows = []
    seen_wards: set[int] = set()
    for ward_entry in wards:
        if not isinstance(ward_entry, dict):
            raise TypeError("official councillor ward entry is not an object")
        try:
            ward = int(_text(ward_entry.get("num"), field="ward number"))
        except ValueError as exc:
            raise ValueError(
                f"invalid official councillor ward number: {ward_entry.get('num')!r}"
            ) from exc
        if ward not in _WARD_NAMES:
            raise ValueError(f"official councillor roster has an out-of-scope ward: {ward}")
        if ward in seen_wards:
            raise ValueError(f"official councillor roster repeats ward {ward}")
        seen_wards.add(ward)

        candidates = ward_entry.get("candidate")
        if not isinstance(candidates, list):
            raise TypeError(f"official councillor ward {ward} is missing its candidate array")
        active_in_ward = 0
        for value in candidates:
            candidate = _active_candidate(value)
            if candidate is None:
                continue
            active_in_ward += 1
            rows.append(
                _candidate_row(
                    candidate,
                    office_type="councillor",
                    official_district_id=f"ward-{ward}",
                    district_name=f"Ward {ward} — {_WARD_NAMES[ward]}",
                    source_detail=COUNCILLOR_CANDIDATES_URL,
                )
            )
        if active_in_ward == 0:
            raise ValueError(f"official councillor ward {ward} contains no active candidates")

    expected_wards = set(_WARD_NAMES)
    if seen_wards != expected_wards:
        missing = sorted(expected_wards - seen_wards)
        unexpected = sorted(seen_wards - expected_wards)
        raise ValueError(
            "official councillor roster does not cover the 25-ward regime: "
            f"missing={missing}, unexpected={unexpected}"
        )
    return rows


def _trustee_rows(
    payload: dict[str, object], crosswalk_path: str | Path
) -> list[dict[str, object]]:
    boards = payload.get("schoolBoard")
    if not isinstance(boards, list):
        raise TypeError("official trustee roster is missing its schoolBoard array")

    crosswalk = load_trustee_ward_crosswalk(crosswalk_path)
    crosswalk_by_key = {
        (str(row.board_id), int(row.ward_id)): row for row in crosswalk.itertuples(index=False)
    }
    rows: list[dict[str, object]] = []
    seen_boards: set[str] = set()
    seen_contests: set[tuple[str, int]] = set()

    for board_entry in boards:
        if not isinstance(board_entry, dict):
            raise TypeError("official trustee school-board entry is not an object")
        try:
            office_code = int(board_entry.get("id"))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"invalid official trustee board id: {board_entry.get('id')!r}"
            ) from exc
        board_id = BOARD_ID_BY_OFFICE_CODE.get(office_code)
        if board_id is None:
            raise ValueError(f"official trustee roster has unexpected board id: {office_code}")
        if board_id in seen_boards:
            raise ValueError(f"official trustee roster repeats board {board_id}")
        seen_boards.add(board_id)
        metadata = BOARD_METADATA[board_id]

        wards = board_entry.get("ward")
        if not isinstance(wards, list):
            raise TypeError(f"official trustee board {board_id} is missing its ward array")
        seen_wards: set[int] = set()
        for ward_entry in wards:
            if not isinstance(ward_entry, dict):
                raise TypeError("official trustee ward entry is not an object")
            try:
                ward = int(_text(ward_entry.get("num"), field="trustee ward number"))
            except ValueError as exc:
                raise ValueError(
                    f"invalid official trustee ward number: {ward_entry.get('num')!r}"
                ) from exc
            if ward in seen_wards:
                raise ValueError(f"official trustee roster repeats {board_id} ward {ward}")
            seen_wards.add(ward)
            key = (board_id, ward)
            if key not in crosswalk_by_key:
                raise ValueError(f"official trustee roster has out-of-scope contest {key!r}")
            if key in seen_contests:
                raise ValueError(f"official trustee roster repeats contest {key!r}")
            seen_contests.add(key)

            candidates = ward_entry.get("candidate")
            if not isinstance(candidates, list):
                raise TypeError(
                    f"official trustee {board_id} ward {ward} is missing its candidate array"
                )
            active = [candidate for value in candidates if (candidate := _active_candidate(value))]
            if not active:
                raise ValueError(
                    f"official trustee {board_id} ward {ward} contains no active candidates"
                )
            raw_names = [_text(candidate.get("name"), field="name") for candidate in active]
            if len(raw_names) != len(set(raw_names)):
                raise ValueError(
                    f"official trustee {board_id} ward {ward} repeats an active candidacy"
                )

            acclaimed_name = _TRUSTEE_ACCLAMATIONS.get(key)
            if acclaimed_name is not None:
                canonical_names = [
                    " ".join(
                        part
                        for value in [candidate.get("firstName"), candidate.get("lastName")]
                        if (part := _optional_text(value)) is not None
                    )
                    for candidate in active
                ]
                if canonical_names != [acclaimed_name]:
                    raise ValueError(
                        f"declared acclamation {board_id} ward {ward} must contain only "
                        f"{acclaimed_name}"
                    )

            district = crosswalk_by_key[key]
            for candidate in active:
                outcome_method = "acclamation" if acclaimed_name is not None else "pending"
                detail = TRUSTEE_CANDIDATES_URL
                if acclaimed_name is not None:
                    detail = f"{detail};{TRUSTEE_ACCLAMATION_URL}"
                rows.append(
                    _candidate_row(
                        candidate,
                        office_type="trustee",
                        official_district_id=str(ward),
                        district_name=str(district.district_name),
                        source_detail=detail,
                        represented_body=str(metadata["represented_body"]),
                        boundary_regime=str(metadata["boundary_regime"]),
                        expected_office=office_code,
                        outcome_method=outcome_method,
                        result_status="final" if acclaimed_name is not None else "pending",
                    )
                )

        if tuple(sorted(seen_wards)) != EXPECTED_WARDS[board_id]:
            raise ValueError(
                f"official trustee {board_id} roster does not cover the expected wards: "
                f"expected={list(EXPECTED_WARDS[board_id])}, actual={sorted(seen_wards)}"
            )

    if seen_boards != set(EXPECTED_WARDS):
        raise ValueError(
            "official trustee roster does not cover the four expected boards: "
            f"missing={sorted(set(EXPECTED_WARDS) - seen_boards)}"
        )
    return rows


def _pending_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=PENDING_ADAPTER_COLUMNS)
    for column in ["votes", "eligible_electors", "ballots_cast"]:
        frame[column] = frame[column].astype("Int64")
    for column in ["elected", "incumbent_reported"]:
        frame[column] = frame[column].astype("boolean")
    for column in ["party_name_raw", "turnout_scope"]:
        frame[column] = frame[column].astype("string")
    return frame.reset_index(drop=True)


def parse_pending_candidate_rosters(
    mayor_path: str | Path,
    councillor_path: str | Path,
    trustee_path: str | Path,
    *,
    trustee_crosswalk_path: str | Path = Path("data/reference") / TRUSTEE_CROSSWALK_FILENAME,
) -> pd.DataFrame:
    """Parse official cached rosters into pending source-adapter rows."""

    rows = [
        *_mayor_rows(_load_json(mayor_path)),
        *_councillor_rows(_load_json(councillor_path)),
        *_trustee_rows(_load_json(trustee_path), trustee_crosswalk_path),
    ]
    return _pending_frame(rows)


def load_pending_council_candidates(
    source_dir: str | Path = Path("data/raw/pending_candidates"),
    *,
    download: bool = False,
    session: requests.Session | None = None,
    overwrite: bool = False,
    trustee_crosswalk_path: str | Path = Path("data/reference") / TRUSTEE_CROSSWALK_FILENAME,
) -> pd.DataFrame:
    """Load all certified 2026 Toronto municipal candidate rosters."""

    paths = pending_candidate_paths(source_dir)
    if download:
        paths = download_pending_candidate_rosters(
            source_dir,
            session=session,
            overwrite=overwrite,
        )
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "missing official 2026 candidate roster file(s): " + ", ".join(missing)
        )
    return parse_pending_candidate_rosters(
        *paths,
        trustee_crosswalk_path=trustee_crosswalk_path,
    )
