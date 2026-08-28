"""Atomic checkpoints with complete fixed-epoch resume state."""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from acda3d import __version__
from acda3d.exceptions import TrainingRuntimeError


def configuration_hash(configuration: dict[str, Any]) -> str:
    encoded = json.dumps(configuration, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


_BINARY_TASK_ID = "cn_vs_impaired"
_BINARY_CLASS_ORDER = ["CN", "Impaired"]
_BINARY_MAPPING_CONTRACT = "phase-18b-binary-v1"


def validate_binary_checkpoint_metadata(checkpoint: dict[str, Any], *, model: nn.Module | None = None) -> None:
    """Validate the complete task-bound metadata before any binary state load."""
    if not isinstance(checkpoint, dict):
        raise TrainingRuntimeError("binary checkpoint metadata is required")
    if checkpoint.get("task_id") != _BINARY_TASK_ID:
        if checkpoint.get("class_order") == ["CN", "MCI", "AD"] or checkpoint.get("num_classes") == 3:
            raise TrainingRuntimeError("historical three-class checkpoint metadata is incompatible with binary cardinality")
        raise TrainingRuntimeError("binary two-class checkpoint metadata is incomplete: task_id=cn_vs_impaired is required")
    if checkpoint.get("class_order") not in (_BINARY_CLASS_ORDER, tuple(_BINARY_CLASS_ORDER)):
        raise TrainingRuntimeError("binary checkpoint metadata has incompatible class order or cardinality")
    if checkpoint.get("mapping_contract") != _BINARY_MAPPING_CONTRACT:
        raise TrainingRuntimeError("binary checkpoint metadata mapping contract is missing or tampered")
    split_identity = checkpoint.get("split_identity")
    split_hash = checkpoint.get("split_assignment_hash")
    if not isinstance(split_identity, str) or len(split_identity) != 64 or not all(c in "0123456789abcdef" for c in split_identity):
        raise TrainingRuntimeError("binary checkpoint metadata split identity/hash is missing or tampered")
    if not isinstance(split_hash, str) or len(split_hash) != 64 or not all(c in "0123456789abcdef" for c in split_hash):
        raise TrainingRuntimeError("binary checkpoint metadata split assignment hash is missing or tampered")
    payload = checkpoint.get("configuration_payload")
    payload_hash = checkpoint.get("configuration_payload_hash")
    if not isinstance(payload, dict) or not isinstance(payload_hash, str) or payload_hash != configuration_hash(payload):
        raise TrainingRuntimeError("binary checkpoint configuration payload/hash is missing or tampered")
    cardinality = checkpoint.get("binary_classifier_cardinality", checkpoint.get("classifier_cardinality", checkpoint.get("num_classes")))
    if cardinality != 2:
        raise TrainingRuntimeError("binary checkpoint classifier cardinality must be exactly two")
    if model is not None and getattr(model, "num_classes", None) != 2:
        raise TrainingRuntimeError("binary model must expose exactly two classifier outputs")


def _is_binary_checkpoint(checkpoint: dict[str, Any]) -> bool:
    return any(key in checkpoint for key in ("task_id", "mapping_contract", "binary_classifier_cardinality"))


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=5
        )
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def capture_rng_state() -> dict[str, Any]:
    state: dict[str, Any] = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        state["torch_cuda"] = torch.cuda.get_rng_state_all()
    return state


def restore_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch_cpu"])
    if "torch_cuda" in state and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["torch_cuda"])


