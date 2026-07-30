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
from pada3dacb.exceptions import ExperimentValidationError

RUN_STATUSES = {"PENDING", "RUNNING", "INTERRUPTED", "COMPLETED", "FAILED"}


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


def create_run_manifest(**values: Any) -> dict[str, Any]:
    manifest = {
        **values,
        **runtime_environment(),
        "status": "PENDING",
        "start_time": None,
        "completion_time": None,
        "checkpoint_paths": {},
    }
    return manifest


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
