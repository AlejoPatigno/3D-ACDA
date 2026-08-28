"""Canonical atlas-grid to encoder-feature-grid ROI mask preparation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

import torch
from torch.nn import functional as functional

from acda3d.exceptions import ModelContractError


@dataclass(frozen=True)
class ROIMaskPreparationConfig:
    mode: str = "nearest"
    normalize: bool = True
    epsilon: float = 1e-8
    expected_num_rois: int | None = None

    def validate(self) -> None:
        if self.mode != "nearest":
            raise ModelContractError("Canonical feature-grid ROI preparation requires nearest mode.")
        if self.epsilon <= 0:
            raise ModelContractError("ROI mask normalization epsilon must be positive.")
        if self.expected_num_rois is not None and self.expected_num_rois <= 0:
            raise ModelContractError("expected_num_rois must be positive when provided.")

    def sha256(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("ascii")).hexdigest()


def roi_mask_cache_key(
    atlas_hash: str,
    feature_shape: tuple[int, int, int],
    config: ROIMaskPreparationConfig,
) -> str:
    config.validate()
    if not atlas_hash:
        raise ModelContractError("atlas_hash is required for a feature-mask cache key.")
    payload = {
        "atlas_hash": atlas_hash,
        "feature_shape": list(feature_shape),
        "preparation_configuration_hash": config.sha256(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def prepare_feature_grid_roi_masks(
    roi_masks: torch.Tensor,
    feature_shape: tuple[int, int, int],
    config: ROIMaskPreparationConfig | None = None,
    *,
    device: torch.device | str | None = None,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Resize with nearest interpolation, then normalize each ROI to sum to one."""
    config = config or ROIMaskPreparationConfig()
    config.validate()
    if roi_masks.ndim != 4:
        raise ModelContractError(f"ROI masks must have shape (K,H,W,D), got {tuple(roi_masks.shape)}.")
    if len(feature_shape) != 3 or any(int(value) <= 0 for value in feature_shape):
        raise ModelContractError(f"feature_shape must contain three positive values: {feature_shape}.")
    if config.expected_num_rois is not None and roi_masks.shape[0] != config.expected_num_rois:
        raise ModelContractError(
            f"Expected {config.expected_num_rois} ROI masks, got {roi_masks.shape[0]}."
        )
    if not roi_masks.dtype.is_floating_point and roi_masks.dtype != torch.bool:
        raise ModelContractError("ROI masks must be floating point or bool.")
    if not torch.isfinite(roi_masks).all():
        raise ModelContractError("ROI masks must contain only finite values.")
    target_device = torch.device(device) if device is not None else roi_masks.device
    source = roi_masks.to(device=target_device, dtype=torch.float32)
    resized = functional.interpolate(
        source.unsqueeze(1), size=tuple(int(value) for value in feature_shape), mode=config.mode
    ).squeeze(1)
    flat = resized.flatten(1)
    sums = flat.sum(dim=1, keepdim=True)
    empty = (sums <= 0).nonzero(as_tuple=False)[:, 0].tolist()
    if empty:
        raise ModelContractError(f"ROIs became empty on the feature grid: indices={empty}.")
    if config.normalize:
        flat = flat / sums.clamp_min(config.epsilon)
        resized = flat.view_as(resized)
    return resized.to(dtype=dtype)
