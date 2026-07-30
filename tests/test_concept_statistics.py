"""Deterministic statistical reference tests for Phase 16."""

from __future__ import annotations

import numpy as np
import pytest

from pada3dacb.evaluation.concepts.statistics import (
    CONCEPT_COMPARATOR_METHODS,
    adjust_holm,
    bootstrap_metric,
    exact_mcnemar,
    paired_bootstrap_diff,
)
from pada3dacb.evaluation.schemas import MethodId, ValueStatus


def test_subject_bootstrap_is_deterministic() -> None:
    values = np.array([0.1, 0.2, 0.3, 0.4])

    labels = np.array([0, 0, 1, 1])
    first = bootstrap_metric(values, labels=labels, metric="concept_mae", n_replicates=100, seed=7)
    second = bootstrap_metric(values, labels=labels, metric="concept_mae", n_replicates=100, seed=7)

    assert first == second
    assert first.status is ValueStatus.AVAILABLE
    assert first.point_estimate == pytest.approx(0.25)
    assert first.requested == first.successful == 100
    assert first.invalid == 0
    assert first.ci_low <= first.point_estimate <= first.ci_high


def test_subject_bootstrap_rejects_roi_matrix() -> None:
    with pytest.raises(ValueError, match="per-subject vector"):
        bootstrap_metric(
            np.ones((2, 3)), labels=np.array([0, 1]), metric="concept_mae", n_replicates=10
        )


def test_exact_mcnemar_matches_known_discordant_counts() -> None:
    result = exact_mcnemar(
        pred_a=np.array([0, 0, 1, 2]),
        pred_b=np.array([0, 1, 0, 2]),
        y_true=np.array([0, 0, 0, 2]),
        comparator_method=MethodId.SOURCE_ONLY,
    )

    assert result.n01_reference_correct == 1
    assert result.n10_comparator_correct == 1
    assert result.discordant_count == 2
    assert result.raw_p_value == pytest.approx(1.0)


def test_paired_bootstrap_uses_subject_pairs_and_centered_p_value() -> None:
    result = paired_bootstrap_diff(
        np.array([0.1, 0.2, 0.3, 0.4]),
        np.array([0.2, 0.2, 0.2, 0.2]),
        labels=np.array([0, 0, 1, 1]),
        comparator_method=MethodId.CORAL,
        metric="concept_mae",
        n_replicates=100,
        seed=11,
    )

    assert result.status is ValueStatus.AVAILABLE
    assert result.observed_difference == pytest.approx(0.05)
    assert result.p_value_method == "centered_plus_one"
    assert 0.0 <= result.raw_p_value <= 1.0
    assert result.requested == result.successful == 100


def test_paired_bootstrap_rejects_non_concept_baseline() -> None:
    with pytest.raises(ValueError, match="four PADA-3DACB comparators"):
        paired_bootstrap_diff(
            np.array([0.1, 0.2]),
            np.array([0.2, 0.1]),
            labels=np.array([0, 1]),
            comparator_method=MethodId.AAGN,
            metric="concept_mae",
            n_replicates=10,
            seed=3,
        )


def test_stratified_bootstrap_preserves_diagnosis_support() -> None:
    result = bootstrap_metric(
        np.array([0.0, 0.0, 10.0, 10.0]),
        labels=np.array([0, 0, 1, 1]),
        metric="concept_mae",
        n_replicates=100,
        seed=19,
    )

    assert result.ci_low == result.ci_high == 5.0


def test_holm_uses_only_the_four_pada_comparators() -> None:
    raw = [0.01, 0.04, 0.03, 0.2]

    rows = adjust_holm(raw, metric="concept_mae")

    assert tuple(row.comparator_method for row in rows) == CONCEPT_COMPARATOR_METHODS
    assert len(rows) == 4
    assert all(row.family_size == 4 for row in rows)
    assert all(row.status is ValueStatus.AVAILABLE for row in rows)
    adjusted = [row.adjusted_p_value for row in rows]
    assert all(value is not None and 0.0 <= value <= 1.0 for value in adjusted)
