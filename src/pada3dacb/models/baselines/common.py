"""Shared contracts and tensor helpers for approved Phase 14 baselines."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import torch
from torch import Tensor, nn


@dataclass(frozen=True)
class BaselineSpec:
    """Immutable public metadata for one approved baseline."""

    id: str
    display_name: str
    class_name: str
    notebook_provenance: str
    input_contract: str
    requires_roi_masks: bool
    optional_dependencies: tuple[str, ...]
    default_config: Mapping[str, Any]
    output_classes: int


class ConvNormAct3D(nn.Sequential):
    """Small dependency-free 3D convolution block."""

    def __init__(self, in_ch: int, out_ch: int, *, stride: int = 1) -> None:
        super().__init__(
            nn.Conv3d(in_ch, out_ch, kernel_size=3, stride=stride, padding=1, bias=False),
            nn.InstanceNorm3d(out_ch, affine=True),
            nn.ReLU(inplace=True),
        )


class Small3DBackbone(nn.Sequential):
    """Single-channel feature extractor shared by the ROI-aware baseline."""

    def __init__(self, out_ch: int, *, base_ch: int = 32) -> None:
        if out_ch <= 0 or base_ch <= 0:
            raise ValueError("backbone channel counts must be positive")
        super().__init__(
            ConvNormAct3D(1, base_ch, stride=2),
            ConvNormAct3D(base_ch, base_ch * 2, stride=2),
            ConvNormAct3D(base_ch * 2, out_ch, stride=2),
        )


def validate_mri_input(x: Tensor) -> Tensor:
    """Validate the common single-channel MRI batch contract."""
    if not isinstance(x, Tensor) or x.ndim != 5 or x.shape[1] != 1:
        raise ValueError("MRI input must have shape [B, 1, D, H, W]")
    if not x.is_floating_point():
        raise TypeError("MRI input must be a floating-point tensor")
    if not torch.isfinite(x).all():
        raise ValueError("MRI input must contain only finite values")
    return x


def validate_baseline_output(
    output: Mapping[str, Tensor], *, batch_size: int, output_classes: int = 3
) -> Mapping[str, Tensor]:
    """Validate the common classification output contract."""
    if not isinstance(output, Mapping):
        raise TypeError("baseline output must be a mapping")
    logits = output.get("logits")
    if not isinstance(logits, Tensor) or logits.shape != (batch_size, output_classes):
        raise ValueError(f"baseline logits must have shape [B, {output_classes}]")
    return output


def parameter_metadata(model: nn.Module) -> dict[str, int]:
    """Compute parameter counts directly from an instantiated model."""
    return {
        "total_parameters": sum(parameter.numel() for parameter in model.parameters()),
        "trainable_parameters": sum(
            parameter.numel() for parameter in model.parameters() if parameter.requires_grad
        ),
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Tensor):
        tensor = value.detach().cpu().contiguous()
        return {
            "dtype": str(tensor.dtype),
            "shape": list(tensor.shape),
            "sha256": hashlib.sha256(tensor.numpy().tobytes()).hexdigest(),
        }
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"Unsupported reproducibility value: {type(value).__name__}")


def reproducibility_hash(canonical_id: str, resolved_config: Mapping[str, Any]) -> str:
    """Hash the canonical baseline id and every resolved constructor value."""
    payload = {"canonical_id": canonical_id, "resolved_config": _jsonable(resolved_config)}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
