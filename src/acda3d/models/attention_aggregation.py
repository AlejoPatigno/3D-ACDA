"""Soft attention over non-contextual ROI tokens."""

from __future__ import annotations

import torch
from torch import nn

from acda3d.exceptions import ModelContractError


class AttentionAggregator(nn.Module):
    def __init__(self, token_dim: int):
        super().__init__()
        self.token_dim = token_dim
        self.W_a = nn.Linear(token_dim, token_dim, bias=True)
        self.v = nn.Linear(token_dim, 1, bias=False)

    def forward(self, tokens: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if tokens.ndim != 3 or tokens.shape[-1] != self.token_dim:
            raise ModelContractError(
                f"Attention input must have shape (B,K,{self.token_dim}), got {tuple(tokens.shape)}."
            )
        scores = self.v(torch.tanh(self.W_a(tokens))).squeeze(-1)
        attention = torch.softmax(scores, dim=-1)
        embedding = (attention.unsqueeze(-1) * tokens).sum(dim=1)
        return embedding, attention
