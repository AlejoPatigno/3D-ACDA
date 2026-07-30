from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pada3dacb.evaluation.report import (
    build_completion_manifest,
    build_output_plan,
    commit_output,
    extract_computational_values,
)
from pada3dacb.evaluation.schemas import (
    AnalysisMode,
    CheckpointPolicy,
    Direction,
    MethodId,
    OutputCommitError,
    ValueStatus,
)

IDENTITY = {"configuration_sha256": "b" * 64, "authorization_sha256": "c" * 64}
LIBRARIES = {"numpy": "test", "scipy": "test"}


def _plan():
    return build_output_plan(
        "a" * 64, AnalysisMode.SYNTHETIC_TEST_ONLY, (MethodId.MMD,),
        (Direction.ADNI_TO_OASIS,), (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        included_methods=(MethodId.MMD,),
    )


def _artifacts(plan) -> dict[str, bytes]:
    artifacts = {
        path: f"synthetic:{path}\n".encode()
        for path in plan.intended_relative_paths if path != "evaluation_manifest.json"
    }
    artifacts["evaluation_manifest.json"] = build_completion_manifest(
        plan, artifacts, identity_inputs=IDENTITY, library_versions=LIBRARIES
    )
    return artifacts


def test_completed_tree_is_exact_manifest_last_and_input_immutable(tmp_path: Path) -> None:
    source = tmp_path / "runs/input.csv"
    source.parent.mkdir()
    source.write_bytes(b"immutable-input")
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    plan = _plan()
    output = tmp_path / "results"
    commit_output(output, plan, _artifacts(plan))
    files = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
    assert files == set(plan.intended_relative_paths)
    assert plan.intended_relative_paths[-1] == "evaluation_manifest.json"
    confusion = "predictive/adni_to_oasis/primary_best_source_f1/confusion_matrices/mmd"
    assert {path.name for path in (output / confusion).iterdir()} == {
        "confusion_matrix_counts.csv", "confusion_matrix_normalized.csv",
        "confusion_matrix_counts.png", "confusion_matrix_normalized.png",
    }
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_failed_commit_leaves_no_completed_output_or_input_mutation(tmp_path: Path) -> None:
    source = tmp_path / "runs/input.csv"
    source.parent.mkdir()
    source.write_bytes(b"immutable-input")
    before = source.read_bytes()
    calls = 0

    def fail_writer(path: Path, payload: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("injected")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    with pytest.raises(OutputCommitError):
        commit_output(tmp_path / "results", _plan(), _artifacts(_plan()), writer=fail_writer)
    assert not (tmp_path / "results/evaluation_manifest.json").exists()
    assert source.read_bytes() == before


def test_missing_computational_values_are_explicit_nulls_not_zero() -> None:
    values = extract_computational_values(())
    assert len(values) == 7
    assert all(item.value is None and item.status is ValueStatus.NOT_RECORDED for item in values)
    assert all(item.reason == "not_recorded" for item in values)


def test_phase15_boundaries_exclude_training_concepts_manuscript_and_phase16() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/pada3dacb/evaluation").glob("*.py")
    ) + Path("scripts/evaluate.py").read_text(encoding="utf-8")
    assert "pada3dacb.training" not in sources
    assert "pada3dacb.experiments" not in sources
    assert "ContextualROIEncoder" not in sources
    assert "manuscript" not in sources.lower()
    assert "phase 16" not in sources.lower()
