"""Canonical concept-target mean squared error."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as functional

from pada3dacb.losses.outputs import validate_pair


class ConceptSupervisionLoss(nn.Module):
    def forward(self, concepts: torch.Tensor, concept_targets: torch.Tensor) -> torch.Tensor:
        validate_pair(concepts, concept_targets, "concepts", "concept_targets")
        return functional.mse_loss(concepts, concept_targets)
