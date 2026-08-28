"""Checkpoint and artifact discovery for concept evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

from .provenance import verify_provenance_manifest
from .schemas import (
    CheckpointPolicy,
    ConceptCandidate,
    Direction,
    MethodId,
    ProvenanceManifest,
    validate_sha256,
)

# 3D-ACDA eligible methods for concept evaluation
ACDA_METHODS = frozenset({
    MethodId.SOURCE_ONLY,
    MethodId.CORAL,
    MethodId.MMD,
    MethodId.CDAN,
    MethodId.PROTOTYPE_PSEUDO,
})

# Methods not applicable to concept evaluation
NOT_APPLICABLE_METHODS = frozenset({
    MethodId.AAGN,
    MethodId.FASTER_SNN,
})
NOT_APPLICABLE_STATUS = "not_applicable_no_acda3d_concept_head"


@dataclass(frozen=True)
class DiscoveryConfig:
    """Configuration for checkpoint discovery."""

    runs_root: Path
    artifact_root: Path
    methods: frozenset[MethodId]
    directions: frozenset[Direction]
    checkpoint_policies: frozenset[CheckpointPolicy]
    expected_folds: Sequence[int]
    expected_seeds: Sequence[int]
    expected_concept_normalizer_hash: str | None = None
    expected_atlas_roi_order_hash: str | None = None
    expected_atlas_hash: str | None = None
    strict: bool = False
    manifest_path: Path | None = None
    runtime_roi_labels: Sequence[int] | None = None
    atlas_manager: Any | None = None

    def validate(self) -> None:
        if not isinstance(self.runs_root, Path) or not isinstance(self.artifact_root, Path):
            raise ValueError("discovery roots must be pathlib.Path values")
        for name, values in (("methods", self.methods), ("directions", self.directions), ("checkpoint_policies", self.checkpoint_policies)):
            if not isinstance(values, (set, frozenset)) or not values:
                raise ValueError(f"{name} must be a non-empty set")
        for name, values in (("expected_folds", self.expected_folds), ("expected_seeds", self.expected_seeds)):
            if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
                raise ValueError(f"{name} must be a non-empty sequence")
            if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
                raise ValueError(f"{name} must contain non-negative integers")
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must not contain duplicates")
        for name, value in (("expected_concept_normalizer_hash", self.expected_concept_normalizer_hash), ("expected_atlas_roi_order_hash", self.expected_atlas_roi_order_hash), ("expected_atlas_hash", self.expected_atlas_hash)):
            if value is not None:
                validate_sha256(value, name)
        if self.strict and (self.manifest_path is None or not self.manifest_path.is_file()):
            raise ValueError("strict discovery requires an existing provenance manifest")
        if self.strict and (self.runtime_roi_labels is None or not self.runtime_roi_labels):
            raise ValueError("strict discovery requires runtime ROI labels")
        if self.strict and self.atlas_manager is None:
            raise ValueError("strict discovery requires an atlas manager")
        if self.runtime_roi_labels is not None and (isinstance(self.runtime_roi_labels, (str, bytes)) or not isinstance(self.runtime_roi_labels, Sequence) or not self.runtime_roi_labels):
            raise ValueError("runtime ROI labels must be a non-empty sequence")


def discover_candidates(config: DiscoveryConfig) -> tuple[list[ConceptCandidate], list[str]]:
    """
    Discover eligible checkpoint candidates for concept evaluation.

    Returns:
        Tuple of (valid_candidates, validation_issues)
    """
    candidates = []
    issues = []
    if config.strict:
        try:
            config.validate()
            manifest = ProvenanceManifest.from_json(config.manifest_path)  # type: ignore[arg-type]
            expected_keys = {(method.value, direction.value, seed, fold, policy.value) for method in config.methods for direction in config.directions for seed in config.expected_seeds for fold in config.expected_folds for policy in config.checkpoint_policies}
            if {entry.key for entry in manifest.candidates} != expected_keys:
                raise ValueError("provenance manifest assignments do not exactly match requested candidates")
            if list(config.runtime_roi_labels) != list(manifest.labels):
                raise ValueError("runtime ROI labels conflict with provenance manifest")
            for method in config.methods:
                for direction in config.directions:
                    for seed in config.expected_seeds:
                        for fold in config.expected_folds:
                            for policy in config.checkpoint_policies:
                                assigned = manifest.candidate_for((method, direction, seed, fold, policy))
                                derived = config.artifact_root / "concept_targets" / direction.value / f"seed_{seed}" / f"fold_{fold}"
                                if assigned is None or (manifest.root / assigned.concept_artifacts_root).resolve() != derived.resolve():
                                    raise ValueError(f"manifest artifact assignment conflicts for {method.value}:{direction.value}:seed{seed}:fold{fold}:{policy.value}")
            verify_provenance_manifest(manifest, atlas_manager=config.atlas_manager)
        except (OSError, ValueError, TypeError) as error:
            return [], [f"provenance_manifest_invalid:{error}"]
    else:
        # Loose fixture callers retain issue-list behavior and legacy roots.
        manifest = None

    for method in sorted(config.methods, key=lambda item: item.value):
        for direction in sorted(config.directions, key=lambda item: item.value):
            for seed in sorted(config.expected_seeds):
                for fold in sorted(config.expected_folds):
                    for policy in sorted(config.checkpoint_policies, key=lambda item: item.value):
                        candidate, candidate_issues = _discover_single(
                            config, method, direction, seed, fold, policy, manifest
                        )
                        if candidate:
                            candidates.append(candidate)
                        issues.extend(candidate_issues)

    return candidates, issues


def _discover_single(
    config: DiscoveryConfig,
    method: MethodId,
    direction: Direction,
    seed: int,
    fold: int,
    policy: CheckpointPolicy,
    manifest: ProvenanceManifest | None = None,
) -> tuple[ConceptCandidate | None, list[str]]:
    """Discover one candidate."""
    if method in NOT_APPLICABLE_METHODS:
        return None, [f"not_applicable:{method.value}:{NOT_APPLICABLE_STATUS}"]

    issues = []

    # Build expected checkpoint directory
    dir_name = f"{method.value}__{direction.value}__seed_{seed}__fold_{fold}"
    checkpoint_dir = config.runs_root / "checkpoints" / dir_name

    if not checkpoint_dir.exists():
        issues.append(f"checkpoint_dir_not_found:{method.value}:{direction.value}:seed{seed}:fold{fold}")
        return None, issues

    # Find checkpoint file matching policy in policy subdirectory
    policy_dir = checkpoint_dir / policy.value
    if not policy_dir.exists():
        issues.append(f"checkpoint_policy_dir_not_found:{method.value}:{direction.value}:seed{seed}:fold{fold}:{policy.value}")
        return None, issues

    if policy == CheckpointPolicy.PRIMARY_BEST_SOURCE_F1:
        checkpoint_files = list(policy_dir.glob("best_source_f1*.pt"))
    elif policy == CheckpointPolicy.SENSITIVITY_LAST:
        checkpoint_files = list(policy_dir.glob("last*.pt"))
    else:
        issues.append(f"unknown_checkpoint_policy:{policy.value}")
        return None, issues

    if not checkpoint_files:
        issues.append(f"checkpoint_not_found:{method.value}:{direction.value}:seed{seed}:fold{fold}:{policy.value}")
        return None, issues

    if len(checkpoint_files) > 1:
        issues.append(f"multiple_checkpoints_found:{method.value}:{direction.value}:seed{seed}:fold{fold}:{policy.value}")
        return None, issues

    checkpoint_path = checkpoint_files[0]
    artifact_root = config.artifact_root / "concept_targets" / direction.value / f"seed_{seed}" / f"fold_{fold}"
    if config.strict and manifest is not None:
        assigned = manifest.candidate_for((method, direction, seed, fold, policy))
        if assigned is None:
            return None, [f"manifest_assignment_missing:{method.value}:{direction.value}:seed{seed}:fold{fold}:{policy.value}"]
        expected_path = manifest.root / assigned.checkpoint.relative_path
        expected_artifact_root = manifest.root / assigned.concept_artifacts_root
        if checkpoint_path.resolve() != expected_path.resolve() or artifact_root.resolve() != expected_artifact_root.resolve():
            return None, [f"manifest_assignment_conflict:{method.value}:{direction.value}:seed{seed}:fold{fold}:{policy.value}"]

    # Safe tensor-only metadata inspection; arbitrary object reconstruction is forbidden.
    try:
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    except Exception as e:
        issues.append(f"checkpoint_load_failed:{method.value}:{direction.value}:seed{seed}:fold{fold}:{e}")
        return None, issues

    # Extract hashes from checkpoint
    experiment_hash = checkpoint.get("experiment_hash", "")
    model_hash = checkpoint.get("model_hash", "")
    training_hash = checkpoint.get("training_hash", "")

    if not all([experiment_hash, model_hash, training_hash]):
        issues.append(f"missing_hashes_in_checkpoint:{method.value}:{direction.value}:seed{seed}:fold{fold}")
        return None, issues

    # Split hashes from run_manifest or fold_result
    split_hashes = {}
    manifest_path = config.runs_root / "manifests" / f"{experiment_hash}.json"
    if manifest_path.exists():
        import json
        with open(manifest_path) as f:
            run_manifest_payload = json.load(f)
        split_hashes = run_manifest_payload.get("split_hashes", {})

    # Atlas and ROI order hashes
    atlas_hash = checkpoint.get("atlas_hash", "")
    roi_order_hash = checkpoint.get("roi_order_hash", "")

    # Concept normalizer hash
    concept_norm_hash = checkpoint.get("concept_normalizer_hash", "")
    if config.expected_concept_normalizer_hash and concept_norm_hash != config.expected_concept_normalizer_hash:
        issues.append(f"concept_normalizer_hash_mismatch:{method.value}:{direction.value}:seed{seed}:fold{fold}")

    if config.expected_atlas_roi_order_hash and roi_order_hash != config.expected_atlas_roi_order_hash:
        issues.append(f"roi_order_hash_mismatch:{method.value}:{direction.value}:seed{seed}:fold{fold}")

    if config.expected_atlas_hash and atlas_hash != config.expected_atlas_hash:
        issues.append(f"atlas_hash_mismatch:{method.value}:{direction.value}:seed{seed}:fold{fold}")

    # Concept artifacts root
    if not artifact_root.exists():
        issues.append(f"concept_artifacts_not_found:{method.value}:{direction.value}:seed{seed}:fold{fold}")

    candidate = ConceptCandidate(
        method_id=method,
        direction=direction,
        seed=seed,
        fold=fold,
        checkpoint_policy=policy,
        logical_checkpoint="best_source_f1" if policy == CheckpointPolicy.PRIMARY_BEST_SOURCE_F1 else "last",
        checkpoint_epoch=checkpoint.get("epoch", 0),
        experiment_hash=experiment_hash,
        model_hash=model_hash,
        training_hash=training_hash,
        split_hashes=split_hashes,
        atlas_hash=atlas_hash,
        roi_order_hash=roi_order_hash,
        concept_normalizer_hash=concept_norm_hash,
        checkpoint_path=checkpoint_path,
        concept_artifacts_root=artifact_root,
        issues=list(issues),
    )

    return candidate, issues


def filter_acda_candidates(candidates: Sequence[ConceptCandidate]) -> list[ConceptCandidate]:
    """Filter to only 3D-ACDA eligible methods."""
    return [c for c in candidates if c.method_id in ACDA_METHODS]


def group_by_subject(candidates: Sequence[ConceptCandidate]) -> dict[str, list[ConceptCandidate]]:
    """Group candidates by subject for aggregation."""
    # This would need subject-level metadata from checkpoint
    # For now, return empty dict - actual grouping happens at inference time
    return {}


def validate_candidate_hashes(
    candidate: ConceptCandidate,
    expected_normalizer: str | None,
    expected_roi_order: str | None,
    expected_atlas: str | None,
) -> list[str]:
    """Validate candidate's provenance hashes."""
    issues = []

    if expected_normalizer and candidate.concept_normalizer_hash != expected_normalizer:
        issues.append(f"concept_normalizer_mismatch:{candidate.method_id.value}:{candidate.direction.value}")

    if expected_roi_order and candidate.roi_order_hash != expected_roi_order:
        issues.append(f"roi_order_mismatch:{candidate.method_id.value}:{candidate.direction.value}")

    if expected_atlas and candidate.atlas_hash != expected_atlas:
        issues.append(f"atlas_mismatch:{candidate.method_id.value}:{candidate.direction.value}")

    return issues