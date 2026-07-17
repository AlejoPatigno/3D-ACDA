"""Quality-control overlay generation for derivative verification."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import matplotlib
import numpy as np

from pada3dacb.data.derivative_verification import VerificationResult, VerificationStatus

os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _slice_indices(mask: np.ndarray, axis: int, count: int) -> list[int]:
    coords = np.where(mask)
    if len(coords[axis]) == 0:
        center = mask.shape[axis] // 2
        return [center]
    values = coords[axis]
    if count <= 1:
        return [int(np.median(values))]
    quantiles = np.linspace(0.25, 0.75, count)
    return sorted({int(np.quantile(values, q)) for q in quantiles})


def _take_slice(array: np.ndarray, axis: int, index: int) -> np.ndarray:
    if axis == 0:
        return array[index, :, :]
    if axis == 1:
        return array[:, index, :]
    return array[:, :, index]


def generate_subject_overlays(
    image_array: np.ndarray,
    atlas_array: np.ndarray,
    result: VerificationResult,
    output_dir: Path,
    *,
    slices_per_axis: int = 3,
) -> VerificationStatus:
    """Generate read-only array-grid overlays without resampling."""
    if tuple(image_array.shape[:3]) != tuple(atlas_array.shape[:3]):
        return VerificationStatus.FAILED
    output_dir.mkdir(parents=True, exist_ok=True)
    image = np.asarray(image_array)
    atlas = np.asarray(atlas_array)
    if image.ndim == 4:
        image = image[0]
    support = atlas != 0
    axes = [(0, "sagittal"), (1, "coronal"), (2, "axial")]
    for axis, name in axes:
        fig, axs = plt.subplots(1, len(_slice_indices(support, axis, slices_per_axis)), figsize=(9, 3))
        if not isinstance(axs, np.ndarray):
            axs = np.asarray([axs])
        for ax, index in zip(axs, _slice_indices(support, axis, slices_per_axis), strict=False):
            img_slice = np.rot90(_take_slice(image, axis, index))
            atlas_slice = np.rot90(_take_slice(atlas, axis, index))
            finite = img_slice[np.isfinite(img_slice)]
            if finite.size:
                vmin, vmax = np.percentile(finite, [1, 99])
            else:
                vmin, vmax = 0.0, 1.0
            ax.imshow(img_slice, cmap="gray", vmin=vmin, vmax=vmax)
            masked = np.ma.masked_where(atlas_slice == 0, atlas_slice)
            ax.imshow(masked, cmap="tab20", alpha=0.35, interpolation="nearest")
            ax.set_title(f"{name} {index}", fontsize=8)
            ax.axis("off")
        fig.suptitle(
            f"{result.subject_hash} {result.cohort or 'UNKNOWN'} | "
            f"grid={result.geometry.array_grid_status.value} | "
            f"physical={result.geometry.physical_geometry_status.value}",
            fontsize=9,
        )
        if result.geometry.physical_geometry_status == VerificationStatus.INSUFFICIENT_METADATA:
            fig.text(0.5, 0.01, "ARRAY-GRID OVERLAY ONLY - PHYSICAL GEOMETRY UNVERIFIED", ha="center", fontsize=8)
        fig.tight_layout()
        fig.savefig(output_dir / f"{result.subject_hash}_{name}.png", dpi=120)
        plt.close(fig)
    return VerificationStatus.PASSED
