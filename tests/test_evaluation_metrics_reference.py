from __future__ import annotations

import math

import numpy as np
import pytest
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

from acda3d.evaluation.confusion_matrices import compute_confusion
from acda3d.evaluation.metrics import compute_metrics
from acda3d.evaluation.schemas import (
    AGGREGATE_METRIC_NAMES,
    CheckpointPolicy,
    Direction,
    MethodId,
    SubjectPrediction,
    ValueStatus,
)

LABELS = (0, 1, 2)


def _table(probabilities: tuple[tuple[float, float, float], ...]) -> tuple[SubjectPrediction, ...]:
    true_labels = (0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2)
    return tuple(
        SubjectPrediction(
            MethodId.MMD,
            Direction.ADNI_TO_OASIS,
            CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            f"subject-{index}",
            truth,
            probability,
            5,
            2,
            (f"{index + 1:064x}",),
        )
        for index, (truth, probability) in enumerate(
            zip(true_labels, probabilities, strict=True)
        )
    )


def _nondegenerate_table() -> tuple[SubjectPrediction, ...]:
    return _table((
        (0.80, 0.10, 0.10), (0.20, 0.70, 0.10),
        (0.55, 0.20, 0.25), (0.10, 0.25, 0.65),
        (0.10, 0.75, 0.15), (0.15, 0.35, 0.50),
        (0.20, 0.60, 0.20), (0.60, 0.25, 0.15),
        (0.10, 0.20, 0.70), (0.20, 0.65, 0.15),
        (0.15, 0.10, 0.75), (0.55, 0.15, 0.30),
    ))


def _arrays(table: tuple[SubjectPrediction, ...]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    truth = np.asarray([row.true_label for row in table], dtype=np.int64)
    probability = np.asarray([row.probabilities for row in table], dtype=np.float64)
    prediction = np.argmax(probability, axis=1)
    return truth, prediction, probability


def test_repeated_subjects_require_explicit_internal_resample_mode() -> None:
    table = _nondegenerate_table()
    resample = (table[0], table[0], table[4], table[8])
    with pytest.raises(ValueError, match="one row per subject"):
        compute_metrics(resample)

    result = compute_metrics(resample, allow_repeated_subjects=True)
    assert result.subject_count == 4
    assert result.aggregate_metrics["accuracy"].value == 1.0


def test_all_aggregate_metrics_match_fixed_label_library_and_direct_references() -> None:
    table = _nondegenerate_table()
    truth, prediction, probability = _arrays(table)
    result = compute_metrics(table)
    one_hot = np.eye(3, dtype=np.float64)[truth]
    clipped = np.clip(probability, np.finfo(np.float64).eps, 1.0 - np.finfo(np.float64).eps)
    clipped /= clipped.sum(axis=1, keepdims=True)
    aucs = [roc_auc_score(truth == label, probability[:, label]) for label in LABELS]
    aps = [average_precision_score(truth == label, probability[:, label]) for label in LABELS]
    expected = {
        "accuracy": accuracy_score(truth, prediction),
        "balanced_accuracy": balanced_accuracy_score(truth, prediction),
        "macro_f1": f1_score(truth, prediction, labels=LABELS, average="macro"),
        "weighted_f1": f1_score(truth, prediction, labels=LABELS, average="weighted"),
        "macro_precision": precision_score(truth, prediction, labels=LABELS, average="macro"),
        "macro_recall": recall_score(truth, prediction, labels=LABELS, average="macro"),
        "multiclass_mcc": matthews_corrcoef(truth, prediction),
        "cohen_kappa": cohen_kappa_score(truth, prediction, labels=LABELS),
        "multiclass_log_loss": log_loss(truth, clipped, labels=LABELS, normalize=True),
        "multiclass_brier_score": np.mean(np.sum((probability - one_hot) ** 2, axis=1)),
        "macro_ovr_roc_auc": math.fsum(aucs) / 3,
        "macro_ovr_average_precision": math.fsum(aps) / 3,
    }
    assert tuple(result.aggregate_metrics) == AGGREGATE_METRIC_NAMES
    for name, reference in expected.items():
        value = result.aggregate_metrics[name]
        assert value.status is ValueStatus.AVAILABLE
        assert float(value.value) == pytest.approx(float(reference), rel=1e-13, abs=1e-13)


def test_every_per_class_row_matches_independent_count_and_ranking_formulas() -> None:
    table = _nondegenerate_table()
    truth, prediction, probability = _arrays(table)
    result = compute_metrics(table)
    by_key = {(row.class_index, row.metric): row for row in result.per_class_metrics}
    assert len(by_key) == 24

    for label in LABELS:
        positive = truth == label
        predicted_positive = prediction == label
        tp = int(np.sum(positive & predicted_positive))
        fp = int(np.sum(~positive & predicted_positive))
        fn = int(np.sum(positive & ~predicted_positive))
        tn = int(np.sum(~positive & ~predicted_positive))
        expected = {
            "support": int(np.sum(positive)),
            "precision": tp / (tp + fp),
            "recall": tp / (tp + fn),
            "sensitivity": tp / (tp + fn),
            "specificity": tn / (tn + fp),
            "f1": 2 * tp / (2 * tp + fp + fn),
            "ovr_roc_auc": roc_auc_score(positive, probability[:, label]),
            "ovr_average_precision": average_precision_score(positive, probability[:, label]),
        }
        for metric, reference in expected.items():
            row = by_key[(label, metric)]
            assert row.value.status is ValueStatus.AVAILABLE
            assert float(row.value.value) == pytest.approx(float(reference), rel=1e-13, abs=1e-13)


def test_confusion_counts_and_normalization_match_independent_fixed_matrix() -> None:
    table = _nondegenerate_table()
    truth, prediction, _ = _arrays(table)
    result = compute_confusion(table)
    counts = confusion_matrix(truth, prediction, labels=LABELS)
    normalized = counts.astype(np.float64) / counts.sum(axis=1, keepdims=True)
    assert result.counts == tuple(tuple(int(value) for value in row) for row in counts)
    assert np.asarray(result.normalized, dtype=np.float64) == pytest.approx(normalized)
    assert all(status.status is ValueStatus.AVAILABLE for status in result.normalized_row_statuses)


def test_float64_log_loss_clipping_and_unscaled_brier_are_exactly_distinct() -> None:
    probabilities = [row.probabilities for row in _nondegenerate_table()]
    probabilities[0] = (1.0, 0.0, 0.0)
    probabilities[4] = (0.0, 1.0, 0.0)
    probabilities[8] = (0.0, 0.0, 1.0)
    table = _table(tuple(probabilities))
    truth, _, probability = _arrays(table)
    result = compute_metrics(table)
    eps = np.finfo(np.float64).eps
    clipped = np.clip(probability, eps, 1.0 - eps)
    clipped /= clipped.sum(axis=1, keepdims=True)
    one_hot = np.eye(3, dtype=np.float64)[truth]
    brier = float(np.mean(np.sum((probability - one_hot) ** 2, axis=1)))
    assert result.aggregate_metrics["multiclass_log_loss"].value == pytest.approx(
        log_loss(truth, clipped, labels=LABELS, normalize=True), rel=0.0, abs=1e-15
    )
    assert result.aggregate_metrics["multiclass_brier_score"].value == pytest.approx(brier)
    assert brier != pytest.approx(brier / 3.0)
