"""Official City of Toronto 2026 pending-candidate adapter."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from toronto_election_results.pending_candidates import (
    BOUNDARY_REGIME,
    COUNCILLOR_CANDIDATES_FILENAME,
    COUNCILLOR_CANDIDATES_URL,
    ELECTION_DATE,
    MAYOR_CANDIDATES_FILENAME,
    MAYOR_CANDIDATES_URL,
    PENDING_ADAPTER_COLUMNS,
    download_pending_candidate_rosters,
    load_pending_council_candidates,
    parse_pending_candidate_rosters,
    pending_candidate_paths,
)
from toronto_election_results.schema import (
    derive_result_metrics,
    normalize_adapter_frame,
    stable_id,
)

FIXTURES = Path(__file__).parent / "fixtures" / "pending_candidates"
MAYOR_FIXTURE = FIXTURES / MAYOR_CANDIDATES_FILENAME
COUNCILLOR_FIXTURE = FIXTURES / COUNCILLOR_CANDIDATES_FILENAME


def test_parser_emits_active_certified_candidates_as_pending_adapter_rows():
    results = parse_pending_candidate_rosters(MAYOR_FIXTURE, COUNCILLOR_FIXTURE)

    assert list(results.columns) == PENDING_ADAPTER_COLUMNS
    assert len(results) == 27
    assert results["office_type"].value_counts().to_dict() == {
        "councillor": 25,
        "mayor": 2,
    }
    assert "Withdrawn, Wendy" not in set(results["candidate_name_raw"])
    assert "One, Inactive" not in set(results["candidate_name_raw"])

    assert (
        results["event_id"]
        .eq(stable_id("evt", "toronto_city_clerk", ELECTION_DATE, "general"))
        .all()
    )
    assert results["election_date"].eq(pd.Timestamp(ELECTION_DATE).date()).all()
    assert results["boundary_regime"].eq(BOUNDARY_REGIME).all()
    assert results["result_status"].eq("pending").all()
    assert results["outcome_method"].eq("pending").all()
    assert results["coverage_status"].eq("complete").all()
    assert results["votes"].isna().all()
    assert results["elected"].isna().all()
    assert results["eligible_electors"].isna().all()
    assert results["ballots_cast"].isna().all()
    assert results["turnout_scope"].isna().all()

    normalized = normalize_adapter_frame(results)
    derived = derive_result_metrics(normalized)
    assert derived["turnout"].isna().all()
    assert derived["vote_share"].isna().all()
    assert derived["vote_rank"].isna().all()


def test_parser_preserves_official_raw_name_and_uses_first_plus_last_as_canonical_name():
    results = parse_pending_candidate_rosters(MAYOR_FIXTURE, COUNCILLOR_FIXTURE)

    alaa = results.loc[results["candidate_name_raw"].eq("Adib, Alaa")].iloc[0]
    assert alaa["candidate_name"] == "Ala'a Adib"

    mayor = results.loc[results["office_type"].eq("mayor")]
    assert set(mayor["official_district_id"]) == {"city"}
    assert set(mayor["district_name"]) == {"City of Toronto"}
    ward_25 = results.loc[results["official_district_id"].eq("ward-25")].iloc[0]
    assert ward_25["district_name"] == "Ward 25 — Scarborough-Rouge Park"
    nisha = results.loc[results["candidate_name_raw"].eq("Nisha Kumari")].iloc[0]
    assert nisha["candidate_name"] == "Nisha Kumari"
    assert (
        results.loc[results["office_type"].eq("councillor"), "official_district_id"].nunique() == 25
    )


def test_adapter_excludes_contact_social_status_and_source_occurrence_fields():
    results = parse_pending_candidate_rosters(MAYOR_FIXTURE, COUNCILLOR_FIXTURE)

    forbidden = {
        "email",
        "phone",
        "socialMedias",
        "dateNomination",
        "status",
        "source_candidacy_id",
    }
    assert forbidden.isdisjoint(results.columns)
    assert set(results["source_detail"]) == {
        MAYOR_CANDIDATES_URL,
        COUNCILLOR_CANDIDATES_URL,
    }
    assert set(results["source_authority"]) == {"City of Toronto"}
    assert results["source_resource"].eq("2026 Municipal Election — Certified Candidates").all()


class _Response:
    def __init__(self, content: bytes):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        assert chunk_size > 0
        midpoint = len(self.content) // 2
        return iter((self.content[:midpoint], self.content[midpoint:]))


class _Session:
    def __init__(self, payloads: dict[str, bytes]):
        self.payloads = payloads
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Response(self.payloads[url])


def test_downloader_is_atomic_idempotent_and_uses_only_the_two_active_rosters(tmp_path):
    session = _Session(
        {
            MAYOR_CANDIDATES_URL: MAYOR_FIXTURE.read_bytes(),
            COUNCILLOR_CANDIDATES_URL: COUNCILLOR_FIXTURE.read_bytes(),
        }
    )

    first = download_pending_candidate_rosters(tmp_path, session=session)
    second = download_pending_candidate_rosters(tmp_path, session=session)

    assert first == second == pending_candidate_paths(tmp_path)
    assert [url for url, _kwargs in session.calls] == [
        MAYOR_CANDIDATES_URL,
        COUNCILLOR_CANDIDATES_URL,
    ]
    assert all(kwargs == {"stream": True, "timeout": 300} for _url, kwargs in session.calls)
    assert not list(tmp_path.glob("*.part"))
    assert first[0].read_bytes() == MAYOR_FIXTURE.read_bytes()
    assert first[1].read_bytes() == COUNCILLOR_FIXTURE.read_bytes()


def test_invalid_overwrite_never_replaces_a_valid_cached_roster(tmp_path):
    destination = tmp_path / MAYOR_CANDIDATES_FILENAME
    destination.write_bytes(MAYOR_FIXTURE.read_bytes())
    session = _Session(
        {
            MAYOR_CANDIDATES_URL: b"not-json",
            COUNCILLOR_CANDIDATES_URL: COUNCILLOR_FIXTURE.read_bytes(),
        }
    )

    with pytest.raises(json.JSONDecodeError):
        download_pending_candidate_rosters(tmp_path, session=session, overwrite=True)

    assert destination.read_bytes() == MAYOR_FIXTURE.read_bytes()
    assert not list(tmp_path.glob("*.part"))


def test_loader_reads_the_deterministic_cache_paths(tmp_path):
    mayor_path, councillor_path = pending_candidate_paths(tmp_path)
    shutil.copyfile(MAYOR_FIXTURE, mayor_path)
    shutil.copyfile(COUNCILLOR_FIXTURE, councillor_path)

    results = load_pending_council_candidates(tmp_path)

    assert len(results) == 27
    assert set(results["official_district_id"]) >= {"city", "ward-1", "ward-25"}


def test_parser_rejects_a_partial_ward_inventory(tmp_path):
    payload = json.loads(COUNCILLOR_FIXTURE.read_text(encoding="utf-8"))
    payload["ward"] = payload["ward"][:-1]
    partial = tmp_path / COUNCILLOR_CANDIDATES_FILENAME
    partial.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="does not cover the 25-ward regime"):
        parse_pending_candidate_rosters(MAYOR_FIXTURE, partial)
