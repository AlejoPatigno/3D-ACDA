import copy

import torch
from torch import nn

from acda3d.models import ACDA3D


class NotebookLiteReference(nn.Module):
    """Former identity_ctx execution, transcribed from training cell 7/18."""

    def __init__(self, production: ACDA3D):
        super().__init__()
        self.encoder = copy.deepcopy(production.encoder)
        self.tokenizer = copy.deepcopy(production.tokenizer)
        self.token_norm = copy.deepcopy(production.token_norm)
        self.token_mlp = copy.deepcopy(production.token_mlp)
        self.token_dropout = copy.deepcopy(production.token_dropout)
        self.aggregator = copy.deepcopy(production.aggregator)
        self.cls_head = copy.deepcopy(production.cls_head)
        self.cbm = copy.deepcopy(production.cbm)

    def forward(self, x, roi_masks):
        feature_map = self.encoder(x)
        tokens = self.tokenizer(feature_map, roi_masks)
        tokens = self.token_norm(tokens)
        tokens = tokens + self.token_mlp(tokens)
        tokens = self.token_dropout(tokens)
        non_contextual = tokens
        embedding, attention = self.aggregator(non_contextual)
        logits = self.cls_head(embedding)
        concepts, concept_logits = self.cbm(non_contextual)
        return feature_map, tokens, non_contextual, embedding, attention, logits, concepts, concept_logits


def test_complete_former_lite_float32_parity():
    torch.manual_seed(17)
    production = ACDA3D(3, 8, 6, base_channels=4, concept_hidden_dim=4).eval()
    reference = NotebookLiteReference(production).eval()
    x = torch.randn(2, 1, 16, 16, 16)
    roi_masks = torch.ones(3, 2, 2, 2) / 8
    expected = reference(x, roi_masks)
    actual = production(x, roi_masks)
    values = (
        actual.F, actual.T, actual.U, actual.z, actual.alpha,
        actual.latent_logits, actual.concepts, actual.concept_logits,
    )
    for observed, canonical in zip(values, expected, strict=True):
        assert observed.shape == canonical.shape
        torch.testing.assert_close(observed, canonical, rtol=1e-6, atol=1e-7)
