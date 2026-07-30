"""Independent hand-calculated references for Phase 16 metrics."""

from __future__ import annotations

import math

import numpy as np
import pytest

from pada3dacb.evaluation.concepts.agreement import compute_js_divergence
from pada3dacb.evaluation.concepts.anatomy import compute_global_anatomy
from pada3dacb.evaluation.concepts.fidelity import compute_global_fidelity


def test_fidelity_matches_direct_elementwise_reference() -> None:
    predicted = np.array([[0.0, 0.5], [1.0, 0.5]])
    target = np.array([[0.0, 0.0], [0.5, 1.0]])

    result = compute_global_fidelity(predicted, target)

    errors = np.array([0.0, 0.5, 0.5, -0.5])
    assert result.mae == pytest.approx(float(np.mean(np.abs(errors))))
    assert result.rmse == pytest.approx(float(np.sqrt(np.mean(errors**2))))
    assert result.bias == pytest.approx(float(np.mean(errors)))


def test_anatomy_uses_g_bar_not_concept_target() -> None:
    predicted = np.array([[0.1, 0.9], [0.2, 0.8]])
    g_bar = np.array([[0.0, 1.0], [0.0, 1.0]])

    result = compute_global_anatomy(predicted, g_bar)

    assert result.mae == pytest.approx(0.15)
    assert result.rmse == pytest.approx(math.sqrt(0.025))
    assert result.bias == pytest.approx(0.0)


def test_js_divergence_matches_closed_form_binary_embedding() -> None:
    latent = np.array([[1.0, 0.0, 0.0]])
    concept = np.array([[0.0, 1.0, 0.0]])

    assert compute_js_divergence(latent, concept) == pytest.approx(math.log(2.0), abs=1e-10)
