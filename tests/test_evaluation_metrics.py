from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import (
    average_precision_score,
    cohen_kappa_score,
    log_loss,
    matthews_corrcoef,
    roc_auc_score,
)

from acda3d.evaluation.metrics import compute_count_metrics, compute_metrics
from acda3d.evaluation.schemas import (
    CheckpointPolicy,
    Direction,
    MethodId,
    SubjectPrediction,
    ValueStatus,
)


def _subject(
    name: str,
    true_label: int,
    predicted_label: int,
    *,
    method: MethodId = MethodId.MMD,
    direction: Direction = Direction.ADNI_TO_OASIS,
    policy: CheckpointPolicy = CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
) -> SubjectPrediction:
    probabilities = tuple(1.0 if index == predicted_label else 0.0 for index in range(3))
    return SubjectPrediction(
        method, direction, policy, name, true_label, probabilities,
        5, 2, ((name[0] * 64) if name[0] in "abcdef" else "a" * 64,),
    )


def _nondegenerate() -> tuple[SubjectPrediction, ...]:
    return tuple(
        _subject(f"{letter}-subject", truth, prediction)
        for letter, truth, prediction in (
            ("a", 0, 0), ("b", 0, 1), ("c", 1, 1),
            ("d", 1, 1), ("e", 2, 2), ("f", 2, 0),
        )
    )


def test_count_metrics_match_hand_calculation_and_sklearn() -> None:
    table = _nondegenerate()
    result = compute_count_metrics(table)
    values = result.aggregate_metrics
    assert values["accuracy"].value == pytest.approx(4 / 6)
    assert values["balanced_accuracy"].value == pytest.approx(2 / 3)
    assert values["macro_recall"].value == pytest.approx(2 / 3)
    assert values["macro_f1"].value == pytest.approx((0.5 + 0.8 + 2 / 3) / 3)
    assert values["weighted_f1"].value == pytest.approx((0.5 + 0.8 + 2 / 3) / 3)
    assert values["macro_precision"].value == pytest.approx((0.5 + 2 / 3 + 1.0) / 3)
    y_true = [row.true_label for row in table]
    y_pred = [row.predicted_label for row in table]
    assert values["multiclass_mcc"].value == pytest.approx(matthews_corrcoef(y_true, y_pred))
    assert values["cohen_kappa"].value == pytest.approx(cohen_kappa_score(y_true, y_pred, labels=[0, 1, 2]))


def test_per_class_count_rows_have_exact_order_and_alias() -> None:
    result = compute_count_metrics(_nondegenerate())
    assert len(result.per_class_metrics) == 18
    assert [(row.class_index, row.metric) for row in result.per_class_metrics[:6]] == [
        (0, "support"), (0, "precision"), (0, "recall"),
        (0, "sensitivity"), (0, "specificity"), (0, "f1"),
    ]
    by_key = {(row.class_index, row.metric): row for row in result.per_class_metrics}
    assert by_key[(0, "support")].value.value == 2
    assert by_key[(0, "recall")].value == by_key[(0, "sensitivity")].value
    assert by_key[(1, "specificity")].value.value == pytest.approx(0.75)


def test_missing_true_class_propagates_in_fixed_class_order() -> None:
    table = (
        _subject("a-subject", 0, 0),
        _subject("b-subject", 0, 1),
        _subject("c-subject", 1, 1),
    )
    result = compute_count_metrics(table)
    by_key = {(row.class_index, row.metric): row.value for row in result.per_class_metrics}
    assert by_key[(2, "support")].value == 0
    assert by_key[(2, "recall")].reason == "missing_true_class"
    assert result.aggregate_metrics["balanced_accuracy"].reason == "missing_true_class"
    assert result.aggregate_metrics["macro_recall"].reason == "missing_true_class"
    assert result.aggregate_metrics["weighted_f1"].status is ValueStatus.AVAILABLE


def test_no_predicted_positive_is_unavailable_not_zero() -> None:
    table = (
        _subject("a-subject", 0, 0),
        _subject("b-subject", 1, 0),
        _subject("c-subject", 2, 0),
    )
    result = compute_count_metrics(table)
    by_key = {(row.class_index, row.metric): row.value for row in result.per_class_metrics}
    assert by_key[(1, "precision")].value is None
    assert by_key[(1, "precision")].reason == "no_predicted_positive"
    assert result.aggregate_metrics["macro_precision"].reason == "no_predicted_positive"


