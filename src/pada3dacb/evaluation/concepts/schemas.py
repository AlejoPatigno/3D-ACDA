"""Phase 16 concept evaluation schemas and validation."""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from typing_extensions import Self

from pada3dacb.evaluation.schemas import (
    CheckpointPolicy,
    ConfigurationError,
    Direction,
    MethodId,
    ValueStatus,
    canonical_sha256,
)

# ============================================================================
# Concept-specific enums and status types
# ============================================================================

class ConceptMethodStatus(str, Enum):
    """Status of a method in concept evaluation."""
    INCLUDED = "included"
    EXCLUDED = "excluded"
    NOT_APPLICABLE = "not_applicable_no_pada3dacb_concept_head"


class ConceptAggregationPolicy(str, Enum):
    """Aggregation policy for fold/seed levels."""
    FOLD_MEAN = "fold_mean"
    SEED_MEAN = "seed_mean"
    FOLD_THEN_SEED = "fold_then_seed"


class ConceptNormalizerHash(str):
    """SHA-256 hash of concept normalizer JSON."""


class AtlasROIOrderHash(str):
    """SHA-256 hash of canonical ROI label sequence."""


# ============================================================================
# Subject-level output
# ============================================================================

@dataclass(frozen=True)
class ConceptSubjectRecord:
    """One subject's concept evaluation outputs."""

    # Identifiers
    method_id: MethodId
    model: str
    direction: Direction
    source_domain: str
    target_domain: str
    seed: int
    fold: int
    logical_checkpoint: str
    checkpoint_epoch: int
    checkpoint_policy: CheckpointPolicy
    experiment_hash: str
    subject_id: str
    subject_hash: str
    cohort: str
    true_label: int
    label_name: str

    # Vector outputs (K entries in canonical ROI order)
    predicted_concepts: tuple[float, ...]
    concept_targets: tuple[float, ...]
    anatomical_targets: tuple[float, ...]
    attention_alpha: tuple[float, ...]
    latent_probabilities: tuple[float, float, float]
    concept_probabilities: tuple[float, float, float]
    latent_prediction: int
    concept_prediction: int

    # Metadata
    K: int
    roi_order_hash: AtlasROIOrderHash
    normalizer_hash: ConceptNormalizerHash
    concept_config_hash: str

    def __post_init__(self) -> None:
        if self.K <= 0:
            raise ValueError("K must be positive")
        for name, value in (
            ("seed", self.seed),
            ("fold", self.fold),
            ("checkpoint_epoch", self.checkpoint_epoch),
        ):
            if value < 0:
                raise ValueError(f"{name} must be nonnegative")
        label_names = {0: "CN", 1: "MCI", 2: "AD"}
        if self.true_label not in label_names:
            raise ValueError("true_label must be 0, 1, or 2")
        if self.label_name != label_names[self.true_label]:
            raise ValueError("label_name does not match true_label")
        expected_source, expected_target = self.direction.cohorts
        if self.source_domain != expected_source:
            raise ValueError("source_domain does not match direction")
        if self.target_domain != expected_target:
            raise ValueError("target_domain does not match direction")
        if self.cohort not in {expected_source, expected_target}:
            raise ValueError("cohort must match source or target domain")
        if self.logical_checkpoint != self.checkpoint_policy.logical_checkpoint:
            raise ValueError("logical checkpoint does not match policy")

        for name, value in (
            ("experiment_hash", self.experiment_hash),
            ("subject_hash", self.subject_hash),
            ("roi_order_hash", str(self.roi_order_hash)),
            ("normalizer_hash", str(self.normalizer_hash)),
            ("concept_config_hash", self.concept_config_hash),
        ):
            if re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError(f"{name} must be lowercase SHA-256")

        roi_vectors = [
            ("predicted_concepts", self.predicted_concepts),
            ("concept_targets", self.concept_targets),
            ("anatomical_targets", self.anatomical_targets),
            ("attention_alpha", self.attention_alpha),
        ]
        for name, vec in roi_vectors:
            if len(vec) != self.K:
                raise ValueError(f"{name} length {len(vec)} != K={self.K}")
        if len(self.latent_probabilities) != 3:
            raise ValueError("latent_probabilities must have 3 entries")
        if len(self.concept_probabilities) != 3:
            raise ValueError("concept_probabilities must have 3 entries")

        for name, values in [
            *roi_vectors,
            ("latent_probabilities", self.latent_probabilities),
            ("concept_probabilities", self.concept_probabilities),
        ]:
            validate_finite_array(np.asarray(values, dtype=np.float64), name)
        alpha = np.asarray(self.attention_alpha, dtype=np.float64)
        if np.any(alpha < 0.0):
            raise ValueError("attention_alpha must be nonnegative")
        validate_alpha_sums_to_one(alpha)

        probability_contracts = (
            ("latent_probabilities", self.latent_probabilities, self.latent_prediction),
            ("concept_probabilities", self.concept_probabilities, self.concept_prediction),
        )
        for name, values, prediction in probability_contracts:
            probabilities = np.asarray(values, dtype=np.float64)
            if np.any((probabilities < 0.0) | (probabilities > 1.0)):
                raise ValueError(f"{name} must be in [0, 1]")
            if not np.isclose(probabilities.sum(), 1.0, rtol=0.0, atol=1e-6):
                raise ValueError(f"{name} must sum to one")
            if prediction not in {0, 1, 2}:
                raise ValueError(f"{name.removesuffix('_probabilities')}_prediction must be 0, 1, or 2")
            if prediction != int(np.argmax(probabilities)):
                raise ValueError(
                    f"{name.removesuffix('_probabilities')}_prediction must equal probability argmax"
                )

    @property
    def subject_key(self) -> tuple:
        """Composite key for deduplication."""
        return (self.method_id, self.direction, self.seed, self.fold, self.subject_hash)


