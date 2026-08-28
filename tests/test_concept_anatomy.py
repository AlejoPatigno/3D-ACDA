"""Reference tests for Phase 16 anatomical consistency metrics."""

from __future__ import annotations

import numpy as np
import pytest

from acda3d.evaluation.concepts.anatomy import (
    compute_global_anatomy,
    compute_weighted_anatomy_score,
)
from acda3d.evaluation.schemas import ValueStatus


def test_global_anatomy_matches_direct_reference() -> None:
    predicted = np.array([[1.0, 3.0], [2.0, 4.0]])
    anatomy = np.array([[0.0, 1.0], [2.0, 2.0]])

    result = compute_global_anatomy(predicted, anatomy)

    assert result.mae == pytest.approx(1.25)
    assert result.rmse == pytest.approx(1.5)
    assert result.bias == pytest.approx(1.25)


def test_weighted_anatomy_matches_protocol_equations() -> None:
    predicted = np.array([[1.0, 3.0], [2.0, 4.0]])
    anatomy = np.array([[0.0, 1.0], [2.0, 2.0]])

    result = compute_weighted_anatomy_score(
        predicted,
        anatomy,
        roi_weights=np.array([0.25, 0.75]),
    )

    assert result.status is ValueStatus.AVAILABLE
    assert result.weighted_mae == pytest.approx(1.625)
    assert result.weighted_rmse == pytest.approx(np.sqrt(3.125))
    assert result.weighted_bias == pytest.approx(1.625)


def test_weighted_anatomy_is_explicitly_unavailable_without_weights() -> None:
    result = compute_weighted_anatomy_score(
        np.ones((2, 2)),
        np.ones((2, 2)),
        roi_weights=None,
    )

    assert result.status is ValueStatus.UNAVAILABLE
    assert result.weighted_mae is None
    assert result.reason == "weights_unavailable"


def test_anatomy_correlation_prioritizes_insufficient_samples() -> None:
    from acda3d.evaluation.concepts.anatomy import compute_per_roi_anatomy

    results = compute_per_roi_anatomy(
        np.array([[0.0, 1.0]]),
        np.array([[1.0, 2.0]]),
    )

    assert results[0].status is ValueStatus.UNAVAILABLE
    assert results[0].pearson is None
    assert results[0].spearman is None
    assert results[0].reason == "insufficient_samples"


def test_per_roi_anatomy_reports_constant_roi_as_unavailable() -> None:
    from acda3d.evaluation.concepts.anatomy import compute_per_roi_anatomy

    results = compute_per_roi_anatomy(
        np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]]),
        np.array([[0.0, 5.0], [2.0, 5.0], [4.0, 5.0]]),
    )

    assert results[0].status is ValueStatus.AVAILABLE
    assert results[0].pearson == pytest.approx(1.0)
    assert results[1].status is ValueStatus.UNAVAILABLE
    assert results[1].pearson is None
    assert results[1].reason == "constant_roi"


@pytest.mark.parametrize(
    "weights",
    [
        np.array([-0.5, 1.5]),
        np.array([np.nan, np.nan]),
        np.array([0.2, 0.2]),
    ],
)
def test_weighted_anatomy_rejects_invalid_weights(weights) -> None:
    with pytest.raises(ValueError, match="ROI weights"):
        compute_weighted_anatomy_score(
            np.ones((2, 2)),
            np.zeros((2, 2)),
            roi_weights=weights,
        )


def test_anatomy_rejects_non_finite_inputs() -> None:
    with pytest.raises(ValueError, match="finite"):
        compute_global_anatomy(
            np.array([[np.inf, 0.0]]),
            np.zeros((1, 2)),
        )
