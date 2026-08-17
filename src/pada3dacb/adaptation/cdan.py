"""Exact outer-product CDAN over latent PADA-3DACB embeddings."""

from __future__ import annotations

import math
from typing import Any

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from pada3dacb.adaptation.domain_discriminator import DomainDiscriminator
from pada3dacb.adaptation.gradient_reversal import gradient_reverse
from pada3dacb.adaptation.outputs import AdaptationLossOutput
from pada3dacb.exceptions import LossContractError
from pada3dacb.models import PADA3DACBOutput

CDAN_CLASS_COUNT = 3  # historical default; binary callers pass the task-derived width
BINARY_CDAN_CLASS_COUNT = 2


def expected_conditional_dimension(embedding_dimension: int, class_count: int = CDAN_CLASS_COUNT) -> int:
    """Return the inferred flattened CDAN outer-product dimension."""
    if not isinstance(embedding_dimension, int) or embedding_dimension <= 0:
        raise LossContractError("CDAN embedding dimension must be a positive integer.")
    if not isinstance(class_count, int) or class_count <= 0:
        raise LossContractError("CDAN class count must be a positive integer.")
    return embedding_dimension * class_count


def conditional_outer_product(
    features: Tensor, class_probabilities: Tensor, class_count: int | None = None
) -> Tensor:
    """Build row-major outer products using the runtime class count without detaching."""
    if features.ndim != 2 or class_probabilities.ndim != 2:
        raise LossContractError("CDAN features and probabilities must both be rank 2.")
    if features.shape[0] != class_probabilities.shape[0] or class_probabilities.shape[1] <= 0:
        raise LossContractError("CDAN requires matched batches and at least one class probability.")
    if class_count is not None and class_probabilities.shape[1] != class_count:
        raise LossContractError("CDAN probability width must match the runtime class count.")
    if features.device != class_probabilities.device:
        raise LossContractError("CDAN inputs must share a device.")
    if not features.is_floating_point() or not class_probabilities.is_floating_point():
        raise LossContractError("CDAN inputs must use floating-point dtypes.")
    probability_row_sums = class_probabilities.sum(dim=1)
    if (
        not torch.isfinite(features).all()
        or not torch.isfinite(class_probabilities).all()
        or (class_probabilities < 0).any()
        or not torch.allclose(probability_row_sums, torch.ones_like(probability_row_sums), atol=1e-5)
    ):
        raise LossContractError("CDAN probabilities must be finite normalized rows and features finite.")

    result = (features.unsqueeze(2) * class_probabilities.unsqueeze(1)).flatten(1)
    if not torch.isfinite(result).all():
        raise LossContractError("CDAN conditional features must be finite.")
    return result


def _declared_discriminator_input_dimension(discriminator: nn.Module) -> int | None:
    for attribute_name in ("input_dimension", "input_dim", "in_features"):
        value = getattr(discriminator, attribute_name, None)
        if isinstance(value, int):
            return value

    config = getattr(discriminator, "config", None)
    if config is not None:
        for attribute_name in ("input_dimension", "input_dim", "in_features"):
            value = getattr(config, attribute_name, None)
            if isinstance(value, int):
                return value

    for module in discriminator.modules():
        if isinstance(module, nn.Linear):
            return int(module.in_features)
    return None


def _validate_discriminator_dimension(discriminator: nn.Module, conditional_dimension: int) -> None:
    declared_dimension = _declared_discriminator_input_dimension(discriminator)
    if declared_dimension is None:
        return
    if declared_dimension != conditional_dimension:
        raise LossContractError(
            "CDAN discriminator input dimension must match the inferred conditional dimension "
            f"{conditional_dimension}; got {declared_dimension}."
        )


def _squeeze_domain_logits(logits: Tensor, expected_batch_size: int) -> Tensor:
    if logits.ndim == 2 and logits.shape[1] == 1:
        logits = logits.squeeze(1)
    if logits.ndim != 1 or logits.shape[0] != expected_batch_size:
        raise LossContractError("CDAN discriminator must return exactly one raw logit per sample.")
    if not logits.is_floating_point() or not torch.isfinite(logits).all():
        raise LossContractError("CDAN discriminator logits must be finite floating-point tensors.")
    return logits


class CDANAdaptationMethod:
    name = "cdan"
    feature = "z"

    def __init__(self, discriminator: DomainDiscriminator, grl_coefficient: float) -> None:
        if not math.isfinite(float(grl_coefficient)) or float(grl_coefficient) < 0:
            raise LossContractError("CDAN GRL coefficient must be finite and non-negative.")
        self.discriminator = discriminator
        self.grl_coefficient = float(grl_coefficient)

    def compute(self, source_output: PADA3DACBOutput, target_output: PADA3DACBOutput, stage: str) -> AdaptationLossOutput:
        if stage not in {"warm", "full"}:
            raise LossContractError("CDAN stage must be 'warm' or 'full'.")
        if stage == "warm":
            zero = source_output.z.float().sum() * 0.0
            return AdaptationLossOutput(zero, {"cdan": zero}, {})

        source_h = conditional_outer_product(source_output.z, source_output.latent_probabilities)
        target_h = conditional_outer_product(target_output.z, target_output.latent_probabilities)
        if source_h.shape[1] != target_h.shape[1]:
            raise LossContractError("CDAN source and target conditional dimensions must match.")
        _validate_discriminator_dimension(self.discriminator, source_h.shape[1])

        source_logits = _squeeze_domain_logits(
            self.discriminator(gradient_reverse(source_h, self.grl_coefficient)),
            source_h.shape[0],
        )
        target_logits = _squeeze_domain_logits(
            self.discriminator(gradient_reverse(target_h, self.grl_coefficient)),
            target_h.shape[0],
        )
        logits = torch.cat((source_logits, target_logits), dim=0)
        targets = torch.cat((torch.zeros_like(source_logits), torch.ones_like(target_logits)), dim=0)
        loss = F.binary_cross_entropy_with_logits(logits, targets, reduction="mean")
        source_loss = F.binary_cross_entropy_with_logits(source_logits, torch.zeros_like(source_logits), reduction="mean")
        target_loss = F.binary_cross_entropy_with_logits(target_logits, torch.ones_like(target_logits), reduction="mean")
        predictions = (logits >= 0).float()
        diagnostics: dict[str, Any] = {
            "source_domain_loss": source_loss,
            "target_domain_loss": target_loss,
            "domain_accuracy": (predictions == targets).float().mean(),
            "source_domain_accuracy": (source_logits < 0).float().mean(),
            "target_domain_accuracy": (target_logits >= 0).float().mean(),
            "source_domain_logit_mean": source_logits.mean(),
            "target_domain_logit_mean": target_logits.mean(),
            "source_conditional_norm": source_h.norm(dim=1).mean(),
            "target_conditional_norm": target_h.norm(dim=1).mean(),
            "grl_coefficient": loss.new_tensor(self.grl_coefficient),
            "conditional_dimension": loss.new_tensor(source_h.shape[1]),
        }
        return AdaptationLossOutput(loss, {"cdan": loss}, diagnostics)