# Alias for backward compatibility with tests
SubjectConceptRecord = ConceptSubjectRecord


# ============================================================================
# Aggregated outputs
# ============================================================================

@dataclass(frozen=True)
class FoldEnsembleRecord:
    """Target subject after fold averaging within one seed."""

    method_id: MethodId
    direction: Direction
    seed: int
    subject_id: str
    subject_hash: str
    cohort: str
    true_label: int
    label_name: str

    # Fold-averaged
    predicted_concepts: tuple[float, ...]
    latent_probabilities: tuple[float, float, float]
    concept_probabilities: tuple[float, float, float]
    attention_alpha: tuple[float, ...]

    # Immutable per-subject artifacts
    concept_targets: tuple[float, ...]
    anatomical_targets: tuple[float, ...]

    # Metadata
    K: int
    fold_count: int
    roi_order_hash: AtlasROIOrderHash
    normalizer_hash: ConceptNormalizerHash


@dataclass(frozen=True)
class SeedEnsembleRecord:
    """Final subject record after seed aggregation (if multiple seeds)."""

    method_id: MethodId
    direction: Direction
    subject_id: str
    subject_hash: str
    cohort: str
    true_label: int
    label_name: str

    # Seed-averaged (or single seed)
    predicted_concepts: tuple[float, ...]
    latent_probabilities: tuple[float, float, float]
    concept_probabilities: tuple[float, float, float]
    attention_alpha: tuple[float, ...]

    # Immutable
    concept_targets: tuple[float, ...]
    anatomical_targets: tuple[float, ...]

    # Metadata
    K: int
    seed_count: int
    roi_order_hash: AtlasROIOrderHash
    normalizer_hash: ConceptNormalizerHash


# ============================================================================
# Configuration and provenance
# ============================================================================

