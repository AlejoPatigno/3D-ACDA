"""Prepared discrete-atlas handling extracted from the canonical notebook."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import torch

from acda3d.exceptions import ArtifactValidationError


@dataclass
class AtlasConfig:
    label_values: Sequence[int] | None = None
    drop_background: bool = True
    eps: float = 1e-8
    min_voxels_per_roi: int = 1
    expected_num_rois: int | None = 102


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_label_atlas(path: str | Path) -> tuple[nib.spatialimages.SpatialImage, np.ndarray]:
    """Load a prepared atlas and reject lossy label coercion."""
    image = nib.as_closest_canonical(nib.load(str(path)))
    atlas = image.get_fdata(dtype=np.float32)
    if atlas.ndim == 4 and atlas.shape[-1] == 1:
        atlas = atlas[..., 0]
    if atlas.ndim != 3:
        raise ArtifactValidationError(f"Prepared atlas must be 3D, got {atlas.shape}.")
    if not np.isfinite(atlas).all():
        raise ArtifactValidationError("Prepared atlas contains non-finite labels.")
    if not np.allclose(atlas, np.rint(atlas), rtol=0.0, atol=1e-5):
        raise ArtifactValidationError("Prepared atlas labels are not integer-like.")
    return image, np.rint(atlas).astype(np.int32)


def infer_label_values(atlas: np.ndarray, drop_background: bool = True, min_voxels_per_roi: int = 1) -> list[int]:
    values = sorted(int(value) for value in np.unique(atlas))
    if drop_background:
        values = [value for value in values if value != 0]
    return [value for value in values if int((atlas == value).sum()) >= min_voxels_per_roi]


def validate_atlas_grid(atlas_shape: Sequence[int], spatial_shape: Sequence[int]) -> None:
    if tuple(atlas_shape) != tuple(spatial_shape):
        raise ArtifactValidationError(
            f"Prepared atlas grid {tuple(atlas_shape)} does not match MRI grid {tuple(spatial_shape)}; Phase 5 does not resample atlases."
        )


def build_roi_masks(atlas: np.ndarray, labels: Sequence[int]) -> torch.Tensor:
    if not labels:
        raise ArtifactValidationError("No ROI labels were found in the prepared atlas.")
    masks = torch.from_numpy(np.stack([(atlas == int(label)).astype(np.float32) for label in labels]))
    empty = torch.where(masks.flatten(1).sum(1) == 0)[0].tolist()
    if empty:
        raise ArtifactValidationError(f"Prepared atlas has empty ROI masks at positions {empty}.")
    return masks


class AtlasROIManager:
    def __init__(self, atlas_path: str | Path, config: AtlasConfig | None = None):
        self.atlas_path = str(Path(atlas_path).resolve())
        self.config = config or AtlasConfig()
        self.atlas_img, self.atlas_np = load_label_atlas(self.atlas_path)
        self.affine = np.asarray(self.atlas_img.affine).copy()
        self.shape = tuple(int(value) for value in self.atlas_np.shape)
        self.label_values = (
            [int(value) for value in self.config.label_values]
            if self.config.label_values is not None
            else infer_label_values(self.atlas_np, self.config.drop_background, self.config.min_voxels_per_roi)
        )
        self.atlas_tensor = build_roi_masks(self.atlas_np, self.label_values)
        self.roi_volumes = self.atlas_tensor.flatten(1).sum(1).long()
        self.K = len(self.label_values)
        if self.config.expected_num_rois is not None:
            self.maybe_validate_K(self.config.expected_num_rois)
        self.atlas_hash = _sha256(self.atlas_path)

    def get_binary_masks(self, target_shape: Sequence[int] | None = None, device: torch.device | None = None, dtype: torch.dtype = torch.float32) -> torch.Tensor:
        if target_shape is not None:
            validate_atlas_grid(self.shape, target_shape)
        return self.atlas_tensor.to(device=device, dtype=dtype)

    def get_masks(self, target_shape: Sequence[int] | None = None, normalize: bool = True, device: torch.device | None = None, dtype: torch.dtype = torch.float32) -> torch.Tensor:
        masks = self.get_binary_masks(target_shape, dtype=torch.float32)
        if normalize:
            masks = masks / masks.flatten(1).sum(1).clamp_min(self.config.eps).view(-1, 1, 1, 1)
        return masks.to(device=device, dtype=dtype)

    def maybe_validate_K(self, expected: int) -> None:
        if int(expected) != self.K:
            raise ArtifactValidationError(f"Prepared atlas has K={self.K}, expected K={int(expected)}.")

    def summary(self) -> dict[str, Any]:
        return {"atlas_path": self.atlas_path, "atlas_hash": self.atlas_hash, "shape": list(self.shape), "K": self.K, "label_values": self.label_values, "roi_volumes": self.roi_volumes.tolist(), "configuration": asdict(self.config)}


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def export_atlas_metadata(manager: AtlasROIManager, output_dir: str | Path) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    metadata = root / "atlas_metadata.json"
    labels = root / "roi_labels.json"
    masks = root / "roi_masks.pt"
    _atomic_json(metadata, manager.summary())
    _atomic_json(labels, {"label_values": manager.label_values, "atlas_hash": manager.atlas_hash})
    temporary = masks.with_name(f".{masks.name}.{os.getpid()}.tmp")
    torch.save({"roi_masks": manager.atlas_tensor, "label_values": manager.label_values, "atlas_hash": manager.atlas_hash}, temporary)
    os.replace(temporary, masks)
    return {"metadata": metadata, "labels": labels, "masks": masks}
