"""Phase-boundary regressions for Phase 16 concept evaluation."""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

PHASE16_SOURCES = (
    *Path("src/pada3dacb/evaluation/concepts").glob("*.py"),
    Path("scripts/evaluate_concepts.py"),
)
FORBIDDEN_IMPORT_PREFIXES = (
    "pada3dacb.training",
    "pada3dacb.experiments",
)


def test_phase16_never_imports_training_or_experiment_runners() -> None:
    violations = []
    for path in PHASE16_SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    violations.append(f"{path}:{node.lineno}:{name}")
    assert violations == []


def test_phase16_contains_no_backward_or_optimizer_calls() -> None:
    violations = []
    for path in PHASE16_SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            attribute = function.attr if isinstance(function, ast.Attribute) else ""
            if attribute in {"backward", "step", "zero_grad"}:
                violations.append(f"{path}:{node.lineno}:{attribute}")
    assert violations == []


def test_real_evaluation_gate_remains_closed() -> None:
    config = yaml.safe_load(Path("configs/evaluation/concepts.yaml").read_text(encoding="utf-8"))

    assert config["analysis_mode"] == "real"
    assert config["real_evaluation_gate"]["authorized"] is False
    assert all(
        evidence == {"resolved": False, "sha256": None}
        for name, evidence in config["real_evaluation_gate"].items()
        if name != "authorized"
    )
