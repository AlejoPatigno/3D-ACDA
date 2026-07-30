"""Canonical asymmetric KL consistency between both prediction branches."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as functional

from pada3dacb.losses.outputs import validate_pair


class PredictionConsistencyLoss(nn.Module):
    def forward(self, latent_logits: torch.Tensor, concept_logits: torch.Tensor) -> torch.Tensor:
        validate_pair(latent_logits, concept_logits, "latent_logits", "concept_logits")
        log_latent = functional.log_softmax(latent_logits, dim=-1)
        concept_probabilities = functional.softmax(concept_logits, dim=-1)
        return functional.kl_div(log_latent, concept_probabilities, reduction="batchmean")
