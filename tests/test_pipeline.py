"""Public command behavior for the v2 release pipeline."""

import json
from types import SimpleNamespace

import pandas as pd
import pytest

from toronto_election_results import (
    assemble,
    crosscheck_winners,
    geometry,
    pipeline,
)
from toronto_election_results import (
    validate as legacy_validate,
)
from toronto_election_results.release import ReleaseTables


def test_prior_manifest_marks_completion_of_the_candidacy_ledger_migration(tmp_path):
    ledger = tmp_path / "reference" / "candidacy_identity_ledger.csv"
    ledger.parent.mkdir()
    ledger.write_text("candidacy_id\n", encoding="utf-8")
    output = tmp_path / "out"
    output.mkdir()
    manifest = output / "build_manifest.json"
    manifest.write_text(
        json.dumps({"sources": [{"local_path": "data/reference/roster_agent_a.txt"}]}),
        encoding="utf-8",
    )

    assert not pipeline._prior_manifest_tracks_ledger(output, ledger)

    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "local_path": ledger.as_posix(),
                        "sha256": pipeline.sha256_file(ledger),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert pipeline._prior_manifest_tracks_ledger(output, ledger)
    pipeline._verify_prior_ledger_checksum(output, ledger)

    with ledger.open("a", encoding="utf-8") as handle:
        handle.write("\n")

    with pytest.raises(ValueError, match="ledger checksum"):
        pipeline._verify_prior_ledger_checksum(output, ledger)


def test_pipeline_refuses_a_missing_ledger_after_a_ledger_backed_release(tmp_path, monkeypatch):
    reference = tmp_path / "reference"
    ledger = reference / pipeline.CANDIDACY_LEDGER_FILENAME
    output = tmp_path / "out"
    output.mkdir()
    (output / "build_manifest.json").write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "local_path": ledger.as_posix(),
                        "sha256": "previous-ledger-hash",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        pipeline,
        "_load_source_adapters",
        lambda **_: pytest.fail("source adapters must not load before ledger recovery"),
    )

    with pytest.raises(ValueError, match="persisted Candidacy ledger is missing"):
        pipeline.run_all(
            skip_download=True,
            raw=tmp_path / "raw",
            interim=tmp_path / "interim",
            out=output,
            reference=reference,
        )


def test_prior_identity_registry_requires_both_persisted_tables(tmp_path):
    people = pd.DataFrame(
        {
            "person_id": ["per_persisted"],
            "preferred_name": ["Alex Example"],
            "identity_status": ["active"],
            "redirect_to_person_id": [pd.NA],
            "created_release": ["2026-08-20"],
        }
    )
    links = pd.DataFrame(
        {
            "candidacy_id": ["can_persisted"],
            "person_id": ["per_persisted"],
            "link_status": ["confirmed"],
            "method": ["audited"],
            "evidence": ["official source"],
            "reviewer": ["curator"],
            "valid_from_release": ["2026-08-20"],
            "valid_to_release": [pd.NA],
        }
    )
    people.to_csv(tmp_path / "people.csv", index=False)
    links.to_csv(tmp_path / "candidacy_person_links.csv", index=False)
    pd.DataFrame({"candidacy_id": ["can_persisted"]}).to_csv(
        tmp_path / "election_results.csv", index=False
    )
    ledger = pd.DataFrame(
        {"candidacy_id": ["can_persisted", "can_new_release"], "valid_to_release": [pd.NA, pd.NA]}
    )

    loaded_people, loaded_links = pipeline._load_existing_identity_registry(tmp_path, ledger)

    assert loaded_people["person_id"].tolist() == ["per_persisted"]
    assert loaded_links["candidacy_id"].tolist() == ["can_persisted"]

    artifact_paths = [
        tmp_path / "people.csv",
        tmp_path / "candidacy_person_links.csv",
        tmp_path / "election_results.csv",
    ]
    (tmp_path / "build_manifest.json").write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "local_path": path.as_posix(),
                        "sha256": pipeline.sha256_file(path),
                    }
                    for path in artifact_paths
                ]
            }
        ),
        encoding="utf-8",
    )
    pipeline._load_existing_identity_registry(
        tmp_path,
        ledger,
        verify_artifact_hashes=True,
    )
    with (tmp_path / "candidacy_person_links.csv").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="checksum"):
        pipeline._load_existing_identity_registry(
            tmp_path,
            ledger,
            verify_artifact_hashes=True,
        )
    links.to_csv(tmp_path / "candidacy_person_links.csv", index=False)

    (tmp_path / "candidacy_person_links.csv").unlink()
    with pytest.raises(ValueError, match="both people.csv and candidacy_person_links.csv"):
        pipeline._load_existing_identity_registry(tmp_path, ledger)

    links.to_csv(tmp_path / "candidacy_person_links.csv", index=False)
    (tmp_path / "people.csv").unlink()
    (tmp_path / "candidacy_person_links.csv").unlink()
    with pytest.raises(ValueError, match="checksum"):
        pipeline._load_existing_identity_registry(
            tmp_path,
            ledger,
            verify_artifact_hashes=True,
        )


