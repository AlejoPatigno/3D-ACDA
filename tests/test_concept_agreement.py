"""Reference tests for Phase 16 head agreement metrics."""

from __future__ import annotations

import numpy as np
import pytest

from acda3d.evaluation.concepts.agreement import (
    compute_all_agreement,
    compute_consistency_direction,
    compute_head_predictive_metrics,
    compute_js_divergence,
    compute_per_class_disagreement,
    compute_top1_agreement,
)
from acda3d.evaluation.schemas import ValueStatus


def test_top1_and_js_match_direct_reference() -> None:
    latent = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    concept = np.array([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])

    agreement, disagreement = compute_top1_agreement(latent, concept)
    js = compute_js_divergence(latent, concept)

    assert agreement == pytest.approx(0.5)
    assert disagreement == pytest.approx(0.5)
    assert js == pytest.approx(np.log(2.0) / 2.0)


def test_per_class_disagreement_preserves_zero_support() -> None:
    results = compute_per_class_disagreement(
        latent_pred=np.array([0, 1]),
        concept_pred=np.array([0, 0]),
        true_labels=np.array([0, 1]),
    )

    assert results[0].disagree_rate == 0.0
    assert results[1].disagree_rate == 1.0
    assert results[2].status is ValueStatus.UNAVAILABLE
    assert results[2].disagree_rate is None
    assert results[2].reason == "zero_support"


def test_complete_agreement_uses_fixed_class_order() -> None:
    probabilities = np.array(
        [
            [0.8, 0.1, 0.1],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
        ]
    )

    result = compute_all_agreement(
        probabilities,
        probabilities.copy(),
        true_labels=np.array([0, 1, 2]),
        consistency_loss_type="kl",
    )

    assert result.latent_accuracy == 1.0
    assert result.latent_macro_f1 == 1.0
    assert result.concept_accuracy == 1.0
    assert result.top1_agreement_rate == 1.0
    assert result.mean_js_divergence == pytest.approx(0.0)
    assert result.consistency_direction == "latent_supervises_concept"

    with pytest.raises(TypeError):
        compute_all_agreement(
            probabilities,
            probabilities.copy(),
            true_labels=np.array([0, 1, 2]),
        )


@pytest.mark.parametrize(
    ("latent", "concept", "message"),
    [
        (np.ones((2, 2)), np.ones((2, 3)), "shape"),
        (np.ones((0, 3)), np.ones((0, 3)), "at least one subject"),
        (np.array([[np.nan, 0.0, 1.0]]), np.array([[0.0, 0.0, 1.0]]), "finite"),
        (np.array([[0.2, 0.2, 0.2]]), np.array([[0.0, 0.0, 1.0]]), "sum to one"),
    ],
)
def test_agreement_rejects_invalid_probability_matrices(latent, concept, message) -> None:
    with pytest.raises(ValueError, match=message):
        compute_js_divergence(latent, concept)


def test_consistency_direction_rejects_unknown_loss() -> None:
    with pytest.raises(ValueError, match="consistency loss"):
        compute_consistency_direction(
            np.ones((1, 3)) / 3,
            np.ones((1, 3)) / 3,
            consistency_loss_type="unknown",
        )


def test_complete_agreement_exposes_per_class_disagreement_counts() -> None:
    latent = np.array(
        [
            [0.8, 0.1, 0.1],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
            [0.8, 0.1, 0.1],
        ]
    )
    concept = np.array(
        [
            [0.1, 0.8, 0.1],
            [0.1, 0.8, 0.1],
            [0.8, 0.1, 0.1],
            [0.8, 0.1, 0.1],
        ]
    )

    latent_predictions = np.argmax(latent, axis=1)
    concept_predictions = np.argmax(concept, axis=1)
    result = compute_per_class_disagreement(
        latent_predictions,
        concept_predictions,
        true_labels=np.array([0, 1, 2, 2]),
    )

    assert [(item.class_label, item.disagree_count, item.total_count) for item in result] == [
        ("CN", 1, 1),
        ("MCI", 0, 1),
        ("AD", 1, 2),
    ]


def test_agreement_rejects_labels_outside_fixed_class_order() -> None:
    probabilities = np.ones((2, 3)) / 3

    with pytest.raises(ValueError, match="true_labels"):
        compute_head_predictive_metrics(
            probabilities,
            probabilities.copy(),
            true_labels=np.array([0, 3]),
        )


def test_per_class_disagreement_rejects_mismatched_vectors() -> None:
    with pytest.raises(ValueError, match="same length"):
        compute_per_class_disagreement(
            latent_pred=np.array([0, 1]),
            concept_pred=np.array([0]),
            true_labels=np.array([0, 1]),
        )