@dataclass(frozen=True)
class ConceptEvaluationConfig:
    """Resolved concept evaluation configuration."""

    schema_version: str
    protocol_version: str
    class_order: Mapping[str, int]
    methods: tuple[MethodId, ...]
    directions: tuple[Direction, ...]
    expected_folds: tuple[int, ...]
    expected_seeds: tuple[int, ...]
    checkpoint_policies: tuple[CheckpointPolicy, ...]
    primary_policy: CheckpointPolicy
    sensitivity_policy: CheckpointPolicy | None
    bootstrap_replicates: int
    bootstrap_seed: int
    ci_policy: str
    stratification: str
    top_k: tuple[int, ...]
    real_gate_authorized: bool
    concept_normalizer_hash: ConceptNormalizerHash | None
    atlas_roi_order_hash: AtlasROIOrderHash | None
    atlas_hash: str | None
    device: str

    @classmethod
    def from_yaml(cls, path: str | Path) -> Self:
        import yaml
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # Validate required fields
        required = [
            "schema_version", "protocol_version", "class_order", "methods",
            "directions", "expected_folds", "expected_seeds",
            "checkpoint_policies", "primary_policy", "bootstrap_replicates",
            "bootstrap_seed", "ci_policy", "stratification", "top_k",
            "real_gate", "device"
        ]
        for r in required:
            if r not in data:
                raise ConfigurationError(f"Missing required config field: {r}")
        # Parse enums
        methods = tuple(MethodId(m) for m in data["methods"])
        directions = tuple(Direction(d) for d in data["directions"])
        policies = tuple(CheckpointPolicy(p) for p in data["checkpoint_policies"])
        primary = CheckpointPolicy(data["primary_policy"])
        sensitivity = CheckpointPolicy(data["sensitivity_policy"]) if data.get("sensitivity_policy") else None
        # Gate
        gate = data["real_gate"]
        authorized = bool(gate.get("authorized", False))
        # Hashes
        norm_hash = gate.get("concept_normalizer_hash")
        roi_hash = gate.get("atlas_roi_order_hash")
        atlas_hash = gate.get("atlas_hash")
        return cls(
            schema_version=data["schema_version"],
            protocol_version=data["protocol_version"],
            class_order=data["class_order"],
            methods=methods,
            directions=directions,
            expected_folds=tuple(data["expected_folds"]),
            expected_seeds=tuple(data["expected_seeds"]),
            checkpoint_policies=policies,
            primary_policy=primary,
            sensitivity_policy=sensitivity,
            bootstrap_replicates=int(data["bootstrap_replicates"]),
            bootstrap_seed=int(data["bootstrap_seed"]),
            ci_policy=data["ci_policy"],
            stratification=data["stratification"],
            top_k=tuple(data["top_k"]),
            real_gate_authorized=authorized,
            concept_normalizer_hash=ConceptNormalizerHash(norm_hash) if norm_hash else None,
            atlas_roi_order_hash=AtlasROIOrderHash(roi_hash) if roi_hash else None,
            atlas_hash=atlas_hash,
            device=data["device"],
        )


@dataclass(frozen=True)
class ConceptCandidate:
    """Discovered checkpoint candidate for concept evaluation."""

    method_id: MethodId
    direction: Direction
    seed: int
    fold: int
    checkpoint_policy: CheckpointPolicy
    logical_checkpoint: str
    checkpoint_epoch: int
    experiment_hash: str
    model_hash: str
    training_hash: str
    split_hashes: Mapping[str, str]
    atlas_hash: str
    roi_order_hash: str
    concept_normalizer_hash: str | None
    checkpoint_path: Path
    concept_artifacts_root: Path
    issues: list[str] = field(default_factory=list)

    @property
    def candidate_key(self) -> tuple:
        return (self.method_id, self.direction, self.seed, self.fold, self.checkpoint_policy)


@dataclass(frozen=True)
class ConceptProvenanceRecord:
    """Provenance record for one validated candidate."""

    method_id: MethodId
    direction: Direction
    seed: int
    fold: int
    checkpoint_policy: CheckpointPolicy
    status: str  # "included" | "excluded"
    experiment_hash: str
    model_hash: str
    training_hash: str
    split_hashes: Mapping[str, str]
    atlas_hash: str
    roi_order_hash: str
    concept_normalizer_hash: str | None
    input_files: tuple[Path, ...]
    issues: tuple[str, ...] = ()


# ============================================================================
# Metric result schemas
# ============================================================================

@dataclass(frozen=True)
class CorrelationResult:
    """Per-ROI correlation with availability status."""

    roi_index: int
    pearson: float | None
    spearman: float | None
    status: ValueStatus
    reason: str | None


