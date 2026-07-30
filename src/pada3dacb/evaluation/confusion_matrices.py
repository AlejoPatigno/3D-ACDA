"""Fixed-order count and nullable row-normalized confusion matrices."""
from __future__ import annotations

from collections.abc import Sequence

from sklearn.metrics import confusion_matrix

from .schemas import ConfusionResult, MetricValue, SubjectPrediction


def _validate_table(table: Sequence[SubjectPrediction]) -> None:
    if not table:
        return
    first = table[0]
    identity = (first.method_id, first.direction, first.checkpoint_policy)
    if any((row.method_id, row.direction, row.checkpoint_policy) != identity for row in table[1:]):
        raise ValueError("confusion table must be homogeneous")
    subjects = [row.subject_hash for row in table]
    if len(subjects) != len(set(subjects)):
        raise ValueError("confusion table must contain one row per subject")


def compute_confusion(table: Sequence[SubjectPrediction]) -> ConfusionResult:
    """Derive both matrix forms from one final subject table."""
    rows = tuple(table)
    _validate_table(rows)
    if rows:
        matrix = confusion_matrix(
            [row.true_label for row in rows],
            [row.predicted_label for row in rows],
            labels=[0, 1, 2],
        )
        counts = tuple(tuple(int(value) for value in row) for row in matrix.tolist())
    else:
        counts = ((0, 0, 0),) * 3
    normalized = []
    statuses = []
    for row in counts:
        support = sum(row)
        if support == 0:
            normalized.append((None, None, None))
            statuses.append(MetricValue.unavailable("zero_true_support"))
        else:
            normalized.append(tuple(value / support for value in row))
            statuses.append(MetricValue.available(support))
    return ConfusionResult(counts, tuple(normalized), tuple(statuses))
