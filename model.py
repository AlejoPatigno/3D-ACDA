
"""
model_patch_concept.py
======================
Drop-in replacement for the ConceptBottleneck class in model.py.

This patch is needed because the current implementation uses a single shared
linear scorer across ROIs plus a per-ROI bias, whereas the mathematics in
Section J requires a distinct weight vector w_k for each ROI:
    c_{n,k} = sigma(w_k^T u_{n,k} + b_k)
"""

from __future__ import annotations

import torch
import torch.nn as nn


class ConceptBottleneck(nn.Module):
    def __init__(self, K: int, C_t: int, n_classes: int):
        super().__init__()
        self.K = K
        self.C_t = C_t

        self.concept_weights = nn.Parameter(torch.empty(K, C_t))
        self.concept_bias = nn.Parameter(torch.zeros(K))
        nn.init.xavier_uniform_(self.concept_weights)

        self.cbm_head = nn.Linear(K, n_classes)

    def forward(self, U: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # U: (B, K, C_t)
        raw = torch.einsum("bkc,kc->bk", U, self.concept_weights) + self.concept_bias
        c = torch.sigmoid(raw)
        cbm_logits = self.cbm_head(c)
        return c, cbm_logits
