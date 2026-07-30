"""Canonical source classification objective."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as functional

from pada3dacb.exceptions import LossContractError
from pada3dacb.losses.outputs import validate_finite_tensor


class ClassificationLoss(nn.Module):
    def __init__(self, label_smoothing: float = 0.0):
        super().__init__()
        if not 0 <= label_smoothing < 1:
            raise LossContractError("label_smoothing must be in [0, 1).")
        self.label_smoothing = label_smoothing

    def forward(self, logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        validate_finite_tensor(logits, "logits", 2)
        if labels.ndim != 1 or labels.shape[0] != logits.shape[0] or labels.dtype != torch.long:
            raise LossContractError("labels must be long with shape (B,) matching logits.")
        if labels.device != logits.device:
            raise LossContractError("labels and logits must be on the same device.")
        if labels.numel() and ((labels < 0).any() or (labels >= logits.shape[1]).any()):
            raise LossContractError("labels contain an invalid class index.")
        return functional.cross_entropy(logits, labels, label_smoothing=self.label_smoothing)
