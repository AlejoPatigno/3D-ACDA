"""Synthetic mode-boundary tests for Phase 16."""

from __future__ import annotations

from pathlib import Path

import yaml

import scripts.evaluate_concepts as concept_cli
from scripts.evaluate_concepts import (
    ExitCode,
    _synthetic_fixture_metrics,
    _unresolved_real_gates,
    main,
)


def _fixture_config(tmp_path: Path) -> Path:
    config = yaml.safe_load(Path("configs/evaluation/concepts.yaml").read_text(encoding="utf-8"))
    config["analysis_mode"] = "synthetic_test_only"
    config["expected_folds"] = [0, 1]
    config["expected_seeds"] = [42]
    config["top_k"] = [1, 2]
    path = tmp_path / "synthetic.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=True), encoding="utf-8")
    return path


def _base_args(tmp_path: Path, config: Path) -> list[str]:
    runs = tmp_path / "runs"
    artifacts = tmp_path / "artifacts"
    runs.mkdir()
    artifacts.mkdir()
    return [
        "--config", str(config),
        "--runs-root", str(runs),
        "--artifact-root", str(artifacts),
        "--direction", "adni_to_oasis",
        "--method", "source_only",
    ]


def test_synthetic_fixture_metrics_are_deterministic() -> None:
    first = _synthetic_fixture_metrics()
    second = _synthetic_fixture_metrics()

    assert first == second
    assert first["fixture_only"] is True
    assert first["subject_count"] == 6
    assert first["concept_mae"] >= 0.0
    assert 0.0 <= first["top1_agreement_rate"] <= 1.0


def test_dry_run_never_executes_fixture_metrics(tmp_path, monkeypatch) -> None:
    config = _fixture_config(tmp_path)
    args = _base_args(tmp_path, config)

    def forbidden() -> dict:
        raise AssertionError("dry-run executed synthetic metrics")

    monkeypatch.setattr(concept_cli, "_synthetic_fixture_metrics", forbidden)

    assert main([*args, "--dry-run"]) == ExitCode.SUCCESS
    assert not (tmp_path / "results").exists()


def test_validate_only_executes_fixture_without_writing(tmp_path, monkeypatch) -> None:
    config = _fixture_config(tmp_path)
    args = _base_args(tmp_path, config)
    calls = 0
    original = concept_cli._synthetic_fixture_metrics

    def counted() -> dict:
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(concept_cli, "_synthetic_fixture_metrics", counted)

    assert main([*args, "--validate-only"]) == ExitCode.SUCCESS
    assert calls == 1
    assert not (tmp_path / "results").exists()


def test_synthetic_evaluate_and_read_only_reuse(tmp_path) -> None:
    config = _fixture_config(tmp_path)
    args = _base_args(tmp_path, config)
    output = tmp_path / "results"

    evaluate_code = main(
        [
            *args,
            "--output-root", str(output),
            "--bootstrap-replicates", "100",
            "--bootstrap-seed", "7",
        ]
    )
    assert evaluate_code == ExitCode.SUCCESS
    manifest = output / "evaluation_manifest.json"
    assert manifest.is_file()

    second_output = tmp_path / "results-repeat"
    assert main(
        [
            *args,
            "--output-root", str(second_output),
            "--bootstrap-replicates", "100",
            "--bootstrap-seed", "7",
        ]
    ) == ExitCode.SUCCESS
    first_bytes = {
        path.relative_to(output): path.read_bytes()
        for path in output.rglob("*") if path.is_file()
    }
    second_bytes = {
        path.relative_to(second_output): path.read_bytes()
        for path in second_output.rglob("*") if path.is_file()
    }
    assert second_bytes == first_bytes

    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    config_data["completed_reuse"]["approved_output_roots"] = [str(output)]
    config.write_text(yaml.safe_dump(config_data, sort_keys=True), encoding="utf-8")
    before = {path: path.stat().st_mtime_ns for path in output.rglob("*") if path.is_file()}

    reuse_code = main(
        [
            "--config", str(config),
            "--output-root", str(output),
            "--direction", "adni_to_oasis",
            "--method", "source_only",
            "--reuse",
        ]
    )
    after = {path: path.stat().st_mtime_ns for path in output.rglob("*") if path.is_file()}

    assert reuse_code == ExitCode.SUCCESS
    assert after == before

    (output / "synthetic_metrics.json").write_text("{}\n", encoding="utf-8")
    assert main(
        [
            "--config", str(config),
            "--output-root", str(output),
            "--direction", "adni_to_oasis",
            "--method", "source_only",
            "--reuse",
        ]
    ) == ExitCode.REUSE_REJECTED


def test_real_dry_run_discovers_and_rejects_missing_matrix(tmp_path) -> None:
    runs = tmp_path / "runs"
    artifacts = tmp_path / "artifacts"
    runs.mkdir()
    artifacts.mkdir()

    code = main(
        [
            "--config", "configs/evaluation/concepts.yaml",
            "--runs-root", str(runs),
            "--artifact-root", str(artifacts),
            "--direction", "adni_to_oasis",
            "--method", "source_only",
            "--dry-run",
        ]
    )

    assert code == ExitCode.CONFIGURATION_ERROR


def test_real_validate_only_is_gate_blocked(tmp_path) -> None:
    runs = tmp_path / "runs"
    artifacts = tmp_path / "artifacts"
    runs.mkdir()
    artifacts.mkdir()

    assert main(
        [
            "--config", "configs/evaluation/concepts.yaml",
            "--runs-root", str(runs),
            "--artifact-root", str(artifacts),
            "--direction", "adni_to_oasis",
            "--method", "source_only",
            "--validate-only",
        ]
    ) == ExitCode.GATE_BLOCKED


def test_default_real_evaluation_is_blocked_before_output(tmp_path) -> None:
    runs = tmp_path / "runs"
    artifacts = tmp_path / "artifacts"
    output = tmp_path / "results"
    runs.mkdir()
    artifacts.mkdir()

    code = main(
        [
            "--config", "configs/evaluation/concepts.yaml",
            "--runs-root", str(runs),
            "--artifact-root", str(artifacts),
            "--output-root", str(output),
            "--direction", "adni_to_oasis",
            "--method", "source_only",
            "--bootstrap-seed", "7",
        ]
    )

    assert code == ExitCode.GATE_BLOCKED
    assert not output.exists()


def test_real_gate_rejects_non_hex_evidence() -> None:
    gate = {
        "authorized": True,
        "authorized_exports": {"resolved": True, "sha256": "z" * 64},
        "concept_normalizer": {"resolved": True, "sha256": "z" * 64},
        "atlas_hash": {"resolved": True, "sha256": "z" * 64},
        "protocol_approval": {"resolved": True, "sha256": "z" * 64},
    }

    assert _unresolved_real_gates(gate) == (
        "authorized_exports",
        "concept_normalizer",
        "atlas_hash",
        "protocol_approval",
    )
