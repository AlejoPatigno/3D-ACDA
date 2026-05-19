
"""
jacobian_utils.py
=================
Section L of the Materials and Methods.

This module computes:
    g_{n,k}   = mean_{x in R_k} psi(J_n(x))
    g_bar     = normalized ROI-wise deformation summary

It supports two regimes:
  1. If a displacement field already exists, compute Jacobian directly.
  2. If only template and subject MRI are available, estimate a non-linear
     displacement field with SimpleITK (Demons registration).

The implementation is deliberately explicit because Jacobian-based terms are
part of the anatomical plausibility regularizer, not pathology ground truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union

import nibabel as nib
import numpy as np
import torch

from atlas_utils import AtlasROIManager

try:
    import SimpleITK as sitk
except Exception:  # pragma: no cover
    sitk = None

ArrayLikePath = Union[str, Path]


@dataclass
class JacobianConfig:
    psi: str = "neg_log"   # currently: neg_log | identity
    eps: float = 1e-6
    n_iterations: int = 50
    smooth_displacement_field: bool = True
    normalize_within_subject: bool = True


def _ensure_sitk():
    if sitk is None:
        raise ImportError(
            "SimpleITK is required for Jacobian computation from displacement fields "
            "or for Demons registration. Install SimpleITK before using jacobian_utils.py."
        )

def load_nifti_array(path: ArrayLikePath) -> np.ndarray:
    img = nib.load(str(path))
    img = nib.as_closest_canonical(img)
    arr = img.get_fdata(dtype=np.float32)
    if arr.ndim == 4:
        arr = arr[..., 0]
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

def sitk_from_numpy(arr: np.ndarray) -> "sitk.Image":
    _ensure_sitk()
    img = sitk.GetImageFromArray(arr.astype(np.float32))
    img.SetSpacing((1.0, 1.0, 1.0))
    return img

def estimate_displacement_field(
    fixed_volume: np.ndarray,
    moving_volume: np.ndarray,
    cfg: Optional[JacobianConfig] = None,
) -> "sitk.Image":
    _ensure_sitk()
    cfg = cfg or JacobianConfig()

    fixed = sitk_from_numpy(fixed_volume)
    moving = sitk_from_numpy(moving_volume)

    matcher = sitk.HistogramMatchingImageFilter()
    matcher.SetNumberOfHistogramLevels(128)
    matcher.SetNumberOfMatchPoints(10)
    moving = matcher.Execute(moving, fixed)

    demons = sitk.DiffeomorphicDemonsRegistrationFilter()
    demons.SetNumberOfIterations(int(cfg.n_iterations))
    demons.SetStandardDeviations(1.0)
    displacement = demons.Execute(fixed, moving)

    if cfg.smooth_displacement_field:
        displacement = sitk.SmoothingRecursiveGaussian(displacement, 1.0)
    return displacement

def jacobian_determinant_from_displacement(displacement_field: "sitk.Image") -> np.ndarray:
    _ensure_sitk()
    jac = sitk.DisplacementFieldJacobianDeterminant(displacement_field)
    jac_np = sitk.GetArrayFromImage(jac).astype(np.float32)
    return np.nan_to_num(jac_np, nan=1.0, posinf=1.0, neginf=1.0)

def apply_psi(jac_det: np.ndarray, psi: str = "neg_log", eps: float = 1e-6) -> np.ndarray:
    jac_det = np.clip(jac_det, eps, None)
    if psi == "neg_log":
        return -np.log(jac_det).astype(np.float32)
    if psi == "identity":
        return jac_det.astype(np.float32)
    raise ValueError(f"Unknown psi={psi!r}")

def pool_roi_deformation(
    psi_jacobian: np.ndarray,
    atlas_mgr: AtlasROIManager,
) -> np.ndarray:
    masks = atlas_mgr.get_binary_masks(psi_jacobian.shape).cpu().numpy()
    out = np.zeros(atlas_mgr.K, dtype=np.float32)

    for k in range(atlas_mgr.K):
        mask = masks[k] > 0
        if np.any(mask):
            out[k] = float(psi_jacobian[mask].mean())
    return out

def normalize_roi_summary(g: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    g = np.asarray(g, dtype=np.float32)
    mu = float(g.mean())
    sigma = float(g.std())
    z = (g - mu) / (sigma + eps)
    return (1.0 / (1.0 + np.exp(-z))).astype(np.float32)

def compute_g_bar_from_template_and_subject(
    template_volume: np.ndarray,
    subject_volume: np.ndarray,
    atlas_mgr: AtlasROIManager,
    cfg: Optional[JacobianConfig] = None,
) -> torch.Tensor:
    cfg = cfg or JacobianConfig()
    displacement = estimate_displacement_field(template_volume, subject_volume, cfg=cfg)
    jac_det = jacobian_determinant_from_displacement(displacement)
    psi_jac = apply_psi(jac_det, psi=cfg.psi, eps=cfg.eps)
    g = pool_roi_deformation(psi_jac, atlas_mgr)

    if cfg.normalize_within_subject:
        g = normalize_roi_summary(g, eps=cfg.eps)
    return torch.from_numpy(g.astype(np.float32))

def precompute_jacobians_from_dataframe(
    df,
    atlas_mgr: AtlasROIManager,
    template_x_path: ArrayLikePath,
    x_column: str = "x_path",
    subject_id_column: str = "subject_id",
    output_dir: ArrayLikePath = "./jacobian_targets",
    cfg: Optional[JacobianConfig] = None,
):
    import pandas as pd

    cfg = cfg or JacobianConfig()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    template_obj = torch.load(template_x_path, map_location="cpu")
    template_x = template_obj["x"] if isinstance(template_obj, dict) and "x" in template_obj else template_obj
    if torch.is_tensor(template_x):
        template_x = template_x.squeeze(0).cpu().numpy().astype(np.float32)

    rows = []
    for _, row in df.iterrows():
        x_obj = torch.load(row[x_column], map_location="cpu")
        x = x_obj["x"] if isinstance(x_obj, dict) and "x" in x_obj else x_obj
        if torch.is_tensor(x):
            x = x.squeeze(0).cpu().numpy().astype(np.float32)

        g_bar = compute_g_bar_from_template_and_subject(
            template_volume=template_x,
            subject_volume=x,
            atlas_mgr=atlas_mgr,
            cfg=cfg,
        )

        save_path = output_dir / f"{row[subject_id_column]}_g_bar.pt"
        torch.save(g_bar, save_path)

        rows.append({
            "subject_id": row[subject_id_column],
            "x_path": row[x_column],
            "g_bar_path": str(save_path),
        })

    return pd.DataFrame(rows)
