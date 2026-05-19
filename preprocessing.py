
"""
preprocessing.py
=================
Section B of the Materials and Methods.

This module standardizes a structural MRI volume into the common tensor space
expected by the model:
    X -> X_tilde -> X_bar

It is intentionally conservative. If the Kaggle derivatives are already
preprocessed, this module behaves as a consistency operator plus resampling
and intensity normalization.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

import nibabel as nib
import numpy as np
import torch
import torch.nn.functional as F


ArrayLikePath = Union[str, Path]


@dataclass
class PreprocessConfig:
    target_shape: Tuple[int, int, int] = (128, 128, 128)
    eps: float = 1e-6
    brain_mask_threshold: float = 0.0
    clip_percentiles: Tuple[float, float] = (0.5, 99.5)
    enforce_canonical: bool = True


def load_nifti_canonical(path: ArrayLikePath, enforce_canonical: bool = True) -> tuple[np.ndarray, np.ndarray]:
    img = nib.load(str(path))
    if enforce_canonical:
        img = nib.as_closest_canonical(img)
    vol = img.get_fdata(dtype=np.float32)
    if vol.ndim == 4:
        vol = vol[..., 0]
    vol = np.nan_to_num(vol, nan=0.0, posinf=0.0, neginf=0.0)
    return vol.astype(np.float32), img.affine.astype(np.float32)


def make_brain_mask(volume: np.ndarray, threshold: float = 0.0) -> np.ndarray:
    mask = np.isfinite(volume) & (volume > threshold)
    return mask.astype(np.float32)


def robust_clip_inside_mask(
    volume: np.ndarray,
    mask: np.ndarray,
    clip_percentiles: Tuple[float, float] = (0.5, 99.5),
) -> np.ndarray:
    vox = volume[mask > 0]
    if vox.size == 0:
        return volume.astype(np.float32)
    lo, hi = np.percentile(vox, clip_percentiles)
    return np.clip(volume, lo, hi).astype(np.float32)


def zscore_inside_mask(volume: np.ndarray, mask: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    vox = volume[mask > 0]
    if vox.size == 0:
        return volume.astype(np.float32)
    mu = float(vox.mean())
    sigma = float(vox.std())
    out = (volume - mu) / (sigma + eps)
    out[mask <= 0] = 0.0
    return out.astype(np.float32)


def resize_volume_torch(volume: np.ndarray, target_shape: Sequence[int]) -> np.ndarray:
    x = torch.from_numpy(volume).unsqueeze(0).unsqueeze(0)  # (1,1,H,W,D)
    x = F.interpolate(x, size=tuple(target_shape), mode="trilinear", align_corners=False)
    return x.squeeze(0).squeeze(0).cpu().numpy().astype(np.float32)


def preprocess_volume_array(volume: np.ndarray, cfg: PreprocessConfig) -> tuple[np.ndarray, np.ndarray]:
    mask = make_brain_mask(volume, threshold=cfg.brain_mask_threshold)
    volume = robust_clip_inside_mask(volume, mask, cfg.clip_percentiles)
    volume = resize_volume_torch(volume, cfg.target_shape)
    mask = resize_volume_torch(mask.astype(np.float32), cfg.target_shape)
    mask = (mask > 0.5).astype(np.float32)
    volume = zscore_inside_mask(volume, mask, eps=cfg.eps)
    return volume.astype(np.float32), mask.astype(np.float32)


def preprocess_nifti(
    path: ArrayLikePath,
    cfg: Optional[PreprocessConfig] = None,
    save_pt_path: Optional[ArrayLikePath] = None,
) -> dict:
    cfg = cfg or PreprocessConfig()
    volume, affine = load_nifti_canonical(path, enforce_canonical=cfg.enforce_canonical)
    x_bar, brain_mask = preprocess_volume_array(volume, cfg)

    tensor = torch.from_numpy(x_bar).unsqueeze(0)      # (1,H,W,D)
    mask_t = torch.from_numpy(brain_mask).unsqueeze(0) # (1,H,W,D)

    out = {
        "x": tensor.to(torch.float32),
        "brain_mask": mask_t.to(torch.float32),
        "affine": affine,
        "source_path": str(path),
    }

    if save_pt_path is not None:
        save_pt_path = Path(save_pt_path)
        save_pt_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(out, save_pt_path)

    return out


def validate_tensor_contract(sample: dict, expected_shape: Sequence[int] = (1, 128, 128, 128)) -> None:
    if "x" not in sample:
        raise KeyError("Missing key 'x' in preprocessed sample.")
    x = sample["x"]
    if not torch.is_tensor(x):
        raise TypeError("'x' must be a torch.Tensor.")
    if tuple(x.shape) != tuple(expected_shape):
        raise ValueError(f"Expected x shape {tuple(expected_shape)}, got {tuple(x.shape)}.")
