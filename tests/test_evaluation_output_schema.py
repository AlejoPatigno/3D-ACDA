from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from pada3dacb.evaluation.report import (
    build_artifact_index,
    build_completion_manifest,
    build_output_plan,
    build_report_statistics,
    commit_output,
    project_and_commit_output,
)
from pada3dacb.evaluation.schemas import (
    AnalysisMode,
    CheckpointPolicy,
    Direction,
    ExistingOutputError,
    MethodId,
    OutputCommitError,
    SubjectPrediction,
)

ROOT_FILES = {
    "evaluation_config_resolved.yaml",
    "provenance_report.json",
    "method_status.csv",
    "computational_summary.csv",
    "evaluation_log.txt",
    "evaluation_manifest.json",
}


def _plan(included: tuple[MethodId, ...] = (MethodId.MMD,)):
    return build_output_plan(
        "a" * 64,
        AnalysisMode.SYNTHETIC_TEST_ONLY,
        (MethodId.MMD, MethodId.CORAL),
        (Direction.ADNI_TO_OASIS,),
        (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        included_methods=included,
    )


def _artifacts(plan) -> dict[str, bytes]:
    return {path: f"payload:{path}\n".encode() for path in plan.intended_relative_paths}


def _files(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def test_completion_manifest_contains_every_schema_v2_identity_field() -> None:
    plan = _plan()
    artifacts = {
        path: path.encode() for path in plan.intended_relative_paths
        if path != "evaluation_manifest.json"
    }
    payload = json.loads(build_completion_manifest(
        plan,
        artifacts,
        identity_inputs={
            "configuration_sha256": "b" * 64,
            "authorization_sha256": "c" * 64,
            "ordered_input_sha256s": ["d" * 64],
        },
        library_versions={"numpy": "2.3.2"},
        bootstrap_replicates=10_000,
        bootstrap_seed=17,
        ci_policy="percentile_95_linear",
        gate_states={
            "authorized_exports": True, "D-14-001": True,
            "D-14-002": True, "protocol_approval": True,
        },
        created_utc="2026-01-01T00:00:00Z",
        completed_utc="2026-01-01T00:01:00Z",
        disposition="completed_overwrite",
    ))
    assert payload["class_order"] == {"CN": 0, "MCI": 1, "AD": 2}
    assert payload["bootstrap"] == {
        "replicates": 10_000, "seed": 17, "ci_policy": "percentile_95_linear"
    }
    assert payload["configuration_sha256"] == "b" * 64
    assert payload["authorization_sha256"] == "c" * 64
    assert payload["gate_states"] == {
        "authorized_exports": True, "D-14-001": True,
        "D-14-002": True, "protocol_approval": True,
    }
    assert payload["created_utc"] < payload["completed_utc"]
    assert payload["ordered_input_sha256s"] == ["d" * 64]
    assert payload["disposition"] == "completed_overwrite"
    assert list(payload["output_sha256s"]) == sorted(artifacts)


def test_artifact_index_hashes_required_outputs_and_excludes_itself() -> None:
    payload = json.loads(build_artifact_index({"a.csv": b"a", "b.json": b"b"}))
    assert list(payload) == ["artifacts", "schema_version"]
    assert list(payload["artifacts"]) == ["a.csv", "b.json"]
    with pytest.raises(ValueError, match="exclude"):
        build_artifact_index({"artifact_index.json": b"recursive"})


def test_output_plan_places_optional_artifact_index_immediately_before_manifest() -> None:
    plan = build_output_plan(
        "a" * 64, AnalysisMode.SYNTHETIC_TEST_ONLY, (MethodId.MMD,),
        (Direction.ADNI_TO_OASIS,), (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        included_methods=(MethodId.MMD,), include_artifact_index=True,
    )
    assert plan.intended_relative_paths[-2:] == (
        "artifact_index.json", "evaluation_manifest.json"
    )


def test_output_plan_has_exact_root_policy_and_per_method_paths_without_identity_nesting() -> None:
    plan = _plan()
    paths = set(plan.intended_relative_paths)
    assert paths >= ROOT_FILES
    base = "predictive/adni_to_oasis/primary_best_source_f1"
    assert {
        f"{base}/inclusion_report.csv",
        f"{base}/metrics/predictive_metrics.csv",
        f"{base}/metrics/per_class_metrics.csv",
        f"{base}/confidence_intervals/predictive_metrics_with_ci.csv",
        f"{base}/pairwise_comparisons/pairwise_metric_differences.csv",
        f"{base}/pairwise_comparisons/mcnemar_results.csv",
        f"{base}/pairwise_comparisons/holm_adjusted.csv",
        f"{base}/tables/predictive_metrics_with_ci.csv",
        f"{base}/subject_predictions/mmd.csv",
    } <= paths
    confusion = f"{base}/confusion_matrices/mmd"
    assert {
        f"{confusion}/confusion_matrix_counts.csv",
        f"{confusion}/confusion_matrix_normalized.csv",
        f"{confusion}/confusion_matrix_counts.png",
        f"{confusion}/confusion_matrix_normalized.png",
    } <= paths
    assert all(not path.startswith(plan.evaluation_identity) for path in paths)
    assert plan.intended_relative_paths[-1] == "evaluation_manifest.json"


def test_excluded_methods_keep_header_complete_common_files_without_method_artifacts() -> None:
    plan = _plan(included=())
    paths = set(plan.intended_relative_paths)
    base = "predictive/adni_to_oasis/primary_best_source_f1"
    assert f"{base}/inclusion_report.csv" in paths
    assert f"{base}/metrics/predictive_metrics.csv" in paths
    assert not any("subject_predictions/" in path for path in paths)
    assert not any("confusion_matrices/" in path for path in paths)


def test_project_and_commit_builds_exact_hash_bound_completed_tree(tmp_path: Path) -> None:
    plan = build_output_plan(
        "a" * 64, AnalysisMode.SYNTHETIC_TEST_ONLY, (MethodId.MMD,),
        (Direction.ADNI_TO_OASIS,), (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        included_methods=(MethodId.MMD,), include_artifact_index=True,
    )
    rows = tuple(
        SubjectPrediction(
            MethodId.MMD, Direction.ADNI_TO_OASIS,
            CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, f"subject-{index}", truth,
            tuple(0.9 if label == truth else 0.05 for label in range(3)),
            5, 1, (f"{index + 1:064x}",),
        )
        for index, truth in enumerate((0, 0, 1, 1, 2, 2))
    )
    scope = (Direction.ADNI_TO_OASIS, CheckpointPolicy.PRIMARY_BEST_SOURCE_F1)
    statistics = build_report_statistics(
        {MethodId.MMD.value: rows}, bootstrap_replicates=3, bootstrap_seed=17
    )
    output = tmp_path / "evaluation"
    project_and_commit_output(
        output, plan, {scope: {MethodId.MMD: rows}}, {scope: statistics},
        root_metadata={
            "resolved_config": {"analysis_mode": "synthetic_test_only"},
            "provenance_records": (), "method_status_rows": (),
            "computational_rows": (), "log_events": (),
        },
        policy_metadata={scope: {"inclusion_rows": ()}},
        identity_inputs={
            "configuration_sha256": "b" * 64,
            "authorization_sha256": "c" * 64,
            "ordered_input_sha256s": ["d" * 64],
        },
        library_versions={"numpy": "2.3.2"}, bootstrap_replicates=3,
        bootstrap_seed=17, ci_policy="percentile_95_linear",
        gate_states={
            "authorized_exports": True, "D-14-001": True,
            "D-14-002": True, "protocol_approval": True,
        },
        created_utc="2026-01-01T00:00:00Z",
        completed_utc="2026-01-01T00:01:00Z",
    )
    assert _files(output) == set(plan.intended_relative_paths)
    index = json.loads((output / "artifact_index.json").read_bytes())
    manifest = json.loads((output / "evaluation_manifest.json").read_bytes())
    assert "artifact_index.json" not in index["artifacts"]
    assert set(manifest["output_sha256s"]) == set(plan.intended_relative_paths) - {
        "evaluation_manifest.json"
    }


def test_whole_run_commit_writes_manifest_last_and_publishes_exact_tree(tmp_path: Path) -> None:
    plan = _plan()
    artifacts = _artifacts(plan)
    written: list[str] = []

    def writer(path: Path, payload: bytes) -> None:
        written.append(path.as_posix())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    output = tmp_path / "evaluation"
    commit_output(output, plan, artifacts, writer=writer)
    assert _files(output) == set(plan.intended_relative_paths)
    assert output.joinpath("evaluation_manifest.json").read_bytes() == artifacts["evaluation_manifest.json"]
    assert written[-1].endswith("evaluation_manifest.json")
    assert not any(path.name.startswith(".evaluation.stage") for path in tmp_path.iterdir())


def test_publish_retries_transient_permission_error_only(tmp_path: Path) -> None:
    plan = _plan()
    output = tmp_path / "evaluation"
    calls = 0

    def transient_lock(source: str | Path, destination: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError("transient Windows lock")
        os.replace(source, destination)

    commit_output(output, plan, _artifacts(plan), replace=transient_lock)
    assert calls == 2
    assert _files(output) == set(plan.intended_relative_paths)


def test_existing_output_requires_guarded_overwrite_and_rejects_unknown_files(tmp_path: Path) -> None:
    plan = _plan()
    artifacts = _artifacts(plan)
    output = tmp_path / "evaluation"
    commit_output(output, plan, artifacts)
    with pytest.raises(ExistingOutputError):
        commit_output(output, plan, artifacts)
    (output / "unknown.txt").write_text("user file", encoding="utf-8")
    with pytest.raises(ExistingOutputError, match="unknown"):
        commit_output(output, plan, artifacts, overwrite=True)
    assert (output / "unknown.txt").read_text(encoding="utf-8") == "user file"


def test_guarded_overwrite_replaces_only_exact_known_tree(tmp_path: Path) -> None:
    plan = _plan()
    output = tmp_path / "evaluation"
    original = _artifacts(plan)
    commit_output(output, plan, original)
    replacement = {path: b"new:" + payload for path, payload in original.items()}
    commit_output(output, plan, replacement, overwrite=True)
    assert _files(output) == set(plan.intended_relative_paths)
    assert all((output / path).read_bytes() == replacement[path] for path in plan.intended_relative_paths)


def test_failed_overwrite_restores_completed_tree_and_removes_staging(tmp_path: Path) -> None:
    plan = _plan()
    output = tmp_path / "evaluation"
    original = _artifacts(plan)
    commit_output(output, plan, original)
    replacement = dict.fromkeys(plan.intended_relative_paths, b"replacement")
    calls = 0

    def fail_publish(source: str | Path, destination: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected publish failure")
        os.replace(source, destination)

    with pytest.raises(OutputCommitError, match="restored"):
        commit_output(output, plan, replacement, overwrite=True, replace=fail_publish)
    assert all((output / path).read_bytes() == original[path] for path in plan.intended_relative_paths)
    assert set(tmp_path.iterdir()) == {output}
