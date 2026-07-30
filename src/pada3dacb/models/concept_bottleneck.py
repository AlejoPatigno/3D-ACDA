"""Active per-ROI MLP concept bottleneck from the training notebook."""

from __future__ import annotations

import torch
from torch import nn

from pada3dacb.exceptions import ModelContractError


class ConceptBottleneck(nn.Module):
    def __init__(
        self,
        num_rois: int,
        token_dim: int,
        num_classes: int = 3,
        hidden_dim: int = 64,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.num_rois = num_rois
        self.token_dim = token_dim
        self.concept_mlps = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(token_dim, hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.Linear(hidden_dim, 1),
                )
                for _ in range(num_rois)
            ]
        )
        self.cbm_head = nn.Linear(num_rois, num_classes)

    def forward(self, tokens: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if tokens.ndim != 3 or tuple(tokens.shape[1:]) != (self.num_rois, self.token_dim):
            raise ModelContractError(
                "Concept input must have shape "
                f"(B,{self.num_rois},{self.token_dim}), got {tuple(tokens.shape)}."
            )
        raw = torch.cat(
            [predictor(tokens[:, index, :]) for index, predictor in enumerate(self.concept_mlps)],
            dim=1,
        )
        concepts = torch.sigmoid(raw)
        return concepts, self.cbm_head(concepts)
