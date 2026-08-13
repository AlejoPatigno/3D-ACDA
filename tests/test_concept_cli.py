"""CLI contract tests for Phase 16 concept evaluation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import scripts.evaluate_concepts as concept_cli
from pada3dacb.evaluation.schemas import (
    CheckpointPolicy,
    ConfigurationError,
    Direction,
    MethodId,
    RunMode,
    SelectorConflictError,
    UnsafePathError,
)
from scripts.evaluate_concepts import ExitCode, main, parse_cli

BASE = [
    "--config", "configs/evaluation/concepts.yaml",
    "--runs-root", "runs",
    "--artifact-root", "artifacts",
    "--direction", "adni_to_oasis",
]


@pytest.mark.parametrize(
    "error",
    (
        ConfigurationError("configuration field is invalid"),
        SelectorConflictError("selector conflict: method"),
        UnsafePathError("unsafe output path"),
    ),
)
def test_main_reports_configuration_failures_to_stderr(error, capsys) -> None:
    def fail(_selection):
        raise error

    code = main([*BASE, "--method", "source_only", "--dry-run"], executor=fail)

    assert code == ExitCode.CONFIGURATION_ERROR
    assert "configuration error" in capsys.readouterr().err


def test_parse_cli_exposes_deterministic_synthetic_controls() -> None:
    selection = parse_cli(
        [
            *BASE,
            "--method", "source_only",
            "--dry-run",
            "--top-k", "2",
            "--top-k", "5",
            "--device", "cpu",
        ]
    )

    assert selection.run_mode is RunMode.DRY_RUN
    assert selection.methods == (MethodId.SOURCE_ONLY,)
    assert selection.top_k == (2, 5)
    assert selection.device == "cpu"


def test_all_pada_methods_excludes_non_concept_baselines() -> None:
    selection = parse_cli([*BASE, "--all-pada-methods", "--dry-run"])

    assert selection.methods == (
        MethodId.SOURCE_ONLY,
        MethodId.CORAL,
        MethodId.MMD,
        MethodId.CDAN,
        MethodId.PROTOTYPE_PSEUDO,
    )
    assert MethodId.AAGN not in selection.methods
    assert MethodId.FASTER_SNN not in selection.methods


def test_cli_rejects_duplicate_methods_and_top_k() -> None:
    duplicate_method = main(
        [*BASE, "--method", "source_only", "--method", "source_only", "--dry-run"]
    )
    duplicate_top_k = main(
        [
            *BASE,
            "--method", "source_only",
            "--dry-run",
            "--top-k", "2",
            "--top-k", "2",
        ]
    )

    assert duplicate_method == ExitCode.CONFIGURATION_ERROR
    assert duplicate_top_k == ExitCode.CONFIGURATION_ERROR


def test_parse_cli_accepts_all_evaluation_controls_and_case_insensitive_direction(tmp_path) -> None:
    selection = parse_cli(
        [
            "--config", "configs/evaluation/concepts.yaml",
            "--runs-root", str(tmp_path / "runs"),
            "--artifact-root", str(tmp_path / "artifacts"),
            "--output-root", str(tmp_path / "results"),
            "--both-directions",
            "--all-pada-methods",
            "--checkpoint-policy", "best_source_f1",
            "--include-sensitivity",
            "--bootstrap-replicates", "25",
            "--bootstrap-seed", "7",
            "--top-k", "2",
            "--top-k", "5",
            "--device", "cpu",
            "--overwrite",
        ]
    )

    assert selection.directions == (Direction.ADNI_TO_OASIS, Direction.OASIS_TO_ADNI)
    assert selection.checkpoint_policies == (
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        CheckpointPolicy.SENSITIVITY_LAST,
    )
    assert selection.bootstrap_replicates == 25
    assert selection.bootstrap_seed == 7
    assert selection.overwrite is True

    uppercase = parse_cli(
        [
            *BASE,
            "--direction", "ADNI_to_OASIS",
            "--method", "source_only",
            "--dry-run",
        ]
    )
    assert uppercase.directions == (Direction.ADNI_TO_OASIS,)


def test_cli_rejects_sensitivity_conflict_and_missing_artifact_root() -> None:
    sensitivity_conflict = main(
        [
            *BASE,
            "--method", "source_only",
            "--checkpoint-policy", "last",
            "--include-sensitivity",
            "--dry-run",
        ]
    )
    missing_artifacts = main(
        [
            "--config", "configs/evaluation/concepts.yaml",
            "--runs-root", "runs",
            "--direction", "adni_to_oasis",
            "--method", "source_only",
            "--dry-run",
        ]
    )

    assert sensitivity_conflict == ExitCode.CONFIGURATION_ERROR
    assert missing_artifacts == ExitCode.CONFIGURATION_ERROR


def test_authorized_real_cli_without_manifest_or_callback_stays_closed(tmp_path: Path) -> None:
    config = yaml.safe_load(Path("configs/evaluation/concepts.yaml").read_text(encoding="utf-8"))
    gate = config["real_evaluation_gate"]
    gate["authorized"] = True
    for evidence in ("authorized_exports", "concept_normalizer", "atlas_hash", "protocol_approval"):
        gate[evidence] = {"resolved": True, "sha256": "a" * 64}
    config["manifest_path"] = str(tmp_path / "manifest.json")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    config_path = tmp_path / "authorized.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    (tmp_path / "runs").mkdir()
    (tmp_path / "artifacts").mkdir()

    code = main([
        "--config", str(config_path),
        "--runs-root", str(tmp_path / "runs"),
        "--artifact-root", str(tmp_path / "artifacts"),
        "--direction", "adni_to_oasis",
        "--method", "source_only",
        "--validate-only",
    ])

    assert code == ExitCode.CONFIGURATION_ERROR


def test_authorized_real_cli_passes_capability_to_orchestration_seam(tmp_path: Path, monkeypatch) -> None:
    config = yaml.safe_load(Path("configs/evaluation/concepts.yaml").read_text(encoding="utf-8"))
    gate = config["real_evaluation_gate"]
    gate["authorized"] = True
    for evidence in ("authorized_exports", "concept_normalizer", "atlas_hash", "protocol_approval"):
        gate[evidence] = {"resolved": True, "sha256": "a" * 64}
    config["manifest_path"] = str(tmp_path / "manifest.json")
    config_path = tmp_path / "authorized.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "runs").mkdir()
    (tmp_path / "artifacts").mkdir()
    issued = object()
    seen = {}

    monkeypatch.setattr(concept_cli, "_issue_cli_capability", lambda *args: issued)

    def fake_real_orchestration(**kwargs):
        seen.update(kwargs)
        raise concept_cli.ConfigurationError("real evaluation is closed")

    monkeypatch.setattr(concept_cli, "run_real_evaluation", fake_real_orchestration, raising=False)

    code = concept_cli.main([
        "--config", str(config_path),
        "--runs-root", str(tmp_path / "runs"),
        "--artifact-root", str(tmp_path / "artifacts"),
        "--direction", "adni_to_oasis",
        "--method", "source_only",
        "--validate-only",
    ])

    assert code == ExitCode.CONFIGURATION_ERROR
    assert seen["capability"] is issued
