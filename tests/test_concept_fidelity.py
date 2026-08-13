"""Reference tests for Phase 16 concept fidelity metrics."""

from __future__ import annotations

import numpy as np
import pytest

from pada3dacb.evaluation.concepts.fidelity import (
    compute_global_fidelity,
    compute_per_roi_fidelity,
    compute_per_subject_fidelity,
)
from pada3dacb.evaluation.schemas import ValueStatus


def test_global_and_per_subject_fidelity_match_direct_reference() -> None:
    predicted = np.array([[1.0, 3.0], [2.0, 4.0]])
    target = np.array([[0.0, 1.0], [2.0, 2.0]])

    global_result = compute_global_fidelity(predicted, target)
    subject_results = compute_per_subject_fidelity(predicted, target)

    assert global_result.mae == pytest.approx(1.25)
    assert global_result.rmse == pytest.approx(1.5)
    assert global_result.bias == pytest.approx(1.25)
    assert [result.mae for result in subject_results] == pytest.approx([1.5, 1.0])
    assert [result.rmse for result in subject_results] == pytest.approx(
        [np.sqrt(2.5), np.sqrt(2.0)]
    )


def test_per_roi_correlation_reports_constant_roi_as_unavailable() -> None:
    predicted = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]])
    target = np.array([[0.0, 5.0], [2.0, 5.0], [4.0, 5.0]])

    results = compute_per_roi_fidelity(predicted, target)

    assert results[0].status is ValueStatus.AVAILABLE
    assert results[0].pearson == pytest.approx(1.0)
    assert results[0].spearman == pytest.approx(1.0)
    assert results[1].status is ValueStatus.UNAVAILABLE
    assert results[1].pearson is None
    assert results[1].reason == "constant_roi"


def test_per_roi_correlation_prioritizes_insufficient_samples() -> None:
    results = compute_per_roi_fidelity(
        np.array([[0.0, 1.0]]),
        np.array([[1.0, 2.0]]),
    )

    assert results[0].status is ValueStatus.UNAVAILABLE
    assert results[0].pearson is None
    assert results[0].spearman is None
    assert results[0].reason == "insufficient_samples"


def test_per_roi_fidelity_reports_direct_reference_values() -> None:
    results = compute_per_roi_fidelity(
        np.array([[0.0, 1.0], [2.0, 4.0], [4.0, 7.0]]),
        np.array([[0.0, 0.0], [1.0, 2.0], [2.0, 4.0]]),
    )

    assert [result.mae for result in results] == pytest.approx([1.0, 2.0])
    assert [result.rmse for result in results] == pytest.approx(
        [np.sqrt(5.0 / 3.0), np.sqrt(14.0 / 3.0)]
    )
    assert [result.bias for result in results] == pytest.approx([1.0, 2.0])


@pytest.mark.parametrize(
    ("predicted", "target", "message"),
    [
        (np.ones((2, 2)), np.ones((2, 3)), "Shape mismatch"),
        (np.ones(2), np.ones(2), "two-dimensional"),
        (np.empty((0, 2)), np.empty((0, 2)), "at least one subject"),
        (np.array([[np.nan, 0.0]]), np.zeros((1, 2)), "finite"),
    ],
)
def test_fidelity_rejects_invalid_arrays(predicted, target, message) -> None:
    with pytest.raises(ValueError, match=message):
        compute_global_fidelity(predicted, target)
