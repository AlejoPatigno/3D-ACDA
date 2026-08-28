"""Static scientific and phase boundaries for Phase 16."""

from __future__ import annotations

import ast
from pathlib import Path

PHASE16_ROOT = Path("src/acda3d/evaluation/concepts")


def test_phase16_has_no_training_or_experiment_dependencies() -> None:
    forbidden = ("acda3d.training", "acda3d.experiments")
    violations = []
    for path in PHASE16_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            violations.extend(
                f"{path}:{node.lineno}:{module}"
                for module in modules
                if module.startswith(forbidden)
            )
    assert violations == []


def test_inference_loads_precomputed_targets_without_regeneration() -> None:
    source = (PHASE16_ROOT / "inference.py").read_text(encoding="utf-8")

    assert "@torch.no_grad()" in source
    assert "build_subject_concept_target" not in source
    assert 'batch["concept_targets"]' in source
    assert 'batch["anatomical_targets"]' in source
    assert "backward(" not in source
    assert "optimizer" not in source


def test_phase16_concept_modules_remain_independent_of_phase17() -> None:
    assert Path("specs/phase_17_ablations").is_dir()
    source = "\n".join(path.read_text(encoding="utf-8") for path in PHASE16_ROOT.glob("*.py"))
    forbidden = ("acda3d.ablations", "target_adaptation", "phase_17")
    assert [token for token in forbidden if token in source.lower()] == []


def test_concept_evaluator_has_no_forbidden_adaptation_or_causal_paths() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in PHASE16_ROOT.glob("*.py"))
    forbidden = (
        "target_adaptation",
        "jacobian",
        "causal importance",
        "biomarker",
        "disease mechanism",
        "phase_17",
    )
    assert [token for token in forbidden if token in source.lower()] == []
