"""Static scientific and phase boundaries for Phase 16."""

from __future__ import annotations

import ast
from pathlib import Path

PHASE16_ROOT = Path("src/pada3dacb/evaluation/concepts")


def test_phase16_has_no_training_or_experiment_dependencies() -> None:
    forbidden = ("pada3dacb.training", "pada3dacb.experiments")
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


def test_phase17_has_not_started() -> None:
    assert not any(Path("specs").glob("phase_17*"))
    assert not any(Path("src/pada3dacb").rglob("*phase17*"))
