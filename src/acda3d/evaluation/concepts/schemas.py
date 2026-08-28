"""Phase 16 concept evaluation schemas and validation."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from typing_extensions import Self

from acda3d.evaluation.schemas import (
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
    NOT_APPLICABLE = "not_applicable_no_acda3d_concept_head"


class ConceptAggregationPolicy(str, Enum):
    """Aggregation policy for fold/seed levels."""
    FOLD_MEAN = "fold_mean"
    SEED_MEAN = "seed_mean"
    FOLD_THEN_SEED = "fold_then_seed"


class ConceptNormalizerHash(str):
    """SHA-256 hash of concept normalizer JSON."""


# Phase 18B is an additive task scope.  These constants intentionally live next
# to the historical concept schemas so callers cannot infer class order from
# observed records or from the legacy three-class configuration.
BINARY_CONCEPT_TASK_ID = "cn_vs_impaired"
BINARY_CONCEPT_CLASS_ORDER = ("CN", "Impaired")
BINARY_CONCEPT_CLASS_TO_INDEX = {"CN": 0, "Impaired": 1}
BINARY_CONCEPT_MAPPING_CONTRACT = "phase-18b-binary-v1"


@dataclass(frozen=True)
class BinaryConceptEvaluationConfig:
    """Explicit task scope for binary concept evaluation over retained artifacts."""

    task_id: str = BINARY_CONCEPT_TASK_ID
    class_order: tuple[str, ...] = BINARY_CONCEPT_CLASS_ORDER
    class_to_index: Mapping[str, int] = field(
        default_factory=lambda: dict(BINARY_CONCEPT_CLASS_TO_INDEX)
    )
    mapping_contract: str = BINARY_CONCEPT_MAPPING_CONTRACT
    task_hash: str | None = None
    refit: bool = False
    regenerate: bool = False

    def __post_init__(self) -> None:
        if self.task_id != BINARY_CONCEPT_TASK_ID:
            raise ConfigurationError(
                "binary concept evaluation requires task_id='cn_vs_impaired'"
            )
        if tuple(self.class_order) != BINARY_CONCEPT_CLASS_ORDER:
            raise ConfigurationError("binary concept class order must be CN, Impaired")
        if dict(self.class_to_index) != BINARY_CONCEPT_CLASS_TO_INDEX:
            raise ConfigurationError("binary concept class IDs must be CN=0 and Impaired=1")
        if self.mapping_contract != BINARY_CONCEPT_MAPPING_CONTRACT:
            raise ConfigurationError("binary concept mapping contract is incompatible")
        if self.refit:
            raise ConfigurationError("binary concept evaluation does not permit refit")
        if self.regenerate:
            raise ConfigurationError("binary concept evaluation does not permit regeneration")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> BinaryConceptEvaluationConfig:
        if not isinstance(value, Mapping):
            raise ConfigurationError("binary concept evaluation config must be a mapping")
        return cls(
            task_id=value.get("task_id", ""),
            class_order=tuple(value.get("class_order", ())),
            class_to_index=value.get("class_to_index", value.get("class_ids", {})),
            mapping_contract=value.get("mapping_contract", ""),
            task_hash=value.get("task_hash"),
            refit=bool(value.get("refit", value.get("fit", False))),
            regenerate=bool(value.get("regenerate", value.get("regeneration", False))),
        )


REAL_EVALUATION_CAPABILITY_SCHEMA_VERSION = "phase16-real-evaluation-capability-v1"
_REAL_CAPABILITY_ISSUER_TOKEN = object()
_REAL_CAPABILITY_EVIDENCE = (
    "authorized_exports",
    "concept_normalizer",
    "atlas_hash",
    "protocol_approval",
)


@dataclass(frozen=True)
class RealEvaluationCapability:
    """Opaque, process-local authorization for real concept evaluation."""

    schema_version: str
    manifest_sha256: str
    authorization_sha256: str
    issuer: str
    _issuer_token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.schema_version != REAL_EVALUATION_CAPABILITY_SCHEMA_VERSION:
            raise ValueError("unsupported real evaluation capability schema")
        validate_sha256(self.manifest_sha256, "capability manifest sha256")
        validate_sha256(self.authorization_sha256, "capability authorization sha256")
        if not isinstance(self.issuer, str) or not self.issuer.strip():
            raise ValueError("capability issuer must be a non-empty label")

    def __getstate__(self):
        raise TypeError("real evaluation capabilities are process-local and non-serializable")


def issue_real_evaluation_capability(
    authorization_evidence: Mapping[str, Any],
    manifest_sha256: str,
    *,
    issuer: str,
) -> RealEvaluationCapability:
    """Keep real capability issuance closed until an external issuer exists."""
    raise ValueError(
        "real evaluation capability issuance is closed: external authorization issuer is not configured"
    )


def _is_issued_real_evaluation_capability(value: object) -> bool:
    return False


PROVENANCE_MANIFEST_SCHEMA_VERSION = "phase16-concept-provenance-v1"
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def validate_sha256(value: Any, field_name: str = "hash") -> str:
    """Return a canonical lowercase SHA-256 or fail closed."""
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256")
    return value


def canonical_roi_order_hash(labels: Sequence[int]) -> str:
    """Hash the ordered ROI labels without sorting or normalizing them."""
    if isinstance(labels, (str, bytes)) or not isinstance(labels, Sequence) or not labels:
        raise ValueError("ROI labels must be a non-empty sequence")
    normalized = []
    for label in labels:
        if isinstance(label, bool) or not isinstance(label, int):
            raise ValueError("ROI labels must be integers")
        normalized.append(label)
    if len(set(normalized)) != len(normalized):
        raise ValueError("ROI labels must be unique")
    return hashlib.sha256(json.dumps(normalized).encode("utf-8")).hexdigest()


def validate_safe_relative_path(value: Any, field_name: str = "relative_path") -> str:
    """Validate a root-relative POSIX path and reject traversal/platform escapes."""
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError(f"{field_name} must be a safe POSIX-relative path")
    path = Path(value)
    if path.is_absolute() or value.startswith("/"):
        raise ValueError(f"{field_name} must be a safe POSIX-relative path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{field_name} must be a safe POSIX-relative path")
    return value


@dataclass(frozen=True)
class FileIdentity:
    """Immutable identity established from file bytes before parsing."""

    path: Path
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        validate_sha256(self.sha256, "file sha256")
        if self.size_bytes < 0:
            raise ValueError("file size must be non-negative")


FIXTURE_MANIFEST_SCHEMA_VERSION = "phase16-concept-fixture-manifest-v1"
FIXTURE_MANIFEST_MARKER = "phase16-synthetic-fixture"
_FIXTURE_MANIFEST_ISSUER_TOKEN = object()


@dataclass(frozen=True)
class VerifiedFixtureManifest:
    """Immutable fixture identity issued only after complete manifest verification."""

    manifest_path: Path
    manifest_sha256: str
    allowed_root: Path
    files: tuple[FileIdentity, ...]
    _issuer_token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        validate_sha256(self.manifest_sha256, "fixture manifest sha256")
        if not self.files:
            raise ValueError("fixture manifest must list at least one file")
        root = self.allowed_root.resolve()
        manifest = self.manifest_path.resolve()
        try:
            manifest.relative_to(root)
        except ValueError as error:
            raise ValueError("fixture manifest path escapes allowed root") from error
        if not root.is_dir() or not manifest.is_file():
            raise ValueError("fixture manifest path and allowed root must exist")
        for identity in self.files:
            try:
                identity.path.resolve().relative_to(root)
            except ValueError as error:
                raise ValueError("fixture file path escapes allowed root") from error

    def file_identity(self, path: Path) -> FileIdentity | None:
        resolved = Path(path).resolve()
        return next((item for item in self.files if item.path.resolve() == resolved), None)



    @property
    def fixture_files(self) -> tuple[dict[str, str | int], ...]:
        """Return the verified fixture file set in a portable canonical form."""
        root = self.allowed_root.resolve()
        entries = []
        for identity in self.files:
            relative_path = identity.path.resolve().relative_to(root).as_posix()
            entries.append({
                "relative_path": relative_path,
                "sha256": identity.sha256,
                "size_bytes": identity.size_bytes,
            })
        return tuple(sorted(entries, key=lambda item: item["relative_path"]))

    @property
    def fixture_payload_sha256(self) -> str:
        """Hash the verified manifest bytes and relative fixture paths, bytes, and sizes."""
        return canonical_sha256({
            "schema_version": FIXTURE_MANIFEST_SCHEMA_VERSION,
            "manifest_sha256": self.manifest_sha256,
            "files": self.fixture_files,
        })


def _is_verified_fixture_manifest(value: object) -> bool:
    return isinstance(value, VerifiedFixtureManifest) and value._issuer_token is _FIXTURE_MANIFEST_ISSUER_TOKEN



def verify_fixture_manifest(
    manifest_path: str | Path,
    expected_sha256: str,
    allowed_root: str | Path,
) -> VerifiedFixtureManifest:
    """Verify a synthetic fixture manifest and every listed fixture file."""
    try:
        expected = validate_sha256(expected_sha256, "fixture manifest sha256")
        root = Path(allowed_root).resolve()
        path = Path(manifest_path).resolve()
        if not root.is_dir():
            raise ValueError("fixture manifest allowed root must be an existing directory")
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("fixture manifest path escapes allowed root") from error
        raw_bytes = path.read_bytes()
    except (OSError, TypeError, ValueError) as error:
        if isinstance(error, ValueError):
            raise
        raise ValueError(f"fixture manifest is unreadable: {path}") from error
    actual = hashlib.sha256(raw_bytes).hexdigest()
    if not hmac.compare_digest(actual, expected):
        raise ValueError("fixture manifest sha256 is forged or stale")
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("fixture manifest is unreadable") from error
    if not isinstance(payload, Mapping):
        raise ValueError("fixture manifest must be a mapping")
    if payload.get("schema_version") != FIXTURE_MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported fixture manifest schema version")
    if payload.get("fixture_marker") != FIXTURE_MANIFEST_MARKER:
        raise ValueError("fixture marker is missing or invalid")
    if payload.get("fixture_only") is not True:
        raise ValueError("fixture manifest must explicitly set fixture_only=true")
    entries = payload.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("fixture manifest files must be a non-empty list")
    identities = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise ValueError(f"fixture manifest files[{index}] must be a mapping")
        relative_path = validate_safe_relative_path(
            entry.get("relative_path"), f"fixture manifest files[{index}].relative_path"
        )
        if relative_path in seen:
            raise ValueError(f"duplicate fixture path: {relative_path}")
        seen.add(relative_path)
        file_path = (root / relative_path).resolve()
        try:
            file_path.relative_to(root)
        except ValueError as error:
            raise ValueError("fixture file path escapes allowed root") from error
        if not file_path.is_file():
            raise ValueError(f"fixture file is missing: {relative_path}")
        declared = validate_sha256(
            entry.get("sha256"), f"fixture manifest files[{index}].sha256"
        )
        actual_file = compute_sha256_file(file_path)
        if not hmac.compare_digest(actual_file, declared):
            raise ValueError(f"fixture file hash mismatch: {relative_path}")
        identities.append(FileIdentity(file_path, actual_file, file_path.stat().st_size))
    return VerifiedFixtureManifest(
        path,
        actual,
        root,
        tuple(identities),
        _FIXTURE_MANIFEST_ISSUER_TOKEN,
    )


@dataclass(frozen=True)
class ManifestArtifact:
    relative_path: str
    sha256: str
    roi_order_sha256: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], field_name: str) -> ManifestArtifact:
        if not isinstance(value, Mapping):
            raise ValueError(f"{field_name} must be a mapping")
        return cls(
            validate_safe_relative_path(value.get("relative_path"), f"{field_name}.relative_path"),
            validate_sha256(value.get("sha256"), f"{field_name}.sha256"),
            validate_sha256(value.get("roi_order_sha256"), f"{field_name}.roi_order_sha256"),
        )


@dataclass(frozen=True)
class ManifestCandidate:
    key: tuple[str, str, int, int, str]
    checkpoint: ManifestArtifact
    normalizer: ManifestArtifact
    concept_artifacts_root: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], index: int) -> ManifestCandidate:
        if not isinstance(value, Mapping) or not isinstance(value.get("key"), Mapping):
            raise ValueError(f"candidates[{index}].key is required")
        key_value = value["key"]
        names = ("method_id", "direction", "seed", "fold", "checkpoint_policy")
        if any(name not in key_value for name in names):
            raise ValueError(f"candidates[{index}].key is incomplete")
        seed, fold = key_value["seed"], key_value["fold"]
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError(f"candidates[{index}].key.seed must be a non-negative integer")
        if isinstance(fold, bool) or not isinstance(fold, int) or fold < 0:
            raise ValueError(f"candidates[{index}].key.fold must be a non-negative integer")
        return cls(
            (str(key_value["method_id"]), str(key_value["direction"]), seed, fold, str(key_value["checkpoint_policy"])),
            ManifestArtifact.from_mapping(value.get("checkpoint"), f"candidates[{index}].checkpoint"),
            ManifestArtifact.from_mapping(value.get("normalizer"), f"candidates[{index}].normalizer"),
            validate_safe_relative_path(value.get("concept_artifacts_root"), f"candidates[{index}].concept_artifacts_root"),
        )


@dataclass(frozen=True)
class ProvenanceManifest:
    schema_version: str
    labels: tuple[int, ...]
    roi_order_sha256: str
    atlas: ManifestArtifact
    candidates: tuple[ManifestCandidate, ...]
    root: Path
    raw_bytes: bytes = b""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], root: str | Path) -> ProvenanceManifest:
        if not isinstance(value, Mapping):
            raise ValueError("provenance manifest must be a mapping")
        if value.get("schema_version") != PROVENANCE_MANIFEST_SCHEMA_VERSION:
            raise ValueError("unsupported provenance manifest schema version")
        roi = value.get("roi_order")
        if not isinstance(roi, Mapping):
            raise ValueError("roi_order is required")
        labels = tuple(roi.get("labels", ()))
        roi_hash = validate_sha256(roi.get("sha256"), "roi_order.sha256")
        if canonical_roi_order_hash(labels) != roi_hash:
            raise ValueError("roi_order.sha256 does not match ordered labels")
        atlas = ManifestArtifact.from_mapping(value.get("atlas"), "atlas")
        entries = value.get("candidates")
        if not isinstance(entries, list):
            raise ValueError("candidates must be a list")
        candidates = tuple(ManifestCandidate.from_mapping(item, index) for index, item in enumerate(entries))
        keys = [candidate.key for candidate in candidates]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate candidate key in provenance manifest")
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise ValueError("provenance manifest root must be an existing directory")
        for name, artifact in [("atlas", atlas)]:
            resolved_path = (root_path / artifact.relative_path).resolve()
            try:
                resolved_path.relative_to(root_path)
            except ValueError as error:
                raise ValueError(f"{name} path escapes manifest root") from error
            if not resolved_path.is_file():
                raise ValueError(f"{name} file is missing: {artifact.relative_path}")
        for candidate in candidates:
            for name, artifact in (("checkpoint", candidate.checkpoint), ("normalizer", candidate.normalizer)):
                resolved_path = (root_path / artifact.relative_path).resolve()
                try:
                    resolved_path.relative_to(root_path)
                except ValueError as error:
                    raise ValueError(f"{name} path escapes manifest root") from error
                if not resolved_path.is_file():
                    raise ValueError(f"{name} file is missing: {artifact.relative_path}")
            artifacts_root = (root_path / candidate.concept_artifacts_root).resolve()
            try:
                artifacts_root.relative_to(root_path)
            except ValueError as error:
                raise ValueError("concept artifact root escapes manifest root") from error
            if not artifacts_root.is_dir():
                raise ValueError(f"concept artifact root is missing: {candidate.concept_artifacts_root}")
            for artifact_name, artifact in (("atlas", atlas), ("checkpoint", candidate.checkpoint), ("normalizer", candidate.normalizer)):
                if artifact.roi_order_sha256 != roi_hash:
                    raise ValueError(f"{artifact_name} ROI order hash conflicts with manifest")
        return cls(PROVENANCE_MANIFEST_SCHEMA_VERSION, labels, roi_hash, atlas, candidates, root_path)

    @classmethod
    def from_json(cls, path: str | Path) -> ProvenanceManifest:
        manifest_path = Path(path).resolve()
        try:
            raw_bytes = manifest_path.read_bytes()
            payload = json.loads(raw_bytes.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"provenance manifest is unreadable: {manifest_path}") from error
        parsed = cls.from_mapping(payload, manifest_path.parent)
        object.__setattr__(parsed, "raw_bytes", raw_bytes)
        return parsed

    def candidate_for(self, key: tuple[Any, ...]) -> ManifestCandidate | None:
        normalized = tuple(item.value if isinstance(item, Enum) else item for item in key)
        return next((candidate for candidate in self.candidates if candidate.key == normalized), None)


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
        if len(self.latent_probabilities) not in {2, 3} or len(self.concept_probabilities) != len(self.latent_probabilities):
            raise ValueError("task probabilities must contain either two binary or three historical classes")
        label_names = (
            {0: "CN", 1: "Impaired"}
            if len(self.latent_probabilities) == 2
            else {0: "CN", 1: "MCI", 2: "AD"}
        )
        if self.true_label not in label_names:
            message = "true_label must be 0, 1, or 2" if len(self.latent_probabilities) == 3 else "true_label is outside the declared task label space"
            raise ValueError(message)
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
        for name, values in [
            *roi_vectors,
            ("latent_probabilities", self.latent_probabilities),
            ("concept_probabilities", self.concept_probabilities),
        ]:
            array = np.asarray(values, dtype=np.float64)
            validate_finite_array(array, name)
            if name in {"predicted_concepts", "concept_targets", "anatomical_targets"} and np.any(
                (array < 0.0) | (array > 1.0)
            ):
                raise ValueError(f"{name} must be in [0, 1]")
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
            if prediction not in set(range(len(values))):
                if len(values) == 3:
                    raise ValueError(f"{name.removesuffix('_probabilities')}_prediction must be 0, 1, or 2")
                raise ValueError(f"{name.removesuffix('_probabilities')}_prediction is outside the task label space")
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
    manifest_path: str | None = None
    atlas_path: str | None = None
    output_root: str | None = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> Self:
        import yaml

        with open(path, encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
        if not isinstance(data, Mapping):
            raise ConfigurationError("concept evaluation config must be a mapping")
        required = ("schema_version", "protocol_version", "class_order", "methods", "directions", "expected_folds", "expected_seeds", "checkpoint_policies", "bootstrap", "top_k", "real_evaluation_gate", "device")
        missing = [name for name in required if name not in data]
        if missing:
            raise ConfigurationError(f"Missing required config field: {missing[0]}")
        if not isinstance(data["schema_version"], str) or not isinstance(data["protocol_version"], str):
            raise ConfigurationError("schema and protocol versions must be strings")
        if data["class_order"] not in ({"CN": 0, "MCI": 1, "AD": 2}, {"CN": 0, "Impaired": 1}):
            raise ConfigurationError("class_order must be historical CN/MCI/AD or Phase 18B CN/Impaired")

        def sequence(name: str) -> tuple[Any, ...]:
            value = data[name]
            if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or not value:
                raise ConfigurationError(f"{name} must be a non-empty sequence")
            if len(set(value)) != len(value):
                raise ConfigurationError(f"{name} must not contain duplicates")
            return tuple(value)

        try:
            methods = tuple(MethodId(value) for value in sequence("methods"))
            directions = tuple(Direction(value) for value in sequence("directions"))
            policy_data = data["checkpoint_policies"]
            if not isinstance(policy_data, Mapping):
                raise ConfigurationError("checkpoint_policies must be a mapping")
            def parse_policy(value: Any) -> CheckpointPolicy:
                aliases = {"best_source_f1": CheckpointPolicy.PRIMARY_BEST_SOURCE_F1.value, "last": CheckpointPolicy.SENSITIVITY_LAST.value}
                return CheckpointPolicy(aliases.get(value, value))
            primary = parse_policy(policy_data["primary"])
            sensitivity = parse_policy(policy_data["sensitivity"]) if policy_data.get("sensitivity") else None
            policies = tuple(policy for policy in (primary, sensitivity) if policy is not None)
        except (KeyError, TypeError, ValueError) as error:
            raise ConfigurationError(f"invalid method, direction, or checkpoint policy: {error}") from error

        def nonnegative_int(name: str, values: Sequence[Any]) -> tuple[int, ...]:
            result = []
            for value in values:
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ConfigurationError(f"{name} must contain non-negative integers")
                result.append(value)
            return tuple(result)

        folds = nonnegative_int("expected_folds", sequence("expected_folds"))
        seeds = nonnegative_int("expected_seeds", sequence("expected_seeds"))
        top_k = nonnegative_int("top_k", sequence("top_k"))
        if any(value == 0 for value in top_k):
            raise ConfigurationError("top_k values must be positive")
        bootstrap = data["bootstrap"]
        if not isinstance(bootstrap, Mapping):
            raise ConfigurationError("bootstrap must be a mapping")
        replicates, bootstrap_seed = bootstrap.get("replicates"), bootstrap.get("seed")
        if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates < 0:
            raise ConfigurationError("bootstrap.replicates must be a non-negative integer")
        if isinstance(bootstrap_seed, bool) or not isinstance(bootstrap_seed, int) or bootstrap_seed < 0:
            raise ConfigurationError("bootstrap.seed must be a non-negative integer")
        for name in ("ci_policy", "stratification"):
            if not isinstance(bootstrap.get(name), str) or not bootstrap[name]:
                raise ConfigurationError(f"bootstrap.{name} must be a non-empty string")
        gate = data["real_evaluation_gate"]
        if not isinstance(gate, Mapping) or not isinstance(gate.get("authorized"), bool):
            raise ConfigurationError("real_evaluation_gate.authorized must be boolean")
        if not isinstance(data["device"], str) or not data["device"]:
            raise ConfigurationError("device must be a non-empty string")

        def gate_hash(name: str) -> str | None:
            entry = gate.get(name)
            if not isinstance(entry, Mapping) or not isinstance(entry.get("resolved"), bool):
                raise ConfigurationError(f"real_evaluation_gate.{name} must be a mapping with boolean resolved")
            value = entry.get("sha256")
            if entry["resolved"] and value is None:
                raise ConfigurationError(f"real_evaluation_gate.{name}.sha256 is required when evidence is resolved")
            if value is not None:
                value = validate_sha256(value, f"real_evaluation_gate.{name}.sha256")
            if gate["authorized"] and entry["resolved"] is not True:
                raise ConfigurationError(f"authorized real evaluation requires resolved {name} evidence")
            return value

        _ = gate_hash("authorized_exports")
        norm_hash = gate_hash("concept_normalizer")
        atlas_hash = gate_hash("atlas_hash")
        _ = gate_hash("protocol_approval")
        atlas = data.get("atlas") or {}
        normalizer = data.get("concept_normalizer") or {}
        if not isinstance(atlas, Mapping) or not isinstance(normalizer, Mapping):
            raise ConfigurationError("atlas and concept_normalizer must be mappings")
        roi_hash = atlas.get("expected_roi_order_hash")
        if roi_hash is not None:
            roi_hash = validate_sha256(roi_hash, "atlas.expected_roi_order_hash")
        if norm_hash is None and normalizer.get("expected_hash") is not None:
            norm_hash = validate_sha256(normalizer["expected_hash"], "concept_normalizer.expected_hash")
        if atlas_hash is None and atlas.get("expected_atlas_hash") is not None:
            atlas_hash = validate_sha256(atlas["expected_atlas_hash"], "atlas.expected_atlas_hash")
        manifest_path = data.get("manifest_path")
        atlas_path = data.get("atlas_path")
        output_root = data.get("output_root")
        for name, value in (("manifest_path", manifest_path), ("atlas_path", atlas_path), ("output_root", output_root)):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ConfigurationError(f"{name} must be a non-empty path string")
        if gate["authorized"]:
            def required_path(name: str, kind: str) -> Path:
                value = data.get(name)
                if not isinstance(value, str) or not value.strip():
                    raise ConfigurationError(f"{name} must be a non-empty path string")
                resolved = (Path(path).resolve().parent / value).resolve()
                valid = resolved.is_file() if kind == "file" else resolved.is_dir()
                if not valid:
                    raise ConfigurationError(f"{name} does not exist as a {kind}: {resolved}")
                return resolved

            manifest_file = required_path("manifest_path", "file")
            atlas_file = required_path("atlas_path", "file")
            output_dir = required_path("output_root", "directory")
            try:
                manifest = ProvenanceManifest.from_json(manifest_file)
            except (OSError, ValueError) as error:
                raise ConfigurationError(f"manifest_path is invalid: {error}") from error
            if (manifest.root / manifest.atlas.relative_path).resolve() != atlas_file:
                raise ConfigurationError("atlas_path does not match the manifest atlas assignment")
            if atlas_hash is not None and compute_sha256_file(atlas_file) != atlas_hash:
                raise ConfigurationError("atlas_path does not match the configured atlas hash")
            manifest_normalizers = {entry.normalizer.sha256 for entry in manifest.candidates}
            if norm_hash is not None and manifest_normalizers and manifest_normalizers != {norm_hash}:
                raise ConfigurationError("manifest normalizer assignments conflict with configured hash")
            input_values = data.get("input_roots", data.get("input_root", ()))
            if isinstance(input_values, str):
                input_values = (input_values,)
            if input_values is None or isinstance(input_values, (bytes, Mapping)) or not isinstance(input_values, Sequence):
                raise ConfigurationError("input_roots must be a sequence of paths")
            input_paths = []
            for index, value in enumerate(input_values):
                if not isinstance(value, str) or not value.strip():
                    raise ConfigurationError(f"input_roots[{index}] must be a path string")
                input_paths.append((Path(path).resolve().parent / value).resolve())
            for input_path in input_paths:
                if input_path == output_dir or input_path in output_dir.parents or output_dir in input_path.parents:
                    raise ConfigurationError("input and output roots must not overlap")
            manifest_path, atlas_path, output_root = str(manifest_file), str(atlas_file), str(output_dir)
        if gate["authorized"] and (norm_hash is None or atlas_hash is None or roi_hash is None):
            raise ConfigurationError("authorized real evaluation requires atlas, normalizer, and ROI hashes")
        return cls(
            schema_version=data["schema_version"], protocol_version=data["protocol_version"], class_order=data["class_order"],
            methods=methods, directions=directions, expected_folds=folds, expected_seeds=seeds,
            checkpoint_policies=policies, primary_policy=primary, sensitivity_policy=sensitivity,
            bootstrap_replicates=replicates, bootstrap_seed=bootstrap_seed, ci_policy=bootstrap["ci_policy"],
            stratification=bootstrap["stratification"], top_k=top_k, real_gate_authorized=gate["authorized"],
            concept_normalizer_hash=ConceptNormalizerHash(norm_hash) if norm_hash else None,
            atlas_roi_order_hash=AtlasROIOrderHash(roi_hash) if roi_hash else None, atlas_hash=atlas_hash,
            device=data["device"], manifest_path=manifest_path, atlas_path=atlas_path,
            output_root=output_root,
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