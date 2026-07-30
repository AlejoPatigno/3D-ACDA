"""Source validation and explicitly isolated target monitoring."""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score

from pada3dacb.losses import CorePADA3DACBLoss
from pada3dacb.training.runtime import move_batch, require_batch_keys, validate_nonempty_loader

TARGET_MONITORING_LABEL = "MONITORING ONLY — NOT A TRAINING LOSS"


@torch.no_grad()
def evaluate_labeled_loader(
    model: torch.nn.Module,
    loader: Any,
    roi_masks: torch.Tensor,
    device: torch.device,
    *,
    loss_fn: CorePADA3DACBLoss | None = None,
    stage: str = "full",
    namespace: str = "source_validation",
) -> dict[str, float | str]:
    validate_nonempty_loader(loader, f"{namespace}_loader")
    was_training = model.training
    model.eval()
    labels: list[torch.Tensor] = []
    predictions: list[torch.Tensor] = []
    losses: list[float] = []
    try:
        for raw_batch in loader:
            require_batch_keys(raw_batch, ["x", "y"])
            batch = move_batch(raw_batch, device)
            output = model(batch["x"], roi_masks)
            prediction = output.concept_probabilities.argmax(dim=-1)
            labels.append(batch["y"].detach().cpu())
            predictions.append(prediction.detach().cpu())
            if loss_fn is not None and {"c_target", "g_bar"}.issubset(batch):
                result = loss_fn(output, batch["y"], batch["c_target"], batch["g_bar"], stage=stage)
                losses.append(float(result.total.detach().cpu()))
    finally:
        model.train(was_training)
    y_true = torch.cat(labels).numpy()
    y_pred = torch.cat(predictions).numpy()
    metrics: dict[str, float | str] = {
        f"{namespace}/accuracy": float(accuracy_score(y_true, y_pred)),
        f"{namespace}/macro_f1": float(
            f1_score(y_true, y_pred, labels=np.arange(3), average="macro", zero_division=0)
        ),
    }
    if losses:
        metrics[f"{namespace}/loss"] = float(np.mean(losses))
    if namespace == "target_monitoring":
        metrics["target_monitoring/label"] = TARGET_MONITORING_LABEL
    return metrics
