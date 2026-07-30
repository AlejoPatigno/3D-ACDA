"""Checkpoint and artifact discovery for concept evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import torch

from .schemas import (
    CheckpointPolicy,
    ConceptCandidate,
    Direction,
    MethodId,
)

# PADA-3DACB eligible methods for concept evaluation
PADA_METHODS = frozenset({
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


def discover_candidates(config: DiscoveryConfig) -> tuple[list[ConceptCandidate], list[str]]:
    """
    Discover eligible checkpoint candidates for concept evaluation.

    Returns:
        Tuple of (valid_candidates, validation_issues)
    """
    candidates = []
    issues = []

    for method in config.methods:
        for direction in config.directions:
            for seed in config.expected_seeds:
                for fold in config.expected_folds:
                    for policy in config.checkpoint_policies:
                        candidate, candidate_issues = _discover_single(
                            config, method, direction, seed, fold, policy
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
) -> tuple[ConceptCandidate | None, list[str]]:
    """Discover one candidate."""
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

    # Load checkpoint metadata (weights_only=False for metadata dicts)
    try:
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
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
            manifest = json.load(f)
        split_hashes = manifest.get("split_hashes", {})

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
    artifact_root = config.artifact_root / "concept_targets" / direction.value / f"seed_{seed}" / f"fold_{fold}"
    if not artifact_root.exists():
        issues.append(f"concept_artifacts_not_found:{method.value}:{direction.value}:seed{seed}:fold{fold}")

    # Skip non-PADA methods for concept evaluation
    if method in NOT_APPLICABLE_METHODS:
        issues.append(f"not_applicable:{method.value}:no_pada3dacb_concept_head")
        return None, issues

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


def filter_pada_candidates(candidates: Sequence[ConceptCandidate]) -> list[ConceptCandidate]:
    """Filter to only PADA-3DACB eligible methods."""
    return [c for c in candidates if c.method_id in PADA_METHODS]


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