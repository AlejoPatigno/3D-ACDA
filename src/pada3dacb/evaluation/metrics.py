"""Fixed-label predictive metrics with explicit availability contracts."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    cohen_kappa_score,
    log_loss,
    matthews_corrcoef,
    roc_auc_score,
)

from .schemas import (
    AGGREGATE_METRIC_NAMES,
    ANALYSIS_CLASS_INDICES,
    ANALYSIS_CLASS_LABELS,
    PER_CLASS_METRIC_NAMES,
    MetricSet,
    MetricValue,
    PerClassMetric,
    SubjectPrediction,
    ValueStatus,
)

COUNT_METRIC_NAMES = AGGREGATE_METRIC_NAMES[:8]
COUNT_PER_CLASS_NAMES = ("support", "precision", "recall", "sensitivity", "specificity", "f1")


def compute_binary_metrics(rows: Sequence[Mapping[str, object]]) -> dict[str, dict[str, object]]:
    """Compute the Phase 18B fixed-order metric set with nullable failures."""
    from pada3dacb.binary import evaluate_binary_predictions

    return evaluate_binary_predictions(rows).metrics


@dataclass(frozen=True)
class CountMetricResult:
    subject_count: int
    aggregate_metrics: Mapping[str, MetricValue]
    per_class_metrics: tuple[PerClassMetric, ...]

    def __post_init__(self) -> None:
        if tuple(self.aggregate_metrics) != COUNT_METRIC_NAMES:
            raise ValueError("count metrics must be complete and ordered")
        object.__setattr__(self, "aggregate_metrics", MappingProxyType(dict(self.aggregate_metrics)))
        object.__setattr__(self, "per_class_metrics", tuple(self.per_class_metrics))


def _unavailable(reason: str) -> MetricValue:
    return MetricValue.unavailable(reason)


def _ratio(numerator: int, denominator: int, reason: str) -> MetricValue:
    return MetricValue.available(numerator / denominator) if denominator else _unavailable(reason)


def _first_unavailable(values: Sequence[MetricValue]) -> str | None:
    return next((value.reason for value in values if value.status is ValueStatus.UNAVAILABLE), None)


def _mean(values: Sequence[MetricValue]) -> MetricValue:
    reason = _first_unavailable(values)
    if reason is not None:
        return _unavailable(reason)
    return MetricValue.available(math.fsum(float(value.value) for value in values) / len(values))


def _validate_homogeneous(
    table: Sequence[SubjectPrediction], *, allow_repeated_subjects: bool = False
) -> None:
    if not table:
        return
    first = table[0]
    identity = (first.method_id, first.direction, first.checkpoint_policy)
    if any((row.method_id, row.direction, row.checkpoint_policy) != identity for row in table[1:]):
        raise ValueError("metric table must be homogeneous")
    subjects = [row.subject_hash for row in table]
    if not allow_repeated_subjects and len(subjects) != len(set(subjects)):
        raise ValueError("metric table must contain one row per subject")


def _empty_result() -> CountMetricResult:
    unavailable = _unavailable("empty_subject_set")
    aggregates = dict.fromkeys(COUNT_METRIC_NAMES, unavailable)
    rows = tuple(
        PerClassMetric(
            ANALYSIS_CLASS_LABELS[index], index, unavailable,
            metric, unavailable,
        )
        for index in ANALYSIS_CLASS_INDICES
        for metric in COUNT_PER_CLASS_NAMES
    )
    return CountMetricResult(0, aggregates, rows)


def compute_count_metrics(
    table: Sequence[SubjectPrediction], *, allow_repeated_subjects: bool = False
) -> CountMetricResult:
    """Compute count-derived metrics without coercing undefined values to zero."""
    rows = tuple(table)
    _validate_homogeneous(rows, allow_repeated_subjects=allow_repeated_subjects)
    if not rows:
        return _empty_result()

    true_labels = [row.true_label for row in rows]
    predicted_labels = [row.predicted_label for row in rows]
    count_matrix = [
        [sum(truth == true_index and prediction == predicted_index for truth, prediction in zip(true_labels, predicted_labels, strict=True))
         for predicted_index in ANALYSIS_CLASS_INDICES]
        for true_index in ANALYSIS_CLASS_INDICES
    ]
    true_counts = [sum(row) for row in count_matrix]
    predicted_counts = [sum(count_matrix[truth][prediction] for truth in ANALYSIS_CLASS_INDICES) for prediction in ANALYSIS_CLASS_INDICES]
    total = len(rows)
    per_class: list[PerClassMetric] = []
    class_values: dict[str, list[MetricValue]] = {name: [] for name in COUNT_PER_CLASS_NAMES}

    for index in ANALYSIS_CLASS_INDICES:
        true_positive = count_matrix[index][index]
        false_positive = predicted_counts[index] - true_positive
        false_negative = true_counts[index] - true_positive
        true_negative = total - true_positive - false_positive - false_negative
        support = MetricValue.available(true_counts[index])
        values = {
            "support": support,
            "precision": _ratio(true_positive, true_positive + false_positive, "no_predicted_positive"),
            "recall": _ratio(true_positive, true_counts[index], "missing_true_class"),
            "specificity": _ratio(true_negative, true_negative + false_positive, "missing_negative_class"),
            "f1": _ratio(2 * true_positive, 2 * true_positive + false_positive + false_negative, "zero_f1_denominator"),
        }
        values["sensitivity"] = values["recall"]
        for metric in COUNT_PER_CLASS_NAMES:
            class_values[metric].append(values[metric])
            per_class.append(PerClassMetric(
                ANALYSIS_CLASS_LABELS[index], index, support, metric, values[metric]
            ))

    accuracy = MetricValue.available(sum(count_matrix[index][index] for index in ANALYSIS_CLASS_INDICES) / total)
    weighted_reason = _first_unavailable([
        class_values["f1"][index]
        for index in ANALYSIS_CLASS_INDICES
        if true_counts[index] > 0
    ])
    weighted_f1 = (
        _unavailable(weighted_reason)
        if weighted_reason is not None
        else MetricValue.available(math.fsum(
            true_counts[index] / total * float(class_values["f1"][index].value)
            for index in ANALYSIS_CLASS_INDICES if true_counts[index] > 0
        ))
    )
    mcc_denominator = math.sqrt(
        (total * total - sum(value * value for value in predicted_counts))
        * (total * total - sum(value * value for value in true_counts))
    )
    mcc = (
        MetricValue.available(float(matthews_corrcoef(true_labels, predicted_labels)))
        if mcc_denominator else _unavailable("zero_mcc_denominator")
    )
    expected_agreement = math.fsum(
        true_counts[index] / total * predicted_counts[index] / total
        for index in ANALYSIS_CLASS_INDICES
    )
    kappa = (
        MetricValue.available(float(cohen_kappa_score(true_labels, predicted_labels, labels=[0, 1, 2])))
        if 1.0 - expected_agreement > 0.0 else _unavailable("zero_kappa_denominator")
    )
    aggregates = {
        "accuracy": accuracy,
        "balanced_accuracy": _mean(class_values["recall"]),
        "macro_f1": _mean(class_values["f1"]),
        "weighted_f1": weighted_f1,
        "macro_precision": _mean(class_values["precision"]),
        "macro_recall": _mean(class_values["recall"]),
        "multiclass_mcc": mcc,
        "cohen_kappa": kappa,
    }
    return CountMetricResult(total, aggregates, tuple(per_class))


def _finite_metric(value: float) -> MetricValue:
    return MetricValue.available(value) if math.isfinite(value) else _unavailable("non_finite_input")


def compute_metrics(
    table: Sequence[SubjectPrediction], *, allow_repeated_subjects: bool = False
) -> MetricSet:
    """Compute metrics, allowing repeated observations only for explicit resamples."""
    rows = tuple(table)
    count_result = compute_count_metrics(
        rows, allow_repeated_subjects=allow_repeated_subjects
    )
    if not rows:
        aggregates = dict(count_result.aggregate_metrics)
        aggregates.update({name: _unavailable("empty_subject_set") for name in AGGREGATE_METRIC_NAMES[8:]})
        count_lookup = {(row.class_index, row.metric): row for row in count_result.per_class_metrics}
        per_class = tuple(
            count_lookup.get(
                (index, metric),
                PerClassMetric(
                    ANALYSIS_CLASS_LABELS[index], index,
                    _unavailable("empty_subject_set"), metric,
                    _unavailable("empty_subject_set"),
                ),
            )
            for index in ANALYSIS_CLASS_INDICES
            for metric in PER_CLASS_METRIC_NAMES
        )
        return MetricSet(0, aggregates, per_class)

    probabilities = np.asarray([row.probabilities for row in rows], dtype=np.float64)
    true_labels = np.asarray([row.true_label for row in rows], dtype=np.int64)
    eps = np.finfo(np.float64).eps
    clipped = np.clip(probabilities, eps, 1.0 - eps)
    clipped /= clipped.sum(axis=1, keepdims=True)
    log_loss_value = _finite_metric(float(log_loss(
        true_labels, clipped, labels=[0, 1, 2], normalize=True
    )))
    one_hot = np.eye(3, dtype=np.float64)[true_labels]
    brier_value = _finite_metric(float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))))

    ranking_rows: dict[tuple[int, str], MetricValue] = {}
    auc_values: list[MetricValue] = []
    ap_values: list[MetricValue] = []
    for index in ANALYSIS_CLASS_INDICES:
        binary = true_labels == index
        positives = int(binary.sum())
        negatives = len(rows) - positives
        if positives == 0:
            auc = ap = _unavailable("missing_true_class")
        elif negatives == 0:
            auc = ap = _unavailable("missing_negative_class")
        else:
            auc = _finite_metric(float(roc_auc_score(binary, probabilities[:, index])))
            ap = _finite_metric(float(average_precision_score(binary, probabilities[:, index])))
        ranking_rows[(index, "ovr_roc_auc")] = auc
        ranking_rows[(index, "ovr_average_precision")] = ap
        auc_values.append(auc)
        ap_values.append(ap)

    aggregates = dict(count_result.aggregate_metrics)
    aggregates.update({
        "multiclass_log_loss": log_loss_value,
        "multiclass_brier_score": brier_value,
        "macro_ovr_roc_auc": _mean(auc_values),
        "macro_ovr_average_precision": _mean(ap_values),
    })
    count_lookup = {(row.class_index, row.metric): row for row in count_result.per_class_metrics}
    per_class = []
    for index in ANALYSIS_CLASS_INDICES:
        support = count_lookup[(index, "support")].support
        for metric in PER_CLASS_METRIC_NAMES:
            count_row = count_lookup.get((index, metric))
            value = count_row.value if count_row is not None else ranking_rows[(index, metric)]
            per_class.append(PerClassMetric(
                ANALYSIS_CLASS_LABELS[index], index, support, metric, value
            ))
    return MetricSet(len(rows), aggregates, tuple(per_class))


compute_task_scoped_binary_metrics = compute_binary_metrics
