"""CLI contract tests for Phase 16 concept evaluation."""

from __future__ import annotations

from pada3dacb.evaluation.schemas import MethodId, RunMode
from scripts.evaluate_concepts import ExitCode, main, parse_cli

BASE = [
    "--config", "configs/evaluation/concepts.yaml",
    "--runs-root", "runs",
    "--artifact-root", "artifacts",
    "--direction", "adni_to_oasis",
]


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
