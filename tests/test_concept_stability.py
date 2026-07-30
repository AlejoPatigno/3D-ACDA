"""Reference tests for Phase 16 ROI stability metrics."""

from __future__ import annotations

import numpy as np
import pytest

from pada3dacb.evaluation.concepts.stability import (
    compute_all_stability,
    compute_mean_jaccard,
    compute_mean_pairwise_rho,
    compute_pairwise_spearman,
)


def test_pairwise_spearman_preserves_reverse_ranking() -> None:
    profiles = np.array([[1.0, 2.0, 3.0], [3.0, 2.0, 1.0]])

    matrix = compute_pairwise_spearman(profiles)

    np.testing.assert_allclose(matrix, np.array([[1.0, -1.0], [-1.0, 1.0]]))
    assert compute_mean_pairwise_rho(matrix) == pytest.approx(-1.0)


def test_constant_pairwise_profile_is_explicitly_unavailable() -> None:
    profiles = np.array([[1.0, 1.0, 1.0], [2.0, 2.0, 2.0]])

    matrix = compute_pairwise_spearman(profiles)

    assert np.isnan(matrix[0, 1])
    assert compute_mean_pairwise_rho(matrix) is None


def test_complete_stability_returns_serializable_contract() -> None:
    fidelity = np.array([[0.1, 0.2, 0.3], [0.2, 0.3, 0.1]])
    anatomy = np.array([[0.3, 0.2, 0.1], [0.2, 0.1, 0.3]])
    concepts = np.array([[0.2, 0.4, 0.6], [0.3, 0.5, 0.4]])
    alpha = np.array([[0.2, 0.3, 0.5], [0.3, 0.2, 0.5]])

    result = compute_all_stability(
        fidelity,
        anatomy,
        concepts,
        alpha,
        k_values=[1, 2],
    )

    assert isinstance(result.pairwise_rho_fidelity, tuple)
    assert len(result.pairwise_rho_fidelity) == 2
    assert len(result.instance_std_concept) == 3
    assert set(result.jaccard_fidelity) == {1, 2}
    assert set(result.jaccard_anatomy) == {1, 2}
    assert set(result.jaccard_concept) == {1, 2}
    assert set(result.jaccard_alpha) == {1, 2}
    assert len(result.rank_dispersion_std) == 3
    assert len(result.rank_dispersion_range) == 3


def test_stability_rejects_shape_drift_and_invalid_k() -> None:
    with pytest.raises(ValueError, match="same shape"):
        compute_all_stability(
            np.ones((2, 3)),
            np.ones((2, 2)),
            np.ones((2, 3)),
            np.ones((2, 3)),
            k_values=[1],
        )

    with pytest.raises(ValueError, match="positive"):
        compute_mean_jaccard(np.ones((2, 3)), [0])