def test_incompatible_draft_registry_cannot_seed_persistent_people(tmp_path):
    pd.DataFrame(
        {
            "person_id": ["per_old"],
            "preferred_name": ["Alex"],
            "identity_status": ["active"],
            "redirect_to_person_id": [pd.NA],
            "created_release": ["draft"],
        }
    ).to_csv(tmp_path / "people.csv", index=False)
    pd.DataFrame(
        {
            "candidacy_id": ["can_name_derived"],
            "person_id": ["per_old"],
            "link_status": ["confirmed"],
            "method": ["draft"],
            "evidence": ["draft"],
            "reviewer": ["draft"],
            "valid_from_release": ["draft"],
            "valid_to_release": [pd.NA],
        }
    ).to_csv(tmp_path / "candidacy_person_links.csv", index=False)
    pd.DataFrame({"candidacy_id": ["can_name_derived"]}).to_csv(
        tmp_path / "election_results.csv", index=False
    )
    ledger = pd.DataFrame({"candidacy_id": ["can_persistent"], "valid_to_release": [pd.NA]})

    with pytest.raises(
        pipeline.PriorRegistryCandidacyMismatch,
        match="incompatible with the active Candidacy ledger",
    ):
        pipeline._load_existing_identity_registry(tmp_path, ledger)


def test_prior_registry_cannot_silently_drop_a_candidacy_link_state(tmp_path):
    pd.DataFrame(
        {
            "person_id": ["per_one"],
            "preferred_name": ["Alex"],
            "identity_status": ["active"],
            "redirect_to_person_id": [pd.NA],
            "created_release": ["2026-08-20"],
        }
    ).to_csv(tmp_path / "people.csv", index=False)
    pd.DataFrame(
        {
            "candidacy_id": ["can_one"],
            "person_id": ["per_one"],
            "link_status": ["confirmed"],
            "method": ["audited"],
            "evidence": ["official"],
            "reviewer": ["curator"],
            "valid_from_release": ["2026-08-20"],
            "valid_to_release": [pd.NA],
        }
    ).to_csv(tmp_path / "candidacy_person_links.csv", index=False)
    pd.DataFrame({"candidacy_id": ["can_one", "can_two"]}).to_csv(
        tmp_path / "election_results.csv", index=False
    )
    ledger = pd.DataFrame(
        {
            "candidacy_id": ["can_one", "can_two"],
            "valid_to_release": [pd.NA, pd.NA],
        }
    )

    with pytest.raises(ValueError, match="active identity-registry state"):
        pipeline._load_existing_identity_registry(tmp_path, ledger)


def test_pipeline_advances_ledger_before_promoting_public_release(tmp_path, monkeypatch):
    calls: list[str] = []
    assembled_kwargs: dict[str, object] = {}
    empty = pd.DataFrame()
    tables = ReleaseTables(
        election_results=empty,
        election_events=empty,
        contests=empty,
        people=empty,
        candidacy_person_links=empty,
        parties=empty,
        office_tenures=empty,
        electoral_districts=empty,
    )
    assignment = SimpleNamespace(adapter_frames=[empty], ledger=empty)
    built = SimpleNamespace(tables=tables, candidacy_ledger=empty)
    monkeypatch.setattr(pipeline, "read_candidacy_ledger", lambda _: empty)
    monkeypatch.setattr(pipeline, "_load_source_adapters", lambda **_: ([empty], empty))
    monkeypatch.setattr(pipeline, "assign_candidacy_ids", lambda *_, **__: assignment)
    monkeypatch.setattr(pipeline, "build_mayoral_career_identity_assertions", lambda *_, **__: ())
    monkeypatch.setattr(
        pipeline, "exclude_superseded_identity_decisions", lambda decisions, *_: decisions
    )

    def assemble(*_, **kwargs):
        assembled_kwargs.update(kwargs)
        return built

    monkeypatch.setattr(pipeline, "assemble_bootstrapped_release", assemble)
    monkeypatch.setattr(pipeline, "enrich_district_geometries", lambda frame: frame)
    monkeypatch.setattr(
        pipeline,
        "build_default_endorsement_inputs",
        lambda *_args, **_kwargs: SimpleNamespace(
            endorsers=empty,
            assertions=empty,
            coverage=empty,
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "assemble_endorsement_tables",
        lambda **_: SimpleNamespace(
            endorsers=empty,
            endorsement_assertions=empty,
            endorsements=empty,
            endorsement_coverage=empty,
        ),
    )
    monkeypatch.setattr(pipeline, "validate_tables", lambda _: [])
    monkeypatch.setattr(
        pipeline,
        "write_candidacy_ledger",
        lambda *_: calls.append("ledger"),
    )

    def fail_during_release(*_):
        calls.append("release")
        raise RuntimeError("simulated release promotion failure")

    monkeypatch.setattr(pipeline, "write_release", fail_during_release)

    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / pipeline.IDENTITY_REVIEW_DISPOSITIONS_FILENAME).write_text(
        "candidacy_id,target_person_id,decision,confidence,rationale,evidence_urls,reviewer\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="simulated release promotion failure"):
        pipeline.run_all(
            skip_download=True,
            raw=tmp_path / "raw",
            interim=tmp_path / "interim",
            out=tmp_path / "out",
            reference=reference,
        )

    assert calls == ["ledger", "release"]
    assert assembled_kwargs["identity_review_decisions"].empty


def test_legacy_assemble_entrypoint_refuses_to_publish_v1_outputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="toronto_election_results.pipeline"):
        assemble.main()

    assert not (tmp_path / "data" / "out").exists()


@pytest.mark.parametrize(
    "entrypoint",
    [legacy_validate.main, geometry.main, crosscheck_winners.main],
)
def test_other_legacy_entrypoints_point_to_v2_pipeline_without_reading_v1_outputs(
    entrypoint, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="toronto_election_results.pipeline"):
        entrypoint()

    assert not (tmp_path / "data" / "out").exists()
