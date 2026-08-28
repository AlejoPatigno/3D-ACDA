"""Typed outputs and shared validation for core scientific losses."""

from __future__ import annotations

from dataclasses import dataclass

import torch

from acda3d.exceptions import LossContractError


@dataclass(frozen=True)
class CoreLossOutput:
    total: torch.Tensor
    classification: torch.Tensor
    concept_classification: torch.Tensor
    concept_supervision: torch.Tensor
    anatomical_consistency: torch.Tensor
    prediction_consistency: torch.Tensor

    def detached(self) -> dict[str, float]:
        return {name: float(value.detach().cpu()) for name, value in vars(self).items()}


def validate_finite_tensor(value: torch.Tensor, name: str, ndim: int) -> None:
    if not torch.is_tensor(value) or value.ndim != ndim:
        shape = tuple(value.shape) if torch.is_tensor(value) else type(value).__name__
        raise LossContractError(f"{name} must be a {ndim}D tensor, got {shape}.")
    if not torch.isfinite(value).all():
        raise LossContractError(f"{name} must contain only finite values.")


def validate_pair(left: torch.Tensor, right: torch.Tensor, left_name: str, right_name: str) -> None:
    validate_finite_tensor(left, left_name, 2)
    validate_finite_tensor(right, right_name, 2)
    if left.shape != right.shape:
        raise LossContractError(
            f"{left_name} and {right_name} must have identical shapes, got "
            f"{tuple(left.shape)} and {tuple(right.shape)}."
        )
    if left.device != right.device:
        raise LossContractError(f"{left_name} and {right_name} must be on the same device.")