@dataclass(frozen=True)
class ConceptFidelityGlobal:
    mae: float
    rmse: float
    bias: float


@dataclass(frozen=True)
class ConceptFidelityPerSubject:
    subject_hash: str
    mae: float
    rmse: float


@dataclass(frozen=True)
class ConceptFidelityPerROI:
    roi_index: int
    mae: float
    rmse: float
    bias: float
    pearson: float | None
    spearman: float | None
    status: ValueStatus
    reason: str | None


@dataclass(frozen=True)
class AnatomyConsistencyGlobal:
    mae: float
    rmse: float
    bias: float


@dataclass(frozen=True)
class AnatomyConsistencyPerSubject:
    subject_hash: str
    mae: float
    rmse: float


@dataclass(frozen=True)
class AnatomyConsistencyPerROI:
    roi_index: int
    mae: float
    rmse: float
    bias: float
    pearson: float | None
    spearman: float | None
    status: ValueStatus
    reason: str | None


@dataclass(frozen=True)
class WeightedAnatomyScore:
    weighted_mae: float | None
    weighted_rmse: float | None
    weighted_bias: float | None
    status: ValueStatus
    reason: str | None


@dataclass(frozen=True)
class HeadAgreementMetrics:
    latent_accuracy: float
    latent_balanced_accuracy: float
    latent_macro_f1: float
    concept_accuracy: float
    concept_balanced_accuracy: float
    concept_macro_f1: float
    top1_agreement_rate: float
    top1_disagreement_rate: float
    mean_js_divergence: float
    consistency_direction: str  # "latent_supervises_concept" | "symmetric"


@dataclass(frozen=True)
class PerClassDisagreement:
    class_label: str
    class_index: int
    disagree_count: int
    total_count: int
    disagree_rate: float | None
    status: ValueStatus = ValueStatus.AVAILABLE
    reason: str | None = None


@dataclass(frozen=True)
class ROIStabilityMetrics:
    pairwise_rho_fidelity: tuple[tuple[float | None, ...], ...]
    pairwise_rho_anatomy: tuple[tuple[float | None, ...], ...]
    pairwise_rho_concept: tuple[tuple[float | None, ...], ...]
    pairwise_rho_alpha: tuple[tuple[float | None, ...], ...]
    mean_pairwise_rho_fidelity: float | None
    mean_pairwise_rho_anatomy: float | None
    mean_pairwise_rho_concept: float | None
    mean_pairwise_rho_alpha: float | None
    instance_std_fidelity: tuple[float, ...]
    instance_std_anatomy: tuple[float, ...]
    instance_std_concept: tuple[float, ...]
    instance_std_alpha: tuple[float, ...]
    jaccard_fidelity: dict[int, float]
    jaccard_anatomy: dict[int, float]
    jaccard_concept: dict[int, float]
    jaccard_alpha: dict[int, float]
    rank_dispersion_std: tuple[float, ...]
    rank_dispersion_range: tuple[float, ...]


@dataclass(frozen=True)
class ClassConditionalProfile:
    class_label: str
    class_index: int
    support: int
    mean_predicted_concepts: tuple[float, ...]
    mean_concept_targets: tuple[float, ...]
    mean_anatomical_targets: tuple[float, ...]
    bootstrap_ci_low: tuple[float, ...]
    bootstrap_ci_high: tuple[float, ...]
    status: ValueStatus = ValueStatus.AVAILABLE
    reason: str | None = None


CONCEPT_COMPARISON_METRICS = frozenset({
    "concept_mae",
    "anatomy_mae",
    "js_divergence",
})


@dataclass(frozen=True)
class ConceptBootstrapInterval:
    metric: str
    point_estimate: float | None
    ci_level: float
    ci_method: str
    ci_low: float | None
    ci_high: float | None
    bootstrap_seed: int
    requested: int
    successful: int
    invalid: int
    status: ValueStatus
    reason: str | None

    def __post_init__(self) -> None:
        if self.metric not in CONCEPT_COMPARISON_METRICS:
            raise ValueError("concept bootstrap metric is invalid")
        if self.requested != self.successful + self.invalid:
            raise ValueError("concept bootstrap counts are inconsistent")


