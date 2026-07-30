"""Canonical weighted concept/Jacobian anatomical consistency objective."""

from __future__ import annotations

import torch
from torch import nn

from pada3dacb.exceptions import LossContractError
from pada3dacb.losses.outputs import validate_pair


class AnatomicalConsistencyLoss(nn.Module):
    def __init__(self, num_rois: int, roi_weights: torch.Tensor | None = None):
        super().__init__()
        if num_rois <= 0:
            raise LossContractError("num_rois must be positive.")
        if roi_weights is None:
            roi_weights = torch.ones(num_rois, dtype=torch.float32) / num_rois
        if roi_weights.ndim != 1 or roi_weights.shape[0] != num_rois:
            raise LossContractError(f"roi_weights must have shape ({num_rois},).")
        if not torch.isfinite(roi_weights).all():
            raise LossContractError("roi_weights must be finite.")
        self.num_rois = num_rois
        self.register_buffer("roi_weights", roi_weights.detach().clone().float())

    def forward(self, concepts: torch.Tensor, g_bar: torch.Tensor) -> torch.Tensor:
        validate_pair(concepts, g_bar, "concepts", "g_bar")
        if concepts.shape[1] != self.num_rois:
            raise LossContractError(f"Expected K={self.num_rois}, got K={concepts.shape[1]}.")
        if self.roi_weights.device != concepts.device:
            raise LossContractError("roi_weights and loss inputs must be on the same device.")
        residuals = (concepts - g_bar).square()
        return (residuals * self.roi_weights.to(dtype=concepts.dtype).unsqueeze(0)).mean()
