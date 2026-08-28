"""Generic ROI pooling without mask resampling."""

from __future__ import annotations

import numpy as np
import torch


def _arrays(volume: np.ndarray | torch.Tensor, masks: np.ndarray | torch.Tensor) -> tuple[np.ndarray, np.ndarray]:
    vol = volume.detach().cpu().numpy() if torch.is_tensor(volume) else np.asarray(volume)
    roi = masks.detach().cpu().numpy() if torch.is_tensor(masks) else np.asarray(masks)
    vol = np.asarray(vol, dtype=np.float32)
    roi = np.asarray(roi)
    if vol.ndim != 3 or roi.ndim != 4 or tuple(roi.shape[1:]) != tuple(vol.shape):
        raise ValueError(f"Expected volume (H,W,D) and masks (K,H,W,D), got {vol.shape} and {roi.shape}.")
    if not np.isfinite(vol).all():
        raise ValueError("Regional pooling input contains non-finite values.")
    return vol, roi


def masked_mean_pool(
    volume: np.ndarray | torch.Tensor,
    masks: np.ndarray | torch.Tensor,
    *,
    empty_value: float = 0.0,
) -> np.ndarray:
    """Return one mean per mask in stable mask order."""
    vol, roi = _arrays(volume, masks)
    result = np.full(roi.shape[0], empty_value, dtype=np.float32)
    for index in range(roi.shape[0]):
        mask = roi[index] > 0
        if np.any(mask):
            result[index] = float(vol[mask].mean())
    return result


def masked_fraction_at_or_below(
    volume: np.ndarray | torch.Tensor,
    masks: np.ndarray | torch.Tensor,
    threshold: float,
) -> np.ndarray:
    """Return the canonical fraction of ROI voxels at or below a threshold."""
    vol, roi = _arrays(volume, masks)
    result = np.zeros(roi.shape[0], dtype=np.float32)
    for index in range(roi.shape[0]):
        mask = roi[index] > 0
        if np.any(mask):
            result[index] = float((vol[mask] <= threshold).mean())
    return result
