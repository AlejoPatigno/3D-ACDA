"""Canonical MRI-only regional tissue-loss concept targets."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch

from pada3dacb import __version__
from pada3dacb.artifacts.atlas import AtlasROIManager
from pada3dacb.artifacts.regional_features import masked_fraction_at_or_below


@dataclass
class ConceptTargetConfig:
    brain_threshold: float = 0.0
    low_intensity_percentile: float = 20.0
    eps: float = 1e-6
    normal_class_name: str = "CN"


def to_plain_tensor(value: Any, *, expected_shape: Sequence[int] | None = None) -> torch.Tensor:
    tensor = value.detach().cpu() if torch.is_tensor(value) else torch.as_tensor(value)
    tensor = torch.tensor(tensor.numpy(), dtype=torch.float32).contiguous()
    if expected_shape is not None and tuple(tensor.shape) != tuple(expected_shape):
        raise ValueError(f"Expected tensor shape {tuple(expected_shape)}, got {tuple(tensor.shape)}.")
    if not torch.isfinite(tensor).all():
        raise ValueError("Tensor contains non-finite values.")
    return tensor


def _volume(value: torch.Tensor | np.ndarray) -> np.ndarray:
    array = value.detach().cpu().numpy() if torch.is_tensor(value) else np.asarray(value)
    array = np.asarray(array, dtype=np.float32)
    if array.ndim == 4 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 3:
        raise ValueError(f"Expected (H,W,D) or (1,H,W,D), got {array.shape}.")
    if not np.isfinite(array).all():
        raise ValueError("MRI tensor contains non-finite values.")
    return array


def extract_tissue_loss_proxy(value: torch.Tensor | np.ndarray, atlas_mgr: AtlasROIManager, cfg: ConceptTargetConfig | None = None) -> np.ndarray:
    cfg = cfg or ConceptTargetConfig()
    volume = _volume(value)
    masks = atlas_mgr.get_binary_masks(volume.shape)
    brain = volume[volume > cfg.brain_threshold]
    if brain.size == 0:
        raise ValueError("Empty brain mask after thresholding; cannot compute concept targets.")
    threshold = float(np.percentile(brain, cfg.low_intensity_percentile))
    return masked_fraction_at_or_below(volume, masks, threshold).astype(np.float32)


@dataclass
class ConceptNormalizer:
    mu: np.ndarray
    sigma: np.ndarray
    eps: float = 1e-6
    roi_labels: list[int] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def transform(self, features: np.ndarray) -> np.ndarray:
        values = np.asarray(features, dtype=np.float32)
        if values.ndim == 1:
            values = values[None, :]
        z_score = (values - self.mu[None, :]) / (self.sigma[None, :] + self.eps)
        return (1.0 / (1.0 + np.exp(-z_score))).astype(np.float32)

    def to_dict(self) -> dict[str, Any]:
        return {"mu": self.mu.tolist(), "sigma": self.sigma.tolist(), "eps": self.eps, "roi_labels": self.roi_labels, "provenance": self.provenance}

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, target)

    @classmethod
    def load(cls, path: str | Path) -> ConceptNormalizer:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(np.asarray(payload["mu"], dtype=np.float32), np.asarray(payload["sigma"], dtype=np.float32), float(payload["eps"]), [int(v) for v in payload.get("roi_labels", [])], payload.get("provenance", {}))


def fit_concept_normalizer(
    features: np.ndarray,
    labels: Sequence[str] | Sequence[int],
    normal_label: str | int = "CN",
    eps: float = 1e-6,
    *,
    roi_labels: Sequence[int] = (),
    cohorts: Sequence[str] | None = None,
    configuration_hash: str | None = None,
    inventory_hash: str | None = None,
) -> ConceptNormalizer:
    values = np.asarray(features, dtype=np.float32)
    classes = np.asarray(labels)
    mask = classes == normal_label
    if values.ndim != 2 or values.shape[0] != classes.shape[0]:
        raise ValueError("Concept features and labels have incompatible shapes.")
    if not np.any(mask):
        raise ValueError(f"No samples found for normal_label={normal_label!r}.")
    reference = values[mask]
    cohort_values = np.asarray(cohorts)[mask].tolist() if cohorts is not None else []
    provenance = {
        "normalizer_scope": "per supplied inventory/cohort",
        "normal_class_name": str(normal_label),
        "number_of_fitted_subjects": int(mask.sum()),
        "class_composition": {str(normal_label): int(mask.sum())},
        "cohort_composition": {str(value): cohort_values.count(value) for value in sorted(set(cohort_values))},
        "configuration_hash": configuration_hash,
        "source_inventory_hash": inventory_hash,
        "software_version": __version__,
        "statistics": "population mean and population standard deviation (ddof=0)",
        "output_transformation": "sigmoid((s-mu)/(sigma+eps))",
    }
    return ConceptNormalizer(reference.mean(0).astype(np.float32), reference.std(0).astype(np.float32), eps, [int(v) for v in roi_labels], provenance)


def build_subject_concept_target(value: torch.Tensor | np.ndarray, atlas_mgr: AtlasROIManager, normalizer: ConceptNormalizer, cfg: ConceptTargetConfig | None = None) -> torch.Tensor:
    proxy = extract_tissue_loss_proxy(value, atlas_mgr, cfg)
    return torch.from_numpy(normalizer.transform(proxy)[0])


def save_plain_mri_pt(value: Any, path: str | Path, *, key: str = "x") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    del key
    torch.save(to_plain_tensor(value), temporary)
    os.replace(temporary, target)


def precompute_concept_targets_from_dataframe(df: Any, atlas_mgr: AtlasROIManager, x_column: str = "x_path", label_column: str = "label", subject_id_column: str = "subject_id", output_dir: str | Path = "./concept_targets", cfg: ConceptTargetConfig | None = None) -> tuple[ConceptNormalizer, Any]:
    import pandas as pd

    cfg = cfg or ConceptTargetConfig()
    features = []
    for path in df[x_column]:
        obj = torch.load(path, map_location="cpu", weights_only=True)
        value = next((obj[k] for k in ("x", "image", "mri", "tensor", "volume") if isinstance(obj, dict) and k in obj), obj)
        features.append(extract_tissue_loss_proxy(value, atlas_mgr, cfg))
    values = np.stack(features)
    normalizer = fit_concept_normalizer(values, df[label_column].tolist(), cfg.normal_class_name, cfg.eps, roi_labels=atlas_mgr.label_values, cohorts=df["cohort"].tolist() if "cohort" in df else None)
    root = Path(output_dir)
    rows = []
    for (_, row), target in zip(df.iterrows(), normalizer.transform(values), strict=True):
        path = root / f"{row[subject_id_column]}_c_target.pt"
        save_plain_mri_pt(target, path, key="c_target")
        rows.append({"subject_id": row[subject_id_column], "label": row[label_column], "x_path": row[x_column], "concept_target_path": str(path)})
    normalizer.save(root / "concept_normalizer.json")
    return normalizer, pd.DataFrame(rows)
