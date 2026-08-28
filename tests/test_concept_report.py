"""Atomic report tests for Phase 16 concept evaluation."""

from __future__ import annotations

import json

import pytest

import pada3dacb.evaluation.concepts.report as report_module
from pada3dacb.evaluation.concepts.report import (
    ConceptEvaluationPlan,
    _synthetic_status_rows,
    build_artifact_index,
    build_completion_manifest,
    build_concept_output_plan,
    build_synthetic_fixture_bundle,
    commit_output,
    verify_completed_output,
)
from pada3dacb.evaluation.schemas import CheckpointPolicy, Direction, MethodId


def _write_owner_metadata(entry, *, pid: int, token: str) -> None:
    (entry / ".pada3dacb-owner.json").write_text(
        json.dumps({"schema_version": "1", "pid": pid, "token": token}), encoding="utf-8"
    )


def _completed_bundle(identity: str, *, analysis_mode: str = "synthetic_test_only") -> tuple[ConceptEvaluationPlan, dict[str, bytes]]:
    plan = ConceptEvaluationPlan(
        evaluation_identity=identity,
        analysis_mode=analysis_mode,
        methods=(MethodId.SOURCE_ONLY,),
        directions=(Direction.ADNI_TO_OASIS,),
        checkpoint_policies=(CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        intended_relative_paths=("data.csv", "artifact_index.json", "evaluation_manifest.json"),
    )
    ordinary = {"data.csv": f"{identity}\n".encode()}
    artifacts = dict(ordinary)
    artifacts["artifact_index.json"] = build_artifact_index(ordinary)
    artifacts["evaluation_manifest.json"] = build_completion_manifest(
        plan,
        ordinary,
        {},
        {},
        1,
        1,
        "none",
        {},
        "1970-01-01T00:00:00Z",
        "1970-01-01T00:00:00Z",
    )
    return plan, artifacts


def test_synthetic_status_rows_do_not_duplicate_not_applicable_methods() -> None:
    rows = _synthetic_status_rows(
        (MethodId.AAGN,),
        (Direction.ADNI_TO_OASIS,),
        (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
    )

    statuses = [row for row in rows if row["method"] == MethodId.AAGN.value]
    assert len(statuses) == 1
    assert statuses[0]["status"] == "not_applicable_no_pada3dacb_concept_head"


def test_output_plan_contains_files_only_and_is_deterministic() -> None:
    first = build_concept_output_plan(
        "fixture-identity",
        "synthetic_test_only",
        methods=(MethodId.SOURCE_ONLY,),
        directions=(Direction.ADNI_TO_OASIS,),
        checkpoint_policies=(CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        included_methods=(MethodId.SOURCE_ONLY,),
    )
    second = build_concept_output_plan(
        "fixture-identity",
        "synthetic_test_only",
        methods=(MethodId.SOURCE_ONLY,),
        directions=(Direction.ADNI_TO_OASIS,),
        checkpoint_policies=(CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        included_methods=(MethodId.SOURCE_ONLY,),
    )

    assert first == second
    assert len(first.intended_relative_paths) == len(set(first.intended_relative_paths))
    assert all(not path.endswith("/") for path in first.intended_relative_paths)
    assert any(path.endswith("subject_outputs/subject_outputs.csv") for path in first.intended_relative_paths)
    assert first.intended_relative_paths[-1] == "evaluation_manifest.json"
    assert "artifact_index.json" in first.intended_relative_paths


@pytest.mark.parametrize("method", (MethodId.AAGN, MethodId.FASTER_SNN))
def test_not_applicable_baseline_has_no_included_concept_output_plan(method) -> None:
    plan = build_concept_output_plan(
        "fixture-identity",
        "synthetic_test_only",
        methods=(method,),
        directions=(Direction.ADNI_TO_OASIS,),
        checkpoint_policies=(CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        included_methods=(),
    )

    assert not any(path.startswith("concepts/") for path in plan.intended_relative_paths)
    assert plan.methods == (method,)


def test_artifact_index_is_self_excluding_and_sorted() -> None:
    payload = build_artifact_index({"z.csv": b"z\n", "a.csv": b"a\n"})
    decoded = json.loads(payload)

    assert list(decoded["artifacts"]) == ["a.csv", "z.csv"]
    with pytest.raises(ValueError, match="exclude itself"):
        build_artifact_index({"artifact_index.json": b"invalid"})


def test_commit_output_requires_exact_allowlisted_tree(tmp_path) -> None:
    plan, artifacts = _completed_bundle("fixture")

    output = commit_output(tmp_path / "results", plan, artifacts)

    assert (output / "data.csv").read_bytes() == b"fixture\n"
    with pytest.raises(ValueError, match="exactly match"):
        commit_output(tmp_path / "bad", plan, {"data.csv": b"value\n"})


def test_overwrite_rejects_unknown_existing_paths(tmp_path) -> None:
    plan, artifacts = _completed_bundle("fixture")
    output = commit_output(tmp_path / "results", plan, artifacts)
    (output / "unplanned.txt").write_text("keep me", encoding="utf-8")

    with pytest.raises(RuntimeError, match="unknown output paths"):
        commit_output(output, plan, artifacts, overwrite=True)
    assert (output / "unplanned.txt").read_text(encoding="utf-8") == "keep me"


def test_synthetic_bundle_is_deterministic_manifest_last_and_reusable(tmp_path) -> None:
    kwargs = {
        "evaluation_identity": "fixture-identity",
        "methods": (MethodId.SOURCE_ONLY,),
        "directions": (Direction.ADNI_TO_OASIS,),
        "checkpoint_policies": (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        "metrics": {"fixture_only": True, "concept_mae": 0.05},
        "resolved_config": {"analysis_mode": "synthetic_test_only"},
        "identity_inputs": {
            "configuration_sha256": "a" * 64,
            "authorization_sha256": "0" * 64,
            "ordered_input_sha256s": [],
        },
        "library_versions": {"python": "test"},
        "bootstrap_replicates": 100,
        "bootstrap_seed": 7,
    }
    first_plan, first_artifacts = build_synthetic_fixture_bundle(**kwargs)
    second_plan, second_artifacts = build_synthetic_fixture_bundle(**kwargs)
    assert first_plan == second_plan
    assert first_artifacts == second_artifacts
    table_root = "concepts/adni_to_oasis/best_source_f1/tables"
    figure_root = "concepts/adni_to_oasis/best_source_f1/figures"
    assert sum(path.startswith(table_root) for path in first_artifacts) == 11
    assert sum(path.startswith(figure_root) for path in first_artifacts) == 5
    assert first_artifacts[f"{figure_root}/concept_fidelity_roi_heatmap.png"].startswith(
        b"\x89PNG\r\n\x1a\n"
    )

    write_order = []

    def recording_writer(path, payload) -> None:
        write_order.append(path.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    output = commit_output(
        tmp_path / "synthetic-results",
        first_plan,
        first_artifacts,
        writer=recording_writer,
    )

    assert write_order[-1] == "evaluation_manifest.json"
    manifest = verify_completed_output(output, expected_identity="fixture-identity")
    assert manifest["analysis_mode"] == "synthetic_test_only"

    (output / "evaluation_log.txt").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_completed_output(output, expected_identity="fixture-identity")


def test_non_overwrite_rejects_different_identity_without_mutating_base(tmp_path) -> None:
    plan_one, artifacts_one = _completed_bundle("identity-one")
    output = commit_output(tmp_path / "results", plan_one, artifacts_one)
    before = {path.relative_to(output).as_posix(): path.read_bytes() for path in output.rglob("*") if path.is_file()}

    plan_two, artifacts_two = _completed_bundle("identity-two")
    with pytest.raises(ValueError, match="explicit overwrite"):
        commit_output(output, plan_two, artifacts_two)

    assert {path.relative_to(output).as_posix(): path.read_bytes() for path in output.rglob("*") if path.is_file()} == before
    assert verify_completed_output(output)["evaluation_identity"] == "identity-one"


def test_non_overwrite_rejects_invalid_base_and_preserves_occupied_sibling(tmp_path) -> None:
    invalid = tmp_path / "invalid"
    invalid.mkdir()
    (invalid / "keep.txt").write_bytes(b"keep")
    plan, artifacts = _completed_bundle("identity")
    with pytest.raises(RuntimeError, match="unknown output paths"):
        commit_output(invalid, plan, artifacts)
    assert (invalid / "keep.txt").read_bytes() == b"keep"

    base_plan, base_artifacts = _completed_bundle("base")
    base = commit_output(tmp_path / "results", base_plan, base_artifacts)
    occupied = base.with_name("results.v000001")
    occupied.mkdir()
    (occupied / "untrusted.txt").write_bytes(b"preserve")
    with pytest.raises(ValueError, match="explicit overwrite"):
        commit_output(base, plan, artifacts)
    assert (occupied / "untrusted.txt").read_bytes() == b"preserve"


def test_unrecognized_allocation_lock_is_preserved_during_publication(tmp_path) -> None:
    stale_lock = tmp_path / ".results.allocation.lock"
    stale_lock.mkdir()
    _write_owner_metadata(stale_lock, pid=101, token="crashed-lock")

    plan, artifacts = _completed_bundle("preserve-lock")
    output = commit_output(tmp_path / "results", plan, artifacts)

    assert output == tmp_path / "results"
    assert output.is_dir()
    assert stale_lock.is_dir()
    assert json.loads((stale_lock / ".pada3dacb-owner.json").read_text()) == {
        "schema_version": "1", "pid": 101, "token": "crashed-lock"
    }


def test_unrecognized_stage_and_reservation_are_preserved_without_touching_output(tmp_path) -> None:
    stale_stage = tmp_path / ".results.stage.crashed-stage"
    stale_stage.mkdir()
    (stale_stage / "partial.bin").write_bytes(b"partial")
    _write_owner_metadata(stale_stage, pid=102, token="crashed-stage")
    stale_reservation = tmp_path / ".results.v000001.reserve.crashed-reservation"
    stale_reservation.mkdir()
    _write_owner_metadata(stale_reservation, pid=103, token="crashed-reservation")

    plan, artifacts = _completed_bundle("preserve-stage")
    output = commit_output(tmp_path / "results", plan, artifacts)

    assert output == tmp_path / "results"
    assert (output / "data.csv").read_bytes() == b"preserve-stage\n"
    assert (stale_stage / "partial.bin").read_bytes() == b"partial"
    assert stale_stage.is_dir()
    assert stale_reservation.is_dir()


def test_live_allocation_lock_is_not_reclaimed(tmp_path, monkeypatch) -> None:
    live_lock = tmp_path / ".results.allocation.lock"
    live_lock.mkdir()
    _write_owner_metadata(live_lock, pid=104, token="live-lock")
    monkeypatch.setattr(report_module, "_process_is_alive", lambda pid: True)

    with (
        pytest.raises(RuntimeError, match="busy"),
        report_module._allocation_lock(tmp_path, "results", timeout_seconds=0),
    ):
        raise AssertionError("live lock must not be acquired")

    assert live_lock.exists()


def test_recovery_does_not_delete_arbitrary_namespace_directories(tmp_path, monkeypatch) -> None:
    arbitrary = tmp_path / ".results.user-owned"
    arbitrary.mkdir()
    (arbitrary / "keep.txt").write_bytes(b"keep")
    monkeypatch.setattr(report_module, "_process_is_alive", lambda pid: False)

    plan, artifacts = _completed_bundle("preserve-arbitrary")
    commit_output(tmp_path / "results", plan, artifacts)

    assert (arbitrary / "keep.txt").read_bytes() == b"keep"


def test_controlled_entry_cleanup_retries_windows_permission_error(tmp_path, monkeypatch) -> None:
    entry = tmp_path / ".results.stage.owner"
    entry.mkdir()
    (entry / ".pada3dacb-owner.json").write_text("{}", encoding="utf-8")
    calls = 0
    sleeps = []
    real_rmtree = report_module.shutil.rmtree

    def flaky_rmtree(path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("transient Windows sharing violation")
        real_rmtree(path)

    monkeypatch.setattr(report_module.shutil, "rmtree", flaky_rmtree)
    monkeypatch.setattr(report_module.time, "sleep", sleeps.append)
    monkeypatch.setattr(report_module.os, "name", "nt")

    assert report_module._remove_controlled_entry(entry, tmp_path)
    assert calls == 2
    assert sleeps == [0.02]
    assert not entry.exists()


def test_same_identity_converges_on_canonical_output(tmp_path) -> None:
    plan, artifacts = _completed_bundle("same-identity")

    first = commit_output(tmp_path / "results", plan, artifacts)
    second = commit_output(tmp_path / "results", plan, artifacts)

    assert first == second == tmp_path / "results"
    assert verify_completed_output(second, expected_identity="same-identity")
    assert not list(tmp_path.glob("p3dco.*"))


def test_generic_completed_verification_accepts_non_fixture_mode(tmp_path) -> None:
    plan, artifacts = _completed_bundle("real-shaped", analysis_mode="real")
    output = commit_output(tmp_path / "results", plan, artifacts)
    assert verify_completed_output(output, expected_identity="real-shaped")["analysis_mode"] == "real"


def test_overwrite_rejects_invalid_completed_tree_without_modifying_it(tmp_path) -> None:
    plan, artifacts = _completed_bundle("identity")
    output = commit_output(tmp_path / "results", plan, artifacts)
    manifest_before = (output / "evaluation_manifest.json").read_bytes()
    (output / "artifact_index.json").write_bytes(b"tampered\\n")

    with pytest.raises(ValueError, match="artifact index hash mismatch"):
        commit_output(output, plan, artifacts, overwrite=True)
    assert (output / "artifact_index.json").read_bytes() == b"tampered\\n"
    assert (output / "evaluation_manifest.json").read_bytes() == manifest_before


def test_overwrite_failure_restores_prior_tree_and_writer_failure_cleans_stage(tmp_path) -> None:
    old_plan, old_artifacts = _completed_bundle("old")
    output = commit_output(tmp_path / "results", old_plan, old_artifacts)
    before = {path.relative_to(output).as_posix(): path.read_bytes() for path in output.rglob("*") if path.is_file()}
    new_plan, new_artifacts = old_plan, old_artifacts

    calls = 0

    def fail_publish(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replace failure")
        return __import__("os").replace(source, destination)

    with pytest.raises(report_module.PublicationBlocked, match="rollback succeeded") as error:
        commit_output(
            output,
            new_plan,
            new_artifacts,
            overwrite=True,
            replace=fail_publish,
            absent_window_timeout_seconds=1.0,
        )
    assert error.value.status == "BLOCKED"
    assert error.value.rollback_succeeded is True
    assert {path.relative_to(output).as_posix(): path.read_bytes() for path in output.rglob("*") if path.is_file()} == before
    preserved_candidates = list(tmp_path.glob("p3dco.*"))
    assert len(preserved_candidates) == 1
    assert preserved_candidates[0].is_dir()
    assert not list(tmp_path.glob(".results.backup.*"))

    def fail_writer(path, payload):
        if path.name == "data.csv":
            raise OSError("injected writer failure")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    with pytest.raises(report_module.PublicationBlocked, match="durability boundary"):
        commit_output(
            output,
            new_plan,
            new_artifacts,
            overwrite=True,
            writer=fail_writer,
            absent_window_timeout_seconds=1.0,
        )
    assert {path.relative_to(output).as_posix(): path.read_bytes() for path in output.rglob("*") if path.is_file()} == before
    assert len(list(tmp_path.glob("p3dco.*"))) == 2
    assert not list(tmp_path.glob(".results.backup.*"))
