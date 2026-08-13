"""Explicit synthetic-only mean-pooling composition for Phase 17."""

from __future__ import annotations

import torch
from torch import nn

from pada3dacb.ablations.schemas import ModelVariant, sha256_payload
from pada3dacb.exceptions import ModelContractError
from pada3dacb.models.classification_head import ClassificationHead
from pada3dacb.models.concept_bottleneck import ConceptBottleneck
from pada3dacb.models.encoder3d import Encoder3D
from pada3dacb.models.pada3dacb import PADA3DACBOutput
from pada3dacb.models.roi_tokenizer import ROITokenizer

MEAN_POOL_MODEL_VARIANT = ModelVariant(
    name="PADA-3DACB+MeanPoolAggregator",
    aggregator="MeanPoolAggregator",
)
MEAN_POOL_MODEL_VARIANT_HASH = sha256_payload(MEAN_POOL_MODEL_VARIANT.to_dict())


class MeanPoolAggregator(nn.Module):
    """Apply the notebook's exact uniform ROI mean operation."""

    def forward(self, U: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if U.ndim != 3 or U.shape[1] <= 0:
            raise ModelContractError("Mean-pool input must have shape (B,K,C) with K > 0.")
        if not torch.isfinite(U).all():
            raise ModelContractError("Mean-pool input must contain only finite values.")
        z = U.mean(dim=1)
        alpha = torch.ones(U.shape[0], U.shape[1], dtype=U.dtype, device=U.device) / U.shape[1]
        return z, alpha


class MeanPoolPADA3DACB(nn.Module):
    """PADA-3DACB with one explicit, non-contextual mean-pool composition."""

    public_name = MEAN_POOL_MODEL_VARIANT.name
    model_variant = MEAN_POOL_MODEL_VARIANT.name
    model_variant_hash = MEAN_POOL_MODEL_VARIANT_HASH
    class_order = ("CN", "MCI", "AD")

    def __init__(
        self,
        num_rois: int = 84,
        feature_dim: int = 256,
        token_dim: int = 128,
        num_classes: int = 3,
        base_channels: int = 32,
        concept_hidden_dim: int = 64,
        token_dropout: float = 0.2,
        concept_dropout: float = 0.2,
        validate_inputs: bool = True,
    ) -> None:
        super().__init__()
        if num_classes != len(self.class_order):
            raise ModelContractError("PADA-3DACB has the fixed class order CN/MCI/AD.")
        if min(num_rois, feature_dim, token_dim, base_channels, concept_hidden_dim) <= 0:
            raise ModelContractError("All model dimensions must be positive.")
        self.num_rois = num_rois
        self.feature_dim = feature_dim
        self.token_dim = token_dim
        self.num_classes = num_classes
        self.validate_inputs = validate_inputs
        self.encoder = Encoder3D(feature_dim=feature_dim, base_channels=base_channels)
        self.tokenizer = ROITokenizer(num_rois, feature_dim, token_dim)
        self.token_norm = nn.LayerNorm(token_dim)
        self.token_mlp = nn.Sequential(
            nn.Linear(token_dim, token_dim),
            nn.GELU(),
            nn.Dropout(token_dropout),
            nn.Linear(token_dim, token_dim),
        )
        self.token_dropout = nn.Dropout(token_dropout)
        self.aggregator = MeanPoolAggregator()
        self.cls_head = ClassificationHead(token_dim, num_classes)
        self.cbm = ConceptBottleneck(
            num_rois, token_dim, num_classes, concept_hidden_dim, concept_dropout
        )

    def _validate_x(self, x: torch.Tensor) -> None:
        if x.ndim != 5 or x.shape[1] != 1:
            raise ModelContractError(f"x must have shape (B,1,H,W,D), got {tuple(x.shape)}.")
        if x.dtype != torch.float32:
            raise ModelContractError(f"x must use float32, got {x.dtype}.")
        if not torch.isfinite(x).all():
            raise ModelContractError("x must contain only finite values.")
        if x.device != next(self.parameters()).device:
            raise ModelContractError("x and model parameters must be on the same device.")

    def forward(self, x: torch.Tensor, roi_masks: torch.Tensor) -> PADA3DACBOutput:
        if self.validate_inputs:
            self._validate_x(x)
        feature_map = self.encoder(x)
        tokens = self.tokenizer(feature_map, roi_masks)
        tokens = self.token_norm(tokens)
        tokens = tokens + self.token_mlp(tokens)
        tokens = self.token_dropout(tokens)
        non_contextual_tokens = tokens
        embedding, attention = self.aggregator(non_contextual_tokens)
        latent_logits = self.cls_head(embedding)
        concepts, concept_logits = self.cbm(non_contextual_tokens)
        return PADA3DACBOutput(
            F=feature_map,
            T=tokens,
            U=non_contextual_tokens,
            z=embedding,
            alpha=attention,
            latent_logits=latent_logits,
            latent_probabilities=torch.softmax(latent_logits, dim=-1),
            concepts=concepts,
            concept_logits=concept_logits,
            concept_probabilities=torch.softmax(concept_logits, dim=-1),
        )

    @torch.no_grad()
    def predict(self, x: torch.Tensor, roi_masks: torch.Tensor) -> dict[str, torch.Tensor]:
        output = self(x, roi_masks)
        return {
            "y_hat": output.concept_probabilities.argmax(dim=-1),
            "p_tilde": output.concept_probabilities,
            "c": output.concepts,
            "alpha": output.alpha,
        }


def build_mean_pool_model(**kwargs: object) -> MeanPoolPADA3DACB:
    """Build the explicit approved ``mean_pool`` architecture composition."""
    return MeanPoolPADA3DACB(**kwargs)


def mean_pool_model_variant_hash() -> str:
    """Return the deterministic registry-compatible model-variant hash."""
    return MEAN_POOL_MODEL_VARIANT_HASH
