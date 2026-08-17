"""Deterministic subject-level prediction export for approved checkpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score

from pada3dacb.data.records import CLASS_ORDER
from pada3dacb.exceptions import ExperimentValidationError
from pada3dacb.training.runtime import move_batch, require_batch_keys

PREDICTION_COLUMNS = (
    "subject_hash", "cohort", "true_label", "true_label_index", "predicted_label",
    "predicted_label_index", "probability_CN", "probability_MCI", "probability_AD",
    "direction", "method", "model", "fold", "seed", "checkpoint_name",
    "checkpoint_epoch", "split", "experiment_hash",
)
# Minimal task-scoped publication schema. Evaluation labels belong to the
# separate label-bearing frame used only for evaluation.
BINARY_PREDICTION_COLUMNS = (
    "subject_hash", "cohort", "prob_cn", "prob_impaired", "predicted_label",
)
BINARY_EVALUATION_COLUMNS = (
    "subject_hash", "cohort", "true_label", "true_label_index", "predicted_label",
    "predicted_label_index", "prob_cn", "prob_impaired", "direction", "method", "model",
    "fold", "seed", "checkpoint_name", "checkpoint_epoch", "split", "experiment_hash",
)

ABLATION_PREDICTION_COLUMNS = (
    "schema_version", "subject_id", "subject_hash", "cohort", "dataset_role",
    "target_labels_present", "target_label_usage", "direction", "method", "model",
    "fold", "seed", "checkpoint_name", "checkpoint_epoch", "split",
    "experiment_hash", "predicted_class_z", "predicted_class_c",
)


def validate_ablation_prediction_records(records: list[dict[str, Any]]) -> None:
    """Validate Phase 17 subject records without permitting target-adaptation labels."""
    for record in records:
        missing = set(ABLATION_PREDICTION_COLUMNS) - set(record)
        if missing:
            raise ExperimentValidationError(
                f"Ablation prediction is missing columns: {sorted(missing)}."
            )
        if record["method"] != "ablation" or record["schema_version"] != "phase17.prediction.v1":
            raise ExperimentValidationError("Ablation prediction has an invalid method or schema.")
        if record["dataset_role"] == "target_adaptation":
            if record["target_labels_present"] or record["target_label_usage"] != "forbidden":
                raise ExperimentValidationError(
                    "Target-adaptation predictions must not contain target labels."
                )
        elif record["dataset_role"] == "target_evaluation" and (
            not record["target_labels_present"]
            or record["target_label_usage"] != "monitoring_only"
        ):
            raise ExperimentValidationError("Target-evaluation predictions must be monitoring-only.")


def export_ablation_predictions(records: list[dict[str, Any]], path: str | Path) -> Path:
    """Atomically publish a Phase 17 prediction JSONL only for a completed run."""
    validate_ablation_prediction_records(records)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text("".join(json_line(record) for record in records), encoding="utf-8")
    temporary.replace(target)
    return target


def json_line(record: dict[str, Any]) -> str:
    import json

    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


@torch.no_grad()
def collect_predictions(
    model: torch.nn.Module,
    loader: Any,
    roi_masks: torch.Tensor,
    device: torch.device,
    *,
    direction: str,
    fold: int,
    seed: int,
    checkpoint_name: str,
    checkpoint_epoch: int,
    split: str,
    experiment_hash: str,
    method: str = "source_only",
    model_name: str = "PADA-3DACB Source-Only",
) -> pd.DataFrame:
    was_training = model.training
    model.eval()
    rows: list[dict[str, Any]] = []
    try:
        for raw_batch in loader:
            require_batch_keys(raw_batch, ["x", "y", "subject_hash", "cohort"])
            batch = move_batch(raw_batch, device)
            output = model(batch["x"], roi_masks)
            probabilities = output.concept_probabilities.detach().cpu()
            true_indices = batch["y"].detach().cpu()
            predicted_indices = probabilities.argmax(dim=-1)
            for index in range(probabilities.shape[0]):
                true_index = int(true_indices[index])
                predicted_index = int(predicted_indices[index])
                rows.append(
                    {
                        "subject_hash": str(raw_batch["subject_hash"][index]),
                        "cohort": str(raw_batch["cohort"][index]),
                        "true_label": CLASS_ORDER[true_index],
                        "true_label_index": true_index,
                        "predicted_label": CLASS_ORDER[predicted_index],
                        "predicted_label_index": predicted_index,
                        "probability_CN": float(probabilities[index, 0]),
                        "probability_MCI": float(probabilities[index, 1]),
                        "probability_AD": float(probabilities[index, 2]),
                        "direction": direction,
                        "method": method,
                        "model": model_name,
                        "fold": fold,
                        "seed": seed,
                        "checkpoint_name": checkpoint_name,
                        "checkpoint_epoch": checkpoint_epoch,
                        "split": split,
                        "experiment_hash": experiment_hash,
                    }
                )
    finally:
        model.train(was_training)
    frame = pd.DataFrame(rows, columns=PREDICTION_COLUMNS)
    validate_prediction_frame(frame)
    return frame.sort_values(["cohort", "subject_hash"]).reset_index(drop=True)


def validate_prediction_frame(frame: pd.DataFrame) -> None:
    missing = set(PREDICTION_COLUMNS) - set(frame.columns)
    if missing:
        raise ExperimentValidationError(f"Prediction export is missing columns: {sorted(missing)}.")
    if frame.empty:
        raise ExperimentValidationError("Prediction export cannot be empty.")
    identity = ["subject_hash", "checkpoint_name", "split"]
    if frame.duplicated(identity).any():
        raise ExperimentValidationError("Prediction export contains duplicate subjects.")
    probabilities = frame[["probability_CN", "probability_MCI", "probability_AD"]].to_numpy(float)
    if not np.isfinite(probabilities).all() or not np.allclose(probabilities.sum(1), 1, atol=1e-6):
        raise ExperimentValidationError("Prediction probabilities must be finite and sum to one.")


def validate_binary_prediction_frame(frame: pd.DataFrame) -> None:
    """Validate the minimal task-scoped publication dataframe."""
    from pada3dacb.binary import BinaryLabelError, validate_binary_prediction

    allowed = set(BINARY_PREDICTION_COLUMNS) | {"original_label_name"}
    missing = set(BINARY_PREDICTION_COLUMNS) - set(frame.columns)
    forbidden = {"probability_MCI", "probability_AD", "prob_mci", "prob_ad", "true_label", "true_label_index"}
    if missing or forbidden.intersection(frame.columns) or set(frame.columns) - allowed:
        raise ExperimentValidationError(f"Binary prediction export has incompatible columns: {sorted(missing)}")
    if frame.empty:
        raise ExperimentValidationError("Binary prediction export cannot be empty.")
    if frame.duplicated(["subject_hash"]).any():
        raise ExperimentValidationError("Binary prediction export contains duplicate subjects.")
    for row in frame.to_dict("records"):
        try:
            parsed = validate_binary_prediction(row)
        except BinaryLabelError as error:
            raise ExperimentValidationError(str(error)) from error
        if int(row["predicted_label"]) != parsed.predicted_label:
            raise ExperimentValidationError("Binary prediction predicted_label does not match lower-index argmax.")


def validate_binary_evaluation_frame(frame: pd.DataFrame) -> None:
    """Validate the label-bearing frame used only for binary evaluation."""
    from pada3dacb.binary import BinaryLabelError, validate_binary_prediction

    missing = set(BINARY_EVALUATION_COLUMNS) - set(frame.columns)
    forbidden = {"probability_MCI", "probability_AD", "prob_mci", "prob_ad"}
    if missing or forbidden.intersection(frame.columns):
        raise ExperimentValidationError(f"Binary evaluation frame has incompatible columns: {sorted(missing)}")
    if frame.empty:
        raise ExperimentValidationError("Binary evaluation frame cannot be empty.")
    if frame.duplicated(["subject_hash", "checkpoint_name", "split"]).any():
        raise ExperimentValidationError("Binary evaluation frame contains duplicate subjects.")
    for row in frame.to_dict("records"):
        if row["true_label_index"] not in (0, 1) or row["true_label"] != ("CN", "Impaired")[int(row["true_label_index"])]:
            raise ExperimentValidationError("Binary evaluation labels do not match the fixed class order.")
        try:
            parsed = validate_binary_prediction(row)
        except BinaryLabelError as error:
            raise ExperimentValidationError(str(error)) from error
        if int(row["predicted_label_index"]) != parsed.predicted_label or row["predicted_label"] != ("CN", "Impaired")[parsed.predicted_label]:
            raise ExperimentValidationError("Binary evaluation prediction does not match the probability argmax.")


@torch.no_grad()
def collect_binary_predictions(
    model: torch.nn.Module,
    loader: Any,
    roi_masks: torch.Tensor,
    device: torch.device,
    *,
    direction: str,
    fold: int,
    seed: int,
    checkpoint_name: str,
    checkpoint_epoch: int,
    split: str,
    experiment_hash: str,
    method: str = "source_only",
    model_name: str = "PADA-3DACB",
) -> pd.DataFrame:
    """Collect binary task-head probabilities with fixed CN/Impaired semantics."""
    was_training = model.training
    model.eval()
    rows: list[dict[str, Any]] = []
    try:
        for raw_batch in loader:
            require_batch_keys(raw_batch, ["x", "y", "subject_hash", "cohort"])
            batch = move_batch(raw_batch, device)
            output = model(batch["x"], roi_masks)
            probabilities = output.latent_probabilities.detach().cpu()
            labels = batch["y"].detach().cpu()
            for index in range(probabilities.shape[0]):
                predicted = int(probabilities[index].argmax().item())
                rows.append({
                    "subject_hash": str(raw_batch["subject_hash"][index]),
                    "cohort": str(raw_batch["cohort"][index]),
                    "true_label": ("CN", "Impaired")[int(labels[index])],
                    "true_label_index": int(labels[index]),
                    "predicted_label": ("CN", "Impaired")[predicted],
                    "predicted_label_index": predicted,
                    "prob_cn": float(probabilities[index, 0]),
                    "prob_impaired": float(probabilities[index, 1]),
                    "direction": direction, "method": method, "model": model_name,
                    "fold": fold, "seed": seed, "checkpoint_name": checkpoint_name,
                    "checkpoint_epoch": checkpoint_epoch, "split": split,
                    "experiment_hash": experiment_hash,
                })
    finally:
        model.train(was_training)
    frame = pd.DataFrame(rows, columns=BINARY_EVALUATION_COLUMNS)
    validate_binary_evaluation_frame(frame)
    return frame.sort_values(["cohort", "subject_hash"]).reset_index(drop=True)


def binary_prediction_metrics(frame: pd.DataFrame) -> dict[str, dict[str, object]]:
    from pada3dacb.binary import evaluate_binary_predictions

    validate_binary_evaluation_frame(frame)
    rows = [
        {"true_label": int(row["true_label_index"]), "prob_cn": row["prob_cn"], "prob_impaired": row["prob_impaired"]}
        for row in frame.to_dict("records")
    ]
    return evaluate_binary_predictions(rows).metrics


def export_predictions(frame: pd.DataFrame, path: str | Path) -> Path:
    validate_prediction_frame(frame)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    return target


def prediction_metrics(frame: pd.DataFrame) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(frame["true_label_index"], frame["predicted_label_index"])),
        "macro_f1": float(
            f1_score(
                frame["true_label_index"],
                frame["predicted_label_index"],
                labels=np.arange(3),
                average="macro",
                zero_division=0,
            )
        ),
    }


# Strict task-scoped export.  The historical PREDICTION_COLUMNS contract above
# remains the three-class Phase 15 API.
TASK_BINARY_PREDICTION_FIELDS = frozenset({
    "subject_hash", "cohort", "prob_cn", "prob_impaired", "predicted_label",
    "original_label_name",
})
TASK_BINARY_REQUIRED_FIELDS = frozenset({
    "subject_hash", "cohort", "prob_cn", "prob_impaired", "predicted_label",
})
TASK_BINARY_FORBIDDEN_FIELDS = frozenset({
    "prob_mci", "prob_ad", "probability_MCI", "probability_AD",
    "true_label", "true_label_index", "predicted_label_index",
})


def validate_task_scoped_binary_prediction_records(records: list[dict[str, Any]]) -> None:
    """Validate the minimal binary prediction export schema.

    Ground-truth labels belong to the evaluation input, not to this prediction
    artifact.  ``original_label_name`` is retained only as optional provenance.
    """
    from pada3dacb.binary import BinaryLabelError, BinaryPrediction
    if not records:
        raise ExperimentValidationError("Binary prediction export cannot be empty.")
    for record in records:
        keys = set(record)
        if keys & TASK_BINARY_FORBIDDEN_FIELDS:
            raise ExperimentValidationError("Binary prediction export contains historical or evaluation-only fields.")
        if not keys >= TASK_BINARY_REQUIRED_FIELDS or not keys <= TASK_BINARY_PREDICTION_FIELDS:
            raise ExperimentValidationError("Binary prediction export has incompatible fields.")
        if not isinstance(record["subject_hash"], str) or not record["subject_hash"]:
            raise ExperimentValidationError("Binary prediction subject_hash is required.")
        if not isinstance(record["cohort"], str) or not record["cohort"]:
            raise ExperimentValidationError("Binary prediction cohort is required.")
        try:
            parsed = BinaryPrediction.from_mapping(record)
        except BinaryLabelError as error:
            raise ExperimentValidationError(str(error)) from error
        if int(record["predicted_label"]) != parsed.predicted_label:
            raise ExperimentValidationError("Binary prediction predicted_label does not match lower-index argmax.")
    subjects = [record["subject_hash"] for record in records]
    if len(subjects) != len(set(subjects)):
        raise ExperimentValidationError("Binary prediction export contains duplicate subjects.")


def export_task_scoped_binary_predictions(records: list[dict[str, Any]], path: str | Path) -> Path:
    """Write a deterministic JSONL task-scoped binary prediction artifact."""
    validate_task_scoped_binary_prediction_records(records)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text("".join(json_line(record) for record in records), encoding="utf-8")
    temporary.replace(target)
    return target


def task_scoped_binary_prediction_from_logits(
    logits: torch.Tensor, *, subject_hash: str, cohort: str, original_label_name: str | None = None,
) -> dict[str, Any]:
    from pada3dacb.binary import binary_prediction_from_logits
    payload = binary_prediction_from_logits(logits)
    payload.update({"subject_hash": subject_hash, "cohort": cohort})
    if original_label_name is not None:
        payload["original_label_name"] = original_label_name
    validate_task_scoped_binary_prediction_records([payload])
    return payload