from __future__ import annotations

from collections.abc import Callable

from acda3d.evaluation.bootstrap import bootstrap_metrics
from acda3d.evaluation.confusion_matrices import compute_confusion
from acda3d.evaluation.metrics import compute_metrics
from acda3d.evaluation.multiple_testing import adjust_holm
from acda3d.evaluation.paired_statistics import exact_mcnemar, paired_bootstrap
from acda3d.evaluation.schemas import (
    COMPARATOR_METHODS,
    CheckpointPolicy,
    Direction,
    MethodId,
    MetricValue,
    PairedDifference,
    SubjectPrediction,
    ValueStatus,
)


def _row(
    method: MethodId,
    subject: str,
    truth: int,
    prediction: int,
) -> SubjectPrediction:
    probability = [0.05, 0.05, 0.05]
    probability[prediction] = 0.9
    return SubjectPrediction(
        method, Direction.ADNI_TO_OASIS,
        CheckpointPolicy.PRIMARY_BEST_SOURCE_F1, subject, truth,
        tuple(probability), 5, 2,
        (f"{sum(map(ord, subject)) + list(MethodId).index(method):064x}",),
    )


def _metric_lookup(table: tuple[SubjectPrediction, ...]) -> dict[tuple[int, str], MetricValue]:
    return {
        (row.class_index, row.metric): row.value
        for row in compute_metrics(table).per_class_metrics
    }


def test_missing_classes_no_predicted_positives_and_degenerate_metrics_are_null() -> None:
    table = (
        _row(MethodId.MMD, "a", 0, 0),
        _row(MethodId.MMD, "b", 0, 0),
        _row(MethodId.MMD, "c", 1, 0),
    )
    result = compute_metrics(table)
    per_class = _metric_lookup(table)
    assert per_class[(1, "precision")].reason == "no_predicted_positive"
    assert per_class[(2, "recall")].reason == "missing_true_class"
    assert per_class[(2, "ovr_roc_auc")].reason == "missing_true_class"
    assert result.aggregate_metrics["balanced_accuracy"].status is ValueStatus.UNAVAILABLE
    assert result.aggregate_metrics["macro_ovr_roc_auc"].status is ValueStatus.UNAVAILABLE
    assert result.aggregate_metrics["multiclass_mcc"].reason == "zero_mcc_denominator"


def test_zero_support_confusion_row_is_three_nulls_with_exact_reason() -> None:
    table = (
        _row(MethodId.MMD, "a", 0, 0),
        _row(MethodId.MMD, "b", 1, 1),
    )
    result = compute_confusion(table)
    assert result.counts[2] == (0, 0, 0)
    assert result.normalized[2] == (None, None, None)
    assert result.normalized_row_statuses[2] == MetricValue.unavailable("zero_true_support")


def _threshold_metric(invalid_replicates: int) -> Callable[[tuple[SubjectPrediction, ...]], MetricValue]:
    calls = 0

    def metric(rows: tuple[SubjectPrediction, ...]) -> MetricValue:
        nonlocal calls
        calls += 1
        if 1 < calls <= invalid_replicates + 1:
            return MetricValue.unavailable("undefined")
        return MetricValue.available(1.0)

    return metric


def test_bootstrap_availability_changes_exactly_at_ceil_ninety_five_percent() -> None:
    table = (
        _row(MethodId.MMD, "a", 0, 0),
        _row(MethodId.MMD, "b", 1, 1),
        _row(MethodId.MMD, "c", 2, 2),
    )
    available = bootstrap_metrics(
        table, {"accuracy": _threshold_metric(1)}, replicates=20, seed=1
    )[0]
    unavailable = bootstrap_metrics(
        table, {"accuracy": _threshold_metric(2)}, replicates=20, seed=1
    )[0]
    assert (available.successful, available.invalid, available.status) == (19, 1, ValueStatus.AVAILABLE)
    assert (unavailable.successful, unavailable.invalid) == (18, 2)
    assert unavailable.reason == "insufficient_valid_bootstrap_replicates"


def test_zero_discordance_is_available_not_an_error_or_unavailable_value() -> None:
    reference = tuple(
        _row(MethodId.PROTOTYPE_PSEUDO, subject, truth, truth)
        for subject, truth in (("a", 0), ("b", 1), ("c", 2))
    )
    comparator = tuple(
        _row(MethodId.CORAL, row.subject_hash, row.true_label, row.true_label)
        for row in reference
    )
    result = exact_mcnemar(reference, comparator)
    assert result.status is ValueStatus.AVAILABLE
    assert result.raw_p_value == 1.0
    assert result.reason is None
    assert result.note_code == "no_discordant_pairs"


def test_incompatible_subjects_make_every_paired_result_unavailable_without_intersection() -> None:
    reference = tuple(
        _row(MethodId.PROTOTYPE_PSEUDO, subject, truth, truth)
        for subject, truth in (("a", 0), ("b", 1), ("c", 2))
    )
    comparator = (
        _row(MethodId.CORAL, "a", 0, 0),
        _row(MethodId.CORAL, "b", 2, 1),
        _row(MethodId.CORAL, "different", 2, 2),
    )
    metric_calls = 0

    def must_not_run(rows: tuple[SubjectPrediction, ...]) -> MetricValue:
        nonlocal metric_calls
        metric_calls += 1
        return MetricValue.available(1.0)

    mcnemar = exact_mcnemar(reference, comparator)
    paired = paired_bootstrap(
        reference,
        comparator,
        {"accuracy": must_not_run, "macro_f1": must_not_run},
        replicates=10,
        seed=4,
    )
    assert mcnemar.status is ValueStatus.UNAVAILABLE
    assert mcnemar.reason == "incompatible_subjects"
    assert mcnemar.n_subjects == 0
    assert all(result.status is ValueStatus.UNAVAILABLE for result in paired)
    assert all(result.reason == "incompatible_subjects" for result in paired)
    assert all((result.successful, result.invalid) == (0, 10) for result in paired)
    assert metric_calls == 0


def test_holm_retains_unavailable_slot_and_only_six_prototype_comparators() -> None:
    rows = []
    for index, method in enumerate(COMPARATOR_METHODS):
        available = method is not MethodId.CDAN
        rows.append(PairedDifference(
            method, "accuracy", "prototype_pseudo-comparator",
            0.1 if available else None, 0.95, "percentile",
            0.0 if available else None, 0.2 if available else None,
            "centered_plus_one", 0.05 * (index + 1) if available else None,
            17, 100, 100 if available else 0, 0 if available else 100,
            ValueStatus.AVAILABLE if available else ValueStatus.UNAVAILABLE,
            None if available else "observed_metric_unavailable",
        ))
    adjusted = adjust_holm(rows)
    assert len(adjusted) == 6
    assert tuple(row.comparator_method for row in adjusted) == COMPARATOR_METHODS
    unavailable = adjusted[COMPARATOR_METHODS.index(MethodId.CDAN)]
    assert unavailable.family_size == 6
    assert unavailable.raw_p_value is unavailable.adjusted_p_value is None
    assert MethodId.PROTOTYPE_PSEUDO not in {row.comparator_method for row in adjusted}
