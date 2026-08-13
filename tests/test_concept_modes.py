"""Synthetic mode-boundary tests for Phase 16."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
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
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir()
    (fixture_root / "fixture.bin").write_bytes(b"phase16-fixture")
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


def test_synthetic_execution_requires_fixture_manifest(tmp_path) -> None:
    config = _fixture_config(tmp_path)
    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    config_data.pop("fixture_manifest_path")
    config.write_text(yaml.safe_dump(config_data, sort_keys=True), encoding="utf-8")

    assert main([*_base_args(tmp_path, config), "--validate-only"]) == ExitCode.CONFIGURATION_ERROR


def test_synthetic_fixture_metrics_are_deterministic() -> None:
    first = _synthetic_fixture_metrics()
    second = _synthetic_fixture_metrics()

    assert first == second
    assert first["fixture_only"] is True
    assert first["subject_count"] == 6
    assert first["concept_mae"] >= 0.0
    assert 0.0 <= first["top1_agreement_rate"] <= 1.0


def test_synthetic_fixture_identity_is_bound_to_metrics_and_output(tmp_path) -> None:
    config = _fixture_config(tmp_path)
    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    verified = concept_cli._load_verified_fixture_manifest(config_data, config)
    first_metrics = _synthetic_fixture_metrics(verified.fixture_payload_sha256)
    assert first_metrics["fixture_payload_sha256"] == verified.fixture_payload_sha256

    output = tmp_path / "results"
    assert main([
        *_base_args(tmp_path, config),
        "--output-root", str(output),
        "--bootstrap-seed", "7",
    ]) == ExitCode.SUCCESS
    output_manifest = json.loads(
        (output / "evaluation_manifest.json").read_text(encoding="utf-8")
    )
    assert output_manifest["identity_inputs"]["fixture_payload_sha256"] == verified.fixture_payload_sha256
    assert output_manifest["identity_inputs"]["fixture_files"] == [
        {
            "relative_path": "fixture.bin",
            "sha256": verified.files[0].sha256,
            "size_bytes": verified.files[0].size_bytes,
        }
    ]


def test_synthetic_fixture_identity_changes_when_verified_file_changes(tmp_path) -> None:
    config = _fixture_config(tmp_path)
    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    fixture_root = Path(config_data["fixture_allowed_root"])
    fixture_path = fixture_root / "fixture.bin"
    fixture_path.write_bytes(b"changed-phase16-fixture")
    manifest_path = Path(config_data["fixture_manifest_path"])
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["files"][0]["sha256"] = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    manifest_bytes = json.dumps(manifest_data, sort_keys=True, separators=(",", ":")).encode()
    manifest_path.write_bytes(manifest_bytes)
    config_data["fixture_manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    config.write_text(yaml.safe_dump(config_data, sort_keys=True), encoding="utf-8")

    verified = concept_cli._load_verified_fixture_manifest(config_data, config)
    assert verified.fixture_payload_sha256 != _synthetic_fixture_metrics()["fixture_payload_sha256"]
    assert _synthetic_fixture_metrics(verified.fixture_payload_sha256)["fixture_payload_sha256"] == (
        verified.fixture_payload_sha256
    )


def test_synthetic_fixture_tampering_rejects_execution_before_output(tmp_path) -> None:
    config = _fixture_config(tmp_path)
    fixture_root = yaml.safe_load(config.read_text(encoding="utf-8"))["fixture_allowed_root"]
    (Path(fixture_root) / "fixture.bin").write_bytes(b"tampered-phase16-fixture")

    output = tmp_path / "results"
    assert main([
        *_base_args(tmp_path, config),
        "--output-root", str(output),
        "--bootstrap-seed", "7",
    ]) == ExitCode.CONFIGURATION_ERROR
    assert not output.exists()


def test_synthetic_reuse_rejects_output_bound_to_stale_fixture_identity(tmp_path) -> None:
    config = _fixture_config(tmp_path)
    output = tmp_path / "results"
    assert main([
        *_base_args(tmp_path, config),
        "--output-root", str(output),
        "--bootstrap-seed", "7",
    ]) == ExitCode.SUCCESS

    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    fixture_root = Path(config_data["fixture_allowed_root"])
    fixture_path = fixture_root / "fixture.bin"
    fixture_path.write_bytes(b"changed-after-evaluation")
    manifest_path = Path(config_data["fixture_manifest_path"])
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["files"][0]["sha256"] = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    manifest_bytes = json.dumps(manifest_data, sort_keys=True, separators=(",", ":")).encode()
    manifest_path.write_bytes(manifest_bytes)
    config_data["fixture_manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    config_data["completed_reuse"] = {"approved_output_roots": [str(output)]}
    config.write_text(yaml.safe_dump(config_data, sort_keys=True), encoding="utf-8")

    assert main([
        "--config", str(config),
        "--output-root", str(output),
        "--direction", "adni_to_oasis",
        "--method", "source_only",
        "--reuse",
    ]) == ExitCode.REUSE_REJECTED


def test_validate_only_fixture_payload_identity_includes_manifest_bytes(tmp_path) -> None:
    config = _fixture_config(tmp_path)
    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    before = concept_cli._load_verified_fixture_manifest(config_data, config)

    manifest_path = Path(config_data["fixture_manifest_path"])
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_bytes = json.dumps(manifest_payload, indent=2).encode()
    manifest_path.write_bytes(manifest_bytes)
    config_data["fixture_manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    config.write_text(yaml.safe_dump(config_data, sort_keys=True), encoding="utf-8")

    after = concept_cli._load_verified_fixture_manifest(config_data, config)
    assert after.manifest_sha256 != before.manifest_sha256
    assert after.fixture_payload_sha256 != before.fixture_payload_sha256
    assert main([*_base_args(tmp_path, config), "--validate-only"]) == ExitCode.SUCCESS


def test_dry_run_never_executes_fixture_metrics(tmp_path, monkeypatch) -> None:
    config = _fixture_config(tmp_path)
    args = _base_args(tmp_path, config)

    def forbidden() -> dict:
        raise AssertionError("dry-run executed synthetic metrics")

    monkeypatch.setattr(concept_cli, "_synthetic_fixture_metrics", forbidden)

    assert main([*args, "--dry-run"]) == ExitCode.SUCCESS
    assert not (tmp_path / "results").exists()


def test_validate_only_skips_statistics_and_writes_nothing(tmp_path, monkeypatch) -> None:
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
    assert calls == 0
    assert not (tmp_path / "results").exists()


def test_validate_only_runs_synthetic_model_contract(tmp_path, monkeypatch) -> None:
    config = _fixture_config(tmp_path)
    args = _base_args(tmp_path, config)
    calls = 0
    payloads = []
    original = concept_cli._validate_synthetic_fixture

    def counted(*fixture_args, **fixture_kwargs):
        nonlocal calls
        calls += 1
        result = original(*fixture_args, **fixture_kwargs)
        payloads.append(result)
        return result

    monkeypatch.setattr(concept_cli, "_validate_synthetic_fixture", counted)
    monkeypatch.setattr(
        concept_cli,
        "_synthetic_fixture_metrics",
        lambda: (_ for _ in ()).throw(AssertionError("validate-only computed statistics")),
    )

    assert main([*args, "--validate-only"]) == ExitCode.SUCCESS
    assert calls == 1
    verified = concept_cli._load_verified_fixture_manifest(
        yaml.safe_load(config.read_text(encoding="utf-8")), config
    )
    assert payloads == [verified.fixture_payload_sha256]
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
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_data["identity_inputs"]["fixture_manifest_sha256"] == yaml.safe_load(
        config.read_text(encoding="utf-8")
    )["fixture_manifest_sha256"]

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
            "--bootstrap-replicates", "100",
            "--bootstrap-seed", "7",
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
            "--bootstrap-replicates", "100",
            "--bootstrap-seed", "7",
            "--reuse",
        ]
    ) == ExitCode.REUSE_REJECTED


@pytest.mark.parametrize(
    ("identity_field", "replacement"),
    (
        ("analysis_mode", "real"),
        ("configuration_sha256", "0" * 64),
        ("authorization_sha256", "0" * 64),
        ("device", "cuda"),
        ("evaluation_identity", "0" * 64),
    ),
)
def test_synthetic_reuse_rejects_each_identity_dimension_mismatch(
    tmp_path, identity_field, replacement
) -> None:
    config = _fixture_config(tmp_path)
    output = tmp_path / "results"
    assert main([
        *_base_args(tmp_path, config),
        "--output-root", str(output),
        "--bootstrap-replicates", "100",
        "--bootstrap-seed", "7",
    ]) == ExitCode.SUCCESS

    manifest_path = output / "evaluation_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if identity_field == "evaluation_identity":
        manifest[identity_field] = replacement
    else:
        manifest["identity_inputs"][identity_field] = replacement
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    config_data["completed_reuse"] = {"approved_output_roots": [str(output)]}
    config.write_text(yaml.safe_dump(config_data, sort_keys=True), encoding="utf-8")

    assert main([
        "--config", str(config),
        "--output-root", str(output),
        "--direction", "adni_to_oasis",
        "--method", "source_only",
        "--bootstrap-replicates", "100",
        "--bootstrap-seed", "7",
        "--reuse",
    ]) == ExitCode.REUSE_REJECTED


def test_reuse_failure_reports_actionable_stderr(tmp_path, capsys) -> None:
    config = _fixture_config(tmp_path)
    output = tmp_path / "results"
    assert main([
        *_base_args(tmp_path, config),
        "--output-root", str(output),
        "--bootstrap-seed", "7",
    ]) == ExitCode.SUCCESS

    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    config_data["completed_reuse"] = {"approved_output_roots": [str(output)]}
    config.write_text(yaml.safe_dump(config_data, sort_keys=True), encoding="utf-8")
    manifest = json.loads((output / "evaluation_manifest.json").read_text(encoding="utf-8"))
    manifest["identity_inputs"]["device"] = "cuda"
    (output / "evaluation_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    assert main([
        "--config", str(config),
        "--output-root", str(output),
        "--direction", "adni_to_oasis",
        "--method", "source_only",
        "--bootstrap-seed", "7",
        "--reuse",
    ]) == ExitCode.REUSE_REJECTED
    stderr = capsys.readouterr().err
    assert "reuse verification failed" in stderr
    assert "device" in stderr


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


def test_synthetic_cli_reports_one_truthful_status_for_selected_baseline(tmp_path) -> None:
    config = _fixture_config(tmp_path)
    args = _base_args(tmp_path, config)
    output = tmp_path / "results"

    assert main([
        *args[:8],
        "--method", "aagn",
        "--output-root", str(output),
        "--bootstrap-seed", "7",
    ]) == ExitCode.SUCCESS

    with (output / "method_status.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    aagn_rows = [row for row in rows if row["method"] == "aagn"]
    assert len(aagn_rows) == 1
    assert aagn_rows[0]["status"] == "not_applicable_no_pada3dacb_concept_head"
    assert all(row["status"] != "included" for row in aagn_rows)


def test_real_dry_run_reports_not_applicable_without_failure(tmp_path, capsys) -> None:
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
            "--method", "aagn",
            "--dry-run",
        ]
    )

    assert code == ExitCode.SUCCESS
    assert "aagn: not_applicable_no_pada3dacb_concept_head" in capsys.readouterr().out


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


def test_authorized_real_mode_never_falls_back_to_synthetic(tmp_path, monkeypatch) -> None:
    config = _fixture_config(tmp_path)
    config_data = yaml.safe_load(config.read_text(encoding="utf-8"))
    config_data["analysis_mode"] = "real"
    config_data["manifest_path"] = str(tmp_path / "manifest.json")
    gate = config_data["real_evaluation_gate"]
    gate["authorized"] = True
    for evidence in ("authorized_exports", "concept_normalizer", "atlas_hash", "protocol_approval"):
        gate[evidence] = {"resolved": True, "sha256": "a" * 64}
    config.write_text(yaml.safe_dump(config_data), encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    args = _base_args(tmp_path, config)
    issued = object()
    called = {}

    monkeypatch.setattr(concept_cli, "_issue_cli_capability", lambda *args: issued)
    monkeypatch.setattr(
        concept_cli,
        "_synthetic_fixture_metrics",
        lambda: (_ for _ in ()).throw(AssertionError("real mode used synthetic metrics")),
    )

    def closed_real_orchestration(**kwargs):
        called.update(kwargs)
        raise concept_cli.ConfigurationError("real evaluation is closed")

    monkeypatch.setattr(concept_cli, "run_real_evaluation", closed_real_orchestration)

    assert main([*args, "--validate-only"]) == ExitCode.CONFIGURATION_ERROR
    assert called["capability"] is issued


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
