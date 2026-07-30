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
