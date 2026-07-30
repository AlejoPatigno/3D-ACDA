"""Provenance validation and hashing utilities for concept evaluation."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from pada3dacb.evaluation.schemas import canonical_json

from .schemas import (
    AtlasROIOrderHash,
    ConceptCandidate,
    ConceptNormalizerHash,
    compute_sha256_file,
)

# ============================================================================
# Hash computation utilities
# ============================================================================

def compute_sha256_dict(data: Mapping[str, Any]) -> str:
    """Compute SHA-256 of canonical JSON representation."""
    canonical = canonical_json(data).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def compute_sha256_array(arr: np.ndarray) -> str:
    """Compute SHA-256 of numpy array (bytes)."""
    return hashlib.sha256(arr.tobytes()).hexdigest()


def compute_sha256_torch(tensor) -> str:
    """Compute SHA-256 of torch tensor (CPU bytes)."""
    arr = tensor.detach().cpu().numpy()
    return compute_sha256_array(arr)


# ============================================================================
# Normalizer hash validation
# ============================================================================

def load_normalizer_hash(normalizer_path: Path) -> ConceptNormalizerHash:
    """Load and return SHA-256 hash of concept normalizer file."""
    return ConceptNormalizerHash(compute_sha256_file(normalizer_path))


def validate_normalizer_hash(
    actual_hash: ConceptNormalizerHash,
    expected_hash: ConceptNormalizerHash | str | None,
) -> list[str]:
    """Validate normalizer hash against expected value."""
    if expected_hash is None:
        return []
    expected = ConceptNormalizerHash(expected_hash) if isinstance(expected_hash, str) else expected_hash
    if actual_hash != expected:
        return [f"normalizer_hash_mismatch: expected {expected_hash}, got {actual_hash}"]
    return []


def validate_roi_order_hash(
    actual_hash: AtlasROIOrderHash,
    expected_hash: AtlasROIOrderHash | str | None,
) -> list[str]:
    """Validate ROI order hash against expected value."""
    if expected_hash is None:
        return []
    expected = AtlasROIOrderHash(expected_hash) if isinstance(expected_hash, str) else expected_hash
    if actual_hash != expected:
        return [f"roi_order_hash_mismatch: expected {expected_hash}, got {actual_hash}"]
    return []


# ============================================================================
# Artifact hash validation
# ============================================================================

@dataclass(frozen=True)
class ArtifactHashes:
    """Collected hashes for all evaluation artifacts."""

    checkpoint_hashes: Mapping[tuple, str]
    normalizer_hash: ConceptNormalizerHash
    roi_order_hash: AtlasROIOrderHash
    atlas_hash: str
    concept_target_hashes: Mapping[str, str]
    anatomical_target_hashes: Mapping[str, str]


def compute_artifact_hashes(
    candidates: Sequence[ConceptCandidate],
    concept_artifacts_roots: Mapping[tuple, Path],
) -> ArtifactHashes:
    """Compute and cross-check every required immutable artifact hash."""
    if not candidates:
        raise ValueError("at least one concept candidate is required")
    checkpoint_hashes: dict[tuple, str] = {}
    concept_target_hashes: dict[str, str] = {}
    anatomical_target_hashes: dict[str, str] = {}
    normalizer_hashes: set[str] = set()
    roi_order_hashes: set[str] = set()
    atlas_hashes: set[str] = set()

    for candidate in candidates:
        key = candidate.candidate_key
        if not candidate.checkpoint_path.is_file():
            raise ValueError(f"checkpoint is missing for candidate {key}")
        checkpoint_hashes[key] = compute_sha256_file(candidate.checkpoint_path)
        artifacts_root = concept_artifacts_roots.get(key)
        if artifacts_root is None or not artifacts_root.is_dir():
            raise ValueError(f"concept artifact root is missing for candidate {key}")

        normalizer_path = artifacts_root / "concept_normalizer.json"
        if not normalizer_path.is_file():
            raise ValueError(f"concept normalizer is missing for candidate {key}")
        actual_normalizer = compute_sha256_file(normalizer_path)
        if candidate.concept_normalizer_hash != actual_normalizer:
            raise ValueError(f"concept normalizer hash mismatch for candidate {key}")
        normalizer_hashes.add(actual_normalizer)

        try:
            normalizer_data = json.loads(normalizer_path.read_text(encoding="utf-8"))
            roi_labels = normalizer_data["roi_labels"]
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise ValueError(f"normalizer ROI order is unreadable for candidate {key}") from error
        if not isinstance(roi_labels, list) or not roi_labels:
            raise ValueError(f"normalizer ROI order is empty for candidate {key}")
        actual_roi_order = hashlib.sha256(json.dumps(roi_labels).encode()).hexdigest()
        if candidate.roi_order_hash != actual_roi_order:
            raise ValueError(f"ROI order hash mismatch for candidate {key}")
        roi_order_hashes.add(actual_roi_order)

        if re.fullmatch(r"[0-9a-f]{64}", candidate.atlas_hash) is None:
            raise ValueError(f"atlas hash is invalid for candidate {key}")
        atlas_hashes.add(candidate.atlas_hash)

        concept_files = sorted(artifacts_root.glob("*_c_target.pt"))
        anatomical_files = sorted(artifacts_root.glob("*_g_bar.pt"))
        if not concept_files or not anatomical_files:
            raise ValueError(f"precomputed concept/anatomical targets are missing for candidate {key}")
        prefix = ":".join(str(part.value if hasattr(part, "value") else part) for part in key)
        for target_file in concept_files:
            concept_target_hashes[f"{prefix}:{target_file.stem}"] = compute_sha256_file(target_file)
        for target_file in anatomical_files:
            anatomical_target_hashes[f"{prefix}:{target_file.stem}"] = compute_sha256_file(target_file)

    if len(normalizer_hashes) != 1 or len(roi_order_hashes) != 1 or len(atlas_hashes) != 1:
        raise ValueError("candidate artifact hashes are not globally consistent")
    return ArtifactHashes(
        checkpoint_hashes=checkpoint_hashes,
        normalizer_hash=ConceptNormalizerHash(next(iter(normalizer_hashes))),
        roi_order_hash=AtlasROIOrderHash(next(iter(roi_order_hashes))),
        atlas_hash=next(iter(atlas_hashes)),
        concept_target_hashes=concept_target_hashes,
        anatomical_target_hashes=anatomical_target_hashes,
    )


# ============================================================================
# Provenance record construction
# ============================================================================

def build_provenance_report(
    candidates: Sequence[ConceptCandidate],
    validation_issues: Mapping[tuple, list[str]],
) -> dict[str, Any]:
    """Build complete provenance report for evaluation."""
    candidates_list = []
    excluded_list = []

    for candidate in candidates:
        key = (candidate.method_id, candidate.direction, candidate.seed, candidate.fold, candidate.checkpoint_policy)
        issues = list(dict.fromkeys([
            *candidate.issues,
            *validation_issues.get(key, []),
        ]))

        record = {
            "method_id": candidate.method_id.value,
            "direction": candidate.direction.value,
            "seed": candidate.seed,
            "fold": candidate.fold,
            "checkpoint_policy": candidate.checkpoint_policy.value,
            "experiment_hash": candidate.experiment_hash,
            "model_hash": candidate.model_hash,
            "training_hash": candidate.training_hash,
            "split_hashes": candidate.split_hashes,
            "atlas_hash": candidate.atlas_hash,
            "roi_order_hash": candidate.roi_order_hash,
            "concept_normalizer_hash": candidate.concept_normalizer_hash,
            "checkpoint_epoch": candidate.checkpoint_epoch,
            "logical_checkpoint": candidate.logical_checkpoint,
            "status": "excluded" if issues else "included",
        }

        if issues:
            record["issues"] = issues
            excluded_list.append(record)
        else:
            candidates_list.append(record)

    return {
        "candidates": candidates_list,
        "excluded": excluded_list,
        "validation_issues": [
            {"candidate": k, "issues": v}
            for k, v in validation_issues.items()
            if v
        ],
    }