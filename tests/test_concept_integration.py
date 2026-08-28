"""Synthetic matrix integration test for Phase 16."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from acda3d.evaluation.concepts.report import build_concept_output_plan
from scripts.evaluate_concepts import ExitCode, main
from tests.phase16_integration_fixtures import fixture_matrix


def _write_fixture_config(config: dict, tmp_path: Path) -> Path:
    """Write a synthetic config carrying a verified fixture manifest."""
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir()
    (fixture_root / "fixture.bin").write_bytes(b"phase16-integration-fixture")
    fixture_payload = {
        "schema_version": "phase16-concept-fixture-manifest-v1",
        "fixture_marker": "phase16-synthetic-fixture",
        "fixture_only": True,
        "files": [{
            "relative_path": "fixture.bin",
            "sha256": hashlib.sha256((fixture_root / "fixture.bin").read_bytes()).hexdigest(),
        }],
    }
    manifest_path = fixture_root / "manifest.json"
    manifest_bytes = json.dumps(
        fixture_payload, sort_keys=True, separators=(",", ":")
    ).encode()
    manifest_path.write_bytes(manifest_bytes)
    config["fixture_manifest_path"] = str(manifest_path)
    config["fixture_manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    config["fixture_allowed_root"] = str(fixture_root)
    config_path = tmp_path / "synthetic.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=True), encoding="utf-8")
    return config_path


def test_complete_synthetic_method_direction_policy_matrix(tmp_path) -> None:
    config = yaml.safe_load(Path("configs/evaluation/concepts.yaml").read_text(encoding="utf-8"))
    config["analysis_mode"] = "synthetic_test_only"
    matrix = fixture_matrix(config)
    config["top_k"] = [1, 2]
    config_path = _write_fixture_config(config, tmp_path)
    runs = tmp_path / "runs"
    artifacts = tmp_path / "artifacts"
    output = tmp_path / "results"
    runs.mkdir()
    artifacts.mkdir()

    code = main(
        [
            "--config", str(config_path),
            "--runs-root", str(runs),
            "--artifact-root", str(artifacts),
            "--output-root", str(output),
            "--both-directions",
            "--all-acda-methods",
            "--include-sensitivity",
            "--bootstrap-replicates", "100",
            "--bootstrap-seed", "17",
        ]
    )

    assert code == ExitCode.SUCCESS
    manifest = json.loads((output / "evaluation_manifest.json").read_text(encoding="utf-8"))
    assert manifest["methods"] == [method.value for method in matrix.methods]
    assert manifest["directions"] == [direction.value for direction in matrix.directions]
    assert manifest["checkpoint_policies"] == [policy.logical_checkpoint for policy in matrix.policies]
    plan = build_concept_output_plan(
        manifest["evaluation_identity"],
        "synthetic_test_only",
        matrix.methods,
        matrix.directions,
        matrix.policies,
        matrix.methods,
    )
    actual_paths = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file()
    }
    assert actual_paths == set(plan.intended_relative_paths)
    assert manifest["analysis_mode"] == "synthetic_test_only"

    with (output / "method_status.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    included = [row for row in rows if row["status"] == "included"]
    not_applicable = [
        row for row in rows
        if row["status"] == "not_applicable_no_acda3d_concept_head"
    ]
    assert len(included) == len(matrix.methods) * len(matrix.directions) * len(matrix.policies)
    assert len(not_applicable) == len(matrix.not_applicable) * len(matrix.directions) * len(matrix.policies)
    assert {row["method"] for row in not_applicable} == {method.value for method in matrix.not_applicable}
    assert {row["status"] for row in not_applicable} == {"not_applicable_no_acda3d_concept_head"}


def test_synthetic_reuse_rejects_mismatched_method_and_direction_selection(tmp_path) -> None:
    config = yaml.safe_load(Path("configs/evaluation/concepts.yaml").read_text(encoding="utf-8"))
    config["analysis_mode"] = "synthetic_test_only"
    config["expected_folds"] = [0]
    config["expected_seeds"] = [42]
    config["top_k"] = [1, 2]
    config_path = _write_fixture_config(config, tmp_path)
    runs = tmp_path / "runs"
    artifacts = tmp_path / "artifacts"
    output = tmp_path / "results"
    runs.mkdir()
    artifacts.mkdir()

    base = [
        "--config", str(config_path),
        "--runs-root", str(runs),
        "--artifact-root", str(artifacts),
    ]
    source_only_args = [
        *base,
        "--direction", "adni_to_oasis",
        "--method", "source_only",
        "--output-root", str(output),
        "--bootstrap-seed", "7",
    ]
    assert main(source_only_args) == ExitCode.SUCCESS
    stored_manifest = json.loads(
        (output / "evaluation_manifest.json").read_text(encoding="utf-8")
    )
    assert stored_manifest["methods"] == ["source_only"]
    assert stored_manifest["directions"] == ["adni_to_oasis"]

    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config_data["completed_reuse"] = {"approved_output_roots": [str(output)]}
    config_path.write_text(yaml.safe_dump(config_data, sort_keys=True), encoding="utf-8")

    reuse_args = [
        "--config", str(config_path),
        "--output-root", str(output),
        "--reuse",
        "--bootstrap-seed", "7",
    ]
    assert main(
        [
            *reuse_args,
            "--direction", "adni_to_oasis",
            "--method", "source_only",
        ]
    ) == ExitCode.SUCCESS

    assert main(
        [
            *reuse_args,
            "--direction", "adni_to_oasis",
            "--all-acda-methods",
        ]
    ) == ExitCode.REUSE_REJECTED

    assert main(
        [
            *reuse_args,
            "--direction", "oasis_to_adni",
            "--method", "source_only",
        ]
    ) == ExitCode.REUSE_REJECTED


def test_fixture_matrix_rejects_missing_fold_coverage() -> None:
    config = yaml.safe_load(Path("configs/evaluation/concepts.yaml").read_text(encoding="utf-8"))
    config["expected_folds"] = [0, 1]
    with pytest.raises(AssertionError):
        fixture_matrix(config)
