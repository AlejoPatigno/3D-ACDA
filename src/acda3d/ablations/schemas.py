"""Typed contracts for the Phase 17 ablation registry and resolver."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

CANONICALIZATION_VERSION = "phase17.canonical-json.v1"
HASH_ALGORITHM = "sha256"
PHASE = 17
PRIMARY_COEFFICIENT_NAMES = (
    "lambda_z",
    "lambda_c",
    "lambda_cons",
    "lambda_cbm",
    "lambda_anat",
    "lambda_proto",
    "lambda_pl",
    "tau_p",
    "proto_margin",
    "lambda_sep",
    "label_smoothing",
    "warm_lambda_z",
    "warm_lambda_c",
    "warm_lambda_cbm",
    "warm_lambda_anat",
    "warm_lambda_cons",
)
LOSS_TERM_NAMES = ("L_cls_z", "L_cls_c", "L_cons", "L_concept", "L_anat", "L_proto", "L_pl")
ARCHITECTURE_COMPONENTS = (
    "Encoder3D",
    "ROITokenizer",
    "token_processing",
    "AttentionAggregator",
    "ClassificationHead",
    "ConceptBottleneck",
)
MEAN_POOL_COMPONENT = "MeanPoolAggregator"
IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
TARGET_ADAPTATION_FIELDS = ("x", "subject_id", "subject_hash", "cohort")
FORBIDDEN_TARGET_FIELDS = frozenset(
    {
        "y",
        "label",
        "labels",
        "label_name",
        "true_label",
        "c_target",
        "g_bar",
        "diagnosis",
        "diagnostic_probability",
        "diagnostic_probabilities",
        "stored_diagnostic_probability",
        "stored_diagnostic_probabilities",
        "target_diagnostic_probability",
        "target_diagnostic_probabilities",
        "concept_target",
        "concept_targets",
        "jacobian_target",
        "jacobian_targets",
        "artifact",
        "artifacts",
        "precomputed_artifact",
        "precomputed_artifacts",
        "supervision",
        "supervision_targets",
    }
)


class CandidateClassification(str, Enum):
    CANONICAL_DEFINED_NOT_EXECUTED = "canonical_defined_not_executed"
    EQUIVALENT_TO_EXISTING_METHOD = "equivalent_to_existing_method"
    INVALID_AFTER_ARCHITECTURE_REVISION = "invalid_after_architecture_revision"
    OBSOLETE = "obsolete"
    UNSUPPORTED = "unsupported"
    HELPER_ONLY = "helper_only"


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    UNAPPROVED = "unapproved"
    NOT_APPLICABLE = "not_applicable"


class InterventionKind(str, Enum):
    LOSS_OVERRIDE = "loss_override"
    AGGREGATOR_REPLACEMENT = "aggregator_replacement"


class Disposition(str, Enum):
    RUNNABLE_AFTER_APPROVAL = "RUNNABLE_AFTER_APPROVAL"
    EQUIVALENT_TO_EXISTING_METHOD = "EQUIVALENT_TO_EXISTING_METHOD"
    INVALID_AFTER_ARCHITECTURE_REVISION = "INVALID_AFTER_ARCHITECTURE_REVISION"
    BLOCKED_NOT_PROVEN = "BLOCKED_NOT_PROVEN"
    UNSUPPORTED_ALIAS = "UNSUPPORTED_ALIAS"
    HELPER_ONLY = "HELPER_ONLY"
    UNRESOLVED_CONFIGURATION = "UNRESOLVED_CONFIGURATION"


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _require_identifier(value: object, field_name: str) -> str:
    text = _require_text(value, field_name)
    if not IDENTIFIER_RE.fullmatch(text):
        raise ValueError(f"{field_name} must contain only ASCII letters, digits, and underscores")
    return text


def _require_finite(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def _tuple_text(values: Sequence[object], field_name: str) -> tuple[str, ...]:
    result = tuple(_require_text(value, f"{field_name}[]") for value in values)
    if not result:
        raise ValueError(f"{field_name} must not be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


@dataclass(frozen=True)
class NotebookProvenance:
    path: str
    cell: int
    lines: str

    def __post_init__(self) -> None:
        _require_text(self.path, "provenance.path")
        if not isinstance(self.cell, int) or self.cell < 0:
            raise ValueError("provenance.cell must be a non-negative integer")
        _require_text(self.lines, "provenance.lines")

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path, "cell": self.cell, "lines": self.lines}


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    status: ApprovalStatus
    scope: str = "synthetic_only"
    approved_by: str = "maintainer"

    def __post_init__(self) -> None:
        _require_text(self.approval_id, "approval_id")
        if not isinstance(self.status, ApprovalStatus):
            raise ValueError("approval.status must be an ApprovalStatus")
        _require_text(self.scope, "approval.scope")
        _require_text(self.approved_by, "approval.approved_by")

    @property
    def is_approved(self) -> bool:
        return self.status is ApprovalStatus.APPROVED

    def to_dict(self) -> dict[str, str]:
        return {
            "approval_id": self.approval_id,
            "status": self.status.value,
            "scope": self.scope,
            "approved_by": self.approved_by,
        }


@dataclass(frozen=True)
class Intervention:
    kind: InterventionKind
    parameter: str
    old_value: float | str
    new_value: float | str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, InterventionKind):
            raise ValueError("intervention.kind must be an InterventionKind")
        _require_text(self.parameter, "intervention.parameter")
        if isinstance(self.old_value, float):
            _require_finite(self.old_value, "intervention.old_value")
        if isinstance(self.new_value, float):
            _require_finite(self.new_value, "intervention.new_value")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "parameter": self.parameter,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }


@dataclass(frozen=True)
class LossTermExpectation:
    name: str
    warm_active: bool
    full_active: bool

    def __post_init__(self) -> None:
        if self.name not in LOSS_TERM_NAMES:
            raise ValueError(f"unknown loss term: {self.name!r}")
        if not isinstance(self.warm_active, bool) or not isinstance(self.full_active, bool):
            raise ValueError("loss term activity must be boolean")

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "warm_active": self.warm_active, "full_active": self.full_active}


@dataclass(frozen=True)
class ExpectedLossTerms:
    terms: tuple[LossTermExpectation, ...]

    def __post_init__(self) -> None:
        names = tuple(term.name for term in self.terms)
        if names != LOSS_TERM_NAMES:
            raise ValueError(f"expected loss terms must be exactly {LOSS_TERM_NAMES!r}")

    def to_dict(self) -> tuple[dict[str, object], ...]:
        return tuple(term.to_dict() for term in self.terms)

    @classmethod
    def canonical(cls, disabled_full_term: str | None = None, disabled_warm_term: str | None = None) -> ExpectedLossTerms:
        terms = []
        for name in LOSS_TERM_NAMES:
            warm_active = name in {"L_cls_z", "L_cls_c", "L_concept", "L_anat"}
            full_active = True
            if name in {"L_proto", "L_pl"}:
                warm_active = False
            if name == "L_cons":
                warm_active = False
            if disabled_full_term == name:
                full_active = False
            if disabled_warm_term == name:
                warm_active = False
            terms.append(LossTermExpectation(name, warm_active, full_active))
        return cls(tuple(terms))


@dataclass(frozen=True)
class ModelVariant:
    name: str
    aggregator: str
    architecture_components: tuple[str, ...] = ARCHITECTURE_COMPONENTS
    contextual_encoder: None = None
    runtime_variant_switch: bool = False

    def __post_init__(self) -> None:
        _require_text(self.name, "model_variant.name")
        _require_text(self.aggregator, "model_variant.aggregator")
        if tuple(self.architecture_components) != ARCHITECTURE_COMPONENTS:
            raise ValueError("model variant must retain the canonical 3D-ACDA components")
        if self.contextual_encoder is not None:
            raise ValueError("contextual encoders are forbidden in Phase 17")
        if self.runtime_variant_switch:
            raise ValueError("runtime Full/Lite variant switches are forbidden")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "aggregator": self.aggregator,
            "architecture_components": self.architecture_components,
            "contextual_encoder": self.contextual_encoder,
            "runtime_variant_switch": self.runtime_variant_switch,
        }


@dataclass(frozen=True)
class AblationSpec:
    id: str
    display_name: str
    scientific_question: str
    provenance: NotebookProvenance
    classification: CandidateClassification
    base_method: str
    changed_components: tuple[str, ...]
    preserved_components: tuple[str, ...]
    equivalent_method: str | None
    requires_target_adaptation: bool
    model_variant: ModelVariant
    expected_loss_terms: ExpectedLossTerms
    approval: ApprovalRecord | None
    blocked_reasons: tuple[str, ...]
    aliases: tuple[str, ...]
    intervention: Intervention | None
    disposition: Disposition

    _REQUIRED_FIELDS: ClassVar[tuple[str, ...]] = (
        "id",
        "display_name",
        "scientific_question",
        "provenance",
        "classification",
        "base_method",
        "changed_components",
        "preserved_components",
        "equivalent_method",
        "requires_target_adaptation",
        "model_variant",
        "expected_loss_terms",
        "approval",
        "blocked_reasons",
        "aliases",
    )

    def __post_init__(self) -> None:
        _require_identifier(self.id, "ablation.id")
        _require_text(self.display_name, "ablation.display_name")
        _require_text(self.scientific_question, "ablation.scientific_question")
        _require_text(self.base_method, "ablation.base_method")
        if not isinstance(self.classification, CandidateClassification):
            raise ValueError("ablation.classification must be a CandidateClassification")
        _tuple_text(self.changed_components, "changed_components") if self.changed_components else None
        _tuple_text(self.preserved_components, "preserved_components")
        if self.equivalent_method is not None:
            _require_text(self.equivalent_method, "equivalent_method")
        if not isinstance(self.requires_target_adaptation, bool):
            raise ValueError("requires_target_adaptation must be boolean")
        _tuple_text(self.blocked_reasons, "blocked_reasons") if self.blocked_reasons else None
        for alias in self.aliases:
            _require_identifier(alias, "ablation.alias")
        if len(set(self.aliases)) != len(self.aliases):
            raise ValueError("ablation aliases must be unique")
        runnable = self.classification is CandidateClassification.CANONICAL_DEFINED_NOT_EXECUTED and not self.blocked_reasons
        if runnable and (self.approval is None or not self.approval.is_approved):
            raise ValueError("runnable ablation candidates require explicit approval")
        if runnable and self.intervention is None:
            raise ValueError("runnable ablation candidates require one intervention")
        if runnable and len(self.changed_components) != 1:
            raise ValueError("runnable candidates must change exactly one component")
        if not runnable and not self.blocked_reasons:
            raise ValueError("blocked candidates require a structured blocked reason")

    @property
    def is_runnable(self) -> bool:
        return self.classification is CandidateClassification.CANONICAL_DEFINED_NOT_EXECUTED and self.approval is not None and self.approval.is_approved

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "scientific_question": self.scientific_question,
            "provenance": self.provenance.to_dict(),
            "classification": self.classification.value,
            "base_method": self.base_method,
            "changed_components": self.changed_components,
            "preserved_components": self.preserved_components,
            "equivalent_method": self.equivalent_method,
            "requires_target_adaptation": self.requires_target_adaptation,
            "model_variant": self.model_variant.to_dict(),
            "expected_loss_terms": self.expected_loss_terms.to_dict(),
            "approval": None if self.approval is None else self.approval.to_dict(),
            "blocked_reasons": self.blocked_reasons,
            "aliases": self.aliases,
            "intervention": None if self.intervention is None else self.intervention.to_dict(),
            "disposition": self.disposition.value,
        }


@dataclass(frozen=True)
class LossCoefficients:
    lambda_z: float
    lambda_c: float
    lambda_cons: float
    lambda_cbm: float
    lambda_anat: float
    lambda_proto: float
    lambda_pl: float
    tau_p: float
    proto_margin: float
    lambda_sep: float
    label_smoothing: float
    warm_lambda_z: float
    warm_lambda_c: float
    warm_lambda_cbm: float
    warm_lambda_anat: float
    warm_lambda_cons: float

    def __post_init__(self) -> None:
        for name in PRIMARY_COEFFICIENT_NAMES:
            _require_finite(getattr(self, name), f"losses.{name}")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> LossCoefficients:
        missing = [name for name in PRIMARY_COEFFICIENT_NAMES if name not in value]
        if missing:
            raise ValueError(f"missing canonical loss coefficients: {missing}")
        return cls(**{name: _require_finite(value[name], f"losses.{name}") for name in PRIMARY_COEFFICIENT_NAMES})

    def to_dict(self) -> dict[str, float]:
        return {name: getattr(self, name) for name in PRIMARY_COEFFICIENT_NAMES}


@dataclass(frozen=True)
class RunMatrix:
    directions: tuple[str, ...]
    folds: tuple[int, ...]
    seeds: tuple[int, ...]

    def __post_init__(self) -> None:
        _tuple_text(self.directions, "matrix.directions")
        if not self.folds or any(not isinstance(value, int) or value < 0 for value in self.folds):
            raise ValueError("matrix.folds must be non-empty non-negative integers")
        if not self.seeds or any(isinstance(value, bool) or not isinstance(value, int) for value in self.seeds):
            raise ValueError("matrix.seeds must be non-empty integers")
        allowed = {"ADNI_to_OASIS", "OASIS_to_ADNI", "ADNI->OASIS", "OASIS->ADNI"}
        if any(direction not in allowed for direction in self.directions):
            raise ValueError("matrix.directions contains an unsupported transfer direction")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> RunMatrix:
        required = ("directions", "folds", "seeds")
        missing = [name for name in required if name not in value]
        if missing:
            raise ValueError(f"incomplete matrix; missing {missing}")
        directions = value["directions"]
        folds = value["folds"]
        seeds = value["seeds"]
        if not isinstance(directions, Sequence) or isinstance(directions, (str, bytes)):
            raise ValueError("matrix.directions must be a sequence")
        if not isinstance(folds, Sequence) or isinstance(folds, (str, bytes)):
            raise ValueError("matrix.folds must be a sequence")
        if not isinstance(seeds, Sequence) or isinstance(seeds, (str, bytes)):
            raise ValueError("matrix.seeds must be a sequence")
        return cls(tuple(str(item) for item in directions), tuple(folds), tuple(seeds))

    def to_dict(self) -> dict[str, object]:
        return {"directions": self.directions, "folds": self.folds, "seeds": self.seeds}


@dataclass(frozen=True)
class AssignmentManifest:
    source: tuple[str, ...]
    target_adaptation: tuple[str, ...]
    target_evaluation: tuple[str, ...]

    def __post_init__(self) -> None:
        _tuple_text(self.source, "assignments.source")
        _tuple_text(self.target_adaptation, "assignments.target_adaptation")
        _tuple_text(self.target_evaluation, "assignments.target_evaluation")
        overlap = set(self.target_adaptation) & set(self.target_evaluation)
        if overlap:
            raise ValueError(f"target adaptation/evaluation assignments overlap: {sorted(overlap)}")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> AssignmentManifest:
        required = ("source", "target_adaptation", "target_evaluation")
        missing = [name for name in required if name not in value]
        if missing:
            raise ValueError(f"missing assignment manifests: {missing}")
        return cls(
            _flatten_assignments(value["source"], "assignments.source"),
            _flatten_assignments(value["target_adaptation"], "assignments.target_adaptation"),
            _flatten_assignments(value["target_evaluation"], "assignments.target_evaluation"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "target_adaptation": self.target_adaptation,
            "target_evaluation": self.target_evaluation,
        }


def _flatten_assignments(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return _tuple_text(value, field_name)
    if isinstance(value, Mapping):
        flattened: list[str] = []
        for key in sorted(value):
            nested = _flatten_assignments(value[key], f"{field_name}.{key}")
            flattened.extend(f"{key}={item}" for item in nested)
        return _tuple_text(flattened, field_name)
    raise ValueError(f"{field_name} must be a string, sequence, or mapping")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(_canonicalize(value), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_payload(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _canonicalize(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonicalize(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, set):
        return sorted(_canonicalize(item) for item in value)
    return value


def validate_sha256(value: object, field_name: str) -> str:
    text = _require_text(value, field_name)
    if not HASH_RE.fullmatch(text):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")
    return text


@dataclass(frozen=True)
class AblationBaseConfig:
    """Validated input contract accepted by the pure resolver."""

    base_method: str
    losses: LossCoefficients
    model: ModelVariant
    approval: ApprovalRecord
    epochs_warm: int
    epochs_full: int
    matrix: RunMatrix
    assignments: AssignmentManifest
    precomputed_artifacts: tuple[str, ...]
    target_adaptation_keys: tuple[str, ...] = TARGET_ADAPTATION_FIELDS
    real_data_run: bool = False
    publication_metrics: bool = False

    def __post_init__(self) -> None:
        if self.base_method != "3D-ACDA":
            raise ValueError("base_method must be '3D-ACDA'")
        if not self.approval.is_approved:
            raise ValueError("explicit approved maintainer approval is required")
        if not isinstance(self.epochs_warm, int) or self.epochs_warm < 0:
            raise ValueError("epochs.warm must be a non-negative integer")
        if not isinstance(self.epochs_full, int) or self.epochs_full <= 0:
            raise ValueError("epochs.full must be a positive integer")
        _tuple_text(self.precomputed_artifacts, "precomputed_artifacts")
        target_keys = _tuple_text(self.target_adaptation_keys, "target_adaptation_keys")
        if set(target_keys) != set(TARGET_ADAPTATION_FIELDS):
            missing = sorted(set(TARGET_ADAPTATION_FIELDS) - set(target_keys))
            extra = sorted(set(target_keys) - set(TARGET_ADAPTATION_FIELDS))
            raise ValueError(
                "target adaptation batches must contain exactly the four allowed fields "
                f"{TARGET_ADAPTATION_FIELDS!r}; missing={missing!r}, extra={extra!r}"
            )
        object.__setattr__(self, "target_adaptation_keys", TARGET_ADAPTATION_FIELDS)
        if self.real_data_run or self.publication_metrics:
            raise ValueError("real data and publication metrics are not authorized in Phase 17")

    def to_dict(self) -> dict[str, object]:
        return {
            "base_method": self.base_method,
            "losses": self.losses.to_dict(),
            "model": self.model.to_dict(),
            "approval": self.approval.to_dict(),
            "epochs": {"warm": self.epochs_warm, "full": self.epochs_full},
            "matrix": self.matrix.to_dict(),
            "assignments": self.assignments.to_dict(),
            "precomputed_artifacts": self.precomputed_artifacts,
            "target_adaptation_keys": self.target_adaptation_keys,
            "real_data_run": self.real_data_run,
            "publication_metrics": self.publication_metrics,
        }


@dataclass(frozen=True)
class IdentityEnvelope:
    schema_version: str
    phase: int
    candidate_id: str
    candidate_classification: CandidateClassification
    candidate_approval_id: str | None
    requested_name: str
    alias_mapping: str | None
    direction: str
    fold: int
    seed: int
    registry_hash: str
    candidate_hash: str
    resolved_config_hash: str
    model_variant_hash: str
    source_split_assignment_hash: str
    target_adaptation_assignment_hash: str
    target_evaluation_assignment_hash: str
    precomputed_artifacts_hash: str
    hash_algorithm: str = HASH_ALGORITHM
    canonicalization_version: str = CANONICALIZATION_VERSION

    def __post_init__(self) -> None:
        _require_text(self.schema_version, "identity.schema_version")
        if self.phase != PHASE:
            raise ValueError("identity.phase must be 17")
        _require_identifier(self.candidate_id, "identity.candidate_id")
        if not isinstance(self.candidate_classification, CandidateClassification):
            raise ValueError("identity.candidate_classification must be typed")
        if self.candidate_approval_id is not None:
            _require_text(self.candidate_approval_id, "identity.candidate_approval_id")
        _require_text(self.requested_name, "identity.requested_name")
        _require_text(self.direction, "identity.direction")
        if (
            not isinstance(self.fold, int)
            or isinstance(self.fold, bool)
            or self.fold < 0
            or not isinstance(self.seed, int)
            or isinstance(self.seed, bool)
        ):
            raise ValueError("identity.fold and identity.seed must be valid integers")
        for name in (
            "registry_hash",
            "candidate_hash",
            "resolved_config_hash",
            "model_variant_hash",
            "source_split_assignment_hash",
            "target_adaptation_assignment_hash",
            "target_evaluation_assignment_hash",
            "precomputed_artifacts_hash",
        ):
            validate_sha256(getattr(self, name), f"identity.{name}")
        if self.hash_algorithm != HASH_ALGORITHM:
            raise ValueError("only sha256 identities are supported")
        if self.canonicalization_version != CANONICALIZATION_VERSION:
            raise ValueError("unsupported canonicalization version")

    def to_dict(self) -> dict[str, object]:
        return _canonicalize(self)  # type: ignore[return-value]
