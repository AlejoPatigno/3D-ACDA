"""Audited retained-weight migration from historical Lite checkpoints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch import nn

from pada3dacb.exceptions import CheckpointMigrationError

RENAMED_PREFIXES = {
    "roi_tokenizer.": "tokenizer.",
    "classification_head.": "cls_head.",
    "latent_classification_head.": "cls_head.",
    "concept_bottleneck.": "cbm.",
}
FULL_ONLY_PREFIXES = ("ctx_enc.", "contextual_encoder.")
STATE_DICT_FIELDS = ("model_state_dict", "state_dict", "model")


@dataclass(frozen=True)
class CheckpointMigrationReport:
    loaded_keys: tuple[str, ...]
    dropped_full_only_keys: tuple[str, ...]
    renamed_keys: tuple[tuple[str, str], ...]
    missing_retained_keys: tuple[str, ...]
    unexpected_keys: tuple[str, ...]


def _locate_state_dict(checkpoint: Any) -> dict[str, torch.Tensor]:
    if isinstance(checkpoint, (str, Path)):
        checkpoint = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict):
        raise CheckpointMigrationError("Checkpoint must be a path or dictionary.")
    if checkpoint and all(torch.is_tensor(value) for value in checkpoint.values()):
        return checkpoint
    matches = [field for field in STATE_DICT_FIELDS if isinstance(checkpoint.get(field), dict)]
    if len(matches) != 1:
        raise CheckpointMigrationError(
            "Checkpoint must contain exactly one explicit model state dictionary field."
        )
    state = checkpoint[matches[0]]
    if not all(isinstance(key, str) and torch.is_tensor(value) for key, value in state.items()):
        raise CheckpointMigrationError("Located model state dictionary contains invalid entries.")
    return state


def _rename_key(key: str) -> tuple[str, bool]:
    source = key.removeprefix("module.")
    for old, new in RENAMED_PREFIXES.items():
        if source.startswith(old):
            return new + source[len(old) :], True
    return source, source != key


def migrate_legacy_lite_state_dict(
    checkpoint: Any,
    model: nn.Module,
    *,
    strict_retained: bool = True,
) -> tuple[dict[str, torch.Tensor], CheckpointMigrationReport]:
    """Extract compatible retained tensors without reconstructing the Full model."""
    legacy = _locate_state_dict(checkpoint)
    target = model.state_dict()
    migrated: dict[str, torch.Tensor] = {}
    dropped: list[str] = []
    renamed: list[tuple[str, str]] = []
    unexpected: list[str] = []
    for original_key, tensor in legacy.items():
        key_without_module = original_key.removeprefix("module.")
        if key_without_module.startswith(FULL_ONLY_PREFIXES):
            dropped.append(original_key)
            continue
        key, changed = _rename_key(original_key)
        if changed:
            renamed.append((original_key, key))
        if key not in target:
            unexpected.append(original_key)
            continue
        if tuple(tensor.shape) != tuple(target[key].shape):
            raise CheckpointMigrationError(
                f"Incompatible retained tensor {original_key!r}: checkpoint {tuple(tensor.shape)} "
                f"!= model {tuple(target[key].shape)}."
            )
        if key in migrated:
            raise CheckpointMigrationError(f"Multiple legacy keys map to retained key {key!r}.")
        migrated[key] = tensor
    missing = sorted(set(target) - set(migrated))
    report = CheckpointMigrationReport(
        loaded_keys=tuple(sorted(migrated)),
        dropped_full_only_keys=tuple(sorted(dropped)),
        renamed_keys=tuple(sorted(renamed)),
        missing_retained_keys=tuple(missing),
        unexpected_keys=tuple(sorted(unexpected)),
    )
    if unexpected:
        raise CheckpointMigrationError(f"Unexpected legacy keys: {sorted(unexpected)}")
    if strict_retained and missing:
        raise CheckpointMigrationError(f"Missing retained keys: {missing}")
    return migrated, report


def load_binary_checkpoint(model: nn.Module, checkpoint: Any) -> nn.Module:
    """Load a complete Phase 18B checkpoint only after metadata validation."""
    from pada3dacb.binary import load_binary_checkpoint as _load_binary_checkpoint
    from pada3dacb.training.checkpointing import validate_binary_checkpoint_metadata

    metadata = checkpoint
    if isinstance(checkpoint, (str, Path)):
        metadata = torch.load(checkpoint, weights_only=True, map_location="cpu")
    if not isinstance(metadata, dict):
        raise CheckpointMigrationError("binary checkpoint metadata is required; unsafe fallback is prohibited")
    try:
        validate_binary_checkpoint_metadata(metadata, model=model)
    except Exception as error:
        if isinstance(error, CheckpointMigrationError):
            raise
        raise CheckpointMigrationError(str(error)) from error
    try:
        return _load_binary_checkpoint(model, metadata)
    except Exception as error:
        if isinstance(error, CheckpointMigrationError):
            raise
        raise CheckpointMigrationError("binary checkpoint load failed; partial loading is prohibited") from error


def load_migrated_legacy_checkpoint(
    model: nn.Module,
    checkpoint: Any,
    *,
    strict_retained: bool = True,
) -> CheckpointMigrationReport:
    """Migrate then load retained weights into an explicit production model."""
    state, report = migrate_legacy_lite_state_dict(
        checkpoint, model, strict_retained=strict_retained
    )
    model.load_state_dict(state, strict=strict_retained)
    return report
