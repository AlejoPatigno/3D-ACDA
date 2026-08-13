"""Read-only aggregate validation for the Phase 18 fail-closed boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .canonical_json import is_sha256
from .experiment_matrix import (
    DIRECTIONS,
    FOLDS,
    METHODS,
    ExperimentMatrix,
    ExperimentRow,
    MatrixValidationError,
    RowKind,
    RowState,
    matrix_content_hash,
    validate_matrix,
)
from .feasibility import SyntheticFeasibilityObservation
from .provenance import (
    ManifestValidation,
    ProvenanceStatus,
    _disjoint_fingerprint,
    _is_verified_disjoint_result,
    _is_verifier_issued_manifest,
    _validate_target_manifest_value,
    check_assignment_disjointness,
)
from .provenance import (
    validate_target_adaptation_batch as _validate_target_adaptation_batch,
)
from .provenance import (
    validate_target_evaluation_metadata as _validate_target_evaluation_metadata,
)


@dataclass(frozen=True)
class ValidationBlocker:
    code: str
    message: str
    field: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    blockers: tuple[ValidationBlocker, ...]
    data_access_opened: bool = False

    @property
    def valid(self) -> bool:
        return not self.blockers and not self.data_access_opened

    @property
    def authorized(self) -> bool:
        return self.valid


def validate_matrix_input(matrix: Any) -> tuple[ValidationBlocker, ...]:
    """Validate a complete planning matrix without opening any data path."""

    if isinstance(matrix, ExperimentMatrix):
        try:
            validate_matrix(
                matrix.rows,
                resolved_seed_policy=matrix.resolved_seed_policy,
            )
        except ValueError as exc:
            return (ValidationBlocker("incomplete_matrix", str(exc), "matrix"),)
        blockers = list(_check_rows(matrix.rows))
        blockers.extend(_bind_outer_matrix_identity(matrix.matrix_id, matrix.rows))
        if tuple(matrix.seeds) != (42,) and not (
            isinstance(matrix.resolved_seed_policy, Mapping)
            and matrix.resolved_seed_policy.get("resolved") is True
            and matrix.resolved_seed_policy.get("seeds") == list(matrix.seeds)
        ):
            blockers.append(ValidationBlocker("seed_policy_mismatch", "resolved seed policy is required for non-default seeds", "matrix.seeds"))
        return tuple(_unique(blockers))
    if not isinstance(matrix, Mapping):
        return (ValidationBlocker("incomplete_matrix", "matrix rows are missing", "matrix"),)
    metadata = matrix
    rows = matrix.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return (ValidationBlocker("incomplete_matrix", "matrix rows are missing", "matrix.rows"),)
    seeds = metadata.get("seeds")
    if (
        not isinstance(seeds, Sequence)
        or isinstance(seeds, (str, bytes))
        or not seeds
        or any(type(seed) is not int for seed in seeds)
        or len(set(seeds)) != len(seeds)
    ):
        return (ValidationBlocker("seed_policy_mismatch", "matrix seeds must be explicit unique integers", "matrix.seeds"),)
    expected_rows = len(METHODS) * len(DIRECTIONS) * len(FOLDS) * len(seeds) * 2
    if len(rows) != expected_rows:
        return (ValidationBlocker("incomplete_matrix", f"matrix must contain {expected_rows} rows for the resolved seed set", "matrix.rows"),)
    declared_content_hash = metadata.get("matrix_content_hash")
    try:
        actual_content_hash = matrix_content_hash(metadata)
    except (MatrixValidationError, TypeError, ValueError) as exc:
        return (ValidationBlocker("hash_mismatch", str(exc), "matrix_content_hash"),)
    if declared_content_hash != actual_content_hash:
        return (ValidationBlocker("hash_mismatch", "matrix_content_hash does not match complete matrix rows", "matrix_content_hash"),)
    blockers: list[ValidationBlocker] = []
    training_ids: set[str] = set()
    projection_parents: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            blockers.append(ValidationBlocker("incomplete_matrix", "matrix row is not an object", "matrix.rows"))
            continue
        state = row.get("state")
        if state == "COMPLETED":
            blockers.append(ValidationBlocker("incomplete_matrix", "completed rows are forbidden", "matrix.rows"))
        if row.get("completion_allowed") is not False:
            blockers.append(ValidationBlocker("incomplete_matrix", "completion is not allowed", "matrix.rows"))
        if row.get("row_kind") == RowKind.TRAINING.value:
            if row.get("training_invocation") is not True:
                blockers.append(ValidationBlocker("incomplete_matrix", "training row must invoke training", "matrix.rows"))
            training_ids.add(str(row.get("row_id", "")))
        elif row.get("row_kind") == RowKind.CHECKPOINT_PROJECTION.value:
            parent = row.get("parent_training_id")
            if not parent:
                blockers.append(ValidationBlocker("incomplete_matrix", "projection parent is missing", "matrix.rows"))
            projection_parents.add(str(parent))
        else:
            blockers.append(ValidationBlocker("incomplete_matrix", "unsupported row kind", "matrix.rows"))
    if training_ids != projection_parents:
        blockers.append(ValidationBlocker("incomplete_matrix", "training/projection links are incomplete", "matrix.rows"))
    if isinstance(matrix, Mapping):
        if metadata.get("schema_version") != "phase18.matrix.v1":
            blockers.append(ValidationBlocker("incomplete_matrix", "matrix schema version is invalid", "matrix.schema_version"))
        if not is_sha256(metadata.get("matrix_id")):
            blockers.append(ValidationBlocker("incomplete_matrix", "matrix identity is missing or invalid", "matrix.matrix_id"))
        if metadata.get("methods") != list(METHODS):
            blockers.append(ValidationBlocker("incomplete_matrix", "method inventory is incomplete or reordered", "matrix.methods"))
        if metadata.get("directions") != list(DIRECTIONS):
            blockers.append(ValidationBlocker("non_canonical_direction", "direction inventory is not canonical lowercase", "matrix.directions"))
        if metadata.get("folds") != list(FOLDS):
            blockers.append(ValidationBlocker("incomplete_matrix", "fold inventory must be 0..4", "matrix.folds"))
        if metadata.get("checkpoint_policies") != ["best_source_f1", "last"]:
            blockers.append(ValidationBlocker("incomplete_matrix", "checkpoint policies are incomplete", "matrix.checkpoint_policies"))
        seeds = metadata.get("seeds")
        policy = metadata.get("resolved_seed_policy")
        if seeds != [42] and not (isinstance(policy, Mapping) and policy.get("resolved") is True and policy.get("seeds") == seeds):
            blockers.append(ValidationBlocker("seed_policy_mismatch", "default publication seed policy must be [42] or explicitly resolved", "matrix.seeds"))
        typed_rows: list[ExperimentRow] = []
        for raw in rows:
            if not isinstance(raw, Mapping):
                continue
            try:
                typed_rows.append(
                    ExperimentRow(
                        row_id=raw["row_id"], matrix_id=raw["matrix_id"], row_kind=RowKind(raw["row_kind"]),
                        parent_training_id=raw.get("parent_training_id"), training_invocation=raw["training_invocation"],
                        method_id=raw["method_id"], public_method_name=raw["public_method_name"],
                        source_cohort=raw["source_cohort"], target_cohort=raw["target_cohort"], direction=raw["direction"],
                        fold=raw["fold"], seed=raw["seed"], checkpoint_policy=raw["checkpoint_policy"],
                        split_assignment_hash=raw["split_assignment_hash"], target_adaptation_assignment_hash=raw["target_adaptation_assignment_hash"],
                        target_evaluation_assignment_hash=raw["target_evaluation_assignment_hash"], resolved_config_hash=raw["resolved_config_hash"],
                        artifact_identity_hash=raw["artifact_identity_hash"], state=RowState(raw["state"]),
                        completion_allowed=raw["completion_allowed"], blocked_reasons=tuple(raw.get("blocked_reasons", ())),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                blockers.append(ValidationBlocker("incomplete_matrix", str(exc), "matrix.rows"))
        if len(typed_rows) == len(rows):
            try:
                validate_matrix(
                    typed_rows,
                    resolved_seed_policy=policy,
                )
            except (MatrixValidationError, ValueError) as exc:
                blockers.append(ValidationBlocker("incomplete_matrix", str(exc), "matrix.rows"))
            else:
                blockers.extend(_bind_outer_matrix_identity(metadata.get("matrix_id"), typed_rows))
    return tuple(_unique(blockers))


TARGET_ADAPTATION_FIELDS = frozenset({"x", "subject_id", "subject_hash", "cohort"})
TARGET_MONITORING_LABEL = "MONITORING ONLY — NOT A TRAINING LOSS"


def validate_target_adaptation_batch(batch: Mapping[str, Any]) -> None:
    """Reject target supervision before any loss or selection code can consume it."""

    _validate_target_adaptation_batch(batch)


def validate_target_evaluation_metadata(metadata: Mapping[str, Any]) -> None:
    """Require target metrics to be monitoring-only and read-only."""

    _validate_target_evaluation_metadata(metadata)


def _target_isolation_blockers(
    target_adaptation: Any = None, target_evaluation: Any = None
) -> tuple[ValidationBlocker, ...]:
    blockers: list[ValidationBlocker] = []
    if target_adaptation is not None:
        try:
            _validate_target_manifest_value(target_adaptation, role="target_adaptation")
        except ValueError as exc:
            blockers.append(ValidationBlocker("target_isolation_violation", str(exc), "target_adaptation"))
    if target_evaluation is not None:
        try:
            if isinstance(target_evaluation, Mapping) and (
                "monitoring_label" in target_evaluation
                or "selection_usage" in target_evaluation
                or "read_only" in target_evaluation
            ):
                validate_target_evaluation_metadata(target_evaluation)
            else:
                _validate_target_manifest_value(target_evaluation, role="target_evaluation")
        except ValueError as exc:
            blockers.append(ValidationBlocker("target_isolation_violation", str(exc), "target_evaluation"))
    return tuple(blockers)


def validate_provenance_inputs(provenance: Any) -> tuple[ValidationBlocker, ...]:
    """Validate opaque verifier results and recompute target disjointness every time."""

    if not isinstance(provenance, Mapping):
        return (ValidationBlocker("missing_assignment", "provenance inputs are missing", "provenance"),)
    blockers: list[ValidationBlocker] = []
    validated: dict[str, ManifestValidation] = {}
    for name in ("source", "target_adaptation", "target_evaluation"):
        result = provenance.get(name)
        if result is None:
            blockers.append(ValidationBlocker("missing_assignment", f"{name} manifest result is missing", name))
        elif not isinstance(result, ManifestValidation):
            blockers.append(
                ValidationBlocker(
                    "provenance_conflict",
                    f"{name} must be a verifier-issued validated manifest record",
                    name,
                )
            )
        elif not _is_verifier_issued_manifest(result, expected_role=name):
            blockers.append(
                ValidationBlocker(
                    "provenance_conflict",
                    f"{name} is not verifier-issued, parsed, and exact-byte/hash bound",
                    name,
                )
            )
        else:
            validated[name] = result

    recomputed: ManifestValidation | None = None
    adaptation = validated.get("target_adaptation")
    evaluation = validated.get("target_evaluation")
    if adaptation is not None and evaluation is not None:
        recomputed = check_assignment_disjointness(adaptation, evaluation)
        if recomputed.status is not ProvenanceStatus.VERIFIED:
            blockers.append(_provenance_blocker("disjoint_assignments", recomputed.status, recomputed.reason))

    disjoint = provenance.get("disjoint_assignments")
    if disjoint is None:
        blockers.append(
            ValidationBlocker(
                "overlapping_assignments",
                "content-level disjointness is not verified",
                "disjoint_assignments",
            )
        )
    elif not _is_verified_disjoint_result(disjoint):
        blockers.append(
            ValidationBlocker(
                "provenance_conflict",
                "caller-supplied disjointness status is not verifier-issued",
                "disjoint_assignments",
            )
        )
    elif recomputed is not None and (
        disjoint.status is not recomputed.status
        or disjoint.overlap != recomputed.overlap
        or disjoint._disjoint_fingerprint != _disjoint_fingerprint(adaptation, evaluation)
    ):
        blockers.append(
            ValidationBlocker(
                "provenance_conflict",
                "caller-supplied disjointness does not match recomputed verified records",
                "disjoint_assignments",
            )
        )
    return tuple(_unique(blockers))


def validate_feasibility_input(feasibility: Any) -> tuple[ValidationBlocker, ...]:
    """Require synthetic-only feasibility evidence while retaining real blockers."""

    if isinstance(feasibility, SyntheticFeasibilityObservation):
        values = feasibility.to_mapping()
    elif isinstance(feasibility, Mapping):
        values = feasibility
    else:
        return (ValidationBlocker("shape_mismatch", "feasibility observation is missing", "feasibility"),)
    blockers: list[ValidationBlocker] = []
    if values.get("mode") != "synthetic_only":
        blockers.append(ValidationBlocker("shape_mismatch", "feasibility must be synthetic-only", "feasibility.mode"))
    for field in ("real_data_accessed", "publication_metrics_present", "real_resource_fields_resolved"):
        if values.get(field) is not False:
            blockers.append(ValidationBlocker("authorization_blocked", f"{field} must be false", f"feasibility.{field}"))
    if values.get("status") not in {"pass", "PASS", "blocked", "RESOURCE_BLOCKED", None}:
        blockers.append(ValidationBlocker("shape_mismatch", "unsupported feasibility status", "feasibility.status"))
    if values.get("status") in {"pass", "PASS"}:
        if not isinstance(values.get("matrix_identity_hash"), str) or not is_sha256(values.get("matrix_identity_hash")):
            blockers.append(ValidationBlocker("RESOURCE_BLOCKED", "feasibility requires an explicit matrix identity", "feasibility.matrix_identity_hash"))
        if values.get("synthetic_forward_success") is not True or values.get("synthetic_backward_success") is not True:
            blockers.append(ValidationBlocker("RESOURCE_BLOCKED", "feasibility requires explicit forward and backward evidence", "feasibility"))
        if values.get("production_fit_established") is not True:
            blockers.append(ValidationBlocker("RESOURCE_BLOCKED", "feasibility pass cannot establish production fit without complete callbacks", "feasibility.production_fit_established"))
    return tuple(_unique(blockers))


def aggregate_validators(
    *,
    matrix: Any = None,
    provenance: Any = None,
    feasibility: Any = None,
    target_adaptation: Any = None,
    target_evaluation: Any = None,
    blockers: Sequence[Any] = (),
) -> ValidationReport:
    """Aggregate independent checks before any real-data access can be attempted."""

    findings: list[ValidationBlocker] = []
    if matrix is not None:
        findings.extend(validate_matrix_input(matrix))
    if provenance is not None:
        findings.extend(validate_provenance_inputs(provenance))
    if feasibility is not None:
        findings.extend(validate_feasibility_input(feasibility))
    findings.extend(_target_isolation_blockers(target_adaptation, target_evaluation))
    for blocker in blockers:
        if isinstance(blocker, ValidationBlocker):
            findings.append(blocker)
        elif isinstance(blocker, Mapping):
            findings.append(ValidationBlocker(str(blocker.get("code", "authorization_blocked")), str(blocker.get("message", "blocked")), blocker.get("field")))
        else:
            findings.append(ValidationBlocker("authorization_blocked", str(blocker)))
    return ValidationReport(tuple(_unique(findings)), data_access_opened=False)


def validate_blockers(blockers: Sequence[Any]) -> tuple[ValidationBlocker, ...]:
    """Normalize explicit blocker records without treating them as resolved."""

    return tuple(aggregate_validators(blockers=blockers).blockers)


def aggregate_validation(**kwargs: Any) -> ValidationReport:
    """Compatibility spelling for the aggregate fail-closed validator."""

    return aggregate_validators(**kwargs)


def validate_all(**kwargs: Any) -> ValidationReport:
    """Short compatibility spelling used by preparation callers."""

    return aggregate_validators(**kwargs)


def _bind_outer_matrix_identity(
    outer_matrix_id: Any, rows: Sequence[ExperimentRow]
) -> tuple[ValidationBlocker, ...]:
    """Bind the outer identity to the identity carried by validated rows."""

    if not rows:
        return ()
    canonical_row_identity = rows[0].matrix_id
    if outer_matrix_id != canonical_row_identity:
        return (
            ValidationBlocker(
                "hash_mismatch",
                "outer matrix identity does not match the validated complete rows",
                "matrix.matrix_id",
            ),
        )
    return ()


def _check_rows(rows: Sequence[ExperimentRow]) -> tuple[ValidationBlocker, ...]:
    blockers: list[ValidationBlocker] = []
    for row in rows:
        if row.state.value == "COMPLETED":
            blockers.append(ValidationBlocker("incomplete_matrix", "completed rows are forbidden", "matrix.rows"))
        if row.completion_allowed is not False:
            blockers.append(ValidationBlocker("incomplete_matrix", "completion is not allowed", "matrix.rows"))
    return tuple(_unique(blockers))


def _provenance_blocker(name: str, status: ProvenanceStatus, reason: str | None) -> ValidationBlocker:
    code = {
        ProvenanceStatus.BLOCKED_DATA: "missing_assignment",
        ProvenanceStatus.OVERLAPPING_ASSIGNMENTS: "overlapping_assignments",
        ProvenanceStatus.PROVENANCE_MISMATCH: "hash_mismatch",
    }.get(status, "provenance_conflict")
    return ValidationBlocker(code, reason or f"{name} provenance is invalid", name)


def _unique(blockers: Sequence[ValidationBlocker]) -> list[ValidationBlocker]:
    seen: set[tuple[str, str, str | None]] = set()
    result: list[ValidationBlocker] = []
    for blocker in blockers:
        identity = (blocker.code, blocker.message, blocker.field)
        if identity not in seen:
            seen.add(identity)
            result.append(blocker)
    return result