def save_training_checkpoint(
    path: str | Path,
    *,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    scaler: Any,
    epoch: int,
    global_step: int,
    best_source_macro_f1: float,
    stage: str,
    resolved_configuration: dict[str, Any],
    split_assignment_hash: str,
    atlas_hash: str,
    roi_order_hash: str,
    random_seed: int,
    history_rows: list[dict[str, Any]],
    loader_generator_states: dict[str, torch.Tensor | None] | None = None,
    extra_payload: dict[str, Any] | None = None,
    task_id: str | None = None,
    class_order: list[str] | None = None,
    mapping_contract: str | None = None,
    split_identity: str | None = None,
    configuration_payload: dict[str, Any] | None = None,
    binary_classifier_cardinality: int | None = None,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
        "scaler_state_dict": scaler.state_dict() if scaler is not None else None,
        "epoch": int(epoch),
        "global_step": int(global_step),
        "best_source_macro_f1": float(best_source_macro_f1),
        "training_stage": stage,
        "resolved_configuration": resolved_configuration,
        "configuration_hash": configuration_hash(resolved_configuration),
        "split_assignment_hash": split_assignment_hash,
        "atlas_hash": atlas_hash,
        "roi_order_hash": roi_order_hash,
        "random_seed": int(random_seed),
        "rng_state": capture_rng_state(),
        "loader_generator_states": loader_generator_states or {},
        "history_rows": history_rows,
        "software_version": __version__,
        "git_commit": _git_commit(),
    }
    if extra_payload:
        protected = set(payload).intersection(extra_payload)
        if protected:
            raise TrainingRuntimeError(
                f"Checkpoint extra payload cannot replace core fields: {sorted(protected)}."
            )
        payload.update(extra_payload)
    if task_id is not None:
        binary_payload = {
            "task_id": task_id,
            "class_order": class_order,
            "mapping_contract": mapping_contract,
            "split_identity": split_identity,
            "configuration_payload": configuration_payload or resolved_configuration,
            "configuration_payload_hash": configuration_hash(configuration_payload or resolved_configuration),
            "binary_classifier_cardinality": binary_classifier_cardinality,
        }
        validate_binary_checkpoint_metadata({**payload, **binary_payload})
        payload.update(binary_payload)
    elif _is_binary_checkpoint(payload):
        validate_binary_checkpoint_metadata(payload)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        torch.save(payload, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def save_binary_training_checkpoint(path: str | Path, **kwargs: Any) -> Path:
    """Save a checkpoint through the mandatory binary metadata contract."""
    kwargs.setdefault("task_id", _BINARY_TASK_ID)
    kwargs.setdefault("class_order", list(_BINARY_CLASS_ORDER))
    kwargs.setdefault("mapping_contract", _BINARY_MAPPING_CONTRACT)
    return save_training_checkpoint(path, **kwargs)


def load_training_checkpoint(path: str | Path) -> dict[str, Any]:
    checkpoint = torch.load(Path(path), map_location="cpu", weights_only=False)
    required = {
        "model_state_dict", "optimizer_state_dict", "epoch", "global_step",
        "best_source_macro_f1", "resolved_configuration", "configuration_hash",
        "split_assignment_hash", "atlas_hash", "roi_order_hash", "rng_state",
    }
    missing = sorted(required - set(checkpoint))
    if missing:
        raise TrainingRuntimeError(f"Checkpoint is missing required fields: {missing}.")
    if _is_binary_checkpoint(checkpoint):
        validate_binary_checkpoint_metadata(checkpoint)
    return checkpoint


def load_binary_training_checkpoint(path: str | Path) -> dict[str, Any]:
    """Load only a complete, metadata-bound Phase 18B checkpoint."""
    checkpoint = torch.load(Path(path), map_location="cpu", weights_only=True)
    required = {"model_state_dict", "optimizer_state_dict", "epoch", "global_step", "rng_state"}
    missing = sorted(required - set(checkpoint)) if isinstance(checkpoint, dict) else ["checkpoint"]
    if missing:
        raise TrainingRuntimeError(f"Binary checkpoint is partial or missing required fields: {missing}.")
    validate_binary_checkpoint_metadata(checkpoint)
    return checkpoint


def restore_training_checkpoint(
    checkpoint: dict[str, Any],
    *,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    scaler: Any,
    resolved_configuration: dict[str, Any],
    split_assignment_hash: str,
    atlas_hash: str,
    roi_order_hash: str,
) -> None:
    expected = {
        "configuration_hash": configuration_hash(resolved_configuration),
        "split_assignment_hash": split_assignment_hash,
        "atlas_hash": atlas_hash,
        "roi_order_hash": roi_order_hash,
    }
    mismatches = [key for key, value in expected.items() if checkpoint.get(key) != value]
    if checkpoint["resolved_configuration"].get("model_name") != "3D-ACDA":
        mismatches.append("model_name")
    if mismatches:
        raise TrainingRuntimeError(f"Incompatible resume checkpoint fields: {sorted(set(mismatches))}.")
    if _is_binary_checkpoint(checkpoint):
        validate_binary_checkpoint_metadata(checkpoint, model=model)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    if scheduler is not None:
        if checkpoint.get("scheduler_state_dict") is None:
            raise TrainingRuntimeError("Resume checkpoint has no scheduler state.")
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
    if scaler is not None and checkpoint.get("scaler_state_dict") is not None:
        scaler.load_state_dict(checkpoint["scaler_state_dict"])
    restore_rng_state(checkpoint["rng_state"])
