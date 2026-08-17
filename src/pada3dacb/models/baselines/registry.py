"""Strict, lazy registry for approved Phase 14 architectural baselines."""

from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module
from types import MappingProxyType
from typing import Any

from torch import nn

from pada3dacb.models.baselines.common import (
    BaselineSpec,
    parameter_metadata,
    reproducibility_hash,
)

_INPUT = "float32 MRI tensor [B, 1, D, H, W]"
_SPECS = (
    BaselineSpec(
        id="aagn",
        display_name="AAGN / ROI-aware gating",
        class_name="ROIAwareGatingBaseline",
        notebook_provenance="notebooks/archive/baselines_original.ipynb:cell-17:603-625",
        input_contract=_INPUT,
        requires_roi_masks=True,
        optional_dependencies=(),
        default_config=MappingProxyType(
            {"n_classes": 3, "base_ch": 32, "embed_dim": 128, "dropout": 0.1}
        ),
        output_classes=3,
    ),
    BaselineSpec(
        id="faster_snn",
        display_name="FasterSNN",
        class_name="FasterSNNBaseline",
        notebook_provenance="notebooks/archive/baselines_original.ipynb:cell-17:575-600",
        input_contract=_INPUT,
        requires_roi_masks=False,
        optional_dependencies=(),
        default_config=MappingProxyType(
            {"n_classes": 3, "base_ch": 16, "dropout": 0.1}
        ),
        output_classes=3,
    ),
)
_BY_ID = MappingProxyType({spec.id: spec for spec in _SPECS})
_ALIASES = MappingProxyType(
    {
        "roiawaregating": "aagn",
        "aagnstyle": "aagn",
        "roi-aware-gating": "aagn",
        "roi_gating": "aagn",
        "fastersnn": "faster_snn",
        "faster-snn": "faster_snn",
    }
)
_MODULES = MappingProxyType(
    {
        "aagn": "pada3dacb.models.baselines.roi_aware_gating",
        "faster_snn": "pada3dacb.models.baselines.faster_snn",
    }
)
_NAMES = tuple(spec.id for spec in _SPECS)


def list_baselines() -> tuple[str, ...]:
    """Return approved canonical ids in stable order."""
    return _NAMES


def get_baseline_spec(name: str) -> BaselineSpec:
    """Resolve a canonical id or an explicitly declared alias."""
    if not isinstance(name, str):
        raise TypeError("baseline name must be a string")
    canonical_id = name if name in _BY_ID else _ALIASES.get(name)
    if canonical_id is None:
        raise KeyError(f"Unknown or unapproved baseline: {name!r}")
    return _BY_ID[canonical_id]


def build_baseline(name: str, config: Mapping[str, Any]) -> nn.Module:
    """Construct an approved historical or explicitly task-scoped baseline.

    Historical calls retain the Phase 14 three-class contract.  A binary task is
    routed to the separate task builder and cannot silently alter that registry.
    """
    if not isinstance(config, Mapping):
        raise TypeError("baseline config must be a mapping")
    if "task_id" in config or "task" in config:
        from pada3dacb.binary import build_binary_baseline

        return build_binary_baseline(name, config)
    spec = get_baseline_spec(name)
    allowed = set(spec.default_config)
    if spec.requires_roi_masks:
        allowed.add("roi_masks")
    unsupported = sorted(set(config) - allowed)
    if unsupported:
        raise ValueError(f"Unsupported constructor keys for {spec.id}: {unsupported}")

    resolved = dict(spec.default_config)
    resolved.update(config)
    if resolved["n_classes"] != spec.output_classes or spec.output_classes != 3:
        raise ValueError("approved baselines must produce exactly 3 output classes")
    if spec.requires_roi_masks and resolved.get("roi_masks") is None:
        raise ValueError(f"{spec.id} requires roi_masks")

    module = import_module(_MODULES[spec.id])
    model_class = getattr(module, spec.class_name)
    model = model_class(**resolved)
    if not isinstance(model, nn.Module):
        raise TypeError(f"{spec.class_name} must construct a torch.nn.Module")
    model.baseline_metadata = {
        "canonical_id": spec.id,
        "resolved_config": resolved.copy(),
        "reproducibility_hash": reproducibility_hash(spec.id, resolved),
        **parameter_metadata(model),
    }
    return model


def build_task_baseline(name: str, config: Mapping[str, Any]) -> nn.Module:
    """Build a baseline only from an explicit task-bound configuration."""
    from pada3dacb.binary import build_binary_baseline

    return build_binary_baseline(name, config)
