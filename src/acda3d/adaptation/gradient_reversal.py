"""Explicit constant-coefficient gradient reversal for CDAN."""

from __future__ import annotations

import math
from numbers import Real

import torch
from torch import Tensor, nn

from acda3d.exceptions import LossContractError


def _validate_coefficient(coefficient: float) -> float:
    if not isinstance(coefficient, Real) or isinstance(coefficient, bool):
        raise LossContractError("GRL coefficient must be an explicit constant number.")
    value = float(coefficient)
    if not math.isfinite(value) or value < 0:
        raise LossContractError("GRL coefficient must be finite and non-negative.")
    return value


def _validate(x: Tensor, coefficient: float, *, strict: bool = True) -> float:
    if not torch.is_tensor(x) or not x.is_floating_point():
        raise LossContractError("Gradient reversal requires a floating-point tensor.")
    value = _validate_coefficient(coefficient)
    if strict and not torch.isfinite(x).all():
        raise LossContractError("Gradient reversal input must be finite.")
    return value


class GradientReversalFunction(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x: Tensor, coefficient: float) -> Tensor:  # type: ignore[override]
        ctx.coefficient = coefficient
        return x.view_as(x)

    @staticmethod
    def backward(ctx, gradient: Tensor) -> tuple[Tensor, None]:  # type: ignore[override]
        return gradient.neg().mul(ctx.coefficient), None


def gradient_reverse(x: Tensor, coefficient: float, *, strict: bool = True) -> Tensor:
    return GradientReversalFunction.apply(x, _validate(x, coefficient, strict=strict))


class GradientReversal(nn.Module):
    def __init__(self, coefficient: float, *, strict: bool = True) -> None:
        super().__init__()
        self.coefficient = _validate_coefficient(coefficient)
        self.strict = strict

    def forward(self, x: Tensor) -> Tensor:
        return gradient_reverse(x, self.coefficient, strict=self.strict)
