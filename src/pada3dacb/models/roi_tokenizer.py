"""Canonical pre-normalized ROI masked pooling and token projection."""

from __future__ import annotations

import torch
from torch import nn

from pada3dacb.exceptions import ModelContractError


class ROITokenizer(nn.Module):
    """Pool feature-grid ROIs in stable order and add learned ROI embeddings."""

    def __init__(self, num_rois: int, feature_dim: int, token_dim: int):
        super().__init__()
        if min(num_rois, feature_dim, token_dim) <= 0:
            raise ModelContractError("Tokenizer dimensions must be positive.")
        self.num_rois = num_rois
        self.feature_dim = feature_dim
        self.token_dim = token_dim
        self.proj = nn.Linear(feature_dim, token_dim)
        self.roi_emb = nn.Embedding(num_rois, token_dim)

    def forward(self, features: torch.Tensor, roi_masks: torch.Tensor) -> torch.Tensor:
        if features.ndim != 5 or features.shape[1] != self.feature_dim:
            raise ModelContractError(
                f"Features must have shape (B,{self.feature_dim},h,w,d), got {tuple(features.shape)}."
            )
        if roi_masks.ndim != 4 or roi_masks.shape[0] != self.num_rois:
            raise ModelContractError(
                f"ROI masks must have shape ({self.num_rois},h,w,d), got {tuple(roi_masks.shape)}."
            )
        if tuple(roi_masks.shape[1:]) != tuple(features.shape[2:]):
            raise ModelContractError(
                "Canonical ROI masks must already match the encoder feature grid; "
                f"got {tuple(roi_masks.shape[1:])} and {tuple(features.shape[2:])}."
            )
        if roi_masks.device != features.device:
            raise ModelContractError("ROI masks and features must be on the same device.")
        masks = roi_masks.to(dtype=features.dtype)
        if not torch.isfinite(masks).all():
            raise ModelContractError("ROI masks must contain only finite values.")
        if (masks.reshape(self.num_rois, -1).abs().sum(dim=1) == 0).any():
            raise ModelContractError("Every ROI mask must be non-empty.")
        flat_features = features.reshape(features.shape[0], self.feature_dim, -1)
        pooled = torch.einsum("bcv,kv->bkc", flat_features, masks.reshape(self.num_rois, -1))
        indices = torch.arange(self.num_rois, device=features.device)
        return self.proj(pooled) + self.roi_emb(indices).unsqueeze(0)