def test_zero_mcc_and_kappa_denominators_remain_explicit() -> None:
    table = (_subject("a-subject", 0, 0), _subject("b-subject", 0, 0))
    result = compute_count_metrics(table)
    assert result.aggregate_metrics["multiclass_mcc"].reason == "zero_mcc_denominator"
    assert result.aggregate_metrics["cohen_kappa"].reason == "zero_kappa_denominator"
    assert result.aggregate_metrics["accuracy"].value == 1.0


def test_empty_table_marks_count_metrics_unavailable() -> None:
    result = compute_count_metrics(())
    assert result.subject_count == 0
    assert all(value.reason == "empty_subject_set" for value in result.aggregate_metrics.values())
    assert all(row.support.reason == "empty_subject_set" for row in result.per_class_metrics)


def test_probability_metrics_match_explicit_references() -> None:
    table = _nondegenerate()
    result = compute_metrics(table)
    probabilities = np.asarray([row.probabilities for row in table], dtype=np.float64)
    true_labels = np.asarray([row.true_label for row in table], dtype=np.int64)
    eps = np.finfo(np.float64).eps
    clipped = np.clip(probabilities, eps, 1.0 - eps)
    clipped /= clipped.sum(axis=1, keepdims=True)
    assert result.aggregate_metrics["multiclass_log_loss"].value == pytest.approx(
        log_loss(true_labels, clipped, labels=[0, 1, 2], normalize=True)
    )
    one_hot = np.eye(3, dtype=np.float64)[true_labels]
    expected_brier = np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))
    assert result.aggregate_metrics["multiclass_brier_score"].value == pytest.approx(expected_brier)
    aucs = [roc_auc_score(true_labels == index, probabilities[:, index]) for index in range(3)]
    aps = [average_precision_score(true_labels == index, probabilities[:, index]) for index in range(3)]
    assert result.aggregate_metrics["macro_ovr_roc_auc"].value == pytest.approx(np.mean(aucs))
    assert result.aggregate_metrics["macro_ovr_average_precision"].value == pytest.approx(np.mean(aps))


def test_complete_metric_set_has_exact_rows_and_recall_alias() -> None:
    result = compute_metrics(_nondegenerate())
    assert len(result.aggregate_metrics) == 12
    assert len(result.per_class_metrics) == 24
    by_key = {(row.class_index, row.metric): row.value for row in result.per_class_metrics}
    for index in range(3):
        assert by_key[(index, "recall")] == by_key[(index, "sensitivity")]
        assert by_key[(index, "ovr_roc_auc")].status is ValueStatus.AVAILABLE
        assert by_key[(index, "ovr_average_precision")].status is ValueStatus.AVAILABLE


def test_missing_ovr_class_and_negative_reasons_are_explicit() -> None:
    missing_class = (
        _subject("a-subject", 0, 0), _subject("b-subject", 0, 1),
        _subject("c-subject", 1, 1),
    )
    result = compute_metrics(missing_class)
    by_key = {(row.class_index, row.metric): row.value for row in result.per_class_metrics}
    assert by_key[(2, "ovr_roc_auc")].reason == "missing_true_class"
    assert by_key[(2, "ovr_average_precision")].reason == "missing_true_class"
    assert result.aggregate_metrics["macro_ovr_roc_auc"].reason == "missing_true_class"

    one_class = (_subject("a-subject", 0, 0), _subject("b-subject", 0, 0))
    result = compute_metrics(one_class)
    by_key = {(row.class_index, row.metric): row.value for row in result.per_class_metrics}
    assert by_key[(0, "ovr_roc_auc")].reason == "missing_negative_class"
    assert result.aggregate_metrics["macro_ovr_roc_auc"].reason == "missing_negative_class"


def test_empty_complete_metrics_are_all_unavailable() -> None:
    result = compute_metrics(())
    assert all(value.reason == "empty_subject_set" for value in result.aggregate_metrics.values())
    assert len(result.per_class_metrics) == 24


def test_metric_table_must_be_homogeneous() -> None:
    mixed = (
        _subject("a-subject", 0, 0),
        _subject("b-subject", 1, 1, direction=Direction.OASIS_TO_ADNI),
    )
    with pytest.raises(ValueError, match="homogeneous"):
        compute_count_metrics(mixed)
