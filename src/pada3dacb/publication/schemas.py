"""Strict, authorization-independent Phase 18 freeze schema primitives."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any

from .canonical_json import identity_sha256, is_sha256

SCHEMA_VERSION = "phase18.freeze.v1"
CANONICALIZATION_PROFILE = "phase18.canonical-json.v1"
PHASE = 18
UNRESOLVED = "unresolved"
FREEZE_PAYLOAD_REQUIRED_FIELDS = (
    "schema_version",
    "phase",
    "status",
    "phase_18_authorized",
    "freeze_approved",
    "real_execution_authorized",
    "publication_authorized",
    "phase_19_forbidden",
    "scientific_resolution_hash",
    "matrix_hash",
    "provenance_freeze_hash",
    "feasibility_hash",
    "resource_budget_hash",
    "independent_review_hash",
    "human_authorization_hash",
)


class ValueClass(str, Enum):
    CANONICAL_FIXED = "canonical_fixed"
    MANUALLY_SELECTED_PRE_RUN = "manually_selected_pre_run"
    ENGINEERING_ONLY = "engineering_only"
    UNRESOLVED_BLOCKING = "unresolved_blocking"


class BlockerCode(str, Enum):
    AUTHORIZATION_BLOCKED = "authorization_blocked"
    UNRESOLVED_SCIENTIFIC_VALUE = "unresolved_scientific_value"
    UNRESOLVED_METHOD_PARAMETER = "unresolved_method_parameter"
    NON_CANONICAL_DIRECTION = "non_canonical_direction"
    INCOMPLETE_MATRIX = "incomplete_matrix"
    MISSING_ASSIGNMENT = "missing_assignment"
    OVERLAPPING_ASSIGNMENTS = "overlapping_assignments"
    MISSING_IMMUTABLE_ARTIFACT = "missing_immutable_artifact"
    TARGET_LABEL_FIREWALL_VIOLATION = "target_label_firewall_violation"
    PROVENANCE_CONFLICT = "provenance_conflict"
    CANONICALIZATION_UNRESOLVED = "canonicalization_unresolved"
    HASH_MISMATCH = "hash_mismatch"
    SHAPE_MISMATCH = "shape_mismatch"
    NON_FINITE_VALUE = "non_finite_value"
    RESOURCE_BUDGET_UNRESOLVED = "resource_budget_unresolved"
    INTERRUPTED = "interrupted"
    RUNTIME_FAILURE = "runtime_failure"
    STORAGE_FAILURE = "storage_failure"
    RESUME_IDENTITY_MISMATCH = "resume_identity_mismatch"
    PUBLICATION_NOT_AUTHORIZED = "publication_not_authorized"


@dataclass(frozen=True)
class ValueClassification:
    """A value with explicit evidence classification; no scientific defaulting."""

    name: str
    value: Any
    value_class: ValueClass
    source: str | None
    reason: str | None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("value classification name is required")
        if not isinstance(self.value_class, ValueClass):
            raise TypeError("value_class must be a ValueClass")
        if not self.source and not self.reason:
            raise ValueError("value classification requires a source or reason")
        if self.value_class is ValueClass.UNRESOLVED_BLOCKING and not self.reason:
            raise ValueError("unresolved values require a blocking reason")


@dataclass(frozen=True)
class BlockerRecord:
    code: BlockerCode
    message: str
    evidence: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.code, BlockerCode):
            raise TypeError("code must be a BlockerCode")
        if not self.message:
            raise ValueError("blocker message is required")


class MatrixRowKind(str, Enum):
    TRAINING = "training"
    CHECKPOINT_PROJECTION = "checkpoint_projection"


class MatrixStatus(str, Enum):
    PLANNED = "PLANNED"
    BLOCKED = "BLOCKED"
    READY_FOR_AUTHORIZATION = "READY_FOR_AUTHORIZATION"
    AUTHORIZED = "AUTHORIZED"
    RUNNING = "RUNNING"
    RETRY_REQUIRED = "RETRY_REQUIRED"
    FAILED = "FAILED"


_ALLOWED_METHODS = {
    "source_only",
    "coral",
    "mmd",
    "cdan",
    "prototype_pseudo",
    "aagn",
    "faster_snn",
}
_DIRECTIONS = {
    "adni_to_oasis": ("ADNI", "OASIS"),
    "oasis_to_adni": ("OASIS", "ADNI"),
}


@dataclass(frozen=True)
class MatrixRow:
    matrix_id: str
    row_kind: MatrixRowKind
    parent_training_id: str | None
    training_invocation: bool
    method_id: str
    public_method_name: str
    direction: str
    source_cohort: str
    target_cohort: str
    fold: int
    seed: int
    checkpoint_policy: str
    resolved_config_hash: str
    split_assignment_hash: str
    target_adaptation_assignment_hash: str
    target_evaluation_assignment_hash: str
    immutable_artifacts_hash: str
    state: MatrixStatus
    completion_allowed: bool
    blocked_reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_matrix_row(self)


@dataclass(frozen=True)
class FreezePayload:
    """The hashed payload; ``freeze_hash`` intentionally does not belong here."""

    schema_version: str
    phase: int
    status: str
    phase_18_authorized: bool
    freeze_approved: bool
    real_execution_authorized: bool
    publication_authorized: bool
    phase_19_forbidden: bool
    scientific_resolution_hash: str
    matrix_hash: str
    provenance_freeze_hash: str
    feasibility_hash: str
    resource_budget_hash: str
    independent_review_hash: str
    human_authorization_hash: str
    blockers: tuple[str, ...] = ()
    extensions: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=True)

    def __post_init__(self) -> None:
        validate_freeze_payload(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> FreezePayload:
        if not isinstance(value, Mapping):
            raise TypeError("freeze payload must be a mapping")
        if "freeze_hash" in value:
            raise ValueError("freeze_hash must remain outside the freeze payload")
        missing = sorted(set(FREEZE_PAYLOAD_REQUIRED_FIELDS) - set(value))
        if missing:
            raise ValueError(f"missing required freeze field: {missing[0]}")
        blockers = value.get("blockers", ())
        if not isinstance(blockers, (list, tuple)):
            raise TypeError("blockers must be a sequence")
        core_names = {field.name for field in fields(cls)} - {"extensions"}
        extensions = {key: item for key, item in value.items() if key not in core_names}
        return cls(
            **{
                field.name: (
                    tuple(blockers) if field.name == "blockers" else extensions if field.name == "extensions" else value[field.name]
                )
                for field in fields(cls)
            }
        )

    def to_mapping(self) -> dict[str, Any]:
        mapping = dict(self.extensions)
        mapping.update({field.name: getattr(self, field.name) for field in fields(self) if field.name != "extensions"})
        mapping["blockers"] = list(self.blockers)
        return mapping

    def identity_hash(self) -> str:
        return freeze_payload_hash(self)


@dataclass(frozen=True)
class FreezePayloadEnvelope:
    """Payload plus its externally stored identity hash."""

    payload: FreezePayload
    freeze_hash: str | None

    def __post_init__(self) -> None:
        if self.freeze_hash is not None and not is_sha256(self.freeze_hash):
            raise ValueError("freeze_hash must be a lowercase SHA-256 digest")
        if self.freeze_hash is not None and self.freeze_hash != freeze_payload_hash(self.payload):
            raise ValueError("freeze_hash does not match payload identity")


FreezeRecord = FreezePayload


def freeze_payload_hash(payload: FreezePayload | Mapping[str, Any]) -> str:
    """Hash the canonical, typed Phase 18 freeze payload identity."""

    if isinstance(payload, FreezePayload):
        typed = payload
    else:
        if "freeze_hash" in payload:
            raise ValueError("freeze_hash must remain outside the freeze payload")
        typed = FreezePayload.from_mapping(payload)
    return identity_sha256(typed.to_mapping())


def validate_freeze_payload(payload: FreezePayload) -> tuple[BlockerRecord, ...]:
    """Validate schema and current authorization boundary without authorizing a run."""

    if "freeze_hash" in payload.extensions:
        raise ValueError("freeze_hash must remain outside the freeze payload")
    if payload.schema_version != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    if payload.phase != PHASE:
        raise ValueError("phase must be 18")
    if payload.status != "blocked_planning":
        raise ValueError("Phase 18 primitive payload must remain blocked_planning")
    for field_name in (
        "phase_18_authorized",
        "freeze_approved",
        "real_execution_authorized",
        "publication_authorized",
        "phase_19_forbidden",
    ):
        _require_bool(getattr(payload, field_name), field_name)
    if not payload.phase_18_authorized:
        raise ValueError("phase_18_authorized must remain true")
    if payload.freeze_approved:
        raise ValueError("freeze_approved must remain false")
    if payload.real_execution_authorized:
        raise ValueError("real_execution_authorized must remain false")
    if payload.publication_authorized:
        raise ValueError("publication_authorized must remain false")
    if not payload.phase_19_forbidden:
        raise ValueError("phase_19_forbidden must remain true")

    hash_fields = (
        "scientific_resolution_hash",
        "matrix_hash",
        "provenance_freeze_hash",
        "feasibility_hash",
        "resource_budget_hash",
        "independent_review_hash",
        "human_authorization_hash",
    )
    for field_name in hash_fields:
        value = getattr(payload, field_name)
        if value != UNRESOLVED and not is_sha256(value):
            raise ValueError(f"{field_name} must be unresolved or a lowercase SHA-256 digest")
    return ()


def validate_matrix_row(row: MatrixRow) -> tuple[BlockerRecord, ...]:
    """Validate a row without changing state or making an authorization decision."""

    _validate_matrix_row(row)
    return ()


def _require_bool(value: object, field_name: str) -> None:
    if type(value) is not bool:
        raise TypeError(f"{field_name} must be a bool")


def _validate_matrix_row(row: MatrixRow) -> None:
    if not is_sha256(row.matrix_id):
        raise ValueError("matrix_id must be a lowercase SHA-256 digest")
    if not isinstance(row.row_kind, MatrixRowKind):
        raise TypeError("row_kind must be a MatrixRowKind")
    if not isinstance(row.state, MatrixStatus):
        raise TypeError("state must be a MatrixStatus")
    if row.method_id not in _ALLOWED_METHODS:
        raise ValueError("method_id is not in the protected Phase 18 inventory")
    if row.direction not in _DIRECTIONS:
        raise ValueError("direction must be a canonical lowercase Phase 18 identifier")
    source, target = _DIRECTIONS[row.direction]
    if (row.source_cohort, row.target_cohort) != (source, target):
        raise ValueError("cohorts do not match the canonical direction")
    if row.fold not in range(5):
        raise ValueError("fold must be one of 0..4")
    if row.seed != 42:
        raise ValueError("seed must be the canonical Phase 18 seed 42")
    _require_bool(row.training_invocation, "training_invocation")
    _require_bool(row.completion_allowed, "completion_allowed")
    if row.completion_allowed:
        raise ValueError("completion_allowed must remain false in Phase 18")
    if row.row_kind is MatrixRowKind.TRAINING:
        if row.parent_training_id is not None:
            raise ValueError("training rows cannot have parent_training_id")
        if row.training_invocation is not True:
            raise ValueError("training rows require training_invocation=true")
        if row.checkpoint_policy != "best_source_f1":
            raise ValueError("training rows require best_source_f1")
    else:
        if not row.parent_training_id:
            raise ValueError("checkpoint_projection rows require parent_training_id")
        if row.training_invocation is not False:
            raise ValueError("checkpoint_projection rows require training_invocation=false")
        if row.checkpoint_policy != "last":
            raise ValueError("checkpoint_projection rows require last")
    for field_name in (
        "resolved_config_hash",
        "split_assignment_hash",
        "target_adaptation_assignment_hash",
        "target_evaluation_assignment_hash",
        "immutable_artifacts_hash",
    ):
        value = getattr(row, field_name)
        if value != UNRESOLVED and not is_sha256(value):
            raise ValueError(f"{field_name} must be unresolved or a lowercase SHA-256 digest")
    if not isinstance(row.blocked_reasons, tuple) or any(
        not isinstance(reason, str) or not reason for reason in row.blocked_reasons
    ):
        raise TypeError("blocked_reasons must be a tuple of non-empty strings")
