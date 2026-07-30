"""Canonical pseudo-label selection and CE loss for PADA-3DACB adaptation."""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
from torch import Tensor
from torch.nn import functional as F

from pada3dacb.exceptions import LossContractError

DEFAULT_PSEUDO_LABEL_CLASS_COUNT = 3
DEFAULT_TAU_P = 0.95


@dataclass(frozen=True)
class PseudoLabelSelection:
    probabilities: Tensor
    confidence: Tensor
    pseudo_labels: Tensor
    accepted: Tensor

    @property
    def rejected(self) -> Tensor:
        return ~self.accepted

    @property
    def accepted_count(self) -> int:
        return int(self.accepted.sum().item())

    @property
    def rejected_count(self) -> int:
        return int((~self.accepted).sum().item())


@dataclass(frozen=True)
class PseudoLabelLossOutput:
    loss: Tensor
    probabilities: Tensor
    confidence: Tensor
    pseudo_labels: Tensor
    accepted: Tensor

    @property
    def rejected(self) -> Tensor:
        return ~self.accepted

    @property
    def accepted_count(self) -> int:
        return int(self.accepted.sum().item())

    @property
    def rejected_count(self) -> int:
        return int((~self.accepted).sum().item())


def _validate_class_count(class_count: int) -> int:
    if not isinstance(class_count, int) or class_count <= 0:
        raise LossContractError("Pseudo-label class_count must be a positive integer.")
    return class_count


def _validate_probability_threshold(tau_p: float) -> float:
    value = float(tau_p)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise LossContractError("Pseudo-label tau_p must be finite and within [0, 1].")
    return value


def _validate_logits(logits_c_tgt: Tensor, class_count: int) -> None:
    if not torch.is_tensor(logits_c_tgt) or logits_c_tgt.ndim != 2:
        shape = tuple(logits_c_tgt.shape) if torch.is_tensor(logits_c_tgt) else type(logits_c_tgt).__name__
        raise LossContractError(f"logits_c_tgt must be a rank-2 tensor, got {shape}.")
    if logits_c_tgt.shape[0] == 0 or logits_c_tgt.shape[1] == 0:
        raise LossContractError("logits_c_tgt must have non-empty batch and class dimensions.")
    if logits_c_tgt.shape[1] != class_count:
        raise LossContractError(f"logits_c_tgt must have {class_count} classes, got {logits_c_tgt.shape[1]}.")
    if not logits_c_tgt.is_floating_point():
        raise LossContractError("logits_c_tgt must use a floating-point dtype.")
    if not torch.isfinite(logits_c_tgt).all():
        raise LossContractError("logits_c_tgt must contain only finite values.")


def _zero_scalar_like(reference: Tensor) -> Tensor:
    return reference.sum() * 0.0


def select_pseudo_labels(
    logits_c_tgt: Tensor,
    *,
    tau_p: float = DEFAULT_TAU_P,
    class_count: int = DEFAULT_PSEUDO_LABEL_CLASS_COUNT,
) -> PseudoLabelSelection:
    """Select target pseudo-labels from concept-head target logits."""
    class_count = _validate_class_count(class_count)
    tau_p = _validate_probability_threshold(tau_p)
    _validate_logits(logits_c_tgt, class_count)

    probabilities = F.softmax(logits_c_tgt, dim=-1)
    if not torch.isfinite(probabilities).all():
        raise LossContractError("target pseudo-label probabilities must be finite.")
    confidence, pseudo_labels = probabilities.max(dim=-1)
    accepted = confidence >= tau_p
    return PseudoLabelSelection(
        probabilities=probabilities,
        confidence=confidence,
        pseudo_labels=pseudo_labels,
        accepted=accepted,
    )


def pseudo_label_cross_entropy(
    logits_c_tgt: Tensor,
    *,
    tau_p: float = DEFAULT_TAU_P,
    class_count: int = DEFAULT_PSEUDO_LABEL_CLASS_COUNT,
) -> PseudoLabelLossOutput:
    """Return mean CE over accepted pseudo-labeled target rows."""
    selection = select_pseudo_labels(logits_c_tgt, tau_p=tau_p, class_count=class_count)
    if selection.accepted_count == 0:
        loss = _zero_scalar_like(logits_c_tgt)
    else:
        loss = F.cross_entropy(logits_c_tgt[selection.accepted], selection.pseudo_labels[selection.accepted])
    if loss.ndim != 0 or not torch.isfinite(loss):
        raise LossContractError("Pseudo-label loss must be a finite scalar.")
    return PseudoLabelLossOutput(
        loss=loss,
        probabilities=selection.probabilities,
        confidence=selection.confidence,
        pseudo_labels=selection.pseudo_labels,
        accepted=selection.accepted,
    )


class PseudoLabelLoss:
    """Stateless canonical pseudo-label adaptation loss from concept-head logits."""

    def __init__(
        self,
        *,
        tau_p: float = DEFAULT_TAU_P,
        class_count: int = DEFAULT_PSEUDO_LABEL_CLASS_COUNT,
    ) -> None:
        self.tau_p = _validate_probability_threshold(tau_p)
        self.class_count = _validate_class_count(class_count)

    def __call__(self, logits_c_tgt: Tensor) -> PseudoLabelLossOutput:
        return self.forward(logits_c_tgt)

    def forward(self, logits_c_tgt: Tensor) -> PseudoLabelLossOutput:
        return pseudo_label_cross_entropy(logits_c_tgt, tau_p=self.tau_p, class_count=self.class_count)
