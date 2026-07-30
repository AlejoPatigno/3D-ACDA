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

from pada3dacb import __version__
from pada3dacb.exceptions import TrainingRuntimeError


def configuration_hash(configuration: dict[str, Any]) -> str:
    encoded = json.dumps(configuration, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


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
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        torch.save(payload, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


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
    if checkpoint["resolved_configuration"].get("model_name") != "PADA-3DACB":
        mismatches.append("model_name")
    if mismatches:
        raise TrainingRuntimeError(f"Incompatible resume checkpoint fields: {sorted(set(mismatches))}.")
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    if scheduler is not None:
        if checkpoint.get("scheduler_state_dict") is None:
            raise TrainingRuntimeError("Resume checkpoint has no scheduler state.")
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
    if scaler is not None and checkpoint.get("scaler_state_dict") is not None:
        scaler.load_state_dict(checkpoint["scaler_state_dict"])
    restore_rng_state(checkpoint["rng_state"])
