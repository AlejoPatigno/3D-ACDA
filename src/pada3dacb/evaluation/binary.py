"""Compatibility import surface for Phase 18B prediction/evaluation schemas."""

from collections.abc import Mapping, Sequence
from typing import Any

from pada3dacb.binary import (
    BINARY_CLASS_ORDER,
    BinaryEvaluationResult,
    BinaryLabelError,
    BinaryPrediction,
    evaluate_binary_predictions,
    validate_binary_prediction,
)

__all__ = [
    "BINARY_CLASS_ORDER", "BinaryEvaluationResult", "BinaryLabelError", "BinaryPrediction",
    "evaluate_binary_predictions", "validate_binary_prediction", "BINARY_TASK_ID",
        "BINARY_REQUIRED_METRICS", "validate_binary_task_metadata", "evaluate_binary_rows",
        "binary_evaluation_payload",
]


BINARY_TASK_ID = "cn_vs_impaired"
BINARY_TASK_HASH_PREFIX = "phase18b.binary.task.v1"
BINARY_REQUIRED_METRICS = (
    "accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "sensitivity",
    "specificity", "mcc", "cohen_kappa", "roc_auc", "pr_auc", "log_loss", "brier_score",
)


def validate_binary_task_metadata(metadata: Mapping[str, Any]) -> None:
    if not isinstance(metadata, Mapping):
        raise BinaryLabelError("binary task metadata must be a mapping")
    task = metadata.get("task", metadata.get("task_id"))
    if task != BINARY_TASK_ID:
        raise BinaryLabelError("task-scoped evaluation requires cn_vs_impaired")
    if metadata.get("class_order") not in (None, list(BINARY_CLASS_ORDER), tuple(BINARY_CLASS_ORDER)):
        raise BinaryLabelError("binary evaluation class order must be CN, Impaired")
    historical = {"prob_mci", "prob_ad", "probability_MCI", "probability_AD"}
    if historical.intersection(metadata):
        raise BinaryLabelError("historical three-class fields are not accepted by binary evaluation")


def evaluate_binary_rows(rows: Sequence[Mapping[str, Any]], *, task: str = BINARY_TASK_ID) -> BinaryEvaluationResult:
    if task != BINARY_TASK_ID:
        raise BinaryLabelError("task-scoped evaluation requires cn_vs_impaired")
    result = evaluate_binary_predictions(rows)
    missing = [name for name in BINARY_REQUIRED_METRICS if name not in result.metrics]
    if missing:
        raise BinaryLabelError(f"binary metric set is incomplete: {missing}")
    return result


def binary_evaluation_payload(rows: Sequence[Mapping[str, Any]], *, task_hash: str | None = None) -> dict[str, Any]:
    result = evaluate_binary_rows(rows)
    return {
        "task": BINARY_TASK_ID,
        "class_order": list(BINARY_CLASS_ORDER),
        "positive_class": "Impaired",
        "task_hash": task_hash,
        "confusion_matrix": [list(row) for row in result.confusion_matrix],
        "metrics": result.metrics,
        "real_run": False,
        "validate_only": True,
    }
