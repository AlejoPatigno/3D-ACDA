"""Atomic report tests for Phase 16 concept evaluation."""

from __future__ import annotations

import json

import pytest

from pada3dacb.evaluation.concepts.report import (
    ConceptEvaluationPlan,
    build_artifact_index,
    build_concept_output_plan,
    build_synthetic_fixture_bundle,
    commit_output,
    verify_completed_output,
)
from pada3dacb.evaluation.schemas import CheckpointPolicy, Direction, MethodId


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
    assert first.intended_relative_paths[-1] != "evaluation_manifest.json"  # sorted plan
    assert "evaluation_manifest.json" in first.intended_relative_paths
    assert "artifact_index.json" in first.intended_relative_paths


def test_artifact_index_is_self_excluding_and_sorted() -> None:
    payload = build_artifact_index({"z.csv": b"z\n", "a.csv": b"a\n"})
    decoded = json.loads(payload)

    assert list(decoded["artifacts"]) == ["a.csv", "z.csv"]
    with pytest.raises(ValueError, match="exclude itself"):
        build_artifact_index({"artifact_index.json": b"invalid"})


def test_commit_output_requires_exact_allowlisted_tree(tmp_path) -> None:
    plan = ConceptEvaluationPlan(
        evaluation_identity="fixture",
        analysis_mode="synthetic_test_only",
        methods=(MethodId.SOURCE_ONLY,),
        directions=(Direction.ADNI_TO_OASIS,),
        checkpoint_policies=(CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        intended_relative_paths=("data.csv", "evaluation_manifest.json"),
    )

    output = commit_output(
        tmp_path / "results",
        plan,
        {"data.csv": b"value\n", "evaluation_manifest.json": b"{}\n"},
    )

    assert (output / "data.csv").read_bytes() == b"value\n"
    with pytest.raises(ValueError, match="exactly match"):
        commit_output(tmp_path / "bad", plan, {"data.csv": b"value\n"})


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
