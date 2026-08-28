"""Provenance validation and hashing utilities for concept evaluation."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np
import torch

from acda3d.evaluation.schemas import canonical_json

from .schemas import (
    AtlasROIOrderHash,
    ConceptCandidate,
    ConceptNormalizerHash,
    FileIdentity,
    ManifestArtifact,
    ProvenanceManifest,
    canonical_roi_order_hash,
    compute_sha256_file,
    validate_sha256,
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


@dataclass(frozen=True)
class VerifiedEvaluationInputs:
    """Immutable, provenance-verified inputs handed to a real execution boundary."""

    manifest_sha256: str
    roi_labels: tuple[int, ...]
    roi_order_hash: AtlasROIOrderHash
    atlas: FileIdentity
    normalizers: Mapping[tuple, FileIdentity]
    checkpoints: Mapping[tuple, FileIdentity]
    checkpoint_metadata: Mapping[tuple, Mapping[str, Any]]

    def __post_init__(self) -> None:
        validate_sha256(self.manifest_sha256, "manifest sha256")
        object.__setattr__(self, "normalizers", MappingProxyType(dict(self.normalizers)))
        object.__setattr__(self, "checkpoints", MappingProxyType(dict(self.checkpoints)))
        object.__setattr__(self, "checkpoint_metadata", MappingProxyType({key: MappingProxyType(dict(value)) for key, value in self.checkpoint_metadata.items()}))


def _safe_checkpoint_metadata(path: Path) -> Mapping[str, Any]:
    """Inspect only safe tensor-compatible checkpoint mappings."""
    try:
        payload = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as error:
        raise ValueError(f"checkpoint metadata inspection failed: {path}") from error
    if not isinstance(payload, Mapping):
        raise ValueError(f"checkpoint metadata must be a mapping: {path}")
    return payload


def _artifact_identity(root: Path, artifact: ManifestArtifact, field_name: str) -> FileIdentity:
    path = root / artifact.relative_path
    if not path.is_file():
        raise ValueError(f"{field_name} file is missing: {artifact.relative_path}")
    actual = compute_sha256_file(path)
    if actual != artifact.sha256:
        raise ValueError(f"{field_name} hash mismatch: expected {artifact.sha256}, got {actual}")
    return FileIdentity(path, actual, path.stat().st_size)


def verify_provenance_manifest(
    manifest: ProvenanceManifest | Mapping[str, Any] | str | Path,
    root: str | Path | None = None,
    *,
    atlas_manager: Any | None = None,
    atlas_manager_factory: Any | None = None,
) -> VerifiedEvaluationInputs:
    """Verify canonical files and cross-artifact ROI identity before checkpoint parsing."""
    if isinstance(manifest, ProvenanceManifest):
        resolved = manifest
    elif isinstance(manifest, (str, Path)):
        resolved = ProvenanceManifest.from_json(manifest)
    else:
        if root is None:
            raise ValueError("manifest root is required for a mapping")
        resolved = ProvenanceManifest.from_mapping(manifest, root)
    manifest_bytes = resolved.raw_bytes or canonical_json({
        "schema_version": resolved.schema_version,
        "roi_order": {"labels": list(resolved.labels), "sha256": resolved.roi_order_sha256},
        "atlas": {"relative_path": resolved.atlas.relative_path, "sha256": resolved.atlas.sha256, "roi_order_sha256": resolved.atlas.roi_order_sha256},
        "candidates": [{"key": list(candidate.key), "checkpoint": candidate.checkpoint.__dict__, "normalizer": candidate.normalizer.__dict__, "concept_artifacts_root": candidate.concept_artifacts_root} for candidate in resolved.candidates],
    }).encode("utf-8")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    atlas_identity = _artifact_identity(resolved.root, resolved.atlas, "atlas")
    if atlas_manager_factory is not None:
        atlas_manager = atlas_manager_factory(atlas_identity.path)
    if atlas_manager is None:
        raise ValueError("atlas manager is required for strict provenance verification")
    atlas_labels = getattr(atlas_manager, "label_values", None)
    atlas_hash = getattr(atlas_manager, "atlas_hash", None)
    if not isinstance(atlas_labels, Sequence) or isinstance(atlas_labels, (str, bytes)) or not atlas_labels:
        raise ValueError("atlas ROI labels are missing or conflict with manifest")
    if list(atlas_labels) != list(resolved.labels):
        raise ValueError("atlas ROI labels are missing or conflict with manifest")
    if not isinstance(atlas_hash, str) or atlas_hash != atlas_identity.sha256:
        raise ValueError("atlas manager hash conflicts with manifest")

    normalizers: dict[tuple, FileIdentity] = {}
    checkpoints: dict[tuple, FileIdentity] = {}
    metadata: dict[tuple, Mapping[str, Any]] = {}
    normalizer_hashes: set[str] = set()
    for entry in resolved.candidates:
        key = entry.key
        normalizer_identity = _artifact_identity(resolved.root, entry.normalizer, f"normalizer {key}")
        try:
            normalizer_data = json.loads(normalizer_identity.path.read_text(encoding="utf-8"))
            labels = normalizer_data["roi_labels"]
            if list(labels) != list(resolved.labels) or canonical_roi_order_hash(labels) != resolved.roi_order_sha256:
                raise ValueError("normalizer ROI labels conflict with manifest")
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            if isinstance(error, ValueError) and "conflict" in str(error):
                raise
            raise ValueError(f"normalizer ROI labels are missing or unreadable for {key}") from error
        normalizers[key] = normalizer_identity
        normalizer_hashes.add(normalizer_identity.sha256)
        checkpoint_identity = _artifact_identity(resolved.root, entry.checkpoint, f"checkpoint {key}")
        checkpoint_metadata = _safe_checkpoint_metadata(checkpoint_identity.path)
        metadata[key] = checkpoint_metadata
        for field_name, expected in (("roi_order_hash", resolved.roi_order_sha256), ("atlas_hash", atlas_identity.sha256), ("concept_normalizer_hash", normalizer_identity.sha256)):
            actual = checkpoint_metadata.get(field_name)
            if actual != expected:
                raise ValueError(f"checkpoint metadata {field_name} conflicts for {key}")
        checkpoints[key] = checkpoint_identity
    if len(normalizer_hashes) > 1:
        raise ValueError("normalizer file identities conflict across candidates")
    return VerifiedEvaluationInputs(
        manifest_sha256, resolved.labels, AtlasROIOrderHash(resolved.roi_order_sha256),
        atlas_identity, normalizers, checkpoints, metadata,
    )


def load_provenance_manifest(path: str | Path) -> ProvenanceManifest:
    """Load and strictly parse a canonical provenance manifest."""
    return ProvenanceManifest.from_json(path)


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

# ---------------------------------------------------------------------------
# Phase 18B task-scoped compatibility
# ---------------------------------------------------------------------------


def validate_binary_concept_compatibility(
    *,
    task_id: str,
    artifact_hashes: Mapping[str, Any] | None = None,
    expected_artifact_hashes: Mapping[str, Any] | None = None,
    k: int | None = None,
    expected_k: int | None = None,
    roi_order: Sequence[Any] | None = None,
    expected_roi_order: Sequence[Any] | None = None,
    roi_order_hash: str | None = None,
    expected_roi_order_hash: str | None = None,
    atlas_hash: str | None = None,
    expected_atlas_hash: str | None = None,
    mask_hash: str | None = None,
    expected_mask_hash: str | None = None,
    task_hash: str | None = None,
    expected_task_hash: str | None = None,
    refit: bool = False,
    regenerate: bool = False,
) -> None:
    """Fail closed unless binary evaluation reuses the established artifacts."""
    if task_id != "cn_vs_impaired":
        raise ValueError("binary concept compatibility requires task_id='cn_vs_impaired'")
    if refit:
        raise ValueError("binary concept evaluation does not permit refit")
    if regenerate:
        raise ValueError("binary concept evaluation does not permit regeneration")
    if expected_task_hash is not None and task_hash != expected_task_hash:
        raise ValueError("binary concept task hash mismatch")
    if expected_artifact_hashes is not None and (
        artifact_hashes is None or dict(artifact_hashes) != dict(expected_artifact_hashes)
    ):
        raise ValueError("binary concept artifact hashes changed")
    if expected_k is not None and k != expected_k:
        raise ValueError(f"binary concept K changed: got {k}, expected {expected_k}")
    if expected_roi_order is not None and tuple(roi_order or ()) != tuple(expected_roi_order):
        raise ValueError("binary concept ROI ordering changed")
    if expected_roi_order_hash is not None and roi_order_hash != expected_roi_order_hash:
        raise ValueError("binary concept ROI order hash changed")
    if expected_atlas_hash is not None and atlas_hash != expected_atlas_hash:
        raise ValueError("binary concept atlas hash changed")
    if expected_mask_hash is not None and mask_hash != expected_mask_hash:
        raise ValueError("binary concept ROI mask identity changed")


validate_binary_artifact_compatibility = validate_binary_concept_compatibility


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