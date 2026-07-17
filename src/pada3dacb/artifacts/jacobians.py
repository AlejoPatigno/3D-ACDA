"""Canonical Diffeomorphic Demons Jacobian artifact computation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from pada3dacb.artifacts.atlas import AtlasROIManager, validate_atlas_grid
from pada3dacb.artifacts.concepts import save_plain_mri_pt
from pada3dacb.artifacts.regional_features import masked_mean_pool
from pada3dacb.exceptions import MissingOptionalDependencyError

try:
    import SimpleITK as sitk
except ImportError:  # pragma: no cover
    sitk = None


@dataclass
class JacobianConfig:
    psi: str = "neg_log"
    eps: float = 1e-6
    n_iterations: int = 50
    smooth_displacement_field: bool = True
    normalize_within_subject: bool = True


def _require_sitk() -> Any:
    if sitk is None:
        raise MissingOptionalDependencyError("SimpleITK is required for canonical Jacobian computation. Install pada3dacb[full].")
    return sitk


def _volume(value: Any) -> np.ndarray:
    array = value.detach().cpu().numpy() if torch.is_tensor(value) else np.asarray(value)
    array = np.asarray(array, dtype=np.float32)
    if array.ndim == 4 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 3 or not np.isfinite(array).all():
        raise ValueError(f"Expected finite 3D volume, got {array.shape}.")
    return np.ascontiguousarray(array)


def estimate_displacement_field(fixed_volume: np.ndarray, moving_volume: np.ndarray, cfg: JacobianConfig | None = None) -> Any:
    library = _require_sitk()
    cfg = cfg or JacobianConfig()
    fixed_array, moving_array = _volume(fixed_volume), _volume(moving_volume)
    if fixed_array.shape != moving_array.shape:
        raise ValueError("Template and subject grids must match for Jacobian computation.")
    fixed = library.GetImageFromArray(fixed_array)
    moving = library.GetImageFromArray(moving_array)
    fixed.SetSpacing((1.0, 1.0, 1.0))
    moving.SetSpacing((1.0, 1.0, 1.0))
    matcher = library.HistogramMatchingImageFilter()
    matcher.SetNumberOfHistogramLevels(128)
    matcher.SetNumberOfMatchPoints(10)
    moving = matcher.Execute(moving, fixed)
    demons = library.DiffeomorphicDemonsRegistrationFilter()
    demons.SetNumberOfIterations(int(cfg.n_iterations))
    demons.SetStandardDeviations(1.0)
    displacement = demons.Execute(fixed, moving)
    return library.SmoothingRecursiveGaussian(displacement, 1.0) if cfg.smooth_displacement_field else displacement


def jacobian_determinant_from_displacement(displacement_field: Any) -> np.ndarray:
    library = _require_sitk()
    jacobian = library.DisplacementFieldJacobianDeterminant(displacement_field)
    return np.nan_to_num(library.GetArrayFromImage(jacobian).astype(np.float32), nan=1.0, posinf=1.0, neginf=1.0)


def apply_psi(jacobian: np.ndarray, psi: str = "neg_log", eps: float = 1e-6) -> np.ndarray:
    values = np.asarray(jacobian, dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError("Jacobian determinant contains non-finite values.")
    clipped = np.clip(values, eps, None)
    if psi == "neg_log":
        return -np.log(clipped).astype(np.float32)
    if psi == "identity":
        return clipped.astype(np.float32)
    raise ValueError(f"Unknown psi={psi!r}.")


def pool_roi_deformation(psi_jacobian: np.ndarray, atlas_mgr: AtlasROIManager) -> np.ndarray:
    validate_atlas_grid(atlas_mgr.shape, psi_jacobian.shape)
    return masked_mean_pool(psi_jacobian, atlas_mgr.get_binary_masks()).astype(np.float32)


def normalize_regional_deformation(values: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    z_score = (array - float(array.mean())) / (float(array.std()) + eps)
    return (1.0 / (1.0 + np.exp(-z_score))).astype(np.float32)


normalize_roi_summary = normalize_regional_deformation


def compute_g_bar_from_template_and_subject(template_volume: np.ndarray, subject_volume: np.ndarray, atlas_mgr: AtlasROIManager, cfg: JacobianConfig | None = None) -> torch.Tensor:
    cfg = cfg or JacobianConfig()
    displacement = estimate_displacement_field(template_volume, subject_volume, cfg)
    raw = pool_roi_deformation(apply_psi(jacobian_determinant_from_displacement(displacement), cfg.psi, cfg.eps), atlas_mgr)
    output = normalize_regional_deformation(raw, cfg.eps) if cfg.normalize_within_subject else raw
    return torch.from_numpy(output.astype(np.float32))


def precompute_jacobians_from_dataframe(df: Any, atlas_mgr: AtlasROIManager, template_x_path: str | Path, x_column: str = "x_path", subject_id_column: str = "subject_id", output_dir: str | Path = "./jacobian_targets", cfg: JacobianConfig | None = None) -> Any:
    import pandas as pd

    def load(path: str | Path) -> Any:
        obj = torch.load(path, map_location="cpu", weights_only=True)
        return next((obj[k] for k in ("x", "image", "mri", "tensor", "volume") if isinstance(obj, dict) and k in obj), obj)

    template = _volume(load(template_x_path))
    rows = []
    for _, row in df.iterrows():
        vector = compute_g_bar_from_template_and_subject(template, _volume(load(row[x_column])), atlas_mgr, cfg)
        path = Path(output_dir) / f"{row[subject_id_column]}_g_bar.pt"
        save_plain_mri_pt(vector, path, key="g_bar")
        rows.append({"subject_id": row[subject_id_column], "x_path": row[x_column], "g_bar_path": str(path)})
    return pd.DataFrame(rows)