@dataclass(frozen=True)
class ConceptPairedDifference:
    comparator_method: MethodId
    metric: str
    orientation: str
    observed_difference: float | None
    ci_level: float
    ci_method: str
    ci_low: float | None
    ci_high: float | None
    p_value_method: str
    raw_p_value: float | None
    bootstrap_seed: int
    requested: int
    successful: int
    invalid: int
    status: ValueStatus
    reason: str | None


@dataclass(frozen=True)
class ConceptHolmRow:
    statistic_family: str
    metric: str
    family_size: int
    available_count: int
    comparator_method: MethodId
    raw_p_value: float
    holm_rank: int
    adjusted_p_value: float
    status: ValueStatus
    reason: str | None

    def __post_init__(self) -> None:
        if self.metric not in CONCEPT_COMPARISON_METRICS:
            raise ValueError("concept Holm metric is invalid")
        if self.family_size != 4 or self.available_count != 4:
            raise ValueError("concept Holm family must contain four comparators")


@dataclass(frozen=True)
class PairedMethodComparison:
    comparator_method: MethodId
    direction: Direction
    checkpoint_policy: CheckpointPolicy
    metric_family: str  # "concept_mae" | "anatomy_mae" | "js_divergence"
    mean_difference: float
    ci_low: float | None
    ci_high: float | None
    p_value: float | None
    adjusted_p_value: float | None
    holm_rank: int | None
    status: ValueStatus
    reason: str | None


# ============================================================================
# Output paths
# ============================================================================

@dataclass(frozen=True)
class ConceptOutputPaths:
    """Complete output path manifest for concept evaluation."""

    root: Path
    evaluation_manifest: Path
    evaluation_config: Path
    provenance_report: Path
    method_status: Path
    evaluation_log: Path

    # Per direction/policy
    direction_roots: Mapping[tuple[Direction, CheckpointPolicy], Path]

    def direction_root(self, direction: Direction, policy: CheckpointPolicy) -> Path:
        return self.direction_roots[(direction, policy)]


# ============================================================================
# Validation utilities
# ============================================================================

def validate_roi_order(k: int, roi_order_hash: AtlasROIOrderHash, expected_hash: AtlasROIOrderHash | None) -> None:
    """Validate ROI order hash matches expected."""
    if k <= 0:
        raise ConfigurationError("ROI count must be positive")
    if expected_hash is not None and roi_order_hash != expected_hash:
        raise ConfigurationError(
            f"ROI order hash mismatch: got {roi_order_hash}, expected {expected_hash}"
        )


def validate_concept_normalizer(norm_hash: ConceptNormalizerHash, expected_hash: ConceptNormalizerHash | None) -> None:
    """Validate concept normalizer hash."""
    if expected_hash is not None and norm_hash != expected_hash:
        raise ConfigurationError(
            f"Concept normalizer hash mismatch: got {norm_hash}, expected {expected_hash}"
        )


def validate_finite_array(arr: np.ndarray, name: str) -> None:
    """Validate array contains only finite values."""
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} contains non-finite values")


def validate_alpha_sums_to_one(alpha: np.ndarray, tol: float = 1e-4) -> None:
    """Validate attention alpha sums to approximately 1 per subject."""
    sums = alpha.sum(axis=1) if alpha.ndim == 2 else np.array([alpha.sum()])
    if not np.allclose(sums, 1.0, atol=tol):
        raise ValueError(f"attention alpha sums to {sums}, expected ~1.0")


def compute_sha256_file(path: Path) -> str:
    """Compute SHA-256 of file contents."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_sha256_dict(d: Mapping[str, Any]) -> str:
    """Compute deterministic SHA-256 of JSON-serializable dict."""
    return canonical_sha256(d)


# ============================================================================
# Subject concept record (inference output before aggregation)
# ============================================================================

# Use ConceptSubjectRecord as the canonical name; alias for backward compatibility
SubjectConceptRecord = ConceptSubjectRecord