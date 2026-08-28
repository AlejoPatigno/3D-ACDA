from __future__ import annotations

import hashlib

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
    SubjectPrediction,
    ValueStatus,
    canonical_json,
)
from acda3d.evaluation.tables import bind_subject_table_hash

TRUTHS = (0, 0, 1, 1, 2, 2)


def _table(method: MethodId, predictions: tuple[int, ...]) -> tuple[SubjectPrediction, ...]:
    rows = []
    for index, (truth, predicted) in enumerate(zip(TRUTHS, predictions, strict=True)):
        probabilities = [0.05, 0.05, 0.05]
        probabilities[predicted] = 0.9
        rows.append(SubjectPrediction(
            method, Direction.ADNI_TO_OASIS, CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,
            f"subject-{index}", truth, tuple(probabilities), 2, 1,
            (f"{index + 1:064x}",),
        ))
    return tuple(rows)


def _accuracy(rows: tuple[SubjectPrediction, ...]) -> MetricValue:
    correct = sum(row.predicted_label == row.true_label for row in rows)
    return MetricValue.available(correct / len(rows))


def test_canonical_tables_drive_complete_metrics_confusion_and_bootstrap() -> None:
    table = _table(MethodId.PROTOTYPE_PSEUDO, (0, 1, 1, 1, 2, 0))
    metrics = compute_metrics(table)
    assert metrics.subject_count == 6
    assert len(metrics.aggregate_metrics) == 12
    assert len(metrics.per_class_metrics) == 24
    assert all(value.status is ValueStatus.AVAILABLE for value in metrics.aggregate_metrics.values())

    confusion = compute_confusion(table)
    assert sum(sum(row) for row in confusion.counts) == 6
    assert tuple(row.true_label for row in table) == TRUTHS
    intervals = bootstrap_metrics(table, {"accuracy": _accuracy}, replicates=100, seed=19)
    assert intervals[0].requested == 100
    assert intervals[0].successful + intervals[0].invalid == 100


def test_pairing_orientation_mcnemar_and_six_slot_holm_are_regression_protected() -> None:
    reference = _table(MethodId.PROTOTYPE_PSEUDO, (0, 0, 1, 1, 2, 2))
    paired_rows = []
    mcnemar_rows = []
    for offset, comparator in enumerate(COMPARATOR_METHODS):
        predictions = tuple((truth + (index == offset % len(TRUTHS))) % 3 for index, truth in enumerate(TRUTHS))
        candidate = _table(comparator, predictions)
        paired = paired_bootstrap(
            reference, candidate, {"accuracy": _accuracy}, replicates=100, seed=23
        )[0]
        assert paired.orientation == "prototype_pseudo-comparator"
        paired_rows.append(paired)
        mcnemar_rows.append(exact_mcnemar(reference, candidate))
    adjusted_paired = adjust_holm(tuple(paired_rows))
    adjusted_mcnemar = adjust_holm(tuple(mcnemar_rows))
    assert tuple(row.comparator_method for row in adjusted_paired) == COMPARATOR_METHODS
    assert tuple(row.comparator_method for row in adjusted_mcnemar) == COMPARATOR_METHODS
    assert all(row.family_size == 6 for row in (*adjusted_paired, *adjusted_mcnemar))


def test_publication_rows_bind_exact_serialized_subject_table_hash() -> None:
    table = _table(MethodId.MMD, (0, 0, 1, 2, 2, 2))
    serialized = canonical_json(table).encode()
    digest = hashlib.sha256(serialized).hexdigest()
    rows = bind_subject_table_hash(({"metric": "accuracy", "value": 5 / 6},), digest)
    assert rows == ({"metric": "accuracy", "value": 5 / 6, "subject_table_sha256": digest},)
    contradictory_cache = hashlib.sha256(b"cached-fold-summary").hexdigest()
    assert contradictory_cache != rows[0]["subject_table_sha256"]
