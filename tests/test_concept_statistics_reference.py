"""Independent references for Phase 16 stratified inference."""

from __future__ import annotations

import numpy as np
import pytest

from pada3dacb.evaluation.concepts.statistics import adjust_holm, bootstrap_metric


def test_diagnosis_stratification_keeps_fixed_class_mix() -> None:
    result = bootstrap_metric(
        np.array([0.0, 0.0, 10.0, 10.0, 20.0, 20.0]),
        labels=np.array([0, 0, 1, 1, 2, 2]),
        metric="concept_mae",
        n_replicates=200,
        seed=23,
    )

    assert result.point_estimate == 10.0
    assert result.ci_low == result.ci_high == 10.0
    assert result.successful == 200
    assert result.invalid == 0


def test_four_comparator_holm_matches_manual_step_down_values() -> None:
    rows = adjust_holm([0.01, 0.04, 0.03, 0.20], metric="concept_mae")

    adjusted = [row.adjusted_p_value for row in rows]
    assert adjusted == pytest.approx([0.04, 0.09, 0.09, 0.20])
    assert [row.holm_rank for row in rows] == [1, 3, 2, 4]
    assert all(row.family_size == 4 for row in rows)
