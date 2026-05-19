
"""
concept_targets.py
==================
Section K of the Materials and Methods.

This module implements a practical MRI-only anatomical target c_tilde_{n,k}
for each ROI. Because the Kaggle derivatives may not ship FreeSurfer-based
cortical thickness or per-region morphometric spreadsheets, we implement an
atlas-based tissue-loss summary that is directly computable from the 3D MRI.

The default biomarker is:
    s_{n,k} = fraction of ROI voxels below the subject-specific q-th
              percentile of the intracranial intensity distribution

This makes s_{n,k} a bounded regional tissue-loss proxy. It is then converted
into a concept target in [0,1] through a CN-referenced z-score and a sigmoid:
    c_tilde_{n,k} = sigmoid((s_{n,k} - mu_k_CN) / (sigma_k_CN + eps))

If you later obtain stronger morphometric measurements, only the extractor
function needs to be replaced; the normalizer and cache protocol can remain.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Sequence, Union

import numpy as np
import torch

ArrayLikePath = Union[str, Path]

@dataclass
class ConceptTargetConfig:
    brain_threshold: float = 0.0
    low_intensity_percentile: float = 20.0
    eps: float = 1e-6
    normal_class_name: str = "CN"


def _safe_torch_load(path):
    obj = torch.load(str(path), map_location="cpu", weights_only=False)

    if torch.is_tensor(obj):
        x = obj
    elif isinstance(obj, dict):
        x = None
        for key in ["x", "image", "mri", "tensor", "volume"]:
            if key in obj:
                x = obj[key]
                break
        if x is None:
            raise KeyError(f"No se encontró tensor MRI en {path}")
    else:
        x = torch.as_tensor(obj)

    if not torch.is_tensor(x):
        x = torch.as_tensor(x)

    x = x.detach().to(torch.float32)
    x = torch.tensor(x.cpu().numpy(), dtype=torch.float32)
    return x


def _unwrap_tensorlike(obj):
    """
    Accept:
      - plain Tensor / MetaTensor
      - dict with keys like 'x', 'image', 'mri', 'tensor', 'volume'
    """
    if torch.is_tensor(obj):
        return obj

    if isinstance(obj, dict):
        for key in ["x", "image", "mri", "tensor", "volume"]:
            if key in obj:
                x = obj[key]
                if torch.is_tensor(x):
                    return x
                return torch.as_tensor(x)

    # final fallback
    return torch.as_tensor(obj)


def _to_numpy_volume(x: torch.Tensor | np.ndarray) -> np.ndarray:
    if torch.is_tensor(x):
        x = x.detach().cpu().numpy()
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 4 and x.shape[0] == 1:
        x = x[0]
    if x.ndim != 3:
        raise ValueError(f"Expected 3D volume or (1,H,W,D), got shape {x.shape}.")
    return x.astype(np.float32)


def extract_tissue_loss_proxy(
    x: torch.Tensor | np.ndarray,
    atlas_mgr: AtlasROIManager,
    cfg: Optional[ConceptTargetConfig] = None,
) -> np.ndarray:
    cfg = cfg or ConceptTargetConfig()
    vol = _to_numpy_volume(x)
    roi_masks = atlas_mgr.get_binary_masks(vol.shape).cpu().numpy()   # (K,H,W,D)

    brain = vol[vol > cfg.brain_threshold]
    if brain.size == 0:
        raise ValueError("Empty brain mask after thresholding; cannot compute concept targets.")

    q = np.percentile(brain, cfg.low_intensity_percentile)
    proxy = np.zeros(atlas_mgr.K, dtype=np.float32)

    for k in range(atlas_mgr.K):
        mask = roi_masks[k] > 0
        if not np.any(mask):
            continue
        roi_vals = vol[mask]
        proxy[k] = float((roi_vals <= q).mean())

    return proxy.astype(np.float32)



def _to_torch_volume(x, device):
    if torch.is_tensor(x):
        vol = x.detach()
    else:
        vol = torch.as_tensor(x)

    vol = vol.float()

    # admitir (1,H,W,D) o (H,W,D)
    if vol.ndim == 4 and vol.shape[0] == 1:
        vol = vol[0]
    elif vol.ndim != 3:
        raise ValueError(f"Se esperaba volumen 3D o (1,H,W,D), llegó {tuple(vol.shape)}")

    return vol.to(device, non_blocking=True)


@dataclass
class ConceptNormalizer:
    mu: np.ndarray
    sigma: np.ndarray
    eps: float = 1e-6

    def transform(self, features: np.ndarray) -> np.ndarray:
        z = (features - self.mu[None, :]) / (self.sigma[None, :] + self.eps)
        return 1.0 / (1.0 + np.exp(-z))

    def save(self, path: ArrayLikePath) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mu": self.mu.tolist(),
            "sigma": self.sigma.tolist(),
            "eps": float(self.eps),
        }
        path.write_text(json.dumps(payload, indent=2))

    @classmethod
    def load(cls, path: ArrayLikePath) -> "ConceptNormalizer":
        payload = json.loads(Path(path).read_text())
        return cls(
            mu=np.asarray(payload["mu"], dtype=np.float32),
            sigma=np.asarray(payload["sigma"], dtype=np.float32),
            eps=float(payload["eps"]),
        )


def fit_concept_normalizer(
    features: np.ndarray,
    labels: Sequence[str] | Sequence[int],
    normal_label: str | int = "CN",
    eps: float = 1e-6,
) -> ConceptNormalizer:
    features = np.asarray(features, dtype=np.float32)
    labels = np.asarray(labels)
    mask = labels == normal_label
    if mask.sum() == 0:
        raise ValueError(f"No samples found for normal_label={normal_label!r}.")
    ref = features[mask]
    mu = ref.mean(axis=0).astype(np.float32)
    sigma = ref.std(axis=0).astype(np.float32)
    return ConceptNormalizer(mu=mu, sigma=sigma, eps=eps)



def build_subject_concept_target(
    x: torch.Tensor | np.ndarray,
    atlas_mgr: AtlasROIManager,
    normalizer: ConceptNormalizer,
    cfg: Optional[ConceptTargetConfig] = None,
) -> torch.Tensor:
    feats = extract_tissue_loss_proxy(x, atlas_mgr, cfg=cfg)[None, :]
    c_tilde = normalizer.transform(feats)[0]
    return torch.from_numpy(c_tilde.astype(np.float32))


def precompute_concept_targets_from_dataframe(
    df,
    atlas_mgr: AtlasROIManager,
    x_column: str = "x_path",
    label_column: str = "label",
    subject_id_column: str = "subject_id",
    output_dir: ArrayLikePath = "./concept_targets",
    cfg: Optional[ConceptTargetConfig] = None,
) -> tuple[ConceptNormalizer, "pd.DataFrame"]:
    import pandas as pd

    cfg = cfg or ConceptTargetConfig()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_features = []
    labels = []
    rows = []

    for _, row in df.iterrows():
        x = _safe_torch_load(row[x_column])
        feats = extract_tissue_loss_proxy(x, atlas_mgr, cfg=cfg)
        raw_features.append(feats)
        labels.append(row[label_column])

        rows.append({
            "subject_id": row[subject_id_column],
            "label": row[label_column],
            "x_path": row[x_column],
        })

    raw_features = np.stack(raw_features, axis=0)
    normalizer = fit_concept_normalizer(
        raw_features,
        labels=labels,
        normal_label=cfg.normal_class_name,
        eps=cfg.eps,
    )

    out_rows = []
    transformed = normalizer.transform(raw_features)

    for meta, c_tilde in zip(rows, transformed):
        save_path = output_dir / f"{meta['subject_id']}_c_target.pt"
        save_plain_vector_pt(torch.from_numpy(c_tilde.astype(np.float32)), save_path, key="c_target")

        out_rows.append({
            **meta,
            "concept_target_path": str(save_path),
        })

    normalizer.save(output_dir / "concept_normalizer.json")
    return normalizer, pd.DataFrame(out_rows)
    