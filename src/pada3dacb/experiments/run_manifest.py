"""Atomic manifests for approved source-only and adaptation experiments."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from pada3dacb import __version__
from pada3dacb.binary import (
    BINARY_CLASS_ORDER,
    BINARY_MAPPING_CONTRACT,
    BINARY_TASK,
    SUPERSESSION_MARKER,
)
from pada3dacb.exceptions import ExperimentValidationError

RUN_STATUSES = {"PENDING", "RUNNING", "INTERRUPTED", "COMPLETED", "FAILED"}


def ablation_output_path(
    output_root: str | Path,
    ablation_id: str,
    direction: str,
    seed: int,
    fold: int,
) -> Path:
    """Return the Phase 17 path without creating it or discovering data."""
    return (
        Path(output_root)
        / "ablations"
        / str(ablation_id)
        / str(direction)
        / f"seed_{int(seed)}"
        / f"fold_{int(fold)}"
    )


def create_ablation_manifest(**values: Any) -> dict[str, Any]:
    """Create a timestamp-free, synthetic-only ablation identity envelope."""
    required = {
        "method": "ablation",
        "base_method": "prototype_pseudo",
        "real_data_run": False,
        "publication_metrics_present": False,
    }
    manifest = {**required, **values}
    manifest.setdefault("schema_version", "phase17.ablation-manifest.v1")
    manifest.setdefault("phase", 17)
    manifest.setdefault("synthetic", True)
    manifest.setdefault("target_label_firewall", {
        "target_adaptation_batch_keys": ["x", "subject_id", "subject_hash", "cohort"],
        "target_labels_in_adaptation": False,
    })
    return manifest


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def atomic_json(path: str | Path, payload: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def runtime_environment() -> dict[str, Any]:
    gpu_name = None
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
    return {
        "package_version": __version__,
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "gpu_name": gpu_name,
        "git_commit": git_commit(),
    }


def _reject_public_subject_ids(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).casefold() in {"subject_id", "raw_subject_id", "raw_id"}:
                raise ExperimentValidationError("public binary identities must not contain raw subject IDs")
            _reject_public_subject_ids(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_public_subject_ids(nested)


def create_run_manifest(**values: Any) -> dict[str, Any]:
    if str(values.get("task_id", "")).casefold() == "cn_vs_impaired":
        _reject_public_subject_ids(values)
        values = {
            **values,
            "task_id": "cn_vs_impaired",
            "task": BINARY_TASK,
            "class_order": list(BINARY_CLASS_ORDER),
            "mapping_contract": BINARY_MAPPING_CONTRACT,
            "supersession_marker": SUPERSESSION_MARKER,
            "binary_task": True,
        }
    manifest = {
        **values,
        **runtime_environment(),
        "status": "PENDING",
        "start_time": None,
        "completion_time": None,
        "checkpoint_paths": {},
    }
    if manifest.get("task_id") == "cn_vs_impaired":
        identity_payload = {key: value for key, value in manifest.items() if key not in {"start_time", "completion_time", "status", "checkpoint_paths"}}
        manifest["identity_hash"] = stable_hash(identity_payload)
    return manifest


def create_binary_run_manifest(**values: Any) -> dict[str, Any]:
    values["task_id"] = "cn_vs_impaired"
    return create_run_manifest(**values)


def update_run_manifest(path: str | Path, manifest: dict[str, Any], status: str, **updates: Any) -> None:
    if status not in RUN_STATUSES:
        raise ExperimentValidationError(f"Invalid run status: {status}.")
    manifest.update(updates)
    manifest["status"] = status
    if status == "RUNNING" and manifest.get("start_time") is None:
        manifest["start_time"] = utc_now()
    if status == "RUNNING":
        manifest["completion_time"] = None
    if status in {"COMPLETED", "FAILED", "INTERRUPTED"}:
        manifest["completion_time"] = utc_now()
    atomic_json(path, manifest)
