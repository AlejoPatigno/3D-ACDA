"""Edge-case references for Phase 16 statistical contracts."""

from __future__ import annotations

import numpy as np
import pytest

from pada3dacb.evaluation.concepts.fidelity import compute_per_roi_fidelity
from pada3dacb.evaluation.concepts.statistics import bootstrap_metric, paired_bootstrap_diff
from pada3dacb.evaluation.schemas import MethodId, ValueStatus


def test_constant_roi_correlation_is_unavailable_not_zero() -> None:
    rows = compute_per_roi_fidelity(
        np.ones((4, 2)),
        np.array([[0.0, 1.0], [0.0, 2.0], [0.0, 3.0], [0.0, 4.0]]),
    )

    assert rows[0].status is ValueStatus.UNAVAILABLE
    assert rows[0].pearson is None
    assert rows[0].spearman is None


def test_single_subject_bootstrap_tracks_all_invalid_replicates() -> None:
    result = bootstrap_metric(
        np.array([0.5]),
        labels=np.array([1]),
        metric="concept_mae",
        n_replicates=25,
        seed=5,
    )

    assert result.status is ValueStatus.UNAVAILABLE
    assert result.successful == 0
    assert result.invalid == 25


def test_non_concept_baseline_cannot_enter_paired_family() -> None:
    with pytest.raises(ValueError, match="four PADA-3DACB comparators"):
        paired_bootstrap_diff(
            np.array([0.1, 0.2]),
            np.array([0.2, 0.1]),
            labels=np.array([0, 1]),
            comparator_method=MethodId.FASTER_SNN,
            metric="concept_mae",
            n_replicates=20,
            seed=5,
        )


def test_correlation_numerical_failure_is_unavailable(monkeypatch) -> None:
    def fail_pearson(*args, **kwargs):
        raise FloatingPointError("reference failure")

    monkeypatch.setattr(
        "pada3dacb.evaluation.concepts.fidelity.stats.pearsonr",
        fail_pearson,
    )
    rows = compute_per_roi_fidelity(
        np.array([[0.0], [1.0], [2.0]]),
        np.array([[0.0], [2.0], [4.0]]),
    )

    assert rows[0].status is ValueStatus.UNAVAILABLE
    assert rows[0].reason == "numerical_error"
    assert rows[0].pearson is None
    assert rows[0].spearman is None


def test_bootstrap_allows_missing_class_support_without_fabricating_rows() -> None:
    result = bootstrap_metric(
        np.array([1.0, 3.0, 5.0, 7.0]),
        labels=np.array([0, 0, 1, 1]),
        metric="concept_mae",
        n_replicates=20,
        seed=9,
    )

    assert result.status is ValueStatus.AVAILABLE
    assert result.point_estimate == pytest.approx(4.0)
    assert result.successful == 20
    assert result.invalid == 0


def test_paired_bootstrap_rejects_mismatched_subject_vectors() -> None:
    with pytest.raises(ValueError, match="aligned per-subject vectors"):
        paired_bootstrap_diff(
            np.array([0.1, 0.2]),
            np.array([0.2]),
            labels=np.array([0, 1]),
            comparator_method=MethodId.SOURCE_ONLY,
            metric="concept_mae",
            n_replicates=20,
            seed=5,
        )
