"""Fixed-order count and nullable row-normalized confusion matrices."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

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


def compute_binary_confusion(rows: Sequence[dict]) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return true-row/predicted-column CN/Impaired counts."""
    matrix = [[0, 0], [0, 0]]
    for row in rows:
        true_label = row.get("true_label")
        if isinstance(true_label, bool) or true_label not in (0, 1):
            raise ValueError("binary true_label must be 0 or 1")
        from acda3d.binary import BinaryPrediction
        prediction = BinaryPrediction.from_mapping(row)
        matrix[int(true_label)][prediction.predicted_label] += 1
    return (tuple(matrix[0]), tuple(matrix[1]))


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


@dataclass(frozen=True)
class BinaryConfusionResult:
    """Fixed CN/Impaired confusion counts and row-normalized values."""
    counts: tuple[tuple[int, int], tuple[int, int]]
    normalized: tuple[tuple[float | None, float | None], tuple[float | None, float | None]]
    reasons: tuple[str | None, str | None]
    class_order: tuple[str, str] = ("CN", "Impaired")

    @property
    def subject_count(self) -> int:
        return sum(value for row in self.counts for value in row)

    def to_dict(self) -> dict[str, object]:
        return {
            "class_order": list(self.class_order),
            "positive_class": "Impaired",
            "counts": [list(row) for row in self.counts],
            "normalized": [list(row) for row in self.normalized],
            "reasons": list(self.reasons),
        }


def compute_task_binary_confusion(rows: Sequence[dict]) -> BinaryConfusionResult:
    counts = compute_binary_confusion(rows)
    normalized = []
    reasons = []
    for row in counts:
        support = sum(row)
        if support == 0:
            normalized.append((None, None))
            reasons.append("zero_true_support")
        else:
            normalized.append((row[0] / support, row[1] / support))
            reasons.append(None)
    return BinaryConfusionResult(counts, (tuple(normalized[0]), tuple(normalized[1])), tuple(reasons))

# Descriptive alias used by task-scoped report callers.
compute_binary_task_confusion = compute_task_binary_confusion


compute_binary_confusion_matrix = compute_task_binary_confusion
