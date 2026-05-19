
"""
atlas_utils.py
==============
Section C of the Materials and Methods.

Defines an atlas manager that:
  1. Loads an integer-valued atlas in template space.
  2. Extracts ROI masks {R_k}_{k=1}^K.
  3. Resamples those masks either to image space or feature-map space.
  4. Normalizes each ROI mask so that its support sums to 1, matching the
     masked pooling formula used by ROITokenizer.

The module does not assume a specific atlas vendor. It only requires a NIfTI
label map with integer region identifiers.
"""



from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union

import nibabel as nib
import numpy as np
import torch
import torch.nn.functional as F

ArrayLikePath = Union[str, Path]


@dataclass
class AtlasConfig:
    label_values: Optional[Sequence[int]] = None
    drop_background: bool = True
    eps: float = 1e-8
    min_voxels_per_roi: int = 1


def load_label_atlas(path: ArrayLikePath):
    img = nib.load(str(path))
    img = nib.as_closest_canonical(img)
    atlas = img.get_fdata(dtype=np.float32)

    if atlas.ndim == 4:
        atlas = atlas[..., 0]

    atlas = np.rint(atlas).astype(np.int32)
    return img, atlas


def infer_label_values(
    atlas: np.ndarray,
    drop_background: bool = True,
    min_voxels_per_roi: int = 1,
) -> list[int]:
    vals = np.unique(atlas).tolist()
    vals = [int(v) for v in vals]

    if drop_background:
        vals = [v for v in vals if v != 0]

    if min_voxels_per_roi > 1:
        vals = [v for v in vals if int((atlas == v).sum()) >= min_voxels_per_roi]

    return sorted(vals)


class AtlasROIManager:
    def __init__(self, atlas_path: ArrayLikePath, config: Optional[AtlasConfig] = None):
        self.atlas_path = str(atlas_path)
        self.config = config or AtlasConfig()

        self.atlas_img, self.atlas_np = load_label_atlas(self.atlas_path)
        self.affine = self.atlas_img.affine.copy()
        self.shape = tuple(int(v) for v in self.atlas_np.shape)

        if self.config.label_values is not None:
            self.label_values = [int(v) for v in self.config.label_values]
        else:
            self.label_values = infer_label_values(
                self.atlas_np,
                drop_background=self.config.drop_background,
                min_voxels_per_roi=self.config.min_voxels_per_roi,
            )

        self.K = len(self.label_values)

        self._atlas_onehot = self._build_onehot(self.atlas_np, self.label_values)
        self.atlas_tensor = self._atlas_onehot  # alias público

        self.roi_volumes = self._atlas_onehot.flatten(1).sum(dim=1).long()

        self._validate_nonempty()

    @staticmethod
    def _build_onehot(atlas: np.ndarray, label_values: Sequence[int]) -> torch.Tensor:
        masks = []
        for lab in label_values:
            masks.append((atlas == int(lab)).astype(np.float32))

        if len(masks) == 0:
            raise ValueError("No ROI labels were found in the atlas.")

        onehot = np.stack(masks, axis=0)  # (K, H, W, D)
        return torch.from_numpy(onehot)

    def _validate_nonempty(self):
        empty = (self.roi_volumes <= 0).nonzero(as_tuple=False).flatten().tolist()
        if len(empty) > 0:
            bad_labels = [self.label_values[i] for i in empty]
            raise ValueError(
                f"El atlas contiene ROIs vacías después de cargarlo. "
                f"indices={empty}, labels={bad_labels}"
            )

    @staticmethod
    def _resize_masks(masks: torch.Tensor, target_shape: Sequence[int]) -> torch.Tensor:
        """
        masks: (K, H, W, D)
        output: (K, Ht, Wt, Dt)
        """
        if len(target_shape) != 3:
            raise ValueError(f"target_shape debe tener longitud 3, llegó: {target_shape}")

        x = masks.unsqueeze(1)  # (K,1,H,W,D)
        x = F.interpolate(x, size=tuple(int(v) for v in target_shape), mode="nearest")
        return x.squeeze(1)

    @staticmethod
    def _normalize_masks(masks: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
        flat = masks.flatten(1)
        denom = flat.sum(dim=1, keepdim=True).clamp_min(eps)
        flat = flat / denom
        return flat.view_as(masks)

    def get_masks(
        self,
        target_shape: Sequence[int],
        normalize: bool = True,
        device: Optional[torch.device] = None,
        dtype: torch.dtype = torch.float32,
    ) -> torch.Tensor:
        """
        Devuelve máscaras ROI remuestreadas al shape objetivo.
        Salida: (K, Ht, Wt, Dt)
        """
        masks = self._resize_masks(self._atlas_onehot.float(), target_shape)

        if normalize:
            masks = self._normalize_masks(masks, eps=self.config.eps)

        masks = masks.to(dtype=dtype)

        if device is not None:
            masks = masks.to(device)

        return masks

    def get_binary_masks(
        self,
        target_shape: Sequence[int],
        device: Optional[torch.device] = None,
        dtype: torch.dtype = torch.float32,
    ) -> torch.Tensor:
        masks = self._resize_masks(self._atlas_onehot.float(), target_shape)
        masks = (masks > 0.5).to(dtype=dtype)

        if device is not None:
            masks = masks.to(device)

        return masks

    def roi_weights_from_volume(
        self,
        power: float = 0.0,
        device: Optional[torch.device] = None,
        dtype: torch.dtype = torch.float32,
    ) -> torch.Tensor:
        """
        power = 0.0 -> pesos uniformes
        power > 0.0 -> inverse-volume weighting^power, renormalizado
        """
        vol = self._atlas_onehot.flatten(1).sum(dim=1).float().clamp_min(1.0)

        if power <= 0:
            w = torch.ones_like(vol)
        else:
            w = (1.0 / vol) ** power

        w = w / w.sum().clamp_min(self.config.eps)
        w = w.to(dtype=dtype)

        if device is not None:
            w = w.to(device)

        return w

    def maybe_validate_K(self, K_expected: int) -> None:
        if self.K != int(K_expected):
            raise ValueError(
                f"Atlas has K={self.K} regions, but the model/loss expects K={int(K_expected)}."
            )

    def summary(self) -> dict:
        return {
            "atlas_path": self.atlas_path,
            "shape": self.shape,
            "K": self.K,
            "label_min": int(min(self.label_values)) if self.K > 0 else None,
            "label_max": int(max(self.label_values)) if self.K > 0 else None,
            "n_background_voxels": int((self.atlas_np == 0).sum()),
            "roi_volumes_min": int(self.roi_volumes.min().item()) if self.K > 0 else None,
            "roi_volumes_max": int(self.roi_volumes.max().item()) if self.K > 0 else None,
        }
        