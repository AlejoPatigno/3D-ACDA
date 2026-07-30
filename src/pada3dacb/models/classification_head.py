"""Canonical linear latent classification head."""

from __future__ import annotations

import torch
from torch import nn


class ClassificationHead(nn.Module):
    def __init__(self, token_dim: int, num_classes: int = 3):
        super().__init__()
        self.fc = nn.Linear(token_dim, num_classes)

    def forward(self, embedding: torch.Tensor) -> torch.Tensor:
        return self.fc(embedding)
