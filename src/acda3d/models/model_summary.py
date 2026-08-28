"""Dependency-free CPU model inspection utilities."""

from __future__ import annotations

from typing import Any

import torch
from torch import nn

from acda3d.models.acda3d import ACDA3D


def count_trainable_parameters(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def count_parameters_by_module(model: nn.Module) -> dict[str, int]:
    names = (
        "encoder",
        "tokenizer",
        "token_norm",
        "token_mlp",
        "token_dropout",
        "aggregator",
        "cls_head",
        "cbm",
    )
    return {
        name: sum(parameter.numel() for parameter in getattr(model, name).parameters())
        for name in names
        if hasattr(model, name)
    }


@torch.no_grad()
def infer_output_shapes(
    model: ACDA3D,
    synthetic_input: torch.Tensor,
    roi_masks: torch.Tensor,
) -> dict[str, tuple[int, ...]]:
    was_training = model.training
    model.eval()
    try:
        output = model(synthetic_input, roi_masks)
        return {name: tuple(value.shape) for name, value in output.items()}
    finally:
        model.train(was_training)


@torch.no_grad()
def summarize_model(
    model: ACDA3D,
    input_shape: tuple[int, int, int, int, int],
    roi_masks: torch.Tensor | None = None,
) -> dict[str, Any]:
    parameter = next(model.parameters())
    synthetic = torch.zeros(input_shape, dtype=torch.float32, device=parameter.device)
    if roi_masks is None:
        feature_shape = model.encoder.infer_output_shape(input_shape)[2:]
        roi_masks = torch.ones(
            (model.num_rois, *feature_shape), dtype=parameter.dtype, device=parameter.device
        )
        roi_masks = roi_masks / roi_masks[0].numel()
    total = sum(parameter.numel() for parameter in model.parameters())
    trainable = count_trainable_parameters(model)
    return {
        "model_name": model.public_name,
        "total_parameters": total,
        "trainable_parameters": trainable,
        "non_trainable_parameters": total - trainable,
        "parameters_by_module": count_parameters_by_module(model),
        "input_shape": tuple(input_shape),
        "output_shapes": infer_output_shapes(model, synthetic, roi_masks),
    }
