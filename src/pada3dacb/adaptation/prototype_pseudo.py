"""Stateless composition of canonical prototype and pseudo-label adaptation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import torch
from torch import Tensor

from pada3dacb.adaptation.prototype import (
    DEFAULT_LAMBDA_SEP,
    DEFAULT_PROTO_MARGIN,
    DEFAULT_PROTOTYPE_CLASS_COUNT,
    DEFAULT_TAU_P,
    PrototypeLoss,
)
from pada3dacb.adaptation.pseudo_label import PseudoLabelLoss
from pada3dacb.exceptions import LossContractError

DEFAULT_LAMBDA_PROTO = 1.0
DEFAULT_LAMBDA_PL = 0.1
Stage = Literal["warm", "full"]


@dataclass(frozen=True)
class PrototypePseudoAdaptationConfig:
    """Canonical Phase 13 adaptation coefficients."""

    lambda_proto: float = DEFAULT_LAMBDA_PROTO
    lambda_pl: float = DEFAULT_LAMBDA_PL
    tau_p: float = DEFAULT_TAU_P
    proto_margin: float = DEFAULT_PROTO_MARGIN
    lambda_sep: float = DEFAULT_LAMBDA_SEP
    num_classes: int = DEFAULT_PROTOTYPE_CLASS_COUNT

    def __post_init__(self) -> None:
        _validate_nonnegative_scalar(self.lambda_proto, "lambda_proto")
        _validate_nonnegative_scalar(self.lambda_pl, "lambda_pl")
        _validate_probability_threshold(self.tau_p, "tau_p")
        _validate_nonnegative_scalar(self.proto_margin, "proto_margin")
        _validate_nonnegative_scalar(self.lambda_sep, "lambda_sep")
        _validate_class_count(self.num_classes)


@dataclass(frozen=True)
class PrototypePseudoAdaptationOutput:
    """Typed adaptation contribution and diagnostics for one batch."""

    total: Tensor
    prototype_raw: Tensor
    prototype_weighted: Tensor
    prototype_alignment: Tensor
    prototype_separation: Tensor
    pseudo_label_raw: Tensor
    pseudo_label_weighted: Tensor
    accepted_count: int
    rejected_count: int
    acceptance_rate: float
    confidence_mean_accepted: float | None
    classes_with_source_prototypes: list[int]
    classes_with_target_prototypes: list[int]
    classes_with_both_prototypes: list[int]
    prototype_distance_mean: float | None
    adaptation_active: bool
    source_prototypes: Tensor | None = None
    target_prototypes: Tensor | None = None
    valid_source_prototypes: Tensor | None = None
    valid_target_prototypes: Tensor | None = None
    target_pseudo_labels: Tensor | None = None
    accepted_target: Tensor | None = None
    pseudo_label_confidence: Tensor | None = None


class PrototypePseudoAdaptationLoss:
    """Compose canonical prototype loss and pseudo-label loss without extra state."""

    def __init__(self, config: PrototypePseudoAdaptationConfig | None = None) -> None:
        self.config = config if config is not None else PrototypePseudoAdaptationConfig()
        if not isinstance(self.config, PrototypePseudoAdaptationConfig):
            raise LossContractError("config must be a PrototypePseudoAdaptationConfig instance.")
        self.prototype_loss = PrototypeLoss(
            tau_p=self.config.tau_p,
            proto_margin=self.config.proto_margin,
            lambda_sep=self.config.lambda_sep,
            class_count=self.config.num_classes,
        )
        self.pseudo_label_loss = PseudoLabelLoss(
            tau_p=self.config.tau_p,
            class_count=self.config.num_classes,
        )

    def __call__(self, z_src: Tensor, y_src: Tensor, z_tgt: Tensor, logits_c_tgt: Tensor, *, stage: Stage) -> PrototypePseudoAdaptationOutput:
        return self.forward(z_src, y_src, z_tgt, logits_c_tgt, stage=stage)

    def forward(self, z_src: Tensor, y_src: Tensor, z_tgt: Tensor, logits_c_tgt: Tensor, *, stage: Stage) -> PrototypePseudoAdaptationOutput:
        stage = _validate_stage(stage)
        if stage == "warm":
            return _inactive_output(z_src, z_tgt, logits_c_tgt)

        prototype = self.prototype_loss(z_src, y_src, z_tgt, logits_c_tgt)
        pseudo_label = self.pseudo_label_loss(logits_c_tgt)
        prototype_weighted = prototype.total * prototype.total.new_tensor(self.config.lambda_proto)
        pseudo_label_weighted = pseudo_label.loss * pseudo_label.loss.new_tensor(self.config.lambda_pl)
        total = prototype_weighted + pseudo_label_weighted
        _validate_scalar_loss(total, "prototype + pseudo-label adaptation total")

        accepted_count = pseudo_label.accepted_count
        rejected_count = pseudo_label.rejected_count
        acceptance_rate = accepted_count / int(logits_c_tgt.shape[0])
        confidence_mean_accepted = None
        if accepted_count > 0:
            confidence_mean_accepted = float(pseudo_label.confidence[pseudo_label.accepted].mean().item())

        classes_with_source = _classes_from_mask(prototype.valid_source)
        classes_with_target = _classes_from_mask(prototype.valid_target)
        classes_with_both = _classes_from_mask(prototype.valid_source & prototype.valid_target)
        distance_mean = _prototype_distance_mean(
            prototype.source_prototypes,
            prototype.valid_source,
            prototype.target_prototypes,
            prototype.valid_target,
        )

        return PrototypePseudoAdaptationOutput(
            total=total,
            prototype_raw=prototype.total,
            prototype_weighted=prototype_weighted,
            prototype_alignment=prototype.alignment,
            prototype_separation=prototype.separation,
            pseudo_label_raw=pseudo_label.loss,
            pseudo_label_weighted=pseudo_label_weighted,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            acceptance_rate=acceptance_rate,
            confidence_mean_accepted=confidence_mean_accepted,
            classes_with_source_prototypes=classes_with_source,
            classes_with_target_prototypes=classes_with_target,
            classes_with_both_prototypes=classes_with_both,
            prototype_distance_mean=distance_mean,
            adaptation_active=True,
            source_prototypes=prototype.source_prototypes,
            target_prototypes=prototype.target_prototypes,
            valid_source_prototypes=prototype.valid_source,
            valid_target_prototypes=prototype.valid_target,
            target_pseudo_labels=prototype.target_pseudo_labels,
            accepted_target=prototype.accepted_target,
            pseudo_label_confidence=pseudo_label.confidence,
        )


def prototype_pseudo_adaptation_loss(
    *,
    z_src: Tensor,
    y_src: Tensor,
    z_tgt: Tensor,
    logits_c_tgt: Tensor,
    stage: Stage,
    config: PrototypePseudoAdaptationConfig | None = None,
) -> PrototypePseudoAdaptationOutput:
    """Return only the Phase 13 adaptation contribution for warm or full stage."""
    return PrototypePseudoAdaptationLoss(config)(z_src, y_src, z_tgt, logits_c_tgt, stage=stage)


def _validate_stage(stage: object) -> Stage:
    if stage not in ("warm", "full"):
        raise LossContractError("stage must be either 'warm' or 'full'.")
    return stage  # type: ignore[return-value]


def _validate_class_count(class_count: int) -> int:
    if not isinstance(class_count, int) or class_count <= 0:
        raise LossContractError("num_classes must be a positive integer.")
    return class_count


def _validate_probability_threshold(value: float, name: str) -> float:
    scalar = float(value)
    if not math.isfinite(scalar) or scalar < 0.0 or scalar > 1.0:
        raise LossContractError(f"{name} must be finite and within [0, 1].")
    return scalar


def _validate_nonnegative_scalar(value: float, name: str) -> float:
    scalar = float(value)
    if not math.isfinite(scalar) or scalar < 0.0:
        raise LossContractError(f"{name} must be finite and non-negative.")
    return scalar


def _validate_scalar_loss(loss: Tensor, name: str) -> None:
    if loss.ndim != 0 or not torch.isfinite(loss):
        raise LossContractError(f"{name} must be a finite scalar.")


def _zero_like_adaptation(z_src: Tensor, z_tgt: Tensor, logits_c_tgt: Tensor) -> Tensor:
    if not torch.is_tensor(z_src) or not torch.is_tensor(z_tgt) or not torch.is_tensor(logits_c_tgt):
        raise LossContractError("warm-stage adaptation tensors must be tensors.")
    tensors = [tensor for tensor in (z_src, z_tgt, logits_c_tgt) if tensor.is_floating_point()]
    if not tensors:
        raise LossContractError("warm-stage adaptation requires at least one floating-point reference tensor.")
    zero = tensors[0].sum() * 0.0
    for tensor in tensors[1:]:
        zero = zero + tensor.sum() * 0.0
    return zero


def _inactive_output(z_src: Tensor, z_tgt: Tensor, logits_c_tgt: Tensor) -> PrototypePseudoAdaptationOutput:
    zero = _zero_like_adaptation(z_src, z_tgt, logits_c_tgt)
    return PrototypePseudoAdaptationOutput(
        total=zero,
        prototype_raw=zero,
        prototype_weighted=zero,
        prototype_alignment=zero,
        prototype_separation=zero,
        pseudo_label_raw=zero,
        pseudo_label_weighted=zero,
        accepted_count=0,
        rejected_count=0,
        acceptance_rate=0.0,
        confidence_mean_accepted=None,
        classes_with_source_prototypes=[],
        classes_with_target_prototypes=[],
        classes_with_both_prototypes=[],
        prototype_distance_mean=None,
        adaptation_active=False,
    )


def _classes_from_mask(mask: Tensor) -> list[int]:
    return [int(index.item()) for index in torch.nonzero(mask, as_tuple=False).flatten()]


def _prototype_distance_mean(source_prototypes: Tensor, valid_source: Tensor, target_prototypes: Tensor, valid_target: Tensor) -> float | None:
    mutually_valid = valid_source & valid_target
    if not bool(mutually_valid.any()):
        return None
    distances = (source_prototypes[mutually_valid] - target_prototypes[mutually_valid]).norm(p=2, dim=1)
    return float(distances.mean().item())
