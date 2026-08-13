"""Deterministic Phase 16 synthetic evaluation matrix."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pada3dacb.evaluation.schemas import CheckpointPolicy, Direction, MethodId


@dataclass(frozen=True)
class FixtureMatrix:
    methods: tuple[MethodId, ...]
    directions: tuple[Direction, ...]
    policies: tuple[CheckpointPolicy, ...]
    folds: tuple[int, ...]
    seeds: tuple[int, ...]
    not_applicable: tuple[MethodId, ...]


def fixture_matrix(config: Mapping[str, Any]) -> FixtureMatrix:
    """Return the complete configured fixture matrix, failing on scope drift."""
    methods = (
        MethodId.SOURCE_ONLY,
        MethodId.CORAL,
        MethodId.MMD,
        MethodId.CDAN,
        MethodId.PROTOTYPE_PSEUDO,
    )
    directions = (Direction.ADNI_TO_OASIS, Direction.OASIS_TO_ADNI)
    policies = (
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
        CheckpointPolicy.SENSITIVITY_LAST,
    )
    folds = tuple(int(value) for value in config.get("expected_folds", ()))
    seeds = tuple(int(value) for value in config.get("expected_seeds", ()))
    assert folds == (0, 1, 2, 3, 4)
    assert seeds == (42,)
    assert tuple(config.get("methods", ())) == tuple(method.value for method in methods)
    assert tuple(config.get("baselines", ())) == tuple(method.value for method in (
        MethodId.AAGN,
        MethodId.FASTER_SNN,
    ))
    return FixtureMatrix(
        methods=methods,
        directions=directions,
        policies=policies,
        folds=folds,
        seeds=seeds,
        not_applicable=(MethodId.AAGN, MethodId.FASTER_SNN),
    )
