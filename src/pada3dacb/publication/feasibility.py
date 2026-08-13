"""Synthetic-only Phase 18 feasibility and resource-budget contracts.

This module deliberately contains no data loaders, training imports, optimizers, or
publication metrics.  It validates production-shaped synthetic contracts and records
engineering observations without authorizing or closing any real resource field.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .canonical_json import is_sha256


class EvidenceType(str, Enum):
    MEASURED_SYNTHETIC = "measured_synthetic"
    EXTRAPOLATED_FROM_SYNTHETIC = "extrapolated_from_synthetic"
    NOT_RECORDED = "not_recorded"
    BLOCKED = "blocked"


EVIDENCE_TYPES = tuple(item.value for item in EvidenceType)


class SyntheticFeasibilityStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    RESOURCE_BLOCKED = "RESOURCE_BLOCKED"


class ResourceBudgetStatus(str, Enum):
    UNRESOLVED_BLOCKING = "unresolved_blocking"


class ResourceBudgetClosureError(ValueError):
    """Raised when synthetic/planning evidence is mistaken for real closure."""


@dataclass(frozen=True)
class ProductionShapeMetadata:
    """Explicit, faithful production tensor shapes and labels.

    Shapes are full shapes, including batch dimensions where the model contract has
    one.  The values are metadata only; this class never allocates a production-sized
    tensor or discovers a model configuration.
    """

    input_shape: tuple[int, ...]
    feature_shape: tuple[int, ...]
    roi_mask_shape: tuple[int, ...]
    token_shape: tuple[int, ...]
    embedding_shape: tuple[int, ...]
    concepts_shape: tuple[int, ...]
    c_target_shape: tuple[int, ...]
    g_bar_shape: tuple[int, ...]
    diagnosis_logits_shape: tuple[int, ...]
    class_labels: tuple[str, ...]

    @property
    def target_concepts_shape(self) -> tuple[int, ...]:
        """Compatibility alias for the explicit ``c_target`` contract."""

        return self.c_target_shape
    roi_labels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ProductionShapeMetadata:
        """Create metadata from an explicit machine-readable shape mapping."""

        required = (
            "input_shape",
            "feature_shape",
            "roi_mask_shape",
            "token_shape",
            "embedding_shape",
            "concepts_shape",
            "c_target_shape",
            "g_bar_shape",
            "diagnosis_logits_shape",
            "class_labels",
            "roi_labels",
        )
        missing = [name for name in required if name not in value]
        if missing:
            raise ValueError(f"production shape metadata is missing: {', '.join(missing)}")
        return cls(
            **{
                name: tuple(value[name]) if name.endswith("shape") else tuple(value[name])
                for name in required
            }
        )

    def validation_errors(self, *, requested_batch_size: int) -> tuple[str, ...]:
        errors: list[str] = []
        shapes = {
            "input_shape": self.input_shape,
            "feature_shape": self.feature_shape,
            "roi_mask_shape": self.roi_mask_shape,
            "token_shape": self.token_shape,
            "embedding_shape": self.embedding_shape,
            "concepts_shape": self.concepts_shape,
            "target_concepts_shape": self.target_concepts_shape,
            "g_bar_shape": self.g_bar_shape,
            "diagnosis_logits_shape": self.diagnosis_logits_shape,
        }
        if any(
            not isinstance(dimension, int) or isinstance(dimension, bool) or dimension <= 0
            for shape in shapes.values()
            for dimension in shape
        ):
            errors.append("shape_dimensions_must_be_positive_integers")
            return tuple(errors)
        if requested_batch_size <= 0:
            errors.append("requested_batch_size_must_be_positive")
            return tuple(errors)
        if len(self.input_shape) != 5 or self.input_shape[0] != requested_batch_size:
            errors.append("input_shape_mismatch")
        elif self.input_shape[1] != 1:
            errors.append("input_channel_mismatch")
        batch_shapes = (
            ("feature_shape", self.feature_shape),
            ("token_shape", self.token_shape),
            ("embedding_shape", self.embedding_shape),
            ("concepts_shape", self.concepts_shape),
            ("c_target_shape", self.c_target_shape),
            ("g_bar_shape", self.g_bar_shape),
            ("diagnosis_logits_shape", self.diagnosis_logits_shape),
        )
        for name, shape in batch_shapes:
            if not shape or shape[0] != requested_batch_size:
                errors.append(f"{name}_batch_mismatch")
        if len(self.feature_shape) != 5 or self.feature_shape[1] != 256:
            errors.append("feature_channel_mismatch")
        if len(self.roi_mask_shape) != 4 or self.roi_mask_shape[0] != 102:
            errors.append("roi_count_mismatch")
        if len(self.token_shape) != 3 or self.token_shape[1:] != (102, 128):
            errors.append("token_shape_mismatch")
        if len(self.embedding_shape) != 2 or self.embedding_shape[1] != 128:
            errors.append("embedding_shape_mismatch")
        for name, shape in (
            ("concepts_shape", self.concepts_shape),
            ("target_concepts_shape", self.target_concepts_shape),
        ):
            if len(shape) != 2 or shape[1] != 102:
                errors.append(f"{name}_mismatch")
        if len(self.g_bar_shape) != 2 or self.g_bar_shape != (requested_batch_size, 102):
            errors.append("g_bar_shape_mismatch")
        if len(self.diagnosis_logits_shape) != 2 or self.diagnosis_logits_shape[1] != 3:
            errors.append("diagnosis_class_count_mismatch")
        if self.class_labels != ("CN", "MCI", "AD"):
            errors.append("class_order_mismatch")
        if len(self.roi_labels) != 102 or len(set(self.roi_labels)) != 102:
            errors.append("roi_order_mismatch")
        return tuple(dict.fromkeys(errors))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "input_shape": list(self.input_shape),
            "feature_shape": list(self.feature_shape),
            "roi_mask_shape": list(self.roi_mask_shape),
            "token_shape": list(self.token_shape),
            "embedding_shape": list(self.embedding_shape),
            "concepts_shape": list(self.concepts_shape),
            "c_target_shape": list(self.c_target_shape),
            "g_bar_shape": list(self.g_bar_shape),
            "diagnosis_logits_shape": list(self.diagnosis_logits_shape),
            "class_labels": list(self.class_labels),
            "roi_labels": list(self.roi_labels),
        }


@dataclass(frozen=True)
class SyntheticTensor:
    """A deterministic CPU-safe tensor descriptor used by pure probe callbacks."""

    shape: tuple[int, ...]
    dtype: str = "float32"
    device: str = "cpu"
    finite: bool = True
    fill_value: float = 0.0


@dataclass(frozen=True)
class SyntheticFeasibilityObservation:
    schema_version: str
    mode: str
    real_data_accessed: bool
    publication_metrics_present: bool
    seed: int
    matrix_identity_hash: str
    device: str
    dtype: str
    parameter_count: int | None
    production_input_shape: tuple[int, ...] | None
    requested_batch_size: int | None
    synthetic_forward_success: bool | None
    synthetic_backward_success: bool | None
    synthetic_peak_memory_bytes: int | None
    synthetic_wall_time_seconds: float | None
    synthetic_storage_bytes: int | None
    synthetic_workers: int | None
    status: SyntheticFeasibilityStatus
    evidence_type: EvidenceType
    failure_reasons: tuple[str, ...]
    observation_namespace: str
    production_fit_established: bool
    real_resource_fields_resolved: bool

    def __post_init__(self) -> None:
        if self.schema_version != "phase18.feasibility.v1":
            raise ValueError("unsupported feasibility schema version")
        if self.mode != "synthetic_only" or self.real_data_accessed:
            raise ValueError("feasibility observations must remain synthetic-only")
        if self.publication_metrics_present or self.real_resource_fields_resolved:
            raise ValueError("synthetic observations cannot authorize real evidence")
        if self.seed != 42:
            raise ValueError("synthetic feasibility seed must be 42")
        for name, value in (
            ("synthetic_forward_success", self.synthetic_forward_success),
            ("synthetic_backward_success", self.synthetic_backward_success),
            ("production_fit_established", self.production_fit_established),
            ("real_resource_fields_resolved", self.real_resource_fields_resolved),
        ):
            if type(value) is not bool and value is not None:
                raise ValueError(f"{name} must be an explicit boolean or None")
        if self.observation_namespace == "non_publication_engineering_probe" and self.production_fit_established:
            raise ValueError("engineering-only probes cannot establish production fit")
        if self.production_fit_established and (
            self.status is not SyntheticFeasibilityStatus.PASS
            or not is_sha256(self.matrix_identity_hash)
            or self.synthetic_forward_success is not True
            or self.synthetic_backward_success is not True
        ):
            raise ValueError(
                "production fit requires a non-unresolved matrix identity and explicit callback evidence"
            )
        if self.evidence_type.value not in EVIDENCE_TYPES:
            raise ValueError("unsupported evidence_type")

    def to_mapping(self) -> dict[str, Any]:
        def recorded(value: Any) -> Any:
            return "not_recorded" if value is None else value

        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "real_data_accessed": self.real_data_accessed,
            "publication_metrics_present": self.publication_metrics_present,
            "seed": self.seed,
            "matrix_identity_hash": self.matrix_identity_hash,
            "device": self.device,
            "dtype": self.dtype,
            "parameter_count": recorded(self.parameter_count),
            "production_input_shape": recorded(
                None if self.production_input_shape is None else list(self.production_input_shape)
            ),
            "requested_batch_size": recorded(self.requested_batch_size),
            "synthetic_forward_success": recorded(self.synthetic_forward_success),
            "synthetic_backward_success": recorded(self.synthetic_backward_success),
            "synthetic_peak_memory_bytes": recorded(self.synthetic_peak_memory_bytes),
            "synthetic_wall_time_seconds": recorded(self.synthetic_wall_time_seconds),
            "synthetic_storage_bytes": recorded(self.synthetic_storage_bytes),
            "synthetic_workers": recorded(self.synthetic_workers),
            "status": self.status.value,
            "evidence_type": self.evidence_type.value,
            "failure_reasons": list(self.failure_reasons),
            "observation_namespace": self.observation_namespace,
            "production_fit_established": self.production_fit_established,
            "real_resource_fields_resolved": self.real_resource_fields_resolved,
        }


# Short compatibility name for callers that refer to the required observation record.
FeasibilityObservation = SyntheticFeasibilityObservation


def run_synthetic_feasibility(
    production_shape: ProductionShapeMetadata | Mapping[str, Any] | None,
    *,
    requested_batch_size: int | None = None,
    parameter_count: int | None = None,
    matrix_identity_hash: str = "unresolved",
    device: str = "cpu",
    dtype: str = "float32",
    forward_callback: Callable[[Mapping[str, SyntheticTensor]], Any] | None = None,
    backward_callback: Callable[[Mapping[str, SyntheticTensor], Any], Any] | None = None,
    peak_memory_bytes: int | None = None,
    step_time_seconds: float | None = None,
    storage_bytes: int | None = None,
    workers: int | None = None,
    reduced_engineering_probe: bool = False,
) -> SyntheticFeasibilityObservation:
    """Run a deterministic shape/probe check without touching runtime resources.

    Callbacks are pure, injectable test seams.  They receive lightweight synthetic
    tensor descriptors, never paths or real tensors.  Returning ``False`` or raising
    marks the corresponding synthetic operation as failed.
    """

    shape = (
        production_shape
        if isinstance(production_shape, ProductionShapeMetadata) or production_shape is None
        else ProductionShapeMetadata.from_mapping(production_shape)
    )
    batch_size = requested_batch_size
    if batch_size is None and shape is not None and shape.input_shape:
        batch_size = shape.input_shape[0]
    reasons: list[str] = []
    if shape is None:
        reasons.append("production_shape_unavailable")
    if device != "cpu":
        reasons.append("cpu_only_probe_required")
    if batch_size is None:
        reasons.append("requested_batch_size_unavailable")
    if not is_sha256(matrix_identity_hash):
        reasons.append("matrix_identity_required")
    if forward_callback is None:
        reasons.append("forward_callback_required")
    if backward_callback is None:
        reasons.append("backward_callback_required")
    if reasons:
        return _observation(
            shape=shape,
            batch_size=batch_size,
            parameter_count=parameter_count,
            matrix_identity_hash=matrix_identity_hash,
            device=device,
            dtype=dtype,
            status=SyntheticFeasibilityStatus.RESOURCE_BLOCKED,
            evidence_type=EvidenceType.BLOCKED,
            failure_reasons=reasons,
            reduced_engineering_probe=reduced_engineering_probe,
            peak_memory_bytes=peak_memory_bytes,
            step_time_seconds=step_time_seconds,
            storage_bytes=storage_bytes,
            workers=workers,
        )
    assert shape is not None and batch_size is not None
    shape_errors = shape.validation_errors(requested_batch_size=batch_size)
    if shape_errors:
        return _observation(
            shape=shape,
            batch_size=batch_size,
            parameter_count=parameter_count,
            matrix_identity_hash=matrix_identity_hash,
            device=device,
            dtype=dtype,
            status=SyntheticFeasibilityStatus.FAIL,
            evidence_type=EvidenceType.BLOCKED,
            failure_reasons=("shape_mismatch", *shape_errors),
            reduced_engineering_probe=reduced_engineering_probe,
            peak_memory_bytes=peak_memory_bytes,
            step_time_seconds=step_time_seconds,
            storage_bytes=storage_bytes,
            workers=workers,
        )
    batch = _synthetic_batch(shape, device=device, dtype=dtype)
    forward_success: bool | None = None
    backward_success: bool | None = None
    callback_reasons: list[str] = []
    forward_result: Any = None
    if forward_callback is not None:
        try:
            forward_result = forward_callback(batch)
            forward_success = _explicit_callback_success(
                forward_result, operation="forward", reasons=callback_reasons
            )
        except Exception as error:  # callback boundary is recorded, not propagated
            forward_success = False
            callback_reasons.append(f"synthetic_forward_failed:{type(error).__name__}")
    if backward_callback is not None and forward_success is True:
        try:
            backward_result = backward_callback(batch, forward_result)
            backward_success = _explicit_callback_success(
                backward_result, operation="backward", reasons=callback_reasons
            )
        except Exception as error:  # callback boundary is recorded, not propagated
            backward_success = False
            callback_reasons.append(f"synthetic_backward_failed:{type(error).__name__}")
    if forward_success is False or backward_success is False:
        status = SyntheticFeasibilityStatus.FAIL
        evidence_type = EvidenceType.BLOCKED
    else:
        status = SyntheticFeasibilityStatus.PASS
        evidence_type = EvidenceType.MEASURED_SYNTHETIC
    return _observation(
        shape=shape,
        batch_size=batch_size,
        parameter_count=parameter_count,
        matrix_identity_hash=matrix_identity_hash,
        device=device,
        dtype=dtype,
        status=status,
        evidence_type=evidence_type,
        failure_reasons=callback_reasons,
        reduced_engineering_probe=reduced_engineering_probe,
        peak_memory_bytes=peak_memory_bytes,
        step_time_seconds=step_time_seconds,
        storage_bytes=storage_bytes,
        workers=workers,
        synthetic_forward_success=forward_success,
        synthetic_backward_success=backward_success,
    )


def _explicit_callback_success(
    result: Any, *, operation: str, reasons: list[str]
) -> bool:
    """Accept only an exact boolean callback result as operation evidence."""

    if type(result) is bool:
        return result
    reasons.append(f"synthetic_{operation}_invalid_result")
    return False


def _synthetic_batch(
    shape: ProductionShapeMetadata, *, device: str, dtype: str
) -> dict[str, SyntheticTensor]:
    return {
        "x": SyntheticTensor(shape.input_shape, dtype=dtype, device=device),
        "feature_map": SyntheticTensor(shape.feature_shape, dtype=dtype, device=device),
        "roi_masks": SyntheticTensor(shape.roi_mask_shape, dtype=dtype, device=device),
        "tokens": SyntheticTensor(shape.token_shape, dtype=dtype, device=device),
        "z": SyntheticTensor(shape.embedding_shape, dtype=dtype, device=device),
        "concepts": SyntheticTensor(shape.concepts_shape, dtype=dtype, device=device),
        "c_target": SyntheticTensor(shape.c_target_shape, dtype=dtype, device=device),
        "g_bar": SyntheticTensor(shape.g_bar_shape, dtype=dtype, device=device),
        "logits": SyntheticTensor(shape.diagnosis_logits_shape, dtype=dtype, device=device),
    }


def _observation(
    *,
    shape: ProductionShapeMetadata | None,
    batch_size: int | None,
    parameter_count: int | None,
    matrix_identity_hash: str,
    device: str,
    dtype: str,
    status: SyntheticFeasibilityStatus,
    evidence_type: EvidenceType,
    failure_reasons: Sequence[str],
    reduced_engineering_probe: bool,
    peak_memory_bytes: int | None,
    step_time_seconds: float | None,
    storage_bytes: int | None,
    workers: int | None,
    synthetic_forward_success: bool | None = None,
    synthetic_backward_success: bool | None = None,
) -> SyntheticFeasibilityObservation:
    return SyntheticFeasibilityObservation(
        schema_version="phase18.feasibility.v1",
        mode="synthetic_only",
        real_data_accessed=False,
        publication_metrics_present=False,
        seed=42,
        matrix_identity_hash=matrix_identity_hash,
        device=device,
        dtype=dtype,
        parameter_count=parameter_count,
        production_input_shape=None if shape is None else shape.input_shape,
        requested_batch_size=batch_size,
        synthetic_forward_success=synthetic_forward_success,
        synthetic_backward_success=synthetic_backward_success,
        synthetic_peak_memory_bytes=peak_memory_bytes,
        synthetic_wall_time_seconds=step_time_seconds,
        synthetic_storage_bytes=storage_bytes,
        synthetic_workers=workers,
        status=status,
        evidence_type=evidence_type,
        failure_reasons=tuple(dict.fromkeys(failure_reasons)),
        observation_namespace=(
            "non_publication_engineering_probe"
            if reduced_engineering_probe
            else "synthetic_feasibility"
        ),
        production_fit_established=(
            status is SyntheticFeasibilityStatus.PASS
            and not reduced_engineering_probe
            and is_sha256(matrix_identity_hash)
            and synthetic_forward_success is True
            and synthetic_backward_success is True
        ),
        real_resource_fields_resolved=False,
    )


@dataclass(frozen=True)
class ResourceBudgetField:
    name: str
    conservative: Any
    nominal: Any
    required_evidence: str
    evidence_type: EvidenceType
    status: ResourceBudgetStatus = ResourceBudgetStatus.UNRESOLVED_BLOCKING
    engineering_value: Any = None

    def to_mapping(self) -> dict[str, Any]:
        return {
            "conservative": self.conservative,
            "nominal": self.nominal,
            "required_evidence": self.required_evidence,
            "evidence_type": self.evidence_type.value,
            "status": self.status.value,
            "engineering_value": self.engineering_value,
        }


@dataclass(frozen=True)
class ResourceBudget:
    methods: int
    directions: int
    folds: int
    seeds: int
    primary_cell_count: int
    sensitivity_projection_count: int
    formulas: Mapping[str, str]
    fields: Mapping[str, ResourceBudgetField]
    status: ResourceBudgetStatus = ResourceBudgetStatus.UNRESOLVED_BLOCKING
    real_budget_closed: bool = False

    def __post_init__(self) -> None:
        if self.real_budget_closed:
            raise ValueError("this synthetic-only slice cannot close a real budget")
        if self.primary_cell_count != self.methods * self.directions * self.folds * self.seeds:
            raise ValueError("primary cell arithmetic is inconsistent")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": "phase18.resource-budget.v1",
            "mode": "synthetic_only_planning",
            "methods": self.methods,
            "directions": self.directions,
            "folds": self.folds,
            "seeds": self.seeds,
            "primary_cell_count": self.primary_cell_count,
            "sensitivity_projection_count": self.sensitivity_projection_count,
            "formulas": dict(self.formulas),
            "fields": {name: field.to_mapping() for name, field in self.fields.items()},
            "status": self.status.value,
            "real_budget_closed": self.real_budget_closed,
            "real_execution_authorized": False,
            "publication_authorized": False,
            "phase_19_forbidden": True,
        }

    def require_real_closure(self) -> None:
        validate_budget_closure(self)


def build_resource_budget(
    *,
    methods: int = 7,
    directions: int = 2,
    folds: int = 5,
    seeds: int = 1,
    staging_margin_bytes: int | None = None,
    synthetic_peak_memory_bytes: int | None = None,
    synthetic_step_time_seconds: float | None = None,
) -> ResourceBudget:
    """Build explicit planning arithmetic while retaining every real blocker."""

    dimensions = {"methods": methods, "directions": directions, "folds": folds, "seeds": seeds}
    if any(type(value) is not int or value <= 0 for value in dimensions.values()):
        raise ValueError("budget dimensions must be positive integers")
    primary_count = methods * directions * folds * seeds
    fields = {
        "device_type": _field("device_type", "UNRESOLVED", "UNRESOLVED", "approved device and backend", EvidenceType.BLOCKED),
        "gpu_vram": _field("gpu_vram", "UNRESOLVED", "UNRESOLVED", "real hardware observation", EvidenceType.BLOCKED, synthetic_peak_memory_bytes),
        "host_ram": _field("host_ram", "UNRESOLVED", "UNRESOLVED", "real hardware observation and margin", EvidenceType.BLOCKED),
        "storage_per_cell": _field("storage_per_cell", "UNRESOLVED", "UNRESOLVED", "measured real artifact sizes", EvidenceType.BLOCKED),
        "total_storage": _field("total_storage", "UNRESOLVED", "UNRESOLVED", "real per-cell storage plus staging margin", EvidenceType.BLOCKED),
        "wall_time_per_primary_cell": _field(
            "wall_time_per_primary_cell", "UNRESOLVED", "UNRESOLVED", "real-data pilot or approved operational evidence",
            EvidenceType.EXTRAPOLATED_FROM_SYNTHETIC if synthetic_step_time_seconds is not None else EvidenceType.NOT_RECORDED,
            synthetic_step_time_seconds,
        ),
        "total_wall_time": _field(
            "total_wall_time", "UNRESOLVED", "UNRESOLVED", "sum of approved real per-cell observations",
            EvidenceType.EXTRAPOLATED_FROM_SYNTHETIC if synthetic_step_time_seconds is not None else EvidenceType.NOT_RECORDED,
            None if synthetic_step_time_seconds is None else primary_count * synthetic_step_time_seconds,
        ),
        "workers": _field("workers", "UNRESOLVED", "UNRESOLVED", "real data-loader observation", EvidenceType.BLOCKED),
        "retry_allowance": _field("retry_allowance", "UNRESOLVED", "UNRESOLVED", "maintainer-selected failure policy", EvidenceType.BLOCKED),
        "concurrency": _field("concurrency", "1 sequential cell", "1 sequential cell", "separate concurrency decision", EvidenceType.NOT_RECORDED),
    }
    storage_formula = (
        f"{primary_count} × measured_storage_per_cell + "
        + ("staging_margin" if staging_margin_bytes is None else str(staging_margin_bytes))
    )
    formulas = {
        "primary_cell_count": f"{methods} × {directions} × {folds} × {seeds} = {primary_count}",
        "primary_storage": storage_formula,
        "primary_wall_time": "sum(measured_or_approved_wall_time_per_cell)",
    }
    return ResourceBudget(
        methods=methods,
        directions=directions,
        folds=folds,
        seeds=seeds,
        primary_cell_count=primary_count,
        sensitivity_projection_count=primary_count,
        formulas=formulas,
        fields=fields,
    )


def _field(
    name: str,
    conservative: Any,
    nominal: Any,
    required_evidence: str,
    evidence_type: EvidenceType,
    engineering_value: Any = None,
) -> ResourceBudgetField:
    return ResourceBudgetField(
        name=name,
        conservative=conservative,
        nominal=nominal,
        required_evidence=required_evidence,
        evidence_type=evidence_type,
        engineering_value=engineering_value,
    )


def validate_budget_closure(budget: ResourceBudget) -> None:
    if not isinstance(budget, ResourceBudget) or not budget.real_budget_closed:
        raise ResourceBudgetClosureError(
            "real evidence is required; synthetic/planning arithmetic cannot close the budget"
        )


# Explicit aliases make the two required record families discoverable to callers.
ResourceBudgetRecord = ResourceBudgetField
SyntheticResourceBudget = ResourceBudget
